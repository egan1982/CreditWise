# 策略诊断 SOP 任务设计方案

> **文档版本**: v0.1（框架）  
> **创建日期**: 2026-04-16  
> **状态**: 方案设计中  
> **优先级**: P2-P3（待评估）  
> **开发评审**: 📋 待 plan review  
> **前置条件**: 无硬性前置依赖，可独立于其他 P2 任务开发

---

## 一、需求背景

### 1.1 行业定位

策略诊断（Strategy Diagnosis / Strategy Backtesting）在风控行业中是**独立于策略开发**的分析活动：

| 参考来源 | 核心观点 |
|---------|---------|
| 冯占鹏、姚志勇《Python金融风控策略实践》§4.3 | **Swap Set 分析**是新旧策略更替的独立评估方法，流程位于策略开发之后、上线决策之前 |
| FICO《A Guide to Champion/Challenger Testing》 | Champion-Challenger 是**独立测试框架**，需独立的数据分流和指标体系 |
| 风控行业实践共识 | 换入换出分析的两个核心维度：**人数口径 + 金额口径**；策略调整需同时评估对业务和风险两个层面的影响 |

### 1.2 与现有任务的关系

```
┌────────────────────┐     ┌────────────────────┐
│   规则挖掘任务       │     │   评分卡开发任务     │
│   (已有 SOP)        │     │   (已有 SOP)        │
│                    │     │                    │
│   输出: 最优规则集   │     │   输出: 评分卡表     │
└────────┬───────────┘     └────────┬───────────┘
         │ 新策略/新模型              │ 新策略/新模型
         └───────────┐  ┌───────────┘
                     ▼  ▼
         ┌─────────────────────────┐
         │   ★ 策略诊断任务（新建）   │
         │                         │
         │   输入:                  │
         │   ├─ 旧策略（CSV/手动）   │
         │   ├─ 新策略（任务结果导入）│
         │   ├─ 数据集（含目标变量） │
         │   └─ 金额列（可选，多列） │
         │                         │
         │   输出:                  │
         │   ├─ Swap Set 四象限分析  │
         │   ├─ 人数/金额双口径对比  │
         │   ├─ 业务+风险影响评估    │
         │   ├─ 换入/换出客群画像    │
         │   └─ 诊断报告 + AI 分析   │
         └─────────────────────────┘
```

### 1.3 当前项目空白

| 维度 | 规则挖掘现有能力 | 策略诊断需要但缺失 |
|------|:---------------:|:-----------------:|
| 先验规则导入 | ✅ textarea 手动输入 | CSV 批量导入（P2-8 补充） |
| 金额维度分析 | ✅ `AmountAnalyzer`（单金额列、规则效果视角） | 多金额列（授信/放款/损失）、策略对比视角 |
| Swap Set 分析 | ❌ | ✅ 四象限（all_in / swap_in / swap_out / all_out） |
| 人数口径指标 | ✅ 命中率/坏账率/Lift | ✅ + 通过率变化、换入换出人数对比 |
| 金额口径指标 | ✅ 命中金额/金额坏账率/金额Lift | ✅ + 通过金额变化、损失金额变化 |
| 业务影响评估 | ❌ | ✅ 通过率→放款量→收入预估 |
| 风险影响评估 | ❌ | ✅ 坏账率→损失额→资产质量预估 |
| 换入/换出客群画像 | ❌ | ✅ 特征分布对比 |
| AI 分析 | ❌ 金额维度未纳入 Prompt | ✅ 策略诊断专属分析 Prompt |
| 服务对象 | 仅规则挖掘 | 规则挖掘 + 评分卡 + 未来 ML 模型 |

---

## 二、核心概念

### 2.1 Swap Set 四象限

```
                    新策略通过           新策略拒绝
                 ┌─────────────────┬─────────────────┐
  旧策略通过      │  All In (A)      │  Swap Out (B)   │
                 │  新旧都通过       │  旧通过新拒绝    │
                 │  → 审批不变       │  → 被换出的客群  │
                 ├─────────────────┼─────────────────┤
  旧策略拒绝      │  Swap In (C)     │  All Out (D)    │
                 │  旧拒绝新通过     │  新旧都拒绝      │
                 │  → 被换入的客群   │  → 审批不变      │
                 └─────────────────┴─────────────────┘

核心判断逻辑：
  ✅ 新策略更优: Swap In 坏账率 < Swap Out 坏账率
     （换入的客户比换出的客户风险更低）
  ❌ 新策略更差: Swap In 坏账率 > Swap Out 坏账率
```

