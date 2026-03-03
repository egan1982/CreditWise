# -*- coding: utf-8 -*-
"""
Expert Mode Executor - 专家模式执行器

提供阶段级别的手动控制执行能力：
- 阶段参数调整
- 阶段代码编辑
- 单阶段执行
- 阶段跳过/重做
"""

from __future__ import annotations

import logging
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..executor import (
    ExecutionStatus,
    get_executor,
)
from ..registry import get_registry
from .stage_result_store import StageResultStore
from .stage_state_machine import StageStatus, StageStateMachine

logger = logging.getLogger(__name__)


class ExpertStageState(Enum):
    """专家模式阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExpertStageContext:
    """专家模式阶段执行上下文"""
    
    stage_id: str
    stage_name: str
    state: ExpertStageState = ExpertStageState.PENDING
    
    # 阶段参数
    params: Dict[str, Any] = field(default_factory=dict)
    
    # 阶段代码（用户可编辑）
    code: str = ""
    original_code: str = ""  # 原始代码（用于对比）
    
    # 阶段输入/输出
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    
    # 执行信息
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    logs: List[str] = field(default_factory=list)
    
    # 用户修改标记
    params_modified: bool = False
    code_modified: bool = False
    
    @property
    def execution_time_ms(self) -> int | None:
        """计算阶段执行时间（毫秒）"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "state": self.state.value,
            "params": self.params,
            "code": self.code,
            "code_modified": self.code_modified,
            "params_modified": self.params_modified,
            "has_outputs": bool(self.outputs),
            "error": self.error,
            "logs": self.logs[-20:],  # 最近20条日志
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "params_used": self.params,  # 使用的配置参数（专家模式下即为params）
            "execution_time_ms": self.execution_time_ms,  # 阶段执行时间（毫秒）
        }


