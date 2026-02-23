# P0 安全漏洞修复说明文档

## 修复概述

本次修复针对电商MVP项目中发现的两个P0级安全漏洞：
1. **权限验证返回None问题** - 调用方可能忽略None返回值，导致未授权访问
2. **属性注入风险** - 使用`hasattr`动态设置属性，可能导致任意字段被修改

---

## 修复详情

### 1. 权限验证返回None问题修复

#### 问题描述
原代码在权限验证失败时返回`None`，调用方如果未正确处理返回值，可能导致：
- 未授权用户访问/修改其他用户的数据
- 数据泄露或篡改

#### 修复文件

##### 1.1 cart_service.py
**修复位置:** `update_cart_item` 方法 (line 140-142) 和 `remove_from_cart` 方法 (line 167-169)

**修复前:**
```python
# 权限验证
if user_id and cart_item.user_id != user_id:
    return None
```

**修复后:**
```python
# 权限验证
if user_id and cart_item.user_id != user_id:
    raise PermissionError("无权访问此购物车项")
```

同时，当购物车项不存在时，也改为抛出异常而非返回None：
```python
if not cart_item:
    raise ValueError(f"购物车项不存在: {cart_id}")
```

##### 1.2 address_service.py
**修复位置:** 
- `update_address` 方法 (line 96-98)
- `delete_address` 方法 (line 112-114)
- `set_default_address` 方法 (line 130-132)

**修复前:**
```python
# 权限验证
if address.user_id != user_id:
    return None  # 或 return False
```

**修复后:**
```python
# 权限验证
if address.user_id != user_id:
    raise PermissionError("无权访问此地址")
```

同时，当地址不存在时抛出`ValueError`。

##### 1.3 order_service.py
**修复位置:**
- `cancel_order` 方法 (line 166-168)
- `refund_order` 方法

**修复前:**
```python
if not order:
    return None
```

**修复后:**
```python
if not order:
    raise PermissionError("订单不存在或无权访问")
```

---

### 2. 属性注入风险修复

#### 问题描述
原代码使用`hasattr`检查字段是否存在后直接设置值，攻击者可能通过构造特定的请求参数来修改敏感字段（如`user_id`、`id`、`created_at`等）。

#### 修复文件

##### 2.1 product_service.py

**修复位置1:** `update_category` 方法 (line 56-66)

**修复前:**
```python
for field, value in update_data.items():
    if hasattr(category, field):
        setattr(category, field, value)
```

**修复后:**
```python
# 使用白名单防止属性注入攻击
ALLOWED_FIELDS = {"name", "description", "parent_id", "is_active", "sort_order"}
for field, value in update_data.items():
    if field in ALLOWED_FIELDS and hasattr(category, field):
        setattr(category, field, value)
```

**修复位置2:** `update_product` 方法 (line 137-148)

**修复后:**
```python
# 使用白名单防止属性注入攻击
ALLOWED_FIELDS = {"name", "description", "price", "original_price", "stock", 
                 "category_id", "images", "sort_order", "status"}
for field, value in update_data.items():
    if field in ALLOWED_FIELDS and hasattr(product, field):
        setattr(product, field, value)
```

**修复位置3:** `update_product_spec` 方法

**修复后:**
```python
# 使用白名单防止属性注入攻击
ALLOWED_FIELDS = {"name", "values"}
for field, value in update_data.items():
    if field in ALLOWED_FIELDS and hasattr(spec, field):
        setattr(spec, field, value)
```

##### 2.2 address_service.py

**修复位置:** `update_address` 方法

**修复后:**
```python
# 更新字段 - 使用白名单防止属性注入
ALLOWED_FIELDS = {"name", "phone", "province", "city", "district", "detail", "zip_code", "is_default"}
for field, value in update_data.items():
    if field in ALLOWED_FIELDS and hasattr(address, field):
        setattr(address, field, value)
```

---

## 修复验证

运行测试脚本验证修复：

```bash
python3 test_security_fixes.py
```

测试结果：
- ✅ 权限验证修复: 通过
- ✅ 属性注入防护: 通过
- ✅ 危险模式检查: 通过

---

## 调用方适配建议

由于服务层方法现在会抛出异常而非返回None，调用方需要更新异常处理逻辑：

### 修复前调用方式:
```python
result = cart_service.update_cart_item(db, cart_id, quantity, user_id)
if result is None:
    # 处理失败情况
    return {"error": "操作失败"}
```

### 修复后调用方式:
```python
try:
    result = cart_service.update_cart_item(db, cart_id, quantity, user_id)
except PermissionError as e:
    return {"error": str(e), "code": 403}
except ValueError as e:
    return {"error": str(e), "code": 404}
```

---

## 安全改进总结

| 漏洞类型 | 风险等级 | 修复前 | 修复后 |
|---------|---------|-------|-------|
| 权限验证返回None | P0 | 返回None，可能被忽略 | 抛出PermissionError |
| 属性注入 | P0 | 可修改任意字段 | 白名单限制可修改字段 |

---

## 后续建议

1. **API层统一异常处理**: 建议在API路由层添加统一的异常处理器，将PermissionError转换为HTTP 403响应
2. **日志审计**: 建议记录所有权限验证失败和异常操作，便于安全审计
3. **单元测试**: 为权限验证和属性注入防护添加专门的单元测试用例
4. **代码审查**: 对其他服务层代码进行类似的安全审查

---

## 修复时间
2026-02-21

## 修复人
Amelia (开发者)
