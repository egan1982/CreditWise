# -*- coding: utf-8 -*-
"""
SOP Task Type Definitions - 任务类型定义模块

提供 SOP 任务系统的所有类型定义，包括：
- 参数类型枚举
- 任务类型枚举（通用/SOP）
- 参数定义
- 阶段定义
- 输出定义
- 任务定义（含 Chat 入口字段）
- TypedDict 类型（用于 *_meta.py 文件）

设计原则：
- 类型定义与业务逻辑分离
- 支持 Chat 入口的触发词和说明
- 向后兼容现有任务元数据格式
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


# =============================================================================
# Enums
# =============================================================================

class ParamType(Enum):
    """参数类型枚举"""
    STRING = "string"
    TEXT = "text"
    TEXTAREA = "textarea"
    INTEGER = "integer"
    FLOAT = "float"
    NUMBER = "number"
    BOOLEAN = "boolean"
    CHECKBOX = "checkbox"
    SELECT = "select"
    RADIO = "radio"
    MULTI_SELECT = "multi_select"
    COLUMN_SELECT = "column_select"
    COLUMN_MULTI_SELECT = "column_multi_select"
    COLUMN_COMBOBOX = "column_combobox"  # 支持下拉选择和自定义输入的列选择器


class TaskType(Enum):
    """任务类型枚举
    
    区分通用任务和 SOP 任务：
    - GENERAL: 通用任务，无固定流程，LLM 自由发挥
    - SOP: SOP 任务，有固定 Pipeline 流程，LLM 只负责参数提取
    """
    GENERAL = "general"
    SOP = "sop"


# =============================================================================
# Dataclass Definitions
# =============================================================================

@dataclass
class ParamDefinition:
    """参数定义"""
    name: str                          # 参数名（英文）
    label: str                         # 显示标签（中文）
    param_type: ParamType              # 参数类型
    required: bool = True              # 是否必填
    default: Any = None                # 默认值
    description: str = ""              # 参数说明
    label_en: str = ""                 # 英文标签
    options: List[Dict[str, str]] = field(default_factory=list)  # 选项列表
    validation: Optional[Dict] = None  # 验证规则 (min, max, step)
    group: str = "basic"               # 参数分组（basic/advanced）
    show_when: Optional[Dict] = None   # 条件显示
    allow_empty: bool = False          # 是否允许空值
    stage: str = ""                    # 参数所属阶段ID
    advanced: bool = False             # 是否为调优参数（阶段内二级折叠显示）


@dataclass
class StageDefinition:
    """任务阶段定义"""
    id: str                            # 阶段ID
    name: str                          # 阶段名称（中文）
    description: str = ""              # 阶段说明
    progress_weight: int = 10          # 进度权重（百分比）
    estimated_time: str = "未知"       # 预估耗时


@dataclass
class OutputDefinition:
    """输出定义"""
    id: str                            # 输出ID
    name: str                          # 输出名称
    output_type: str                   # 输出类型 (table/chart/json/file)
    description: str = ""              # 输出说明
    show_when: Optional[Dict] = None   # 条件显示


@dataclass
class SOPTaskDefinition:
    """SOP 任务定义
    
    包含任务的完整元数据，支持：
    - 基本信息（ID、名称、描述、分类）
    - 输入要求（必需列、支持的文件类型）
    - 参数定义（必需参数、可选参数）
    - 执行阶段
    - 输出定义
    - 执行器配置
    - Chat 入口配置（触发词、简短说明）
    """
    # ========== 基本信息 ==========
    task_id: str                       # 任务唯一标识
    task_name: str                     # 任务名称（中文）
    task_name_en: str                  # 任务名称（英文）
    description: str                   # 任务描述
    category: str                      # 任务分类（风控建模/营销分析/运营分析）
    icon: str = "target"               # 任务图标
    estimated_time: str = "未知"       # 预估总耗时
    
    # ========== 输入要求 ==========
    required_columns: List[str] = field(default_factory=list)
    supported_file_types: List[str] = field(default_factory=lambda: [".csv", ".xlsx"])
    
    # ========== 参数定义 ==========
    required_params: List[ParamDefinition] = field(default_factory=list)
    optional_params: List[ParamDefinition] = field(default_factory=list)
    
    # ========== 执行阶段 ==========
    stages: List[StageDefinition] = field(default_factory=list)
    
    # ========== 输出定义 ==========
    outputs: List[OutputDefinition] = field(default_factory=list)
    
    # ========== 执行器配置 ==========
    executor_class: str = ""           # 执行器类的完整路径
    pipeline_class: str = ""           # Pipeline类的完整路径
    
    # ========== Prompt 模板 ==========
    sop_prompt_template: str = ""      # LLM SOP Prompt模板
    
    # ========== 文档 ==========
    workflow_doc: str = ""             # 工作流文档路径
    
    # ========== 版本 ==========
    version: str = "1.0.0"
    
    # ========== Chat 入口配置（新增） ==========
    task_type: TaskType = TaskType.SOP  # 任务类型：通用/SOP
    trigger_keywords: List[str] = field(default_factory=list)  # 触发词列表
    chat_summary: str = ""             # 面向用户的简短功能说明
    required_params_summary: str = ""  # 必需参数的简化说明（用于 Chat 提示）


# =============================================================================
# TypedDict Definitions (用于 *_meta.py 文件的类型提示)
# =============================================================================

class StageDict(TypedDict):
    """阶段定义字典类型"""
    id: str
    name: str
    progress_weight: int
    description: str  # 可选，但 TypedDict 不支持 total=False 的部分字段


class OptionDict(TypedDict):
    """选项字典类型"""
    value: str
    label: str


class ParamDict(TypedDict, total=False):
    """参数定义字典类型（所有字段可选）"""
    name: str
    type: str
    label: str
    label_en: str
    description: str
    required: bool
    allow_empty: bool
    default: Any
    min: float
    max: float
    step: float
    options: List[OptionDict]
    show_when: Dict[str, Any]
    stage: str


class OutputDict(TypedDict, total=False):
    """输出定义字典类型"""
    id: str
    name: str
    type: str
    show_when: Dict[str, Any]


class TaskMetaDict(TypedDict, total=False):
    """任务元数据字典类型
    
    用于 *_meta.py 文件的类型提示，与 SOPTaskDefinition 字段对应。
    """
    # 基本信息
    task_id: str
    task_name: str
    task_name_en: str
    description: str
    category: str
    icon: str
    estimated_time: str
    
    # 阶段和参数
    stages: List[StageDict]
    required_params: List[ParamDict]
    optional_params: List[ParamDict]
    outputs: List[OutputDict]
    
    # Chat 入口配置（新增）
    task_type: str  # "general" 或 "sop"
    trigger_keywords: List[str]
    chat_summary: str
    required_params_summary: str


# =============================================================================
# Export
# =============================================================================

__all__ = [
    # Enums
    'ParamType',
    'TaskType',
    # Dataclasses
    'ParamDefinition',
    'StageDefinition',
    'OutputDefinition',
    'SOPTaskDefinition',
    # TypedDicts
    'StageDict',
    'OptionDict',
    'ParamDict',
    'OutputDict',
    'TaskMetaDict',
]
