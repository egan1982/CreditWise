# System Prompt 架构重构方案

> 本文档记录对话/参数提取路径的 System Prompt 构建逻辑重构分析与实施方案。
> 
> **创建日期**：2026-03-11  
> **关联文档**：`docs/system_prompt_guide.md`（架构指南）  
> **状态**：✅ 已完成（2026-04-15 核实：代码库已包含全部改动，此前已实施但文档状态未更新）  
> **开发评审**: 🟢 无需评审，可直接实施 — 方案极其详细（565 行设计文档），文件变更清单、代码示例、测试要点齐全（2026-04-15 评估）

### 📌 快速回顾（开发前必读）

**作用与目标**：消除 `chat_api.py` 中通过关键词嗅探（`_is_param_extraction_mode()`）判断"对话/参数提取"模式的隐式逻辑，改用显式 `mode` 参数分流。

**当前实现的问题**：
- `_is_param_extraction_mode()` 用关键词（"参数提取助手"、"task_type"等）嗅探 system prompt 判断模式，但这些关键词可能在普通对话中出现，导致**误判**
- 对话模式被错误追加 JSON 格式要求，LLM 返回 JSON 而非自然语言
- `_append_json_instruction()` 在消息中**重复追加** JSON 指令（system prompt 和消息各一次）

**优化内容**：
- 新增 `_determine_chat_mode()` 函数：根据前端传入的 `task_type` 或消息推断，**显式**返回 `mode="chat"` 或 `"extraction"`
- `TaskPromptProvider.build_system_prompt(mode=...)` 按 mode 分流构建不同 prompt
- 删除 `_is_param_extraction_mode()`、`_append_json_instruction()` 两个函数

**后端变化**：
- `chat_api.py`：删除 2 个函数，新增 `_determine_chat_mode()`，修改 `_build_enhanced_system_prompt()` 传递 mode
- `task_prompt_provider.py`：`build_system_prompt()` 新增 mode 参数，新增 `DEFAULT_EXTRACTION_ROLE`、`JSON_OUTPUT_FORMAT` 常量
- `llm_param_extractor.py`：**不改动**（维持独立，方案 A）

**前端变化**：无（mode 判定完全在后端）

**不受影响**：AI 分析路径（`/v1/analysis/prompt` → `AI_analysis_prompts.py`）完全独立，不经过本次重构的任何函数

---

## 1. 问题背景

### 1.1 当前架构的缺陷

当前 `chat_api.py` 中的 `_build_enhanced_system_prompt()` 函数存在**模式识别混乱**的问题：

```
当前流程（有问题的）：
────────────────────────────────
用户消息 ──→ _build_enhanced_system_prompt()
                │
                ├── 构建 system prompt（组合基础角色 + 任务说明）
                │
                └── _is_param_extraction_mode()   ← ⚠️ 问题点
                     │
                     │  通过关键词嗅探判断是否为参数提取模式
                     │  关键词："参数提取助手", "task_type", "clarification_needed" 等
                     │
                     └── 如果命中关键词 → 追加 JSON 输出格式要求
```

**问题详情**：

| 问题 | 描述 | 影响 |
|------|------|------|
| **关键词误判** | `_is_param_extraction_mode()` 用关键词嗅探推断模式，但 `task_type` 等关键词可能出现在普通对话的任务列表中 | 普通对话被错误地追加 JSON 格式要求 |
| **职责不清** | 同一个函数同时处理"对话"和"参数提取"两种模式，通过关键词隐式切换 | 代码难以维护，新增模式时容易引入 bug |
| **双重注入** | `_build_enhanced_system_prompt()` 追加 JSON 指令 + `_append_json_instruction()` 在消息中再追加一次 | LLM 收到重复指令，浪费 token |

### 1.2 涉及范围

