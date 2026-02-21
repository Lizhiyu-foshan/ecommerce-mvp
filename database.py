"""
统一数据库配置
单体架构：直接 SQLAlchemy
微服务预留：可切换为异步引擎 + 连接池
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings

# 数据库引擎（单体模式）
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    # 微服务预留：连接池配置
    # pool_size=10,
    # max_overflow=20,
    # pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """获取数据库会话 - 单体模式"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 微服务预留：异步数据库支持
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# async_engine = create_async_engine(settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"))
# AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
