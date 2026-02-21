"""
Phase 1 功能测试脚本
验证商品、购物车、地址模块的基本功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
from models import User, Category, Product, Cart, Address
from services.product_service import ProductService
from services.cart_service import CartService
from services.address_service import AddressService


import uuid

def test_product_service():
    """测试商品服务"""
    print("\n=== 测试商品服务 ===")
    db = SessionLocal()
    
    try:
        # 使用唯一名称创建分类
        unique_name = f"测试分类_{uuid.uuid4().hex[:8]}"
        category = ProductService.create_category(
            db, name=unique_name, description="这是一个测试分类"
        )
        print(f"✅ 创建分类: {category.name} (ID: {category.id})")
        
        # 创建商品
        product = ProductService.create_product(
            db,
            name=f"测试商品_{uuid.uuid4().hex[:8]}",
            price=99.99,
            category_id=category.id,
            description="这是一个测试商品",
            stock=100
        )
        print(f"✅ 创建商品: {product.name} (ID: {product.id}, 价格: {product.price})")
        
        # 查询商品
        found_product = ProductService.get_product_by_id(db, product.id)
        print(f"✅ 查询商品: {found_product.name}")
        
        # 更新商品
        updated = ProductService.update_product(db, product.id, {"price": 88.88})
        print(f"✅ 更新商品价格: {updated.price}")
        
        # 商品列表
        result = ProductService.list_products(db, page=1, page_size=10)
        print(f"✅ 商品列表: 共 {result['total']} 个商品")
        
        # 创建规格
        spec = ProductService.create_product_spec(
            db, product.id, "颜色", ["红色", "蓝色", "黑色"]
        )
        print(f"✅ 创建规格: {spec.name} = {spec.values}")
        
        # 库存扣减
        success = ProductService.deduct_stock(db, product.id, 10)
        print(f"✅ 扣减库存: {'成功' if success else '失败'}")
        
        # 软删除商品
        success = ProductService.delete_product(db, product.id, hard_delete=False)
        print(f"✅ 软删除商品: {'成功' if success else '失败'}")
        
        # 删除分类
        success = ProductService.delete_category(db, category.id)
        print(f"✅ 删除分类: {'成功' if success else '失败'}")
        
        print("\n✅ 商品服务测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ 商品服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_cart_service():
    """测试购物车服务"""
    print("\n=== 测试购物车服务 ===")
    db = SessionLocal()
    
    try:
        # 先创建一个用户和商品
        user = db.query(User).first()
        if not user:
            from services.auth_service import AuthService
            from models.schemas import UserCreate
            user = AuthService.create_user(
                db, 
                UserCreate(username="testuser", email="test@example.com", password="testpass123")
            )
            print(f"✅ 创建测试用户: {user.username}")
        else:
            print(f"✅ 使用现有用户: {user.username}")
        
        # 创建商品
        product = ProductService.create_product(
            db, name=f"购物车测试商品_{uuid.uuid4().hex[:8]}", price=50.00, stock=50
        )
        print(f"✅ 创建商品: {product.name}")
        
        # 添加到购物车
        cart_item = CartService.add_to_cart(
            db, product_id=product.id, quantity=2, user_id=user.id
        )
        print(f"✅ 添加到购物车: 商品={cart_item.product_id}, 数量={cart_item.quantity}")
        
        # 获取购物车
        items = CartService.get_cart(db, user_id=user.id)
        print(f"✅ 获取购物车: 共 {len(items)} 项")
        
        # 计算总价
        cart_info = CartService.calculate_cart_total(db, user_id=user.id)
        print(f"✅ 购物车总价: ¥{cart_info['total_amount']}, 共 {cart_info['total_quantity']} 件")
        
        # 更新数量
        updated = CartService.update_cart_item(db, cart_item.id, quantity=5, user_id=user.id)
        print(f"✅ 更新数量: {updated.quantity}")
        
        # 验证结算
        validation = CartService.validate_cart_for_checkout(db, user_id=user.id)
        print(f"✅ 结算验证: {validation['message']}")
        
        # 清空购物车
        count = CartService.clear_cart(db, user_id=user.id)
        print(f"✅ 清空购物车: 删除 {count} 项")
        
        # 删除测试商品
        ProductService.delete_product(db, product.id, hard_delete=True)
        
        print("\n✅ 购物车服务测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ 购物车服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_address_service():
    """测试地址服务"""
    print("\n=== 测试地址服务 ===")
    db = SessionLocal()
    
    try:
        # 获取或创建用户
        user = db.query(User).first()
        if not user:
            from services.auth_service import AuthService
            from models.schemas import UserCreate
            user = AuthService.create_user(
                db,
                UserCreate(username="testuser2", email="test2@example.com", password="testpass123")
            )
        
        # 创建地址
        address = AddressService.create_address(
            db,
            user_id=user.id,
            name="张三",
            phone="13800138000",
            province="广东省",
            city="深圳市",
            district="南山区",
            detail="科技园南路88号",
            zip_code="518000",
            is_default=True
        )
        print(f"✅ 创建地址: {address.full_address}")
        print(f"   收件人: {address.name}, 电话: {address.masked_phone}")
        
        # 获取地址列表
        result = AddressService.get_user_addresses(db, user_id=user.id)
        print(f"✅ 地址列表: 共 {result['total']} 个地址")
        
        # 获取默认地址
        default_addr = AddressService.get_default_address(db, user_id=user.id)
        print(f"✅ 默认地址: {default_addr.full_address if default_addr else '无'}")
        
        # 更新地址
        updated = AddressService.update_address(
            db, address.id, user_id=user.id, update_data={"detail": "科技园南路99号"}
        )
        print(f"✅ 更新地址: {updated.full_address}")
        
        # 创建第二个地址并设为默认
        address2 = AddressService.create_address(
            db,
            user_id=user.id,
            name="李四",
            phone="13900139000",
            province="广东省",
            city="广州市",
            district="天河区",
            detail="珠江新城",
            is_default=True
        )
        print(f"✅ 创建第二个地址并设为默认")
        
        # 删除地址
        success = AddressService.delete_address(db, address2.id, user_id=user.id)
        print(f"✅ 删除地址: {'成功' if success else '失败'}")
        
        # 删除第一个地址
        success = AddressService.delete_address(db, address.id, user_id=user.id)
        print(f"✅ 删除第一个地址: {'成功' if success else '失败'}")
        
        print("\n✅ 地址服务测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ 地址服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """运行所有测试"""
    print("=" * 50)
    print("E-Commerce MVP Phase 1 功能测试")
    print("=" * 50)
    
    # 确保表已创建
    Base.metadata.create_all(bind=engine)
    
    results = []
    
    # 测试商品服务
    results.append(("商品服务", test_product_service()))
    
    # 测试购物车服务
    results.append(("购物车服务", test_cart_service()))
    
    # 测试地址服务
    results.append(("地址服务", test_address_service()))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print("\n⚠️ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
