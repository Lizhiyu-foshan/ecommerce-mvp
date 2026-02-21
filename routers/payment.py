"""
支付路由
整合自 module-payment
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from database import get_db
from services.payment_service import PaymentService
from models import PaymentMethod
from models.schemas import (
    PaymentCreate, PaymentResponse, AlipayCallback, WechatCallback, ResponseBase
)

router = APIRouter(prefix="/payment", tags=["支付"])


@router.post("/create", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(payment_data: PaymentCreate, db: Session = Depends(get_db)):
    """创建支付订单"""
    try:
        payment = PaymentService.create_payment(db, payment_data)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/alipay", response_model=PaymentResponse)
def alipay_payment(order_id: int, db: Session = Depends(get_db)):
    """创建支付宝支付"""
    try:
        payment = PaymentService.create_alipay_payment(db, order_id)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wechat", response_model=PaymentResponse)
def wechat_payment(order_id: int, db: Session = Depends(get_db)):
    """创建微信支付"""
    try:
        payment = PaymentService.create_wechat_payment(db, order_id)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{order_id}")
def get_payment_status(order_id: int, db: Session = Depends(get_db)):
    """查询支付状态"""
    status = PaymentService.get_payment_status(db, order_id)
    if not status:
        raise HTTPException(status_code=404, detail="支付记录不存在")
    return status


# ==================== 回调接口 ====================

@router.post("/callback/alipay")
def alipay_callback(callback_data: AlipayCallback, db: Session = Depends(get_db)):
    """支付宝异步回调"""
    success = PaymentService.handle_alipay_callback(db, callback_data)
    if success:
        return {"code": "SUCCESS", "message": "处理成功"}
    return {"code": "FAIL", "message": "处理失败"}


@router.post("/callback/wechat")
def wechat_callback(callback_data: WechatCallback, db: Session = Depends(get_db)):
    """微信异步回调"""
    success = PaymentService.handle_wechat_callback(db, callback_data)
    if success:
        return {"code": "SUCCESS", "message": "处理成功"}
    return {"code": "FAIL", "message": "处理失败"}


# ==================== 测试接口 ====================

@router.get("/callback/test/alipay/{out_trade_no}")
def test_alipay_callback(out_trade_no: str, db: Session = Depends(get_db)):
    """模拟支付宝回调（测试用）"""
    from models import Order
    order = db.query(Order).filter(Order.order_no == out_trade_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 模拟回调数据
    callback_data = AlipayCallback(
        out_trade_no=out_trade_no,
        trade_no=f"ALIPAY{out_trade_no}",
        trade_status="TRADE_SUCCESS",
        buyer_id="test_buyer_001",
        total_amount=float(order.total_amount)
    )
    
    success = PaymentService.handle_alipay_callback(db, callback_data)
    return {"success": success, "message": "模拟支付宝回调完成"}


@router.get("/callback/test/wechat/{out_trade_no}")
def test_wechat_callback(out_trade_no: str, db: Session = Depends(get_db)):
    """模拟微信回调（测试用）"""
    from models import Order
    order = db.query(Order).filter(Order.order_no == out_trade_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 模拟回调数据（微信单位为分）
    callback_data = WechatCallback(
        out_trade_no=out_trade_no,
        transaction_id=f"WECHAT{out_trade_no}",
        result_code="SUCCESS",
        openid="test_openid_001",
        total_fee=int(order.total_amount * 100)
    )
    
    success = PaymentService.handle_wechat_callback(db, callback_data)
    return {"success": success, "message": "模拟微信回调完成"}
