# CreditWise 项目文档审计报告

> **审计日期**: 2026-06-12  
> **审计方式**: 全量扫描 69 个 .md 文件，结合代码核实完成状态（含 pull 最新 commit db49fe6 后新增的 1 个文档）  
> **审核人**: AI Assistant（基于 CLAUDE.md + 代码库交叉验证）

---

## 目录

1. [需废弃/删除的文档](#一需废弃删除-5-个)
2. [需更新内容的文档](#二需更新内容-6-个)
3. [可归档的文档](#三可归档-17-个)
4. [完全待实施 — PENDING](#四完全待实施--pending-3-个)
5. [分批完成 — 核心已上线，剩余 Phase 待推进](#五分批完成-2-个)
6. [应保留的核心文档](#六应保留的核心文档)
7. [统计汇总](#七统计汇总)
8. [底线变动说明](#八底线变动说明)
9. [关于项目介绍文档的建议](#九关于项目介绍文档的建议)

---

## 一、需废弃/删除 (5 个)

| # | 文件 | 原因 |
|---|------|------|
| 1 | `deepanalyze/README.md` | 空文件，仅 1 字节 |
| 2 | `API/README.md` | 引用原始 DeepAnalyze-8B vLLM 架构，与 CreditWise「外部 API + LLM Manager 代理」架构无关 |
| 3 | `API/README_ZH.md` | 同上 |
| 4 | `demo/cli/README.md` | 引用已废弃的命令行工具和 vLLM 服务 |
| 5 | `demo/cli/README_ZH.md` | 同上 |

---

## 二、需更新内容 (6 个)

| # | 文件 | 需更新内容 |
|---|------|-----------|
| 1 | **`README.md`** | ① 突出信贷风控定位而非通用数据科学；② 补充 macOS `python run.py` + Docker 启动方式；③ 展示两大核心任务（规则挖掘/评分卡）和 Pipeline 架构特色；④ 移除不存在的 `SCRIPT_USAGE.md` 引用 |
| 2 | **`RELEASE_NOTES.md`** | v1.0.0-beta.1 距今 3 个月，需补充关键更新（阶段重试、AI 建议卡片、OPT-1 双 prompt、不平衡处理、WOE 参数分离等） |
| 3 | `docs/project_status_summary.md` | 最后更新 2026-03-11，多个文档状态已过时（`feature_derivation_refactor` 和 `rule_mining_enhancement` 实际已完成但标记为待实施） |
| 4 | `docs/analysis_prompt_refactor_plan.md` | Phase 2（分析深度变体：快速/标准/详细）尚未实施，需明确是否推进 |
| 5 | `docs/report_config_driven_plan.md` | Phase 2（配置驱动方案）标记 "⏳ 待实施"，`FieldDisplayConfig`/`ConfigDrivenReportGenerator` 零代码，需确认 |
| 6 | `docs/taskSOP_solution/rule_mining_oot_validation_design.md` | 开发评审标注 "建议轻量评审" + 参数删除向后兼容等风险项，实际 Phase 1-6 全完成，可清理评审提示 |

---

## 三、可归档 (17 个)

已实现功能的测试方案或设计文档，建议移入 `docs/archive/`：

### 测试方案/手册（6 个）

| # | 文件 | 说明 |
|---|------|------|
| 1 | `docs/resume_test_guide.md` | 暂停/恢复功能测试，功能已验证 |
| 2 | `docs/test_analysis_report.md` | 任务管理模块测试分析报告（2025-01-05） |
| 3 | `docs/test_strategy_resume_functionality.md` | Resume 功能测试策略 |
| 4 | `docs/taskSOP_solution/amount_analysis_test_plan.md` | 金额分析测试方案 |
| 5 | `docs/taskSOP_solution/amount_prior_manual_test_guide.md` | 金额+先验规则测试 |
| 6 | `docs/taskSOP_solution/class_imbalance_manual_test_guide.md` | 不平衡处理测试 |

### 已完成功能的设计文档（11 个）

| # | 文件 | 说明 |
|---|------|------|
| 7 | `docs/taskSOP_solution/prior_rules_enhancement_plan.md` | 先验规则增强（已实施） |
| 8 | `docs/taskSOP_solution/polling_optimization_design.md` | 轮询优化（已完成） |
| 9 | `docs/taskSOP_solution/sample_feature_tab_design.md` | 样本特征 Tab（已完成） |
| 10 | `docs/taskSOP_solution/SOP_WebUI_Integration_design.md` | WebUI 集成设计 |
| 11 | `docs/taskSOP_solution/SOP_WebUI_detail_design.md` | WebUI 详细设计 |
| 12 | `docs/taskSOP_solution/scorecard_result_adjustment_design.md` | 评分卡结果调整（全部完成） |
| 13 | `docs/taskSOP_solution/ai_suggest_retry_design.md` | AI 建议重试（已实施） |
| 14 | `docs/taskSOP_solution/class_imbalance_handling_plan.md` | 不平衡处理（MVP 完成） |
| 15 | `docs/taskSOP_solution/model_evaluation_params_design.md` | 模型评估参数（Part 1+CSI 已完成） |
| 16 | `docs/taskSOP_solution/pipeline_ui_enhancement_design.md` | Pipeline UI 增强（Phase 1-4 完成） |
| 17 | `docs/taskSOP_solution/chat_api_integration_design.md` | Chat API 融合（全部完成） |

---

## 四、完全待实施 — PENDING (3 个)

**零功能代码，纯设计文档阶段。**

| # | 文件 | 定位 | 优先级 |
|---|------|------|:--:|
| 1 | `docs/taskSOP_solution/strategy_diagnosis_plan.md` | **策略诊断 SOP 任务**：Swap Set 四象限分析、人数/金额双口径对比、换入/换出客群画像。从 `prior_rules_enhancement` 拆分出的独立 SOP，服务于规则挖掘+评分卡两个任务 | P2-P3 |
| 2 | `docs/multimodal_chat_plan.md` | **多模态对话**：图片粘贴/拖拽、OpenAI Vision API 集成 | 中 |
| 3 | `docs/right_panel_unified_architecture_plan.md` | **右侧面板统一架构重构**：消除 Monaco Editor 双实例化、引入 React Context 统一状态管理、8-12 天前端工作量 | 中 |

> **PENDING 定义**: 只有设计文档，无任何功能代码。三个任务都处于方案设计阶段，未开始编码。

---

## 五、分批完成 (2 个)

**核心功能已上线运行，仅剩增量 Phase 未动工。**

| # | 文件 | 已完成 | 剩余 Phase | 优先级 |
|---|------|--------|-----------|:--:|
| 1 | `docs/taskSOP_solution/analysis_prompt_refactor_plan.md` | Phase 0/1/1.5（prompt 从 550 行前端硬编码抽离到后端 ~1900 行） | Phase 2：分析深度变体（快速/标准/详细三档），`analysis_depth` 参数已预留但仅支持 "standard" | 低 |
| 2 | `docs/taskSOP_solution/report_config_driven_plan.md` | Phase 0-1.6（HTML/MD/Word/Excel 报告版式统一为 6 章节） | Phase 2：配置驱动（`FieldDisplayConfig`/`ConfigDrivenReportGenerator`），让 `task_result_config.py` 从闲置变为实际驱动前端 Tab 和后端报告生成 | 低 |

> **分批完成定义**: 与 PENDING 的区别在于核心功能已上线运行并经过验证，仅剩增量优化 Phase（如深度变体、配置驱动），不影响现有功能正常使用。

---

## 六、应保留的核心文档

### 元文档 / 开发指南

| # | 文件 | 角色 |
|---|------|------|
| 1 | `CHANGELOG.md` | 功能开发清单 |
| 2 | `CLAUDE.md` | 项目级 AI/开发者指南（最新 2026-06-12） |
| 3 | `CONTRIBUTION.md` | 贡献指南 |

### 部署与运维

| # | 文件 | 角色 |
|---|------|------|
| 4 | `docker/README.md` | Docker 部署指南 |
| 5 | `docs/deployment_guide.md` | 通用部署指南 |
| 6 | `docs/intranet_deployment_guide.md` | 内网多用户部署指南 |
| 7 | `docs/online_multiuser_deployment_assessment.md` | 多用户部署评估报告 |
| 8 | `docs/cvm_deployment_test_plan.md` | CVM 新部署方案验证测试计划（db49fe6 新增，当前活跃） |
| 9 | `docs/dual_platform_git_guide.md` | 工蜂+GitHub 双平台推送指南 |

### 架构设计

| # | 文件 | 角色 |
|---|------|------|
| 9 | `docs/LLM_Manager_guide.md` | LLM Manager 使用指南 |
| 10 | `docs/LLM_Optimization_design.md` | LLM+Pipeline 架构设计 |
| 11 | `docs/DeepAnalyze_upgrade_design.md` | StatisticalLogisticRegression 等底层模块设计 |
| 12 | `docs/routing_architecture_guide.md` | 前后端路由架构参考 |
| 13 | `docs/taskSOP_solution/pipeline_llm_hybrid_design.md` | Pipeline+LLM 混合架构设计 |

### System Prompt

| # | 文件 | 角色 |
|---|------|------|
| 14 | `docs/system_prompt_guide.md` | System Prompt 设计规范 |
| 15 | `docs/system_prompt_restructuring_design.md` | Prompt 重构方案（已完成） |

### SOP 任务设计（已完成）

| # | 文件 | 角色 |
|---|------|------|
| 16 | `docs/taskSOP_solution/rule_mining_task_design.md` | 规则挖掘 SOP 构建方案 |
| 17 | `docs/taskSOP_solution/rule_mining_workflow.md` | 规则挖掘工作流说明 |
| 18 | `docs/taskSOP_solution/rule_mining_oot_validation_design.md` | OOT 验证设计（✅ 全部完成） |
| 19 | `docs/taskSOP_solution/rule_mining_enhancement_design.md` | 规则挖掘增强设计（✅ 全部完成） |
| 20 | `docs/taskSOP_solution/feature_derivation_refactor_design.md` | 特征衍生重构设计（✅ 全部完成） |
| 21 | `docs/taskSOP_solution/scorecard_dev_workflow.md` | 评分卡工作流说明 |
| 22 | `docs/taskSOP_solution/scorecard_development_task_design.md` | 评分卡 SOP 构建方案 |
| 23 | `docs/taskSOP_solution/task_report_ai_analysis_design.md` | 报告生成+AI 分析框架 |
| 24 | `docs/taskSOP_solution/task_sop_expert_mode_design.md` | 专家模式设计 |
| 25 | `docs/taskSOP_solution/task_management_module_design.md` | 任务管理模块设计（✅ 全部完成） |
| 26 | `docs/taskSOP_solution/unified_implementation_roadmap.md` | 统一实施路线图 |

### 项目复盘与规划

| # | 文件 | 角色 |
|---|------|------|
| 27 | `docs/project_development_review.md` | 项目开发复盘（2026-04-07） |
| 28 | `docs/release_readiness_plan.md` | Release 就绪计划（Phase 2-5 待推进） |

### 业务指南

| # | 文件 | 角色 |
|---|------|------|
| 29 | `docs/规则指标体系与策略应用指南.md` | 规则指标定义与公式 |
| 30 | `docs/规则重叠与策略编排指南.md` | 规则重叠、贪婪算法、策略编排 |

### 测试与安全

| # | 文件 | 角色 |
|---|------|------|
| 31 | `docs/sensitive_account_manual_test_guide.md` | 安全测试指南（2026-06-01） |

### 子模块说明

| # | 文件 | 角色 |
|---|------|------|
| 32 | `example/README.md` | 示例贡献指南 |
| 33 | `example/analysis_on_student_loan/README.md` | 学生贷款分析案例 |
| 34 | `example/simpson_paradox_analysis/README.md` | 辛普森悖论分析案例 |
| 35 | `demo/jupyter/README.md` | Jupyter 前端说明 |
| 36 | `demo/jupyter/README_ZH.md` | Jupyter 前端说明（中文） |
| 37 | `llm_manager_integrated/react-components/README.md` | LLM Manager React 组件库说明 |

---

## 七、统计汇总

| 类别 | 数量 | 占比 |
|------|:--:|:--:|
| 🔴 废弃/删除 | 5 | 7.2% |
| 🟡 需更新 | 6 | 8.7% |
| 🟠 可归档 | 17 | 24.6% |
| ⚪ PENDING（零代码） | 3 | 4.3% |
| 🟣 分批完成（核心已上线） | 2 | 2.9% |
| ✅ 保留 | 38 | 55.1% |
| **合计** | **69** | 100% |

---

## 八、底线变动说明

本次审计过程中，以下文档的状态经代码实际核实后发生了变更：

| 原状态 | 文件 | 核实后状态 | 证据 |
|--------|------|-----------|------|
| 待实施 | `taskSOP_solution/feature_derivation_refactor_design.md` | ✅ 已实施 | `rule_mining.py:6336-6337` `do_datetime=False, do_text=False`；`rule_mining.py:6622-6654` datetime/text 衍生代码含 P1-4 标记 |
| 待评审 | `taskSOP_solution/rule_mining_enhancement_design.md` | ✅ 已完成 | `RuleValidator:4552` / `RuleInterpreter:5327` / `calculate_rule_psi:3036` / 前端 `ValidationReportPanel` + `PSIReportPanel` |
| Phase 6 待实施 | `taskSOP_solution/rule_mining_oot_validation_design.md` | ✅ 全部完成 | `tests/test_oot_validation.py` 覆盖 TC001-TC008 |
| Phase 25 待实施 | `taskSOP_solution/task_management_module_design.md` | ✅ 全部完成 | `API/sop_api.py:3676` `POST /history/batch-delete` + `BatchDeleteRequest` 模型 + 级联清理逻辑 + 前端批量删除 UI |
| 主报告漏列 | `taskSOP_solution/strategy_diagnosis_plan.md` | 确认 PENDING | v0.1 框架，零代码实现，优先级 P2-P3 |
| 状态标注错误 | `taskSOP_solution/rule_mining_ooo_validation_design.md`（项目状态汇总） | 已修正 | `project_status_summary.md` 中 Phase 25 引用从 "待实施" 改为 "已完成" |

---

## 九、关于项目介绍文档的建议

**结论：不建议新建独立文档，重点更新现有 `README.md` 即可。**

理由：

| 评估维度 | 分析 |
|----------|------|
| **现有 README 的问题** | 第 47-50 行直接引用原始 DeepAnalyze 论文的通用数据科学描述，未突出 CreditWise **信贷风控专项**定位；启动方式只列 PowerShell；未提及两大核心 SOP 任务 |
| **CLAUDE.md 的定位** | 已包含架构决策、关键文件、已知问题等开发视角信息，但面向 AI/开发者而非最终用户 |
| **project_development_review.md** | 有完整的项目定位和功能矩阵，但属内部复盘文档，不适合作为对外 README |
| **README 改造方向** | 突出六大模块：LLM+Pipeline 架构 → 规则挖掘 → 评分卡开发 → WOE/IV → LLM Manager → Docker 内网部署；补充典型使用场景和快速体验流程 |

**建议的 README 结构**：
```
1. CreditWise 定位（一句话 + 核心差异化 vs 原始 DeepAnalyze）
2. 核心能力（规则挖掘流程 / 评分卡开发流程 图文展示）
3. 架构特色（LLM 智能入口 + Pipeline 确定性执行 图解）
4. 快速开始（macOS python run.py / Docker / PowerShell 三选一）
5. LLM Manager 多渠道路由
6. 详细文档索引（指向 docs/ 下核心文档）
```

---

> **审计结论归档日期**: 2026-06-12  
> **建议复审周期**: 每季度或重大版本发布后
>
> ### 更新记录
>
> | 时间 | 说明 |
> |------|------|
> | 2026-06-12 16:41 | 初版完成，覆盖 68 个 .md 文件 |
> | 2026-06-12 16:42 | pull commit `db49fe6`，新增 `docs/cvm_deployment_test_plan.md`（CVM 部署方案验证测试计划），归入「保留—部署与运维」，总数更新为 69 |
> | 2026-06-17 | 执行审计建议 + 补充更新：① §二 #1 `README.md` 已更新（版本 bate.2 badge、起源描述、Python 3.10+、docker compose、文档索引精简至 6 条）；② §二 #2 `RELEASE_NOTES.md` 已补充（Bug 修复汇总表、安全细节、级联清理范围）；③ `CHANGELOG.md` 新增 `[1.0.0-beta.1]` 和 `[1.0.0-beta.2]` 两版本章节（覆盖 2026.01-06 全部功能+Bug）；④ `LICENSE` 版权年份 2025→2025-2026；⑤ `docs/routing_architecture_guide.md` 已归档至 `docs/archive/`（路由严重过时，FastAPI /docs 可替代）；⑥ `rule_mining_workflow.md` + `scorecard_dev_workflow.md` 补充专家模式 AI 建议交互流程 |
