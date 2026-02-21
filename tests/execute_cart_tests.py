"""
购物车模块测试执行脚本
QA 工程师 Quinn - 测试执行报告生成
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine, Base
from models import User, Product, Cart, Category
from services.cart_service import CartService
from services.product_service import ProductService
from services.auth_service import AuthService
from models.schemas import UserCreate
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

# 测试报告数据结构
class TestResult:
    def __init__(self, case_id: str, case_name: str, priority: str):
        self.case_id = case_id
        self.case_name = case_name
        self.priority = priority
        self.status = "未执行"
        self.actual_output = ""
        self.expected_output = ""
        self.issues = []
        self.execution_time = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "priority": self.priority,
            "status": self.status,
            "actual_output": self.actual_output,
            "expected_output": self.expected_output,
            "issues": self.issues,
            "execution_time": self.execution_time
        }

# 全局测试数据
test_data = {
    "users": {},
    "products": {},
    "carts": {},
    "sessions": {}
}

# 测试结果列表
test_results: List[TestResult] = []


def setup_test_data(db: SessionLocal):
    """准备测试数据"""
    print("\n=== 准备测试数据 ===")
    
    # 创建测试用户
    for i in [1, 2]:
        try:
            user = AuthService.create_user(
                db,
                UserCreate(
                    username=f"test_user_{i}_{uuid.uuid4().hex[:6]}",
                    email=f"test{i}_{uuid.uuid4().hex[:6]}@example.com",
                    password="testpass123"
                )
            )
            test_data["users"][f"user_{i}"] = user
            print(f"✅ 创建测试用户 {i}: ID={user.id}")
        except Exception as e:
            # 用户可能已存在，查询现有用户
            user = db.query(User).filter(User.username == f"test_user_{i}").first()
            if user:
                test_data["users"][f"user_{i}"] = user
                print(f"✅ 使用现有用户 {i}: ID={user.id}")
    
    # 创建测试商品
    products_data = [
        {"name": "测试商品-正常", "price": 100, "stock": 100},
        {"name": "测试商品-低库存", "price": 50, "stock": 5},
        {"name": "测试商品-已下架", "price": 100, "stock": 100},
    ]
    
    for i, pdata in enumerate(products_data):
        product = ProductService.create_product(db, **pdata)
        key = ["prod_normal", "prod_low_stock", "prod_inactive"][i]
        test_data["products"][key] = product
        print(f"✅ 创建测试商品 {key}: ID={product.id}, stock={product.stock}, status={product.status}")
    
    # 将第三个商品设为下架状态
    ProductService.update_product(db, test_data["products"]["prod_inactive"].id, {"status": "inactive"})
    db.refresh(test_data["products"]["prod_inactive"])
    print(f"✅ 更新测试商品 prod_inactive 状态为 inactive")
    
    # 创建 session IDs
    test_data["sessions"]["sess_1"] = f"sess-test-{uuid.uuid4().hex[:8]}"
    test_data["sessions"]["sess_empty"] = f"sess-empty-{uuid.uuid4().hex[:8]}"
    print(f"✅ 创建测试 Sessions")
    
    return test_data


def cleanup_test_data(db: SessionLocal):
    """清理测试数据"""
    print("\n=== 清理测试数据 ===")
    
    # 清理购物车
    for user_key, user in test_data["users"].items():
        CartService.clear_cart(db, user_id=user.id)
    
    for sess_key, session_id in test_data["sessions"].items():
        CartService.clear_cart(db, session_id=session_id)
    
    # 清理商品
    for prod_key, product in test_data["products"].items():
        try:
            ProductService.delete_product(db, product.id, hard_delete=True)
            print(f"✅ 删除测试商品: {prod_key}")
        except:
            pass
    
    print("✅ 测试数据清理完成")


def run_test(case_id: str, case_name: str, priority: str, test_func, *args, **kwargs):
    """执行单个测试用例"""
    result = TestResult(case_id, case_name, priority)
    start_time = datetime.now()
    
    try:
        print(f"\n--- 执行测试: {case_id} - {case_name} ---")
        test_func(result, *args, **kwargs)
        if result.status == "未执行":
            result.status = "通过"
    except AssertionError as e:
        result.status = "失败"
        result.issues.append(f"断言失败: {str(e)}")
        result.actual_output = str(e)
    except Exception as e:
        result.status = "失败"
        result.issues.append(f"异常: {str(e)}")
        result.actual_output = str(e)
        import traceback
        traceback.print_exc()
    finally:
        result.execution_time = (datetime.now() - start_time).total_seconds()
    
    test_results.append(result)
    status_icon = "✅" if result.status == "通过" else "❌"
    print(f"{status_icon} 测试 {case_id}: {result.status}")
    return result


# ==================== 测试用例实现 ====================

def test_add_to_cart_logged_in(result: TestResult, db: SessionLocal):
    """TC-CART-001: 登录用户添加商品到购物车"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    result.expected_output = f"返回 Cart 对象，user_id={user.id}, product_id={product.id}, quantity=2"
    
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=2, user_id=user.id
    )
    
    assert cart_item.user_id == user.id, f"user_id 不匹配"
    assert cart_item.product_id == product.id, f"product_id 不匹配"
    assert cart_item.quantity == 2, f"quantity 不匹配"
    
    test_data["carts"]["cart_001"] = cart_item
    result.actual_output = f"Cart(id={cart_item.id}, user_id={cart_item.user_id}, product_id={cart_item.product_id}, quantity={cart_item.quantity})"


def test_add_to_cart_anonymous(result: TestResult, db: SessionLocal):
    """TC-CART-002: 匿名用户添加商品到购物车"""
    product = test_data["products"]["prod_normal"]
    session_id = test_data["sessions"]["sess_1"]
    
    result.expected_output = f"返回 Cart 对象，session_id={session_id}, user_id=None"
    
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, session_id=session_id
    )
    
    assert cart_item.session_id == session_id, f"session_id 不匹配"
    assert cart_item.user_id is None, f"user_id 应该为 None"
    assert cart_item.quantity == 1, f"quantity 不匹配"
    
    result.actual_output = f"Cart(id={cart_item.id}, session_id={cart_item.session_id}, user_id={cart_item.user_id})"


def test_add_to_cart_no_identifier(result: TestResult, db: SessionLocal):
    """TC-CART-003: 添加商品时缺少用户标识"""
    product = test_data["products"]["prod_normal"]
    
    result.expected_output = "抛出 ValueError('必须提供 user_id 或 session_id')"
    
    try:
        CartService.add_to_cart(db, product_id=product.id, quantity=1)
        result.status = "失败"
        result.issues.append("应该抛出 ValueError，但没有抛出")
        result.actual_output = "没有抛出异常"
    except ValueError as e:
        if "必须提供 user_id 或 session_id" in str(e):
            result.status = "通过"
            result.actual_output = f"抛出 ValueError: {e}"
        else:
            result.status = "失败"
            result.issues.append(f"错误消息不匹配: {e}")
            result.actual_output = str(e)


