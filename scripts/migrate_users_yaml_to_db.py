#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户管理模块 批次2 Phase9：config/users.yaml → users表 一次性导入脚本

用法：
    cd workspace/DeepAnalyze
    .venv/Scripts/python.exe scripts/migrate_users_yaml_to_db.py           # 执行导入
    .venv/Scripts/python.exe scripts/migrate_users_yaml_to_db.py --dry-run # 仅预览，不写入

说明：
    - 幂等：已存在于 users 表的 username 会被跳过（不覆盖），可安全重复执行。
    - 密码哈希原样搬运（yaml 里已经是 bcrypt 哈希），不会重新加密，也不会要求
      输入明文密码——迁移后用户仍可用原密码登录。
    - 导入完成后 config/users.yaml 保留作为灾备/离线场景兜底，不会被本脚本删除。
    - `SimpleAuth`（Phase10 已完成）会在每次登录请求时实时检测 users 表是否有记录：
      表中一旦有记录即自动优先走数据库鉴权，否则回退读 yaml——本脚本执行完成后，
      下一次登录请求即生效，无需重启服务。

详见 docs/user_management_module_design.md §十三。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 项目根目录加入 sys.path，保证无论从哪个 cwd 运行都能正确 import
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import yaml  # noqa: E402


def _load_yaml_users(yaml_path: Path) -> list:
    if not yaml_path.exists():
        print(f"❌ 未找到 {yaml_path}，无需迁移（可能本就是全新部署，尚未配置过 users.yaml）")
        return []
    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    users = config.get("users") or []
    if not users:
        print(f"⚠️  {yaml_path} 中没有配置任何用户")
    return users


def main() -> int:
    parser = argparse.ArgumentParser(description="将 config/users.yaml 中的账户导入 users 表")
    parser.add_argument("--dry-run", action="store_true", help="仅预览将要导入的账户，不实际写入数据库")
    parser.add_argument(
        "--yaml-path",
        default=str(_PROJECT_ROOT / "config" / "users.yaml"),
        help="users.yaml 路径（默认 config/users.yaml）",
    )
    args = parser.parse_args()

    yaml_path = Path(args.yaml_path)
    yaml_users = _load_yaml_users(yaml_path)
    if not yaml_users:
        return 0

    print(f"从 {yaml_path} 读取到 {len(yaml_users)} 个账户：")
    for u in yaml_users:
        print(f"  - {u.get('username')} (role={u.get('role', 'user')}, valid_until={u.get('valid_until') or '永久'})")

    if args.dry_run:
        print("\n[--dry-run] 未执行任何写入操作。去掉 --dry-run 参数以实际导入。")
        return 0

    from deepanalyze.core.task_manager.database import get_task_manager_db
    from deepanalyze.core.task_manager.user_service import UserService

    # 触发数据库初始化（会自动 create_all，包括新增的 users 表）
    get_task_manager_db()

    before = UserService.count_users()
    result = UserService.import_from_yaml_users(yaml_users)
    after = UserService.count_users()

    print(f"\n✅ 导入完成：users 表账户数 {before} → {after}")
    print(f"  已导入: {result['imported']}")
    if result["skipped_existing"]:
        print(f"  已跳过（表中已存在，未覆盖）: {result['skipped_existing']}")
    if result["errors"]:
        print(f"  ⚠️ 导入失败项:")
        for e in result["errors"]:
            print(f"    - {e['username']}: {e['error']}")

    print(
        "\n提示：下一次登录请求即会自动优先走数据库鉴权（SimpleAuth 实时检测 users 表，"
        "无需重启服务）。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
