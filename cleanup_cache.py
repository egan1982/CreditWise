#!/usr/bin/env python3
"""
Python缓存清理脚本
删除所有 __pycache__ 目录和 .pyc 文件
"""

import os
import shutil
from pathlib import Path


def clean_python_cache(start_path: str = "."):
    """清理指定路径下的所有Python缓存"""
    start_path = Path(start_path).resolve()
    print(f"开始清理: {start_path}")

    pycache_dirs = []
    pyc_files = []

    # 遍历目录
    for root, dirs, files in os.walk(start_path):
        # 收集 __pycache__ 目录
        if "__pycache__" in dirs:
            pycache_path = Path(root) / "__pycache__"
            pycache_dirs.append(pycache_path)
            dirs.remove("__pycache__")  # 不再递归进入

        # 收集 .pyc 文件
        for file in files:
            if file.endswith(".pyc") or file.endswith(".pyo"):
                pyc_path = Path(root) / file
                pyc_files.append(pyc_path)

    # 删除 __pycache__ 目录
    print(f"\n找到 {len(pycache_dirs)} 个 __pycache__ 目录")
    for pycache in pycache_dirs:
        try:
            shutil.rmtree(pycache)
            print(f"  ✓ 已删除: {pycache}")
        except Exception as e:
            print(f"  ✗ 删除失败: {pycache} - {e}")

    # 删除 .pyc 文件
    print(f"\n找到 {len(pyc_files)} 个 .pyc/.pyo 文件")
    for pyc_file in pyc_files:
        try:
            pyc_file.unlink()
            print(f"  ✓ 已删除: {pyc_file}")
        except Exception as e:
            print(f"  ✗ 删除失败: {pyc_file} - {e}")

    print(f"\n清理完成!")
    print(f"  删除目录: {len(pycache_dirs)} 个")
    print(f"  删除文件: {len(pyc_files)} 个")


if __name__ == "__main__":
    import sys

    # 默认清理当前目录，或接受命令行参数
    target_path = sys.argv[1] if len(sys.argv) > 1 else "."

    # 如果目标是相对路径，转换为绝对路径
    target = Path(target_path).resolve()

    if not target.exists():
        print(f"错误: 路径不存在 - {target}")
        sys.exit(1)

    confirm = input(f"确定要清理 {target} 下的Python缓存吗? [y/N]: ")
    if confirm.lower() == "y":
        clean_python_cache(target)
    else:
        print("已取消")
