# CreditWise 代码审计报告 — 二次审计意见

> 审计日期：2026-06-15  
> 审计对象：`docs/code_quality_assessment_2026-06-13.md`（原报告）  
> 审计方法：逐项验证原报告数据 + 补充深度分析（6 个并行 explore agent + 上游 GitHub 溯源）

---

## 一、原报告数据准确性验证

### 1.1 文件行数验证

| 文件 | 原报告声明 | 实际 `wc -l` | 偏差 | 判定 |
|------|:--------:|:----------:|:----:|:----:|
| `deepanalyze/analysis/excel_report.py` | 4,809 | 4,809 | 0 | ✅ 准确 |
| `API/sop_api.py` | 4,592 | 4,592 | 0 | ✅ 准确 |
| `deepanalyze/analysis/html_report.py` | 3,559 | 3,559 | 0 | ✅ 准确 |
| `deepanalyze/analysis/word_report.py` | 3,177 | 3,177 | 0 | ✅ 准确 |
| `API/AI_analysis_prompts.py` | 2,571 | 2,571 | 0 | ✅ 准确 |
| `deepanalyze/analysis/markdown_report.py` | 2,427 | 2,427 | 0 | ✅ 准确 |
| `API/chat_api.py` | 2,175 | 2,175 | 0 | ✅ 准确 |
| `demo/chat/components/three-panel-interface.tsx` | **~6,500+** | **5,120** | **虚高 27%** | ❌ 严重偏差 |
| `API/scorecard_api.py` | ~280 | 334 | 偏差 | ⚠️ 粗略 |
| `API/start_server.py` | ~8 | 14 | 偏差 | ⚠️ 粗略 |
| `demo/cli/api_cli.py` | ~800 | 898 | 偏差 | ⚠️ 粗略 |

### 1.2 文件数量验证

| 指标 | 原报告声明 | 实际验证 | 判定 |
|------|:--------:|:------:|:----:|
| Python 文件 | ~180+ | **158** | ⚠️ 虚高 14% |
| TS/TSX 文件（排除 node_modules） | ~100+ | **100** | ✅ 准确 |
| 测试文件 | 21 | **22** | ⚠️ 偏差 |
| 测试数据 CSV | 6 | 6 | ✅ 准确 |

### 1.3 小结

核心大文件（7 个 Python 文件）行数**全部精确匹配**，说明原报告对后端分析较充分。但前端主文件行数严重虚高（6,500 vs 5,120），辅助数据多处粗略。

---

## 二、原报告事实错误

### 2.1 ❌ `run.py` 删除建议基于错误前提

**原报告声明**：
> `run.py` — 根目录的 demo 脚本，导入 `deepanalyze.py` 打印配置。不是启动入口，未被任何文档引用。

**实际情况**：

`run.py` 被 **6 个文档文件** 引用为启动命令：

| 文档 | 引用内容 |
|------|---------|
| `README.md` 第 77 行 | `python run.py` |
| `CLAUDE.md` 第 63、102 行 | 目录结构标注「启动入口」+ `python run.py` |
| `RELEASE_NOTES.md` 第 55、75 行 | `python run.py` |
| `docs/user_manual.md` 第 73 行 | `python run.py` |
| `docs/document_audit_report_2026-06-12.md` | 多处引用 |

**上游溯源结论**（GitHub `ruc-datalab/DeepAnalyze`）：

| 对比项 | 上游 DeepAnalyze（GitHub 原版） | CreditWise（Fork 版） |
|--------|-------------------------------|---------------------|
| `deepanalyze.py` | `DeepAnalyzeVLLM` 类，~160 行，多轮推理 + 代码执行 + vLLM 调用 | `DeepAnalyzeAPI` 类，**32 行**，仅打印配置，核心功能全部删除 |
| `run.py` | 演示脚本：调用 `DeepAnalyzeVLLM` 对 10 个数据文件做自动分析 | 演示脚本：调用阉割版 `DeepAnalyzeAPI` 打印 3 行配置 |
| 实际入口 | `demo/chat/start.sh`（WebUI）、`API/start_server.py`（API） | `API/main.py`（FastAPI）、`start_dev.ps1`（Windows） |

**关键发现**：

1. **`run.py` 在上游也不是启动入口**。上游 README 的 WebUI 启动方式是 `bash start.sh`，API 启动是 `python API/start_server.py`。`run.py` 只是 CLI 演示脚本。
2. **`deepanalyze.py` 已被 CreditWise 完全掏空**。原版核心能力全部移除，只剩空壳。
3. **`deepanalyze.py`（根目录文件）实际是死代码**。`conftest.py` 中 `import deepanalyze` 解析到的是 `deepanalyze/` **包目录**（`deepanalyze/__init__.py`），Python 包优先于同名模块文件：
   ```
   >>> import deepanalyze
   >>> deepanalyze.__file__
   './deepanalyze/__init__.py'   ← 包目录，不是 deepanalyze.py
   ```
