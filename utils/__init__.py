"""
事务管理工具
提供数据库事务装饰器和上下文管理器
"""
from functools import wraps
from typing import Callable, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from config.logging_config import logger


def transactional(func: Callable) -> Callable:
    """
    事务装饰器
    
    自动处理数据库事务的提交和回滚。
    如果函数执行成功，自动提交事务；
    如果发生异常，自动回滚事务并抛出异常。
    
    要求被装饰函数的第一个参数必须是 db: Session
    
    用法:
        @transactional
        def create_order(db: Session, user_id: int, ...):
            # 业务逻辑
            pass
    """
    @wraps(func)
    def wrapper(db: Session, *args, **kwargs):
        try:
            result = func(db, *args, **kwargs)
            db.commit()
            logger.debug(f"事务提交成功: {func.__name__}")
            return result
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"数据库错误，事务回滚: {func.__name__}, 错误: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"业务错误，事务回滚: {func.__name__}, 错误: {e}")
            raise
    return wrapper


class TransactionContext:
    """
    事务上下文管理器
    
    用于需要在代码块级别控制事务的场景
    
    用法:
        with TransactionContext(db) as tx:
            # 执行业务操作
            tx.db.add(order)
            # 如果发生异常，自动回滚
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.committed = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # 没有异常，提交事务
            try:
                self.db.commit()
                self.committed = True
                logger.debug("事务上下文提交成功")
            except SQLAlchemyError as e:
                self.db.rollback()
                logger.error(f"事务上下文提交失败，已回滚: {e}")
                raise
        else:
            # 发生异常，回滚事务
            self.db.rollback()
            logger.error(f"事务上下文发生异常，已回滚: {exc_val}")
        return False  # 不抑制异常
    
    def commit(self):
        """手动提交事务"""
        try:
            self.db.commit()
            self.committed = True
            logger.debug("事务手动提交成功")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"事务手动提交失败，已回滚: {e}")
            raise
    
    def rollback(self):
        """手动回滚事务"""
        self.db.rollback()
        self.committed = False
        logger.debug("事务手动回滚")


def safe_commit(db: Session, operation_name: str = "操作") -> bool:
    """
    安全提交事务
    
    尝试提交事务，如果失败则回滚并记录日志
    
    Args:
        db: 数据库会话
        operation_name: 操作名称，用于日志记录
    
    Returns:
        bool: 是否提交成功
    """
    try:
        db.commit()
        logger.debug(f"{operation_name} 提交成功")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{operation_name} 提交失败，已回滚: {e}")
        return False
