# AI分析评估System Prompt重构计划

> 本文档记录将`StageOutputPreview.tsx`中的AI分析评估system prompt抽离为独立模块的分析结论和实施方案。

---

## 实施状态

| Phase | 状态 | 完成时间 | 说明 |
|-------|------|----------|------|
| **Phase 0** | ✅ 已完成 | 2026-01-22 | 前端Prompt统一 |
| **Phase 1** | ✅ 已完成 | 2026-01-22 | 后端抽离（`API/AI_analysis_prompts.py`） |
| **Phase 1.5** | ✅ 已完成 | 2026-02-03 | 前端冗余代码清理（约860行） |
| **Phase 2** | 📋 待实施 | - | 深度变体支持（可选） |
| **Phase 3** | 📋 待实施 | - | LLM Manager集成（可选） |

**Phase 1 实现文件**：
- `API/AI_analysis_prompts.py` - Prompt 构建模块（新建，约1900行）
- `API/chat_api.py` - `/v1/chat/analysis/prompt` API 端点

**Phase 1.5 清理内容**：
- `StageOutputPreview.tsx` - 清理冗余代码（备份文件：`StageOutputPreview.tsx.backup`，4576行）

---

## 1. 背景与问题

### 1.1 现状

当前AI任务结果分析评估的system prompt硬编码在`StageOutputPreview.tsx`组件中（约550行），包含两类prompt：
- **阶段分析Prompt** (`buildStageAnalysisPrompt`)：各阶段独立评估
- **整体分析Prompt** (`buildOverallAnalysisPrompt`)：报告生成阶段的整体评估（专家模式）

存在以下问题：

| 问题 | 影响 |
|------|------|
| **职责混杂** | UI组件承担prompt定义职责，违反单一职责原则 |
| **维护困难** | 修改prompt需要在前端组件中查找，不直观 |
| **复用受限** | 其他场景需要类似分析时无法复用 |
| **扩展性差** | 难以支持不同分析深度或任务类型的定制 |

### 1.2 当前阶段配置清单（2026-01-22更新）

#### 1.2.1 角色配置 (`stageRoleConfig`)

**评分卡建模任务阶段**：

| 阶段ID | 角色 | 专长领域 | 关注维度 |
|--------|------|----------|----------|
| `data_loading` | 资深数据工程师 | 数据质量评估与ETL流程优化 | 数据完整性（缺失率可接受范围）、样本量充足、正负样本比例（坏账率）、排除变量合理性 |
| `preprocessing` | 数据质量分析师 | 数据清洗与异常检测 | 异常值处理必要性、数据集划分比例、特征数量适中 |
| `woe_binning` | 风控建模专家 | WOE编码与信息价值分析 | IV值分布（0.02-0.5有效区间）、高IV特征业务可解释性、过拟合风险（IV过高）、分箱单调性 |
| `feature_selection` | 特征工程专家 | 特征筛选与降维策略 | 筛选比例合理性、保留特征代表性、信息损失风险 |
| `model_training` | 机器学习工程师 | 模型训练与调优 | 训练/测试集性能差异（过拟合检测）、AUC>0.7/KS>0.2达标、模型复杂度与泛化平衡 |
| `model_evaluation` | 模型验证专家 | 模型性能评估与稳定性分析 | 区分度（KS、AUC）业务要求、PSI<0.1稳定性、Lift业务价值 |
| `score_scaling` | 评分卡设计专家 | 信用评分刻度设计 | 基准分合理性、PDO符合业务需求、分数分布可解释性 |
| `report_generation` | 风控分析师 | 建模报告撰写与结果解读 | 报告完整性、关键结论准确性 |

**规则挖掘任务阶段**：

