"""
日志配置模块
支持多级别日志、文件轮转、结构化输出
"""
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from config.settings import settings


# 日志目录
LOG_DIR = Path("/root/.openclaw/workspace/projects/ecommerce-mvp/logs")
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# JSON格式（用于结构化日志）
JSON_FORMAT = '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "file": "%(filename)s", "line": %(lineno)d, "message": "%(message)s"}'


def setup_logging(
    log_level: str = "INFO",
    enable_file: bool = True,
    enable_console: bool = True,
    json_format: bool = False
) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        enable_file: 是否启用文件日志
        enable_console: 是否启用控制台日志
        json_format: 是否使用JSON格式
    
    Returns:
        配置好的logger实例
    """
    # 获取日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 创建logger
    logger = logging.getLogger("ecommerce")
    logger.setLevel(level)
    
    # 清除已有处理器
    logger.handlers.clear()
    
    # 选择格式
    fmt = JSON_FORMAT if json_format else LOG_FORMAT
    formatter = logging.Formatter(fmt, datefmt=DATE_FORMAT)
    
    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 文件处理器 - 主日志（按大小轮转）
    if enable_file:
        # 主应用日志 - 按大小轮转（10MB，保留5个备份）
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 错误日志 - 单独记录ERROR及以上级别
        error_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "error.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        # 访问日志 - 单独记录（用于分析）
        access_handler = logging.handlers.TimedRotatingFileHandler(
            LOG_DIR / "access.log",
            when="midnight",  # 每天午夜轮转
            interval=1,
            backupCount=30,  # 保留30天
            encoding="utf-8"
        )
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(formatter)
        logger.addHandler(access_handler)
    
    return logger


# 创建默认logger
logger = setup_logging(
    log_level=settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "INFO",
    enable_file=True,
    enable_console=settings.DEBUG if hasattr(settings, "DEBUG") else False
)


class RequestLogMiddleware:
    """请求日志中间件 - 记录HTTP请求"""
    
    def __init__(self, app):
        self.app = app
        self.access_logger = logging.getLogger("ecommerce.access")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = datetime.now()
            
            # 记录请求信息
            method = scope.get("method", "UNKNOWN")
            path = scope.get("path", "UNKNOWN")
            client = scope.get("client", ("unknown", 0))[0]
            
            self.access_logger.info(f"Request started: {method} {path} from {client}")
            
            # 包装send以捕获响应状态
            async def wrapped_send(message):
                if message["type"] == "http.response.start":
                    status_code = message.get("status", 0)
                    duration = (datetime.now() - start_time).total_seconds() * 1000
                    self.access_logger.info(
                        f"Request completed: {method} {path} - Status: {status_code} - Duration: {duration:.2f}ms"
                    )
                await send(message)
            
            await self.app(scope, receive, wrapped_send)
        else:
            await self.app(scope, receive, send)


def log_function_call(func):
    """装饰器：记录函数调用"""
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        module_name = func.__module__
        logger.debug(f"Calling {module_name}.{func_name}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{module_name}.{func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{module_name}.{func_name} failed: {str(e)}", exc_info=True)
            raise
    
    return wrapper


def audit_log(action: str, user_id: str = None, details: dict = None):
    """
    审计日志 - 记录敏感操作
    
    Args:
        action: 操作名称
        user_id: 用户ID
        details: 操作详情
    """
    audit_logger = logging.getLogger("ecommerce.audit")
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "user_id": user_id or "anonymous",
        "details": details or {}
    }
    
    audit_logger.info(f"AUDIT: {log_entry}")
