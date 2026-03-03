# 策略规则挖掘任务SOP构建方案

> **文档目的**：基于项目已有底层能力，参照 `scorecard_development_task_design.md` 的架构设计，构建策略规则挖掘场景的业务任务模板方案，供评估后实施。

---

## 一、项目现有能力盘点

### 1.1 已具备的底层模块

| 模块 | 文件位置 | 核心能力 | 规则挖掘适用性 |
|------|----------|----------|----------------|
| **通用数据预处理** | `preprocessing.py` | `DatetimeProcessor`、`TextProcessor`、`CategoricalProcessor`、`ColumnCleaner` | ✅ 通用模块 |
| **数据预处理** | `rule_mining.py` | `DataPreprocessor.preprocess()` | ✅ 已实现（复用通用模块） |
| **特征工程** | `rule_mining.py` | `FeatureEngineer.preprocess()` | ✅ 已实现 |
| **单特征规则生成** | `rule_mining.py` | `SingleVarRuleMiner.generate_rules()` | ✅ 已实现 |
| **多特征规则生成** | `rule_mining.py` | `RuleMiner.generate_rules()` | ✅ 已实现 |
| **规则效果评估** | `rule_mining.py` | `RuleEvaluator.evaluate_rules()` | ✅ 已实现 |
| **最优规则选择** | `rule_mining.py` | `RuleSelector.select_optimal_rules()` | ✅ 已实现 |
| **Pipeline编排** | `rule_mining.py` | `RuleMiningPipeline.run()` | ✅ 已实现 |
| **决策树** | `sklearn.tree` (已安装) | 规则提取、方向判断 | ✅ 直接可用 |
| **可视化** | `matplotlib/plotly` | 规则效果图、累计曲线 | ✅ 直接可用 |

### 1.2 通用数据预处理模块

新增通用预处理模块 `deepanalyze/analysis/preprocessing.py`，提供可复用的数据预处理工具：

```python
from deepanalyze.analysis.preprocessing import (
    DatetimeProcessor,      # 日期时间列检测与特征提取
    TextProcessor,          # 文本列检测与特征提取
    CategoricalProcessor,   # 分类列检测与One-Hot编码
    ColumnCleaner,          # ID列、常量列、高缺失列清理
    GeneralPreprocessor     # 统一预处理接口
)

# 独立使用示例
datetime_proc = DatetimeProcessor(indicator='_dt_')
df, new_cols = datetime_proc.process(df, datetime_cols=['create_time'])

text_proc = TextProcessor(indicator='_txt_')
df, new_cols = text_proc.process(df, text_cols=['comment'], keywords={'has_complaint': ['投诉']})

# 统一接口
preprocessor = GeneralPreprocessor(id_cols=['user_id'])
df_clean, info = preprocessor.preprocess(df, exclude_cols=['target'])
```

### 1.3 核心类功能映射

```python
from deepanalyze.analysis.task_SOP.rule_mining import (
    DataPreprocessor,      # 数据预处理（特征名映射、智能检测排除列、日期/文本处理、One-Hot编码）
    FeatureEngineer,       # 特征工程预处理（缺失值、IV筛选）
    SingleVarRuleMiner,    # 单特征规则生成（阈值分箱）
    RuleMiner,             # 多特征规则生成（决策树）
    RuleEvaluator,         # 规则效果评估
    RuleSelector,          # 最优规则选择（贪心算法）
    RuleMiningPipeline     # 完整流程编排
)

# 核心功能调用
preprocessor = DataPreprocessor(
    id_cols=['fuuid'], 
    name_mapping={'f0': 'age'},
    datetime_indicator='_dt_',
    text_indicator='_txt_'
)
df_clean, info = preprocessor.preprocess(
    df, target_col='target',
    do_onehot=True, do_datetime=True, do_text=True,
    datetime_features=['year', 'month', 'dayofweek', 'days_since'],
    text_features=['length', 'word_count'],
    text_keywords={'has_complaint': ['投诉', '差评']}
)

miner = SingleVarRuleMiner(n_bins=10, directions='both')
rules = miner.generate_rules(df, feature_cols, target_col, weight_col)

evaluator = RuleEvaluator()
evaluated = evaluator.evaluate_rules(df, rules, target_col, weight_col)

selector = RuleSelector()
optimal = selector.select_optimal_rules(df, evaluated, target_col, weight_col)
```

### 1.3 已实现 vs 待完善能力

| 能力 | 现状 | 说明 |
|------|------|------|
| 数据预处理 | ✅ 已实现 | `DataPreprocessor` 类 |
| 特征工程预处理 | ✅ 已实现 | `FeatureEngineer` 类（可选） |
| 单特征规则生成 | ✅ 已实现 | `SingleVarRuleMiner` 类 |
| 多特征规则生成 | ✅ 已实现 | `RuleMiner` 类 |
| 规则效果评估 | ✅ 已实现 | `RuleEvaluator` 类 |
| 最优规则选择 | ✅ 已实现 | `RuleSelector` 类 |
| Pipeline编排 | ✅ 已实现 | `RuleMiningPipeline` 类 |
| WebUI任务元数据 | ✅ 已完成 | `rule_mining_meta.py` |
| LLM SOP Prompt模板 | ✅ 已完成 | 集成在 `rule_mining_meta.py` |
| SOP Registry注册中心 | ✅ 已完成 | `registry.py` |
| SOP Executor执行引擎 | ✅ 已完成 | `executor.py` |
| SOP API端点 | ✅ 已完成 | `API/sop_api.py` |
| 可视化报告生成 | ✅ 已完成 | `rule_mining_viz.py` |
| 单元测试 | ✅ 已完成 | `tests/test_rule_mining.py` |
| 集成测试 | ✅ 已完成 | `tests/test_sop_api.py` |
| 前端参数表单 | ✅ 已完成 | `demo/chat/components/sop/` |
| 前端服务层 | ✅ 已完成 | `demo/chat/lib/sopService.ts` |

---

## 二、规则挖掘标准工作流（SOP）

