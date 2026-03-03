# Pipeline + LLM 智能入口架构

> **文档版本**：v3.0（2026-03-02更新）
> **状态**：✅ **已实现** - LLM 作为智能入口，Pipeline 作为唯一执行引擎
> 
> **架构要点**：
> - LLM 作为智能入口（参数推断器），从自然语言理解用户意图
> - 统一使用 Pipeline 执行引擎，确保执行确定性和可靠性
> - 新架构详见 `llm_param_extractor.py` 和 `task_router.py`

## 1. 架构概述

### 1.1 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| Pipeline执行器 | ✅ 已实现 | `RuleMiningPipeline`, `ScorecardPipeline` - **唯一执行引擎** |
| SOPExecutor | ✅ 已实现 | Pipeline模式执行器 |
| LLM参数推断器 | ✅ 已实现 | `LLMParamExtractor` - 从自然语言推断任务参数 |
| 专家模式 | ✅ 已实现 | `interaction_mode: expert` 支持阶段暂停干预 |

### 1.2 架构设计

```
用户自然语言描述 → LLMParamExtractor（参数推断） → Pipeline执行引擎 → 结果
                   ↑ LLM作为智能入口                ↑ 唯一执行引擎
```

### 1.3 设计目标

- **Pipeline执行引擎**：唯一的任务执行方式，确保确定性和可靠性
- **LLM智能入口**：通过自然语言理解用户意图，自动推断任务参数
- **专家模式**：支持阶段级人工干预，参数调整和重试

---

## 2. 架构设计

### 2.1 Pipeline执行引擎

Pipeline模式采用预定义的执行路径，确保执行确定性：

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Pipeline执行（预定义路径）                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  def run(self, df, ...):                                           │
│      df = self.preprocessor.preprocess(df)      # 步骤1-预定义     │
│      df = self.feature_engineer.process(df)     # 步骤2-预定义     │
│      rules = self.miner.generate_rules(df)      # 步骤3-预定义     │
│      rules = self.miner.filter_rules(rules)     # 步骤4-预定义     │
│      rules = self.evaluator.evaluate(rules)     # 步骤5-预定义     │
│      return self.selector.select(rules)         # 步骤6-预定义     │
│                                                                     │
│  特点：执行路径编译时确定，运行时不变，100%可预测                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 架构优势

| 优势 | 说明 |
|------|------|
| **确定性** | Pipeline执行100%可预测 |
| **可靠性** | 经过测试的固定代码路径 |
| **低成本** | LLM仅用于参数推断，调用次数少 |
| **易调试** | 传统调试工具可用 |
| **用户友好** | 自然语言输入，无需了解参数细节 |

### 2.3 LLM 智能入口架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    架构：LLM 智能入口 + Pipeline执行                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  用户输入（自然语言）                                                │
│  "帮我分析这个数据集，挖掘高风险客户规则"                            │
│              ↓                                                      │
│      ┌──────────────┐                                               │
│      │ LLMParamExtractor │  ← LLM作为智能入口                       │
│      │ (参数推断器)      │     理解意图，推断参数                    │
│      └───────┬──────────┘                                           │
│              ↓                                                      │
│      ┌──────────────┐                                               │
│      │ TaskRouter   │  ← 路由到对应任务                             │
│      └───────┬──────────┘                                           │
│              ↓                                                      │
│      ┌──────────────┐                                               │
│      │ Pipeline     │  ← 唯一执行引擎                               │
│      │ Executor     │     确定性执行                                │
│      └───────┬──────────┘                                           │
│              ↓                                                      │
│         执行结果                                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 实现计划

## 5. 实现计划

### 5.1 阶段一：基础设施（P0）

**目标**：为混合模式提供基础支持

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 5.1.1 定义引擎模式枚举 | `EngineMode.PIPELINE`, `EngineMode.LLM_SOP` | 小 |
| 5.1.2 扩展ExecutionContext | 添加 `engine_mode` 字段 | 小 |
| 5.1.3 扩展API参数 | `/sop/execute` 接口添加 `engine_mode` 参数 | 小 |

