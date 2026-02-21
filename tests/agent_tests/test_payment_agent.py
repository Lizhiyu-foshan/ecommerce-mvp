"""
电商支付模块单元测试
使用 pytest 框架和 SQLite 内存数据库
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# 导入支付模块
from payment import (
    Base, Order, Payment, PaymentStatus, PaymentChannel,
    PaymentService, PaymentError, OrderNotFoundError,
    PaymentAlreadyExistsError, PaymentNotFoundError,
    AmountMismatchError, DuplicateCallbackError
)


# ==================== Fixtures ====================

@pytest.fixture
def engine():
    """
    创建 SQLite 内存数据库引擎
    
    Returns:
        Engine: SQLAlchemy 数据库引擎
    """
    return create_engine('sqlite:///:memory:', echo=False)


@pytest.fixture
def session(engine):
    """
    创建数据库会话
    
    Args:
        engine: 数据库引擎
        
    Returns:
        Session: SQLAlchemy 会话
    """
    # 创建所有表
    Base.metadata.create_all(engine)
    
    # 创建会话
    Session = sessionmaker(bind=engine)
    db_session = Session()
    
    yield db_session
    
    # 清理
    db_session.close()


@pytest.fixture
def payment_service(session):
    """
    创建支付服务实例
    
    Args:
        session: 数据库会话
        
    Returns:
        PaymentService: 支付服务实例
    """
    return PaymentService(session)


@pytest.fixture
def sample_order(session):
    """
    创建示例订单
    
    Args:
        session: 数据库会话
        
    Returns:
        Order: 示例订单
    """
    order = Order(
        id="ORD202402210001",
        user_id="USER001",
        amount=99.99,
        status="pending"
    )
    session.add(order)
    session.commit()
    return order


@pytest.fixture
def sample_payment(session, sample_order):
    """
    创建示例支付记录
    
    Args:
        session: 数据库会话
        sample_order: 示例订单
        
    Returns:
        Payment: 示例支付记录
    """
    payment = Payment(
        id="PAY202402210001",
        order_id=sample_order.id,
        user_id="USER001",
        amount=99.99,
        channel=PaymentChannel.ALIPAY.value,
        status=PaymentStatus.PENDING.value
    )
    session.add(payment)
    session.commit()
    return payment


# ==================== 支付创建功能测试 ====================

class TestCreatePayment:
    """
    测试支付创建功能
    
    包括:
    1. 正常创建支付
    2. 订单不存在时创建支付
    3. 重复创建支付
    4. 金额不匹配时创建支付
    """
    
    def test_create_payment_success(self, payment_service, sample_order, session):
        """
        测试正常创建支付记录
        
        场景: 订单存在且没有现有支付记录
        预期: 成功创建支付记录，状态为待支付
        """
        # 执行创建支付
        payment = payment_service.create_payment(
            order_id=sample_order.id,
            user_id=sample_order.user_id,
            amount=sample_order.amount,
            channel=PaymentChannel.ALIPAY
        )
        
        # 验证支付记录
        assert payment is not None
        assert payment.order_id == sample_order.id
        assert payment.user_id == sample_order.user_id
        assert payment.amount == sample_order.amount
        assert payment.channel == PaymentChannel.ALIPAY.value
        assert payment.status == PaymentStatus.PENDING.value
        assert payment.id is not None
        assert payment.id.startswith("PAY")
        
        # 验证数据库中存在记录
        db_payment = session.query(Payment).filter(Payment.id == payment.id).first()
        assert db_payment is not None
        assert db_payment.status == PaymentStatus.PENDING.value
    
    def test_create_payment_order_not_found(self, payment_service):
        """
        测试订单不存在时创建支付
        
        场景: 使用不存在的订单ID创建支付
        预期: 抛出 OrderNotFoundError 异常
        """
        # 使用不存在的订单ID
        non_existent_order_id = "ORD999999999"
        
        # 预期抛出异常
        with pytest.raises(OrderNotFoundError) as exc_info:
            payment_service.create_payment(
                order_id=non_existent_order_id,
                user_id="USER001",
                amount=99.99,
                channel=PaymentChannel.ALIPAY
            )
        
        # 验证异常信息
        assert "订单不存在" in str(exc_info.value)
        assert non_existent_order_id in str(exc_info.value)
    
    def test_create_payment_duplicate(self, payment_service, sample_order, sample_payment):
        """
        测试重复创建支付
        
        场景: 订单已存在支付记录时再次创建
        预期: 抛出 PaymentAlreadyExistsError 异常
        """
        # 尝试为已有支付记录的订单创建支付
        with pytest.raises(PaymentAlreadyExistsError) as exc_info:
            payment_service.create_payment(
                order_id=sample_order.id,
                user_id=sample_order.user_id,
                amount=sample_order.amount,
                channel=PaymentChannel.WECHAT
            )
        
        # 验证异常信息
        assert "已存在支付记录" in str(exc_info.value)
        assert sample_order.id in str(exc_info.value)
    
    def test_create_payment_amount_mismatch(self, payment_service, sample_order):
        """
        测试金额不匹配时创建支付
        
        场景: 支付金额与订单金额不一致
        预期: 抛出 AmountMismatchError 异常
        """
        # 使用错误的金额
        wrong_amount = sample_order.amount + 10.0
        
        # 预期抛出异常
        with pytest.raises(AmountMismatchError) as exc_info:
            payment_service.create_payment(
                order_id=sample_order.id,
                user_id=sample_order.user_id,
                amount=wrong_amount,
                channel=PaymentChannel.ALIPAY
            )
        
        # 验证异常信息
        assert "金额不匹配" in str(exc_info.value)
    
    def test_create_payment_different_channels(self, payment_service, session):
        """
        测试不同支付渠道创建支付
        
        场景: 使用支付宝和微信支付分别创建
        预期: 都能成功创建，渠道信息正确
        """
        # 创建两个订单
        order_alipay = Order(
            id="ORD_ALIPAY_001",
            user_id="USER001",
            amount=50.00,
            status="pending"
        )
        order_wechat = Order(
            id="ORD_WECHAT_001",
            user_id="USER001",
            amount=100.00,
            status="pending"
        )
        session.add_all([order_alipay, order_wechat])
        session.commit()
        
        # 创建支付宝支付
        payment_alipay = payment_service.create_payment(
            order_id=order_alipay.id,
            user_id=order_alipay.user_id,
            amount=order_alipay.amount,
            channel=PaymentChannel.ALIPAY
        )
        
        # 创建微信支付
        payment_wechat = payment_service.create_payment(
            order_id=order_wechat.id,
            user_id=order_wechat.user_id,
            amount=order_wechat.amount,
            channel=PaymentChannel.WECHAT
        )
        
        # 验证渠道信息
        assert payment_alipay.channel == PaymentChannel.ALIPAY.value
        assert payment_wechat.channel == PaymentChannel.WECHAT.value


# ==================== 支付宝回调功能测试 ====================

class TestAlipayCallback:
    """
    测试支付宝回调功能
    
    包括:
    1. 支付宝回调成功
    2. 金额不匹配
    3. 支付记录不存在
    4. 重复回调
    5. 交易状态非成功
    """
    
    def test_alipay_callback_success(self, payment_service, sample_payment, session):
        """
        测试支付宝回调成功场景
        
        场景: 支付宝返回 TRADE_SUCCESS 状态，金额匹配
        预期: 支付状态更新为成功，订单状态更新为已支付
        """
        # 准备回调数据
        callback_data = {
            "out_trade_no": sample_payment.id,
            "trade_no": "2024022122001156789012345678",
            "total_amount": str(sample_payment.amount),
            "trade_status": "TRADE_SUCCESS"
        }
        
        # 处理回调
        payment = payment_service.process_alipay_callback(callback_data)
        
        # 验证支付记录更新
        assert payment.status == PaymentStatus.SUCCESS.value
        assert payment.third_party_id == callback_data["trade_no"]
        assert payment.callback_data == str(callback_data)
        assert payment.callback_at is not None
        
        # 验证订单状态更新
        order = session.query(Order).filter(Order.id == sample_payment.order_id).first()
        assert order.status == "paid"
    
    def test_alipay_callback_amount_mismatch(self, payment_service, sample_payment):
        """
        测试支付宝回调金额不匹配
        
        场景: 回调金额与实际应付金额不一致
        预期: 抛出 AmountMismatchError 异常，状态不变
        """
        # 准备回调数据（错误金额）
        callback_data = {
            "out_trade_no": sample_payment.id,
            "trade_no": "2024022122001156789012345678",
            "total_amount": str(sample_payment.amount + 10.0),  # 错误的金额
            "trade_status": "TRADE_SUCCESS"
        }
        
        # 预期抛出异常
        with pytest.raises(AmountMismatchError) as exc_info:
            payment_service.process_alipay_callback(callback_data)
        
        # 验证异常信息
        assert "金额不匹配" in str(exc_info.value)
    
    def test_alipay_callback_payment_not_found(self, payment_service):
        """
        测试支付宝回调支付记录不存在
        
        场景: 使用不存在的支付ID进行回调
        预期: 抛出 PaymentNotFoundError 异常
        """
        # 准备回调数据（不存在的支付ID）
        callback_data = {
            "out_trade_no": "PAY999999999",
            "trade_no": "2024022122001156789012345678",
            "total_amount": "99.99",
            "trade_status": "TRADE_SUCCESS"
        }
        
        # 预期抛出异常
        with pytest.raises(PaymentNotFoundError) as exc_info:
            payment_service.process_alipay_callback(callback_data)
        
        # 验证异常信息
        assert "支付记录不存在" in str(exc_info.value)
    
    def test_alipay_callback_duplicate(self, payment_service, sample_payment, session):
        """
        测试支付宝重复回调
        
        场景: 支付已成功，再次收到回调
        预期: 抛出 DuplicateCallbackError 异常
        """
        # 先将支付状态设为成功
        sample_payment.status = PaymentStatus.SUCCESS.value
        sample_payment.third_party_id = "2024022122001156789012345678"
        session.commit()
        
        # 准备回调数据
        callback_data = {
            "out_trade_no": sample_payment.id,
            "trade_no": "2024022122001156789012345678",
            "total_amount": str(sample_payment.amount),
            "trade_status": "TRADE_SUCCESS"
        }
        
        # 预期抛出异常
        with pytest.raises(DuplicateCallbackError) as exc_info:
            payment_service.process_alipay_callback(callback_data)
        
        # 验证异常信息
        assert "重复回调" in str(exc_info.value)
    
    def test_alipay_callback_not_success_status(self, payment_service, sample_payment, session):
        """
        测试支付宝回调非成功状态
        
        场景: 交易状态不是 TRADE_SUCCESS
        预期: 支付状态保持待支付，不做更新
        """
        # 准备回调数据（非成功状态）
        callback_data = {
            "out_trade_no": sample_payment.id,
            "trade_no": "2024022122001156789012345678",
            "total_amount": str(sample_payment.amount),
            "trade_status": "WAIT_BUYER_PAY"  # 等待买家付款
        }
        
        # 处理回调
        payment = payment_service.process_alipay_callback(callback_data)
        
        # 验证支付状态未改变
        assert payment.status == PaymentStatus.PENDING.value
        assert payment.third_party_id is None
        assert payment.callback_at is None


# ==================== 微信支付回调功能测试 ====================

class TestWechatCallback:
    """
    测试微信支付回调功能
    
    包括:
    1. 微信回调成功
    2. 金额不匹配（微信金额单位为分）
    3. 支付记录不存在
    4. 重复回调
    5. 业务结果非成功
    """
    
    def test_wechat_callback_success(self, payment_service, sample_payment, session):
        """
        测试微信支付回调成功场景
        
        场景: 微信返回 SUCCESS 结果，金额匹配（转换为分）
        预期: 支付状态更新为成功，订单状态更新为已支付
        """
        # 准备回调数据（微信金额是分）
        amount_fen = int(sample_payment.amount * 100)
        callback_data = {
            "out_trade_no": sample_payment.id,
            "transaction_id": "420000202420240221678901234567",
            "total_fee": amount_fen,
            "result_code": "SUCCESS"
        }
        
        # 处理回调
        payment = payment_service.process_wechat_callback(callback_data)
        
        # 验证支付记录更新
        assert payment.status == PaymentStatus.SUCCESS.value
        assert payment.third_party_id == callback_data["transaction_id"]
        assert payment.callback_data == str(callback_data)
        assert payment.callback_at is not None
        
        # 验证订单状态更新
        order = session.query(Order).filter(Order.id == sample_payment.order_id).first()
        assert order.status == "paid"
    
    def test_wechat_callback_amount_mismatch(self, payment_service, sample_payment):
        """
        测试微信支付回调金额不匹配
        
        场景: 回调金额（分）与实际应付金额不一致
        预期: 抛出 AmountMismatchError 异常
        """
        # 准备回调数据（错误金额，多加100分=1元）
        callback_data = {
            "out_trade_no": sample_payment.id,
            "transaction_id": "420000202420240221678901234567",
            "total_fee": int((sample_payment.amount + 1.0) * 100),  # 错误的金额
            "result_code": "SUCCESS"
        }
        
        # 预期抛出异常
        with pytest.raises(AmountMismatchError) as exc_info:
            payment_service.process_wechat_callback(callback_data)
        
        # 验证异常信息
        assert "金额不匹配" in str(exc_info.value)
    
    def test_wechat_callback_payment_not_found(self, payment_service):
        """
        测试微信支付回调支付记录不存在
        
        场景: 使用不存在的支付ID进行回调
        预期: 抛出 PaymentNotFoundError 异常
        """
        # 准备回调数据（不存在的支付ID）
        callback_data = {
            "out_trade_no": "PAY999999999",
            "transaction_id": "420000202420240221678901234567",
            "total_fee": 9999,
            "result_code": "SUCCESS"
        }
        
        # 预期抛出异常
        with pytest.raises(PaymentNotFoundError) as exc_info:
            payment_service.process_wechat_callback(callback_data)
        
        # 验证异常信息
        assert "支付记录不存在" in str(exc_info.value)
    
    def test_wechat_callback_duplicate(self, payment_service, sample_payment, session):
        """
        测试微信支付重复回调
        
        场景: 支付已成功，再次收到回调
        预期: 抛出 DuplicateCallbackError 异常
        """
        # 先将支付状态设为成功
        sample_payment.status = PaymentStatus.SUCCESS.value
        sample_payment.third_party_id = "420000202420240221678901234567"
        session.commit()
        
        # 准备回调数据
        amount_fen = int(sample_payment.amount * 100)
        callback_data = {
            "out_trade_no": sample_payment.id,
            "transaction_id": "420000202420240221678901234567",
            "total_fee": amount_fen,
            "result_code": "SUCCESS"
        }
        
        # 预期抛出异常
        with pytest.raises(DuplicateCallbackError) as exc_info:
            payment_service.process_wechat_callback(callback_data)
        
        # 验证异常信息
        assert "重复回调" in str(exc_info.value)
    
    def test_wechat_callback_fail_result(self, payment_service, sample_payment, session):
        """
        测试微信支付回调失败结果
        
        场景: 业务结果不是 SUCCESS
        预期: 支付状态保持待支付，不做更新
        """
        # 准备回调数据（失败结果）
        amount_fen = int(sample_payment.amount * 100)
        callback_data = {
            "out_trade_no": sample_payment.id,
            "transaction_id": "420000202420240221678901234567",
            "total_fee": amount_fen,
            "result_code": "FAIL"  # 业务失败
        }
        
        # 处理回调
        payment = payment_service.process_wechat_callback(callback_data)
        
        # 验证支付状态未改变
        assert payment.status == PaymentStatus.PENDING.value
        assert payment.third_party_id is None
        assert payment.callback_at is None


# ==================== 支付状态查询功能测试 ====================

class TestQueryPaymentStatus:
    """
    测试支付状态查询功能
    
    包括:
    1. 正常查询支付状态
    2. 查询不存在的支付
    3. 查询不同状态的支付
    """
    
    def test_query_payment_status_success(self, payment_service, sample_payment):
        """
        测试正常查询支付状态
        
        场景: 使用存在的支付ID查询
        预期: 返回完整的支付状态信息
        """
        # 查询支付状态
        status = payment_service.query_payment_status(sample_payment.id)
        
        # 验证返回信息
        assert status["payment_id"] == sample_payment.id
        assert status["order_id"] == sample_payment.order_id
        assert status["amount"] == sample_payment.amount
        assert status["channel"] == sample_payment.channel
        assert status["status"] == sample_payment.status
        assert status["third_party_id"] == sample_payment.third_party_id
        assert "created_at" in status
        assert "updated_at" in status
        assert "callback_at" in status
    
    def test_query_payment_status_not_found(self, payment_service):
        """
        测试查询不存在的支付
        
        场景: 使用不存在的支付ID查询
        预期: 抛出 PaymentNotFoundError 异常
        """
        # 使用不存在的支付ID
        non_existent_payment_id = "PAY999999999"
        
        # 预期抛出异常
        with pytest.raises(PaymentNotFoundError) as exc_info:
            payment_service.query_payment_status(non_existent_payment_id)
        
        # 验证异常信息
        assert "支付记录不存在" in str(exc_info.value)
        assert non_existent_payment_id in str(exc_info.value)
    
    def test_query_payment_status_pending(self, payment_service, sample_payment):
        """
        测试查询待支付状态
        
        场景: 支付处于待支付状态
        预期: 返回状态为 pending
        """
        # 确保状态为待支付
        assert sample_payment.status == PaymentStatus.PENDING.value
        
        # 查询状态
        status = payment_service.query_payment_status(sample_payment.id)
        
        # 验证状态
        assert status["status"] == PaymentStatus.PENDING.value
        assert status["third_party_id"] is None
        assert status["callback_at"] is None
    
    def test_query_payment_status_success_state(self, payment_service, sample_payment, session):
        """
        测试查询支付成功状态
        
        场景: 支付已成功
        预期: 返回状态为 success，包含回调信息
        """
        # 将支付设为成功状态
        sample_payment.status = PaymentStatus.SUCCESS.value
        sample_payment.third_party_id = "THIRD_PARTY_001"
        sample_payment.callback_at = datetime.utcnow()
        session.commit()
        
        # 查询状态
        status = payment_service.query_payment_status(sample_payment.id)
        
        # 验证状态
        assert status["status"] == PaymentStatus.SUCCESS.value
        assert status["third_party_id"] == "THIRD_PARTY_001"
        assert status["callback_at"] is not None


# ==================== 边界条件测试 ====================

class TestEdgeCases:
    """
    测试边界条件和异常情况
    """
    
    def test_amount_precision(self, payment_service, session):
        """
        测试金额精度处理
        
        场景: 金额有浮点精度误差
        预期: 允许0.01元以内的误差
        """
        # 创建订单
        order = Order(
            id="ORD_PRECISION_001",
            user_id="USER001",
            amount=100.00,
            status="pending"
        )
        session.add(order)
        session.commit()
        
        # 创建支付
        payment = payment_service.create_payment(
            order_id=order.id,
            user_id=order.user_id,
            amount=order.amount,
            channel=PaymentChannel.ALIPAY
        )
        
        # 回调金额有0.005元的误差（在允许范围内）
        callback_data = {
            "out_trade_no": payment.id,
            "trade_no": "2024022122001156789012345678",
            "total_amount": "100.005",  # 0.005元误差
            "trade_status": "TRADE_SUCCESS"
        }
        
        # 应该成功处理
        updated_payment = payment_service.process_alipay_callback(callback_data)
        assert updated_payment.status == PaymentStatus.SUCCESS.value
    
    def test_zero_amount(self, payment_service, session):
        """
        测试零金额支付
        
        场景: 订单金额为0
        预期: 正常处理
        """
        # 创建零金额订单
        order = Order(
            id="ORD_ZERO_001",
            user_id="USER001",
            amount=0.00,
            status="pending"
        )
        session.add(order)
        session.commit()
        
        # 创建支付
        payment = payment_service.create_payment(
            order_id=order.id,
            user_id=order.user_id,
            amount=order.amount,
            channel=PaymentChannel.WECHAT
        )
        
        # 回调
        callback_data = {
            "out_trade_no": payment.id,
            "transaction_id": "420000202420240221678901234567",
            "total_fee": 0,  # 0分
            "result_code": "SUCCESS"
        }
        
        updated_payment = payment_service.process_wechat_callback(callback_data)
        assert updated_payment.status == PaymentStatus.SUCCESS.value
        assert updated_payment.amount == 0.00
