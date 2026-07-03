#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户管理模块 批次2 补充：首个管理员账户 一键初始化脚本

⚠️ 提示：自本脚本创建后，`API/main.py` 已内置了等价的零账户自动兜底逻辑
（`_ensure_bootstrap_admin_if_empty`）——只要以 ENABLE_AUTH=true 正常启动服务，
检测到数据库0账户且 yaml 未配置时会自动创建同样效果的 admin 账户并打印一次性密码到
启动日志，**不需要手动跑本脚本**。本脚本现在主要用于以下场景：
  - 需要自定义初始用户名（默认自动兜底固定用 "admin"）
  - 需要在服务已运行、账户已存在的情况下应急重置密码（--reset-if-exists）
  - CI/自动化测试场景需要可控的固定密码（--password）

用法：
    cd workspace/DeepAnalyze
    .venv/Scripts/python.exe scripts/init_admin.py                  # 用户名默认 admin，随机生成密码
    .venv/Scripts/python.exe scripts/init_admin.py --username alice # 自定义用户名
    .venv/Scripts/python.exe scripts/init_admin.py --password xxx   # 自定义密码（不建议，见下方说明）

设计动机：
    多用户模式下 SimpleAuth 需要 users 表（或 config/users.yaml）中至少有一个账户才能登录。
    此前的路径是"手动复制 users.yaml.example → 跑 hash_password.py 生成哈希 → 手填yaml →
    再跑 migrate_users_yaml_to_db.py 导入数据库"，步骤繁琐，因此先有了本脚本；
    后续进一步把等价逻辑内置到了 main.py 启动流程里，多数场景已不再需要手动执行。

    本脚本直接调用 UserService.create_user() 写入数据库，一步到位，且：
    - 默认随机生成一个高强度密码（而非写死一个固定弱密码，如 admin123 —— 固定弱密码一旦被
      写进仓库模板/文档，会随公开仓库一起泄露，是经典的默认凭证安全隐患，故本脚本不提供
      "内置固定密码"的模式）
    - 密码仅在本次运行的终端一次性打印，不落盘、不写日志文件
    - 自动设置 must_change_password=True，首次登录会被强制要求改密（复用 SimpleAuth/
      前端已有的强制改密机制），即使这个初始密码被人看到，也只有极短的有效窗口

    若确实需要指定密码（如自动化测试场景），可用 --password 传入，但生产/交给测试同事使用的
    场景请优先使用默认的随机生成模式。

幂等性：
    若 users 表中已存在同名账户，脚本会报错退出，不会覆盖已有账户（避免误伤已在使用的账户）。
    如需重置密码，请使用 Web UI「用户管理」页面的"重置密码"功能，或
    scripts/migrate_users_yaml_to_db.py 之外的管理接口，而非重新跑本脚本。

详见 docs/user_management_module_design.md §十七。
"""

from __future__ import annotations

import argparse
import io
import secrets
import string
import sys
from pathlib import Path

# 项目根目录加入 sys.path，保证无论从哪个 cwd 运行都能正确 import
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Windows 下终端默认代码页是 GBK（936），而本脚本输出含中文与 emoji，直接 print 会抛
# UnicodeEncodeError 导致脚本在打印一次性密码之前崩溃（密码哈希已入库、明文却没能显示，
# 造成账户创建成功但密码丢失）。这里强制 stdout/stderr 用 UTF-8 编码，异常字符用 replace
# 兜底，确保无论终端代码页如何都不会在打印阶段崩溃。
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _generate_random_password(length: int = 14) -> str:
    """生成一个高强度随机密码（字母大小写+数字+少量安全符号，避免歧义字符如 0/O/1/l）"""
    alphabet = "".join(
        c for c in (string.ascii_letters + string.digits + "!@#%^&*")
        if c not in "0Ol1I"
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> int:
    parser = argparse.ArgumentParser(description="一键创建首个管理员账户（写入数据库，跳过手动编辑 yaml）")
    parser.add_argument("--username", default="admin", help="管理员用户名（默认: admin）")
    parser.add_argument(
        "--password",
        default=None,
        help="指定密码（不指定则自动生成随机高强度密码，推荐使用默认行为）",
    )
    parser.add_argument("--org", default="", help="部门/组织备注（可选）")
    parser.add_argument(
        "--no-force-change",
        action="store_true",
        help="不强制首次登录改密（不推荐，仅供自动化测试场景使用）",
    )
    parser.add_argument(
        "--reset-if-exists",
        action="store_true",
        help="若该用户名已存在，改为重置其密码（而非报错退出）；用于Web UI尚未可用时的应急恢复，"
        "正常场景请优先使用「用户管理」页面的重置密码功能",
    )
    args = parser.parse_args()

    from deepanalyze.core.task_manager.database import get_task_manager_db
    from deepanalyze.core.task_manager.user_service import UserService, UsernameConflictError

    # 触发数据库初始化（自动 create_all，包括 users 表）
    get_task_manager_db()

    existing_count = UserService.count_users()
    password = args.password or _generate_random_password()
    action = "创建"

    try:
        UserService.create_user(
            username=args.username,
            password=password,
            role="admin",
            org=args.org or None,
            description="初始管理员账户（scripts/init_admin.py 创建）",
            must_change_password=not args.no_force_change,
            created_by="init_admin_script",
        )
    except UsernameConflictError as e:
        if not args.reset_if_exists:
            print(f"❌ 创建失败：用户名 '{args.username}' 已存在（{e}）")
            print(
                "   如需重置该账户密码，请使用「用户管理」Web UI 的重置密码功能，"
                "或加 --reset-if-exists 参数重新运行本脚本。"
            )
            return 1
        UserService.set_password(
            username=args.username,
            new_password=password,
            must_change_password=not args.no_force_change,
        )
        action = "重置密码"
    except ValueError as e:
        print(f"❌ 创建失败：{e}")
        return 1

    print("=" * 60)
    print(f"✅ 管理员账户{action}成功")
    print("=" * 60)
    print(f"  用户名: {args.username}")
    print(f"  密码  : {password}")
    print("=" * 60)
    if not args.no_force_change:
        print("⚠️  该密码仅在此处显示一次，请立即记录。")
        print("   首次登录后会被强制要求修改密码（must_change_password=True）。")
    else:
        print("⚠️  该密码仅在此处显示一次，请立即记录并妥善保管。")
    new_count = UserService.count_users()
    print(f"\nusers 表账户数：{existing_count} → {new_count}")
    print(
        "\n提示：下一次登录请求即会自动优先走数据库鉴权（SimpleAuth 实时检测 users 表，"
        "无需重启服务）。请确保 .env 中 ENABLE_AUTH=true 后即可使用该账户登录。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
