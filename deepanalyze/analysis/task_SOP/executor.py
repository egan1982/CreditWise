"""
SOP Task Executor - 统一任务执行引擎

Provides:
- Unified task execution interface
- Progress tracking and reporting
- Async execution support
- Result management
- Task persistence and control (pause/stop/resume)
"""
# pyright: reportConstantRedefinition=false
# pyright: reportImplicitRelativeImport=false
# pyright: reportAssignmentType=false
# pyright: reportExplicitAny=false
# pyright: reportAny=false
# pyright: reportUnusedImport=false
# pyright: reportImportCycles=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnnecessaryTypeIgnoreComment=false
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from .registry import SOPRegistry, SOPTaskDefinition

from .registry import get_registry

# JSON serializable type alias
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]

logger = logging.getLogger(__name__)

# =============================================================================
# Task Manager Integration
# =============================================================================
# Try to import task manager components, with fallback stubs if not available

TASK_MANAGER_AVAILABLE: bool = False

# Type aliases for task manager components
TaskHistoryService: Any = None
TaskController: Any = None
TaskControlAction: Any = None
TaskStatus: Any = None
TaskResultStorage: Any = None
get_result_storage: Any = None
CheckpointMixin: Any = None
TaskStoppedException: Any = Exception
InteractionMode: Any = None
PersistentExecutionStore: Any = None
ExecutionStateRecovery: Any = None

try:
    from deepanalyze.core.task_manager import (
        TaskHistoryService,
        TaskController,
        TaskControlAction,
        TaskStatus,
        TaskResultStorage,
        get_result_storage,
        CheckpointMixin,
        TaskStoppedException,
        InteractionMode,
        PersistentExecutionStore,
        ExecutionStateRecovery,
    )
    TASK_MANAGER_AVAILABLE = True
except ImportError:
    # Task manager not available, use stub values
    pass


# =============================================================================
# Execution Status
# =============================================================================

class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageRetryException(Exception):
    """阶段重试异常
    
    当用户请求重试某个阶段时抛出此异常，
    用于中断当前 Pipeline 执行并从指定阶段重新开始。
    """
    stage_id: str
    
    def __init__(self, stage_id: str, message: str = ""):
        self.stage_id = stage_id
        super().__init__(message or f"Stage retry requested: {stage_id}")


# =============================================================================
# Expert Mode Helper Functions
# =============================================================================

def check_expert_mode_pause(
    context: "ExecutionContext",
    stage_id: str,
    registry: "SOPRegistry | None" = None
) -> bool:
    """
    检查专家模式下是否需要在阶段完成后暂停
    
    统一的专家模式暂停逻辑，供Pipeline模式使用。
    
    Args:
        context: 执行上下文
        stage_id: 当前完成的阶段ID
        registry: SOP注册表（可选，用于获取任务定义）
        
    Returns:
        True: 已设置暂停信号
        False: 无需暂停（非专家模式、最后阶段、或TaskManager不可用）
    """
    # 非专家模式，不暂停
    if context.interaction_mode != "expert":
        return False
    
    # TaskManager不可用，无法设置暂停信号
    if not TASK_MANAGER_AVAILABLE:
        logger.warning("[Expert Mode] TaskManager not available, cannot pause")
        return False
    
    # 检查是否标记为跳过专家模式暂停（用于阶段重试时的前置阶段）
    if stage_id in context.stages:
        stage = context.stages[stage_id]
        if stage.output_preview and stage.output_preview.get('_skip_expert_pause'):
            logger.info(f"[Expert Mode] Stage {stage_id} has _skip_expert_pause flag, skipping pause")
            return False
    
    # 检查是否是已执行完的重试阶段（从context.executed_retry_stages获取）
    # 如果当前完成的阶段是重试阶段，不暂停
    if hasattr(context, 'executed_retry_stages') and stage_id in context.executed_retry_stages:
        logger.info(f"[Expert Mode] Stage {stage_id} is in executed retry stages, skipping pause")
        return False
    
    # 获取任务定义以检查是否还有后续阶段
    if registry is None:
        registry = get_registry()
    
    task_def = registry.get_task(context.task_id)
    if not task_def:
        logger.warning(f"[Expert Mode] Task definition not found: {context.task_id}")
        return False
    
    # 检查是否还有后续阶段
    stage_ids = [s.id for s in task_def.stages]
    current_idx = stage_ids.index(stage_id) if stage_id in stage_ids else -1
    has_next_stage = current_idx >= 0 and current_idx < len(stage_ids) - 1
    
    logger.info(f"[Expert Mode Debug] stage_ids={stage_ids}, current_idx={current_idx}, has_next_stage={has_next_stage}")
    
    if not has_next_stage:
        # 最后一个阶段，不需要暂停
        logger.info(f"[Expert Mode Debug] Stage {stage_id} is the last stage, skipping pause")
        return False
    
    # 设置暂停信号
    logger.info(f"[Expert Mode] Stage {stage_id} completed, auto-pausing for user intervention")
    TaskController.request_pause(context.execution_id)
    
    # 更新执行状态为暂停（这样前端才能检测到暂停状态）
    context.status = ExecutionStatus.PAUSED
    context.message = f"专家模式：阶段 {stage_id} 完成，等待用户确认继续"
    
    # 更新阶段消息
    if stage_id in context.stages:
        stage = context.stages[stage_id]
        stage.message = f"阶段完成，等待用户确认继续..."
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [专家模式] 阶段完成，等待用户干预")
    
    return True




@dataclass
class StageSnapshot:
    """阶段版本快照 — 每次 retry 前保存，用于版本历史对比"""
    version: int                          # 版本号，从 1 开始
    params_used: dict[str, object]        # 本次执行实际使用的参数
    output_preview: dict[str, object] | None  # 本次执行的阶段输出
    ai_analysis: str | None               # 本次执行的 AI 分析文本（可选）
    suggested_params: dict[str, object] | None  # AI 建议的参数（如有）
    execution_time_ms: int | None         # 执行耗时（毫秒）
    completed_at: str | None              # ISO 时间字符串
    retry_reason: str | None = None       # 本次重试原因


