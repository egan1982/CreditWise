#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户管理模块 批次1 Phase5：历史数据迁移脚本（admin 人工映射兜底路径）

背景：
    workspace 目录历史上按前端随机生成的 session_<timestamp>_<random> 隔离，
    未与登录用户名绑定。多用户模式上线后，主路径是"用户自助认领"
    （见 API `POST /workspace/claim-legacy-session`）。
    本脚本处理主路径覆盖不到的残留数据：用户已清缓存、换终端等，
    无法在前端自证归属的历史目录，由 admin 人工比对后批量迁移。

用法：
    # 第一步：扫描 workspace/，生成待人工审核的CSV报表（不做任何写入）
    python scripts/migrate_user_isolation.py --scan

    # 第二步：admin人工审核报表，填写映射文件 mapping.csv（两列：old_session_id,new_username）
    # 第三步：先 dry-run 预览（默认，不加 --apply 就是 dry-run）
    python scripts/migrate_user_isolation.py --mapping-file mapping.csv

    # 第四步：确认无误后真正执行
    python scripts/migrate_user_isolation.py --mapping-file mapping.csv --apply

    # 可选：把mapping.csv中未覆盖、但明显是历史遗留格式的目录归档到 workspace/_legacy/
    python scripts/migrate_user_isolation.py --mapping-file mapping.csv --apply --quarantine-unmapped

安全设计（详见 docs/user_management_module_design.md §六 / §八）：
    - 默认 dry-run，需显式 --apply 才真正写入/移动文件
    - 执行顺序固定为"先回填DB → 再移动文件目录 → 写进度记录"，
      进度记录保证中断后重跑可跳过已完成项（幂等）
    - 不物理删除任何数据，仅移动/改名
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "API"))

PROGRESS_FILE = _PROJECT_ROOT / "logs" / "migration_progress.json"
DEFAULT_REPORT_FILE = _PROJECT_ROOT / "logs" / "migration_scan_report.csv"


def _load_known_usernames() -> set:
    """从 config/users.yaml 读取当前所有已知用户名（用于判断哪些目录\"已经是正常用户目录\"）"""
    import yaml

    users_yaml = _PROJECT_ROOT / "config" / "users.yaml"
    if not users_yaml.exists():
        users_yaml = _PROJECT_ROOT / "config" / "users.yaml.example"
    if not users_yaml.exists():
        return set()
    with open(users_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {u.get("username") for u in data.get("users", []) if u.get("username")}


def _load_progress() -> Dict[str, Any]:
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"completed": {}}
    return {"completed": {}}


def _save_progress(progress: Dict[str, Any]) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def _dir_stats(path: Path) -> Dict[str, Any]:
    file_count = 0
    total_size = 0
    last_modified = 0.0
    for p in path.rglob("*"):
        if p.is_file():
            file_count += 1
            try:
                stat = p.stat()
                total_size += stat.st_size
                last_modified = max(last_modified, stat.st_mtime)
            except OSError:
                pass
    return {
        "file_count": file_count,
        "total_size_bytes": total_size,
        "last_modified": (
            datetime.fromtimestamp(last_modified).isoformat() if last_modified else ""
        ),
    }


