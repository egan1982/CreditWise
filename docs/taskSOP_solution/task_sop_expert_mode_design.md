# Task SOP 专家模式功能设计及实施方案

> **文档版本**: v1.1
> **更新日期**: 2026-03-02（移除 LLM SOP 相关内容）
> **状态**: ✅ 已实现

## 一、背景与目标

### 1.1 背景

当前 Task SOP 功能采用**全自动模式**：用户配置参数后一键执行，AI 自动完成所有阶段，中间过程不可干预。

原项目（非 Task SOP 模式）支持**对话式人工干预**：
- 代码块编辑：右侧 Code 列支持编辑
- 多轮调整：用户可在对话中继续要求 AI 调整
- 但**没有结构化阶段控制**和**版本对比**功能

### 1.2 目标

在保留现有全自动模式的基础上，新增**专家模式（人工辅助模式）**，支持：
- 阶段级执行控制（暂停/继续/重试）
- 参数热调整（在阶段间修改参数）
- 代码编辑与重新执行
- 阶段结果查看与对比

### 1.3 两种模式定位

| 模式 | 适用场景 | 用户群体 |
|------|---------|---------|
| **全自动模式** | 数据质量好、流程标准、快速验证 | 新手、标准化任务 |
| **专家模式** | 数据复杂、需要调参、学习理解流程 | 专家、探索性分析 |

### 1.3.1 两种模式的 LLM 价值定位

> **更新日期**: 2024-12-24

| 模式 | LLM 角色 | AI分析评估按钮 |
|------|---------|---------------|
| **全自动模式** | 辅助入口（参数提取） | ✅ 可用（紫色高亮） |
| **专家模式** | 核心辅助（阶段分析） | ❌ 禁用（灰色） |

**设计原则**：
- **全自动模式**：执行过程无 LLM 干预，任务完成后提供"AI 分析评估"按钮供用户按需调用
- **专家模式**：每阶段暂停时已包含 AI 结果分析和建议，无需额外的"AI 分析评估"按钮

**"AI 分析评估"按钮禁用逻辑**：
```typescript
// three-panel-interface.tsx
<Button
  disabled={isAIAnalyzing || interactionMode === "expert"}
  title={interactionMode === "expert" 
    ? "专家模式下各阶段已包含AI分析" 
    : "对任务结果进行AI智能分析"}
>
```

### 1.4 通用性设计

本方案设计为**任务类型无关**，可同时支持：
- ✅ 评分卡开发任务（附录A.2已定义阶段）
- ✅ 规则挖掘任务（附录A.1已定义阶段）
- ✅ 后续新增任务类型（通过在Meta中定义阶段列表和可调参数）

### 1.5 执行模式

本方案定义的 `interaction_mode` 支持两种执行方式：

| interaction_mode | 场景描述 | 状态 |
|-----------------|---------|------|
| `auto` | 全自动执行，阶段自动流转完成 | ✅ 已实现 |
| `expert` | 专家模式，支持阶段暂停、参数调整、阶段重试 | ✅ 已实现 |

**模式说明**：
- **全自动模式**：适合标准化任务，执行过程无人工干预
- **专家模式**：适合需要调参或理解流程的场景，每阶段完成后自动暂停，用户可查看结果、调整参数后继续

> **注意**：统一使用 Pipeline 执行引擎。LLM 作为智能入口（`LLMParamExtractor`）负责参数推断，而非执行引擎。

---

