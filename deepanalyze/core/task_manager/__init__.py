# -*- coding: utf-8 -*-
"""
Task Manager Module

提供统一的任务管理能力，包括：
- 任务进程控制：暂停、停止、恢复
- 任务记录持久化：保存到数据库
- 历史记录查询：多条件筛选、分页
- 阶段 AI 分析持久化（Phase 7）

设计原则：
1. 通用性：不耦合 Task SOP 业务逻辑，可复用至其他任务类型
2. 低侵入：通过扩展而非重写实现
3. 可扩展：支持未来扩展到 Redis/PostgreSQL 等存储后端
"""

from .enums import TaskStatus, TaskControlAction, TaskCategory, InteractionMode
from .models import TaskRecord, TaskControl, TaskManagerBase, ExecutionState, ExecutionCheckpoint, StageAIAnalysis, OverallAIAnalysis, User
from .database import TaskManagerDB, get_task_manager_db
from .controller import TaskController
from .history_service import TaskHistoryService
from .result_storage import TaskResultStorage, get_result_storage
from .checkpoint import CheckpointMixin, TaskPausedException, TaskStoppedException
from .persistent_store import PersistentExecutionStore
from .recovery import ExecutionStateRecovery
from .stage_analysis_service import StageAnalysisService
from .user_service import UserService, UsernameConflictError, validate_username

__all__ = [
    # Enums
    "TaskStatus",
    "TaskControlAction", 
    "TaskCategory",
    "InteractionMode",
    # Models
    "TaskRecord",
    "TaskControl",
    "TaskManagerBase",
    "ExecutionState",
    "ExecutionCheckpoint",
    "StageAIAnalysis",
    "OverallAIAnalysis",
    "User",
    # Database
    "TaskManagerDB",
    "get_task_manager_db",
    # Controller
    "TaskController",
    # History Service
    "TaskHistoryService",
    # Result Storage
    "TaskResultStorage",
    "get_result_storage",
    # Checkpoint
    "CheckpointMixin",
    "TaskPausedException",
    "TaskStoppedException",
    # Persistent Store (Phase 6)
    "PersistentExecutionStore",
    # Recovery Service (Phase 6)
    "ExecutionStateRecovery",
    # Stage Analysis Service (Phase 7)
    "StageAnalysisService",
    # User Service (批次2 Phase9/10)
    "UserService",
    "UsernameConflictError",
    "validate_username",
]
