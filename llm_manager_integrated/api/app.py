"""
FastAPI 应用工厂 - 支持前端集成

支持作为独立应用或子应用使用，包含前端静态文件服务。
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Any
import logging
from pathlib import Path
import os

from .responses import success_response, error_response
from .routes import channels, logs, monitoring
from .routes.proxy import proxy_router, models_router
from .html_processor import process_html_for_subapp
from llm_manager_integrated.models import orm
from llm_manager_integrated.models.database import DatabaseManager

logger = logging.getLogger(__name__)


def create_app(
    config: dict[str, Any] | None = None,
    as_subapp: bool = False,
    enable_frontend: bool = True,
    prefix: str = ""
) -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Args:
        config: 配置字典，包含 cors_origins, app_title 等
        as_subapp: 是否作为子应用（影响路由前缀和文档路径）
        enable_frontend: 是否启用前端静态文件服务
        prefix: 子应用的挂载前缀（如 '/llm'，用于正确挂载静态文件）
    
    Returns:
        FastAPI 应用实例
    
    Examples:
        # 独立应用
        app = create_app()
        
        # 作为子应用集成到现有项目
        from fastapi import FastAPI
        main_app = FastAPI()
        llm_manager = create_app(as_subapp=True)
        main_app.mount("/llm-manager", llm_manager)
        
        # 自定义配置
        config = {
            "cors_origins": ["http://localhost:3000"],
            "app_title": "LLM API Manager"
        }
        app = create_app(config=config)
    """
    # 使用提供的配置或创建默认配置
    if config is None:
        config = {}
    
    cors_origins = config.get("cors_origins", ["http://localhost:3000", "http://localhost:8000"])
    app_title = config.get("app_title", "LLM API Manager")
    app_description = config.get("app_description", "集成前端的大模型 API 管理和代理系统")
    
    # 创建 FastAPI 应用
    app_kwargs = {
        "title": app_title,
        "description": app_description,
        "version": "2.0.0",
    }
    
    # 如果是子应用，调整文档路径
    if as_subapp:
        app_kwargs.update({
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json"
        })
    
    app = FastAPI(**app_kwargs)
    
    # 应用启动事件
    @app.on_event("startup")
    async def startup_event():
        import logging
        logger = logging.getLogger(__name__)
        logger.info("应用启动事件开始执行...")
        
        from llm_manager_integrated.core.startup import app_startup_handler
        from llm_manager_integrated.core.load_balancer import get_load_balancer
        
        # 获取负载均衡器实例并存储在应用状态中
        load_balancer = get_load_balancer()
        logger.info(f"获取到负载均衡器实例: {id(load_balancer)}")
        app.state.load_balancer = load_balancer
        
        # 将渠道加载到同一个负载均衡器实例
        from llm_manager_integrated.core.startup import load_channels_to_load_balancer
        success, message = await load_channels_to_load_balancer(load_balancer)
        if success:
            logger.info(f"渠道加载成功: {message}, 负载均衡器中的渠道数: {len(load_balancer.channels)}")
        else:
            logger.warning(f"渠道加载失败，但应用将继续启动: {message}")
        
        # 执行其他应用启动逻辑
        await app_startup_handler(app)
        logger.info("应用启动事件执行完成")
    
    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # HTTP异常处理
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # 添加调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"HTTP异常处理器被调用: {exc.status_code}, detail类型: {type(exc.detail)}, detail内容: {exc.detail}")
        
        # 检查detail是否已经是标准格式的错误响应
        if isinstance(exc.detail, dict) and 'code' in exc.detail and 'message' in exc.detail:
            # 如果已经是标准格式，直接返回
            logger.info(f"使用标准格式错误响应: {exc.detail}")
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail
            )
        else:
            # 如果不是标准格式，转换为标准格式
            logger.info(f"转换为标准格式错误响应: {exc.detail}")
            return JSONResponse(
                status_code=exc.status_code,
                content=error_response(
                    code=exc.status_code,
                    message=str(exc.detail)
                )
            )
    
    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"全局异常: {exc}", exc_info=True)
        
        # 检查是否是HTTPException，如果是，使用HTTP异常处理器
        if isinstance(exc, HTTPException):
            logger.warning(f"全局异常处理器捕获到HTTPException，转发给HTTP异常处理器: {exc.status_code}, {exc.detail}")
            # 调用HTTP异常处理器
            return await http_exception_handler(request, exc)
        
        return JSONResponse(
            status_code=500,
            content=error_response(
                code=500,
                message="服务器内部错误"
            )
        )
    
    # 存储配置到应用状态
    app.state.config = config
    
    # 初始化数据库管理器
    from llm_manager_integrated.core.config import settings
    db_manager = DatabaseManager(settings.database_url)
    app.state.db_manager = db_manager
    
    # 创建数据库表
    db_manager.create_tables()
    
    # 健康检查
    @app.get("/health", tags=["通用"])
    def health_check():
        return success_response(
            data={"status": "healthy"},
            message="服务健康"
        )
    
    # 配置信息端点
    @app.get("/api/config", tags=["配置"])
    def get_config():
        """获取前端配置信息"""
        return success_response(
            data={
                "app_title": app_title,
                "app_description": app_description,
                "version": "2.0.0",
                "api_base_url": "/api",
                "theme": config.get("theme", "light"),
                "features": config.get("features", {})
            },
            message="配置获取成功"
        )
    
    # 注册 API 路由
    app.include_router(channels.router, prefix="/api/manage", tags=["渠道管理"])
    app.include_router(logs.router, prefix="/api", tags=["日志管理"])
    app.include_router(proxy_router, prefix="/api/proxy", tags=["API代理"])
    app.include_router(models_router, prefix="/api", tags=["模型管理"])
    app.include_router(monitoring.router, prefix="/api/monitoring", tags=["系统监控"])
    
    # 挂载前端静态文件 & SPA 路由处理
    if enable_frontend:
        static_dir = Path(__file__).parent.parent / "static"
        
        logger.debug(f"Frontend enabled. Static dir: {static_dir}, Exists: {static_dir.exists()}")
        logger.info(f"[DEBUG] enable_frontend={enable_frontend}, static_dir.exists()={static_dir.exists()}")
        
        if static_dir.exists():
            logger.info("[DEBUG] Static dir exists, registering HTML routes")
            # 使用 StaticFiles 处理静态文件
            # 直接 mount 到 /static（不使用前缀，因为会在路由级别处理）
            static_dir_abs = os.path.abspath(static_dir)
            logger.info(f"[DEBUG] Setting up static files from: {static_dir_abs}")
            # 根路径 - 返回前端 HTML（优先级高于 SPA catch-all 路由）
            @app.get("/", tags=["前端"], include_in_schema=False)
            async def serve_root():
                """返回前端主页 HTML"""
                logger.info("[DEBUG] serve_root called")
                index_file = static_dir / "index.html"
                if index_file.exists():
                    with open(index_file, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    # 替换资源路径，添加前缀
                    if prefix:
                        # 替换绝对路径，添加前缀
                        html_content = (
                            html_content
                            .replace('href="/', f'href="{prefix}/')
                            .replace('src="/', f'src="{prefix}/')
                        )
                    return HTMLResponse(content=html_content)
                
                return JSONResponse(
                    status_code=404,
                    content=error_response(code=404, message="前端文件不存在")
                )
            
            # SPA 路由处理 - 所有未匹配的路由返回 index.html
            @app.get("/{full_path:path}", tags=["前端"], include_in_schema=False)
            async def serve_spa(full_path: str):
                """SPA 路由处理 - 为所有非 API 路由返回 index.html"""
                # 排除 API 路由（这些已由前面的 include_router 处理）
                if full_path.startswith("api/"):
                    return JSONResponse(
                        status_code=404,
                        content=error_response(code=404, message="API 端点不存在")
                    )
                
                # 静态文件由主 app 的 /llm-manager-static/ 路由提供
                
                # 返回 index.html（前端 SPA 路由处理）
                index_file = static_dir / "index.html"
                if index_file.exists():
                    with open(index_file, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    # 替换资源路径，添加前缀
                    if prefix:
                        html_content = (
                            html_content
                            .replace('href="/', f'href="{prefix}/')
                            .replace('src="/', f'src="{prefix}/')
                        )
                    return HTMLResponse(content=html_content)
                
                return JSONResponse(
                    status_code=404,
                    content=error_response(code=404, message="页面不存在")
                )
        else:
            # 前端静态文件不存在，添加 API only 模式的根路由
            @app.get("/", tags=["通用"], include_in_schema=False)
            def read_root():
                """API 只读模式下的根路由"""
                return success_response(
                    data={
                        "message": "欢迎使用 LLM API Manager",
                        "version": "2.0.0",
                        "mode": "api_only"
                    },
                    message="服务正常"
                )
            
            logger.warning(f"前端静态文件目录不存在: {static_dir}，使用 API Only 模式")
    else:
        # 禁用前端时的根路由
        @app.get("/", tags=["通用"], include_in_schema=False)
        def read_root():
            """API 服务根路由"""
            return success_response(
                data={
                    "message": "欢迎使用 LLM API Manager",
                    "version": "2.0.0",
                    "mode": "subapp" if as_subapp else "standalone"
                },
                message="服务正常"
            )
    
    return app


# 便捷函数：创建独立应用
def create_standalone_app(config: dict[str, Any] | None = None) -> FastAPI:
    """创建独立运行的应用"""
    return create_app(config=config, as_subapp=False, enable_frontend=True)


# 便捷函数：创建子应用
def create_subapp(config: dict[str, Any] | None = None) -> FastAPI:
    """创建可集成到其他 FastAPI 应用的子应用"""
    return create_app(config=config, as_subapp=True, enable_frontend=False)
