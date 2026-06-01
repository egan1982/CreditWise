"""
Basic Auth 认证中间件 — 内网多用户版

功能：
- HTTP Basic Auth 认证（bcrypt 密码验证）
- 角色级别访问控制（admin/user）
- 账户锁定机制（连续失败 N 次后锁定）
- 登录审计日志
- 动态 CORS Origin 处理（兼容 credentials）
- 白名单路由（健康检查、API 文档、SSE 等）

请求流程：
    REQUEST → 白名单检查 → Basic Auth 验证 → 角色检查 → PASS/REJECT

Admin-only 路由（role=admin 才能访问）：
    /llm-manager/api/manage/*   — 渠道管理
    /llm-manager/api/logs/*     — API 日志
    /llm-manager/               — 管理页面
    /llm-manager/api/monitoring/* — 系统监控
"""

import base64
import time
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

import yaml
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

try:
    import bcrypt
except ImportError:
    bcrypt = None  # type: ignore

logger = logging.getLogger(__name__)


# =============================================================================
# 配置加载
# =============================================================================

def _find_config_path() -> Path:
    """查找 users.yaml 配置文件路径"""
    candidates = [
        Path(__file__).parent.parent / "config" / "users.yaml",
        Path("config") / "users.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "用户配置文件未找到！请创建 config/users.yaml\n"
        "参考：docs/online_multiuser_deployment_assessment.md 第 8 章"
    )


def load_users_config() -> dict:
    """加载用户配置"""
    config_path = _find_config_path()
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config or "users" not in config:
        raise ValueError("users.yaml 格式错误：缺少 users 字段")

    users = config["users"]
    if not users:
        raise ValueError("users.yaml 中没有配置任何用户")

    # 检查是否有占位符密码
    for user in users:
        if "PLACEHOLDER" in user.get("password_hash", ""):
            logger.warning(
                f"用户 {user['username']} 的密码是占位符！"
                f"请运行 python scripts/hash_password.py 生成真实哈希"
            )

    return config


# =============================================================================
# 白名单和 Admin 路由配置
# =============================================================================

# 不需要认证的路由前缀
AUTH_WHITELIST = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    # 前端静态资源（JS/CSS/图片等）
    "/_next",                    # Next.js 静态资源
    "/llm-manager/static",       # LLM Manager 静态资源
]

# 不需要认证的精确路径（非前缀匹配）
# "/" 和 "/favicon.ico" 只返回前端 HTML/图标，不含敏感数据
# 所有数据操作 API（/workspace/*、/sop/*、/v1/*）仍需认证
AUTH_WHITELIST_EXACT = [
    "/",
    "/favicon.ico",
]

# SSE 端点白名单（EventSource 不支持自定义 header）
SSE_WHITELIST_PATTERNS = [
    "/sop/status/",  # /sop/status/{id}/stream
]

# 仅 admin 可访问的路由前缀
ADMIN_ONLY_PREFIXES = [
    "/llm-manager/api/manage/",
    "/llm-manager/api/logs",
    "/llm-manager/api/monitoring/",
]

# LLM Manager 管理页面（非 API 路由）— 仅 admin
ADMIN_ONLY_EXACT = [
    "/llm-manager",
    "/llm-manager/",
]


def _is_whitelisted(path: str) -> bool:
    """检查路由是否在白名单中"""
    # 精确匹配（如 "/" 首页、"/favicon.ico"）
    if path in AUTH_WHITELIST_EXACT:
        return True
    # 前缀匹配
    for prefix in AUTH_WHITELIST:
        if path == prefix or path.startswith(prefix + "/"):
            return True
    for pattern in SSE_WHITELIST_PATTERNS:
        if pattern in path and path.endswith("/stream"):
            return True
    return False


def _is_admin_route(path: str) -> bool:
    """检查是否为 admin-only 路由"""
    for prefix in ADMIN_ONLY_PREFIXES:
        if path.startswith(prefix):
            return True
    for exact in ADMIN_ONLY_EXACT:
        if path == exact:
            return True
    return False


# =============================================================================
# 认证核心
# =============================================================================

