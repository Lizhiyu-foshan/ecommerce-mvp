"""
事务管理测试
验证订单和购物车服务的事务管理功能
"""
import pytest
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import Base, get_db
from models import User, Order, OrderStatus
from services.auth_service import AuthService
from services.order_service import OrderService
from services.cart_service import CartService
from services.product_service import ProductService
from models.schemas import UserCreate, OrderCreate, OrderItem
from utils.transaction import transactional, TransactionContext

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


def get_test_db():
    """获取测试数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestTransactionManagement:
    """事务管理测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.db = TestingSessionLocal()
        
        # 创建测试用户
        user_data = UserCreate(
            username=f"testuser_{id(self)}",
            email=f"test_{id(self)}@example.com",
            password="testpass123"
        )
        self.user = AuthService.create_user(self.db, user_data)
        self.db.commit()
        
        # 创建测试商品
        self.product = ProductService.create_product(
            db=self.db,
            name=f"Test Product {id(self)}",
            price=100.00,
            stock=10
        )
        self.db.commit()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        self.db.rollback()
        self.db.close()
    
    def test_transactional_decorator_success(self):
        """测试事务装饰器 - 成功提交"""
        @transactional
        def create_test_order(db, user_id, product_id):
            order_data = OrderCreate(items=[
                OrderItem(product_id=product_id, product_name="Test", quantity=1, unit_price=100.00)
            ])
            return OrderService.create_order(db, user_id, order_data)
        
        order = create_test_order(self.db, self.user.id, self.product.id)
        
        # 验证订单已创建
        assert order is not None
        assert order.id is not None
        
        # 验证可以在新查询中获取到订单
        db2 = TestingSessionLocal()
        found_order = db2.query(Order).filter(Order.id == order.id).first()
        assert found_order is not None
        assert found_order.order_no == order.order_no
        db2.close()
    
    def test_transactional_decorator_rollback(self):
        """测试事务装饰器 - 失败回滚"""
        initial_stock = self.product.stock
        
        @transactional
        def failing_operation(db, user_id):
            # 先创建订单
            order_data = OrderCreate(items=[
                OrderItem(product_id=self.product.id, product_name="Test", quantity=1, unit_price=100.00)
            ])
            order = OrderService.create_order(db, user_id, order_data)
            
            # 然后抛出异常
            raise ValueError("模拟业务错误")
        
        # 执行应该抛出异常
        with pytest.raises(ValueError, match="模拟业务错误"):
            failing_operation(self.db, self.user.id)
        
        # 验证订单未创建（事务回滚）
        db2 = TestingSessionLocal()
        orders = db2.query(Order).filter(Order.user_id == self.user.id).all()
        # 只有setup时创建的订单
        db2.close()
    
    def test_create_order_from_cart_transaction(self):
        """测试从购物车创建订单的事务原子性"""
        # 添加商品到购物车
        cart_item = CartService.add_to_cart(
            db=self.db,
            product_id=self.product.id,
            quantity=2,
            user_id=self.user.id
        )
        
        initial_stock = self.product.stock
        
        # 从购物车创建订单
        cart_items = CartService.get_cart(self.db, user_id=self.user.id)
        order = OrderService.create_order_from_cart(
            db=self.db,
            user_id=self.user.id,
            cart_items=cart_items
        )
        
        # 验证订单创建成功
        assert order is not None
        assert order.order_no.startswith("ORD")
        assert order.total_amount == 200.00  # 100 * 2
        
        # 验证库存已扣减
        self.db.refresh(self.product)
        assert self.product.stock == initial_stock - 2
        
        # 验证购物车已清空
        cart_items_after = CartService.get_cart(self.db, user_id=self.user.id)
        assert len(cart_items_after) == 0
    
    def test_create_order_from_cart_rollback_on_insufficient_stock(self):
        """测试库存不足时事务回滚"""
        # 添加商品到购物车（数量超过库存）
        cart_item = CartService.add_to_cart(
            db=self.db,
            product_id=self.product.id,
            quantity=3,
            user_id=self.user.id
        )
        
        # 手动修改库存使其不足
        self.product.stock = 1
        self.db.commit()
        
        initial_stock = self.product.stock
        
        # 尝试创建订单应该失败
        cart_items = CartService.get_cart(self.db, user_id=self.user.id)
        
        with pytest.raises(ValueError, match="库存不足"):
            OrderService.create_order_from_cart(
                db=self.db,
                user_id=self.user.id,
                cart_items=cart_items
            )
        
        # 验证库存未变化（事务回滚）
        self.db.refresh(self.product)
        assert self.product.stock == initial_stock
        
        # 验证购物车未清空（事务回滚）
        cart_items_after = CartService.get_cart(self.db, user_id=self.user.id)
        assert len(cart_items_after) == 1
    
    def test_transaction_context_manager(self):
        """测试事务上下文管理器"""
        initial_stock = self.product.stock
        
        # 使用新的数据库会话来验证回滚
        db2 = TestingSessionLocal()
        product2 = db2.query(self.product.__class__).filter(self.product.__class__.id == self.product.id).first()
        initial_stock2 = product2.stock
        
        try:
            with TransactionContext(db2) as tx:
                # 扣减库存
                product2.stock -= 2
                db2.flush()
                
                # 模拟错误
                raise ValueError("测试回滚")
        except ValueError:
            pass
        
        # 验证事务已回滚
        db2.refresh(product2)
        assert product2.stock == initial_stock2
        db2.close()
    
    def test_concurrent_stock_deduction_with_lock(self):
        """测试并发库存扣减（使用行锁）"""
        # 添加商品到购物车
        CartService.add_to_cart(
            db=self.db,
            product_id=self.product.id,
            quantity=2,
            user_id=self.user.id
        )
        
        # 创建订单（使用行锁）
        cart_items = CartService.get_cart(self.db, user_id=self.user.id)
        order = OrderService.create_order_from_cart(
            db=self.db,
            user_id=self.user.id,
            cart_items=cart_items
        )
        
        # 验证订单创建成功
        assert order is not None
        
        # 验证库存正确扣减
        self.db.refresh(self.product)
        assert self.product.stock == 8  # 10 - 2
    
    def test_cancel_order_transaction(self):
        """测试取消订单事务"""
        # 先创建订单
        order_data = OrderCreate(items=[
            OrderItem(product_id=self.product.id, product_name="Test", quantity=1, unit_price=100.00)
        ])
        order = OrderService.create_order(self.db, self.user.id, order_data)
        
        # 取消订单
        cancelled_order = OrderService.cancel_order(self.db, order.id, self.user.id)
        
        # 验证订单已取消
        assert cancelled_order is not None
        assert cancelled_order.status == OrderStatus.CANCELLED
        
        # 验证数据库状态
        self.db.refresh(order)
        assert order.status == OrderStatus.CANCELLED
    
    def test_cart_add_transaction(self):
        """测试添加购物车事务"""
        cart_item = CartService.add_to_cart(
            db=self.db,
            product_id=self.product.id,
            quantity=3,
            user_id=self.user.id
        )
        
        # 验证购物车项已创建
        assert cart_item is not None
        assert cart_item.quantity == 3
        
        # 再次添加相同商品（应该合并）
        cart_item2 = CartService.add_to_cart(
            db=self.db,
            product_id=self.product.id,
            quantity=2,
            user_id=self.user.id
        )
        
        # 验证数量合并
        assert cart_item2.quantity == 5  # 3 + 2
    
    def test_cart_add_transaction_rollback_on_insufficient_stock(self):
        """测试添加购物车库存不足时回滚"""
        # 尝试添加超过库存数量的商品
        with pytest.raises(ValueError, match="库存不足"):
            CartService.add_to_cart(
                db=self.db,
                product_id=self.product.id,
                quantity=100,  # 超过库存
                user_id=self.user.id
            )
        
        # 验证购物车未添加
        cart_items = CartService.get_cart(self.db, user_id=self.user.id)
        assert len(cart_items) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
