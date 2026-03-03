# -*- coding: utf-8 -*-
"""
Task Controller

提供任务的暂停、停止、恢复控制。
使用内存缓存 + 数据库持久化双层存储。
"""

import threading
import logging
from datetime import datetime
from typing import Dict, Optional
from .enums import TaskControlAction
from .database import get_task_manager_db
from .models import TaskControl

logger = logging.getLogger(__name__)


class TaskController:
    """任务控制器
    
    提供任务的暂停、停止、恢复控制。
    使用内存缓存 + 数据库持久化双层存储：
    - 内存缓存：快速响应控制请求检查
    - 数据库持久化：确保控制请求不丢失
    
    使用示例:
        # 请求暂停
        TaskController.request_pause("exec-123")
        
        # 在执行器中检查控制状态
        control = TaskController.check_control("exec-123")
        if control == TaskControlAction.PAUSE:
            # 处理暂停逻辑
            TaskController.mark_processed("exec-123")
    """
    
    # 内存缓存（快速响应）
    _control_cache: Dict[str, TaskControlAction] = {}
    _lock = threading.Lock()
    
    @classmethod
    def request_pause(cls, execution_id: str) -> bool:
        """请求暂停任务
        
        Args:
            execution_id: 执行ID
            
        Returns:
            是否成功发送请求
        """
        logger.info(f"Pause requested for execution: {execution_id}")
        return cls._set_control(execution_id, TaskControlAction.PAUSE)
    
    @classmethod
    def request_stop(cls, execution_id: str) -> bool:
        """请求停止任务
        
        Args:
            execution_id: 执行ID
            
        Returns:
            是否成功发送请求
        """
        logger.info(f"Stop requested for execution: {execution_id}")
        return cls._set_control(execution_id, TaskControlAction.STOP)
    
    @classmethod
    def request_resume(cls, execution_id: str) -> bool:
        """请求恢复任务
        
        Args:
            execution_id: 执行ID
            
        Returns:
            是否成功发送请求
        """
        logger.info(f"Resume requested for execution: {execution_id}")
        return cls._set_control(execution_id, TaskControlAction.RESUME)
    
    @classmethod
    def check_control(cls, execution_id: str) -> TaskControlAction:
        """检查控制状态（执行器在检查点调用）
        
        Args:
            execution_id: 执行ID
            
        Returns:
            当前控制动作
        """
        with cls._lock:
            # 优先从缓存读取
            if execution_id in cls._control_cache:
                return cls._control_cache[execution_id]
        
        # 回退到数据库
        return cls._get_control_from_db(execution_id)
    
    @classmethod
    def clear_control(cls, execution_id: str) -> None:
        """清除控制状态（任务完成后调用）
        
        Args:
            execution_id: 执行ID
        """
        with cls._lock:
            cls._control_cache.pop(execution_id, None)
        cls._delete_control_from_db(execution_id)
        logger.debug(f"Control cleared for execution: {execution_id}")
    
    @classmethod
    def mark_processed(cls, execution_id: str) -> None:
        """标记控制请求已处理
        
        Args:
            execution_id: 执行ID
        """
        with cls._lock:
            cls._control_cache[execution_id] = TaskControlAction.NONE
        cls._update_control_processed(execution_id)
        logger.debug(f"Control marked as processed for execution: {execution_id}")
    
    @classmethod
    def get_pending_controls(cls) -> Dict[str, TaskControlAction]:
        """获取所有待处理的控制请求
        
        Returns:
            执行ID到控制动作的映射
        """
        with cls._lock:
            return {
                k: v for k, v in cls._control_cache.items()
                if v != TaskControlAction.NONE
            }
    
    # =========== 私有方法 ===========
    
    @classmethod
    def _set_control(cls, execution_id: str, action: TaskControlAction) -> bool:
        """设置控制状态
        
        Args:
            execution_id: 执行ID
            action: 控制动作
            
        Returns:
            是否成功
        """
        with cls._lock:
            cls._control_cache[execution_id] = action
        return cls._save_control_to_db(execution_id, action)
    
    @classmethod
    def _save_control_to_db(cls, execution_id: str, action: TaskControlAction) -> bool:
        """保存控制状态到数据库
        
        Args:
            execution_id: 执行ID
            action: 控制动作
            
        Returns:
            是否成功
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                control = session.query(TaskControl).filter_by(
                    execution_id=execution_id
                ).first()
                
                if control:
                    control.action = action.value
                    control.requested_at = datetime.now()
                    control.processed_at = None
                else:
                    control = TaskControl(
                        execution_id=execution_id,
                        action=action.value
                    )
                    session.add(control)
            return True
        except Exception as e:
            logger.error(f"Failed to save control to DB: {e}")
            return False
    
    @classmethod
    def _get_control_from_db(cls, execution_id: str) -> TaskControlAction:
        """从数据库读取控制状态
        
        Args:
            execution_id: 执行ID
            
        Returns:
            控制动作
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                control = session.query(TaskControl).filter_by(
                    execution_id=execution_id
                ).first()
                
                if control and control.processed_at is None:
                    return TaskControlAction(control.action)
        except Exception as e:
            logger.error(f"Failed to get control from DB: {e}")
        
        return TaskControlAction.NONE
    
    @classmethod
    def _delete_control_from_db(cls, execution_id: str) -> None:
        """从数据库删除控制状态
        
        Args:
            execution_id: 执行ID
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                session.query(TaskControl).filter_by(
                    execution_id=execution_id
                ).delete()
        except Exception as e:
            logger.error(f"Failed to delete control from DB: {e}")
    
    @classmethod
    def _update_control_processed(cls, execution_id: str) -> None:
        """更新控制请求为已处理
        
        Args:
            execution_id: 执行ID
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                control = session.query(TaskControl).filter_by(
                    execution_id=execution_id
                ).first()
                
                if control:
                    control.processed_at = datetime.now()
        except Exception as e:
            logger.error(f"Failed to update control processed: {e}")
