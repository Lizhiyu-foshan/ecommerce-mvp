"""
用户地址数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


class Address(Base):
    """收货地址表"""
    __tablename__ = "addresses"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)  # 收件人姓名
    phone = Column(String(20), nullable=False)
    province = Column(String(50), nullable=False)
    city = Column(String(50), nullable=False)
    district = Column(String(50), nullable=False)
    detail = Column(String(200), nullable=False)  # 详细地址
    zip_code = Column(String(10), nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", backref="addresses")
    
    def __repr__(self):
        return f"<Address(id={self.id}, user_id={self.user_id}, name={self.name})>"
    
    @property
    def full_address(self) -> str:
        """获取完整地址字符串"""
        return f"{self.province}{self.city}{self.district}{self.detail}"
    
    @property
    def masked_phone(self) -> str:
        """获取脱敏手机号"""
        if len(self.phone) == 11:
            return f"{self.phone[:3]}****{self.phone[7:]}"
        return self.phone
