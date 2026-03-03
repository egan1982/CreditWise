"""
纯API应用工厂 - 专为集成到目标项目设计

不包含任何前端静态文件服务，仅提供API功能。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import logging

from .routes import channels, logs, monitoring
from .routes.proxy import proxy_router
from .responses import success_response, error_response
from ..models import orm
from ..models.database import DatabaseManager

logger = logging.getLogger(__name__)


def create_pure_api_app(
    config: Optional[Dict[str, Any]] = None,
    prefix: str = ""
) -> FastAPI:
    """
    创建纯API应用，用于集成到目标项目
    
    Args:
        config: 配置字典，包含 cors_origins, app_title 等
        prefix: API路由前缀，用于避免路由冲突
    
    Returns:
        FastAPI应用实例
    """
    # 使用提供的配置或创建默认配置
    if config is None:
        config = {}
    
    cors_origins = config.get("cors_origins", ["http://localhost:3000", "http://localhost:8000"])
    app_title = config.get("app_title", "LLM API Manager")
    app_description = config.get("app_description", "LLM API管理和代理系统")
    
    # 创建 FastAPI 应用
    app = FastAPI(
        title=app_title,
        description=app_description,
        version="2.0.0",
        docs_url=f"{prefix}/docs" if prefix else "/docs",
        redoc_url=f"{prefix}/redoc" if prefix else "/redoc",
        openapi_url=f"{prefix}/openapi.json" if prefix else "/openapi.json"
    )
    
    # 应用启动事件
    @app.on_event("startup")
    async def startup_event():
        from ..core.startup import app_startup_handler
        await app_startup_handler(app)
    
    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 存储配置到应用状态
    app.state.config = config
    
    # 初始化数据库管理器
    from ..core.config import settings
    db_manager = DatabaseManager(settings.database_url)
    app.state.db_manager = db_manager
    
    # 创建数据库表
    db_manager.create_tables()
    
    # 健康检查
    @app.get(f"{prefix}/health" if prefix else "/health", tags=["通用"])
    def health_check():
        return success_response(
            data={"status": "healthy"},
            message="LLM Manager API服务正常"
        )
    
    # 配置信息端点
    @app.get(f"{prefix}/config" if prefix else "/config", tags=["配置"])
    def get_config():
        """获取前端配置信息"""
        return success_response(
            data={
                "app_title": app_title,
                "app_description": app_description,
                "version": "2.0.0",
                "api_base_url": prefix or "/api",
                "theme": config.get("theme", "light"),
                "features": config.get("features", {})
            },
            message="配置获取成功"
        )
    
    # 注册 API 路由
    api_prefix = f"{prefix}/api" if prefix else "/api"
    app.include_router(channels.router, prefix=f"{api_prefix}/manage", tags=["渠道管理"])
    app.include_router(logs.router, prefix=api_prefix, tags=["日志管理"])
    app.include_router(proxy_router, prefix=f"{api_prefix}/proxy", tags=["API代理"])
    app.include_router(monitoring.router, prefix=f"{api_prefix}/monitoring", tags=["系统监控"])
    
    return app


# 便捷函数，用于直接集成到FastAPI应用
def mount_to_fastapi(
    main_app: FastAPI, 
    prefix: str = "/api/llm-manager",
    config: Optional[Dict[str, Any]] = None
) -> FastAPI:
    """
    将LLM Manager API集成到现有FastAPI应用
    
    Args:
        main_app: 目标FastAPI应用
        prefix: 挂载前缀
        config: 配置字典
    
    Returns:
        LLM Manager API应用实例
    """
    llm_app = create_pure_api_app(config=config, prefix="")
    main_app.mount(prefix, llm_app)
    return llm_app