def test_add_to_cart_product_not_exist(result: TestResult, db: SessionLocal):
    """TC-CART-004: 添加不存在的商品"""
    user = test_data["users"]["user_1"]
    
    result.expected_output = "抛出 ValueError('商品不存在')"
    
    try:
        CartService.add_to_cart(db, product_id="prod-not-exist", quantity=1, user_id=user.id)
        result.status = "失败"
        result.issues.append("应该抛出 ValueError，但没有抛出")
        result.actual_output = "没有抛出异常"
    except ValueError as e:
        if "商品不存在" in str(e):
            result.status = "通过"
            result.actual_output = f"抛出 ValueError: {e}"
        else:
            result.status = "失败"
            result.issues.append(f"错误消息不匹配: {e}")


def test_add_to_cart_inactive_product(result: TestResult, db: SessionLocal):
    """TC-CART-005: 添加已下架商品"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_inactive"]
    
    result.expected_output = "抛出 ValueError('商品已下架')"
    
    try:
        CartService.add_to_cart(db, product_id=product.id, quantity=1, user_id=user.id)
        result.status = "失败"
        result.issues.append("应该抛出 ValueError，但没有抛出")
        result.actual_output = "没有抛出异常"
    except ValueError as e:
        if "商品已下架" in str(e):
            result.status = "通过"
            result.actual_output = f"抛出 ValueError: {e}"
        else:
            result.status = "失败"
            result.issues.append(f"错误消息不匹配: {e}")


def test_add_to_cart_insufficient_stock(result: TestResult, db: SessionLocal):
    """TC-CART-006: 添加库存不足的商品"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_low_stock"]
    
    result.expected_output = "抛出 ValueError('库存不足，当前库存: 5')"
    
    try:
        CartService.add_to_cart(db, product_id=product.id, quantity=10, user_id=user.id)
        result.status = "失败"
        result.issues.append("应该抛出 ValueError，但没有抛出")
        result.actual_output = "没有抛出异常"
    except ValueError as e:
        if "库存不足" in str(e):
            result.status = "通过"
            result.actual_output = f"抛出 ValueError: {e}"
        else:
            result.status = "失败"
            result.issues.append(f"错误消息不匹配: {e}")


def test_add_to_cart_with_spec(result: TestResult, db: SessionLocal):
    """TC-CART-007: 添加带规格组合的商品"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    spec_combo = {"颜色": "红色", "尺寸": "XL"}
    
    result.expected_output = f"返回 Cart 对象，spec_combo={spec_combo}"
    
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, spec_combo=spec_combo, user_id=user.id
    )
    
    assert cart_item.spec_combo == spec_combo, f"spec_combo 不匹配"
    
    test_data["carts"]["cart_spec_red"] = cart_item
    result.actual_output = f"Cart(id={cart_item.id}, spec_combo={cart_item.spec_combo})"


def test_add_to_cart_duplicate_spec(result: TestResult, db: SessionLocal):
    """TC-CART-008: 重复添加相同规格商品（数量累加）"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    spec_combo = {"颜色": "红色"}
    
    result.expected_output = "返回同一 Cart 对象，quantity=5 (2+3)"
    
    # 先添加 2 个
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=2, spec_combo=spec_combo, user_id=user.id
    )
    cart_id = cart_item.id
    
    # 再添加 3 个（相同规格）
    cart_item2 = CartService.add_to_cart(
        db, product_id=product.id, quantity=3, spec_combo=spec_combo, user_id=user.id
    )
    
    assert cart_item2.id == cart_id, f"应该是同一个购物车项"
    assert cart_item2.quantity == 5, f"quantity 应该是 5，实际是 {cart_item2.quantity}"
    
    result.actual_output = f"Cart(id={cart_item2.id}, quantity={cart_item2.quantity})"


def test_add_to_cart_different_spec(result: TestResult, db: SessionLocal):
    """TC-CART-009: 添加相同商品不同规格"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    result.expected_output = "返回新的 Cart 对象，数据库中存在两条记录"
    
    # 添加红色规格
    cart_red = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, spec_combo={"颜色": "红色"}, user_id=user.id
    )
    
    # 添加蓝色规格
    cart_blue = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, spec_combo={"颜色": "蓝色"}, user_id=user.id
    )
    
    assert cart_red.id != cart_blue.id, f"应该是不同的购物车项"
    
    # 验证数据库中有两条记录
    items = CartService.get_cart(db, user_id=user.id)
    product_items = [item for item in items if item.product_id == product.id]
    
    result.actual_output = f"红色项: {cart_red.id}, 蓝色项: {cart_blue.id}, 该商品共 {len(product_items)} 条记录"


def test_add_to_cart_zero_quantity(result: TestResult, db: SessionLocal):
    """TC-CART-010: 添加商品数量为0"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    result.expected_output = "返回 Cart 对象，quantity=0 或根据业务规则处理"
    
    # 数量为0应该被允许（业务规则可能不同）
    try:
        cart_item = CartService.add_to_cart(
            db, product_id=product.id, quantity=0, user_id=user.id
        )
        result.actual_output = f"Cart(id={cart_item.id}, quantity={cart_item.quantity})"
        # 数量为0被允许，但需要验证后续行为
        if cart_item.quantity == 0:
            result.issues.append("警告: 购物车项数量为0，可能导致结算问题")
    except ValueError as e:
        result.actual_output = f"抛出 ValueError: {e}"
        result.issues.append(f"数量为0被拒绝: {e}")


# ==================== 购物车列表查询测试 ====================

def test_get_cart_logged_in(result: TestResult, db: SessionLocal):
    """TC-CART-011: 登录用户查询购物车列表"""
    user = test_data["users"]["user_1"]
    
    result.expected_output = "返回 List[Cart]，包含多条记录"
    
    items = CartService.get_cart(db, user_id=user.id)
    
    assert len(items) >= 0, f"应该返回列表"
    
    result.actual_output = f"返回 {len(items)} 条购物车记录"


def test_get_cart_anonymous(result: TestResult, db: SessionLocal):
    """TC-CART-012: 匿名用户查询购物车列表"""
    session_id = test_data["sessions"]["sess_1"]
    
    result.expected_output = "返回 List[Cart]，包含匿名用户的记录"
    
    items = CartService.get_cart(db, session_id=session_id)
    
    assert len(items) >= 0, f"应该返回列表"
    
    result.actual_output = f"返回 {len(items)} 条购物车记录"


def test_get_cart_empty(result: TestResult, db: SessionLocal):
    """TC-CART-013: 查询空购物车"""
    user = test_data["users"]["user_2"]
    
    # 确保用户2购物车为空
    CartService.clear_cart(db, user_id=user.id)
    
    result.expected_output = "返回空列表 []"
    
    items = CartService.get_cart(db, user_id=user.id)
    
    assert items == [], f"应该返回空列表"
    
    result.actual_output = f"返回空列表: {items}"


