# DeepAnalyze LLM + Pipeline 架构设计文档

> **文档目的**：LLM 作为智能入口，Pipeline 作为唯一执行引擎的架构设计，以及 Code 栏展示优化方案。
>
> **创建日期**：2024-12-19
>
> **更新日期**：2026-03-02（移除 LLM SOP 废弃相关内容，简化文档）
>
> **状态**：✅ 已实现

---

## 目录

1. [背景与现状分析](#一背景与现状分析)
2. [架构设计](#二架构设计)
3. [Code 栏展示优化方案](#三code-栏展示优化方案)
4. [实施路径与计划](#四实施路径与计划)
5. [风险评估与应对](#五风险评估与应对)

---

## 一、背景与现状分析

### 1.1 系统架构

DeepAnalyze 任务 SOP 模块采用统一架构：

| 组件 | 实现文件 | 角色 |
|------|----------|------|
| **Pipeline 执行引擎** | `executor.py` | 唯一执行引擎，执行路径确定，运行时可预测 |
| **LLM 参数推断器** | `llm_param_extractor.py` | 智能入口，从自然语言理解用户意图，推断任务参数 |

### 1.2 现有入口与交互方式

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户入口                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │   SOP 界面入口   │              │   Chat 界面入口  │          │
│  │  (左侧任务选项卡) │              │  (自然语言对话)  │          │
│  └────────┬────────┘              └────────┬────────┘          │
│           │                                 │                   │
│           ▼                                 ▼                   │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │  参数配置面板    │              │   LLM 参数推断   │          │
│  │  (表单式配置)    │              │  (从对话中提取)  │          │
│  └────────┬────────┘              └────────┬────────┘          │
│           │                                 │                   │
│           ▼                                 ▼                   │
│  ┌─────────────────────────────────────────────────┐           │
│  │              Pipeline 执行引擎                   │           │
│  │         (rule_mining.py / scorecard.py)         │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 核心问题识别

| 问题类别 | 具体问题 | 影响程度 |
|----------|----------|----------|
| **架构复杂性** | 两套执行模式并行维护，代码重复 | 高 |
| **LLM SOP 稳定性** | 动态决策导致执行路径不可控 | 高 |
| **Code 栏可见性** | 自动模式下仅展示结果，过程不透明 | 中 |
| **用户学习成本** | 两种模式差异大，用户困惑 | 中 |

---

## 二、架构设计

### 2.1 架构设计原则

| 原则 | 说明 |
|------|------|
| **统一执行引擎** | Pipeline 作为唯一执行引擎，确保执行确定性和可靠性 |
| **智能入口** | LLM 作为智能入口，负责从自然语言理解用户意图，推断任务参数 |
| **透明度** | 实时展示执行过程和等效代码，提升用户体验 |

### 2.2 架构对比

| 维度 | 原方案（设想的 LLM SOP） | 当前架构（LLM + Pipeline） |
|------|------------------------|---------------------------|
| **执行确定性** | ❌ 低（动态决策） | ✅ 高（预定义路径） |
| **错误可追溯性** | ❌ 难（LLM 黑盒） | ✅ 易（明确阶段） |
| **性能开销** | ❌ 高（多次 LLM 调用） | ✅ 低（直接执行） |
| **代码安全性** | ❌ 需沙箱（动态生成） | ✅ 预审核代码 |
| **维护成本** | ❌ 高（两套逻辑） | ✅ 低（统一引擎） |
| **LLM 调用次数** | ❌ 每阶段需调用 | ✅ 仅参数推断时调用 |

### 2.3 当前架构实现

当前已实现 LLM 作为智能入口、Pipeline 作为唯一执行引擎的架构：

| 组件 | 状态 | 说明 |
|------|------|------|
| `LLMParamExtractor` | ✅ 已实现 | 从自然语言推断任务参数 |
| `TaskRouter` | ✅ 已实现 | 路由用户请求到对应 Pipeline |
| `Pipeline Executor` | ✅ 已实现 | 统一的任务执行引擎 |
| 代码安全沙箱 | ✅ 已实现 | 用于代码执行安全（`sandbox_fusion.py`）|


## 三、LLM+Pipeline 架构设计

### 3.1 架构设计目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| **统一执行引擎** | 只保留 Pipeline 模式作为执行引擎 | P0 |
| **保留 LLM 价值** | LLM 作为"智能入口"而非"执行引擎" | P0 |
| **提升透明度** | 实时展示执行过程和等效代码 | P1 |
| **简化维护** | 减少代码重复，统一测试策略 | P1 |

### 3.2 新架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LLM + Pipeline 新架构                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                         入口层 (Entry Layer)                       │ │
│  │  ┌─────────────────────┐       ┌─────────────────────┐           │ │
│  │  │   SOP 界面入口       │       │   Chat 界面入口      │           │ │
│  │  │  (表单式参数配置)    │       │  (自然语言对话)      │           │ │
│  │  └──────────┬──────────┘       └──────────┬──────────┘           │ │
│  │             │                              │                       │ │
│  │             │                              ▼                       │ │
│  │             │                   ┌─────────────────────┐           │ │
│  │             │                   │   LLM 参数推断器    │           │ │
│  │             │                   │  (Intent + Params)  │           │ │
│  │             │                   └──────────┬──────────┘           │ │
│  │             │                              │                       │ │
│  │             ▼                              ▼                       │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │              统一参数验证 & 任务路由                          │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│                                    ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      执行层 (Execution Layer)                      │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │                   Pipeline 执行引擎                          │ │ │
│  │  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐    │ │ │
│  │  │  │ Stage 1 │──▶│ Stage 2 │──▶│ Stage 3 │──▶│ Stage N │    │ │ │
│  │  │  └─────────┘   └─────────┘   └─────────┘   └─────────┘    │ │ │
│  │  │       │             │             │             │          │ │ │
│  │  │       ▼             ▼             ▼             ▼          │ │ │
│  │  │  ┌─────────────────────────────────────────────────────┐  │ │ │
│  │  │  │              实时事件流 (Event Stream)               │  │ │ │
│  │  │  │  • 阶段开始/完成事件                                 │  │ │ │
│  │  │  │  • 伪代码片段                                        │  │ │ │
│  │  │  │  • 进度更新                                          │  │ │ │
│  │  │  │  • 结果预览                                          │  │ │ │
│  │  │  └─────────────────────────────────────────────────────┘  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│                                    ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                       输出层 (Output Layer)                        │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │ │
│  │  │   结果数据       │  │   等效代码       │  │   LLM 解释      │   │ │
│  │  │  (DataFrame)    │  │  (可复制执行)    │  │  (自然语言)     │   │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 核心组件设计

#### 3.3.1 LLM 参数推断器

**职责**：从自然语言对话中提取任务意图和参数

```python
# llm_param_extractor.py (新增)

from dataclasses import dataclass
from typing import Optional

@dataclass
class TaskIntent:
    """任务意图识别结果"""
    task_type: str  # 任务类型 ID，如 "rule_mining", "scorecard_dev"
    confidence: float  # 置信度 0-1
    params: dict  # 提取的参数
    missing_params: list[str]  # 缺失的必需参数
    clarification_needed: bool  # 是否需要用户澄清


class LLMParamExtractor:
    """LLM 参数推断器
    
    使用 LLM 从自然语言中提取任务参数，而非动态生成执行代码。
    这是 LLM SOP 模式废弃后，LLM 能力的新定位。
    """
    
    EXTRACTION_PROMPT_TEMPLATE = '''
你是一个参数提取助手。根据用户的请求，识别任务类型并提取相关参数。

可用的任务类型：
{task_definitions}

用户请求：
{user_message}

当前工作区文件：
{workspace_files}

请以 JSON 格式返回：
{{
    "task_type": "任务类型ID",
    "confidence": 0.95,
    "params": {{
        "target": "目标变量名",
        "force_categorical": ["列名1", "列名2"],
        ...
    }},
    "missing_params": ["缺失的必需参数"],
    "clarification_needed": false,
    "clarification_question": "如果需要澄清，这里是问题"
}}
'''
    
    async def extract(
        self,
        user_message: str,
        workspace_files: list[str],
        conversation_history: list[dict]
    ) -> TaskIntent:
        """从用户消息中提取任务意图和参数"""
        # 构建 prompt
        prompt = self._build_prompt(user_message, workspace_files)
        
        # 调用 LLM
        response = await self._call_llm(prompt)
        
        # 解析响应
        return self._parse_response(response)
    
    def _build_prompt(self, user_message: str, workspace_files: list[str]) -> str:
        """构建提取 prompt"""
        from deepanalyze.analysis.task_SOP.registry import get_registry
        
        registry = get_registry()
        task_definitions = registry.get_all_task_summaries()
        
        return self.EXTRACTION_PROMPT_TEMPLATE.format(
            task_definitions=task_definitions,
            user_message=user_message,
            workspace_files="\n".join(workspace_files)
        )
```

#### 3.3.2 统一任务路由器

**职责**：验证参数并路由到 Pipeline 执行

```python
# task_router.py (新增)

class UnifiedTaskRouter:
    """统一任务路由器
    
    无论从 SOP 界面还是 Chat 界面进入，最终都通过此路由器
    调用 Pipeline 执行引擎。
    """
    
    async def route(
        self,
        task_type: str,
        params: dict,
        source: str,  # "sop_ui" | "chat"
        context: ExecutionContext
    ) -> ExecutionResult:
        """路由任务到 Pipeline 执行"""
        
        # 1. 参数验证
        validated_params = await self._validate_params(task_type, params)
        
        # 2. 记录来源（用于分析和调试）
        context.metadata["entry_source"] = source
        if source == "chat":
            context.metadata["llm_extracted"] = True
        
        # 3. 调用 Pipeline 执行
        executor = PipelineExecutor()
        result = await executor.execute(task_type, validated_params, context)
        
        # 4. 如果是 Chat 来源，生成自然语言解释
        if source == "chat":
            result.explanation = await self._generate_explanation(result)
        
        return result
```

#### 3.3.3 Pipeline 事件流增强

**职责**：实时推送执行过程信息

```python
# executor.py 增强

class PipelineExecutor:
    """Pipeline 执行器（增强版）"""
    
    async def execute_stage(self, stage: Stage, context: ExecutionContext):
        """执行单个阶段（增强事件推送）"""
        
        # 阶段开始事件
        await self._emit_event({
            "type": "stage_start",
            "stage_id": stage.id,
            "stage_name": stage.name,
            "pseudo_code": stage.generate_pseudo_code(),  # 新增：伪代码
            "params_used": stage.get_params_snapshot(),   # 新增：使用的参数
        })
        
        try:
            # 执行阶段
            result = await stage.run(context)
            
            # 阶段完成事件
            await self._emit_event({
                "type": "stage_complete",
                "stage_id": stage.id,
                "result_preview": self._create_preview(result),  # 结果预览
                "equivalent_code": stage.generate_equivalent_code(),  # 等效代码
                "execution_time_ms": stage.execution_time_ms,
            })
            
            return result
            
        except Exception as e:
            # 阶段失败事件
            await self._emit_event({
                "type": "stage_error",
                "stage_id": stage.id,
                "error": str(e),
                "traceback": traceback.format_exc(),
            })
            raise
```

### 3.4 两种入口的差异处理

| 维度 | SOP 界面入口 | Chat 界面入口 |
|------|-------------|---------------|
| **参数来源** | 表单直接输入 | LLM 从对话提取 |
| **参数验证** | 前端 + 后端双重验证 | 后端验证 + LLM 补充询问 |
| **执行引擎** | Pipeline（相同） | Pipeline（相同） |
| **结果展示** | 结构化数据 + 等效代码 | 结构化数据 + 等效代码 + 自然语言解释 |
| **Code 栏内容** | 阶段伪代码 + 等效代码 | LLM 推断过程 + 阶段伪代码 + 等效代码 |

### 3.5 两种模式的LLM价值定位

> **更新日期**: 2024-12-24

#### 3.5.1 核心原则

**LLM 的核心价值应集中在专家模式，全自动模式保持简洁高效。**

| 模式 | LLM 角色 | 说明 |
|------|---------|------|
| **全自动模式** | 辅助入口 | LLM 仅用于 Chat 入口的参数提取，执行过程无 LLM 干预 |
| **专家模式** | 核心辅助 | LLM 在每阶段提供结果分析、异常诊断、参数调优建议 |

#### 3.5.2 全自动模式的 LLM 价值分析

全自动模式下，LLM 的价值有限：
- **执行过程**：Pipeline 使用固定默认参数，LLM 不参与
- **结果解释**：任务结束后可单独询问 AI，无需集成
- **便捷性**：自然语言发起任务比填表单稍方便，但非核心价值

#### 3.5.3 "AI 分析评估"按钮设计

为满足全自动模式用户对结果解读的需求，在结果页提供**按需调用**的 AI 分析功能：

```
┌─────────────────────────────────────────────────────────────────┐
│  [← 返回]  [开发结果] [阶段详情]  [🧠 AI 分析评估]        [×]  │
│                                    ↑ 紫色渐变高亮按钮           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ AI 分析评估结果面板（点击按钮后展开）─────────────────────┐ │
│  │ 🧠 AI 分析评估                                    [×]    │ │
│  │ ┌─────────────────────────────────────────────────────┐  │ │
│  │ │ ## 整体评价                                         │  │ │
│  │ │ 模型KS值0.42，AUC 0.78，整体表现良好...             │  │ │
│  │ │                                                     │  │ │
│  │ │ ## 关键指标解读                                     │  │ │
│  │ │ ...                                                 │  │ │
│  │ └─────────────────────────────────────────────────────┘  │ │
│  │                              [🔄 重新分析] [📋 复制]     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  [原有的结果展示内容...]                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**按钮显示规则**：

| 模式 | 按钮状态 | 样式 | 原因 |
|------|---------|------|------|
| **全自动模式** | 可点击 | 紫色渐变高亮 | 核心功能入口，提供按需 AI 分析 |
| **专家模式** | 禁用 | 灰色 | 各阶段已包含 AI 分析，无需重复 |

**实现细节**：

| 特性 | 说明 |
|------|------|
| **显示条件** | 仅在"开发结果"视图 + 任务完成状态时显示 |
| **禁用条件** | `interactionMode === "expert"` 时禁用 |
| **提示文案** | 专家模式下悬停提示"专家模式下各阶段已包含AI分析" |
| **流式输出** | 调用 Chat API 流式返回，实时显示分析结果 |
| **分析内容** | 整体评价、指标解读、优势亮点、潜在问题、改进建议 |

**相关代码变更**：

| 文件 | 变更内容 |
|------|----------|
| `three-panel-interface.tsx` | +3 状态变量、+2 处理函数、+按钮和面板 UI |

```typescript
// 新增状态变量
const [isAIAnalyzing, setIsAIAnalyzing] = useState(false);
const [aiAnalysisResult, setAiAnalysisResult] = useState<string | null>(null);
const [showAIAnalysisPanel, setShowAIAnalysisPanel] = useState(false);

// 按钮禁用逻辑
<Button
  disabled={isAIAnalyzing || interactionMode === "expert"}
  title={interactionMode === "expert" 
    ? "专家模式下各阶段已包含AI分析" 
    : "对任务结果进行AI智能分析"}
  // ...
>
```

### 3.6 接口定义

#### 3.5.1 统一执行请求

```typescript
// 前端请求类型定义
interface UnifiedExecuteRequest {
  // 任务标识
  task_type: string;
  
  // 参数（SOP 入口直接提供，Chat 入口由 LLM 提取）
  params: Record<string, any>;
  
  // 入口来源
  source: "sop_ui" | "chat";
  
  // 交互模式
  interaction_mode: "auto" | "expert";
  
  // Chat 入口特有字段
  chat_context?: {
    user_message: string;
    conversation_history: ChatMessage[];
    llm_extraction_result?: TaskIntent;
  };
  
  // 数据文件
  file_path?: string;
  
  // 会话标识
  session_id: string;
}
```

#### 3.5.2 事件流类型

```typescript
// SSE 事件类型定义
type PipelineEvent = 
  | { type: "task_start"; task_id: string; stages: StageInfo[] }
  | { type: "stage_start"; stage_id: string; pseudo_code: string }
  | { type: "stage_progress"; stage_id: string; progress: number; message: string }
  | { type: "stage_complete"; stage_id: string; equivalent_code: string; result_preview: any }
  | { type: "stage_error"; stage_id: string; error: string }
  | { type: "task_complete"; final_result: any; full_code: string }
  | { type: "llm_extraction"; intent: TaskIntent }  // Chat 入口特有
  | { type: "llm_explanation"; explanation: string }; // Chat 入口特有
```

---

## 四、Code 栏展示优化方案

### 4.1 当前状态分析

**当前 Pipeline 自动模式 Code 栏展示**：
- 仅在阶段完成后展示阶段结果信息
- **未展示**各阶段生成的伪代码/等效代码
- 实时性不足，用户无法看到执行过程

### 4.2 优化目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| **过程透明** | 实时展示当前阶段的伪代码 | P0 |
| **代码可复现** | 提供可复制执行的等效代码 | P0 |
| **推断可见** | Chat 入口展示 LLM 参数推断过程 | P1 |
| **学习价值** | 帮助用户理解执行逻辑 | P2 |

### 4.3 Code 栏内容设计

#### 4.3.1 纯 Pipeline 模式（SOP 界面入口）

```python
# === 任务配置 ===
# 任务类型: 规则挖掘 (rule_mining)
# 数据文件: credit_data.csv
# 参数配置:
#   - target: "is_default"
#   - force_categorical: ["province_code", "city_code"]
#   - allow_overlap: True

# === 阶段 1: 数据预处理 ===
# 执行中...
df = load_data("credit_data.csv")
df = preprocess(df, 
    force_categorical=['province_code', 'city_code'],
    target='is_default'
)
# → 完成: 识别 15 个特征, 3 个分类变量
# → 耗时: 1.2s

# === 阶段 2: 特征筛选 ===
# 执行中...
selected_features = feature_selection(
    df,
    target='is_default',
    iv_threshold=0.02,
    vif_threshold=5.0
)
# → 完成: 筛选出 8 个有效特征
# → 耗时: 3.5s

# === 阶段 3: 规则生成 ===
# 执行中...
rules = generate_rules(
    df[selected_features + ['is_default']],
    target='is_default',
    max_depth=3,
    min_samples_leaf=100
)
# → 完成: 生成 12 条规则
# → 耗时: 5.8s

# === 完整等效代码 ===
# 以下代码可直接复制执行，复现本次分析结果

import pandas as pd
from deepanalyze.analysis.task_SOP.rule_mining import RuleMiningPipeline

# 加载数据
df = pd.read_csv("credit_data.csv")

# 配置参数
config = {
    "target": "is_default",
    "force_categorical": ["province_code", "city_code"],
    "allow_overlap": True,
    "iv_threshold": 0.02,
    "vif_threshold": 5.0,
    "max_depth": 3,
    "min_samples_leaf": 100
}

# 执行规则挖掘
pipeline = RuleMiningPipeline(config)
result = pipeline.run(df)

# 导出结果
result.rules.to_excel("rules_output.xlsx")
```

#### 4.3.2 LLM + Pipeline 模式（Chat 界面入口）

在纯 Pipeline 基础上**额外展示** LLM 推断过程：

```python
# === LLM 参数推断 ===
# 用户请求: "帮我做规则挖掘，目标变量是is_default，省份和城市代码是分类变量"
# 
# 推断结果:
#   - task_type: "rule_mining" (置信度: 0.95)
#   - target: "is_default" (从请求中提取)
#   - force_categorical: ["province_code", "city_code"] (从请求中提取)
#   - allow_overlap: True (使用默认值)
#
# 调用 Pipeline:
# start_rule_mining_task(
#     target="is_default",
#     force_categorical=["province_code", "city_code"],
#     interaction_mode="auto"
# )

# === 阶段 1: 数据预处理 ===
# ... (同纯 Pipeline 模式)
```

### 4.4 实现方案

#### 4.4.1 阶段伪代码生成器

```python
# code_templates.py 增强

class StageCodeGenerator:
    """阶段伪代码生成器"""
    
    @staticmethod
    def generate_pseudo_code(stage_id: str, params: dict) -> str:
        """生成阶段伪代码"""
        templates = {
            "data_preprocessing": '''
df = load_data("{file_path}")
df = preprocess(df, 
    force_categorical={force_categorical},
    target='{target}'
)''',
            "feature_selection": '''
selected_features = feature_selection(
    df,
    target='{target}',
    iv_threshold={iv_threshold},
    vif_threshold={vif_threshold}
)''',
            "rule_generation": '''
rules = generate_rules(
    df[selected_features + ['{target}']],
    target='{target}',
    max_depth={max_depth},
    min_samples_leaf={min_samples_leaf}
)''',
            # ... 更多阶段模板
        }
        
        template = templates.get(stage_id, "# 执行 {stage_id}")
        return template.format(**params, stage_id=stage_id)
    
    @staticmethod
    def generate_equivalent_code(task_type: str, params: dict) -> str:
        """生成完整等效代码"""
        # 根据任务类型生成可复制执行的完整代码
        pass
```

#### 4.4.2 前端 Code 栏组件增强

```typescript
// components/CodePanel.tsx 增强

interface CodePanelProps {
  executionId: string;
  source: "sop_ui" | "chat";
}

const CodePanel: React.FC<CodePanelProps> = ({ executionId, source }) => {
  const [codeBlocks, setCodeBlocks] = useState<CodeBlock[]>([]);
  
  // 监听 SSE 事件流
  useEffect(() => {
    const eventSource = new EventSource(`/api/sop/stream/${executionId}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case "llm_extraction":
          // Chat 入口：展示 LLM 推断过程
          if (source === "chat") {
            setCodeBlocks(prev => [...prev, {
              type: "llm_extraction",
              content: formatLLMExtraction(data.intent),
              timestamp: Date.now()
            }]);
          }
          break;
          
        case "stage_start":
          // 展示阶段伪代码
          setCodeBlocks(prev => [...prev, {
            type: "stage_start",
            stageId: data.stage_id,
            content: data.pseudo_code,
            status: "running",
            timestamp: Date.now()
          }]);
          break;
          
        case "stage_complete":
          // 更新阶段状态，添加结果
          setCodeBlocks(prev => prev.map(block => 
            block.stageId === data.stage_id
              ? { ...block, status: "completed", result: data.result_preview }
              : block
          ));
          break;
          
        case "task_complete":
          // 添加完整等效代码
          setCodeBlocks(prev => [...prev, {
            type: "full_code",
            content: data.full_code,
            copyable: true,
            timestamp: Date.now()
          }]);
          break;
      }
    };
    
    return () => eventSource.close();
  }, [executionId, source]);
  
  return (
    <div className="code-panel">
      {codeBlocks.map((block, index) => (
        <CodeBlock key={index} block={block} />
      ))}
    </div>
  );
};
```

### 4.5 展示效果对比

| 维度 | 当前 | 优化后 |
|------|------|--------|
| **执行过程可见性** | 低（仅结果） | 高（实时伪代码） |
| **代码可复现性** | 无 | 有（等效代码可复制） |
| **LLM 推断透明度** | N/A | 展示推断过程 |
| **用户学习价值** | 低 | 高（理解执行逻辑） |

---

## 五、实施路径与计划

### 5.1 实施进度记录

> **最后更新**: 2024-12-24

| 阶段 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|----------|------|
| **Phase 1** | LLM 参数推断器 | ✅ 完成 | 2024-12-19 | `llm_param_extractor.py` |
| **Phase 1** | 统一任务路由器 | ✅ 完成 | 2024-12-19 | `task_router.py` |
| **Phase 1** | Pipeline 事件流增强 | ✅ 完成 | 2024-12-19 | `code_templates.py` 增强 |
| **Phase 2** | 阶段伪代码生成器 | ✅ 完成 | 2024-12-19 | `StageCodeGenerator` 类 |
| **Phase 2** | 等效代码生成器 | ✅ 完成 | 2024-12-19 | `EquivalentCodeGenerator` 类 |
| **Phase 2** | 前端 Code 栏组件 | ✅ 完成 | 2024-12-19 | `PipelineCodePanel.tsx` |
| **Phase 3** | API 层适配 | ✅ 完成 | 2024-12-19 | `sop_api.py` 新增端点 |
| **Phase 3** | Chat API融合测试 | ✅ 完成 | 2024-12-24 | 8/8测试项全部通过（渠道工厂、配置获取、健康API、config格式、流式响应、代码执行、任务提示词、健康状态） |
| **Phase 4** | LLM SOP 标记废弃 | ✅ 完成 | 2024-12-19 | 添加 DeprecationWarning |
| **Phase 5** | AI分析评估按钮 | ✅ 完成 | 2024-12-24 | 全自动模式结果页新增，专家模式禁用 |

#### 新增文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `llm_param_extractor.py` | 新增 | LLM 参数推断器，从自然语言提取任务参数 |
| `task_router.py` | 新增 | 统一任务路由器，支持 SOP UI 和 Chat 两种入口 |
| `PipelineCodePanel.tsx` | 新增 | 前端 Code 栏组件，实时展示执行代码 |

#### 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `code_templates.py` | 新增 `StageCodeGenerator`、`EquivalentCodeGenerator` 类 |
| `__init__.py` | 导出新模块和类 |
| `sop_api.py` | 新增 `/llm/extract`、`/unified/execute`、`/code/{id}/events` 端点 |
| `llm_sop_executor.py` | 添加废弃警告和迁移指南 |
| `index.ts` (前端) | 导出 `PipelineCodePanel` 组件 |
| `three-panel-interface.tsx` | 新增 AI 分析评估按钮和面板（3状态变量+2处理函数） |

### 5.2 整体时间线

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           实施时间线                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Week 1-2: 基础设施准备                                                 │
│  ├── LLM 参数推断器开发                                                 │
│  ├── 统一任务路由器开发                                                 │
│  └── Pipeline 事件流增强                                                │
│                                                                         │
│  Week 3-4: Code 栏优化                                                  │
│  ├── 阶段伪代码生成器                                                   │
│  ├── 前端 Code 栏组件增强                                               │
│  └── SSE 事件流对接                                                     │
│                                                                         │
│  Week 5-6: 集成与测试                                                   │
│  ├── SOP 界面入口集成                                                   │
│  ├── Chat 界面入口集成                                                  │
│  └── 端到端测试                                                         │
│                                                                         │
│  Week 7-8: LLM SOP 废弃                                                 │
│  ├── 标记 deprecated                                                    │
│  ├── 迁移文档更新                                                       │
│  └── 兼容性测试                                                         │
│                                                                         │
│  Month 3+: 清理                                                         │
│  └── 移除 LLM SOP 代码                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 详细任务分解

#### Phase 1: 基础设施准备（Week 1-2）

| 任务 | 文件 | 工作量 | 依赖 |
|------|------|--------|------|
| 实现 LLM 参数推断器 | `llm_param_extractor.py` (新增) | 3d | 无 |
| 实现统一任务路由器 | `task_router.py` (新增) | 2d | 无 |
| 增强 Pipeline 事件流 | `executor.py` (修改) | 2d | 无 |
| 定义事件类型 | `types.py` (修改) | 1d | 无 |
| 单元测试 | `tests/` | 2d | 上述任务 |

#### Phase 2: Code 栏优化（Week 3-4）

| 任务 | 文件 | 工作量 | 依赖 |
|------|------|--------|------|
| 阶段伪代码生成器 | `code_templates.py` (修改) | 2d | Phase 1 |
| 等效代码生成器 | `code_templates.py` (修改) | 2d | Phase 1 |
| 前端 Code 栏组件 | `CodePanel.tsx` (修改) | 3d | 事件流 |
| SSE 事件流对接 | `sopService.ts` (修改) | 2d | 事件流 |
| 样式优化 | `CodePanel.css` (修改) | 1d | 组件 |

#### Phase 3: 集成与测试（Week 5-6）

| 任务 | 文件 | 工作量 | 依赖 |
|------|------|--------|------|
| SOP 界面集成 | `SopStageController.tsx` (修改) | 2d | Phase 2 |
| Chat 界面集成 | `ChatPanel.tsx` (修改) | 3d | Phase 2 |
| API 层适配 | `sop_api.py` (修改) | 2d | Phase 1 |
| 端到端测试 | `tests/e2e/` | 3d | 上述任务 |

#### Phase 4: LLM SOP 废弃（Week 7-8）

| 任务 | 文件 | 工作量 | 依赖 |
|------|------|--------|------|
| 标记 deprecated | `llm_sop_executor.py` | 0.5d | Phase 3 |
| 添加兼容层 | `sop_api.py` | 1d | Phase 3 |
| 更新文档 | `SOP_docs/` | 1d | 上述任务 |
| 迁移测试用例 | `tests/` | 2d | 上述任务 |

### 5.3 里程碑定义

| 里程碑 | 时间点 | 验收标准 |
|--------|--------|----------|
| **M1: 基础设施就绪** | Week 2 末 | LLM 推断器和路由器可独立运行 |
| **M2: Code 栏可用** | Week 4 末 | 自动模式下实时展示伪代码 |
| **M3: 双入口统一** | Week 6 末 | SOP/Chat 入口均走新架构 |
| **M4: LLM SOP 废弃** | Week 8 末 | 旧模式标记废弃，新模式稳定 |

---

## 六、风险评估与应对

### 6.1 技术风险

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| LLM 参数提取准确率低 | 中 | 高 | 设计回退机制，提取失败时引导用户手动配置 |
| 事件流性能瓶颈 | 低 | 中 | 使用消息队列缓冲，批量推送 |
| 前端渲染性能 | 低 | 低 | 虚拟滚动，增量更新 |

### 6.2 兼容性风险

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 现有 LLM SOP 用户迁移 | 高 | 中 | 提供 3 个月兼容期，自动转换请求 |
| API 接口变更 | 中 | 中 | 版本化 API，旧版本保留 |
| 前端状态管理变更 | 中 | 低 | 渐进式迁移，保持向后兼容 |

### 6.3 回滚方案

```python
# 配置开关，支持快速回滚
class FeatureFlags:
    # 新架构开关
    USE_UNIFIED_ROUTER = True  # 统一路由器
    USE_ENHANCED_CODE_PANEL = True  # 增强 Code 栏
    LLM_SOP_DEPRECATED = True  # LLM SOP 废弃
    
    @classmethod
    def rollback_to_legacy(cls):
        """紧急回滚到旧架构"""
        cls.USE_UNIFIED_ROUTER = False
        cls.USE_ENHANCED_CODE_PANEL = False
        cls.LLM_SOP_DEPRECATED = False
```

---

## 附录

### A. 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| SOP WebUI 详细设计 | `taskSOP_solution/SOP_WebUI_Detail_Design.md` | 前端 UI/UX 设计 |
| SOP WebUI 集成设计 | `taskSOP_solution/SOP_WebUI_Integration_design.md` | 后端架构与开发计划 |
| 专家模式设计 | `taskSOP_solution/task_sop_expert_mode_design.md` | 专家模式详细设计 |

### B. 核心文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `executor.py` | 修改 | Pipeline 执行器增强 |
| `llm_sop_executor.py` | 废弃 | LLM SOP 执行器 |
| `llm_param_extractor.py` | 新增 | LLM 参数推断器 |
| `task_router.py` | 新增 | 统一任务路由器 |
| `code_templates.py` | 修改 | 伪代码/等效代码生成 |
| `sop_api.py` | 修改 | API 层适配 |
| `CodePanel.tsx` | 修改 | 前端 Code 栏组件 |
| `sopService.ts` | 修改 | 前端服务层 |

### C. 术语表

| 术语 | 说明 |
|------|------|
| **Pipeline 模式** | 预定义执行路径的任务执行模式 |
| **LLM SOP 模式** | LLM 动态决策的任务执行模式（将废弃） |
| **伪代码** | 阶段执行时展示的简化代码，说明正在做什么 |
| **等效代码** | 任务完成后生成的可复制执行的完整代码 |
| **参数推断** | LLM 从自然语言中提取任务参数 |

---

> **文档维护**：本文档随项目演进持续更新，最新版本以代码仓库为准。
