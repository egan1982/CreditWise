"""
API模块 - 提供纯API和带前端的API两种模式

可以根据集成需求选择使用：
1. 纯API模式：仅提供API功能，不包含任何前端静态文件
2. 集成前端模式：包含前端静态文件服务（兼容旧版）
"""

from .app import create_app, create_standalone_app, create_subapp
from .pure_app import create_pure_api_app, mount_to_fastapi
from .responses import success_response, error_response
from .routes import channels, logs, proxy, monitoring

__all__ = [
    # 原有函数（兼容性）
    'create_app',
    'create_standalone_app', 
    'create_subapp',
    # 新增纯API函数（推荐用于集成）
    'create_pure_api_app',
    'mount_to_fastapi',
    # 路由模块
    'channels',
    'logs',
    'proxy',
    'monitoring'
]
