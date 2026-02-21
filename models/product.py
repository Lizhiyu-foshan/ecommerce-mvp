"""
商品数据模型
包含：分类、商品、商品规格
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


class Category(Base):
    """商品分类表"""
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    parent_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    products = relationship("Product", back_populates="category")
    parent = relationship("Category", remote_side=[id], backref="children")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class Product(Base):
    """商品表"""
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    stock = Column(Integer, default=0, nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    images = Column(JSON, default=list)  # [{"url": "...", "sort": 1}]
    status = Column(String(20), default="active")  # active, inactive, deleted
    sort_order = Column(Integer, default=0)
    sales_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    category = relationship("Category", back_populates="products")
    specs = relationship("ProductSpec", back_populates="product", cascade="all, delete-orphan")
    cart_items = relationship("Cart", back_populates="product")
    
    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, price={self.price})>"
    
    @property
    def is_available(self) -> bool:
        """检查商品是否可售"""
        return self.status == "active" and self.stock > 0


class ProductSpec(Base):
    """商品规格表"""
    __tablename__ = "product_specs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    name = Column(String(50), nullable=False)  # 颜色、尺寸等
    values = Column(JSON, nullable=False)  # ["红色", "蓝色", "黑色"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    product = relationship("Product", back_populates="specs")
    
    def __repr__(self):
        return f"<ProductSpec(id={self.id}, name={self.name})>"
