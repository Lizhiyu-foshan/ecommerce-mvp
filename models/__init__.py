"""
统一数据模型
包含：用户、订单、支付、商品、购物车、地址六个模块的模型
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

# 导入新模型
from models.product import Category, Product, ProductSpec
from models.cart import Cart
from models.address import Address


# ==================== 用户模块 ====================
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Integer, default=1)  # 1=active, 0=inactive
    is_admin = Column(Integer, default=0)  # 1=admin, 0=normal user  # ✅ 添加管理员字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    orders = relationship("Order", back_populates="user")


# ==================== 订单模块 ====================
class OrderStatus(str, enum.Enum):
    PENDING = "pending"      # 待支付
    PAID = "paid"           # 已支付
    PROCESSING = "processing"  # 处理中
    SHIPPED = "shipped"     # 已发货
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_no = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(String(100), nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="orders")
    payment = relationship("Payment", back_populates="order", uselist=False)


# ==================== 支付模块 ====================
class PaymentStatus(str, enum.Enum):
    PENDING = "pending"      # 待支付
    PROCESSING = "processing"  # 处理中
    SUCCESS = "success"      # 支付成功
    FAILED = "failed"        # 支付失败
    REFUNDED = "refunded"    # 已退款


class PaymentMethod(str, enum.Enum):
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CREDIT_CARD = "credit_card"


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    payment_no = Column(String(50), unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # 第三方支付信息
    third_party_trade_no = Column(String(100), nullable=True)  # 支付宝/微信订单号
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # 回调信息
    callback_data = Column(Text, nullable=True)  # JSON 存储回调数据
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    order = relationship("Order", back_populates="payment")
