# 常用业务场景SOP模块 WebUI集成功能优化任务计划

> **文档版本**: v1.0  
> **创建日期**: 2025-12-09  
> **适用项目**: DeepAnalyze  
> **示例任务**: 策略规则挖掘（Rule Mining）

---

## 📌 文档定位与关联

| 属性 | 说明 |
|------|------|
| **本文档定位** | **后端架构与开发计划** - 侧重系统架构、API设计、任务分解、验收标准 |
| **关联文档** | [SOP_WebUI_Detail_Design.md](./SOP_WebUI_Detail_Design.md) - 前端UI/UX详细设计 |
| **示例任务** | 策略规则挖掘（Rule Mining） |

### 文档分工

| 内容领域 | Detail_Design | 本文档 |
|----------|:-------------:|:------:|
| **三列式UI布局设计** | ✅ 主责 | 引用 |
| **左侧任务选项卡设计** | ✅ 主责 | 引用 |
| **参数面板内嵌设计** | ✅ 主责 | 引用 |
| **交互流程时序图** | ✅ 主责 | 引用 |
| **Prompt注入机制** | ✅ 主责 | 引用 |
| **前端组件代码示例** | ✅ 主责 | 补充 |
| **系统架构设计** | 引用 | ✅ 主责 |
| **SOP Registry设计** | 引用 | ✅ 主责 |
| **API端点设计** | 引用 | ✅ 主责 |
| **任务执行引擎** | 引用 | ✅ 主责 |
| **开发任务分解** | 引用 | ✅ 主责 |
| **文件结构规划** | 引用 | ✅ 主责 |
| **验收标准** | 引用 | ✅ 主责 |

### 阅读建议

1. **UI/UX设计师**：优先阅读 `SOP_WebUI_Detail_Design.md`
2. **后端开发者**：优先阅读本文档
3. **全栈开发者**：两个文档结合阅读
4. **项目经理**：本文档的"开发任务分解"和"验收标准"部分

---

## 一、项目背景与目标

### 1.1 当前状态分析

#### 已有能力
| 模块 | 状态 | 说明 |
|------|------|------|
| 规则挖掘核心算法 | ✅ 已实现 | `deepanalyze/analysis/task_SOP/rule_mining.py` |
| 文件上传API | ✅ 已实现 | `/v1/files/upload-to`, `/workspace/upload` |
| 工作区管理 | ✅ 已实现 | 按session_id隔离的workspace目录 |
| 代码执行引擎 | ✅ 已实现 | `execute_code_safe` / `execute_code_safe_async` |
| LLM对话接口 | ✅ 已实现 | `/v1/chat/completions` |
| 前端管理界面 | ✅ 已实现 | `llm_manager_integrated/frontend/` |

#### 缺失环节
| 功能 | 优先级 | 影响 |
|------|--------|------|
| 数据预览/探索 | P0 | 用户无法在UI上查看数据结构和样本 |
| 交互式参数配置 | P0 | 无法通过UI设置target_col、weight_col等关键参数 |
| 任务模板/SOP引导 | P0 | LLM不知道该调用哪个SOP模块 |
| 任务进度反馈 | P1 | 长时间任务无进度显示 |
| 结果可视化 | P1 | 规则效果无图表展示 |
| 任务历史管理 | P2 | 无法查看和复用历史任务配置 |

### 1.2 目标愿景

构建一个**通用的业务场景SOP WebUI集成框架**，使得：
1. 用户可通过WebUI完成端到端的业务任务（上传数据→配置参数→执行任务→查看结果）
2. LLM能够识别用户意图并自动调用对应的SOP模块
3. 新增业务场景SOP时，只需按规范编写模块即可自动适配WebUI

---

## 二、系统架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DeepAnalyze WebUI SOP 集成架构                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           前端层 (Frontend)                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │   │
│  │  │ 数据上传组件  │  │ 任务选择面板  │  │ 参数配置表单  │  │ 结果展示区  │  │   │
│  │  │ DataUploader │  │ TaskSelector │  │ ParamConfig  │  │ ResultView  │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  │   │
│  │         │                 │                 │                 │         │   │
│  │         └─────────────────┴─────────────────┴─────────────────┘         │   │
│  │                                    │                                     │   │
│  │                           ┌────────▼────────┐                           │   │
│  │                           │  SOP Task Panel │                           │   │
│  │                           │  (任务编排中心)  │                           │   │
│  │                           └────────┬────────┘                           │   │
│  └────────────────────────────────────┼────────────────────────────────────┘   │
│                                       │ HTTP/WebSocket                         │
│  ┌────────────────────────────────────▼────────────────────────────────────┐   │
│  │                            API层 (Backend)                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │   │
│  │  │ /sop/tasks   │  │ /sop/execute │  │ /sop/status  │  │/sop/results │  │   │
│  │  │ 任务类型列表  │  │ 任务执行入口  │  │ 进度查询     │  │ 结果获取    │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │   │
│  │                                    │                                     │   │
│  │                           ┌────────▼────────┐                           │   │
│  │                           │  SOP Router     │                           │   │
│  │                           │  (任务路由分发)  │                           │   │
│  │                           └────────┬────────┘                           │   │
│  └────────────────────────────────────┼────────────────────────────────────┘   │
│                                       │                                        │
│  ┌────────────────────────────────────▼────────────────────────────────────┐   │
│  │                          SOP模块层 (Core)                                │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    SOP Registry (任务注册中心)                     │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │   │
│  │  │  │ rule_mining │  │ scorecard   │  │ feature_eng │  ...          │   │   │
│  │  │  │ 规则挖掘    │  │ 评分卡建模  │  │ 特征工程    │               │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘               │   │   │
│  │  └──────────────────────────────────────────────────────────────────┘   │   │
│  │                                    │                                     │   │
│  │                           ┌────────▼────────┐                           │   │
│  │                           │  Executor       │                           │   │
│  │                           │  (统一执行引擎)  │                           │   │
│  │                           └─────────────────┘                           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流设计

