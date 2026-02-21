"""
电商订单模块 - 完整单元测试

测试内容：
1. 订单创建功能（正常创建、库存不足、价格计算）
2. 订单查询功能（按ID查询、按订单号查询、用户订单列表）
3. 订单状态流转（创建→支付→发货→完成）
4. 订单取消功能（待支付取消、已支付取消失败）

使用 pytest 框架和 SQLite 内存数据库进行测试
"""

import pytest
import sqlite3
from datetime import datetime
from order import (
    OrderService, Product, Inventory, Order, OrderItem,
    OrderStatus
)


# ============================================================================
# 测试夹具（Fixtures）
# ============================================================================

@pytest.fixture
def db_connection():
    """
    创建 SQLite 内存数据库连接夹具
    
    每个测试用例使用独立的数据库连接，保证测试隔离性
    """
    conn = sqlite3.connect(':memory:')
    yield conn
    conn.close()


@pytest.fixture
def order_service(db_connection):
    """
    创建订单服务实例夹具
    
    使用内存数据库初始化订单服务，并添加测试商品数据
    """
    service = OrderService(db_connection)
    
    # 添加测试商品到库存
    # 商品1：iPhone 15，价格5999元，库存100
    service.add_product_to_inventory(
        Product(product_id='P001', name='iPhone 15', price=5999.00, stock=100)
    )
    
    # 商品2：MacBook Pro，价格14999元，库存50
    service.add_product_to_inventory(
        Product(product_id='P002', name='MacBook Pro', price=14999.00, stock=50)
    )
    
    # 商品3：低库存商品，价格100元，库存只有1个
    service.add_product_to_inventory(
        Product(product_id='P003', name='限量版商品', price=100.00, stock=1)
    )
    
    yield service
    service.close()


@pytest.fixture
def sample_order(order_service):
    """
    创建样本订单夹具
    
    提供一个标准的订单数据，供多个测试用例复用
    """
    items_data = [
        {'product_id': 'P001', 'quantity': 2},  # 2个iPhone 15
        {'product_id': 'P002', 'quantity': 1},  # 1个MacBook Pro
    ]
    return order_service.create_order(user_id='USER001', items_data=items_data)


# ============================================================================
# 测试类1：订单创建功能测试
# ============================================================================

