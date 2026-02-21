"""
电商系统认证模块单元测试
使用 pytest 框架和 SQLite 内存数据库
"""

import pytest
import time
import json
import base64
from auth import AuthManager, UserExistsError, InvalidCredentialsError, TokenExpiredError, InvalidTokenError


# ==================== Fixtures ====================

@pytest.fixture
def auth_manager():
    """
    测试夹具：创建认证管理器实例
    每个测试函数前都会创建一个新的内存数据库实例
    """
    return AuthManager(db_path=":memory:")


@pytest.fixture
def registered_user(auth_manager):
    """
    测试夹具：创建已注册的用户
    用于需要已存在用户的测试场景
    """
    return auth_manager.register(
        username="testuser",
        email="test@example.com",
        password="password123"
    )


# ==================== 用户注册功能测试 ====================

class TestUserRegistration:
    """测试用户注册功能"""
    
    def test_normal_registration(self, auth_manager):
        """
        测试正常用户注册
        
        场景：使用有效的用户名、邮箱和密码注册新用户
        期望：注册成功，返回用户信息
        """
        result = auth_manager.register(
            username="newuser",
            email="newuser@example.com",
            password="securepassword123"
        )
        
        assert result["user_id"] is not None
        assert result["username"] == "newuser"
        assert result["email"] == "newuser@example.com"
        assert result["message"] == "注册成功"
    
    def test_duplicate_username_registration(self, auth_manager, registered_user):
        """
        测试重复用户名注册
        
        场景：尝试使用已被注册的用户名注册
        期望：抛出 UserExistsError 异常
        """
        with pytest.raises(UserExistsError) as exc_info:
            auth_manager.register(
                username="testuser",  # 与registered_user相同的用户名
                email="different@example.com",
                password="password456"
            )
        
        assert "已被注册" in str(exc_info.value)
        assert "testuser" in str(exc_info.value)
    
    def test_duplicate_email_registration(self, auth_manager, registered_user):
        """
        测试重复邮箱注册
        
        场景：尝试使用已被注册的邮箱注册
        期望：抛出 UserExistsError 异常
        """
        with pytest.raises(UserExistsError) as exc_info:
            auth_manager.register(
                username="differentuser",
                email="test@example.com",  # 与registered_user相同的邮箱
                password="password456"
            )
        
        assert "已被注册" in str(exc_info.value)
        assert "test@example.com" in str(exc_info.value)
    
    def test_multiple_users_registration(self, auth_manager):
        """
        测试多个用户注册
        
        场景：注册多个不同用户
        期望：所有用户都能成功注册
        """
        users = [
            ("user1", "user1@example.com", "pass1"),
            ("user2", "user2@example.com", "pass2"),
            ("user3", "user3@example.com", "pass3")
        ]
        
        results = []
        for username, email, password in users:
            result = auth_manager.register(username, email, password)
            results.append(result)
        
        assert len(results) == 3
        assert results[0]["user_id"] == 1
        assert results[1]["user_id"] == 2
        assert results[2]["user_id"] == 3


# ==================== 用户登录功能测试 ====================

class TestUserLogin:
    """测试用户登录功能"""
    
    def test_login_with_correct_password(self, auth_manager, registered_user):
        """
        测试使用正确密码登录
        
        场景：使用正确的用户名和密码登录
        期望：登录成功，返回Token和用户信息
        """
        result = auth_manager.login(
            username="testuser",
            password="password123"
        )
        
        assert result["token"] is not None
        assert len(result["token"]) > 0
        assert result["user_id"] == registered_user["user_id"]
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert result["message"] == "登录成功"
    
    def test_login_with_wrong_password(self, auth_manager, registered_user):
        """
        测试使用错误密码登录
        
        场景：使用错误的密码尝试登录
        期望：抛出 InvalidCredentialsError 异常
        """
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_manager.login(
                username="testuser",
                password="wrongpassword"
            )
        
        assert "密码错误" in str(exc_info.value)
    
    def test_login_with_nonexistent_user(self, auth_manager):
        """
        测试不存在的用户登录
        
        场景：使用不存在的用户名尝试登录
        期望：抛出 InvalidCredentialsError 异常
        """
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_manager.login(
                username="nonexistentuser",
                password="anypassword"
            )
        
        assert "用户名不存在" in str(exc_info.value)
    
    def test_login_case_sensitivity(self, auth_manager, registered_user):
        """
        测试用户名大小写敏感性
        
        场景：使用不同大小写的用户名登录
        期望：视为不同用户，抛出异常
        """
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_manager.login(
                username="TESTUSER",  # 大写
                password="password123"
            )
        
        assert "用户名不存在" in str(exc_info.value)


