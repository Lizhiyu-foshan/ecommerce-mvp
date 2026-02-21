# BUG-004 库存扣减并发控制修复文档

## 问题描述

当前库存扣减存在并发问题：多个用户同时购买时，由于读取-修改-写入的非原子操作，可能导致超卖现象。

### 原有问题代码

```python
@staticmethod
def deduct_stock(db: Session, product_id: str, quantity: int) -> bool:
    """扣减库存"""
    product = ProductService.get_product_by_id(db, product_id)  # 读取
    if not product or product.stock < quantity:
        return False
    
    product.stock -= quantity      # 修改
    product.sales_count += quantity
    db.commit()                    # 写入
    return True
```

**问题分析：**
1. 多个并发请求同时读取到相同的库存值
2. 各自扣减后同时写入，导致实际扣减数量小于预期
3. 最终库存可能为负数（超卖）

## 修复方案

采用**数据库级别的原子操作**方案，使用单条 SQL UPDATE 语句完成库存扣减。

### 修复后代码

```python
@staticmethod
def deduct_stock(db: Session, product_id: str, quantity: int) -> bool:
    """
    扣减库存（原子操作，防止并发超卖）
    
    使用数据库级别的原子 UPDATE 操作，避免并发问题：
    - 通过 WHERE stock >= quantity 条件确保库存充足
    - 单条 SQL 语句执行，避免读取-修改-写入的竞争条件
    """
    if quantity <= 0:
        return False
    
    # 使用原子 UPDATE 操作
    result = db.execute(
        text("""
            UPDATE products 
            SET stock = stock - :quantity,
                sales_count = sales_count + :quantity,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :product_id 
            AND stock >= :quantity
        """),
        {
            "product_id": product_id,
            "quantity": quantity
        }
    )
    db.commit()
    
    return result.rowcount > 0
```

### 方案优势

1. **原子性**：单条 SQL 语句执行，数据库保证操作的原子性
2. **无锁竞争**：不需要显式锁定，减少数据库锁等待
3. **高性能**：避免了 SELECT + UPDATE 的往返开销
4. **数据库无关**：SQL 语句兼容 MySQL、PostgreSQL、SQLite 等主流数据库

## 附加功能

### 1. 悲观锁版本（备用）

为需要额外业务逻辑检查的场景提供了 `deduct_stock_with_lock()` 方法：

```python
@staticmethod
def deduct_stock_with_lock(db: Session, product_id: str, quantity: int) -> bool:
    """扣减库存（悲观锁版本）"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.stock >= quantity
    ).with_for_update().first()  # 获取行级锁
    
    if not product:
        return False
    
    product.stock -= quantity
    product.sales_count += quantity
    db.commit()
    return True
```

### 2. 参数校验

- 扣减数量必须大于 0
- 增加了详细的日志记录

## 修改文件

### 1. `/root/.openclaw/workspace/projects/ecommerce-mvp/services/product_service.py`

- 导入 `text` 函数：`from sqlalchemy import or_, and_, text`
- 重写 `deduct_stock()` 方法，使用原子 UPDATE
- 新增 `deduct_stock_with_lock()` 方法

### 2. `/root/.openclaw/workspace/projects/ecommerce-mvp/services/cart_service.py`

无需修改。结算流程在 `order_service.py` 中已使用 `ProductService.deduct_stock()`，自动受益于本次修复。

### 3. `/root/.openclaw/workspace/projects/ecommerce-mvp/tests/test_product_execution.py`

- 更新 `test_deduct_stock_zero` 测试用例（quantity=0 应该返回 False）
- 新增 `TestConcurrentStockDeduction` 测试类，包含 5 个并发测试用例

## 测试验证

### 现有测试

```bash
pytest tests/test_product_execution.py::TestProductManagement::test_deduct_stock_success -v
pytest tests/test_product_execution.py::TestProductManagement::test_deduct_stock_insufficient -v
pytest tests/test_product_execution.py::TestProductManagement::test_deduct_stock_not_exist -v
pytest tests/test_product_execution.py::TestProductManagement::test_deduct_stock_zero -v
```

**结果**：全部通过 ✅

### 新增并发测试

```bash
pytest tests/test_product_execution.py::TestConcurrentStockDeduction -v
```

**测试用例**：
1. `test_concurrent_deduct_stock_no_oversell` - 验证并发扣减不会超卖
2. `test_concurrent_deduct_stock_partial_failure` - 验证库存不足时部分失败
3. `test_concurrent_deduct_stock_large_quantity` - 验证单次大量扣减
4. `test_deduct_stock_negative_quantity` - 验证负数扣减失败
5. `test_deduct_stock_exact_match` - 验证精确扣减（数量等于库存）

**结果**：全部通过 ✅

## 兼容性说明

- **API 兼容**：`deduct_stock()` 方法签名保持不变
- **行为兼容**：正常情况下的返回值和之前一致
- **边界情况**：quantity <= 0 时现在返回 False（更合理的行为）

## 部署建议

1. 无需数据库迁移（没有修改表结构）
2. 建议在生产环境压测验证并发性能
3. 监控库存扣减失败率（正常情况下应该极低）

## 总结

本次修复通过数据库原子操作解决了库存扣减的并发安全问题，有效防止了超卖现象。方案简单高效，无需额外的锁机制或版本号字段。
