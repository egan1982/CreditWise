# -*- coding: utf-8 -*-
"""
Checkpoint Mechanism

为执行器提供检查点功能，支持在阶段之间检查控制状态。
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from .controller import TaskController
from .enums import TaskControlAction, TaskStatus
from .history_service import TaskHistoryService

logger = logging.getLogger(__name__)


class TaskPausedException(Exception):
    """任务暂停异常"""
    pass


class TaskStoppedException(Exception):
    """任务停止异常"""
    pass


class CheckpointMixin:
    """检查点混入类
    
    为执行器提供检查点功能，支持在阶段之间检查控制状态。
    
    使用示例:
        class MyExecutor(CheckpointMixin):
            async def execute(self, context):
                for stage in stages:
                    # 检查控制点
                    should_continue = await self.check_control_point(
                        execution_id=context.execution_id,
                        record_id=context.record_id,
                        stage_id=stage.id
                    )
                    if not should_continue:
                        return  # 任务已停止
                    
                    # 执行阶段
                    await self.execute_stage(stage)
    """
    
    async def check_control_point(
        self,
        execution_id: str,
        record_id: str,
        stage_id: str,
        save_state_callback: Optional[Callable[[], Dict[str, Any]]] = None
    ) -> bool:
        """检查控制点
        
        在每个阶段开始前调用，检查是否需要暂停或停止。
        
        Args:
            execution_id: 执行ID
            record_id: 记录ID
            stage_id: 当前阶段ID
            save_state_callback: 保存状态的回调函数
            
        Returns:
            True: 继续执行
            False: 任务已停止
        """
        control = TaskController.check_control(execution_id)
        
        if control == TaskControlAction.STOP:
            logger.info(f"Task {execution_id} stop requested at stage {stage_id}")
            
            # 更新状态为已停止
            TaskHistoryService.update_status(
                record_id=record_id,
                status=TaskStatus.STOPPED,
                message=f"用户在阶段 {stage_id} 停止了任务"
            )
            
            # 清除控制状态
            TaskController.clear_control(execution_id)
            
            return False
        
        if control == TaskControlAction.PAUSE:
            logger.info(f"Task {execution_id} pause requested at stage {stage_id}")
            
            # 保存当前状态
            if save_state_callback:
                try:
                    state = save_state_callback()
                    logger.debug(f"Saved state at stage {stage_id}: {list(state.keys())}")
                except Exception as e:
                    logger.warning(f"Failed to save state: {e}")
            
            # 更新状态为已暂停
            TaskHistoryService.update_status(
                record_id=record_id,
                status=TaskStatus.PAUSED,
                message=f"任务在阶段 {stage_id} 暂停"
            )
            
            # 标记控制请求已处理
            TaskController.mark_processed(execution_id)
            
            # 等待恢复
            await self._wait_for_resume(execution_id, record_id, stage_id)
            
            return True
        
        return True
    
    async def _wait_for_resume(
        self,
        execution_id: str,
        record_id: str,
        stage_id: str,
        check_interval: float = 1.0,
        timeout: float = 3600.0  # 1小时超时
    ) -> None:
        """等待恢复
        
        Args:
            execution_id: 执行ID
            record_id: 记录ID
            stage_id: 当前阶段ID
            check_interval: 检查间隔（秒）
            timeout: 超时时间（秒）
            
        Raises:
            TaskStoppedException: 任务在暂停期间被停止
        """
        elapsed = 0.0
        
        logger.info(f"Task {execution_id} waiting for resume at stage {stage_id}")
        
        while elapsed < timeout:
            control = TaskController.check_control(execution_id)
            
            if control == TaskControlAction.RESUME:
                logger.info(f"Task {execution_id} resumed at stage {stage_id}")
                
                # 更新状态为运行中
                TaskHistoryService.update_status(
                    record_id=record_id,
                    status=TaskStatus.RUNNING,
                    message=f"任务已恢复，继续执行阶段 {stage_id}"
                )
                
                # 清除控制状态
                TaskController.mark_processed(execution_id)
                return
            
            if control == TaskControlAction.STOP:
                logger.info(f"Task {execution_id} stopped while paused at stage {stage_id}")
                
                # 更新状态为已停止
                TaskHistoryService.update_status(
                    record_id=record_id,
                    status=TaskStatus.STOPPED,
                    message=f"任务在暂停期间被停止"
                )
                
                # 清除控制状态
                TaskController.clear_control(execution_id)
                
                raise TaskStoppedException("Task stopped while paused")
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        # 超时，自动恢复
        logger.warning(f"Task {execution_id} pause timeout at stage {stage_id}, auto-resuming")
        TaskHistoryService.update_status(
            record_id=record_id,
            status=TaskStatus.RUNNING,
            message=f"暂停超时，自动恢复执行阶段 {stage_id}"
        )
    
    def check_control_point_sync(
        self,
        execution_id: str,
        record_id: str,
        stage_id: str
    ) -> bool:
        """同步版本的控制点检查（仅检查停止请求）
        
        适用于不支持异步的场景，只检查停止请求。
        暂停请求需要使用异步版本。
        
        Args:
            execution_id: 执行ID
            record_id: 记录ID
            stage_id: 当前阶段ID
            
        Returns:
            True: 继续执行
            False: 任务已停止
        """
        control = TaskController.check_control(execution_id)
        
        if control == TaskControlAction.STOP:
            logger.info(f"Task {execution_id} stop requested at stage {stage_id}")
            
            # 更新状态为已停止
            TaskHistoryService.update_status(
                record_id=record_id,
                status=TaskStatus.STOPPED,
                message=f"用户在阶段 {stage_id} 停止了任务"
            )
            
            # 清除控制状态
            TaskController.clear_control(execution_id)
            
            return False
        
        if control == TaskControlAction.PAUSE:
            logger.warning(
                f"Pause requested for {execution_id} at stage {stage_id}, "
                "but sync mode doesn't support pause. Ignoring."
            )
        
        return True