| 阶段ID | 角色 | 专长领域 | 关注维度 |
|--------|------|----------|----------|
| `preprocessing`（动态） | 规则策略数据分析师 | 风控规则挖掘数据预处理 | 数据完整性、坏账率水平（3%-15%理想）、异常值情况（仅检测不处理）、训练集/测试集划分（**无OOT概念**）、特征数量适中 |
| `feature_engineering` | 规则挖掘特征工程专家 | 分类变量编码与特征筛选 | One-Hot编码理解（特征数先膨胀再收缩）、IV分布理解（筛选前统计）、IV筛选效果、最终特征数量（20-50个）、强IV占比（>30%）、**禁止建议调整IV阈值对比稳定性** |
| `generating_rules` | 规则策略专家 | 风控规则挖掘与策略设计 | 生成规则数量（过少调整叶节点比例）、挖掘模式适用性、决策树深度与变量组合配置、**本阶段无需关注冗余度和覆盖率** |
| `rule_filtering` | 规则筛选专家 | 规则质量评估与筛选 | 单调性校验效果（移除逆向规则）、Lift/命中率阈值合理性、有效规则保留率（5-20条为宜）、**本阶段仅评估筛选效果不评估生成参数** |
| `selecting_rules` | 规则优化专家 | 最优规则集选择与组合 | 最优规则集覆盖率、规则互补性、风险目标达成（召回率、精准度、提升度）、整体策略效果 |
| `rule_mining` | 规则策略专家 | 风控规则挖掘与策略设计 | 规则覆盖率与精准率平衡、业务可解释性、规则冲突与冗余 |
| `evaluating_rules`（兼容） | 规则验证专家 | 规则效果评估与优化 | 测试集表现、规则稳定性、误杀率与漏杀率权衡 |
| `filtering_rules`（兼容） | 规则筛选专家 | 规则质量评估与筛选 | 同rule_filtering |

#### 1.2.2 数据描述模板 (`buildStageAnalysisPrompt` switch cases)

| 阶段ID | 数据字段 |
|--------|----------|
| `data_loading`/`preprocessing` | rows, feature_count, missing_rate, target_rate, split_info, auto_exclude_report, derived_features, outlier_count |
| `woe_binning` | total_features, iv_range, iv_table (Top 5) |
| `feature_selection`/`feature_engineering` | before_count, after_count, selected_features, selection_method, iv_distribution, iv_threshold, onehot_stats, warning |
| `model_training` | coefficients (Top 5), intercept, train_auc/ks, test_auc/ks |
| `model_evaluation` | train_metrics, test_metrics, gini, lift, psi, overfit_warning |
| `score_scaling` | base_score, base_odds, pdo, num_variables, score_range, scorecard_preview |
| `generating_rules` | total_rules, mining_mode, use_full_tree, n_vars, max_depth, min_samples_leaf, tree_count |
| `rule_filtering`/`filtering_rules` | generated_count, direction_filtered_count, after_count, filter_criteria, filter_summary (direction_removed, lift_removed, hit_rate_removed) |
| `evaluating_rules` | before_count, after_count, filter_criteria, evaluation_stats |
| `selecting_rules` | candidate_count, selected_count/optimal_rules.length, total_coverage, avg_lift, selection_mode, selection_method |
| `rule_mining` | rule_count, coverage, precision, recall, rules (Top 3) |
| `report_generation` | status, report_sections, datasets, chart_types, has_chart_data, quality_score, quality_level, validation_passed, validation_issues, psi_summary, final_rules_count, total_rules_evaluated, has_tree_structure, scorecard_validation, score_statistics, n_features |

#### 1.2.3 整体分析Prompt (`buildOverallAnalysisPrompt`) - Phase 21新增

专家模式下，报告生成阶段使用整体分析Prompt，整合7类数据：

**评分卡开发任务**：
| 数据类别 | 关键指标 |
|---------|---------|
| 样本概况 | total_rows, bad_rate, feature_count |
| 特征筛选 | original_count, final_count |
| 模型性能 | train_auc/ks, test_auc/ks, oot_auc/ks（如有） |
| 评分刻度 | base_score, pdo, score_range |
| 稳定性 | psi值判断（<0.1稳定/0.1-0.25轻微偏移/>0.25不稳定） |
| 评分卡预览 | Top 5变量及分箱 |

**规则挖掘任务**：
| 数据类别 | 关键指标 |
|---------|---------|
| 样本及特征概况 | total_rows, bad_rate, feature_count（从stages.preprocessing获取） |
| 规则挖掘结果 | candidate_count, selected_count, avg_lift, avg_bad_rate |
| 累计效果 | cum_recall, cum_hit_rate, cum_bad_rate, cum_lift |
| **规则筛选过程** | rejected_count, 主要淘汰原因分布（按数量降序Top5） |
| **质量验证** | quality_score, **avg_overlap**（重叠度）, validation_issues |
| **稳定性分析** | stable_count, unstable_count, avg_psi |
| Top规则示例 | Top 3规则及指标 |

**重点关注维度**（规则挖掘）：
1. 规则质量（提升度≥2，坏账率显著高于总体）
2. 累计效果（召回率与命中率平衡）
3. **筛选策略（淘汰原因分布是否合理）**
4. **规则重叠度（0说明规则互斥，较高需关注效率损耗）**
5. 稳定性（PSI可接受范围）
6. 规则数量（6条以内较理想）

### 1.3 参考先例

