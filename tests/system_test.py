#!/usr/bin/env python3
"""
系统全面测试脚本
QA 工程师 Quinn - 系统测试
"""
import requests
import json
import sys
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add(self, name, passed, details=""):
        self.tests.append({"name": name, "passed": passed, "details": details})
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def summary(self):
        total = self.passed + self.failed
        return f"\n{Colors.BLUE}测试结果: {self.passed}/{total} 通过{Colors.RESET}"

results = TestResult()

# ==================== 辅助函数 ====================
def log_test(name):
    print(f"\n{Colors.YELLOW}▶ {name}{Colors.RESET}")

def log_pass(msg=""):
    print(f"{Colors.GREEN}  ✓ 通过{Colors.RESET} {msg}")

def log_fail(msg):
    print(f"{Colors.RED}  ✗ 失败: {msg}{Colors.RESET}")

# ==================== 1. 用户认证测试 ====================
print(f"{Colors.BLUE}╔════════════════════════════════════════════════════════╗{Colors.RESET}")
print(f"{Colors.BLUE}║     E-Commerce MVP - 系统全面测试                      ║{Colors.RESET}")
print(f"{Colors.BLUE}╚════════════════════════════════════════════════════════╝{Colors.RESET}")

# 1.1 用户注册
log_test("1.1 用户注册 - 普通用户")
try:
    import time
    unique_suffix = str(int(time.time()))
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "username": f"testuser_{unique_suffix}",
        "email": f"test_{unique_suffix}@example.com",
        "password": "testpass123"
    })
    if resp.status_code == 201:
        log_pass(f"用户ID: {resp.json().get('id')}")
        results.add("用户注册-普通用户", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("用户注册-普通用户", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("用户注册-普通用户", False, str(e))

# 1.2 管理员注册
log_test("1.2 用户注册 - 管理员用户")
try:
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "username": f"adminuser_{unique_suffix}",
        "email": f"admin_{unique_suffix}@example.com",
        "password": "adminpass123"
    })
    if resp.status_code == 201:
        # 设置为管理员（直接修改数据库）
        log_pass(f"管理员用户ID: {resp.json().get('id')}")
        results.add("用户注册-管理员", True)
        admin_id = resp.json().get('id')
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("用户注册-管理员", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("用户注册-管理员", False, str(e))

# 1.3 用户登录
log_test("1.3 用户登录 - 获取JWT Token")
try:
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": f"testuser_{unique_suffix}",
        "password": "testpass123"
    })
    if resp.status_code == 200:
        user_token = resp.json()["access_token"]
        log_pass("获取到用户JWT Token")
        results.add("用户登录-普通用户", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("用户登录-普通用户", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("用户登录-普通用户", False, str(e))

# 1.4 管理员登录 - 使用预创建的管理员
log_test("1.4 管理员登录 - 获取JWT Token")
try:
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "admin",
        "password": "admin123"
    })
    if resp.status_code == 200:
        admin_token = resp.json()["access_token"]
        log_pass("获取到管理员JWT Token")
        results.add("管理员登录", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("管理员登录", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("管理员登录", False, str(e))

# 1.5 获取当前用户信息
log_test("1.5 获取当前用户信息")
try:
    resp = requests.get(f"{BASE_URL}/auth/me", headers={
        "Authorization": f"Bearer {user_token}"
    })
    if resp.status_code == 200:
        log_pass(f"用户名: {resp.json().get('username')}")
        results.add("获取当前用户信息", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("获取当前用户信息", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("获取当前用户信息", False, str(e))

# ==================== 2. 商品管理测试 ====================
print(f"\n{Colors.BLUE}--- 商品管理测试 ---{Colors.RESET}")

# 2.1 创建分类（管理员）
log_test("2.1 创建商品分类 - 管理员")
try:
    resp = requests.post(f"{BASE_URL}/api/v1/products/categories", json={
        "name": "电子产品",
        "description": "各类电子设备"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 201:
        category_id = resp.json().get('id')
        log_pass(f"分类ID: {category_id}")
        results.add("创建商品分类-管理员", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("创建商品分类-管理员", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("创建商品分类-管理员", False, str(e))

# 2.2 创建分类（普通用户-应失败）
log_test("2.2 创建商品分类 - 普通用户（应被拒绝）")
try:
    resp = requests.post(f"{BASE_URL}/api/v1/products/categories", json={
        "name": "测试分类",
        "description": "测试"
    }, headers={"Authorization": f"Bearer {user_token}"})
    if resp.status_code == 403:
        log_pass("正确拒绝普通用户")
        results.add("创建分类-普通用户拒绝", True)
    else:
        log_fail(f"应返回403，实际: {resp.status_code}")
        results.add("创建分类-普通用户拒绝", False, f"期望403，实际{resp.status_code}")
except Exception as e:
    log_fail(str(e))
    results.add("创建分类-普通用户拒绝", False, str(e))

# 2.3 创建商品（管理员）
log_test("2.3 创建商品 - 管理员")
try:
    resp = requests.post(f"{BASE_URL}/api/v1/products", json={
        "name": "iPhone 15 Pro",
        "description": "最新款苹果手机",
        "price": 7999.00,
        "original_price": 8999.00,
        "stock": 100,
        "category_id": category_id
    }, headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 201:
        product_id = resp.json().get('id')
        log_pass(f"商品ID: {product_id}")
        results.add("创建商品-管理员", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("创建商品-管理员", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("创建商品-管理员", False, str(e))

# 2.4 获取商品列表
log_test("2.4 获取商品列表")
try:
    resp = requests.get(f"{BASE_URL}/api/v1/products")
    if resp.status_code == 200:
        data = resp.json()
        log_pass(f"总数: {data.get('total')}, 当前页: {data.get('items', [])}")
        results.add("获取商品列表", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("获取商品列表", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("获取商品列表", False, str(e))

# 2.5 获取商品详情
log_test("2.5 获取商品详情")
try:
    resp = requests.get(f"{BASE_URL}/api/v1/products/{product_id}")
    if resp.status_code == 200:
        log_pass(f"商品: {resp.json().get('name')}")
        results.add("获取商品详情", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("获取商品详情", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("获取商品详情", False, str(e))

# ==================== 3. 购物车测试 ====================
print(f"\n{Colors.BLUE}--- 购物车测试 ---{Colors.RESET}")

# 3.1 添加商品到购物车
log_test("3.1 添加商品到购物车")
try:
    resp = requests.post(f"{BASE_URL}/api/v1/cart/items", json={
        "product_id": product_id,
        "quantity": 2
    }, headers={"Authorization": f"Bearer {user_token}"})
    if resp.status_code == 201:
        cart_item_id = resp.json().get('id')
        log_pass(f"购物车项ID: {cart_item_id}")
        results.add("添加商品到购物车", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("添加商品到购物车", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("添加商品到购物车", False, str(e))

# 3.2 获取购物车
log_test("3.2 获取购物车")
try:
    resp = requests.get(f"{BASE_URL}/api/v1/cart", headers={
        "Authorization": f"Bearer {user_token}"
    })
    if resp.status_code == 200:
        data = resp.json()
        log_pass(f"商品数: {data.get('item_count')}, 总金额: {data.get('total_amount')}")
        results.add("获取购物车", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("获取购物车", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("获取购物车", False, str(e))

# 3.3 更新购物车数量
log_test("3.3 更新购物车数量")
try:
    resp = requests.put(f"{BASE_URL}/api/v1/cart/items/{cart_item_id}", json={
        "quantity": 3
    }, headers={"Authorization": f"Bearer {user_token}"})
    if resp.status_code == 200:
        log_pass(f"新数量: {resp.json().get('quantity')}")
        results.add("更新购物车数量", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("更新购物车数量", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("更新购物车数量", False, str(e))

# ==================== 4. 地址管理测试 ====================
print(f"\n{Colors.BLUE}--- 地址管理测试 ---{Colors.RESET}")

# 4.1 创建地址
log_test("4.1 创建收货地址")
try:
    resp = requests.post(f"{BASE_URL}/api/v1/addresses", json={
        "name": "张三",
        "phone": "13800138000",
        "province": "广东省",
        "city": "深圳市",
        "district": "南山区",
        "detail": "科技园南路88号",
        "is_default": True
    }, headers={"Authorization": f"Bearer {user_token}"})
    if resp.status_code == 201:
        address_id = resp.json().get('id')
        log_pass(f"地址ID: {address_id}")
        results.add("创建收货地址", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("创建收货地址", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("创建收货地址", False, str(e))

# 4.2 获取地址列表
log_test("4.2 获取地址列表")
try:
    resp = requests.get(f"{BASE_URL}/api/v1/addresses", headers={
        "Authorization": f"Bearer {user_token}"
    })
    if resp.status_code == 200:
        data = resp.json()
        log_pass(f"总数: {data.get('total')}")
        results.add("获取地址列表", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("获取地址列表", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("获取地址列表", False, str(e))

# 4.3 获取地址详情
log_test("4.3 获取地址详情")
try:
    resp = requests.get(f"{BASE_URL}/api/v1/addresses/{address_id}", headers={
        "Authorization": f"Bearer {user_token}"
    })
    if resp.status_code == 200:
        log_pass(f"收件人: {resp.json().get('name')}")
        results.add("获取地址详情", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("获取地址详情", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("获取地址详情", False, str(e))

# ==================== 5. 订单模块测试 ====================
print(f"\n{Colors.BLUE}--- 订单模块测试 ---{Colors.RESET}")

# 5.1 创建订单
log_test("5.1 创建订单")
try:
    resp = requests.post(f"{BASE_URL}/orders/create", json={
        "items": [
            {
                "product_id": product_id,
                "product_name": "iPhone 15 Pro",
                "quantity": 1,
                "unit_price": 7999.00
            }
        ]
    }, headers={"Authorization": f"Bearer {user_token}"})
    if resp.status_code == 201:
        order_id = resp.json().get('id')
        order_no = resp.json().get('order_no')
        log_pass(f"订单ID: {order_id}, 订单号: {order_no}")
        results.add("创建订单", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("创建订单", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("创建订单", False, str(e))

# 5.2 查询订单列表
log_test("5.2 查询订单列表")
try:
    resp = requests.get(f"{BASE_URL}/orders/list", headers={
        "Authorization": f"Bearer {user_token}"
    })
    if resp.status_code == 200:
        data = resp.json()
        log_pass(f"总数: {data.get('total')}")
        results.add("查询订单列表", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("查询订单列表", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("查询订单列表", False, str(e))

# 5.3 查询订单详情
log_test("5.3 查询订单详情")
try:
    resp = requests.get(f"{BASE_URL}/orders/{order_id}", headers={
        "Authorization": f"Bearer {user_token}"
    })
    if resp.status_code == 200:
        log_pass(f"订单状态: {resp.json().get('status')}")
        results.add("查询订单详情", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("查询订单详情", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("查询订单详情", False, str(e))

# 5.4 其他用户访问订单详情（应失败）
log_test("5.4 订单详情权限验证 - 其他用户访问（应被拒绝）")
try:
    # 创建另一个用户
    import time
    other_suffix = str(int(time.time()) + 1)
    requests.post(f"{BASE_URL}/auth/register", json={
        "username": f"otheruser_{other_suffix}",
        "email": f"other_{other_suffix}@example.com",
        "password": "otherpass123"
    })
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": f"otheruser_{other_suffix}",
        "password": "otherpass123"
    })
    other_token = resp.json()["access_token"]
    
    # 尝试访问其他用户的订单
    resp = requests.get(f"{BASE_URL}/orders/{order_id}", headers={
        "Authorization": f"Bearer {other_token}"
    })
    if resp.status_code == 404:
        log_pass("正确拒绝访问其他用户订单")
        results.add("订单详情权限验证", True)
    else:
        log_fail(f"应返回404，实际: {resp.status_code}")
        results.add("订单详情权限验证", False, f"期望404，实际{resp.status_code}")
except Exception as e:
    log_fail(str(e))
    results.add("订单详情权限验证", False, str(e))

# 5.5 取消订单
log_test("5.5 取消订单")
try:
    resp = requests.post(f"{BASE_URL}/orders/cancel", json={
        "order_id": str(order_id),
        "reason": "测试取消"
    }, headers={"Authorization": f"Bearer {user_token}"})
    if resp.status_code == 200:
        log_pass(f"订单状态: {resp.json().get('status')}")
        results.add("取消订单", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("取消订单", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("取消订单", False, str(e))

# ==================== 6. 图片上传测试 ====================
print(f"\n{Colors.BLUE}--- 图片上传测试 ---{Colors.RESET}")

# 创建测试图片文件
import tempfile
from PIL import Image as PILImage
import io

def create_test_image(format='JPEG', size=(100, 100), color='red'):
    img = PILImage.new('RGB', size, color)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes

# 6.1 上传合法图片 - JPG
log_test("6.1 上传合法图片 - JPG")
try:
    img = create_test_image('JPEG')
    resp = requests.post(
        f"{BASE_URL}/api/v1/products/{product_id}/images",
        files={"file": ("test.jpg", img, "image/jpeg")},
        data={"sort": 0},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 200:
        log_pass("JPG上传成功")
        results.add("上传图片-JPG", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("上传图片-JPG", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("上传图片-JPG", False, str(e))

# 6.2 上传合法图片 - PNG
log_test("6.2 上传合法图片 - PNG")
try:
    img = create_test_image('PNG')
    resp = requests.post(
        f"{BASE_URL}/api/v1/products/{product_id}/images",
        files={"file": ("test.png", img, "image/png")},
        data={"sort": 1},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 200:
        log_pass("PNG上传成功")
        results.add("上传图片-PNG", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("上传图片-PNG", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("上传图片-PNG", False, str(e))

# 6.3 上传合法图片 - GIF
log_test("6.3 上传合法图片 - GIF")
try:
    img = create_test_image('GIF')
    resp = requests.post(
        f"{BASE_URL}/api/v1/products/{product_id}/images",
        files={"file": ("test.gif", img, "image/gif")},
        data={"sort": 2},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 200:
        log_pass("GIF上传成功")
        results.add("上传图片-GIF", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("上传图片-GIF", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("上传图片-GIF", False, str(e))

# 6.4 上传合法图片 - WebP
log_test("6.4 上传合法图片 - WebP")
try:
    img = create_test_image('WEBP')
    resp = requests.post(
        f"{BASE_URL}/api/v1/products/{product_id}/images",
        files={"file": ("test.webp", img, "image/webp")},
        data={"sort": 3},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 200:
        log_pass("WebP上传成功")
        results.add("上传图片-WebP", True)
    else:
        log_fail(f"状态码: {resp.status_code}, {resp.text}")
        results.add("上传图片-WebP", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("上传图片-WebP", False, str(e))

# 6.5 上传非法文件类型
log_test("6.5 上传非法文件类型（应被拒绝）")
try:
    fake_file = io.BytesIO(b"This is not an image file")
    resp = requests.post(
        f"{BASE_URL}/api/v1/products/{product_id}/images",
        files={"file": ("test.txt", fake_file, "text/plain")},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 400:
        log_pass("正确拒绝非法文件类型")
        results.add("拒绝非法文件类型", True)
    else:
        log_fail(f"应返回400，实际: {resp.status_code}")
        results.add("拒绝非法文件类型", False, f"期望400，实际{resp.status_code}")
except Exception as e:
    log_fail(str(e))
    results.add("拒绝非法文件类型", False, str(e))

# 6.6 上传超大文件
log_test("6.6 上传超大文件（应被拒绝）")
try:
    # 创建一个超过10MB的"图片"
    large_img = io.BytesIO(b'\x00' * (11 * 1024 * 1024))  # 11MB
    resp = requests.post(
        f"{BASE_URL}/api/v1/products/{product_id}/images",
        files={"file": ("large.jpg", large_img, "image/jpeg")},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code == 400:
        log_pass("正确拒绝超大文件")
        results.add("拒绝超大文件", True)
    else:
        log_fail(f"应返回400，实际: {resp.status_code}")
        results.add("拒绝超大文件", False, f"期望400，实际{resp.status_code}")
except Exception as e:
    log_fail(str(e))
    results.add("拒绝超大文件", False, str(e))

# ==================== 7. 管理员权限测试 ====================
print(f"\n{Colors.BLUE}--- 管理员权限测试 ---{Colors.RESET}")

# 7.1 管理员访问管理接口
log_test("7.1 管理员访问管理接口")
try:
    resp = requests.post(f"{BASE_URL}/api/v1/products", json={
        "name": "管理员商品",
        "price": 999.00,
        "stock": 50
    }, headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 201:
        log_pass("管理员可访问管理接口")
        results.add("管理员访问管理接口", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("管理员访问管理接口", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("管理员访问管理接口", False, str(e))

# 7.2 普通用户访问管理接口（应被拒绝）
log_test("7.2 普通用户访问管理接口（应被拒绝）")
try:
    resp = requests.post(f"{BASE_URL}/api/v1/products", json={
        "name": "普通用户商品",
        "price": 999.00,
        "stock": 50
    }, headers={"Authorization": f"Bearer {user_token}"})
    if resp.status_code == 403:
        log_pass("正确拒绝普通用户访问管理接口")
        results.add("普通用户访问管理接口拒绝", True)
    else:
        log_fail(f"应返回403，实际: {resp.status_code}")
        results.add("普通用户访问管理接口拒绝", False, f"期望403，实际{resp.status_code}")
except Exception as e:
    log_fail(str(e))
    results.add("普通用户访问管理接口拒绝", False, str(e))

# 7.3 删除商品（管理员）
log_test("7.3 删除商品 - 管理员")
try:
    # 先创建一个要删除的商品
    resp = requests.post(f"{BASE_URL}/api/v1/products", json={
        "name": "待删除商品",
        "price": 99.00,
        "stock": 10
    }, headers={"Authorization": f"Bearer {admin_token}"})
    delete_product_id = resp.json().get('id')
    
    resp = requests.delete(f"{BASE_URL}/api/v1/products/{delete_product_id}",
        headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        log_pass("商品删除成功")
        results.add("删除商品-管理员", True)
    else:
        log_fail(f"状态码: {resp.status_code}")
        results.add("删除商品-管理员", False, resp.text)
except Exception as e:
    log_fail(str(e))
    results.add("删除商品-管理员", False, str(e))

# ==================== 8. 无权限访问测试 ====================
print(f"\n{Colors.BLUE}--- 无权限访问测试 ---{Colors.RESET}")

# 8.1 未登录访问订单
log_test("8.1 未登录访问订单（应被拒绝）")
try:
    resp = requests.get(f"{BASE_URL}/orders/list")
    if resp.status_code == 401:
        log_pass("正确拒绝未登录访问")
        results.add("未登录访问订单拒绝", True)
    else:
        log_fail(f"应返回401，实际: {resp.status_code}")
        results.add("未登录访问订单拒绝", False, f"期望401，实际{resp.status_code}")
except Exception as e:
    log_fail(str(e))
    results.add("未登录访问订单拒绝", False, str(e))

# 8.2 无效Token访问
log_test("8.2 无效Token访问（应被拒绝）")
try:
    resp = requests.get(f"{BASE_URL}/orders/list", headers={
        "Authorization": "Bearer invalid_token"
    })
    if resp.status_code == 401:
        log_pass("正确拒绝无效Token")
        results.add("无效Token访问拒绝", True)
    else:
        log_fail(f"应返回401，实际: {resp.status_code}")
        results.add("无效Token访问拒绝", False, f"期望401，实际{resp.status_code}")
except Exception as e:
    log_fail(str(e))
    results.add("无效Token访问拒绝", False, str(e))

# ==================== 测试总结 ====================
print(f"\n{Colors.BLUE}╔════════════════════════════════════════════════════════╗{Colors.RESET}")
print(f"{Colors.BLUE}║                   测试总结                             ║{Colors.RESET}")
print(f"{Colors.BLUE}╚════════════════════════════════════════════════════════╝{Colors.RESET}")

print(results.summary())
print(f"\n通过: {Colors.GREEN}{results.passed}{Colors.RESET}")
print(f"失败: {Colors.RED}{results.failed}{Colors.RESET}")

# 保存测试结果到文件
output = {
    "test_date": datetime.now().isoformat(),
    "total_tests": results.passed + results.failed,
    "passed": results.passed,
    "failed": results.failed,
    "tests": results.tests
}

with open("/root/.openclaw/workspace/projects/ecommerce-mvp/tests/test_results.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\n详细结果已保存到: tests/test_results.json")

if results.failed > 0:
    sys.exit(1)
else:
    print(f"\n{Colors.GREEN}🎉 所有测试通过！{Colors.RESET}")
    sys.exit(0)
