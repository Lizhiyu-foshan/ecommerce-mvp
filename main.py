"""
E-Commerce MVP - 统一入口
单体架构（预留微服务迁移接口）
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
from config.settings import settings

# 导入路由
from routers import auth, orders, payment


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功!")
    print(f"📊 架构模式: {settings.ARCHITECTURE_MODE}")
    yield
    # 关闭时清理资源
    print("👋 应用关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="电商系统 MVP - 包含用户认证、订单管理、支付处理",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

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
app.include_router(orders.router)
app.include_router(payment.router)


@app.get("/")
def root():
    """根路径 - API 信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mode": settings.ARCHITECTURE_MODE,
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth",
            "orders": "/orders",
            "payment": "/payment"
        }
    }


@app.get("/health")
def health_check():
    """健康检查"""
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
