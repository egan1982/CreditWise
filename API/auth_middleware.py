"""
自定义 CWAuth 认证中间件 — 内网多用户版

功能：
- 自定义 `CWAuth` 认证方案（bcrypt 密码验证；用户管理模块 批次3/2026-07-03
  从标准 `Basic` 改名为自定义方案名，编码方式仍是 base64("user:pass") 不变，
  仅 Authorization 头前缀不同——目的是让浏览器不再对凭证做原生识别/缓存/
  自动重发，彻底解决"生产模式下退出登录后浏览器又自动用旧账号登录"的问题，
  详见 `SimpleAuth.authenticate` docstring）
- 角色级别访问控制（admin/user）
- 账户锁定机制（连续失败 N 次后锁定）
- 登录审计日志
- 动态 CORS Origin 处理（兼容 credentials）
- 白名单路由（健康检查、API 文档、SSE、"/"及"/llm-manager"页面壳子等）

请求流程：
    REQUEST → 白名单检查 → CWAuth 凭证验证 → 角色检查 → PASS/REJECT

Admin-only 路由（role=admin 才能访问）：
    /llm-manager/api/manage/*   — 渠道管理
    /llm-manager/api/logs/*     — API 日志
    /llm-manager/api/monitoring/* — 系统监控
"""

import base64
import json
import time
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

import yaml
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from starlette.concurrency import run_in_threadpool

try:
    import bcrypt
except ImportError:
    bcrypt = None  # type: ignore

logger = logging.getLogger(__name__)


# =============================================================================
# 配置加载
# =============================================================================

def _find_config_path() -> Path:
    """查找 users.yaml 配置文件路径

    用 is_file() 而非 exists()：Docker bind mount 一个宿主机不存在的文件路径时，
    Docker 会在容器内自动创建一个同名空目录（而非文件）来兜底——若用 exists() 判断，
    这个"意外生成的空目录"会被误判为"配置已存在"，随后 open() 时抛出
    IsADirectoryError（而非本函数约定的 FileNotFoundError），导致上层
    SimpleAuth/零账户自动兜底逻辑（见 API/main.py _ensure_bootstrap_admin_if_empty）
    的异常类型判断失效，静默退化为无鉴权。is_file() 对目录返回 False，
    使这种情况被正确视为"配置不存在"，保持异常类型契约一致。
    """
    candidates = [
        Path(__file__).parent.parent / "config" / "users.yaml",
        Path("config") / "users.yaml",
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "用户配置文件未找到！请创建 config/users.yaml\n"
        "参考：docs/online_multiuser_deployment_assessment.md 第 8 章"
    )

def _get_state_path() -> Path:
    """获取登录失败状态文件路径（与 users.yaml 同级）"""
    return Path(__file__).parent.parent / "config" / "login_state.json"


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
    "/llm-manager/static",       # LLM Manager 静态资源（生产同源部署）
    # 用户管理模块 批次2 补充加固（2026-07-02）：LLM Manager 开发模式静态资源
    # （main.py 里 _serve_llm_frontend_asset 提供的 /llm-manager/scripts/*、
    # /llm-manager/shared/* 两个路由，对应源码目录而非构建产物）。这些是纯前端
    # 静态代码/样式文件，本身不含敏感数据，公开可读没有安全问题；且必须白名单
    # 放行——浏览器 <script src>/<link> 标签加载资源不会带 Authorization 头，
    # 若被鉴权拦截会直接 404/401，导致 LLM Manager 页面 main.js 加载失败，
    # 表现为渠道列表卡在"加载中"、各 Tab 点击无响应（与此前修复的开发模式
    # 404 问题是同一组文件，但这次是被鉴权拦住，而非路由缺失）。
    "/llm-manager/scripts",
    "/llm-manager/shared",
]


