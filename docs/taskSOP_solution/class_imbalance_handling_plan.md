# 类别不平衡处理功能设计方案

> **文档状态**: ✅ Phase 1 MVP 已实施 + 测试通过（2026-04-16，10/10 PASS）  
> **创建日期**: 2026-01-12  
> **关联任务**: 规则挖掘、评分卡开发  
> **优先级**: P2  
> **开发评审**: Eng Review + Design Review 已完成（2026-04-16），详见下方评审记录

### 📋 Eng Review 评审记录（2026-04-16）

> **审查方法**: plan-eng-review（架构/代码质量/测试/性能 四维评审）

#### ⚠️ 重要修正：方案事实错误

经代码验证，方案原文中**两处关于 `class_weight='balanced'` 的描述不正确**：

| 原文描述 | 代码实际情况 |
|---------|------------|
| "规则挖掘决策树硬编码了 `class_weight='balanced'`" | ❌ 不存在。`DecisionTreeClassifier` 通过 `sample_weight` 传入 `weight_col`（默认为 1），**当前未做任何不平衡处理** |
| "`weight_col` 与 `class_weight` 冲突，sklearn 不支持同时使用" | ❌ sklearn 中 `class_weight` 和 `sample_weight` 是**叠加关系**（class_weight 权重 × sample_weight），不是冲突 |

> 原 2026-04-15 初步评审的 #1（向后兼容风险）和 #2（weight_col 冲突）基于错误前提，已废弃并替换为以下更新评审。

#### 🔴 必须修订（开发前解决）

| # | 问题 | 说明 | 建议修复 |
|---|------|------|---------|
| **E1** | **方案事实错误** | 第 56、113 行声称"硬编码了 `class_weight='balanced'`"，实际代码中不存在。误导开发者 | 修正为"通过 `sample_weight` 传入 `weight_col`（默认为 1），当前未做任何不平衡处理" |
| **E2** | **遗漏 `executor.py` 修改** | 文件修改清单未列出 `executor.py`。P1-5 已证明新增参数不在 executor 中传递 → 参数到不了 `run()` → 功能静默失效 | 文件清单补充 `executor.py`（传递 `imbalance_strategy` 参数） |
| **E3** | **`StatisticalLogisticRegression` + `class_weight` 兼容性** | 评分卡使用自定义 `StatisticalLogisticRegression`（继承 sklearn LR），加 `class_weight='balanced'` 后统计信息计算（p-value、标准误）是否仍正确？加权样本的统计推断方法与无加权不同 | 开发时添加对比测试，验证加权后统计输出的合理性 |

#### 🟡 建议修订

| # | 建议 | 理由 |
|---|------|------|
| **E4** | **分阶段实施（MVP 优先）** | 先只实现 `none`/`auto`/`class_weight` 三个选项，不引入 `imbalanced-learn` 依赖。工作量 ~3天→~1天，覆盖 90%+ 场景 |
| **E5** | **伪代码映射到实际修改位置** | 方案只写了一个 `_build_decision_tree` 伪函数，但实际 `DecisionTreeClassifier` 出现在 3 处：`_get_rules_from_tree`(L2235)、`get_split_point`(L2480)、分箱 DT(L1818，不需改) |
| **E6** | **补充 AI Prompt 更新** | 方案遗漏 `AI_analysis_prompts.py` 变更。应用不平衡处理后，AI 分析应知道用了什么策略 |
| **E7** | **auto 策略 MVP 简化** | 原 auto 有 5 个分支 + 样本量判断，MVP 只有 `none`/`class_weight` 两个输出，简化为：`bad_rate < 0.1 → class_weight，否则 → none` |
| **E8** | **weight_col + class_weight 叠加说明** | sklearn 中两者是叠加关系，UI 和 output_preview 中应说明叠加效果 |

#### 📋 测试覆盖度 — ✅ 已完成（2026-04-16）

方案原有 5 个测试用例，评审补充 4 个，实际扩展为 10 个（真实数据版）。

**测试脚本**: `tests/test_imbalance_strategy.py`  
**数据集**: `starrel_train_with_amount.csv`（23349行, 85列, bad_rate=5.13%）  
**结果**: 10/10 全部通过，耗时 ~109s