本次重构**仅涉及**对话/参数提取路径（路径 A & B），**不涉及** AI 分析路径（路径 C）：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  DeepAnalyze 的三条 Prompt 路径                          │
│                                                                         │
│  路径 A：直接提取              路径 B：Chat API            路径 C：AI 分析│
│  (llm_param_extractor.py)     (chat_api.py)              (独立模块)     │
│                                                                         │
│  ┌─────────────┐    ┌─────────────────────┐    ┌─────────────────────┐ │
│  │ 目的：       │    │ 目的：               │    │ 目的：               │ │
│  │ 从用户输入   │    │ 对话 + 意图识别     │    │ 分析任务执行结果    │ │
│  │ 提取SOP参数  │    │ + 参数提取           │    │ 生成业务洞察        │ │
│  └──────┬──────┘    └──────────┬──────────┘    └──────────┬──────────┘ │
│         │                      │                          │             │
│    🔴 本次重构                🔴 本次重构              ✅ 不受影响      │
│    涉及的范围                 涉及的范围               完全独立的模块    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 AI 分析路径不受影响的原因

```
路径 A & B（本次重构涉及的）:
────────────────────────────────
llm_param_extractor.py ──→ TaskPromptProvider (task_prompt_provider.py)
chat_api.py            ──→ TaskPromptProvider (task_prompt_provider.py)
                           ↑
                      本次重构的核心模块（新增 mode 参数分流）


路径 C（AI 分析）:
────────────────────
chat_api.py: /v1/analysis/prompt ──→ AI_analysis_prompts.py
                                     ↑
                                完全独立的 Prompt 模块
                                ❌ 不依赖 TaskPromptProvider
                                ❌ 不依赖 EXTRACTION_SYSTEM_PROMPT
                                ❌ 不经过 _is_param_extraction_mode()
                                ❌ 不经过 _build_enhanced_system_prompt()
```

| 维度 | 路径 A/B（对话/参数提取） | 路径 C（AI 分析） |
|------|---------------------------|-------------------|
| **Prompt 构建模块** | `task_prompt_provider.py` | `AI_analysis_prompts.py` |
| **API 端点** | `/v1/chat/completions` | `/v1/analysis/prompt` + `/v1/chat/completions` |
| **调用链** | `_build_enhanced_system_prompt()` → `TaskPromptProvider` | 前端调用 `/v1/analysis/prompt` 获取 prompt → 再发给 LLM |
| **角色定义来源** | `DEFAULT_BASE_PROMPT` / `DEFAULT_EXTRACTION_ROLE` | `STAGE_ROLE_CONFIG`（每阶段独立角色） |
| **涉及的函数** | `_determine_chat_mode()`, `build_system_prompt(mode=...)` | `get_overall_analysis_prompt()`, `get_stage_analysis_prompt()` |
| **是否使用 `mode` 参数** | ✅ 是（重构核心） | ❌ 否（无 mode 概念） |

---

## 2. 重构目标

### 2.1 核心目标

**引入显式的 `mode` 参数**，取代关键词嗅探的隐式模式识别：

```
重构后（显式分流）：
────────────────────────────────
请求参数 mode=chat/extraction
           │
           ├── mode=chat ──→ 对话模式 Prompt（角色 + 任务列表简介）
           │
           └── mode=extraction ──→ 参数提取模式 Prompt（角色 + JSON格式要求 + 参数Schema）
```

### 2.2 设计原则

1. **显式优于隐式**：mode 参数由调用方明确传入，不靠关键词猜测
2. **单一职责**：每种模式有独立的 Prompt 构建逻辑
3. **统一构建中心**：`TaskPromptProvider.build_system_prompt(mode=...)` 是唯一的 Prompt 构建入口
4. **消除冗余**：JSON 输出指令只在 system prompt 中出现一次

---

## 3. 架构设计

### 3.1 重构后的 Prompt 构建架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   调用入口                   TaskPromptProvider                         │
│                              (统一构建中心)                             │
│                                                                         │
│   chat_api.py ─────┐                                                   │
│                     │                                                   │
│                     ├──→ build_system_prompt(mode="chat")               │
│                     │    │                                              │
│                     │    ├── DEFAULT_BASE_PROMPT (角色定义)              │
│                     │    ├── get_all_tasks_prompt_brief() (任务简介)     │
│                     │    └── [workspace_files] (可选)                   │
│                     │                                                   │
│                     ├──→ build_system_prompt(mode="extraction")         │
│                     │    │                                              │
│                     │    ├── DEFAULT_EXTRACTION_ROLE (提取角色)          │
│                     │    ├── get_task_prompt(task_type) (参数Schema)     │
│                     │    ├── JSON_OUTPUT_FORMAT (格式要求)               │
│                     │    └── [workspace_files] (可选)                   │
│                     │                                                   │
│   llm_param_        │                                                   │
│   extractor.py ─────┘                                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 模式定义