4. **Git 历史**：两个文件自初始提交 `c272aa7` 以来**从未修改过**，属于原样保留的上游遗留。

**修正建议**：删除 `run.py` 和根目录 `deepanalyze.py`，但**必须同步修复所有文档中的启动命令引用**。

---

### 2.2 ❌ SOP 组件清单不完整

**原报告声明**：列出 17 个 SOP 组件，并称「未发现僵尸组件」。

**实际情况**：`sop/` 目录共有 **27 个组件**，遗漏了 10 个：

| 遗漏组件 | 是否活跃 | 使用位置 |
|----------|:-------:|---------|
| `TaskProgress.tsx` | ✅ | `three-panel-interface.tsx` |
| `SopStageController.tsx` | ✅ | `three-panel-interface.tsx`（4 处 JSX） |
| `PipelineCodePanel.tsx` | ❌ **僵尸** | 无任何导入 |
| `StageCodePreview.tsx` | ❌ **僵尸** | 无任何导入 |
| `StageParamsForm.tsx` | ✅ | `StageOutputPreview.tsx` |
| `ModelStatisticsPanel.tsx` | ✅ | `ScorecardResults.tsx` |
| `ScoreConverter.tsx` | ❌ **僵尸** | 无任何导入 |
| `AmountAnalysisPanel.tsx` | ✅ | `RuleMiningResults.tsx` |
| `PriorRulesInput.tsx` | ✅ | `DynamicParamRenderer.tsx` |
| `TaskHistoryList.tsx` | ❌ **僵尸** | 无任何导入（被 `TaskHistoryCompact` 替代） |

**修正结论**：发现 **4 个僵尸组件**（`PipelineCodePanel`、`StageCodePreview`、`ScoreConverter`、`TaskHistoryList`），原报告「未发现僵尸组件」的结论**不成立**。

---

### 2.3 ❌ barrel export 声明不准确

**原报告声明**：
> 所有 SOP 组件均通过 `index.ts` barrel export 且被 `three-panel-interface.tsx` 引用。

**实际情况**：

| 组件 | index.ts 导出 | 导入方式 | 使用位置 |
|------|:-----------:|---------|---------|
| `TaskGuideDialog.tsx` | ❌ 未导出 | 直接路径 `import` | `TaskConfigPanel.tsx` |
| `SensitiveCheckDialog.tsx` | ❌ 未导出 | 直接路径 `import` | `three-panel-interface.tsx` |

两个组件绕过了 barrel export，属于代码规范问题，原报告未发现。

---

## 三、原报告遗漏的重要问题

### 3.1 🔴 `main.py` 904 行且职责过重（原报告完全未提及）

`API/main.py` 包含 **7 个不同职责**，其中 workspace 管理占 **55%**（498 行）：

| 职责 | 行范围 | 行数 |
|------|--------|:----:|
| 环境初始化与配置 | 1-104 | 104 |
| LLM Manager 集成 | 66-104, 764-816 | 158 |
| 中间件注册（CORS/Auth） | 110-135 | 26 |
| 异常处理器注册 | 138-167, 841-867 | 57 |
| 路由注册（chat/sop） | 169-198 | 30 |
| **Workspace 文件管理（11 个路由）** | **223-721** | **498** |
| 前端静态文件挂载 | 818-867 | 50 |
| 服务器启动入口 | 873-904 | 32 |

Workspace 路由包括：文件列表、上传、下载、删除、移动、树结构、列信息、清空、目录删除、子目录上传、报告导出。

### 3.2 🔴 `cors_origins` 变量未定义 — 潜在运行时 Bug

`main.py:791` 引用了 `cors_origins` 变量，但该变量在 `main.py` 中**从未定义**：

```python
llm_manager_app = llm_manager.create_app(
    config={
        "app_title": "LLM API Manager for DeepAnalyze",
        "cors_origins": cors_origins,  # ← NameError!
    },
    ...
)
```

全项目搜索 `cors_origins`，仅在 `llm_manager_integrated/api/app.py`、`pure_app.py`、`create_app.py` 中有定义，`main.py` 中无任何定义或导入。

**影响范围**：当 `DEV_MODE=false`（生产模式）且 `llm_manager.available=True` 时，挂载 LLM Manager 子应用将触发 `NameError`，导致**应用启动失败**。开发模式下该代码路径不执行，故未暴露。

### 3.3 🟡 `main.py` 重复注册异常处理器

| 行号 | 异常类型 | 处理器 |
|:----:|---------|--------|
| 151 | `StarletteHTTPException` | `http_exception_handler`（注入 CORS 头） |
| 159 | `Exception` | `general_exception_handler` |
| **841** | **`StarletteHTTPException`** | **`spa_fallback`（重复！覆盖第 151 行）** |