## 二、功能架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Task SOP 执行模式                               │
├─────────────────────────────┬───────────────────────────────────────────┤
│     🚀 全自动模式           │     🎛️ 专家模式                           │
│     (现有功能)              │     (新增功能)                            │
├─────────────────────────────┼───────────────────────────────────────────┤
│                             │                                           │
│  配置参数 → 一键执行        │  配置参数 → 阶段1 → [暂停] → 阶段2 → ... │
│      ↓                      │                ↓                          │
│  AI自动完成所有阶段         │  每阶段可：                               │
│      ↓                      │  • 查看结果                               │
│  输出最终结果               │  • 调整下阶段参数                         │
│                             │  • 重试当前阶段                           │
│                             │  • 编辑代码后执行                         │
│                             │  • 继续下一阶段                           │
└─────────────────────────────┴───────────────────────────────────────────┘
```

### 2.2 模块划分

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           前端模块                                       │
├─────────────────────────────────────────────────────────────────────────┤
│  sop/                                                                   │
│  ├── TaskSelector.tsx           # 任务选择器（现有）                    │
│  ├── TaskConfigPanel.tsx        # 通用配置面板（动态渲染）              │
│  ├── DynamicParamRenderer.tsx   # 动态参数渲染器                        │
│  ├── TaskProgress.tsx           # 任务进度（现有）                      │
│  ├── RuleMiningResults.tsx      # 结果展示（现有）                      │
│  │                                                                      │
│  └── expert/                    # 专家模式组件（新增）                  │
│      ├── ExecutionModeSelector.tsx   # 执行模式选择器                   │
│      ├── StageController.tsx         # 阶段控制器                       │
│      ├── StageParameterEditor.tsx    # 阶段参数编辑器                   │
│      ├── StageCodeEditor.tsx         # 阶段代码编辑器                   │
│      ├── StageResultViewer.tsx       # 阶段结果查看器                   │
│      ├── StageTimeline.tsx           # 阶段时间线                       │
│      └── index.ts                    # 导出                             │
├─────────────────────────────────────────────────────────────────────────┤
│                           后端模块                                       │
├─────────────────────────────────────────────────────────────────────────┤
│  API/                                                                   │
│  ├── sop_api.py                 # SOP API（现有，需扩展）               │
│  │   ├── POST /sop/execute      # 全自动执行（现有）                    │
│  │   ├── POST /sop/execute/stage     # 单阶段执行（新增）               │
│  │   ├── POST /sop/retry/stage       # 阶段重试（新增）                 │
│  │   ├── GET  /sop/stage/result      # 获取阶段结果（新增）             │
│  │   ├── PUT  /sop/stage/params      # 更新阶段参数（新增）             │
│  │   └── POST /sop/execute/code      # 执行编辑后代码（新增）           │
│  │                                                                      │
│  └── utils.py                   # 工具函数（现有，可复用）              │
│      ├── execute_code_safe()         # 代码执行                         │
│      ├── WorkspaceTracker            # 文件跟踪                         │
│      └── extract_code_from_segment() # 代码提取                         │
├─────────────────────────────────────────────────────────────────────────┤
│                         状态管理模块                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  deepanalyze/analysis/task_SOP/                                         │
│  ├── stage_state_machine.py     # 阶段状态机（新增）                    │
│  ├── stage_result_store.py      # 阶段结果存储（新增）                  │
│  └── expert_mode_executor.py    # 专家模式执行器（新增）                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、详细功能设计

### 3.1 执行模式选择器

#### 3.1.1 UI 设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 执行模式                                                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ○ 🚀 全自动模式                    ● 🎛️ 专家模式                       │
│    一键执行所有阶段                   每阶段可暂停、调整、重试           │
│    适合标准化任务                     适合探索性分析                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 3.1.2 组件接口

```typescript
// ExecutionModeSelector.tsx
interface ExecutionModeSelectorProps {
  mode: "auto" | "expert";  // interaction_mode: 交互模式
  onChange: (mode: "auto" | "expert") => void;
  disabled?: boolean;
}
```

> **命名约定**：此处的 `mode` 对应 `interaction_mode`（交互模式），与 `pipeline_llm_hybrid_design.md` 中的 `engine_mode`（执行引擎）正交。详见该文档附录10.3。

### 3.2 阶段控制器

#### 3.2.1 阶段状态定义

```typescript
type StageStatus = 
  | "pending"      // 待执行
  | "running"      // 执行中
  | "paused"       // 已暂停（等待用户操作）
  | "completed"    // 已完成
  | "failed"       // 执行失败
  | "skipped";     // 已跳过

interface StageState {
  stageId: string;
  stageName: string;
  status: StageStatus;
  startTime?: Date;
  endTime?: Date;
  result?: StageResult;
  error?: string;
  parameters: Record<string, any>;
  generatedCode?: string;
}
```

#### 3.2.2 阶段控制 UI

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 阶段 2/6: WOE分箱 ✅ 完成                                    [展开 ▼]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  📊 本阶段结果:                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ • 成功分箱变量: 15 个                                           │   │
│  │ • 平均IV值: 0.35                                                │   │
│  │ • 最高IV变量: credit_score (IV=0.82)                            │   │
│  │ • 生成文件: woe_result.csv, iv_table.csv                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  📝 生成代码:                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ # WOE分箱代码                                                   │   │
│  │ from toad import transform                                      │   │
│  │ ...                                              [查看完整代码]  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  下一阶段: 特征筛选                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 可调整参数:                                                     │   │
│  │   IV下限: [0.02    ▼]                                           │   │
│  │   VIF阈值: [10     ▼]                                           │   │
│  │   相关系数阈值: [0.7 ▼]                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ ▶ 继续   │  │ 🔄 重试  │  │ ✏️ 编辑  │  │ ⏹ 终止  │               │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 3.2.3 组件接口

```typescript
// StageController.tsx
interface StageControllerProps {
  sessionId: string;
  taskId: string;
  stages: StageState[];
  currentStageIndex: number;
  onContinue: () => void;
  onRetry: (stageId: string) => void;
  onEditCode: (stageId: string, code: string) => void;
  onUpdateParams: (stageId: string, params: Record<string, any>) => void;
  onTerminate: () => void;
}
```

### 3.3 阶段参数编辑器

#### 3.3.1 功能说明

允许用户在阶段间修改下一阶段的参数，参数定义从任务 Meta 中获取。

#### 3.3.2 组件接口

```typescript
// StageParameterEditor.tsx
interface StageParameterEditorProps {
  stageId: string;
  stageName: string;
  parameters: ParameterDefinition[];
  values: Record<string, any>;
  onChange: (values: Record<string, any>) => void;
  disabled?: boolean;
}