class SimpleAuth:
    """Basic Auth 认证器"""

    def __init__(self):
        if bcrypt is None:
            raise ImportError(
                "bcrypt 未安装！请运行: pip install bcrypt\n"
                "或: pip install -r requirements.txt"
            )

        config = load_users_config()
        self.users = {u["username"]: u for u in config["users"]}
        settings = config.get("settings", {})
        self.max_failures = settings.get("max_login_failures", 5)
        self.lockout_duration = settings.get("lockout_duration_minutes", 15) * 60

        # 登录失败追踪: {username: {"count": int, "last_failure": float}}
        self._failure_tracker: dict = defaultdict(
            lambda: {"count": 0, "last_failure": 0.0}
        )

        logger.info(
            f"认证系统初始化完成：{len(self.users)} 个用户，"
            f"锁定阈值={self.max_failures}次，"
            f"锁定时长={self.lockout_duration // 60}分钟"
        )

    def _is_locked(self, username: str) -> bool:
        """检查账户是否被锁定"""
        tracker = self._failure_tracker.get(username)
        if not tracker:
            return False
        if tracker["count"] >= self.max_failures:
            elapsed = time.time() - tracker["last_failure"]
            if elapsed < self.lockout_duration:
                return True
            # 锁定时间已过，重置
            self._failure_tracker[username] = {"count": 0, "last_failure": 0.0}
        return False

    def _record_failure(self, username: str) -> None:
        """记录登录失败"""
        self._failure_tracker[username]["count"] += 1
        self._failure_tracker[username]["last_failure"] = time.time()

    def _reset_failures(self, username: str) -> None:
        """登录成功后重置"""
        self._failure_tracker[username] = {"count": 0, "last_failure": 0.0}

    def verify(self, username: str, password: str) -> Optional[dict]:
        """
        验证用户凭证

        Returns:
            成功返回用户字典，失败返回 None
        """
        user = self.users.get(username)
        if not user:
            # 即使用户不存在也做一次哈希运算，防止时序攻击泄露用户名
            bcrypt.hashpw(b"dummy_password", bcrypt.gensalt())
            return None

        stored_hash = user.get("password_hash", "").encode("utf-8")
        try:
            if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
                return None
        except Exception:
            return None

        # ★ 账户有效期检查（valid_until 字段，格式 YYYY-MM-DD，留空=永久有效）
        valid_until = user.get("valid_until", "")
        if valid_until and str(valid_until).strip():
            try:
                from datetime import date
                expiry = date.fromisoformat(str(valid_until).strip())
                if date.today() > expiry:
                    logger.warning(
                        f"账户已过期，拒绝登录: username={username}, valid_until={valid_until}"
                    )
                    return None  # 过期返回 None，触发 401
            except ValueError:
                logger.error(
                    f"users.yaml 中 valid_until 格式错误，保守拒绝: username={username}, value={valid_until}"
                )
                return None  # 格式错误时保守拒绝

        return user
        return None

    def authenticate(self, request: Request) -> dict:
        """
        从请求中提取并验证 Basic Auth 凭证

        Returns:
            认证成功的用户字典

        Raises:
            HTTPException: 认证失败
        """
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Basic "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization",
                headers={"WWW-Authenticate": "Basic realm=\"DeepAnalyze\""},
            )

        try:
            encoded = auth_header.split(" ", 1)[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
                headers={"WWW-Authenticate": "Basic realm=\"DeepAnalyze\""},
            )

        client_ip = request.client.host if request.client else "unknown"

        # 检查账户锁定
        if self._is_locked(username):
            logger.warning(f"账户锁定: {username} (IP: {client_ip})")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"账户已锁定，请 {self.lockout_duration // 60} 分钟后重试",
            )

        # 验证凭证
        user = self.verify(username, password)
        if not user:
            self._record_failure(username)
            remaining = self.max_failures - self._failure_tracker[username]["count"]
            logger.warning(
                f"登录失败: {username} (IP: {client_ip}, 剩余 {max(0, remaining)} 次)"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic realm=\"DeepAnalyze\""},
            )

        self._reset_failures(username)
        logger.info(f"登录成功: {username} (IP: {client_ip}, role: {user.get('role')})")
        return user


# =============================================================================
# FastAPI 中间件
# =============================================================================

class BasicAuthMiddleware(BaseHTTPMiddleware):
    """
    Basic Auth 认证中间件

    - 白名单路由直接放行
    - OPTIONS 预检请求放行（CORS）
    - 已认证请求检查角色权限
    - 动态设置 Access-Control-Allow-Origin（解决 credentials + wildcard 冲突）
    """

    def __init__(self, app, auth: SimpleAuth):
        super().__init__(app)
        self.auth = auth

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # 1. OPTIONS 预检请求：直接返回 CORS 头，不传给后续中间件
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            return self._patch_cors(request, response)

        # 2. 白名单路由放行
        if _is_whitelisted(path):
            response = await call_next(request)
            return self._patch_cors(request, response)

        # 3. 认证
        try:
            user = self.auth.authenticate(request)
        except HTTPException as exc:
            # 构造错误响应并补上 CORS 头
            response = JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=dict(exc.headers) if exc.headers else {},
            )
            return self._patch_cors(request, response)

        # 4. 角色检查：admin-only 路由
        if _is_admin_route(path):
            if user.get("role") != "admin":
                logger.warning(
                    f"权限拒绝: {user['username']} 尝试访问 {path}"
                )
                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "需要管理员权限"},
                )
                return self._patch_cors(request, response)

        # 5. 将用户信息存入 request.state 供后续路由使用
        request.state.user = user

        # 6. 执行后续路由
        response = await call_next(request)
        return self._patch_cors(request, response)

    def _patch_cors(self, request: Request, response: Response) -> Response:
        """
        动态设置 CORS Origin

        解决 allow_origins=* 与 credentials=true 不兼容的问题：
        将 Access-Control-Allow-Origin 设为请求的实际 Origin
        """
        origin = request.headers.get("origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Expose-Headers"] = "*"
        return response