```
用户操作流程:
┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 上传 │───▶│ 数据预览 │───▶│ 选择任务 │───▶│ 配置参数 │───▶│ 执行任务 │
│ 数据 │    │ 列信息   │    │ 类型     │    │ 目标列等 │    │ 查看结果 │
└──────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
    │            │               │               │               │
    ▼            ▼               ▼               ▼               ▼
┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│POST  │    │GET       │    │GET       │    │POST      │    │GET       │
│/files│    │/data/    │    │/sop/     │    │/sop/     │    │/sop/     │
│upload│    │preview   │    │tasks     │    │execute   │    │results   │
└──────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

---

## 三、模块详细设计

### 3.1 SOP任务注册中心 (SOP Registry)

#### 3.1.1 设计目标
- 统一管理所有业务场景SOP模块
- 提供标准化的任务元数据定义
- 支持动态注册和发现

#### 3.1.2 任务元数据Schema

```python
# 文件: deepanalyze/analysis/task_SOP/registry.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

class ParamType(Enum):
    """参数类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    SELECT = "select"           # 下拉选择
    MULTI_SELECT = "multi_select"  # 多选
    COLUMN_SELECT = "column_select"  # 从数据列中选择
    COLUMN_MULTI_SELECT = "column_multi_select"  # 从数据列中多选

@dataclass
class ParamDefinition:
    """参数定义"""
    name: str                          # 参数名（英文）
    label: str                         # 显示标签（中文）
    param_type: ParamType              # 参数类型
    required: bool = True              # 是否必填
    default: Any = None                # 默认值
    description: str = ""              # 参数说明
    options: List[Dict[str, str]] = field(default_factory=list)  # 选项列表（用于SELECT类型）
    validation: Optional[Dict] = None  # 验证规则
    group: str = "basic"               # 参数分组（basic/advanced）

@dataclass
class StageDefinition:
    """任务阶段定义"""
    name: str                          # 阶段名（英文）
    label: str                         # 显示标签（中文）
    description: str                   # 阶段说明
    estimated_time: str = "未知"       # 预估耗时

@dataclass
class SOPTaskDefinition:
    """SOP任务定义"""
    task_id: str                       # 任务唯一标识
    name: str                          # 任务名称（中文）
    description: str                   # 任务描述
    category: str                      # 任务分类（如：风控、营销、运营）
    icon: str = "📊"                   # 任务图标
    
    # 输入要求
    required_columns: List[str] = field(default_factory=list)  # 必需的列类型
    supported_file_types: List[str] = field(default_factory=lambda: [".csv", ".xlsx"])
    
    # 参数定义
    params: List[ParamDefinition] = field(default_factory=list)
    
    # 执行阶段
    stages: List[StageDefinition] = field(default_factory=list)
    
    # 输出定义
    output_types: List[str] = field(default_factory=lambda: ["dataframe", "report"])
    
    # 执行器
    executor_class: str = ""           # 执行器类的完整路径
    
    # 文档
    workflow_doc: str = ""             # 工作流文档路径
    
    # 版本
    version: str = "1.0.0"
```

#### 3.1.3 规则挖掘任务注册示例

```python
# 文件: deepanalyze/analysis/task_SOP/rule_mining_meta.py

from .registry import SOPTaskDefinition, ParamDefinition, StageDefinition, ParamType

RULE_MINING_TASK = SOPTaskDefinition(
    task_id="rule_mining",
    name="策略规则挖掘",
    description="基于决策树算法，从历史数据中自动挖掘高效的风控规则，并通过贪心算法筛选出最优规则集",
    category="风控",
    icon="🎯",
    
    required_columns=["target", "weight"],
    supported_file_types=[".csv", ".xlsx"],
    
    params=[
        # 基础参数
        ParamDefinition(
            name="target_col",
            label="目标变量列",
            param_type=ParamType.COLUMN_SELECT,
            required=True,
            description="二值目标变量（0/1），如：is_bad、is_fraud",
            group="basic"
        ),
        ParamDefinition(
            name="weight_col",
            label="样本权重列",
            param_type=ParamType.COLUMN_SELECT,
            required=False,
            default=None,
            description="样本权重列，如无则自动设为1",
            group="basic"
        ),
        ParamDefinition(
            name="feature_cols",
            label="特征变量列",
            param_type=ParamType.COLUMN_MULTI_SELECT,
            required=True,
            description="用于规则挖掘的特征列，支持多选",
            group="basic"
        ),
        ParamDefinition(
            name="score_vars",
            label="评分变量",
            param_type=ParamType.COLUMN_MULTI_SELECT,
            required=False,
            description="评分类变量（如有），需指定方向约束",
            group="basic"
        ),
        
        # 高级参数
        ParamDefinition(
            name="n_vars",
            label="组合变量数",
            param_type=ParamType.INTEGER,
            required=False,
            default=3,
            description="每个规则组合包含的变量数量",
            validation={"min": 2, "max": 5},
            group="advanced"
        ),
        ParamDefinition(
            name="max_depth",
            label="决策树最大深度",
            param_type=ParamType.INTEGER,
            required=False,
            default=5,
            validation={"min": 2, "max": 10},
            group="advanced"
        ),
        ParamDefinition(
            name="min_samples_leaf",
            label="叶节点最小样本比例",
            param_type=ParamType.FLOAT,
            required=False,
            default=0.01,
            validation={"min": 0.001, "max": 0.1},
            group="advanced"
        ),
        ParamDefinition(
            name="max_hit_rate_filter",
            label="过滤阶段最大命中率",
            param_type=ParamType.FLOAT,
            required=False,
            default=0.03,
            validation={"min": 0.01, "max": 0.1},
            group="advanced"
        ),
        ParamDefinition(
            name="min_lift_filter",
            label="过滤阶段最小提升度",
            param_type=ParamType.FLOAT,
            required=False,
            default=3.5,
            validation={"min": 1.5, "max": 10.0},
            group="advanced"
        ),
        ParamDefinition(
            name="max_hit_rate_select",
            label="最大命中率（规则集）",
            param_type=ParamType.FLOAT,
            required=False,
            default=0.1,
            validation={"min": 0.05, "max": 0.3},
            group="advanced"
        ),
        # 风险目标参数（规则集级别约束，可选）
        ParamDefinition(
            name="min_recall_ruleset",
            label="最低召回率（规则集）",
            param_type=ParamType.FLOAT,
            required=False,
            default=None,
            validation={"min": 0.05, "max": 0.8},
            group="risk_targets"
        ),
        ParamDefinition(
            name="min_bad_rate_ruleset",
            label="最低坏账率（规则集）",
            param_type=ParamType.FLOAT,
            required=False,
            default=None,
            validation={"min": 0.1, "max": 0.9},
            group="risk_targets"
        ),
        ParamDefinition(
            name="min_lift_ruleset",
            label="最低提升度（规则集）",
            param_type=ParamType.FLOAT,
            required=False,
            default=None,
            validation={"min": 1.5, "max": 10.0},
            group="risk_targets"
        ),
    ],
    
    stages=[
        StageDefinition(
            name="data_preprocessing",
            label="数据预处理",
            description="特征映射、One-Hot编码、权重处理",
            estimated_time="10秒"
        ),
        StageDefinition(
            name="rule_generation",
            label="候选规则生成",
            description="基于决策树生成候选规则（约10万条）",
            estimated_time="5-10分钟"
        ),
        StageDefinition(
            name="direction_detection",
            label="特征方向检测",
            description="确定各特征的风险分裂方向",
            estimated_time="30秒"
        ),
        StageDefinition(
            name="rule_filtering",
            label="规则过滤",
            description="按方向和有效性过滤规则",
            estimated_time="10秒"
        ),
        StageDefinition(
            name="rule_evaluation",
            label="规则效果评估",
            description="计算recall、bad_rate、lift、hit_rate",
            estimated_time="1-2分钟"
        ),
        StageDefinition(
            name="rule_selection",
            label="最优规则选择",
            description="贪心算法选择最优规则集",
            estimated_time="30秒"
        ),
        StageDefinition(
            name="report_generation",
            label="报告生成",
            description="生成可视化图表数据供前端展示",
            estimated_time="10秒"
        ),
    ],
    
    output_types=["dataframe", "report", "visualization", "chart_data"],
    executor_class="deepanalyze.analysis.task_SOP.rule_mining.RuleMiningPipeline",
    workflow_doc="docs/taskSOP_solution/rule_mining_workflow.md",
    version="1.0.0"
)
```

### 3.2 后端API设计

#### 3.2.1 新增API端点

```python
# 文件: API/sop_api.py

"""
SOP Task API - 业务场景SOP任务管理接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import asyncio
import json