# 不需要认证的精确路径（非前缀匹配）
# "/" 和 "/favicon.ico" 只返回前端 HTML/图标，不含敏感数据
# 所有数据操作 API（/workspace/*、/sop/*、/v1/*）仍需认证
# "/auth/mode" 用户管理模块 批次2 Phase10：登录前需探测是否启用认证，供前端决定是否渲染登录框
#
# 用户管理模块 批次3（2026-07-03）：新增 "/"、"/llm-manager"、"/llm-manager/" 三个
# 页面壳白名单，修复"生产模式下退出登录无法切换账号"的技术债。
#
# 根因回顾：此前整页导航访问这些路径时，若未认证，中间件会保留
# `WWW-Authenticate` 响应头触发浏览器**原生** Basic Auth 弹窗；一旦用户通过原生
# 弹窗登录成功一次，浏览器会把凭证与"域名+realm"绑定长期缓存——JS 层
# `clearAuth()` 清 localStorage 对这份浏览器原生缓存完全无效，导致刷新页面后
# 自动用旧凭证重新登录，无法切换账号（浏览器无痕/隐私窗口经实测也不能可靠规避，
# 见 docs/project_status_summary.md 第20项限制①）。
#
# 修复思路：这两个页面都是纯静态导出的 SPA 壳子（demo/chat 是
# `output:'export'` 的 Next.js 静态导出；llm_manager_integrated/frontend 是
# Vite 构建产物），HTML/JS 本身不含任何用户数据，公开加载无安全风险。真正需要
# 判断身份的动作全部发生在 JS 加载完成后主动发起的 AJAX 请求（`/auth/me`、
# `/llm-manager/api/manage/*` 等），这些请求走的是 authFetch/全局 fetch 拦截器
# （demo/chat 的 lib/config.ts、llm_manager_integrated 的 shared/js/auth.js），
# 401 响应已经主动去掉 WWW-Authenticate 头（见下方 dispatch() 第591行注释），
# 只会弹自定义登录框，不会触发浏览器原生弹窗，从而也不会产生原生凭证缓存——这正是
# 本机开发模式（Next dev server :3000 独立于本中间件之外）从未出现此问题的原因，
# 现在让生产模式的页面壳子复用同一条已验证有效的鉴权路径。
#
# 安全边界：仅豁免"页面壳子"这三个路径本身的 HTTP 层认证/角色前置检查，不代表
# 放开权限——`/llm-manager/api/manage/*` 等真正的管理操作 API 仍在
# ADMIN_ONLY_PREFIXES 里强制要求 admin 角色（403），`/llm-manager` 原来挂在
# ADMIN_ONLY_EXACT 的角色前置检查一并移除（见下方该常量的说明），角色判断改为
# 与 `/user-manager` 等其它 admin 专属前端路由一致的模式——由前端 JS 根据
# `/auth/me` 返回的 role 字段决定渲染什么内容，真正的数据操作仍受后端 API 层
# 强制拦截，不因页面壳子公开而放宽。
AUTH_WHITELIST_EXACT = [
    "/favicon.ico",
    "/placeholder-logo.png",
    "/placeholder-user.jpg",
    "/auth/mode",
    "/",
    "/llm-manager",
    "/llm-manager/",
]

# 静态资源后缀白名单（浏览器直接加载，无法注入 Authorization header）
# 这类请求返回 401 会触发浏览器原生 Basic Auth 弹窗
AUTH_WHITELIST_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".css", ".map",
}

# SSE 端点白名单（EventSource 不支持自定义 header）
SSE_WHITELIST_PATTERNS = [
    "/sop/status/",  # /sop/status/{id}/stream
]

# 仅 admin 可访问的路由前缀
ADMIN_ONLY_PREFIXES = [
    "/llm-manager/api/manage/",
    "/llm-manager/api/logs",
    "/llm-manager/api/monitoring/",
    "/admin/",  # 用户管理模块 批次1 Phase6：账户合并等admin专属接口统一前缀
]

# 用户管理模块 批次2 补充加固（2026-07-02）：ADMIN_ONLY_PREFIXES 例外白名单。
#
# 背景：`/llm-manager/api/manage/` 这个前缀下混杂了两类接口——真正的渠道管理
# 操作（创建/编辑/删除渠道，理应 admin-only）和少数"只读、供所有用户使用"的接口
# （如 `/channels/active-configs`，后端注释明确写着"用于三列式前端选择"——
# `demo/chat/components/ModelSelector.tsx` 里聊天界面的模型下拉框就是调这个接口
# 获取可选渠道列表）。粗粒度按前缀整体拦截，导致普通用户点开模型选择器直接收到
# 403，表现为"无可用配置"，即使管理员已经配置好了渠道。
#
# 这里用精确路径做例外豁免（而非放宽整个前缀，避免误放行真正的管理操作），
# 后续如有新的"只读、面向全体用户"的 manage/ 子路径，在此追加即可。
ADMIN_PREFIX_EXCEPTIONS = [
    "/llm-manager/api/manage/channels/active-configs",
]