项目中已有成功的prompt分离案例：
- `deepanalyze/analysis/task_SOP/llm_param_extractor.py` 中的 `EXTRACTION_SYSTEM_PROMPT`
- 该常量独立定义，与执行逻辑分离，便于维护和测试

---

## 2. 重构目标

1. **职责分离**：将prompt定义从UI组件中抽离
2. **可维护性**：集中管理所有分析相关prompt
3. **可扩展性**：支持不同分析深度和任务类型
4. **一致性**：与现有`EXTRACTION_SYSTEM_PROMPT`架构保持一致

---

## 3. 实施方案

### 3.1 目标架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    重构后架构                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  API/analysis_prompts.py (新建)                                     │
│  ├── ANALYSIS_SYSTEM_PROMPT          # 基础分析prompt               │
│  ├── ANALYSIS_PROMPT_VARIANTS        # 不同深度变体                  │
│  │   ├── quick                       # 快速分析                     │
│  │   ├── standard                    # 标准分析（默认）              │
│  │   ├── deep                        # 深度分析                     │
│  │   └── expert                      # 专家模式                     │
│  └── get_analysis_prompt()           # 获取prompt的工厂函数          │
│                                                                     │
│  API/chat_api.py                                                    │
│  └── /analyze-output endpoint        # 调用analysis_prompts         │
│                                                                     │
│  StageOutputPreview.tsx                                             │
│  └── 仅保留UI逻辑，调用后端API                                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 分阶段实施

#### Phase 1: 基础抽离（推荐优先实施）

**目标**：将prompt移至独立Python模块

**新建文件**：`API/analysis_prompts.py`

```python
"""
AI分析评估System Prompt定义

与llm_param_extractor.py中的EXTRACTION_SYSTEM_PROMPT保持一致的架构风格。
"""

# 基础分析System Prompt
ANALYSIS_SYSTEM_PROMPT = """
You are an expert AI analyst specializing in evaluating task execution results.

## Your Role
Analyze the output of automated data analysis tasks and provide:
1. Quality assessment of the results
2. Key findings and insights
3. Potential issues or anomalies
4. Recommendations for next steps

## Analysis Guidelines
...（从StageOutputPreview.tsx迁移的完整prompt内容）
"""

def get_analysis_prompt(
    task_type: str = "general",
    analysis_depth: str = "standard"
) -> str:
    """获取分析prompt
    
    Args:
        task_type: 任务类型 (rule_mining, scorecard, feature_engineering等)
        analysis_depth: 分析深度 (quick, standard, deep, expert)
    
    Returns:
        完整的system prompt字符串
    """
    return ANALYSIS_SYSTEM_PROMPT
```

**修改文件**：`StageOutputPreview.tsx`
- 移除硬编码的prompt定义
- 调用后端API获取分析结果（prompt由后端注入）

**工作量估算**：约2-4小时

---

#### Phase 2: 深度变体支持（可选扩展）

**目标**：支持不同分析深度

```python
ANALYSIS_PROMPT_VARIANTS = {
    "quick": """
    Provide a brief summary of the results:
    - Overall status (success/warning/error)
    - Top 3 key findings
    - One-line recommendation
    """,
    
    "standard": ANALYSIS_SYSTEM_PROMPT,  # 默认
    
    "deep": """
    {ANALYSIS_SYSTEM_PROMPT}
    
    ## Additional Deep Analysis
    - Statistical significance assessment
    - Cross-validation with historical data
    - Sensitivity analysis considerations
    """,
    
    "expert": """
    {ANALYSIS_SYSTEM_PROMPT}
    
    ## Expert Mode Extensions
    - Methodology critique
    - Alternative approach suggestions
    - Academic reference recommendations
    """
}

def get_analysis_prompt(
    task_type: str = "general",
    analysis_depth: str = "standard"
) -> str:
    """获取指定深度的分析prompt"""
    base_prompt = ANALYSIS_PROMPT_VARIANTS.get(analysis_depth, ANALYSIS_SYSTEM_PROMPT)
    
    # 任务类型特化（可选）
    task_specific_additions = TASK_SPECIFIC_PROMPTS.get(task_type, "")
    
    return base_prompt + task_specific_additions
```

**工作量估算**：约1-2小时（基于Phase 1）

---

#### Phase 3: LLM Manager集成（可选）

**目标**：通过LLM Manager配置分析prompt

**实现方式**：
- 在LLM Manager的preset配置中添加"Result Analysis"预设
- 后端API检测preset类型，自动应用对应prompt

**工作量估算**：约4-6小时

---

