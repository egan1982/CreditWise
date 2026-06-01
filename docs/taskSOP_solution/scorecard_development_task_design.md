# 评分卡开发任务SOP构建方案

> **文档目的**：基于项目已有底层能力，结合 `rule_mining.py` 的架构设计，构建评分卡开发场景的业务任务模板方案，供评估后实施。
>
> **架构原则**：✅ **复用 rule_mining 的正确架构模式**——底层工具抽离 + 任务层委托调用，确保架构一致性。

---

## 一、架构设计说明

### 1.0 架构模式对齐 ✅

本模块将严格遵循 `rule_mining.py` 已验证的正确架构模式：

```
┌──────────────────────────────────────────────────────────────┐
│          ✅ 统一的架构分层（对齐 rule_mining）                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📦 底层通用工具（deepanalyze/analysis/）                     │
│  ├── preprocessing.py         ✅ 数据预处理（Rule Mining用）│
│  ├── woe.py                   ✅ WOE/IV计算（已有）         │
│  ├── feature_binning.py       ✅ 分箱工具（已有）           │
│  └── feature_correlation.py   ✅ 已实现（CorrelationAnalyzer/VIFAnalyzer）│
│                                                              │
│  📦 任务SOP层（deepanalyze/analysis/task_SOP/）              │
│  ├── rule_mining.py           ✅ 规则挖掘（架构样板）        │
│  │   ├── DataPreprocessor     ✅ 委托 preprocessing.py     │
│  │   └── FeatureEngineer      ✅ 简化版IV + 委托One-Hot    │
│  └── scorecard_development.py ✅ 已实现                     │
│      ├── DataPreprocessor     ✅ 数据预处理编排             │
│      ├── WOETransformer       ✅ 封装scorecardpy           │
│      └── FeatureSelector      ✅ 委托 feature_correlation  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**关键设计决策**：
1. ✅ **新增底层工具** `feature_correlation.py`（相关性分析、VIF检验）
2. ✅ **任务层委托调用**：`FeatureSelector` 委托给 `CorrelationAnalyzer`/`VIFAnalyzer`
3. ✅ **职责分离**：`FeatureSelector` 只负责流程编排，不包含算法实现
4. ✅ **架构一致性**：与 `rule_mining.py` 的 `DataPreprocessor` 委托模式完全对齐

---

## 二、项目现有能力盘点

### 2.1 已具备的底层模块

| 模块 | 文件位置 | 核心能力 | 评分卡开发适用性 | 架构层级 |
|------|----------|----------|------------------|---------|
| **WOE计算** | `woe.py` | `WOECalculator.calculate_woe()` | ✅ 直接可用 | 🔵 底层工具 |
| **IV分析** | `iv_analysis.py` | `IVAnalyzer.analyze_features()` | ✅ 直接可用 | 🔵 底层工具 |
| **特征分箱** | `feature_binning.py` | `FeatureBinner.auto_bin()` | ✅ 直接可用 | 🔵 底层工具 |
| **数据预处理** | `preprocessing.py` | `DatetimeProcessor`/`TextProcessor` | ✅ 可选使用 | 🔵 底层工具 |
| **相关性分析** | `feature_correlation.py` | `CorrelationAnalyzer`/`VIFAnalyzer` | ✅ 已实现 | 🔵 底层工具 |
| **scorecardpy** | `requirements.txt` | 完整评分卡工具链 | ✅ 直接可用 | 🔵 外部依赖 |
| **统计分析** | `statsmodels` | 逻辑回归、VIF检验 | ✅ 直接可用 | 🔵 外部依赖 |
| **可视化** | `matplotlib/seaborn/plotly` | ROC/KS曲线、分箱图 | ✅ 直接可用 | 🔵 外部依赖 |

### 2.2 scorecardpy 核心功能映射

```python
import scorecardpy as sc