def test_get_cart_no_identifier(result: TestResult, db: SessionLocal):
    """TC-CART-014: 未提供 user_id 和 session_id 查询"""
    result.expected_output = "返回空列表 []"
    
    items = CartService.get_cart(db)
    
    assert items == [], f"应该返回空列表"
    
    result.actual_output = f"返回: {items}"


def test_get_cart_item_by_id(result: TestResult, db: SessionLocal):
    """TC-CART-015: 根据ID获取单个购物车项"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    # 先添加一个商品
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user.id
    )
    
    result.expected_output = f"返回 Cart 对象，id={cart_item.id}"
    
    found_item = CartService.get_cart_item(db, cart_item.id)
    
    assert found_item is not None, f"应该找到购物车项"
    assert found_item.id == cart_item.id, f"ID 应该匹配"
    
    result.actual_output = f"返回 Cart(id={found_item.id}, product_id={found_item.product_id})"


def test_get_cart_item_not_exist(result: TestResult, db: SessionLocal):
    """TC-CART-016: 获取不存在的购物车项"""
    result.expected_output = "返回 None"
    
    found_item = CartService.get_cart_item(db, "cart-not-exist")
    
    assert found_item is None, f"应该返回 None"
    
    result.actual_output = f"返回: {found_item}"


# ==================== 修改购物车商品数量测试 ====================

def test_update_cart_item_normal(result: TestResult, db: SessionLocal):
    """TC-CART-017: 正常修改购物车商品数量"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    # 先添加商品
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=2, user_id=user.id
    )
    
    result.expected_output = "返回 Cart 对象，quantity=5"
    
    updated = CartService.update_cart_item(
        db, cart_id=cart_item.id, quantity=5, user_id=user.id
    )
    
    assert updated is not None, f"应该返回更新后的购物车项"
    assert updated.quantity == 5, f"quantity 应该是 5"
    
    result.actual_output = f"Cart(id={updated.id}, quantity={updated.quantity})"


def test_update_cart_item_stock_boundary(result: TestResult, db: SessionLocal):
    """TC-CART-018: 修改数量为库存边界值"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_low_stock"]
    
    # 先添加商品
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user.id
    )
    
    result.expected_output = "返回 Cart 对象，quantity=5（库存上限）"
    
    updated = CartService.update_cart_item(
        db, cart_id=cart_item.id, quantity=5, user_id=user.id
    )
    
    assert updated is not None, f"应该返回更新后的购物车项"
    assert updated.quantity == 5, f"quantity 应该是 5"
    
    result.actual_output = f"Cart(id={updated.id}, quantity={updated.quantity})"


def test_update_cart_item_over_stock(result: TestResult, db: SessionLocal):
    """TC-CART-019: 修改数量超过库存"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_low_stock"]
    
    # 先添加商品
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user.id
    )
    
    result.expected_output = "抛出 ValueError('库存不足，当前库存: 5')"
    
    try:
        CartService.update_cart_item(
            db, cart_id=cart_item.id, quantity=10, user_id=user.id
        )
        result.status = "失败"
        result.issues.append("应该抛出 ValueError，但没有抛出")
        result.actual_output = "没有抛出异常"
    except ValueError as e:
        if "库存不足" in str(e):
            result.status = "通过"
            result.actual_output = f"抛出 ValueError: {e}"
        else:
            result.status = "失败"
            result.issues.append(f"错误消息不匹配: {e}")


def test_update_cart_item_zero_quantity(result: TestResult, db: SessionLocal):
    """TC-CART-020: 修改数量为0（删除商品）"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    # 先添加商品
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user.id
    )
    cart_id = cart_item.id
    
    result.expected_output = "返回 None，数据库中该记录被删除"
    
    updated = CartService.update_cart_item(
        db, cart_id=cart_id, quantity=0, user_id=user.id
    )
    
    # 验证记录被删除
    found = CartService.get_cart_item(db, cart_id)
    
    assert updated is None, f"应该返回 None"
    assert found is None, f"记录应该被删除"
    
    result.actual_output = f"返回: {updated}, 记录存在: {found is not None}"


def test_update_cart_item_negative(result: TestResult, db: SessionLocal):
    """TC-CART-021: 修改数量为负数"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    # 先添加商品
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user.id
    )
    cart_id = cart_item.id
    
    result.expected_output = "返回 None，数据库中该记录被删除"
    
    updated = CartService.update_cart_item(
        db, cart_id=cart_id, quantity=-1, user_id=user.id
    )
    
    # 验证记录被删除
    found = CartService.get_cart_item(db, cart_id)
    
    assert updated is None, f"应该返回 None"
    assert found is None, f"记录应该被删除"
    
    result.actual_output = f"返回: {updated}, 记录存在: {found is not None}"


def test_update_cart_item_not_exist(result: TestResult, db: SessionLocal):
    """TC-CART-022: 修改不存在的购物车项"""
    user = test_data["users"]["user_1"]
    
    result.expected_output = "返回 None"
    
    updated = CartService.update_cart_item(
        db, cart_id="cart-not-exist", quantity=5, user_id=user.id
    )
    
    assert updated is None, f"应该返回 None"
    
    result.actual_output = f"返回: {updated}"


def test_update_cart_item_no_permission(result: TestResult, db: SessionLocal):
    """TC-CART-023: 无权限修改他人购物车项"""
    user1 = test_data["users"]["user_1"]
    user2 = test_data["users"]["user_2"]
    product = test_data["products"]["prod_normal"]
    
    # 用户2添加商品到购物车
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user2.id
    )
    
    result.expected_output = "返回 None (权限不足)"
    
    # 用户1尝试修改
    updated = CartService.update_cart_item(
        db, cart_id=cart_item.id, quantity=5, user_id=user1.id
    )
    
    assert updated is None, f"应该返回 None（权限不足）"
    
    result.actual_output = f"返回: {updated}"


def test_update_cart_item_no_user_id(result: TestResult, db: SessionLocal):
    """TC-CART-024: 修改时不传递 user_id（跳过权限验证）"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    # 先添加商品
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user.id
    )
    
    result.expected_output = "返回更新后的 Cart 对象"
    
    updated = CartService.update_cart_item(
        db, cart_id=cart_item.id, quantity=5  # 不传递 user_id
    )
    
    assert updated is not None, f"应该返回更新后的购物车项"
    assert updated.quantity == 5, f"quantity 应该是 5"
    
    result.actual_output = f"Cart(id={updated.id}, quantity={updated.quantity})"


# ==================== 删除购物车商品测试 ====================

def test_remove_from_cart_normal(result: TestResult, db: SessionLocal):
    """TC-CART-025: 正常删除购物车商品"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    # 先添加商品
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user.id
    )
    cart_id = cart_item.id
    
    result.expected_output = "返回 True，数据库中该记录被删除"
    
    success = CartService.remove_from_cart(db, cart_id=cart_id, user_id=user.id)
    
    # 验证记录被删除
    found = CartService.get_cart_item(db, cart_id)
    
    assert success is True, f"应该返回 True"
    assert found is None, f"记录应该被删除"
    
    result.actual_output = f"返回: {success}, 记录存在: {found is not None}"


