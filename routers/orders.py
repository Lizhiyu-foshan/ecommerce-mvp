"""
订单路由
整合自 module-order
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from services.order_service import OrderService
from models import OrderStatus
from models.schemas import (
    OrderCreate, OrderResponse, OrderListRequest, OrderListResponse,
    OrderCancelRequest, ResponseBase, UserResponse
)
from routers.auth import get_current_user

router = APIRouter(prefix="/orders", tags=["订单"])


@router.post("/create", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建订单"""
    order = OrderService.create_order(db, user_id=current_user.id, order_data=order_data)
    return order


@router.get("/list", response_model=OrderListResponse)
def get_order_list(
    page: int = 1,
    page_size: int = 10,
    status: Optional[OrderStatus] = None,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询订单列表"""
    request = OrderListRequest(page=page, page_size=page_size, status=status)
    return OrderService.get_user_orders(db, user_id=current_user.id, request=request)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_detail(
    order_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询订单详情"""
    order = OrderService.get_order_by_id(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.post("/cancel", response_model=OrderResponse)
def cancel_order(
    cancel_data: OrderCancelRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消订单"""
    try:
        order = OrderService.cancel_order(db, int(cancel_data.order_id), user_id=current_user.id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