interface ParameterDefinition {
  name: string;
  type: "number" | "string" | "boolean" | "select";
  label: string;
  description?: string;
  default: any;
  options?: { label: string; value: any }[];  // for select type
  min?: number;  // for number type
  max?: number;
  step?: number;
}
```

### 3.4 阶段代码编辑器

#### 3.4.1 功能说明

- 显示 AI 生成的代码
- 支持用户编辑
- 编辑后可重新执行
- 基于 Monaco Editor（复用原项目能力）

#### 3.4.2 UI 设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 阶段代码编辑器 - WOE分箱                              [重置] [执行 ▶]  │
├─────────────────────────────────────────────────────────────────────────┤
│  1 │ # WOE分箱代码                                                     │
│  2 │ import pandas as pd                                               │
│  3 │ from toad import transform                                        │
│  4 │                                                                   │
│  5 │ # 加载数据                                                        │
│  6 │ df = pd.read_csv('data.csv')                                      │
│  7 │                                                                   │
│  8 │ # WOE转换                                                         │
│  9 │ transformer = transform.WOETransformer()                          │
│ 10 │ df_woe = transformer.fit_transform(df, target='label')            │
│ 11 │                                                                   │
│ 12 │ # 保存结果                                                        │
│ 13 │ df_woe.to_csv('woe_result.csv', index=False)                      │
│    │                                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│ 执行结果:                                                               │
│ ┌─────────────────────────────────────────────────────────────────────┐│
│ │ [2024-01-15 10:30:15] 开始执行...                                   ││
│ │ [2024-01-15 10:30:16] WOE转换完成，处理15个变量                     ││
│ │ [2024-01-15 10:30:16] 结果已保存至 woe_result.csv                   ││
│ │ [2024-01-15 10:30:16] 执行成功 ✅                                   ││
│ └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

#### 3.4.3 组件接口

```typescript
// StageCodeEditor.tsx
interface StageCodeEditorProps {
  stageId: string;
  stageName: string;
  originalCode: string;
  onExecute: (code: string) => Promise<ExecutionResult>;
  onReset: () => void;
  isExecuting?: boolean;
}

interface ExecutionResult {
  success: boolean;
  output: string;
  error?: string;
  artifacts?: string[];  // 生成的文件列表
}
```

### 3.5 阶段结果查看器

#### 3.5.1 功能说明

- 展示阶段执行结果
- 支持查看生成的文件
- 支持查看图表（如 WOE 分箱图、IV 表等）

#### 3.5.2 组件接口

```typescript
// StageResultViewer.tsx
interface StageResultViewerProps {
  stageId: string;
  stageName: string;
  result: StageResult;
  onViewFile: (filePath: string) => void;
}

interface StageResult {
  summary: string;
  metrics: Record<string, number | string>;
  artifacts: Artifact[];
  charts?: ChartData[];
}

interface Artifact {
  name: string;
  path: string;
  type: "csv" | "json" | "image" | "html" | "other";
  size: number;
}
```

### 3.6 阶段时间线

#### 3.6.1 UI 设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 执行进度                                                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ●───────●───────●───────◐───────○───────○                             │
│  │       │       │       │       │       │                             │
│  数据    特征    WOE    特征    模型    评分                           │
│  加载    工程    分箱    筛选    训练    刻度                           │
│  ✅      ✅      ✅      ⏸️      ⏳      ⏳                             │
│  1.2s    3.5s    5.8s   暂停中                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 3.6.2 组件接口

```typescript
// StageTimeline.tsx
interface StageTimelineProps {
  stages: StageState[];
  currentStageIndex: number;
  onStageClick: (stageIndex: number) => void;
}
```

---

## 四、后端 API 设计

### 4.1 API 列表

| 方法 | 路径 | 说明 | 模式 |
|------|------|------|------|
| POST | `/sop/execute` | 全自动执行（现有） | 全自动 |
| POST | `/sop/execute/stage` | 执行单个阶段 | 专家 |
| POST | `/sop/retry/stage` | 重试某个阶段 | 专家 |
| GET | `/sop/stage/result/{session_id}/{stage_id}` | 获取阶段结果 | 专家 |
| PUT | `/sop/stage/params` | 更新阶段参数 | 专家 |
| POST | `/sop/execute/code` | 执行编辑后的代码 | 专家 |
| GET | `/sop/session/state/{session_id}` | 获取会话状态 | 专家 |

### 4.2 API 详细设计

#### 4.2.1 执行单个阶段

```python
# POST /sop/execute/stage
class ExecuteStageRequest(BaseModel):
    session_id: str
    task_id: str
    stage_id: str
    parameters: Dict[str, Any] = {}

class ExecuteStageResponse(BaseModel):
    success: bool
    stage_id: str
    status: str  # "completed" | "failed"
    result: Optional[StageResult]
    error: Optional[str]
    next_stage_id: Optional[str]
    next_stage_params: Optional[Dict[str, Any]]
