# 类别不平衡处理功能设计方案

> **文档状态**: 待开发  
> **创建日期**: 2026-01-12  
> **关联任务**: 规则挖掘、评分卡开发  
> **优先级**: 中

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
- 决策树代码中使用了 `class_weight='balanced'`，但用户无法控制

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
| `rule_mining.py` | 添加不平衡处理逻辑，修改决策树训练代码 |
| `scorecard_development.py` | 添加不平衡处理逻辑，修改逻辑回归训练代码 |
| `StageOutputPreview.tsx` | 增加不平衡分析信息展示 |
| `requirements.txt` | 确认 `imbalanced-learn` 依赖 |

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