router = APIRouter(prefix="/sop", tags=["SOP Tasks"])


# ==================== 数据模型 ====================

class DataPreviewRequest(BaseModel):
    """数据预览请求"""
    file_id: str
    rows: int = 10

class DataPreviewResponse(BaseModel):
    """数据预览响应"""
    columns: List[Dict[str, str]]  # [{name, dtype, sample_values}]
    preview_data: List[Dict]       # 前N行数据
    total_rows: int
    total_columns: int

class TaskExecuteRequest(BaseModel):
    """任务执行请求"""
    task_id: str                   # 任务类型ID
    session_id: str                # 会话ID
    file_id: str                   # 数据文件ID
    params: Dict[str, Any]         # 任务参数

class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    execution_id: str
    status: str                    # pending/running/completed/failed
    current_stage: str
    progress: float                # 0-100
    message: str
    started_at: Optional[str]
    completed_at: Optional[str]

class TaskResultResponse(BaseModel):
    """任务结果响应"""
    execution_id: str
    status: str
    outputs: Dict[str, Any]        # 输出数据
    files: List[Dict[str, str]]    # 生成的文件列表
    summary: str                   # 结果摘要


# ==================== API端点 ====================

@router.get("/tasks")
async def list_available_tasks() -> List[Dict]:
    """
    获取所有可用的SOP任务类型
    
    Returns:
        任务类型列表，包含元数据
    """
    # ✅ 已实现：从SOP Registry获取
    registry = get_registry()
    return registry.list_tasks()