**代码示例**：
```python
# executor.py
from enum import Enum

class EngineMode(Enum):
    """执行引擎模式（选择用哪个引擎执行）"""
    PIPELINE = "pipeline"      # 纯Pipeline执行
    LLM_SOP = "llm_sop"        # LLM SOP执行

@dataclass
class ExecutionContext:
    task_id: str
    session_id: str
    params: Dict[str, Any]
    engine_mode: EngineMode = EngineMode.PIPELINE  # 默认Pipeline
    # ...
```

### 5.2 阶段二：LLM SOP执行器（P1）

**目标**：实现LLM驱动的SOP执行逻辑

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 5.2.1 创建LLMSOPExecutor类 | 负责LLM SOP模式的执行 | 大 |
| 5.2.2 实现Prompt构建逻辑 | 将SOP Prompt + 数据上下文组合 | 中 |
| 5.2.3 实现代码生成与执行 | LLM生成代码 → 沙箱执行 → 结果收集 | 大 |
| 5.2.4 实现步骤状态管理 | 跟踪每个SOP步骤的执行状态 | 中 |
| 5.2.5 实现结果解释生成 | LLM生成每步结果的自然语言解释 | 中 |

**代码示例**：
```python
# llm_sop_executor.py
class LLMSOPExecutor:
    """LLM驱动的SOP执行器"""
    
    def __init__(self, llm_client, code_executor):
        self.llm_client = llm_client
        self.code_executor = code_executor
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """执行LLM SOP模式"""
        # 1. 获取SOP Prompt模板
        sop_prompt = self._get_sop_prompt(context.task_id)
        
        # 2. 构建完整Prompt（SOP + 数据上下文）
        full_prompt = self._build_prompt(sop_prompt, context)
        
        # 3. 逐步执行
        results = []
        for step in sop_prompt.steps:
            # 3.1 LLM理解当前步骤目标
            step_prompt = self._build_step_prompt(step, context, results)
            
            # 3.2 LLM生成代码
            code = await self.llm_client.generate_code(step_prompt)
            
            # 3.3 执行代码
            step_result = await self.code_executor.execute(code, context)
            
            # 3.4 LLM生成解释
            explanation = await self.llm_client.explain_result(step, step_result)
            
            results.append({
                'step': step.name,
                'code': code,
                'result': step_result,
                'explanation': explanation
            })
        
        return ExecutionResult(results=results)
```

### 5.3 阶段三：模式切换集成（P2）

**目标**：在SOPExecutor中集成模式切换逻辑

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 5.3.1 修改SOPExecutor | 添加模式分发逻辑 | 中 |
| 5.3.2 统一结果格式 | 两种模式返回相同结构 | 小 |
| 5.3.3 统一进度回调 | 两种模式使用相同的进度回调签名 | 小 |

**代码示例**：
```python
# executor.py
class SOPExecutor:
    def __init__(self, ...):
        self.pipeline_executor = PipelineExecutor(...)
        self.llm_sop_executor = LLMSOPExecutor(...)
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        if context.engine_mode == EngineMode.PIPELINE:
            return await self.pipeline_executor.execute(context)
        elif context.engine_mode == EngineMode.LLM_SOP:
            return await self.llm_sop_executor.execute(context)
        else:
            raise ValueError(f"Unknown engine mode: {context.engine_mode}")
```

### 5.4 阶段四：安全与沙箱（P3）【延后开发】

> ⚠️ **延后说明**：项目现阶段仅在可信环境的内部使用，安全沙箱功能暂不紧急，延后至后续优化迭代中实施。建议在阶段二中嵌入最小安全集（基础代码审查白名单）作为临时方案。

**目标**：确保LLM生成代码的安全执行

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 5.4.1 实现代码沙箱 | 限制LLM生成代码的执行权限 | 大 |
| 5.4.2 实现代码审查 | 检测危险代码模式 | 中 |
| 5.4.3 实现资源限制 | CPU/内存/时间限制 | 中 |
| 5.4.4 实现回滚机制 | 执行失败时回滚状态 | 中 |

**最小安全集（建议嵌入阶段二）**：
```python
# 基础代码安全检查（临时方案）
FORBIDDEN_PATTERNS = [
    r'os\.system', r'subprocess', r'eval\s*\(', r'exec\s*\(',
    r'__import__', r'open\s*\([^)]*[\'"]w', r'shutil\.rmtree'
]

def basic_code_review(code: str) -> bool:
    """基础代码安全检查"""
    import re
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return False
    return True
```

