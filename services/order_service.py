"""
订单服务
整合自 module-order
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Order, OrderStatus, User
from models.schemas import (
    OrderCreate, OrderResponse, OrderListRequest, OrderListResponse, OrderItem
)
import uuid


class OrderService:
    """订单服务 - 单体模式"""
    
    @staticmethod
    def generate_order_no() -> str:
        """生成唯一订单号"""
        return f"ORD{uuid.uuid4().hex[:16].upper()}"
    
    @staticmethod
    def create_order(db: Session, user_id: int, order_data: OrderCreate) -> Order:
        """创建订单"""
        # 简化版：只处理单个商品（实际应处理购物车）
        item = order_data.items[0] if order_data.items else None
        if not item:
            raise ValueError("订单商品不能为空")
        
        order_no = OrderService.generate_order_no()
        total_amount = item.unit_price * item.quantity
        
        db_order = Order(
            order_no=order_no,
            user_id=user_id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_amount=total_amount,
            status=OrderStatus.PENDING
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        return db_order
    
    @staticmethod
    def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
        """根据 ID 查询订单"""
        return db.query(Order).filter(Order.id == order_id).first()
    
    @staticmethod
    def get_order_by_no(db: Session, order_no: str) -> Optional[Order]:
        """根据订单号查询订单"""
        return db.query(Order).filter(Order.order_no == order_no).first()
    
    @staticmethod
    def get_user_orders(
        db: Session,
        user_id: int,
        request: OrderListRequest
    ) -> OrderListResponse:
        """查询用户订单列表"""
        query = db.query(Order).filter(Order.user_id == user_id)
        
        # 状态筛选
        if request.status:
            query = query.filter(Order.status == request.status)
        
        # 分页
        total = query.count()
        orders = query.offset((request.page - 1) * request.page_size).limit(request.page_size).all()
        
        return OrderListResponse(
            total=total,
            items=[OrderResponse.from_orm(o) for o in orders],
            page=request.page,
            page_size=request.page_size
        )
    
    @staticmethod
    def cancel_order(db: Session, order_id: int, user_id: int) -> Optional[Order]:
        """取消订单"""
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id
        ).first()
        
        if not order:
            return None
        
        # 只有待支付订单可以取消
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"订单状态为 {order.status}，无法取消")
        
        order.status = OrderStatus.CANCELLED
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def update_order_status(db: Session, order_id: int, status: OrderStatus) -> Optional[Order]:
        """更新订单状态（内部使用，如支付回调）"""
        order = OrderService.get_order_by_id(db, order_id)
        if not order:
            return None
        
        order.status = status
        db.commit()
        db.refresh(order)
        return order


# 微服务预留：HTTP 客户端调用方式
# class OrderServiceClient:
#     """订单服务 - 微服务模式（HTTP 调用）"""
#     BASE_URL = settings.ORDER_SERVICE_URL
#     
#     @staticmethod
#     async def create_order(token: str, order_data: OrderCreate) -> dict:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{OrderServiceClient.BASE_URL}/orders",
#                 json=order_data.dict(),
#                 headers={"Authorization": f"Bearer {token}"}
#             )
#             return response.json()
