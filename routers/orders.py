"""
订单路由
整合自 module-order
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from services.order_service import OrderService
from services.auth_service import AuthService
from models import OrderStatus
from models.schemas import (
    OrderCreate, OrderResponse, OrderListRequest, OrderListResponse,
    OrderCancelRequest, ResponseBase
)

router = APIRouter(prefix="/orders", tags=["订单"])


def get_current_user(token: str, db: Session):
    """获取当前用户（内部使用）"""
    from routers.auth import oauth2_scheme, get_current_user
    return get_current_user(token, db)


@router.post("/create", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    current_user = Depends(lambda db=Depends(get_db): AuthService.get_user_by_id(db, 1)),  # 简化版，实际应使用 token
    db: Session = Depends(get_db)
):
    """创建订单"""
    # TODO: 从 token 获取 user_id
    # 简化版：使用 user_id=1
    order = OrderService.create_order(db, user_id=1, order_data=order_data)
    return order


@router.get("/list", response_model=OrderListResponse)
def get_order_list(
    page: int = 1,
    page_size: int = 10,
    status: Optional[OrderStatus] = None,
    current_user = Depends(lambda db=Depends(get_db): AuthService.get_user_by_id(db, 1)),
    db: Session = Depends(get_db)
):
    """查询订单列表"""
    request = OrderListRequest(page=page, page_size=page_size, status=status)
    return OrderService.get_user_orders(db, user_id=1, request=request)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_detail(order_id: int, db: Session = Depends(get_db)):
    """查询订单详情"""
    order = OrderService.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.post("/cancel", response_model=OrderResponse)
def cancel_order(
    cancel_data: OrderCancelRequest,
    current_user = Depends(lambda db=Depends(get_db): AuthService.get_user_by_id(db, 1)),
    db: Session = Depends(get_db)
):
    """取消订单"""
    try:
        order = OrderService.cancel_order(db, int(cancel_data.order_id), user_id=1)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