### 2.1 工作流全景图

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            策略规则挖掘完整工作流（6阶段，含报告生成）                                │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                    │
│  ┌──────────┐   ┌──────────┐   ┌────────────────┐   ┌────────────────┐   ┌─────────┐   ┌─────────┐│
│  │ 阶段1    │   │[可选]    │   │    阶段3       │   │    阶段4       │   │ 阶段5   │   │ 阶段6   ││
│  │ 数据     │──▶│ 阶段2    │──▶│  规则生成      │──▶│  规则过滤      │──▶│ 最优    │──▶│ 报告    ││
│  │ 预处理   │   │ 特征工程 │   │ (模式可选)     │   │ (方向+效果)    │   │ 选择    │   │ 生成    ││
│  └──────────┘   └──────────┘   └────────────────┘   └────────────────┘   └─────────┘   └─────────┘│
│       │              │              │                      │                  │             │     │
│       ▼              ▼              ▼                      ▼                  ▼             ▼     │
│  特征名映射      缺失值处理    ┌─────────────────┐    方向过滤+效果评估     贪心算法     可视化图表 │
│  智能检测排除列  IV计算       │🎯单特征: 阈值分箱│    recall/bad_rate      累计指标     规则表格   │
│  日期时间处理    变量预筛选    │🌲多特征: 决策树 │    lift/hit_rate过滤    最优规则     效果分析   │
│  文本特征处理                 └─────────────────┘                                                 │
│  One-Hot编码                                                                                      │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 各阶段详细说明

#### 阶段0a：数据预处理（必需）

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 0a.1 | 特征名映射 | `DataPreprocessor.rename_features()` | 重命名后的列 |
| 0a.2 | 智能检测ID列 | `DataPreprocessor._detect_id_columns()` | ID列列表（只标记不删除） |
| 0a.3 | 检测常量列 | `DataPreprocessor._detect_constant_columns()` | 常量列列表（只标记不删除） |
| 0a.4 | 日期时间列处理 | `DataPreprocessor.preprocess_datetime()` | 日期衍生特征 |
| 0a.5 | 文本列处理 | `DataPreprocessor.preprocess_text()` | 文本衍生特征 |
| 0a.6 | One-Hot编码 | `DataPreprocessor.onehot_encode()` | 编码后数据 |
| 0a.7 | **数据质量自动检测** | `DataPreprocessor.assess_data_quality()` | 质量评估报告 |

**关键参数**：
- `id_cols`: ID列名列表（如 `['fuuid', 'user_id']`）
- `drop_cols`: 额外需要删除的列
- `name_mapping`: 特征名映射字典（如 `{'f0': 'age'}`）
- `categorical_cols`: 需要One-Hot编码的分类列
- `datetime_cols`: 需要处理的日期时间列（可自动检测）
- `text_cols`: 需要处理的文本列（可自动检测）
- `datetime_features`: 日期衍生特征列表（默认：year, month, dayofweek, hour, days_since）
- `text_features`: 文本衍生特征列表（默认：length, word_count）
- `text_keywords`: 关键词检测字典（如 `{'has_complaint': ['投诉', '差评']}`）

**数据质量自动检测**（`assess_data_quality` 方法）：
- 缺失率分析：检测高缺失率特征（阈值默认30%）
- 数据类型分析：区分数值型/分类型/文本型特征比例
- 基数分析：检测高基数分类变量（阈值默认50）
- 方差分析：检测常量列和低方差列
- 质量评分：计算0-100分的综合质量评分
- 自动决策：评分<70或问题≥2时建议启用特征工程

#### 阶段0b：特征工程预处理（根据数据质量自动决定或用户指定）

**执行条件判断**：
- 如果 `enable_feature_engineering=True`（用户明确启用）：执行特征工程
- 如果 `enable_feature_engineering=False` 但数据质量评分 < 70：建议启用特征工程，并在日志中提示
- 如果 `enable_feature_engineering=False` 且数据质量评分 >= 70：跳过特征工程，数据质量良好

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 0b.1 | 缺失值检查 | `FeatureEngineer.check_missing()` | 缺失率报告 |
| 0b.2 | 缺失值处理 | `FeatureEngineer.handle_missing()` | 清洗后数据 |
| 0b.3 | IV值计算 | `FeatureEngineer.calculate_iv()` | IV值表 |
| 0b.4 | 变量预筛选 | `FeatureEngineer.filter_by_iv()` | 有效变量列表 |
| 0b.5 | One-Hot编码 | `FeatureEngineer.onehot_encode()` | 编码后数据 |

**关键参数**：
- `missing_threshold`: 缺失率阈值（默认0.5）
- `iv_threshold`: IV值阈值（默认0.02）
- `onehot_indicator`: One-Hot编码标识符（默认`_is_`）

#### 阶段1：规则生成（模式可选）

##### 模式A：单特征规则（阈值分箱）

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 1.1 | 获取分箱阈值 | `SingleVarRuleMiner._get_thresholds()` | 阈值列表 |
| 1.2 | 生成数值规则 | `SingleVarRuleMiner.generate_rules()` | 数值规则 |
| 1.3 | 生成分类规则 | `SingleVarRuleMiner.generate_categorical_rules()` | 分类规则 |

**关键参数**：
- `n_bins`: 分箱数量（默认10）
- `bin_method`: 分箱方式（`'quantile'`/`'uniform'`/`'custom'`）
- `rule_directions`: 规则方向（`'<='`/`'>'`/`'both'`）

**规则格式**：`(age <= 25)`, `(income > 50000)`

##### 模式B：多特征组合规则（决策树）

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 1.1 | 变量组合 | `itertools.combinations()` | 组合列表 |
| 1.2 | 构建决策树 | `sklearn.tree.DecisionTreeClassifier` | 决策树模型 |
| 1.3 | 提取规则路径 | `RuleMiner._get_rules_from_tree()` | 规则表达式 |

**关键参数**：
- `n_vars`: 每个组合的变量数（默认3）
- `max_depth`: 决策树最大深度（默认5）
- `min_samples_leaf`: 叶节点最小样本比例（默认0.01）
- `max_onehot_vars`: 每个组合最多One-Hot变量数（默认2）

**规则格式**：`(age <= 25.5) & (income <= 5000.0) & (channel_is_A > 0.5)`

#### 阶段2：规则过滤（合并方向过滤+效果评估）