### 2.2 双口径分析框架

| 口径 | 定义 | 衡量目标 |
|------|------|---------|
| **人数口径** | 坏账人数 / 总通过人数 | 策略对人群的区分能力 |
| **金额口径** | 坏账金额 / 总放款金额 | 策略对实际资产质量的影响 |

> **关键**：人数口径和金额口径可能给出相反结论。例如换入客群人数坏账率低但授信额度高，金额口径坏账率可能反而上升。

### 2.3 业务/风险双链路

```
业务链路（通过率维度）:
  新策略通过率 vs 旧策略通过率
    → 通过率变化 (+2%)
    → 预估客群量变化 (+2000人)
    → 预估放款量变化 (+¥5,000,000)

风险链路（坏账率维度）:
  新策略坏账率 vs 旧策略坏账率
    → 坏账率变化 (-0.91%)
    → 预估损失变化 (-¥450,000)
    → 资产质量改善评估
```

---

## 三、任务设计

### 3.1 任务元数据

```python
STRATEGY_DIAGNOSIS_META = {
    "task_type": "strategy_diagnosis",
    "task_name": "策略诊断",
    "description": "评估新旧策略/模型更替对业务和风险的影响，支持 Swap Set 分析、人数/金额双口径对比",
    "trigger_keywords": [
        "策略诊断", "策略回溯", "策略对比", "新旧策略", "换入换出",
        "Swap Set", "Champion Challenger", "策略评估",
        "规则对比", "模型对比", "策略影响分析"
    ],
    
    "stages": [
        {"id": "data_loading", "name": "数据加载与校验", "progress_weight": 10},
        {"id": "strategy_application", "name": "策略应用与标记", "progress_weight": 20},
        {"id": "impact_analysis", "name": "多维度影响分析", "progress_weight": 25},
        {"id": "swap_analysis", "name": "换入换出客群分析", "progress_weight": 25},
        {"id": "report_generation", "name": "诊断报告生成", "progress_weight": 20}
    ],
}
```

### 3.2 参数设计

#### 必选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `target_col` | column_select | 目标变量（0/1，1=坏样本） |
| `old_strategy` | textarea / file_upload | 旧策略（规则表达式列表 / CSV 文件） |
| `new_strategy` | textarea / file_upload / task_result | 新策略（同上，或从历史任务结果导入） |

#### 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `exposure_amount_col` | column_select | 授信/放款金额列（启用金额口径分析） |
| `loss_amount_col` | column_select | 损失/逾期金额列（可选，默认用 target × exposure 估算） |
| `sample_type_col` | column_select | 样本类型列（train/test/oot），用于分数据集评估 |
| `time_col` | column_select | 时间列（用于时间维度的策略效果对比） |
| `strategy_type` | select | 策略类型：`rules`（规则集）/ `model`（评分模型 + cutoff） |

#### 策略输入格式

**规则类策略**：
```
# CSV 格式（结构化）
feature, operator, threshold
age, >, 30
income, <, 5000
credit_score, <=, 550

# 表达式格式（每行一条）
(age > 30)
(income < 5000) & (credit_score <= 550)
```

**模型类策略**：
```
# 评分卡表 + cutoff
score_column: credit_score
cutoff: 600
direction: higher_is_better  # 分数越高越好

# 或从历史评分卡任务导入
task_result_id: "abc123"  # 引用评分卡任务结果
```

### 3.3 Pipeline 阶段设计

#### Stage 1: 数据加载与校验 (data_loading)