# scorecardpy 提供的关键函数
sc.germancredit()       # 示例数据集
sc.var_filter()         # 变量筛选（缺失率/IV/单一值）
sc.woebin()             # WOE分箱（自动/手动）
sc.woebin_plot()        # 分箱可视化
sc.woebin_adj()         # 分箱调整
sc.woebin_ply()         # WOE转换
sc.scorecard()          # 评分卡生成
sc.scorecard_ply()      # 评分计算
sc.perf_eva()           # 模型评估（KS/AUC/ROC）
sc.perf_psi()           # PSI稳定性评估
```

### 2.3 底层工具与任务层职责划分

**关键架构原则**（复用 rule_mining 模式）：

| 层级 | 职责 | 示例 |
|------|------|------|
| **底层工具层** | 提供纯粹的数据分析能力，不包含业务逻辑 | `CorrelationAnalyzer.calculate_correlation()`<br>`VIFAnalyzer.calculate_vif()` |
| **任务SOP层** | 流程编排，委托调用底层工具 | `FeatureSelector.filter_by_correlation()`<br>→ 委托给 `CorrelationAnalyzer` |

### 2.4 需要新增的能力

| 能力 | 层级 | 实现方式 | 优先级 |
|------|------|---------|--------|
| **相关性分析** | 🔵 底层工具 | 新增 `feature_correlation.py::CorrelationAnalyzer` | 🔴 P0 |
| **VIF检验** | 🔵 底层工具 | 新增 `feature_correlation.py::VIFAnalyzer` | 🔴 P0 |
| **WOE封装** | 🟢 任务层 | 新增 `WOETransformer`（封装scorecardpy） | 🔴 P0 |
| **特征筛选编排** | 🟢 任务层 | 新增 `FeatureSelector`（委托底层工具） | 🟡 P0（依赖上两项） |
| **逻辑回归建模** | 🟢 任务层 | 新增 `ScorecardModeler`（封装sklearn） | 🟡 P1 |
| **评分刻度转换** | 🟢 任务层 | 新增 `ScorecardScaler`（封装scorecardpy） | 🟡 P1 |
| **模型评估** | 🟢 任务层 | 新增 `ModelEvaluator`（封装scorecardpy） | 🟡 P1 |

---

## 三、评分卡开发标准工作流（SOP）

### 3.1 工作流全景图

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                              评分卡开发完整工作流（7阶段）                                     │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ 阶段1   │  │ 阶段2   │  │ 阶段3   │  │ 阶段4   │  │ 阶段5   │  │ 阶段6   │  │ 阶段7   │ │
│  │数据预处理│─▶│特征工程 │─▶│特征筛选 │─▶│模型训练 │─▶│评分转换 │─▶│模型评估 │─▶│报告生成 │ │
│  │         │  │(WOE/IV) │  │         │  │(LR+验证)│  │(Scaling)│  │         │  │         │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │
│       │            │            │            │            │            │            │       │
│       ▼            ▼            ▼            ▼            ▼            ▼            ▼       │
│  缺失值处理    WOE分箱      IV筛选      逐步回归     刻度转换     KS/AUC      图表数据   │
│  异常值检测    IV计算       VIF检验     显著性检验   评分卡表     ROC曲线     可视化渲染 │
│  数据分割      分箱调整     相关性分析  系数方向验证 分数分布     PSI稳定     前端展示   │
│                                          迭代验证                                            │
│                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 各阶段详细说明

#### 阶段1：数据预处理

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 1.1 | 数据加载 | `pd.read_csv()` | DataFrame |
| 1.2 | 缺失值检查 | `df.isnull().sum()/len(df)` | 缺失率报告 |
| 1.3 | 缺失值处理 | 剔除缺失率>50%的变量 | 清洗后数据 |
| 1.4 | 异常值检测 | IQR/3σ原则 | 异常值报告 |
| 1.5 | 数据分割 | `sc.split_df()` 或 sklearn | train/test集 |

**关键参数**：
- `missing_threshold`: 缺失率阈值（默认0.5）
- `test_ratio`: 测试集比例（默认0.3）
- `random_state`: 随机种子（默认42）

#### 阶段2：特征工程（WOE/IV）

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 2.1 | 初步变量筛选 | `sc.var_filter()` | 候选变量列表 |
| 2.2 | WOE分箱 | `sc.woebin()` | 分箱规则 |
| 2.3 | 分箱可视化 | `sc.woebin_plot()` | 分箱图 |
| 2.4 | 分箱调整（可选）| `sc.woebin_adj()` | 调整后分箱 |
| 2.5 | WOE转换 | `sc.woebin_ply()` | WOE编码数据 |
| 2.6 | IV计算 | 从woebin结果提取 | IV值表 |

**关键参数**：
- `iv_limit`: IV筛选阈值（默认0.02）
- `missing_limit`: 缺失率阈值（默认0.95）
- `identical_limit`: 单一值比例阈值（默认0.95）
- `bin_num_limit`: 最大分箱数（默认8）
- `method`: 分箱方法（'tree'/'chimerge'/'quantile'）

#### 阶段3：特征筛选

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 3.1 | IV值筛选 | IV ∈ [0.02, 0.5] | 有效变量列表 |
| 3.2 | 相关性分析 | `df.corr()` | 相关性矩阵 |
| 3.3 | VIF检验 | `statsmodels.stats.outliers_influence.variance_inflation_factor` | VIF值表 |
| 3.4 | 剔除共线性变量 | VIF > 5 剔除 | 最终变量列表 |

**关键参数**：
- `iv_lower`: IV下限（默认0.02）
- `iv_upper`: IV上限（默认0.5，过高可能过拟合）
- `vif_threshold`: VIF阈值（默认5）
- `corr_threshold`: 相关系数阈值（默认0.7）

> **注意**：v4.3起，逐步回归、显著性检验、系数方向验证已迁移至阶段4（模型训练）

#### 阶段4：模型训练（含迭代验证）

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 4.1 | 逐步回归（可选）| 前向/后向/双向选择 | 精简变量集 |
| 4.2 | 逻辑回归建模 | `sklearn.linear_model.LogisticRegression` | LR模型 |
| 4.3 | 系数显著性检验 | p-value < significance_level | 显著变量 |
| 4.4 | 系数方向验证 | 系数符号与业务逻辑一致 | 验证报告 |
| 4.5 | **迭代验证循环** | 不通过则剔除变量重训练 | 最终模型 |

**v4.3+ 迭代验证循环流程**：
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 逐步回归    │────▶│ 逻辑回归    │────▶│ 显著性检验  │
│ (特征选择)  │     │ (建模)      │     │ (p值检验)   │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                    ┌─────────────────────────────────────┐
                    │ 所有变量显著？                        │
                    │ • 是 → 进入系数方向验证              │
                    │ • 否 → 剔除不显著变量，重新建模     │
                    └─────────────────────────────────────┘
                                              │
                                              ▼
                    ┌─────────────────────────────────────┐
                    │ 系数方向验证                         │
                    │ • 通过 → 完成，输出最终模型         │
                    │ • 不通过 → 根据mode处理:            │
                    │   - skip: 警告并继续                 │
                    │   - warn: 记录日志并继续            │
                    │   - remove: 剔除变量，重新建模      │
                    └─────────────────────────────────────┘
```

**关键参数**：
- `use_stepwise`: 是否启用逐步回归（默认True）
- `stepwise_direction`: 逐步回归方向（'forward'/'backward'/'both'，默认'both'）
- `significance_level`: P值显著性阈值（默认0.05）
- `significance_mode`: 显著性检验模式（'skip'/'warn'/'remove'，默认'remove'）
- `coefficient_direction_mode`: 系数方向验证模式（'skip'/'warn'/'remove'，默认'warn'）
- `max_validation_iterations`: 最大迭代次数（默认20，防止无限循环）

