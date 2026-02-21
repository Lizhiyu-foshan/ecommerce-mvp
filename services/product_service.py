"""
商品服务层
提供商品、分类的 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from models.product import Category, Product, ProductSpec
from config.logging_config import logger


class ProductService:
    """商品服务"""
    
    # ==================== 分类管理 ====================
    
    @staticmethod
    def create_category(db: Session, name: str, description: Optional[str] = None, 
                       parent_id: Optional[str] = None) -> Category:
        """创建分类"""
        logger.info(f"创建分类: {name}")
        category = Category(
            name=name,
            description=description,
            parent_id=parent_id
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        logger.info(f"分类创建成功: ID={category.id}")
        return category
    
    @staticmethod
    def get_category_by_id(db: Session, category_id: str) -> Optional[Category]:
        """根据 ID 获取分类"""
        return db.query(Category).filter(Category.id == category_id).first()
    
    @staticmethod
    def list_categories(db: Session, parent_id: Optional[str] = None, 
                       is_active: bool = True) -> List[Category]:
        """获取分类列表"""
        query = db.query(Category).filter(Category.is_active == is_active)
        if parent_id:
            query = query.filter(Category.parent_id == parent_id)
        else:
            query = query.filter(Category.parent_id.is_(None))
        return query.order_by(Category.sort_order).all()
    
    @staticmethod
    def update_category(db: Session, category_id: str, 
                       update_data: Dict[str, Any]) -> Optional[Category]:
        """更新分类"""
        category = ProductService.get_category_by_id(db, category_id)
        if not category:
            return None
        
        # 使用白名单防止属性注入攻击
        ALLOWED_FIELDS = {"name", "description", "parent_id", "is_active", "sort_order"}
        for field, value in update_data.items():
            if field in ALLOWED_FIELDS and hasattr(category, field):
                setattr(category, field, value)
        
        db.commit()
        db.refresh(category)
        logger.info(f"分类更新成功: ID={category_id}")
        return category
    
    @staticmethod
    def delete_category(db: Session, category_id: str) -> bool:
        """删除分类（软删除）"""
        category = ProductService.get_category_by_id(db, category_id)
        if not category:
            return False
        
        category.is_active = False
        db.commit()
        logger.info(f"分类已删除: ID={category_id}")
        return True
    
    # ==================== 商品管理 ====================
    
    @staticmethod
    def create_product(db: Session, name: str, price: float, 
                      category_id: Optional[str] = None,
                      description: Optional[str] = None,
                      original_price: Optional[float] = None,
                      stock: int = 0, images: Optional[List[Dict]] = None,
                      sort_order: int = 0) -> Product:
        """创建商品"""
        logger.info(f"创建商品: {name}")
        product = Product(
            name=name,
            description=description,
            price=price,
            original_price=original_price,
            stock=stock,
            category_id=category_id,
            images=images or [],
            sort_order=sort_order,
            status="active"
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        logger.info(f"商品创建成功: ID={product.id}")
        return product
    
    @staticmethod
    def get_product_by_id(db: Session, product_id: str) -> Optional[Product]:
        """根据 ID 获取商品"""
        return db.query(Product).filter(Product.id == product_id).first()
    
    @staticmethod
    def list_products(
        db: Session,
        category_id: Optional[str] = None,
        keyword: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        status: str = "active",
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """获取商品列表（支持分页和筛选）"""
        query = db.query(Product).filter(Product.status == status)
        
        # 分类筛选
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        # 关键词搜索
        if keyword:
            search_filter = or_(
                Product.name.contains(keyword),
                Product.description.contains(keyword)
            )
            query = query.filter(search_filter)
        
        # 价格区间筛选
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        
        # 排序
        sort_field = getattr(Product, sort_by, Product.created_at)
        if sort_order == "desc":
            sort_field = sort_field.desc()
        query = query.order_by(sort_field)
        
        # 分页
        total = query.count()
        products = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "total": total,
            "items": products,
            "page": page,
            "page_size": page_size
        }
    
    @staticmethod
    def update_product(db: Session, product_id: str, 
                      update_data: Dict[str, Any]) -> Optional[Product]:
        """更新商品"""
        product = ProductService.get_product_by_id(db, product_id)
        if not product:
            return None
        
        # 使用白名单防止属性注入攻击
        ALLOWED_FIELDS = {"name", "description", "price", "original_price", "stock", 
                         "category_id", "images", "sort_order", "status"}
        for field, value in update_data.items():
            if field in ALLOWED_FIELDS and hasattr(product, field):
                setattr(product, field, value)
        
        db.commit()
        db.refresh(product)
        logger.info(f"商品更新成功: ID={product_id}")
        return product
    
    @staticmethod
    def delete_product(db: Session, product_id: str, hard_delete: bool = False) -> bool:
        """删除商品（软删除或硬删除）"""
        product = ProductService.get_product_by_id(db, product_id)
        if not product:
            return False
        
        if hard_delete:
            db.delete(product)
        else:
            product.status = "deleted"
        
        db.commit()
        logger.info(f"商品已删除: ID={product_id}, 硬删除={hard_delete}")
        return True
    
    @staticmethod
    def update_product_status(db: Session, product_id: str, status: str) -> Optional[Product]:
        """
        更新商品状态，并触发购物车更新
        
        Args:
            db: 数据库会话
            product_id: 商品ID
            status: 新状态 (active, inactive, deleted)
        
        Returns:
            Product: 更新后的商品，失败返回 None
        """
        product = ProductService.get_product_by_id(db, product_id)
        if not product:
            return None
        
        old_status = product.status
        product.status = status
        db.commit()
        db.refresh(product)
        
        # 如果商品下架，记录日志
        if status == "inactive" and old_status == "active":
            logger.info(f"商品下架: {product_id}，购物车中的该商品将标记为不可用")
            # 这里可以添加消息通知，通知购物车服务
        
        logger.info(f"商品状态更新: ID={product_id}, 旧状态={old_status}, 新状态={status}")
        return product
    
    @staticmethod
    def deactivate_product(db: Session, product_id: str) -> Optional[Product]:
        """
        下架商品（快捷方法）
        
        Args:
            db: 数据库会话
            product_id: 商品ID
        
        Returns:
            Product: 更新后的商品，失败返回 None
        """
        return ProductService.update_product_status(db, product_id, "inactive")
    
    @staticmethod
    def activate_product(db: Session, product_id: str) -> Optional[Product]:
        """
        上架商品（快捷方法）
        
        Args:
            db: 数据库会话
            product_id: 商品ID
        
        Returns:
            Product: 更新后的商品，失败返回 None
        """
        return ProductService.update_product_status(db, product_id, "active")
    
    @staticmethod
    def update_stock(db: Session, product_id: str, quantity: int) -> Optional[Product]:
        """
        更新商品库存
        
        Args:
            db: 数据库会话
            product_id: 商品ID
            quantity: 新库存数量
        
        Returns:
            Product: 更新后的商品，失败返回 None
        """
        product = ProductService.get_product_by_id(db, product_id)
        if not product:
            return None
        
        product.stock = quantity
        db.commit()
        db.refresh(product)
        logger.info(f"商品库存更新: ID={product_id}, 新库存={quantity}")
        return product

    @staticmethod
    def deduct_stock(db: Session, product_id: str, quantity: int) -> bool:
        """
        扣减库存（原子操作，防止并发超卖）
        
        使用数据库级别的原子 UPDATE 操作，避免并发问题：
        - 通过 WHERE stock >= quantity 条件确保库存充足
        - 单条 SQL 语句执行，避免读取-修改-写入的竞争条件
        
        Args:
            db: 数据库会话
            product_id: 商品ID
            quantity: 扣减数量
            
        Returns:
            bool: 扣减成功返回 True，库存不足或商品不存在返回 False
        """
        if quantity <= 0:
            logger.warning(f"扣减库存失败: 数量必须大于0, product_id={product_id}, quantity={quantity}")
            return False
        
        # 使用原子 UPDATE 操作，避免并发问题
        # WHERE stock >= quantity 确保库存充足
        result = db.execute(
            text("""
                UPDATE products 
                SET stock = stock - :quantity,
                    sales_count = sales_count + :quantity,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :product_id 
                AND stock >= :quantity
            """),
            {
                "product_id": product_id,
                "quantity": quantity
            }
        )
        db.commit()
        
        if result.rowcount > 0:
            logger.info(f"商品库存扣减成功: ID={product_id}, 扣减={quantity}")
            return True
        else:
            # 扣减失败，可能是库存不足或商品不存在
            product = ProductService.get_product_by_id(db, product_id)
            if not product:
                logger.warning(f"扣减库存失败: 商品不存在, product_id={product_id}")
            else:
                logger.warning(f"扣减库存失败: 库存不足, product_id={product_id}, 当前库存={product.stock}, 需要={quantity}")
            return False
    
    @staticmethod
    def deduct_stock_with_lock(db: Session, product_id: str, quantity: int) -> bool:
        """
        扣减库存（悲观锁版本，适用于需要额外业务逻辑检查的场景）
        
        使用 SELECT FOR UPDATE 获取行级锁，确保并发安全。
        适用于需要在扣减前进行复杂业务校验的场景。
        
        Args:
            db: 数据库会话
            product_id: 商品ID
            quantity: 扣减数量
            
        Returns:
            bool: 扣减成功返回 True，库存不足或商品不存在返回 False
        """
        if quantity <= 0:
            return False
        
        # 使用悲观锁获取商品
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.stock >= quantity
        ).with_for_update().first()
        
        if not product:
            return False
        
        product.stock -= quantity
        product.sales_count += quantity
        db.commit()
        logger.info(f"商品库存扣减(悲观锁): ID={product_id}, 扣减={quantity}, 剩余={product.stock}")
        return True
    
    # ==================== 商品规格管理 ====================
    
    @staticmethod
    def create_product_spec(db: Session, product_id: str, name: str, 
                           values: List[str]) -> ProductSpec:
        """创建商品规格"""
        logger.info(f"创建商品规格: product_id={product_id}, name={name}")
        spec = ProductSpec(
            product_id=product_id,
            name=name,
            values=values
        )
        db.add(spec)
        db.commit()
        db.refresh(spec)
        return spec
    
    @staticmethod
    def get_product_specs(db: Session, product_id: str) -> List[ProductSpec]:
        """获取商品的所有规格"""
        return db.query(ProductSpec).filter(ProductSpec.product_id == product_id).all()
    
    @staticmethod
    def update_product_spec(db: Session, spec_id: str, 
                           update_data: Dict[str, Any]) -> Optional[ProductSpec]:
        """更新商品规格"""
        spec = db.query(ProductSpec).filter(ProductSpec.id == spec_id).first()
        if not spec:
            return None
        
        # 使用白名单防止属性注入攻击
        ALLOWED_FIELDS = {"name", "values"}
        for field, value in update_data.items():
            if field in ALLOWED_FIELDS and hasattr(spec, field):
                setattr(spec, field, value)
        
        db.commit()
        db.refresh(spec)
        return spec
    
    @staticmethod
    def delete_product_spec(db: Session, spec_id: str) -> bool:
        """删除商品规格"""
        spec = db.query(ProductSpec).filter(ProductSpec.id == spec_id).first()
        if not spec:
            return False
        
        db.delete(spec)
        db.commit()
        return True
    
    # ==================== 图片管理 ====================
    
    @staticmethod
    def add_product_image(db: Session, product_id: str, image_url: str, 
                         sort: int = 0) -> Optional[Product]:
        """添加商品图片"""
        product = ProductService.get_product_by_id(db, product_id)
        if not product:
            return None
        
        if not product.images:
            product.images = []
        
        product.images.append({"url": image_url, "sort": sort})
        db.commit()
        db.refresh(product)
        logger.info(f"商品图片添加: ID={product_id}, URL={image_url}")
        return product
    
    @staticmethod
    def remove_product_image(db: Session, product_id: str, image_url: str) -> Optional[Product]:
        """移除商品图片"""
        product = ProductService.get_product_by_id(db, product_id)
        if not product or not product.images:
            return None
        
        product.images = [img for img in product.images if img.get("url") != image_url]
        db.commit()
        db.refresh(product)
        logger.info(f"商品图片移除: ID={product_id}, URL={image_url}")
        return product