> **v2.0 更新**：将原 `filtering_rules`（方向过滤）和 `evaluating_rules`（效果评估）合并为单一阶段 `rule_filtering`

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 2.1 | 计算分裂方向 | `RuleMiner.get_split_direction()` | 方向表 |
| 2.2 | 方向一致性过滤 | `RuleMiner.filter_rules()` / `SingleVarRuleMiner.filter_by_direction()` | 方向过滤后规则 |
| 2.3 | 有效性检查 | 排除无效切分点 | 有效规则 |
| 2.4 | 计算recall | 规则命中坏样本/总坏样本 | recall值 |
| 2.5 | 计算bad_rate | 规则命中样本中坏样本占比 | bad_rate值 |
| 2.6 | 计算lift | bad_rate/整体bad_rate | lift值 |
| 2.7 | 计算hit_rate | 规则命中样本/总样本 | hit_rate值 |
| 2.8 | 指标过滤 | `RuleEvaluator.filter_by_metrics()` | 符合条件规则 |

**关键约束**：
- 规则中特征的方向需与分裂方向一致
- 排除切分点为`(-inf, inf]`的无效特征
- 评分类变量可强制指定方向

**关键参数**：
- `max_hit_rate_filter`: 最大命中率阈值（默认0.03）
- `min_lift_filter`: 最小lift阈值（默认3.5）

**评估指标说明**：
| 指标 | 计算公式 | 业务含义 |
|------|----------|----------|
| recall | 规则命中坏样本 / 总坏样本 | 规则对坏样本的召回能力 |
| bad_rate | 规则命中坏样本 / 规则命中样本 | 规则的精准度 |
| lift | bad_rate / 整体bad_rate | 规则的提升倍数 |
| hit_rate | 规则命中样本 / 总样本 | 规则的覆盖范围 |

#### 阶段3：最优规则选择

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 3.1 | 初始化 | 剩余样本集=全部样本 | 初始状态 |
| 3.2 | 选择最优规则 | 选bad_rate最高的规则 | 当前最优规则 |
| 3.3 | 移除命中样本 | 从剩余样本中移除 | 更新样本集 |
| 3.4 | 累计指标计算 | 计算累计recall/hit_rate | 累计指标 |
| 3.5 | 终止判断 | 累计hit_rate > 阈值 或 风险目标达成 | 最优规则集 |

**关键参数**：
- `max_hit_rate_select`: 最大命中率（规则集）阈值（默认0.1）- 业务目标
- `min_recall_ruleset`: 最低召回率（规则集）目标（可选）- 风险目标
- `min_bad_rate_ruleset`: 最低坏账率（规则集）目标（可选）- 风险目标
- `max_bad_rate_ruleset`: 最高坏账率（规则集）目标（可选）- 风险目标（硬约束）
- `min_lift_ruleset`: 最低提升度（规则集）目标（可选）- 风险目标

**贪心算法流程**：
```
1. 初始化：剩余样本集 = 全部样本，已选规则集 = 空
2. 在剩余样本上计算所有规则的bad_rate
3. 选择bad_rate最高的规则加入已选规则集
4. 从剩余样本中移除被该规则命中的样本
5. 检查终止条件：
   - 累计hit_rate > max_hit_rate_select → 达到业务目标上限
   - 累计recall >= min_recall_ruleset → 达到召回目标
   - 累计bad_rate >= min_bad_rate_ruleset → 达到最低坏账率目标
   - 累计bad_rate > max_bad_rate_ruleset → 超过最高坏账率限制（硬约束，停止添加）
   - 累计lift >= min_lift_ruleset → 达到提升度目标
   满足任一条件 → 结束，输出最优规则集
   否则 → 返回步骤2继续迭代
```

#### 阶段4：报告生成

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 4.1 | 生成累计指标曲线数据 | `get_chart_data_for_frontend()` | 图表JSON数据 |
| 4.2 | 生成规则详情表格 | 格式化optimal_rules | 规则表格 |
| 4.3 | 生成效果对比分析 | 计算边际贡献 | 分析报告 |

**输出数据结构**：
```python
chart_data = {
    'cumulative_metrics': {
        'x_axis': [...],  # 规则序号
        'cum_recall': [...],  # 累计召回率
        'cum_hit_rate': [...],  # 累计命中率
        'cum_lift': [...]  # 累计Lift
    },
    'rule_table': [
        {'rule': '...', 'lift': 3.5, 'dev_cum_recall': 0.15, ...},
        ...
    ]
}
```

---

## 三、模块架构设计

### 3.1 类设计概览（已实现）