@dataclass
class StageProgress:
    """阶段进度"""
    stage_id: str
    stage_name: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    progress: float = 0.0  # 0-100
    message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    # 新增字段
    logs: list[str] = field(default_factory=list)  # 阶段日志列表
    code: str = ""  # 阶段对应的Python伪代码
    output_preview: dict[str, object] | None = None  # 阶段输出预览
    params_used: dict[str, object] = field(default_factory=dict)  # 该阶段使用的配置参数
    # 参数元数据（用于前端可视化表单渲染）
    params_meta: list[dict[str, object]] = field(default_factory=list)
    # 版本历史快照（每次 retry 前追加）
    snapshots: list[StageSnapshot] = field(default_factory=list)
    
    @property
    def execution_time_ms(self) -> int | None:
        """计算阶段执行时间（毫秒）"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None


@dataclass
class ExecutionContext:
    """执行上下文"""
    execution_id: str
    task_id: str
    session_id: str
    params: dict[str, object]
    data: pd.DataFrame | None = None
    file_path: str | None = None
    
    # Status tracking
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_stage: str = ""
    overall_progress: float = 0.0
    message: str = ""
    
    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Stage progress
    stages: dict[str, StageProgress] = field(default_factory=dict)
    stage_order: list[str] = field(default_factory=list)  # 阶段执行顺序
    
    # Results
    outputs: dict[str, object] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    
    # Callbacks
    progress_callback: Callable[[str, float, str], None] | None = None
    
    # Task Manager Integration (new fields)
    record_id: str | None = None  # 关联的持久化记录ID
    interaction_mode: str = "auto"  # 交互模式: auto, expert
    
    # LLM Configuration (from frontend ModelSelector)
    model: str = "deepseek-chat"  # LLM模型名称
    api_base: str = "http://localhost:8200/v1"  # LLM API基础URL
    system_prompt: str | None = None  # 用户自定义系统提示词（与SOP Prompt合并）
    
    # Stage Retry Support (Phase 6)
    retry_from_stage: str | None = None  # 需要重试的阶段ID，设置后Pipeline将从该阶段重新开始
    executed_retry_stages: set[str] = field(default_factory=set)  # 已执行完的重试阶段ID集合，用于跳过重试阶段的专家模式暂停
    
    # Retry 版本号：每次 retry 递增，旧线程的 progress_callback 检测到版本不匹配时抛异常退出
    _execution_version: int = 0


# =============================================================================
# Execution Store
# =============================================================================

class ExecutionStore:
    """
    执行状态存储
    
    In-memory storage for execution contexts.
    Can be extended to use Redis/DB for persistence.
    """
    
    _executions: dict[str, ExecutionContext] = {}
    
    @classmethod
    def create(
        cls,
        task_id: str,
        session_id: str,
        params: dict[str, object],
        data: pd.DataFrame | None = None,
        file_path: str | None = None,
        execution_id: str | None = None,
        interaction_mode: str = "auto",
        model: str = "deepseek-chat",
        api_base: str = "http://localhost:8200/v1",
        system_prompt: str | None = None
    ) -> ExecutionContext:
        """创建执行上下文"""
        if execution_id is None:
            execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        
        # Get task definition for stages
        registry = get_registry()
        task_def = registry.get_task(task_id)
        
        stages: dict[str, StageProgress] = {}
        stage_order: list[str] = []
        if task_def:
            for stage in task_def.stages:
                stages[stage.id] = StageProgress(
                    stage_id=stage.id,
                    stage_name=stage.name
                )
                stage_order.append(stage.id)
        
        context = ExecutionContext(
            execution_id=execution_id,
            task_id=task_id,
            session_id=session_id,
            params=params,
            data=data,
            file_path=file_path,
            stages=stages,
            stage_order=stage_order,
            interaction_mode=interaction_mode,
            model=model,
            api_base=api_base,
            system_prompt=system_prompt
        )
        
        logger.info(f"[ExecutionStore.create] Created context with file_path={file_path}")
        
        cls._executions[execution_id] = context
        
        # Create persistent record if task manager is available
        if TASK_MANAGER_AVAILABLE:
            try:
                inputs_summary = None
                if data is not None:
                    inputs_summary = {
                        "rows": len(data),
                        "columns": len(data.columns),
                        "column_names": list(data.columns)[:20],  # Limit to first 20
                        "file_path": file_path  # 保存数据文件路径
                    }
                elif file_path is not None:
                    inputs_summary = {
                        "file_path": file_path  # 即使没有data也保存file_path
                    }
                
                record_id = TaskHistoryService.create_record(
                    task_type=task_id,
                    execution_id=execution_id,
                    session_id=session_id,
                    params=dict(params),
                    task_category="sop",
                    interaction_mode=interaction_mode,
                    inputs_summary=inputs_summary
                )
                context.record_id = record_id
                logger.info(f"Created persistent record: {record_id} for execution: {execution_id}")
                
                # Phase 6: 创建执行状态持久化记录
                if PersistentExecutionStore is not None:
                    PersistentExecutionStore.create(
                        execution_id=execution_id,
                        task_id=task_id,
                        session_id=session_id,
                        params=dict(params),
                        interaction_mode=interaction_mode,
                        record_id=record_id,
                        data_file_path=file_path,
                    )
                    logger.info(f"Created ExecutionState for: {execution_id}")
            except Exception as e:
                logger.warning(f"Failed to create persistent record: {e}")
        
        return context
    
    @classmethod
    def get(cls, execution_id: str) -> ExecutionContext | None:
        """获取执行上下文"""
        return cls._executions.get(execution_id)
    
    @classmethod
    def update(cls, context: ExecutionContext) -> None:
        """更新执行上下文"""
        cls._executions[context.execution_id] = context
        
        # Sync to persistent storage if available
        if TASK_MANAGER_AVAILABLE and context.record_id:
            try:
                # Map ExecutionStatus to TaskStatus
                status_map = {
                    ExecutionStatus.PENDING: TaskStatus.PENDING,
                    ExecutionStatus.RUNNING: TaskStatus.RUNNING,
                    ExecutionStatus.PAUSED: TaskStatus.PAUSED,
                    ExecutionStatus.COMPLETED: TaskStatus.COMPLETED,
                    ExecutionStatus.FAILED: TaskStatus.FAILED,
                    ExecutionStatus.CANCELLED: TaskStatus.CANCELLED,
                }
                task_status = status_map.get(context.status, TaskStatus.RUNNING)
                
                # Convert stages to dict format (包含output_preview以便前端显示阶段预览)
                # 注意：必须包含params_used和params_meta，否则历史任务恢复后无法显示"参数"tab
                # 注意：必须包含execution_time_ms，否则历史任务恢复后无法显示阶段耗时
                stages_dict = {
                    stage_id: {
                        "stage_id": stage.stage_id,
                        "stage_name": stage.stage_name,
                        "status": stage.status.value,
                        "progress": stage.progress,
                        "message": stage.message,
                        "logs": stage.logs[-20:] if stage.logs else [],
                        "code": stage.code,
                        "output_preview": _make_json_serializable(stage.output_preview) if stage.output_preview else None,
                        "params_used": _make_json_serializable(stage.params_used) if stage.params_used else {},
                        "params_meta": stage.params_meta if hasattr(stage, 'params_meta') else [],
                        "started_at": stage.started_at.isoformat() if stage.started_at else None,
                        "completed_at": stage.completed_at.isoformat() if stage.completed_at else None,
                        "execution_time_ms": stage.execution_time_ms,  # 阶段执行耗时（毫秒）
                        "snapshots": [
                            {
                                "version": s.version,
                                "params_used": _make_json_serializable(s.params_used),
                                "output_preview": _make_json_serializable(s.output_preview) if s.output_preview else None,
                                "ai_analysis": s.ai_analysis,
                                "suggested_params": _make_json_serializable(s.suggested_params) if s.suggested_params else None,
                                "execution_time_ms": s.execution_time_ms,
                                "completed_at": s.completed_at,
                                "retry_reason": s.retry_reason,
                            }
                            for s in (stage.snapshots if hasattr(stage, 'snapshots') else [])
                        ],
                    }
                    for stage_id, stage in context.stages.items()
                }
                
                TaskHistoryService.update_status(
                    record_id=context.record_id,
                    status=task_status,
                    progress=context.overall_progress,
                    current_stage=context.current_stage,
                    message=context.message,
                    stages=stages_dict
                )
                
                # Phase 6: 同步更新执行状态
                if PersistentExecutionStore is not None:
                    PersistentExecutionStore.update(
                        execution_id=context.execution_id,
                        status=task_status.value,
                        current_stage_id=context.current_stage,
                        pause_stage_id=context.current_stage if context.status == ExecutionStatus.PAUSED else None,
                    )
                    
                    # Phase 6: 当任务暂停时，保存完整的ExecutionContext到文件
                    # 这样在重启后可以通过load_full_state恢复
                    if context.status == ExecutionStatus.PAUSED:
                        try:
                            PersistentExecutionStore.save_full_state(
                                execution_id=context.execution_id,
                                context=context
                            )
                            logger.info(f"[ExecutionStore] Saved full context to persistent storage for resumable execution: {context.execution_id}")
                        except Exception as e:
                            logger.error(f"[ExecutionStore] Failed to save full context to persistent storage: {e}", exc_info=True)
            except Exception as e:
                logger.warning(f"Failed to sync to persistent storage: {e}")
    
    @classmethod
    def delete(cls, execution_id: str) -> bool:
        """删除执行上下文"""
        if execution_id in cls._executions:
            del cls._executions[execution_id]
            # Phase 6: 同步删除执行状态
            if TASK_MANAGER_AVAILABLE and PersistentExecutionStore is not None:
                try:
                    PersistentExecutionStore.delete(execution_id)
                except Exception as e:
                    logger.warning(f"Failed to delete ExecutionState: {e}")
            return True
        return False
    
    @classmethod
    def list_by_session(cls, session_id: str) -> list[ExecutionContext]:
        """列出会话的所有执行"""
        return [
            ctx for ctx in cls._executions.values()
            if ctx.session_id == session_id
        ]
    
    @classmethod
    def cleanup_old(cls, max_age_hours: int = 24) -> int:
        """清理过期执行记录"""
        now = datetime.now()
        to_delete: list[str] = []
        
        for exec_id, ctx in cls._executions.items():
            if ctx.completed_at:
                age = (now - ctx.completed_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_delete.append(exec_id)
        
        for exec_id in to_delete:
            del cls._executions[exec_id]
        
        return len(to_delete)


# =============================================================================
# SOP Executor
# =============================================================================

class SOPExecutor:
    """
    SOP任务执行器
    
    Provides unified interface for executing SOP tasks.
    Supports:
    - Pipeline mode: 预编译执行，高性能、低成本
    - LLM SOP mode: 解释执行，灵活、可解释
    - Task control (pause/stop/resume) and result persistence.
    """
    
    registry: SOPRegistry
    
    def __init__(self, registry: SOPRegistry | None = None):
        """
        初始化执行器
        
        Args:
            registry: SOP注册中心，默认使用全局实例
        """
        self.registry = registry or get_registry()
    
    def execute(
        self,
        task_id: str,
        session_id: str,
        params: dict[str, object],
        data: pd.DataFrame | None = None,
        file_path: str | None = None,
        progress_callback: Callable[[str, float, str], None] | None = None,
        interaction_mode: str = "auto"
    ) -> ExecutionContext:
        """
        同步执行任务
        
        Args:
            task_id: 任务ID
            session_id: 会话ID
            params: 任务参数
            data: 输入数据（可选）
            file_path: 数据文件路径（可选）
            progress_callback: 进度回调函数 (stage_id, progress, message)
            interaction_mode: 交互模式 (auto, expert)
            
        Returns:
            执行上下文
        """
        # Create execution context
        context = ExecutionStore.create(
            task_id=task_id,
            session_id=session_id,
            params=params,
            data=data,
            file_path=file_path,
            interaction_mode=interaction_mode
        )
        context.progress_callback = progress_callback
        
        try:
            self._run_task(context)
            # Save results on success
            self._save_results(context)
        except Exception as e:
            context.status = ExecutionStatus.FAILED
            context.message = str(e)
            full_traceback = traceback.format_exc()
            context.errors.append(full_traceback)
            logger.error(f"Task execution failed: {e}\n{full_traceback}")
            # 清除重试阶段标记
            context.executed_retry_stages.clear()
            # Update error in persistent storage
            self._save_error(context, str(e), full_traceback)
        finally:
            context.completed_at = datetime.now()
            ExecutionStore.update(context)
        
        return context
    
    async def execute_async(
        self,
        task_id: str,
        session_id: str,
        params: dict[str, object],
        data: pd.DataFrame | None = None,
        file_path: str | None = None,
        progress_callback: Callable[[str, float, str], None] | None = None,
        execution_id: str | None = None,
        interaction_mode: str = "auto",
        model: str = "deepseek-chat",
        api_base: str = "http://localhost:8200/v1",
        system_prompt: str | None = None
    ) -> ExecutionContext:
        """
        异步执行任务
        
        Args:
            task_id: 任务ID
            session_id: 会话ID
            params: 任务参数
            data: 输入数据（可选）
            file_path: 数据文件路径（可选）
            progress_callback: 进度回调函数
            execution_id: 执行ID（可选，用于复用已创建的context）
            interaction_mode: 交互模式 (auto, expert)
            model: LLM模型名称（来自前端ModelSelector）
            api_base: LLM API基础URL
            system_prompt: 用户自定义系统提示词
            
        Returns:
            执行上下文
        """
        # Use existing context or create new one
        context = None
        if execution_id:
            context = ExecutionStore.get(execution_id)
        
        if context is None:
            context = ExecutionStore.create(
                task_id=task_id,
                session_id=session_id,
                params=params,
                data=data,
                file_path=file_path,
                execution_id=execution_id,
                interaction_mode=interaction_mode,
                model=model,
                api_base=api_base,
                system_prompt=system_prompt
            )
        else:
            # Update context with additional data
            if data is not None:
                context.data = data
            # 如果context.data为None且有file_path，重新加载数据
            elif context.data is None and context.file_path:
                logger.info(f"[execute_async] Loading data from file_path: {context.file_path}")
                try:
                    import pandas as pd
                    context.data = pd.read_csv(context.file_path)
                    logger.info(f"[execute_async] Data loaded: {len(context.data)} rows, {len(context.data.columns)} columns")
                except Exception as e:
                    logger.error(f"[execute_async] Failed to load data: {e}")
                    context.data = None
            if file_path is not None:
                context.file_path = file_path
            # Update LLM config if provided
            context.model = model
            context.api_base = api_base
            context.system_prompt = system_prompt
            # 更新参数（用于阶段重试时应用新参数）
            # 注意：这里不覆盖整个params，因为params可能包含执行过程中产生的中间数据
            # 只更新传入的新参数
            if params:
                old_params = dict(context.params)
                context.params.update(params)
                # 记录参数变化
                changed_params = {k: v for k, v in params.items() if old_params.get(k) != v}
                if changed_params:
                    logger.info(f"[execute_async] Updated params: {list(changed_params.keys())}")
        
        context.progress_callback = progress_callback
        
        _was_cancelled = False  # 标记是否被 asyncio.CancelledError 取消（阶段重试场景）
        try:
            # 使用Pipeline模式执行
            await asyncio.to_thread(self._run_task, context)
            # Save results on success
            self._save_results(context)
        except asyncio.CancelledError:
            # 任务被取消（通常是阶段重试时 _cancel_existing_task 触发）
            # 不更新 ExecutionStore，因为 retry API 已经重置了所有阶段状态，
            # 旧任务的 context（包含已完成阶段的旧状态）不应覆盖重置后的状态
            _was_cancelled = True
            logger.info(f"Task cancelled (likely stage retry): {context.execution_id}, skipping ExecutionStore update")
            raise  # 重新抛出让 asyncio 正确处理
        except Exception as e:
            # Check if it's a stop exception (from pipeline or task_manager)
            error_type = type(e).__name__
            if error_type == 'TaskStoppedException' or 'stopped' in str(e).lower():
                # 检查是否是因为阶段重试而被中止（不是用户手动停止）
                if getattr(context, '_aborted_for_retry', False):
                    _was_cancelled = True
                    logger.info(f"Task stopped for retry (aborted_for_retry): {context.execution_id}, skipping status update")
                else:
                    context.status = ExecutionStatus.CANCELLED
                    context.message = "任务已被用户停止"
                    logger.info(f"Task stopped by user: {context.execution_id}")
                    # 清除重试阶段标记
                    context.executed_retry_stages.clear()
                    # Update status in persistent storage
                    if TASK_MANAGER_AVAILABLE and context.record_id:
                        TaskHistoryService.update_status(
                            record_id=context.record_id,
                            status=TaskStatus.STOPPED,
                            message="任务已被用户停止"
                        )
            else:
                context.status = ExecutionStatus.FAILED
                context.message = str(e)
                full_traceback = traceback.format_exc()
                context.errors.append(full_traceback)
                logger.error(f"Task execution failed: {e}\n{full_traceback}")
                # 清除重试阶段标记
                context.executed_retry_stages.clear()
                # Update error in persistent storage
                self._save_error(context, str(e), full_traceback)
        finally:
            if _was_cancelled:
                # 被取消的任务不更新 ExecutionStore，避免覆盖 retry API 已重置的状态
                logger.info(f"Skipping ExecutionStore update for cancelled task: {context.execution_id}")
            else:
                context.completed_at = datetime.now()
                ExecutionStore.update(context)
                
                # 安全网：确保数据库 status 与内存 context 一致
                # 场景：_save_results 抛异常（如序列化失败），数据库 status 仍为 'running'，
                # 但内存 context.status 已是 COMPLETED（由 _run_task 设置），导致历史列表显示"执行中"
                if TASK_MANAGER_AVAILABLE and context.record_id and context.status == ExecutionStatus.COMPLETED:
                    try:
                        record = TaskHistoryService.get_record(context.record_id)
                        if record and record.get('status') != 'completed':
                            logger.warning(f"[SOP] DB status mismatch detected: context=COMPLETED, db={record.get('status')}. Fixing...")
                            TaskHistoryService.update_status(
                                record_id=context.record_id,
                                status=TaskStatus.COMPLETED,
                                progress=100.0,
                                message="任务执行完成"
                            )
                    except Exception as fix_err:
                        logger.error(f"[SOP] Failed to fix DB status mismatch: {fix_err}")
        
        return context
    
    def _run_task(self, context: ExecutionContext) -> None:
        """
        执行任务核心逻辑
        
        Args:
            context: 执行上下文
        """
        # 保存原始状态用于恢复判断
        original_status = context.status
        is_resuming_from_pause = (original_status == ExecutionStatus.PAUSED)
        
        # 设置启动时间（仅在首次执行时设置，恢复执行时保留原有时间）
        if context.started_at is None:
            context.started_at = datetime.now()
        
        logger.info(f"[SOP] Starting task execution: {context.task_id}, execution_id: {context.execution_id}")
        logger.info(f"[SOP] Original status: {original_status}, is_resuming_from_pause: {is_resuming_from_pause}")
        
        # Get task definition
        task_def = self.registry.get_task(context.task_id)
        if not task_def:
            raise ValueError(f"Unknown task: {context.task_id}")
        
        logger.info(f"[SOP] Task definition found: {task_def.task_name}")
        
        # Get executor class
        executor_class = self.registry.get_executor(context.task_id)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        if not executor_class:
            raise ValueError(f"No executor found for task: {context.task_id}")
        
        logger.info(f"[SOP] Executor class: {executor_class.__name__}")
        
        # Load data if file path provided
        if context.file_path and context.data is None:
            logger.info(f"[SOP] Loading data from: {context.file_path}")
            context.data = self._load_data(context.file_path)
            logger.info(f"[SOP] Data loaded: {context.data.shape[0]} rows, {context.data.shape[1]} columns")
            
            # Update inputs summary in persistent storage
            if TASK_MANAGER_AVAILABLE and context.record_id:
                try:
                    # TaskHistoryService already imported at module level
                    TaskHistoryService.update_status(
                        record_id=context.record_id,
                        status=TaskStatus.RUNNING,
                        message=f"数据加载完成: {context.data.shape[0]} 行, {context.data.shape[1]} 列"
                    )
                except Exception as e:
                    logger.warning(f"Failed to update inputs summary: {e}")
        
        if context.data is None:
            raise ValueError("No data provided for execution")
        
        # Check for stop request before starting
        if not self._check_control(context):
            return
        
        # 记录当前执行版本号，用于检测旧线程
        my_version = context._execution_version
        
        # Create progress callback wrapper (supports code parameter for pseudocode)
        def pipeline_progress_callback(
            stage_id: str, 
            progress: float, 
            message: str = "", 
            code: str | None = None,
            output_preview: dict[str, object] | None = None
        ) -> None:
            # 版本号检查：如果 context 的版本已递增（retry 启动了新线程），旧线程立即退出
            if context._execution_version != my_version:
                logger.warning(f"[SOP] Stale thread detected (my_version={my_version}, current={context._execution_version}), aborting")
                raise TaskStoppedException(f"Stale execution thread (version mismatch: {my_version} != {context._execution_version})")
            
            logger.info(f"[SOP] Progress: {stage_id} - {progress:.1f}% - {message}")
            
            # 检查是否需要跳过专家模式暂停（阶段重试时，之前的阶段不暂停）
            # 从 output_preview 中读取 _skip_expert_pause 标记
            should_skip_pause = False
            if output_preview and output_preview.get('_skip_expert_pause'):
                should_skip_pause = True
                logger.info(f"[SOP] Detected _skip_expert_pause flag in output_preview")
            
            # 注意：不要在这里移除 _skip_expert_pause 标记！
            # 需要保留它传递给 _update_progress，这样 check_expert_mode_pause 才能正确检测
            # _skip_expert_pause 会在 _update_progress 中被处理和移除
            
            logger.debug(f"[SOP] Pause check for stage {stage_id}: interaction_mode={context.interaction_mode}, progress={progress}, should_skip_pause={should_skip_pause}")
            
            self._update_progress(context, stage_id, progress, message, code=code or "", output_preview=output_preview)
            
            # 专家模式：阶段完成后检查暂停信号并阻塞等待
            # check_expert_mode_pause 在 _update_progress 中被调用，会设置暂停信号
            # 这里需要检查并等待用户确认继续
            if progress >= 100 and context.interaction_mode == "expert" and not should_skip_pause:
                logger.info(f"[Expert Mode Debug] Stage {stage_id} completed (progress={progress}), checking control...")
                logger.info(f"[Expert Mode Debug] Pause condition: expert={context.interaction_mode=='expert'}, should_skip={should_skip_pause}, progress={progress}")
                # 检查是否有暂停信号，如果有则阻塞等待
                result = self._check_control(context)
                logger.info(f"[Expert Mode Debug] _check_control returned: {result}")
                
                # 检测到阶段重试请求
                if result == "retry":
                    retry_stage = context.retry_from_stage
                    logger.info(f"[Expert Mode] Stage retry requested: {retry_stage}")
                    # 清除重试标记（会在重新执行时重新设置）
                    context.retry_from_stage = None
                    raise StageRetryException(retry_stage or stage_id)
            elif should_skip_pause:
                logger.info(f"[Expert Mode Debug] Stage {stage_id} completed, skipping pause (before retry stage)")
            else:
                logger.debug(f"[SOP] Stage {stage_id} progress={progress}, no pause needed (mode={context.interaction_mode}, should_skip={should_skip_pause})")
        
        # Create stop check callback for pipeline
        def check_stop_callback() -> bool:
            """检查是否应该停止执行
            
            Returns:
                True: 应该停止
                False: 继续执行
            """
            # 版本号检查
            if context._execution_version != my_version:
                logger.warning(f"[SOP] Stale thread in stop_check (my_version={my_version}, current={context._execution_version})")
                return True  # 告诉 Pipeline 停止
            result = self._check_control(context)
            # retry 也应该停止当前执行
            return result == False or result == "retry"
        
        # Initialize and run pipeline
        pipeline_params = self._prepare_pipeline_params(context.params, task_def)
        pipeline_params['progress_callback'] = pipeline_progress_callback
        pipeline_params['stop_check_callback'] = check_stop_callback
        
        # 详细日志：显示关键参数的实际值
        filter_params = {k: v for k, v in pipeline_params.items() if 'lift' in k or 'hit_rate' in k}
        binning_params = {k: v for k, v in pipeline_params.items() if k in ['n_bins', 'bin_method', 'mining_mode', 'rule_directions']}
        logger.info(f"[SOP] Pipeline params: {list(pipeline_params.keys())}")
        logger.info(f"[SOP] Filter params (from user): {filter_params}")
        logger.info(f"[SOP] Binning params (from user): {binning_params}")
        
        # Create pipeline instance
        pipeline = executor_class(**pipeline_params)  # pyright: ignore[reportAny]
        
        # Extract execution params with parameter name compatibility
        # Support both 'target' and 'target_col' for backward compatibility
        target_col = context.params.get('target_col') or context.params.get('target')
        
        # 获取用户指定的排除列（新参数名）或特征列（旧参数名）
        exclude_cols = context.params.get('exclude_cols')
        feature_cols = context.params.get('feature_cols')  # 兼容旧参数名
        
        # 修复：空字符串或空列表应视为None
        if not feature_cols:  # 空字符串、空列表、None都会变成None
            feature_cols = None
        if not exclude_cols:
            exclude_cols = None
        
        # 处理 exclude_cols 的格式：支持字符串（逗号分隔）或列表
        if exclude_cols:
            if isinstance(exclude_cols, str):
                # 逗号分隔的字符串，解析为列表
                exclude_cols = [col.strip() for col in exclude_cols.split(',') if col.strip()]
            elif isinstance(exclude_cols, list):
                # 已经是列表，过滤空值
                exclude_cols = [col for col in exclude_cols if col]
            
            if not exclude_cols:
                exclude_cols = None
        
        # 如果使用旧的 feature_cols 参数，转换为 exclude_cols 逻辑
        # 注意：评分卡的 run 方法现在会自动检测非建模列，所以这里只传递用户指定的排除列
        if exclude_cols:
            logger.info(f"[SOP] 用户指定排除列: {exclude_cols}")
        
        # 根据任务类型构建不同的执行参数
        task_type = task_def.task_id
        
        if task_type == "rule_mining":
            # 规则挖掘任务的参数（与评分卡一致，包含exclude_cols）
            exec_params: dict[str, object] = {
                'df': context.data,
                'target_col': target_col,
                'weight_col': context.params.get('weight_col'),
                'feature_cols': feature_cols,
                'exclude_cols': exclude_cols,  # 用户指定的排除列（与评分卡一致）
                'score_vars': context.params.get('score_vars'),
                'var_name_dict': context.params.get('var_name_dict'),
                'skip_preprocessing': context.params.get('skip_preprocessing', False),
                'custom_thresholds': context.params.get('custom_thresholds'),
                'prior_rules': context.params.get('prior_rules'),
                'amount_col': context.params.get('amount_col'),
                # P1-5: 数据集划分参数（与评分卡一致，支持 OOT）
                'sample_type_col': context.params.get('sample_type_col'),
                'time_col': context.params.get('time_col'),
                'oot_ratio': context.params.get('oot_ratio', 0.0),
                'test_ratio': context.params.get('test_ratio', 0.0),
                # P1-5: OOT 验证参数
                'enable_oot_validation': context.params.get('enable_oot_validation', False),
                'enable_stability_filter': context.params.get('enable_stability_filter', False),
                'cv_threshold': context.params.get('cv_threshold', 0.35),
            }
        else:
            # 评分卡等其他任务的参数
            exec_params = {
                'df': context.data,
                'target_col': target_col,
                'weight_col': context.params.get('weight_col'),
                'feature_cols': feature_cols,
                'exclude_cols': exclude_cols,
                # OOT划分参数（手动划分或智能划分）
                'sample_type_col': pipeline_params.get('sample_type_col'),
                'time_col': pipeline_params.get('time_col'),
                'oot_ratio': pipeline_params.get('oot_ratio', 0.0)
            }
        
        logger.info(f"[SOP] Execution params: target_col={exec_params['target_col']}")
        
        # Run pipeline with retry support
        # 支持阶段重试：当用户请求重试某个阶段时，Pipeline 会从该阶段重新开始
        max_retries = 10  # 防止无限循环
        retry_count = 0
        start_from_stage: str | None = None
        cached_state: dict[str, object] | None = None  # Phase 6: 缓存的中间状态
        
        # 如果任务是从暂停状态恢复，从暂停的阶段继续执行
        # 注意：如果有 retry_from_stage，说明是阶段重试（不是普通 resume），
        # 应跳过暂停恢复路径，由 while 循环中的 retry_from_stage 处理
        has_retry_request = hasattr(context, 'retry_from_stage') and context.retry_from_stage
        logger.info(f"[SOP] Checking if task is resuming from pause: status={context.status}, current_stage={context.current_stage}, retry_from_stage={getattr(context, 'retry_from_stage', None)}")
        if context.status == ExecutionStatus.PAUSED and context.current_stage and not has_retry_request:
            logger.info(f"[SOP] Task is paused with current_stage: {context.current_stage}")
            paused_stage_id = context.current_stage
            # 检查暂停的阶段状态，如果已完成则从下一个阶段开始
            logger.info(f"[SOP] Checking if paused_stage_id '{paused_stage_id}' exists in context.stages")
            if paused_stage_id in context.stages:
                paused_stage = context.stages[paused_stage_id]
                logger.info(f"[SOP] Paused stage found: status={paused_stage.status}")
                if paused_stage.status == ExecutionStatus.COMPLETED:
                    # 暂停的阶段已完成，从下一个阶段开始
                    # 获取任务定义的阶段顺序
                    task_def = get_registry().get_task(context.task_id)
                    if task_def:
                        stage_ids = [s.id for s in task_def.stages]
                        try:
                            paused_idx = stage_ids.index(paused_stage_id)
                            if paused_idx + 1 < len(stage_ids):
                                start_from_stage = stage_ids[paused_idx + 1]
                                logger.info(f"[SOP] Paused stage {paused_stage_id} completed, resuming from next stage: {start_from_stage}")
                            else:
                                logger.info(f"[SOP] Paused stage {paused_stage_id} is the last stage, completing task")
                                context.status = ExecutionStatus.COMPLETED
                                context.message = "任务已完成"
                                context.overall_progress = 100.0
                                ExecutionStore.update(context)
                                if context.record_id:
                                    TaskHistoryService.update_status(
                                        record_id=context.record_id,
                                        status=TaskStatus.COMPLETED,
                                        message="任务已完成"
                                    )
                                return
                        except ValueError:
                            logger.warning(f"[SOP] Paused stage {paused_stage_id} not found in stage list")
                            start_from_stage = paused_stage_id
                else:
                    # 暂停的阶段未完成，从该阶段继续
                    start_from_stage = paused_stage_id
                    logger.info(f"[SOP] Resuming from paused stage: {start_from_stage}")
            else:
                start_from_stage = paused_stage_id
                logger.warning(f"[SOP] Paused stage {paused_stage_id} not found in context.stages")
            
            # 更新状态为RUNNING，避免再次触发暂停逻辑
            context.status = ExecutionStatus.RUNNING
            context.message = "任务已恢复执行"
            ExecutionStore.update(context)
            logger.info(f"[SOP] Updated context status to RUNNING for resumable execution: {context.execution_id}")
            
            # 注意：Resume场景不应该将start_from_stage添加到executed_retry_stages
            # executed_retry_stages只用于阶段重试（retry from stage）场景
            # Resume时，被跳过的阶段通过_skip_expert_pause标记来跳过暂停
            # start_from_stage是要正常执行的阶段，完成后应该正常暂停
            
            # 加载缓存的中间状态（用于跳过已完成的阶段）
            if TASK_MANAGER_AVAILABLE and PersistentExecutionStore is not None:
                try:
                    cached_state = PersistentExecutionStore.get_cached_state_for_retry(
                        context.execution_id, start_from_stage
                    )
                    if cached_state:
                        logger.info(f"[SOP] Loaded cached state for resume: {list(cached_state.keys())}")
                        stage_outputs = cached_state.get("stage_outputs")
                        if stage_outputs and isinstance(stage_outputs, dict):
                            logger.info(f"[SOP] Cached stage_outputs keys: {list(stage_outputs.keys())}")
                        if "last_completed_stage" in cached_state:
                            logger.info(f"[SOP] Last completed stage: {cached_state['last_completed_stage']}")
                except Exception as e:
                    logger.warning(f"[SOP] Failed to load cached state: {e}")
        else:
            # 非恢复任务，设置状态为RUNNING
            if context.status != ExecutionStatus.RUNNING:
                context.status = ExecutionStatus.RUNNING
                context.message = "任务正在执行"
                ExecutionStore.update(context)
                logger.info(f"[SOP] Set context status to RUNNING: {context.execution_id}")
        
        while retry_count < max_retries:
            try:
                # 检查是否有重试阶段请求（通过API设置retry_from_stage）
                # 注意：retry_from_stage 优先于暂停恢复的 start_from_stage
                # 因为用户可能在暂停状态下请求从更早的阶段重试
                if hasattr(context, 'retry_from_stage') and context.retry_from_stage:
                    if start_from_stage and start_from_stage != context.retry_from_stage:
                        logger.info(f"[SOP] Overriding start_from_stage: {start_from_stage} -> {context.retry_from_stage} (retry_from_stage takes priority)")
                    start_from_stage = context.retry_from_stage
                    # 清除重试标记（避免重复处理）
                    context.retry_from_stage = None
                    logger.info(f"[SOP] Using retry_from_stage: {start_from_stage}")
                    
                    # 判断retry阶段是否是第一个阶段
                    is_first_stage = False
                    _task_def = get_registry().get_task(context.task_id)
                    if _task_def:
                        _stage_ids = [s.id for s in _task_def.stages]
                        is_first_stage = (_stage_ids and start_from_stage == _stage_ids[0])
                    
                    if is_first_stage:
                        # 从第一个阶段重试 = 完全重跑，不需要任何缓存
                        cached_state = None
                        start_from_stage = None  # Pipeline 从头执行
                        logger.info(f"[SOP] Retry from first stage, clearing cached_state and start_from_stage (full re-execution)")
                    else:
                        # 从非首阶段重试，重新加载正确的 cached_state
                        if TASK_MANAGER_AVAILABLE and PersistentExecutionStore is not None:
                            try:
                                cached_state = PersistentExecutionStore.get_cached_state_for_retry(
                                    context.execution_id, start_from_stage
                                )
                                if cached_state:
                                    logger.info(f"[SOP] Reloaded cached state for retry_from_stage={start_from_stage}: {list(cached_state.keys())}")
                                else:
                                    logger.info(f"[SOP] No cached state for retry_from_stage={start_from_stage}, will re-execute all stages")
                            except Exception as e:
                                logger.warning(f"[SOP] Failed to reload cached state for retry: {e}")
                                cached_state = None
                        else:
                            cached_state = None
                
                logger.info(f"[SOP] Running pipeline... (retry_count={retry_count}, start_from_stage={start_from_stage})")
                
                # 添加 start_from_stage 和 cached_state 参数（如果有）
                run_params = {k: v for k, v in exec_params.items() if v is not None}
                if start_from_stage:
                    run_params['start_from_stage'] = start_from_stage
                    # Phase 6: 加载缓存的中间状态
                    if cached_state:
                        run_params['cached_state'] = cached_state
                        logger.info(f"[SOP] Using cached state for retry, keys: {list(cached_state.keys())}")
                
                result: dict[str, object] = pipeline.run(**run_params)  # pyright: ignore[reportAny]
                
                logger.info(f"[SOP] Pipeline completed. Result keys: {list(result.keys()) if result else 'None'}")
                break  # 成功完成，退出循环
                
            except StageRetryException as e:
                retry_count += 1
                start_from_stage = e.stage_id
                logger.info(f"[SOP] Stage retry requested: {e.stage_id}, retry_count={retry_count}")
                
                # 注意：不要将start_from_stage添加到executed_retry_stages
                # start_from_stage是要正常执行的阶段，完成后应该正常暂停
                # 之前的阶段通过_skip_expert_pause标记来跳过暂停
                
                # Phase 6: 加载缓存的中间状态（从检查点恢复）
                if TASK_MANAGER_AVAILABLE and PersistentExecutionStore is not None:
                    try:
                        cached_state = PersistentExecutionStore.get_cached_state_for_retry(
                            context.execution_id, start_from_stage
                        )
                        if cached_state:
                            logger.info(f"[SOP] Loaded cached state for retry: {list(cached_state.keys())}")
                        else:
                            logger.warning(f"[SOP] No cached state found for retry, will re-execute all stages")
                    except Exception as cache_err:
                        logger.warning(f"[SOP] Failed to load cached state: {cache_err}")
                        cached_state = None
                
                # 重置该阶段及后续阶段的状态
                if task_def:  # task_def 已在上方验证非 None
                    self._reset_stages_from(context, task_def, start_from_stage)
                
                # 重新创建 Pipeline 实例（使用更新后的参数）
                if not task_def:
                    raise ValueError(f"Task definition not found: {context.task_id}")
                pipeline_params = self._prepare_pipeline_params(context.params, task_def)
                pipeline_params['progress_callback'] = pipeline_progress_callback
                pipeline_params['stop_check_callback'] = check_stop_callback
                pipeline = executor_class(**pipeline_params)  # pyright: ignore[reportAny]
                
                continue
        else:
            raise RuntimeError(f"Pipeline retry limit exceeded ({max_retries})")
        
        # Store results
        context.outputs = result
        context.status = ExecutionStatus.COMPLETED
        context.overall_progress = 100.0
        context.message = "任务执行完成"
        
        # 清除重试阶段标记
        context.executed_retry_stages.clear()
        
        logger.info(f"[SOP] Task execution completed: {context.execution_id}")
    
    def _check_control(self, context: ExecutionContext) -> bool | str:
        """检查任务控制状态
        
        支持暂停、停止和阶段重试三种控制：
        - 停止：立即返回 False，任务终止
        - 暂停：阻塞等待恢复信号，期间可被停止
        - 阶段重试：恢复时检测到 retry_from_stage，返回 "retry"
        
        Args:
            context: 执行上下文
            
        Returns:
            True: 继续执行
            False: 任务已停止
            "retry": 需要从 context.retry_from_stage 指定的阶段重试
        """
        import time
        
        if not TASK_MANAGER_AVAILABLE:
            return True
        
        try:
            while True:
                control = TaskController.check_control(context.execution_id)
                
                if control == TaskControlAction.STOP:
                    logger.info(f"Task {context.execution_id} stop requested")
                    context.status = ExecutionStatus.CANCELLED
                    context.message = "任务已被用户停止"
                    
                    if context.record_id:
                        TaskHistoryService.update_status(
                            record_id=context.record_id,
                            status=TaskStatus.STOPPED,
                            message="任务已被用户停止"
                        )
                    
                    TaskController.clear_control(context.execution_id)
                    return False
                
                elif control == TaskControlAction.PAUSE:
                    logger.info(f"Task {context.execution_id} paused")
                    context.status = ExecutionStatus.PAUSED
                    context.message = "任务已暂停，等待恢复..."
                    
                    # 更新ExecutionStore以便前端轮询获取状态
                    ExecutionStore.update(context)
                    
                    if context.record_id:
                        TaskHistoryService.update_status(
                            record_id=context.record_id,
                            status=TaskStatus.PAUSED,
                            message="任务已暂停"
                        )
                    
                    # 标记暂停请求已处理，等待恢复或停止
                    TaskController.mark_processed(context.execution_id)
                    
                    # 阻塞等待恢复或停止信号
                    while True:
                        time.sleep(0.1)  # 每0.1秒检查一次，提高响应速度
                        new_control = TaskController.check_control(context.execution_id)
                        
                        if new_control == TaskControlAction.STOP:
                            logger.info(f"Task {context.execution_id} stopped while paused")
                            context.status = ExecutionStatus.CANCELLED
                            context.message = "任务已被用户停止"
                            
                            if context.record_id:
                                TaskHistoryService.update_status(
                                    record_id=context.record_id,
                                    status=TaskStatus.STOPPED,
                                    message="任务已被用户停止"
                                )
                            
                            TaskController.clear_control(context.execution_id)
                            # 直接抛异常退出整个调用栈，而非返回 False
                            # 返回 False 只能通知 progress_callback 的调用者，
                            # 但 Pipeline 不一定在每个阶段开始前都检查 _should_stop()，
                            # 导致旧线程可能继续执行后续阶段（如 report_generation）
                            raise TaskStoppedException("任务已被用户停止")
                        
                        elif new_control == TaskControlAction.RESUME:
                            logger.info(f"Task {context.execution_id} resumed")
                            context.status = ExecutionStatus.RUNNING
                            context.message = "任务已恢复执行"
                            
                            # 更新ExecutionStore以便前端轮询获取状态
                            ExecutionStore.update(context)
                            
                            if context.record_id:
                                TaskHistoryService.update_status(
                                    record_id=context.record_id,
                                    status=TaskStatus.RUNNING,
                                    message="任务已恢复执行"
                                )
                            
                            TaskController.mark_processed(context.execution_id)
                            
                            # 检查是否有阶段重试请求
                            if context.retry_from_stage:
                                logger.info(f"Task {context.execution_id} has retry_from_stage: {context.retry_from_stage}")
                                # 返回特殊值表示需要重试
                                # 返回 "retry" 字符串而不是 True/False
                                return "retry"
                            
                            break  # 跳出内层循环，继续执行
                    
                    # 恢复后继续外层循环检查
                    continue
                
                else:
                    # 无控制请求，继续执行
                    return True
                    
        except TaskStoppedException:
            # TaskStoppedException 必须穿透，不能被吞掉
            raise
        except Exception as e:
            logger.warning(f"Failed to check control: {e}")
        
        return True
    
    def _reset_stages_from(
        self, 
        context: ExecutionContext, 
        task_def: "SOPTaskDefinition", 
        from_stage_id: str
    ) -> None:
        """重置指定阶段及其后续阶段的状态
        
        用于阶段重试时，将目标阶段及所有后续阶段重置为 PENDING 状态。
        
        2026-02-10: 修复逻辑 - 只对已执行过的阶段显示"阶段已重置"
        - 从未执行过的阶段（status=PENDING）不应显示重置信息
        
        Args:
            context: 执行上下文
            task_def: 任务定义
            from_stage_id: 起始阶段ID
        """
        stage_ids = [s.id for s in task_def.stages]
        
        if from_stage_id not in stage_ids:
            logger.warning(f"Stage {from_stage_id} not found in task definition")
            return
        
        start_idx = stage_ids.index(from_stage_id)
        stages_to_reset = stage_ids[start_idx:]
        
        logger.info(f"[SOP] Resetting stages from {from_stage_id}: {stages_to_reset}")
        
        for stage_id in stages_to_reset:
            if stage_id in context.stages:
                stage = context.stages[stage_id]
                
                # 判断阶段是否曾经执行过（非PENDING状态或有output_preview）
                was_executed = (
                    stage.status != ExecutionStatus.PENDING or
                    stage.output_preview is not None or
                    stage.started_at is not None
                )
                
                # 重置阶段状态
                stage.status = ExecutionStatus.PENDING
                stage.progress = 0.0
                stage.started_at = None
                stage.completed_at = None
                stage.output_preview = None
                # 清空历史快照：上游阶段重试后，下游阶段的历史快照已无效
                # （快照记录的是该阶段自身的重试历史，上游重置后这些历史与新执行无关）
                if hasattr(stage, 'snapshots'):
                    stage.snapshots = []
                
                # 只有曾经执行过的阶段才记录"已重置"日志
                if was_executed:
                    stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段已重置（准备重试）")
                    logger.info(f"[SOP] Reset stage {stage_id} (was executed)")
                else:
                    logger.info(f"[SOP] Stage {stage_id} was never executed, no reset log added")
        
        # 更新 ExecutionStore
        ExecutionStore.update(context)
        
        # 如果有持久化存储，也更新检查点
        if TASK_MANAGER_AVAILABLE and PersistentExecutionStore:
            try:
                PersistentExecutionStore.invalidate_checkpoints_from(
                    context.execution_id, 
                    from_stage_id
                )
            except Exception as e:
                logger.warning(f"Failed to invalidate checkpoints: {e}")
    
    def _save_results(self, context: ExecutionContext) -> None:
        """保存执行结果到持久化存储
        
        Args:
            context: 执行上下文
        """
        if not TASK_MANAGER_AVAILABLE or not context.record_id:
            return
        
        try:
            # Create outputs summary
            outputs_summary = {}
            for key, value in context.outputs.items():
                if isinstance(value, pd.DataFrame):
                    outputs_summary[key] = {
                        "type": "dataframe",
                        "shape": list(value.shape)
                    }
                elif isinstance(value, dict):
                    outputs_summary[key] = {
                        "type": "dict",
                        "keys": list(value.keys())[:10]
                    }
                elif isinstance(value, list):
                    outputs_summary[key] = {
                        "type": "list",
                        "length": len(value)
                    }
                else:
                    outputs_summary[key] = {
                        "type": type(value).__name__
                    }
            
            # Save full results to file storage
            storage = get_result_storage()
            result_path = storage.save_result(
                record_id=context.record_id,
                result=dict(context.outputs),
                metadata={
                    "task_type": context.task_id,
                    "execution_id": context.execution_id,
                    "session_id": context.session_id
                }
            )
            
            # Update record with summary and file path
            TaskHistoryService.update_result(
                record_id=context.record_id,
                outputs_summary=outputs_summary,
                result_file_path=result_path
            )
            
            # 保存阶段信息（包含output_preview）到数据库
            stages_data = {}
            for stage_id, stage in context.stages.items():
                stages_data[stage_id] = {
                    "stage_id": stage.stage_id,
                    "stage_name": stage.stage_name,
                    "status": stage.status.value,
                    "progress": stage.progress,
                    "message": stage.message,
                    "logs": stage.logs[-20:] if stage.logs else [],  # 只保留最后20条日志
                    "code": stage.code,
                    "output_preview": _make_json_serializable(stage.output_preview) if stage.output_preview else None,
                    "started_at": stage.started_at.isoformat() if stage.started_at else None,
                    "completed_at": stage.completed_at.isoformat() if stage.completed_at else None
                }
            
            # 更新stages到数据库
            TaskHistoryService.update_status(
                record_id=context.record_id,
                status=TaskStatus.COMPLETED,
                progress=100.0,
                current_stage=context.current_stage,
                message="任务执行完成",
                stages=stages_data
            )
            
            # 清理暂停时保存的 context.pkl 文件，避免重启后加载过期状态
            try:
                PersistentExecutionStore.update(
                    execution_id=context.execution_id,
                    status=TaskStatus.COMPLETED.value
                )
                # 删除 context.pkl 文件
                import os
                state_dir = PersistentExecutionStore.get_state_dir()
                state_file = os.path.join(state_dir, context.execution_id, "context.pkl")
                if os.path.exists(state_file):
                    os.remove(state_file)
                    logger.info(f"Cleaned up context.pkl for completed task: {context.execution_id}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup context.pkl: {cleanup_err}")
            
            logger.info(f"Saved results for {context.record_id} to {result_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save results: {e}")
    
    def _save_error(self, context: ExecutionContext, error_message: str, error_traceback: str) -> None:
        """保存错误信息到持久化存储
        
        Args:
            context: 执行上下文
            error_message: 错误消息
            error_traceback: 错误堆栈
        """
        if not TASK_MANAGER_AVAILABLE or not context.record_id:
            return
        
        try:
            TaskHistoryService.update_error(
                record_id=context.record_id,
                error_message=error_message,
                error_traceback=error_traceback
            )
        except Exception as e:
            logger.warning(f"Failed to save error: {e}")
    
    def _load_data(self, file_path: str) -> pd.DataFrame:
        """加载数据文件"""
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)  # pyright: ignore[reportUnknownMemberType]
        if file_path.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file_path)  # pyright: ignore[reportUnknownMemberType]
        raise ValueError(f"Unsupported file type: {file_path}")
    
    def _prepare_pipeline_params(
        self,
        params: dict[str, object],
        task_def: SOPTaskDefinition
    ) -> dict[str, object]:
        """
        准备Pipeline参数
        
        从用户参数中提取Pipeline构造函数需要的参数
        """
        pipeline_params: dict[str, object] = {}
        
        # 规则挖掘任务的参数映射
        if task_def.task_id == "rule_mining":
            param_mapping = {
                'mining_mode': 'mining_mode',
                'enable_feature_engineering': 'enable_feature_engineering',
                'missing_threshold': 'missing_threshold',
                'iv_threshold': 'iv_threshold',
                'n_bins': 'n_bins',
                'bin_method': 'bin_method',
                'rule_directions': 'rule_directions',
                'use_full_tree': 'use_full_tree',  # 全特征决策树（用于可视化）
                'n_vars': 'n_vars',
                'max_depth': 'max_depth',
                'min_samples_leaf': 'min_samples_leaf',
                'min_lift_filter': 'min_lift_filter',
                'max_hit_rate_filter': 'max_hit_rate_filter',
                'max_hit_rate_select': 'max_hit_rate_select',
                'allow_overlap': 'allow_overlap',
                # 规则集级别风险目标参数
                'min_recall_ruleset': 'min_recall_ruleset',
                'min_bad_rate_ruleset': 'min_bad_rate_ruleset',
                'target_bad_rate_ruleset': 'target_bad_rate_ruleset',
                'min_lift_ruleset': 'min_lift_ruleset',
                # P2-6: 类别不平衡处理
                'imbalance_strategy': 'imbalance_strategy',
                # 注意：test_ratio, sample_type_col, time_col 等不在这里，它们只传给 run() 方法，不传给 __init__
            }
            
            for user_key, pipeline_key in param_mapping.items():
                if user_key in params:
                    pipeline_params[pipeline_key] = params[user_key]
            
            # Parse special_values from comma-separated string to list
            if 'special_values' in params:
                special_values_str = params['special_values']
                if isinstance(special_values_str, str) and special_values_str.strip():
                    try:
                        pipeline_params['special_values'] = [float(v.strip()) for v in special_values_str.split(',') if v.strip()]
                    except ValueError:
                        logger.warning(f"Invalid special_values format: {special_values_str}, using defaults")
                elif isinstance(special_values_str, list):
                    pipeline_params['special_values'] = special_values_str
            
            # Parse force_categorical (supports both list from column_multi_select and legacy string format)
            if 'force_categorical' in params:
                force_cat_val = params['force_categorical']
                if isinstance(force_cat_val, list):
                    pipeline_params['force_categorical'] = force_cat_val
                elif isinstance(force_cat_val, str) and force_cat_val.strip():
                    # Legacy: comma-separated string format
                    pipeline_params['force_categorical'] = [v.strip() for v in force_cat_val.split(',') if v.strip()]
        
        # 评分卡开发任务的参数映射
        elif task_def.task_id == "scorecard_dev":
            param_mapping = {
                # 数据预处理参数
                'missing_threshold': 'missing_threshold',
                'test_ratio': 'test_ratio',
                'random_state': 'random_state',
                # 手动样本划分参数
                'sample_type_col': 'sample_type_col',
                # 智能OOT划分参数
                'time_col': 'time_col',
                'oot_ratio': 'oot_ratio',
                # WOE分箱参数
                'binning_method': 'bin_method',  # 元数据用binning_method，Pipeline用bin_method
                'bin_num_limit': 'max_bins',     # 元数据用bin_num_limit，Pipeline用max_bins
                'use_high_precision': 'use_high_precision',  # 高精度模式
                # 特征选择参数
                'iv_lower': 'iv_lower',
                'iv_upper': 'iv_upper',
                'vif_threshold': 'vif_threshold',
                'corr_threshold': 'corr_threshold',
                # 模型训练参数
                'use_stepwise': 'use_stepwise',
                'stepwise_direction': 'stepwise_direction',  # 逐步回归方向
                'significance_level': 'significance_level',
                'significance_mode': 'significance_mode',  # B+方案：显著性检验模式
                'validate_coefficients': 'validate_coefficients',  # 系数方向验证
                'coefficient_direction_mode': 'coefficient_direction_mode',  # 系数方向异常处理模式
                'max_validation_iterations': 'max_validation_iterations',  # B+方案：最大迭代次数
                # 评分刻度参数
                'base_score': 'base_score',
                'base_odds': 'base_odds',
                'pdo': 'pdo',
                # FICO标准分数范围参数
                'use_fico_range': 'use_fico_range',
                'fico_min': 'fico_min',
                'fico_max': 'fico_max',
                # 评分分布显示参数
                'score_bin_method': 'score_bin_method',
                'score_distribution_bins': 'score_distribution_bins',
                'ranking_analysis_bins': 'ranking_analysis_bins',
                # 过拟合检测阈值参数
                'overfit_ks_threshold': 'overfit_ks_threshold',
                'overfit_auc_threshold': 'overfit_auc_threshold',
                # P2-6: 类别不平衡处理
                'imbalance_strategy': 'imbalance_strategy'
            }
            
            for user_key, pipeline_key in param_mapping.items():
                if user_key in params:
                    pipeline_params[pipeline_key] = params[user_key]
            
            # Parse special_values from comma-separated string to list
            if 'special_values' in params:
                special_values_str = params['special_values']
                if isinstance(special_values_str, str) and special_values_str.strip():
                    try:
                        pipeline_params['special_values'] = [float(v.strip()) for v in special_values_str.split(',') if v.strip()]
                    except ValueError:
                        logger.warning(f"Invalid special_values format: {special_values_str}, using defaults")
                elif isinstance(special_values_str, list):
                    pipeline_params['special_values'] = special_values_str
            
            # Parse force_categorical (supports both list from column_multi_select and legacy string format)
            if 'force_categorical' in params:
                force_cat_val = params['force_categorical']
                if isinstance(force_cat_val, list):
                    pipeline_params['force_categorical'] = force_cat_val
                elif isinstance(force_cat_val, str) and force_cat_val.strip():
                    # Legacy: comma-separated string format
                    pipeline_params['force_categorical'] = [v.strip() for v in force_cat_val.split(',') if v.strip()]
        
        return pipeline_params
    
    def _update_progress(
        self,
        context: ExecutionContext,
        stage_id: str,
        progress: float,
        message: str,
        code: str = "",
        output_preview: dict[str, object] | None = None,
        params_used: dict[str, object] | None = None
    ) -> None:
        """更新进度
        
        Args:
            context: 执行上下文
            stage_id: 阶段ID
            progress: 进度百分比 (0-100)
            message: 进度消息
            code: 阶段对应的Python伪代码（可选）
            output_preview: 阶段输出预览数据（可选）
            params_used: 阶段使用的配置参数（可选）
        """
        context.current_stage = stage_id
        
        if stage_id in context.stages:
            stage = context.stages[stage_id]
            stage.progress = progress
            stage.message = message
            
            # 追加日志
            timestamp = datetime.now().strftime("%H:%M:%S")
            stage.logs.append(f"[{timestamp}] {message}")
            
            # 更新伪代码（如果提供）
            if code:
                stage.code = code
            
            # 更新输出预览（如果提供）
            # 注意：需要在保存到 stage.output_preview 之前移除内部标记（如 _skip_expert_pause）
            # 但要在调用 check_expert_mode_pause 之后移除，因为它需要检查这个标记
            if output_preview is not None:
                # 检查是否是跳过的阶段（只有skipped标记，没有业务数据）
                is_skip_only = (
                    output_preview.get('skipped') and 
                    len([k for k in output_preview.keys() if not k.startswith('_') and k not in ('skipped', 'reason', 'retry_message')]) == 0
                )
                
                if is_skip_only and stage.output_preview:
                    # 如果是跳过的阶段且只有skip标记，保留原有的业务数据，只添加skip标记
                    logger.info(f"[SOP] Preserving existing output_preview for skipped stage {stage_id}, adding skip flags")
                    # 合并：保留原有数据，添加新的标记
                    merged_preview = dict(stage.output_preview)
                    merged_preview.update(output_preview)
                    stage.output_preview = merged_preview
                else:
                    # 正常更新
                    stage.output_preview = output_preview
                logger.debug(f"[SOP] Updated output_preview for stage {stage_id}, keys: {list(stage.output_preview.keys()) if stage.output_preview else []}")
            
            # 更新使用的参数（如果提供）
            if params_used:
                stage.params_used = params_used
            
            if progress == 0:
                # 阶段开始：设置状态和开始时间
                # 注意：阶段重试时，状态已被重置为 PENDING，started_at 为 None
                if stage.status == ExecutionStatus.PENDING or stage.started_at is None:
                    stage.status = ExecutionStatus.RUNNING
                    stage.started_at = datetime.now()
                    # 重置 completed_at 以确保重试时重新计算耗时
                    stage.completed_at = None
                    # 阶段开始时，如果未提供params_used，从context.params复制相关参数
                    if not params_used and not stage.params_used:
                        stage.params_used = dict(context.params)
            elif progress >= 100:
                stage.status = ExecutionStatus.COMPLETED
                # 检查是否是跳过的阶段（使用缓存）
                is_skipped_stage = output_preview and output_preview.get('_skipped_during_retry')
                if is_skipped_stage:
                    # 跳过的阶段：尝试从检查点恢复原有的时间信息
                    # 这样历史任务可以显示正确的各阶段执行时间
                    restored_times = False
                    if TASK_MANAGER_AVAILABLE and PersistentExecutionStore is not None:
                        try:
                            checkpoint = PersistentExecutionStore.get_checkpoint(context.execution_id, stage_id)
                            if checkpoint:
                                if checkpoint.get('started_at'):
                                    stage.started_at = datetime.fromisoformat(checkpoint['started_at'])
                                    restored_times = True
                                if checkpoint.get('completed_at'):
                                    stage.completed_at = datetime.fromisoformat(checkpoint['completed_at'])
                                    restored_times = True
                                if restored_times:
                                    logger.info(f"[SOP] Restored times for skipped stage {stage_id}: started={stage.started_at}, completed={stage.completed_at}")
                        except Exception as e:
                            logger.warning(f"[SOP] Failed to restore times for skipped stage {stage_id}: {e}")
                    
                    # 如果无法从检查点恢复，使用当前时间（保持原有逻辑）
                    if not restored_times:
                        now = datetime.now()
                        if stage.started_at is None:
                            stage.started_at = now
                        if stage.completed_at is None:
                            stage.completed_at = now
                        logger.info(f"[SOP] Using current time for skipped stage {stage_id} (no checkpoint found)")
                else:
                    # 正常执行的阶段：只设置 completed_at
                    stage.completed_at = datetime.now()
                
                # Phase 6: 保存阶段检查点
                # 注意：如果是跳过的阶段（包含_skipped_during_retry标记），不要覆盖已有的检查点
                if not is_skipped_stage:
                    self._save_stage_checkpoint(context, stage_id, stage, output_preview)
                else:
                    logger.info(f"[SOP] Skipping checkpoint save for skipped stage: {stage_id}")
                
                # 专家模式：阶段完成后自动暂停（使用统一的公共函数）
                # 注意：check_expert_mode_pause 会检查 stage.output_preview 中的 _skip_expert_pause 标记
                check_expert_mode_pause(context, stage_id, self.registry)
                
                # 在暂停检查之后，移除内部标记（不传递给前端）
                if stage.output_preview:
                    internal_keys = [k for k in stage.output_preview.keys() if k.startswith('_')]
                    if internal_keys:
                        stage.output_preview = {k: v for k, v in stage.output_preview.items() if not k.startswith('_')}
                        logger.info(f"[SOP] Removed internal keys from output_preview: {internal_keys}")
                        if not stage.output_preview:
                            stage.output_preview = None
        
        # Calculate overall progress
        task_def = self.registry.get_task(context.task_id)
        if task_def:
            total_weight = sum(s.progress_weight for s in task_def.stages)
            completed_weight = 0
            
            for stage in task_def.stages:
                if stage.id in context.stages:
                    stage_progress = context.stages[stage.id].progress
                    completed_weight += (stage_progress / 100) * stage.progress_weight
            
            context.overall_progress = (completed_weight / total_weight) * 100 if total_weight > 0 else 0
        
        context.message = message
        ExecutionStore.update(context)
        
        # Call user callback
        if context.progress_callback:
            try:
                context.progress_callback(stage_id, progress, message)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    def _save_stage_checkpoint(
        self,
        context: ExecutionContext,
        stage_id: str,
        stage: StageProgress,
        output_preview: dict[str, object] | None = None
    ) -> None:
        """保存阶段检查点（Phase 6）
        
        Args:
            context: 执行上下文
            stage_id: 阶段ID
            stage: 阶段进度对象
            output_preview: 输出预览数据（可能包含 _full_stage_data）
        """
        if not TASK_MANAGER_AVAILABLE or PersistentExecutionStore is None:
            return
        
        try:
            # 获取阶段索引
            task_def = self.registry.get_task(context.task_id)
            stage_index = 0
            if task_def:
                for i, s in enumerate(task_def.stages):
                    if s.id == stage_id:
                        stage_index = i
                        break
            
            # Phase 6: 提取完整阶段数据（如果存在）
            full_stage_data: dict[str, object] | None = None
            clean_output_preview = None
            
            if output_preview:
                # 提取 _full_stage_data 并从 output_preview 中移除
                _fsd = output_preview.pop("_full_stage_data", None)
                if isinstance(_fsd, dict):
                    full_stage_data = _fsd
                logger.info(f"[Checkpoint] Stage {stage_id}: _full_stage_data exists: {full_stage_data is not None}")
                if full_stage_data:
                    logger.info(f"[Checkpoint] Stage {stage_id}: _full_stage_data keys: {list(full_stage_data.keys())}")
                    if "df_processed" in full_stage_data:
                        df_val = full_stage_data.get("df_processed")
                        logger.info(f"[Checkpoint] Stage {stage_id}: df_processed is None: {df_val is None}, type: {type(df_val)}")
                        if df_val is not None and hasattr(df_val, 'shape'):
                            logger.info(f"[Checkpoint] Stage {stage_id}: df_processed shape: {df_val.shape}")  # pyright: ignore[reportAttributeAccessIssue]
                # 创建不包含大型数据的预览副本
                clean_output_preview = {k: v for k, v in output_preview.items() if not k.startswith("_")}
            
            # 构建输出摘要（用于快速查看，不包含大型数据）
            outputs_summary = None
            if clean_output_preview:
                outputs_summary = {
                    "keys": list(clean_output_preview.keys())[:10],
                    "preview_available": True,
                }
            
            # 构建要保存的输出数据
            # Phase 6: 如果有完整阶段数据，保存完整数据；否则只保存预览
            if full_stage_data:
                # 通用字段（规则挖掘和评分卡共用）
                outputs_to_save = {
                    "output_preview": clean_output_preview,
                    "results": full_stage_data.get("results"),
                    "feature_cols": full_stage_data.get("feature_cols"),
                }
                
                # 规则挖掘任务特有字段
                if "df_processed" in full_stage_data:
                    outputs_to_save["df_processed"] = full_stage_data.get("df_processed")
                
                # 评分卡任务特有字段
                if "train_df" in full_stage_data:
                    outputs_to_save["train_df"] = full_stage_data.get("train_df")
                if "test_df" in full_stage_data:
                    outputs_to_save["test_df"] = full_stage_data.get("test_df")
                if "oot_df" in full_stage_data:
                    outputs_to_save["oot_df"] = full_stage_data.get("oot_df")
                if "df_woe" in full_stage_data:
                    outputs_to_save["df_woe"] = full_stage_data.get("df_woe")
                if "bins" in full_stage_data:
                    outputs_to_save["bins"] = full_stage_data.get("bins")
                if "iv_table" in full_stage_data:
                    outputs_to_save["iv_table"] = full_stage_data.get("iv_table")
                if "selected_features" in full_stage_data:
                    outputs_to_save["selected_features"] = full_stage_data.get("selected_features")
                if "model" in full_stage_data:
                    outputs_to_save["model"] = full_stage_data.get("model")
                if "woe_feature_cols" in full_stage_data:
                    outputs_to_save["woe_feature_cols"] = full_stage_data.get("woe_feature_cols")
                if "scorecard" in full_stage_data:
                    outputs_to_save["scorecard"] = full_stage_data.get("scorecard")
                
                # Phase 24: 评分卡任务评估数据（供report_generation使用）
                if "y_train" in full_stage_data:
                    outputs_to_save["y_train"] = full_stage_data.get("y_train")
                if "y_train_pred_proba" in full_stage_data:
                    outputs_to_save["y_train_pred_proba"] = full_stage_data.get("y_train_pred_proba")
                if "y_test" in full_stage_data:
                    outputs_to_save["y_test"] = full_stage_data.get("y_test")
                if "y_pred_proba" in full_stage_data:
                    outputs_to_save["y_pred_proba"] = full_stage_data.get("y_pred_proba")
                if "y_oot" in full_stage_data:
                    outputs_to_save["y_oot"] = full_stage_data.get("y_oot")
                if "y_oot_pred_proba" in full_stage_data:
                    outputs_to_save["y_oot_pred_proba"] = full_stage_data.get("y_oot_pred_proba")
                
                # 规则挖掘任务：决策树可视化数据（Full Tree模式）和规则来源统计（组合树模式）
                if "full_tree" in full_stage_data:
                    outputs_to_save["full_tree"] = full_stage_data.get("full_tree")
                if "full_tree_features" in full_stage_data:
                    outputs_to_save["full_tree_features"] = full_stage_data.get("full_tree_features")
                if "rule_source_stats" in full_stage_data:
                    outputs_to_save["rule_source_stats"] = full_stage_data.get("rule_source_stats")
                if "feature_cols_for_rules" in full_stage_data:
                    outputs_to_save["feature_cols_for_rules"] = full_stage_data.get("feature_cols_for_rules")
                
                logger.info(f"[Checkpoint] Saving full stage data for checkpoint: {stage_id}, keys: {list(outputs_to_save.keys())}")
                if "df_processed" in outputs_to_save:
                    df_val = outputs_to_save.get("df_processed")
                    logger.info(f"[Checkpoint] outputs_to_save['df_processed'] is None: {df_val is None}")
            else:
                outputs_to_save = {"output_preview": clean_output_preview} if clean_output_preview else None
            
            # 保存检查点
            PersistentExecutionStore.save_checkpoint(
                execution_id=context.execution_id,
                stage_id=stage_id,
                stage_index=stage_index,
                stage_status="completed",
                outputs=outputs_to_save,
                outputs_summary=outputs_summary,
                params=dict(stage.params_used) if stage.params_used else None,
                started_at=stage.started_at,
                completed_at=stage.completed_at,
            )
            
            logger.debug(f"Saved checkpoint for stage: {stage_id}")
        except Exception as e:
            logger.warning(f"Failed to save stage checkpoint: {e}")


# =============================================================================
# Helper Functions
# =============================================================================

def get_execution_status(execution_id: str) -> dict[str, object] | None:
    """
    获取执行状态
    
    支持从持久化存储加载：如果ExecutionStore中没有context，会从持久化存储中加载。
    如果持久化存储中有更新的状态，优先使用持久化存储的状态。
    
    注意：对于已完成的任务，不从 context.pkl 加载（避免加载过期的暂停状态）。
    
    Args:
        execution_id: 执行ID
        
    Returns:
        状态信息字典
    """
    context = ExecutionStore.get(execution_id)
    
    # 如果内存中没有，尝试从持久化存储加载
    if not context:
        logger.info(f"[get_execution_status] Context not found in ExecutionStore, checking persistent storage: {execution_id}")
        
        # 先检查 PersistentExecutionStore 中的状态
        # 如果状态是 completed/failed/cancelled，不需要加载 context.pkl
        persistent_state = PersistentExecutionStore.get(execution_id)
        if persistent_state:
            persistent_status = persistent_state.get("status", "")
            if persistent_status in ("completed", "failed", "cancelled", "stopped"):
                logger.info(f"[get_execution_status] Task already {persistent_status}, not loading context.pkl: {execution_id}")
                return None  # 已完成的任务应该通过历史记录查看，不通过 execution_status
        
        # 尝试从 context.pkl 加载（仅用于暂停/运行中的任务）
        context = PersistentExecutionStore.load_full_state(execution_id)
        
        if not context:
            logger.info(f"[get_execution_status] Context not found in persistent storage: {execution_id}")
            return None
        
        # 将加载的context恢复到ExecutionStore，以便后续操作
        ExecutionStore.update(context)
        logger.info(f"[get_execution_status] Restored context to ExecutionStore: {execution_id}")
    else:
        # 内存中有context，但需要检查持久化存储是否有更新的状态
        # 这是为了解决跨重启恢复时的状态不同步问题
        if PersistentExecutionStore is not None:
            try:
                # 从持久化存储加载状态（不恢复到ExecutionStore，只比较状态）
                persistent_state_dict = PersistentExecutionStore.get(execution_id)
                if persistent_state_dict:
                    # 检测状态不同步：内存是running但持久化是paused/completed/failed/cancelled
                    # 或者持久化存储的updated_at比内存中的新
                    persistent_status = persistent_state_dict.get("status", "")
                    context_status = context.status.value
                    
                    # 如果状态不匹配，或者持久化存储更新时间更新
                    should_reload = False
                    if context_status in ("running", "pending") and persistent_status in ("paused", "completed", "failed", "cancelled"):
                        should_reload = True
                        logger.warning(f"[get_execution_status] Status mismatch (memory={context_status}, persistent={persistent_status}), reloading from persistent storage: {execution_id}")
                    elif persistent_state_dict.get("updated_at"):
                        persistent_updated = persistent_state_dict["updated_at"]
                        if isinstance(persistent_updated, str):
                            from datetime import datetime
                            persistent_updated = datetime.fromisoformat(persistent_updated)
                        # ExecutionContext 没有 updated_at 属性，跳过时间比较
                        # 直接基于状态不匹配决定是否重新加载
                    
                    if should_reload:
                        # 从持久化存储重新加载context
                        loaded_context = PersistentExecutionStore.load_full_state(execution_id)
                        if loaded_context:
                            ExecutionStore.update(loaded_context)
                            context = loaded_context
                            logger.info(f"[get_execution_status] Reloaded context from persistent storage: {execution_id}")
            except Exception as e:
                logger.warning(f"[get_execution_status] Failed to check persistent state: {e}")
    
    # 获取任务定义以便提供参数元数据
    registry = get_registry()
    task_def = registry.get_task(context.task_id)
    
    # 构建阶段参数映射（从任务定义中获取每个阶段的参数）
    stage_params_meta: dict[str, list[dict[str, object]]] = {}
    if task_def:
        all_params = list(task_def.required_params) + list(task_def.optional_params)
        for param in all_params:
            if param.stage:
                if param.stage not in stage_params_meta:
                    stage_params_meta[param.stage] = []
                # 从 validation 中提取 min/max/step（如果存在）
                min_val = param.validation.get("min") if param.validation else None
                max_val = param.validation.get("max") if param.validation else None
                step_val = param.validation.get("step") if param.validation else None
                stage_params_meta[param.stage].append({
                    "name": param.name,
                    "label": param.label,
                    "type": param.param_type.value,
                    "default": param.default,
                    "description": param.description,
                    "options": param.options,
                    "validation": param.validation,
                    "required": param.required,
                    "allow_empty": param.allow_empty,  # 可选参数标识
                    "min": min_val,  # 顶层字段
                    "max": max_val,
                    "step": step_val,
                    "show_when": param.show_when,
                    "group": param.group,  # 参数分组标识
                })
    
    def get_stage_params(stage_id: str, stage: StageProgress) -> dict[str, object]:
        """获取阶段的可编辑参数值"""
        # 已完成阶段：使用 params_used
        if stage.params_used:
            return dict(stage.params_used)
        # 待执行阶段：使用执行上下文中的参数或默认值
        result: dict[str, object] = {}
        if stage_id in stage_params_meta:
            for param_meta in stage_params_meta[stage_id]:
                param_name = str(param_meta.get("name", ""))
                if param_name in context.params:
                    result[param_name] = context.params[param_name]
                elif param_meta.get("default") is not None:
                    result[param_name] = param_meta.get("default")
        return result
    
    logger.info(f"[get_execution_status] context.file_path={context.file_path}")
    
    return {
        "execution_id": context.execution_id,
        "task_id": context.task_id,
        "status": context.status.value,
        "current_stage": context.current_stage,
        "overall_progress": context.overall_progress,
        "message": context.message,
        "started_at": context.started_at.isoformat() if context.started_at else None,
        "completed_at": context.completed_at.isoformat() if context.completed_at else None,
        "record_id": context.record_id,  # Phase 9: 添加record_id用于AI分析缓存
        "file_path": context.file_path,  # 任务使用的数据文件路径
        "stage_order": context.stage_order,  # 阶段执行顺序
        "stages": {
            stage_id: {
                "stage_id": stage.stage_id,
                "stage_name": stage.stage_name,
                "status": stage.status.value,
                "progress": stage.progress,
                "message": stage.message,
                "logs": stage.logs,  # 阶段日志
                "code": stage.code,  # 阶段伪代码
                "output_preview": stage.output_preview,  # 阶段输出预览
                "params_used": stage.params_used,  # 阶段使用的配置参数（只读）
                "params": get_stage_params(stage_id, stage),  # 阶段可编辑参数
                # 参数元数据：优先从任务定义获取（包含最新字段如allow_empty/min/max/step）
                # 回退到缓存的params_meta（兼容旧数据）
                "params_meta": stage_params_meta.get(stage_id, []) or stage.params_meta,
                "execution_time_ms": stage.execution_time_ms,  # 阶段执行时间（毫秒）
                "started_at": stage.started_at.isoformat() if stage.started_at else None,  # 阶段开始时间
                "completed_at": stage.completed_at.isoformat() if stage.completed_at else None,  # 阶段完成时间
                "snapshots": [
                    {
                        "version": s.version,
                        "params_used": s.params_used,
                        "output_preview": s.output_preview,
                        "ai_analysis": s.ai_analysis,
                        "suggested_params": s.suggested_params,
                        "execution_time_ms": s.execution_time_ms,
                        "completed_at": s.completed_at,
                        "retry_reason": s.retry_reason,
                    }
                    for s in (stage.snapshots if hasattr(stage, 'snapshots') else [])
                ],
            }
            for stage_id, stage in context.stages.items()
        }
    }


def _make_json_serializable(obj: object) -> JsonValue:
    """将对象转换为JSON可序列化格式"""
    import numpy as np
    
    if obj is None:
        return None
    if isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    if isinstance(obj, np.integer):
        return int(obj)  # pyright: ignore[reportUnknownArgumentType]
    if isinstance(obj, np.floating):
        val = float(obj)  # pyright: ignore[reportUnknownArgumentType]
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    if isinstance(obj, np.ndarray):
        return [_make_json_serializable(x) for x in obj.tolist()]  # pyright: ignore[reportAny]
    if isinstance(obj, dict):
        return {str(k): _make_json_serializable(v) for k, v in obj.items()}  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    if isinstance(obj, (list, tuple)):
        return [_make_json_serializable(x) for x in obj]  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    if isinstance(obj, pd.DataFrame):
        records = obj.fillna("").head(100).to_dict(orient="records")  # pyright: ignore[reportUnknownMemberType]
        return [_make_json_serializable(r) for r in records]
    if isinstance(obj, pd.Series):
        return [_make_json_serializable(v) for v in obj.fillna("").to_list()]  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportUnknownVariableType]
    return str(obj)


def get_execution_result(execution_id: str) -> dict[str, object] | None:
    """
    获取执行结果
    
    支持从持久化存储加载：如果ExecutionStore中没有context，会从持久化存储中加载。
    
    Args:
        execution_id: 执行ID
        
    Returns:
        结果信息字典
    """
    context = ExecutionStore.get(execution_id)
    
    # 如果内存中没有，尝试从持久化存储加载
    if not context:
        logger.info(f"[get_execution_result] Context not found in ExecutionStore, loading from persistent storage: {execution_id}")
        context = PersistentExecutionStore.load_full_state(execution_id)
        
        if not context:
            logger.info(f"[get_execution_result] Context not found in persistent storage: {execution_id}")
            return None
        
        # 将加载的context恢复到ExecutionStore，以便后续操作
        ExecutionStore.update(context)
        logger.info(f"[get_execution_result] Restored context to ExecutionStore: {execution_id}")
    
    # Convert DataFrame outputs to serializable format
    outputs: dict[str, object] = {}
    for key, value in context.outputs.items():
        try:
            if isinstance(value, pd.DataFrame):
                # 处理DataFrame，替换NaN为空字符串
                df_clean: pd.DataFrame = value.fillna("")  # pyright: ignore[reportUnknownMemberType]
                outputs[key] = {
                    "type": "dataframe",
                    "columns": list(df_clean.columns),
                    "shape": list(df_clean.shape),
                    "data": _make_json_serializable(df_clean.head(100).to_dict(orient="records"))  # pyright: ignore[reportUnknownMemberType]
                }
            elif isinstance(value, dict):
                # 检查是否是 dict[str, DataFrame] 结构（如scorecard）
                dict_value: dict[object, object] = value  # pyright: ignore[reportUnknownVariableType]
                if dict_value and all(isinstance(v, pd.DataFrame) for v in dict_value.values()):
                    # 特殊处理：将每个DataFrame转换为可序列化格式
                    serialized_dict: dict[str, object] = {}
                    for sub_key, sub_val in dict_value.items():
                        if isinstance(sub_val, pd.DataFrame):
                            df_clean = sub_val.fillna("")  # pyright: ignore[reportUnknownMemberType]
                            serialized_dict[str(sub_key)] = {
                                "columns": list(df_clean.columns),
                                "data": _make_json_serializable(df_clean.to_dict(orient="records"))  # pyright: ignore[reportUnknownMemberType]
                            }
                    outputs[key] = {"type": "dict_of_dataframes", "data": serialized_dict}
                else:
                    outputs[key] = {"type": "dict", "data": _make_json_serializable(dict_value)}
            elif isinstance(value, (list, tuple)):
                # 正确处理list类型（如selected_features）
                outputs[key] = {"type": "list", "data": _make_json_serializable(list(value))}  # pyright: ignore[reportUnknownArgumentType]
            else:
                outputs[key] = {"type": "other", "data": str(value)}
        except Exception as e:
            outputs[key] = {"type": "error", "data": f"Serialization error: {str(e)}"}
    
    return {
        "execution_id": context.execution_id,
        "task_id": context.task_id,
        "status": context.status.value,
        "record_id": context.record_id,  # 添加record_id用于获取历史stages数据
        "outputs": outputs,
        "errors": context.errors
    }


# =============================================================================
# Global Executor Instance
# =============================================================================

_executor: SOPExecutor | None = None


def get_executor() -> SOPExecutor:
    """获取全局执行器实例"""
    global _executor
    if _executor is None:
        _executor = SOPExecutor()
    return _executor


# =============================================================================
# Export
# =============================================================================

__all__ = [
    # Status
    'ExecutionStatus',
    'StageProgress',
    'ExecutionContext',
    # Store
    'ExecutionStore',
    # Executor
    'SOPExecutor',
    'get_executor',
    # Helpers
    'get_execution_status',
    'get_execution_result',
    'check_expert_mode_pause',  # 统一的专家模式暂停逻辑
]