### 5.5 阶段五：用户体验优化（P4）【延后开发】

> ⚠️ **延后说明**：本阶段延后至后续优化迭代中实施。其中"结果对比"功能**依赖任务管理功能模块**（`task_management_module_design.md`）的任务记录持久化能力。

**目标**：提升LLM SOP模式的用户体验

| 任务 | 说明 | 工作量 | 前置依赖 |
|------|------|--------|----------|
| 5.5.1 实现流式输出 | LLM推理过程实时展示 | 中 | 无 |
| 5.5.2 实现步骤可视化 | 前端展示SOP步骤进度 | 中 | 无 |
| 5.5.3 实现交互式调整 | 用户可在中间步骤干预 | 大 | 无 |
| 5.5.4 实现结果对比 | 对比Pipeline和LLM SOP结果 | 中 | **任务管理模块** |

> **5.5.4 结果对比功能前置依赖说明**：
> 
> 当前项目**未实现任务记录持久化机制**（`ExecutionStateStore`仅为内存存储），无法跨会话查询历史执行结果。
> 
> 实现"结果对比"功能需先完成任务管理模块（`task_management_module_design.md`）中的以下前置任务：
> - TaskRecord模型设计与实现
> - 结果持久化存储
> - 历史查询API

---

## 6. 接口设计

### 6.1 API扩展

```python
# sop_api.py

class ExecuteSOPRequest(BaseModel):
    task_id: str
    session_id: str
    params: Dict[str, Any]
    engine_mode: str = "pipeline"  # "pipeline" | "llm_sop"（执行引擎选择）
    llm_config: Optional[LLMConfig] = None  # LLM SOP模式专用配置

class LLMConfig(BaseModel):
    model: str = "deepseek-chat"  # 使用的LLM模型
    temperature: float = 0.1      # 生成温度（低温更确定）
    max_tokens: int = 4096        # 最大token数
    stream: bool = True           # 是否流式输出
```

### 6.2 响应格式扩展

```python
class ExecutionResult(BaseModel):
    task_id: str
    engine_mode: str  # 使用的执行引擎
    status: str
    
    # Pipeline模式结果
    pipeline_result: Optional[Dict[str, Any]] = None
    
    # LLM SOP模式结果
    llm_sop_result: Optional[LLMSOPResult] = None

class LLMSOPResult(BaseModel):
    steps: List[StepResult]
    final_result: Dict[str, Any]
    total_tokens: int
    execution_time: float

class StepResult(BaseModel):
    step_id: str
    step_name: str
    generated_code: str
    execution_output: Any
    explanation: str
    tokens_used: int
```

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM生成代码有bug | 执行失败 | 代码审查 + 沙箱执行 + 重试机制 |
| LLM幻觉 | 结果不可信 | 结果验证 + 与Pipeline对比 |
| API调用失败 | 任务中断 | 降级到Pipeline模式 |
| 成本过高 | 预算超支 | 设置token限制 + 成本预估 |
| 执行时间过长 | 用户体验差 | 超时控制 + 流式输出 |

---

## 8. 里程碑

| 阶段 | 预计时间 | 交付物 | 状态 |
|------|---------|--------|------|
| 阶段一 | 1周 | 基础设施就绪，模式枚举、API参数扩展 | ✅ **已完成** |
| 阶段二 | 3周 | LLMSOPExecutor核心功能 + 最小安全集 | ✅ **已完成** |
| 阶段三 | 1周 | 模式切换集成完成 | ✅ **已完成** |
| 阶段四 | 2周 | 安全沙箱就绪 | ✅ **已完成** |
| 阶段五 | 2周 | 用户体验优化完成 | ⚠️ **部分完成** |

**阶段一至四已完成**（2024-12）