```python
# rule_mining.py 模块结构

class DataPreprocessor:
    """数据预处理器"""
    def load_name_mapping(mapping_file, key_col, value_col) -> Dict
    def rename_features(df, mapping) -> pd.DataFrame
    def drop_id_columns(df, id_cols) -> Tuple[pd.DataFrame, List[str]]  # 保留但不在preprocess中调用
    def drop_constant_columns(df, exclude_cols) -> Tuple[pd.DataFrame, List[str]]  # 保留但不在preprocess中调用
    def _detect_id_columns(df) -> List[str]  # 新增：只检测不删除
    def _detect_constant_columns(df, exclude_cols) -> List[str]  # 新增：只检测不删除
    def detect_datetime_columns(df, exclude_cols) -> List[str]
    def preprocess_datetime(df, datetime_cols, reference_date, extract_features, exclude_cols) -> Tuple[pd.DataFrame, List[str]]
    def detect_text_columns(df, exclude_cols, min_unique_ratio, min_avg_length) -> List[str]
    def preprocess_text(df, text_cols, extract_features, keywords, exclude_cols) -> Tuple[pd.DataFrame, List[str]]
    def onehot_encode(df, categorical_cols) -> Tuple[pd.DataFrame, List[str]]
    def preprocess(df, target_col, weight_col, do_onehot, do_datetime, do_text, ...) -> Tuple[pd.DataFrame, Dict]
    @staticmethod
    def assess_data_quality(df, target_col, weight_col, ...) -> Dict[str, Any]  # 数据质量自动检测

class FeatureEngineer:
    """特征工程预处理器（可选）"""
    def check_missing(df, exclude_cols) -> pd.DataFrame
    def handle_missing(df, exclude_cols) -> Tuple[pd.DataFrame, List[str]]
    def calculate_iv(df, target_col, weight_col, ...) -> pd.DataFrame
    def filter_by_iv(df, iv_table) -> Tuple[pd.DataFrame, List[str]]
    def onehot_encode(df, categorical_cols) -> Tuple[pd.DataFrame, List[str]]
    def preprocess(df, target_col, weight_col, ...) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]

class SingleVarRuleMiner:
    """单特征规则生成器"""
    def _get_thresholds(series, custom_thresholds) -> List[float]
    def generate_rules(df, feature_cols, target_col, weight_col, ...) -> pd.DataFrame
    def generate_categorical_rules(df, categorical_cols, ...) -> pd.DataFrame
    def filter_by_direction(rule_df, direction_df) -> pd.DataFrame
    def is_binary_feature(col_name, series) -> bool  # 二值特征检测
    def detect_binary_features(df, feature_cols) -> Tuple[List[str], List[str]]  # 特征分类

class RuleMiner:
    """多特征规则生成器（决策树）"""
    def _get_rules_from_tree(df, x_ls, target, weight, ...) -> pd.DataFrame
    def generate_rules(df, feature_cols, target_col, weight_col, ...) -> pd.DataFrame
    def get_split_direction(df, target_col, weight_col, ...) -> pd.DataFrame
    def filter_rules(rule_df, direction_df, score_vars, ...) -> pd.DataFrame

class RuleEvaluator:
    """规则效果评估器"""
    def evaluate_rules(df, rule_df, target_col, weight_col, ...) -> pd.DataFrame
    def filter_by_metrics(rule_info_df, max_hit_rate, min_lift) -> pd.DataFrame
    def calculate_rule_psi(rules_df, df_base, df_compare, ...) -> pd.DataFrame  # 规则PSI计算
    def calculate_rule_psi_by_time(rules_df, df, time_col, ...) -> pd.DataFrame  # 按时间分段PSI

class RuleSelector:
    """最优规则选择器"""
    def select_optimal_rules(df, rule_df, target_col, weight_col, ...) -> pd.DataFrame

class RuleValidator:
    """规则质量验证器"""
    def validate(rules_df, df, target_col, weight_col) -> Dict  # 完整验证
    def _check_coverage(rules_df, df, weight_col) -> Dict  # 覆盖率检测
    def _check_conflicts(rules_df, df) -> Dict  # 冲突检测
    def _check_overlap(rules_df, df) -> Dict  # 重叠度检测
    def _check_redundancy(rules_df, df) -> Dict  # 冗余检测

class RuleInterpreter:
    """规则业务解读器"""
    def interpret(rule, var_name_dict, var_desc_dict) -> str  # 规则转业务文本
    def interpret_batch(rules_df, var_name_dict, var_desc_dict) -> pd.DataFrame  # 批量解读

class RuleMiningPipeline:
    """规则挖掘完整流程编排器"""
    def __init__(mining_mode, id_cols, name_mapping, enable_feature_engineering, ...)
    def load_name_mapping(mapping_file, key_col, value_col) -> Dict
    def run(df, target_col, weight_col, feature_cols, ...) -> Dict[str, Any]
```

### 3.2 Pipeline 配置参数

```python
# RuleMiningPipeline 初始化参数

# 规则挖掘模式
mining_mode: str = 'multi'              # 'single'(单特征) / 'multi'(多特征组合)

# 数据预处理参数
id_cols: List[str] = None               # ID列名列表
drop_cols: List[str] = None             # 额外删除的列
name_mapping: Dict[str, str] = None     # 特征名映射字典
categorical_cols: List[str] = None      # 分类变量列表
datetime_cols: List[str] = None         # 日期时间变量列表（可自动检测）
text_cols: List[str] = None             # 文本变量列表（可自动检测）
datetime_features: List[str] = None     # 日期衍生特征（默认：year, month, dayofweek, hour, days_since）
text_features: List[str] = None         # 文本衍生特征（默认：length, word_count）
text_keywords: Dict[str, List[str]] = None  # 关键词检测字典

# 特征工程参数（可选）
enable_feature_engineering: bool = True  # 是否启用特征工程预处理（推荐启用）
missing_threshold: float = 0.5          # 缺失率阈值
iv_threshold: float = 0.02              # IV值阈值

# 单特征规则参数
n_bins: int = 10                        # 分箱数量
bin_method: str = 'quantile'            # 分箱方式
rule_directions: str = 'both'           # 规则方向

# 多特征规则参数
min_samples_leaf: float = 0.01          # 叶节点最小样本比例
max_depth: int = 5                      # 决策树最大深度
n_vars: int = 3                         # 变量组合数
max_onehot_vars: int = 2                # 每组合最多One-Hot变量数

# 规则过滤参数
max_hit_rate_filter: float = 0.03       # 过滤阶段最大命中率
min_lift_filter: float = 3.5            # 过滤阶段最小lift

# 规则选择参数
max_hit_rate_select: float = 0.1        # 最大命中率（规则集）
onehot_indicator: str = '_is_'          # One-Hot编码标识符
datetime_indicator: str = '_dt_'        # 日期衍生特征标识符
text_indicator: str = '_txt_'           # 文本衍生特征标识符
```

### 3.3 与 scorecard_development.py 的架构对比

| 设计要素 | rule_mining.py | scorecard_development.py |
|----------|----------------|--------------------------|
| **核心类数量** | 6个 | 6个 |
| **Pipeline类** | `RuleMiningPipeline` | `ScorecardPipeline` |
| **配置方式** | 构造函数参数 | `ScorecardConfig` dataclass |
| **进度回调** | `progress_callback` | `progress_callback` |
| **结果返回** | `Dict[str, pd.DataFrame/Dict]` | `Dict[str, Any]` |
| **外部依赖** | sklearn.tree | scorecardpy + statsmodels |
| **模式选择** | `mining_mode`(single/multi) | 无（固定流程） |

---

## 四、WebUI集成方案

> **完整设计文档参考**：
> - 三列式UI布局、任务选项卡、参数面板等详细设计：[SOP_WebUI_Detail_Design.md](./SOP_WebUI_Detail_Design.md)
> - 系统架构、API设计、前端组件等完整集成设计：[SOP_WebUI_Integration_design.md](./SOP_WebUI_Integration_design.md)
>
> 本节仅列出规则挖掘任务的**任务元数据定义**和**SOP Prompt模板**，这是与完整WebUI集成方案对接的核心配置。

### 4.1 与完整WebUI方案的关系