# LLM Manager 管理页面（非 API 路由）— 角色前置检查
#
# 用户管理模块 批次3（2026-07-03）：`/llm-manager`、`/llm-manager/` 已上移至
# `AUTH_WHITELIST_EXACT`（页面壳子公开，理由见该常量上方注释），中间件层面的
# `_is_whitelisted()` 会在 dispatch() 第2步直接放行，永远不会走到下方
# `_is_admin_route()` 的角色检查这一步——此列表因此保持为空，仅作为历史记录/
# 类型占位保留。真正的 admin 权限边界现在完全由 `ADMIN_ONLY_PREFIXES` 里的
# `/llm-manager/api/manage/*` 等数据操作 API 承担（非 admin 用户加载页面壳子后，
# 调用这些 API 仍会收到 403，行为与 `/user-manager` 等其它 admin 专属前端路由
# 一致：页面本身不做服务端拦截，权限判断下放到 API 调用层 + 前端按 role 决定
# 渲染内容）。
ADMIN_ONLY_EXACT: list[str] = []


def _is_whitelisted(path: str) -> bool:
    """检查路由是否在白名单中"""
    # 精确匹配（如 "/" 首页、"/favicon.ico"）
    if path in AUTH_WHITELIST_EXACT:
        return True
    # 前缀匹配
    for prefix in AUTH_WHITELIST:
        if path == prefix or path.startswith(prefix + "/"):
            return True
    # SSE 端点
    for pattern in SSE_WHITELIST_PATTERNS:
        if pattern in path and path.endswith("/stream"):
            return True
    # 静态资源后缀匹配（图片/字体/CSS 等，浏览器直接加载无法带认证头）
    _, _, ext = path.rpartition(".")
    if ext and f".{ext.lower()}" in AUTH_WHITELIST_EXTENSIONS:
        return True
    return False