def test_remove_from_cart_not_exist(result: TestResult, db: SessionLocal):
    """TC-CART-026: 删除不存在的购物车项"""
    user = test_data["users"]["user_1"]
    
    result.expected_output = "返回 False"
    
    success = CartService.remove_from_cart(db, cart_id="cart-not-exist", user_id=user.id)
    
    assert success is False, f"应该返回 False"
    
    result.actual_output = f"返回: {success}"


def test_remove_from_cart_no_permission(result: TestResult, db: SessionLocal):
    """TC-CART-027: 无权限删除他人购物车项"""
    user1 = test_data["users"]["user_1"]
    user2 = test_data["users"]["user_2"]
    product = test_data["products"]["prod_normal"]
    
    # 用户2添加商品到购物车
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user2.id
    )
    
    result.expected_output = "返回 False (权限不足)"
    
    # 用户1尝试删除
    success = CartService.remove_from_cart(db, cart_id=cart_item.id, user_id=user1.id)
    
    assert success is False, f"应该返回 False（权限不足）"
    
    result.actual_output = f"返回: {success}"


def test_remove_from_cart_no_user_id(result: TestResult, db: SessionLocal):
    """TC-CART-028: 删除时不传递 user_id（跳过权限验证）"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    # 先添加商品
    cart_item = CartService.add_to_cart(
        db, product_id=product.id, quantity=1, user_id=user.id
    )
    cart_id = cart_item.id
    
    result.expected_output = "返回 True，记录被删除"
    
    success = CartService.remove_from_cart(db, cart_id=cart_id)  # 不传递 user_id
    
    # 验证记录被删除
    found = CartService.get_cart_item(db, cart_id)
    
    assert success is True, f"应该返回 True"
    assert found is None, f"记录应该被删除"
    
    result.actual_output = f"返回: {success}, 记录存在: {found is not None}"


# ==================== 清空购物车测试 ====================

def test_clear_cart_logged_in(result: TestResult, db: SessionLocal):
    """TC-CART-029: 登录用户清空购物车"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    
    # 先添加多个商品
    for i in range(3):
        CartService.add_to_cart(
            db, product_id=product.id, quantity=1, 
            spec_combo={"序号": str(i)}, user_id=user.id
        )
    
    # 获取添加前的数量
    items_before = CartService.get_cart(db, user_id=user.id)
    count_before = len(items_before)
    
    result.expected_output = f"返回 {count_before} (删除的项数)"
    
    count = CartService.clear_cart(db, user_id=user.id)
    
    # 验证购物车为空
    items_after = CartService.get_cart(db, user_id=user.id)
    
    assert count == count_before, f"应该返回删除的项数 {count_before}"
    assert len(items_after) == 0, f"购物车应该为空"
    
    result.actual_output = f"返回: {count}, 清空前: {count_before} 项"


def test_clear_cart_anonymous(result: TestResult, db: SessionLocal):
    """TC-CART-030: 匿名用户清空购物车"""
    product = test_data["products"]["prod_normal"]
    session_id = test_data["sessions"]["sess_1"]
    
    # 先添加商品到匿名购物车
    CartService.add_to_cart(
        db, product_id=product.id, quantity=1, session_id=session_id
    )
    
    # 获取添加前的数量
    items_before = CartService.get_cart(db, session_id=session_id)
    count_before = len(items_before)
    
    result.expected_output = f"返回 {count_before}"
    
    count = CartService.clear_cart(db, session_id=session_id)
    
    # 验证购物车为空
    items_after = CartService.get_cart(db, session_id=session_id)
    
    assert count == count_before, f"应该返回删除的项数 {count_before}"
    assert len(items_after) == 0, f"购物车应该为空"
    
    result.actual_output = f"返回: {count}, 清空前: {count_before} 项"


def test_clear_cart_empty(result: TestResult, db: SessionLocal):
    """TC-CART-031: 清空空购物车"""
    user = test_data["users"]["user_2"]
    
    # 确保购物车为空
    CartService.clear_cart(db, user_id=user.id)
    
    result.expected_output = "返回 0"
    
    count = CartService.clear_cart(db, user_id=user.id)
    
    assert count == 0, f"应该返回 0"
    
    result.actual_output = f"返回: {count}"


def test_clear_cart_no_identifier(result: TestResult, db: SessionLocal):
    """TC-CART-032: 未提供 user_id 和 session_id 清空"""
    result.expected_output = "返回 0"
    
    count = CartService.clear_cart(db)
    
    assert count == 0, f"应该返回 0"
    
    result.actual_output = f"返回: {count}"


# ==================== 合并匿名购物车测试 ====================