def cmd_scan(workspace_dir: Path, report_file: Path) -> None:
    """扫描 workspace/，生成CSV报表：候选的\"待认领历史遗留会话\"目录清单"""
    from deepanalyze.core.task_manager.user_migration_service import is_legacy_session_id

    known_usernames = _load_known_usernames()
    rows: List[Dict[str, Any]] = []

    if not workspace_dir.exists():
        print(f"workspace 目录不存在: {workspace_dir}")
        return

    for entry in sorted(workspace_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name in known_usernames:
            continue  # 已经是正常用户目录，跳过
        if name == "_legacy":
            continue
        stats = _dir_stats(entry)
        rows.append({
            "session_id": name,
            "looks_legacy_format": is_legacy_session_id(name),
            "suggested_action": "人工比对后填入mapping.csv" if is_legacy_session_id(name) else "格式异常，需人工确认",
            **stats,
        })

    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["session_id", "looks_legacy_format", "suggested_action",
                        "file_count", "total_size_bytes", "last_modified"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"扫描完成：{len(rows)} 个待人工审核目录，报表已写入 {report_file}")
    print("请人工比对后创建 mapping.csv（两列：old_session_id,new_username），"
          "再运行 --mapping-file 执行迁移。")


def cmd_migrate(workspace_dir: Path, mapping_file: Path, apply: bool, quarantine_unmapped: bool) -> None:
    """读取mapping.csv，逐条迁移；支持从进度文件恢复中断的批次"""
    from deepanalyze.core.task_manager.user_migration_service import (
        is_legacy_session_id, merge_user_data,
    )

    if not mapping_file.exists():
        print(f"映射文件不存在: {mapping_file}")
        sys.exit(1)

    progress = _load_progress()
    completed: Dict[str, Any] = progress.setdefault("completed", {})

    mappings: List[Dict[str, str]] = []
    with open(mapping_file, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            old_id = (row.get("old_session_id") or "").strip()
            new_user = (row.get("new_username") or "").strip()
            if old_id and new_user:
                mappings.append({"old_session_id": old_id, "new_username": new_user})

    print(f"共 {len(mappings)} 条映射，模式: {'APPLY（真正执行）' if apply else 'DRY-RUN（仅预览）'}")

    mapped_old_ids = set()
    for m in mappings:
        old_id, new_user = m["old_session_id"], m["new_username"]
        mapped_old_ids.add(old_id)

        if apply and old_id in completed:
            print(f"  [跳过-已完成] {old_id} -> {new_user}（进度文件中已标记完成）")
            continue

        try:
            result = merge_user_data(
                from_session_id=old_id,
                to_username=new_user,
                workspace_base_dir=str(workspace_dir),
                dry_run=not apply,
            )
        except ValueError as e:
            print(f"  [失败] {old_id} -> {new_user}: {e}")
            continue

        print(f"  [{'已迁移' if apply else '预览'}] {old_id} -> {new_user}: "
              f"task_records={result['task_records_matched']}, "
              f"execution_states={result['execution_states_matched']}, "
              f"workspace目录存在={result['workspace_dir_exists']}")

        if apply:
            completed[old_id] = {
                "to_username": new_user,
                "migrated_at": datetime.now().isoformat(),
                "result": result,
            }
            _save_progress(progress)  # 每条立即落盘，保证中断后可从下一条恢复

    if quarantine_unmapped and apply:
        _quarantine_unmapped(workspace_dir, mapped_old_ids, completed)


def _quarantine_unmapped(workspace_dir: Path, mapped_old_ids: set, completed: Dict[str, Any]) -> None:
    """把明显是历史遗留格式、但mapping.csv未覆盖的目录移动到 workspace/_legacy/ 供后续人工处理"""
    from deepanalyze.core.task_manager.user_migration_service import is_legacy_session_id
    import shutil

    legacy_dir = workspace_dir / "_legacy"
    known_usernames = _load_known_usernames()

    for entry in sorted(workspace_dir.iterdir()):
        if not entry.is_dir() or entry.name == "_legacy":
            continue
        name = entry.name
        if name in known_usernames or name in mapped_old_ids or name in completed:
            continue
        if not is_legacy_session_id(name):
            continue  # 不确定归属、且格式也不像遗留会话，不动它，避免误处理正常目录

        legacy_dir.mkdir(parents=True, exist_ok=True)
        dest = legacy_dir / name
        if dest.exists():
            dest = legacy_dir / f"{name}__{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.move(str(entry), str(dest))
        print(f"  [归档] {name} -> workspace/_legacy/{dest.name}（未映射，仅admin可后续处理）")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace-dir", default=str(_PROJECT_ROOT / "workspace"), help="workspace根目录")
    parser.add_argument("--scan", action="store_true", help="扫描并生成待审核报表")
    parser.add_argument("--report-file", default=str(DEFAULT_REPORT_FILE), help="扫描报表输出路径")
    parser.add_argument("--mapping-file", help="人工审核后的映射文件（CSV: old_session_id,new_username）")
    parser.add_argument("--apply", action="store_true", help="真正执行迁移（默认dry-run仅预览）")
    parser.add_argument("--quarantine-unmapped", action="store_true",
                         help="把mapping.csv未覆盖、但格式明显是历史遗留会话的目录归档到 workspace/_legacy/")
    args = parser.parse_args()

    workspace_dir = Path(args.workspace_dir)

    if args.scan:
        cmd_scan(workspace_dir, Path(args.report_file))
    elif args.mapping_file:
        cmd_migrate(workspace_dir, Path(args.mapping_file), args.apply, args.quarantine_unmapped)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