| 设计要素 | 完整方案文档 | 本任务配置 |
|----------|-------------|-----------|
| **三列式UI布局** | `SOP_WebUI_Detail_Design.md` 第二节 | - |
| **左侧任务选项卡** | `SOP_WebUI_Detail_Design.md` 第2.3节 | 提供 `task_id`、`task_name`、`icon` |
| **参数面板内嵌** | `SOP_WebUI_Detail_Design.md` 第2.4节 | 提供 `required_params`、`optional_params` |
| **进度条可视化** | `SOP_WebUI_Detail_Design.md` 第2.4节 | 提供 `stages` 及 `progress_weight` |
| **SOP Registry** | `SOP_WebUI_Integration_design.md` 第3.1节 | 通过 `RULE_MINING_TASK_META` 注册 |
| **API端点** | `SOP_WebUI_Integration_design.md` 第2.2节 | 由统一API层调用 |
| **LLM Prompt注入** | `SOP_WebUI_Detail_Design.md` 第三节 | 提供 `RULE_MINING_SOP_PROMPT_TEMPLATE` |

### 4.2 任务元数据定义

> **实现文件**：`deepanalyze/analysis/task_SOP/rule_mining_meta.py`（✅ 已完成）

```python
# rule_mining_meta.py

RULE_MINING_TASK_META = {
    "task_id": "rule_mining",
    "task_name": "策略规则挖掘",
    "task_name_en": "Rule Mining",
    "description": "基于决策树/阈值分箱的风控策略规则挖掘与效果评估",
    "category": "风控建模",
    "icon": "target",
    "estimated_time": "3-10分钟",
    
    "stages": [
        {"id": "preprocessing", "name": "数据预处理", "progress_weight": 10},
        {"id": "feature_engineering", "name": "特征工程（可选）", "progress_weight": 12},
        {"id": "generating_rules", "name": "规则生成", "progress_weight": 28},
        {"id": "rule_filtering", "name": "规则过滤", "progress_weight": 20},
        {"id": "selecting_rules", "name": "最优选择", "progress_weight": 18},
        {"id": "report_generation", "name": "报告生成", "progress_weight": 12}
    ],
    
    "required_params": [
        {
            "name": "target_col",
            "type": "column_select",
            "label": "目标变量",
            "description": "二分类目标变量（0/1，1表示坏样本）",
            "required": True
        },
        {
            "name": "weight_col",
            "type": "column_select",
            "label": "权重列",
            "description": "样本权重列（可选，无则默认为1）",
            "required": False
        }
    ],
    
    "optional_params": [
        {
            "name": "mining_mode",
            "type": "radio",
            "label": "规则挖掘模式",
            "options": [
                {"value": "single", "label": "🎯 单特征规则（阈值分箱）"},
                {"value": "multi", "label": "🌲 多特征组合规则（决策树）"}
            ],
            "default": "multi",
            "description": "单特征规则简单直观，多特征规则可捕捉交互效应"
        },
        {
            "name": "enable_feature_engineering",
            "type": "checkbox",
            "label": "启用特征工程预处理",
            "default": True,
            "description": "对原始数据进行缺失值处理、IV筛选等预处理（推荐启用，可自动筛选有效特征）"
        },
        {
            "name": "n_bins",
            "type": "number",
            "label": "分箱数量（单特征模式）",
            "default": 10,
            "min": 5,
            "max": 20,
            "show_when": {"mining_mode": "single"}
        },
        {
            "name": "n_vars",
            "type": "number",
            "label": "变量组合数（多特征模式）",
            "default": 3,
            "min": 2,
            "max": 5,
            "show_when": {"mining_mode": "multi"}
        },
        {
            "name": "max_depth",
            "type": "number",
            "label": "决策树深度（多特征模式）",
            "default": 5,
            "min": 2,
            "max": 8,
            "show_when": {"mining_mode": "multi"}
        },
        {
            "name": "min_lift_filter",
            "type": "number",
            "label": "最小Lift阈值",
            "default": 3.5,
            "min": 1.0,
            "max": 10.0,
            "step": 0.5
        },
        {
            "name": "max_hit_rate_filter",
            "type": "number",
            "label": "最大命中率阈值（过滤）",
            "default": 0.03,
            "min": 0.01,
            "max": 0.1,
            "step": 0.01
        },
        {
            "name": "max_hit_rate_select",
            "type": "number",
            "label": "最大命中率（规则集）",
            "default": 0.1,
            "min": 0.05,
            "max": 0.3,
            "step": 0.01
        },
        {
            "name": "min_recall_ruleset",
            "type": "number",
            "label": "最低召回率（规则集）",
            "default": null,
            "min": 0.05,
            "max": 0.8,
            "step": 0.05,
            "optional": true
        },
        {
            "name": "min_bad_rate_ruleset",
            "type": "number",
            "label": "最低坏账率（规则集）",
            "default": null,
            "min": 0.1,
            "max": 0.9,
            "step": 0.05,
            "optional": true
        },
        {
            "name": "min_lift_ruleset",
            "type": "number",
            "label": "最低提升度（规则集）",
            "default": null,
            "min": 1.5,
            "max": 10.0,
            "step": 0.5,
            "optional": true
        }
    ],
    
    "outputs": [
        {"id": "preprocessing_info", "name": "预处理信息", "type": "json"},
        {"id": "iv_table", "name": "IV值表（如启用特征工程）", "type": "table"},
        {"id": "all_rules", "name": "全部候选规则", "type": "table"},
        {"id": "direction_table", "name": "特征分裂方向", "type": "table"},
        {"id": "evaluated_rules", "name": "评估后规则", "type": "table"},
        {"id": "optimal_rules", "name": "最优规则集", "type": "table"},
        {"id": "cumulative_chart", "name": "累计指标曲线", "type": "chart"}
    ]
}
```

### 4.2 LLM Prompt模板（SOP注入）