后注册的 `spa_fallback` 会覆盖 `http_exception_handler`，导致第 151-157 行的 CORS 头注入逻辑**失效**。

### 3.4 🟡 `start_server.py` 并非完全无意义

原报告称 `start_server.py`「独立脚本入口无意义」。但验证发现：

- 上游 DeepAnalyze README 明确写了 `python API/start_server.py` 作为 API 启动方式
- `main.py` 确实有自己的 `__main__` 块，功能等价
- 当前项目无任何脚本引用它（`start_dev.ps1` 直接调用 `main.py`）

**结论**：确认可删除，但应注明是上游遗留而非「无意义」。

### 3.5 🟡 `demo/cli/` 目录存在中文版 CLI

原报告仅提及 `api_cli.py`（~800 行），遗漏了同目录下的 `api_cli_ZH.py`（899 行）。两个文件均无文档引用、无脚本调用。

---

## 四、原报告发现的修复建议（补充细化）

### 4.1 `sop_api.py` 拆分方案（4,592 行 → 9 个模块）

原报告建议「按功能域拆分为独立路由文件」，方向正确。以下是基于 51 个路由端点的详细分组：

| 模块 | 端点数 | 路由前缀 | 行范围 |
|------|:------:|---------|--------|
| `task_discovery.py` | 3 | `/tasks`、`/docs` | 470-508, 1513-1574 |
| `data_analysis.py` | 3 | `/data/*` | 509-814 |
| `execution_core.py` | 7 | `/execute`、`/unified`、`/status`、`/results`、`/code`、`/llm`、`/prompt` | 815-1456 |
| `task_control.py` | 11 | `/executions/*`（pause/stop/resume/recover/retry/reset） | 1457-1512, 2482-3374 |
| `history_management.py` | 6 | `/history`（CRUD + 批量删除 + 统计） | 3375-3772 |
| `ai_analysis_cache.py` | 8 | `/history/*/stages/*/analysis`、`/history/*/overall-analysis` | 3773-3967, 4378-4529 |
| `expert_mode.py` | 8 | `/expert/*` | 4030-4377 |
| `report_export.py` | 3 | `/report`、`/score`、`/prior-rules` | 1575-1698, 1699-2481, 4530-4592 |
| `cache_management.py` | 2 | `/cache/*` | 3632-3675 |

**共享状态**需提取到 `state.py`：`_running_tasks`、`_running_tasks_lock`、`_preview_cache`、`_TASK_RESULT_CACHE`。

**循环依赖风险**：`sop_api.py` ←→ `chat_api.py`（`sop_api` 导入 `chat_api` 的 `_parse_suggested_params`），拆分时需注意。

### 4.2 `AI_analysis_prompts.py` 拆分方案（2,571 行）

原报告建议「按 SOP 阶段拆分为独立 prompt 模块」，但实际分析发现**按功能模块拆分更合理**：

```
API/AI_analysis_prompts/
├── __init__.py              # 导出 get_analysis_prompt, AI_ANALYSIS_PARAMS
├── config.py                # 常量：STAGE_NAME_MAP, STAGE_ROLE_CONFIG（行 25-234）
├── utils.py                 # 辅助函数：_safe_get, _format_number, _unwrap_data（行 237-287）
├── overall/
│   ├── __init__.py
│   ├── scorecard.py         # _build_scorecard_overall_prompt（行 312-728，417 行）
│   └── rule_mining.py       # _build_rule_mining_overall_prompt（行 729-986，258 行）
├── stage/
│   ├── __init__.py
│   ├── data_description.py  # 所有 _build_*_description() 函数（行 1403-2506）
│   ├── params.py            # _get_stage_available_params*（行 1351-1402）
│   └── retry_context.py     # 重试对比逻辑（行 988-1185）
└── factory.py               # get_analysis_prompt() 工厂函数（行 2508-2571）
```

**外部导入影响**：仅 `chat_api.py` 导入了 3 个符号（`_get_stage_available_params_meta`、`get_analysis_prompt`、`AI_ANALYSIS_PARAMS`），改造范围可控。

### 4.3 报告生成文件拆分方案（4 文件共 13,972 行）

原报告建议「按 Sheet 类型拆分为多个生成器模块」，方向正确。补充细节：

| 文件 | 建议拆分为 | 拆分依据 |
|------|-----------|---------|
| `excel_report.py` (4,809) | 5 个文件 | 按 Sheet 类型：base / core / scorecard / rule_mining / utils |
| `html_report.py` (3,559) | 6 个文件 | 按功能：viz / styles / components / core / rule_mining / scorecard |
| `word_report.py` (3,177) | 5 个文件 | 按功能：utils / components / core / scorecard / rule_mining |
| `markdown_report.py` (2,427) | 4 个文件 | 按任务类型：core / rule_mining / scorecard / utils |

