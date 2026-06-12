"""
Dynamic CORS Middleware

替代 Starlette CORSMiddleware，解决 allow_origins=["*"] + allow_credentials=True
违反 CORS 规范导致浏览器拒绝请求的问题。

实现方式：将所有请求的 Access-Control-Allow-Origin 动态设置为实际的 Origin 头，
而非硬编码 "*"。同时处理 OPTIONS 预检请求。
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """
    动态 CORS 中间件
    
    - OPTIONS 预检：直接返回 200 + 完整 CORS 头
    - 其他请求：透传到下游，在响应上附加 CORS 头
    
    与 BasicAuthMiddleware._patch_cors 兼容：
    两个中间件设置相同的 Origin 值，双重设置幂等无害。
    """

    async def dispatch(self, request: Request, call_next):
        # OPTIONS preflight — handle immediately, bypass auth middleware
        if request.method == "OPTIONS":
            return self._build_preflight_response(request)

        # Normal request — pass through, patch CORS on response
        response = await call_next(request)
        self._patch_cors_headers(request, response)
        return response

    def _patch_cors_headers(self, request: Request, response: Response) -> None:
        """
        将 CORS 响应头设置为请求的实际 Origin。
        
        不覆盖已存在的同名头（BasicAuthMiddleware._patch_cors 已设置时保留原值）。
        """
        origin = request.headers.get("origin")
        if not origin:
            return
        # 只在头部未设置时才写入，避免覆盖 BasicAuthMiddleware 的输出
        if "Access-Control-Allow-Origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = origin
        if "Access-Control-Allow-Credentials" not in response.headers:
            response.headers["Access-Control-Allow-Credentials"] = "true"

    def _build_preflight_response(self, request: Request) -> Response:
        """构建 OPTIONS 预检响应"""
        origin = request.headers.get("origin", "")
        response = Response(status_code=200)
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = (
            request.headers.get("access-control-request-headers", "")
            or "Content-Type, Authorization, X-Requested-With"
        )
        response.headers["Access-Control-Max-Age"] = "86400"  # 24h cache
        return response