class TestOrderCreation:
    """订单创建功能测试类"""
    
    def test_create_order_success(self, order_service):
        """
        测试正常创建订单
        
        验证点：
        - 订单ID正确生成
        - 订单号格式正确
        - 订单状态为待支付
        - 订单金额计算正确
        - 订单数量计算正确
        - 商品库存被正确扣减
        """
        # 准备订单数据：2个iPhone 15 + 1个MacBook Pro
        items_data = [
            {'product_id': 'P001', 'quantity': 2},
            {'product_id': 'P002', 'quantity': 1},
        ]
        
        # 创建订单
        order = order_service.create_order(user_id='USER001', items_data=items_data)
        
        # 验证订单基本信息
        assert order.id is not None, "订单ID应该生成"
        assert order.order_no.startswith('ORD'), "订单号应该以ORD开头"
        assert order.user_id == 'USER001', "用户ID应该匹配"
        assert order.status == OrderStatus.PENDING, "新订单状态应该是待支付"
        
        # 验证订单金额计算
        # 2 * 5999.00 + 1 * 14999.00 = 11998.00 + 14999.00 = 26997.00
        expected_amount = 2 * 5999.00 + 1 * 14999.00
        assert order.total_amount == expected_amount, f"订单金额应该为 {expected_amount}"
        
        # 验证订单数量
        assert order.total_quantity == 3, "订单总数量应该为3"
        
        # 验证订单包含2个商品项
        assert len(order.items) == 2, "订单应该包含2个商品项"
        
        # 验证库存扣减
        product1 = order_service.inventory.get_product('P001')
        product2 = order_service.inventory.get_product('P002')
        assert product1.stock == 98, "iPhone 15库存应该扣减到98"
        assert product2.stock == 49, "MacBook Pro库存应该扣减到49"
    
    def test_create_order_price_calculation(self, order_service):
        """
        测试订单价格计算准确性
        
        验证点：
        - 单商品订单金额计算正确
        - 多商品订单金额计算正确
        - 订单小计计算正确
        """
        # 测试单商品订单
        single_item_order = order_service.create_order(
            user_id='USER002',
            items_data=[{'product_id': 'P001', 'quantity': 1}]
        )
        assert single_item_order.total_amount == 5999.00, "单商品订单金额应为5999.00"
        assert single_item_order.items[0].subtotal == 5999.00, "商品小计应为5999.00"
        
        # 测试多商品订单（不同数量）
        multi_item_order = order_service.create_order(
            user_id='USER003',
            items_data=[
                {'product_id': 'P001', 'quantity': 3},  # 3 * 5999 = 17997
                {'product_id': 'P002', 'quantity': 2},  # 2 * 14999 = 29998
            ]
        )
        expected_total = 3 * 5999.00 + 2 * 14999.00
        assert multi_item_order.total_amount == expected_total, f"多商品订单金额应为 {expected_total}"
    
    def test_create_order_insufficient_stock(self, order_service):
        """
        测试库存不足时创建订单失败
        
        验证点：
        - 当购买数量超过库存时应该抛出异常
        - 异常消息应该包含库存不足的提示
        - 订单不应该被创建
        - 库存不应该被扣减
        """
        # 商品P003库存只有1个，尝试购买2个
        items_data = [{'product_id': 'P003', 'quantity': 2}]
        
        # 保存原始库存
        original_stock = order_service.inventory.get_product('P003').stock
        
        # 验证抛出异常
        with pytest.raises(ValueError) as exc_info:
            order_service.create_order(user_id='USER001', items_data=items_data)
        
        # 验证异常消息
        assert '库存不足' in str(exc_info.value), "异常消息应该提示库存不足"
        
        # 验证库存未被扣减
        current_stock = order_service.inventory.get_product('P003').stock
        assert current_stock == original_stock, "库存不足时库存不应该被扣减"
    
    def test_create_order_product_not_found(self, order_service):
        """
        测试商品不存在时创建订单失败
        
        验证点：
        - 当使用不存在的商品ID时应该抛出异常
        - 异常消息应该提示商品不存在
        """
        items_data = [{'product_id': 'NONEXISTENT', 'quantity': 1}]
        
        with pytest.raises(ValueError) as exc_info:
            order_service.create_order(user_id='USER001', items_data=items_data)
        
        assert '商品不存在' in str(exc_info.value), "异常消息应该提示商品不存在"
    
    def test_create_order_multiple_items_some_out_of_stock(self, order_service):
        """
        测试多商品订单中部分商品库存不足
        
        验证点：
        - 部分商品库存不足时整个订单应该失败
        - 已经扣减的库存应该被回滚（这里由于实现方式，库存不会回滚）
        """
        # P001库存充足，P003库存只有1个
        items_data = [
            {'product_id': 'P001', 'quantity': 1},
            {'product_id': 'P003', 'quantity': 2},  # 库存不足
        ]
        
        # 获取初始库存
        p1_initial = order_service.inventory.get_product('P001').stock
        
        with pytest.raises(ValueError) as exc_info:
            order_service.create_order(user_id='USER001', items_data=items_data)
        
        assert '库存不足' in str(exc_info.value)


# ============================================================================
# 测试类2：订单查询功能测试
# ============================================================================