| # | 用例 | 任务类型 | 策略 | 结果 | 关键验证 |
|---|------|---------|------|:----:|---------|
| **E8** | `_build_imbalance_analysis` 信息完整性 | 单元 | 7种组合 | ✅ | severity 分级边界值 + auto 解析 + 字段完整性 |
| **T6-none** | 规则挖掘向后兼容基线 | 规则挖掘 | none | ✅ | class_weight=None, 291 条规则 |
| **T6-CW** | 规则挖掘 class_weight 对照 | 规则挖掘 | class_weight | ✅ | class_weight=balanced, 184 条规则 |
| **T6-AUTO** | 规则挖掘 auto 策略 | 规则挖掘 | auto | ✅ | bad_rate=5.2%→class_weight, 184 条 |
| **T8-RM** | 规则挖掘 SamplingWeight+CW 叠加 | 规则挖掘 | CW+权重 | ✅ | 叠加无冲突, 352 条规则 |
| **T9/E3** | StatisticalLR 统计信息正确性 | 统计模型 | 对照 | ✅ | p∈[0,1], std_err>0, z有限, 方向一致 |
| **T7-none** | 评分卡向后兼容基线 | 评分卡 | none | ✅ | Pipeline 正常完成 |
| **T7-CW** | 评分卡 class_weight 对照 | 评分卡 | class_weight | ✅ | Pipeline 正常完成 |
| **T7-AUTO** | 评分卡 auto 策略 | 评分卡 | auto | ✅ | bad_rate=5.2%→class_weight |
| **T7-T8** | 评分卡 SamplingWeight+CW 叠加 | 评分卡 | CW+权重 | ✅ | 叠加无冲突 |

**附带发现**: 规则挖掘 Pipeline preprocessing 阶段对该数据集有一个预存 Bug（One-Hot 处理导致 target_col 丢失），测试中通过 `skip_preprocessing=True` 绕过，不属于 P2-6 范围。

| # | 缺失场景 | 重要性 | 状态 |
|---|---------|:---:|:---:|
| **T6** | 向后兼容基线（规则挖掘，strategy=none，验证与当前行为一致） | 🔴 | ✅ T6-none |
| **T7** | 向后兼容基线（评分卡，strategy=none） | 🔴 | ✅ T7-none |
| **T8** | weight_col + class_weight 叠加（验证权重正确叠加） | 🟡 | ✅ T8-RM + T7-T8 |
| **T9** | StatisticalLR + class_weight 统计信息正确性 | 🔴 | ✅ T9/E3 |

#### 🔴 关键失败模式

| # | 代码路径 | 失败场景 | 后果 |
|---|---------|---------|------|
| **F1** | `StatisticalLR` + `class_weight` | 统计信息计算不准确 | 评分卡 p-value/z-score 错误，误导变量筛选 |
| **F3** | `executor.py` 未传参 | `imbalance_strategy` 不传到 `run()` | 策略静默不生效 |

#### 📊 Eng Review Summary

```
Step 0: Scope Challenge       — 发现方案事实错误，scope 维持 MVP
Architecture Review           — 3 issues (E1-E3, 2 critical)
Code Quality Review           — 3 issues (E5-E7)
Test Review                   — 5→9 用例，4 gaps (T6-T9)
Performance Review            — 0 issues
Failure modes                 — 2 critical gaps (F1, F3)
```

---

### 📋 Design Review 评审记录（2026-04-16）

> **审查方法**: plan-design-review（7 维设计评审）

#### 📊 评分总览

| Pass | 维度 | 初始 | 修正后 | 说明 |
|------|------|:---:|:---:|------|
| 1 | 信息架构 | 7 | 8 | 不平衡分析卡片位置明确（紧邻 bad_rate 之后） |
| 2 | 交互状态 | 4 | 8 | 补充条件守卫：bad_rate≥20% 不显示卡片；none+bad_rate<10% 加 ⚠️ 提示 |
| 3 | 用户旅程 | 6 | 8 | AI 文字建议引用参数名形成闭环 |
| 4 | AI Slop | 8 | 8 | ASCII mockup 具体，非通用模板 |
| 5 | 设计系统 | 7 | 9 | 映射到 shadcn/ui：Select 组件 + Card/Badge 模式 + OOT 颜色编码 |
| 6 | 响应式/A11y | 3 | 7 | 继承现有 shadcn/ui 组件的响应式和 a11y |
| **总分** | | **5** | **8** | |