```

#### 4.2.2 重试阶段

```python
# POST /sop/retry/stage
class RetryStageRequest(BaseModel):
    session_id: str
    task_id: str
    stage_id: str
    parameters: Optional[Dict[str, Any]] = None  # 可选，覆盖原参数

class RetryStageResponse(BaseModel):
    success: bool
    stage_id: str
    status: str
    result: Optional[StageResult]
    error: Optional[str]
```

#### 4.2.3 更新阶段参数

```python
# PUT /sop/stage/params
class UpdateStageParamsRequest(BaseModel):
    session_id: str
    task_id: str
    stage_id: str
    parameters: Dict[str, Any]

class UpdateStageParamsResponse(BaseModel):
    success: bool
    stage_id: str
    updated_params: Dict[str, Any]
```

#### 4.2.4 执行编辑后的代码

```python
# POST /sop/execute/code
class ExecuteCodeRequest(BaseModel):
    session_id: str
    task_id: str
    stage_id: str
    code: str

class ExecuteCodeResponse(BaseModel):
    success: bool
    output: str
    error: Optional[str]
    artifacts: List[str]  # 生成的文件列表
```

#### 4.2.5 获取会话状态

```python
# GET /sop/session/state/{session_id}
class SessionStateResponse(BaseModel):
    session_id: str
    task_id: str
    interaction_mode: str  # "auto" | "expert"（交互模式）
    current_stage_index: int
    stages: List[StageState]
    started_at: datetime
    updated_at: datetime
```

> **命名约定**：使用 `interaction_mode` 表示交互模式（auto/expert），与 `engine_mode`（pipeline/llm_sop）正交。

### 4.3 阶段状态机

```python
# stage_state_machine.py

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class StageState:
    stage_id: str
    stage_name: str
    status: StageStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    parameters: Dict[str, Any] = None
    result: Optional[Dict[str, Any]] = None
    generated_code: Optional[str] = None
    error: Optional[str] = None

class StageStateMachine:
    """阶段状态机，管理专家模式下的阶段执行流程"""
    
    def __init__(self, session_id: str, task_id: str, stages: List[str]):
        self.session_id = session_id
        self.task_id = task_id
        self.stages: Dict[str, StageState] = {}
        self.current_stage_index = 0
        self.interaction_mode = "expert"  # 交互模式（auto/expert）
        
        # 初始化所有阶段
        for i, stage_name in enumerate(stages):
            stage_id = f"stage_{i}"
            self.stages[stage_id] = StageState(
                stage_id=stage_id,
                stage_name=stage_name,
                status=StageStatus.PENDING,
                parameters={}
            )
    
    def start_stage(self, stage_id: str) -> bool:
        """开始执行阶段"""
        if stage_id not in self.stages:
            return False
        stage = self.stages[stage_id]
        if stage.status not in [StageStatus.PENDING, StageStatus.PAUSED, StageStatus.FAILED]:
            return False
        stage.status = StageStatus.RUNNING
        stage.start_time = datetime.now()
        return True
    
    def complete_stage(self, stage_id: str, result: Dict[str, Any], code: str = None) -> bool:
        """完成阶段"""
        if stage_id not in self.stages:
            return False
        stage = self.stages[stage_id]
        stage.status = StageStatus.COMPLETED
        stage.end_time = datetime.now()
        stage.result = result
        stage.generated_code = code
        return True
    
    def pause_stage(self, stage_id: str) -> bool:
        """暂停阶段（等待用户操作）"""
        if stage_id not in self.stages:
            return False
        stage = self.stages[stage_id]
        stage.status = StageStatus.PAUSED
        return True
    
    def fail_stage(self, stage_id: str, error: str) -> bool:
        """阶段失败"""
        if stage_id not in self.stages:
            return False
        stage = self.stages[stage_id]
        stage.status = StageStatus.FAILED
        stage.end_time = datetime.now()
        stage.error = error
        return True
    
    def retry_stage(self, stage_id: str, new_params: Dict[str, Any] = None) -> bool:
        """重试阶段"""
        if stage_id not in self.stages:
            return False
        stage = self.stages[stage_id]
        stage.status = StageStatus.PENDING
        stage.start_time = None
        stage.end_time = None
        stage.result = None
        stage.error = None
        if new_params:
            stage.parameters.update(new_params)
        
        # 清除后续阶段的结果
        self._clear_subsequent_stages(stage_id)
        return True
    
    def update_params(self, stage_id: str, params: Dict[str, Any]) -> bool:
        """更新阶段参数"""
        if stage_id not in self.stages:
            return False
        self.stages[stage_id].parameters.update(params)
        return True
    
    def _clear_subsequent_stages(self, stage_id: str):
        """清除指定阶段之后所有阶段的结果"""
        stage_ids = list(self.stages.keys())
        start_clearing = False
        for sid in stage_ids:
            if sid == stage_id:
                start_clearing = True
                continue
            if start_clearing:
                stage = self.stages[sid]
                stage.status = StageStatus.PENDING
                stage.start_time = None
                stage.end_time = None
                stage.result = None
                stage.generated_code = None
                stage.error = None
    
    def get_current_stage(self) -> Optional[StageState]:
        """获取当前阶段"""
        stage_ids = list(self.stages.keys())
        if self.current_stage_index < len(stage_ids):
            return self.stages[stage_ids[self.current_stage_index]]
        return None
    
    def get_next_stage(self) -> Optional[StageState]:
        """获取下一阶段"""
        stage_ids = list(self.stages.keys())
        next_index = self.current_stage_index + 1
        if next_index < len(stage_ids):
            return self.stages[stage_ids[next_index]]
        return None
    
    def advance_to_next_stage(self) -> bool:
        """推进到下一阶段"""
        stage_ids = list(self.stages.keys())
        if self.current_stage_index + 1 < len(stage_ids):
            self.current_stage_index += 1
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "interaction_mode": self.interaction_mode,  # 交互模式
            "current_stage_index": self.current_stage_index,
            "stages": [
                {
                    "stage_id": s.stage_id,
                    "stage_name": s.stage_name,
                    "status": s.status.value,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "parameters": s.parameters,
                    "result": s.result,
                    "generated_code": s.generated_code,
                    "error": s.error
                }
                for s in self.stages.values()
            ]
        }
