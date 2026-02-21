"""
购物车状态刷新测试 (BUG-005)
测试购物车商品状态实时更新功能
"""

import pytest
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base
from models import User, Product, Cart
from services.auth_service import AuthService
from services.product_service import ProductService
from services.cart_service import CartService
from models.schemas import UserCreate

# 测试数据库（内存中的 SQLite）
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建测试数据库表
Base.metadata.create_all(bind=engine)


import uuid

# ==================== Fixtures ====================

@pytest.fixture
def db():
    """提供数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db):
    """创建测试用户"""
    unique_id = str(uuid.uuid4())[:8]
    user_data = UserCreate(
        username=f"carttestuser_{unique_id}",
        email=f"carttest_{unique_id}@example.com",
        password="testpass123"
    )
    user = AuthService.create_user(db, user_data)
    return user


@pytest.fixture
def test_product_active(db):
    """创建测试商品（上架状态）"""
    product = ProductService.create_product(
        db=db,
        name="测试商品-上架中",
        price=99.99,
        stock=100
    )
    return product


@pytest.fixture
def test_product_inactive(db):
    """创建测试商品（下架状态）"""
    product = ProductService.create_product(
        db=db,
        name="测试商品-已下架",
        price=99.99,
        stock=100
    )
    # 下架商品
    ProductService.update_product_status(db, product.id, "inactive")
    db.refresh(product)
    return product


@pytest.fixture
def test_product_low_stock(db):
    """创建测试商品（库存不足）"""
    product = ProductService.create_product(
        db=db,
        name="测试商品-库存不足",
        price=99.99,
        stock=1
    )
    return product


# ==================== 购物车状态检查测试 ====================

class TestCartStatusCheck:
    """购物车商品状态检查测试"""
    
    def test_get_cart_with_active_product(self, db, test_user, test_product_active):
        """测试获取包含上架商品的购物车"""
        # 添加商品到购物车
        cart_item = CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=2,
            user_id=test_user.id
        )
        
        # 获取购物车详情
        cart_items = CartService.get_cart_with_products(db, user_id=test_user.id)
        
        assert len(cart_items) == 1
        item = cart_items[0]
        assert item["product_id"] == test_product_active.id
        assert item["product_name"] == test_product_active.name
        assert item["status"] == "active"
        assert item["is_available"] is True
        assert item["unavailable_reason"] is None
        assert item["stock"] == 100
    
    def test_get_cart_with_inactive_product(self, db, test_user, test_product_active):
        """测试获取包含下架商品的购物车"""
        # 添加商品到购物车
        cart_item = CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=2,
            user_id=test_user.id
        )
        
        # 商品下架
        ProductService.update_product_status(db, test_product_active.id, "inactive")
        
        # 获取购物车详情
        cart_items = CartService.get_cart_with_products(db, user_id=test_user.id)
        
        assert len(cart_items) == 1
        item = cart_items[0]
        assert item["product_id"] == test_product_active.id
        assert item["status"] == "inactive"
        assert item["is_available"] is False
        assert item["unavailable_reason"] == "商品已下架"
    
    def test_get_cart_with_low_stock_product(self, db, test_user, test_product_low_stock):
        """测试获取包含库存不足商品的购物车"""
        # 添加商品到购物车（数量超过库存）
        cart_item = CartService.add_to_cart(
            db=db,
            product_id=test_product_low_stock.id,
            quantity=1,
            user_id=test_user.id
        )
        
        # 减少库存
        ProductService.update_stock(db, test_product_low_stock.id, 0)
        
        # 获取购物车详情
        cart_items = CartService.get_cart_with_products(db, user_id=test_user.id)
        
        assert len(cart_items) == 1
        item = cart_items[0]
        assert item["is_available"] is False
        assert item["unavailable_reason"] == "库存不足"
        assert item["stock"] == 0
    
    def test_get_cart_with_deleted_product(self, db, test_user, test_product_active):
        """测试获取包含已删除商品的购物车"""
        # 添加商品到购物车
        cart_item = CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=2,
            user_id=test_user.id
        )
        cart_id = cart_item.id
        product_id = test_product_active.id
        
        # 软删除商品（硬删除会导致外键约束问题）
        ProductService.delete_product(db, test_product_active.id, hard_delete=False)
        
        # 获取购物车详情
        cart_items = CartService.get_cart_with_products(db, user_id=test_user.id)
        
        assert len(cart_items) == 1
        item = cart_items[0]
        assert item["product_id"] == product_id
        assert item["status"] == "deleted"
        assert item["is_available"] is False
        assert item["unavailable_reason"] == "商品已下架"
    
    def test_get_cart_with_mixed_products(self, db, test_user, test_product_active, test_product_inactive, test_product_low_stock):
        """测试获取包含多种状态商品的购物车"""
        # 添加上架商品
        CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=2,
            user_id=test_user.id
        )
        
        # 添加已下架商品 - 先添加上架商品，然后下架它
        inactive_product = ProductService.create_product(
            db=db,
            name="临时下架商品",
            price=99.99,
            stock=100
        )
        CartService.add_to_cart(
            db=db,
            product_id=inactive_product.id,
            quantity=1,
            user_id=test_user.id
        )
        # 下架商品
        ProductService.update_product_status(db, inactive_product.id, "inactive")
        
        # 添加库存不足商品 - 先添加，然后减少库存
        low_stock_product = ProductService.create_product(
            db=db,
            name="临时库存不足商品",
            price=99.99,
            stock=100
        )
        CartService.add_to_cart(
            db=db,
            product_id=low_stock_product.id,
            quantity=5,
            user_id=test_user.id
        )
        # 减少库存使其不足
        ProductService.update_stock(db, low_stock_product.id, 1)
        
        # 获取购物车详情
        cart_items = CartService.get_cart_with_products(db, user_id=test_user.id)
        
        assert len(cart_items) == 3
        
        # 检查每个商品的状态
        available_count = sum(1 for item in cart_items if item["is_available"])
        unavailable_count = sum(1 for item in cart_items if not item["is_available"])
        
        assert available_count == 1  # 只有上架商品可用
        assert unavailable_count == 2  # 下架和库存不足商品不可用


# ==================== 商品状态变更监听测试 ====================

class TestProductStatusChange:
    """商品状态变更监听测试"""
    
    def test_update_product_status_to_inactive(self, db, test_product_active):
        """测试商品下架"""
        old_status = test_product_active.status
        
        updated_product = ProductService.update_product_status(
            db, test_product_active.id, "inactive"
        )
        
        assert updated_product is not None
        assert updated_product.status == "inactive"
        assert old_status == "active"
    
    def test_update_product_status_to_active(self, db, test_product_inactive):
        """测试商品上架"""
        updated_product = ProductService.update_product_status(
            db, test_product_inactive.id, "active"
        )
        
        assert updated_product is not None
        assert updated_product.status == "active"
    
    def test_deactivate_product(self, db, test_product_active):
        """测试快捷下架方法"""
        updated_product = ProductService.deactivate_product(
            db, test_product_active.id
        )
        
        assert updated_product is not None
        assert updated_product.status == "inactive"
    
    def test_activate_product(self, db, test_product_inactive):
        """测试快捷上架方法"""
        updated_product = ProductService.activate_product(
            db, test_product_inactive.id
        )
        
        assert updated_product is not None
        assert updated_product.status == "active"
    
    def test_update_nonexistent_product_status(self, db):
        """测试更新不存在的商品状态"""
        result = ProductService.update_product_status(
            db, "NONEXISTENT-ID", "inactive"
        )
        
        assert result is None


# ==================== 结算验证测试 ====================

class TestCheckoutValidation:
    """结算验证测试"""
    
    def test_validate_cart_with_all_valid_items(self, db, test_user, test_product_active):
        """测试所有商品都可结算"""
        CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=2,
            user_id=test_user.id
        )
        
        result = CartService.validate_cart_for_checkout(db, user_id=test_user.id)
        
        assert result["valid"] is True
        assert result["message"] == "可以结算"
        assert len(result["invalid_items"]) == 0
    
    def test_validate_cart_with_inactive_item(self, db, test_user, test_product_active):
        """测试包含下架商品的购物车"""
        CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=2,
            user_id=test_user.id
        )
        
        # 商品下架
        ProductService.update_product_status(db, test_product_active.id, "inactive")
        
        result = CartService.validate_cart_for_checkout(db, user_id=test_user.id)
        
        assert result["valid"] is False
        assert result["message"] == "部分商品无法购买"
        assert len(result["invalid_items"]) == 1
        assert result["invalid_items"][0]["reason"] == "商品已inactive"
    
    def test_validate_cart_with_low_stock_item(self, db, test_user, test_product_low_stock):
        """测试包含库存不足商品的购物车"""
        # 先添加商品（数量1，库存足够）
        CartService.add_to_cart(
            db=db,
            product_id=test_product_low_stock.id,
            quantity=1,  # 库存1，刚好够
            user_id=test_user.id
        )
        
        # 然后减少库存使其不足
        ProductService.update_stock(db, test_product_low_stock.id, 0)
        
        result = CartService.validate_cart_for_checkout(db, user_id=test_user.id)
        
        assert result["valid"] is False
        assert len(result["invalid_items"]) == 1
        assert "库存不足" in result["invalid_items"][0]["reason"]
    
    def test_validate_empty_cart(self, db, test_user):
        """测试空购物车"""
        result = CartService.validate_cart_for_checkout(db, user_id=test_user.id)
        
        assert result["valid"] is False
        assert result["message"] == "购物车为空"
    
    def test_validate_cart_with_deleted_product(self, db, test_user, test_product_active):
        """测试包含已删除商品的购物车"""
        CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=2,
            user_id=test_user.id
        )
        
        # 软删除商品
        ProductService.delete_product(db, test_product_active.id, hard_delete=False)
        
        result = CartService.validate_cart_for_checkout(db, user_id=test_user.id)
        
        assert result["valid"] is False
        assert len(result["invalid_items"]) == 1
        assert "商品已deleted" in result["invalid_items"][0]["reason"]
    
    def test_validate_cart_with_mixed_invalid_items(self, db, test_user, test_product_active, test_product_inactive, test_product_low_stock):
        """测试包含多种无效商品的购物车"""
        # 添加上架商品（有效）
        CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=1,
            user_id=test_user.id
        )
        
        # 添加下架商品（无效）- 需要先创建上架商品，然后下架
        inactive_product = ProductService.create_product(
            db=db,
            name="临时下架商品2",
            price=99.99,
            stock=100
        )
        CartService.add_to_cart(
            db=db,
            product_id=inactive_product.id,
            quantity=1,
            user_id=test_user.id
        )
        ProductService.update_product_status(db, inactive_product.id, "inactive")
        
        # 添加库存不足商品（无效）- 先添加，再减少库存
        low_stock_product = ProductService.create_product(
            db=db,
            name="临时库存不足商品2",
            price=99.99,
            stock=100
        )
        CartService.add_to_cart(
            db=db,
            product_id=low_stock_product.id,
            quantity=5,
            user_id=test_user.id
        )
        # 减少库存使其不足
        ProductService.update_stock(db, low_stock_product.id, 1)
        
        result = CartService.validate_cart_for_checkout(db, user_id=test_user.id)
        
        assert result["valid"] is False
        assert len(result["invalid_items"]) == 2  # 2个无效商品


# ==================== 实时状态刷新测试 ====================

class TestRealTimeStatusRefresh:
    """实时状态刷新测试"""
    
    def test_cart_reflects_product_status_change(self, db, test_user, test_product_active):
        """测试购物车能反映商品状态变化"""
        # 添加商品到购物车
        CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=2,
            user_id=test_user.id
        )
        
        # 初始状态：商品可用
        cart_items = CartService.get_cart_with_products(db, user_id=test_user.id)
        assert cart_items[0]["is_available"] is True
        
        # 商品下架
        ProductService.update_product_status(db, test_product_active.id, "inactive")
        
        # 再次获取购物车：商品应该变为不可用
        cart_items = CartService.get_cart_with_products(db, user_id=test_user.id)
        assert cart_items[0]["is_available"] is False
        assert cart_items[0]["unavailable_reason"] == "商品已下架"
    
    def test_cart_reflects_stock_change(self, db, test_user, test_product_active):
        """测试购物车能反映库存变化"""
        # 添加商品到购物车（数量5）
        CartService.add_to_cart(
            db=db,
            product_id=test_product_active.id,
            quantity=5,
            user_id=test_user.id
        )
        
        # 初始状态：库存充足，商品可用
        cart_items = CartService.get_cart_with_products(db, user_id=test_user.id)
        assert cart_items[0]["is_available"] is True
        
        # 减少库存
        ProductService.update_stock(db, test_product_active.id, 3)
        
        # 再次获取购物车：库存不足，商品不可用
        cart_items = CartService.get_cart_with_products(db, user_id=test_user.id)
        assert cart_items[0]["is_available"] is False
        assert cart_items[0]["unavailable_reason"] == "库存不足"


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