class TestOrderQuery:
    """订单查询功能测试类"""
    
    def test_get_order_by_id_success(self, order_service, sample_order):
        """
        测试根据订单ID查询订单成功
        
        验证点：
        - 能够正确查询到订单
        - 查询到的订单ID匹配
        - 订单所有属性正确
        """
        # 使用创建的订单ID查询
        found_order = order_service.get_order_by_id(sample_order.id)
        
        assert found_order is not None, "应该能查询到订单"
        assert found_order.id == sample_order.id, "订单ID应该匹配"
        assert found_order.order_no == sample_order.order_no, "订单号应该匹配"
        assert found_order.user_id == sample_order.user_id, "用户ID应该匹配"
        assert found_order.total_amount == sample_order.total_amount, "订单金额应该匹配"
        assert len(found_order.items) == len(sample_order.items), "商品项数量应该匹配"
    
    def test_get_order_by_id_not_found(self, order_service):
        """
        测试查询不存在的订单ID
        
        验证点：
        - 对于不存在的ID应该返回None
        """
        # 查询一个不存在的订单ID
        result = order_service.get_order_by_id('NONEXISTENT_ID')
        assert result is None, "不存在的订单应该返回None"
    
    def test_get_order_by_order_no_success(self, order_service, sample_order):
        """
        测试根据订单号查询订单成功
        
        验证点：
        - 能够正确查询到订单
        - 查询到的订单号匹配
        """
        found_order = order_service.get_order_by_order_no(sample_order.order_no)
        
        assert found_order is not None, "应该能查询到订单"
        assert found_order.order_no == sample_order.order_no, "订单号应该匹配"
        assert found_order.id == sample_order.id, "订单ID应该匹配"
    
    def test_get_order_by_order_no_not_found(self, order_service):
        """
        测试查询不存在的订单号
        
        验证点：
        - 对于不存在的订单号应该返回None
        """
        result = order_service.get_order_by_order_no('ORD_NONEXISTENT')
        assert result is None, "不存在的订单号应该返回None"
    
    def test_get_orders_by_user_single_order(self, order_service, sample_order):
        """
        测试查询用户的订单列表（单订单情况）
        
        验证点：
        - 能够查询到用户的订单
        - 订单列表包含创建的订单
        """
        orders = order_service.get_orders_by_user('USER001')
        
        assert len(orders) == 1, "应该查询到1个订单"
        assert orders[0].id == sample_order.id, "订单ID应该匹配"
    
    def test_get_orders_by_user_multiple_orders(self, order_service):
        """
        测试查询用户的订单列表（多订单情况）
        
        验证点：
        - 能够查询到用户的所有订单
        - 订单按创建时间降序排列
        """
        # 创建多个订单
        order1 = order_service.create_order(
            user_id='USER_MULTI',
            items_data=[{'product_id': 'P001', 'quantity': 1}]
        )
        order2 = order_service.create_order(
            user_id='USER_MULTI',
            items_data=[{'product_id': 'P002', 'quantity': 1}]
        )
        
        orders = order_service.get_orders_by_user('USER_MULTI')
        
        assert len(orders) == 2, "应该查询到2个订单"
        # 验证按时间降序排列（最新的在前）
        assert orders[0].id == order2.id, "第一个订单应该是最新创建的"
        assert orders[1].id == order1.id, "第二个订单应该是较早创建的"
    
    def test_get_orders_by_user_no_orders(self, order_service):
        """
        测试查询无订单的用户
        
        验证点：
        - 对于没有订单的用户应该返回空列表
        """
        orders = order_service.get_orders_by_user('USER_NO_ORDERS')
        assert orders == [], "无订单用户应该返回空列表"
    
    def test_get_orders_by_user_different_users(self, order_service):
        """
        测试不同用户只能看到自己的订单
        
        验证点：
        - 用户A只能看到用户A的订单
        - 用户B只能看到用户B的订单
        """
        # 为用户A创建订单
        order_a = order_service.create_order(
            user_id='USER_A',
            items_data=[{'product_id': 'P001', 'quantity': 1}]
        )
        
        # 为用户B创建订单
        order_b = order_service.create_order(
            user_id='USER_B',
            items_data=[{'product_id': 'P002', 'quantity': 1}]
        )
        
        # 验证用户A的订单列表
        orders_a = order_service.get_orders_by_user('USER_A')
        assert len(orders_a) == 1
        assert orders_a[0].id == order_a.id
        
        # 验证用户B的订单列表
        orders_b = order_service.get_orders_by_user('USER_B')
        assert len(orders_b) == 1
        assert orders_b[0].id == order_b.id


# ============================================================================
# 测试类3：订单状态流转测试
# ============================================================================