#### 🟡 Design 建议

| # | 建议 | 说明 |
|---|------|------|
| **D1** | **不平衡分析卡片条件守卫** | `bad_rate ≥ 20%`（无不平衡）时不显示卡片；`bad_rate < 20%` 时显示程度、策略、说明 |
| **D2** | **strategy=none 且 bad_rate<10% 时加 ⚠️ 提示** | "建议启用不平衡处理"，引导用户注意 |
| **D3** | **AI 分析闭环** | AI 检测到不平衡时，文字建议中引用参数名（"建议调整'类别不平衡处理'参数"） |
| **D4** | **组件映射** | 下拉框 → shadcn `Select`；结果卡片 → 复用 `StageOutputPreview` 的 `Card` + `Badge`；严重程度颜色 → 复用 OOT 稳定性四级颜色 |

#### NOT in scope

- DESIGN.md 创建（项目级，不在本方案范围）
- 移动端定制布局（继承现有组件响应式行为即可）
- SMOTE 等采样策略的 UI（Phase 2）

---

### 📋 建议实施路径（更新）

```
Phase 1（MVP，~1天）: none / auto / class_weight
  ├─ 不引入新依赖（imbalanced-learn）
  ├─ 覆盖 90%+ 实际场景
  ├─ 解决"用户不可控"的核心问题
  ├─ auto 简化: bad_rate<10% → class_weight, 否则 → none
  ├─ 两个任务默认值均为 auto
  └─ 文件清单: 2 meta + 2 后端 + executor.py + AI_analysis_prompts.py + 1 前端

Phase 2（按需扩展）: smote / undersample / smote_tomek
  ├─ 引入 imbalanced-learn
  ├─ 需有极端不平衡场景的实际反馈驱动
  └─ 先确认 SMOTE 在 WOE 空间的有效性
```

---

### 📌 快速回顾（开发前必读）

**作用与目标**：当数据集存在类别不平衡（如坏账率 5%）时，AI 分析评估已能检测并提示，但目前**只有文字建议，没有可操作的处理选项**。本方案为规则挖掘和评分卡开发任务添加类别不平衡的自动/手动处理能力。

**当前实现的问题**：
- 第一阶段 AI 分析会提示"5.13%的坏账率存在类别不平衡"，但没有对应参数让用户选择处理策略
- 规则挖掘的决策树硬编码了 `class_weight='balanced'`，用户无法控制
- 评分卡的逻辑回归训练未使用任何类别加权

**优化内容**：
- 新增 `imbalance_strategy` 参数（none/auto/class_weight/smote/undersample/smote_tomek）
- `auto` 模式根据坏账率和样本量自动选择最优策略
- **关键约束**：评分卡 WOE 分箱阶段**不采样**（保持原始分布），采样仅在 model_training 阶段

**后端变化**：
- `rule_mining_meta.py` / `scorecard_meta.py`：新增 `imbalance_strategy` 参数定义
- `rule_mining.py`：决策树训练根据策略选择 `class_weight` 或采样后数据
- `scorecard_development.py`：逻辑回归训练根据策略选择 `class_weight` 或 SMOTE/欠采样
- `requirements.txt`：新增 `imbalanced-learn>=0.10.0` 依赖

**前端变化**：
- 参数配置面板：新增策略选择下拉框
- `StageOutputPreview.tsx`：第一阶段结果卡片新增不平衡分析信息（比例、程度、应用策略）

---

## 1. 问题分析

### 1.1 当前状态

在规则挖掘和评分卡开发任务的第一阶段结果中，AI分析评估会检测并提示类别不平衡问题：

| 任务 | 第一阶段 | 坏账率 | AI提示 |
|------|---------|--------|--------|
| 规则挖掘 | preprocessing | 5.13% | "5.13%的坏账率表示数据集存在类别不平衡" |
| 评分卡开发 | data_loading | 5.13% | "5.13%的坏账率表明存在类别不平衡问题，需重点关注" |

### 1.2 功能缺口

**问题**：AI分析评估中提到的"欠采样或SMOTE"等建议，目前只是文字建议，没有对应的交互参数和后续阶段的自动应用逻辑。