```markdown
# Role
你是一名资深的银行风控策略专家，精通策略规则挖掘与效果评估。

# Instruction
请使用上传的数据集进行策略规则挖掘，生成最优风控规则集。
必须严格遵守以下标准工作流进行处理，不要跳过任何步骤：

## 阶段0a：数据预处理（必需）
- 如有特征名映射文件，进行特征名映射
- 智能检测非建模列（ID列、时间列、样本类型列、高基数列）并标记排除
- 检测常量列（只有单一值的列）并标记排除
- 对日期时间列进行特征提取（年、月、日、星期、小时、距今天数等）
- 对文本列进行特征提取（长度、词数、关键词匹配等）
- 对分类变量进行One-Hot编码（如不启用特征工程）

## 阶段0b：特征工程预处理（可选，当 enable_feature_engineering=True 时执行）
- 检查缺失值，对缺失率 > {missing_threshold}% 的变量进行剔除
- 计算所有变量的 IV 值
- 剔除 IV < {iv_threshold} 的弱变量
- 对分类变量进行One-Hot编码

## 阶段1：规则生成

### 如果 mining_mode='single'（单特征规则模式）：
- 使用 {bin_method} 分箱方法，将每个数值特征分为 {n_bins} 个区间
- 对每个分箱阈值生成 <= 和 > 两个方向的规则
- 规则格式：`(age <= 25)`, `(income > 50000)`

### 如果 mining_mode='multi'（多特征组合规则模式）：
- 对所有特征进行 {n_vars} 变量组合
- 对每个组合构建决策树（max_depth={max_depth}）
- 从决策树叶节点向上回溯，提取规则路径
- 规则格式：`(age <= 25.5) & (income <= 5000.0) & (channel_is_A > 0.5)`

## 阶段2：规则过滤（方向过滤+效果评估）
- 对每个特征单独构建决策树，确定其"风险方向"
- 过滤方向不一致的规则
- 排除切分点为 (-inf, inf] 的无效特征
- 如有评分类变量，强制指定方向
- 计算每条规则的 recall（召回率）
- 计算每条规则的 bad_rate（坏账率）
- 计算每条规则的 lift（提升倍数）
- 计算每条规则的 hit_rate（命中率）
- 过滤条件：hit_rate < {max_hit_rate_filter} 且 lift > {min_lift_filter}

## 阶段3：最优规则选择
- 使用贪心算法选择最优规则组合
- 每轮选择当前 bad_rate 最高的规则
- 移除被选中规则命中的样本
- 终止条件：累计 hit_rate > {max_hit_rate_select} 或达到风险目标
- 输出最终的最优规则集及累计指标

## 阶段4：报告生成
- 生成规则挖掘结果的可视化报告
- 输出最优规则集的累计指标曲线图（累计召回率、累计命中率、累计Lift）
- 输出规则详情表格（包含 used_var, rule, lift, dev_cum_recall, dev_cum_bad_rate, dev_cum_hit_rate）
- 生成规则效果对比分析（各规则的边际贡献）
- 输出数据格式需符合前端图表组件要求

# Constraints
- 所有步骤必须按顺序执行，不可跳过（阶段0b除外，根据参数决定是否执行）
- 规则必须具有业务可解释性
- 最终规则集的累计命中率不超过 {max_hit_rate_select}
- 输出结果需包含完整的规则表格和累计指标
- 报告生成阶段为必需阶段，用于生成前端展示所需的图表数据

# Data
{workspace_files_info}
```

---

## 五、实施计划

### 5.1 开发任务分解

| 阶段 | 任务 | 预估工时 | 优先级 | 依赖 | 状态 |
|------|------|----------|--------|------|------|
| **Phase 0** | 核心类实现 | 已完成 | P0 | - | ✅ 已完成 |
| 0.1 | `DataPreprocessor` 类 | - | P0 | - | ✅ 已完成 |
| 0.2 | `FeatureEngineer` 类 | - | P0 | - | ✅ 已完成 |
| 0.3 | `SingleVarRuleMiner` 类 | - | P0 | - | ✅ 已完成 |
| 0.4 | `RuleMiner` 类 | - | P0 | - | ✅ 已完成 |
| 0.5 | `RuleEvaluator` 类 | - | P0 | - | ✅ 已完成 |
| 0.6 | `RuleSelector` 类 | - | P0 | - | ✅ 已完成 |
| 0.7 | `RuleMiningPipeline` 类 | - | P0 | - | ✅ 已完成 |
| **Phase 1** | WebUI集成 | 1天 | P1 | Phase 0 | ✅ 已完成 |
| 1.1 | 任务元数据定义 | 0.25天 | P1 | - | ✅ 已完成 |
| 1.2 | SOP Prompt模板 | 0.25天 | P1 | - | ✅ 已完成 |
| 1.3 | SOP Registry注册中心 | 0.25天 | P1 | 1.1 | ✅ 已完成 |
| 1.4 | SOP Executor执行引擎 | 0.25天 | P1 | 1.3 | ✅ 已完成 |
| 1.5 | SOP API端点 | 0.25天 | P1 | 1.4 | ✅ 已完成 |
| 1.6 | 前端参数表单适配 | 0.5天 | P1 | 1.5 | ✅ 已完成 |
| **Phase 2** | 可视化增强 | 0.5天 | P2 | Phase 0 | ✅ 已完成 |
| 2.1 | 累计指标曲线图 | 0.25天 | P2 | - | ✅ 已完成 |
| 2.2 | 规则分布图 | 0.25天 | P2 | - | ✅ 已完成 |
| **Phase 3** | 文档与测试 | 0.5天 | P1 | Phase 0 | ✅ 已完成 |
| 3.1 | 单元测试 | 0.25天 | P1 | Phase 0 | ✅ 已完成 |
| 3.2 | 集成测试 | 0.25天 | P1 | Phase 1 | ✅ 已完成 |

### 5.2 文件结构规划

```
deepanalyze/analysis/task_SOP/
├── __init__.py                    # ✅ 已更新：导出所有类、Registry、Executor
├── rule_mining.py                 # ✅ 已完成：规则挖掘核心模块
├── rule_mining_meta.py            # ✅ 已完成：任务元数据和SOP Prompt
├── rule_mining_viz.py             # ✅ 已完成：可视化模块（累计曲线、规则分布图）
├── registry.py                    # ✅ 已完成：SOP任务注册中心
├── executor.py                    # ✅ 已完成：SOP任务执行引擎
├── scorecard_development.py       # ✅ 已完成：评分卡开发核心模块
├── scorecard_meta.py              # ✅ 已完成：评分卡任务元数据
# SOP工作流文档已迁移至 docs/taskSOP_solution/
# - rule_mining_workflow.md
# - scorecard_dev_workflow.md

demo/chat/
├── lib/
│   └── sopService.ts              # ✅ 已完成：SOP服务层
└── components/sop/
    ├── index.ts                   # ✅ 已完成：组件导出
    ├── TaskSelector.tsx           # ✅ 已完成：任务选择器
    ├── TaskConfigPanel.tsx        # ✅ 已完成：通用参数配置面板（动态渲染）
    ├── TaskProgress.tsx           # ✅ 已完成：任务进度显示
    └── RuleMiningResults.tsx      # ✅ 已完成：结果展示组件

API/
├── sop_api.py                     # ✅ 已完成：SOP任务API端点
└── main.py                        # ✅ 已更新：注册SOP路由

tests/
├── test_rule_mining.py            # ✅ 已完成：规则挖掘单元测试
└── test_sop_api.py                # ✅ 已完成：SOP API集成测试
```