def _is_admin_route(path: str) -> bool:
    """检查是否为 admin-only 路由"""
    if path in ADMIN_PREFIX_EXCEPTIONS:
        return False
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

        # 用户管理模块 批次2 Phase10：账号数据源切换（users表 vs config/users.yaml）
        # 见 docs/user_management_module_design.md §十三："导入后 users.yaml 仅作为
        # 灾备/离线场景兜底保留，正常运行时以数据库为准"。
        # 启动时仅用于决定 yaml 是否必须存在（见下方 try/except）；实际每次登录走哪条
        # 路径由 self._is_db_backed_now() 在 verify() 里实时判断（而非缓存启动时的结果），
        # 这样 admin 通过 /admin/users 创建首个账户、或运维事后执行迁移脚本后，
        # 无需重启服务即可立即切换到数据库模式登录。
        db_backed_at_startup = self._is_db_backed_now()

        # yaml 仍尝试加载：数据库模式下作为灾备信息（不强制要求存在）；
        # 非数据库模式下（未迁移）是唯一数据源，必须存在，沿用原有报错行为。
        try:
            config = load_users_config()
            self.users = {u["username"]: u for u in config["users"]}
            settings = config.get("settings", {})
        except FileNotFoundError:
            if not db_backed_at_startup:
                raise  # 非数据库模式下 yaml 是唯一数据源，缺失必须报错，维持原有行为
            self.users = {}
            settings = {}
            logger.info("config/users.yaml 未找到（数据库模式下允许缺失，作为灾备兜底的可选文件）")

        self.max_failures = settings.get("max_login_failures", 5)
        self.lockout_duration = settings.get("lockout_duration_minutes", 15) * 60

        # 登录失败追踪: {username: {"count": int, "last_failure": float}}
        self._failure_tracker: dict = defaultdict(
            lambda: {"count": 0, "last_failure": 0.0}
        )
        
        # 从磁盘恢复登录失败状态（重启后锁定依然有效）
        self._load_failures()

        logger.info(
            f"认证系统初始化完成：启动时数据源={'users表(数据库)' if db_backed_at_startup else 'config/users.yaml'}"
            f"（运行期会随users表状态动态切换），yaml中定义{len(self.users)}个用户，"
            f"锁定阈值={self.max_failures}次，"
            f"锁定时长={self.lockout_duration // 60}分钟"
        )

    @staticmethod
    def _is_db_backed_now() -> bool:
        """实时判断当前应走 users 表（数据库）还是 config/users.yaml。

        每次调用都重新查询（而非缓存），使数据源切换无需重启服务：
        - 迁移脚本执行完成的那一刻起
        - 或 admin 首次通过 /admin/users 创建账户的那一刻起
        下一次登录请求即可立即感知并切换到数据库模式。

        查询开销：SQLite `SELECT COUNT(*)`，相对 bcrypt 密码哈希计算可忽略不计。
        数据库/依赖不可用时（如某些测试环境未初始化数据库）安全回退到 yaml，不阻断认证。
        """
        try:
            from deepanalyze.core.task_manager.user_service import UserService
            return UserService.count_users() > 0
        except Exception as e:
            logger.debug(f"users表检测失败（可能尚未迁移），回退到 config/users.yaml: {e}")
            return False

    def _load_failures(self) -> None:
        """从磁盘加载登录失败状态"""
        state_path = _get_state_path()
        if not state_path.exists():
            return
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for username, tracker in data.items():
                self._failure_tracker[username] = {
                    "count": int(tracker.get("count", 0)),
                    "last_failure": float(tracker.get("last_failure", 0.0)),
                }
            if data:
                logger.info(f"已从磁盘恢复登录失败状态 ({len(data)} 条记录)")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"读取登录状态文件失败，将丢弃旧状态: {e}")

    def _save_failures(self) -> None:
        """将登录失败状态写入磁盘"""
        state_path = _get_state_path()
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(dict(self._failure_tracker), f, ensure_ascii=False)
        except OSError as e:
            logger.error(f"保存登录状态文件失败: {e}")

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
            self._save_failures()
        return False

    def _record_failure(self, username: str) -> None:
        """记录登录失败"""
        self._failure_tracker[username]["count"] += 1
        self._failure_tracker[username]["last_failure"] = time.time()
        self._save_failures()

    def _reset_failures(self, username: str) -> None:
        """登录成功后重置"""
        self._failure_tracker[username] = {"count": 0, "last_failure": 0.0}
        self._save_failures()

    def verify(self, username: str, password: str) -> Optional[dict]:
        """
        验证用户凭证

        Returns:
            成功返回用户字典（统一字段：username/role/org/description/valid_until/
            display_name/enabled/must_change_password，不含password_hash），
            失败返回 None
        """
        if self._is_db_backed_now():
            return self._verify_db(username, password)
        return self._verify_yaml(username, password)

    def _verify_db(self, username: str, password: str) -> Optional[dict]:
        """用户管理模块 批次2 Phase10：数据库模式下的凭证校验，
        委托给 UserService（含 bcrypt 校验 + valid_until 过期检查 + enabled 检查）。
        """
        from deepanalyze.core.task_manager.user_service import UserService
        return UserService.verify_password(username, password)

    def _verify_yaml(self, username: str, password: str) -> Optional[dict]:
        """原有 config/users.yaml 校验逻辑（未迁移/无数据库场景，兼容保留）"""
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

        # 用户管理模块 批次2 Phase10：归一化返回字段，与 _verify_db 的返回形状保持一致，
        # 使 /auth/me、/auth/profile 等下游读取方不需要区分数据源分支
        return {
            "username": user.get("username", username),
            "role": user.get("role", "user"),
            "org": user.get("org"),
            "description": user.get("description"),
            "valid_until": valid_until or None,
            "display_name": None,               # yaml 模式不支持该字段，统一给 None
            "enabled": True,                     # yaml 中的账户视为始终启用（无软删除概念）
            "must_change_password": False,       # yaml 模式不支持强制改密流程
        }

    def _get_failure_reason(self, username: str, password: str) -> str:
        """用户管理模块 批次2 补充加固（2026-07-03）：登录失败具体原因判定（分发）。

        仅在 `self.verify()` 已返回 None（登录失败）之后调用，根据当前数据源
        （DB优先/yaml兜底）分发到对应实现。返回值："invalid_credentials"（默认，
        密码错误/账户不存在/格式异常时的保守兜底）、"disabled"、"expired"。
        安全边界见 `UserService.get_login_failure_reason` docstring：只有密码
        校验本身通过时才会区分"disabled"/"expired"，避免向未持有正确密码的
        攻击者泄露账户状态。
        """
        if self._is_db_backed_now():
            from deepanalyze.core.task_manager.user_service import UserService
            return UserService.get_login_failure_reason(username, password)
        return self._get_yaml_failure_reason(username, password)

    def _get_yaml_failure_reason(self, username: str, password: str) -> str:
        """`_get_failure_reason` 的 yaml 模式实现，逻辑对齐 `_verify_yaml`。"""
        user = self.users.get(username)
        if not user:
            bcrypt.hashpw(b"dummy_password", bcrypt.gensalt())
            return "invalid_credentials"

        stored_hash = user.get("password_hash", "").encode("utf-8")
        try:
            if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
                return "invalid_credentials"
        except Exception:
            return "invalid_credentials"

        # yaml 模式无禁用概念（无软删除），密码校验通过后只需判断是否过期
        valid_until = user.get("valid_until", "")
        if valid_until and str(valid_until).strip():
            try:
                from datetime import date
                expiry = date.fromisoformat(str(valid_until).strip())
                if date.today() > expiry:
                    return "expired"
            except ValueError:
                return "invalid_credentials"

        return "invalid_credentials"

    def authenticate(self, request: Request) -> dict:
        """
        从请求中提取并验证凭证（自定义 `CWAuth` 认证方案）

        用户管理模块 批次3（2026-07-03）：认证方案从标准 `Basic` 改为自定义
        `CWAuth`（编码方式不变，仍是 base64("username:password")，只改了
        Authorization 头里的方案名）。

        根因：即便页面壳子（`/`、`/llm-manager`）已加入白名单不再触发 401、
        不再返回 `WWW-Authenticate` 头，只要浏览器**历史上**曾经通过原生 Basic
        Auth 弹窗成功登录过这个"域名+realm"一次（哪怕是本次修复上线前测试时
        触发的），浏览器就会把这份凭证缓存，并**自动**附加到该域名下所有后续
        同源请求上——不仅是整页导航，连 JS 用 `fetch()` 发起的 AJAX 请求，
        只要该次调用没有显式设置 `Authorization` 头（例如退出登录后
        localStorage 已清空，`authFetch` 就不会主动加这个头），浏览器也会
        抢先把缓存的旧 Basic 凭证注入进去——`/auth/me` 探测请求因此仍带着
        旧账号的凭证，后端一看凭证有效就直接放行，导致"退出登录"完全失效。
        这是纯浏览器网络层行为，`clearAuth()` 清 localStorage 对它没有任何
        作用，仅仅去掉页面壳子的 401 挑战头治不好已经被浏览器缓存过的旧凭证。

        修复：浏览器只对它自己"认识"的认证方案（`Basic`/`Digest`/`NTLM`/
        `Negotiate`）做这种缓存+自动注入，对不认识的自定义方案名（如这里的
        `CWAuth`）没有任何特殊处理——纯粹是一个不透明的字符串，前端要不要发送
        这个头、发什么值，完全由 JS（`lib/config.ts` / `shared/js/auth.js`）
        自己控制，不会被浏览器绕过。即使浏览器仍留有旧的 `Authorization: Basic
        ...` 缓存并继续尝试自动注入，后端这里也只认 `CWAuth ` 前缀，旧缓存的
        `Basic` 凭证会被直接判定为"未提供有效认证"，自然失效，不需要用户手动
        清浏览器缓存或重启浏览器。

        Returns:
            认证成功的用户字典

        Raises:
            HTTPException: 认证失败
        """
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("CWAuth "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization",
            )

        try:
            encoded = auth_header.split(" ", 1)[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
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
            # 用户管理模块 批次2 补充加固（2026-07-03）：区分"密码错误"与
            # "密码正确但账户已禁用/已过期"，避免统一提示"用户名或密码错误"
            # 误导用户以为自己记错了密码（实测反馈：过期账户、禁用账户输入
            # 完全正确的密码登录时均复现此问题）。
            #
            # 安全边界：_get_failure_reason 内部保证只有密码本身校验通过时才
            # 会返回"disabled"/"expired"，密码错误时始终是"invalid_credentials"，
            # 不会向尚未持有正确密码的攻击者泄露账户状态。
            reason = self._get_failure_reason(username, password)

            if reason == "disabled":
                logger.warning(f"登录被拒（账户已禁用，密码正确）: {username} (IP: {client_ip})")
                # 密码本身是对的，不属于"猜密码"行为，不计入失败次数/触发锁定
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="账号已被禁用，请联系管理员",
                )
            if reason == "expired":
                logger.warning(f"登录被拒（账户已过期，密码正确）: {username} (IP: {client_ip})")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="账号已过期，请联系管理员",
                )

            self._record_failure(username)
            remaining = self.max_failures - self._failure_tracker[username]["count"]
            logger.warning(
                f"登录失败: {username} (IP: {client_ip}, 剩余 {max(0, remaining)} 次)"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
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
        #
        # 用户管理模块 批次2 补充加固（2026-07-02）：认证性能瓶颈修复。
        # 背景：self.auth.authenticate() 内部会走到 bcrypt.checkpw() 做密码校验，
        # 这是一次CPU密集型的**同步阻塞**运算（bcrypt刻意设计得慢以抵御暴力破解，
        # 默认cost factor下单次校验通常在几十到一两百毫秒量级）。Basic Auth无状态，
        # 每次HTTP请求都要重新携带凭证、重新校验一次——此前这里是直接同步调用，
        # 运行在单个asyncio事件循环线程上，会整段阻塞事件循环。页面刷新时前端会
        # 几乎同时发出六到十个左右需要认证的请求（/auth/me、/workspace/files、
        # /workspace/tree、/sop/tasks、/sop/history、渠道列表等），这些请求的bcrypt
        # 校验被迫在同一条线程上排队串行执行，实测是用户反馈"刷新后多个互不相关的
        # 区域都要等几秒才出来"的主要瓶颈来源（而不是网络延迟或对应业务逻辑本身慢）。
        # 用 run_in_threadpool 把这个同步阻塞调用丢到线程池执行：bcrypt底层C扩展
        # 计算期间会释放GIL，多个请求的校验可以在不同线程上真正并行，不再互相排队
        # 阻塞事件循环，能大幅缓解这个问题（但无法降为0，bcrypt本身耗时是安全特性，
        # 不应通过降低cost factor去"优化"）。
        try:
            user = await run_in_threadpool(self.auth.authenticate, request)
        except HTTPException as exc:
            accept = request.headers.get("accept", "")
            is_html_navigation = "text/html" in str(accept)
            # 用户管理模块 批次3（2026-07-03）：认证方案改为自定义 `CWAuth` 后
            # （见 `SimpleAuth.authenticate` docstring 详细根因说明），
            # `authenticate()` 已不再在任何 401 响应上附带 `WWW-Authenticate`
            # 头——浏览器不认识 `CWAuth` 方案，即使带上这个头也不会有任何原生
            # 弹窗/凭证缓存行为，因此这里不再需要区分"页面导航要保留该头、
            # AJAX要主动去掉该头"，HTML 与 JSON 两个分支只是内容格式不同
            # （文本页面 vs. 结构化 JSON），保留是为了防御性兼容极少数场景下
            # 直接整页导航到受保护接口的情况（现有 SPA 架构下所有真实页面入口
            # `/`、`/llm-manager` 已在白名单，理论上不会再触达这里）。
            if is_html_navigation:
                html = f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>{exc.status_code}</title></head><body><h1>{exc.detail}</h1></body></html>"
                response = Response(
                    content=html,
                    status_code=exc.status_code,
                    media_type="text/html",
                )
            else:
                response = JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
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
