"""
订单服务
整合自 module-order
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import Order, OrderStatus, User
from models.schemas import (
    OrderCreate, OrderResponse, OrderListRequest, OrderListResponse, OrderItem
)
from config.logging_config import logger
from utils.transaction import transactional, TransactionContext
import uuid


class OrderService:
    """订单服务 - 单体模式"""
    
    @staticmethod
    def generate_order_no() -> str:
        """生成唯一订单号"""
        return f"ORD{uuid.uuid4().hex[:16].upper()}"
    
    @staticmethod
    @transactional
    def create_order(db: Session, user_id: int, order_data: OrderCreate, address_id: Optional[str] = None) -> Order:
        """
        创建订单（带事务管理）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            order_data: 订单数据
            address_id: 收货地址ID（可选）
        
        Returns:
            Order: 创建的订单
        
        Raises:
            ValueError: 订单商品为空
            SQLAlchemyError: 数据库操作失败
        """
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
        
        logger.info(f"订单创建成功: order_no={order_no}, user_id={user_id}, amount={total_amount}")
        return db_order
    
    @staticmethod
    @transactional
    def create_order_from_cart(
        db: Session,
        user_id: int,
        cart_items: List[Any],
        address_id: Optional[str] = None
    ) -> Order:
        """
        从购物车创建订单（带事务管理）
        
        这是一个原子操作，包含以下步骤：
        1. 验证购物车商品
        2. 检查商品状态和库存
        3. 创建订单
        4. 扣减库存
        5. 清空购物车
        
        如果任何步骤失败，整个事务会回滚，确保数据一致性。
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            cart_items: 购物车项列表
            address_id: 收货地址ID（可选）
        
        Returns:
            Order: 创建的订单
        
        Raises:
            ValueError: 购物车为空或商品无效
            SQLAlchemyError: 数据库操作失败
        """
        if not cart_items:
            raise ValueError("购物车为空")
        
        # 计算订单总金额
        total_amount = 0.0
        order_items_info = []
        
        # 第一步：验证所有商品（在事务内）
        for cart_item in cart_items:
            if not cart_item.product:
                raise ValueError(f"商品不存在: {cart_item.product_id}")
            
            if cart_item.product.status != "active":
                raise ValueError(f"商品已下架: {cart_item.product.name}")
            
            if cart_item.product.stock < cart_item.quantity:
                raise ValueError(f"库存不足: {cart_item.product.name}, "
                               f"需要={cart_item.quantity}, "
                               f"库存={cart_item.product.stock}")
            
            subtotal = cart_item.product.price * cart_item.quantity
            total_amount += subtotal
            
            order_items_info.append({
                "product_id": cart_item.product_id,
                "product_name": cart_item.product.name,
                "quantity": cart_item.quantity,
                "unit_price": cart_item.product.price,
                "spec_combo": cart_item.spec_combo,
                "cart_item": cart_item  # 保存引用用于后续删除
            })
        
        # 第二步：创建订单
        first_item = order_items_info[0]
        order_no = OrderService.generate_order_no()
        
        db_order = Order(
            order_no=order_no,
            user_id=user_id,
            product_id=first_item["product_id"],
            product_name=first_item["product_name"],
            quantity=first_item["quantity"],
            unit_price=first_item["unit_price"],
            total_amount=total_amount,
            status=OrderStatus.PENDING
        )
        
        db.add(db_order)
        db.flush()  # 刷新以获取订单ID，但不提交
        
        # 第三步：扣减库存（在同一事务内）
        from services.product_service import ProductService
        for item_info in order_items_info:
            product = db.query(item_info["cart_item"].product.__class__).filter(
                item_info["cart_item"].product.__class__.id == item_info["product_id"]
            ).with_for_update().first()  # 加锁防止并发问题
            
            if not product or product.stock < item_info["quantity"]:
                raise ValueError(f"库存不足或商品不存在: {item_info['product_name']}")
            
            product.stock -= item_info["quantity"]
            product.sales_count = (product.sales_count or 0) + item_info["quantity"]
            
            logger.info(f"库存扣减: product_id={item_info['product_id']}, "
                       f"扣减={item_info['quantity']}, 剩余={product.stock}")
        
        # 第四步：清空购物车（在同一事务内）
        for item_info in order_items_info:
            db.delete(item_info["cart_item"])
            logger.info(f"购物车项删除: cart_id={item_info['cart_item'].id}")
        
        logger.info(f"订单创建完成: order_no={order_no}, user_id={user_id}, "
                   f"total_amount={total_amount}, items={len(order_items_info)}")
        
        return db_order
    
    @staticmethod
    def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
        """根据 ID 查询订单（只读操作，无需事务）"""
        return db.query(Order).filter(Order.id == order_id).first()
    
    @staticmethod
    def get_order_by_no(db: Session, order_no: str) -> Optional[Order]:
        """根据订单号查询订单（只读操作，无需事务）"""
        return db.query(Order).filter(Order.order_no == order_no).first()
    
    @staticmethod
    def get_user_orders(
        db: Session,
        user_id: int,
        request: OrderListRequest
    ) -> OrderListResponse:
        """查询用户订单列表（只读操作，无需事务）"""
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
    @transactional
    def cancel_order(db: Session, order_id: int, user_id: int) -> Optional[Order]:
        """
        取消订单（带事务管理）
        
        Args:
            db: 数据库会话
            order_id: 订单ID
            user_id: 用户ID
        
        Returns:
            Order: 取消后的订单
        
        Raises:
            ValueError: 订单状态不允许取消
        """
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id
        ).with_for_update().first()  # 加锁防止并发修改
        
        if not order:
            raise PermissionError("订单不存在或无权访问")
        
        # 只有待支付订单可以取消
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"订单状态为 {order.status}，无法取消")
        
        order.status = OrderStatus.CANCELLED
        logger.info(f"订单取消成功: order_id={order_id}, user_id={user_id}")
        return order
    
    @staticmethod
    @transactional
    def update_order_status(db: Session, order_id: int, status: OrderStatus) -> Optional[Order]:
        """
        更新订单状态（带事务管理，内部使用，如支付回调）
        
        Args:
            db: 数据库会话
            order_id: 订单ID
            status: 新状态
        
        Returns:
            Order: 更新后的订单
        """
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order:
            return None
        
        old_status = order.status
        order.status = status
        
        logger.info(f"订单状态更新: order_id={order_id}, "
                   f"{old_status} -> {status}")
        return order
    
    @staticmethod
    @transactional
    def refund_order(db: Session, order_id: int, user_id: int) -> Optional[Order]:
        """
        订单退款（带事务管理）
        
        Args:
            db: 数据库会话
            order_id: 订单ID
            user_id: 用户ID
        
        Returns:
            Order: 退款后的订单
        
        Raises:
            ValueError: 订单状态不允许退款
        """
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id
        ).with_for_update().first()
        
        if not order:
            raise PermissionError("订单不存在或无权访问")
        
        # 只有已支付订单可以退款
        if order.status != OrderStatus.PAID:
            raise ValueError(f"订单状态为 {order.status}，无法退款")
        
        order.status = OrderStatus.CANCELLED
        
        # TODO: 恢复库存
        # TODO: 创建退款记录
        
        logger.info(f"订单退款成功: order_id={order_id}, user_id={user_id}")
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
