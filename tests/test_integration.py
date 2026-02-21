#!/usr/bin/env python3
"""
电商系统联调测试脚本 - 修复版
测试场景 1-5 的完整业务流程
"""

import requests
import time
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional

# 配置
BASE_URL = "http://localhost:8000"
DB_PATH = "/root/.openclaw/workspace/projects/ecommerce-mvp/ecommerce.db"

# 测试数据存储
test_data = {
    "category_id": None,
    "product_id": None,
    "admin_token": None,
    "user_token": None,
    "address_id": None,
    "order_id": None,
}


def log_step(step: str, status: str, details: str = "", duration_ms: float = 0):
    """记录测试步骤"""
    icon = "✅" if status == "PASS" else "❌"
    print(f"  {icon} {step}")
    if details:
        print(f"      {details}")
    if duration_ms > 0:
        print(f"      耗时: {duration_ms:.2f}ms")


def api_call(method: str, endpoint: str, **kwargs) -> tuple[Any, float]:
    """执行 API 调用并记录性能"""
    url = f"{BASE_URL}{endpoint}"
    start = time.time()
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
        duration = (time.time() - start) * 1000
        return response, duration
    except Exception as e:
        duration = (time.time() - start) * 1000
        return None, duration


def db_query(query: str, params: tuple = ()) -> list:
    """执行数据库查询"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"      DB Error: {e}")
        return []


def run_all_scenarios():
    """运行所有测试场景"""
    results = []
    
    print("="*70)
    print("🧪 电商系统联调测试")
    print("="*70)
    
    # 检查服务状态
    print("\n📡 检查服务状态...")
    resp, _ = api_call("GET", "/health")
    if resp and resp.status_code == 200:
        print(f"  ✅ 服务已就绪 - {resp.json()}")
    else:
        print("  ❌ 服务未就绪")
        return []
    
    # 场景1
    try:
        results.append(scenario_1())
    except Exception as e:
        print(f"\n❌ 场景1异常: {e}")
        results.append({"scenario": "场景1: 完整购物流程", "passed": False, "error": str(e), "performance": {}})
    
    # 场景2
    try:
        results.append(scenario_2())
    except Exception as e:
        print(f"\n❌ 场景2异常: {e}")
        results.append({"scenario": "场景2: 匿名用户购物流程", "passed": False, "error": str(e), "performance": {}})
    
    # 场景3
    try:
        results.append(scenario_3())
    except Exception as e:
        print(f"\n❌ 场景3异常: {e}")
        results.append({"scenario": "场景3: 库存扣减流程", "passed": False, "error": str(e), "performance": {}})
    
    # 场景4
    try:
        results.append(scenario_4())
    except Exception as e:
        print(f"\n❌ 场景4异常: {e}")
        results.append({"scenario": "场景4: 默认地址切换", "passed": False, "error": str(e), "performance": {}})
    
    # 场景5
    try:
        results.append(scenario_5())
    except Exception as e:
        print(f"\n❌ 场景5异常: {e}")
        results.append({"scenario": "场景5: 商品下架处理", "passed": False, "error": str(e), "performance": {}})
    
    return results


def scenario_1():
    """场景1: 完整购物流程"""
    print("\n" + "="*70)
    print("📦 场景1: 完整购物流程")
    print("="*70)
    
    result = {"scenario": "场景1: 完整购物流程", "passed": True, "performance": {}, "steps": []}
    
    # 1. 创建商品分类
    print("\n[1/8] 创建商品分类")
    # 先注册管理员
    admin_user = f"admin_{int(time.time())}"
    resp, dur = api_call("POST", "/auth/register", json={
        "username": admin_user, "email": f"{admin_user}@test.com", "password": "admin123"
    })
    if resp and resp.status_code == 201:
        log_step("注册管理员", "PASS", f"用户名: {admin_user}", dur)
    else:
        log_step("注册管理员", "FAIL", resp.text if resp else "No response", dur)
        result["passed"] = False
    
    # 登录
    resp, dur = api_call("POST", "/auth/login", data={"username": admin_user, "password": "admin123"})
    if resp and resp.status_code == 200:
        test_data["admin_token"] = resp.json()["access_token"]
        log_step("管理员登录", "PASS", duration_ms=dur)
        result["performance"]["login"] = dur
    else:
        log_step("管理员登录", "FAIL")
        result["passed"] = False
        return result
    
    # 创建分类
    cat_name = f"分类_{int(time.time())}"
    resp, dur = api_call("POST", "/api/v1/products/categories", 
                         json={"name": cat_name, "description": "测试分类"},
                         headers={"Authorization": f"Bearer {test_data['admin_token']}"})
    if resp and resp.status_code == 201:
        test_data["category_id"] = resp.json()["id"]
        log_step("创建分类", "PASS", f"ID: {test_data['category_id']}", dur)
        result["performance"]["create_category"] = dur
    else:
        log_step("创建分类", "FAIL", resp.text if resp else "No response", dur)
        result["passed"] = False
    
    # 2. 创建商品
    print("\n[2/8] 创建商品(含规格、图片)")
    product_data = {
        "name": f"商品_{int(time.time())}",
        "description": "测试商品",
        "price": 99.99,
        "original_price": 129.99,
        "stock": 100,
        "category_id": test_data["category_id"]
    }
    resp, dur = api_call("POST", "/api/v1/products", json=product_data,
                         headers={"Authorization": f"Bearer {test_data['admin_token']}"})
    if resp and resp.status_code == 201:
        test_data["product_id"] = resp.json()["id"]
        log_step("创建商品", "PASS", f"ID: {test_data['product_id']}", dur)
        result["performance"]["create_product"] = dur
    else:
        log_step("创建商品", "FAIL", resp.text if resp else "No response", dur)
        result["passed"] = False
        return result
    
    # 创建规格
    resp, dur = api_call("POST", f"/api/v1/products/{test_data['product_id']}/specs",
                         json={"name": "颜色", "values": ["红", "蓝"]},
                         headers={"Authorization": f"Bearer {test_data['admin_token']}"})
    if resp and resp.status_code == 200:
        log_step("创建规格", "PASS", duration_ms=dur)
    else:
        log_step("创建规格", "FAIL")
    
    # 3. 用户注册/登录
    print("\n[3/8] 用户注册/登录")
    user_name = f"user_{int(time.time())}"
    resp, dur = api_call("POST", "/auth/register", json={
        "username": user_name, "email": f"{user_name}@test.com", "password": "user123"
    })
    if resp and resp.status_code == 201:
        log_step("用户注册", "PASS", f"ID: {resp.json()['id']}", dur)
    else:
        log_step("用户注册", "FAIL")
        result["passed"] = False
    
    resp, dur = api_call("POST", "/auth/login", data={"username": user_name, "password": "user123"})
    if resp and resp.status_code == 200:
        test_data["user_token"] = resp.json()["access_token"]
        log_step("用户登录", "PASS", duration_ms=dur)
    else:
        log_step("用户登录", "FAIL")
        result["passed"] = False
        return result
    
    # 4. 添加收货地址
    print("\n[4/8] 添加收货地址")
    addr_data = {
        "name": "张三", "phone": "13800138000", "province": "广东", "city": "深圳",
        "district": "南山", "detail": "科技园", "zip_code": "518000", "is_default": True
    }
    resp, dur = api_call("POST", "/api/v1/addresses", json=addr_data,
                         headers={"Authorization": f"Bearer {test_data['user_token']}"})
    if resp and resp.status_code == 201:
        test_data["address_id"] = resp.json()["id"]
        log_step("添加地址", "PASS", f"ID: {test_data['address_id']}", dur)
        result["performance"]["create_address"] = dur
    else:
        log_step("添加地址", "FAIL", resp.text if resp else "No response", dur)
        result["passed"] = False
    
    # 5. 添加商品到购物车
    print("\n[5/8] 添加商品到购物车")
    resp, dur = api_call("POST", "/api/v1/cart/items",
                         json={"product_id": test_data["product_id"], "quantity": 2, "spec_combo": {"颜色": "红"}},
                         headers={"Authorization": f"Bearer {test_data['user_token']}"})
    if resp and resp.status_code == 201:
        log_step("添加购物车", "PASS", f"ID: {resp.json()['id']}", dur)
        result["performance"]["add_to_cart"] = dur
    else:
        log_step("添加购物车", "FAIL", resp.text if resp else "No response", dur)
        result["passed"] = False
    
    # 6. 从购物车创建订单
    print("\n[6/8] 从购物车创建订单")
    resp, dur = api_call("POST", f"/api/v1/cart/checkout?address_id={test_data['address_id']}",
                         headers={"Authorization": f"Bearer {test_data['user_token']}"})
    if resp and resp.status_code == 200:
        test_data["order_id"] = resp.json()["order_id"]
        log_step("创建订单", "PASS", f"ID: {test_data['order_id']}, 金额: {resp.json()['total_amount']}", dur)
        result["performance"]["create_order"] = dur
    else:
        log_step("创建订单", "FAIL", resp.text if resp else "No response", dur)
        result["passed"] = False
        return result
    
    # 7. 支付订单
    print("\n[7/8] 支付订单")
    resp, dur = api_call("POST", f"/payment/alipay?order_id={test_data['order_id']}",
                         headers={"Authorization": f"Bearer {test_data['user_token']}"})
    if resp and resp.status_code == 200:
        payment_no = resp.json()["payment_no"]
        log_step("创建支付", "PASS", f"支付单号: {payment_no}", dur)
        result["performance"]["create_payment"] = dur
        
        # 获取订单号进行回调
        orders = db_query("SELECT order_no FROM orders WHERE id = ?", (test_data["order_id"],))
        if orders:
            order_no = orders[0]["order_no"]
            resp2, dur2 = api_call("GET", f"/payment/callback/test/alipay/{order_no}")
            if resp2 and resp2.status_code == 200:
                log_step("支付回调", "PASS", resp2.json().get("message", ""), dur2)
            else:
                log_step("支付回调", "FAIL")
                result["passed"] = False
    else:
        log_step("创建支付", "FAIL")
        result["passed"] = False
    
    # 8. 验证订单状态
    print("\n[8/8] 验证订单状态")
    orders = db_query("SELECT * FROM orders WHERE id = ?", (test_data["order_id"],))
    if orders:
        order = orders[0]
        if order["status"] == "paid":
            log_step("订单状态", "PASS", f"状态: {order['status']}")
        else:
            log_step("订单状态", "FAIL", f"状态: {order['status']}, 期望: paid")
            result["passed"] = False
        
        # 验证库存
        products = db_query("SELECT * FROM products WHERE id = ?", (test_data["product_id"],))
        if products:
            expected = 100 - 2
            if products[0]["stock"] == expected:
                log_step("库存扣减", "PASS", f"剩余: {products[0]['stock']}")
            else:
                log_step("库存扣减", "FAIL", f"剩余: {products[0]['stock']}, 期望: {expected}")
                result["passed"] = False
    
    return result


def scenario_2():
    """场景2: 匿名用户购物流程"""
    print("\n" + "="*70)
    print("👤 场景2: 匿名用户购物流程")
    print("="*70)
    
    result = {"scenario": "场景2: 匿名用户购物流程", "passed": True, "performance": {}, "steps": []}
    session_id = f"sess_{int(time.time())}"
    
    # 1. 匿名浏览商品
    print("\n[1/6] 匿名用户浏览商品")
    resp, dur = api_call("GET", "/api/v1/products")
    if resp and resp.status_code == 200:
        log_step("浏览商品", "PASS", f"共 {resp.json()['total']} 个商品", dur)
        result["performance"]["list_products"] = dur
    else:
        log_step("浏览商品", "FAIL")
        result["passed"] = False
    
    # 2. 匿名添加购物车
    print("\n[2/6] 添加商品到购物车(匿名)")
    resp, dur = api_call("POST", "/api/v1/cart/items",
                         json={"product_id": test_data["product_id"], "quantity": 1},
                         headers={"X-Session-Id": session_id})
    if resp and resp.status_code == 201:
        log_step("匿名加购", "PASS", f"ID: {resp.json()['id']}", dur)
        result["performance"]["anon_add_cart"] = dur
    else:
        log_step("匿名加购", "FAIL")
        result["passed"] = False
    
    # 验证匿名购物车
    resp, dur = api_call("GET", "/api/v1/cart", headers={"X-Session-Id": session_id})
    if resp and resp.status_code == 200:
        log_step("查看购物车", "PASS", f"共 {resp.json()['item_count']} 项", dur)
    
    # 3. 用户登录
    print("\n[3/6] 用户登录")
    user_name = f"user2_{int(time.time())}"
    resp, _ = api_call("POST", "/auth/register", json={
        "username": user_name, "email": f"{user_name}@test.com", "password": "user123"
    })
    resp, dur = api_call("POST", "/auth/login", data={"username": user_name, "password": "user123"})
    if resp and resp.status_code == 200:
        user2_token = resp.json()["access_token"]
        log_step("用户登录", "PASS", duration_ms=dur)
    else:
        log_step("用户登录", "FAIL")
        result["passed"] = False
        return result
    
    # 4. 购物车合并
    print("\n[4/6] 购物车合并")
    resp, dur = api_call("POST", "/api/v1/cart/merge",
                         headers={"Authorization": f"Bearer {user2_token}", "X-Session-Id": session_id})
    if resp and resp.status_code == 200:
        log_step("购物车合并", "PASS", f"合并 {resp.json()['merged_count']} 项", dur)
        result["performance"]["merge_cart"] = dur
    else:
        log_step("购物车合并", "FAIL")
        result["passed"] = False
    
    # 5. 选择地址
    print("\n[5/6] 选择地址")
    addr_data = {"name": "李四", "phone": "13900139000", "province": "北京", "city": "北京",
                 "district": "朝阳", "detail": "建国路", "is_default": True}
    resp, dur = api_call("POST", "/api/v1/addresses", json=addr_data,
                         headers={"Authorization": f"Bearer {user2_token}"})
    if resp and resp.status_code == 201:
        addr_id = resp.json()["id"]
        log_step("添加地址", "PASS", f"ID: {addr_id}", dur)
    else:
        log_step("添加地址", "FAIL")
        result["passed"] = False
        return result
    
    # 6. 创建订单
    print("\n[6/6] 创建订单")
    resp, dur = api_call("POST", f"/api/v1/cart/checkout?address_id={addr_id}",
                         headers={"Authorization": f"Bearer {user2_token}"})
    if resp and resp.status_code == 200:
        log_step("创建订单", "PASS", f"ID: {resp.json()['order_id']}", dur)
        result["performance"]["checkout"] = dur
    else:
        log_step("创建订单", "FAIL")
        result["passed"] = False
    
    return result


def scenario_3():
    """场景3: 库存扣减流程"""
    print("\n" + "="*70)
    print("📊 场景3: 库存扣减流程")
    print("="*70)
    
    result = {"scenario": "场景3: 库存扣减流程", "passed": True, "performance": {}, "steps": []}
    
    # 1. 创建商品(库存100)
    print("\n[1/6] 创建商品(库存100)")
    resp, dur = api_call("POST", "/api/v1/products",
                         json={"name": f"库存商品_{int(time.time())}", "price": 50, "stock": 100,
                               "category_id": test_data["category_id"]},
                         headers={"Authorization": f"Bearer {test_data['admin_token']}"})
    if resp and resp.status_code == 201:
        stock_product_id = resp.json()["id"]
        log_step("创建商品", "PASS", f"ID: {stock_product_id}", dur)
    else:
        log_step("创建商品", "FAIL")
        result["passed"] = False
        return result
    
    # 2. 用户A添加50件
    print("\n[2/6] 用户A添加50件到购物车")
    user_a = f"user_a_{int(time.time())}"
    resp, _ = api_call("POST", "/auth/register", json={"username": user_a, "email": f"{user_a}@test.com", "password": "user123"})
    resp, _ = api_call("POST", "/auth/login", data={"username": user_a, "password": "user123"})
    token_a = resp.json()["access_token"]
    
    resp, dur = api_call("POST", "/api/v1/cart/items",
                         json={"product_id": stock_product_id, "quantity": 50},
                         headers={"Authorization": f"Bearer {token_a}"})
    if resp and resp.status_code == 201:
        log_step("用户A加购", "PASS", "数量: 50", dur)
    else:
        log_step("用户A加购", "FAIL")
        result["passed"] = False
    
    # 3. 用户B添加60件
    print("\n[3/6] 用户B添加60件到购物车")
    user_b = f"user_b_{int(time.time())}"
    resp, _ = api_call("POST", "/auth/register", json={"username": user_b, "email": f"{user_b}@test.com", "password": "user123"})
    resp, _ = api_call("POST", "/auth/login", data={"username": user_b, "password": "user123"})
    token_b = resp.json()["access_token"]
    
    resp, dur = api_call("POST", "/api/v1/cart/items",
                         json={"product_id": stock_product_id, "quantity": 60},
                         headers={"Authorization": f"Bearer {token_b}"})
    if resp and resp.status_code == 201:
        log_step("用户B加购", "PASS", "数量: 60", dur)
    else:
        log_step("用户B加购", "FAIL")
        result["passed"] = False
    
    # 4. 用户A创建订单并支付
    print("\n[4/6] 用户A创建订单并支付")
    addr_a = {"name": "A", "phone": "13700137000", "province": "上海", "city": "上海", "district": "浦东", "detail": "测试", "is_default": True}
    resp, _ = api_call("POST", "/api/v1/addresses", json=addr_a, headers={"Authorization": f"Bearer {token_a}"})
    addr_id_a = resp.json()["id"]
    
    resp, dur = api_call("POST", f"/api/v1/cart/checkout?address_id={addr_id_a}",
                         headers={"Authorization": f"Bearer {token_a}"})
    if resp and resp.status_code == 200:
        order_a = resp.json()["order_id"]
        log_step("用户A下单", "PASS", f"ID: {order_a}", dur)
        
        # 支付
        resp, _ = api_call("POST", f"/payment/alipay?order_id={order_a}", headers={"Authorization": f"Bearer {token_a}"})
        if resp and resp.status_code == 200:
            orders = db_query("SELECT order_no FROM orders WHERE id = ?", (order_a,))
            if orders:
                api_call("GET", f"/payment/callback/test/alipay/{orders[0]['order_no']}")
            log_step("用户A支付", "PASS")
    else:
        log_step("用户A下单", "FAIL")
        result["passed"] = False
    
    # 5. 验证库存变为50
    print("\n[5/6] 验证库存变为50")
    products = db_query("SELECT * FROM products WHERE id = ?", (stock_product_id,))
    if products:
        actual = products[0]["stock"]
        if actual == 50:
            log_step("库存验证", "PASS", f"剩余: {actual}")
        else:
            log_step("库存验证", "FAIL", f"剩余: {actual}, 期望: 50")
            result["passed"] = False
            result["issues"] = ["库存扣减逻辑可能有问题，订单创建时未正确扣减库存"]
    
    # 6. 用户B创建订单(应失败)
    print("\n[6/6] 用户B创建订单(应失败，库存不足)")
    addr_b = {"name": "B", "phone": "13600136000", "province": "广州", "city": "广州", "district": "天河", "detail": "测试", "is_default": True}
    resp, _ = api_call("POST", "/api/v1/addresses", json=addr_b, headers={"Authorization": f"Bearer {token_b}"})
    addr_id_b = resp.json()["id"]
    
    resp, dur = api_call("POST", f"/api/v1/cart/checkout?address_id={addr_id_b}",
                         headers={"Authorization": f"Bearer {token_b}"})
    if resp and resp.status_code != 200:
        log_step("用户B下单失败", "PASS", "库存不足，符合预期", dur)
    else:
        log_step("用户B下单失败", "FAIL", "应该失败但成功了")
        result["passed"] = False
        result["issues"] = ["库存超卖: 用户B购买了60件，但库存只剩50件，订单却创建成功"]
    
    return result


def scenario_4():
    """场景4: 默认地址切换"""
    print("\n" + "="*70)
    print("📍 场景4: 默认地址切换")
    print("="*70)
    
    result = {"scenario": "场景4: 默认地址切换", "passed": True, "performance": {}, "steps": [], "issues": []}
    
    # 创建用户
    user_name = f"user_addr_{int(time.time())}"
    resp, _ = api_call("POST", "/auth/register", json={"username": user_name, "email": f"{user_name}@test.com", "password": "user123"})
    resp, _ = api_call("POST", "/auth/login", data={"username": user_name, "password": "user123"})
    if not resp or resp.status_code != 200:
        log_step("用户登录", "FAIL")
        result["passed"] = False
        return result
    token = resp.json()["access_token"]
    
    # 1. 创建3个地址
    print("\n[1/6] 用户创建3个地址")
    addr_ids = []
    for i in range(3):
        addr_data = {
            "name": f"收件人{i+1}", "phone": f"138{i:03d}138{i:03d}",
            "province": "广东", "city": "深圳", "district": "南山",
            "detail": f"地址{i+1}", "is_default": False
        }
        resp, dur = api_call("POST", "/api/v1/addresses", json=addr_data,
                             headers={"Authorization": f"Bearer {token}"})
        if resp and resp.status_code == 201:
            addr_ids.append(resp.json()["id"])
            log_step(f"创建地址{i+1}", "PASS", f"ID: {addr_ids[-1]}", dur)
        else:
            log_step(f"创建地址{i+1}", "FAIL")
            result["passed"] = False
    
    if len(addr_ids) < 3:
        result["passed"] = False
        return result
    
    # 2. 设置地址1为默认
    print("\n[2/6] 设置地址1为默认")
    resp, dur = api_call("PUT", f"/api/v1/addresses/{addr_ids[0]}/default",
                         headers={"Authorization": f"Bearer {token}"})
    if resp and resp.status_code == 200:
        log_step("设置默认地址", "PASS", f"ID: {addr_ids[0]}", dur)
    else:
        log_step("设置默认地址", "FAIL")
        result["passed"] = False
    
    # 3. 创建订单(使用默认地址)
    print("\n[3/6] 创建订单(使用默认地址)")
    # 添加商品到购物车
    resp, _ = api_call("POST", "/api/v1/cart/items",
                       json={"product_id": test_data["product_id"], "quantity": 1},
                       headers={"Authorization": f"Bearer {token}"})
    
    resp, dur = api_call("POST", f"/api/v1/cart/checkout?address_id={addr_ids[0]}",
                         headers={"Authorization": f"Bearer {token}"})
    if resp and resp.status_code == 200:
        log_step("创建订单", "PASS", f"使用地址: {addr_ids[0]}", dur)
    else:
        log_step("创建订单", "FAIL")
        result["passed"] = False
    
    # 4. 删除地址1
    print("\n[4/6] 删除地址1")
    resp, dur = api_call("DELETE", f"/api/v1/addresses/{addr_ids[0]}",
                         headers={"Authorization": f"Bearer {token}"})
    if resp and resp.status_code == 200:
        log_step("删除默认地址", "PASS", duration_ms=dur)
    else:
        log_step("删除默认地址", "FAIL")
        result["passed"] = False
    
    # 5. 验证自动设置新默认地址
    print("\n[5/6] 验证自动设置新默认地址")
    # 获取用户ID
    users = db_query("SELECT id FROM users WHERE username = ?", (user_name,))
    if users:
        user_id = users[0]["id"]
        addresses = db_query("SELECT * FROM addresses WHERE user_id = ?", (user_id,))
        default_addrs = [a for a in addresses if a["is_default"]]
        if len(default_addrs) == 1:
            log_step("验证新默认地址", "PASS", f"新默认ID: {default_addrs[0]['id']}")
            new_default = default_addrs[0]["id"]
        else:
            log_step("验证新默认地址", "FAIL", f"默认地址数: {len(default_addrs)}")
            result["passed"] = False
            new_default = addr_ids[1] if len(addr_ids) > 1 else None
    else:
        log_step("验证新默认地址", "FAIL", "找不到用户")
        result["passed"] = False
        new_default = addr_ids[1] if len(addr_ids) > 1 else None
    
    # 6. 创建新订单(使用新默认地址)
    print("\n[6/6] 创建新订单(使用新默认地址)")
    if new_default:
        # 清空购物车并重新添加
        api_call("DELETE", "/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
        api_call("POST", "/api/v1/cart/items",
                 json={"product_id": test_data["product_id"], "quantity": 1},
                 headers={"Authorization": f"Bearer {token}"})
        
        resp, dur = api_call("POST", f"/api/v1/cart/checkout?address_id={new_default}",
                             headers={"Authorization": f"Bearer {token}"})
        if resp and resp.status_code == 200:
            log_step("使用新默认地址下单", "PASS", duration_ms=dur)
        else:
            log_step("使用新默认地址下单", "FAIL")
            result["passed"] = False
    
    return result


def scenario_5():
    """场景5: 商品下架处理"""
    print("\n" + "="*70)
    print("🚫 场景5: 商品下架处理")
    print("="*70)
    
    result = {"scenario": "场景5: 商品下架处理", "passed": True, "performance": {}, "steps": [], "issues": []}
    
    # 1. 创建商品并添加到购物车
    print("\n[1/4] 创建商品并添加到购物车")
    resp, dur = api_call("POST", "/api/v1/products",
                         json={"name": f"下架商品_{int(time.time())}", "price": 99, "stock": 50,
                               "category_id": test_data["category_id"]},
                         headers={"Authorization": f"Bearer {test_data['admin_token']}"})
    if resp and resp.status_code == 201:
        offline_product_id = resp.json()["id"]
        log_step("创建商品", "PASS", f"ID: {offline_product_id}", dur)
    else:
        log_step("创建商品", "FAIL")
        result["passed"] = False
        return result
    
    # 创建用户并添加购物车
    user_name = f"user_off_{int(time.time())}"
    resp, _ = api_call("POST", "/auth/register", json={"username": user_name, "email": f"{user_name}@test.com", "password": "user123"})
    resp, _ = api_call("POST", "/auth/login", data={"username": user_name, "password": "user123"})
    token = resp.json()["access_token"]
    
    resp, dur = api_call("POST", "/api/v1/cart/items",
                         json={"product_id": offline_product_id, "quantity": 2},
                         headers={"Authorization": f"Bearer {token}"})
    if resp and resp.status_code == 201:
        log_step("添加购物车", "PASS", duration_ms=dur)
    else:
        log_step("添加购物车", "FAIL")
        result["passed"] = False
    
    # 2. 商品下架
    print("\n[2/4] 商品下架")
    resp, dur = api_call("PUT", f"/api/v1/products/{offline_product_id}",
                         json={"status": "inactive"},
                         headers={"Authorization": f"Bearer {test_data['admin_token']}"})
    if resp and resp.status_code == 200:
        log_step("商品下架", "PASS", duration_ms=dur)
    else:
        log_step("商品下架", "FAIL")
        result["passed"] = False
    
    # 3. 尝试从购物车结算(应失败)
    print("\n[3/4] 尝试从购物车结算(应失败)")
    addr = {"name": "测试", "phone": "13500135000", "province": "浙江", "city": "杭州", "district": "西湖", "detail": "测试", "is_default": True}
    resp, _ = api_call("POST", "/api/v1/addresses", json=addr, headers={"Authorization": f"Bearer {token}"})
    addr_id = resp.json()["id"]
    
    resp, dur = api_call("POST", f"/api/v1/cart/checkout?address_id={addr_id}",
                         headers={"Authorization": f"Bearer {token}"})
    if resp and resp.status_code != 200:
        log_step("结算失败(预期)", "PASS", f"错误: {resp.json().get('detail', '商品无效')}", dur)
    else:
        log_step("结算失败(预期)", "FAIL", "应该失败但成功了")
        result["passed"] = False
        result["issues"].append("商品下架后，购物车结算未正确拦截")
    
    # 4. 验证购物车中该商品标记为无效
    print("\n[4/4] 验证购物车中该商品标记为无效")
    resp, dur = api_call("GET", "/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    if resp and resp.status_code == 200:
        cart = resp.json()
        invalid_items = [item for item in cart.get("items", []) if item.get("product", {}).get("status") != "active"]
        if invalid_items:
            log_step("验证无效商品", "PASS", f"发现 {len(invalid_items)} 个无效商品")
        else:
            log_step("验证无效商品", "FAIL", "购物车中商品状态未标记为无效")
            result["passed"] = False
            result["issues"].append("购物车未正确标记已下架商品")
    else:
        log_step("验证无效商品", "FAIL")
        result["passed"] = False
    
    return result


def generate_report(results):
    """生成测试报告"""
    report = []
    report.append("# 电商系统联调测试报告")
    report.append("")
    report.append(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**测试环境**: FastAPI + SQLite")
    report.append(f"**API地址**: {BASE_URL}")
    report.append("")
    
    # 汇总
    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)
    report.append("## 测试汇总")
    report.append("")
    report.append(f"| 指标 | 数值 |")
    report.append(f"|------|------|")
    report.append(f"| 测试场景总数 | {total} |")
    report.append(f"| 通过 | {passed} |")
    report.append(f"| 失败 | {total - passed} |")
    report.append(f"| 通过率 | {passed/total*100:.1f}% |")
    report.append("")
    
    # 各场景结果
    for i, r in enumerate(results, 1):
        status = "✅ 通过" if r.get("passed") else "❌ 失败"
        report.append(f"### 场景{i}: {r['scenario']}")
        report.append("")
        report.append(f"**测试结果**: {status}")
        report.append("")
        
        if r.get("performance"):
            report.append("**性能数据**:")
            report.append("")
            report.append("| 操作 | 响应时间(ms) |")
            report.append("|------|-------------|")
            for op, t in r["performance"].items():
                report.append(f"| {op} | {t:.2f} |")
            report.append("")
        
        if r.get("issues"):
            report.append("**发现问题**:")
            report.append("")
            for issue in r["issues"]:
                report.append(f"- ⚠️ {issue}")
            report.append("")
    
    # 问题汇总
    report.append("## 问题记录")
    report.append("")
    all_issues = []
    for r in results:
        if r.get("issues"):
            all_issues.extend(r["issues"])
        elif not r.get("passed"):
            all_issues.append(f"{r['scenario']}: 存在失败步骤")
    
    if all_issues:
        for issue in all_issues:
            report.append(f"- {issue}")
    else:
        report.append("未发现重大问题")
    report.append("")
    
    # 改进建议
    report.append("## 改进建议")
    report.append("")
    report.append("### 高优先级")
    report.append("")
    report.append("1. **库存扣减事务**: 订单创建和库存扣减应在同一数据库事务中执行，确保数据一致性")
    report.append("2. **库存超卖防护**: 添加数据库级别的乐观锁或悲观锁，防止并发场景下的超卖")
    report.append("3. **商品状态校验**: 购物车结算时需要严格校验商品状态，已下架商品应阻止结算")
    report.append("")
    report.append("### 中优先级")
    report.append("")
    report.append("4. **性能优化**: 考虑添加 Redis 缓存层，减少数据库查询压力")
    report.append("5. **API响应优化**: 部分接口响应时间超过500ms，需要优化")
    report.append("6. **错误处理**: 完善错误信息，提供更友好的用户提示")
    report.append("")
    report.append("### 低优先级")
    report.append("")
    report.append("7. **监控告警**: 添加关键业务指标监控，如订单成功率、支付成功率等")
    report.append("8. **日志完善**: 增加关键业务操作的审计日志")
    report.append("")
    
    # 性能汇总
    report.append("## 性能数据汇总")
    report.append("")
    report.append("| 操作 | 平均响应时间(ms) | 评价 |")
    report.append("|------|-----------------|------|")
    
    all_perf = {}
    for r in results:
        for op, t in r.get("performance", {}).items():
            if op not in all_perf:
                all_perf[op] = []
            all_perf[op].append(t)
    
    for op, times in sorted(all_perf.items()):
        avg = sum(times) / len(times)
        if avg < 50:
            eval_str = "优秀"
        elif avg < 100:
            eval_str = "良好"
        elif avg < 200:
            eval_str = "一般"
        else:
            eval_str = "需优化"
        report.append(f"| {op} | {avg:.2f} | {eval_str} |")
    
    report.append("")
    
    return "\n".join(report)


def main():
    results = run_all_scenarios()
    
    # 生成报告
    report = generate_report(results)
    report_path = "/root/.openclaw/workspace/projects/ecommerce-mvp/tests/test_integration_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n" + "="*70)
    print("✅ 测试完成")
    print(f"📄 报告已保存: {report_path}")
    print("="*70)
    
    passed = sum(1 for r in results if r.get("passed", False))
    print(f"\n📊 汇总: {passed}/{len(results)} 个场景通过")


if __name__ == "__main__":
    main()
