# Task SOP 统一实施路线图

> 整合 Pipeline UI Enhancement、Expert Mode、Rule Mining Enhancement、Task Management Module 的实施计划
>
> **更新日期**: 2026-03-02（移除 LLM SOP 相关内容）

---

## 目录

1. [概述](#1-概述)
2. [各模块计划汇总](#2-各模块计划汇总)
3. [依赖关系分析](#3-依赖关系分析)
4. [整合实施阶段](#4-整合实施阶段)
5. [延后开发内容](#5-延后开发内容)
6. [里程碑与时间线](#6-里程碑与时间线)
7. [风险与应对](#7-风险与应对)

---

## 1. 概述

### 1.1 涉及文档

| 文档 | 说明 |
|------|------|
| `pipeline_ui_enhancement_design.md` | Pipeline模式UI展示优化 |
| `pipeline_llm_hybrid_design.md` | Pipeline + LLM 智能入口架构 |
| `task_sop_expert_mode_design.md` | 专家模式（人工干预）功能设计 |
| `rule_mining_enhancement_design.md` | 规则挖掘任务功能增强 |
| `task_management_module_design.md` | 任务管理功能模块（暂停/停止/历史记录） |

### 1.2 整体目标

构建完整的 Task SOP 功能体系，包括：

- **执行引擎**：Pipeline模式（唯一执行引擎）
- **智能入口**：LLM参数推断器（从自然语言提取任务参数）
- **交互模式**：全自动模式 + 专家模式（人工干预）
- **任务管理**：暂停/停止/恢复 + 历史记录持久化
- **UI展示**：阶段卡片 + 日志面板 + 结果预览
- **任务增强**：规则质量验证 + 稳定性检测

---

## 2. 各模块计划汇总

### 2.1 Pipeline UI Enhancement

| Phase | 内容 | 工作量 | 优先级 | 状态 |
|-------|------|--------|--------|------|
| Phase 1 | 基础改造（中间列卡片+右侧日志） | 5-7天 | P0 | ✅ **已完成**（通过Expert Mode实现） |
| Phase 2 | 伪代码生成 | 2-3天 | P1 | ✅ **已完成** |
| Phase 3 | 阶段输出预览 | 3-4天 | P2 | ✅ **已完成**（StageOutputPreview.tsx） |
| Phase 4 | 阶段详情面板 | 2-3天 | P2 | ✅ **已完成** |

**已完成说明**：
- Phase 1 的阶段卡片功能已通过 `SopStageController.tsx` 实现
- Phase 2 伪代码集成已完成：
  - ✅ 模板：`code_templates.py`（评分卡+规则挖掘完整模板）
  - ✅ 前端：`StageCodeEditor.tsx`、`StageOutputPreview.tsx` 显示 `stage.code`
  - ✅ 回调链：`StageProgressCallback` 类型扩展支持 `code` 参数
  - ✅ Pipeline集成：`ScorecardPipeline`、`RuleMiningPipeline` 的 `_update_progress` 支持 `code`
  - ✅ 各阶段开始时调用 `_get_stage_code()` 获取伪代码
- Phase 3 的阶段输出预览已通过 `StageOutputPreview.tsx` 实现
- Phase 4 阶段详情面板已完成：
  - ✅ 点击阶段卡片 → 右侧 `StageOutputPreview` 展示详情
  - ✅ 阶段参数：通过 `stageData.params` 和 `params_used` 展示
  - ✅ 阶段代码：通过 `stageData.code` 展示
  - ✅ 阶段输出预览：各阶段专属预览组件
  - ✅ 执行时间：`execution_time_ms` 属性已实现并在UI展示
  - ❌ 内存占用监控：已废弃，不实现

### 2.2 Pipeline + LLM 智能入口架构

> **架构（2025-12-19更新）**：统一使用 Pipeline 执行引擎，LLM 作为智能入口（参数推断器）

| 阶段 | 内容 | 工作量 | 优先级 | 状态 |
|------|------|--------|--------|------|
| 阶段一 | 基础设施（API扩展、参数验证） | 1周 | P0 | ✅ **已完成** |
| 阶段四 | 安全与沙箱 | 2周 | P3 | ✅ **已完成**（用于代码执行安全） |
| 阶段五 | 用户体验优化 | 2周 | P4 | ⚠️ **部分完成** |
| **核心** | LLM参数推断器 | 1周 | P0 | ✅ **已完成** |

**架构说明**：
- ✅ `LLMParamExtractor` 已实现，作为智能入口推断任务参数
- ✅ `TaskRouter` 已实现，路由用户请求到对应Pipeline
- ✅ 统一使用 Pipeline 执行引擎，确保执行确定性

**阶段四已完成说明**：
- ✅ 代码安全检查：`FORBIDDEN_PATTERNS` 禁止危险模式（eval, exec, subprocess等）
- ✅ 沙箱执行：`sandbox_fusion.py` 完整沙箱工具
- ✅ 资源限制：`memory_limit_mb=1024`, `timeout_sec=120`
- ✅ 允许导入白名单：`ALLOWED_IMPORTS`

**阶段五部分完成说明**：
- ✅ 流式输出：API层支持SSE
- ✅ 步骤可视化：`SopStageController.tsx`
- ✅ 交互式调整：Expert Mode 已实现
- ✅ 代码高亮：`react-syntax-highlighter`
- ✅ 执行历史：`TaskHistoryService`
- ✅ 代码模板：`code_templates.py`
- ❌ 结果对比：依赖任务管理模块完善，**延后**

### 2.3 Expert Mode

| Phase | 内容 | 工作量 | 优先级 | 状态 |
|-------|------|--------|--------|------|
| Phase 1 | 基础框架（模式选择+阶段暂停/继续） | 3-5天 | P1 | ✅ **已完成** |
| Phase 2 | 参数调整（阶段间参数修改+重试） | 2-3天 | P1 | ✅ **已完成** |
| Phase 3 | 代码编辑（编辑+重新执行，仅LLM-SOP） | 3-5天 | P2 | ✅ **已完成** |

**已完成的关键实现**：
- 统一的专家模式暂停逻辑 `check_expert_mode_pause()`
- 前端专家模式控制面板（`SopStageController.tsx`）
- `StageCodeEditor.tsx` - 复用原项目 Monaco Editor 配置（仅展示，Pipeline代码不可编辑）
- `StageParameterEditor.tsx` - JSON 格式参数编辑器

### 2.4 Rule Mining Enhancement

| Phase | 内容 | 工作量 | 优先级 | 状态 |
|-------|------|--------|--------|------|
| Phase 1 | 规则质量验证模块 | 4h | P2 | ✅ **已完成** |
| Phase 2 | 规则稳定性检测 | 3h | P2 | ✅ **已完成** |
| Phase 3 | 前端分箱方法说明 | 1h | P3 | ✅ **已完成** |
| Phase 4 | 规则业务解读增强 | 2h | P3 | ✅ **已完成** |
| Phase 5 | 规则可视化增强 | 4h | P3 | **延后** |

**已完成说明**：
- Phase 1: `RuleValidator` 类已实现（`rule_mining.py` 第2210行），包含覆盖率、冲突、重叠、冗余检测
- Phase 2: `calculate_rule_psi` 和 `calculate_rule_psi_by_time` 方法已实现，已集成到报告生成阶段
- Phase 4: `RuleInterpreter` 类已实现（`rule_mining.py` 第2568行），支持规则业务解读
- 前端展示：`RuleMiningResults.tsx` 包含 `ValidationReportPanel` 和 `PSIReportPanel` 组件

### 2.5 Task Management Module（新增）

| Phase | 内容 | 工作量 | 优先级 | 状态 |
|-------|------|--------|--------|------|
| Phase 1 | 基础设施（数据库、ORM模型） | 1周 | P0 | ✅ **已完成** |
| Phase 2 | 任务记录管理（历史服务、结果存储） | 1周 | P0 | ✅ **已完成** |
| Phase 3 | 任务控制（暂停/停止/恢复） | 1周 | P1 | ✅ **已完成** |
| Phase 4 | API接口扩展 | 0.5周 | P1 | ✅ **已完成** |
| Phase 5 | 测试与文档 | 0.5周 | P2 | 待实施 |

**已完成的关键实现**：
- 数据库管理：`deepanalyze/core/task_manager/database.py` (TaskManagerDB)
- ORM模型：`deepanalyze/core/task_manager/models.py` (TaskRecord, TaskControl)
- 枚举定义：`deepanalyze/core/task_manager/enums.py` (TaskStatus, TaskControlAction, EngineMode, InteractionMode)
- 任务控制器：`deepanalyze/core/task_manager/controller.py` (TaskController)
- 历史服务：`deepanalyze/core/task_manager/history_service.py` (TaskHistoryService)
- 结果存储：`deepanalyze/core/task_manager/result_storage.py` (TaskResultStorage)
- 检查点机制：`deepanalyze/core/task_manager/checkpoint.py` (CheckpointMixin)
- API接口：`API/sop_api.py` 中的 `/executions/{id}/pause|stop|resume` 和 `/history` 系列接口

---

## 3. 依赖关系分析

### 3.1 依赖图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           依赖关系图                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Task Management Module                                                 │
│  ┌─────────────────────┐                                               │
│  │ Phase 1-2: 基础设施  │                                               │
│  │ + 任务记录管理       │                                               │
│  └──────────┬──────────┘                                               │
│             │                                                           │
│             ├──────────────────────────────────────┐                   │
│             │                                      │                   │
│             ▼                                      ▼                   │
│  ┌─────────────────────┐              ┌─────────────────────┐         │
│  │ Phase 3: 任务控制    │              │ Hybrid 阶段五:       │         │
│  │ (暂停/停止/恢复)     │              │ 结果对比功能         │         │
│  └──────────┬──────────┘              │ 【延后】             │         │
│             │                          └─────────────────────┘         │
│             ▼                                                           │
│  ┌─────────────────────┐                                               │
│  │ Expert Mode         │                                               │
│  │ (阶段控制可整合)     │                                               │
│  └─────────────────────┘                                               │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  Hybrid 阶段一二                                                        │
│  ┌─────────────────────┐                                               │
│  │ 阶段一: 基础设施     │                                               │
│  │ 阶段二: LLMSOPExecutor│                                              │
│  └──────────┬──────────┘                                               │
│             │                                                           │
│             ▼                                                           │
│  ┌─────────────────────┐                                               │
│  │ Expert Mode         │                                               │
│  │ (LLM SOP + 人工干预) │                                               │
│  └─────────────────────┘                                               │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  相对独立的模块:                                                        │
│  • Pipeline UI Enhancement (Phase 1-3)                                 │
│  • Rule Mining Enhancement (Phase 1-4)                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 关键依赖说明

| 依赖关系 | 说明 |
|----------|------|
| Task Management → Expert Mode | 暂停/恢复/重试功能可整合 |
| Task Management → Pipeline UI | 阶段详情面板需要任务记录持久化 |

---

## 4. 整合实施阶段

### 4.1 第一阶段：基础设施与核心功能（6-8周）

**目标**：建立任务管理基础设施，实现Pipeline UI基础改造

| 模块 | 内容 | 工作量 |
|------|------|--------|
| Task Management | Phase 1-3（基础设施+记录管理+任务控制） | 3周 |
| Pipeline UI | Phase 1（基础改造） | 1周 |
| LLM智能入口 | 参数推断器+任务路由 | 1周 |

**交付物**：
- 任务管理数据库就绪
- 任务暂停/停止/恢复功能可用
- 历史记录持久化和查询功能可用
- Pipeline UI阶段卡片+日志面板
- LLM参数推断器（`LLMParamExtractor`）可用
- 任务路由（`TaskRouter`）可用

### 4.2 第二阶段：功能增强（5-7周）

**目标**：实现专家模式、任务管理API

| 模块 | 内容 | 工作量 |
|------|------|--------|
| Expert Mode | Phase 1-3（全部） | 2周 |
| Task Management | Phase 4-5（API+测试） | 1周 |
| 安全沙箱 | 代码执行安全 | 1周 |

**交付物**：
- 专家模式（阶段暂停/参数调整/阶段重试）可用
- 任务管理API完整可用
- 代码执行安全沙箱可用
- 模式切换（Pipeline/LLM SOP）完成
- 专家模式（阶段控制+参数调整+代码编辑）可用
- 任务管理API完整

### 4.3 第三阶段：优化与扩展（3-5周）

**目标**：UI增强、规则挖掘功能增强

| 模块 | 内容 | 工作量 |
|------|------|--------|
| Pipeline UI | Phase 2-3（伪代码+预览） | 1.5周 |
| Rule Mining | Phase 1-4（质量验证+稳定性+说明+解读） | 1.5周 |

**交付物**：
- Pipeline UI伪代码生成
- Pipeline UI阶段输出预览
- 规则质量验证模块
- 规则稳定性检测（PSI）
- 前端分箱方法说明
- 规则业务解读增强

---

## 5. 延后开发内容

以下内容延后至后续优化迭代中实施：

### 5.1 Pipeline UI - 结果对比

| 内容 | 原因 |
|------|------|
| 结果对比功能 | 依赖任务管理模块的历史记录查询能力完善 |

> **注意**：阶段四（安全沙箱）和流式输出、步骤可视化、交互式调整已完成

### 5.2 Rule Mining Enhancement - Phase 5

| 内容 | 原因 |
|------|------|
| 规则可视化增强（热力图/桑基图/趋势图） | 高级分析功能，基础规则挖掘流程不依赖 |

---

## 6. 里程碑与时间线

### 6.1 里程碑

| 里程碑 | 完成时间 | 交付物 |
|--------|----------|--------|
| M1 | 第3周末 | 任务管理基础设施就绪，暂停/停止/恢复可用 |
| M2 | 第5周末 | Pipeline UI基础改造完成，LLM参数推断器就绪 |
| M3 | 第9周末 | 安全沙箱完成，代码执行安全可用 |
| M4 | 第11周末 | 专家模式完成，任务管理API完整 |
| M5 | 第14周末 | UI增强完成，规则挖掘增强完成 |

### 6.2 时间线

```
Week 1-3:   Task Management Phase 1-3
Week 4-5:   Pipeline UI Phase 1 + LLM智能入口
Week 6-9:   安全沙箱 + Expert Mode基础
Week 10-11: Expert Mode + Task Management Phase 4-5
Week 12-14: Pipeline UI Phase 2-3 + Rule Mining Phase 1-4

延后:
- Pipeline UI结果对比
- Rule Mining Phase 5
```

### 6.3 甘特图

```
                    Week 1  2  3  4  5  6  7  8  9  10 11 12 13 14
Task Management     ████████████████████████████████
  Phase 1-3         ████████████
  Phase 4-5                                     ████

Pipeline UI         ░░░░░░░░████████░░░░░░░░░░░░████████████
  Phase 1                   ████████
  Phase 2-3                                         ████████████

LLM智能入口         ░░░░░░░░░░░░████░░░░░░░░░░░░░░░░░░░░░░░░
  参数推断器                ████

Expert Mode         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████
  Phase 1-3                                     ████████

Rule Mining         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████
  Phase 1-4                                             ████████

延后内容:
  Pipeline UI结果对比      [后续迭代]
  Rule Mining Phase 5      [后续迭代]
```

---

## 7. 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| Task Management 延期 | 阻塞 Expert Mode | 优先保障 Phase 1-2，Phase 3 可并行 |
| 专家模式与任务管理整合困难 | 重复开发 | 提前设计统一的控制接口 |
| 前端组件复用困难 | 增加工作量 | 提前抽取可复用组件 |

---

## 附录

### A. 相关文档链接

- [Pipeline UI Enhancement Design](./pipeline_ui_enhancement_design.md)
- [Pipeline + LLM 智能入口架构](./pipeline_llm_hybrid_design.md)
- [Expert Mode Design](./task_sop_expert_mode_design.md)
- [Rule Mining Enhancement Design](./rule_mining_enhancement_design.md)
- [Task Management Module Design](./task_management_module_design.md)

---

### B. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 初始创建 | 整合各模块实施计划 |
| v1.1 | 2026-03-02 | 移除 LLM SOP 相关内容，统一使用 Pipeline 执行引擎 + LLM 智能入口架构 |

### B. 模式命名规范

| 维度 | 字段名 | 值域 | 说明 | 状态 |
|------|--------|------|------|------|
| **执行引擎** | `engine_mode` | ~~`pipeline` / `llm_sop`~~ | ~~选择用哪个引擎执行任务~~ | ❌ **已废弃** |
| **交互模式** | `interaction_mode` | `auto` / `expert` | 选择人工干预程度 | ✅ 保留 |

**当前有效组合**：

| engine_mode | interaction_mode | 场景描述 | 实现状态 |
|-------------|-----------------|----------|----------|
| `pipeline` | `auto` | Pipeline全自动执行 | ✅ 已实现 |
| `pipeline` | `expert` | Pipeline + 阶段暂停干预 | ✅ 已实现 |
| ~~`llm_sop`~~ | ~~`auto`~~ | ~~LLM SOP全自动执行~~ | ❌ **已废弃** |
| ~~`llm_sop`~~ | ~~`expert`~~ | ~~LLM SOP + 人工干预~~ | ❌ **已废弃** |

> **注意**：`engine_mode` 参数已废弃，统一使用 Pipeline 执行引擎。LLM 作为智能入口（`LLMParamExtractor`）负责参数推断。




---

**文档版本**: v1.8  
**创建日期**: 2025-12-15  
**更新日期**: 2025-12-24  
**状态**: 核心功能已完成，LLM SOP执行模式已废弃

**更新记录**：
- v1.8 (2025-12-24): 新增"AI分析评估"按钮功能：全自动模式结果页可用（紫色高亮），专家模式禁用（各阶段已含AI分析）
- v1.7 (2025-12-19): LLM SOP执行模式废弃，LLM重新定位为智能入口（参数推断器），更新模式命名规范
- v1.6 (2025-12-16): 再次检查后更新：Pipeline UI Phase 4（阶段详情面板）已完成，Rule Mining Phase 3（前端分箱方法说明）已完成
- v1.5 (2025-12-16): 全面检查后更新：Hybrid阶段四（安全沙箱）已完成，阶段五部分完成（除结果对比外）；Rule Mining Phase 4（规则业务解读）已完成
- v1.4 (2025-12-16): 伪代码集成完成：扩展StageProgressCallback类型，修改Pipeline类_update_progress方法，各阶段开始时传入伪代码
- v1.3 (2025-12-16): 深度检查后更新：Rule Mining Enhancement Phase 1-2 已完成（规则质量验证+PSI稳定性检测），伪代码模板已创建待集成
- v1.2 (2025-12-16): 更新所有模块实施状态，Task Management、Hybrid Architecture、Pipeline UI核心功能已完成
- v1.1 (2025-12-16): 更新Expert Mode实施状态，添加统一暂停逻辑说明
