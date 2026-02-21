"""
支付服务
整合自 module-payment
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Payment, PaymentStatus, PaymentMethod, Order, OrderStatus
from models.schemas import PaymentCreate, PaymentResponse, AlipayCallback, WechatCallback
from services.order_service import OrderService
import uuid
import json


class PaymentService:
    """支付服务 - 单体模式"""
    
    @staticmethod
    def generate_payment_no() -> str:
        """生成唯一支付单号"""
        return f"PAY{uuid.uuid4().hex[:16].upper()}"
    
    @staticmethod
    def create_payment(db: Session, payment_data: PaymentCreate) -> Payment:
        """创建支付订单"""
        # 检查订单是否存在
        order = OrderService.get_order_by_id(db, payment_data.order_id)
        if not order:
            raise ValueError("订单不存在")
        
        if order.status.value != "pending":
            raise ValueError(f"订单状态为 {order.status}，无法创建支付")
        
        # 检查是否已有支付记录
        existing = db.query(Payment).filter(Payment.order_id == payment_data.order_id).first()
        if existing:
            return existing
        
        payment_no = PaymentService.generate_payment_no()
        
        db_payment = Payment(
            payment_no=payment_no,
            order_id=payment_data.order_id,
            amount=order.total_amount,
            method=payment_data.method,
            status=PaymentStatus.PENDING
        )
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        return db_payment
    
    @staticmethod
    def get_payment_by_id(db: Session, payment_id: int) -> Optional[Payment]:
        """根据 ID 查询支付"""
        return db.query(Payment).filter(Payment.id == payment_id).first()
    
    @staticmethod
    def get_payment_by_no(db: Session, payment_no: str) -> Optional[Payment]:
        """根据支付单号查询"""
        return db.query(Payment).filter(Payment.payment_no == payment_no).first()
    
    @staticmethod
    def get_payment_status(db: Session, order_id: int) -> Optional[Dict[str, Any]]:
        """查询订单支付状态"""
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            return None
        
        return {
            "payment_no": payment.payment_no,
            "status": payment.status.value,
            "method": payment.method.value,
            "amount": payment.amount,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
        }
    
    # ==================== 支付宝支付 ====================
    
    @staticmethod
    def create_alipay_payment(db: Session, order_id: int) -> Payment:
        """创建支付宝支付"""
        return PaymentService.create_payment(
            db,
            PaymentCreate(order_id=order_id, method=PaymentMethod.ALIPAY)
        )
    
    @staticmethod
    def handle_alipay_callback(db: Session, callback_data: AlipayCallback) -> bool:
        """处理支付宝回调"""
        # 查找支付记录
        payment = db.query(Payment).join(Order).filter(
            Order.order_no == callback_data.out_trade_no
        ).first()
        
        if not payment:
            return False
        
        # 验证金额
        if float(callback_data.total_amount) != payment.amount:
            return False
        
        # 更新支付状态
        if callback_data.trade_status in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
            payment.status = PaymentStatus.SUCCESS
            payment.third_party_trade_no = callback_data.trade_no
            payment.callback_data = json.dumps(callback_data.dict())
            
            # 更新订单状态
            OrderService.update_order_status(db, payment.order_id, OrderStatus.PAID)
        
        db.commit()
        return True
    
    # ==================== 微信支付 ====================
    
    @staticmethod
    def create_wechat_payment(db: Session, order_id: int) -> Payment:
        """创建微信支付"""
        return PaymentService.create_payment(
            db,
            PaymentCreate(order_id=order_id, method=PaymentMethod.WECHAT)
        )
    
    @staticmethod
    def handle_wechat_callback(db: Session, callback_data: WechatCallback) -> bool:
        """处理微信回调"""
        # 查找支付记录
        payment = db.query(Payment).join(Order).filter(
            Order.order_no == callback_data.out_trade_no
        ).first()
        
        if not payment:
            return False
        
        # 验证金额（微信单位为分）
        wechat_amount = callback_data.total_fee / 100
        if wechat_amount != payment.amount:
            return False
        
        # 更新支付状态
        if callback_data.result_code == "SUCCESS":
            payment.status = PaymentStatus.SUCCESS
            payment.third_party_trade_no = callback_data.transaction_id
            payment.callback_data = json.dumps(callback_data.dict())
            
            # 更新订单状态
            OrderService.update_order_status(db, payment.order_id, OrderStatus.PAID)
        
        db.commit()
        return True


# 微服务预留：HTTP 客户端调用方式
# class PaymentServiceClient:
#     """支付服务 - 微服务模式（HTTP 调用）"""
#     BASE_URL = settings.PAYMENT_SERVICE_URL