### 5.3 关键风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 组合数爆炸 | 特征过多时规则生成耗时过长 | 限制最大特征数(<100)，支持中断 |
| 规则过拟合 | 规则在验证集上效果差 | 支持验证集评估，输出过拟合警告 |
| 方向判断错误 | 部分特征方向与业务逻辑不符 | 支持手动指定特征方向 |
| 空规则集 | 阈值过严导致无规则输出 | 自动调整阈值，给出建议 |

---

## 六、验收标准

### 6.1 功能验收

- [x] 能够完成端到端的规则挖掘流程
- [x] 支持单特征规则挖掘（阈值分箱）
- [x] 支持多特征组合规则挖掘（决策树）
- [x] 支持数据预处理（特征名映射、智能检测排除列、One-Hot编码）
- [x] 支持日期时间列预处理（自动检测、特征提取）
- [x] 支持文本列预处理（自动检测、特征提取、关键词匹配）
- [x] 支持可选的特征工程预处理（缺失值、IV筛选）
- [x] 能够计算规则效果指标（recall/bad_rate/lift/hit_rate）
- [x] 能够使用贪心算法选择最优规则集
- [x] WebUI能够正确展示进度和结果
- [x] 支持累计指标曲线可视化

### 6.2 性能验收

- [ ] 10万样本 × 50特征（单特征模式），完整流程 < 1分钟
- [ ] 10万样本 × 50特征（多特征模式），完整流程 < 5分钟
- [ ] 内存占用 < 2GB

### 6.3 兼容性验收

- [x] 支持CSV/Excel输入
- [x] 支持中文列名
- [x] 支持缺失值处理
- [x] 支持特征名映射

---

## 七、两种模式对比总结

| 维度 | 🎯 单特征规则模式 | 🌲 多特征组合规则模式 |
|------|-------------------|----------------------|
| **规则格式** | `(age <= 25)` | `(age <= 25) & (income <= 5000)` |
| **生成算法** | 阈值分箱遍历 | 决策树提取 |
| **规则数量** | ~数百条 | ~数万条 |
| **计算时间** | 秒级 | 分钟级 |
| **可解释性** | 强（直观易懂） | 中（需理解组合逻辑） |
| **适用场景** | 初筛规则、单变量策略 | 精细化规则、组合策略 |
| **典型用途** | 快速探索、简单策略 | 复杂模式、交叉特征 |

### 选择建议

- **选择单特征模式**：初次探索数据、需要快速产出、规则需要高度可解释
- **选择多特征模式**：需要更精细的规则、特征存在交互效应、追求更高精度

---

## 八、v6.2 功能升级方案

> **升级日期**：2025-12-19
> **详细方案**：参见 [`DeepAnalyze_upgrade_design.md`](../DeepAnalyze_upgrade_design.md)

### 8.1 新增独立封装类

| 类名 | 文件位置 | 核心能力 |
|------|----------|----------|
| **PriorRuleAnalyzer** | `rule_mining.py` | 先验规则增量贡献分析器 |
| **AmountAnalyzer** | `rule_mining.py` | 金额维度分析器 |
| **ExcelReportGenerator** | `excel_report.py` | 专业Excel报告生成 |

### 8.2 新增参数

| 参数 | 类型 | 说明 |
|------|------|------|
| **prior_rules** | `list[str]` | 先验规则列表，用于计算增量贡献 |
| **amount_col** | `str` | 金额列名，用于金额维度分析 |

### 8.3 阶段5：效果评估（升级）

**先验规则分析输出**：

| 指标 | 说明 |
|------|------|
| **standalone_recall** | 独立召回率 |
| **standalone_hit_rate** | 独立命中率 |
| **incremental_recall** | 增量召回率（在先验规则基础上额外捕获） |
| **incremental_hit_rate** | 增量命中率 |
| **overlap_rate** | 与先验规则重叠率 |
| **marginal_contribution** | 边际贡献 = incremental / standalone |

**金额维度分析输出**：

| 指标 | 说明 |
|------|------|
| **hit_amount** | 命中金额 |
| **hit_amount_pct** | 命中金额占比 |
| **bad_amount** | 坏样本金额 |
| **bad_amount_pct** | 金额召回率 |
| **amount_bad_rate** | 金额坏账率 |
| **amount_lift** | 金额提升度 |
| **avg_amount_per_hit** | 平均命中金额 |

**代码示例**：
```python
# 方式1：使用独立分析器（推荐）
prior_analyzer = PriorRuleAnalyzer(prior_rules=["(age <= 25)", "credit_score <= 550"])
prior_analyzer.fit(df, target_col='target')
prior_results = prior_analyzer.analyze(optimal_rules)

amount_analyzer = AmountAnalyzer(amount_col='loan_amount')
amount_analyzer.fit(df, target_col='target')
amount_results, amount_summary = amount_analyzer.analyze_with_cumulative(optimal_rules)

# 方式2：通过Pipeline自动调用
pipeline = RuleMiningPipeline(...)
results = pipeline.run(
    df=df,
    target_col='target',
    prior_rules=["(age <= 25)", "credit_score <= 550"],
    amount_col='loan_amount'
)
```

### 8.4 阶段6：报告生成（升级）

**Excel报告内容**：

| Sheet名称 | 内容 |
|-----------|------|
| **概览** | 任务参数、数据概况 |
| **最优规则集** | 贪心选出的规则及累计指标 |
| **全部规则** | 所有候选规则评估结果 |
| **先验分析** | 与先验规则对比（如配置） |
| **金额分析** | 金额维度指标（如配置） |

