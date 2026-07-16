# build_cython.py (放置于项目根目录)
"""
Cython 编译脚本 —— DeepAnalyze 代码保护方案 Layer 2 核心工具

用法:
    python build_cython.py                    # 编译默认模块（P0+P1，16个核心文件）
    python build_cython.py --include-p2       # 额外编译 P2 可选模块（需同步扩展 Dockerfile COPY 范围，见 docs/code-protection-plan.md §5.1.1）
    python build_cython.py --all              # 编译 P0+P1 + 待审计模块（validators.py），不含 P2
    python build_cython.py --all --include-p2 # 编译全部（P0+P1+P2+待审计）
    python build_cython.py --dry-run          # 预览将编译的模块
    python build_cython.py --clean            # 清理所有编译产物
    python build_cython.py --replace          # 编译后用 .pyd/.so 替换 .py
    python build_cython.py --output-dir DIR   # 输出到独立目录，源码无损（用于本地编译后部署）

v1.5 设计要点（源自 docs/code-protection-audit.md 四轮审计）:
    - P2 可选模块独立于 CORE_MODULES，需 --include-p2 显式启用，避免默认路径隐式静默失败
    - 编译完成后输出 compiled_files.txt 清单，供 Dockerfile 按清单删除源码（根治 Gap #3）
    - 文件不存在时的 SKIP 分支同时输出到 stderr，确保 CI/Docker 非交互环境能感知
    - if __name__ == "__main__" 保护 argparse 入口，import 本模块不会触发参数解析
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
BUILD_DIR = "build_cython"
MANIFEST_PATH = ROOT / "compiled_files.txt"

# MinGW-w64 便携式编译器路径（用于无 MSVC 的 Windows 环境）
# 可通过环境变量 MINGW64_PATH 覆盖，默认使用 portable-dev-env 下的工具链
_MINGW64_PATH = os.environ.get(
    "MINGW64_PATH",
    str(Path(os.environ.get("PORTABLE_DEV_ENV", ROOT.parent.parent.as_posix())) / "tools" / "mingw64" / "bin")
)


# =============================================================================
# 模块清单（详见 docs/code-protection-plan.md §4.3）
# =============================================================================

# 默认编译（P0+P1）：Dockerfile.compiled compiler 阶段 COPY 范围与此列表严格对齐
CORE_MODULES = [
    # P0: 核心风控算法（最高优先级）
    "deepanalyze/analysis/task_SOP/rule_mining.py",           # 401 KB - 已确认无 eval/exec
    "deepanalyze/analysis/task_SOP/scorecard_development.py", # 286 KB
    "deepanalyze/analysis/task_SOP/rule_mining_meta.py",      #  39 KB
    "deepanalyze/analysis/task_SOP/scorecard_meta.py",        #  31 KB
    "deepanalyze/analysis/task_SOP/executor.py",              # 109 KB - 已复核，无 eval/exec

    # P1: 报告引擎
    "deepanalyze/analysis/excel_report.py",                   # 226 KB
    "deepanalyze/analysis/html_report.py",                    # 176 KB
    "deepanalyze/analysis/word_report.py",                    # 144 KB
    "deepanalyze/analysis/markdown_report.py",                # 120 KB

    # P1: 数据分析引擎
    "deepanalyze/analysis/preprocessing.py",                  #  60 KB
    "deepanalyze/analysis/statistical_model.py",              #  17 KB
    "deepanalyze/analysis/feature_correlation.py",            #  10 KB
    "deepanalyze/analysis/iv_analysis.py",                    #   8 KB
    "deepanalyze/analysis/woe.py",                            #   8 KB
    "deepanalyze/analysis/feature_binning.py",                #   7 KB
    "deepanalyze/analysis/score_transformer.py",              #  10 KB
]

# 可选编译（P2）：认证/账户基础设施，默认不编译
# 若启用 --include-p2，必须同步在 Dockerfile.compiled 的 compiler 阶段
# 补充 COPY API/ 与 COPY deepanalyze/core/task_manager/
# 否则源文件不在 compiler stage → SKIP → 源码残留但保护效果为零（Gap #3）
OPTIONAL_P2_MODULES = [
    "API/AI_analysis_prompts.py",                              # 135 KB - 纯提示词模板
    "API/auth_middleware.py",                                   #  37 KB - 认证中间件
    "deepanalyze/core/task_manager/user_service.py",             #  20 KB - 账户 CRUD
    "deepanalyze/core/task_manager/user_migration_service.py",   #   7 KB - 迁移脚本
]

# 含真实 eval() 动态执行风险，需先审计 safe_globals 沙箱（见 §4.5）
DYNAMIC_MODULES = [
    "deepanalyze/analysis/task_SOP/validators.py",
]

# 明确不建议编译：含 FastAPI 路由装饰器，Cython 编译会破坏
# inspect.signature() 反射，导致 OpenAPI 生成/依赖注入异常
DO_NOT_COMPILE = [
    "API/sop_api.py",        # 51 处 @router.*
    "API/chat_api.py",       #  5 处 @router.*
    "API/export_api.py",     #  2 处 @router.*
    "API/admin_api.py",      #  2 处 @router.*
    "API/file_api.py",       #  6 处 @router.*
    "API/user_admin_api.py", #  8 处 @router.*
]


# =============================================================================
# 编译核心逻辑
# =============================================================================

def _get_extension_for_module(mod_path: str) -> str:
    """返回当前平台对应的 C 扩展后缀（.pyd on Windows / .so on Linux）"""
    # 延迟导入，避免顶层 import 触发 Cython/setuptools 在 --dry-run 时也被加载
    import importlib.machinery
    for suffix in importlib.machinery.EXTENSION_SUFFIXES:
        if suffix in (".pyd", ".so"):
            return suffix
    return ".so"  # 默认回退


def build_extensions(modules: list[str], output_dir: str | None = None) -> list[str]:
    """
    编译指定模块为 C 扩展。

    Args:
        modules: 待编译的模块路径列表
        output_dir: 输出目录（可选）。指定后 .pyd/.so 输出到此目录并保持包结构，
                    源码不受影响。不指定则 --inplace 编译到源码同级目录。

    返回实际成功进入编译流程的模块列表（用于生成清单文件）。
    """
    # 延迟导入，使本脚本作为纯数据模块 import 时不会触发 heavy dependency
    from Cython.Build import cythonize
    from setuptools import Extension, setup

    extensions = []
    actually_compiled = []
    skipped = []

    for mod_path in modules:
        p = Path(mod_path)
        if not p.exists():
            skipped.append(mod_path)
            continue

        module_name = str(p.with_suffix("")).replace("/", ".").replace("\\", ".")
        extensions.append(
            Extension(
                module_name,
                [mod_path],
                extra_compile_args=["-O2"],
            )
        )
        actually_compiled.append(mod_path)

    # SKIP 文件必须同时输出到 stderr，确保 CI/Docker 等非交互环境能感知
    if skipped:
        for mod_path in skipped:
            print(
                f"  WARNING SKIP: {mod_path} ("
                f"文件不存在，未被编译，源码不会被清理)", file=sys.stderr
            )
        print(
            f"\n*** 警告: {len(skipped)} 个模块因文件不存在被跳过，"
            f"若这些模块本应被编译，请检查是否需要扩展 COPY 范围"
            f"（常见于 P2 模块，见 docs/code-protection-plan.md §4.3）",
            file=sys.stderr,
        )

    if not extensions:
        print("没有需要编译的模块")
        return actually_compiled

    # --- 编译器检测（Windows 便携式环境支持 MinGW-w64）---
    if output_dir:
        build_lib_abs = str(Path(output_dir).resolve())
        script_args = ["build_ext", "--build-lib", build_lib_abs]
    else:
        script_args = ["build_ext", "--inplace"]
    mingw_path = None

    if sys.platform == "win32":
        # 检查 MSVC 是否可用
        msvc_available = False
        try:
            import subprocess
            result = subprocess.run(
                ["where", "cl.exe"], capture_output=True, text=True, timeout=5
            )
            msvc_available = result.returncode == 0
        except Exception:
            pass

        if not msvc_available:
            # 回退到 MinGW-w64
            mingw_bin = Path(_MINGW64_PATH)
            if (mingw_bin / "gcc.exe").exists():
                mingw_path = str(mingw_bin)
                os.environ["PATH"] = mingw_path + ";" + os.environ.get("PATH", "")
                script_args.append("--compiler=mingw32")
                print(f"[编译器] 使用 MinGW-w64: {mingw_path}")
            else:
                print(
                    f"[编译器] 警告: 未检测到 MSVC 或 MinGW-w64 (路径: {mingw_bin})，"
                    f"编译可能失败"
                )

    print(f"\n开始编译 {len(extensions)} 个模块...\n")
    setup(
        name="deepanalyze_compiled",
        ext_modules=cythonize(
            extensions,
            language_level="3",
            build_dir=BUILD_DIR,
            compiler_directives={
                "binding": False,          # 不暴露 C 函数签名
                "embedsignature": False,   # 不嵌入 Python 函数签名
                "always_allow_keywords": True,
                "annotation_typing": False,
            },
        ),
        script_args=script_args,
        zip_safe=False,
        packages=[],  # 只编译扩展模块，不打包 Python 包（避免 flat-layout 发现冲突）
    )
    return actually_compiled


def write_compiled_manifest(modules: list[str]) -> None:
    """
    将实际编译成功的模块列表写入 compiled_files.txt。
    Dockerfile.compiled 的 runtime 阶段据此清单删除对应源码，
    避免硬编码删除清单与 CORE_MODULES 脱节（Gap #3 根治方案）。
    """
    MANIFEST_PATH.write_text("\n".join(modules), encoding="utf-8")
    print(f"\n编译清单已写入: {MANIFEST_PATH} ({len(modules)} 个文件)")


def replace_py_files(modules: list[str]) -> None:
    """编译完成后，将原 .py 重命名为 .py.bak（.pyd/.so 自动优先加载）"""
    for mod_path in modules:
        p = Path(mod_path)
        bak = p.with_suffix(".py.bak") if p.suffix == ".py" else Path(str(p) + ".bak")
        if p.exists():
            p.rename(bak)
            print(f"  BAK: {mod_path} -> {bak.name}")


def restore_py_files(modules: list[str]) -> None:
    """恢复 .py.bak -> .py（用于开发调试）"""
    for mod_path in modules:
        p = Path(mod_path)
        bak = p.with_suffix(".py.bak") if p.suffix == ".py" else Path(str(p) + ".bak")
        if bak.exists():
            bak.rename(p)
            print(f"  RESTORE: {bak.name} -> {mod_path}")


def clean_all() -> None:
    """清理所有编译产物和中间文件，恢复开发环境"""
    # 删除编译产物（排除 .venv 虚拟环境目录）
    skip_dirs = {".venv", "venv", "node_modules", ".git"}
    for pattern in ["*.pyd", "*.so", "*.c", "*.html"]:
        for f in ROOT.rglob(pattern):
            if any(p.name in skip_dirs for p in f.parents):
                continue
            f.unlink()
            print(f"  DEL: {f}")

    # 删除构建目录
    for d in [BUILD_DIR, "build"]:
        p = ROOT / d
        if p.exists() and p.is_dir():
            shutil.rmtree(p)
            print(f"  DEL: {p}/")

    # 删除清单文件
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
        print(f"  DEL: {MANIFEST_PATH}")

    # 恢复 .py.bak
    for bak in ROOT.rglob("*.py.bak"):
        py_file = bak.with_suffix("")
        if not py_file.exists():
            bak.rename(py_file)
            print(f"  RESTORE: {bak} -> {py_file}")


def print_summary(modules: list[str]) -> None:
    """打印编译范围预览"""
    total = 0
    for m in modules:
        p = Path(m)
        if p.exists():
            size = p.stat().st_size / 1024
            total += size
            flag = (
                "\033[91m"  # red for DYNAMIC
                if m in DYNAMIC_MODULES
                else ("\033[93m"  # yellow for P2
                      if m in OPTIONAL_P2_MODULES
                      else "\033[92m")  # green for default
            )
            reset = "\033[0m"
            print(f"  {flag}{m}{reset} ({size:.0f} KB)")
        else:
            print(f"  WARNING {m} (文件不存在，将被 SKIP)")
    print(f"\n 总计: {len(modules)} 个模块, {total:.0f} KB")

    dynamic_included = any(m in modules for m in DYNAMIC_MODULES)
    if dynamic_included:
        print("\n  WARNING: 包含动态执行模块，请确保已审计 exec()/eval() 调用")

    p2_included = any(m in modules for m in OPTIONAL_P2_MODULES)
    if p2_included:
        print(
            "\n  提示: 包含 P2 可选模块，请确认 Dockerfile.compiled 的 compiler 阶段"
            "已扩展 COPY 范围（COPY API/ 与 COPY deepanalyze/core/task_manager/），"
            "否则这些文件会因源文件不存在被 SKIP"
        )


# =============================================================================
# 命令行入口
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="DeepAnalyze Cython 编译工具")
    parser.add_argument(
        "--all", action="store_true",
        help="编译核心模块 + 待审计模块（validators.py）；不含 P2"
    )
    parser.add_argument(
        "--include-p2", action="store_true",
        help="额外编译 OPTIONAL_P2_MODULES"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅预览编译范围，不实际编译"
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="清理所有编译产物和中间文件"
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="编译后用 .pyd/.so 替换原 .py 文件"
    )
    parser.add_argument(
        "--restore", action="store_true",
        help="恢复 .py.bak -> .py"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="跳过交互确认，用于 CI/Docker 等非交互环境"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None, metavar="DIR",
        help="输出目录：编译 .pyd/.so 到此目录并保持包结构，源码不受影响。"
             "用于本地编译后部署到其他机器。与 --replace 互斥。"
    )
    args = parser.parse_args()

    # --- 清理/恢复操作 ---
    if args.clean:
        print("清理所有编译产物...")
        clean_all()
        return

    if args.restore:
        modules = CORE_MODULES.copy()
        if args.all:
            modules += DYNAMIC_MODULES
        if args.include_p2:
            modules += OPTIONAL_P2_MODULES
        print("恢复 .py 源文件...")
        restore_py_files(modules)
        return

    # --- 确定编译范围 ---
    modules = CORE_MODULES.copy()
    if args.all:
        modules += DYNAMIC_MODULES
    if args.include_p2:
        modules += OPTIONAL_P2_MODULES

    # --- 预览模式 ---
    if args.dry_run:
        print(f"=== 编译预览 ({len(modules)} 个模块) ===\n")
        print_summary(modules)

        excluded_dynamic = [m for m in DYNAMIC_MODULES if m not in modules]
        if excluded_dynamic:
            print(f"\n未包含 {len(excluded_dynamic)} 个待审计模块 (--all):")
            for m in excluded_dynamic:
                print(f"  [待审计] {m}")
        excluded_p2 = [m for m in OPTIONAL_P2_MODULES if m not in modules]
        if excluded_p2:
            print(f"\n未包含 {len(excluded_p2)} 个 P2 可选模块 (--include-p2):")
            for m in excluded_p2:
                print(f"  [P2可选] {m}")
        print(f"\n以下模块因含 FastAPI 路由装饰器，任何模式下都不会被编译: "
              f"{len(DO_NOT_COMPILE)} 个")
        return

    # --- 编译确认（--output-dir 模式自动跳过确认，源码不受影响）---
    if args.output_dir:
        args.yes = True  # 输出到独立目录，不修改源码，无需确认
        print(f"\n输出目录: {Path(args.output_dir).resolve()}")
        print("（编译产物输出到独立目录，源码不受影响）")
    else:
        print(f"=== DeepAnalyze Cython 编译 ({len(modules)} 个模块) ===\n")
        print_summary(modules)

        excluded_dynamic = [m for m in DYNAMIC_MODULES if m not in modules]
        if excluded_dynamic:
            print(f"\n未包含 {len(excluded_dynamic)} 个待审计模块 (使用 --all 编译):")
            for m in excluded_dynamic:
                print(f"  [待审计] {m}")
        excluded_p2 = [m for m in OPTIONAL_P2_MODULES if m not in modules]
        if excluded_p2:
            print(f"\n未包含 {len(excluded_p2)} 个 P2 可选模块 (使用 --include-p2 编译):")
            for m in excluded_p2:
                print(f"  [P2可选] {m}")
        print(f"\n以下模块因含 FastAPI 路由装饰器，任何模式下都不会被编译: "
              f"{len(DO_NOT_COMPILE)} 个")

        confirm = "y" if args.yes else input("\n确认编译? [y/N] ")
        if confirm.lower() != "y":
            print("已取消")
            return

    # --- 执行编译 ---
    actually_compiled = build_extensions(modules, output_dir=args.output_dir)

    # 写入清单文件
    if actually_compiled:
        if args.output_dir:
            # 清单写入输出目录
            manifest_dest = Path(args.output_dir) / "compiled_files.txt"
            manifest_dest.parent.mkdir(parents=True, exist_ok=True)
            manifest_dest.write_text("\n".join(actually_compiled), encoding="utf-8")
            print(f"\n编译清单已写入: {manifest_dest} ({len(actually_compiled)} 个文件)")
        else:
            write_compiled_manifest(actually_compiled)

    # 可选：替换源文件（--output-dir 模式下不执行，源码不受影响）
    if args.replace and not args.output_dir:
        replace_py_files(actually_compiled)
        print("\n源码已替换为编译产物")
    elif args.output_dir:
        print("\n编译产物已输出到独立目录，源码未受影响。")
        print("\n=== 部署步骤 ===")
        print(f"1. 将项目源码复制到 {args.output_dir}/ ")
        print(f"   xcopy /E . {args.output_dir}\\ /EXCLUDE:exclude.txt")
        print(f"   或 rsync -a --exclude-from=exclude.txt . {args.output_dir}/")
        print(f"2. 按 compiled_files.txt 清单删除输出目录中的 .py 源码:")
        print(f"   cd {args.output_dir}")
        print(f"   for /f %f in (compiled_files.txt) do @del \"%f\" 2>nul")
        print(f"   （或 Linux: xargs -a compiled_files.txt rm -f）")
        print(f"3. 部署 {args.output_dir}/ 到目标服务器，直接运行。")
    elif not args.replace:
        print("\n编译完成（源文件保留）")
        print("  提示: 使用 --replace 参数可将 .py 替换为编译产物")


if __name__ == "__main__":
    main()