**关键约束**：
- **必须使用逻辑回归**（监管合规要求，禁止XGBoost/RandomForest等黑盒模型）
- 所有入模变量系数需显著（p < significance_level）
- 系数方向需符合业务逻辑

#### 阶段5：评分刻度转换

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 5.1 | 设定基准分 | Base Score = 600 @ odds 20:1 | 基准参数 |
| 5.2 | 设定PDO | PDO = 20 (Points to Double Odds) | PDO参数 |
| 5.3 | 生成评分卡 | `sc.scorecard()` | 评分卡表 |
| 5.4 | 计算样本分数 | `sc.scorecard_ply()` | 分数列 |
| 5.5 | 分数分布分析 | 直方图/箱线图 | 分布图 |

**评分转换公式**：
```
Score = Offset + Factor × ln(Odds)

其中：
- Offset = Base_Score - Factor × ln(Base_Odds)
- Factor = PDO / ln(2)
- Base_Score = 600 (基准分)
- Base_Odds = 20:1 (基准Odds)
- PDO = 20 (翻倍分数)
```

#### 阶段6：模型评估

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 6.1 | KS值计算 | `sc.perf_eva()` | KS值 |
| 6.2 | AUC计算 | `sc.perf_eva()` | AUC值 |
| 6.3 | ROC曲线 | `sc.perf_eva()` | ROC图 |
| 6.4 | KS曲线 | `sc.perf_eva()` | KS图 |
| 6.5 | PSI稳定性（可选）| `sc.perf_psi()` | PSI值 |
| 6.6 | 分数分段分析 | 按分数段统计bad_rate | 分段报告 |

**评估标准**：
| 指标 | 优秀 | 良好 | 一般 | 差 |
|------|------|------|------|-----|
| KS | >0.4 | 0.3-0.4 | 0.2-0.3 | <0.2 |
| AUC | >0.8 | 0.7-0.8 | 0.6-0.7 | <0.6 |
| PSI | <0.1 | 0.1-0.2 | 0.2-0.25 | >0.25 |

---

## 四、模块架构设计（✅ 对齐 rule_mining 架构）

### 4.1 架构设计原则

**核心原则**：完全复用 `rule_mining.py` 的成功架构模式

| 设计维度 | rule_mining | scorecard_development | 一致性 |
|---------|-------------|----------------------|--------|
| **底层工具抽离** | ✅ `preprocessing.py` | ✅ `feature_correlation.py` | ✅ 一致 |
| **任务层委托** | ✅ `DataPreprocessor` 委托底层工具 | ✅ `FeatureSelector` 委托底层工具 | ✅ 一致 |
| **职责分离** | ✅ 任务类不包含算法实现 | ✅ 任务类不包含算法实现 | ✅ 一致 |
| **单一职责** | ✅ 每个类只负责一件事 | ✅ 每个类只负责一件事 | ✅ 一致 |

### 4.2 类设计概览

```python
# scorecard_development.py 模块结构

class DataPreprocessor:
    """
    数据预处理器（评分卡专用）
    
    负责评分卡数据的基础清洗和预处理：
    - 缺失值检查和处理
    - 异常值检测（可选）
    - 数据分割（训练集/测试集）
    
    注意：不包含特征工程（WOE/IV），那是 WOETransformer 的职责
    """
    def __init__(missing_threshold=0.5, test_ratio=0.3, random_state=42)
    def check_missing(df) -> pd.DataFrame
    def handle_missing(df, threshold, strategy='drop') -> pd.DataFrame
    def detect_outliers(df, method='iqr') -> Dict
    def split_data(df, target, test_ratio, random_state) -> Tuple[pd.DataFrame, pd.DataFrame]
    def preprocess(df, target) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]

class WOETransformer:
    """
    WOE转换器（封装scorecardpy）
    
    负责WOE分箱和转换的流程编排：
    - 变量初步筛选（缺失率/单一值）
    - WOE自动分箱
    - 分箱调整（可选）
    - WOE转换
    - IV值提取
    
    注意：委托给 scorecardpy，只负责流程编排
    """
    def __init__(iv_limit=0.02, missing_limit=0.95, identical_limit=0.95, 
                 bin_num_limit=8, method='tree')
    def filter_variables(df, target) -> List[str]
    def auto_binning(df, target, features) -> Dict
    def manual_binning(df, target, breaks_list) -> Dict
    def adjust_binning(bins, adjustments) -> Dict
    def transform(df, bins) -> pd.DataFrame
    def get_iv_table(bins) -> pd.DataFrame
    def fit_transform(df, target, features) -> Tuple[pd.DataFrame, Dict, pd.DataFrame]

class FeatureSelector:
    """
    特征筛选器（评分卡专用）
    
    负责特征筛选流程编排，✅ 关键：委托给底层工具
    1. IV值筛选
    2. 相关性过滤（委托给 CorrelationAnalyzer）
    3. VIF检验（委托给 VIFAnalyzer）
    
    注意：v4.3起，逐步回归已迁移至模型训练阶段（ScorecardModeler）
    """
    def __init__(iv_lower=0.02, iv_upper=0.5, vif_threshold=5.0, corr_threshold=0.7):
        self._corr_analyzer = CorrelationAnalyzer()  # ✅ 委托给底层工具
        self._vif_analyzer = VIFAnalyzer()           # ✅ 委托给底层工具
    
    def select_by_iv(iv_table, lower, upper) -> List[str]
    def filter_by_correlation(df, features, threshold) -> Tuple[List[str], pd.DataFrame, List]
        # ✅ 委托给 self._corr_analyzer.filter_by_correlation()
    def filter_by_vif(df, features, threshold) -> Tuple[List[str], pd.DataFrame]
        # ✅ 委托给 self._vif_analyzer.filter_by_vif()
    def select_features(df, iv_table, features, use_correlation=True, use_vif=True) -> Tuple[List[str], Dict]

class ScorecardModeler:
    """评分卡建模器（封装sklearn逻辑回归 + 迭代验证）
    
    v4.3+: 集成逐步回归、显著性检验、系数方向验证的迭代验证循环
    """
    def __init__(significance_level=0.05, significance_mode='remove', 
                 coefficient_direction_mode='warn', max_validation_iterations=10)
    def stepwise_selection(X, y, direction='both') -> List[str]  # v4.3迁移自FeatureSelector
    def fit_logistic(X, y, **kwargs) -> LogisticRegression
    def check_significance(model, X, y) -> pd.DataFrame
    def check_coefficient_direction(model, feature_names, expected_signs=None) -> Dict
    def fit_with_validation(X, y, feature_names) -> Tuple[LogisticRegression, Dict]  # v4.3新增迭代验证

class ScorecardScaler:
    """评分刻度转换器（封装scorecardpy）"""
    def __init__(base_score=600, base_odds=20, pdo=20)
    def generate_scorecard(bins, model, features) -> pd.DataFrame
    def calculate_score(df, scorecard) -> pd.Series
    def analyze_score_distribution(scores, y_true) -> pd.DataFrame

class ModelEvaluator:
    """模型评估器（封装scorecardpy + sklearn）"""
    def calculate_metrics(y_true, y_pred_proba) -> Dict
    def calculate_ks(y_true, y_pred_proba) -> float
    def calculate_auc(y_true, y_pred_proba) -> float
    def plot_roc(y_true, y_pred_proba, title) -> Figure
    def plot_ks(y_true, y_pred_proba, title) -> Figure
    def calculate_psi(expected_scores, actual_scores, bins=10) -> float
    def evaluate_comprehensive(df_train, df_test, model, scorecard) -> Dict

class ScorecardPipeline:
    """评分卡开发完整流程编排器"""
    def __init__(config: ScorecardConfig)
    def run(df, target, feature_cols=None, progress_callback=None) -> Dict[str, Any]
    def generate_report(results) -> str
```