> **阶段四已完成说明**：
> - ✅ 代码安全检查：`FORBIDDEN_PATTERNS` 禁止危险模式
> - ✅ 沙箱执行：`sandbox_fusion.py` 完整沙箱工具
> - ✅ 资源限制：`memory_limit_mb=1024`, `timeout_sec=120`
> - ✅ 允许导入白名单：`ALLOWED_IMPORTS`
>
> **阶段五部分完成说明**：
> - ✅ 流式输出：API层支持SSE
> - ✅ 步骤可视化：`SopStageController.tsx`（原PipelineStageCards）
> - ✅ 交互式调整：Expert Mode 已实现
> - ❌ 结果对比：依赖任务管理模块完善，**延后**

---

## 9. 验收标准

### 9.1 功能验收（阶段一至三）

- [x] 用户可通过API参数选择执行引擎（engine_mode）
- [x] Pipeline模式行为与当前一致
- [x] LLM SOP模式可正确执行所有SOP步骤
- [x] LLM SOP模式生成的代码通过基础安全检查（最小安全集）
- [x] 两种模式返回统一格式的结果

### 9.2 性能验收

- [ ] Pipeline模式性能无回退
- [ ] LLM SOP模式单步执行时间 < 30秒
- [ ] LLM SOP模式总执行时间 < 5分钟（典型任务）

### 9.3 安全验收（最小安全集）

- [ ] 基础危险代码模式被拦截（os.system, subprocess, eval, exec等）
- [ ] 代码审查白名单机制生效

### 9.4 延后阶段验收标准（后续实施时启用）

**阶段四（安全与沙箱）**：
- [ ] LLM生成代码在沙箱中执行
- [ ] 完整危险代码模式被拦截
- [ ] 资源使用有上限控制
- [ ] 回滚机制可用

**阶段五（用户体验优化）**：
- [ ] 流式输出正常工作
- [ ] 步骤可视化展示正确
- [ ] 交互式调整功能可用
- [ ] 结果对比功能可用（依赖任务管理模块）

---

## 10. 附录

### 10.1 相关文件

| 文件 | 说明 |
|------|------|
| `executor.py` | 当前SOPExecutor实现 |
| `registry.py` | 任务注册与SOP Prompt模板 |
| `rule_mining.py` | 规则挖掘Pipeline |
| `scorecard_development.py` | 评分卡Pipeline |
| `docs/taskSOP_solution/rule_mining_workflow.md` | 规则挖掘SOP文档 |
| `docs/taskSOP_solution/scorecard_dev_workflow.md` | 评分卡SOP文档 |

### 10.2 参考资料

- DeepAnalyze项目架构文档
- LangChain Agent设计模式
- OpenAI Function Calling最佳实践

### 10.3 模式命名规范（更新）

~~为避免命名冲突，Task SOP系统采用**二维模式定义**：~~

| 维度 | 字段名 | 值域 | 说明 | 状态 |
|------|--------|------|------|------|
| **执行引擎** | `engine_mode` | ~~`pipeline` / `llm_sop`~~ | ~~选择用哪个引擎执行任务~~ | ❌ **已废弃**，统一使用Pipeline |
| **交互模式** | `interaction_mode` | `auto` / `expert` | 选择人工干预程度 | ✅ 保留 |

**当前有效组合**：

| engine_mode | interaction_mode | 场景描述 | 状态 |
|-------------|-----------------|----------|------|
| `pipeline` | `auto` | Pipeline全自动执行 | ✅ 已实现 |
| `pipeline` | `expert` | Pipeline + 阶段暂停干预 | ✅ 已实现 |
| ~~`llm_sop`~~ | ~~`auto`~~ | ~~LLM SOP全自动执行~~ | ❌ **已废弃** |
| ~~`llm_sop`~~ | ~~`expert`~~ | ~~LLM SOP + 人工干预~~ | ❌ **已废弃** |

**API请求示例（更新）**：
```python
class ExecuteSOPRequest(BaseModel):
    task_id: str
    session_id: str
    params: Dict[str, Any]
    # engine_mode: str = "pipeline"      # 已废弃，统一使用Pipeline
    interaction_mode: str = "auto"       # 交互模式选择
    llm_config: Optional[LLMConfig] = None  # 用于LLM参数推断（非执行）
```

> **注意**：`engine_mode` 参数已废弃。前端 `ModeSelector` 组件需要更新，移除 LLM SOP 选项。
