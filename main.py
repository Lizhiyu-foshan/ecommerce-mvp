"""
E-Commerce MVP - 统一入口
单体架构（预留微服务迁移接口）
"""
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import time
import os

from database import engine, Base
from config.settings import settings
from config.logging_config import logger, RequestLogMiddleware

# 导入路由
from routers import auth, orders, payment, products, cart, addresses


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功!")
    logger.info(f"📊 架构模式: {settings.ARCHITECTURE_MODE}")
    logger.info(f"📝 日志级别: {settings.LOG_LEVEL}")
    yield
    # 关闭时清理资源
    logger.info("👋 应用关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="电商系统 MVP - 包含用户认证、商品管理、购物车、订单管理、支付处理、地址管理",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# 请求日志中间件
app.add_middleware(RequestLogMiddleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 注册路由
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(addresses.router)
app.include_router(orders.router)
app.include_router(payment.router)

# 静态文件服务（图片上传）
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/")
def root():
    """根路径 - API 信息"""
    logger.info("访问根路径 /")
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mode": settings.ARCHITECTURE_MODE,
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth",
            "products": "/api/v1/products",
            "cart": "/api/v1/cart",
            "addresses": "/api/v1/addresses",
            "orders": "/orders",
            "payment": "/payment"
        }
    }


@app.get("/health")
def health_check():
    """健康检查"""
    logger.debug("健康检查调用")
    return {
        "status": "healthy",
        "mode": settings.ARCHITECTURE_MODE,
        "database": "connected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