### 4.3 关键架构对比

**FeatureSelector 的委托模式**（✅ 复用 rule_mining 模式）：

```python
# ✅ 正确的架构：rule_mining 的 DataPreprocessor
class DataPreprocessor:  # rule_mining.py
    def __init__(self, ...):
        self._datetime_processor = DatetimeProcessor(...)  # 委托给底层工具
        self._text_processor = TextProcessor(...)          # 委托给底层工具
    
    def preprocess(self, df, ...):
        # 只负责流程编排，不包含算法实现
        df, _ = self._datetime_processor.process(df, ...)
        df, _ = self._text_processor.process(df, ...)
        ...

# ✅ 正确的架构：scorecard 的 FeatureSelector（对齐上述模式）
class FeatureSelector:  # scorecard_development.py
    def __init__(self, ...):
        self._corr_analyzer = CorrelationAnalyzer()  # 委托给底层工具
        self._vif_analyzer = VIFAnalyzer()           # 委托给底层工具
    
    def select_features(self, df, ...):
        # 只负责流程编排，不包含算法实现
        selected, _, _ = self._corr_analyzer.filter_by_correlation(df, ...)
        selected, _ = self._vif_analyzer.filter_by_vif(df, ...)
        ...
```

### 4.4 Pipeline 配置类

```python
@dataclass
class ScorecardConfig:
    """评分卡开发配置"""
    # 数据预处理
    missing_threshold: float = 0.5
    test_ratio: float = 0.3
    random_state: int = 42
    
    # WOE分箱
    iv_limit: float = 0.02
    missing_limit: float = 0.95
    identical_limit: float = 0.95
    bin_num_limit: int = 8
    binning_method: str = 'tree'  # 'tree', 'chimerge', 'quantile'
    
    # 特征筛选
    iv_lower: float = 0.02
    iv_upper: float = 0.5
    vif_threshold: float = 5.0
    corr_threshold: float = 0.7
    
    # 模型训练（v4.3+ 逐步回归和验证参数迁移至此）
    use_stepwise: bool = True
    stepwise_direction: str = 'both'  # 'forward', 'backward', 'both'
    significance_level: float = 0.05
    significance_mode: str = 'remove'  # 🆕 v4.3: 'skip', 'warn', 'remove'
    coefficient_direction_mode: str = 'warn'  # 🆕 v4.3: 'skip', 'warn', 'remove'
    max_validation_iterations: int = 20  # 🆕 v4.3: 最大迭代次数
    
    # 评分转换
    base_score: int = 600
    base_odds: int = 20
    pdo: int = 20
```

### 4.5 与 rule_mining.py 的架构对比

| 设计要素 | rule_mining.py | scorecard_development.py | 架构一致性 |
|----------|----------------|--------------------------|-----------|
| **底层工具抽离** | ✅ `preprocessing.py` | ✅ `feature_correlation.py` | ✅ 完全一致 |
| **任务层委托** | ✅ `DataPreprocessor` 委托底层工具 | ✅ `FeatureSelector` 委托底层工具 | ✅ 完全一致 |
| **核心类数量** | 7个（含Pipeline） | 7个（含Pipeline） | ✅ 一致 |
| **Pipeline类** | `RuleMiningPipeline` | `ScorecardPipeline` | ✅ 命名规范一致 |
| **配置方式** | 构造函数参数 | `ScorecardConfig` dataclass | 略有差异 |
| **进度回调** | `progress_callback` | `progress_callback` | ✅ 一致 |
| **结果返回** | `Dict[str, Any]` | `Dict[str, Any]` | ✅ 一致 |
| **外部依赖** | sklearn.tree | scorecardpy + statsmodels | 依赖不同 |

