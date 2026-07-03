# DeepAnalyze 项目文档状态汇总

> 生成时间：2026-03-11  
> 用途：为项目下一步开发提供指引  
> 范围：docs/ 目录下所有设计/计划文档

---

## 📊 总体概览

| 类别 | 数量 |
|------|------|
| ✅ 已实现/已验证/已完成 | 24个 |
| ⚠️ 部分实现 | 4个 |
| 📋 待实施/待开发 | 15个（原新增的"用户管理与数据隔离相关"1项已于2026-07-02完成开发，详见第18项；新增1项：全量测试基础设施历史债务排查发现，详见第19项；新增1项：CVM部署测试发现的已知限制/技术债，详见第20项） |

---

## ✅ 已实现/已验证/已完成（21个）

| 文档路径 | 状态 | 说明 |
|---------|------|------|
| `docs/system_prompt_guide.md` | ✅ 已实现 V3.0 | Prompt架构指南（v2.2→v3.0，更新mode分流架构） |
| `docs/test_strategy_resume_functionality.md` | ✅ 已验证 | Resume功能测试策略 |
| `docs/chat_api_integration_design.md` | ✅ 全部完成 | Chat API融合 |
| `docs/resume_test_guide.md` | ✅ 已实现 | 暂停/恢复测试指南 |
| `docs/test_analysis_report.md` | ✅ 已实现 | 任务管理测试报告 |
| `docs/DeepAnalyze_upgrade_design.md` | ✅ 已实现 V4.2 | 功能升级设计 |
| `docs/LLM_Manager_guide.md` | ✅ 已实现 | 使用指南 |
| `docs/README.md` | ✅ 已实现 | 项目说明 |
| `docs/LLM_Optimization_design.md` | ✅ 已清理 | LLM+Pipeline架构 |
| `docs/routing_architecture_guide.md` | ✅ 已实现 | 路由架构指南 |
| `docs/online_multiuser_deployment_assessment.md` | ✅ 评估完成 V1.2 | 线上多用户部署评估报告 |
| `docs/规则指标体系与策略应用指南.md` | ✅ 已完成 | 规则指标体系与策略应用指南 |
| `docs/规则重叠与策略编排指南.md` | ✅ 已完成 | 规则重叠与策略编排指南 |
| `docs/taskSOP_solution/pipeline_llm_hybrid_design.md` | ✅ 已清理 | 混合架构设计 |
| `docs/taskSOP_solution/unified_implementation_roadmap.md` | ✅ 已清理 | 实施路线图 |
| `docs/taskSOP_solution/task_sop_expert_mode_design.md` | ✅ 已清理 | 专家模式设计 |
| `docs/taskSOP_solution/scorecard_result_adjustment_design.md` | ✅ 已实现 | 评分卡结果设计 |
| `docs/taskSOP_solution/sample_feature_tab_design.md` | ✅ 已完成 | 样本特征Tab设计 |
| `docs/taskSOP_solution/task_management_module_design.md` | ✅ Phase 6/7/8完成 | 任务管理模块设计 |
| `docs/taskSOP_solution/rule_mining_task_design.md` | ✅ 已实现 | 规则挖掘任务设计 |
| `docs/taskSOP_solution/scorecard_development_task_design.md` | ✅ 已实现 | 评分卡开发任务设计 |
| `docs/taskSOP_solution/SOP_WebUI_Integration_design.md` | ✅ 已实现 | WebUI集成计划 |

---

## ⚠️ 部分实现（5个）

### 1. analysis_prompt_refactor_plan.md

| 项目 | 内容 |
|------|------|
| **当前状态** | Phase 0/1/1.5已完成，Phase 2/3待评估 |
| **待实施内容** | **Phase 2 - Prompt模板格式标准化**（~2天）：统一变量占位符、建立命名规范、创建验证机制  <br>**Phase 3 - Prompt结构化拆解**（~3天，待评估）：将大Prompt拆分为小模块、建立模块依赖关系、实现动态组装 |

### 2. model_evaluation_params_design.md

| 项目 | 内容 |
|------|------|
| **当前状态** | Part 1已完成，Part 2 ✅ 已完成（2026-04-15） |
| **待实施内容** | ~~**CSI（特征稳定性）指标**~~ → ✅ 已实现：`_calculate_csi_for_variables()` 函数、前端 CSI 展示、AI 分析 Prompt 集成  <br>~~变量WOE单调性汇总~~ → 已移除（完整评分卡表格已满足需求） |

### 3. report_config_driven_plan.md

| 项目 | 内容 |
|------|------|
| **当前状态** | Phase 0-1.6已完成，Phase 2待启动 |
| **待实施内容** | **Phase 2 - 配置驱动完整方案**（~2-2.5天）：配置模型增强（FieldDisplayConfig等可选增强）、报告生成器改造（HTML/Word/Markdown读取配置动态渲染）、前端Tab列表改造（仅改Tab导航渲染，保留所有子组件）、前端配置同步API（`/api/sop/config/{task_type}`） |

### 4. task_report_ai_analysis_design.md

| 项目 | 内容 |
|------|------|
| **当前状态** | P0/P1/P2核心功能已全部实现 |
| **待实施内容** | ~~PDF报告生成~~ → ❌ 已废弃（改用HTML打印为PDF方案）  <br>✅ Excel任务报告Sheet + 阶段数据整合 → **已实现**  <br>✅ Word报告生成 → **已实现**  <br>📋 **端到端测试验证** → 待完成 |

### 5. release_readiness_plan.md

| 项目 | 内容 |
|------|------|
| **当前状态** | v1.8，发布前代码审计修复已全部完成（P0全部完成，P1必修全部完成，P1建议级完成14/16，P2已修复2/8） |
| **待实施内容** | **Phase 2 - GitHub配置**（Week 1-2）：仓库配置、CI/CD  <br>**Phase 3 - 质量保障**（Week 2）：测试覆盖、性能基准  <br>**Phase 4 - 发布执行**（Week 2-3）：版本发布、部署文档  <br>**Phase 5 - 私有化部署打包配置** |

---

## 📋 待实施/待开发（8个）

### 6. system_prompt_restructuring_design.md