```
输入: 数据集 + 旧策略 + 新策略 + 金额列(可选)
输出:
  ├─ 数据概览（样本量、目标分布、金额分布）
  ├─ 旧策略解析结果（N 条规则 / 1 个模型 + cutoff）
  ├─ 新策略解析结果
  ├─ 列名校验结果
  └─ 金额列校验（如有）

output_preview:
  ├─ total_samples, bad_rate
  ├─ old_strategy_count, new_strategy_count
  ├─ validation_result (pass/fail + 详情)
  └─ amount_info (如有金额列: total_amount, avg_amount)
```

#### Stage 2: 策略应用与标记 (strategy_application)

```
核心逻辑:
  对每条样本：
    old_pass = 旧策略是否命中/通过
    new_pass = 新策略是否命中/通过
    swap_label = 
      'all_in'   if old_pass and new_pass
      'swap_out' if old_pass and not new_pass
      'swap_in'  if not old_pass and new_pass
      'all_out'  if not old_pass and not new_pass

输出:
  ├─ Swap Set 标记列（每条样本的四象限分类）
  ├─ 四象限分布统计（人数 + 占比）
  └─ 新旧策略通过率对比

output_preview:
  ├─ swap_matrix: {all_in: N, swap_in: N, swap_out: N, all_out: N}
  ├─ old_pass_rate, new_pass_rate, pass_rate_change
  └─ swap_in_pct, swap_out_pct
```

#### Stage 3: 多维度影响分析 (impact_analysis)

```
人数口径:
  ├─ 各象限坏账率（all_in / swap_in / swap_out / all_out）
  ├─ 旧策略整体坏账率 vs 新策略整体坏账率
  ├─ 坏账率变化绝对值 + 相对变化
  └─ 关键判断: swap_in 坏账率 vs swap_out 坏账率

金额口径（如有 exposure_amount_col）:
  ├─ 各象限通过金额 / 损失金额
  ├─ 旧策略金额坏账率 vs 新策略金额坏账率
  ├─ 金额维度的 swap_in vs swap_out 对比
  └─ 业务链: 通过率变化 → 放款量变化 → 预估收入影响
  └─ 风险链: 坏账率变化 → 损失变化 → 资产质量影响

output_preview:
  ├─ count_metrics: {old_bad_rate, new_bad_rate, change, swap_in_bad_rate, swap_out_bad_rate}
  ├─ amount_metrics: {old_amount_bad_rate, new_amount_bad_rate, ...} (如有)
  ├─ business_impact: {pass_rate_change, est_volume_change, est_revenue_impact}
  └─ risk_impact: {bad_rate_change, est_loss_change, asset_quality_assessment}
```

#### Stage 4: 换入换出客群分析 (swap_analysis)

```
Swap In 客群画像:
  ├─ 样本量 + 坏账率
  ├─ Top N 特征分布（与整体对比）
  └─ 风险等级分布

Swap Out 客群画像:
  ├─ 同上
  └─ 阈值变化明细（同特征新旧阈值对比）

output_preview:
  ├─ swap_in_profile: {count, bad_rate, top_features: [...]}
  ├─ swap_out_profile: {count, bad_rate, top_features: [...]}
  └─ threshold_changes: [{feature, old_threshold, new_threshold, change_pct}, ...]
```

#### Stage 5: 诊断报告生成 (report_generation)

```
报告内容:
  ├─ 一、策略概览（新旧策略基本信息）
  ├─ 二、Swap Set 矩阵（四象限分布 + 可视化）
  ├─ 三、人数口径对比（通过率/坏账率/各象限指标）
  ├─ 四、金额口径对比（如有）
  ├─ 五、业务+风险影响评估
  ├─ 六、换入/换出客群画像
  ├─ 七、阈值变化明细
  └─ 八、AI 综合诊断意见

导出格式: HTML / Word / Excel / Markdown（复用现有报告框架）
```

---

## 四、可复用的现有模块