```

### 4.4 阶段结果存储

```python
# stage_result_store.py

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

class StageResultStore:
    """阶段结果持久化存储"""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.store_dir = os.path.join(workspace_dir, ".sop_results")
        os.makedirs(self.store_dir, exist_ok=True)
    
    def save_stage_result(
        self, 
        session_id: str, 
        stage_id: str, 
        result: Dict[str, Any],
        code: str = None
    ) -> str:
        """保存阶段结果"""
        result_file = os.path.join(
            self.store_dir, 
            f"{session_id}_{stage_id}.json"
        )
        data = {
            "session_id": session_id,
            "stage_id": stage_id,
            "result": result,
            "code": code,
            "saved_at": datetime.now().isoformat()
        }
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return result_file
    
    def load_stage_result(
        self, 
        session_id: str, 
        stage_id: str
    ) -> Optional[Dict[str, Any]]:
        """加载阶段结果"""
        result_file = os.path.join(
            self.store_dir, 
            f"{session_id}_{stage_id}.json"
        )
        if not os.path.exists(result_file):
            return None
        with open(result_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def delete_stage_result(self, session_id: str, stage_id: str) -> bool:
        """删除阶段结果"""
        result_file = os.path.join(
            self.store_dir, 
            f"{session_id}_{stage_id}.json"
        )
        if os.path.exists(result_file):
            os.remove(result_file)
            return True
        return False
    
    def clear_session_results(self, session_id: str) -> int:
        """清除会话所有结果"""
        count = 0
        for filename in os.listdir(self.store_dir):
            if filename.startswith(f"{session_id}_"):
                os.remove(os.path.join(self.store_dir, filename))
                count += 1
        return count
```

---

## 五、前端状态管理

### 5.1 状态定义

```typescript
// types/sop-expert.ts

export type InteractionMode = "auto" | "expert";  // 交互模式

export type StageStatus = 
  | "pending" 
  | "running" 
  | "paused" 
  | "completed" 
  | "failed" 
  | "skipped";

export interface StageState {
  stageId: string;
  stageName: string;
  status: StageStatus;
  startTime?: string;
  endTime?: string;
  parameters: Record<string, any>;
  result?: StageResult;
  generatedCode?: string;
  error?: string;
}

export interface StageResult {
  summary: string;
  metrics: Record<string, number | string>;
  artifacts: Artifact[];
  charts?: ChartData[];
}

export interface Artifact {
  name: string;
  path: string;
  type: "csv" | "json" | "image" | "html" | "other";
  size: number;
}

export interface SOPExpertState {
  sessionId: string;
  taskId: string;
  interactionMode: InteractionMode;  // 交互模式
  currentStageIndex: number;
  stages: StageState[];
  isExecuting: boolean;
  error?: string;
}
```

### 5.2 状态管理 Hook

```typescript
// hooks/useSOPExpertMode.ts

import { useState, useCallback } from "react";
import { SOPExpertState, StageState, InteractionMode } from "@/types/sop-expert";

export function useSOPExpertMode(sessionId: string, taskId: string) {
  const [state, setState] = useState<SOPExpertState>({
    sessionId,
    taskId,
    interactionMode: "auto",  // 默认全自动
    currentStageIndex: 0,
    stages: [],
    isExecuting: false,
  });

  // 设置交互模式
  const setInteractionMode = useCallback((mode: InteractionMode) => {
    setState(prev => ({ ...prev, interactionMode: mode }));
  }, []);

  // 初始化阶段
  const initializeStages = useCallback((stages: StageState[]) => {
    setState(prev => ({ ...prev, stages, currentStageIndex: 0 }));
  }, []);

  // 执行当前阶段
  const executeCurrentStage = useCallback(async () => {
    const currentStage = state.stages[state.currentStageIndex];
    if (!currentStage) return;

    setState(prev => ({ ...prev, isExecuting: true }));

    try {
      const response = await fetch("/api/sop/execute/stage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          task_id: taskId,
          stage_id: currentStage.stageId,
          parameters: currentStage.parameters,
        }),
      });

      const result = await response.json();

      if (result.success) {
        setState(prev => ({
          ...prev,
          stages: prev.stages.map((s, i) =>
            i === prev.currentStageIndex
              ? { ...s, status: "paused", result: result.result, generatedCode: result.code }
              : s
          ),
          isExecuting: false,
        }));
      } else {
        setState(prev => ({
          ...prev,
          stages: prev.stages.map((s, i) =>
            i === prev.currentStageIndex
              ? { ...s, status: "failed", error: result.error }
              : s
          ),
          isExecuting: false,
          error: result.error,
        }));
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        isExecuting: false,
        error: String(error),
      }));
    }
  }, [state.stages, state.currentStageIndex, sessionId, taskId]);

  // 继续下一阶段
  const continueToNextStage = useCallback(() => {
    setState(prev => {
      const nextIndex = prev.currentStageIndex + 1;
      if (nextIndex >= prev.stages.length) return prev;

      return {
        ...prev,
        stages: prev.stages.map((s, i) =>
          i === prev.currentStageIndex
            ? { ...s, status: "completed" }
            : s
        ),
        currentStageIndex: nextIndex,
      };
    });
  }, []);

  // 重试当前阶段
  const retryCurrentStage = useCallback(async (newParams?: Record<string, any>) => {
    const currentStage = state.stages[state.currentStageIndex];
    if (!currentStage) return;

    setState(prev => ({ ...prev, isExecuting: true }));

    try {
      const response = await fetch("/api/sop/retry/stage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          task_id: taskId,
          stage_id: currentStage.stageId,
          parameters: newParams,
        }),
      });

      const result = await response.json();

      if (result.success) {
        setState(prev => ({
          ...prev,
          stages: prev.stages.map((s, i) =>
            i === prev.currentStageIndex
              ? { 
                  ...s, 
                  status: "paused", 
                  result: result.result, 
                  generatedCode: result.code,
                  parameters: newParams || s.parameters,
                  error: undefined,
                }
              : i > prev.currentStageIndex
              ? { ...s, status: "pending", result: undefined, generatedCode: undefined }
              : s
          ),
          isExecuting: false,
        }));
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        isExecuting: false,
        error: String(error),
      }));
    }
  }, [state.stages, state.currentStageIndex, sessionId, taskId]);

  // 更新阶段参数
  const updateStageParams = useCallback((stageIndex: number, params: Record<string, any>) => {
    setState(prev => ({
      ...prev,
      stages: prev.stages.map((s, i) =>
        i === stageIndex ? { ...s, parameters: { ...s.parameters, ...params } } : s
      ),
    }));
  }, []);

  // 执行编辑后的代码
  const executeEditedCode = useCallback(async (code: string) => {
    const currentStage = state.stages[state.currentStageIndex];
    if (!currentStage) return;

    setState(prev => ({ ...prev, isExecuting: true }));

    try {
      const response = await fetch("/api/sop/execute/code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          task_id: taskId,
          stage_id: currentStage.stageId,
          code,
        }),
      });

      const result = await response.json();

      setState(prev => ({
        ...prev,
        stages: prev.stages.map((s, i) =>
          i === prev.currentStageIndex
            ? { 
                ...s, 
                generatedCode: code,
                result: result.success ? { ...s.result, output: result.output } : s.result,
                error: result.error,
              }
            : s
        ),
        isExecuting: false,
      }));

      return result;
    } catch (error) {
      setState(prev => ({
        ...prev,
        isExecuting: false,
        error: String(error),
      }));
    }
  }, [state.stages, state.currentStageIndex, sessionId, taskId]);

  // 终止执行
  const terminate = useCallback(() => {
    setState(prev => ({
      ...prev,
      isExecuting: false,
      stages: prev.stages.map(s =>
        s.status === "running" ? { ...s, status: "failed", error: "用户终止" } : s
      ),
    }));
  }, []);

  return {
    state,
    setInteractionMode,  // 设置交互模式
    initializeStages,
    executeCurrentStage,
    continueToNextStage,
    retryCurrentStage,
    updateStageParams,
    executeEditedCode,
    terminate,
  };
}
```

---

## 六、可复用的原项目能力

### 6.1 后端工具函数

| 函数/类 | 位置 | 用途 | 复用方式 |
|---------|------|------|---------|
| `execute_code_safe()` | `API/utils.py` | 安全执行 Python 代码 | 直接调用 |
| `execute_code_safe_async()` | `API/utils.py` | 异步执行代码 | 直接调用 |
| `WorkspaceTracker` | `API/utils.py` | 跟踪文件变化 | 直接实例化 |
| `extract_code_from_segment()` | `API/utils.py` | 从 `<Code>` 标签提取代码 | 直接调用 |
| `render_file_block()` | `API/utils.py` | 渲染文件输出块 | 直接调用 |

### 6.2 前端组件

| 组件 | 位置 | 用途 | 复用方式 |
|------|------|------|---------|
| Monaco Editor | `three-panel-interface.tsx` | 代码编辑器 | 抽取为独立组件 |
| CodeBlock 渲染逻辑 | `three-panel-interface.tsx` | 代码块展示 | 抽取为独立组件 |

---

## 七、分阶段实施计划

### Phase 1: 基础框架（预计 3-5 天）✅ 已完成

**目标**：实现模式选择 + 阶段暂停/继续

**前端任务**：
- [x] 创建 `ModeSelector.tsx`（执行模式选择器）
- [x] 创建 `SopStageController.tsx`（阶段卡片，含专家模式控制面板，原名PipelineStageCards）
- [x] ~~创建 `ExpertStageController.tsx`~~（已废弃，功能已合并到SopStageController和StageOutputPreview）
- [x] 修改配置面板，集成模式选择器
- [x] 在 `three-panel-interface.tsx` 中集成专家模式

**后端任务**：
- [x] 创建 `stage_state_machine.py`
- [x] 创建 `expert_executor.py`
- [x] 实现统一的专家模式暂停逻辑 `check_expert_mode_pause()`
- [x] 在 `executor.py` 的 `_update_progress` 中集成暂停逻辑
- [x] 在 `llm_sop_executor.py` 的 `_update_stage_status` 中集成暂停逻辑

**关键实现：统一暂停逻辑**

```python
# executor.py - 公共函数
def check_expert_mode_pause(
    context: ExecutionContext,
    stage_id: str,
    registry: SOPRegistry | None = None
) -> bool:
    """
    统一的专家模式暂停逻辑，供Pipeline和LLM-SOP模式共同使用。
    
    - 检查是否为专家模式
    - 检查是否还有后续阶段
    - 设置TaskController暂停信号
    - 更新阶段消息和日志
    """
