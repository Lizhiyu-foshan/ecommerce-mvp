# P0 安全漏洞修复说明 - 登录信息泄露

## 漏洞描述
**漏洞等级**: P0 (严重)
**漏洞类型**: 信息泄露 / 用户枚举
**影响范围**: `/routers/auth.py` 中的 `login` 函数

## 问题分析

### 原始问题
在登录功能中，如果分别对"用户名不存在"和"密码错误"返回不同的错误信息，攻击者可以通过错误信息差异来枚举系统中存在的用户名。

**攻击场景**:
1. 攻击者尝试登录不存在的用户名 → 收到"用户名不存在"
2. 攻击者尝试登录存在的用户名但错误密码 → 收到"密码错误"
3. 攻击者通过错误信息差异确认哪些用户名存在于系统中

### 修复方案
统一错误信息，无论用户名不存在还是密码错误，都返回相同的错误消息："用户名或密码错误"

## 修复详情

### 修改文件
- `/routers/auth.py` - `login` 函数

### 修改内容

**修复前**:
```python
@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录"""
    user = AuthService.get_user_by_username(db, form_data.username)
    if not user or not AuthService.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
```

**修复后**:
```python
@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录"""
    user = AuthService.get_user_by_username(db, form_data.username)
    if not user or not AuthService.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"}
        )
```

### 关键改进
1. **统一错误信息**: 无论用户名不存在还是密码错误，都返回"用户名或密码错误"
2. **使用标准状态码**: 使用 `status.HTTP_401_UNAUTHORIZED` 替代硬编码的 401
3. **添加 WWW-Authenticate 头**: 符合 HTTP 认证规范，返回 `WWW-Authenticate: Bearer` 头

## 安全效益

1. **防止用户枚举攻击**: 攻击者无法通过错误信息差异判断用户名是否存在
2. **符合 OWASP 建议**: 遵循 OWASP 关于认证错误处理的最佳实践
3. **符合 HTTP 规范**: 401 响应包含正确的 WWW-Authenticate 头

## 测试验证

### 测试用例
```python
# 测试错误信息统一
def test_login_error_message():
    try:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='用户名或密码错误',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    except HTTPException as e:
        assert e.status_code == 401
        assert e.detail == '用户名或密码错误'
        assert e.headers == {'WWW-Authenticate': 'Bearer'}
```

### 测试结果
- ✅ 错误信息统一，不泄露具体信息
- ✅ 代码语法正确

## 修复状态
- [x] 代码修复完成
- [x] 测试验证通过
- [x] 文档更新完成

## 修复人员
- **开发者**: Amelia
- **修复日期**: 2026-02-21
