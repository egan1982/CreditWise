# -*- coding: utf-8 -*-
"""
Persistent Execution Store - 执行状态持久化存储

提供执行状态的持久化存储，支持：
- 跨后端重启恢复任务执行
- 保存/加载执行检查点
- 阶段重试时恢复上一阶段输出
- 完整执行上下文的持久化和恢复
"""

import json
import os
import pickle
import shutil
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

from .database import get_task_manager_db
from .models import ExecutionState, ExecutionCheckpoint, StageAIAnalysis
from .enums import TaskStatus

logger = logging.getLogger(__name__)

# 默认状态文件存储目录
DEFAULT_STATE_DIR = "./execution_states"

# 状态文件保留天数（自动清理）
EXECUTION_STATE_RETENTION_DAYS = 3


class PersistentExecutionStore:
    """执行状态持久化存储
    
    提供执行状态的数据库持久化和文件存储：
    - ExecutionState: 保存执行上下文元数据
    - ExecutionCheckpoint: 保存每个阶段的检查点
    - 文件系统: 存储大型对象（DataFrame、模型等）
    """
    
    # 状态文件存储目录
    _state_dir: str = DEFAULT_STATE_DIR
    
    @classmethod
    def set_state_dir(cls, state_dir: str) -> None:
        """设置状态文件存储目录"""
        cls._state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        logger.info(f"PersistentExecutionStore state_dir set to: {state_dir}")
    
    @classmethod
    def get_state_dir(cls) -> str:
        """获取状态文件存储目录"""
        os.makedirs(cls._state_dir, exist_ok=True)
        return cls._state_dir
    
    # =========================================================================
    # ExecutionState CRUD
    # =========================================================================
    
    @classmethod
    def create(
        cls,
        execution_id: str,
        task_id: str,
        session_id: str,
        params: Dict[str, Any],
        interaction_mode: str = "auto",
        record_id: Optional[str] = None,
        data_file_path: Optional[str] = None,
    ) -> str:
        """创建执行状态记录
        
        Args:
            execution_id: 执行ID
            task_id: 任务类型ID
            session_id: 会话ID
            params: 任务参数
            interaction_mode: 交互模式 (auto/expert)
            record_id: 关联的 TaskRecord ID
            data_file_path: 输入数据文件路径
            
        Returns:
            execution_id
        """
        db = get_task_manager_db()
        
        with db.get_session() as session:
            state = ExecutionState(
                execution_id=execution_id,
                task_id=task_id,
                session_id=session_id,
                record_id=record_id,
                status=TaskStatus.PENDING.value,
                interaction_mode=interaction_mode,
                params_json=json.dumps(params, ensure_ascii=False) if params else None,
                data_file_path=data_file_path,
            )
            session.add(state)
            session.commit()
            
            logger.info(f"Created ExecutionState: {execution_id}")
            return execution_id
    
    @classmethod
    def get(cls, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态
        
        Args:
            execution_id: 执行ID
            
        Returns:
            执行状态字典，不存在返回 None
        """
        db = get_task_manager_db()
        
        with db.get_session() as session:
            state = session.query(ExecutionState).filter_by(
                execution_id=execution_id
            ).first()
            
            if not state:
                return None
            
            return cls._state_to_dict(state)
    
    @classmethod
    def update(
        cls,
        execution_id: str,
        status: Optional[str] = None,
        current_stage_id: Optional[str] = None,
        pause_stage_id: Optional[str] = None,
        state_file_path: Optional[str] = None,
    ) -> bool:
        """更新执行状态
        
        Args:
            execution_id: 执行ID
            status: 新状态
            current_stage_id: 当前阶段ID
            pause_stage_id: 暂停阶段ID
            state_file_path: 状态文件路径
            
        Returns:
            是否更新成功
        """
        db = get_task_manager_db()
        
        with db.get_session() as session:
            state = session.query(ExecutionState).filter_by(
                execution_id=execution_id
            ).first()
            
            if not state:
                logger.warning(f"ExecutionState not found: {execution_id}")
                return False
            
            if status is not None:
                state.status = status
                if status == TaskStatus.PAUSED.value:
                    state.paused_at = datetime.now()
            
            if current_stage_id is not None:
                state.current_stage_id = current_stage_id
            
            if pause_stage_id is not None:
                state.pause_stage_id = pause_stage_id
            
            if state_file_path is not None:
                state.state_file_path = state_file_path
            
            state.updated_at = datetime.now()
            session.commit()
            
            logger.debug(f"Updated ExecutionState: {execution_id}, status={status}")
            return True
    
    @classmethod
    def delete(cls, execution_id: str) -> bool:
        """删除执行状态及关联的检查点
        
        Args:
            execution_id: 执行ID
            
        Returns:
            是否删除成功
        """
        db = get_task_manager_db()
        
        with db.get_session() as session:
            # 删除检查点
            session.query(ExecutionCheckpoint).filter_by(
                execution_id=execution_id
            ).delete()
            
            # 删除状态
            result = session.query(ExecutionState).filter_by(
                execution_id=execution_id
            ).delete()
            
            session.commit()
            
            # 清理文件
            cls._cleanup_state_files(execution_id)
            
            logger.info(f"Deleted ExecutionState and checkpoints: {execution_id}")
            return result > 0
    
    @classmethod
    def list_active(cls) -> List[Dict[str, Any]]:
        """列出活跃的执行状态（非完成/失败）"""
        db = get_task_manager_db()
        
        with db.get_session() as session:
            states = session.query(ExecutionState).filter(
                ExecutionState.status.in_([
                    TaskStatus.PENDING.value,
                    TaskStatus.RUNNING.value,
                    TaskStatus.PAUSED.value,
                ])
            ).order_by(ExecutionState.created_at.desc()).all()
            
            return [cls._state_to_dict(s) for s in states]
    
    @classmethod
    def list_paused(cls, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出暂停中的执行状态
        
        Args:
            session_id: 可选，按会话筛选
        """
        db = get_task_manager_db()
        
        with db.get_session() as session:
            query = session.query(ExecutionState).filter_by(
                status=TaskStatus.PAUSED.value
            )
            
            if session_id:
                query = query.filter_by(session_id=session_id)
            
            states = query.order_by(ExecutionState.paused_at.desc()).all()
            return [cls._state_to_dict(s) for s in states]
    
    # =========================================================================
    # ExecutionCheckpoint CRUD
    # =========================================================================
    
    @classmethod
    def save_checkpoint(
        cls,
        execution_id: str,
        stage_id: str,
        stage_index: int,
        stage_status: str = "completed",
        outputs: Optional[Dict[str, Any]] = None,
        outputs_summary: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> str:
        """保存阶段检查点
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            stage_index: 阶段索引
            stage_status: 阶段状态
            outputs: 阶段输出（大型对象会存储到文件）
            outputs_summary: 输出摘要（存储到数据库）
            params: 阶段参数
            started_at: 开始时间
            completed_at: 完成时间
            
        Returns:
            检查点ID
        """
        db = get_task_manager_db()
        
        # 保存大型输出到文件
        outputs_file_path = None
        if outputs:
            outputs_file_path = cls._save_outputs_to_file(execution_id, stage_id, outputs)
        
        with db.get_session() as session:
            # 查找现有检查点
            checkpoint = session.query(ExecutionCheckpoint).filter_by(
                execution_id=execution_id,
                stage_id=stage_id
            ).first()
            
            if checkpoint:
                # 更新
                checkpoint.stage_status = stage_status
                checkpoint.outputs_summary = json.dumps(outputs_summary, ensure_ascii=False) if outputs_summary else None
                checkpoint.outputs_file_path = outputs_file_path
                checkpoint.params_json = json.dumps(params, ensure_ascii=False) if params else None
                checkpoint.started_at = started_at
                checkpoint.completed_at = completed_at
            else:
                # 新增
                checkpoint = ExecutionCheckpoint(
                    execution_id=execution_id,
                    stage_id=stage_id,
                    stage_index=stage_index,
                    stage_status=stage_status,
                    outputs_summary=json.dumps(outputs_summary, ensure_ascii=False) if outputs_summary else None,
                    outputs_file_path=outputs_file_path,
                    params_json=json.dumps(params, ensure_ascii=False) if params else None,
                    started_at=started_at,
                    completed_at=completed_at,
                )
                session.add(checkpoint)
            
            session.commit()
            
            logger.info(f"Saved checkpoint: {execution_id}/{stage_id}")
            return f"{execution_id}_{stage_id}"
    
    @classmethod
    def get_checkpoint(
        cls,
        execution_id: str,
        stage_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取阶段检查点
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            
        Returns:
            检查点字典，不存在返回 None
        """
        db = get_task_manager_db()
        
        with db.get_session() as session:
            checkpoint = session.query(ExecutionCheckpoint).filter_by(
                execution_id=execution_id,
                stage_id=stage_id
            ).first()
            
            if not checkpoint:
                return None
            
            return cls._checkpoint_to_dict(checkpoint)
    
    @classmethod
    def get_checkpoints(cls, execution_id: str) -> List[Dict[str, Any]]:
        """获取执行的所有检查点
        
        Args:
            execution_id: 执行ID
            
        Returns:
            检查点列表，按阶段索引排序
        """
        db = get_task_manager_db()
        
        with db.get_session() as session:
            checkpoints = session.query(ExecutionCheckpoint).filter_by(
                execution_id=execution_id
            ).order_by(ExecutionCheckpoint.stage_index).all()
            
            return [cls._checkpoint_to_dict(cp) for cp in checkpoints]
    
    @classmethod
    def load_checkpoint_outputs(
        cls,
        execution_id: str,
        stage_id: str
    ) -> Optional[Dict[str, Any]]:
        """加载检查点的完整输出
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            
        Returns:
            输出字典，不存在返回 None
        """
        logger.warning(f"[RETRY-DEBUG] ========== Loading checkpoint outputs for {stage_id} ==========")
        checkpoint = cls.get_checkpoint(execution_id, stage_id)
        if not checkpoint:
            logger.warning(f"[RETRY-DEBUG] No checkpoint found for {stage_id}")
            return None
        
        outputs_file_path = checkpoint.get("outputs_file_path")
        logger.warning(f"[RETRY-DEBUG] outputs_file_path: {outputs_file_path}")
        if not outputs_file_path or not os.path.exists(outputs_file_path):
            logger.warning(f"[RETRY-DEBUG] outputs_file_path not exists or empty")
            return None
        
        outputs = cls._load_outputs_from_file(outputs_file_path)
        if outputs:
            logger.warning(f"[RETRY-DEBUG] Loaded outputs keys: {list(outputs.keys())}")
            if "df_processed" in outputs:
                df_val = outputs.get("df_processed")
                logger.warning(f"[RETRY-DEBUG] df_processed is None: {df_val is None}, type: {type(df_val)}")
                if df_val is not None and hasattr(df_val, 'shape'):
                    logger.warning(f"[RETRY-DEBUG] df_processed shape: {df_val.shape}")
        else:
            logger.warning(f"[RETRY-DEBUG] Failed to load outputs from file")
        logger.warning(f"[RETRY-DEBUG] ========== End loading checkpoint for {stage_id} ==========")
        return outputs
    
    @classmethod
    def reset_checkpoint(
        cls,
        execution_id: str,
        stage_id: str
    ) -> bool:
        """重置阶段检查点（用于阶段重试）
        
        将指定阶段的状态重置为 pending，并清除输出文件。
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            
        Returns:
            是否成功
        """
        db = get_task_manager_db()
        
        with db.get_session() as session:
            checkpoint = session.query(ExecutionCheckpoint).filter_by(
                execution_id=execution_id,
                stage_id=stage_id
            ).first()
            
            if not checkpoint:
                logger.warning(f"Checkpoint not found: {execution_id}/{stage_id}")
                return False
            
            # 清除输出文件
            if checkpoint.outputs_file_path and os.path.exists(checkpoint.outputs_file_path):
                try:
                    os.remove(checkpoint.outputs_file_path)
                except Exception as e:
                    logger.warning(f"Failed to remove outputs file: {e}")
            
            # 重置状态
            checkpoint.stage_status = "pending"
            checkpoint.outputs_summary = None
            checkpoint.outputs_file_path = None
            checkpoint.started_at = None
            checkpoint.completed_at = None
            
            session.commit()
            
            logger.info(f"Reset checkpoint: {execution_id}/{stage_id}")
            return True
    
    @classmethod
    def invalidate_checkpoints_from(
        cls,
        execution_id: str,
        stage_id: str
    ) -> int:
        """使指定阶段及之后的检查点失效
        
        用于阶段重试时，清除该阶段及后续阶段的检查点。
        
        Args:
            execution_id: 执行ID
            stage_id: 起始阶段ID
            
        Returns:
            失效的检查点数量
        """
        db = get_task_manager_db()
        
        with db.get_session() as session:
            # 获取起始阶段的索引
            start_checkpoint = session.query(ExecutionCheckpoint).filter_by(
                execution_id=execution_id,
                stage_id=stage_id
            ).first()
            
            if not start_checkpoint:
                logger.warning(f"Start checkpoint not found: {execution_id}/{stage_id}")
                return 0
            
            start_index = start_checkpoint.stage_index
            
            # 获取需要失效的检查点
            checkpoints = session.query(ExecutionCheckpoint).filter(
                ExecutionCheckpoint.execution_id == execution_id,
                ExecutionCheckpoint.stage_index >= start_index
            ).all()
            
            count = 0
            for cp in checkpoints:
                # 清除输出文件
                if cp.outputs_file_path and os.path.exists(cp.outputs_file_path):
                    try:
                        os.remove(cp.outputs_file_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove outputs file: {e}")
                
                # 重置状态
                cp.stage_status = "pending"
                cp.outputs_summary = None
                cp.outputs_file_path = None
                cp.started_at = None
                cp.completed_at = None
                count += 1
            
            # Phase 7: 清除从重试阶段开始的所有AI分析结果
            # 这样阶段重试后，AI评估结果会重新生成，而不是使用旧的缓存
            stage_ids = [cp.stage_id for cp in checkpoints]
            ai_analysis_count = session.query(StageAIAnalysis).filter(
                StageAIAnalysis.record_id == execution_id,
                StageAIAnalysis.stage_id.in_(stage_ids)
            ).delete(synchronize_session=False)
            
            if ai_analysis_count > 0:
                logger.info(f"Invalidated {ai_analysis_count} AI analysis results from {execution_id}/{stage_id}")
            
            session.commit()
            
            logger.info(f"Invalidated {count} checkpoints from {execution_id}/{stage_id}")
            return count
    
    # =========================================================================
    # 文件存储
    # =========================================================================
    
    @classmethod
    def _save_outputs_to_file(
        cls,
        execution_id: str,
        stage_id: str,
        outputs: Dict[str, Any]
    ) -> str:
        """保存输出到文件
        
        Args:
            execution_id: 执行ID
            stage_id: 阶段ID
            outputs: 输出字典
            
        Returns:
            文件路径
        """
        state_dir = cls.get_state_dir()
        exec_dir = os.path.join(state_dir, execution_id)
        os.makedirs(exec_dir, exist_ok=True)
        
        file_path = os.path.join(exec_dir, f"{stage_id}_outputs.pkl")
        
        with open(file_path, "wb") as f:
            pickle.dump(outputs, f)
        
        logger.debug(f"Saved outputs to: {file_path}")
        return file_path
    
    @classmethod
    def _load_outputs_from_file(cls, file_path: str) -> Optional[Dict[str, Any]]:
        """从文件加载输出
        
        Args:
            file_path: 文件路径
            
        Returns:
            输出字典
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load outputs from {file_path}: {e}")
            return None
    
    @classmethod
    def _cleanup_state_files(cls, execution_id: str) -> None:
        """清理执行状态相关的文件
        
        Args:
            execution_id: 执行ID
        """
        state_dir = cls.get_state_dir()
        exec_dir = os.path.join(state_dir, execution_id)
        
        if os.path.exists(exec_dir):
            import shutil
            try:
                shutil.rmtree(exec_dir)
                logger.info(f"Cleaned up state files: {exec_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup state files: {e}")
    
    # =========================================================================
    # 辅助方法
    # =========================================================================
    
    @classmethod
    def _state_to_dict(cls, state: ExecutionState) -> Dict[str, Any]:
        """将 ExecutionState 转换为字典"""
        return {
            "execution_id": state.execution_id,
            "task_id": state.task_id,
            "session_id": state.session_id,
            "record_id": state.record_id,
            "status": state.status,
            "current_stage_id": state.current_stage_id,
            "pause_stage_id": state.pause_stage_id,
            "interaction_mode": state.interaction_mode,
            "params": json.loads(state.params_json) if state.params_json else None,
            "data_file_path": state.data_file_path,
            "state_file_path": state.state_file_path,
            "created_at": state.created_at.isoformat() if state.created_at else None,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
            "paused_at": state.paused_at.isoformat() if state.paused_at else None,
        }
    
    @classmethod
    def _checkpoint_to_dict(cls, checkpoint: ExecutionCheckpoint) -> Dict[str, Any]:
        """将 ExecutionCheckpoint 转换为字典"""
        return {
            "execution_id": checkpoint.execution_id,
            "stage_id": checkpoint.stage_id,
            "stage_index": checkpoint.stage_index,
            "stage_status": checkpoint.stage_status,
            "outputs_summary": json.loads(checkpoint.outputs_summary) if checkpoint.outputs_summary else None,
            "outputs_file_path": checkpoint.outputs_file_path,
            "params": json.loads(checkpoint.params_json) if checkpoint.params_json else None,
            "started_at": checkpoint.started_at.isoformat() if checkpoint.started_at else None,
            "completed_at": checkpoint.completed_at.isoformat() if checkpoint.completed_at else None,
            "created_at": checkpoint.created_at.isoformat() if checkpoint.created_at else None,
        }
    
    # =========================================================================
    # Phase 6: 完整状态持久化（新增）
    # =========================================================================
    
    @classmethod
    def save_full_state(cls, execution_id: str, context: Any) -> str:
        """保存完整执行状态到文件
        
        在任务暂停时调用，将完整的 ExecutionContext 序列化到文件系统。
        用于跨后端重启恢复任务。
        
        Args:
            execution_id: 执行ID
            context: 执行上下文对象 (ExecutionContext)
            
        Returns:
            状态文件路径
        """
        state_dir = cls.get_state_dir()
        exec_dir = os.path.join(state_dir, execution_id)
        os.makedirs(exec_dir, exist_ok=True)
        
        state_file = os.path.join(exec_dir, "context.pkl")
        
        try:
            with open(state_file, "wb") as f:
                pickle.dump(context, f)
            
            # 更新数据库中的状态文件路径
            cls.update(execution_id=execution_id, state_file_path=state_file)
            
            logger.info(f"Saved full state: {execution_id} -> {state_file}")
            return state_file
        except Exception as e:
            logger.error(f"Failed to save full state for {execution_id}: {e}")
            raise
    
    @classmethod
    def load_full_state(cls, execution_id: str) -> Optional[Any]:
        """从文件加载完整执行状态
        
        Args:
            execution_id: 执行ID
            
        Returns:
            执行上下文对象，不存在或加载失败返回 None
        """
        state_dir = cls.get_state_dir()
        state_file = os.path.join(state_dir, execution_id, "context.pkl")
        
        if not os.path.exists(state_file):
            # 尝试从数据库获取路径
            state = cls.get(execution_id)
            if state and state.get("state_file_path"):
                state_file = state["state_file_path"]
        
        if not os.path.exists(state_file):
            logger.warning(f"State file not found: {state_file}")
            return None
        
        try:
            with open(state_file, "rb") as f:
                context = pickle.load(f)
            logger.info(f"Loaded full state: {execution_id}")
            return context
        except Exception as e:
            logger.error(f"Failed to load full state for {execution_id}: {e}")
            return None
    
    @classmethod
    def mark_paused(
        cls,
        execution_id: str,
        pause_stage_id: str,
        pause_reason: str = "专家模式暂停",
        context: Any = None,
    ) -> bool:
        """标记任务为暂停状态
        
        同时保存完整状态到文件，支持跨重启恢复。
        
        Args:
            execution_id: 执行ID
            pause_stage_id: 暂停时的阶段ID
            pause_reason: 暂停原因
            context: 执行上下文（如果提供，会保存到文件）
            
        Returns:
            是否成功
        """
        # 1. 保存完整状态到文件
        if context:
            try:
                cls.save_full_state(execution_id, context)
            except Exception as e:
                logger.warning(f"Failed to save full state during pause: {e}")
        
        # 2. 更新数据库状态
        return cls.update(
            execution_id=execution_id,
            status=TaskStatus.PAUSED.value,
            pause_stage_id=pause_stage_id,
        )
    
    @classmethod
    def initialize(cls, state_dir: str = DEFAULT_STATE_DIR) -> None:
        """初始化持久化存储
        
        在应用启动时调用，执行：
        1. 设置状态文件目录
        2. 恢复暂停中的任务到内存
        3. 将运行中的任务标记为中断
        4. 清理过期的状态文件
        
        Args:
            state_dir: 状态文件存储目录
        """
        cls.set_state_dir(state_dir)
        logger.info(f"[PersistentStore] Initializing with state_dir: {state_dir}")
        
        # 恢复活跃的执行状态
        cls._restore_active_executions()
        
        # 清理过期状态文件
        cls.cleanup_expired_states()
    
    @classmethod
    def _restore_active_executions(cls) -> int:
        """恢复活跃的执行状态
        
        在应用启动时调用：
        1. 将运行中的任务标记为中断（后端重启导致）
        2. 记录可恢复的暂停任务
        
        Returns:
            恢复的任务数量
        """
        logger.info("[PersistentStore] Restoring active executions...")
        
        db = get_task_manager_db()
        restored_count = 0
        
        with db.get_session() as session:
            # 将运行中的任务标记为中断
            running_states = session.query(ExecutionState).filter(
                ExecutionState.status == TaskStatus.RUNNING.value
            ).all()
            
            for state in running_states:
                state.status = TaskStatus.PAUSED.value
                state.pause_stage_id = state.current_stage_id
                state.paused_at = datetime.now()
                logger.warning(
                    f"[PersistentStore] Marked interrupted: {state.execution_id} "
                    f"(was running stage: {state.current_stage_id})"
                )
            
            # 统计暂停中的任务
            paused_states = session.query(ExecutionState).filter(
                ExecutionState.status == TaskStatus.PAUSED.value
            ).all()
            
            for state in paused_states:
                # 检查是否有状态文件
                state_file = os.path.join(cls.get_state_dir(), state.execution_id, "context.pkl")
                has_state_file = os.path.exists(state_file)
                
                if has_state_file:
                    restored_count += 1
                    logger.info(
                        f"[PersistentStore] Recoverable: {state.execution_id} "
                        f"(paused at stage: {state.pause_stage_id})"
                    )
                else:
                    logger.warning(
                        f"[PersistentStore] Paused but no state file: {state.execution_id}"
                    )
            
            session.commit()
        
        logger.info(f"[PersistentStore] Restored {restored_count} recoverable executions")
        return restored_count
    
    @classmethod
    def cleanup_expired_states(cls, retention_days: int = EXECUTION_STATE_RETENTION_DAYS) -> int:
        """清理过期的状态文件
        
        删除超过保留期限的状态文件和数据库记录。
        
        Args:
            retention_days: 保留天数（默认3天）
            
        Returns:
            清理的执行数量
        """
        logger.info(f"[PersistentStore] Cleaning up states older than {retention_days} days...")
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cleaned_count = 0
        
        db = get_task_manager_db()
        
        with db.get_session() as session:
            # 查找已完成/失败且超过保留期限的执行
            expired_states = session.query(ExecutionState).filter(
                ExecutionState.status.in_([
                    TaskStatus.COMPLETED.value,
                    TaskStatus.FAILED.value,
                    TaskStatus.STOPPED.value,
                ]),
                ExecutionState.updated_at < cutoff_date
            ).all()
            
            for state in expired_states:
                execution_id = state.execution_id
                
                # 删除检查点记录
                session.query(ExecutionCheckpoint).filter_by(
                    execution_id=execution_id
                ).delete()
                
                # 删除状态记录
                session.delete(state)
                
                # 清理文件
                cls._cleanup_state_files(execution_id)
                
                cleaned_count += 1
                logger.debug(f"[PersistentStore] Cleaned up: {execution_id}")
            
            session.commit()
        
        if cleaned_count > 0:
            logger.info(f"[PersistentStore] Cleaned up {cleaned_count} expired executions")
        
        return cleaned_count
    
    @classmethod
    def get_cached_state_for_retry(
        cls,
        execution_id: str,
        retry_stage_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取阶段重试所需的缓存状态
        
        加载重试阶段之前所有已完成阶段的输出，用于跳过已完成阶段。
        
        Args:
            execution_id: 执行ID
            retry_stage_id: 要重试的阶段ID
            
        Returns:
            {
                "df_processed": DataFrame,  # 处理后的数据
                "results": dict,            # 累积的结果
                "stage_outputs": dict,      # 各阶段输出
                "last_completed_stage": str # 最后完成的阶段ID
            }
            如果无法获取，返回 None
        """
        # 获取所有检查点
        checkpoints = cls.get_checkpoints(execution_id)
        if not checkpoints:
            return None
        
        # 找到重试阶段的索引
        retry_stage_index = None
        for cp in checkpoints:
            if cp["stage_id"] == retry_stage_id:
                retry_stage_index = cp["stage_index"]
                break
        
        # 如果找不到retry_stage的检查点（因为该阶段还没执行），
        # 则使用最后一个已完成阶段的stage_index + 1作为retry_stage的索引
        # 这样可以加载所有已完成的阶段
        if retry_stage_index is None:
            # 找到所有已完成的检查点中最大的stage_index
            max_completed_index = -1
            for cp in checkpoints:
                if cp["stage_status"] == "completed" and cp["stage_index"] > max_completed_index:
                    max_completed_index = cp["stage_index"]
            
            if max_completed_index >= 0:
                retry_stage_index = max_completed_index + 1
                logger.info(f"Retry stage {retry_stage_id} not found in checkpoints, using index {retry_stage_index} (last completed index + 1)")
            else:
                logger.warning(f"No completed checkpoints found, cannot load cached state")
                return None
        
        # 加载重试阶段之前的所有已完成阶段输出
        cached_state: Dict[str, Any] = {
            "stage_outputs": {},
            "results": {},
            "df_processed": None,
            "last_completed_stage": None,
            # 规则挖掘任务特有字段
            "feature_cols": None,
            "feature_cols_for_rules": None,
            "full_tree": None,
            "full_tree_features": None,
            "rule_source_stats": None,  # 组合树模式的规则来源统计
            # 评分卡任务特有字段
            "train_df": None,
            "test_df": None,
            "oot_df": None,
            "df_woe": None,
            "bins": None,
            "iv_table": None,
            "selected_features": None,
            # WOE分箱后的特征列表（用于特征选择阶段）
            "woe_cols_for_selection": None,
            "model": None,
            "woe_feature_cols": None,
            "scorecard": None,
            # Phase 24: 评分卡任务评估数据（供report_generation使用）
            "y_train": None,
            "y_train_pred_proba": None,
            "y_test": None,
            "y_pred_proba": None,
            "y_oot": None,
            "y_oot_pred_proba": None,
        }
        
        for cp in checkpoints:
            if cp["stage_index"] >= retry_stage_index:
                break  # 只加载重试阶段之前的
            
            if cp["stage_status"] != "completed":
                continue
            
            stage_id = cp["stage_id"]
            outputs = cls.load_checkpoint_outputs(execution_id, stage_id)
            
            if outputs:
                cached_state["stage_outputs"][stage_id] = outputs
                cached_state["last_completed_stage"] = stage_id
                
                # 提取关键数据（规则挖掘任务）
                if "df_processed" in outputs:
                    cached_state["df_processed"] = outputs["df_processed"]
                if "results" in outputs:
                    cached_state["results"].update(outputs["results"])
                if "feature_cols" in outputs:
                    cached_state["feature_cols"] = outputs["feature_cols"]
                # 规则生成阶段使用的特征列表（已排除数据泄露特征）
                if "feature_cols_for_rules" in outputs:
                    cached_state["feature_cols_for_rules"] = outputs["feature_cols_for_rules"]
                # 决策树用于可视化（Full Tree 模式）
                if "full_tree" in outputs:
                    cached_state["full_tree"] = outputs["full_tree"]
                if "full_tree_features" in outputs:
                    cached_state["full_tree_features"] = outputs["full_tree_features"]
                # 规则来源统计（组合树模式）
                if "rule_source_stats" in outputs:
                    cached_state["rule_source_stats"] = outputs["rule_source_stats"]
                
                # 提取关键数据（评分卡任务）
                if "train_df" in outputs:
                    cached_state["train_df"] = outputs["train_df"]
                if "test_df" in outputs:
                    cached_state["test_df"] = outputs["test_df"]
                if "oot_df" in outputs:
                    cached_state["oot_df"] = outputs["oot_df"]
                if "df_woe" in outputs:
                    cached_state["df_woe"] = outputs["df_woe"]
                if "bins" in outputs:
                    cached_state["bins"] = outputs["bins"]
                if "iv_table" in outputs:
                    cached_state["iv_table"] = outputs["iv_table"]
                if "selected_features" in outputs:
                    cached_state["selected_features"] = outputs["selected_features"]
                # WOE分箱后的特征列表（用于特征选择阶段）
                if "woe_cols_for_selection" in outputs:
                    cached_state["woe_cols_for_selection"] = outputs["woe_cols_for_selection"]
                if "model" in outputs:
                    cached_state["model"] = outputs["model"]
                if "woe_feature_cols" in outputs:
                    cached_state["woe_feature_cols"] = outputs["woe_feature_cols"]
                if "scorecard" in outputs:
                    cached_state["scorecard"] = outputs["scorecard"]
                
                # Phase 24: 提取评估数据（评分卡任务）
                if "y_train" in outputs:
                    cached_state["y_train"] = outputs["y_train"]
                if "y_train_pred_proba" in outputs:
                    cached_state["y_train_pred_proba"] = outputs["y_train_pred_proba"]
                if "y_test" in outputs:
                    cached_state["y_test"] = outputs["y_test"]
                if "y_pred_proba" in outputs:
                    cached_state["y_pred_proba"] = outputs["y_pred_proba"]
                if "y_oot" in outputs:
                    cached_state["y_oot"] = outputs["y_oot"]
                if "y_oot_pred_proba" in outputs:
                    cached_state["y_oot_pred_proba"] = outputs["y_oot_pred_proba"]
        
        if not cached_state["stage_outputs"]:
            logger.warning(f"No cached outputs found before stage: {retry_stage_id}")
            return None
        
        logger.info(
            f"Loaded cached state for retry: {len(cached_state['stage_outputs'])} stages, "
            f"last completed: {cached_state['last_completed_stage']}"
        )
        return cached_state