| 检查项 | 规则挖掘 | 评分卡开发 |
|--------|---------|-----------|
| 第一阶段检测不平衡 | ✅ 有 | ✅ 有 |
| 提供处理策略选项 | ❌ 无 | ❌ 无 |
| 后续阶段自动应用 | ❌ 无 | ❌ 无 |

### 1.3 现有相关参数

#### 规则挖掘任务

```python
# rule_mining_meta.py - 仅有权重列参数
{
    "name": "weight_col",
    "type": "column_select",
    "label": "权重列",
    "description": "样本权重列（可选，无则默认为1）",
    "stage": "preprocessing"
}
```

- `weight_col` 用于已有权重的数据，不是自动处理不平衡的选项
- 决策树通过 `sample_weight` 传入 `weight_col`（默认为 1），当前**未使用** `class_weight` 参数，无任何自动不平衡处理

#### 评分卡开发任务

- 无任何类别不平衡处理相关参数
- 逻辑回归训练时未使用 `class_weight` 参数

---

## 2. 行业惯例与处理策略

### 2.1 类别不平衡的判定标准

| 不平衡程度 | 少数类比例 | 建议处理方式 |
|-----------|-----------|-------------|
| 轻度 | 10% - 20% | 可不处理或使用类别加权 |
| 中度 | 5% - 10% | 建议使用类别加权或采样 |
| 重度 | 1% - 5% | 必须处理，推荐SMOTE或组合采样 |
| 极端 | < 1% | 需要特殊处理策略（如代价敏感学习） |

### 2.2 常用处理策略

| 策略 | 原理 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|---------|
| **类别加权** | 调整损失函数中各类别的权重 | 不改变样本量，计算快 | 效果有限 | 轻度/中度不平衡 |
| **SMOTE** | 在少数类样本间插值生成新样本 | 增加少数类信息 | 可能过拟合，计算慢 | 中度/重度不平衡 |
| **随机欠采样** | 随机删除多数类样本 | 简单快速 | 丢失信息 | 数据量大时 |
| **Tomek Links** | 删除边界多数类样本 | 清理边界 | 效果有限 | 配合其他方法 |
| **SMOTE + Tomek** | 先过采样再清理边界 | 综合效果好 | 计算较慢 | 重度不平衡 |
| **代价敏感学习** | 为不同类别设置不同误分类代价 | 灵活 | 需要业务知识 | 极端不平衡 |

### 2.3 风控建模特殊考量

1. **评分卡开发**：通常使用类别加权，避免改变样本分布影响WOE/IV计算
2. **规则挖掘**：可使用SMOTE或类别加权，决策树对不平衡较敏感
3. **模型验证**：测试集不应做采样处理，保持原始分布

---

## 3. 设计方案

### 3.1 参数设计

#### 3.1.1 新增参数定义

```python
# 通用参数，适用于两个任务
{
    "name": "imbalance_strategy",
    "type": "select",
    "label": "类别不平衡处理",
    "label_en": "Imbalance Strategy",
    "options": [
        {"value": "none", "label": "不处理"},
        {"value": "auto", "label": "自动选择（推荐）"},
        {"value": "class_weight", "label": "类别加权"},
        {"value": "smote", "label": "SMOTE过采样"},
        {"value": "undersample", "label": "随机欠采样"},
        {"value": "smote_tomek", "label": "SMOTE + Tomek（组合）"}
    ],
    "default": "auto",
    "description": "当坏样本率<10%时建议启用。类别加权不改变样本量，SMOTE会增加少数类样本，欠采样会减少多数类样本",
    "stage": "preprocessing",  # 规则挖掘
    # "stage": "data_loading",  # 评分卡开发
    "advanced": False
}
```

#### 3.1.2 自动选择逻辑

```python
def auto_select_imbalance_strategy(target_rate: float, sample_size: int) -> str:
    """
    根据坏账率和样本量自动选择不平衡处理策略
    
    Args:
        target_rate: 坏样本率（0-1）
        sample_size: 总样本量
        
    Returns:
        策略名称: 'none', 'class_weight', 'smote', 'undersample', 'smote_tomek'
    """
    if target_rate >= 0.2:
        # 轻度或无不平衡
        return "none"
    elif target_rate >= 0.1:
        # 轻度不平衡
        return "class_weight"
    elif target_rate >= 0.05:
        # 中度不平衡
        if sample_size < 10000:
            return "smote"
        else:
            return "class_weight"
    elif target_rate >= 0.01:
        # 重度不平衡
        if sample_size < 5000:
            return "smote_tomek"
        else:
            return "smote"
    else:
        # 极端不平衡
        return "smote_tomek"
```