```

**架构图**：
```
┌─────────────────────────────────────────────────────────────┐
│                  check_expert_mode_pause()                  │
│                     (公共函数)                              │
└─────────────────────────────────────────────────────────────┘
                    ▲                    ▲
                    │                    │
        ┌───────────┴───────────┐ ┌──────┴──────────────┐
        │  SOPExecutor          │ │  LLMSOPExecutor     │
        │  _update_progress()   │ │  _update_stage_status()│
        │  (Pipeline模式)       │ │  (LLM-SOP模式)       │
        └───────────────────────┘ └─────────────────────┘
```

### Phase 2: 参数调整（预计 2-3 天）✅ 已完成

**目标**：支持阶段间参数修改 + 阶段重试

**前端任务**：
- [x] 创建 `StageOutputPreview.tsx`（阶段输出预览，集成参数/代码编辑、重试功能）
- [x] 创建 `StageParameterEditor.tsx`（复用 Monaco Editor）

**后端任务**：
- [x] 实现任务控制API（暂停/继续/停止）
- [x] 参数更新通过 `onUpdateParams` 回调处理（无需独立API）
- [x] 阶段重试通过 `onResetStage` 回调处理（无需独立API）

**实现说明**：
- 参数编辑器 `StageParameterEditor.tsx` 复用原项目 Monaco Editor 配置
- 支持 JSON 格式编辑，实时验证格式正确性
- 阶段重试逻辑已集成到 `StageOutputPreview.tsx`

### Phase 3: 代码编辑（预计 3-5 天）✅ 已完成

**目标**：支持代码编辑 + 重新执行（仅LLM-SOP模式）

**前端任务**：
- [x] 在 `StageOutputPreview.tsx` 中根据 `engineMode` 区分代码可编辑性
- [x] 创建 `StageCodeEditor.tsx`（复用原项目 Monaco Editor 配置）
- [x] 集成代码执行结果展示（复用原项目 `/execute/code` API）

**后端任务**：
- [x] 复用现有 `/execute/code` API（无需新建）
- [x] 复用现有 `execute_code_safe()` 和 `WorkspaceTracker`

**实现说明**：
- 代码编辑器 `StageCodeEditor.tsx` 完全复用原项目 Monaco Editor 配置
- Pipeline模式：代码只读展示，不可编辑和执行
- LLM-SOP模式：代码可编辑，支持 Run 按钮执行
- 执行结果展示区与原项目 Code 列保持一致的 UI 风格

---

## 八、测试计划

### 8.1 单元测试

- [ ] `StageStateMachine` 状态转换测试
- [ ] `StageResultStore` 存储/读取测试
- [ ] API 端点测试

### 8.2 集成测试

- [ ] 全自动模式执行流程测试
- [ ] 专家模式完整流程测试
- [ ] 阶段重试后后续阶段清除测试
- [ ] 代码编辑后执行测试

### 8.3 UI 测试

- [ ] 模式切换 UI 测试
- [ ] 阶段控制面板交互测试
- [ ] 参数编辑器表单验证测试
- [ ] 代码编辑器功能测试

---

## 九、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 状态丢失 | 用户调整后数据丢失 | 每阶段自动保存到 `.sop_results/` |
| 交互复杂 | 用户困惑 | 默认全自动，专家模式为高级选项 |
| 阶段依赖 | 修改前序阶段导致后续失效 | 重试时自动清除后续阶段结果 |
| 代码执行安全 | 恶意代码风险 | 复用 `execute_code_safe()` 沙箱机制 |
| 长时间执行 | 用户等待焦虑 | 显示阶段进度和预估时间 |

---

## 十、附录

### A. 任务阶段定义

#### A.1 规则挖掘任务阶段

> 与 `rule_mining_meta.py` 中的 `stages` 定义保持一致

| 阶段ID | 阶段名称 | 可调参数 |
|--------|---------|---------|
| preprocessing | 数据预处理 | id_cols, drop_cols, name_mapping, categorical_cols |
| feature_engineering | 特征工程（可选） | enable_feature_engineering, missing_threshold, iv_threshold |
| generating_rules | 规则生成 | mining_mode, n_bins, bin_method, n_vars, max_depth |
| rule_filtering | 规则过滤 | score_vars, score_direction, min_lift_filter, max_hit_rate_filter |
| selecting_rules | 最优选择 | allow_overlap, max_hit_rate_select, min_recall_ruleset, min_bad_rate_ruleset, max_bad_rate_ruleset, min_lift_ruleset |
| report_generation | 报告生成 | 输出格式 |

#### A.2 评分卡开发任务阶段

> 与 `scorecard_meta.py` 中的 `stages` 定义保持一致

| 阶段ID | 阶段名称 | 可调参数 |
|--------|---------|---------|
| data_loading | 数据加载 | 数据文件、目标列、权重列 |
| woe_binning | WOE分箱 | 分箱方法、最大分箱数 |
| feature_selection | 特征筛选 | IV阈值、VIF阈值、相关系数阈值 |
| model_training | 模型训练 | use_stepwise, stepwise_direction, significance_level, **significance_mode**, **coefficient_direction_mode**, **max_validation_iterations** |
| score_scaling | 评分刻度 | 基准分、基准Odds、PDO |
| model_evaluation | 模型评估 | 评估指标 |
| report_generation | 报告生成 | 输出格式 |

> **v4.3更新**：逐步回归相关参数（use_stepwise, stepwise_direction, significance_level）从阶段3迁移至阶段4，并新增验证模式参数（significance_mode, coefficient_direction_mode, max_validation_iterations）

### B. 文件结构

```
deepanalyze/
├── analysis/
│   └── task_SOP/
│       ├── stage_state_machine.py    # 新增
│       ├── stage_result_store.py     # 新增
│       ├── expert_mode_executor.py   # 新增
│       └── ...
│
demo/chat/
├── components/
│   └── sop/
│       ├── expert/                   # 新增目录
│       │   ├── ExecutionModeSelector.tsx
│       │   ├── StageController.tsx
│       │   ├── StageParameterEditor.tsx
│       │   ├── StageCodeEditor.tsx
│       │   ├── StageResultViewer.tsx
│       │   ├── StageTimeline.tsx
│       │   └── index.ts
│       └── ...
├── hooks/
│   └── useSOPExpertMode.ts           # 新增
└── types/
    └── sop-expert.ts                 # 新增