| 项目 | 内容 |
|------|------|
| **当前状态** | ✅ 已完成（2026-04-15） |
| **已实施内容** | 对话/参数提取路径 Prompt 重构：引入显式 `mode` 参数（`"chat"` / `"extraction"`）取代 `_is_param_extraction_mode()` 关键词嗅探，统一由 `TaskPromptProvider.build_system_prompt(mode=...)` 构建。额外修复：chat mode 下渠道 system_prompt 不再污染对话 |

### 8. multimodal_chat_plan.md

| 项目 | 内容 |
|------|------|
| **当前状态** | 待实施 |
| **待实施内容** | 粘贴图片到输入框（Ctrl+V粘贴剪贴板图片）、拖拽文件到输入框、图片预览显示（发送前预览已添加的图片）、多模态消息格式（OpenAI Vision API格式支持） |
| **预计工作量** | 1-2天 |

### 9. right_panel_unified_architecture_plan.md

| 项目 | 内容 |
|------|------|
| **当前状态** | 待实施（前置依赖：Chat API融合方案完成后） |
| **待实施内容** | Right Panel统一架构优化 |
| **优先级** | 中期优化 |

### 10. class_imbalance_handling_plan.md

| 项目 | 内容 |
|------|------|
| **当前状态** | ✅ Phase 1 MVP 已完成 + 测试通过（2026-04-16，10/10 PASS）|
| **已实施内容** | MVP: none/auto/class_weight 三选项。7 个文件改动：2 meta + rule_mining.py（决策树 class_weight）+ scorecard_development.py（LR class_weight）+ executor.py 传参 + AI_analysis_prompts.py 不平衡引导 + StageOutputPreview.tsx 不平衡卡片。auto 策略：bad_rate<10%→class_weight，否则→none |
| **测试结果** | `tests/test_imbalance_strategy.py` 10/10 通过（真实数据 starrel_train_with_amount.csv）：E8 信息完整性 + T6×3 规则挖掘对照 + T8 权重叠加 + T9/E3 统计正确性 + T7×4 评分卡对照+权重叠加 |
| **待实施内容** | 类别不平衡处理功能（关联任务：规则挖掘、评分卡开发） |
| **优先级** | 中 |

### 11. feature_derivation_refactor_design.md

| 项目 | 内容 |
|------|------|
| **当前状态** | 待实施 |
| **待实施内容** | **全部未实现**：datetime衍生从preprocessing移至feature_engineering、text衍生从preprocessing移至feature_engineering、preprocessing阶段只保留数据清洗和质量评估、更新output_preview结构、prompt模板更新 |
| **预计工作量** | 1-2天 |

### 12. polling_optimization_design.md

| 项目 | 内容 |
|------|------|
| **当前状态** | ✅ 已完成（2026-04-15） |
| **已实施内容** | 实现 `pollTrigger` 机制（TaskProgress.tsx）、paused状态稳定后停止轮询（连续2次检测后停止）、用户操作后重启轮询（handleResumeExecution/onRetryStage/handleSkipStage处调用restartPolling） |

### 13. prior_rules_enhancement_plan.md

| 项目 | 内容 |
|------|------|
| **当前状态** | ✅ Phase 1 已完成 + 测试通过（2026-04-17，12/12 PASS） |
| **已实施内容** | PriorRuleParser 精简类（CSV 解析+校验+表达式生成）+ E2 类型断层修复（字符串→列表）+ E5 安全修复（ast.literal_eval）+ F3 路径注入修复（tempfile）+ /prior-rules/parse API + PriorRulesInput.tsx 前端组件（Tab 手动/文件 + 拖拽上传 + 模板下载 + 解析预览 + 校验状态）+ DynamicParamRenderer prior_rules_input 渲染器 + meta 参数定义更新 |
| **测试结果** | `tests/test_prior_rules.py` 12/12 通过：单元测试×5 + E2回归 + E5安全 + Pipeline集成（真实数据）+ 阈值对比 + 报告数据流检查 + 前端字段匹配 + API格式。**附带修复**: 先验规则全栈数据流断裂 FIX-A（Pipeline扁平化+字段补齐）+ FIX-B（Excel报告结构化），config_driven_report 批次5 已关闭 |
| **优先级** | P2 |

### 14. rule_mining_oot_validation_design.md

| 项目 | 内容 |
|------|------|
| **当前状态** | Phase 1-5 已完成，Phase 6（测试验证）待实施 |
| **已完成** | Phase 1 元数据 + Phase 2 数据划分 + Phase 3 OOT验证逻辑 + Phase 4 前端展示（稳定性Tab融合+规则表格OOT列+质量评分/110适配）+ Phase 5 AI Prompt（focusPoints+数据注入） |
| **待实施** | Phase 6 测试验证。报告导出缺失已登记至 report_config_driven_plan 批次6 |
| **预计剩余** | ~3小时 |

### 15. SOP_WebUI_detail_design.md — 第十章 Chat任务入口交互优化

| 项目 | 内容 |
|------|------|
| **当前状态** | ✅ 已完成（2026-04-16） |
| **已实施内容** | 新建 `sop/TaskConfirmCard.tsx` 轻量确认卡片（~230行），卡片三态（pending/confirmed/dismissed）+ API loading/error 处理；`dismissedTaskTypes` 会话级防重复机制 + 执行中跳过；`TaskConfigPanel` 新增 `initialParams` prop 支持 LLM 参数预填（含独立 useEffect 处理同 taskId 二次打开）；将 `isTaskParamJson` 解析函数抽离至 `lib/taskParamParser.ts`，**删除** `TaskParamCard.tsx`（~1372行），净减 ~1140 行代码 |
| **预计工作量** | ~1-2天 |

### 16. strategy_diagnosis_plan.md

| 项目 | 内容 |
|------|------|
| **当前状态** | 框架文档已创建（v0.1），待方案细化 + Plan Review |
| **待实施内容** | 策略诊断 SOP 任务：Swap Set 四象限分析、人数/金额双口径对比、业务/风险影响评估、换入/换出客群画像。从 P2-8 拆分深度对比分析能力，同时服务于规则挖掘和评分卡任务 |
| **优先级** | P2 |
| **预计工作量** | ~7-8天（分 3 个 Phase 实施） |

### 17. amount_analysis_test_plan.md

