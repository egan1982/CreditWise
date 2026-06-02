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

_ROOT = os.path.dirname(__file__)
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "API"))

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