# ==================== JWT Token 功能测试 ====================

class TestJWTToken:
    """测试 JWT Token 功能"""
    
    def test_token_generation(self, auth_manager, registered_user):
        """
        测试 Token 生成
        
        场景：用户登录后生成Token
        期望：Token格式正确，包含三个部分（header.payload.signature）
        """
        result = auth_manager.login(
            username="testuser",
            password="password123"
        )
        
        token = result["token"]
        parts = token.split(".")
        
        assert len(parts) == 3
        assert all(len(part) > 0 for part in parts)
    
    def test_token_verification(self, auth_manager, registered_user):
        """
        测试 Token 验证
        
        场景：验证有效的Token
        期望：返回Token包含的用户信息
        """
        # 先登录获取Token
        login_result = auth_manager.login(
            username="testuser",
            password="password123"
        )
        token = login_result["token"]
        
        # 验证Token
        verification = auth_manager.verify_token(token)
        
        assert verification["valid"] is True
        assert verification["user_id"] == registered_user["user_id"]
        assert verification["username"] == "testuser"
        assert "issued_at" in verification
        assert "expires_at" in verification
    
    def test_token_expiration(self, auth_manager, registered_user):
        """
        测试 Token 过期
        
        场景：Token超过有效期后验证
        期望：抛出 TokenExpiredError 异常
        """
        # 设置极短的Token有效期以便测试
        auth_manager.token_expiry = 1  # 1秒过期
        
        # 登录获取Token
        login_result = auth_manager.login(
            username="testuser",
            password="password123"
        )
        token = login_result["token"]
        
        # 等待Token过期
        time.sleep(2)
        
        # 验证过期Token
        with pytest.raises(TokenExpiredError) as exc_info:
            auth_manager.verify_token(token)
        
        assert "已过期" in str(exc_info.value)
    
    def test_invalid_token_format(self, auth_manager):
        """
        测试无效Token格式
        
        场景：验证格式不正确的Token
        期望：抛出 InvalidTokenError 异常
        """
        invalid_tokens = [
            "invalid.token",  # 缺少一部分
            "only_one_part",  # 只有一部分
            "too.many.parts.here",  # 部分过多
            "",  # 空字符串
            "header.payload",  # 缺少签名
        ]
        
        for token in invalid_tokens:
            with pytest.raises(InvalidTokenError) as exc_info:
                auth_manager.verify_token(token)
            assert "格式无效" in str(exc_info.value) or len(token) == 0
    
    def test_tampered_token_signature(self, auth_manager, registered_user):
        """
        测试篡改Token签名
        
        场景：修改Token的签名部分
        期望：抛出 InvalidTokenError 异常
        """
        # 登录获取Token
        login_result = auth_manager.login(
            username="testuser",
            password="password123"
        )
        token = login_result["token"]
        
        # 篡改签名
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.tampered_signature"
        
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_manager.verify_token(tampered_token)
        
        assert "签名无效" in str(exc_info.value)
    
    def test_tampered_token_payload(self, auth_manager, registered_user):
        """
        测试篡改Token载荷
        
        场景：修改Token的payload部分
        期望：抛出 InvalidTokenError 异常（签名不匹配）
        """
        # 登录获取Token
        login_result = auth_manager.login(
            username="testuser",
            password="password123"
        )
        token = login_result["token"]
        
        # 篡改payload
        parts = token.split(".")
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps({"user_id": 999, "username": "hacker"}).encode()
        ).decode().rstrip("=")
        
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_manager.verify_token(tampered_token)
        
        assert "签名无效" in str(exc_info.value)
    
    def test_token_blacklist(self, auth_manager, registered_user):
        """
        测试 Token 黑名单
        
        场景：注销后的Token加入黑名单
        期望：验证时抛出 InvalidTokenError 异常
        """
        # 登录获取Token
        login_result = auth_manager.login(
            username="testuser",
            password="password123"
        )
        token = login_result["token"]
        
        # 先验证Token有效
        verification = auth_manager.verify_token(token)
        assert verification["valid"] is True
        
        # 注销（将Token加入黑名单）
        auth_manager.logout(token)
        
        # 再次验证应失败
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_manager.verify_token(token)
        
        assert "已被注销" in str(exc_info.value)


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试 - 测试完整的业务流程"""
    
    def test_complete_user_workflow(self, auth_manager):
        """
        测试完整的用户工作流
        
        场景：注册 -> 登录 -> 验证Token -> 注销
        期望：整个流程正常完成
        """
        # 1. 注册
        register_result = auth_manager.register(
            username="workflowuser",
            email="workflow@example.com",
            password="workflowpass123"
        )
        assert register_result["user_id"] is not None
        
        # 2. 登录
        login_result = auth_manager.login(
            username="workflowuser",
            password="workflowpass123"
        )
        assert login_result["token"] is not None
        token = login_result["token"]
        
        # 3. 验证Token
        verification = auth_manager.verify_token(token)
        assert verification["valid"] is True
        assert verification["username"] == "workflowuser"
        
        # 4. 注销
        auth_manager.logout(token)
        
        # 5. 验证注销后的Token无效
        with pytest.raises(InvalidTokenError):
            auth_manager.verify_token(token)
    
    def test_multiple_tokens_same_user(self, auth_manager, registered_user):
        """
        测试同一用户多个Token
        
        场景：同一用户多次登录获取多个Token
        期望：每个Token都独立有效
        """
        # 多次登录（每次登录之间添加短暂延迟确保Token不同）
        tokens = []
        for _ in range(3):
            result = auth_manager.login(
                username="testuser",
                password="password123"
            )
            tokens.append(result["token"])
            time.sleep(1.1)  # 1.1秒延迟确保时间戳（秒级）不同
        
        # 验证所有Token都有效
        for token in tokens:
            verification = auth_manager.verify_token(token)
            assert verification["valid"] is True
            assert verification["username"] == "testuser"
        
        # 注销其中一个Token
        auth_manager.logout(tokens[0])
        
        # 被注销的Token无效
        with pytest.raises(InvalidTokenError):
            auth_manager.verify_token(tokens[0])
        
        # 其他Token仍然有效
        verification = auth_manager.verify_token(tokens[1])
        assert verification["valid"] is True


# ==================== 数据库测试 ====================

class TestDatabaseOperations:
    """测试数据库操作"""
    
    def test_user_persistence(self, auth_manager):
        """
        测试用户数据持久化
        
        场景：注册用户后查询用户信息
        期望：能从数据库获取用户信息
        """
        # 注册用户
        auth_manager.register(
            username="persistuser",
            email="persist@example.com",
            password="persistpass"
        )
        
        # 查询用户
        user = auth_manager.get_user_by_username("persistuser")
        
        assert user is not None
        assert user["username"] == "persistuser"
        assert user["email"] == "persist@example.com"
        assert user["user_id"] == 1
    
    def test_get_nonexistent_user(self, auth_manager):
        """
        测试查询不存在的用户
        
        场景：查询数据库中不存在的用户
        期望：返回None
        """
        user = auth_manager.get_user_by_username("nonexistent")
        
        assert user is None


# ==================== 主程序入口 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])