---

## 五、WebUI集成方案

> **完整设计文档参考**：
> - 三列式UI布局、任务选项卡、参数面板等详细设计：[SOP_WebUI_Detail_Design.md](./SOP_WebUI_Detail_Design.md)
> - 系统架构、API设计、前端组件等完整集成设计：[SOP_WebUI_Integration_design.md](./SOP_WebUI_Integration_design.md)
>
> 本节仅列出评分卡开发任务的**任务元数据定义**和**SOP Prompt模板**，这是与完整WebUI集成方案对接的核心配置。

### 5.1 与完整WebUI方案的关系

| 设计要素 | 完整方案文档 | 本任务配置 |
|----------|-------------|-----------|
| **三列式UI布局** | `SOP_WebUI_Detail_Design.md` 第二节 | - |
| **左侧任务选项卡** | `SOP_WebUI_Detail_Design.md` 第2.3节 | 提供 `task_id`、`task_name`、`icon` |
| **参数面板内嵌** | `SOP_WebUI_Detail_Design.md` 第2.4节 | 提供 `required_params`、`optional_params` |
| **进度条可视化** | `SOP_WebUI_Detail_Design.md` 第2.4节 | 提供 `stages` 及 `progress_weight` |
| **SOP Registry** | `SOP_WebUI_Integration_design.md` 第3.1节 | 通过 `SCORECARD_TASK_META` 注册 |
| **API端点** | `SOP_WebUI_Integration_design.md` 第2.2节 | 由统一API层调用 |
| **LLM Prompt注入** | `SOP_WebUI_Detail_Design.md` 第三节 | 提供 SOP Prompt 模板 |

### 5.2 任务元数据定义

> **实现文件**：`deepanalyze/analysis/task_SOP/scorecard_meta.py`（✅ 已实现）

```python
# scorecard_meta.py

SCORECARD_TASK_META = {
    "task_id": "scorecard_development",
    "task_name": "评分卡开发",
    "task_name_en": "Scorecard Development",
    "description": "基于WOE/IV方法的标准信用评分卡开发流程",
    "category": "风控建模",
    "icon": "credit-card",
    "estimated_time": "5-15分钟",
    
    "stages": [
        {"id": "data_loading", "name": "数据加载", "progress_weight": 8},
        {"id": "woe_binning", "name": "WOE分箱", "progress_weight": 22},
        {"id": "feature_selection", "name": "特征筛选", "progress_weight": 13},
        {"id": "model_training", "name": "模型训练", "progress_weight": 18},
        {"id": "score_scaling", "name": "评分转换", "progress_weight": 12},
        {"id": "model_evaluation", "name": "模型评估", "progress_weight": 15},
        {"id": "report_generation", "name": "报告生成", "progress_weight": 12}
    ],
    
    "required_params": [
        {
            "name": "target_col",
            "type": "column_select",
            "label": "目标变量",
            "description": "二分类目标变量（0/1）",
            "required": True
        },
        {
            "name": "feature_cols",
            "type": "column_multi_select",
            "label": "特征变量",
            "description": "用于建模的特征列（留空则自动选择数值列）",
            "required": False
        }
    ],
    
    "optional_params": [
        {
            "name": "base_score",
            "type": "number",
            "label": "基准分",
            "default": 600,
            "min": 300,
            "max": 1000
        },
        {
            "name": "pdo",
            "type": "number",
            "label": "PDO（翻倍分数）",
            "default": 20,
            "min": 10,
            "max": 50
        },
        {
            "name": "iv_lower",
            "type": "number",
            "label": "IV下限",
            "default": 0.02,
            "min": 0,
            "max": 0.1,
            "step": 0.01
        },
        {
            "name": "vif_threshold",
            "type": "number",
            "label": "VIF阈值",
            "default": 5,
            "min": 2,
            "max": 10
        }
    ],
    
    "outputs": [
        {"id": "iv_table", "name": "IV值表", "type": "table"},
        {"id": "woe_bins", "name": "WOE分箱规则", "type": "json"},
        {"id": "scorecard", "name": "评分卡", "type": "table"},
        {"id": "model_metrics", "name": "模型指标", "type": "metrics"},
        {"id": "roc_curve", "name": "ROC曲线", "type": "chart"},
        {"id": "ks_curve", "name": "KS曲线", "type": "chart"},
        {"id": "score_distribution", "name": "分数分布", "type": "chart"},
        {"id": "chart_data", "name": "前端图表数据", "type": "chart_data"}
    ]
}
```

### 5.3 LLM Prompt模板（SOP注入）