| 项目 | 内容 |
|------|------|
| **当前状态** | ✅ 单元/集成测试通过（2026-04-16）+ ✅ 人工 Pipeline 测试全部通过（2026-06-01） |
| **测试结果** | 单元测试 23/23 全通过；集成测试 Pipeline 核心通过；人工测试 AT-01~03 + COMBO-01 全通过 |
| **已修复** | FIX-1: Pipeline 输出扁平化；FIX-2: prop 名修复；FIX-3: DataFrame truthiness×6；FIX-4: Excel 金额章节重写；FIX-5: Markdown 金额章节重写；FIX-6: 类型校验。人工测试期间追加修复：金额汇总卡片 4→6 张（增量召回率/样本金额坏账率/金额累计提升度）、报告格式统一、AT-03/PR-03 未启用时面板不隐藏 Bug（enabled 字段检查）、各报告先验规则指标名称与前端对齐 |
| **优先级** | P2 |
| **预计工作量** | 测试 ~0.5天（✅） / 修复 ~2天（✅ 实际 ~0.5天） |

### 18. user_management_module_design.md — 用户管理与数据隔离（批次1、批次2均已完成）

| 项目 | 内容 |
|------|------|
| **当前状态** | ✅ **批次1、批次2均已开发完成并通过全部单元测试（2026-07-02）**，整个用户管理与数据隔离模块开发完毕 |
| **批次1完成内容** | 1. ✅ **workspace 基于用户名隔离**：`session_id`前端改为从`/auth/me`获取的登录用户名，后端27处路由强制从认证身份派生所有权<br>2. ✅ **任务历史按用户隔离**：`/sop/history`列表+13个记录端点强制按用户过滤<br>3. ✅ **数据迁移**：自助认领旧会话接口 + admin批量迁移脚本<br>4. ✅ **账户合并小工具**：`merge_user_data`服务 + `/admin/users/merge` API |
| **批次2完成内容** | 1. ✅ **TD3技术选型**：确定自建，不引入`fastapi-users`<br>2. ✅ **数据模型**：`users`表 + `UserService` + yaml一次性导入脚本<br>3. ✅ **账号管理API**：`/auth/mode`、`/auth/profile`、`/auth/change-password`、`/admin/users`全套CRUD、reset-password；`SimpleAuth`数据源动态切换（DB优先/yaml兜底，无需重启即可切换）<br>4. ✅ **前端**：`AccountSettingsDialog`（改密+个人信息+强制改密模式）、`UserManagerPage`+`/user-manager`独立页面（列表/新建/编辑/重置密码/合并账户/一次性密码展示/有效期临期高亮）、头像身份菜单（按角色差异化）<br>5. ✅ **文档同步**：`intranet_deployment_guide.md`§3.3、`user_manual.md`§3.1/§3.2 已改为以 Web UI 为主路径描述 |
| **回归测试** | 后端全量90项单测全通过（Phase1/5_6/9/10），无回归；前端因项目未配置JS测试框架，以人工代码审查+复用既有UI组件模式的方式验证（未执行实际浏览器运行验证，建议部署后人工走一遍关键路径） |
| **部署链路加固（2026-07-02补充）** | 上线后复核部署链路发现并修复三个串联问题：①`ENABLE_AUTH=true`零账户时旧代码fail-open（静默降级无鉴权）——新增首个账户零配置自动创建消除该状态；②Docker挂载单个不存在的`users.yaml`文件会被自动建成空目录，绕过①的修复——改为挂载整个`config/`目录；③`deploy_linux.sh`旧版无论是否选择编辑都会留下占位哈希yaml，被①误判为"已配置"从而永久锁死登录——改为交互二选一，不选手动配置就不创建该文件。详见`user_management_module_design.md`§二十 |
| **详细设计与实施记录** | 📋 统一详见 [`user_management_module_design.md`](./user_management_module_design.md)§九「批次1 Phase划分」+ §十七「批次2 Phase划分」+ §二十「部署链路加固」（含实施清单、已知未覆盖项） |
| **需求出处（历史文档引用，已归档为本条目）** | `docs/intranet_deployment_guide.md` §5/§6、`docs/online_multiuser_deployment_assessment.md` §五、`docs/project_development_review.md` §7.1 中原"workspace用户名隔离/用户自助改密码/任务历史按用户隔离/数据隔离"相关行，均已同步更新为完成状态并指向本条目 |

### 19. tests/ 目录测试基础设施历史债务（2026-07-02 排查发现）

> 背景：为验证用户管理模块批次1（第18项）无回归，尝试运行全量 `pytest tests/`，发现并修复了一个阻塞性 collection 崩溃 bug；顺带暴露出一批与本次改动无关、长期被掩盖的独立测试维护债务，现登记以便后续排期清理。

| 项目 | 内容 |
|------|------|
| **✅ 已修复（阻塞性 bug）** | `tests/test_oot_validation.py` L32-33 在**模块导入时**（非 `__main__` 保护块内）执行 `sys.stdout = io.TextIOWrapper(...)`，永久劫持 pytest 内部 capture 对象，导致 `pytest tests/`（整目录扫描）在 collection 阶段崩溃退出（`ValueError: I/O operation on closed file`），此前该 bug 使14个测试文件（含`test_sop_api.py`、`test_task_manager_complete.py`等）在整目录扫描时**静默消失、完全不被收集执行**，严重削弱回归测试的可信度。已将这两行移入 `if __name__ == "__main__":` 块内，修复后 `pytest tests/` 可正常收集全部 342 个测试用例 |
| **❌ 待排查修复（2个 collection error）** | `test_resume_expert_mode.py` 导入 `ExecutionStatus`（已从 `deepanalyze.core.task_manager.models` 移除/改名）；`test_resume_integration.py` 导入 `ExecutionStore`（已从 `deepanalyze.core.task_manager.persistent_store` 移除/改名）——均为历史重构后测试文件未同步更新 |
| **❌ 待排查修复（9个 setup error）** | `test_ai_suggest_retry.py::TestSuggestedParamsParsing`/`TestGetApiReturnsCleanText`/`TestPostApiStoresRawText` 试图从 `API.sop_api` 导入 `_parse_suggested_params`，但该函数已迁移至 `chat_api.py`（`sop_api.py` L2786 注释明确记录），测试未同步更新 import 路径 |
| **❌ 待排查修复（8个 setup error）** | `test_sop_api.py::TestSOPAPIEndpoints` 试图 `from API.main import app`，但 `API/main.py` 一直采用 `create_app()` 工厂函数模式，从未导出模块级 `app` 变量——测试文件本身过时 |
| **❌ 待排查修复（17个 failed）** | ①`test_task_manager_complete.py`：数据库共享状态污染（`UNIQUE constraint failed`、"应有且仅有1条历史记录"断言失败等）；②`test_rule_mining.py`/`test_resume_functionality.py`：GBK/UTF-8 编码不一致导致中文断言消息乱码比对失败；③`test_sop_api.py` 既有 bug（`ExecutionContext` 无 `update_stage` 属性、`KeyError: 'id'`、解包异常）；④`test_llm_pipeline_integration.py`：proxy URL 断言与当前实现不一致 |
| **范围判断** | 以上除已修复项外，均为**测试代码本身的维护债务**（非生产代码 bug），且与用户管理模块（批次1/2）改动无关；因分布散（6+文件）、成因各异，修复工作量不亚于独立一个小 Phase，故不纳入批次1/2 范围，登记后按需排期 |
| **优先级** | P3（不阻塞功能开发，但长期积累会持续削弱 `pytest tests/` 全量回归的可信度） |

