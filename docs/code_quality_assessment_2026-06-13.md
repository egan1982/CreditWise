# CreditWise 代码质量与冗余评估报告

> 评估日期：2026-06-13  
> 评估范围：全项目 Python/TypeScript 文件  
> 评估方法：代码库静态分析 + 依赖关系追踪 + 量化指标统计

---

## 一、代码规模概况

| 指标 | 数值 |
|------|------|
| Python 文件 | ~180+ 个 |
| TypeScript/TSX 文件 | ~100+ 个 |
| 最大单文件 | `excel_report.py`（4,809 行） |
| 前端主文件 | `three-panel-interface.tsx`（~6,500+ 行） |

---

## 二、超大文件警告（> 2000 行）

以下文件严重超过行业推荐的 500-800 行上限，属于需要关注的重构候选：

| # | 文件 | 行数 | 风险 | 建议 |
|---|------|:--:|------|------|
| 1 | `deepanalyze/analysis/excel_report.py` | **4,809** | 🔴 严重 | 按 Sheet 类型拆分为多个生成器模块 |
| 2 | `API/sop_api.py` | **4,592** | 🔴 严重 | 按功能域拆分为独立路由文件（task/execute/expert/history/docs） |
| 3 | `deepanalyze/analysis/html_report.py` | **3,559** | 🔴 严重 | 按报告章节拆分为多个 HTML 构建模块 |
| 4 | `deepanalyze/analysis/word_report.py` | **3,177** | 🔴 严重 | 按报告章节拆分，与 html_report 对齐结构 |
| 5 | `API/AI_analysis_prompts.py` | **2,571** | 🟡 高 | 按 SOP 阶段拆分为独立 prompt 模块（规则挖掘/评分卡/通用） |
| 6 | `deepanalyze/analysis/markdown_report.py` | **2,427** | 🟡 高 | 与 html/word/excel 报告同步拆分 |
| 7 | `API/chat_api.py` | **2,175** | 🟡 高 | 逻辑已通过 Prompt Provider 解耦，可进一步拆分路由 |
| 8 | `demo/chat/components/three-panel-interface.tsx` | **~6,500** | 🔴 严重 | 右侧面板架构重构计划已存在（`right_panel_unified_architecture_plan.md`），8-12 天工作量 |

**影响**：大文件导致单文件改动风险高、Code Review 困难、新人上手慢。其中 `sop_api.py` 已纳入架构决策（CLAUDE.md），其余 4 个报告文件属于生成器类代码，拆分难度较低。

---

## 三、冗余/无效文件

### 3.1 确定冗余 — 建议删除

| # | 文件 | 行数 | 原因 |
|---|------|:--:|------|
| 1 | `API/scorecard_api.py` | ~280 | **未注册到 main.py**，所有评分卡功能已迁移到 sop_api.py。文件存在但永远不会被调用 |
| 2 | `API/start_server.py` | ~8 | 仅一行 `from main import main; main()`，`main.py` 有自己的 `__main__` 块。独立脚本入口无意义 |
| 3 | `run.py` | ~15 | 根目录的 demo 脚本，导入 `deepanalyze.py` 打印配置。不是启动入口，未被任何文档引用 |

### 3.2 可能冗余 — 需确认

| # | 文件 | 说明 |
|---|------|------|
| 1 | `demo/cli/api_cli.py` | ~800 行 CLI 工具，当下面向 Web UI 使用，CLI 可能不再需要。需确认是否有用户通过命令行使用 |

### 3.3 代码重复

| 位置 | 问题 | 严重程度 |
|------|------|:--:|
| `three-panel-interface.tsx` vs `StageCodeEditor.tsx` | Monaco Editor 实例化了**双份**，`executeCode` 逻辑相似但不完全相同。已有重构计划（`right_panel_unified_architecture_plan.md`） | 🟡 中 |
| `deepanalyze/analysis/preprocessing.py` vs `rule_mining.py#DataPreprocessor` | 底层预处理工具被 Pipeline 层封装，但两者之间有薄封装层。结构合理但需注意不要出现分支逻辑 | 🟢 低 |

---

## 四、前端组件状况

### 4.1 已确认活跃的 SOP 组件

所有 `demo/chat/components/sop/` 下的组件均通过 `index.ts` barrel export 且被 `three-panel-interface.tsx` 引用：

`TaskSelector`、`TaskConfigPanel`、`DynamicParamRenderer`、`StageOutputPreview`、`StageCodeEditor`、`StageParameterEditor`、`ExecutionLogPanel`、`RuleMiningResults`、`ScorecardResults`、`TaskHistoryList`、`TaskHistoryCompact`、`TaskConfirmCard`、`SuggestedParamsCard`、`StageVersionSelector`、`TaskGuideDialog`、`ModeSelector`、`SensitiveCheckDialog`

**未发现僵尸组件。**

### 4.2 ModeSelector 清理确认

`ModeSelector.tsx` 已正确移除 LLM SOP 模式，仅保留 `auto` 和 `expert` 两个选项。`index.ts` 中 `EngineMode` 类型导出已标记废弃。清理到位。

---

## 五、test 目录状况

| 指标 | 数值 |
|------|------|
| 测试文件 | 21 个 `.py` |
| 测试数据 | 6 个 `.csv` |
| 无引用已删除功能的测试 | ✅ |
| 无空测试文件 | ✅ |

测试文件均覆盖当前活跃功能模块，无僵尸测试。

---

## 六、已知但未构成紧急问题的代码债

| # | 问题 | 位置 | 已有计划？ |
|---|------|------|:--:|
| 1 | `three-panel-interface.tsx` 职责过重（布局+代码编辑+状态） | 前端 | ✅ `right_panel_unified_architecture_plan.md` |
| 2 | 6 个文件 > 2000 行 | 后端报告+SOP API | ❌ 无正式计划 |
| 3 | Monaco Editor 双份实例化 | 前端 | ✅ 同上 |
| 4 | `AI_analysis_prompts.py` 2571 行纯字符串拼接 | 后端 | ❌ 无正式计划 |
| 5 | `sop_api.py` 4592 行单一路由文件 | 后端 | ⚠️ CLAUDE.md 提及但无拆分计划 |

---

## 七、推荐行动优先级

| 优先级 | 行动 | 影响 | 工作量 |
|:--:|------|------|:--:|
| **P0** | 删除 3 个冗余文件（`scorecard_api.py`、`start_server.py`、`run.py`） | 减少混淆 | 5 分钟 |
| **P0** | 确认 `demo/cli/api_cli.py` 是否仍需保留 | 减少维护 | 5 分钟 |
| **P1** | 拆分 `AI_analysis_prompts.py` 按阶段分模块 | 降低新人修改 Prompt 的门槛 | 2 小时 |
| **P1** | 拆分 `sop_api.py` 按功能域分路由 | 降低合并冲突风险 | 3 小时 |
| **P2** | 拆分 4 个报告生成文件（excel/html/word/markdown） | 降低改动风险 | 1-2 天 |
| **P2** | 执行 `right_panel_unified_architecture_plan.md` | 消除 Monaco 双实例 | 8-12 天 |

---

> *本报告基于 2026-06-13 代码库状态，结合文档审计、Graphiti 知识图谱和跨模块代码分析生成。*