@dataclass
class ExpertExecutionContext:
    """专家模式执行上下文"""
    
    execution_id: str
    task_id: str
    session_id: str
    
    # 阶段列表
    stages: Dict[str, ExpertStageContext] = field(default_factory=dict)
    stage_order: List[str] = field(default_factory=list)
    
    # 当前状态
    current_stage_index: int = 0
    overall_status: ExecutionStatus = ExecutionStatus.PENDING
    
    # 全局数据
    global_data: Dict[str, Any] = field(default_factory=dict)
    file_path: str | None = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    @property
    def current_stage_id(self) -> str | None:
        """获取当前阶段ID"""
        if 0 <= self.current_stage_index < len(self.stage_order):
            return self.stage_order[self.current_stage_index]
        return None
    
    @property
    def current_stage(self) -> ExpertStageContext | None:
        """获取当前阶段上下文"""
        stage_id = self.current_stage_id
        if stage_id:
            return self.stages.get(stage_id)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "current_stage_index": self.current_stage_index,
            "current_stage_id": self.current_stage_id,
            "overall_status": self.overall_status.value,
            "stage_order": self.stage_order,
            "stages": {
                stage_id: stage.to_dict()
                for stage_id, stage in self.stages.items()
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ExpertExecutionStore:
    """专家模式执行存储"""
    
    _executions: Dict[str, ExpertExecutionContext] = {}
    
    @classmethod
    def get(cls, execution_id: str) -> ExpertExecutionContext | None:
        """获取执行上下文"""
        return cls._executions.get(execution_id)
    
    @classmethod
    def set(cls, context: ExpertExecutionContext) -> None:
        """保存执行上下文"""
        cls._executions[context.execution_id] = context
    
    @classmethod
    def remove(cls, execution_id: str) -> None:
        """移除执行上下文"""
        cls._executions.pop(execution_id, None)
    
    @classmethod
    def list_by_session(cls, session_id: str) -> List[ExpertExecutionContext]:
        """按会话ID列出执行上下文"""
        return [
            ctx for ctx in cls._executions.values()
            if ctx.session_id == session_id
        ]


class ExpertModeExecutor:
    """
    专家模式执行器
    
    提供阶段级别的手动控制：
    - 阶段参数调整
    - 阶段代码编辑
    - 单阶段执行
    - 阶段跳过/重做
    """
    
    def __init__(self, workspace_dir: str = "."):
        self.registry = get_registry()
        self.workspace_dir = workspace_dir
        self.result_store = StageResultStore(workspace_dir)
        self._code_executor: Callable[[str, dict], dict] | None = None
    
    def set_code_executor(self, executor: Callable[[str, dict], dict]) -> None:
        """设置代码执行器"""
        self._code_executor = executor
    
    def create_execution(
        self,
        task_id: str,
        session_id: str,
        file_path: str | None = None,
        params: Dict[str, Any] | None = None
    ) -> ExpertExecutionContext:
        """
        创建专家模式执行上下文
        
        Args:
            task_id: 任务类型ID
            session_id: 会话ID
            file_path: 数据文件路径
            params: 初始参数
            
        Returns:
            专家模式执行上下文
        """
        # 获取任务定义
        task_def = self.registry.get_task(task_id)
        if not task_def:
            raise ValueError(f"Unknown task: {task_id}")
        
        # 创建执行上下文
        execution_id = str(uuid.uuid4())
        context = ExpertExecutionContext(
            execution_id=execution_id,
            task_id=task_id,
            session_id=session_id,
            file_path=file_path,
        )
        
        # 初始化阶段
        for stage in task_def.stages:
            stage_context = ExpertStageContext(
                stage_id=stage.id,
                stage_name=stage.name,
            )
            
            # 从任务参数中提取阶段相关参数
            if params:
                stage_params = {}
                for key, value in params.items():
                    if key.startswith(f"{stage.id}_") or key in stage.required_inputs:
                        stage_params[key] = value
                stage_context.params = stage_params
            
            context.stages[stage.id] = stage_context
            context.stage_order.append(stage.id)
        
        # 保存
        ExpertExecutionStore.set(context)
        
        logger.info(f"[Expert] Created execution: {execution_id}, task: {task_id}, stages: {len(context.stages)}")
        
        return context
    
    def get_execution(self, execution_id: str) -> ExpertExecutionContext | None:
        """获取执行上下文"""
        return ExpertExecutionStore.get(execution_id)
    
    def update_stage_params(
        self,
        execution_id: str,
        stage_id: str,
        params: Dict[str, Any]
    ) -> ExpertStageContext:
        """
        更新阶段参数
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            params: 新参数
            
        Returns:
            更新后的阶段上下文
        """
        context = ExpertExecutionStore.get(execution_id)
        if not context:
            raise ValueError(f"Execution not found: {execution_id}")
        
        stage = context.stages.get(stage_id)
        if not stage:
            raise ValueError(f"Stage not found: {stage_id}")
        
        # 检查状态是否允许修改
        allowed_states = [ExpertStageState.PENDING, ExpertStageState.PAUSED, ExpertStageState.COMPLETED]
        if stage.state not in allowed_states:
            raise ValueError(f"Cannot modify params in state: {stage.state}")
        
        stage.params.update(params)
        stage.params_modified = True
        
        # 如果阶段已完成，标记为需要重新执行
        if stage.state == ExpertStageState.COMPLETED:
            stage.state = ExpertStageState.PENDING
        
        logger.info(f"[Expert] Updated stage params: {execution_id}/{stage_id}")
        
        return stage
    
    def update_stage_code(
        self,
        execution_id: str,
        stage_id: str,
        code: str
    ) -> ExpertStageContext:
        """
        更新阶段代码
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            code: 新代码
            
        Returns:
            更新后的阶段上下文
        """
        context = ExpertExecutionStore.get(execution_id)
        if not context:
            raise ValueError(f"Execution not found: {execution_id}")
        
        stage = context.stages.get(stage_id)
        if not stage:
            raise ValueError(f"Stage not found: {stage_id}")
        
        # 保存原始代码（如果是首次修改）
        if not stage.original_code:
            stage.original_code = stage.code
        
        stage.code = code
        stage.code_modified = (code != stage.original_code)
        
        # 如果阶段已完成，标记为需要重新执行
        if stage.state == ExpertStageState.COMPLETED:
            stage.state = ExpertStageState.PENDING
        
        logger.info(f"[Expert] Updated stage code: {execution_id}/{stage_id}, modified: {stage.code_modified}")
        
        return stage
    
    async def execute_stage(
        self,
        execution_id: str,
        stage_id: str,
        progress_callback: Callable[[str, float, str], None] | None = None
    ) -> ExpertStageContext:
        """
        执行单个阶段
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            progress_callback: 进度回调
            
        Returns:
            执行后的阶段上下文
        """
        context = ExpertExecutionStore.get(execution_id)
        if not context:
            raise ValueError(f"Execution not found: {execution_id}")
        
        stage = context.stages.get(stage_id)
        if not stage:
            raise ValueError(f"Stage not found: {stage_id}")
        
        # 检查状态是否允许开始
        startable_states = [ExpertStageState.PENDING, ExpertStageState.PAUSED, ExpertStageState.FAILED]
        if stage.state not in startable_states:
            raise ValueError(f"Cannot start stage in state: {stage.state}")
        
        # 更新状态
        stage.state = ExpertStageState.RUNNING
        stage.started_at = datetime.now()
        stage.error = None
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 开始执行阶段: {stage.stage_name}")
        
        try:
            # 收集输入
            stage.inputs = self._collect_stage_inputs(context, stage_id)
            
            # 执行阶段代码
            if stage.code and self._code_executor:
                stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 执行用户代码...")
                
                # 准备执行环境
                exec_globals = {
                    **stage.inputs,
                    **stage.params,
                    "data": context.global_data.get("data"),
                }
                
                # 执行代码
                result = self._code_executor(stage.code, exec_globals)
                
                if result.get("success"):
                    stage.outputs = result.get("outputs", {})
                    stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 代码执行成功")
                else:
                    raise RuntimeError(result.get("error", "代码执行失败"))
            else:
                # 使用默认执行器
                stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 使用默认执行器...")
                stage.outputs = await self._execute_stage_default(context, stage)
            
            # 保存结果
            self.result_store.save_stage_result(context.session_id, stage_id, stage.outputs)
            
            # 更新状态
            stage.state = ExpertStageState.COMPLETED
            stage.completed_at = datetime.now()
            stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段执行完成")
            
            # 回调
            if progress_callback:
                progress_callback(stage_id, 100.0, "阶段执行完成")
            
        except Exception as e:
            stage.state = ExpertStageState.FAILED
            stage.error = str(e)
            stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 执行失败: {e}")
            logger.error(f"[Expert] Stage execution failed: {execution_id}/{stage_id}: {e}")
            logger.error(traceback.format_exc())
        
        return stage
    
    def _collect_stage_inputs(
        self,
        context: ExpertExecutionContext,
        stage_id: str
    ) -> Dict[str, Any]:
        """收集阶段输入"""
        inputs: Dict[str, Any] = {}
        
        # 从全局数据收集
        inputs.update(context.global_data)
        
        # 从前置阶段输出收集
        stage_index = context.stage_order.index(stage_id)
        for i in range(stage_index):
            prev_stage_id = context.stage_order[i]
            prev_stage = context.stages.get(prev_stage_id)
            if prev_stage and prev_stage.outputs:
                inputs.update(prev_stage.outputs)
        
        return inputs
    
    async def _execute_stage_default(
        self,
        context: ExpertExecutionContext,
        stage: ExpertStageContext
    ) -> Dict[str, Any]:
        """使用默认执行器执行阶段"""
        import asyncio
        
        # 获取任务定义
        task_def = self.registry.get_task(context.task_id)
        if not task_def:
            raise ValueError(f"Unknown task: {context.task_id}")
        
        # 查找阶段定义
        stage_def = None
        for s in task_def.stages:
            if s.id == stage.stage_id:
                stage_def = s
                break
        
        if not stage_def:
            raise ValueError(f"Stage definition not found: {stage.stage_id}")
        
        # 获取阶段处理函数
        if stage_def.handler:
            # 准备输入
            handler_inputs = {**stage.inputs, **stage.params}
            if context.global_data.get("data") is not None:
                handler_inputs["data"] = context.global_data["data"]
            
            # 执行处理函数
            if asyncio.iscoroutinefunction(stage_def.handler):
                result = await stage_def.handler(**handler_inputs)
            else:
                result = await asyncio.to_thread(stage_def.handler, **handler_inputs)
            
            return result if isinstance(result, dict) else {"result": result}
        
        return {}
    
    def skip_stage(
        self,
        execution_id: str,
        stage_id: str,
        reason: str = ""
    ) -> ExpertStageContext:
        """
        跳过阶段
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            reason: 跳过原因
            
        Returns:
            更新后的阶段上下文
        """
        context = ExpertExecutionStore.get(execution_id)
        if not context:
            raise ValueError(f"Execution not found: {execution_id}")
        
        stage = context.stages.get(stage_id)
        if not stage:
            raise ValueError(f"Stage not found: {stage_id}")
        
        # 只能从 PENDING 状态跳过
        if stage.state != ExpertStageState.PENDING:
            raise ValueError(f"Cannot skip stage in state: {stage.state}")
        
        stage.state = ExpertStageState.SKIPPED
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段已跳过: {reason or '用户选择跳过'}")
        
        logger.info(f"[Expert] Skipped stage: {execution_id}/{stage_id}")
        
        return stage
    
    def reset_stage(
        self,
        execution_id: str,
        stage_id: str
    ) -> ExpertStageContext:
        """
        重置阶段
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            
        Returns:
            重置后的阶段上下文
        """
        context = ExpertExecutionStore.get(execution_id)
        if not context:
            raise ValueError(f"Execution not found: {execution_id}")
        
        stage = context.stages.get(stage_id)
        if not stage:
            raise ValueError(f"Stage not found: {stage_id}")
        
        # 可以从任何状态重置
        stage.state = ExpertStageState.PENDING
        stage.outputs = {}
        stage.error = None
        stage.started_at = None
        stage.completed_at = None
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段已重置")
        
        # 清除保存的结果
        self.result_store.delete_stage_result(context.session_id, stage_id)
        
        logger.info(f"[Expert] Reset stage: {execution_id}/{stage_id}")
        
        return stage
    
    def move_to_stage(
        self,
        execution_id: str,
        stage_id: str
    ) -> ExpertExecutionContext:
        """
        移动到指定阶段
        
        Args:
            execution_id: 执行ID
            stage_id: 目标阶段ID
            
        Returns:
            更新后的执行上下文
        """
        context = ExpertExecutionStore.get(execution_id)
        if not context:
            raise ValueError(f"Execution not found: {execution_id}")
        
        if stage_id not in context.stage_order:
            raise ValueError(f"Stage not found: {stage_id}")
        
        context.current_stage_index = context.stage_order.index(stage_id)
        
        logger.info(f"[Expert] Moved to stage: {execution_id}/{stage_id}")
        
        return context
    
    def get_stage_result(
        self,
        session_id: str,
        stage_id: str
    ) -> Dict[str, Any] | None:
        """获取阶段结果"""
        return self.result_store.load_stage_result(session_id, stage_id)


# 全局实例
_expert_executors: Dict[str, ExpertModeExecutor] = {}


def get_expert_executor(workspace_dir: str = ".") -> ExpertModeExecutor:
    """获取专家模式执行器实例
    
    Args:
        workspace_dir: 工作区目录
        
    Returns:
        ExpertModeExecutor实例
    """
    import os
    abs_path = os.path.abspath(workspace_dir)
    
    if abs_path not in _expert_executors:
        _expert_executors[abs_path] = ExpertModeExecutor(abs_path)
    
    return _expert_executors[abs_path]
