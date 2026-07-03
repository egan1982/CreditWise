"""
pytest 根配置 — 路径注入 + 本地环境依赖隔离

策略：预先将 deepanalyze.analysis 注册为一个轻量 stub 模块，
再把真实的 data_validator 子包挂载到这个 stub 上。
这样可以绕过 analysis/__init__.py 对 task_SOP/scorecardpy/aiohttp 的重量级依赖，
同时让 data_validator 相关测试正常运行。

本地 portable-dev-env 使用 Python 3.12，缺少 scorecardpy/aiohttp 等生产依赖，
这些依赖仅在 Docker 容器（生产）中可用。
"""
import sys
import os
import types
import importlib
import tempfile

_ROOT = os.path.dirname(__file__)
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "API"))

# ── 测试数据库隔离（2026-07-02 新增）──────────────────────────────────────
# 背景：部分测试（如性能测试/用户管理模块测试）调用 get_task_manager_db() 时未显式
# 传入 database_url，会落到 TaskManagerDB 的默认值 sqlite:///./task_manager.db——
# 也就是本地开发时正在使用的真实数据库文件。历史上曾出现整个 pytest 会话跑下来，
# 往真实 task_manager.db 里灌入近5000条测试脏数据（session_id=alice/bob/session-perf等），
# 污染了开发环境里的任务历史列表。
# 这里在任何测试代码 import 到 database.py 之前，把 TASK_MANAGER_DB_URL 环境变量
# 指向一个进程级临时文件，使所有"未显式传参"的 get_task_manager_db() 调用都自动落在
# 隔离的临时库上，不再触碰真实数据。已显式传入 database_url（如 tmp_path fixture）的
# 测试不受影响，继续按各自逻辑隔离。
os.environ.setdefault(
    "TASK_MANAGER_DB_URL",
    f"sqlite:///{tempfile.gettempdir()}/pytest_task_manager_{os.getpid()}.db",
)

# ── 测试鉴权状态隔离（2026-07-02 新增）──────────────────────────────────────
# 背景：本地开发时为了手动测试多用户模式，会把真实的 `.env` 改成 ENABLE_AUTH=true。
# `API/main.py` 在被 import 时会调用 `load_dotenv(.env)`，且 python-dotenv 默认
# `override=False`——只有当 os.environ 里*还没有*该变量时才会从 .env 写入。
# 若不做任何处理，pytest 进程一旦 import 到 API.main，就会把开发者本地 .env 里的
# ENABLE_AUTH 值带进整个测试会话，使一批"假定默认无鉴权"的用户管理模块测试意外收到
# 真实的 401 拦截（这些测试通过自定义中间件注入 `x-test-username` 头模拟身份，
# 并不携带真实 Basic Auth 凭证）。
# 这里强制显式设为 "false"（而非 setdefault），确保测试会话不受开发者本机 .env 状态
# 影响；测试内部若需要验证 ENABLE_AUTH=true 场景，会自行用 monkeypatch.setenv 覆盖，
# 不受此处初始值影响。
os.environ["ENABLE_AUTH"] = "false"

# ── 为 deepanalyze.analysis 注册轻量 stub，阻断重量级依赖链 ──────────────────
# 确保 deepanalyze 包本身可以正常初始化
import deepanalyze  # noqa: E402

# 创建 deepanalyze.analysis stub
_analysis_stub = types.ModuleType("deepanalyze.analysis")
_analysis_stub.__path__ = [os.path.join(_ROOT, "deepanalyze", "analysis")]
_analysis_stub.__package__ = "deepanalyze.analysis"
sys.modules["deepanalyze.analysis"] = _analysis_stub
deepanalyze.analysis = _analysis_stub  # type: ignore

# 直接加载 data_validator 子包（不经过 analysis/__init__）
import importlib.util as _ilu

def _load_subpkg(pkg_name: str, rel_path: str) -> types.ModuleType:
    """直接从文件系统加载子包，注册到 sys.modules"""
    pkg_dir = os.path.join(_ROOT, rel_path)
    init_path = os.path.join(pkg_dir, "__init__.py")
    spec = _ilu.spec_from_file_location(pkg_name, init_path,
        submodule_search_locations=[pkg_dir])
    mod = _ilu.module_from_spec(spec)
    sys.modules[pkg_name] = mod
    spec.loader.exec_module(mod)
    return mod

_dv = _load_subpkg(
    "deepanalyze.analysis.data_validator",
    "deepanalyze/analysis/data_validator",
)
_analysis_stub.data_validator = _dv  # type: ignore