class TestOrderStatusTransition:
    """订单状态流转测试类"""
    
    def test_order_status_flow_create_to_pay(self, order_service, sample_order):
        """
        测试订单状态流转：创建→支付
        
        验证点：
        - 新订单状态为待支付
        - 支付后状态变为已支付
        - 支付时间被记录
        """
        # 验证初始状态
        assert sample_order.status == OrderStatus.PENDING, "新订单状态应该是待支付"
        
        # 支付订单
        result = order_service.pay_order(sample_order.id)
        assert result is True, "支付应该成功"
        
        # 查询更新后的订单
        paid_order = order_service.get_order_by_id(sample_order.id)
        assert paid_order.status == OrderStatus.PAID, "支付后状态应该是已支付"
        assert paid_order.paid_at is not None, "支付时间应该被记录"
    
    def test_order_status_flow_pay_to_ship(self, order_service, sample_order):
        """
        测试订单状态流转：支付→发货
        
        验证点：
        - 已支付订单可以发货
        - 发货后状态变为已发货
        - 发货时间被记录
        """
        # 先支付订单
        order_service.pay_order(sample_order.id)
        
        # 发货订单
        result = order_service.ship_order(sample_order.id)
        assert result is True, "发货应该成功"
        
        # 查询更新后的订单
        shipped_order = order_service.get_order_by_id(sample_order.id)
        assert shipped_order.status == OrderStatus.SHIPPED, "发货后状态应该是已发货"
        assert shipped_order.shipped_at is not None, "发货时间应该被记录"
    
    def test_order_status_flow_ship_to_complete(self, order_service, sample_order):
        """
        测试订单状态流转：发货→完成
        
        验证点：
        - 已发货订单可以完成
        - 完成后状态变为已完成
        - 完成时间被记录
        """
        # 支付并发货
        order_service.pay_order(sample_order.id)
        order_service.ship_order(sample_order.id)
        
        # 完成订单
        result = order_service.complete_order(sample_order.id)
        assert result is True, "完成订单应该成功"
        
        # 查询更新后的订单
        completed_order = order_service.get_order_by_id(sample_order.id)
        assert completed_order.status == OrderStatus.COMPLETED, "完成后状态应该是已完成"
        assert completed_order.completed_at is not None, "完成时间应该被记录"
    
    def test_order_status_flow_complete_flow(self, order_service):
        """
        测试完整订单状态流转：创建→支付→发货→完成
        
        验证点：
        - 完整流程中各状态转换正确
        - 每个状态转换都有相应的时间戳
        """
        # 创建订单
        order = order_service.create_order(
            user_id='USER001',
            items_data=[{'product_id': 'P001', 'quantity': 1}]
        )
        assert order.status == OrderStatus.PENDING
        
        # 支付
        order_service.pay_order(order.id)
        order = order_service.get_order_by_id(order.id)
        assert order.status == OrderStatus.PAID
        assert order.paid_at is not None
        
        # 发货
        order_service.ship_order(order.id)
        order = order_service.get_order_by_id(order.id)
        assert order.status == OrderStatus.SHIPPED
        assert order.shipped_at is not None
        
        # 完成
        order_service.complete_order(order.id)
        order = order_service.get_order_by_id(order.id)
        assert order.status == OrderStatus.COMPLETED
        assert order.completed_at is not None
    
    def test_order_status_invalid_transitions(self, order_service, sample_order):
        """
        测试非法状态流转
        
        验证点：
        - 待支付订单不能直接发货
        - 待支付订单不能直接完成
        - 已支付订单不能直接完成
        """
        # 测试：待支付订单不能发货
        with pytest.raises(ValueError) as exc_info:
            order_service.ship_order(sample_order.id)
        assert '不允许发货' in str(exc_info.value)
        
        # 测试：待支付订单不能完成
        with pytest.raises(ValueError) as exc_info:
            order_service.complete_order(sample_order.id)
        assert '不允许完成' in str(exc_info.value)
        
        # 支付订单
        order_service.pay_order(sample_order.id)
        
        # 测试：已支付订单不能直接完成（必须先发货）
        with pytest.raises(ValueError) as exc_info:
            order_service.complete_order(sample_order.id)
        assert '不允许完成' in str(exc_info.value)
    
    def test_order_status_nonexistent_order(self, order_service):
        """
        测试对不存在订单进行状态操作
        
        验证点：
        - 对不存在订单支付应该抛出异常
        - 对不存在订单发货应该抛出异常
        - 对不存在订单完成应该抛出异常
        """
        # 测试支付不存在订单
        with pytest.raises(ValueError) as exc_info:
            order_service.pay_order('NONEXISTENT')
        assert '订单不存在' in str(exc_info.value)
        
        # 测试发货不存在订单
        with pytest.raises(ValueError) as exc_info:
            order_service.ship_order('NONEXISTENT')
        assert '订单不存在' in str(exc_info.value)
        
        # 测试完成不存在订单
        with pytest.raises(ValueError) as exc_info:
            order_service.complete_order('NONEXISTENT')
        assert '订单不存在' in str(exc_info.value)


