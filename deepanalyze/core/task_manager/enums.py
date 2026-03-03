# -*- coding: utf-8 -*-
"""
Task Manager Enums

定义任务管理相关的枚举类型。
"""

from enum import Enum


class TaskStatus(str, Enum):
    """任务执行状态"""
    PENDING = "pending"          # 等待执行
    RUNNING = "running"          # 正在执行
    PAUSED = "paused"            # 已暂停
    COMPLETED = "completed"      # 执行完成
    FAILED = "failed"            # 执行失败
    STOPPED = "stopped"          # 用户停止
    CANCELLED = "cancelled"      # 已取消


class TaskControlAction(str, Enum):
    """任务控制动作"""
    NONE = "none"                # 无动作
    PAUSE = "pause"              # 请求暂停
    STOP = "stop"                # 请求停止
    RESUME = "resume"            # 请求恢复


class TaskCategory(str, Enum):
    """任务类别（用于通用性）"""
    SOP = "sop"                  # SOP任务（规则挖掘、评分卡等）
    INFERENCE = "inference"      # LLM推理任务
    TRAINING = "training"        # 模型训练任务
    ETL = "etl"                  # 数据处理任务
    OTHER = "other"              # 其他任务


class InteractionMode(str, Enum):
    """交互模式（选择人工干预程度）
    
    用于专家模式设计：
    - auto：全自动执行，无人工干预
    - expert：专家模式，支持阶段暂停、参数调整、代码编辑
    """
    AUTO = "auto"                # 全自动模式
    EXPERT = "expert"            # 专家模式（人工干预）
