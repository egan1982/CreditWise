#!/usr/bin/env python3
"""
生成 bcrypt 密码哈希值，用于 config/users.yaml

用法：
    python scripts/hash_password.py <password>
    python scripts/hash_password.py              # 交互式输入（不回显）

示例：
    python scripts/hash_password.py admin123
    → 将输出的哈希值复制到 config/users.yaml 的 password_hash 字段
"""
import sys

try:
    import bcrypt
except ImportError:
    print("错误：缺少 bcrypt 依赖，请先安装：")
    print("  pip install bcrypt")
    sys.exit(1)


def hash_password(password: str) -> str:
    """生成 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pwd = sys.argv[1]
    else:
        import getpass
        pwd = getpass.getpass("请输入密码: ")

    if not pwd:
        print("错误：密码不能为空")
        sys.exit(1)

    hashed = hash_password(pwd)
    print(f"\n密码哈希值:\n{hashed}")
    print("\n请将此值复制到 config/users.yaml 的 password_hash 字段")