## 4. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `API/analysis_prompts.py` | 新建 | Prompt定义和工厂函数 |
| `API/chat_api.py` | 修改 | 添加/修改分析endpoint |
| `demo/chat/components/sop/StageOutputPreview.tsx` | 修改 | 移除prompt定义，调用API |
| `docs/system_prompt_guide.md` | 更新 | 添加分析prompt章节 |

---

## 5. 验收标准

### Phase 1 验收
- [ ] `analysis_prompts.py`文件创建完成
- [ ] prompt内容完整迁移，无遗漏
- [ ] `StageOutputPreview.tsx`中无prompt硬编码
- [ ] AI分析功能正常工作，输出质量不变
- [ ] 单元测试覆盖prompt获取函数

### Phase 2 验收（如实施）
- [ ] 支持4种分析深度选择
- [ ] 前端UI支持深度切换
- [ ] 不同深度输出符合预期

---

## 6. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Prompt迁移遗漏 | 低 | 中 | 逐行对比，保留原文件备份 |
| API调用增加延迟 | 低 | 低 | Prompt可缓存，影响可忽略 |
| 前后端接口不匹配 | 中 | 中 | 定义清晰的接口契约 |

---

## 7. 时间规划

| 阶段 | 预计耗时 | 优先级 |
|------|----------|--------|
| Phase 1: 基础抽离 | 4-6小时 | **高** |
| Phase 2: 深度变体 | 2-3小时 | 中 |
| Phase 3: LLM Manager集成 | 4-6小时 | 低 |

**建议**：先完成Phase 1，观察效果后再决定是否推进后续阶段。

---

## 8. 版本信息

- **文档版本**: 1.8
- **创建日期**: 2025-12-26
- **最后更新**: 2026-02-06
- **状态**: ✅ Phase 0/1/1.5 已完成并验收 | ⏸️ Phase 2 暂不实施 | 📋 Phase 3 按需实施
- **关联文档**:
  - `docs/system_prompt_guide.md` - System Prompt配置指南
  - `deepanalyze/analysis/task_SOP/llm_param_extractor.py` - 参考实现
  - `docs/taskSOP_solution/task_report_ai_analysis_design.md` - AI分析设计文档

---

## 9. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2025-12-26 | 初始版本 |
| 1.1 | 2025-12-26 | 新增规则挖掘任务阶段配置清单（generating_rules, filtering_rules, evaluating_rules, selecting_rules）；更新代码行数估算（约260行→约350行）|
| 1.2 | 2026-01-12 | 更新规则挖掘阶段：合并 filtering_rules + evaluating_rules 为 rule_filtering（7阶段→6阶段）|
| 1.3 | 2026-01-12 | 同步角色配置与实际代码一致；新增规则挖掘任务preprocessing阶段的动态角色配置（无OOT验证集概念）|
| 1.4 | 2026-01-22 | **全面更新**：(1) 代码行数更新为约550行；(2) 新增`buildOverallAnalysisPrompt`整体分析Prompt说明（Phase 21）；(3) 更新角色配置详情（feature_engineering改为规则挖掘专用、generating_rules/rule_filtering增加禁止建议说明）；(4) 完善数据描述模板字段清单（新增derived_features、onehot_stats、filter_summary等）；(5) 详细说明规则挖掘整体分析的7类数据整合（含筛选过程、质量验证avg_overlap、稳定性PSI）；(6) 更新工作量估算 |
| 1.5 | 2026-01-22 | **前端统一方案已实施**：(1) 将`buildOverallAnalysisPrompt`从组件内useCallback提取为独立export函数；(2) `three-panel-interface.tsx`中自动模式的`buildAnalysisPrompt`（简化版）已删除，改为调用统一的`buildOverallAnalysisPrompt`；(3) 自动模式和专家模式现使用完全相同的AI整体分析prompt；(4) 此为Phase 1后端抽离的前置步骤，当前prompt仍在前端`StageOutputPreview.tsx`中 |
| 1.6 | 2026-02-03 | **Phase 1.5 前端清理完成**：(1) 删除`StageOutputPreview.tsx`中约860行冗余代码（`buildOverallAnalysisPrompt`导出函数、`stageNameMap`、`stageRoleConfig`、`buildStageAnalysisPrompt`）；(2) 修改`sop/index.ts`移除导出；(3) AI分析功能已完全迁移至后端`/v1/chat/analysis/prompt` API |
| 1.7 | 2026-02-06 | **验收确认**：(1) 更新`AI_analysis_prompts.py`实际行数（约700行→约1900行）；(2) 更新代码统计数据（含后续迭代新增代码说明）；(3) 新增第11章验收确认表格 |
| 1.8 | 2026-02-06 | **Phase 2 评估**：深度变体支持（quick/standard/deep/expert）评估为暂不实施，原因：当前阶段级别差异化 prompt 已满足需求，无明确用户痛点 |