@router.get("/tasks/{task_id}")
async def get_task_definition(task_id: str) -> Dict:
    """
    获取指定任务的详细定义
    
    Args:
        task_id: 任务类型ID
        
    Returns:
        任务定义，包含参数Schema、阶段信息等
    """
    pass

@router.post("/data/preview")
async def preview_data(request: DataPreviewRequest) -> DataPreviewResponse:
    """
    预览上传的数据文件
    
    Args:
        request: 包含file_id和预览行数
        
    Returns:
        数据预览信息，包含列信息和样本数据
    """
    pass

@router.post("/data/analyze")
async def analyze_data(file_id: str) -> Dict:
    """
    分析数据特征，推荐任务类型和参数
    
    Args:
        file_id: 数据文件ID
        
    Returns:
        数据分析结果和推荐配置
    """
    pass

@router.post("/execute")
async def execute_task(
    request: TaskExecuteRequest,
    background_tasks: BackgroundTasks
) -> Dict:
    """
    执行SOP任务
    
    Args:
        request: 任务执行请求
        background_tasks: 后台任务管理器
        
    Returns:
        execution_id用于后续查询状态
    """
    pass

@router.get("/status/{execution_id}")
async def get_task_status(execution_id: str) -> TaskStatusResponse:
    """
    查询任务执行状态
    
    Args:
        execution_id: 任务执行ID
        
    Returns:
        当前状态、进度、阶段信息
    """
    pass

@router.get("/status/{execution_id}/stream")
async def stream_task_status(execution_id: str) -> StreamingResponse:
    """
    SSE流式获取任务状态更新
    
    Args:
        execution_id: 任务执行ID
        
    Returns:
        Server-Sent Events流
    """
    pass

@router.get("/results/{execution_id}")
async def get_task_results(execution_id: str) -> TaskResultResponse:
    """
    获取任务执行结果
    
    Args:
        execution_id: 任务执行ID
        
    Returns:
        任务输出数据和生成的文件
    """
    pass

@router.get("/history")
async def list_task_history(
    session_id: str,
    task_id: Optional[str] = None,
    limit: int = 20
) -> List[Dict]:
    """
    获取任务执行历史
    
    Args:
        session_id: 会话ID
        task_id: 可选，按任务类型过滤
        limit: 返回数量限制
        
    Returns:
        历史任务列表
    """
    pass
```

#### 3.2.2 任务执行引擎

```python
# 文件: API/sop_executor.py

