# -*- coding: utf-8 -*-
"""
Task History Service

提供任务历史记录的创建、更新、查询功能。
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, and_, func
from .database import get_task_manager_db
from .models import TaskRecord, StageAIAnalysis
from .enums import TaskStatus, TaskCategory, InteractionMode

logger = logging.getLogger(__name__)


class TaskHistoryService:
    """任务历史查询服务
    
    提供任务历史记录的完整生命周期管理：
    - 创建记录：任务开始时创建
    - 更新状态：执行过程中更新进度、阶段
    - 更新结果：任务完成时保存结果摘要
    - 查询记录：多条件筛选、分页
    - 统计信息：成功率、平均耗时等
    
    使用示例:
        # 创建记录
        record_id = TaskHistoryService.create_record(
            task_type="scorecard_dev",
            execution_id="exec-123",
            session_id="session-456",
            params={"target_col": "label"}
        )
        
        # 更新状态
        TaskHistoryService.update_status(
            record_id=record_id,
            status=TaskStatus.RUNNING,
            progress=50.0,
            current_stage="woe_binning"
        )
        
        # 查询历史
        records = TaskHistoryService.list_records(
            task_type="scorecard_dev",
            status="completed",
            limit=10
        )
    """
    
    @classmethod
    def create_record(
        cls,
        task_type: str,
        execution_id: str,
        session_id: str,
        params: Dict[str, Any],
        task_category: str = "sop",
        interaction_mode: str = "auto",
        inputs_summary: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建任务记录
        
        Args:
            task_type: 任务类型（rule_mining, scorecard_dev等）
            execution_id: 执行ID
            session_id: 会话ID
            params: 任务参数
            task_category: 任务类别
            interaction_mode: 交互模式
            inputs_summary: 输入数据摘要
            
        Returns:
            记录ID
        """
        record_id = f"rec-{uuid.uuid4().hex[:12]}"
        
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                record = TaskRecord(
                    record_id=record_id,
                    task_type=task_type,
                    task_category=task_category,
                    execution_id=execution_id,
                    session_id=session_id,
                    interaction_mode=interaction_mode,
                    status=TaskStatus.PENDING.value,
                    params_json=json.dumps(params, ensure_ascii=False, default=str),
                    inputs_summary=json.dumps(inputs_summary, ensure_ascii=False, default=str) if inputs_summary else None
                )
                session.add(record)
            
            logger.info(f"Created task record: {record_id} for task_type: {task_type}")
            return record_id
            
        except Exception as e:
            logger.error(f"Failed to create task record: {e}")
            raise
    
    @classmethod
    def update_status(
        cls,
        record_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
        current_stage: Optional[str] = None,
        message: Optional[str] = None,
        stages: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新任务状态
        
        Args:
            record_id: 记录ID
            status: 新状态
            progress: 进度（0-100）
            current_stage: 当前阶段
            message: 状态消息
            stages: 阶段进度详情
            
        Returns:
            是否成功
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                record = session.query(TaskRecord).filter_by(
                    record_id=record_id
                ).first()
                
                if not record:
                    logger.warning(f"Task record not found: {record_id}")
                    return False
                
                record.status = status.value
                record.updated_at = datetime.now()
                
                if progress is not None:
                    record.progress = progress
                if current_stage is not None:
                    record.current_stage = current_stage
                if message is not None:
                    record.message = message
                if stages is not None:
                    record.stages_json = json.dumps(stages, ensure_ascii=False, default=str)
                
                # 更新时间戳 - 使用本地时间
                if status == TaskStatus.RUNNING and record.started_at is None:
                    record.started_at = datetime.now()
                elif status == TaskStatus.PAUSED:
                    record.paused_at = datetime.now()
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.STOPPED):
                    record.completed_at = datetime.now()
                    if record.started_at:
                        # 确保started_at是datetime类型（SQLite可能返回字符串）
                        started = record.started_at
                        if isinstance(started, str):
                            from datetime import datetime as dt
                            started = dt.fromisoformat(started.replace('Z', '+00:00'))
                        record.duration_seconds = (
                            record.completed_at - started
                        ).total_seconds()
            
            logger.debug(f"Updated task record: {record_id} to status: {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return False
    
    @classmethod
    def update_result(
        cls,
        record_id: str,
        outputs_summary: Dict[str, Any],
        result_file_path: Optional[str] = None
    ) -> bool:
        """更新任务结果
        
        Args:
            record_id: 记录ID
            outputs_summary: 输出结果摘要
            result_file_path: 完整结果文件路径
            
        Returns:
            是否成功
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                record = session.query(TaskRecord).filter_by(
                    record_id=record_id
                ).first()
                
                if not record:
                    logger.warning(f"Task record not found: {record_id}")
                    return False
                
                record.outputs_summary = json.dumps(
                    outputs_summary, ensure_ascii=False, default=str
                )
                if result_file_path:
                    record.result_file_path = result_file_path
                record.updated_at = datetime.now()
            
            logger.debug(f"Updated task result: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task result: {e}")
            return False
    
    @classmethod
    def update_error(
        cls,
        record_id: str,
        error_message: str,
        error_traceback: Optional[str] = None
    ) -> bool:
        """更新错误信息
        
        Args:
            record_id: 记录ID
            error_message: 错误消息
            error_traceback: 错误堆栈
            
        Returns:
            是否成功
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                record = session.query(TaskRecord).filter_by(
                    record_id=record_id
                ).first()
                
                if not record:
                    logger.warning(f"Task record not found: {record_id}")
                    return False
                
                record.status = TaskStatus.FAILED.value
                record.error_message = error_message
                record.error_traceback = error_traceback
                record.completed_at = datetime.now()
                record.updated_at = datetime.now()
                
                if record.started_at:
                    # 确保started_at是datetime类型（SQLite可能返回字符串）
                    started = record.started_at
                    if isinstance(started, str):
                        from datetime import datetime as dt
                        started = dt.fromisoformat(started.replace('Z', '+00:00'))
                    record.duration_seconds = (
                        record.completed_at - started
                    ).total_seconds()
            
            logger.info(f"Updated task error: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task error: {e}")
            return False
    
    @classmethod
    def get_record(cls, record_id: str) -> Optional[Dict[str, Any]]:
        """获取单条记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录字典，不存在返回None
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                record = session.query(TaskRecord).filter_by(
                    record_id=record_id
                ).first()
                
                if not record:
                    return None
                return cls._record_to_dict(record)
                
        except Exception as e:
            logger.error(f"Failed to get task record: {e}")
            return None
    
    @classmethod
    def get_record_by_execution_id(cls, execution_id: str) -> Optional[Dict[str, Any]]:
        """通过execution_id获取记录
        
        Args:
            execution_id: 执行ID
            
        Returns:
            记录字典，不存在返回None
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                record = session.query(TaskRecord).filter_by(
                    execution_id=execution_id
                ).first()
                
                if not record:
                    return None
                return cls._record_to_dict(record)
                
        except Exception as e:
            logger.error(f"Failed to get task record by execution_id: {e}")
            return None
    
    @classmethod
    def list_records(
        cls,
        task_type: Optional[str] = None,
        task_category: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列表查询
        
        Args:
            task_type: 任务类型筛选
            task_category: 任务类别筛选
            session_id: 会话ID筛选
            status: 状态筛选
            start_date: 开始日期
            end_date: 结束日期
            limit: 每页数量
            offset: 偏移量
            
        Returns:
            记录列表
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                query = session.query(TaskRecord)
                
                # 构建筛选条件
                conditions = []
                if task_type:
                    conditions.append(TaskRecord.task_type == task_type)
                if task_category:
                    conditions.append(TaskRecord.task_category == task_category)
                if session_id:
                    conditions.append(TaskRecord.session_id == session_id)
                if status:
                    conditions.append(TaskRecord.status == status)
                if start_date:
                    conditions.append(TaskRecord.created_at >= start_date)
                if end_date:
                    conditions.append(TaskRecord.created_at <= end_date)
                
                if conditions:
                    query = query.filter(and_(*conditions))
                
                # 排序和分页
                query = query.order_by(desc(TaskRecord.created_at))
                query = query.offset(offset).limit(limit)
                
                records = query.all()
                return [cls._record_to_dict(r) for r in records]
                
        except Exception as e:
            logger.error(f"Failed to list task records: {e}")
            return []
    
    @classmethod
    def count_records(
        cls,
        task_type: Optional[str] = None,
        task_category: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """统计记录数量
        
        Args:
            task_type: 任务类型筛选
            task_category: 任务类别筛选
            session_id: 会话ID筛选
            status: 状态筛选
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            记录数量
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                query = session.query(func.count(TaskRecord.id))
                
                conditions = []
                if task_type:
                    conditions.append(TaskRecord.task_type == task_type)
                if task_category:
                    conditions.append(TaskRecord.task_category == task_category)
                if session_id:
                    conditions.append(TaskRecord.session_id == session_id)
                if status:
                    conditions.append(TaskRecord.status == status)
                if start_date:
                    conditions.append(TaskRecord.created_at >= start_date)
                if end_date:
                    conditions.append(TaskRecord.created_at <= end_date)
                
                if conditions:
                    query = query.filter(and_(*conditions))
                
                return query.scalar() or 0
                
        except Exception as e:
            logger.error(f"Failed to count task records: {e}")
            return 0
    
    @classmethod
    def delete_record(cls, record_id: str, cleanup_execution: bool = True) -> bool:
        """删除记录（含关联的 AI 分析、执行状态、检查点和状态文件）
        
        Phase 25: 级联清理所有关联资源。
        
        Args:
            record_id: 记录ID
            cleanup_execution: 是否清理 ExecutionState/Checkpoint 和状态文件
            
        Returns:
            是否成功
        """
        try:
            db = get_task_manager_db()
            execution_id = None
            
            with db.get_session() as session:
                # 0. 先查出 execution_id（用于后续清理执行状态）
                record = session.query(TaskRecord).filter_by(
                    record_id=record_id
                ).first()
                if record:
                    execution_id = record.execution_id
                
                # 1. 删除关联的 StageAIAnalysis（Phase 7）
                ai_analysis_count = session.query(StageAIAnalysis).filter_by(
                    record_id=record_id
                ).delete()
                if ai_analysis_count > 0:
                    logger.debug(f"Deleted {ai_analysis_count} stage AI analyses for record: {record_id}")
                
                # 2. 删除关联的 OverallAnalysis（Phase 25 级联清理）
                try:
                    from .models import OverallAnalysis
                    overall_count = session.query(OverallAnalysis).filter_by(
                        record_id=record_id
                    ).delete()
                    if overall_count > 0:
                        logger.debug(f"Deleted {overall_count} overall analyses for record: {record_id}")
                except Exception as e:
                    logger.debug(f"OverallAnalysis cleanup skipped (model may not exist): {e}")
                
                # 3. 删除任务记录
                result = session.query(TaskRecord).filter_by(
                    record_id=record_id
                ).delete()
            
            # 4. 清理 ExecutionState/Checkpoint 和状态文件（Phase 25）
            if cleanup_execution and execution_id:
                try:
                    from .persistent_store import PersistentExecutionStore
                    PersistentExecutionStore.delete(execution_id)
                    logger.debug(f"Cleaned up execution state for: {execution_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup execution state for {execution_id}: {e}")
                
                # 5. 清理 TaskControl 记录（Phase 25）
                try:
                    from .controller import TaskController
                    TaskController._delete_control_from_db(execution_id)
                    logger.debug(f"Cleaned up task control for: {execution_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup task control for {execution_id}: {e}")
            
            if result > 0:
                logger.info(f"Deleted task record with cascade cleanup: {record_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete task record: {e}")
            return False
    
    @classmethod
    def batch_delete_records(cls, record_ids: list, cleanup_files: bool = True) -> dict:
        """批量删除记录（含级联清理）
        
        Phase 25: 批量删除支持。
        
        Args:
            record_ids: 记录ID列表
            cleanup_files: 是否清理关联文件
            
        Returns:
            {"deleted": int, "failed": int, "failed_ids": list, "skipped_running": list}
        """
        deleted = 0
        failed = 0
        failed_ids = []
        skipped_running = []
        
        for record_id in record_ids:
            try:
                # 检查是否正在运行（仅跳过 SOP 任务的 running 状态）
                record = cls.get_record(record_id)
                if record and record.get("status") == "running":
                    skipped_running.append(record_id)
                    continue
                
                success = cls.delete_record(record_id, cleanup_execution=cleanup_files)
                if success:
                    deleted += 1
                else:
                    failed += 1
                    failed_ids.append(record_id)
            except Exception as e:
                logger.error(f"Failed to delete record {record_id}: {e}")
                failed += 1
                failed_ids.append(record_id)
        
        logger.info(f"Batch delete: {deleted} deleted, {failed} failed, {len(skipped_running)} skipped (running)")
        return {
            "deleted": deleted,
            "failed": failed,
            "failed_ids": failed_ids,
            "skipped_running": skipped_running
        }
    
    @classmethod
    def get_statistics(
        cls,
        task_type: Optional[str] = None,
        task_category: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取统计信息
        
        Args:
            task_type: 任务类型筛选
            task_category: 任务类别筛选
            days: 统计天数
            
        Returns:
            统计信息字典
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                start_date = datetime.now() - timedelta(days=days)
                
                query = session.query(TaskRecord).filter(
                    TaskRecord.created_at >= start_date
                )
                
                if task_type:
                    query = query.filter(TaskRecord.task_type == task_type)
                if task_category:
                    query = query.filter(TaskRecord.task_category == task_category)
                
                records = query.all()
                
                total = len(records)
                completed = sum(1 for r in records if r.status == TaskStatus.COMPLETED.value)
                failed = sum(1 for r in records if r.status == TaskStatus.FAILED.value)
                stopped = sum(1 for r in records if r.status == TaskStatus.STOPPED.value)
                running = sum(1 for r in records if r.status == TaskStatus.RUNNING.value)
                paused = sum(1 for r in records if r.status == TaskStatus.PAUSED.value)
                
                durations = [r.duration_seconds for r in records if r.duration_seconds]
                avg_duration = sum(durations) / len(durations) if durations else 0
                
                return {
                    "total": total,
                    "completed": completed,
                    "failed": failed,
                    "stopped": stopped,
                    "running": running,
                    "paused": paused,
                    "success_rate": completed / total if total > 0 else 0,
                    "avg_duration_seconds": round(avg_duration, 2),
                    "period_days": days
                }
                
        except Exception as e:
            logger.error(f"Failed to get task statistics: {e}")
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "stopped": 0,
                "running": 0,
                "paused": 0,
                "success_rate": 0,
                "avg_duration_seconds": 0,
                "period_days": days
            }
    
    @classmethod
    def cleanup_old(cls, days: int = 90) -> int:
        """清理过期记录
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数
        """
        try:
            db = get_task_manager_db()
            with db.get_session() as session:
                cutoff = datetime.now() - timedelta(days=days)
                result = session.query(TaskRecord).filter(
                    TaskRecord.created_at < cutoff
                ).delete()
            
            logger.info(f"Cleaned up {result} old task records")
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup old task records: {e}")
            return 0
    
    @staticmethod
    def _record_to_dict(record: TaskRecord) -> Dict[str, Any]:
        """将ORM对象转换为字典
        
        Args:
            record: TaskRecord对象
            
        Returns:
            字典表示
        """
        return {
            "record_id": record.record_id,
            "task_type": record.task_type,
            "task_category": record.task_category,
            "execution_id": record.execution_id,
            "session_id": record.session_id,
            "interaction_mode": record.interaction_mode,
            "status": record.status,
            "progress": record.progress,
            "current_stage": record.current_stage,
            "message": record.message,
            "params": json.loads(record.params_json) if record.params_json else None,
            "inputs_summary": json.loads(record.inputs_summary) if record.inputs_summary else None,
            "outputs_summary": json.loads(record.outputs_summary) if record.outputs_summary else None,
            "result_file_path": record.result_file_path,
            "stages": json.loads(record.stages_json) if record.stages_json else None,
            "error_message": record.error_message,
            "error_traceback": record.error_traceback,
            # 使用本地时间，前端直接解析即可
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "paused_at": record.paused_at.isoformat() if record.paused_at else None,
            "resumed_at": record.resumed_at.isoformat() if record.resumed_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            "duration_seconds": record.duration_seconds
        }