### 20. CVM部署测试发现的已知限制/技术债（2026-07-03排查发现；限制①已于当日修复）

> 背景：本轮 CVM（TencentOS/RPM系）重新部署测试（Docker单用户/非Docker手动部署）期间，除已当场修复的代码/脚本 bug（`executor.py` PEP695语法兼容性、`deploy_manual.sh` 缺少 `DEV_MODE=false`、`deploy_manual.sh` Tailwind `--content`覆盖config导致CSS不完整）外，还发现2个不阻塞本次部署的已知限制，登记如下；限制①经用户确认后已于当日完成架构级修复。

| 项目 | 内容 |
|------|------|
| **限制①（✅ 2026-07-03已修复）：生产模式下 Basic Auth 退出登录无法真正切换账号** | **现象**：同源生产部署（`DEV_MODE=false`+`ENABLE_AUTH=true`）下，用户点"退出登录"后浏览器自动用**原生缓存**的 Basic Auth 凭证重新登录，无法切换账号；浏览器无痕窗口经实测也不可靠。**根因**：整页导航访问 `/`（及 `/llm-manager`）时若未认证，中间件保留 `WWW-Authenticate` 头触发浏览器原生弹窗，一旦登录成功浏览器会长期缓存该凭证，JS的 `clearAuth()` 清不掉这份浏览器原生缓存。**影响范围**：写在共享后端代码 `API/auth_middleware.py` 里，Docker多用户模式与非Docker手动多用户模式同等程度受影响（Docker单用户模式因 `ENABLE_AUTH=false` 不涉及）。<br>**✅ 修复方案（已实施并推送，commit `04b21ad`）**：把 `/`、`/llm-manager`、`/llm-manager/` 三个页面壳子路径纳入 `AUTH_WHITELIST_EXACT`，公开可加载（`demo/chat`是`output:'export'`纯静态导出+llm_manager_integrated的Vite构建产物，HTML/JS本身不含用户数据，公开无安全风险），鉴权完全交给页面加载后的 AJAX 探测（`/auth/me`）+ 自定义 `LoginDialog`/`shared/js/auth.js` 登录框处理——即让生产模式复用开发模式本就验证有效、从未出现此问题的鉴权路径；相应把 `/llm-manager` 页面级的 admin 角色前置检查从 `ADMIN_ONLY_EXACT` 移除（改为空列表占位），真正的权限边界完全下放到 `/llm-manager/api/manage/*` 等具体管理 API（`ADMIN_ONLY_PREFIXES`，仍强制403），与 `/user-manager` 等其它前端 admin 专属路由的权限模式保持一致。**验证结论：不会重新引入"首屏JS未加载完前怎么鉴权"的历史顾虑**——原前提"首页导航需要认证保护"被移除，首页壳子本身不含敏感数据，无需在JS加载前做任何身份判断。<br>**验证结果**：`tests/test_auth_middleware.py`等77项回归测试全通过（同步更新了2处断言：`/llm-manager/`不再是admin-only路由、改为验证已加入白名单）；CVM实测确认 `curl` 无认证访问 `/`（含`Accept: text/html`模拟真实浏览器导航）返回200且不带`WWW-Authenticate`头，`/llm-manager/`同样200，`/workspace/files`等真实数据API仍返回401，安全边界未受影响。 |
| **限制②（低优先级）：`deploy_manual.sh` 系统依赖检测硬编码 `dpkg`，RPM系发行版下完全失效** | **现象**：`deploy_manual.sh` 的系统依赖检测逻辑硬编码调用 `dpkg -s` 判断系统库是否已安装，但在 RPM 系发行版（如本次CVM实测的 TencentOS，用 yum/rpm 而非 dpkg）上该命令根本不存在，导致检测环节**静默失效**——不报错、不提示"检测不到"，直接跳过，可能使真实缺失的系统库延迟到后续编译/运行阶段才暴露，报错信息也不够精确。<br>**发现于**：2026-07-03 CVM非Docker手动部署测试（测试2）。<br>**影响范围**：仅限非Docker手动部署路径（`deploy_manual.sh`）且仅限目标机器是 RPM 系发行版（CentOS/RHEL/TencentOS/Fedora等）；Docker部署路径不受影响（依赖已固化在镜像内，构建时用的是 Debian 系基础镜像的包管理器，与此无关）。<br>**优先级**：低（未阻塞本次CVM测试实际部署成功；不修复的直接后果仅是"库缺失时报错时机后移、提示不够精确"，不影响能否部署成功）。<br>**建议修复方向**：改为先探测 `/etc/os-release` 判断发行版系，再分支调用 `dpkg -s`（Debian系）或 `rpm -q`（RPM系）；或统一改用更通用的探测方式（如直接用 `python -c "import xxx"` 探测Python库依赖，不依赖系统包管理器命令）。 |
| **登记来源** | `docs/cvm_deployment_test_plan.md` 本轮重新部署测试（Docker单用户模式 ✅ 通过、非Docker手动部署 ✅ 核心流程通过，测试期间发现并修复4个真实bug：executor.py PEP695语法/deploy_manual.sh缺DEV_MODE/deploy_manual.sh CSS构建/退出登录无法切账号，另登记限制②待排期） |

---

## 📝 说明

