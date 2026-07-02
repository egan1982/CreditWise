# -*- coding: utf-8 -*-
"""
用户管理模块 批次1 Phase5/6：数据迁移与账户合并服务

提供两类能力（详见 docs/user_management_module_design.md §六、§七）：
1. 用户自助认领旧 session（主路径）/ admin 批量迁移（兜底）的底层合并逻辑
2. 账户合并小工具（改名场景：把旧 session_id/username 名下的数据转移到新 username 下）

设计要点（对齐 M9/M10 决策）：
- 固定执行顺序："先回填 DB → 再移动文件目录 → 最后记录完成"，保证文件与DB不一致的
  时间窗口最短，且允许调用方在中断后重新调用（DB更新使用 WHERE session_id=old 的
  批量UPDATE，天然幂等；文件目录移动前会检测目标是否已存在，避免重复移动报错）。
- 默认 dry_run=True，只统计不写入，调用方需显式传 dry_run=False 才真正执行。
- 不做物理删除：目标目录已存在的同名文件，改名为 "name__migrated_<timestamp><ext>"
  保留，不覆盖不丢弃。
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict

from .database import get_task_manager_db
from .models import TaskRecord, ExecutionState

logger = logging.getLogger(__name__)

# 旧版随机 session_id 格式（前端历史遗留生成规则）：session_<timestamp>_<random>
LEGACY_SESSION_ID_PATTERN = re.compile(r'^session_\d+_[a-zA-Z0-9]+$')

# username / session_id 安全字符集（与 API/utils.py::_SAFE_ID_PATTERN 保持一致）
_SAFE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


def is_legacy_session_id(session_id: str) -> bool:
    """判断一个 session_id 是否为旧版随机生成格式（用于区分\"待认领的历史遗留会话\"
    和\"正常的其他用户目录\"，防止用户自助认领时误关联他人真实账户目录）。
    """
    return bool(LEGACY_SESSION_ID_PATTERN.match(session_id or ""))


def _merge_directory(src_dir: Path, dst_dir: Path) -> Dict[str, Any]:
    """将 src_dir 下的全部内容合并移动到 dst_dir（dst_dir 不存在则直接改名）。

    同名文件冲突时，源文件改名为 "<stem>__migrated_<timestamp><suffix>" 后再移动，
    不覆盖、不丢弃任何数据。
    """
    moved_files: list[str] = []
    renamed_conflicts: list[str] = []

    if not dst_dir.exists():
        # 目标不存在：整目录直接改名（最快路径，保留所有子目录结构）
        shutil.move(str(src_dir), str(dst_dir))
        return {"moved_files": ["<entire directory>"], "renamed_conflicts": []}

    dst_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    for item in list(src_dir.iterdir()):
        target = dst_dir / item.name
        if target.exists():
            new_name = f"{target.stem}__migrated_{ts}{target.suffix}"
            target = dst_dir / new_name
            renamed_conflicts.append(item.name)
        shutil.move(str(item), str(target))
        moved_files.append(item.name)

    # 源目录内容已全部移出，清理空目录
    try:
        src_dir.rmdir()
    except OSError:
        pass  # 目录非空（极少数并发写入场景）或权限问题，保留目录不强删

    return {"moved_files": moved_files, "renamed_conflicts": renamed_conflicts}


def merge_user_data(
    from_session_id: str,
    to_username: str,
    workspace_base_dir: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """将 from_session_id 名下的全部数据（task_records / execution_states /
    workspace目录）转移到 to_username 名下。

    Args:
        from_session_id: 旧 session_id 或旧 username（数据当前归属的标识）
        to_username: 新的登录用户名（数据应转移到的归属）
        workspace_base_dir: workspace 根目录（即 config.WORKSPACE_BASE_DIR）
        dry_run: True（默认）时只统计不写入；False 时真正执行迁移

    Returns:
        {
            "from": str, "to": str, "dry_run": bool,
            "task_records_matched": int, "execution_states_matched": int,
            "workspace_dir_exists": bool, "moved_files": [...], "renamed_conflicts": [...],
        }

    Raises:
        ValueError: from_session_id / to_username 未通过安全字符集校验，或两者相同
    """
    if not _SAFE_ID_PATTERN.match(from_session_id or ""):
        raise ValueError(f"Invalid from_session_id: {from_session_id!r}")
    if not _SAFE_ID_PATTERN.match(to_username or ""):
        raise ValueError(f"Invalid to_username: {to_username!r}")
    if from_session_id == to_username:
        raise ValueError("from_session_id 与 to_username 相同，无需迁移")

    db = get_task_manager_db()
    with db.get_session() as session:
        task_records_matched = (
            session.query(TaskRecord).filter(TaskRecord.session_id == from_session_id).count()
        )
        execution_states_matched = (
            session.query(ExecutionState).filter(ExecutionState.session_id == from_session_id).count()
        )

        if not dry_run:
            # ── Step 1: 先回填 DB（批量UPDATE，天然幂等，可安全重跑）──────────
            session.query(TaskRecord).filter(TaskRecord.session_id == from_session_id).update(
                {TaskRecord.session_id: to_username}, synchronize_session=False
            )
            session.query(ExecutionState).filter(ExecutionState.session_id == from_session_id).update(
                {ExecutionState.session_id: to_username}, synchronize_session=False
            )
            # get_session() 上下文退出时自动 commit

    result: Dict[str, Any] = {
        "from": from_session_id,
        "to": to_username,
        "dry_run": dry_run,
        "task_records_matched": task_records_matched,
        "execution_states_matched": execution_states_matched,
        "workspace_dir_exists": False,
        "moved_files": [],
        "renamed_conflicts": [],
    }

    # ── Step 2: 再移动 workspace 目录（DB已先落地，文件移动失败也不会丢线索）──
    src_dir = Path(workspace_base_dir) / from_session_id
    if src_dir.exists() and src_dir.is_dir():
        result["workspace_dir_exists"] = True
        if not dry_run:
            dst_dir = Path(workspace_base_dir) / to_username
            merge_result = _merge_directory(src_dir, dst_dir)
            result["moved_files"] = merge_result["moved_files"]
            result["renamed_conflicts"] = merge_result["renamed_conflicts"]
            logger.info(
                f"[UserMigration] Merged workspace dir {from_session_id} -> {to_username}: "
                f"{len(merge_result['moved_files'])} files moved, "
                f"{len(merge_result['renamed_conflicts'])} name conflicts renamed"
            )

    return result
