# DeepAnalyze 功能升级设计文档

> **文档版本**：v4.2（融合版）  
> **创建日期**：2025-12-15  
> **更新日期**：2025-12-22  
> **参考项目**：[scorecardpipeline](https://github.com/itlubber/scorecardpipeline)  
> **适用模块**：`scorecard_development.py`, `rule_mining.py`

---

## 一、升级功能概览

### 1.1 新增底层模块

| 模块 | 文件位置 | 核心能力 | 适用任务 |
|------|----------|----------|----------|
| **StatisticalLogisticRegression** | `analysis/statistical_model.py` | 统计检验逻辑回归（p值/z值/标准误/置信区间） | 评分卡开发 |
| **ScoreTransformer** | `analysis/score_transformer.py` | 评分↔概率双向转换 | 评分卡开发 |
| **ExcelReportGenerator** | `analysis/excel_report.py` | 专业Excel报告生成 | 评分卡/规则挖掘 |

### 1.2 新增任务层功能

| 功能 | 所属模块 | 核心能力 | 适用任务 |
|------|----------|----------|----------|
| **evaluate_with_prior** | `rule_mining.py::RuleEvaluator` | 先验规则增量贡献分析 | 规则挖掘 |
| **evaluate_with_amount** | `rule_mining.py::RuleEvaluator` | 金额维度效果评估 | 规则挖掘 |
| **prior_rules参数** | `rule_mining_meta.py` | 先验规则列表配置 | 规则挖掘 |
| **amount_col参数** | `rule_mining_meta.py` | 金额列配置 | 规则挖掘 |

### 1.3 文件改动清单

#### 后端新增文件

| 文件 | 功能 |
|------|------|
| `deepanalyze/analysis/statistical_model.py` | 统计信息逻辑回归 |
| `deepanalyze/analysis/score_transformer.py` | 评分刻度转换器 |
| `deepanalyze/analysis/excel_report.py` | Excel报告生成器 |

#### 后端修改文件

| 文件 | 改动内容 |
|------|----------|
| `scorecard_development.py` | 引入StatisticalLogisticRegression，返回model_statistics、score_scale |
| `rule_mining.py` | RuleEvaluator新增evaluate_with_prior()、evaluate_with_amount() |
| `rule_mining_meta.py` | 参数定义增加prior_rules、amount_col |
| `API/sop_api.py` | 新增/sop/score/convert端点，修改ReportExportRequest |

#### 前端新增文件

| 文件 | 功能 |
|------|------|
| `components/sop/ModelStatisticsPanel.tsx` | 模型统计展示 |
| `components/sop/ScoreConverter.tsx` | 评分转换器 |
| `components/sop/AmountAnalysisPanel.tsx` | 金额分析展示 |
| `components/sop/ExportConfigDialog.tsx` | 导出配置对话框 |

#### 前端修改文件

| 文件 | 改动内容 |
|------|----------|
| `ScorecardResults.tsx` | 新增模型统计Tab、评分转换器、修改导出按钮 |
| `RuleMiningResults.tsx` | 新增金额分析Tab、表格增加增量指标列 |
| `TaskConfigPanel.tsx` | 规则挖掘参数增加prior_rules、amount_col |
| `lib/sopService.ts` | 新增convertScore()方法 |

---

## 二、评分卡开发任务升级方案

### 2.1 架构层级更新

```
┌──────────────────────────────────────────────────────────────┐
│          评分卡开发架构（v4.2 升级后）                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📦 底层通用工具（deepanalyze/analysis/）                     │
│  ├── woe.py                   ✅ WOE/IV计算                 │
│  ├── feature_binning.py       ✅ 分箱工具                   │
│  ├── feature_correlation.py   ✅ 相关性分析/VIF检验         │
│  ├── statistical_model.py     🆕 统计信息逻辑回归           │
│  ├── score_transformer.py     🆕 评分刻度转换器             │
│  └── excel_report.py          🆕 Excel报告生成器            │
│                                                              │
│  📦 任务SOP层（deepanalyze/analysis/task_SOP/）              │
│  └── scorecard_development.py                                │
│      ├── DataPreprocessor     ✅ 数据预处理                 │
│      ├── WOETransformer       ✅ WOE分箱转换                │
│      ├── FeatureSelector      ✅ 特征筛选（委托底层工具）    │
│      ├── ScorecardModeler     ✅ 集成StatisticalLR          │
│      ├── ScorecardScaler      ✅ 集成ScoreTransformer       │
│      ├── ModelEvaluator       ✅ 模型评估                   │
│      └── ScorecardPipeline    ✅ 支持Excel报告              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 阶段功能升级详情

#### 阶段4：模型训练（升级）

**原有功能**：
- 逻辑回归建模
- 逐步回归（可选）
- 系数方向检验

**新增功能**：

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 4.1 | 逻辑回归建模 | `StatisticalLogisticRegression.fit()` | LR模型 |
| 4.2 | 统计检验 | `StatisticalLogisticRegression.summary()` | 统计信息表 |
| 4.3 | 系数显著性检验 | p-value < 0.05 | 显著变量 |
| 4.4 | 系数方向检验 | 系数符号与业务逻辑一致 | 验证报告 |

**统计检验输出**：

| 指标 | 说明 | 用途 |
|------|------|------|
| **coef** | 回归系数 | 变量影响方向和强度 |
| **std_err** | 标准误差 | 系数估计精度 |
| **z_stat** | Wald z统计量 | 系数显著性检验 |
| **p_value** | p值 | p<0.05表示显著 |
| **ci_lower/ci_upper** | 95%置信区间 | 系数可信范围 |

**模型拟合统计**：

| 指标 | 说明 |
|------|------|
| **pseudo_r2** | McFadden伪R²，模型解释力 |
| **log_likelihood** | 对数似然值 |
| **aic** | 赤池信息准则 |
| **bic** | 贝叶斯信息准则 |

#### 阶段5：评分转换（升级）

**原有功能**：
- 设定基准分/PDO
- 生成评分卡
- 计算样本分数

**新增功能**：

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 5.1 | 初始化转换器 | `ScoreTransformer(base_score, pdo, bad_rate)` | 转换器实例 |
| 5.2 | 生成评分卡 | `sc.scorecard()` | 评分卡表 |
| 5.3 | 计算样本分数 | `sc.scorecard_ply()` | 分数列 |
| 5.4 | **评分→概率** | `ScoreTransformer.inverse_transform(scores)` | 概率值 |
| 5.5 | **概率→评分** | `ScoreTransformer.transform(probs)` | 评分值 |
| 5.6 | 分数分布分析 | 直方图/箱线图 | 分布图 |

**双向转换API**：

| 方向 | 方法 | 输入 | 输出 | 场景 |
|------|------|------|------|------|
| 概率→评分 | `transform()` | 违约概率 | 信用评分 | 模型输出转评分 |
| 评分→概率 | `inverse_transform()` | 信用评分 | 违约概率 | 评分校准/风险量化 |

#### 阶段7：报告生成（升级）

**原有功能**：
- HTML/Markdown报告
- 可视化图表

**新增功能**：

| 步骤 | 操作 | 工具/方法 | 输出 |
|------|------|-----------|------|
| 7.1 | 生成HTML报告 | 原有逻辑 | HTML文件 |
| 7.2 | **生成Excel报告** | `ExcelReportGenerator.generate_scorecard_report()` | Excel文件 |

**Excel报告内容**：

| Sheet名称 | 内容 |
|-----------|------|
| **概览** | 任务参数、数据概况、模型摘要 |
| **分箱详情** | WOE分箱表、IV值 |
| **评分卡** | 完整评分卡表 |
| **统计检验** | 系数统计信息（p值/z值/标准误/置信区间） |
| **模型评估** | KS/AUC/PSI指标 |
| **分数分布** | 分数段分布统计 |

### 2.3 ScorecardModeler 类设计

```python
class ScorecardModeler:
    """
    评分卡建模器（v4.2升级版）
    
    升级内容：
    - 集成StatisticalLogisticRegression，提供完整统计检验
    - 支持统计信息输出（p值/z值/标准误/置信区间）
    - 保持与原sklearn LogisticRegression的兼容性
    """
    
    def __init__(
        self,
        significance_level: float = 0.05,
        use_statistical_model: bool = True,  # 是否使用统计模型
        penalty: str | None = None,
        C: float = 1e10,
        **kwargs
    ):
        self.significance_level = significance_level
        self.use_statistical_model = use_statistical_model
        
        # 根据配置选择模型
        if use_statistical_model:
            self.model = StatisticalLogisticRegression(
                calculate_stats=True,
                penalty=penalty,
                C=C,
                **kwargs
            )
        else:
            self.model = LogisticRegression(
                penalty=penalty,
                C=C,
                **kwargs
            )
    
    def fit(self, X, y, feature_names=None) -> "ScorecardModeler":
        """训练模型"""
        self.model.fit(X, y)
        self.feature_names_ = feature_names or [f'x{i}' for i in range(X.shape[1])]
        return self
    
    def get_statistics(self) -> dict:
        """
        获取统计检验信息
        
        Returns:
            dict with keys:
            - summary: DataFrame with coef, std_err, z_stat, p_value, ci_lower, ci_upper
            - model_info: dict with pseudo_r2, log_likelihood, aic, bic
            - significant_vars: list of significant variables (p < 0.05)
        """
        if not self.use_statistical_model:
            raise ValueError("Statistical model not enabled. Set use_statistical_model=True")
        
        stats = self.model.summary()
        
        # 标记显著变量
        summary_df = stats['summary']
        significant_vars = summary_df[
            summary_df['p_value'] < self.significance_level
        ].index.tolist()
        
        return {
            'summary': summary_df,
            'model_info': stats['model_info'],
            'significant_vars': significant_vars,
            'insignificant_vars': [v for v in summary_df.index if v not in significant_vars]
        }
```

### 2.4 ScorecardScaler 类设计

```python
class ScorecardScaler:
    """
    评分刻度转换器（v4.2升级版）
    
    升级内容：
    - 集成ScoreTransformer，支持评分↔概率双向转换
    - 提供转换工具供前端/API调用
    """
    
    def __init__(
        self,
        base_score: int = 600,
        base_odds: int = 20,
        pdo: int = 20,
        bad_rate: float | None = None  # 可选：从数据计算base_odds
    ):
        self.base_score = base_score
        self.base_odds = base_odds
        self.pdo = pdo
        self.bad_rate = bad_rate
        self._transformer: ScoreTransformer | None = None
    
    def fit(self, y_train: pd.Series | None = None) -> "ScorecardScaler":
        """初始化转换器"""
        if self.bad_rate is None and y_train is not None:
            self.bad_rate = y_train.mean()
        elif self.bad_rate is None:
            self.bad_rate = self.base_odds / (1 + self.base_odds)
        
        self._transformer = ScoreTransformer(
            base_score=self.base_score,
            pdo=self.pdo,
            bad_rate=self.bad_rate
        )
        self._transformer.fit()
        return self
    
    def score_to_probability(self, scores: list | np.ndarray) -> np.ndarray:
        """评分转概率"""
        if self._transformer is None:
            raise ValueError("Scaler not fitted. Call fit() first.")
        return self._transformer.inverse_transform(scores)
    
    def probability_to_score(self, probs: list | np.ndarray) -> np.ndarray:
        """概率转评分"""
        if self._transformer is None:
            raise ValueError("Scaler not fitted. Call fit() first.")
        return self._transformer.transform(probs)
    
    def get_scale_info(self) -> dict:
        """获取刻度参数信息"""
        if self._transformer is None:
            raise ValueError("Scaler not fitted. Call fit() first.")
        return self._transformer.get_scale_info()
```

### 2.5 Pipeline 输出结构

```python
# ScorecardPipeline.run() 返回结构
results = {
    # 原有字段
    'preprocessing': {...},
    'woe_binning': {...},
    'feature_selection': {...},
    'model': model_object,
    'scorecard': scorecard_df,
    'evaluation': {...},
    
    # 新增字段
    'model_statistics': {
        'summary': pd.DataFrame,  # 系数统计表
        'model_info': {
            'pseudo_r2': float,
            'log_likelihood': float,
            'aic': float,
            'bic': float,
            'n_obs': int
        },
        'significant_vars': list,
        'insignificant_vars': list
    },
    'score_transformer': {
        'A': float,  # 刻度参数A
        'B': float,  # 刻度参数B
        'base_odds': float,
        'base_score': float,
        'pdo': float
    }
}
```

---

## 三、规则挖掘任务升级方案

### 3.1 架构层级更新

```
┌──────────────────────────────────────────────────────────────┐
│          规则挖掘架构（v6.2 升级后）                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📦 底层通用工具（deepanalyze/analysis/）                     │
│  ├── preprocessing.py         ✅ 通用数据预处理              │
│  └── excel_report.py          🆕 Excel报告生成器            │
│                                                              │
│  📦 任务SOP层（deepanalyze/analysis/task_SOP/）              │
│  └── rule_mining.py                                          │
│      ├── DataPreprocessor     ✅ 数据预处理                 │
│      ├── FeatureEngineer      ✅ 特征工程（可选）           │
│      ├── SingleVarRuleMiner   ✅ 单特征规则生成             │
│      ├── RuleMiner            ✅ 多特征规则生成             │
│      ├── RuleEvaluator        ✅ 规则效果评估               │
│      ├── PriorRuleAnalyzer    🆕 先验规则增量贡献分析器    │
│      ├── AmountAnalyzer       🆕 金额维度分析器            │
│      ├── RuleSelector         ✅ 最优规则选择               │
│      └── RuleMiningPipeline   ✅ 集成新分析器              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 新增独立封装类

#### 3.2.1 PriorRuleAnalyzer（先验规则分析器）

```python
class PriorRuleAnalyzer:
    """
    先验规则增量贡献分析器
    
    分析新规则相对于已有规则的增量贡献，用于：
    - 评估新规则对线上规则集的边际效果
    - 规则优化和冗余检测
    - 理解规则重叠情况
    """
    
    def __init__(
        self,
        prior_rules: list[str] | None = None,
        weight_col: str | None = None
    ):
        ...
    
    def fit(self, df: pd.DataFrame, target_col: str = 'target') -> "PriorRuleAnalyzer":
        """拟合分析器，计算先验规则组合命中情况"""
        ...
    
    def analyze_rule(self, rule: str) -> dict[str, Any]:
        """分析单条规则的增量贡献"""
        ...
    
    def analyze(self, rule_df: pd.DataFrame) -> pd.DataFrame:
        """批量分析规则的增量贡献"""
        ...
```

**输出指标**：

| 指标 | 说明 | 计算方式 |
|------|------|----------|
| **standalone_recall** | 独立召回率 | 规则命中坏样本 / 总坏样本 |
| **standalone_hit_rate** | 独立命中率 | 规则命中样本 / 总样本 |
| **incremental_recall** | 增量召回率 | 在先验规则基础上额外捕获的坏样本 / 总坏样本 |
| **incremental_hit_rate** | 增量命中率 | 在先验规则基础上额外命中的样本 / 总样本 |
| **overlap_rate** | 重叠率 | 与先验规则重叠命中的样本 / 规则命中样本 |
| **marginal_contribution** | 边际贡献 | incremental_recall / standalone_recall |

#### 3.2.2 AmountAnalyzer（金额维度分析器）

```python
class AmountAnalyzer:
    """
    金额维度分析器
    
    从金融/金额维度分析规则效果：
    - 规则捕获了多少风险敞口（金额）？
    - 捕获的坏样本金额是多少？
    - 金额维度的提升度和坏账率
    """
    
    def __init__(
        self,
        amount_col: str = 'amount',
        weight_col: str | None = None
    ):
        ...
    
    def fit(self, df: pd.DataFrame, target_col: str = 'target') -> "AmountAnalyzer":
        """拟合分析器，计算总金额和总坏账金额"""
        ...
    
    def analyze_rule(self, rule: str) -> dict[str, Any]:
        """分析单条规则的金额维度指标"""
        ...
    
    def analyze_with_cumulative(self, rule_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        """分析规则并计算累计金额指标"""
        ...
```

**输出指标**：

| 指标 | 说明 | 计算方式 |
|------|------|----------|
| **hit_amount** | 命中金额 | 规则命中样本的金额总和 |
| **hit_amount_pct** | 命中金额占比 | hit_amount / 总金额 |
| **bad_amount** | 坏样本金额 | 规则命中的坏样本金额总和 |
| **bad_amount_pct** | 金额召回率 | bad_amount / 总坏样本金额 |
| **amount_bad_rate** | 金额坏账率 | bad_amount / hit_amount |
| **amount_lift** | 金额提升度 | amount_bad_rate / 整体金额坏账率 |
| **avg_amount_per_hit** | 平均命中金额 | hit_amount / 命中样本数 |

### 3.3 RuleEvaluator 类升级设计

```python
class RuleEvaluator:
    """
    规则效果评估器（v6.2升级版）
    
    升级内容：
    - 新增先验规则增量贡献分析
    - 新增金额维度效果评估
    - 支持批量评估
    """
    
    def evaluate_rules(self, df, rule_df, target_col, weight_col=None) -> pd.DataFrame:
        """基础规则评估（原有逻辑）"""
        ...
    
    def evaluate_with_prior(
        self,
        df: pd.DataFrame,
        rule: str,
        prior_rules: list[str],
        target_col: str
    ) -> dict:
        """
        评估单条规则相对于先验规则的增量贡献
        
        Returns:
            dict with:
            - standalone_recall: 独立召回率
            - incremental_recall: 增量召回率
            - overlap_rate: 重叠率
            - marginal_contribution: 边际贡献
        """
        ...
    
    def evaluate_with_amount(
        self,
        df: pd.DataFrame,
        rule: str,
        target_col: str,
        amount_col: str = 'amount'
    ) -> dict:
        """
        评估单条规则的金额维度效果
        
        Returns:
            dict with:
            - hit_amount: 命中金额
            - bad_amount: 坏样本金额
            - amount_recall: 金额召回率
            - amount_lift: 金额提升度
        """
        ...
```

### 3.4 Pipeline 输出结构

```python
# RuleMiningPipeline.run() 返回结构
results = {
    # 原有字段
    'preprocessing': {...},
    'feature_engineering': {...},
    'all_rules': pd.DataFrame,
    'direction': pd.DataFrame,
    'filtered_rules': pd.DataFrame,
    'evaluated_rules': pd.DataFrame,
    'optimal_rules': pd.DataFrame,
    
    # 新增字段
    'prior_analysis': {
        'enabled': bool,
        'prior_rules': list[str],
        'results': pd.DataFrame,
        'summary': {
            'total_prior_recall': float,
            'total_incremental_recall': float,
            'avg_overlap_rate': float
        }
    },
    'amount_analysis': {
        'enabled': bool,
        'amount_col': str,
        'results': pd.DataFrame,
        'summary': {
            'total_amount': float,
            'total_bad_amount': float,
            'optimal_rules_amount_recall': float,
            'optimal_rules_amount_lift': float
        }
    }
}
```

---

## 四、API接口设计

### 4.1 评分转换API

```
POST /sop/score/convert

Request:
{
    "values": [680, 720, 600],
    "direction": "to_prob",  // 或 "to_score"
    "scale_params": {
        "base_score": 660,
        "pdo": 75,
        "base_odds": 0.176
    }
}

Response:
{
    "results": [
        {"input": 680, "output": 0.12},
        {"input": 720, "output": 0.06},
        {"input": 600, "output": 0.35}
    ],
    "scale_info": {
        "A": 487.12,
        "B": 108.2
    }
}
```

### 4.2 Excel导出API

```
POST /sop/report/export

Request:
{
    "execution_id": "exec-xxx",
    "format": "excel",  // 或 "html"
    "sections": ["overview", "bins", "scorecard", "statistics", "charts"],
    "style": "professional"
}

Response:
{
    "download_url": "/sop/report/download/xxx.xlsx",
    "file_name": "scorecard_report_20251219.xlsx"
}
```

### 4.3 结果结构扩展（评分卡）

```json
{
    "model_statistics": {
        "summary": [
            {"feature": "const", "coef": -2.5, "std_err": 0.12, "z": -20.8, "p_value": 0.0, "ci_lower": -2.74, "ci_upper": -2.26},
            {"feature": "age_woe", "coef": 0.85, "std_err": 0.05, "z": 17.0, "p_value": 0.0, "ci_lower": 0.75, "ci_upper": 0.95}
        ],
        "n_observations": 10000,
        "pseudo_r2": 0.25,
        "log_likelihood": -4500.5
    },
    "score_scale": {
        "base_score": 660,
        "pdo": 75,
        "base_odds": 0.176,
        "A": 487.12,
        "B": 108.2
    }
}
```

### 4.4 结果结构扩展（规则挖掘）

```json
{
    "prior_analysis": {
        "prior_rules": ["age > 30", "income < 5000"],
        "rules_incremental": [
            {
                "rule": "debt_ratio > 0.8",
                "standalone_recall": 0.15,
                "incremental_recall": 0.08,
                "standalone_hit_rate": 0.12,
                "incremental_hit_rate": 0.05,
                "overlap_with_prior": 0.47,
                "marginal_contribution": 0.08
            }
        ]
    },
    "amount_analysis": {
        "total_amount": 1000000,
        "total_bad_amount": 150000,
        "rules_amount": [
            {
                "rule": "debt_ratio > 0.8",
                "hit_amount": 200000,
                "hit_amount_pct": 0.20,
                "bad_amount": 45000,
                "bad_amount_pct": 0.30,
                "amount_bad_rate": 0.225,
                "amount_lift": 1.50
            }
        ],
        "cumulative": {
            "cum_hit_amount": 350000,
            "cum_bad_amount": 85000,
            "amount_recall": 0.57
        }
    }
}
```

---

## 五、前端UI设计

### 5.1 ModelStatisticsPanel 组件

**位置**：ScorecardResults.tsx 新增Tab

```
┌─────────────────────────────────────────────────────────────┐
│ 模型统计信息                                                  │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐                        │
│ │ 样本量   │ │ 伪R²    │ │对数似然  │  ← 指标卡片            │
│ │ 10,000  │ │ 0.25    │ │ -4500.5 │                        │
│ └─────────┘ └─────────┘ └─────────┘                        │
├─────────────────────────────────────────────────────────────┤
│ 变量      │ 系数    │ 标准误  │ z值    │ p值    │ 显著性  │
│ const    │ -2.50   │ 0.12   │ -20.8  │ 0.000  │ ***     │
│ age_woe  │ 0.85    │ 0.05   │ 17.0   │ 0.000  │ ***     │
│ income   │ 0.42    │ 0.08   │ 5.25   │ 0.000  │ ***     │
│ debt_woe │ 0.15    │ 0.06   │ 2.50   │ 0.012  │ *       │
└─────────────────────────────────────────────────────────────┘

显著性标记：*** p<0.001, ** p<0.01, * p<0.05
```

**TypeScript接口**：
```typescript
interface ModelStatistics {
  summary: Array<{
    feature: string;
    coef: number;
    std_err: number;
    z: number;
    p_value: number;
    ci_lower: number;
    ci_upper: number;
  }>;
  n_observations: number;
  pseudo_r2: number;
  log_likelihood: number;
}
```

### 5.2 ScoreConverter 组件

**位置**：ScorecardResults.tsx 评分卡Tab内嵌入

```
┌─────────────────────────────────────────────────────────────┐
│ 评分转换器                                                   │
├─────────────────────────────────────────────────────────────┤
│ 刻度参数: base_score=660, PDO=75, A=487.12, B=108.2        │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────┐    ⟷    ┌──────────────┐                  │
│ │ 评分: [680 ] │  [转换]  │ 概率: 12.3%  │                  │
│ └──────────────┘         └──────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│ 批量转换:                                                    │
│ ┌────────────────────────────────────────┐                  │
│ │ 600, 650, 700, 750, 800               │ [批量转换]        │
│ └────────────────────────────────────────┘                  │
│ 结果表格:                                                    │
│ │ 评分  │ 概率    │                                         │
│ │ 600  │ 35.2%  │                                         │
│ │ 650  │ 18.5%  │                                         │
│ │ 700  │ 9.8%   │                                         │
└─────────────────────────────────────────────────────────────┘
```

**TypeScript接口**：
```typescript
interface ScoreScale {
  base_score: number;
  pdo: number;
  base_odds: number;
  A: number;
  B: number;
}

interface ConvertResult {
  input: number;
  output: number;
}
```

### 5.3 AmountAnalysisPanel 组件

**位置**：RuleMiningResults.tsx 新增Tab

```
┌─────────────────────────────────────────────────────────────┐
│ 金额维度分析                                                  │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│ │ 总金额      │ │ 坏账金额    │ │ 拦截金额比  │            │
│ │ ¥1,000,000 │ │ ¥150,000   │ │ 56.7%      │            │
│ └─────────────┘ └─────────────┘ └─────────────┘            │
├─────────────────────────────────────────────────────────────┤
│ 规则          │ 命中金额   │ 坏账金额  │ 金额Lift │ 金额占比│
│ debt>0.8     │ ¥200,000  │ ¥45,000  │ 1.50    │ 20%    │
│ income<5000  │ ¥150,000  │ ¥40,000  │ 1.78    │ 15%    │
│ 累计         │ ¥350,000  │ ¥85,000  │ 1.62    │ 35%    │
├─────────────────────────────────────────────────────────────┤
│ [累计金额曲线图]                                              │
└─────────────────────────────────────────────────────────────┘
```

**TypeScript接口**：
```typescript
interface AmountAnalysis {
  total_amount: number;
  total_bad_amount: number;
  rules_amount: Array<{
    rule: string;
    hit_amount: number;
    hit_amount_pct: number;
    bad_amount: number;
    bad_amount_pct: number;
    amount_bad_rate: number;
    amount_lift: number;
  }>;
  cumulative: {
    cum_hit_amount: number;
    cum_bad_amount: number;
    amount_recall: number;
  };
}
```

### 5.4 ExportConfigDialog 组件

**位置**：ScorecardResults.tsx / RuleMiningResults.tsx 导出按钮触发

```
┌─────────────────────────────────────────┐
│ 导出报告配置                     [×]    │
├─────────────────────────────────────────┤
│ 格式:                                    │
│ ○ HTML    ● Excel                       │
├─────────────────────────────────────────┤
│ 导出内容:                                │
│ ☑ 概览摘要                              │
│ ☑ 分箱详情                              │
│ ☑ 评分卡                                │
│ ☑ 模型统计                              │
│ ☐ 图表（嵌入Excel）                      │
├─────────────────────────────────────────┤
│ 样式模板:                                │
│ [专业模板           ▼]                   │
├─────────────────────────────────────────┤
│           [取消]  [导出]                 │
└─────────────────────────────────────────┘
```

### 5.5 规则挖掘配置面板扩展

**位置**：TaskConfigPanel.tsx 规则挖掘参数区域

```
┌─────────────────────────────────────────────────────────────┐
│ 高级选项                                            [展开▼] │
├─────────────────────────────────────────────────────────────┤
│ 金额列（可选）:                                              │
│ [选择金额列...        ▼]  ← 从数据列中选择                   │
│                                                             │
│ 先验规则（可选）:                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ age > 30                                                │ │
│ │ income < 5000                                           │ │
│ │ (每行一条规则)                                           │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [从历史任务导入...]                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、后端实现方案

### 6.1 统计信息逻辑回归

**文件**：`deepanalyze/analysis/statistical_model.py`

```python
"""统计信息增强的逻辑回归模型"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from scipy import stats

class StatisticalLogisticRegression(LogisticRegression):
    """带统计信息输出的逻辑回归"""
    
    def __init__(self, calculate_stats=True, **kwargs):
        super().__init__(**kwargs)
        self.calculate_stats = calculate_stats
        self._stats = None
        self._model_info = {}
        
    def fit(self, X, y, sample_weight=None, **kwargs):
        if isinstance(X, pd.DataFrame):
            self.feature_names_in_ = X.columns.tolist()
            X_array = X.values
        else:
            self.feature_names_in_ = [f"x{i}" for i in range(X.shape[1])]
            X_array = X
            
        super().fit(X_array, y, sample_weight=sample_weight, **kwargs)
        
        if self.calculate_stats:
            self._calculate_statistics(X_array, y)
        return self
    
    def _calculate_statistics(self, X, y):
        """基于Hessian矩阵计算统计信息"""
        n_samples = X.shape[0]
        
        if self.fit_intercept:
            X_with_intercept = np.column_stack([np.ones(n_samples), X])
            coefs = np.concatenate([[self.intercept_[0]], self.coef_[0]])
            feature_names = ["const"] + self.feature_names_in_
        else:
            X_with_intercept = X
            coefs = self.coef_[0]
            feature_names = self.feature_names_in_
        
        proba = self.predict_proba(X)[:, 1]
        
        # Hessian矩阵计算标准误
        W = np.diag(proba * (1 - proba))
        H = X_with_intercept.T @ W @ X_with_intercept
        
        try:
            cov_matrix = np.linalg.inv(H)
            std_errors = np.sqrt(np.diag(cov_matrix))
        except np.linalg.LinAlgError:
            std_errors = np.full(len(coefs), np.nan)
        
        z_stats = coefs / std_errors
        p_values = 2 * (1 - stats.norm.cdf(np.abs(z_stats)))
        ci_lower = coefs - 1.96 * std_errors
        ci_upper = coefs + 1.96 * std_errors
        
        self._stats = pd.DataFrame({
            "feature": feature_names,
            "coef": coefs,
            "std_err": std_errors,
            "z": z_stats,
            "p_value": p_values,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
        })
        
        # 计算模型整体指标
        log_likelihood = np.sum(y * np.log(proba + 1e-10) + (1 - y) * np.log(1 - proba + 1e-10))
        null_proba = np.mean(y)
        null_log_likelihood = np.sum(y * np.log(null_proba) + (1 - y) * np.log(1 - null_proba))
        pseudo_r2 = 1 - (log_likelihood / null_log_likelihood)
        
        self._model_info = {
            "n_observations": n_samples,
            "log_likelihood": log_likelihood,
            "pseudo_r2": pseudo_r2
        }
    
    def summary(self) -> dict:
        """返回模型统计摘要"""
        if self._stats is None:
            raise ValueError("模型尚未训练或未启用统计信息计算")
        return {
            "summary": self._stats.to_dict(orient="records"),
            **self._model_info
        }
```

### 6.2 评分刻度转换器

**文件**：`deepanalyze/analysis/score_transformer.py`

```python
"""评分刻度转换器"""

import numpy as np
import pandas as pd

class ScoreTransformer:
    """评分刻度转换器：概率⟷评分双向转换"""
    
    def __init__(
        self,
        base_score: float = 660,
        pdo: float = 75,
        rate: float = 2,
        bad_rate: float = 0.15,
        down_lmt: float = 300,
        up_lmt: float = 850
    ):
        self.base_score = base_score
        self.pdo = pdo
        self.rate = rate
        self.bad_rate = bad_rate
        self.down_lmt = down_lmt
        self.up_lmt = up_lmt
        self._fitted = False
        
    def fit(self, X=None, y=None):
        self.base_odds_ = self.bad_rate / (1 - self.bad_rate)
        self.B_ = self.pdo / np.log(self.rate)
        self.A_ = self.base_score + self.B_ * np.log(self.base_odds_)
        self._fitted = True
        return self
    
    def transform(self, proba) -> np.ndarray:
        """概率→评分"""
        if not self._fitted:
            self.fit()
        proba = np.clip(np.asarray(proba).ravel(), 1e-10, 1 - 1e-10)
        scores = self.A_ - self.B_ * np.log(proba / (1 - proba))
        return np.clip(scores, self.down_lmt, self.up_lmt)
    
    def inverse_transform(self, scores) -> np.ndarray:
        """评分→概率"""
        if not self._fitted:
            self.fit()
        scores = np.asarray(scores).ravel()
        return 1 / (1 + np.exp((self.A_ - scores) / self.B_))
    
    def get_scale_info(self) -> dict:
        """获取评分刻度信息"""
        if not self._fitted:
            self.fit()
        return {
            "base_score": self.base_score,
            "pdo": self.pdo,
            "base_odds": round(self.base_odds_, 4),
            "A": round(self.A_, 2),
            "B": round(self.B_, 2)
        }
```

### 6.3 规则增强方法

**文件**：`deepanalyze/analysis/task_SOP/rule_mining.py`（RuleEvaluator类新增）

```python
def evaluate_with_prior(
    self, 
    df: pd.DataFrame, 
    rule: str, 
    prior_rules: list[str], 
    target: str
) -> dict:
    """
    先验规则评估：评估规则在已有规则基础上的增量贡献
    """
    # 计算prior规则的联合命中
    prior_hit = pd.Series(False, index=df.index)
    for pr in prior_rules:
        try:
            prior_hit |= df.eval(pr)
        except:
            continue
    
    # 计算当前规则命中
    rule_hit = df.eval(rule)
    
    # 计算指标
    total_bad = df[target].sum()
    total_samples = len(df)
    
    # 独立指标
    standalone_recall = df.loc[rule_hit, target].sum() / total_bad if total_bad > 0 else 0
    standalone_hit_rate = rule_hit.sum() / total_samples
    
    # 增量指标（排除prior已命中的）
    incremental_hit = rule_hit & ~prior_hit
    incremental_recall = df.loc[incremental_hit, target].sum() / total_bad if total_bad > 0 else 0
    incremental_hit_rate = incremental_hit.sum() / total_samples
    
    # 重叠度
    overlap = (rule_hit & prior_hit).sum() / rule_hit.sum() if rule_hit.sum() > 0 else 0
    
    return {
        "rule": rule,
        "standalone_recall": round(standalone_recall, 4),
        "incremental_recall": round(incremental_recall, 4),
        "standalone_hit_rate": round(standalone_hit_rate, 4),
        "incremental_hit_rate": round(incremental_hit_rate, 4),
        "overlap_with_prior": round(overlap, 4),
        "marginal_contribution": round(incremental_recall, 4)
    }

def evaluate_with_amount(
    self, 
    df: pd.DataFrame, 
    rule: str, 
    target: str, 
    amount_col: str
) -> dict:
    """
    金额维度分析：统计命中金额、坏账金额
    """
    rule_hit = df.eval(rule)
    
    total_amount = df[amount_col].sum()
    total_bad_amount = df.loc[df[target] == 1, amount_col].sum()
    
    hit_amount = df.loc[rule_hit, amount_col].sum()
    bad_amount = df.loc[rule_hit & (df[target] == 1), amount_col].sum()
    
    # 金额维度指标
    hit_amount_pct = hit_amount / total_amount if total_amount > 0 else 0
    bad_amount_pct = bad_amount / total_bad_amount if total_bad_amount > 0 else 0
    amount_bad_rate = bad_amount / hit_amount if hit_amount > 0 else 0
    overall_bad_rate = total_bad_amount / total_amount if total_amount > 0 else 0
    amount_lift = amount_bad_rate / overall_bad_rate if overall_bad_rate > 0 else 0
    
    return {
        "rule": rule,
        "hit_amount": round(hit_amount, 2),
        "hit_amount_pct": round(hit_amount_pct, 4),
        "bad_amount": round(bad_amount, 2),
        "bad_amount_pct": round(bad_amount_pct, 4),
        "amount_bad_rate": round(amount_bad_rate, 4),
        "amount_lift": round(amount_lift, 2),
        "avg_amount_per_hit": round(hit_amount / rule_hit.sum(), 2) if rule_hit.sum() > 0 else 0
    }
```

---

## 七、实施状态

### 7.1 已完成项

| 项目 | 状态 | 说明 |
|------|------|------|
| StatisticalLogisticRegression | ✅ 已实现 | `analysis/statistical_model.py` |
| ScoreTransformer | ✅ 已实现 | `analysis/score_transformer.py` |
| ExcelReportGenerator | ✅ 已实现 | `analysis/excel_report.py` |
| evaluate_with_prior | ✅ 已实现 | `rule_mining.py::RuleEvaluator` |
| evaluate_with_amount | ✅ 已实现 | `rule_mining.py::RuleEvaluator` |
| prior_rules/amount_col参数 | ✅ 已实现 | `rule_mining_meta.py` |
| ModelStatisticsPanel | ✅ 已实现 | 前端组件 |
| ScoreConverter | ✅ 已实现 | 前端组件 |
| AmountAnalysisPanel | ✅ 已实现 | 前端组件 |
| ScorecardModeler集成StatisticalLR | ✅ 已完成 | 新增`ScorecardModeler`类 |
| ScorecardScaler集成ScoreTransformer | ✅ 已完成 | 新增`ScorecardScaler`类 |
| PriorRuleAnalyzer独立封装 | ✅ 已完成 | 新增`PriorRuleAnalyzer`类 |
| AmountAnalyzer独立封装 | ✅ 已完成 | 新增`AmountAnalyzer`类 |
| Pipeline输出结构升级 | ✅ 已完成 | 两个Pipeline已集成新分析器 |
| 评分转换API | ✅ 已完成 | `/sop/score/convert`端点已实现 |
| Excel报告导出API | ✅ 已完成 | `/sop/report/export`端点已实现 |
| 前端Tab集成 | ✅ 已完成 | 组件已集成到结果页 |
| 工作流文档更新 | ✅ 已完成 | v4.2/v6.2 |

### 7.2 已完成功能历史记录

| 功能 | 实现位置 | 完成日期 |
|------|----------|----------|
| 逐步回归 | `FeatureSelector.stepwise_selection()` | - |
| 多种分箱方法 | `WOETransformer` | - |
| IV/VIF/相关性筛选 | `FeatureSelector` | - |
| 规则&组合 | `rule_mining.py` | - |
| PSI稳定性 | `RuleEvaluator.calculate_rule_psi()` | 2025-12-15 |
| 规则质量验证 | `RuleValidator` | 2025-12-15 |
| 规则业务解读 | `RuleInterpreter` | 2025-12-15 |
| 二值特征方向优化 | `rule_mining.py` | 2025-12-10 |
| **决策树图形可视化** | `rule_mining_viz.plot_decision_tree()` | 2025-12-26 |
| **规则PSI趋势图** | `rule_mining_viz.plot_psi_trend()` | 2025-12-26 |

### 7.3 P2 可选功能（待实施）

| 功能 | 说明 | 工作量 |
|------|------|--------|
| **PMML导出** | sklearn2pmml集成 | 0.5天 |
| **规则类封装** | Rule类支持&\|操作符 | 1天 |

### 7.4 废弃功能

| 功能 | 说明 | 废弃原因 |
|------|------|----------|
| ~~规则覆盖热力图~~ | 展示规则间样本覆盖重叠 | 与现有重叠度报告功能重复，ROI低 |
| ~~规则贡献桑基图~~ | 展示规则组合累计召回贡献 | 与累计曲线功能重叠，信息冗余 |

### 7.5 验收标准

| 功能 | 验收标准 |
|------|----------|
| 统计信息逻辑回归 | 输出标准误/z值/p值，前端正确展示，显著性标记正确 |
| 评分反向转换 | 680分→约12%概率，批量转换结果正确 |
| Excel报告导出 | 生成专业格式报告，包含条件格式，多Sheet结构正确 |
| 先验规则评估 | 正确计算增量贡献，重叠度计算准确 |
| 金额维度分析 | 输出命中金额/坏账金额，金额Lift计算正确 |

---

## 八、附录

### 8.1 评分转换公式推导

```
标准评分转换公式：
Score = A - B × ln(odds)

其中：
- odds = p / (1-p)，p为违约概率
- A = base_score + B × ln(base_odds)
- B = PDO / ln(rate)
- rate: PDO对应的odds倍数（通常为2）

逆转换：
odds = exp((A - Score) / B)
p = odds / (1 + odds)
```

### 8.2 先验规则增量贡献计算

```
设：
- S: 总样本集
- B: 总坏样本集
- P: 先验规则命中集
- R: 当前规则命中集

则：
- standalone_recall = |R ∩ B| / |B|
- incremental_recall = |R ∩ B - P ∩ B| / |B|
- overlap_rate = |R ∩ P| / |R|
- marginal_contribution = incremental_recall / standalone_recall
```

### 8.3 金额维度指标计算

```
设：
- A: 总金额
- A_bad: 总坏样本金额
- A_hit: 规则命中金额
- A_hit_bad: 规则命中坏样本金额

则：
- amount_recall = A_hit_bad / A_bad
- amount_lift = amount_recall / (A_hit / A)
```

---

*文档版本：v4.2（融合版）*  
*创建日期：2025-12-15*  
*更新日期：2025-12-22*  
*状态：已实现*