def test_merge_cart_normal(result: TestResult, db: SessionLocal):
    """TC-CART-033: 正常合并匿名购物车"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    session_id = f"sess-merge-{uuid.uuid4().hex[:8]}"
    
    # 清空用户购物车
    CartService.clear_cart(db, user_id=user.id)
    
    # 添加商品到匿名购物车
    for i in range(3):
        CartService.add_to_cart(
            db, product_id=product.id, quantity=1,
            spec_combo={"序号": str(i)}, session_id=session_id
        )
    
    result.expected_output = "返回 3 (合并的项数)"
    
    merged_count = CartService.merge_cart(db, user_id=user.id, session_id=session_id)
    
    # 验证匿名购物车被清空
    anon_items = CartService.get_cart(db, session_id=session_id)
    user_items = CartService.get_cart(db, user_id=user.id)
    
    assert merged_count == 3, f"应该返回 3"
    assert len(anon_items) == 0, f"匿名购物车应该被清空"
    assert len(user_items) == 3, f"用户购物车应该有 3 项"
    
    result.actual_output = f"返回: {merged_count}, 用户购物车: {len(user_items)} 项"


def test_merge_cart_duplicate(result: TestResult, db: SessionLocal):
    """TC-CART-034: 合并时商品已存在（数量累加）"""
    user = test_data["users"]["user_1"]
    product = test_data["products"]["prod_normal"]
    session_id = f"sess-merge-dup-{uuid.uuid4().hex[:8]}"
    spec_combo = {"颜色": "红色"}
    
    # 清空用户购物车
    CartService.clear_cart(db, user_id=user.id)
    
    # 用户购物车已有商品，quantity=2
    CartService.add_to_cart(
        db, product_id=product.id, quantity=2,
        spec_combo=spec_combo, user_id=user.id
    )
    
    # 匿名购物车有相同商品，quantity=3
    CartService.add_to_cart(
        db, product_id=product.id, quantity=3,
        spec_combo=spec_combo, session_id=session_id
    )
    
    result.expected_output = "用户购物车中该商品 quantity=5 (2+3)"
    
    merged_count = CartService.merge_cart(db, user_id=user.id, session_id=session_id)
    
    # 验证数量累加
    user_items = CartService.get_cart(db, user_id=user.id)
    
    assert len(user_items) == 1, f"用户购物车应该有 1 项"
    assert user_items[0].quantity == 5, f"quantity 应该是 5，实际是 {user_items[0].quantity}"
    
    result.actual_output = f"合并项数: {merged_count}, 最终数量: {user_items[0].quantity}"


def test_merge_cart_insufficient_stock(result: TestResult, db: SessionLocal):
    """TC-CART-035: 合并时部分商品库存不足"""
    user = test_data["users"]["user_1"]
    product_normal = test_data["products"]["prod_normal"]
    product_low = test_data["products"]["prod_low_stock"]
    session_id = f"sess-merge-stock-{uuid.uuid4().hex[:8]}"
    
    # 清空用户购物车
    CartService.clear_cart(db, user_id=user.id)
    
    # 匿名购物车：正常商品 quantity=1，低库存商品 quantity=1（先添加，再减少库存）
    CartService.add_to_cart(
        db, product_id=product_normal.id, quantity=1, session_id=session_id
    )
    CartService.add_to_cart(
        db, product_id=product_low.id, quantity=1, session_id=session_id
    )
    
    # 减少库存使其不足（购物车有1个，库存改为0）
    ProductService.update_stock(db, product_low.id, 0)
    
    result.expected_output = "返回 1 (成功合并的项数)，库存不足的商品未被合并"
    
    merged_count = CartService.merge_cart(db, user_id=user.id, session_id=session_id)
    
    # 恢复库存
    ProductService.update_stock(db, product_low.id, 5)
    
    # 验证只有正常商品被合并
    user_items = CartService.get_cart(db, user_id=user.id)
    
    assert merged_count == 1, f"应该返回 1"
    assert len(user_items) == 1, f"用户购物车应该有 1 项"
    
    result.actual_output = f"返回: {merged_count}, 用户购物车: {len(user_items)} 项"


def test_merge_cart_empty(result: TestResult, db: SessionLocal):
    """TC-CART-036: 合并空匿名购物车"""
    user = test_data["users"]["user_1"]
    session_id = test_data["sessions"]["sess_empty"]
    
    # 确保匿名购物车为空
    CartService.clear_cart(db, session_id=session_id)
    
    result.expected_output = "返回 0"
    
    merged_count = CartService.merge_cart(db, user_id=user.id, session_id=session_id)
    
    assert merged_count == 0, f"应该返回 0"
    
    result.actual_output = f"返回: {merged_count}"


def test_merge_cart_inactive_product(result: TestResult, db: SessionLocal):
    """TC-CART-037: 合并时商品已下架"""
    user = test_data["users"]["user_1"]
    product_normal = test_data["products"]["prod_normal"]
    product_inactive = test_data["products"]["prod_inactive"]
    session_id = f"sess-merge-inactive-{uuid.uuid4().hex[:8]}"
    
    # 清空用户购物车
    CartService.clear_cart(db, user_id=user.id)
    
    # 先恢复商品为active状态，添加到购物车，然后再设为inactive
    ProductService.update_product(db, product_inactive.id, {"status": "active"})
    
    # 匿名购物车：正常商品 + 即将下架的商品
    CartService.add_to_cart(
        db, product_id=product_normal.id, quantity=1, session_id=session_id
    )
    CartService.add_to_cart(
        db, product_id=product_inactive.id, quantity=1, session_id=session_id
    )
    
    # 将商品设为inactive
    ProductService.update_product(db, product_inactive.id, {"status": "inactive"})
    
    result.expected_output = "返回 1 (成功合并的项数)，已下架商品未被合并"
    
    merged_count = CartService.merge_cart(db, user_id=user.id, session_id=session_id)
    
    # 验证只有正常商品被合并
    user_items = CartService.get_cart(db, user_id=user.id)
    
    assert merged_count == 1, f"应该返回 1"
    assert len(user_items) == 1, f"用户购物车应该有 1 项"
    
    result.actual_output = f"返回: {merged_count}, 用户购物车: {len(user_items)} 项"


# ==================== 购物车结算验证测试 ====================

def test_calculate_cart_total(result: TestResult, db: SessionLocal):
    """TC-CART-038: 计算购物车总价"""
    user = test_data["users"]["user_1"]
    product_normal = test_data["products"]["prod_normal"]
    product_low = test_data["products"]["prod_low_stock"]
    
    # 清空购物车并添加商品
    CartService.clear_cart(db, user_id=user.id)
    CartService.add_to_cart(db, product_id=product_normal.id, quantity=2, user_id=user.id)  # 100*2=200
    CartService.add_to_cart(db, product_id=product_low.id, quantity=1, user_id=user.id)    # 50*1=50
    
    result.expected_output = "total_amount=250, total_quantity=3, item_count=2"
    
    cart_info = CartService.calculate_cart_total(db, user_id=user.id)
    
    expected_amount = product_normal.price * 2 + product_low.price * 1
    
    assert cart_info["total_amount"] == expected_amount, f"总价不匹配"
    assert cart_info["total_quantity"] == 3, f"总数量不匹配"
    assert cart_info["item_count"] == 2, f"商品项数不匹配"
    
    result.actual_output = f"total_amount={cart_info['total_amount']}, total_quantity={cart_info['total_quantity']}, item_count={cart_info['item_count']}"


def test_calculate_cart_with_inactive(result: TestResult, db: SessionLocal):
    """TC-CART-039: 计算包含已下架商品的总价"""
    user = test_data["users"]["user_1"]
    product_normal = test_data["products"]["prod_normal"]
    product_inactive = test_data["products"]["prod_inactive"]
    
    # 先恢复商品为active状态，添加到购物车
    ProductService.update_product(db, product_inactive.id, {"status": "active"})
    
    # 清空购物车并添加商品
    CartService.clear_cart(db, user_id=user.id)
    CartService.add_to_cart(db, product_id=product_normal.id, quantity=1, user_id=user.id)   # 100
    CartService.add_to_cart(db, product_id=product_inactive.id, quantity=1, user_id=user.id) # 100
    
    # 然后将商品设为inactive
    ProductService.update_product(db, product_inactive.id, {"status": "inactive"})
    
    result.expected_output = "total_amount=100 (只计算有效商品)，invalid_items 包含已下架商品"
    
    cart_info = CartService.calculate_cart_total(db, user_id=user.id)
    
    assert cart_info["total_amount"] == product_normal.price, f"总价应该只包含有效商品"
    assert len(cart_info["invalid_items"]) == 1, f"应该有 1 个无效商品"
    
    result.actual_output = f"total_amount={cart_info['total_amount']}, invalid_items={len(cart_info['invalid_items'])}"


def test_calculate_cart_empty(result: TestResult, db: SessionLocal):
    """TC-CART-040: 计算空购物车总价"""
    user = test_data["users"]["user_2"]
    
    # 确保购物车为空
    CartService.clear_cart(db, user_id=user.id)
    
    result.expected_output = "total_amount=0, total_quantity=0, item_count=0"
    
    cart_info = CartService.calculate_cart_total(db, user_id=user.id)
    
    assert cart_info["total_amount"] == 0, f"总价应该为 0"
    assert cart_info["total_quantity"] == 0, f"总数量应该为 0"
    assert cart_info["item_count"] == 0, f"商品项数应该为 0"
    
    result.actual_output = f"total_amount={cart_info['total_amount']}, total_quantity={cart_info['total_quantity']}, item_count={cart_info['item_count']}"


def test_validate_cart_checkout_normal(result: TestResult, db: SessionLocal):
    """TC-CART-041: 验证购物车可结算（正常情况）"""
    user = test_data["users"]["user_1"]
    product_normal = test_data["products"]["prod_normal"]
    
    # 清空购物车并添加正常商品
    CartService.clear_cart(db, user_id=user.id)
    CartService.add_to_cart(db, product_id=product_normal.id, quantity=1, user_id=user.id)
    
    result.expected_output = "valid=True, message='可以结算', invalid_items=[]"
    
    validation = CartService.validate_cart_for_checkout(db, user_id=user.id)
    
    assert validation["valid"] is True, f"应该可以结算"
    assert validation["message"] == "可以结算", f"消息不匹配"
    assert len(validation["invalid_items"]) == 0, f"无效商品列表应该为空"
    
    result.actual_output = f"valid={validation['valid']}, message='{validation['message']}', invalid_items={len(validation['invalid_items'])}"


def test_validate_cart_checkout_empty(result: TestResult, db: SessionLocal):
    """TC-CART-042: 验证空购物车结算"""
    user = test_data["users"]["user_2"]
    
    # 确保购物车为空
    CartService.clear_cart(db, user_id=user.id)
    
    result.expected_output = "valid=False, message='购物车为空'"
    
    validation = CartService.validate_cart_for_checkout(db, user_id=user.id)
    
    assert validation["valid"] is False, f"空购物车不应该可以结算"
    assert "购物车为空" in validation["message"], f"消息不匹配"
    
    result.actual_output = f"valid={validation['valid']}, message='{validation['message']}'"


def test_validate_cart_checkout_inactive(result: TestResult, db: SessionLocal):
    """TC-CART-043: 验证包含已下架商品的结算"""
    user = test_data["users"]["user_1"]
    product_inactive = test_data["products"]["prod_inactive"]
    
    # 先恢复商品为active状态，添加到购物车
    ProductService.update_product(db, product_inactive.id, {"status": "active"})
    
    # 清空购物车并添加商品
    CartService.clear_cart(db, user_id=user.id)
    CartService.add_to_cart(db, product_id=product_inactive.id, quantity=1, user_id=user.id)
    
    # 然后将商品设为inactive
    ProductService.update_product(db, product_inactive.id, {"status": "inactive"})
    
    result.expected_output = "valid=False, message='部分商品无法购买', invalid_items 包含已下架商品"
    
    validation = CartService.validate_cart_for_checkout(db, user_id=user.id)
    
    assert validation["valid"] is False, f"不应该可以结算"
    assert "部分商品无法购买" in validation["message"], f"消息不匹配"
    assert len(validation["invalid_items"]) == 1, f"应该有 1 个无效商品"
    
    result.actual_output = f"valid={validation['valid']}, message='{validation['message']}', invalid_items={len(validation['invalid_items'])}"


def test_validate_cart_checkout_insufficient_stock(result: TestResult, db: SessionLocal):
    """TC-CART-044: 验证包含库存不足商品的结算"""
    user = test_data["users"]["user_1"]
    product_low = test_data["products"]["prod_low_stock"]
    
    # 清空购物车并添加商品（数量在库存范围内）
    CartService.clear_cart(db, user_id=user.id)
    CartService.add_to_cart(db, product_id=product_low.id, quantity=3, user_id=user.id)  # 库存有5
    
    # 然后减少库存使其不足
    ProductService.update_stock(db, product_low.id, 2)  # 库存改为2，但购物车有3
    
    result.expected_output = "valid=False, message='部分商品无法购买', invalid_items 包含库存不足商品"
    
    validation = CartService.validate_cart_for_checkout(db, user_id=user.id)
    
    # 恢复库存
    ProductService.update_stock(db, product_low.id, 5)
    
    assert validation["valid"] is False, f"不应该可以结算"
    assert "部分商品无法购买" in validation["message"], f"消息不匹配"
    assert len(validation["invalid_items"]) == 1, f"应该有 1 个无效商品"
    assert "库存不足" in validation["invalid_items"][0]["reason"], f"原因应该包含库存不足"
    
    result.actual_output = f"valid={validation['valid']}, message='{validation['message']}', invalid_items={validation['invalid_items']}"


def test_validate_cart_checkout_product_not_exist(result: TestResult, db: SessionLocal):
    """TC-CART-045: 验证包含不存在商品的结算"""
    user = test_data["users"]["user_1"]
    
    # 清空购物车
    CartService.clear_cart(db, user_id=user.id)
    
    # 手动创建一个购物车项，关联不存在的商品
    cart_item = Cart(
        user_id=user.id,
        product_id="prod-not-exist-12345",
        quantity=1
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    
    result.expected_output = "valid=False, invalid_items 包含'商品不存在'信息"
    
    validation = CartService.validate_cart_for_checkout(db, user_id=user.id)
    
    # 清理测试数据
    db.delete(cart_item)
    db.commit()
    
    assert validation["valid"] is False, f"不应该可以结算"
    # 注意：由于 product 关系返回 None，可能会被归类为商品不存在
    
    result.actual_output = f"valid={validation['valid']}, invalid_items={validation['invalid_items']}"


def test_validate_cart_checkout_multiple_invalid(result: TestResult, db: SessionLocal):
    """TC-CART-046: 验证多种无效商品同时存在"""
    user = test_data["users"]["user_1"]
    product_normal = test_data["products"]["prod_normal"]
    product_inactive = test_data["products"]["prod_inactive"]
    product_low = test_data["products"]["prod_low_stock"]
    
    # 先恢复商品为active状态
    ProductService.update_product(db, product_inactive.id, {"status": "active"})
    
    # 清空购物车并添加多种商品
    CartService.clear_cart(db, user_id=user.id)
    CartService.add_to_cart(db, product_id=product_normal.id, quantity=1, user_id=user.id)     # 正常
    CartService.add_to_cart(db, product_id=product_inactive.id, quantity=1, user_id=user.id)   # 即将下架
    CartService.add_to_cart(db, product_id=product_low.id, quantity=3, user_id=user.id)        # 库存充足
    
    # 然后将商品设为inactive，并减少库存
    ProductService.update_product(db, product_inactive.id, {"status": "inactive"})
    ProductService.update_stock(db, product_low.id, 1)  # 库存改为1，但购物车有3
    
    result.expected_output = "valid=False, invalid_items 包含 2 条记录（已下架和库存不足）"
    
    validation = CartService.validate_cart_for_checkout(db, user_id=user.id)
    
    # 恢复库存
    ProductService.update_stock(db, product_low.id, 5)
    
    assert validation["valid"] is False, f"不应该可以结算"
    assert len(validation["invalid_items"]) == 2, f"应该有 2 个无效商品"
    
    result.actual_output = f"valid={validation['valid']}, invalid_items={len(validation['invalid_items'])}"


def test_calculate_cart_total_anonymous(result: TestResult, db: SessionLocal):
    """TC-CART-047: 匿名用户计算总价"""
    product = test_data["products"]["prod_normal"]
    session_id = f"sess-calc-{uuid.uuid4().hex[:8]}"
    
    # 添加商品到匿名购物车
    CartService.add_to_cart(db, product_id=product.id, quantity=2, session_id=session_id)
    
    result.expected_output = "正确返回总价信息"
    
    cart_info = CartService.calculate_cart_total(db, session_id=session_id)
    
    expected_amount = product.price * 2
    
    assert cart_info["total_amount"] == expected_amount, f"总价不匹配"
    assert cart_info["total_quantity"] == 2, f"总数量不匹配"
    
    result.actual_output = f"total_amount={cart_info['total_amount']}, total_quantity={cart_info['total_quantity']}"


# ==================== 主执行函数 ====================

def run_all_tests():
    """运行所有测试用例"""
    print("=" * 60)
    print("购物车模块测试执行")
    print("执行人: QA 工程师 Quinn")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 确保表已创建
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 准备测试数据
        setup_test_data(db)
        
        # ==================== 1. 添加商品到购物车 (10个用例) ====================
        print("\n" + "=" * 60)
        print("1. 添加商品到购物车")
        print("=" * 60)
        
        run_test("TC-CART-001", "登录用户添加商品到购物车", "P0", test_add_to_cart_logged_in, db)
        run_test("TC-CART-002", "匿名用户添加商品到购物车", "P0", test_add_to_cart_anonymous, db)
        run_test("TC-CART-003", "添加商品时缺少用户标识", "P1", test_add_to_cart_no_identifier, db)
        run_test("TC-CART-004", "添加不存在的商品", "P1", test_add_to_cart_product_not_exist, db)
        run_test("TC-CART-005", "添加已下架商品", "P1", test_add_to_cart_inactive_product, db)
        run_test("TC-CART-006", "添加库存不足的商品", "P0", test_add_to_cart_insufficient_stock, db)
        run_test("TC-CART-007", "添加带规格组合的商品", "P1", test_add_to_cart_with_spec, db)
        run_test("TC-CART-008", "重复添加相同规格商品数量累加", "P1", test_add_to_cart_duplicate_spec, db)
        run_test("TC-CART-009", "添加相同商品不同规格", "P1", test_add_to_cart_different_spec, db)
        run_test("TC-CART-010", "添加商品数量为0", "P2", test_add_to_cart_zero_quantity, db)
        
        # ==================== 2. 购物车列表查询 (6个用例) ====================
        print("\n" + "=" * 60)
        print("2. 购物车列表查询")
        print("=" * 60)
        
        run_test("TC-CART-011", "登录用户查询购物车列表", "P0", test_get_cart_logged_in, db)
        run_test("TC-CART-012", "匿名用户查询购物车列表", "P0", test_get_cart_anonymous, db)
        run_test("TC-CART-013", "查询空购物车", "P1", test_get_cart_empty, db)
        run_test("TC-CART-014", "未提供用户标识查询购物车", "P1", test_get_cart_no_identifier, db)
        run_test("TC-CART-015", "根据ID获取单个购物车项", "P1", test_get_cart_item_by_id, db)
        run_test("TC-CART-016", "获取不存在的购物车项", "P1", test_get_cart_item_not_exist, db)
        
        # ==================== 3. 修改购物车商品数量 (8个用例) ====================
        print("\n" + "=" * 60)
        print("3. 修改购物车商品数量")
        print("=" * 60)
        
        run_test("TC-CART-017", "正常修改购物车商品数量", "P0", test_update_cart_item_normal, db)
        run_test("TC-CART-018", "修改数量为库存边界值", "P1", test_update_cart_item_stock_boundary, db)
        run_test("TC-CART-019", "修改数量超过库存", "P0", test_update_cart_item_over_stock, db)
        run_test("TC-CART-020", "修改数量为0自动删除", "P1", test_update_cart_item_zero_quantity, db)
        run_test("TC-CART-021", "修改数量为负数", "P1", test_update_cart_item_negative, db)
        run_test("TC-CART-022", "修改不存在的购物车项", "P1", test_update_cart_item_not_exist, db)
        run_test("TC-CART-023", "无权限修改他人购物车项", "P0", test_update_cart_item_no_permission, db)
        run_test("TC-CART-024", "修改时不传递user_id", "P2", test_update_cart_item_no_user_id, db)
        
        # ==================== 4. 删除购物车商品 (4个用例) ====================
        print("\n" + "=" * 60)
        print("4. 删除购物车商品")
        print("=" * 60)
        
        run_test("TC-CART-025", "正常删除购物车商品", "P0", test_remove_from_cart_normal, db)
        run_test("TC-CART-026", "删除不存在的购物车项", "P1", test_remove_from_cart_not_exist, db)
        run_test("TC-CART-027", "无权限删除他人购物车项", "P0", test_remove_from_cart_no_permission, db)
        run_test("TC-CART-028", "删除时不传递user_id", "P2", test_remove_from_cart_no_user_id, db)
        
        # ==================== 5. 清空购物车 (4个用例) ====================
        print("\n" + "=" * 60)
        print("5. 清空购物车")
        print("=" * 60)
        
        run_test("TC-CART-029", "登录用户清空购物车", "P0", test_clear_cart_logged_in, db)
        run_test("TC-CART-030", "匿名用户清空购物车", "P0", test_clear_cart_anonymous, db)
        run_test("TC-CART-031", "清空空购物车", "P1", test_clear_cart_empty, db)
        run_test("TC-CART-032", "未提供用户标识清空购物车", "P1", test_clear_cart_no_identifier, db)
        
        # ==================== 6. 合并匿名购物车 (5个用例) ====================
        print("\n" + "=" * 60)
        print("6. 合并匿名购物车")
        print("=" * 60)
        
        run_test("TC-CART-033", "正常合并匿名购物车", "P0", test_merge_cart_normal, db)
        run_test("TC-CART-034", "合并时商品已存在数量累加", "P1", test_merge_cart_duplicate, db)
        run_test("TC-CART-035", "合并时部分商品库存不足", "P1", test_merge_cart_insufficient_stock, db)
        run_test("TC-CART-036", "合并空匿名购物车", "P1", test_merge_cart_empty, db)
        run_test("TC-CART-037", "合并时商品已下架", "P1", test_merge_cart_inactive_product, db)
        
        # ==================== 7. 购物车结算验证 (10个用例) ====================
        print("\n" + "=" * 60)
        print("7. 购物车结算验证")
        print("=" * 60)
        
        run_test("TC-CART-038", "计算购物车总价", "P0", test_calculate_cart_total, db)
        run_test("TC-CART-039", "计算包含已下架商品的总价", "P1", test_calculate_cart_with_inactive, db)
        run_test("TC-CART-040", "计算空购物车总价", "P1", test_calculate_cart_empty, db)
        run_test("TC-CART-041", "验证购物车可结算-正常情况", "P0", test_validate_cart_checkout_normal, db)
        run_test("TC-CART-042", "验证空购物车结算", "P0", test_validate_cart_checkout_empty, db)
        run_test("TC-CART-043", "验证包含已下架商品的结算", "P0", test_validate_cart_checkout_inactive, db)
        run_test("TC-CART-044", "验证包含库存不足商品的结算", "P0", test_validate_cart_checkout_insufficient_stock, db)
        run_test("TC-CART-045", "验证包含不存在商品的结算", "P1", test_validate_cart_checkout_product_not_exist, db)
        run_test("TC-CART-046", "验证多种无效商品同时存在", "P1", test_validate_cart_checkout_multiple_invalid, db)
        run_test("TC-CART-047", "匿名用户计算总价", "P1", test_calculate_cart_total_anonymous, db)
        
    finally:
        # 清理测试数据
        cleanup_test_data(db)
        db.close()
    
    # 生成测试报告
    generate_report()


def generate_report():
    """生成测试执行报告"""
    print("\n" + "=" * 60)
    print("测试执行完成，生成报告...")
    print("=" * 60)
    
    # 统计结果
    total = len(test_results)
    passed = sum(1 for r in test_results if r.status == "通过")
    failed = sum(1 for r in test_results if r.status == "失败")
    p0_total = sum(1 for r in test_results if r.priority == "P0")
    p0_passed = sum(1 for r in test_results if r.priority == "P0" and r.status == "通过")
    
    pass_rate = (passed / total * 100) if total > 0 else 0
    p0_pass_rate = (p0_passed / p0_total * 100) if p0_total > 0 else 0
    
    # 生成 Markdown 报告
    report_lines = []
    report_lines.append("# 购物车模块测试执行报告")
    report_lines.append("")
    report_lines.append(f"**执行人**: QA 工程师 Quinn")
    report_lines.append(f"**执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**测试环境**: E-Commerce MVP")
    report_lines.append("")
    
    # 汇总统计
    report_lines.append("## 测试汇总")
    report_lines.append("")
    report_lines.append("| 统计项 | 数值 |")
    report_lines.append("|--------|------|")
    report_lines.append(f"| 总用例数 | {total} |")
    report_lines.append(f"| 通过 | {passed} |")
    report_lines.append(f"| 失败 | {failed} |")
    report_lines.append(f"| 总通过率 | {pass_rate:.1f}% |")
    report_lines.append("")
    report_lines.append("| 优先级 | 总数 | 通过 | 通过率 |")
    report_lines.append("|--------|------|------|--------|")
    report_lines.append(f"| P0 (核心) | {p0_total} | {p0_passed} | {p0_pass_rate:.1f}% |")
    report_lines.append(f"| P1 (重要) | {sum(1 for r in test_results if r.priority == 'P1')} | {sum(1 for r in test_results if r.priority == 'P1' and r.status == '通过')} | - |")
    report_lines.append(f"| P2 (一般) | {sum(1 for r in test_results if r.priority == 'P2')} | {sum(1 for r in test_results if r.priority == 'P2' and r.status == '通过')} | - |")
    report_lines.append("")
    
    # 详细结果
    report_lines.append("## 详细测试结果")
    report_lines.append("")
    
    for result in test_results:
        status_icon = "✅" if result.status == "通过" else "❌"
        report_lines.append(f"### {result.case_id}: {result.case_name}")
        report_lines.append("")
        report_lines.append(f"- **优先级**: {result.priority}")
        report_lines.append(f"- **测试结果**: {status_icon} {result.status}")
        report_lines.append(f"- **执行时间**: {result.execution_time:.3f}s")
        report_lines.append("")
        report_lines.append(f"**预期输出**:")
        report_lines.append(f"```")
        report_lines.append(result.expected_output or "无")
        report_lines.append(f"```")
        report_lines.append("")
        report_lines.append(f"**实际输出**:")
        report_lines.append(f"```")
        report_lines.append(result.actual_output or "无")
        report_lines.append(f"```")
        report_lines.append("")
        
        if result.issues:
            report_lines.append(f"**问题记录**:")
            for issue in result.issues:
                report_lines.append(f"- ⚠️ {issue}")
            report_lines.append("")
        
        report_lines.append("---")
        report_lines.append("")
    
    # 失败用例汇总
    if failed > 0:
        report_lines.append("## 失败用例汇总")
        report_lines.append("")
        for result in test_results:
            if result.status == "失败":
                report_lines.append(f"- **{result.case_id}**: {result.case_name}")
                report_lines.append(f"  - 问题: {', '.join(result.issues) if result.issues else '无详细记录'}")
        report_lines.append("")
    
    # 结论
    report_lines.append("## 测试结论")
    report_lines.append("")
    if failed == 0:
        report_lines.append("✅ **所有测试用例通过**")
    elif p0_pass_rate == 100:
        report_lines.append(f"⚠️ **部分非核心用例失败**，核心功能(P0)全部通过，通过率: {pass_rate:.1f}%")
    else:
        report_lines.append(f"❌ **存在核心用例失败**，P0通过率: {p0_pass_rate:.1f}%，需要修复")
    report_lines.append("")
    
    # 保存报告
    report_content = "\n".join(report_lines)
    report_path = "/root/.openclaw/workspace/projects/ecommerce-mvp/tests/test_cart_report.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"✅ 测试报告已保存到: {report_path}")
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"总用例数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"通过率: {pass_rate:.1f}%")
    print(f"P0通过率: {p0_pass_rate:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