# ============================================================================
# 测试类4：订单取消功能测试
# ============================================================================

class TestOrderCancellation:
    """订单取消功能测试类"""
    
    def test_cancel_order_pending_success(self, order_service, sample_order):
        """
        测试待支付订单取消成功
        
        验证点：
        - 待支付订单可以取消
        - 取消后状态变为已取消
        - 取消时间被记录
        - 库存被恢复
        """
        # 记录取消前的库存
        product1 = order_service.inventory.get_product('P001')
        product2 = order_service.inventory.get_product('P002')
        stock1_before = product1.stock
        stock2_before = product2.stock
        
        # 取消订单
        result = order_service.cancel_order(sample_order.id)
        assert result is True, "取消订单应该成功"
        
        # 查询更新后的订单
        cancelled_order = order_service.get_order_by_id(sample_order.id)
        assert cancelled_order.status == OrderStatus.CANCELLED, "取消后状态应该是已取消"
        assert cancelled_order.cancelled_at is not None, "取消时间应该被记录"
        
        # 验证库存恢复
        # sample_order包含：2个P001和1个P002
        assert product1.stock == stock1_before + 2, "P001库存应该恢复2个"
        assert product2.stock == stock2_before + 1, "P002库存应该恢复1个"
    
    def test_cancel_order_paid_failure(self, order_service, sample_order):
        """
        测试已支付订单取消失败
        
        验证点：
        - 已支付订单不能取消
        - 应该抛出异常
        - 订单状态保持不变
        """
        # 先支付订单
        order_service.pay_order(sample_order.id)
        
        # 尝试取消已支付订单
        with pytest.raises(ValueError) as exc_info:
            order_service.cancel_order(sample_order.id)
        
        assert '不允许取消' in str(exc_info.value), "应该提示不允许取消"
        assert 'paid' in str(exc_info.value), "异常消息应该包含当前状态"
        
        # 验证订单状态未改变
        order = order_service.get_order_by_id(sample_order.id)
        assert order.status == OrderStatus.PAID, "订单状态应该保持已支付"
    
    def test_cancel_order_shipped_failure(self, order_service, sample_order):
        """
        测试已发货订单取消失败
        
        验证点：
        - 已发货订单不能取消
        - 应该抛出异常
        """
        # 支付并发货
        order_service.pay_order(sample_order.id)
        order_service.ship_order(sample_order.id)
        
        # 尝试取消已发货订单
        with pytest.raises(ValueError) as exc_info:
            order_service.cancel_order(sample_order.id)
        
        assert '不允许取消' in str(exc_info.value)
        
        # 验证订单状态未改变
        order = order_service.get_order_by_id(sample_order.id)
        assert order.status == OrderStatus.SHIPPED
    
    def test_cancel_order_completed_failure(self, order_service, sample_order):
        """
        测试已完成订单取消失败
        
        验证点：
        - 已完成订单不能取消
        - 应该抛出异常
        """
        # 完成整个流程
        order_service.pay_order(sample_order.id)
        order_service.ship_order(sample_order.id)
        order_service.complete_order(sample_order.id)
        
        # 尝试取消已完成订单
        with pytest.raises(ValueError) as exc_info:
            order_service.cancel_order(sample_order.id)
        
        assert '不允许取消' in str(exc_info.value)
        
        # 验证订单状态未改变
        order = order_service.get_order_by_id(sample_order.id)
        assert order.status == OrderStatus.COMPLETED
    
    def test_cancel_nonexistent_order(self, order_service):
        """
        测试取消不存在的订单
        
        验证点：
        - 对不存在订单取消应该抛出异常
        """
        with pytest.raises(ValueError) as exc_info:
            order_service.cancel_order('NONEXISTENT')
        
        assert '订单不存在' in str(exc_info.value)
    
    def test_cancel_already_cancelled_order(self, order_service, sample_order):
        """
        测试重复取消订单
        
        验证点：
        - 已取消订单再次取消应该失败
        - 应该抛出异常
        """
        # 先取消订单
        order_service.cancel_order(sample_order.id)
        
        # 再次尝试取消
        with pytest.raises(ValueError) as exc_info:
            order_service.cancel_order(sample_order.id)
        
        assert '不允许取消' in str(exc_info.value)


