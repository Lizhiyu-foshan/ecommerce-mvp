"""
购物车服务层
提供购物车的增删改查和结算功能（带事务管理）
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError
from models.cart import Cart
from models.product import Product
from config.logging_config import logger
from utils.transaction import transactional, TransactionContext


class CartService:
    """购物车服务 - 带事务管理"""

    @staticmethod
    @transactional
    def add_to_cart(
        db: Session,
        product_id: str,
        quantity: int = 1,
        spec_combo: Optional[Dict[str, str]] = None,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Cart:
        """
        添加商品到购物车（带事务管理）

        Args:
            db: 数据库会话
            product_id: 商品ID
            quantity: 数量
            spec_combo: 规格组合，如 {"颜色": "红色", "尺寸": "XL"}
            user_id: 用户ID（登录用户）
            session_id: 会话ID（匿名用户）

        Returns:
            Cart: 购物车项

        Raises:
            ValueError: 商品不存在、已下架或库存不足
            SQLAlchemyError: 数据库操作失败
        """
        # 验证商品（加锁防止并发修改库存）
        product = db.query(Product).filter(
            Product.id == product_id
        ).with_for_update().first()

        if not product:
            raise ValueError("商品不存在")

        if product.status != "active":
            raise ValueError("商品已下架")

        if product.stock < quantity:
            raise ValueError(f"库存不足，当前库存: {product.stock}")

        # 检查购物车中是否已有相同商品和规格
        query = db.query(Cart).filter(Cart.product_id == product_id)

        if user_id:
            query = query.filter(Cart.user_id == user_id)
        elif session_id:
            query = query.filter(Cart.session_id == session_id)
        else:
            raise ValueError("必须提供 user_id 或 session_id")

        # 检查规格是否相同
        existing_item = query.filter(Cart.spec_combo == (spec_combo or {})).first()

        if existing_item:
            # 更新数量（检查库存）
            new_quantity = existing_item.quantity + quantity
            if product.stock < new_quantity:
                raise ValueError(f"库存不足，当前库存: {product.stock}，购物车已有: {existing_item.quantity}")

            existing_item.quantity = new_quantity
            logger.info(f"购物车数量更新: user_id={user_id}, product_id={product_id}, "
                       f"quantity={existing_item.quantity}")
            return existing_item
        else:
            # 创建新购物车项
            cart_item = Cart(
                user_id=user_id,
                session_id=session_id,
                product_id=product_id,
                quantity=quantity,
                spec_combo=spec_combo or {}
            )
            db.add(cart_item)
            db.flush()  # 获取ID但不提交
            logger.info(f"购物车添加商品: user_id={user_id}, product_id={product_id}, "
                       f"quantity={quantity}")
            return cart_item

    @staticmethod
    def get_cart(
        db: Session,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> List[Cart]:
        """
        获取购物车列表（只读操作，无需事务）

        Args:
            db: 数据库会话
            user_id: 用户ID（登录用户）
            session_id: 会话ID（匿名用户）

        Returns:
            List[Cart]: 购物车项列表
        """
        query = db.query(Cart)

        if user_id:
            query = query.filter(Cart.user_id == user_id)
        elif session_id:
            query = query.filter(Cart.session_id == session_id)
        else:
            return []

        return query.order_by(Cart.created_at.desc()).all()

    @staticmethod
    def get_cart_item(db: Session, cart_id: str) -> Optional[Cart]:
        """根据 ID 获取购物车项（只读操作，无需事务）"""
        return db.query(Cart).filter(Cart.id == cart_id).first()

    @staticmethod
    @transactional
    def update_cart_item(
        db: Session,
        cart_id: str,
        quantity: int,
        user_id: Optional[int] = None
    ) -> Optional[Cart]:
        """
        更新购物车商品数量（带事务管理）

        Args:
            db: 数据库会话
            cart_id: 购物车项ID
            quantity: 新数量
            user_id: 用户ID（用于权限验证）

        Returns:
            Cart: 更新后的购物车项，如果数量为0则返回None

        Raises:
            ValueError: 库存不足
        """
        cart_item = CartService.get_cart_item(db, cart_id)
        if not cart_item:
            raise ValueError(f"购物车项不存在: {cart_id}")

        # 权限验证
        if user_id and cart_item.user_id != user_id:
            raise PermissionError("无权访问此购物车项")

        # 验证库存（加锁）
        product = db.query(Product).filter(
            Product.id == cart_item.product_id
        ).with_for_update().first()

        if quantity <= 0:
            # 数量为0或负数，删除该项
            db.delete(cart_item)
            logger.info(f"购物车项删除: cart_id={cart_id} (数量设为0)")
            return None

        if product and product.stock < quantity:
            raise ValueError(f"库存不足，当前库存: {product.stock}")

        cart_item.quantity = quantity
        logger.info(f"购物车数量更新: cart_id={cart_id}, quantity={quantity}")
        return cart_item

    @staticmethod
    @transactional
    def remove_from_cart(
        db: Session,
        cart_id: str,
        user_id: Optional[int] = None
    ) -> bool:
        """
        从购物车删除商品（带事务管理）

        Args:
            db: 数据库会话
            cart_id: 购物车项ID
            user_id: 用户ID（用于权限验证）

        Returns:
            bool: 是否删除成功
        """
        cart_item = CartService.get_cart_item(db, cart_id)
        if not cart_item:
            raise ValueError(f"购物车项不存在: {cart_id}")

        # 权限验证
        if user_id and cart_item.user_id != user_id:
            raise PermissionError("无权访问此购物车项")

        db.delete(cart_item)
        logger.info(f"购物车项删除: cart_id={cart_id}")
        return True

    @staticmethod
    @transactional
    def clear_cart(
        db: Session,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> int:
        """
        清空购物车（带事务管理）

        Args:
            db: 数据库会话
            user_id: 用户ID（登录用户）
            session_id: 会话ID（匿名用户）

        Returns:
            int: 删除的项数
        """
        query = db.query(Cart)

        if user_id:
            query = query.filter(Cart.user_id == user_id)
        elif session_id:
            query = query.filter(Cart.session_id == session_id)
        else:
            return 0

        count = query.count()
        query.delete(synchronize_session=False)
        logger.info(f"购物车清空: user_id={user_id}, session_id={session_id}, "
                   f"删除项数={count}")
        return count

    @staticmethod
    @transactional
    def merge_cart(
        db: Session,
        user_id: int,
        session_id: str
    ) -> int:
        """
        合并匿名购物车到用户购物车（带事务管理，登录时调用）

        Args:
            db: 数据库会话
            user_id: 用户ID
            session_id: 匿名会话ID

        Returns:
            int: 合并的项数
        """
        # 获取匿名购物车项
        anonymous_items = db.query(Cart).filter(Cart.session_id == session_id).all()

        merged_count = 0
        for item in anonymous_items:
            try:
                # 检查用户购物车是否已有相同商品
                existing = db.query(Cart).filter(
                    Cart.user_id == user_id,
                    Cart.product_id == item.product_id,
                    Cart.spec_combo == item.spec_combo
                ).first()

                if existing:
                    # 合并数量（检查库存）
                    product = db.query(Product).filter(
                        Product.id == item.product_id
                    ).with_for_update().first()

                    new_quantity = existing.quantity + item.quantity
                    if product and product.stock >= new_quantity:
                        existing.quantity = new_quantity
                        db.delete(item)
                        merged_count += 1
                        logger.info(f"购物车合并(更新): user_id={user_id}, "
                                   f"product_id={item.product_id}, quantity={new_quantity}")
                    else:
                        logger.warning(f"购物车合并失败(库存不足): user_id={user_id}, "
                                     f"product_id={item.product_id}")
                else:
                    # 转移匿名购物车项到用户
                    item.user_id = user_id
                    item.session_id = None
                    merged_count += 1
                    logger.info(f"购物车合并(转移): user_id={user_id}, "
                               f"product_id={item.product_id}")
            except Exception as e:
                logger.warning(f"合并购物车项失败: {e}")
                continue

        logger.info(f"购物车合并完成: user_id={user_id}, 合并项数={merged_count}")
        return merged_count

    @staticmethod
    def calculate_cart_total(
        db: Session,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算购物车总价（只读操作，无需事务）

        Args:
            db: 数据库会话
            user_id: 用户ID（登录用户）
            session_id: 会话ID（匿名用户）

        Returns:
            Dict: 包含商品总数、总金额等信息
        """
        items = CartService.get_cart(db, user_id=user_id, session_id=session_id)

        total_amount = 0.0
        total_quantity = 0
        valid_items = []
        invalid_items = []

        for item in items:
            if item.product and item.product.status == "active":
                subtotal = item.subtotal
                total_amount += subtotal
                total_quantity += item.quantity
                valid_items.append(item)
            else:
                invalid_items.append(item)

        return {
            "total_amount": round(total_amount, 2),
            "total_quantity": total_quantity,
            "item_count": len(valid_items),
            "valid_items": valid_items,
            "invalid_items": invalid_items
        }

    @staticmethod
    def validate_cart_for_checkout(
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """
        验证购物车是否可结算（增强版）
        
        Args:
            db: 数据库会话
            user_id: 用户ID
        
        Returns:
            Dict: 验证结果
        """
        items = CartService.get_cart(db, user_id=user_id)
        
        if not items:
            return {
                "valid": False,
                "message": "购物车为空",
                "invalid_items": []
            }
        
        invalid_items = []
        
        for item in items:
            product = item.product
            if not product:
                invalid_items.append({
                    "cart_id": item.id,
                    "reason": "商品不存在"
                })
            elif product.status != "active":
                invalid_items.append({
                    "cart_id": item.id,
                    "product_name": product.name,
                    "reason": f"商品已{product.status}"
                })
            elif product.stock < item.quantity:
                invalid_items.append({
                    "cart_id": item.id,
                    "product_name": product.name,
                    "reason": f"库存不足，当前库存: {product.stock}"
                })
        
        return {
            "valid": len(invalid_items) == 0,
            "message": "可以结算" if len(invalid_items) == 0 else "部分商品无法购买",
            "invalid_items": invalid_items
        }

    @staticmethod
    def get_cart_with_products(
        db: Session,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取购物车列表（包含商品信息和状态）

        Args:
            db: 数据库会话
            user_id: 用户ID（登录用户）
            session_id: 会话ID（匿名用户）

        Returns:
            List[dict]: 购物车项列表，包含商品状态信息
        """
        cart_items = CartService.get_cart(db, user_id, session_id)
        result = []

        for item in cart_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()

            if product:
                # 检查商品状态
                is_available = (
                    product.status == "active" and
                    product.stock >= item.quantity
                )

                result.append({
                    "cart_id": item.id,
                    "product_id": product.id,
                    "product_name": product.name,
                    "price": float(product.price),
                    "quantity": item.quantity,
                    "spec_combo": item.spec_combo,
                    "stock": product.stock,
                    "status": product.status,  # 添加商品状态
                    "is_available": is_available,  # 是否可购买
                    "unavailable_reason": None if is_available else (
                        "商品已下架" if product.status != "active" else "库存不足"
                    ),
                    "subtotal": float(product.price) * item.quantity
                })
            else:
                # 商品不存在
                result.append({
                    "cart_id": item.id,
                    "product_id": item.product_id,
                    "product_name": "商品已删除",
                    "is_available": False,
                    "unavailable_reason": "商品不存在"
                })

        return result

    @staticmethod
    @transactional
    def checkout_cart(
        db: Session,
        user_id: int,
        address_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        购物车结算（带事务管理）

        这是一个原子操作，包含以下步骤：
        1. 验证购物车
        2. 创建订单
        3. 扣减库存
        4. 清空购物车

        Args:
            db: 数据库会话
            user_id: 用户ID
            address_id: 收货地址ID（可选）

        Returns:
            Dict: 包含订单信息和结算结果

        Raises:
            ValueError: 购物车验证失败
        """
        # 验证购物车
        validation = CartService.validate_cart_for_checkout(db, user_id)
        if not validation["valid"]:
            raise ValueError(f"购物车验证失败: {validation['message']}")

        # 获取购物车商品
        cart_items = CartService.get_cart(db, user_id=user_id)

        # 调用订单服务创建订单（在同一事务中）
        from services.order_service import OrderService
        order = OrderService.create_order_from_cart(
            db=db,
            user_id=user_id,
            cart_items=cart_items,
            address_id=address_id
        )

        logger.info(f"购物车结算完成: user_id={user_id}, order_no={order.order_no}")

        return {
            "success": True,
            "order": order,
            "order_no": order.order_no,
            "total_amount": order.total_amount
        }