| 模式 | mode 值 | 触发时机 | Prompt 特征 |
|------|---------|----------|-------------|
| **对话模式** | `"chat"` | 普通对话、通用问答 | 角色 + 任务列表简介（让 LLM 知道有哪些任务可以触发） |
| **参数提取模式** | `"extraction"` | 前端传入 `task_type`，或 `_infer_task_type_from_messages()` 推断出任务 | 提取角色 + 目标任务参数 Schema + JSON 格式要求 |

### 3.3 模式判定逻辑

```python
def _determine_chat_mode(task_type: Optional[str], messages: List[Dict]) -> str:
    """
    显式判定聊天模式
    
    规则：
    1. 前端传入了 task_type → extraction
    2. 从消息中推断出 task_type → extraction
    3. 其他情况 → chat
    """
    if task_type:
        return "extraction"
    
    inferred = _infer_task_type_from_messages(messages)
    if inferred:
        return "extraction"
    
    return "chat"
```

---

## 4. 详细改造方案

### 4.1 文件变更清单

| 文件 | 变更类型 | 变更内容 |
|------|----------|----------|
| `task_prompt_provider.py` | **修改** | `build_system_prompt()` 新增 `mode` 参数，分流构建逻辑 |
| `task_prompt_provider.py` | **新增** | `DEFAULT_EXTRACTION_ROLE` 常量（提取模式角色定义） |
| `task_prompt_provider.py` | **新增** | `JSON_OUTPUT_FORMAT` 常量（JSON 输出格式要求） |
| `chat_api.py` | **修改** | `_build_enhanced_system_prompt()` → 使用 `mode` 参数调用 provider |
| `chat_api.py` | **删除** | `_is_param_extraction_mode()` 函数（关键词嗅探，不再需要） |
| `chat_api.py` | **删除** | `_append_json_instruction()` 函数（消息级 JSON 指令，不再需要） |
| `chat_api.py` | **新增** | `_determine_chat_mode()` 函数（显式模式判定） |

### 4.2 `TaskPromptProvider.build_system_prompt()` 改造

```python
# task_prompt_provider.py

DEFAULT_EXTRACTION_ROLE = """你是 DeepAnalyze 数据分析平台的任务参数提取助手。

## 你的角色定位
在 LLM+Pipeline 架构中，你是"智能入口"而非"执行引擎"：
- 你只负责理解用户意图并提取任务参数
- 任务执行由 Pipeline 引擎完成（预定义的确定性代码）

## 核心职责
1. 识别任务类型
2. 提取必需和可选参数
3. 信息不足时请求澄清

## 关键约束
- 不要尝试生成执行代码
- 不要假设用户未提及的参数值
- 只提取用户明确提供的信息"""

JSON_OUTPUT_FORMAT = """
## 输出格式要求

**严格返回 JSON 格式，不要有任何解释文字或自然语言回复。**

```json
{
    "task_type": "任务类型ID",
    "confidence": 0.95,
    "params": {"param1": "value1"},
    "missing_params": ["缺失的必需参数名"],
    "clarification_needed": false,
    "clarification_question": ""
}
```

**重要**：
1. 只返回 JSON，不要有任何解释文字
2. 参数齐全时 clarification_needed=false
3. 仅当 missing_params 不为空时 clarification_needed=true"""


class TaskPromptProvider:
    
    def build_system_prompt(
        self,
        base_prompt: str = "",
        task_type: Optional[str] = None,
        include_all_tasks: bool = True,
        workspace_files: Optional[list[str]] = None,
        mode: str = "chat",  # ← 新增参数
    ) -> str:
        """构建组合后的系统提示词
        
        Args:
            mode: "chat"（对话模式）或 "extraction"（参数提取模式）
        """
        if mode == "extraction":
            return self._build_extraction_prompt(base_prompt, task_type, workspace_files)
        else:
            return self._build_chat_prompt(base_prompt, task_type, include_all_tasks, workspace_files)
    
    def _build_chat_prompt(self, base_prompt, task_type, include_all_tasks, workspace_files):
        """对话模式：角色 + 任务列表简介"""
        sections = []
        sections.append(base_prompt.strip() if base_prompt else DEFAULT_BASE_PROMPT)
        
        if task_type:
            task_guidance = self.get_task_prompt(task_type)
            if task_guidance:
                sections.append(task_guidance)
        elif include_all_tasks:
            all_tasks = self.get_all_tasks_prompt_brief()
            if all_tasks:
                sections.append(all_tasks)
        
        if workspace_files:
            sections.append(self._format_workspace_files(workspace_files))
        
        return "\n\n".join(sections)
    
    def _build_extraction_prompt(self, base_prompt, task_type, workspace_files):
        """参数提取模式：提取角色 + 参数Schema + JSON格式要求"""
        sections = []
        
        # 使用提取专用角色（忽略用户的 base_prompt）
        sections.append(DEFAULT_EXTRACTION_ROLE)
        
        # 注入目标任务的参数 Schema
        if task_type:
            task_guidance = self.get_task_prompt(task_type)
            if task_guidance:
                sections.append(task_guidance)
        else:
            # 未指定任务类型时注入全部任务列表
            all_tasks = self.get_all_tasks_prompt()
            if all_tasks:
                sections.append(all_tasks)
        
        # JSON 输出格式要求（只在这里出现一次）
        sections.append(JSON_OUTPUT_FORMAT)
        
        if workspace_files:
            sections.append(self._format_workspace_files(workspace_files))
        
        return "\n\n".join(sections)
```

