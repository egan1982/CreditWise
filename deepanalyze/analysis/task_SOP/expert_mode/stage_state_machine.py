# -*- coding: utf-8 -*-
"""
Stage State Machine - 阶段状态机

管理专家模式下的阶段执行流程：
- 阶段状态转换
- 阶段参数管理
- 阶段结果跟踪
- 重试与回滚逻辑
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class StageStatus(Enum):
    """阶段状态枚举"""
    PENDING = "pending"        # 待执行
    RUNNING = "running"        # 执行中
    PAUSED = "paused"          # 已暂停（等待用户操作）
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 执行失败
    SKIPPED = "skipped"        # 已跳过


@dataclass
class StageState:
    """阶段状态"""
    stage_id: str
    stage_name: str
    status: StageStatus = StageStatus.PENDING
    start_time: datetime | None = None
    end_time: datetime | None = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] | None = None
    generated_code: str | None = None
    error: str | None = None
    logs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "parameters": self.parameters,
            "result": self.result,
            "generated_code": self.generated_code,
            "error": self.error,
            "logs": self.logs,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageState":
        """从字典反序列化"""
        return cls(
            stage_id=data["stage_id"],
            stage_name=data["stage_name"],
            status=StageStatus(data.get("status", "pending")),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            parameters=data.get("parameters", {}),
            result=data.get("result"),
            generated_code=data.get("generated_code"),
            error=data.get("error"),
            logs=data.get("logs", []),
        )


class StageStateMachine:
    """阶段状态机
    
    管理专家模式下的阶段执行流程：
    - 状态转换控制
    - 阶段参数管理
    - 重试与回滚逻辑
    """
    
    def __init__(
        self,
        session_id: str,
        task_id: str,
        stages: List[Dict[str, str]],
        interaction_mode: str = "expert"
    ):
        """初始化状态机
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            stages: 阶段定义列表 [{"id": "...", "name": "..."}]
            interaction_mode: 交互模式
        """
        self.session_id = session_id
        self.task_id = task_id
        self.interaction_mode = interaction_mode
        self.current_stage_index = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # 初始化所有阶段
        self.stages: Dict[str, StageState] = {}
        self._stage_order: List[str] = []
        
        for stage in stages:
            stage_id = stage.get("id", "")
            stage_name = stage.get("name", "")
            self.stages[stage_id] = StageState(
                stage_id=stage_id,
                stage_name=stage_name,
                status=StageStatus.PENDING,
                parameters={}
            )
            self._stage_order.append(stage_id)
    
    # =========================================================================
    # 状态转换方法
    # =========================================================================
    
    def start_stage(self, stage_id: str) -> bool:
        """开始执行阶段
        
        Args:
            stage_id: 阶段ID
            
        Returns:
            是否成功开始
        """
        if stage_id not in self.stages:
            logger.warning(f"Stage not found: {stage_id}")
            return False
        
        stage = self.stages[stage_id]
        
        # 只能从 PENDING、PAUSED、FAILED 状态开始
        if stage.status not in [StageStatus.PENDING, StageStatus.PAUSED, StageStatus.FAILED]:
            logger.warning(f"Cannot start stage {stage_id} from status {stage.status}")
            return False
        
        stage.status = StageStatus.RUNNING
        stage.start_time = datetime.now()
        stage.error = None
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段开始执行")
        
        self._update_current_index(stage_id)
        self.updated_at = datetime.now()
        
        logger.info(f"Started stage: {stage_id}")
        return True
    
    def complete_stage(
        self,
        stage_id: str,
        result: Dict[str, Any] | None = None,
        code: str | None = None
    ) -> bool:
        """完成阶段
        
        Args:
            stage_id: 阶段ID
            result: 阶段结果
            code: 生成的代码
            
        Returns:
            是否成功完成
        """
        if stage_id not in self.stages:
            return False
        
        stage = self.stages[stage_id]
        stage.status = StageStatus.COMPLETED
        stage.end_time = datetime.now()
        stage.result = result
        stage.generated_code = code
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段执行完成")
        
        self.updated_at = datetime.now()
        
        logger.info(f"Completed stage: {stage_id}")
        return True
    
    def pause_stage(self, stage_id: str) -> bool:
        """暂停阶段（等待用户操作）
        
        Args:
            stage_id: 阶段ID
            
        Returns:
            是否成功暂停
        """
        if stage_id not in self.stages:
            return False
        
        stage = self.stages[stage_id]
        
        # 只能从 RUNNING 或 COMPLETED 状态暂停
        if stage.status not in [StageStatus.RUNNING, StageStatus.COMPLETED]:
            logger.warning(f"Cannot pause stage {stage_id} from status {stage.status}")
            return False
        
        stage.status = StageStatus.PAUSED
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段已暂停，等待用户操作")
        
        self.updated_at = datetime.now()
        
        logger.info(f"Paused stage: {stage_id}")
        return True
    
    def fail_stage(self, stage_id: str, error: str) -> bool:
        """阶段失败
        
        Args:
            stage_id: 阶段ID
            error: 错误信息
            
        Returns:
            是否成功标记失败
        """
        if stage_id not in self.stages:
            return False
        
        stage = self.stages[stage_id]
        stage.status = StageStatus.FAILED
        stage.end_time = datetime.now()
        stage.error = error
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段执行失败: {error}")
        
        self.updated_at = datetime.now()
        
        logger.error(f"Failed stage: {stage_id}, error: {error}")
        return True
    
    def skip_stage(self, stage_id: str) -> bool:
        """跳过阶段
        
        Args:
            stage_id: 阶段ID
            
        Returns:
            是否成功跳过
        """
        if stage_id not in self.stages:
            return False
        
        stage = self.stages[stage_id]
        
        # 只能从 PENDING 状态跳过
        if stage.status != StageStatus.PENDING:
            logger.warning(f"Cannot skip stage {stage_id} from status {stage.status}")
            return False
        
        stage.status = StageStatus.SKIPPED
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段已跳过")
        
        self.updated_at = datetime.now()
        
        logger.info(f"Skipped stage: {stage_id}")
        return True
    
    # =========================================================================
    # 重试与回滚
    # =========================================================================
    
    def retry_stage(
        self,
        stage_id: str,
        new_params: Dict[str, Any] | None = None
    ) -> bool:
        """重试阶段
        
        Args:
            stage_id: 阶段ID
            new_params: 新参数（可选，覆盖原参数）
            
        Returns:
            是否成功重置
        """
        if stage_id not in self.stages:
            return False
        
        stage = self.stages[stage_id]
        
        # 被重试的阶段一定是执行过的，记录重置日志
        stage.status = StageStatus.PENDING
        stage.start_time = None
        stage.end_time = None
        stage.result = None
        stage.error = None
        stage.generated_code = None
        
        if new_params:
            stage.parameters.update(new_params)
        
        stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段已重置，准备重试")
        
        # 清除后续阶段的结果
        self._clear_subsequent_stages(stage_id)
        
        self.updated_at = datetime.now()
        
        logger.info(f"Reset stage for retry: {stage_id}")
        return True
    
    def _clear_subsequent_stages(self, stage_id: str) -> None:
        """清除指定阶段之后所有阶段的结果
        
        2026-02-10: 修复逻辑 - 只对已执行过的阶段显示"阶段已重置"
        - 从未执行过的阶段（status=PENDING）不应显示重置信息
        """
        start_clearing = False
        
        for sid in self._stage_order:
            if sid == stage_id:
                start_clearing = True
                continue
            
            if start_clearing:
                stage = self.stages[sid]
                
                # 判断阶段是否曾经执行过（非PENDING状态或有结果）
                was_executed = (
                    stage.status != StageStatus.PENDING or
                    stage.result is not None or
                    stage.start_time is not None
                )
                
                # 重置阶段状态
                stage.status = StageStatus.PENDING
                stage.start_time = None
                stage.end_time = None
                stage.result = None
                stage.generated_code = None
                stage.error = None
                
                # 只有曾经执行过的阶段才记录"已重置"日志
                if was_executed:
                    stage.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 阶段已重置（前序阶段重试）")
    
    # =========================================================================
    # 参数管理
    # =========================================================================
    
    def update_params(self, stage_id: str, params: Dict[str, Any]) -> bool:
        """更新阶段参数
        
        Args:
            stage_id: 阶段ID
            params: 参数字典
            
        Returns:
            是否成功更新
        """
        if stage_id not in self.stages:
            return False
        
        self.stages[stage_id].parameters.update(params)
        self.stages[stage_id].logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] 参数已更新: {list(params.keys())}"
        )
        
        self.updated_at = datetime.now()
        
        logger.info(f"Updated params for stage {stage_id}: {list(params.keys())}")
        return True
    
    def get_params(self, stage_id: str) -> Dict[str, Any]:
        """获取阶段参数
        
        Args:
            stage_id: 阶段ID
            
        Returns:
            参数字典
        """
        if stage_id not in self.stages:
            return {}
        return self.stages[stage_id].parameters.copy()
    
    # =========================================================================
    # 导航方法
    # =========================================================================
    
    def get_current_stage(self) -> StageState | None:
        """获取当前阶段"""
        if self.current_stage_index < len(self._stage_order):
            stage_id = self._stage_order[self.current_stage_index]
            return self.stages.get(stage_id)
        return None
    
    def get_next_stage(self) -> StageState | None:
        """获取下一阶段"""
        next_index = self.current_stage_index + 1
        if next_index < len(self._stage_order):
            stage_id = self._stage_order[next_index]
            return self.stages.get(stage_id)
        return None
    
    def advance_to_next_stage(self) -> bool:
        """推进到下一阶段
        
        Returns:
            是否成功推进
        """
        if self.current_stage_index + 1 < len(self._stage_order):
            self.current_stage_index += 1
            self.updated_at = datetime.now()
            return True
        return False
    
    def _update_current_index(self, stage_id: str) -> None:
        """更新当前阶段索引"""
        try:
            self.current_stage_index = self._stage_order.index(stage_id)
        except ValueError:
            pass
    
    # =========================================================================
    # 序列化
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "interaction_mode": self.interaction_mode,
            "current_stage_index": self.current_stage_index,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "stages": [
                self.stages[stage_id].to_dict()
                for stage_id in self._stage_order
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageStateMachine":
        """从字典反序列化"""
        stages_data = data.get("stages", [])
        stages_init = [
            {"id": s["stage_id"], "name": s["stage_name"]}
            for s in stages_data
        ]
        
        machine = cls(
            session_id=data["session_id"],
            task_id=data["task_id"],
            stages=stages_init,
            interaction_mode=data.get("interaction_mode", "expert")
        )
        
        machine.current_stage_index = data.get("current_stage_index", 0)
        machine.created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        machine.updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        
        # 恢复阶段状态
        for stage_data in stages_data:
            stage_id = stage_data["stage_id"]
            if stage_id in machine.stages:
                machine.stages[stage_id] = StageState.from_dict(stage_data)
        
        return machine
    
    # =========================================================================
    # 状态查询
    # =========================================================================
    
    def is_completed(self) -> bool:
        """检查是否所有阶段都已完成"""
        return all(
            s.status in [StageStatus.COMPLETED, StageStatus.SKIPPED]
            for s in self.stages.values()
        )
    
    def has_failed(self) -> bool:
        """检查是否有阶段失败"""
        return any(s.status == StageStatus.FAILED for s in self.stages.values())
    
    def get_progress(self) -> float:
        """获取整体进度百分比"""
        if not self.stages:
            return 0.0
        
        completed_count = sum(
            1 for s in self.stages.values()
            if s.status in [StageStatus.COMPLETED, StageStatus.SKIPPED]
        )
        return (completed_count / len(self.stages)) * 100