```markdown
# Role
你是一名资深的银行风控建模专家，精通信用评分卡开发。

# Instruction
请使用上传的数据集构建一张标准的信用评分卡（Credit Scorecard）。
必须严格遵守以下标准工作流进行处理，不要跳过任何步骤：

## 阶段1：数据清洗与预处理
- 检查缺失值，对缺失率 > {missing_threshold}% 的变量进行剔除
- 检查异常值，使用IQR方法识别
- 将数据分割为训练集和测试集（比例 {test_ratio}）

## 阶段2：特征工程（核心步骤）
- 必须使用 **Weight of Evidence (WOE)** 方法对所有连续变量和分类变量进行转换
- 使用 {binning_method} 分箱方法进行处理
- 必须计算每个变量的 **Information Value (IV)**
- 生成WOE分箱可视化图

## 阶段3：特征筛选
- 仅保留 IV 值在 [{iv_lower}, {iv_upper}] 之间的变量
- 检查变量间的多重共线性（VIF），剔除 VIF > {vif_threshold} 的变量
- 检查变量间相关性，剔除相关系数 > {corr_threshold} 的冗余变量

## 阶段4：模型训练
- 使用 **逻辑回归 (Logistic Regression)** 算法（监管要求的解释性模型，禁止使用XGBoost/RandomForest）
- 使用逐步回归（Stepwise）进行特征选择（方向：{stepwise_direction}）
- 检验所有系数的显著性（p < {significance_level}）
- 验证系数方向与业务逻辑一致

## 阶段5：评分刻度转换（Scaling）
- 设定 Base Score = {base_score} points at odds {base_odds}:1
- 设定 PDO (Points to Double the Odds) = {pdo}
- 输出最终的评分卡刻度表

## 阶段6：模型评估
- 绘制 ROC 曲线，计算 AUC 值
- 计算 KS 值 (Kolmogorov-Smirnov)，绘制 KS 曲线
- 分析分数分布，按分数段统计bad_rate

# Constraints
- 所有步骤必须按顺序执行，不可跳过
- 必须使用逻辑回归，禁止使用其他算法
- 所有入模变量必须通过显著性检验
- 输出结果需包含完整的评分卡表格

# Data
{workspace_files_info}
```

---

## 六、实施计划

### 6.1 开发任务分解（✅ 全部完成）

| 阶段 | 任务 | 预估工时 | 优先级 | 依赖 | 状态 |
|------|------|----------|--------|------|------|
| **Phase 0** | 底层工具开发 | 1天 | 🔴 P0 | - | ✅ 已完成 |
| 0.1 | `feature_correlation.py` - `CorrelationAnalyzer` | 0.5天 | 🔴 P0 | - | ✅ 已完成 |
| 0.2 | `feature_correlation.py` - `VIFAnalyzer` | 0.5天 | 🔴 P0 | - | ✅ 已完成 |
| **Phase 1** | 任务层核心类 | 2天 | 🔴 P0 | Phase 0 | ✅ 已完成 |
| 1.1 | `DataPreprocessor` 类 | 0.5天 | 🔴 P0 | - | ✅ 已完成 |
| 1.2 | `WOETransformer` 类（封装scorecardpy） | 0.5天 | 🔴 P0 | - | ✅ 已完成 |
| 1.3 | `FeatureSelector` 类 | 0.5天 | 🟡 P0 | Phase 0 | ✅ 已完成 |
| 1.4 | 建模与评分功能（内联到Pipeline） | 0.5天 | 🟡 P1 | - | ✅ 已完成 |
| **Phase 2** | Pipeline与评估 | 1天 | 🟡 P1 | Phase 1 | ✅ 已完成 |
| 2.1 | 模型评估功能（内联到Pipeline） | 0.5天 | 🟡 P1 | - | ✅ 已完成 |
| 2.2 | `ScorecardPipeline` 流程编排 | 0.5天 | 🟡 P1 | 1.1-2.1 | ✅ 已完成 |
| **Phase 3** | WebUI集成 | 1天 | 🟡 P1 | Phase 2 | ✅ 已完成 |
| 3.1 | 任务元数据定义 | 0.25天 | 🟡 P1 | - | ✅ 已完成 |
| 3.2 | SOP Prompt模板 | 0.25天 | 🟡 P1 | - | ✅ 已完成 |
| 3.3 | 前端参数表单适配 | 0.5天 | 🟡 P1 | 3.1 | ✅ 已完成 |
| **Phase 4** | 文档与测试 | 1天 | 🟡 P1 | Phase 2 | ✅ 已完成 |
| 4.1 | SOP工作流文档 | 0.5天 | 🟡 P1 | - | ✅ 已完成 |
| 4.2 | 单元测试 | 0.5天 | 🟡 P1 | Phase 2 | ✅ 已完成 |

**架构实现说明**：
- 原设计中的 `ScorecardModeler`、`ScorecardScaler`、`ModelEvaluator` 三个独立类的功能已**内联整合到 `ScorecardPipeline` 中**
- 这种设计简化了类结构，减少了模块间的耦合
- 核心功能通过 `scorecardpy` 库的 `sc.scorecard()` 和 `sc.scorecard_ply()` 实现
- 逻辑回归建模使用 `sklearn.linear_model.LogisticRegression`

### 6.2 文件结构规划（✅ 全部完成）