1. **已实现/已验证/已完成**（24个）：文档设计的功能已全部实现或已清理（过时/合并）
2. **部分实现**（4个）：已完成基础功能，但有明确的后续开发内容
3. **待实施/待开发**（13个）：尚未开始实现，或仅完成设计阶段
4. 本报告基于2026-04-15的代码库核实及最新文档状态同步结果更新
5. 2026-07-01 补充：新增部署类文档（`intranet_deployment_guide.md`）中登记的用户管理相关待实现任务（第18项）；2026-07-02 更新：第18项批次1已开发完成并通过测试，第18项标题及相关引用（6c/18a/后续迭代列表）已统一指向 `user_management_module_design.md`§九
6. 2026-07-02 补充：批次1回归测试期间排查发现并修复了 `pytest tests/` 整目录扫描崩溃的阻塞性 bug（`test_oot_validation.py` stdout劫持），顺带登记暴露出的一批独立测试维护债务（第19项，P3，与用户管理模块无关）
7. 2026-07-03 补充：CVM重新部署测试期间登记2项已知限制/技术债（第20项）：①生产模式Basic Auth退出登录无法切换账号——**已于当日修复**（`auth_middleware.py`白名单调整，commit `04b21ad`，77项回归测试通过+CVM实测验证）；②`deploy_manual.sh`依赖检测硬编码dpkg在RPM系发行版失效（低优先级，待排期）

---

*本报告用于指导项目下一步开发优先级规划*

---

## 🎯 下一步开发优先级建议

### 🔴 P0 - 立即实施（阻塞性功能或高价值低工作量）— ✅ 已完成

| 优先级 | 文档 | 建议理由 | 预计工作量 | 状态 |
|:------:|------|---------|-----------|:----:|
| **1** | `polling_optimization_design.md` | 体验优化，解决paused状态无效轮询问题 | ~0.5天 | ✅ 已完成 |
| **2** | `system_prompt_restructuring_design.md` | 架构改善，消除关键词嗅探隐患 | ~0.5天 | ✅ 已完成 |
| **3** | `model_evaluation_params_design.md` | 评分卡功能完整性，CSI指标 | 🟡 中优先级 | ✅ 已完成 |

### 🟡 P1 - 短期实施（1-2周内）

| 优先级 | 文档 | 建议理由 | 预计工作量 |
|:------:|------|---------|-----------|
| **4** | `feature_derivation_refactor_design.md` | ✅ 已完成（后端+前端+AI提示词+QA 通过） | 1-2天 |
| **5** | `rule_mining_oot_validation_design.md` | ✅ Phase 1-6 全部完成（后端+前端融合展示+AI Prompt+测试 8/8 通过）。Phase 6 修复：preprocess one-hot 编码未排除 exclude_cols 导致 sample_type 列被删除 | ~14h |
| **6** | ✅ `sensitive_field_detection` | **已完成 + 人工验证通过（2026-06-02）**：双层检测（L1列名+L2值扫描）+ 高危阻断上传+自动删除 + 中危警告 + SensitiveCheckDialog + 29个单元测试通过 | ~2天 |
| **6b** | ✅ `ai_suggest_retry_design.md` | **已完成（2026-06-02）**：StageSnapshot dataclass + FIFO快照 + SUGGESTED_PARAMS Prompt注入+解析 + SuggestedParamsCard.tsx + StageVersionSelector.tsx + 版本历史对比。B1~B6后端 + F1~F4前端 + T1 12单元测试全通过。待：HT-01~HT-05本机手工验证 | ~2天（实际~2天） |
| **6c** | ✅ `user_management_module_design.md` — **workspace 基于用户名隔离** | **已完成（2026-07-02）**：详见[`user_management_module_design.md`](./user_management_module_design.md)§九 | ~1天（实际~2天，含Phase3全部27处路由改造） |

### 🟢 P2 - 中期实施（1个月内）

| 优先级 | 文档 | 建议理由 | 预计工作量 |
|:------:|------|---------|-----------|
| **7** | ✅ `class_imbalance_handling_plan.md` | Phase 1 MVP 完成 + 测试通过（10/10）：none/auto/class_weight + 前端卡片 + AI Prompt 引导 | ~1天 |
| **8** | ✅ `prior_rules_enhancement_plan.md` | Phase 1 完成 + 单元测试通过（12/12）+ ✅ 人工 Pipeline 测试全部通过（2026-06-01，PR-01~03 + COMBO-01）：PriorRuleParser + CSV上传 + 三级校验 + E2/E5/F3 安全修复。人工测试期间追加修复：未启用时面板不隐藏 Bug、各报告先验规则汇总卡片/详情表列名与前端对齐 | ~1天 |
| **9** | ✅ **Chat任务入口交互优化** | 已完成：TaskConfirmCard 轻量卡片三态 + dismissedTaskTypes 防重复 + ConfigPanel initialParams 参数注入 | ~1-2天 |
| **10** | ✅ **删除历史记录级联清理 + 批量删除** | 已完成 + QA 通过（含 SOP + inference 两种类型验证）：级联清理 7 类资源 + 批量删除 API（POST）+ 前端多选/全选。QA 修复 3 项：路由顺序 Bug、Checkbox 对比度、pending 状态误跳过导致 inference 记录无法批量删除 | ~1天 |
| **11** | ✅ `amount_analysis_test_plan.md` | 测试 + Bug 修复完成：FIX-1 扁平化 + FIX-2 prop 修复 + FIX-3 DataFrame truthiness×6 + FIX-4 Excel 重写 + FIX-5 Markdown 重写 + FIX-6 类型校验 | ~0.5天+0.5天修复 |
| **12** | ✅ **账户有效期控制** | **已完成 + 本机单元测试25/25通过 + CVM集成测试6/6通过（2026-06-01）**：`valid_until` 字段 + 过期拒绝401 + 格式错误保守拒绝 + 部署文档v1.3更新 | ~1.5小时 |
| **12a** | ✅ `user_management_module_design.md` — **用户自助改密码** | **已完成（2026-07-02）**：`/auth/change-password` API + 前端「账户设置」弹窗，详见[`user_management_module_design.md`](./user_management_module_design.md)§十七 | ~1.5天（实际，含整个批次2 Phase10~11） |