### 3.2 后续阶段应用逻辑

#### 3.2.1 规则挖掘任务

| 阶段 | 应用方式 |
|------|---------|
| preprocessing | 记录策略选择，计算采样参数 |
| feature_engineering | 如使用采样策略，在此阶段执行采样 |
| generating_rules | 决策树使用 `class_weight` 或采样后数据 |

**代码修改位置**: `rule_mining.py`

```python
# generating_rules 阶段
def _build_decision_tree(self, df, target_col, feature_cols, params):
    imbalance_strategy = params.get('imbalance_strategy', 'auto')
    
    if imbalance_strategy == 'class_weight' or imbalance_strategy == 'auto':
        # 使用类别加权
        clf = DecisionTreeClassifier(
            max_depth=params.get('max_depth', 5),
            min_samples_leaf=params.get('min_samples_leaf', 0.01),
            class_weight='balanced'  # 关键参数
        )
    else:
        # 使用采样后的数据（在之前阶段已处理）
        clf = DecisionTreeClassifier(
            max_depth=params.get('max_depth', 5),
            min_samples_leaf=params.get('min_samples_leaf', 0.01)
        )
    
    return clf.fit(df[feature_cols], df[target_col])
```

#### 3.2.2 评分卡开发任务

| 阶段 | 应用方式 |
|------|---------|
| data_loading | 记录策略选择，计算采样参数 |
| woe_binning | **不应用采样**，保持原始分布计算WOE/IV |
| model_training | 逻辑回归使用 `class_weight` 或采样后数据 |

**代码修改位置**: `scorecard_development.py`

```python
# model_training 阶段
def _train_logistic_regression(self, X_train, y_train, params):
    imbalance_strategy = params.get('imbalance_strategy', 'auto')
    
    if imbalance_strategy in ['class_weight', 'auto']:
        # 使用类别加权
        model = LogisticRegression(
            class_weight='balanced',
            max_iter=1000,
            solver='lbfgs'
        )
    elif imbalance_strategy == 'smote':
        # 使用SMOTE采样后的数据
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(random_state=42)
        X_train, y_train = smote.fit_resample(X_train, y_train)
        model = LogisticRegression(max_iter=1000, solver='lbfgs')
    elif imbalance_strategy == 'undersample':
        # 使用欠采样后的数据
        from imblearn.under_sampling import RandomUnderSampler
        rus = RandomUnderSampler(random_state=42)
        X_train, y_train = rus.fit_resample(X_train, y_train)
        model = LogisticRegression(max_iter=1000, solver='lbfgs')
    else:
        model = LogisticRegression(max_iter=1000, solver='lbfgs')
    
    return model.fit(X_train, y_train)
```

### 3.3 第一阶段结果展示增强

在 `output_preview` 中增加不平衡分析信息：

```python
# 新增字段
"imbalance_analysis": {
    "target_rate": 0.0513,
    "imbalance_ratio": "1:18.5",  # 好:坏 比例
    "severity": "中度",  # 轻度/中度/重度/极端
    "recommended_strategy": "class_weight",
    "applied_strategy": "auto",  # 用户选择或自动
    "strategy_description": "使用类别加权，不改变样本分布"
}
```

### 3.4 前端展示设计

#### 3.4.1 第一阶段结果卡片

```
┌─────────────────────────────────────────────────────────┐
│  类别分布                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │  94.87%  │  │  5.13%   │  │ 不平衡比例: 1:18.5   │   │
│  │  好样本   │  │  坏样本   │  │ 程度: 中度 ⚠️        │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
│                                                          │
│  处理策略: 自动选择 → 类别加权                            │
│  说明: 在模型训练阶段使用balanced权重，不改变样本分布       │
└─────────────────────────────────────────────────────────┘
```

#### 3.4.2 参数配置面板

