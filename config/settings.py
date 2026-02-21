"""
E-Commerce MVP - Unified Configuration
单体架构配置（预留微服务迁移配置）
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置 - 支持单体和微服务两种模式"""
    
    # 应用信息
    APP_NAME: str = "E-Commerce MVP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 架构模式: "monolithic" | "microservice"
    ARCHITECTURE_MODE: str = "monolithic"
    
    # 数据库配置（单体模式使用 SQLite，微服务模式可切换 PostgreSQL）
    DATABASE_URL: str = "sqlite:///./ecommerce.db"
    # 微服务模式预留: POSTGRES_URL: str = "postgresql://user:pass@localhost/ecommerce"
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS 配置
    CORS_ORIGINS: list = ["*"]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"  # DEBUG/INFO/WARNING/ERROR/CRITICAL
    LOG_DIR: str = "/root/.openclaw/workspace/projects/ecommerce-mvp/logs"
    
    # 微服务通信预留配置
    # AUTH_SERVICE_URL: str = "http://auth-service:8000"
    # ORDER_SERVICE_URL: str = "http://order-service:8000"
    # PAYMENT_SERVICE_URL: str = "http://payment-service:8000"
    
    # 缓存预留（Redis）
    # REDIS_URL: str = "redis://localhost:6379/0"
    
    # 消息队列预留（RabbitMQ/Celery）
    # CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