### 4.3 `chat_api.py` 改造

```python
# chat_api.py

def _determine_chat_mode(
    task_type: Optional[str],
    messages: List[Dict[str, Any]],
    enable_code_execution: bool
) -> Tuple[str, Optional[str]]:
    """
    显式判定聊天模式
    
    Returns:
        (mode, effective_task_type)
    """
    if not enable_code_execution:
        return "chat", None
    
    if task_type:
        return "extraction", task_type
    
    inferred = _infer_task_type_from_messages(messages)
    if inferred:
        return "extraction", inferred
    
    return "chat", None


def _build_enhanced_system_prompt(
    user_system_prompt: Optional[str] = None,
    task_type: Optional[str] = None,
    workspace_files: Optional[List[str]] = None,
    include_task_list: bool = True,
    mode: str = "chat",  # ← 新增参数
) -> str:
    """构建增强的系统提示词"""
    if not TASK_PROMPT_AVAILABLE:
        return user_system_prompt or ""
    
    try:
        provider = get_prompt_provider()
        return provider.build_system_prompt(
            base_prompt=user_system_prompt or "",
            task_type=task_type,
            include_all_tasks=include_task_list,
            workspace_files=workspace_files,
            mode=mode,  # ← 传递 mode
        )
    except Exception as e:
        logger.warning(f"Failed to build enhanced system prompt: {e}")
        return user_system_prompt or ""


# chat_completions 端点中的调用改为：
# 
# mode, effective_task_type = _determine_chat_mode(task_type, messages, enable_code_execution)
# enhanced_system_prompt = _build_enhanced_system_prompt(
#     user_system_prompt=base_system_prompt,
#     task_type=effective_task_type,
#     mode=mode,
# )
# 
# 删除以下代码：
# - _is_param_extraction_mode() 函数定义及调用
# - _append_json_instruction() 函数定义及调用
# - _build_enhanced_system_prompt() 中的 json_format_instruction 拼接逻辑
```

### 4.4 `llm_param_extractor.py` 的适配

`llm_param_extractor.py` 目前是**独立调用 LLM** 的（不经过 `chat_api.py`），它有自己的 `EXTRACTION_SYSTEM_PROMPT` 常量。两种适配方案：

| 方案 | 描述 | 优缺点 |
|------|------|--------|
| **A. 维持独立** | `llm_param_extractor.py` 保持现有的 `EXTRACTION_SYSTEM_PROMPT`，不改动 | ✅ 零风险、不影响直接提取流程<br>❌ 两处维护参数提取 prompt |
| **B. 统一调用** | 改用 `TaskPromptProvider.build_system_prompt(mode="extraction")` | ✅ 单一 prompt 来源<br>❌ 需要适配改造 |