```

### C. 实际实现的文件结构（更新于2025-12-16）

```
deepanalyze/analysis/task_SOP/
├── executor.py                      # 添加 check_expert_mode_pause() 公共函数
├── llm_sop_executor.py              # 集成统一暂停逻辑
├── expert_mode/
│   ├── stage_state_machine.py       # 阶段状态机
│   └── expert_executor.py           # 专家模式执行器
└── __init__.py                      # 导出 check_expert_mode_pause

demo/chat/components/sop/
├── ModeSelector.tsx                 # 执行模式选择器（engine_mode + interaction_mode）
├── SopStageController.tsx           # 阶段卡片+控制面板（原PipelineStageCards，支持跳过阶段）
├── StageCodeEditor.tsx              # 代码编辑器（复用原项目 Monaco Editor）
├── StageParameterEditor.tsx         # 参数编辑器（JSON 格式）
├── StageOutputPreview.tsx           # 阶段输出预览（集成参数/代码编辑、重试功能）
└── index.ts                         # 导出
```

---

**文档版本**: v1.4  
**创建日期**: 2025-12-11  
**更新日期**: 2026-02-04  
**作者**: AI Assistant  
**状态**: Phase 1-3 全部已完成 ✅

**更新记录**：
- v1.4 (2026-02-04): 更新附录A.2评分卡阶段参数列表，反映方案1迁移和方案B+新增参数
- v1.3 (2025-12-19): 更新执行引擎关系说明，LLM SOP执行模式已废弃
- v1.2 (2025-12-16): Phase 2-3 完成，新增 StageCodeEditor 和 StageParameterEditor 组件
- v1.1 (2025-12-16): 更新实施状态，添加统一暂停逻辑说明，更新实际文件结构
