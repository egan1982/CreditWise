"""
DeepAnalyze FastAPI Main Application
Integrates DeepAnalyze backend with LLM_Manager for API management
"""

import os
import sys
import logging
import threading
import shutil
from pathlib import Path

# Fix encoding issues on Windows - only if not already set
if sys.platform == "win32" and "PYTHONIOENCODING" not in os.environ:
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Ensure project root is in sys.path so llm_manager_integrated is discoverable
# This is needed when main.py is imported as a module from other packages
_project_root = Path(__file__).parent.parent
_project_root_str = str(_project_root)
# Always add to path to ensure llm_manager_integrated is discoverable
sys.path.insert(0, _project_root_str)

# Initialize logger early to avoid import errors
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger(__name__)

# Load environment variables from .env file before other imports
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        _ = load_dotenv(env_path)  # Store return value to avoid unused result warning
        logger.debug(f"Loaded environment variables from {env_path}")
except ImportError as e:
    logger.warning(f"python-dotenv not available - {e}")

# Import after environment variables are loaded
try:
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    import uvicorn
except ImportError as e:
    logger.error(f"Failed to import FastAPI modules: {e}")
    raise

# Configuration with error handling
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# Set API_PORT with default and fallback
api_port_str = os.getenv("API_PORT", "8200")
api_port_value = 8200  # Default value
try:
    api_port_value = int(api_port_str)
except (ValueError, TypeError):
    print(f"[WARN] Invalid API_PORT value '{api_port_str}', using default: {api_port_value}")

# Define constant once
API_PORT = api_port_value

API_TITLE = "DeepAnalyze_CreditWise API"
API_VERSION = "1.0.0-beta.1"

# Integrated LLM Manager Backend - using class for better state management
from typing import Callable, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Query, Body

# Define type for create_app function to avoid type inference issues
CreateAppFuncType = Callable[..., FastAPI]

class LLMManagerState:
    def __init__(self):
        self.available: bool = False
        # Use the explicitly defined type to avoid inference issues
        self.create_app: CreateAppFuncType | None = None

llm_manager = LLMManagerState()

# Logger already initialized above

try:
    # Use integrated LLM Manager backend (no external dependency)
    logger.debug(f"Attempting to import llm_manager_integrated from: {sys.path[:3]}")
    print(f"Attempting to import llm_manager_integrated from: {sys.path[:3]}")
    
    # Import llm_manager_integrated using relative import
    from llm_manager_integrated.api.app import create_app as create_llm_manager_app_func  # type: ignore[reportUnknownVariableType]
    
    # Explicitly type the imported function to avoid inference issues
    llm_manager.available = True
    llm_manager.create_app = create_llm_manager_app_func
    logger.info("[OK] LLM Manager backend integrated successfully")
    print("[OK] LLM Manager backend integrated successfully")
except (ImportError, SyntaxError) as e:
    llm_manager.available = False
    logger.error(f"[WARN] LLM Manager not available: {e}", exc_info=True)
    print(f"[WARN] LLM Manager not available: {e}")
except Exception as e:
    llm_manager.available = False
    logger.error(f"[ERROR] Unexpected error importing LLM Manager: {e}", exc_info=True)
    print(f"[ERROR] Unexpected error importing LLM Manager: {e}")