"""
SOP Task Executor - 统一任务执行引擎
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import traceback

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskExecution:
    """任务执行实例"""
    execution_id: str
    task_id: str
    session_id: str
    params: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    current_stage: str = ""
    progress: float = 0.0
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

class SOPExecutor:
    """SOP任务执行器"""
    
    def __init__(self):
        self.executions: Dict[str, TaskExecution] = {}
        self.status_callbacks: Dict[str, List[Callable]] = {}
    
    def create_execution(
        self,
        task_id: str,
        session_id: str,
        params: Dict[str, Any]
    ) -> str:
        """创建任务执行实例"""
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        execution = TaskExecution(
            execution_id=execution_id,
            task_id=task_id,
            session_id=session_id,
            params=params
        )
        self.executions[execution_id] = execution
        return execution_id
    
    async def execute(self, execution_id: str) -> None:
        """执行任务"""
        execution = self.executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution.status = TaskStatus.RUNNING
        execution.started_at = datetime.now()
        
        try:
            # 根据task_id获取对应的执行器
            executor_class = self._get_executor_class(execution.task_id)
            
            # 创建进度回调
            def progress_callback(stage: str, current: int, total: int):
                execution.current_stage = stage
                execution.progress = (current / total) * 100 if total > 0 else 0
                execution.message = f"正在执行: {stage}"
                self._notify_status_change(execution_id)
            
            # 执行任务
            result = await self._run_task(
                executor_class,
                execution.params,
                progress_callback
            )
            
            execution.outputs = result
            execution.status = TaskStatus.COMPLETED
            execution.progress = 100.0
            execution.message = "任务完成"
            
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.error = str(e)
            execution.message = f"任务失败: {str(e)}"
            traceback.print_exc()
        
        finally:
            execution.completed_at = datetime.now()
            self._notify_status_change(execution_id)
    
    def _get_executor_class(self, task_id: str):
        """获取任务执行器类"""
        # ✅ 已实现：从Registry获取
        registry = get_registry()
        task_def = registry.get_task(task_id)
        if not task_def:
            raise ValueError(f"Unknown task: {task_id}")
        return task_def.pipeline_class
    
    async def _run_task(
        self,
        executor_class,
        params: Dict[str, Any],
        progress_callback: Callable
    ) -> Dict[str, Any]:
        """在线程池中运行任务"""
        import concurrent.futures
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool,
                self._sync_run_task,
                executor_class,
                params,
                progress_callback
            )
        return result
    
    def _sync_run_task(
        self,
        executor_class,
        params: Dict[str, Any],
        progress_callback: Callable
    ) -> Dict[str, Any]:
        """同步执行任务"""
        pipeline = executor_class(**params.get("pipeline_config", {}))
        results = pipeline.run(
            df=params["dataframe"],
            feature_cols=params["feature_cols"],
            target_col=params["target_col"],
            weight_col=params.get("weight_col", "weight"),
            progress_callback=progress_callback
        )
        return {
            "all_rules_count": len(results.get("all_rules", [])),
            "filtered_rules_count": len(results.get("filtered_rules", [])),
            "optimal_rules": results.get("optimal_rules", []).to_dict("records"),
            "direction_info": results.get("direction", []).to_dict("records")
        }
    
    def get_status(self, execution_id: str) -> Optional[TaskExecution]:
        """获取任务状态"""
        return self.executions.get(execution_id)
    
    def subscribe_status(self, execution_id: str, callback: Callable):
        """订阅状态更新"""
        if execution_id not in self.status_callbacks:
            self.status_callbacks[execution_id] = []
        self.status_callbacks[execution_id].append(callback)
    
    def _notify_status_change(self, execution_id: str):
        """通知状态变更"""
        callbacks = self.status_callbacks.get(execution_id, [])
        execution = self.executions.get(execution_id)
        for callback in callbacks:
            try:
                callback(execution)
            except Exception:
                pass

# 全局执行器实例
sop_executor = SOPExecutor()
```

### 3.3 前端UI设计

#### 3.3.1 组件结构

```
frontend/
├── components/
│   └── sop/
│       ├── SOPTaskPanel.js          # 任务面板主组件
│       ├── DataUploader.js          # 数据上传组件
│       ├── DataPreview.js           # 数据预览组件
│       ├── TaskSelector.js          # 任务选择组件
│       ├── ParamConfigForm.js       # 参数配置表单
│       ├── ExecutionProgress.js     # 执行进度组件
│       └── ResultViewer.js          # 结果展示组件
├── styles/
│   └── sop.css                      # SOP模块样式
└── services/
    └── sopService.js                # SOP API服务
```

#### 3.3.2 UI交互流程设计

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SOP任务面板 UI布局                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 步骤指示器: [1.上传数据] → [2.选择任务] → [3.配置参数] → [4.执行]    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌───────────────────────────┐  ┌───────────────────────────────────────┐  │
│  │                           │  │                                       │  │
│  │     左侧：数据区域         │  │      右侧：任务配置区域                │  │
│  │                           │  │                                       │  │
│  │  ┌─────────────────────┐  │  │  ┌─────────────────────────────────┐  │  │
│  │  │ 📁 数据上传区       │  │  │  │ 🎯 任务选择                     │  │  │
│  │  │                     │  │  │  │                                 │  │  │
│  │  │ 拖拽或点击上传      │  │  │  │ ○ 策略规则挖掘                  │  │  │
│  │  │ CSV/Excel文件       │  │  │  │ ○ 评分卡建模                    │  │  │
│  │  │                     │  │  │  │ ○ 特征工程                      │  │  │
│  │  └─────────────────────┘  │  │  │                                 │  │  │
│  │                           │  │  └─────────────────────────────────┘  │  │
│  │  ┌─────────────────────┐  │  │                                       │  │
│  │  │ 📊 数据预览         │  │  │  ┌─────────────────────────────────┐  │  │
│  │  │                     │  │  │  │ ⚙️ 参数配置                     │  │  │
│  │  │ 列名 | 类型 | 样本  │  │  │  │                                 │  │  │
│  │  │ ─────┼──────┼────── │  │  │  │ 目标变量: [下拉选择列名]       │  │  │
│  │  │ age  │ int  │ 25,30 │  │  │  │ 权重列:   [下拉选择列名]       │  │  │
│  │  │ inc  │float │ 5000  │  │  │  │ 特征列:   [多选列名]           │  │  │
│  │  │ ...  │ ...  │ ...   │  │  │  │                                 │  │  │
│  │  │                     │  │  │  │ ▼ 高级参数（按阶段分组）        │  │  │
│  │  │ 共 50000 行, 25 列  │  │  │  │   ▶ 数据预处理 (2)             │  │  │
│  │  └─────────────────────┘  │  │  │   ▶ 规则生成 (3)               │  │  │
│  │                           │  │  │   ▶ 规则过滤 (2)               │  │  │
│  └───────────────────────────┘  │  │   ▶ 最优选择 (3)               │  │  │
│                                 │  └─────────────────────────────────┘  │  │
│                                 │                                       │  │
│                                 │  ┌─────────────────────────────────┐  │  │
│                                 │  │ 🚀 执行任务                     │  │  │
│                                 │  │                                 │  │  │
│                                 │  │ [开始执行]  [重置参数]          │  │  │
│                                 │  └─────────────────────────────────┘  │  │
│                                 └───────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 📈 执行进度 & 结果                                                   │   │
│  │                                                                     │   │
│  │ 当前阶段: [规则生成] ████████████░░░░░░░░ 60%                       │   │
│  │                                                                     │   │
│  │ ┌─────────────────────────────────────────────────────────────┐    │   │
│  │ │ 结果预览                                                     │    │   │
│  │ │                                                             │    │   │
│  │ │ 最优规则集 (共12条规则，累计命中率9.8%)                      │    │   │
│  │ │ ┌────────────────────────────────────────────────────────┐ │    │   │
│  │ │ │ 规则 | Lift | 累计召回 | 累计命中率                     │ │    │   │
│  │ │ │ (age<=25) & (income<=5000) | 5.2 | 2.3% | 1.5%        │ │    │   │
│  │ │ │ ...                                                    │ │    │   │
│  │ │ └────────────────────────────────────────────────────────┘ │    │   │
│  │ │                                                             │    │   │
│  │ │ [下载完整结果] [导出报告] [保存配置]                        │    │   │
│  │ └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.3.3 关键交互逻辑

```javascript
// 文件: frontend/services/sopService.js

/**
 * SOP任务服务
 */
class SOPService {
    constructor(baseUrl = 'http://localhost:8200') {
        this.baseUrl = baseUrl;
    }
    
    /**
     * 获取可用任务列表
     */
    async getAvailableTasks() {
        const response = await fetch(`${this.baseUrl}/sop/tasks`);
        return response.json();
    }
    
    /**
     * 获取任务定义
     */
    async getTaskDefinition(taskId) {
        const response = await fetch(`${this.baseUrl}/sop/tasks/${taskId}`);
        return response.json();
    }
    
    /**
     * 预览数据
     */
    async previewData(fileId, rows = 10) {
        const response = await fetch(`${this.baseUrl}/sop/data/preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_id: fileId, rows })
        });
        return response.json();
    }
    
    /**
     * 执行任务
     */
    async executeTask(taskId, sessionId, fileId, params) {
        const response = await fetch(`${this.baseUrl}/sop/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: taskId,
                session_id: sessionId,
                file_id: fileId,
                params
            })
        });
        return response.json();
    }
    
    /**
     * 订阅任务状态（SSE）
     */
    subscribeTaskStatus(executionId, onUpdate, onComplete, onError) {
        const eventSource = new EventSource(
            `${this.baseUrl}/sop/status/${executionId}/stream`
        );
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.status === 'completed' || data.status === 'failed') {
                onComplete(data);
                eventSource.close();
            } else {
                onUpdate(data);
            }
        };
        
        eventSource.onerror = (error) => {
            onError(error);
            eventSource.close();
        };
        
        return eventSource;
    }
    
    /**
     * 获取任务结果
     */
    async getTaskResults(executionId) {
        const response = await fetch(`${this.baseUrl}/sop/results/${executionId}`);
        return response.json();
    }
}

export default new SOPService();
```

### 3.4 LLM集成设计

#### 3.4.1 System Prompt增强

```python
# 文件: API/prompts/sop_system_prompt.py

SOP_SYSTEM_PROMPT_TEMPLATE = """
# DeepAnalyze SOP任务助手