---

## 10. 当前实施状态

### 10.1 已完成：前端 Prompt 统一（Phase 0）

**日期**：2026-01-22

**变更内容**：
- `StageOutputPreview.tsx`：将 `buildOverallAnalysisPrompt` 从组件内 `useCallback` 提取为模块级 `export function`
- `sop/index.ts`：新增 `buildOverallAnalysisPrompt` 导出
- `three-panel-interface.tsx`：
  - 导入并使用 `buildOverallAnalysisPrompt`
  - 删除旧的 `buildAnalysisPrompt` 函数（约65行简化版）
  - 自动模式 AI 分析不再需要额外 system prompt（新函数已包含完整角色设定）

**效果**：
- ✅ 自动模式和专家模式使用完全相同的 `buildOverallAnalysisPrompt`
- ✅ prompt 定义集中在一处，便于维护

### 10.2 已完成：后端抽离（Phase 1）

**日期**：2026-01-22

**新建文件**：`API/AI_analysis_prompts.py`（约1900行）

**实现内容**：
- `STAGE_NAME_MAP` - 阶段名称映射
- `STAGE_ROLE_CONFIG` - 阶段角色配置（评分卡/规则挖掘）
- `build_stage_analysis_prompt()` - 构建阶段分析提示词
- `build_overall_analysis_prompt()` - 构建整体分析提示词
- `_build_*_description()` - 各阶段数据描述构建函数（14个）

**API端点**：`/v1/chat/analysis/prompt`
- 请求参数：`task_type`, `stage_id`, `stage_name`, `output_preview`, `task_result`
- 返回：`{ "prompt": "..." }`

### 10.3 已完成：前端冗余代码清理（Phase 1.5）

**日期**：2026-02-03

**清理内容**：
- 删除导出函数 `buildOverallAnalysisPrompt`（约345行）
- 删除组件内部的 `stageNameMap` 对象（约18行）
- 删除组件内部的 `stageRoleConfig` 对象（约145行）
- 删除 `buildOverallAnalysisPromptCallback`（约4行）
- 删除 `buildStageAnalysisPrompt` 函数（约340行）
- 修复 `performAIAnalysis` 的依赖数组，移除已删除的函数引用

**代码变化统计**：
| 指标 | 数值 | 说明 |
|------|------|------|
| 备份文件行数 | 4576 | 清理前的完整备份 |
| 清理时文件行数 | 3716 | Phase 1.5 完成时 |
| 当前文件行数 | 4634 | 后续功能迭代新增代码 |

**备份文件**：`StageOutputPreview.tsx.backup`

**修改文件**：
- `StageOutputPreview.tsx` - 移除冗余代码，保留注释说明迁移情况
- `sop/index.ts` - 移除 `buildOverallAnalysisPrompt` 导出，添加迁移注释

**验证结果**：
- ✅ 无 linter 错误
- ✅ AI分析功能继续通过后端 `/v1/chat/analysis/prompt` API 获取prompt

### 10.4 Phase 2/3 评估结论

| Phase | 原计划 | 评估结论 | 决策 |
|-------|--------|----------|------|
| Phase 2 | 深度变体支持（quick/standard/deep/expert） | 当前阶段级别的差异化 prompt 已满足需求，无明确用户痛点 | ⏸️ 暂不实施 |
| Phase 3 | LLM Manager集成 | 待评估实际需求 | 📋 按需实施 |

**Phase 2 不实施的原因**：
1. 当前方案已足够：阶段级别的差异化 prompt 已实现"按需分析"效果
2. 投入产出比低：需维护多套 prompt 模板，但使用频率可能很低
3. 用户认知负担：需要用户理解并选择分析深度
4. 无明确痛点：未收到"分析太详细/太简略"的用户反馈

---

## 11. 验收确认（2026-02-06）

| 验收项 | 状态 | 说明 |
|--------|------|------|
| `AI_analysis_prompts.py` 文件创建 | ✅ | 1888行，包含完整实现 |
| prompt内容完整迁移 | ✅ | 包含所有阶段的角色配置和数据描述构建函数 |
| `StageOutputPreview.tsx` 无prompt硬编码 | ✅ | 仅保留迁移说明注释 |
| AI分析功能正常工作 | ✅ | 前端通过 `/v1/chat/analysis/prompt` API 调用 |
| 备份文件存在 | ✅ | `StageOutputPreview.tsx.backup` (4576行) |