> 详细方案见 [`taskSOP_solution/SOP_WebUI_detail_design.md` 第十章](./taskSOP_solution/SOP_WebUI_detail_design.md#十chat-任务入口交互优化方案待实施)

### 🔵 P3 - 长期/可选

| 优先级 | 文档 | 建议理由 | 预计工作量 |
|:------:|------|---------|-----------|
| **13** | `report_config_driven_plan.md` | 报告系统可扩展性，业务功能完善后再处理 | 2-2.5天 |
| **14** | `multimodal_chat_plan.md` | 多模态功能，非核心业务需求 | 1-2天 |
| **15** | `right_panel_unified_architecture_plan.md` | 架构优化，依赖Chat API融合完成后 | 中期优化 |
| **16** | `task_report_ai_analysis_design.md` | 仅剩端到端测试验证，可在其他功能完成后统一测试 | - |
| **17** | `release_readiness_plan.md` | Release发布流程，代码审计已完成，后续Phase按需推进 | 按Phase分阶段 |
| **18** | 📋 **导出报告新增指标同步** | 新增指标（CSI/OOT稳定性等）仅在前端/AI Prompt展示，导出报告缺失。Phase 1.7 作为统一登记处，按批次同步 | 按批次评估 |
| **18a** | ✅ `user_management_module_design.md` — **任务历史按用户隔离** | **已完成（2026-07-02）**：详见[`user_management_module_design.md`](./user_management_module_design.md)§九 | ~0.5天（实际） |

### 🟣 P4 - 远期/按需

| 优先级 | 文档 | 建议理由 | 预计工作量 |
|:------:|------|---------|-----------|
| **19** | `analysis_prompt_refactor_plan.md` | Prompt 工程优化 Phase 2，需根据新增 SOP 任务重新评估提示词框架方案 | Phase 2: ~2天 |
| **20** | `strategy_diagnosis_plan.md` | 策略诊断 SOP 任务：Swap Set + 人数/金额双口径 + 业务/风险影响评估（框架文档已创建，待细化） | ~7-8天 |
| **21** | 📋 `tests/` 目录测试基础设施历史债务（第19项） | 2个ImportError（历史重构遗留）+9个`_parse_suggested_params`路径过时+8个`test_sop_api.py::app`导入过时+17个既有断言/状态污染失败，均非生产bug | 待评估 |
| **22** | 📋 `deploy_manual.sh`依赖检测硬编码dpkg，RPM系发行版失效（第20项限制②） | 改为先探测`/etc/os-release`分支调用`dpkg -s`/`rpm -q`，或统一改用`python -c "import xxx"`探测 | ~0.5天 |

> 详细方案见 [`taskSOP_solution/task_management_module_design.md` Phase 25](./taskSOP_solution/task_management_module_design.md#phase-25删除历史记录级联清理已完成)
> 详细方案见 [`taskSOP_solution/report_config_driven_plan.md` Phase 1.7](./taskSOP_solution/report_config_driven_plan.md#phase-17导出报告补充新增稳定性指标待实施)

---

## 📋 推荐开发顺序

```
Week 1: ✅ 已完成（2026-04-15）
  ├─ [P0] polling_optimization_design (0.5天) ✅
  ├─ [P0] system_prompt_restructuring_design (0.5天) ✅
  └─ [P0] model_evaluation_params_design - CSI指标 ✅

Week 2: ✅ 已完成（2026-04-15）
  ├─ [P1] feature_derivation_refactor_design (1-2天) ✅
  └─ [P1] rule_mining_oot_validation_design (~2天) ✅

Week 3-4:
  ├─ [P2] class_imbalance_handling_plan
  └─ [P2] ✅ prior_rules_enhancement_plan（v1.2 已实施）

Week 5:
  ├─ [P2] ✅ Chat任务入口交互优化（轻量确认卡片 + 防重复机制，已完成）
  ├─ [P2] ✅ 删除历史记录级联清理 + 批量删除（已完成）
  ├─ [P2] ✅ 金额维度分析功能测试（FIX-1~6 修复 + 人工测试 AT-01~03 全通过，2026-06-01）
  └─ [P2] ✅ 先验规则功能人工测试（PR-01~03 + COMBO-01 全通过，2026-06-01）

Week 6（2026-06-02）:
  ├─ [P1] ✅ 敏感信息预检（个保法合规）：双层检测+高危阻断+自动删除文件+29单元测试通过+人工验证通过
  ├─ [P2] ✅ 账户有效期控制：valid_until字段+过期401+单元测试25/25+CVM集成测试6/6通过
  ├─ [UI] ✅ 三项UI优化：SOP面板调出隐藏Chat、规则挖掘默认参数调整、历史记录自动刷新
  ├─ [UI] ✅ 双重登录彻底修复：全局fetch拦截器+LoginDialog+白名单补充静态资源后缀
  ├─ [UI] ✅ workspace文件管理：全选文字按钮+行内Checkbox+批量删除(N)+单击选中/双击预览
  └─ [UI] ✅ workspace文件tooltip：右键操作提示悬浮窗

后续迭代:
  ├─ [P1] ✅ ai_suggest_retry_design（已完成：StageSnapshot+SUGGESTED_PARAMS+SuggestedParamsCard+StageVersionSelector+12单元测试，待HT-01~05本机手工验证）
  ├─ [P1] ✅ workspace 基于用户名隔离（已完成2026-07-02，详见 user_management_module_design.md§九）
  ├─ [P2] ✅ 用户自助改密码 /auth/change-password（已完成2026-07-02，属批次2账号管理Web UI，详见 user_management_module_design.md）
  ├─ [P3] ✅ 任务历史按用户隔离（已完成2026-07-02，详见 user_management_module_design.md§九）
  ├─ [P3] report_config_driven_plan Phase 2（业务功能完善后）
  ├─ [P3] 导出报告新增指标同步（Phase 1.7，按批次实施）
  ├─ [P3] multimodal_chat_plan
  ├─ [P3] right_panel_unified_architecture_plan
  ├─ [P3] release_readiness_plan Phase 2-5 (按需推进)
  ├─ [P3] 📋 tests/ 测试基础设施历史债务（第19项，2026-07-02新增登记，待排期）
  ├─ [P3] ✅ 生产模式Basic Auth退出登录无法切换账号（第20项限制①，2026-07-03登记并当日修复：/、/llm-manager纳入白名单）
  └─ [P4] 📋 deploy_manual.sh依赖检测硬编码dpkg（第20项限制②，2026-07-03新增登记，低优先级）

远期:
  ├─ [P4] analysis_prompt_refactor_plan Phase 2（需根据新增SOP任务重新评估提示词框架方案）
  └─ [P4] strategy_diagnosis_plan（策略诊断 SOP 任务，待实际需求驱动）
```

---

## 💡 关键决策建议

1. **P0 三项已全部完成** — 轮询优化、System Prompt 重构、CSI 指标（2026-04-15）
2. **feature_derivation_refactor_design** 建议优先 — 阶段职责清晰化，影响后续所有 SOP 任务
3. **rule_mining_oot_validation_design** 紧随其后 — 风控场景核心验证功能
4. **Chat任务入口交互优化** 放在 P2 末尾 — 需要前面的业务功能稳定后再优化交互入口
5. **report_config_driven** 降至 P3 — 优先完善业务功能，报告生成后续再处理
6. **analysis_prompt_refactor Phase 3** 建议暂缓 — 待评估实际收益后再决定

---

## 🐛 Bug 修复记录（2026-04-22 ~ 04-23）

### B-OOT-1: preprocess one-hot 编码未排除 exclude_cols（2026-04-22）
- **影响**: P1-5 OOT 验证测试 TC001/TC005/TC008 失败（sample_type 列被删除）
- **根因**: `DataPreprocessor.preprocess` Step 7 调用 `onehot_encode` 时未传入 `exclude_cols`，导致 `sample_type` 字符串列被 one-hot 编码后删除原始列
- **修复**: `rule_mining.py` preprocess 中将 `all_exclude_cols` 加入 `force_numeric`，防止排除列被 one-hot 编码
- **验证**: P1-5 OOT Phase 6 测试 8/8 全部通过

### B-CHAT-1: 任务执行中 TaskConfirmCard 渲染为 raw JSON（2026-04-23）
- **影响**: 有 SOP 任务执行中时，对话框输入触发任务识别后显示 "Code json" 而非确认卡片
- **根因**: 双重问题：①后端 extraction 模式走了 code execution 路径注入 `<Code>` 标签 prompt 与 JSON 输出指令冲突；②前端防重复确认机制 `isSOPExecuting && selectedTaskId === taskType` 时把纯 JSON 用 `renderMarkdownContent` 渲染
- **修复**: ①`chat_api.py` extraction 模式走 `_simple_chat_completion`；②前端将 raw JSON fallback 改为友好提示文本；③`<Code>` section 内增加 `isTaskParamJson` 防御性检测
- **文件**: `API/chat_api.py`, `demo/chat/components/three-panel-interface.tsx`

### B-RESUME-1: 重启后恢复任务点击「继续」无效（2026-04-23）
- **影响**: 后端重启后，恢复暂停状态的历史任务，点击「继续」按钮任务不推进
- **根因**: `get_execution_status` 轮询时自动将 context 从持久化存储恢复到 `ExecutionStore`（用于前端展示），导致 resume API 误判为"有活跃线程在等待信号"（`context.status == PAUSED`），走了发信号分支而非重新启动执行器分支。实际上重启后没有活跃 Pipeline 线程，信号无人接收
- **修复**: `sop_api.py` resume 逻辑增加 `_is_task_running(execution_id)` 活跃线程检查，无活跃线程时走"从持久化加载→重新启动执行器"分支
- **文件**: `API/sop_api.py`

### B-STATUS-1: 任务完成（100%）但历史列表显示"执行中"（2026-04-23）
- **影响**: 任务 Pipeline 正常跑完所有阶段，progress=100%，但历史记录列表显示「执行中」（转圈）
- **根因**: `execute_async` 中 `_run_task` 成功后 `_save_results` 可能抛异常（如结果序列化失败），导致数据库 status 字段未从 `running` 更新为 `completed`。内存 context 已是 COMPLETED（由 `_run_task` 第1064行设置），但数据库不一致
- **修复**: `executor.py` `execute_async` 的 `finally` 块中增加安全网——检测 context.status=COMPLETED 但数据库 status≠completed 时，补一次 `update_status` 调用
- **数据修复**: 已通过 SQL 将 `rec-9f1ac0959c35` 从 running 修正为 completed
- **文件**: `deepanalyze/analysis/task_SOP/executor.py`

### B-RETRY-1: 阶段重试后旧线程继续执行导致状态混乱（2026-04-24）
- **影响**: 专家模式下完成模型评估后暂停，回到数据加载调参重试，旧线程继续执行 report_generation 导致任务直接完成/WOE分箱卡住
- **根因**: 旧线程在 `_check_control` 的 `time.sleep(0.1)` 暂停轮询中等待，retry API 无法可靠终止同步线程。`asyncio.task.cancel()` 无法中断同步线程；STOP 信号产生的 `TaskStoppedException` 被 `_check_control` 外层的 `except Exception` 吞掉；新旧线程共享同一 execution_id 的控制信号，resume 信号同时唤醒两个线程
- **修复**（execution_version 机制）:
  - `ExecutionContext` 新增 `_execution_version` 字段，retry API 每次递增
  - `pipeline_progress_callback` 和 `check_stop_callback` 每次调用时检查版本号，不匹配则抛 `TaskStoppedException`
  - Pipeline 每个阶段的 progress 上报（0%/20%/.../100%）都会触发检查，旧线程在尝试开始下一阶段时自动退出
  - `_check_control` 中 `TaskStoppedException` 不再被 `except Exception` 吞掉（加了 `except TaskStoppedException: raise`）
  - retry 场景下 `_run_task` 跳过暂停恢复路径（检测 `retry_from_stage` 有值时直接进入 retry 逻辑）
  - 从首阶段重试时清空 `cached_state` 和 `start_from_stage`（完全从头执行）
- **文件**: `deepanalyze/analysis/task_SOP/executor.py`, `API/sop_api.py`

### B-RETRY-2: 最优选择阶段重试后报告生成崩溃（2026-04-24）
- **影响**: 规则挖掘任务在最优选择阶段重试后继续执行报告生成时，`UnboundLocalError: all_rules_with_status`
- **根因**: `all_rules_with_status` 在 `evaluating_rules` 阶段赋值，但重试 `selecting_rules` 时 `evaluating_rules` 被跳过（用缓存），变量未定义
- **修复**: `run` 方法开头初始化 `all_rules_with_status = None`；`selecting_rules` 使用前检查是否为 None，从 `results` 缓存恢复
- **文件**: `deepanalyze/analysis/task_SOP/rule_mining.py`

### B-MODEL-1: 迭代验证循环 const 死循环（2026-04-24）
- **影响**: `significance_mode='remove'` 时，迭代验证循环每轮尝试移除截距项 `const` 但无法匹配 `woe_feature_cols`，导致死循环跑满最大迭代次数
- **根因**: `model.summary()` 返回的 p 值列表包含截距项 `const`，未过滤即参与显著性检查
- **修复**: ①过滤 `const` 不参与显著性检查；②`summary()` 失败时加明确 warning；③默认迭代上限 10→20
- **验证**: 单元测试 4/4 通过 + 手动端到端测试通过
- **文件**: `deepanalyze/analysis/task_SOP/scorecard_development.py`

### B-STATS-1: class_weight='balanced' 导致似然比检验和伪R²计算异常（2026-04-24）
- **影响**: 使用 `imbalance_strategy=auto/class_weight` 时，模型训练阶段显示 pseudo_r²=-204%、似然比检验 p=1.0000，AI 分析给出"模型整体有效性存在严重问题"的错误结论
- **根因**: `statistical_model.py` 的 `_calculate_statistics` 和 `_calculate_model_fit_stats` 使用无加权的标准对数似然公式，但 `predict_proba` 来自 `class_weight='balanced'` 训练的模型。加权模型的预测概率偏向少数类，在未加权评估下比 null model 还差
- **修复**（方案A：加权似然公式）:
  - 新增 `_compute_effective_weights()` 方法，用 `sklearn.utils.class_weight.compute_sample_weight` 合并 `class_weight` + `sample_weight`
  - `_calculate_statistics()` 使用加权 Hessian：`H = X^T * diag(w·p·(1-p)) * X`
  - `_calculate_model_fit_stats()` 使用加权似然：`sum(w_i·[y_i·log(p_i) + (1-y_i)·log(1-p_i)])`，加权 `null_proba = sum(w·y)/sum(w)`
  - `summary()` 新增 `class_weight_applied` 布尔标记
  - `scorecard_development.py` output_preview 的 `model_fit` 字典新增 `class_weight_applied` 字段
- **验证**: 修复后 pseudo_r²=0.9038、lr_pvalue=0.0；单元测试 8/8 通过（含极端 1% 不平衡场景）
- **文件**: `deepanalyze/analysis/statistical_model.py`, `deepanalyze/analysis/task_SOP/scorecard_development.py`

### B-LOGIN-1: 双重登录弹窗（2026-06-02）
- **影响**: 首次访问时出现两次登录弹窗——一次是前端 `window.prompt`（串行两次：用户名+密码），一次是浏览器原生 Basic Auth 弹窗
- **根因1**: `<img src="/placeholder-logo.png">` 和 `<img src="/placeholder-user.jpg">` 图片资源不存在，后端返回 401+WWW-Authenticate，浏览器对图片 401 触发原生弹窗。图片加载不走 `fetch()`，全局 fetch 拦截器无效
- **根因2**: 大量组件使用裸 `fetch()` 而非 `authFetch()`，后端 401 触发浏览器弹窗
- **修复**:
  - 后端白名单补充静态资源文件后缀（`.png/.jpg/.svg/.woff` 等），图片资源不触发认证
  - 删除两个不存在的 `<AvatarImage src>` 引用，直接用 `AvatarFallback`
  - 全局 `window.fetch` 拦截器，所有裸 fetch 自动注入 Authorization 头
  - `LoginDialog.tsx` 替代两次串行 `window.prompt`，用户名+密码同时展示
  - 修复 `TaskHistoryList.tsx` 路径 bug：`/api/sop/history` → `/sop/history`
- **文件**: `API/auth_middleware.py`, `demo/chat/components/three-panel-interface.tsx`, `demo/chat/components/LoginDialog.tsx`, `demo/chat/lib/config.ts`, `demo/chat/components/sop/TaskHistoryList.tsx`

### B-SENSITIVE-1: 高危文件上传后弹窗但文件仍保留（2026-06-02）
- **影响**: 高危敏感文件触发阻断弹窗，用户点"重新选择文件"后文件仍然存在于 workspace
- **根因**: 检测逻辑是"先上传再检测"，`onReselect` 回调只关闭弹窗，没有删除已上传的文件
- **修复**: 新增 `sensitiveFilePath` state 记录已上传路径，`onReselect` 时调用 `deleteFile(sensitiveFilePath)` 回滚删除，并重新打开文件选择框
- **文件**: `demo/chat/components/three-panel-interface.tsx`

### B-TEST-1: `pytest tests/` 整目录扫描崩溃，14个测试文件被静默丢弃（2026-07-02）
- **影响**: 执行全量 `pytest tests/` 时仅收集到144个测试用例就以 `ValueError: I/O operation on closed file` 崩溃退出，`test_sop_api.py`、`test_task_manager_complete.py`、`test_user_management_phase1/5_6.py` 等14个测试文件完全不被收集/执行，且无任何错误提示——严重削弱全量回归测试的可信度（发现于用户管理模块批次1回归测试期间）
- **根因**: `tests/test_oot_validation.py` L32-33 在**模块导入时**（而非 `if __name__ == "__main__":` 保护块内）执行 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)`（原意是修复独立脚本运行时的 Windows GBK 编码问题）。但 pytest 收集测试时会**导入**该模块，此时 `sys.stdout` 已被 pytest 的 capture 机制接管，这行代码会把 pytest 内部的 capture 对象**永久替换**掉，导致 session 结束时 pytest 尝试恢复原始 stdout 时崩溃，且此后所有输出/收集均受影响
- **修复**: 将该 stdout/stderr 重绑定逻辑移入 `if __name__ == "__main__":` 块内，不影响其独立脚本运行时的原有编码修复效果，仅消除对 pytest 导入阶段的副作用
- **验证**: 修复后 `pytest tests/ --collect-only` 可正常收集全部 342 个测试用例（此前仅144个即崩溃）
- **文件**: `tests/test_oot_validation.py`
- **遗留**: 修复该崩溃 bug 后暴露出一批与本次改动无关的独立测试维护债务（2个ImportError + 9个`_parse_suggested_params`路径过时 + 8个`test_sop_api.py::app`导入过时 + 17个既有断言/状态污染失败），已登记至本文档「📋 待实施/待开发」第19项，按需排期清理




