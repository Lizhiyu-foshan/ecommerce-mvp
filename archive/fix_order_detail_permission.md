# 订单详情接口权限验证修复说明

## 问题描述
订单详情接口 `/orders/{order_id}` 缺少权限验证，任何用户（包括未登录用户）都可以查询任意订单信息，存在数据泄露风险。

## 修复内容

### 修改文件
`/root/.openclaw/workspace/projects/ecommerce-mvp/routers/orders.py`

### 具体修改

#### 修改前
```python
@router.get("/{order_id}", response_model=OrderResponse)
def get_order_detail(order_id: int, db: Session = Depends(get_db)):
    """查询订单详情"""
    order = OrderService.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order
```

#### 修改后
```python
@router.get("/{order_id}", response_model=OrderResponse)
def get_order_detail(
    order_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询订单详情"""
    order = OrderService.get_order_by_id(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order
```

## 修复点说明

1. **添加认证依赖**：增加 `current_user: UserResponse = Depends(get_current_user)` 参数，要求请求必须携带有效的认证信息

2. **权限验证**：在查询订单后，验证 `order.user_id != current_user.id`，确保用户只能查看自己的订单

3. **安全考虑**：当订单不存在或用户无权访问时，统一返回 404 "订单不存在"，避免泄露订单是否存在的信息（防止通过接口探测订单ID是否存在）

## 测试建议

1. **未登录访问**：不带 Token 访问接口，应返回 401 Unauthorized
2. **访问自己的订单**：携带自己的 Token 访问自己的订单，应正常返回订单详情
3. **访问他人的订单**：携带自己的 Token 访问其他用户的订单，应返回 404
4. **访问不存在的订单**：访问不存在的 order_id，应返回 404

## 修复状态
✅ 已完成修复并验证