### 8.5 Pipeline输出结构升级

```python
results = {
    # 原有字段
    'all_rules': pd.DataFrame,
    'optimal_rules': pd.DataFrame,
    
    # 🆕 新增字段
    'prior_analysis': {
        'enabled': bool,
        'prior_rules': list[str],
        'results': pd.DataFrame,
        'summary': {'prior_metrics': {...}, ...}
    },
    'amount_analysis': {
        'enabled': bool,
        'amount_col': str,
        'results': pd.DataFrame,
        'summary': {'optimal_rules_amount_recall': float, ...}
    }
}
```

### 8.6 前端组件新增

| 组件 | 功能 |
|------|------|
| **AmountAnalysisPanel** | 金额汇总卡片、规则金额指标表格、金额召回率图表 |

### 8.7 任务元数据更新（已完成）

```python
# rule_mining_meta.py 已更新
"optional_params": [
    ...
    {"name": "prior_rules", "type": "text_list", "label": "先验规则", ...},
    {"name": "amount_col", "type": "column_select", "label": "金额列", ...}
],
"output_sections": [
    ...
    {"id": "prior_analysis", "name": "先验规则分析", "show_when": {"prior_rules": "not_empty"}},
    {"id": "amount_analysis", "name": "金额维度分析", "show_when": {"amount_col": "not_empty"}}
]
```

---

## 九、后续扩展方向

1. **规则可视化**：规则决策路径可视化、规则效果对比图
2. **规则验证**：支持验证集/测试集评估，输出过拟合警告
3. **规则导出**：支持导出为SQL/Python/JSON格式
4. **规则监控**：规则效果监控、规则漂移检测
5. **规则组合优化**：基于遗传算法/强化学习的规则组合优化
6. **自动化报告**：生成Word/PDF格式的规则挖掘报告

---

## 九、参考资料

1. scikit-learn决策树文档：https://scikit-learn.org/stable/modules/tree.html
2. 《风控策略》- 李俊
3. 银保监会《商业银行信用风险管理指引》

---

*文档版本：v1.6*  
*创建日期：2025-12-09*  
*更新日期：2026-01-12*  
*适用模块：deepanalyze/analysis/preprocessing.py, deepanalyze/analysis/task_SOP/rule_mining.py*

---

## 更新日志

### v1.6 (2026-01-12)
- **阶段合并**：将 `filtering_rules`（方向过滤）和 `evaluating_rules`（效果评估）合并为 `rule_filtering` 阶段（7阶段→6阶段）
- **风险目标参数**：在 `selecting_rules` 阶段新增 `min_recall_ruleset`、`min_bad_rate_ruleset`、`max_bad_rate_ruleset`、`min_lift_ruleset` 参数
- **前端实现完成**：`TaskConfigPanel.tsx` + `DynamicParamRenderer.tsx` 已支持风险目标参数的动态渲染（可选开关+滑块）
- 更新工作流全景图、阶段详细说明、元数据定义、LLM Prompt模板
- 更新阶段编号：阶段3→最优规则选择，阶段4→报告生成

### v1.5 (2025-12-19)
- 新增第八节：v6.2功能升级方案
- 添加先验规则评估功能（`evaluate_with_prior`）
- 添加金额维度分析功能（`evaluate_with_amount`）
- 添加`prior_rules`、`amount_col`新参数说明
- 添加Pipeline输出结构升级
- 添加前端AmountAnalysisPanel组件说明
- 添加Excel报告导出功能说明

### v1.4 (2025-12-17)
- 新增数据质量自动检测功能
  - `DataPreprocessor.assess_data_quality()` 静态方法
  - 缺失率/数据类型/基数/方差分析
  - 0-100分质量评分，评分<70或问题≥2时建议启用特征工程
- 更新阶段定义：新增 `report_generation` 报告生成阶段（共7阶段）
- 更新 `enable_feature_engineering` 默认值为 `True`（推荐启用）
- 更新阶段0b执行条件：根据数据质量自动决定或用户指定
- 更新类设计概览：新增 `RuleValidator`、`RuleInterpreter`、PSI计算等方法
- 同步代码实现中的数值类型检测方式（`pd.api.types.is_numeric_dtype`）

### v1.3 (2025-12-15)
- 新增规则质量验证模块 `RuleValidator` 类
  - 覆盖率检测：检查规则集对样本的覆盖情况
  - 冲突检测：识别规则间的逻辑冲突
  - 重叠度检测：计算规则间的Jaccard相似度
  - 冗余检测：识别可被其他规则包含的冗余规则
  - 综合质量评分：0-100分的综合质量指标
- 新增规则稳定性检测（PSI）
  - `RuleEvaluator.calculate_rule_psi()` 方法
  - `RuleEvaluator.calculate_rule_psi_by_time()` 按时间分段计算PSI
  - PSI阈值：<0.1稳定，0.1-0.25轻微变化，≥0.25显著变化
- 新增规则业务解读增强 `RuleInterpreter` 类
  - 规则转业务文本解读
  - 批量规则解读
- 前端增强
  - 分箱方法Tooltip说明
  - ValidationReportPanel 质量验证报告面板
  - PSIReportPanel 稳定性报告面板
- Pipeline集成：自动执行验证和PSI计算
- 更新文件结构：评分卡相关模块已全部完成

### v1.2 (2025-12-10)
- 新增通用数据预处理模块 `preprocessing.py`
- 抽取 `DatetimeProcessor`、`TextProcessor`、`CategoricalProcessor`、`ColumnCleaner` 为独立可复用类
- 新增 `GeneralPreprocessor` 统一预处理接口
- 重构 `DataPreprocessor` 类，委托给通用模块实现
- 更新模块导出，支持从 `deepanalyze.analysis` 直接导入通用预处理类

### v1.1 (2025-12-10)
- 新增日期时间列预处理功能（`preprocess_datetime`）
- 新增文本列预处理功能（`preprocess_text`）
- 新增自动检测日期时间列和文本列功能
- 更新 `DataPreprocessor` 类设计，添加 `datetime_indicator`、`text_indicator` 参数
- 更新 `preprocess()` 方法签名，支持 `do_datetime`、`do_text` 等参数
- 更新工作流全景图，增加日期时间处理和文本特征处理步骤
