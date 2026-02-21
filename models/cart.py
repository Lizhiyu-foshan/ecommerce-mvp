"""
购物车数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


class Cart(Base):
    """购物车表"""
    __tablename__ = "carts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100), nullable=True)  # 匿名用户会话ID
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    spec_combo = Column(JSON, default=dict)  # {"颜色": "红色", "尺寸": "XL"}
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", backref="cart_items")
    product = relationship("Product", back_populates="cart_items")
    
    def __repr__(self):
        return f"<Cart(id={self.id}, user_id={self.user_id}, product_id={self.product_id}, quantity={self.quantity})>"
    
    @property
    def subtotal(self) -> float:
        """计算小计金额"""
        if self.product:
            return self.product.price * self.quantity
        return 0.0
