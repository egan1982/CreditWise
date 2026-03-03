# -*- coding: utf-8 -*-
"""
Task Manager ORM Models

定义任务管理相关的数据库模型。
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

TaskManagerBase = declarative_base()


class TaskRecord(TaskManagerBase):
    """任务执行记录
    
    记录任务的完整执行信息，包括：
    - 任务标识（类型、类别、执行ID、会话ID）
    - 执行状态（状态、进度、当前阶段）
    - 参数与结果（JSON格式存储）
    - 时间戳（创建、开始、暂停、完成等）
    - 性能指标（总耗时）
    """
    __tablename__ = "task_records"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # 任务标识
    task_type = Column(String(64), nullable=False, index=True)      # rule_mining, scorecard_dev
    task_category = Column(String(32), nullable=False, default="sop")  # sop, inference, training
    execution_id = Column(String(64), nullable=True, index=True)    # 关联ExecutionContext
    session_id = Column(String(64), nullable=True, index=True)
    
    # 交互模式
    interaction_mode = Column(String(32), nullable=False, default="auto")  # auto, expert
    
    # 状态
    status = Column(String(32), nullable=False, default="pending", index=True)
    progress = Column(Float, default=0.0)
    current_stage = Column(String(64), nullable=True)
    message = Column(Text, nullable=True)
    
    # 参数与结果（JSON字符串）
    params_json = Column(Text, nullable=True)           # 任务参数
    inputs_summary = Column(Text, nullable=True)        # 输入数据摘要（行数、列数、列名）
    outputs_summary = Column(Text, nullable=True)       # 输出结果摘要
    result_file_path = Column(String(512), nullable=True)  # 完整结果文件路径
    
    # 阶段进度（JSON字符串）
    stages_json = Column(Text, nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # 时间戳 - 使用本地时间，与executor.py保持一致
    created_at = Column(DateTime, default=datetime.now, index=True)
    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    resumed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 性能指标
    duration_seconds = Column(Float, nullable=True)     # 总耗时（秒）
    
    # 索引
    __table_args__ = (
        Index('idx_task_type_status', 'task_type', 'status'),
        Index('idx_session_created', 'session_id', 'created_at'),
        Index('idx_category_created', 'task_category', 'created_at'),
    )
    
    def __repr__(self):
        return f"<TaskRecord(record_id='{self.record_id}', task_type='{self.task_type}', status='{self.status}')>"


class TaskControl(TaskManagerBase):
    """任务控制状态
    
    用于持久化控制请求，支持：
    - 暂停请求
    - 停止请求
    - 恢复请求
    
    使用内存缓存 + 数据库持久化双层存储，确保控制请求不丢失。
    """
    __tablename__ = "task_controls"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), unique=True, nullable=False, index=True)
    action = Column(String(32), nullable=False, default="none")  # none, pause, stop, resume
    requested_at = Column(DateTime, default=datetime.now)
    processed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<TaskControl(execution_id='{self.execution_id}', action='{self.action}')>"


# =============================================================================
# Phase 6: 执行状态持久化模型
# =============================================================================

class ExecutionState(TaskManagerBase):
    """执行状态持久化
    
    用于跨后端重启恢复任务执行状态，支持：
    - 保存执行上下文到数据库
    - 记录暂停位置（阶段ID）
    - 支持从暂停点恢复执行
    """
    __tablename__ = "execution_states"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # 任务标识
    task_id = Column(String(64), nullable=False)  # rule_mining, scorecard_dev
    session_id = Column(String(64), nullable=True, index=True)
    record_id = Column(String(64), nullable=True, index=True)  # 关联 TaskRecord
    
    # 执行状态
    status = Column(String(32), nullable=False, default="pending")  # pending, running, paused, completed, failed
    current_stage_id = Column(String(64), nullable=True)  # 当前/最后执行的阶段
    pause_stage_id = Column(String(64), nullable=True)  # 暂停时的阶段ID（用于恢复）
    
    # 交互模式
    interaction_mode = Column(String(32), nullable=False, default="auto")  # auto, expert
    
    # 参数（JSON）
    params_json = Column(Text, nullable=True)  # 任务参数
    
    # 数据文件路径
    data_file_path = Column(String(512), nullable=True)  # 输入数据文件路径
    
    # 状态文件路径（用于存储 ExecutionContext 序列化）
    state_file_path = Column(String(512), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    paused_at = Column(DateTime, nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_exec_state_status', 'status'),
        Index('idx_exec_state_session', 'session_id', 'status'),
    )
    
    def __repr__(self):
        return f"<ExecutionState(execution_id='{self.execution_id}', status='{self.status}', pause_stage='{self.pause_stage_id}')>"


class ExecutionCheckpoint(TaskManagerBase):
    """执行检查点
    
    保存每个阶段完成时的输出，用于：
    - 断点续执行：从指定阶段恢复时，加载之前阶段的输出
    - 阶段重试：重新执行某个阶段时，使用上一阶段的输出作为输入
    """
    __tablename__ = "execution_checkpoints"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), nullable=False, index=True)
    
    # 阶段信息
    stage_id = Column(String(64), nullable=False)
    stage_index = Column(Integer, nullable=False)  # 阶段顺序索引
    stage_status = Column(String(32), nullable=False, default="completed")  # pending, completed, failed
    
    # 输出摘要（JSON，用于快速查看）
    outputs_summary = Column(Text, nullable=True)
    
    # 输出文件路径（大型对象如 DataFrame 存储到文件）
    outputs_file_path = Column(String(512), nullable=True)
    
    # 阶段参数（JSON，用于重试时恢复参数）
    params_json = Column(Text, nullable=True)
    
    # 时间戳
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # 复合唯一索引（同一执行同一阶段只保留一条）
    __table_args__ = (
        Index('idx_checkpoint_exec_stage', 'execution_id', 'stage_id', unique=True),
        Index('idx_checkpoint_exec_index', 'execution_id', 'stage_index'),
    )
    
    def __repr__(self):
        return f"<ExecutionCheckpoint(execution_id='{self.execution_id}', stage_id='{self.stage_id}', status='{self.stage_status}')>"


# =============================================================================
# Phase 7: 阶段 AI 分析结果持久化模型
# =============================================================================

class StageAIAnalysis(TaskManagerBase):
    """阶段 AI 分析结果
    
    保存专家模式下每个阶段的 AI 分析评估文本，支持：
    - 持久化存储：关闭浏览器后仍可访问
    - 跨设备访问：不同设备可查看同一任务的分析结果
    - 生命周期绑定：任务删除时自动清理关联的分析
    - 按需更新：支持重新生成分析（覆盖旧结果）
    """
    __tablename__ = "stage_ai_analysis"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联键
    record_id = Column(String(64), nullable=False, index=True)  # 关联 TaskRecord
    stage_id = Column(String(64), nullable=False)               # 阶段ID
    
    # 分析内容
    analysis_text = Column(Text, nullable=False)                # AI 分析文本
    model_used = Column(String(128), nullable=True)             # 使用的模型
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 复合唯一索引（同一任务同一阶段只保留一条）
    __table_args__ = (
        Index('idx_ai_analysis_record_stage', 'record_id', 'stage_id', unique=True),
    )
    
    def __repr__(self):
        return f"<StageAIAnalysis(record_id='{self.record_id}', stage_id='{self.stage_id}')>"


# =============================================================================
# Phase 8: 任务整体 AI 分析结果持久化模型
# =============================================================================

class OverallAIAnalysis(TaskManagerBase):
    """任务整体 AI 分析结果
    
    保存任务完成后的整体 AI 分析评估文本，支持：
    - 专家模式：report_generation阶段完成后自动生成
    - 自动模式：用户手动触发生成
    - 持久化存储：可跨会话访问
    - 纳入报告：作为执行摘要纳入PDF/Word报告
    """
    __tablename__ = "overall_ai_analysis"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联键
    record_id = Column(String(64), unique=True, nullable=False, index=True)  # 关联 TaskRecord
    task_type = Column(String(64), nullable=False)                           # 任务类型
    
    # 分析内容
    analysis_text = Column(Text, nullable=False)                # AI 分析文本
    model_used = Column(String(128), nullable=True)             # 使用的模型
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<OverallAIAnalysis(record_id='{self.record_id}', task_type='{self.task_type}')>"
