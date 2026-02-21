"""
用户地址服务层
提供收货地址的增删改查功能
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from models.address import Address
from config.logging_config import logger


class AddressService:
    """地址服务"""
    
    MAX_ADDRESSES_PER_USER = 10  # 每个用户最多保存的地址数
    
    @staticmethod
    def create_address(
        db: Session,
        user_id: int,
        name: str,
        phone: str,
        province: str,
        city: str,
        district: str,
        detail: str,
        zip_code: Optional[str] = None,
        is_default: bool = False
    ) -> Address:
        """
        创建收货地址
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            name: 收件人姓名
            phone: 手机号
            province: 省份
            city: 城市
            district: 区县
            detail: 详细地址
            zip_code: 邮编
            is_default: 是否设为默认地址
        
        Returns:
            Address: 创建的地址
        
        Raises:
            ValueError: 地址数量超过限制
        """
        # 检查地址数量限制
        existing_count = db.query(Address).filter(Address.user_id == user_id).count()
        if existing_count >= AddressService.MAX_ADDRESSES_PER_USER:
            raise ValueError(f"每个用户最多保存 {AddressService.MAX_ADDRESSES_PER_USER} 个地址")
        
        # 如果设为默认，取消其他默认地址
        if is_default:
            AddressService._clear_default_addresses(db, user_id)
        
        address = Address(
            user_id=user_id,
            name=name,
            phone=phone,
            province=province,
            city=city,
            district=district,
            detail=detail,
            zip_code=zip_code,
            is_default=is_default
        )
        db.add(address)
        db.commit()
        db.refresh(address)
        logger.info(f"地址创建成功: user_id={user_id}, address_id={address.id}")
        return address
    
    @staticmethod
    def get_address_by_id(db: Session, address_id: str) -> Optional[Address]:
        """根据 ID 获取地址"""
        return db.query(Address).filter(Address.id == address_id).first()
    
    @staticmethod
    def get_user_addresses(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        获取用户的地址列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
        
        Returns:
            Dict: 包含地址列表和分页信息
        """
        query = db.query(Address).filter(Address.user_id == user_id)
        
        total = query.count()
        addresses = query.order_by(
            Address.is_default.desc(),
            Address.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "total": total,
            "items": addresses,
            "page": page,
            "page_size": page_size
        }
    
    @staticmethod
    def get_default_address(db: Session, user_id: int) -> Optional[Address]:
        """获取用户的默认地址"""
        return db.query(Address).filter(
            Address.user_id == user_id,
            Address.is_default == True
        ).first()
    
    @staticmethod
    def update_address(
        db: Session,
        address_id: str,
        user_id: int,
        update_data: Dict[str, Any]
    ) -> Optional[Address]:
        """
        更新地址
        
        Args:
            db: 数据库会话
            address_id: 地址ID
            user_id: 用户ID（用于权限验证）
            update_data: 更新数据
        
        Returns:
            Address: 更新后的地址
        """
        address = AddressService.get_address_by_id(db, address_id)
        if not address:
            raise ValueError(f"地址不存在: {address_id}")
        
        # 权限验证
        if address.user_id != user_id:
            raise PermissionError("无权访问此地址")
        
        # 如果设为默认，取消其他默认地址
        if update_data.get("is_default") and not address.is_default:
            AddressService._clear_default_addresses(db, user_id)
        
        # 更新字段 - 使用白名单防止属性注入
        ALLOWED_FIELDS = {"name", "phone", "province", "city", "district", "detail", "zip_code", "is_default"}
        for field, value in update_data.items():
            if field in ALLOWED_FIELDS and hasattr(address, field):
                setattr(address, field, value)
        
        db.commit()
        db.refresh(address)
        logger.info(f"地址更新成功: address_id={address_id}")
        return address
    
    @staticmethod
    def delete_address(db: Session, address_id: str, user_id: int) -> bool:
        """
        删除地址
        
        Args:
            db: 数据库会话
            address_id: 地址ID
            user_id: 用户ID（用于权限验证）
        
        Returns:
            bool: 是否删除成功
        """
        address = AddressService.get_address_by_id(db, address_id)
        if not address:
            raise ValueError(f"地址不存在: {address_id}")
        
        # 权限验证
        if address.user_id != user_id:
            raise PermissionError("无权访问此地址")
        
        was_default = address.is_default
        db.delete(address)
        db.commit()
        
        # 如果删除的是默认地址，自动设置新的默认地址
        if was_default:
            AddressService._auto_set_default_address(db, user_id)
        
        logger.info(f"地址删除成功: address_id={address_id}")
        return True
    
    @staticmethod
    def set_default_address(db: Session, address_id: str, user_id: int) -> Optional[Address]:
        """
        设置默认地址
        
        Args:
            db: 数据库会话
            address_id: 地址ID
            user_id: 用户ID（用于权限验证）
        
        Returns:
            Address: 更新后的地址
        """
        address = AddressService.get_address_by_id(db, address_id)
        if not address:
            raise ValueError(f"地址不存在: {address_id}")
        
        # 权限验证
        if address.user_id != user_id:
            raise PermissionError("无权访问此地址")
        
        # 取消其他默认地址
        AddressService._clear_default_addresses(db, user_id)
        
        # 设置当前地址为默认
        address.is_default = True
        db.commit()
        db.refresh(address)
        logger.info(f"默认地址设置成功: address_id={address_id}")
        return address
    
    @staticmethod
    def _clear_default_addresses(db: Session, user_id: int) -> None:
        """清除用户的所有默认地址标记（内部方法）"""
        db.query(Address).filter(
            Address.user_id == user_id,
            Address.is_default == True
        ).update({"is_default": False})
        db.commit()
    
    @staticmethod
    def _auto_set_default_address(db: Session, user_id: int) -> Optional[Address]:
        """自动设置默认地址（当默认地址被删除时调用）"""
        first_address = db.query(Address).filter(
            Address.user_id == user_id
        ).order_by(Address.created_at.desc()).first()
        
        if first_address:
            first_address.is_default = True
            db.commit()
            db.refresh(first_address)
            logger.info(f"自动设置默认地址: address_id={first_address.id}")
            return first_address
        
        return None
    
    @staticmethod
    def validate_address_data(data: Dict[str, str]) -> tuple[bool, str]:
        """
        验证地址数据
        
        Args:
            data: 地址数据字典
        
        Returns:
            tuple: (是否有效, 错误信息)
        """
        required_fields = ["name", "phone", "province", "city", "district", "detail"]
        
        for field in required_fields:
            if not data.get(field) or not data[field].strip():
                return False, f"{field} 不能为空"
        
        # 验证手机号格式（简单验证）
        phone = data.get("phone", "")
        if not phone.isdigit() or len(phone) != 11:
            return False, "手机号格式不正确"
        
        return True, ""
