"""
FastAPI集成适配器

提供简单的接口，用于将LLM API Manager集成到FastAPI应用中
"""

from typing import Optional, Dict, Any, Union
from fastapi import FastAPI
from ..api import create_pure_api_app, mount_to_fastapi


def integrate_llm_manager(
    app: FastAPI,
    prefix: str = "/api/llm-manager",
    config: Optional[Dict[str, Any]] = None
) -> FastAPI:
    """
    将LLM Manager集成到FastAPI应用
    
    Args:
        app: 目标FastAPI应用
        prefix: API路由前缀
        config: 配置字典
        
    Returns:
        LLM Manager应用实例
        
    Example:
        >>> from fastapi import FastAPI
        >>> from llm_api_manager.integration.fastapi import integrate_llm_manager
        >>> 
        >>> app = FastAPI()
        >>> llm_app = integrate_llm_manager(app)
        >>> 
        >>> # 访问 /api/llm-manager/docs 查看API文档
    """
    return mount_to_fastapi(app, prefix=prefix, config=config)


def create_llm_manager_app(
    config: Optional[Dict[str, Any]] = None
) -> FastAPI:
    """
    创建独立的LLM Manager应用
    
    Args:
        config: 配置字典
        
    Returns:
        LLM Manager应用实例
        
    Example:
        >>> from llm_api_manager.integration.fastapi import create_llm_manager_app
        >>> import uvicorn
        >>> 
        >>> app = create_llm_manager_app()
        >>> uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    return create_pure_api_app(config=config)


def configure_cors(
    app: FastAPI,
    allowed_origins: Union[str, list] = ["*"],
    allow_credentials: bool = True,
    allow_methods: Union[str, list] = ["*"],
    allow_headers: Union[str, list] = ["*"]
):
    """
    为FastAPI应用配置CORS
    
    Args:
        app: FastAPI应用
        allowed_origins: 允许的源
        allow_credentials: 是否允许凭证
        allow_methods: 允许的方法
        allow_headers: 允许的头部
        
    Example:
        >>> from fastapi import FastAPI
        >>> from llm_api_manager.integration.fastapi import configure_cors
        >>> 
        >>> app = FastAPI()
        >>> configure_cors(
        ...     app,
        ...     allowed_origins=["http://localhost:3000"],
        ...     allow_credentials=True
        ... )
    """
    from fastapi.middleware.cors import CORSMiddleware
    
    # 处理字符串参数
    if isinstance(allowed_origins, str):
        allowed_origins = [allowed_origins]
    if isinstance(allow_methods, str):
        allow_methods = [allow_methods]
    if isinstance(allow_headers, str):
        allow_headers = [allow_headers]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
    )