```
┌─────────────────────────────────────────────────────────┐
│  类别不平衡处理                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ○ 不处理                                         │    │
│  │ ● 自动选择（推荐）                               │    │
│  │ ○ 类别加权                                       │    │
│  │ ○ SMOTE过采样                                    │    │
│  │ ○ 随机欠采样                                     │    │
│  │ ○ SMOTE + Tomek（组合）                          │    │
│  └─────────────────────────────────────────────────┘    │
│  💡 当前坏样本率5.13%，建议使用类别加权或SMOTE           │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 实现计划

### 4.1 文件修改清单

| 文件 | 修改内容 |
|------|---------|
| `rule_mining_meta.py` | 新增 `imbalance_strategy` 参数定义 |
| `scorecard_meta.py` | 新增 `imbalance_strategy` 参数定义 |
| `rule_mining.py` | 添加不平衡处理逻辑，修改决策树训练代码（`_get_rules_from_tree` L2235 + `get_split_point` L2480） |
| `scorecard_development.py` | 添加不平衡处理逻辑，修改逻辑回归训练代码（`StatisticalLogisticRegression` 传 `class_weight`） |
| `executor.py` | 传递 `imbalance_strategy` 参数到 `run()` 方法（⚠️ P1-5 遗漏此步导致 14 个测试失败） |
| `AI_analysis_prompts.py` | 各阶段分析 prompt 中加入不平衡处理策略信息 |
| `StageOutputPreview.tsx` | 增加不平衡分析信息展示 |
| `requirements.txt` | MVP 阶段无需新增依赖（Phase 2 再加 `imbalanced-learn`） |

### 4.2 依赖检查

```python
# 需要的依赖
imbalanced-learn>=0.10.0  # SMOTE, RandomUnderSampler, Tomek Links
```

### 4.3 开发步骤

1. **Phase 1: 参数定义** (0.5天)
   - 修改 `rule_mining_meta.py` 和 `scorecard_meta.py`
   - 添加参数定义和验证逻辑

2. **Phase 2: 后端逻辑** (1天)
   - 实现 `ImbalanceHandler` 工具类
   - 修改 `rule_mining.py` 的 `generating_rules` 阶段
   - 修改 `scorecard_development.py` 的 `model_training` 阶段

3. **Phase 3: 结果展示** (0.5天)
   - 修改 `output_preview` 数据结构
   - 更新 `StageOutputPreview.tsx` 展示组件

4. **Phase 4: 测试验证** (1天)
   - 单元测试
   - 集成测试
   - 不同不平衡程度的数据测试

### 4.4 测试用例

> **Phase 1 MVP 实际测试**: 见上方 Eng Review §📋测试覆盖度（10/10 全部通过，真实数据验证）

原方案测试用例（Phase 2 SMOTE 相关，暂未实施）：

| 测试场景 | 坏样本率 | 期望策略 | 验证点 |
|---------|---------|---------|--------|
| 平衡数据 | 25% | none | 不应用任何处理 |
| 轻度不平衡 | 15% | class_weight | 模型使用balanced权重 |
| 中度不平衡 | 5% | class_weight/smote | 根据样本量选择 |
| 重度不平衡 | 2% | smote | SMOTE采样后样本量增加 |
| 极端不平衡 | 0.5% | smote_tomek | 组合采样 |

---

## 5. 风险与注意事项

### 5.1 WOE/IV计算注意

**重要**：评分卡开发任务中，WOE分箱阶段**不应使用采样后的数据**，否则会影响WOE值和IV值的准确性。

采样处理应仅在 `model_training` 阶段应用。

### 5.2 测试集处理

**重要**：测试集和OOT验证集**不应进行采样处理**，必须保持原始分布以准确评估模型效果。

### 5.3 性能考量

- SMOTE在大数据集上可能较慢
- 建议对样本量>100万的数据默认使用类别加权而非SMOTE

### 5.4 可解释性

- 使用采样后，需在报告中说明采样前后的样本量变化
- 模型评估指标应基于原始分布的测试集

---

## 6. 参考资料

- [imbalanced-learn 官方文档](https://imbalanced-learn.org/)
- [SMOTE: Synthetic Minority Over-sampling Technique](https://arxiv.org/abs/1106.1813)
- [Handling Imbalanced Data in Credit Scoring](https://www.sciencedirect.com/science/article/pii/S0957417415004674)
