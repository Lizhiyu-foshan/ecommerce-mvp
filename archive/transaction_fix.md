# 事务管理修复说明 (BUG-006)

## 问题描述

原系统中订单创建和库存扣减不在同一个事务中，可能导致以下数据不一致问题：

1. **订单创建成功但库存扣减失败** - 导致超卖
2. **库存扣减成功但订单创建失败** - 导致库存丢失
3. **购物车清空失败** - 导致重复下单
4. **并发情况下库存计算错误** - 导致超卖

## 修复方案

### 1. 添加事务装饰器工具

创建 `utils/transaction.py` 提供统一的事务管理工具：

```python
@transactional
def create_order(db: Session, ...):
    # 业务逻辑
    # 自动提交或回滚
```

**特性：**
- 自动提交：函数执行成功时自动提交事务
- 自动回滚：发生异常时自动回滚事务
- 日志记录：记录事务提交和回滚事件

### 2. 添加事务上下文管理器

```python
with TransactionContext(db) as tx:
    # 执行业务操作
    tx.db.add(order)
    # 发生异常自动回滚
```

### 3. 订单服务事务改造

#### `create_order_from_cart` 方法

**原子操作步骤：**
1. 验证购物车商品（检查商品状态、库存）
2. 创建订单
3. 扣减库存（使用 `with_for_update()` 加锁）
4. 清空购物车
5. 提交事务

**关键代码：**
```python
@staticmethod
@transactional
def create_order_from_cart(db: Session, user_id: int, cart_items: List[Any], ...):
    # 1. 验证所有商品
    for cart_item in cart_items:
        if cart_item.product.stock < cart_item.quantity:
            raise ValueError("库存不足")
    
    # 2. 创建订单
    db_order = Order(...)
    db.add(db_order)
    db.flush()
    
    # 3. 扣减库存（加锁）
    for item_info in order_items_info:
        product = db.query(...).with_for_update().first()
        product.stock -= item_info["quantity"]
    
    # 4. 清空购物车
    for item_info in order_items_info:
        db.delete(item_info["cart_item"])
```

### 4. 购物车服务事务改造

#### `add_to_cart` 方法
- 使用 `@transactional` 装饰器
- 添加商品库存检查（加锁）
- 合并购物车时检查库存

#### `update_cart_item` 方法
- 使用 `@transactional` 装饰器
- 更新数量时检查库存

#### `checkout_cart` 方法（新增）
- 封装完整的结算流程
- 验证购物车 → 创建订单 → 扣减库存 → 清空购物车

### 5. 并发控制

使用 `with_for_update()` 对库存记录加行锁，防止并发问题：

```python
product = db.query(Product).filter(
    Product.id == product_id
).with_for_update().first()
```

## 修改文件列表

| 文件 | 修改内容 |
|------|----------|
| `utils/transaction.py` | 新增事务管理工具 |
| `services/order_service.py` | 添加 `@transactional` 装饰器，优化 `create_order_from_cart` |
| `services/cart_service.py` | 添加 `@transactional` 装饰器，新增 `checkout_cart` 方法 |
| `tests/test_transaction.py` | 新增事务管理测试 |

## 测试验证

### 测试用例覆盖

1. **事务装饰器测试**
   - 成功提交场景
   - 失败回滚场景

2. **订单创建事务测试**
   - 从购物车创建订单的原子性
   - 库存不足时的回滚

3. **并发控制测试**
   - 行锁防止超卖

4. **购物车事务测试**
   - 添加商品事务
   - 库存不足时回滚

### 测试结果

```
tests/test_transaction.py::TestTransactionManagement::test_transactional_decorator_success PASSED
tests/test_transaction.py::TestTransactionManagement::test_transactional_decorator_rollback PASSED
tests/test_transaction.py::TestTransactionManagement::test_create_order_from_cart_transaction PASSED
tests/test_transaction.py::TestTransactionManagement::test_create_order_from_cart_rollback_on_insufficient_stock PASSED
tests/test_transaction.py::TestTransactionManagement::test_transaction_context_manager PASSED
tests/test_transaction.py::TestTransactionManagement::test_concurrent_stock_deduction_with_lock PASSED
tests/test_transaction.py::TestTransactionManagement::test_cancel_order_transaction PASSED
tests/test_transaction.py::TestTransactionManagement::test_cart_add_transaction PASSED
tests/test_transaction.py::TestTransactionManagement::test_cart_add_transaction_rollback_on_insufficient_stock PASSED

======================== 9 passed ========================
```

## 使用指南

### 在 Service 方法中添加事务

```python
from utils.transaction import transactional

class MyService:
    @staticmethod
    @transactional
    def my_method(db: Session, ...):
        # 业务逻辑
        db.add(entity)
        # 自动提交或回滚
```

### 使用事务上下文管理器

```python
from utils.transaction import TransactionContext

def complex_operation(db: Session):
    with TransactionContext(db) as tx:
        # 多个操作
        db.add(order)
        db.add(payment)
        # 自动提交或回滚
```

## 注意事项

1. **只读操作不需要事务装饰器** - 如 `get_order_by_id`、`get_cart` 等
2. **嵌套事务** - 当前实现使用简单的事务提交/回滚，不支持嵌套事务
3. **行锁使用** - 在更新库存等关键操作时使用 `with_for_update()` 加锁
4. **异常处理** - 业务异常应该抛出，让装饰器处理回滚

## 后续优化建议

1. 考虑使用 SQLAlchemy 的 `session.begin()` 和嵌套事务支持
2. 添加分布式事务支持（微服务架构下）
3. 添加事务超时控制
4. 添加事务监控和告警