def _generate_bootstrap_password(length: int = 14) -> str:
    """生成一个高强度随机密码，避开易混淆字符（0/O/1/l/I）"""
    import secrets
    import string

    alphabet = "".join(
        c for c in (string.ascii_letters + string.digits + "!@#%^&*")
        if c not in "0Ol1I"
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _ensure_bootstrap_admin_if_empty(username: str = "admin"):
    """用户管理模块 批次2 补充：全新部署零账户自动兜底。

    仅在"数据库0账户 且 config/users.yaml 不存在或其中也没配置任何账户"这一
    真正的空状态下才会创建账户，避免覆盖任何已有的合法配置（无论是数据库还是
    yaml 路径）。创建的密码只在本次进程内存中短暂存在，用于随后打印到启动日志，
    不落盘、不写入任何日志文件之外的持久化位置。

    Returns:
        {"username": ..., "password": ...} 如果本次创建了新账户；
        None 如果已存在可用账户（数据库或yaml任一有账户），未做任何改动。
    """
    try:
        from deepanalyze.core.task_manager.database import get_task_manager_db
        from deepanalyze.core.task_manager.user_service import UserService, UsernameConflictError

        get_task_manager_db()  # 确保 users 表已创建
        if UserService.count_users() > 0:
            return None  # 数据库里已有账户，无需兜底
    except Exception as e:
        logger.warning(f"[WARN] 检测数据库账户数失败，跳过自动兜底创建: {e}")
        return None

    # 数据库为空，再检查 yaml 是否已配置了账户（合法的存量/灾备路径，不应被覆盖）
    try:
        from auth_middleware import load_users_config
        yaml_users = load_users_config().get("users") or []
        if yaml_users:
            return None  # yaml 中已有账户，走 yaml 鉴权，无需兜底
    except FileNotFoundError:
        pass  # yaml 不存在，属于"真正的空状态"，继续走下面的自动创建
    except Exception as e:
        # yaml 存在但格式错误等：保守起见不覆盖，交给原有 except 分支报错处理，
        # 避免自动创建的账户和一份"看起来配置过但实际有问题"的yaml产生歧义
        logger.warning(f"[WARN] config/users.yaml 存在但读取失败，跳过自动兜底创建: {e}")
        return None

    password = _generate_bootstrap_password()
    try:
        UserService.create_user(
            username=username,
            password=password,
            role="admin",
            description="系统首次启动自动创建的初始管理员账户（零账户兜底）",
            must_change_password=True,
            created_by="startup_auto_bootstrap",
        )
    except UsernameConflictError:
        # 极小概率的启动竞态（如多进程同时首启）：已被别的进程创建，直接放弃本次创建
        return None
    return {"username": username, "password": password}


def _print_bootstrap_admin_banner(cred: dict) -> None:
    """在启动日志中醒目打印一次性初始管理员密码。"""
    banner = (
        "\n" + "=" * 70 + "\n"
        "[SECURITY] 首次启动自动创建了初始管理员账户（数据库中此前没有任何账户）\n"
        f"           用户名: {cred['username']}\n"
        f"           密码  : {cred['password']}\n"
        "           该密码仅在此处显示一次，请立即记录！\n"
        "           首次登录后会被强制要求修改密码。\n"
        + "=" * 70 + "\n"
    )
    print(banner)
    logger.warning(
        f"[SECURITY] 自动创建初始管理员账户: username={cred['username']}"
        "（密码已打印到标准输出，不会写入日志文件）"
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""

    # === 部署审批验证（最先执行，Layer 1 默认轻量方案）===
    # 见 docs/code-protection-plan.md §3.0、API/deploy_guard.py
    from API.deploy_guard import check_deploy_approved
    if not check_deploy_approved():
        raise RuntimeError(
            "Deploy approval failed. "
            "DEPLOY_APPROVAL_TOKEN does not match the expected value. "
            "Please contact the administrator for a valid deployment token."
        )

    app = FastAPI(title=API_TITLE, version=API_VERSION)

    # Add Dynamic CORS middleware — sets Origin dynamically per request
    # Avoids the spec-invalid allow_origins=["*"] + allow_credentials=True combination
    from cors_middleware import DynamicCORSMiddleware
    app.add_middleware(DynamicCORSMiddleware)

    # Basic Auth 认证中间件（内网多用户版）
    # 通过环境变量 ENABLE_AUTH=true 启用，默认关闭以兼容现有部署
    if os.getenv("ENABLE_AUTH", "false").lower() == "true":
        try:
            from auth_middleware import SimpleAuth, BasicAuthMiddleware

            # 用户管理模块 批次2 补充：零账户自动兜底（fail-closed 修复）
            # 背景：此前若 ENABLE_AUTH=true 但 users 表为空且 config/users.yaml 不存在
            # （典型场景：全新部署，忘了先跑 init_admin.py），SimpleAuth() 会抛
            # FileNotFoundError；下面的 except 分支会捕获它但**不重新抛出**，导致
            # BasicAuthMiddleware 根本没被挂载——服务在完全无鉴权状态下正常对外运行，
            # 是典型的 fail-open（该失败但没失败，反而降级成了"当作没启用鉴权"）。
            # 这里在构造 SimpleAuth() 之前主动补一个自动创建：只有在"数据库0账户 且
            # yaml不存在/yaml中也没配置任何账户"这一真正的空状态下才触发，生成一个
            # 随机高强度密码（而非固定默认密码，理由见 scripts/init_admin.py 顶部说明），
            # 创建后 SimpleAuth() 就能在数据库模式下正常初始化，无需再要求 yaml 存在，
            # 从根上消除了"忘记bootstrap→静默无鉴权"这条路径。
            _bootstrap_cred = _ensure_bootstrap_admin_if_empty()
            if _bootstrap_cred:
                _print_bootstrap_admin_banner(_bootstrap_cred)

            auth = SimpleAuth()
            app.add_middleware(BasicAuthMiddleware, auth=auth)
            # 用户管理模块 批次2 Phase10：暴露给 /auth/change-password 复用现有账户锁定机制（M19决策）
            app.state.auth = auth
            logger.info("[OK] Basic Auth 认证中间件已启用")
        except FileNotFoundError as e:
            # 走到这里说明是"yaml存在但格式错误/其他非零账户异常"之外的场景，理论上
            # 已被上面的自动兜底消化；仍保留此分支作为防御性兜底日志，避免静默吞掉未知问题。
            logger.error(f"[ERROR] 认证配置缺失: {e}")
            print(f"[ERROR] 认证配置缺失: {e}")
        except ImportError as e:
            logger.error(f"[ERROR] 认证依赖缺失: {e}")
            print(f"[ERROR] 认证依赖缺失（请安装 bcrypt 和 pyyaml）: {e}")
        except Exception as e:
            logger.error(f"[ERROR] 认证中间件初始化失败: {e}")
            print(f"[ERROR] 认证中间件初始化失败: {e}")
    else:
        logger.warning(
            "[SECURITY] ENABLE_AUTH=false — 服务将在无认证模式下运行，"
            "仅适用于单用户开发环境。"
        )

    # 添加全局异常处理器，确保异常响应也包含CORS头
    # 同时处理 SPA fallback（生产模式下对非 API 路径的 404 返回 index.html）
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    def _cors_headers_from_request(request: Request) -> dict:
        """从请求中提取 Origin 构建 CORS 响应头，避免硬编码 '*' 与 credentials 冲突"""
        origin = request.headers.get("origin", "")
        return {
            "Access-Control-Allow-Origin": origin or "*",
            "Access-Control-Allow-Credentials": "true" if origin else "false",
        }

    # 已知的 API 路径前缀（生产模式 SPA fallback 时不应重定向到前端）
    _api_prefixes = (
        "/v1/", "/sop/", "/workspace/", "/health", "/docs",
        "/openapi", "/llm-manager/", "/download/", "/execute/",
        "/export/", "/chat/",
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # 生产模式下，对非 API 路径的 404 尝试 SPA fallback
        dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        if not dev_mode and exc.status_code == 404:
            path = request.url.path
            if not path.startswith(_api_prefixes):
                frontend_dist = Path(__file__).parent.parent / "demo" / "chat" / "dist"
                if frontend_dist.exists():
                    # 优先返回实际静态文件（图片、favicon 等）
                    # 路径遍历防护：resolve 后检查是否仍在 frontend_dist 目录内
                    candidate = (frontend_dist / path.lstrip("/")).resolve()
                    try:
                        candidate.relative_to(frontend_dist.resolve())
                    except ValueError:
                        pass  # 路径逃逸，不回退文件
                    else:
                        if candidate.is_file():
                            from fastapi.responses import FileResponse
                            return FileResponse(str(candidate))
                    # SPA fallback：返回 index.html
                    index_file = frontend_dist / "index.html"
                    if index_file.exists():
                        from fastapi.responses import FileResponse
                        return FileResponse(str(index_file))
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=_cors_headers_from_request(request),
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers=_cors_headers_from_request(request),
        )

    # Include essential routers
    # Note: models_api has been deprecated and replaced by LLM Manager's /api/models endpoint
    
    # Include Chat API router (provides /v1/chat/completions endpoint)
    try:
        try:
            from .chat_api import router as chat_router
        except ImportError:
            from API.chat_api import router as chat_router
        app.include_router(chat_router)
        logger.info("[OK] Chat API router registered at /v1/chat")
    except Exception as e:
        import traceback
        logger.error(f"[ERROR] Chat API not available: {e}")
        print(f"[ERROR] Chat API import failed: {e}")
        traceback.print_exc()
    
    # Include SOP Task API router
    try:
        try:
            from .sop_api import router as sop_router
        except ImportError:
            from API.sop_api import router as sop_router
        app.include_router(sop_router)
        logger.info("[OK] SOP Task API router registered at /sop")
    except Exception as e:
        import traceback
        logger.error(f"[ERROR] SOP Task API not available: {e}")
        print(f"[ERROR] SOP Task API import failed: {e}")
        traceback.print_exc()

    # 用户管理模块 批次2 Phase10：账号管理 API router（/auth/mode, /auth/profile,
    # /auth/change-password, /admin/users*）
    try:
        try:
            from .user_admin_api import router as user_admin_router
        except ImportError:
            from API.user_admin_api import router as user_admin_router
        app.include_router(user_admin_router)
        logger.info("[OK] User Admin API router registered at /auth, /admin/users")
    except Exception as e:
        import traceback
        logger.error(f"[ERROR] User Admin API not available: {e}")
        print(f"[ERROR] User Admin API import failed: {e}")
        traceback.print_exc()

    # Root endpoint - for health checks and basic info
    @app.get("/")
    async def root():  # pyright: ignore[reportUnusedFunction]
        """根路径 - 生产模式返回前端页面，开发模式返回 API 信息"""
        _dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        if not _dev_mode:
            _frontend_index = Path(__file__).parent.parent / "demo" / "chat" / "dist" / "index.html"
            if _frontend_index.exists():
                return FileResponse(str(_frontend_index))
        return {
            "status": "running",
            "service": "DeepAnalyze API Server",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "docs": "/docs",
                "llm_manager": "/llm-manager",
                "llm_manager_vite": "http://localhost:3001",
                "sop_tasks": "/sop/tasks"
            }
        }
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():  # pyright: ignore[reportUnusedFunction]
        return {"status": "healthy"}

    # 用户管理模块 批次1 Phase1 + 批次2 Phase10：返回当前登录用户信息
    # 单用户模式（ENABLE_AUTH=false，中间件未挂载）下 request.state 无 user 属性，
    # 返回 username=None，前端据此判断维持现状（随机sessionId），不受本模块影响。
    @app.get("/auth/me")
    async def get_current_user(request: Request):  # pyright: ignore[reportUnusedFunction]
        """返回当前登录用户名及个人信息，供前端：
        1. 将 username 作为身份隔离键（session_id）使用（批次1 §五）
        2. 渲染账户设置弹窗（display_name/org/description/valid_until/must_change_password，批次2 §十四）
        """
        user = getattr(request.state, "user", None)
        if user:
            return {
                "username": user.get("username"),
                "authenticated": True,
                "display_name": user.get("display_name"),
                "role": user.get("role"),
                "org": user.get("org"),
                "description": user.get("description"),
                "valid_until": user.get("valid_until"),
                "must_change_password": bool(user.get("must_change_password", False)),
            }
        return {"username": None, "authenticated": False}
    
    # Add workspace management endpoints
    @app.get("/workspace/files")
    async def get_workspace_files_endpoint(request: Request, session_id: str = "default"):
        """获取工作区文件列表（继承原始项目设计）"""
        from pathlib import Path
        from utils import get_session_workspace, build_download_url, get_file_icon, validate_session_id, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        # 使用统一的工作区获取函数
        workspace_dir = get_session_workspace(session_id)
        workspace_path = Path(workspace_dir)
        generated_dir = workspace_path / "generated"
        
        # 获取 generated 目录下的文件名集合
        generated_files = (
            set(f.name for f in generated_dir.iterdir() if f.is_file())
            if generated_dir.exists()
            else set()
        )
        
        files = []
        for file_path in workspace_path.iterdir():
            if file_path.is_file():
                if file_path.name in generated_files:
                    continue
                stat = file_path.stat()
                rel_path = f"{session_id}/{file_path.name}"
                files.append(
                    {
                        "name": file_path.name,
                        "size": stat.st_size,
                        "extension": file_path.suffix.lower(),
                        "icon": get_file_icon(file_path.suffix),
                        "download_url": build_download_url(rel_path),
                        "preview_url": (
                            build_download_url(rel_path)
                            if file_path.suffix.lower()
                            in [
                                ".jpg", ".jpeg", ".png", ".gif", ".bmp",
                                ".pdf", ".txt", ".doc", ".docx",
                                ".csv", ".xlsx",
                            ]
                            else None
                        ),
                    }
                )
        return {"files": files}
    
    @app.delete("/workspace/file")
    async def delete_workspace_file(request: Request, path: str, session_id: str = "default"):
        """删除工作区文件（继承原始项目设计）"""
        from pathlib import Path
        from fastapi import HTTPException
        from utils import get_session_workspace, validate_session_id, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        workspace_dir = get_session_workspace(session_id)
        abs_workspace = Path(workspace_dir).resolve()
        target = (abs_workspace / path).resolve()
        
        # 路径遍历防护
        if abs_workspace not in target.parents and target != abs_workspace:
            raise HTTPException(status_code=400, detail="Invalid path")
        
        if not target.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        try:
            if target.is_dir():
                import shutil
                shutil.rmtree(target)
            else:
                target.unlink()
            return {"message": "deleted successfully"}
        except Exception as e:
            logger.error(f"Failed to delete file: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete file")
    
    @app.get("/download/{file_path:path}")
    async def download_file(request: Request, file_path: str):
        """下载工作区文件（继承原始项目设计）"""
        from pathlib import Path
        from fastapi import HTTPException
        from fastapi.responses import FileResponse
        import mimetypes
        from config import WORKSPACE_BASE_DIR
        from utils import enforce_path_ownership
        
        # 文件路径格式: session_id/[generated/]filename
        # 用户管理模块 批次1 Phase3：非admin用户仅可下载自己 session 目录下的文件
        enforce_path_ownership(request, file_path)
        workspace_dir = Path(WORKSPACE_BASE_DIR).resolve()
        target = (workspace_dir / file_path).resolve()
        
        # 路径遍历防护
        if workspace_dir not in target.parents and target != workspace_dir:
            raise HTTPException(status_code=400, detail="Invalid path")
        
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(str(target))
        if mime_type is None:
            # 对于CSV等常见文本文件，设置正确的MIME类型
            ext = target.suffix.lower()
            mime_map = {
                '.csv': 'text/csv',
                '.txt': 'text/plain',
                '.md': 'text/markdown',
                '.json': 'application/json',
                '.xml': 'application/xml',
                '.yaml': 'text/yaml',
                '.yml': 'text/yaml',
                '.py': 'text/x-python',
                '.js': 'text/javascript',
                '.ts': 'text/typescript',
                '.html': 'text/html',
                '.css': 'text/css',
            }
            mime_type = mime_map.get(ext, 'application/octet-stream')
        
        return FileResponse(
            path=target,
            filename=target.name,
            media_type=mime_type
        )
    
    @app.post("/workspace/upload")
    async def upload_to_workspace(
        request: Request,
        session_id: str = Query("default"), 
        dir: str = Query(""),
        files: List[UploadFile] = File(...)
    ):
        """上传文件到工作区（继承原始项目设计）"""
        from pathlib import Path
        from utils import get_session_workspace, validate_session_id, check_upload_size, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        workspace_dir = get_session_workspace(session_id)
        abs_workspace = Path(workspace_dir).resolve()
        target_dir = (abs_workspace / dir).resolve() if dir else abs_workspace
        
        # 路径遍历防护
        if abs_workspace not in target_dir.parents and target_dir != abs_workspace:
            raise HTTPException(status_code=400, detail="Invalid dir path")
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        for file in files:
            # 文件名消毒：仅取 basename，防止路径遍历（P0-1 补修）
            safe_name = Path(file.filename).name if file.filename else "unnamed"
            file_path = target_dir / safe_name
            try:
                content = await file.read()
                check_upload_size(content, safe_name)  # P1-D1: 文件大小限制
                with open(file_path, "wb") as f:
                    f.write(content)
                results.append({"name": safe_name, "status": "success"})
            except HTTPException:
                raise
            except Exception as e:
                results.append({"name": file.filename, "status": "error", "error": str(e)})
        
        return {"files": results}
    
    @app.delete("/workspace/clear")
    async def clear_workspace(request: Request, session_id: str = "default"):
        """清空工作区（继承原始项目设计）"""
        from pathlib import Path
        import shutil
        from utils import get_session_workspace, validate_session_id, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        workspace_dir = Path(get_session_workspace(session_id))
        if workspace_dir.exists():
            # 删除除generated目录外的所有内容
            for item in workspace_dir.iterdir():
                if item.name != "generated":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
        
        return {"message": "workspace cleared"}
    
    @app.post("/export/report")
    async def export_report(
        request: Request,
        session_id: str = "default",
        messages: list = None,
        title: str = "Report"
    ):
        """导出报告（继承原始项目设计）"""
        from pathlib import Path
        from datetime import datetime
        import re
        from utils import get_session_workspace, build_download_url, validate_session_id, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        workspace_dir = get_session_workspace(session_id)
        generated_dir = Path(workspace_dir) / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)
        
        # P1-D13: 文件名消毒 — 仅保留中英文、数字、下划线、连字符、点，限100字符
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', title)[:100] or "Report"
        
        # 生成Markdown内容
        md_content = f"# {title}\n\n"
        if messages:
            for msg in messages:
                role = "用户" if msg.get("role") == "user" else "助手"
                content = msg.get("content", "")
                md_content += f"## {role}\n\n{content}\n\n"
        
        # 保存Markdown文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{safe_title}_{timestamp}.md"
        file_path = generated_dir / file_name
        
        # 额外保险：确保文件路径在 generated_dir 内
        if generated_dir.resolve() not in file_path.resolve().parents:
            raise HTTPException(status_code=400, detail="Invalid title")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        # 使用统一的URL构建函数
        return {
            "md": file_name,
            "url": build_download_url(f"{session_id}/generated/{file_name}")
        }
        
    @app.get("/workspace/tree")
    async def workspace_tree_endpoint(request: Request, session_id: str = "default"):
        """获取工作区文件树结构（继承原始项目设计）"""
        from pathlib import Path
        from utils import get_session_workspace, build_download_url, get_file_icon, validate_session_id, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        # 构建树结构的函数（继承原始项目排序逻辑）
        def _rel_path(path: Path, root: Path) -> str:
            try:
                rel = path.relative_to(root)
                return rel.as_posix()
            except Exception:
                return path.name
        
        def build_tree(path: Path, root: Path) -> dict:
            node = {
                "name": path.name or "workspace",
                "path": _rel_path(path, root),
                "is_dir": path.is_dir(),
            }
            
            if path.is_dir():
                children = []
                # 自定义排序：generated 文件夹放在最后，其他按目录优先、名称排序
                def sort_key(p):
                    is_generated = p.name == "generated"
                    is_dir = p.is_dir()
                    return (is_generated, not is_dir, p.name.lower())
                
                try:
                    for child in sorted(path.iterdir(), key=sort_key):
                        if child.name.startswith("."):
                            continue
                        children.append(build_tree(child, root))
                    node["children"] = children
                except PermissionError:
                    node["children"] = []
            else:
                node["size"] = path.stat().st_size
                node["extension"] = path.suffix.lower()
                node["icon"] = get_file_icon(path.suffix)
                rel = _rel_path(path, root)
                node["download_url"] = build_download_url(f"{session_id}/{rel}")
            
            return node
        
        # 使用统一的工作区获取函数
        workspace_dir = get_session_workspace(session_id)
        root = Path(workspace_dir)
        tree_data = build_tree(root, root)
        
        return tree_data
    
    @app.get("/workspace/data-columns")
    async def get_data_columns(
        request: Request,
        file_path: str = Query(..., description="数据文件路径"),
        session_id: str = Query("default")
    ):
        """
        获取数据文件的列信息
        
        Args:
            file_path: 数据文件路径（相对于workspace）
            session_id: 会话ID
            
        Returns:
            列信息列表 [{"name": "col1", "dtype": "int64"}, ...]
        """
        from pathlib import Path
        from fastapi import HTTPException
        import pandas as pd
        from utils import get_session_workspace, validate_session_id, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        workspace_dir = Path(get_session_workspace(session_id))
        abs_workspace = workspace_dir.resolve()
        full_path = (workspace_dir / file_path).resolve()
        
        # 路径遍历防护（P1-D3 修复）
        if abs_workspace not in full_path.parents and full_path != abs_workspace:
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        try:
            # 根据文件扩展名读取数据
            suffix = full_path.suffix.lower()
            if suffix == ".csv":
                df = pd.read_csv(full_path, nrows=0)  # 只读取列头
            elif suffix in [".xlsx", ".xls"]:
                df = pd.read_excel(full_path, nrows=0)
            elif suffix == ".parquet":
                import pyarrow.parquet as pq
                schema = pq.read_schema(full_path)
                return [
                    {"name": field.name, "dtype": str(field.type)}
                    for field in schema
                ]
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
            
            # 返回列信息
            return [
                {"name": col, "dtype": str(df[col].dtype)}
                for col in df.columns
            ]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to read data columns: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to read data columns")
    
    # ========== 继承原始项目的文件管理路由 ==========
    
    @app.post("/workspace/move")
    async def move_path(
        request: Request,
        src: str = Query(..., description="relative source path under workspace"),
        dst_dir: str = Query("", description="relative target directory under workspace"),
        session_id: str = Query("default"),
    ):
        """在同一 workspace 内移动（或重命名）文件/目录（继承原始项目设计）"""
        from fastapi import HTTPException
        from utils import get_session_workspace, uniquify_path, validate_session_id, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        workspace_dir = Path(get_session_workspace(session_id))
        abs_workspace = workspace_dir.resolve()
        
        abs_src = (abs_workspace / src).resolve()
        if abs_workspace not in abs_src.parents and abs_src != abs_workspace:
            raise HTTPException(status_code=400, detail="Invalid src path")
        if not abs_src.exists():
            raise HTTPException(status_code=404, detail="Source not found")
        
        abs_dst_dir = (abs_workspace / (dst_dir or "")).resolve()
        if abs_workspace not in abs_dst_dir.parents and abs_dst_dir != abs_workspace:
            raise HTTPException(status_code=400, detail="Invalid dst_dir path")
        abs_dst_dir.mkdir(parents=True, exist_ok=True)
        
        target = abs_dst_dir / abs_src.name
        # 使用统一的唯一化路径函数
        target = uniquify_path(target)
        
        try:
            shutil.move(str(abs_src), str(target))
            rel_new = str(target.relative_to(abs_workspace))
            return {"message": "moved", "new_path": rel_new}
        except Exception as e:
            logger.error(f"Move failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Move failed")
    
    @app.delete("/workspace/dir")
    async def delete_workspace_dir(
        request: Request,
        path: str = Query(..., description="relative directory under workspace"),
        recursive: bool = Query(True, description="delete directory recursively"),
        session_id: str = Query("default"),
    ):
        """删除 workspace 下的目录（继承原始项目设计）"""
        from fastapi import HTTPException
        from utils import get_session_workspace, validate_session_id, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        workspace_dir = Path(get_session_workspace(session_id))
        abs_workspace = workspace_dir.resolve()
        target = (abs_workspace / path).resolve()
        
        if abs_workspace not in target.parents and target != abs_workspace:
            raise HTTPException(status_code=400, detail="Invalid path")
        if target == abs_workspace:
            raise HTTPException(status_code=400, detail="Cannot delete workspace root")
        if not target.exists():
            raise HTTPException(status_code=404, detail="Not found")
        if not target.is_dir():
            raise HTTPException(status_code=400, detail="Not a directory")
        
        try:
            if recursive:
                shutil.rmtree(target)
            else:
                target.rmdir()
            return {"message": "deleted"}
        except Exception as e:
            logger.error(f"Failed to delete directory: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete directory")
    
    @app.post("/workspace/upload-to")
    async def upload_to_dir(
        request: Request,
        dir: str = Query("", description="relative directory under workspace"),
        files: List[UploadFile] = File(...),
        session_id: str = Query("default"),
    ):
        """上传文件到 workspace 下的指定子目录（继承原始项目设计）"""
        from fastapi import HTTPException
        from utils import get_session_workspace, uniquify_path, validate_session_id, check_upload_size, resolve_owned_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        session_id = resolve_owned_session_id(request, session_id)  # 用户管理模块 批次1 Phase3：所有权强制落地
        
        workspace_dir = Path(get_session_workspace(session_id))
        abs_workspace = workspace_dir.resolve()
        target_dir = (abs_workspace / dir).resolve()
        
        if abs_workspace not in target_dir.parents and target_dir != abs_workspace:
            raise HTTPException(status_code=400, detail="Invalid dir path")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        saved = []
        for f in files:
            # 文件名消毒：仅取 basename，防止路径遍历（P0-1 补修）
            safe_name = Path(f.filename).name if f.filename else "unnamed"
            dst = target_dir / safe_name
            # 使用统一的唯一化路径函数
            dst = uniquify_path(dst)
            
            try:
                content = await f.read()
                check_upload_size(content, safe_name)  # P1-D1: 文件大小限制
                with open(dst, "wb") as buffer:
                    buffer.write(content)
                saved.append({
                    "name": dst.name,
                    "size": len(content),
                    "path": str(dst.relative_to(abs_workspace)),
                })
            except Exception as e:
                logger.error(f"Save failed: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Save failed")
        
        return {"message": f"uploaded {len(saved)}", "files": saved}

    # 用户管理模块 批次1 Phase5：用户自助认领旧 session（主路径迁移方式）
    # 详见 docs/user_management_module_design.md §六
    @app.post("/workspace/claim-legacy-session")
    async def claim_legacy_session(request: Request, body: Dict[str, Any] = Body(...)):  # pyright: ignore[reportUnusedFunction]
        """登录后，前端检测本地残留的旧格式随机sessionId后调用本接口，
        将该旧session名下的 task_records/execution_states/workspace目录
        全部转移到当前登录用户名下。

        单用户模式（无 request.state.user）下无意义，直接400拒绝。
        仅接受形如 session_<timestamp>_<random> 的旧格式ID，防止误关联他人真实账户目录。
        """
        from fastapi import HTTPException
        from utils import validate_session_id
        from config import WORKSPACE_BASE_DIR
        from deepanalyze.core.task_manager.user_migration_service import (
            is_legacy_session_id, merge_user_data,
        )

        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=400, detail="该操作仅在多用户模式下可用")

        old_session_id = (body or {}).get("old_session_id", "")
        try:
            old_session_id = validate_session_id(old_session_id, param_name="old_session_id")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not is_legacy_session_id(old_session_id):
            raise HTTPException(
                status_code=400,
                detail="仅支持认领旧格式的历史会话（session_<timestamp>_<random>），"
                       "不允许认领其他用户的账户目录",
            )

        username = user.get("username")
        if old_session_id == username:
            return {"success": True, "message": "无需认领，该会话已属于当前账户", "merged": None}

        try:
            merge_result = merge_user_data(
                from_session_id=old_session_id,
                to_username=username,
                workspace_base_dir=WORKSPACE_BASE_DIR,
                dry_run=False,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        logger.info(f"[AUDIT] 用户 {username} 自助认领旧会话 {old_session_id}: {merge_result}")

        return {
            "success": True,
            "message": f"已将历史会话 {old_session_id} 关联到当前账户",
            "merged": merge_result,
        }

    # 用户管理模块 批次1 Phase6：账户合并小工具（admin，改名场景使用）
    # 详见 docs/user_management_module_design.md §七
    @app.post("/admin/users/merge")
    async def merge_user_accounts(request: Request, body: Dict[str, Any] = Body(...)):  # pyright: ignore[reportUnusedFunction]
        """把 from_username 名下的历史数据（task_records/execution_states/
        workspace目录）批量转移到 to_username 名下。仅admin可调用。

        典型场景：管理员通过\"软删除旧账户+创建新账户\"完成改名后，
        用本接口把旧账户的历史数据转移到新账户名下。
        """
        from fastapi import HTTPException
        from config import WORKSPACE_BASE_DIR
        from deepanalyze.core.task_manager.user_migration_service import merge_user_data

        user = getattr(request.state, "user", None)
        # 双重防线：中间件层 ADMIN_ONLY_PREFIXES 已拦截非admin请求，这里再显式校验一次，
        # 避免因中间件配置遗漏导致越权（不可仅依赖前端/中间件单一层校验）
        if not user or user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="需要管理员权限")

        from_username = (body or {}).get("from_username", "")
        to_username = (body or {}).get("to_username", "")
        dry_run = bool((body or {}).get("dry_run", True))

        try:
            merge_result = merge_user_data(
                from_session_id=from_username,
                to_username=to_username,
                workspace_base_dir=WORKSPACE_BASE_DIR,
                dry_run=dry_run,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        logger.info(
            f"[AUDIT] admin {user.get('username')} 执行账户合并 "
            f"{from_username} -> {to_username} (dry_run={dry_run}): {merge_result}"
        )

        return {"success": True, "merged": merge_result}

    # 用户管理模块 批次1 补充：管理员浏览指定工作区（M2026-07-02决策，只读）
    # 详见 docs/user_management_module_design.md §二十六
    #
    # 背景：resolve_owned_session_id 对 admin 早已放行"按客户端传参查看任意
    # session"，但前端从未提供发现机制（admin 不知道磁盘上有哪些 session 可选）
    # 也没有切换入口，导致这项后端已具备的能力实际上无法被使用（例如admin看不到
    # 单用户模式遗留在旧随机session目录下的文档）。本接口只做"列出可选项"，
    # 不改动任何既有鉴权逻辑。
    @app.get("/admin/workspace/sessions")
    async def list_workspace_sessions(request: Request):  # pyright: ignore[reportUnusedFunction]
        """列出 workspace/ 下所有 session 目录，供管理员选择要浏览哪个工作区。

        仅 admin 可调用（中间件 ADMIN_ONLY_PREFIXES 已拦截，此处不再重复校验）。
        每个 session 标注是否对应当前数据库中的真实注册用户，便于前端区分
        "正常账户" 与 "遗留的旧随机session"。
        """
        from pathlib import Path
        from datetime import datetime
        from config import WORKSPACE_BASE_DIR
        from deepanalyze.core.task_manager.user_service import UserService

        # 已注册用户名集合（用于标注 is_registered_user）
        try:
            total_users = UserService.count_users()
            registered = {
                u["username"]
                for u in UserService.list_users(limit=max(total_users, 1)).get("items", [])
            }
        except Exception as e:
            logger.warning(f"[WARN] 读取用户列表失败，is_registered_user 将全部标为 False: {e}")
            registered = set()

        base = Path(WORKSPACE_BASE_DIR)
        sessions = []
        if base.exists():
            for entry in sorted(base.iterdir(), key=lambda p: p.name):
                if not entry.is_dir():
                    continue
                try:
                    stat = entry.stat()
                    # 轻量文件计数：递归遍历但设上限，避免超大目录拖慢列表接口
                    file_count = 0
                    for _ in entry.rglob("*"):
                        file_count += 1
                        if file_count >= 5000:
                            break
                    sessions.append({
                        "session_id": entry.name,
                        "is_registered_user": entry.name in registered,
                        "file_count": file_count,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except Exception as e:
                    logger.warning(f"[WARN] 读取 workspace 子目录 {entry.name} 信息失败，跳过: {e}")
                    continue

        return {"sessions": sessions}

    @app.get("/proxy")
    async def proxy(url: str):
        """CORS proxy for previewing local server files (SSRF-protected)"""
        from fastapi import HTTPException
        from fastapi.responses import Response
        from urllib.parse import urlparse
        import httpx

        # SSRF防护：仅允许访问本机服务的URL
        allowed_hosts = {"localhost", "127.0.0.1", "0.0.0.0"}
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.hostname:
                raise HTTPException(status_code=400, detail="Invalid URL")
            if parsed.hostname not in allowed_hosts:
                raise HTTPException(
                    status_code=403,
                    detail=f"Proxy only allows local URLs (localhost/127.0.0.1), got: {parsed.hostname}",
                )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid URL format")

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                r = await client.get(url)
            return Response(
                content=r.content,
                media_type=r.headers.get("content-type", "application/octet-stream"),
                headers={"Access-Control-Allow-Origin": "*"},
                status_code=r.status_code,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Proxy fetch failed: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail="Proxy fetch failed")
    
    # Integrate LLM_Manager
    # - Dev: sub-app mount API only, Vite dev server at :3001 for frontend
    # - Prod: main app serves pre-built frontend (offline Tailwind CSS + Vite JS)
    #         + registers API routers directly (avoids Starlette mount redirect loops)
    if llm_manager.available and llm_manager.create_app is not None:
        try:
            dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
            
            if dev_mode:
                # 开发模式下 create_app(enable_frontend=False) 只注册了 /api/* 路由，
                # 不提供 index.html/scripts/shared 等静态资源。Vite 开发服务器（:3001）
                # 的 vite.config.js 把整个 /llm-manager 前缀都代理到本服务，包括
                # /llm-manager/scripts/main.js、/llm-manager/shared/* 这些静态资源——
                # 若本服务不显式提供这两个路径，会 404，导致前端脚本加载失败（渠道列表
                # 卡在"加载中"、Tab 切换无响应）。这里直接从 frontend 源码目录提供文件
                # （而非构建产物），路径遍历防护对齐现有 SPA fallback 的处理方式。
                _llm_frontend_dir = Path(__file__).parent.parent / "llm_manager_integrated" / "frontend"

                def _serve_llm_frontend_asset(subdir: str, rel_path: str):
                    from fastapi import HTTPException
                    from fastapi.responses import FileResponse
                    base_dir = (_llm_frontend_dir / subdir).resolve()
                    candidate = (base_dir / rel_path.lstrip("/")).resolve()
                    try:
                        candidate.relative_to(base_dir)
                    except ValueError:
                        raise HTTPException(status_code=404, detail="Not Found")  # 路径逃逸，拒绝
                    if not candidate.is_file():
                        raise HTTPException(status_code=404, detail="Not Found")
                    return FileResponse(str(candidate))

                @app.get("/llm-manager/scripts/{r:path}", include_in_schema=False)
                async def llm_manager_dev_scripts(r: str):  # pyright: ignore[reportUnusedFunction]
                    return _serve_llm_frontend_asset("scripts", r)

                @app.get("/llm-manager/shared/{r:path}", include_in_schema=False)
                async def llm_manager_dev_shared(r: str):  # pyright: ignore[reportUnusedFunction]
                    return _serve_llm_frontend_asset("shared", r)

                llm_manager_app = llm_manager.create_app(
                    config={"app_title": "LLM API Manager for DeepAnalyze"},
                    as_subapp=True, enable_frontend=False, prefix="/llm-manager")
                app.mount("/llm-manager", llm_manager_app)
                
                @app.get("/llm-manager", include_in_schema=False)
                async def llm_manager_dev_redirect():
                    from fastapi.responses import RedirectResponse
                    return RedirectResponse(url="http://localhost:3001", status_code=302)
                
                print("[OK] LLM_Manager backend integrated (Development Mode)")
                print(f"   - API: http://{API_HOST}:{API_PORT}/llm-manager/api")
                print(f"   - Frontend: Running on Vite server at http://localhost:3001")
            else:
                # Prod: register API routers directly on main app
                from llm_manager_integrated.api.routes import channels, logs, monitoring
                from llm_manager_integrated.api.routes.proxy.proxy import router as proxy_router
                from llm_manager_integrated.api.routes.proxy.models_proxy import router as models_router
                app.include_router(channels.router, prefix="/llm-manager/api/manage")
                app.include_router(logs.router, prefix="/llm-manager/api")
                app.include_router(proxy_router, prefix="/llm-manager/api/proxy")
                app.include_router(models_router, prefix="/llm-manager/api")
                app.include_router(monitoring.router, prefix="/llm-manager/api/monitoring")

                # 生产模式：初始化 LLM Manager 依赖（api/dependencies.py 从 app.state 取 db_manager）
                # 必须在 startup 事件中挂载，此时 app.state 才可写
                @app.on_event("startup")
                async def llm_manager_startup():
                    try:
                        from llm_manager_integrated.models.database import DatabaseManager
                        from llm_manager_integrated.core.config import settings as llm_settings
                        from llm_manager_integrated.core.startup import app_startup_handler
                        db_manager = DatabaseManager(llm_settings.database_url)
                        db_manager.create_tables()
                        app.state.db_manager = db_manager
                        app.state.config = llm_settings
                        await app_startup_handler(app)
                        logger.info("[OK] LLM_Manager db_manager initialized on main app.state")
                    except Exception as e:
                        logger.warning(f"[WARN] LLM_Manager startup init failed: {e}")
                
                # Serve pre-built LLM Manager frontend (Vite + Tailwind, offline-ready)
                _llm_static = Path(__file__).parent.parent / "llm_manager_integrated" / "static"
                _llm_assets = _llm_static / "assets"
                
                @app.get("/llm-manager/", include_in_schema=False)
                async def llm_manager_prod_index():
                    from fastapi import HTTPException
                    from fastapi.responses import HTMLResponse
                    # Vite build 产物：assets/index.html（frontend/index.html 经过 Tailwind + sed 处理）
                    idx = _llm_assets / "index.html"
                    if not idx.exists():
                        raise HTTPException(status_code=404, detail="LLM Manager frontend not built")
                    # 同下方 llm_manager_static_files 的 Cache-Control 理由：避免更新后
                    # 浏览器仍复用旧缓存的页面壳子
                    return HTMLResponse(
                        content=idx.read_text(encoding="utf-8"),
                        headers={"Cache-Control": "no-cache"},
                    )
                
                @app.get("/llm-manager", include_in_schema=False)
                async def llm_manager_prod_redirect():
                    from fastapi.responses import RedirectResponse
                    return RedirectResponse(url="/llm-manager/", status_code=302)
                
                # Serve Vite build output (assets, scripts, shared, favicon)
                #
                # CVM部署测试发现（2026-07-03）：这些静态文件（尤其 shared/js/auth.js、
                # scripts/main.js）文件名固定不带content hash（不同于demo/chat的Next.js
                # 构建产物，chunk文件名会随内容变化自动带哈希强制刷新缓存），此前
                # FileResponse 未显式设置 Cache-Control，浏览器会按启发式策略缓存——
                # 实测复现：本次CWAuth认证方案改造更新了auth.js后，用户浏览器仍在用
                # 改造前缓存的旧版本（仍发送Basic方案），导致反复要求登录。加上
                # `Cache-Control: no-cache` 强制浏览器每次都带 If-None-Match 向服务器
                # 校验 ETag 是否变化（未变化时仍走 304，不会增加实际流量/延迟成本），
                # 内容真正变化时能立即拿到最新文件，不再需要用户手动强刷。
                @app.get("/llm-manager/{r:path}", include_in_schema=False)
                async def llm_manager_static_files(r: str):
                    from fastapi import HTTPException
                    file = (_llm_static / r).resolve()
                    if not str(file).startswith(str(_llm_static.resolve())) or not file.is_file():
                        raise HTTPException(status_code=404)
                    ext = file.suffix.lower()
                    mime_map = {".css":"text/css",".js":"application/javascript",".html":"text/html",".ico":"image/x-icon",".woff2":"font/woff2"}
                    return FileResponse(
                        str(file),
                        media_type=mime_map.get(ext, "application/octet-stream"),
                        headers={"Cache-Control": "no-cache"},
                    )
                
                print("[OK] LLM_Manager integrated (Production Mode)")
                print(f"   - UI: http://{API_HOST}:{API_PORT}/llm-manager")
                print(f"   - API: http://{API_HOST}:{API_PORT}/llm-manager/api")
        except Exception as e:
            logger.error(f"Failed to integrate LLM_Manager: {e}")
            print(f"[WARN] Failed to integrate LLM_Manager: {e}")
            import traceback
            traceback.print_exc()
    
    # Note: API/static backup removed as we now rely on Vite-built frontend for LLM Manager

    # 生产模式下挂载 Next.js 静态导出的前端文件
    # 开发模式下前端由 Next.js dev server (:3000) 提供
    # SPA fallback（404 → index.html）已统一处理在上方的 http_exception_handler 中
    dev_mode_global = os.getenv("DEV_MODE", "true").lower() == "true"
    if not dev_mode_global:
        frontend_dist = Path(__file__).parent.parent / "demo" / "chat" / "dist"
        if frontend_dist.exists():
            # 挂载 Next.js 特定的静态资源目录
            _next_dir = frontend_dist / "_next"
            if _next_dir.exists():
                app.mount("/_next", StaticFiles(directory=str(_next_dir)), name="nextjs-assets")
            logger.info(f"[OK] Frontend static files mounted from {frontend_dist}")
        else:
            logger.warning(f"[WARN] Frontend dist not found at {frontend_dist}, skipping frontend mount")

    return app


def main():
    """Main entry point to start the API server"""
    # Import HTTP server starter from utils (继承原始项目设计)
    from utils import start_http_server
    from config import HTTP_SERVER_PORT
    
    print("\n" + "="*60)
    print("DeepAnalyze API Server")
    print("="*60)
    print(f"API Server: http://{API_HOST}:{API_PORT}")
    print(f"File Server: http://localhost:{HTTP_SERVER_PORT}")
    print(f"API Docs: http://{API_HOST}:{API_PORT}/docs")
    
    if llm_manager.available:
        print(f"\nLLM Manager Integration: [ENABLED]")
        print(f"LLM Manager UI: http://{API_HOST}:{API_PORT}/llm-manager")
    else:
        print(f"\nLLM Manager Integration: [DISABLED]")
    print("="*60 + "\n")
    
    # Start HTTP file server in a separate thread (继承原始项目设计)
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Create and start the FastAPI application
    app = create_app()
    
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")


if __name__ == "__main__":
    main()
