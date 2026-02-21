"""
Pydantic Schemas - 统一数据验证
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ==================== 基础响应 ====================
class ResponseBase(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None


# ==================== 用户模块 Schemas ====================
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ==================== 订单模块 Schemas ====================
from models import OrderStatus


class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)


class OrderCreate(BaseModel):
    items: List[OrderItem]


class OrderResponse(BaseModel):
    id: int
    order_no: str
    user_id: int
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_amount: float
    status: OrderStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderListRequest(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    status: Optional[OrderStatus] = None


class OrderListResponse(BaseModel):
    total: int
    items: List[OrderResponse]
    page: int
    page_size: int


class OrderCancelRequest(BaseModel):
    order_id: str
    reason: Optional[str] = None


# ==================== 支付模块 Schemas ====================
from models import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    order_id: int
    method: PaymentMethod


class PaymentResponse(BaseModel):
    id: int
    payment_no: str
    order_id: int
    amount: float
    method: PaymentMethod
    status: PaymentStatus
    third_party_trade_no: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlipayCallback(BaseModel):
    out_trade_no: str
    trade_no: str
    trade_status: str
    buyer_id: str
    total_amount: float


class WechatCallback(BaseModel):
    out_trade_no: str
    transaction_id: str
    result_code: str
    openid: str
    total_fee: int