| 模块 | 位置 | 复用方式 |
|------|------|---------|
| `AmountAnalyzer` | `rule_mining.py` L3710-3980 | 单条规则金额指标计算逻辑可复用 |
| `PriorRuleAnalyzer` | `rule_mining.py` L3476-3707 | 先验规则解析、增量贡献计算可复用 |
| `DataPreprocessor.split_data()` | `scorecard_development.py` L374-512 | 数据集划分逻辑可复用 |
| `_safe_eval_rule()` | `rule_mining.py` | 安全规则评估函数可复用 |
| SOP Pipeline 框架 | `executor.py` + `*_meta.py` 模式 | 任务框架、阶段管理、进度回调完全复用 |
| 报告生成器 | `html/word/excel/markdown_report.py` | 扩展新的 `strategy_diagnosis` 报告类型 |
| 前端结果组件模式 | `RuleMiningResults.tsx` / `ScorecardResults.tsx` | 参照模式新建 `StrategyDiagnosisResults.tsx` |

---

## 五、预估工作量

| 阶段 | 内容 | 预估 |
|------|------|:----:|
| 方案细化 + Plan Review | 完善本文档、评审 | ~1天 |
| Meta + Pipeline 框架 | `strategy_diagnosis_meta.py` + Pipeline 类 | ~0.5天 |
| Stage 1-2（数据加载 + 策略应用） | 策略解析、Swap Set 标记 | ~1天 |
| Stage 3（多维影响分析） | 人数/金额双口径 + 业务/风险链 | ~1.5天 |
| Stage 4（客群画像） | 特征分布对比 + 阈值变化 | ~0.5天 |
| Stage 5（报告生成） | 四种格式报告 + AI Prompt | ~1天 |
| 前端结果页 | `StrategyDiagnosisResults.tsx` | ~1天 |
| 测试 | 单元测试 + 集成测试 | ~1天 |
| **总计** | | **~7-8天** |

---

## 六、实施路径

```
Phase 1（MVP，~4天）:
  ├─ 仅支持规则类策略（规则表达式）
  ├─ 人数口径 Swap Set 分析
  ├─ 简单阈值对比
  ├─ 基础前端结果页
  └─ HTML 报告

Phase 2（扩展，~2天）:
  ├─ 金额口径分析（需 exposure_amount_col）
  ├─ 业务/风险影响链路评估
  └─ 完整四格式报告

Phase 3（增强，~2天）:
  ├─ 支持模型类策略（评分卡 + cutoff）
  ├─ 从历史任务结果导入新策略
  ├─ 换入/换出客群画像
  └─ AI 分析 Prompt

远期:
  ├─ 拒绝推断（Reject Inference）— 估算被拒客群的风险表现
  ├─ 策略穿越测试（用历史数据跑新策略）
  └─ 多策略组合优化
```

---

## 七、风险与注意事项

### 7.1 被拒客群的风险表现

Swap In（旧策略拒绝、新策略通过）和 All Out（新旧都拒绝）的客群在历史上被拒绝，**没有真实的风险表现**。处理方式：

| 方法 | 说明 | 复杂度 |
|------|------|:------:|
| **标注说明** | 在报告中明确标注"Swap In 坏账率为预估值" | 低 |
| **模型分近似** | 用评分模型分来近似坏账率 | 中 |
| **随机测试样本** | 使用历史随机测试（Universe Test）数据 | 高 |
| **拒绝推断** | 硬截断/模糊扩增/外推法 | 高 |

MVP 阶段采用"标注说明"即可，高级方法在远期扩展。

### 7.2 数据要求

- 数据集必须包含旧策略和新策略涉及的所有特征列
- 如果新策略来自规则挖掘结果，数据集应与规则挖掘使用的数据一致
- 金额口径分析需要真实的金额数据（授信额度/放款金额）

### 7.3 与现有金额分析的关系

| 维度 | 现有 `AmountAnalyzer`（规则挖掘） | 策略诊断金额分析 |
|------|:-------------------------------:|:---------------:|
| 视角 | 单条规则的金额效果 | 新旧策略整体的金额影响 |
| 金额列 | 1 个（统一 amount_col） | 多个（授信/放款/损失） |
| 核心指标 | 命中金额、金额Lift | 通过金额变化、损失变化 |
| 分析框架 | 规则评估 | Swap Set 四象限 |
| 复用关系 | — | 可复用 `AmountAnalyzer` 的底层计算 |

---

## 八、变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1 | 2026-04-16 | 框架文档创建。从 `prior_rules_enhancement_plan.md` 拆分深度对比分析能力，新建独立 SOP 任务 |