**额外发现**：`code_templates.py` 第 186 行引用了不存在的 `deepanalyze.analysis.report.ReportGenerator`，应修复。

### 4.4 前端重构

原报告提及 `right_panel_unified_architecture_plan.md` 和 8-12 天工作量。补充修正：

- Monaco Editor 实例化实际为 **4 处**（非原报告暗示的 2 处）：
  - `three-panel-interface.tsx` 第 4687 行（Chat 代码块编辑器）
  - `three-panel-interface.tsx` 第 4982 行（文件预览）
  - `StageCodeEditor.tsx` 第 270 行（SOP 阶段代码编辑器）
  - `StageParameterEditor.tsx` 第 184 行（SOP 阶段参数编辑器）

---

## 五、修正后的行动优先级

### P0 — 立即执行（安全 / 正确性）

| # | 行动 | 影响 | 工作量 |
|:-:|------|------|:------:|
| 1 | 修复 `main.py:791` 的 `cors_origins` 未定义 Bug | 修复生产模式启动崩溃 | 10 分钟 |
| 2 | 修复 `main.py` 重复注册 `StarletteHTTPException` 处理器 | 修复 CORS 头丢失 | 15 分钟 |
| 3 | 删除 `run.py` + 根目录 `deepanalyze.py` | 消除误导 | 5 分钟 |
| 4 | 同步修复 6 个文档中的 `python run.py` 引用 → `python API/main.py` | 文档一致性 | 30 分钟 |
| 5 | 删除 `API/start_server.py` | 减少混淆 | 1 分钟 |
| 6 | 删除 `API/scorecard_api.py`（已标 `[ARCHIVED]`） | 减少混淆 | 1 分钟 |
| 7 | 确认并删除 `demo/cli/api_cli.py` + `api_cli_ZH.py` | 减少维护 | 5 分钟 |
| 8 | 更新 `docker/Dockerfile` 移除 `run.py` 和 `deepanalyze.py` 的 COPY | Docker 瘦身 | 5 分钟 |

### P1 — 短期执行（可维护性）

| # | 行动 | 影响 | 工作量 |
|:-:|------|------|:------:|
| 9 | 提取 `main.py` 的 11 个 workspace 路由到 `workspace_api.py` | `main.py` 减少 ~500 行 | 2 小时 |
| 10 | 拆分 `AI_analysis_prompts.py` 为包结构 | 降低 Prompt 修改门槛 | 2 小时 |
| 11 | 拆分 `sop_api.py` 为 9 个功能域模块 | 降低合并冲突风险 | 3 小时 |
| 12 | 删除 4 个僵尸前端组件 + 修复 2 个绕过 barrel export 的导入 | 减少前端死代码 | 30 分钟 |

### P2 — 中期执行（架构优化）

| # | 行动 | 影响 | 工作量 |
|:-:|------|------|:------:|
| 13 | 拆分 4 个报告生成文件（共 13,972 行 → ~20 个文件） | 降低改动风险 | 1-2 天 |
| 14 | 执行 `right_panel_unified_architecture_plan.md` | 消除 Monaco 4 实例 + 职责过重 | 8-12 天 |
| 15 | 修复 `code_templates.py` 中对不存在的 `ReportGenerator` 的引用 | 消除潜在运行时错误 | 15 分钟 |

---

## 六、原报告评分

| 维度 | 评分 | 说明 |
|------|:----:|------|
| 数据准确性 | **6/10** | 核心大文件行数精确，但前端主文件虚高 27%，辅助数据多处偏差 |
| 分析完整性 | **5/10** | 遗漏 `main.py`（904 行）的关键问题，前端组件清单不完整 |
| 建议可行性 | **7/10** | 优先级排序合理，但 `run.py` 删除建议未考虑文档依赖 |
| 前端分析 | **6/10** | 遗漏 10 个组件、4 个僵尸组件、2 个 barrel export 绕过 |
| 上游溯源 | **未做** | 未识别 `run.py` / `deepanalyze.py` 为上游遗留文件 |

**总评：5.5/10 — 框架合理但执行粗糙。**

核心价值在于对后端大文件的识别和优先级排序。主要缺陷是：
1. 数据验证不严谨（前端行数、组件清单）
2. 遗漏 `main.py` 的关键问题（`cors_origins` Bug、异常处理器覆盖）
3. 未做上游溯源，导致对 `run.py` 的判断基于错误前提

**建议**：在执行任何 P0 操作前，先按本报告修正后的优先级行动，优先修复 `cors_origins` Bug（生产模式崩溃风险）。

---

> *本报告基于 2026-06-15 代码库状态，结合 6 个并行 explore agent 深度分析 + GitHub 上游仓库溯源 + git 历史追踪生成。*