```
deepanalyze/analysis/
├── preprocessing.py               # ✅ 已完成：通用数据预处理
├── feature_correlation.py         # ✅ 已完成：相关性分析、VIF检验
├── woe.py                        # ✅ 已完成：WOE计算
├── iv_analysis.py                # ✅ 已完成：IV分析
├── feature_binning.py            # ✅ 已完成：特征分箱
└── task_SOP/
    ├── __init__.py               # ✅ 已完成：模块导出
    ├── registry.py               # ✅ 已完成：SOP任务注册中心
    ├── executor.py               # ✅ 已完成：SOP任务执行引擎
    ├── llm_sop_executor.py       # ✅ 已完成：LLM SOP执行器
    ├── rule_mining.py            # ✅ 已完成：规则挖掘核心模块
    ├── rule_mining_meta.py       # ✅ 已完成：规则挖掘任务元数据
    ├── rule_mining_viz.py        # ✅ 已完成：规则挖掘可视化模块
    ├── scorecard_development.py  # ✅ 已完成：评分卡开发核心模块
    ├── scorecard_meta.py         # ✅ 已完成：评分卡任务元数据
    ├── scorecard_viz.py          # ✅ 已完成：评分卡可视化模块
    ├── expert_mode/              # ✅ 已完成：专家模式模块
    │   ├── __init__.py
    │   ├── stage_state_machine.py
    │   ├── stage_result_store.py
    │   └── expert_executor.py
    # SOP工作流文档已迁移至 docs/taskSOP_solution/
    # - rule_mining_workflow.md
    # - scorecard_dev_workflow.md

demo/chat/
├── lib/
│   ├── config.ts                 # ✅ 已完成：API配置
│   └── sopService.ts             # ✅ 已完成：SOP服务层
└── components/sop/
    ├── index.ts                  # ✅ 已完成：组件导出
    ├── TaskSelector.tsx          # ✅ 已完成：任务选择器
    ├── TaskConfigPanel.tsx       # ✅ 已完成：通用配置面板（动态渲染，替代旧的静态配置面板）
    ├── DynamicParamRenderer.tsx  # ✅ 已完成：动态参数渲染器
    ├── ModeSelector.tsx          # ✅ 已完成：模式选择器
    ├── TaskProgress.tsx          # ✅ 已完成：任务进度显示
    ├── SopStageController.tsx    # ✅ 已完成：阶段卡片+控制面板（原PipelineStageCards）
    ├── ExecutionLogPanel.tsx     # ✅ 已完成：执行日志面板
    ├── StageCodePreview.tsx      # ✅ 已完成：阶段代码预览
    ├── StageOutputPreview.tsx    # ✅ 已完成：阶段输出预览（集成参数/代码编辑、重试）
    ├── RuleMiningResults.tsx     # ✅ 已完成：规则挖掘结果展示
    ├── ScorecardResults.tsx      # ✅ 已完成：评分卡结果展示
    ├── TaskHistoryList.tsx       # ✅ 已完成：任务历史列表
    └── TaskGuideDialog.tsx       # ✅ 已完成：任务指引对话框

API/
├── sop_api.py                    # ✅ 已完成：SOP任务API端点
└── main.py                       # ✅ 已完成：注册SOP路由

deepanalyze/core/task_manager/
├── __init__.py                   # ✅ 已完成：模块导出
├── enums.py                      # ✅ 已完成：枚举类型定义
├── models.py                     # ✅ 已完成：ORM数据库模型
├── database.py                   # ✅ 已完成：数据库管理
├── controller.py                 # ✅ 已完成：任务控制器
├── history_service.py            # ✅ 已完成：历史记录服务
├── result_storage.py             # ✅ 已完成：结果存储
└── checkpoint.py                 # ✅ 已完成：检查点机制
```

**架构说明**：
- 🔵 **底层工具** (`preprocessing.py`, `feature_correlation.py`, `woe.py`, ...)`：独立可复用
- 🟢 **任务SOP层** (`rule_mining.py`, `scorecard_development.py`)：委托调用底层工具
- 🟣 **可视化模块** (`rule_mining_viz.py`, `scorecard_viz.py`)：提供`get_chart_data_for_frontend()`函数

### 6.4 关键风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| scorecardpy API变更 | 分箱/评分函数调用失败 | 封装适配层，版本锁定 |
| 逐步回归性能问题 | 大量变量时耗时过长 | 设置最大迭代次数，支持中断 |
| WOE分箱失败 | 某些变量无法分箱 | 异常处理，跳过并记录 |
| 系数方向异常 | 模型解释性问题 | 自动检测并告警，支持手动调整 |

---

## 七、验收标准

### 7.1 功能验收

- [x] 能够完成端到端的评分卡开发流程
- [x] 支持自动WOE分箱和手动调整
- [x] 支持IV筛选、VIF检验、相关性分析
- [x] 支持逻辑回归建模和逐步回归
- [x] 能够生成标准格式的评分卡表
- [x] 能够计算KS、AUC并绘制曲线
- [x] WebUI能够正确展示进度和结果
- [x] Pipeline包含独立的report_generation阶段
- [x] 可视化模块提供get_chart_data_for_frontend函数

### 7.2 性能验收

- [ ] 10万样本 × 100特征，完整流程 < 5分钟
- [ ] 内存占用 < 2GB

### 7.3 兼容性验收

- [x] 支持CSV/Excel输入
- [x] 支持中文列名
- [x] 支持缺失值处理
- [x] 兼容scorecardpy 0.1.9.7

### 7.4 架构验收 ✅

- [x] `FeatureSelector` 正确委托给 `CorrelationAnalyzer` 和 `VIFAnalyzer`
- [x] 底层工具 `feature_correlation.py` 可独立使用（不依赖任务层）
- [x] 架构与 `rule_mining.py` 保持一致
- [x] 所有任务类不包含数据分析算法实现
- [x] 两个任务的stages都包含report_generation阶段
- [x] 两个任务的meta定义progress_weight总和为100
- [x] 两个任务都有独立的可视化模块（*_viz.py）

---

## 八、v4.2 功能升级方案

> **升级日期**：2025-12-19
> **详细方案**：参见 [`DeepAnalyze_upgrade_design.md`](../DeepAnalyze_upgrade_design.md)

### 8.1 新增底层模块

| 模块 | 文件位置 | 核心能力 |
|------|----------|----------|
| **StatisticalLogisticRegression** | `analysis/statistical_model.py` | 统计检验逻辑回归（p值/z值/标准误/置信区间） |
| **ScoreTransformer** | `analysis/score_transformer.py` | 评分↔概率双向转换 |
| **ExcelReportGenerator** | `analysis/excel_report.py` | 专业Excel报告生成 |

### 8.2 阶段功能升级

#### 阶段4：模型训练（升级）

**新增输出**：

| 指标 | 说明 |
|------|------|
| **std_err** | 系数标准误差 |
| **z_stat** | Wald z统计量 |
| **p_value** | 显著性p值 |
| **ci_lower/ci_upper** | 95%置信区间 |
| **pseudo_r2** | McFadden伪R² |
| **aic/bic** | 信息准则 |

**代码示例**：
```python
from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression

model = StatisticalLogisticRegression(calculate_stats=True)
model.fit(X_train_woe, y_train)
stats = model.summary()
# stats['summary']: DataFrame with coef, std_err, z_stat, p_value, ci_lower, ci_upper
# stats['model_info']: dict with pseudo_r2, log_likelihood, aic, bic
```

#### 阶段5：评分转换（升级）

**新增功能**：评分↔概率双向转换

| 方向 | 方法 | 场景 |
|------|------|------|
| 概率→评分 | `transform()` | 模型输出转评分 |
| 评分→概率 | `inverse_transform()` | 评分校准/风险量化 |

**代码示例**：
```python
from deepanalyze.analysis.score_transformer import ScoreTransformer

transformer = ScoreTransformer(base_score=660, pdo=75, bad_rate=0.15)
transformer.fit()

# 概率转评分
scores = transformer.transform([0.05, 0.10, 0.15])  # [753, 710, 660]

# 评分转概率
probs = transformer.inverse_transform([600, 650, 700])  # [0.21, 0.16, 0.11]
```

#### 阶段7：报告生成（升级）

**新增功能**：Excel报告导出

| Sheet名称 | 内容 |
|-----------|------|
| **概览** | 任务参数、数据概况 |
| **分箱详情** | WOE分箱表、IV值 |
| **评分卡** | 完整评分卡表 |
| **统计检验** | 系数统计信息 |
| **模型评估** | KS/AUC/PSI指标 |

### 8.3 Pipeline输出结构升级

```python
results = {
    # 原有字段
    'preprocessing': {...},
    'woe_binning': {...},
    'scorecard': scorecard_df,
    'evaluation': {...},
    
    # 🆕 新增字段
    'model_statistics': {
        'summary': pd.DataFrame,  # 系数统计表
        'model_info': {'pseudo_r2': float, 'aic': float, 'bic': float, ...}
    },
    'score_transformer': {
        'A': float, 'B': float, 'base_odds': float, ...
    }
}
```

### 8.4 前端组件新增

| 组件 | 功能 |
|------|------|
| **ModelStatisticsPanel** | 系数统计表、p值显著性标记、模型拟合统计 |
| **ScoreConverter** | 评分↔概率交互式转换工具 |

### 8.5 优化项实施状态（已全部完成 ✅）

| 项目 | 优先级 | 状态 | 说明 |
|------|--------|------|------|
| ScorecardModeler集成StatisticalLR | 🔴 P0 | ✅ 已完成 | 新增`ScorecardModeler`类 |
| ScorecardScaler集成ScoreTransformer | 🔴 P0 | ✅ 已完成 | 新增`ScorecardScaler`类 |
| 评分转换API | 🟡 P1 | ✅ 已完成 | `/sop/score/convert`端点已实现 |
| Excel报告导出API | 🟡 P1 | ✅ 已完成 | `/sop/report/export`端点已实现 |

---

## 九、后续扩展方向

1. **拒绝推断（Reject Inference）**：处理被拒绝样本的标签缺失问题
2. **模型监控**：PSI稳定性监控、特征漂移检测
3. **A卡/B卡/C卡**：申请评分卡、行为评分卡、催收评分卡
4. **评分卡组合**：多张评分卡的融合策略
5. **自动化报告**：生成Word/PDF格式的建模报告

---

## 九、参考资料

1. scorecardpy官方文档：https://github.com/ShichenXie/scorecardpy
2. 《信用风险评分卡研究》- Naeem Siddiqi
3. 银保监会《商业银行信用风险内部评级体系监管指引》

---

## 十、更新日志

### v1.4 (2026-02-04)
- **方案1迁移**：逐步回归、显著性检验、系数方向验证从特征筛选阶段迁移至模型训练阶段
- **方案B+新增**：迭代验证循环机制
- 新增参数：`significance_mode`、`coefficient_direction_mode`、`max_validation_iterations`
- 更新工作流全景图，阶段4新增"迭代验证"
- 更新阶段3（特征筛选）删除逐步回归相关内容
- 更新阶段4（模型训练）添加完整迭代验证流程
- 更新`FeatureSelector`类，删除`stepwise_selection`方法
- 更新`ScorecardModeler`类，新增`stepwise_selection`和`fit_with_validation`方法
- 更新`ScorecardConfig`配置类，添加验证模式参数

### v1.3 (2025-12-19)
- 新增第八节：v4.2功能升级方案
- 添加StatisticalLogisticRegression、ScoreTransformer、ExcelReportGenerator模块说明
- 添加阶段4/5/7升级内容
- 添加Pipeline输出结构升级
- 添加前端新组件说明
- 优化项已全部实施完成（ScorecardModeler、ScorecardScaler、API端点）

### v1.2 (2025-12-15)
- 更新所有开发任务状态为已完成
- 更新文件结构规划，反映完整的项目结构
- 添加架构实现说明：`ScorecardModeler`、`ScorecardScaler`、`ModelEvaluator` 功能已内联到 `ScorecardPipeline`
- 新增 Task Management Module 文件结构
- 新增 Expert Mode 模块文件结构
- 新增前端组件完整列表

### v1.1 (2025-12-10)
- 初始版本
- 定义评分卡开发标准工作流
- 设计模块架构（对齐 rule_mining.py）
- 规划 WebUI 集成方案

---

*文档版本：v1.4*  
*创建日期：2025-12-09*  
*更新日期：2026-02-04*  
*适用模块：deepanalyze/analysis/task_SOP/scorecard_development.py*
