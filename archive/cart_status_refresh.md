# 购物车状态刷新修复说明 (BUG-005)

## 问题描述
商品下架后，购物车中的商品状态未实时更新，用户仍能看到已下架商品。

## 修复内容

### 1. 新增 `get_cart_with_products` 方法 (cart_service.py)

该方法获取购物车列表时，实时检查每个商品的状态：

- **商品存在且状态正常**：返回完整商品信息，`is_available=True`
- **商品已下架**：`is_available=False`，`unavailable_reason="商品已下架"`
- **库存不足**：`is_available=False`，`unavailable_reason="库存不足"`
- **商品已删除**：`is_available=False`，`unavailable_reason="商品不存在"`

返回字段：
```python
{
    "cart_id": str,          # 购物车项ID
    "product_id": str,       # 商品ID
    "product_name": str,     # 商品名称
    "price": float,          # 单价
    "quantity": int,         # 数量
    "spec_combo": dict,      # 规格组合
    "stock": int,            # 当前库存
    "status": str,           # 商品状态 (active/inactive/deleted)
    "is_available": bool,    # 是否可购买
    "unavailable_reason": str, # 不可购买原因
    "subtotal": float        # 小计金额
}
```

### 2. 增强 `validate_cart_for_checkout` 方法 (cart_service.py)

结算验证时提供更详细的错误信息：
- 商品不存在时返回具体原因
- 商品状态变更时返回当前状态（如"商品已inactive"）
- 库存不足时返回当前库存数量

### 3. 新增商品状态管理方法 (product_service.py)

- `update_product_status(db, product_id, status)`：更新商品状态，记录日志
- `deactivate_product(db, product_id)`：快捷下架商品
- `activate_product(db, product_id)`：快捷上架商品
- `update_stock(db, product_id, quantity)`：更新商品库存

当商品从 `active` 变为 `inactive` 时，会自动记录日志：
```
商品下架: {product_id}，购物车中的该商品将标记为不可用
```

## 状态流转图

```
┌─────────────┐     上架      ┌─────────────┐
│   inactive  │ ────────────▶ │   active    │
│   (已下架)   │               │   (上架中)   │
└─────────────┘ ◀──────────── └─────────────┘
       │              下架              │
       │                                │
       │           删除                 │
       └───────────────────────────────▶┘
                                          │
                                          ▼
                                    ┌─────────────┐
                                    │   deleted   │
                                    │   (已删除)   │
                                    └─────────────┘
```

## 购物车商品状态判断逻辑

```python
def check_product_availability(product, quantity):
    if not product:
        return False, "商品不存在"
    
    if product.status != "active":
        return False, "商品已下架"
    
    if product.stock < quantity:
        return False, "库存不足"
    
    return True, None
```

## 使用示例

### 获取购物车列表（带状态检查）
```python
cart_items = CartService.get_cart_with_products(db, user_id=1)
for item in cart_items:
    if item["is_available"]:
        print(f"可购买: {item['product_name']}")
    else:
        print(f"不可购买: {item['product_name']} - {item['unavailable_reason']}")
```

### 验证购物车是否可结算
```python
result = CartService.validate_cart_for_checkout(db, user_id=1)
if result["valid"]:
    print("可以结算")
else:
    for item in result["invalid_items"]:
        print(f"商品无法购买: {item['reason']}")
```

### 下架商品
```python
# 方法1: 使用状态更新
ProductService.update_product_status(db, product_id, "inactive")

# 方法2: 使用快捷方法
ProductService.deactivate_product(db, product_id)
```

## 测试覆盖

修复包含18个测试用例，覆盖以下场景：

1. **购物车状态检查** (5个测试)
   - 上架商品
   - 下架商品
   - 库存不足商品
   - 已删除商品
   - 混合状态商品

2. **商品状态变更** (5个测试)
   - 商品下架
   - 商品上架
   - 快捷方法
   - 更新不存在商品

3. **结算验证** (6个测试)
   - 所有商品有效
   - 包含下架商品
   - 包含库存不足商品
   - 空购物车
   - 包含已删除商品
   - 混合无效商品

4. **实时状态刷新** (2个测试)
   - 商品状态变更实时反映
   - 库存变更实时反映

## 注意事项

1. **实时性**：购物车状态是实时查询的，不依赖缓存
2. **性能**：每次查询都会关联商品表，大数据量时建议加索引
3. **并发**：商品状态变更和购物车查询可能存在竞态条件，但业务上可接受
4. **软删除**：建议使用软删除（status="deleted"）而非硬删除，以保持购物车记录完整性

## 后续优化建议

1. 添加缓存机制，减少数据库查询
2. 使用消息队列通知购物车服务商品状态变更
3. 前端轮询或 WebSocket 实时更新购物车状态
4. 定期清理长期无效的购物车项