你是DeepAnalyze的智能任务助手，能够帮助用户完成各类数据分析任务。

## 可用的SOP任务模块

{available_tasks}

## 任务执行流程

当用户需要执行数据分析任务时，请按以下流程引导：

1. **理解需求**：确认用户想要完成的任务类型
2. **检查数据**：查看用户上传的数据文件，确认数据结构
3. **配置参数**：根据数据特征，推荐或确认任务参数
4. **执行任务**：调用对应的SOP模块执行任务
5. **解读结果**：帮助用户理解任务输出

## 当前工作区状态

{workspace_status}

## 执行任务的代码模板

当需要执行规则挖掘任务时，使用以下代码模板：

```python
from deepanalyze.analysis.task_SOP.rule_mining import RuleMiningPipeline
import pandas as pd

# 读取数据
df = pd.read_csv('数据文件路径')

# 配置并执行
pipeline = RuleMiningPipeline(
    n_vars=3,
    max_depth=5,
    min_lift_filter=3.5,
    max_hit_rate_select=0.1
)

results = pipeline.run(
    df=df,
    feature_cols=['特征列1', '特征列2', ...],
    target_col='目标列',
    weight_col='权重列'
)

# 输出结果
print("最优规则集：")
print(results['optimal_rules'])
```

## 注意事项