**推荐方案 A**（维持独立）：

原因：`llm_param_extractor.py` 的 `EXTRACTION_SYSTEM_PROMPT` 内容更精确（包含置信度评估标准、参数提取规则等），是为**直接 LLM 调用**场景优化的。而 `TaskPromptProvider` 构建的提取 prompt 是为 **Chat API 场景**优化的（需要兼顾前端交互）。两者虽然同为"参数提取"，但上下文和要求略有不同，分开维护更清晰。

后续如需统一，可考虑提取公共部分为 `EXTRACTION_CORE_RULES`，两个场景各自组合使用。

---

## 5. 改造前后对比

### 5.1 调用链对比

**改造前**：
```
chat_completions()
  ├── _build_enhanced_system_prompt(task_type=...)
  │     ├── provider.build_system_prompt(...)  ← 不知道当前模式
  │     └── _is_param_extraction_mode(prompt)  ← 关键词嗅探
  │           └── 命中关键词 → 追加 JSON 指令到 system prompt
  │
  └── _append_json_instruction(messages)       ← 再在消息中追加一次
```

**改造后**：
```
chat_completions()
  ├── _determine_chat_mode(task_type, messages)  ← 显式判定
  │     └── 返回 mode="chat" 或 "extraction"
  │
  └── _build_enhanced_system_prompt(mode=...)
        └── provider.build_system_prompt(mode=...)
              ├── mode="chat" → _build_chat_prompt()
              └── mode="extraction" → _build_extraction_prompt()
                    └── 包含 JSON 格式要求（只出现一次）
```

### 5.2 删除的代码

| 函数/代码块 | 文件 | 原因 |
|------------|------|------|
| `_is_param_extraction_mode()` | `chat_api.py` | 被 `_determine_chat_mode()` 替代 |
| `_append_json_instruction()` | `chat_api.py` | JSON 指令已在 system prompt 中 |
| `json_format_instruction` 拼接 | `_build_enhanced_system_prompt()` 内部 | 移至 `TaskPromptProvider._build_extraction_prompt()` |

### 5.3 Prompt 层级对比

**改造前**（对话模式和提取模式混在一起）：

| 层级 | 内容 | 备注 |
|------|------|------|
| 1 | 基础角色（用户配置/默认） | 两种模式共用 |
| 2 | 任务列表/任务引导 | 动态注入 |
| 3 | JSON 格式指令（关键词命中时） | ⚠️ 隐式追加 |
| 4 | 消息级 JSON 指令 | ⚠️ 重复追加 |

**改造后**（对话模式）：

| 层级 | 内容 | 备注 |
|------|------|------|
| 1 | `DEFAULT_BASE_PROMPT`（对话角色） | 对话专用 |
| 2 | 任务列表简介（简化版） | 用于意图识别 |
| 3 | 工作区文件（可选） | — |

**改造后**（参数提取模式）：

| 层级 | 内容 | 备注 |
|------|------|------|
| 1 | `DEFAULT_EXTRACTION_ROLE`（提取角色） | 提取专用 |
| 2 | 目标任务参数 Schema | 动态注入 |
| 3 | `JSON_OUTPUT_FORMAT`（JSON 格式要求） | ✅ 只出现一次 |
| 4 | 工作区文件（可选） | — |

---

## 6. 实施计划

### 6.1 步骤

| 步骤 | 内容 | 预估工作量 |
|------|------|-----------|
| 1 | 在 `task_prompt_provider.py` 中新增 `DEFAULT_EXTRACTION_ROLE`、`JSON_OUTPUT_FORMAT` 常量 | 15 min |
| 2 | 改造 `build_system_prompt()` 方法，新增 `mode` 参数和分流逻辑 | 30 min |
| 3 | 在 `chat_api.py` 中新增 `_determine_chat_mode()` 函数 | 15 min |
| 4 | 改造 `_build_enhanced_system_prompt()`，传递 `mode` 参数 | 15 min |
| 5 | 删除 `_is_param_extraction_mode()`、`_append_json_instruction()` | 10 min |
| 6 | 清理 `chat_completions()` 中的相关调用 | 15 min |
| 7 | 端到端测试：对话模式 + 参数提取模式 | 30 min |

