"""
API 接口测试脚本
使用 httpx 测试所有新添加的 API 接口
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
import json

BASE_URL = "http://localhost:8000"


def test_auth_flow():
    """测试认证流程"""
    print("\n=== 测试认证流程 ===")
    
    # 注册用户
    register_data = {
        "username": "apitest_user",
        "email": "apitest@example.com",
        "password": "testpass123"
    }
    
    try:
        with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
            # 注册
            response = client.post("/auth/register", json=register_data)
            print(f"注册: {response.status_code}")
            if response.status_code == 201:
                print(f"  ✅ 用户注册成功")
            elif response.status_code == 400 and "已存在" in response.text:
                print(f"  ℹ️ 用户已存在")
            else:
                print(f"  ❌ 注册失败: {response.text}")
            
            # 登录
            login_data = {
                "username": register_data["username"],
                "password": register_data["password"]
            }
            response = client.post("/auth/login", data=login_data)
            print(f"登录: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"  ✅ 登录成功，获取到 token")
                return token_data.get("access_token")
            else:
                print(f"  ❌ 登录失败: {response.text}")
                return None
                
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
        return None


def test_product_apis(token: str = None):
    """测试商品 API"""
    print("\n=== 测试商品 API ===")
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    try:
        with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
            # 获取商品列表
            response = client.get("/api/v1/products?page=1&page_size=10")
            print(f"GET /api/v1/products: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ 获取到 {data.get('total', 0)} 个商品")
            
            # 获取分类列表
            response = client.get("/api/v1/products/categories")
            print(f"GET /api/v1/products/categories: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ 获取分类列表成功")
            
            # 创建分类（需要管理员权限）
            if token:
                category_data = {
                    "name": f"API测试分类_{os.urandom(4).hex()}",
                    "description": "API测试用分类"
                }
                response = client.post("/api/v1/products/categories", 
                                      json=category_data, headers=headers)
                print(f"POST /api/v1/products/categories: {response.status_code}")
                if response.status_code == 201:
                    print(f"  ✅ 创建分类成功")
                    category_id = response.json().get("id")
                    
                    # 创建商品
                    product_data = {
                        "name": f"API测试商品_{os.urandom(4).hex()}",
                        "price": 99.99,
                        "stock": 100,
                        "category_id": category_id,
                        "description": "API测试用商品"
                    }
                    response = client.post("/api/v1/products", 
                                          json=product_data, headers=headers)
                    print(f"POST /api/v1/products: {response.status_code}")
                    if response.status_code == 201:
                        print(f"  ✅ 创建商品成功")
                        product_id = response.json().get("id")
                        
                        # 获取商品详情
                        response = client.get(f"/api/v1/products/{product_id}")
                        print(f"GET /api/v1/products/{product_id}: {response.status_code}")
                        if response.status_code == 200:
                            print(f"  ✅ 获取商品详情成功")
                        
                        # 删除商品
                        response = client.delete(f"/api/v1/products/{product_id}", 
                                                headers=headers)
                        print(f"DELETE /api/v1/products/{product_id}: {response.status_code}")
                        if response.status_code == 200:
                            print(f"  ✅ 删除商品成功")
                    
                    # 删除分类
                    response = client.delete(f"/api/v1/products/categories/{category_id}", 
                                            headers=headers)
                    print(f"DELETE /api/v1/products/categories/{category_id}: {response.status_code}")
                    if response.status_code == 200:
                        print(f"  ✅ 删除分类成功")
                elif response.status_code == 401:
                    print(f"  ℹ️ 需要管理员权限")
                else:
                    print(f"  ❌ 创建分类失败: {response.text}")
                    
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")


def test_cart_apis(token: str = None):
    """测试购物车 API"""
    print("\n=== 测试购物车 API ===")
    
    if not token:
        print("  ℹ️ 需要登录才能测试购物车")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
            # 获取购物车
            response = client.get("/api/v1/cart", headers=headers)
            print(f"GET /api/v1/cart: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ 获取购物车成功")
            
            # 注意：添加商品到购物车需要先创建商品
            # 这里仅测试接口可用性
            
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")


def test_address_apis(token: str = None):
    """测试地址 API"""
    print("\n=== 测试地址 API ===")
    
    if not token:
        print("  ℹ️ 需要登录才能测试地址")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
            # 获取地址列表
            response = client.get("/api/v1/addresses", headers=headers)
            print(f"GET /api/v1/addresses: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ 获取地址列表成功")
            
            # 创建地址
            address_data = {
                "name": "API测试",
                "phone": "13800138000",
                "province": "广东省",
                "city": "深圳市",
                "district": "南山区",
                "detail": "科技园",
                "is_default": True
            }
            response = client.post("/api/v1/addresses", 
                                  json=address_data, headers=headers)
            print(f"POST /api/v1/addresses: {response.status_code}")
            if response.status_code == 201:
                print(f"  ✅ 创建地址成功")
                address_id = response.json().get("id")
                
                # 获取地址详情
                response = client.get(f"/api/v1/addresses/{address_id}", 
                                     headers=headers)
                print(f"GET /api/v1/addresses/{address_id}: {response.status_code}")
                if response.status_code == 200:
                    print(f"  ✅ 获取地址详情成功")
                
                # 更新地址
                update_data = {"detail": "科技园南路"}
                response = client.put(f"/api/v1/addresses/{address_id}", 
                                     json=update_data, headers=headers)
                print(f"PUT /api/v1/addresses/{address_id}: {response.status_code}")
                if response.status_code == 200:
                    print(f"  ✅ 更新地址成功")
                
                # 删除地址
                response = client.delete(f"/api/v1/addresses/{address_id}", 
                                        headers=headers)
                print(f"DELETE /api/v1/addresses/{address_id}: {response.status_code}")
                if response.status_code == 200:
                    print(f"  ✅ 删除地址成功")
            else:
                print(f"  ❌ 创建地址失败: {response.text}")
                
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")


def main():
    """运行 API 测试"""
    print("=" * 50)
    print("E-Commerce MVP Phase 1 API 测试")
    print(f"Base URL: {BASE_URL}")
    print("=" * 50)
    
    # 测试认证
    token = test_auth_flow()
    
    # 测试商品 API
    test_product_apis(token)
    
    # 测试购物车 API
    test_cart_apis(token)
    
    # 测试地址 API
    test_address_apis(token)
    
    print("\n" + "=" * 50)
    print("API 测试完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
