"""
用户认证服务
整合自 module-auth
修复 bcrypt 兼容性问题
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt  # 直接使用 bcrypt 而不是 passlib
from sqlalchemy.orm import Session
from models import User
from models.schemas import UserCreate, UserUpdate
from config.settings import settings
from config.logging_config import logger, audit_log


class AuthService:
    """用户认证服务 - 单体模式"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码 - 使用原生 bcrypt"""
        try:
            # bcrypt 接受 bytes，需要编码
            plain_bytes = plain_password.encode('utf-8')
            hash_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(plain_bytes, hash_bytes)
        except Exception as e:
            logger.error(f"密码验证失败: {str(e)}")
            return False
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """生成密码哈希 - 使用原生 bcrypt"""
        # bcrypt 限制 72 字节，需要截断
        password_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    # ==================== CRUD 操作 ====================
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        logger.info(f"创建新用户: {user.username}")
        hashed_password = AuthService.get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"用户创建成功: ID={db_user.id}")
        audit_log("user_created", str(db_user.id), {"username": user.username})
        return db_user
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
        logger.info(f"更新用户: ID={user_id}")
        db_user = AuthService.get_user_by_id(db, user_id)
        if not db_user:
            logger.warning(f"用户不存在: ID={user_id}")
            return None
        
        update_data = user_update.dict(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = AuthService.get_password_hash(update_data.pop("password"))
            logger.info(f"用户 {user_id} 更新密码")
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        logger.info(f"用户更新成功: ID={user_id}")
        audit_log("user_updated", str(user_id), update_data)
        return db_user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        logger.info(f"删除用户: ID={user_id}")
        db_user = AuthService.get_user_by_id(db, user_id)
        if not db_user:
            logger.warning(f"删除失败，用户不存在: ID={user_id}")
            return False
        db.delete(db_user)
        db.commit()
        logger.info(f"用户删除成功: ID={user_id}")
        audit_log("user_deleted", str(user_id), {"username": db_user.username})
        return True


# 微服务预留：HTTP 客户端调用方式
# class AuthServiceClient:
#     """用户认证服务 - 微服务模式（HTTP 调用）"""
#     BASE_URL = settings.AUTH_SERVICE_URL
#     
#     @staticmethod
#     async def verify_token(token: str) -> Optional[dict]:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{AuthServiceClient.BASE_URL}/auth/verify",
#                 headers={"Authorization": f"Bearer {token}"}
#             )
#             if response.status_code == 200:
#                 return response.json()
#             return None
