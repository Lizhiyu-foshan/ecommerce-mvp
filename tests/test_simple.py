"""
E-Commerce MVP 单元测试 - 简化版
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import AuthService
from services.order_service import OrderService
from services.payment_service import PaymentService


# ==================== 认证服务测试 ====================

class TestAuthService:
    """用户认证服务测试"""
    
    def test_password_hash(self):
        """测试密码哈希生成"""
        password = "testpass123"
        hashed = AuthService.get_password_hash(password)
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")
    
    def test_password_verify_correct(self):
        """测试正确密码验证"""
        password = "testpass123"
        hashed = AuthService.get_password_hash(password)
        assert AuthService.verify_password(password, hashed) is True
    
    def test_password_verify_incorrect(self):
        """测试错误密码验证"""
        password = "testpass123"
        hashed = AuthService.get_password_hash(password)
        assert AuthService.verify_password("wrongpass", hashed) is False
    
    def test_password_verify_long_password(self):
        """测试长密码处理"""
        password = "a" * 100
        hashed = AuthService.get_password_hash(password)
        assert AuthService.verify_password(password[:72], hashed) is True
    
    def test_create_access_token(self):
        """测试访问令牌生成"""
        token = AuthService.create_access_token({"sub": "123"})
        assert token is not None
        assert len(token) > 0
    
    def test_verify_token_valid(self):
        """测试有效令牌验证"""
        token = AuthService.create_access_token({"sub": "123"})
        payload = AuthService.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "123"
    
    def test_verify_token_invalid(self):
        """测试无效令牌验证"""
        payload = AuthService.verify_token("invalid.token.here")
        assert payload is None


# ==================== 订单服务测试 ====================

class TestOrderService:
    """订单服务测试"""
    
    def test_generate_order_no(self):
        """测试订单号生成"""
        order_no = OrderService.generate_order_no()
        assert order_no.startswith("ORD")
        assert len(order_no) > 3
    
    def test_generate_unique_order_no(self):
        """测试订单号唯一性"""
        order_no1 = OrderService.generate_order_no()
        order_no2 = OrderService.generate_order_no()
        assert order_no1 != order_no2


# ==================== 支付服务测试 ====================

class TestPaymentService:
    """支付服务测试"""
    
    def test_generate_payment_no(self):
        """测试支付单号生成"""
        payment_no = PaymentService.generate_payment_no()
        assert payment_no.startswith("PAY")
        assert len(payment_no) > 3
    
    def test_generate_unique_payment_no(self):
        """测试支付单号唯一性"""
        payment_no1 = PaymentService.generate_payment_no()
        payment_no2 = PaymentService.generate_payment_no()
        assert payment_no1 != payment_no2


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