- 始终先确认数据文件已上传到工作区
- 帮助用户识别正确的目标列和特征列
- 对于高级参数，提供默认值并解释其含义
- 任务完成后，提供结果的业务解读
"""

def build_sop_system_prompt(available_tasks: list, workspace_files: list) -> str:
    """构建SOP系统提示词"""
    
    # 格式化可用任务
    tasks_str = ""
    for task in available_tasks:
        tasks_str += f"### {task['name']} ({task['task_id']})\n"
        tasks_str += f"- 描述: {task['description']}\n"
        tasks_str += f"- 分类: {task['category']}\n"
        tasks_str += f"- 文档: {task['workflow_doc']}\n\n"
    
    # 格式化工作区状态
    workspace_str = "当前工作区文件:\n"
    if workspace_files:
        for f in workspace_files:
            workspace_str += f"- {f['name']} ({f['size']})\n"
    else:
        workspace_str += "- (空)\n"
    
    return SOP_SYSTEM_PROMPT_TEMPLATE.format(
        available_tasks=tasks_str,
        workspace_status=workspace_str
    )
```

#### 3.4.2 意图识别与任务路由

```python
# 文件: API/sop_intent.py

"""
SOP任务意图识别
"""

from typing import Optional, Dict, List
import re

# 任务关键词映射
TASK_KEYWORDS = {
    "rule_mining": [
        "规则挖掘", "规则生成", "策略规则", "风控规则",
        "决策树规则", "rule mining", "rule generation"
    ],
    "scorecard": [
        "评分卡", "信用评分", "风险评分", "scorecard",
        "credit score", "risk score"
    ],
    "feature_engineering": [
        "特征工程", "特征选择", "特征筛选", "IV值",
        "WOE", "feature engineering", "feature selection"
    ]
}

def detect_task_intent(user_message: str) -> Optional[str]:
    """
    从用户消息中检测任务意图
    
    Args:
        user_message: 用户输入的消息
        
    Returns:
        检测到的任务ID，或None
    """
    message_lower = user_message.lower()
    
    for task_id, keywords in TASK_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in message_lower:
                return task_id
    
    return None

def extract_column_mentions(
    user_message: str,
    available_columns: List[str]
) -> Dict[str, List[str]]:
    """
    从用户消息中提取列名引用
    
    Args:
        user_message: 用户消息
        available_columns: 可用的列名列表
        
    Returns:
        按类型分组的列名 {target: [...], features: [...], weight: [...]}
    """
    result = {"target": [], "features": [], "weight": []}
    
    # 目标变量关键词
    target_patterns = [
        r"目标[变量列]?[是为]?\s*[：:]\s*(\w+)",
        r"target[是为]?\s*[：:=]\s*(\w+)",
        r"(\w+)\s*作为目标",
    ]
    
    # 权重列关键词
    weight_patterns = [
        r"权重[列]?[是为]?\s*[：:]\s*(\w+)",
        r"weight[是为]?\s*[：:=]\s*(\w+)",
    ]
    
    for pattern in target_patterns:
        matches = re.findall(pattern, user_message, re.IGNORECASE)
        for match in matches:
            if match in available_columns:
                result["target"].append(match)
    
    for pattern in weight_patterns:
        matches = re.findall(pattern, user_message, re.IGNORECASE)
        for match in matches:
            if match in available_columns:
                result["weight"].append(match)
    
    return result
```

---

## 四、开发任务分解

### 4.1 Phase 1: 基础框架搭建 (预计3天)

| 任务 | 优先级 | 预计工时 | 依赖 |
|------|--------|----------|------|
| 1.1 创建SOP Registry框架 | P0 | 4h | - |
| 1.2 定义任务元数据Schema | P0 | 2h | 1.1 |
| 1.3 注册rule_mining任务 | P0 | 2h | 1.2 |
| 1.4 创建sop_api.py基础端点 | P0 | 4h | 1.3 |
| 1.5 实现数据预览接口 | P0 | 3h | 1.4 |
| 1.6 单元测试 | P1 | 3h | 1.5 |

### 4.2 Phase 2: 任务执行引擎 (预计3天)

| 任务 | 优先级 | 预计工时 | 依赖 |
|------|--------|----------|------|
| 2.1 实现SOPExecutor类 | P0 | 4h | Phase 1 |
| 2.2 集成rule_mining执行 | P0 | 3h | 2.1 |
| 2.3 实现进度回调机制 | P0 | 3h | 2.2 |
| 2.4 实现SSE状态推送 | P1 | 4h | 2.3 |
| 2.5 结果存储与获取 | P0 | 3h | 2.2 |
| 2.6 集成测试 | P1 | 3h | 2.5 |

### 4.3 Phase 3: 前端UI开发 (预计4天)

| 任务 | 优先级 | 预计工时 | 依赖 |
|------|--------|----------|------|
| 3.1 创建SOPTaskPanel组件 | P0 | 4h | Phase 2 |
| 3.2 实现DataUploader组件 | P0 | 3h | 3.1 |
| 3.3 实现DataPreview组件 | P0 | 3h | 3.2 |
| 3.4 实现TaskSelector组件 | P0 | 2h | 3.1 |
| 3.5 实现ParamConfigForm组件 | P0 | 4h | 3.4 |
| 3.6 实现ExecutionProgress组件 | P1 | 3h | 3.5 |
| 3.7 实现ResultViewer组件 | P1 | 4h | 3.6 |
| 3.8 样式优化与响应式 | P2 | 3h | 3.7 |

### 4.4 Phase 4: LLM集成与优化 (预计2天)

| 任务 | 优先级 | 预计工时 | 依赖 |
|------|--------|----------|------|
| 4.1 增强System Prompt | P0 | 3h | Phase 3 |
| 4.2 实现意图识别 | P1 | 3h | 4.1 |
| 4.3 对话式参数配置 | P1 | 4h | 4.2 |
| 4.4 结果解读生成 | P2 | 3h | 4.3 |
| 4.5 端到端测试 | P0 | 3h | 4.4 |

### 4.5 Phase 5: 扩展与文档 (预计2天)

| 任务 | 优先级 | 预计工时 | 依赖 |
|------|--------|----------|------|
| 5.1 添加更多SOP任务模板 | P2 | 4h | Phase 4 |
| 5.2 任务历史管理 | P2 | 3h | 5.1 |
| 5.3 配置导入导出 | P2 | 2h | 5.2 |
| 5.4 开发者文档 | P1 | 3h | 5.3 |
| 5.5 用户使用指南 | P1 | 2h | 5.4 |

---

## 五、文件结构规划

```
DeepAnalyze/
├── deepanalyze/
│   └── analysis/
│       └── task_SOP/
│           ├── __init__.py              # [已更新] 模块导出（含图表函数）
│           ├── registry.py              # [新增] SOP任务注册中心
│           ├── rule_mining.py           # [已实现] 规则挖掘核心实现（含report_generation阶段）
│           ├── rule_mining_meta.py      # [已实现] 规则挖掘任务元数据（6阶段，v2.0合并优化）
│           ├── rule_mining_viz.py       # [已实现] 规则挖掘可视化（get_chart_data_for_frontend）
│           ├── scorecard_development.py # [已实现] 评分卡建模（含report_generation阶段）
│           ├── scorecard_meta.py        # [已实现] 评分卡任务元数据（7阶段）
│           ├── scorecard_viz.py         # [已实现] 评分卡可视化（get_chart_data_for_frontend）
│
├── docs/taskSOP_solution/
│   ├── rule_mining_workflow.md      # [已迁移] 规则挖掘工作流文档
│   └── scorecard_dev_workflow.md    # [已迁移] 评分卡工作流文档
│
├── API/
│   ├── sop_api.py                       # [新增] SOP任务API端点
│   ├── sop_executor.py                  # [新增] 任务执行引擎
│   ├── sop_intent.py                    # [新增] 意图识别模块
│   └── prompts/
│       └── sop_system_prompt.py         # [新增] SOP系统提示词
│
├── demo/chat/components/sop/            # [已实现] 前端SOP组件
│   ├── RuleMiningResults.tsx            # [已实现] 规则挖掘结果展示（含SVG图表）
│   └── ScorecardResults.tsx             # [已实现] 评分卡结果展示（含SVG图表）
│
├── llm_manager_integrated/
│   └── frontend/
│       ├── components/
│       │   └── sop/                     # [新增] SOP前端组件目录
│       │       ├── SOPTaskPanel.js
│       │       ├── DataUploader.js
│       │       ├── DataPreview.js
│       │       ├── TaskSelector.js
│       │       ├── ParamConfigForm.js
│       │       ├── ExecutionProgress.js
│       │       └── ResultViewer.js
│       ├── services/
│       │   └── sopService.js            # [新增] SOP API服务
│       └── styles/
│           └── sop.css                  # [新增] SOP模块样式
│
└── docs/
    ├── SOP_WebUI_Integration_design.md    # [本文档] 集成设计
    └── SOP_Developer_Guide.md           # [未来] 开发者指南
```

---

## 六、验收标准

### 6.1 功能验收

| 功能点 | 验收标准 |
|--------|----------|
| 数据上传 | 支持CSV/Excel文件上传，显示上传进度 |
| 数据预览 | 显示列名、数据类型、样本值，支持分页 |
| 任务选择 | 展示可用任务列表，显示任务说明 |
| 参数配置 | 动态生成表单，支持列名下拉选择，参数验证 |
| 任务执行 | 后台异步执行，实时进度更新 |
| 结果展示 | 表格展示最优规则，支持下载和导出 |
| LLM集成 | 对话中识别任务意图，辅助参数配置 |

### 6.2 性能验收

| 指标 | 标准 |
|------|------|
| 数据预览响应时间 | < 2秒（10万行数据） |
| 任务启动响应时间 | < 1秒 |
| 进度更新频率 | 每秒至少1次 |
| 前端渲染性能 | 60fps无卡顿 |

### 6.3 可扩展性验收

| 要求 | 验证方法 |
|------|----------|
| 新增任务类型 | 只需添加xxx.py和xxx_meta.py即可自动注册 |
| 参数类型扩展 | ParamType枚举可扩展，表单自动适配 |
| 前端组件复用 | 各组件可独立使用和组合 |

---

## 七、风险与对策

| 风险 | 可能性 | 影响 | 对策 |
|------|--------|------|------|
| 大数据量任务超时 | 中 | 高 | 分批处理、异步执行、进度保存 |
| 前端状态管理复杂 | 中 | 中 | 使用状态管理库（如Zustand） |
| LLM意图识别不准 | 高 | 中 | 提供明确的任务选择UI作为后备 |
| 跨浏览器兼容性 | 低 | 中 | 使用标准Web API，充分测试 |

---

## 八、后续扩展方向

1. **更多SOP任务**：评分卡建模、特征工程、模型监控等
2. **任务编排**：支持多个SOP任务串联执行
3. **模板市场**：用户可分享和复用任务配置模板
4. **可视化增强**：规则效果图表、特征重要性可视化
5. **协作功能**：多用户协作、任务审批流程

---

## 附录

### A. 相关文档链接

- [规则挖掘工作流说明](./rule_mining_workflow.md)
- [DeepAnalyze API文档](../API/README.md)
- [LLM Manager前端说明](../llm_manager_integrated/frontend/README.md)

### B. 参考资料

- FastAPI官方文档: https://fastapi.tiangolo.com/
- Server-Sent Events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- Tailwind CSS: https://tailwindcss.com/docs
