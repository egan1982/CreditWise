# -*- coding: utf-8 -*-
"""
Execution State Recovery - 执行状态恢复服务

提供任务恢复相关的高级功能：
- 检查任务是否可以恢复
- 获取恢复所需的上下文信息
- 列出可恢复的任务
- 阶段重试支持
"""

import logging
from typing import Any, Dict, List, Optional

from .persistent_store import PersistentExecutionStore
from .enums import TaskStatus

logger = logging.getLogger(__name__)


class ExecutionStateRecovery:
    """执行状态恢复服务
    
    提供任务恢复相关的高级功能：
    - 检查任务是否可以恢复
    - 获取恢复所需的上下文
    - 阶段重试
    """
    
    @classmethod
    def can_resume(cls, execution_id: str) -> Dict[str, Any]:
        """检查任务是否可以恢复
        
        Args:
            execution_id: 执行ID
            
        Returns:
            {
                "can_resume": bool,
                "reason": str,
                "resume_stage_id": str | None,
                "completed_stages": List[str],
            }
        """
        # 获取执行状态
        state = PersistentExecutionStore.get(execution_id)
        
        if not state:
            return {
                "can_resume": False,
                "reason": "执行不存在或已完成",
                "resume_stage_id": None,
                "completed_stages": [],
            }
        
        if state["status"] != TaskStatus.PAUSED.value:
            return {
                "can_resume": False,
                "reason": f"任务状态为 {state['status']}，不可恢复",
                "resume_stage_id": None,
                "completed_stages": [],
            }
        
        # 获取检查点
        checkpoints = PersistentExecutionStore.get_checkpoints(execution_id)
        completed_stages = [
            cp["stage_id"] for cp in checkpoints 
            if cp["stage_status"] == "completed"
        ]
        
        return {
            "can_resume": True,
            "reason": "可以恢复",
            "resume_stage_id": state.get("pause_stage_id") or state.get("current_stage_id"),
            "completed_stages": completed_stages,
        }
    
    @classmethod
    def get_resume_context(cls, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取恢复所需的上下文信息
        
        Args:
            execution_id: 执行ID
            
        Returns:
            {
                "execution_id": str,
                "task_id": str,
                "params": dict,
                "resume_stage_id": str,
                "completed_stages": List[str],
                "stage_outputs": Dict[str, Any],  # 已完成阶段的输出
            }
        """
        check_result = cls.can_resume(execution_id)
        if not check_result["can_resume"]:
            return None
        
        # 获取执行状态
        state = PersistentExecutionStore.get(execution_id)
        if not state:
            return None
        
        # 加载已完成阶段的输出
        stage_outputs = {}
        for stage_id in check_result["completed_stages"]:
            outputs = PersistentExecutionStore.load_checkpoint_outputs(
                execution_id, stage_id
            )
            if outputs:
                stage_outputs[stage_id] = outputs
        
        return {
            "execution_id": execution_id,
            "task_id": state["task_id"],
            "session_id": state["session_id"],
            "record_id": state["record_id"],
            "params": state["params"],
            "interaction_mode": state["interaction_mode"],
            "data_file_path": state["data_file_path"],
            "resume_stage_id": check_result["resume_stage_id"],
            "completed_stages": check_result["completed_stages"],
            "stage_outputs": stage_outputs,
        }
    
    @classmethod
    def list_recoverable(
        cls,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """列出可恢复的任务
        
        Args:
            session_id: 可选，按会话筛选
            
        Returns:
            可恢复任务列表
        """
        paused_states = PersistentExecutionStore.list_paused(session_id)
        
        result = []
        for state in paused_states:
            checkpoints = PersistentExecutionStore.get_checkpoints(state["execution_id"])
            completed_count = sum(1 for cp in checkpoints if cp["stage_status"] == "completed")
            
            result.append({
                **state,
                "completed_stages_count": completed_count,
                "can_resume": True,
            })
        
        return result
    
    @classmethod
    def can_retry_stage(
        cls,
        execution_id: str,
        stage_id: str
    ) -> Dict[str, Any]:
        """检查阶段是否可以重试
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            
        Returns:
            {
                "can_retry": bool,
                "reason": str,
                "previous_stage_id": str | None,  # 前一阶段ID（用于获取输入）
            }
        """
        # 获取执行状态
        state = PersistentExecutionStore.get(execution_id)
        
        if not state:
            return {
                "can_retry": False,
                "reason": "执行不存在",
                "previous_stage_id": None,
            }
        
        # 只有暂停状态才能重试
        if state["status"] != TaskStatus.PAUSED.value:
            return {
                "can_retry": False,
                "reason": f"任务状态为 {state['status']}，需要先暂停才能重试阶段",
                "previous_stage_id": None,
            }
        
        # 获取检查点
        checkpoints = PersistentExecutionStore.get_checkpoints(execution_id)
        checkpoint_dict = {cp["stage_id"]: cp for cp in checkpoints}
        
        if stage_id not in checkpoint_dict:
            return {
                "can_retry": False,
                "reason": f"阶段 {stage_id} 不存在",
                "previous_stage_id": None,
            }
        
        target_checkpoint = checkpoint_dict[stage_id]
        target_index = target_checkpoint["stage_index"]
        
        # 查找前一阶段
        previous_stage_id = None
        if target_index > 0:
            for cp in checkpoints:
                if cp["stage_index"] == target_index - 1:
                    previous_stage_id = cp["stage_id"]
                    break
        
        return {
            "can_retry": True,
            "reason": "可以重试",
            "previous_stage_id": previous_stage_id,
            "stage_index": target_index,
        }
    
    @classmethod
    def prepare_stage_retry(
        cls,
        execution_id: str,
        stage_id: str,
        new_params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """准备阶段重试
        
        重置指定阶段及后续阶段的检查点，并返回重试所需的上下文。
        
        Args:
            execution_id: 执行ID
            stage_id: 要重试的阶段ID
            new_params: 新参数（可选，覆盖原参数）
            
        Returns:
            {
                "execution_id": str,
                "retry_stage_id": str,
                "previous_stage_outputs": Dict[str, Any] | None,  # 前一阶段的输出
                "params": Dict[str, Any],  # 合并后的参数
            }
        """
        # 检查是否可以重试
        check_result = cls.can_retry_stage(execution_id, stage_id)
        if not check_result["can_retry"]:
            logger.warning(f"Cannot retry stage: {check_result['reason']}")
            return None
        
        # 使检查点失效
        invalidated_count = PersistentExecutionStore.invalidate_checkpoints_from(
            execution_id, stage_id
        )
        logger.info(f"Invalidated {invalidated_count} checkpoints from {stage_id}")
        
        # 更新执行状态
        PersistentExecutionStore.update(
            execution_id=execution_id,
            pause_stage_id=stage_id,  # 设置恢复点为要重试的阶段
        )
        
        # 加载前一阶段的输出
        previous_stage_outputs = None
        previous_stage_id = check_result.get("previous_stage_id")
        if previous_stage_id:
            previous_stage_outputs = PersistentExecutionStore.load_checkpoint_outputs(
                execution_id, previous_stage_id
            )
        
        # 获取执行状态
        state = PersistentExecutionStore.get(execution_id)
        original_params = state.get("params", {}) if state else {}
        
        # 合并参数
        merged_params = {**original_params}
        if new_params:
            merged_params.update(new_params)
        
        return {
            "execution_id": execution_id,
            "retry_stage_id": stage_id,
            "retry_stage_index": check_result.get("stage_index", 0),
            "previous_stage_id": previous_stage_id,
            "previous_stage_outputs": previous_stage_outputs,
            "params": merged_params,
        }
    
    @classmethod
    def get_stage_input(
        cls,
        execution_id: str,
        stage_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取阶段的输入（即前一阶段的输出）
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            
        Returns:
            前一阶段的输出，如果是第一个阶段则返回 None
        """
        checkpoints = PersistentExecutionStore.get_checkpoints(execution_id)
        
        # 找到目标阶段的索引
        target_index = None
        for cp in checkpoints:
            if cp["stage_id"] == stage_id:
                target_index = cp["stage_index"]
                break
        
        if target_index is None or target_index == 0:
            return None
        
        # 找到前一阶段
        for cp in checkpoints:
            if cp["stage_index"] == target_index - 1:
                return PersistentExecutionStore.load_checkpoint_outputs(
                    execution_id, cp["stage_id"]
                )
        
        return None
