"""版本号统一管理脚本"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def update_version(new_version: str):
    """更新所有版本号"""
    
    files_to_update = [
        "deepanalyze/__init__.py",
        "llm_manager_integrated/__version__.py",
        "API/main.py",
        "pyproject.toml",
    ]
    
    for file_path in files_to_update:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            print(f"⚠️ 文件不存在: {file_path}")
            continue
        
        content = full_path.read_text(encoding="utf-8")
        
        # 根据文件类型更新版本号
        if file_path.endswith(".toml"):
            # pyproject.toml: version = "x.x.x"
            new_content = re.sub(
                r'^version = "[^"]+"',
                f'version = "{new_version}"',
                content,
                flags=re.MULTILINE
            )
        else:
            # Python 文件: __version__ = "x.x.x"
            new_content = re.sub(
                r'__version__ = "[^"]+"',
                f'__version__ = "{new_version}"',
                content
            )
            # API_VERSION = "x.x.x"
            new_content = re.sub(
                r'API_VERSION = "[^"]+"',
                f'API_VERSION = "{new_version}"',
                new_content
            )
        
        full_path.write_text(new_content, encoding="utf-8")
        print(f"✅ 已更新: {file_path}")
    
    print(f"\n🎉 版本号已统一更新为: {new_version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python scripts/bump_version.py <新版本号>")
        print("示例: python scripts/bump_version.py 1.1.0")
        sys.exit(1)
    
    new_version = sys.argv[1]
    update_version(new_version)