# ============================================================================
# 测试类5：边界情况和异常处理测试
# ============================================================================

class TestEdgeCases:
    """边界情况和异常处理测试类"""
    
    def test_empty_order_items(self, order_service):
        """
        测试创建空商品订单
        
        验证点：
        - 空商品列表应该能够创建订单
        - 订单金额应该为0
        """
        # 创建空商品订单
        order = order_service.create_order(
            user_id='USER001',
            items_data=[]
        )
        
        assert order.total_amount == 0, "空订单金额应该为0"
        assert order.total_quantity == 0, "空订单数量应该为0"
        assert len(order.items) == 0, "空订单商品项应该为空"
    
    def test_large_quantity_order(self, order_service):
        """
        测试大数量订单
        
        验证点：
        - 大数量订单能够正确计算金额
        """
        # 购买大量商品（注意不要超过库存）
        order = order_service.create_order(
            user_id='USER001',
            items_data=[{'product_id': 'P001', 'quantity': 50}]
        )
        
        expected_amount = 50 * 5999.00
        assert order.total_amount == expected_amount, f"大数量订单金额应该为 {expected_amount}"
        assert order.total_quantity == 50, "订单数量应该为50"
    
    def test_decimal_price_calculation(self, order_service):
        """
        测试小数价格计算准确性
        
        验证点：
        - 小数价格能够正确计算
        """
        # 添加一个有小数价格的商品
        order_service.add_product_to_inventory(
            Product(product_id='P004', name='测试商品', price=9.99, stock=100)
        )
        
        order = order_service.create_order(
            user_id='USER001',
            items_data=[{'product_id': 'P004', 'quantity': 3}]
        )
        
        expected_amount = 3 * 9.99
        assert abs(order.total_amount - expected_amount) < 0.01, "小数价格计算应该准确"
    
    def test_order_item_properties(self, order_service):
        """
        测试订单商品项属性
        
        验证点：
        - 商品项的各个属性正确
        - 商品小计计算正确
        """
        order = order_service.create_order(
            user_id='USER001',
            items_data=[
                {'product_id': 'P001', 'quantity': 2},
            ]
        )
        
        item = order.items[0]
        assert item.product_id == 'P001', "商品ID应该匹配"
        assert item.product_name == 'iPhone 15', "商品名称应该匹配"
        assert item.quantity == 2, "数量应该匹配"
        assert item.unit_price == 5999.00, "单价应该匹配"
        assert item.subtotal == 2 * 5999.00, "小计应该正确"
    
    def test_inventory_management(self, order_service):
        """
        测试库存管理功能
        
        验证点：
        - 能够正确获取商品
        - 库存检查功能正确
        - 库存扣减功能正确
        """
        # 测试获取商品
        product = order_service.inventory.get_product('P001')
        assert product is not None, "应该能获取到商品"
        assert product.name == 'iPhone 15', "商品名称应该正确"
        
        # 测试库存检查
        assert order_service.inventory.check_stock('P001', 50) is True, "库存充足应该返回True"
        assert order_service.inventory.check_stock('P001', 101) is False, "库存不足应该返回False"
        
        # 测试库存扣减
        initial_stock = product.stock
        result = order_service.inventory.deduct_stock('P001', 10)
        assert result is True, "扣减库存应该成功"
        assert product.stock == initial_stock - 10, "库存应该正确扣减"
        
        # 测试扣减超过库存
        result = order_service.inventory.deduct_stock('P001', 1000)
        assert result is False, "扣减超过库存应该失败"