### 6.2 测试要点

| 场景 | 预期行为 | 验证方式 |
|------|----------|----------|
| 普通对话 | mode=chat，prompt 不含 JSON 格式要求 | 检查 system prompt 内容 |
| 前端传入 task_type | mode=extraction，prompt 含目标任务 Schema + JSON 格式要求 | 检查 system prompt + LLM 输出 |
| 从消息推断 task_type | mode=extraction，与前端传入相同效果 | 发送含任务关键词的消息 |
| AI 分析路径 | 完全不受影响，走 `/v1/analysis/prompt` 独立流程 | 触发阶段分析 |
| 简单模式（enable_code_execution=False） | mode=chat，不注入任务列表 | 检查 system prompt |

### 6.3 回滚方案

`mode` 参数的默认值为 `"chat"`，与改造前的默认行为一致。如需回滚：
- 恢复 `_is_param_extraction_mode()` 函数
- 恢复 `_append_json_instruction()` 函数
- 移除 `_determine_chat_mode()` 函数
- 移除 `build_system_prompt()` 的 `mode` 参数

---

## 7. 附录：完整数据流图

### 7.1 改造后的对话模式数据流

```
用户消息: "你好，有什么功能？"
        │
        ↓
chat_completions(task_type=None)
        │
        ├── _determine_chat_mode(None, messages)
        │   └── 返回 mode="chat", task_type=None
        │
        ├── _build_enhanced_system_prompt(mode="chat")
        │   └── provider.build_system_prompt(mode="chat")
        │       ├── DEFAULT_BASE_PROMPT（"你是 DeepAnalyze 数据分析平台的 AI 助手..."）
        │       └── get_all_tasks_prompt_brief()（"可用任务：规则挖掘、评分卡开发..."）
        │
        └── LLM 收到:
            - system: 角色 + 任务简介
            - user: "你好，有什么功能？"
            → LLM 用自然语言回复
```

### 7.2 改造后的参数提取模式数据流

```
用户消息: "帮我做个评分卡，目标变量是 is_default"
        │
        ↓
chat_completions(task_type=None)
        │
        ├── _determine_chat_mode(None, messages)
        │   ├── _infer_task_type_from_messages() → "scorecard_dev"
        │   └── 返回 mode="extraction", task_type="scorecard_dev"
        │
        ├── _build_enhanced_system_prompt(mode="extraction", task_type="scorecard_dev")
        │   └── provider.build_system_prompt(mode="extraction", task_type="scorecard_dev")
        │       ├── DEFAULT_EXTRACTION_ROLE（"你是任务参数提取助手..."）
        │       ├── get_task_prompt("scorecard_dev")（评分卡参数 Schema）
        │       └── JSON_OUTPUT_FORMAT（"严格返回 JSON 格式..."）
        │
        └── LLM 收到:
            - system: 提取角色 + 评分卡参数Schema + JSON格式要求
            - user: "帮我做个评分卡，目标变量是 is_default"
            → LLM 返回 JSON: {"task_type": "scorecard_dev", "params": {"target_col": "is_default"}, ...}
```

### 7.3 AI 分析路径数据流（不受影响）

```
前端 StageOutputPreview.tsx
        │
        │ POST /v1/analysis/prompt
        │ { analysis_type, task_type, stage_id, data }
        ↓
chat_api.py: get_analysis_prompt_endpoint()
        │
        │ 直接调用 AI_analysis_prompts.py
        │ （不经过 TaskPromptProvider）
        │ （不经过 _build_enhanced_system_prompt）
        │ （不经过任何 mode 判断）
        ↓
AI_analysis_prompts.py
├── get_stage_analysis_prompt()     ← 阶段分析（自带角色/关注点/数据描述）
├── get_overall_analysis_prompt()   ← 整体分析（自带角色/指标/格式要求）
└── AI_ANALYSIS_PARAMS              ← 专用 LLM 参数（temperature=0.3 等）
        │
        │ 返回 { prompt, params }
        ↓
前端拿到 prompt → 发给 /v1/chat/completions（simple 模式）→ LLM 返回分析结果
```
