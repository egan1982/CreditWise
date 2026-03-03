"""代理路由模块"""

from .proxy import router as proxy_router
from .models_proxy import router as models_router

__all__ = ["proxy_router", "models_router"]