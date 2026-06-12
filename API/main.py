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
from typing import Callable, List
from fastapi import FastAPI, UploadFile, File, Query

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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
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
            auth = SimpleAuth()
            app.add_middleware(BasicAuthMiddleware, auth=auth)
            logger.info("[OK] Basic Auth 认证中间件已启用")
        except FileNotFoundError as e:
            logger.error(f"[ERROR] 认证配置缺失: {e}")
            print(f"[ERROR] 认证配置缺失: {e}")
        except ImportError as e:
            logger.error(f"[ERROR] 认证依赖缺失: {e}")
            print(f"[ERROR] 认证依赖缺失（请安装 bcrypt 和 pyyaml）: {e}")
        except Exception as e:
            logger.error(f"[ERROR] 认证中间件初始化失败: {e}")
            print(f"[ERROR] 认证中间件初始化失败: {e}")

    # 添加全局异常处理器，确保异常响应也包含CORS头
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
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
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
    
    # Add workspace management endpoints
    @app.get("/workspace/files")
    async def get_workspace_files_endpoint(session_id: str = "default"):
        """获取工作区文件列表（继承原始项目设计）"""
        from pathlib import Path
        from utils import get_session_workspace, build_download_url, get_file_icon, validate_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
    async def delete_workspace_file(path: str, session_id: str = "default"):
        """删除工作区文件（继承原始项目设计）"""
        from pathlib import Path
        from fastapi import HTTPException
        from utils import get_session_workspace, validate_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
    async def download_file(file_path: str):
        """下载工作区文件（继承原始项目设计）"""
        from pathlib import Path
        from fastapi import HTTPException
        from fastapi.responses import FileResponse
        import mimetypes
        from config import WORKSPACE_BASE_DIR
        
        # 文件路径格式: session_id/[generated/]filename
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
        session_id: str = Query("default"), 
        dir: str = Query(""),
        files: List[UploadFile] = File(...)
    ):
        """上传文件到工作区（继承原始项目设计）"""
        from pathlib import Path
        from utils import get_session_workspace, validate_session_id, check_upload_size
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
    async def clear_workspace(session_id: str = "default"):
        """清空工作区（继承原始项目设计）"""
        from pathlib import Path
        import shutil
        from utils import get_session_workspace, validate_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
        session_id: str = "default",
        messages: list = None,
        title: str = "Report"
    ):
        """导出报告（继承原始项目设计）"""
        from pathlib import Path
        from datetime import datetime
        import re
        from utils import get_session_workspace, build_download_url, validate_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
    async def workspace_tree_endpoint(session_id: str = "default"):
        """获取工作区文件树结构（继承原始项目设计）"""
        from pathlib import Path
        from utils import get_session_workspace, build_download_url, get_file_icon, validate_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
        from utils import get_session_workspace, validate_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
        src: str = Query(..., description="relative source path under workspace"),
        dst_dir: str = Query("", description="relative target directory under workspace"),
        session_id: str = Query("default"),
    ):
        """在同一 workspace 内移动（或重命名）文件/目录（继承原始项目设计）"""
        from fastapi import HTTPException
        from utils import get_session_workspace, uniquify_path, validate_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
        path: str = Query(..., description="relative directory under workspace"),
        recursive: bool = Query(True, description="delete directory recursively"),
        session_id: str = Query("default"),
    ):
        """删除 workspace 下的目录（继承原始项目设计）"""
        from fastapi import HTTPException
        from utils import get_session_workspace, validate_session_id
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
        dir: str = Query("", description="relative directory under workspace"),
        files: List[UploadFile] = File(...),
        session_id: str = Query("default"),
    ):
        """上传文件到 workspace 下的指定子目录（继承原始项目设计）"""
        from fastapi import HTTPException
        from utils import get_session_workspace, uniquify_path, validate_session_id, check_upload_size
        
        try:
            session_id = validate_session_id(session_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
    
    # LLM Manager direct access (without trailing slash) - 开发模式重定向到Vite服务器
    if llm_manager.available and llm_manager.create_app is not None:
        @app.get("/llm-manager", include_in_schema=False)
        async def llm_manager_direct():  # pyright: ignore[reportUnusedFunction]
            """直接访问LLM Manager - 开发模式重定向到Vite，生产模式由子应用处理"""
            from fastapi.responses import RedirectResponse
            
            # 开发模式下重定向到Vite服务器
            dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
            if dev_mode:
                return RedirectResponse(url="http://localhost:3001", status_code=302)
            
            # 生产模式下重定向到子应用根路径（带斜杠）
            return RedirectResponse(url="/llm-manager/", status_code=302)

    # Integrate LLM_Manager - Backend Only in Development, Backend + Frontend in Production
    if llm_manager.available and llm_manager.create_app is not None:
        try:
            # Check if we're in development mode (Vite server is running)
            dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
            
            # In development mode, only mount the backend API to avoid conflicts with Vite server
            # In production mode, mount both backend and frontend
            llm_manager_app = llm_manager.create_app(
                config={
                    "app_title": "LLM API Manager for DeepAnalyze",
                    "cors_origins": cors_origins,
                },
                as_subapp=True,
                enable_frontend=not dev_mode,  # Disable frontend in development mode
                prefix="/llm-manager"
            )
            
            # Mount the LLM_Manager app at /llm-manager
            # In dev mode: API only (frontend served by Vite at port 3001)
            # In prod mode: Both API and frontend
            app.mount("/llm-manager", llm_manager_app)
            
            if dev_mode:
                print("[OK] LLM_Manager backend integrated (Development Mode)")
                print(f"   - API: http://{API_HOST}:{API_PORT}/llm-manager/api")
                print(f"   - Docs: http://{API_HOST}:{API_PORT}/llm-manager/docs")
                print(f"   - Frontend: Running on Vite server at http://localhost:3001")
            else:
                print("[OK] LLM_Manager integrated (Production Mode)")
                print(f"   - UI: http://{API_HOST}:{API_PORT}/llm-manager")
                print(f"   - API: http://{API_HOST}:{API_PORT}/llm-manager/api")
                print(f"   - Docs: http://{API_HOST}:{API_PORT}/llm-manager/docs")
        except Exception as e:
            logger.error(f"Failed to integrate LLM_Manager: {e}")
            print(f"[WARN] Failed to integrate LLM_Manager: {e}")
            import traceback
            traceback.print_exc()
    
    # Note: API/static backup removed as we now rely on Vite-built frontend for LLM Manager

    # 生产模式下挂载 Next.js 静态导出的前端文件
    # 开发模式下前端由 Next.js dev server (:3000) 提供
    dev_mode_global = os.getenv("DEV_MODE", "true").lower() == "true"
    if not dev_mode_global:
        frontend_dist = Path(__file__).parent.parent / "demo" / "chat" / "dist"
        if frontend_dist.exists():
            # 挂载 Next.js 特定的静态资源目录
            _next_dir = frontend_dist / "_next"
            if _next_dir.exists():
                app.mount("/_next", StaticFiles(directory=str(_next_dir)), name="nextjs-assets")

            # 已知的 API 路径前缀（这些不应 fallback 到前端）
            _api_prefixes = (
                "/v1/", "/sop/", "/workspace/", "/health", "/docs",
                "/openapi", "/llm-manager/", "/download/", "/execute/",
                "/export/", "/chat/",
            )

            from starlette.exceptions import HTTPException as StarletteHTTPException

            @app.exception_handler(StarletteHTTPException)
            async def spa_fallback(request, exc):
                """
                非 API 路径的 404:
                - 先看 dist/ 下有没有对应的静态文件（图片、favicon 等）
                - 没有则返回 index.html（SPA 路由支持）
                API 路径的错误正常返回 JSON
                """
                path = request.url.path
                if exc.status_code == 404 and not path.startswith(_api_prefixes):
                    # 尝试在 dist/ 下找到对应的静态文件
                    static_file = frontend_dist / path.lstrip("/")
                    if static_file.is_file():
                        return FileResponse(str(static_file))
                    # SPA fallback: 返回 index.html
                    index_file = frontend_dist / "index.html"
                    if index_file.exists():
                        return FileResponse(str(index_file))
                # API 路径或非 404 错误，正常返回 JSON
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail or "Not found"},
                )

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
