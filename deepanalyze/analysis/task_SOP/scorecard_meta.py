"""
Scorecard Development Task Metadata and SOP Prompt Template

Provides task definition for WebUI integration:
- Task metadata (stages, parameters, outputs)
- LLM SOP prompt template for guided execution
- Chat entry configuration (trigger keywords, summary)
"""

from __future__ import annotations
from typing import Any, Dict, List

# 导入统一类型定义（可选，用于类型提示）
# from .types import TaskMetaDict, StageDict, ParamDict, OutputDict

# =============================================================================
# Task Metadata Definition
# =============================================================================

SCORECARD_TASK_META: Dict[str, Any] = {
    # Basic Info
    "task_id": "scorecard_dev",
    "task_name": "评分卡开发",
    "task_name_en": "Scorecard Development",
    "description": "基于WOE/IV方法的标准信用评分卡开发流程",
    "category": "风控建模",
    "icon": "chart",
    "estimated_time": "5-15分钟",
    
    # ========== Chat 入口配置（新增） ==========
    "task_type": "sop",  # 任务类型：sop（有固定流程）
    "trigger_keywords": [
        "评分卡", "信用评分", "评分模型", "scorecard", "credit score",
        "信用卡评分", "贷款评分", "风险评分", "申请评分", "行为评分",
        "A卡", "B卡", "C卡", "申请卡", "行为卡", "催收卡"
    ],
    "chat_summary": "基于WOE/IV方法构建标准信用评分卡，包含数据预处理、特征筛选、逻辑回归建模、评分刻度转换和模型评估",
    "required_params_summary": "数据文件、目标变量（0/1二分类，1为坏样本）",
    
    # Workflow Stages
    "stages": [
        {"id": "data_loading", "name": "数据加载", "progress_weight": 8},
        {"id": "woe_binning", "name": "WOE分箱", "progress_weight": 22},
        {"id": "feature_selection", "name": "特征筛选", "progress_weight": 13},
        {"id": "model_training", "name": "模型训练", "progress_weight": 18},
        {"id": "score_scaling", "name": "评分转换", "progress_weight": 12},
        {"id": "model_evaluation", "name": "模型评估", "progress_weight": 15},
        {"id": "report_generation", "name": "报告生成", "progress_weight": 12}
    ],
    
    # Required Parameters
    "required_params": [
        {
            "name": "target_col",
            "type": "column_select",
            "label": "目标变量",
            "label_en": "Target Column",
            "description": "二分类目标变量（0/1，1表示坏样本）",
            "required": True,
            "stage": "data_loading"
        },
        {
            "name": "exclude_cols",
            "type": "column_multi_select",
            "label": "排除变量",
            "label_en": "Exclude Columns",
            "description": "额外指定不参与建模的列。系统会自动检测并排除ID列、时间列、样本标识列等非特征列，此处可补充指定其他需排除的列",
            "required": False,
            "allow_empty": True,
            "stage": "data_loading"
        }
    ],
    
    # Optional Parameters
    "optional_params": [
        # Data Preprocessing
        {
            "name": "special_values",
            "type": "text",
            "label": "特殊缺失值",
            "label_en": "Special Missing Values",
            "default": "-9999,-999,-99999,-998,-9998,-99998",
            "allow_empty": True,
            "description": "额外视为缺失值的特殊数值，逗号分隔。系统已默认将 NaN、None、空字符串识别为缺失值，此处可补充业务系统中常见的缺失标记（如-9999、-999等）。留空表示不额外指定",
            "stage": "data_loading"
        },
        {
            "name": "force_categorical",
            "type": "column_multi_select",
            "label": "指定分类变量",
            "label_en": "Force Categorical Columns",
            "default": [],
            "allow_empty": True,
            "description": "手动指定为分类变量的列（如省份编码、行业编码等）。用于系统无法自动识别的编码型分类变量",
            "stage": "data_loading"
        },
        {
            "name": "missing_threshold",
            "type": "number",
            "label": "缺失率阈值",
            "label_en": "Missing Threshold",
            "default": 0.95,
            "min": 0.3,
            "max": 0.99,
            "step": 0.05,
            "description": "缺失率超过此阈值的变量将被剔除。行业惯例通常为50%，当前默认95%较为宽松（仅剔除几乎全空的变量），可根据数据质量调整",
            "stage": "data_loading"
        },
        {
            "name": "test_ratio",
            "type": "number",
            "label": "测试集比例",
            "label_en": "Test Ratio",
            "default": 0.3,
            "min": 0.1,
            "max": 0.5,
            "step": 0.05,
            "allow_empty": True,
            "description": "测试集占总数据的比例（留空或0表示不划分测试集）",
            "stage": "data_loading"
        },
        {
            "name": "sample_type_col",
            "type": "column_select",
            "label": "样本类型列（手动划分）",
            "label_en": "Sample Type Column",
            "default": None,
            "required": False,
            "allow_empty": True,
            "description": "包含样本类型标签的列名。列值应为 train/test/oot（或 validation）。设置后将按该列的值划分训练集、测试集和OOT验证集",
            "stage": "data_loading"
        },
        {
            "name": "time_col",
            "type": "column_select",
            "label": "时间列（智能OOT划分）",
            "label_en": "Time Column for OOT",
            "default": None,
            "required": False,
            "allow_empty": True,
            "description": "用于智能OOT划分的时间列。支持日期(YYYY-MM-DD)、数值(YYYYMM/YYYYMMDD)等格式。设置后将按时间顺序自动选取最近的数据作为OOT验证集。仅在未设置样本类型列时生效",
            "stage": "data_loading",
            "show_when": {"sample_type_col": {"$eq": None}}
        },
        {
            "name": "oot_ratio",
            "type": "number",
            "label": "OOT验证集比例",
            "label_en": "OOT Ratio",
            "default": 0.0,
            "min": 0.0,
            "max": 0.3,
            "step": 0.05,
            "allow_empty": True,
            "description": "OOT验证集占总数据的比例（0或留空表示不划分OOT）。仅在设置时间列时生效，将选取最近时间段的数据作为OOT",
            "stage": "data_loading",
            "show_when": {"time_col": {"$ne": None}, "sample_type_col": {"$eq": None}}
        },
        # P2-6: 类别不平衡处理
        {
            "name": "imbalance_strategy",
            "type": "select",
            "label": "类别不平衡处理",
            "label_en": "Imbalance Strategy",
            "options": [
                {"value": "auto", "label": "自动选择（推荐）"},
                {"value": "none", "label": "不处理"},
                {"value": "class_weight", "label": "类别加权"}
            ],
            "default": "auto",
            "description": "当坏样本率<10%时建议启用。auto模式会根据坏账率自动决定是否使用类别加权。注意：WOE分箱阶段不受影响，仅在模型训练阶段应用",
            "stage": "data_loading",
            "advanced": False
        },
        
        # WOE Binning
        {
            "name": "binning_method",
            "type": "select",
            "label": "分箱方法",
            "label_en": "Binning Method",
            "options": [
                {"value": "tree", "label": "决策树分箱"},
                {"value": "chimerge", "label": "卡方分箱"},
                {"value": "quantile", "label": "等频分箱"}
            ],
            "default": "tree",
            "description": "WOE分箱方法选择",
            "stage": "woe_binning"
        },
        {
            "name": "bin_num_limit",
            "type": "number",
            "label": "最大分箱数",
            "label_en": "Max Bins",
            "default": 8,
            "min": 3,
            "max": 15,
            "step": 1,
            "description": "每个变量的最大分箱数量",
            "stage": "woe_binning"
        },
        {
            "name": "use_high_precision",
            "type": "checkbox",
            "label": "高精度模式",
            "label_en": "High Precision Mode",
            "default": True,
            "description": "使用scorecardpy进行分箱，WOE更单调、IV更高，但执行速度较慢",
            "stage": "woe_binning"
        },
        
        # Feature Selection
        {
            "name": "iv_lower",
            "type": "number",
            "label": "IV下限",
            "label_en": "IV Lower",
            "default": 0.02,
            "min": 0.01,  # 2026-02-10: 允许用户设置更低的阈值（如0.01），但默认仍为0.02
            "max": 0.1,
            "step": 0.01,
            "description": "IV值低于此阈值的变量将被剔除",
            "stage": "feature_selection"
        },
        {
            "name": "iv_upper",
            "type": "number",
            "label": "IV上限",
            "label_en": "IV Upper",
            "default": 0.5,
            "min": 0.3,
            "max": 1.0,
            "step": 0.1,
            "description": "IV值高于此阈值的变量可能过拟合",
            "stage": "feature_selection"
        },
        {
            "name": "vif_threshold",
            "type": "number",
            "label": "VIF阈值",
            "label_en": "VIF Threshold",
            "default": 5,
            "min": 2,
            "max": 10,
            "step": 1,
            "description": "VIF超过此阈值的变量将被剔除",
            "stage": "feature_selection"
        },
        {
            "name": "corr_threshold",
            "type": "number",
            "label": "相关系数阈值",
            "label_en": "Correlation Threshold",
            "default": 0.7,
            "min": 0.5,
            "max": 0.95,
            "step": 0.05,
            "description": "相关系数超过此阈值的变量对将被处理",
            "stage": "feature_selection"
        },
        
        # Model Training
        {
            "name": "use_stepwise",
            "type": "checkbox",
            "label": "启用逐步回归",
            "label_en": "Use Stepwise",
            "default": True,
            "description": "使用逐步回归进行特征选择",
            "stage": "model_training"
        },
        {
            "name": "stepwise_direction",
            "type": "select",
            "label": "逐步回归方向",
            "label_en": "Stepwise Direction",
            "options": [
                {"value": "both", "label": "双向"},
                {"value": "forward", "label": "前向"},
                {"value": "backward", "label": "后向"}
            ],
            "default": "both",
            "show_when": {"use_stepwise": True},
            "description": "逐步回归的方向",
            "stage": "model_training"
        },
        {
            "name": "significance_level",
            "type": "number",
            "label": "显著性水平",
            "label_en": "Significance Level",
            "default": 0.05,
            "min": 0.01,
            "max": 0.1,
            "step": 0.01,
            "description": "系数显著性检验的p值阈值",
            "stage": "model_training"
        },
        {
            "name": "significance_mode",
            "type": "select",
            "label": "显著性检验模式",
            "label_en": "Significance Test Mode",
            "options": [
                {"value": "skip", "label": "跳过（不做检验）"},
                {"value": "warn", "label": "警告（保留变量，仅提示）"},
                {"value": "remove", "label": "移除（迭代移除不显著变量）"}
            ],
            "default": "warn",
            "show_when": {"use_stepwise": True},
            "description": "显著性检验失败的变量处理方式：跳过/警告/迭代移除",
            "stage": "model_training"
        },
        {
            "name": "coefficient_direction_mode",
            "type": "select",
            "label": "系数方向异常处理",
            "label_en": "Coefficient Direction Mode",
            "options": [
                {"value": "skip", "label": "跳过（不做检验）"},
                {"value": "warn", "label": "警告（保留变量，仅提示）"},
                {"value": "remove", "label": "移除（迭代移除异常变量）"}
            ],
            "default": "warn",
            "description": "系数方向异常（负系数）的变量处理方式：跳过/警告/迭代移除",
            "stage": "model_training"
        },
        {
            "name": "max_validation_iterations",
            "type": "number",
            "label": "最大迭代次数",
            "label_en": "Max Validation Iterations",
            "default": 10,
            "min": 1,
            "max": 20,
            "step": 1,
            "show_when": {
                "$or": [
                    {"significance_mode": "remove"},
                    {"coefficient_direction_mode": "remove"}
                ]
            },
            "description": "迭代验证的最大循环次数，防止无限循环（仅当启用迭代移除模式时生效）",
            "stage": "model_training"
        },
        
        # Score Scaling
        {
            "name": "base_score",
            "type": "number",
            "label": "基准分",
            "label_en": "Base Score",
            "default": 600,
            "min": 300,
            "max": 1000,
            "step": 10,
            "description": "基准Odds对应的分数",
            "stage": "score_scaling"
        },
        {
            "name": "base_odds",
            "type": "number",
            "label": "基准Odds",
            "label_en": "Base Odds",
            "default": 20,
            "min": 5,
            "max": 100,
            "step": 5,
            "description": "好坏比（Good:Bad）",
            "stage": "score_scaling"
        },
        {
            "name": "pdo",
            "type": "number",
            "label": "PDO",
            "label_en": "PDO",
            "default": 50,
            "min": 20,
            "max": 100,
            "step": 5,
            "description": "Odds翻倍时分数的变化量（行业标准50分）",
            "stage": "score_scaling"
        },
        
        # Model Evaluation - Score Distribution Display
        {
            "name": "score_bin_method",
            "type": "select",
            "label": "评分分布分箱",
            "label_en": "Score Distribution Binning",
            "options": [
                {"value": "equal_width", "label": "等宽分箱"},
                {"value": "equal_frequency", "label": "等频分箱"}
            ],
            "default": "equal_width",
            "description": "评分分布图的分箱方法：等宽分箱区间宽度一致（如50分一档），等频分箱每个区间样本数相近",
            "stage": "model_evaluation"
        },
        {
            "name": "score_distribution_bins",
            "type": "number",
            "label": "分布图分箱数",
            "label_en": "Distribution Bins",
            "default": 8,
            "min": 5,
            "max": 20,
            "step": 1,
            "description": "评分分布图的分箱数量（等宽分箱时生效）。分数范围较大时可增加分箱数",
            "stage": "model_evaluation",
            "show_when": {"score_bin_method": "equal_width"}
        },
        {
            "name": "ranking_analysis_bins",
            "type": "number",
            "label": "排序分析分组数",
            "label_en": "Ranking Analysis Bins",
            "default": 10,
            "min": 5,
            "max": 20,
            "step": 1,
            "description": "排序性分析的分组数量（等频分箱）。行业标准为10组（Decile），一般无需调整",
            "stage": "model_evaluation"
        },
        
        # Model Evaluation - Overfit Detection (Advanced)
        {
            "name": "overfit_ks_threshold",
            "type": "number",
            "label": "过拟合KS阈值",
            "label_en": "Overfit KS Threshold",
            "default": 0.05,
            "min": 0.02,
            "max": 0.15,
            "step": 0.01,
            "description": "训练集与测试集KS差值超过此阈值时发出过拟合警告",
            "stage": "model_evaluation",
            "advanced": True
        },
        {
            "name": "overfit_auc_threshold",
            "type": "number",
            "label": "过拟合AUC阈值",
            "label_en": "Overfit AUC Threshold",
            "default": 0.03,
            "min": 0.01,
            "max": 0.10,
            "step": 0.01,
            "description": "训练集与测试集AUC差值超过此阈值时发出过拟合警告",
            "stage": "model_evaluation",
            "advanced": True
        }
    ],
    
    # Output Definitions
    "outputs": [
        {"id": "preprocessing_info", "name": "预处理信息", "type": "json"},
        {"id": "iv_table", "name": "IV值表", "type": "table"},
        {"id": "woe_bins", "name": "WOE分箱规则", "type": "json"},
        {"id": "feature_selection", "name": "特征筛选结果", "type": "json"},
        {"id": "model_summary", "name": "模型摘要", "type": "table"},
        {"id": "scorecard", "name": "评分卡", "type": "table"},
        {"id": "model_metrics", "name": "模型指标", "type": "metrics"},
        {"id": "roc_curve", "name": "ROC曲线", "type": "chart"},
        {"id": "ks_curve", "name": "KS曲线", "type": "chart"},
        {"id": "score_distribution", "name": "分数分布", "type": "chart"}
    ]
}


# =============================================================================
# SOP Prompt Template
# =============================================================================

SCORECARD_SOP_PROMPT_TEMPLATE = """
# Role
你是一名资深的银行风控建模专家，精通信用评分卡开发。

# Instruction
请使用上传的数据集构建一张标准的信用评分卡（Credit Scorecard）。
必须严格遵守以下标准工作流进行处理，不要跳过任何步骤：

## 阶段1：数据清洗与预处理
- **特殊缺失值替换**：将以下特殊值视为缺失值并替换为NaN：{special_values}
- **分类变量识别**：
  - 自动识别分类变量（object/category类型、小范围整数编码、稀疏编码等）
  - 用户指定的分类变量：{force_categorical}（如有指定，优先作为分类变量处理）
- 检查缺失值，对缺失率 > {missing_threshold} 的变量进行剔除
- 检查异常值，使用IQR方法识别（计算Q1、Q3，标记超出1.5倍IQR范围的值）
- 数据分割（支持三种模式）：
  - **手动标注模式**：如果数据包含 sample_type 列（train/test/oot），按该列分割
  - **智能OOT模式**：如果指定了时间列，自动选取最近时间段的数据作为OOT验证集
  - **随机分割模式**：随机分割为训练集和测试集（比例 {test_ratio}）
- OOT（Out-of-Time）验证集用于评估模型的时间稳定性

## 阶段2：特征工程（核心步骤）
- 必须使用 **Weight of Evidence (WOE)** 方法对所有连续变量和分类变量进行转换
- 使用 {binning_method} 分箱方法进行处理，最大分箱数 {bin_num_limit}
- 必须计算每个变量的 **Information Value (IV)**
- 检查WOE单调性，对非单调变量进行标记或调整
- 生成WOE分箱可视化图

## 阶段3：特征筛选
- 仅保留 IV 值在 [{iv_lower}, {iv_upper}] 之间的变量
- 检查变量间的多重共线性（VIF），剔除 VIF > {vif_threshold} 的变量
- 检查变量间相关性，剔除相关系数 > {corr_threshold} 的冗余变量

## 阶段4：模型训练
- 使用 **逻辑回归 (Logistic Regression)** 算法（监管要求的解释性模型，禁止使用XGBoost/RandomForest）
- 使用逐步回归（Stepwise）进行特征选择（方向：{stepwise_direction}）
- 检验所有系数的显著性（p < {significance_level}），剔除不显著变量
- 验证系数方向与业务逻辑一致（WOE为正时系数应为正，表示风险越高得分越低）
- 对系数方向异常的变量进行标记和说明

## 阶段5：评分刻度转换（Scaling）
- 设定 Base Score = {base_score} points at odds {base_odds}:1
- 设定 PDO (Points to Double the Odds) = {pdo}
- 输出最终的评分卡刻度表

## 阶段6：模型评估
- 分别计算训练集、测试集（及OOT验证集，如有）的评估指标
- 绘制 ROC 曲线，计算 AUC 值
- 计算 KS 值 (Kolmogorov-Smirnov)，绘制 KS 曲线
- 计算 Gini 系数 (Gini = 2*AUC - 1)
- 检测过拟合：若训练集KS显著高于测试集KS（差值>0.05），发出警告
- 分析分数分布，按分数段统计bad_rate

## 阶段7：报告生成
- 汇总各阶段关键结果
- 生成多数据集指标对比表（训练集/测试集/OOT）
- 输出完整的评分卡表格
- 生成ROC曲线、KS曲线、分数分布图的数据
- 如有模型质量警告（过拟合、系数异常等），在报告中明确标注

# Constraints
- 所有步骤必须按顺序执行，不可跳过
- 必须使用逻辑回归，禁止使用其他算法
- 所有入模变量必须通过显著性检验（p < {significance_level}）
- 系数方向必须与业务逻辑一致
- 输出结果需包含完整的评分卡表格
- 必须对训练集和测试集分别评估，检测过拟合风险

# Data
{workspace_files_info}

# Available Local Components (优先使用以下项目组件)

## 1. WOE计算器 - deepanalyze.analysis.woe.WOECalculator
```python
from deepanalyze.analysis.woe import WOECalculator

# 计算单个特征的WOE和IV
result = WOECalculator.calculate_woe(
    df,                    # DataFrame
    feature='age',         # 特征名
    target='target',       # 目标变量名（0/1二分类）
    n_bins=5,              # 分箱数量
    method='quantile'      # 分箱方法: 'quantile'/'uniform'/'kmeans'
)
# 返回: {{'iv': float, 'woe': list, 'bins': list[dict], 'status': 'success', 'interpretation': str}}
```

## 2. IV分析器 - deepanalyze.analysis.iv_analysis.IVAnalyzer
```python
from deepanalyze.analysis.iv_analysis import IVAnalyzer

# 批量分析多个特征的IV值
result = IVAnalyzer.analyze_features(
    df,                    # DataFrame
    target='target',       # 目标变量名
    features=None,         # 特征列表（None=所有数值列）
    n_bins=5,
    method='quantile'
)
# 返回: {{'results': list[dict], 'summary': dict, 'status': 'success'}}

# 基于IV阈值筛选特征
result = IVAnalyzer.feature_selection(
    df,
    target='target',
    iv_threshold=0.02,     # IV阈值
    features=None
)
# 返回: {{'selected_features': list[str], 'selection_details': list[dict]}}
```

## 3. 相关性分析器 - deepanalyze.analysis.feature_correlation.CorrelationAnalyzer
```python
from deepanalyze.analysis.feature_correlation import CorrelationAnalyzer

# 计算相关性矩阵
corr_matrix = CorrelationAnalyzer.calculate_correlation(
    df,
    feature_cols=None,     # 特征列（None=所有数值列）
    method='pearson'       # 'pearson'/'spearman'/'kendall'
)

# 查找高相关特征对
high_corr_pairs = CorrelationAnalyzer.find_high_correlation(
    corr_matrix,
    threshold=0.7          # 相关系数阈值
)
# 返回: list[(feature1, feature2, corr_value)]

# 基于相关性过滤特征
df_filtered, removed, pairs = CorrelationAnalyzer.filter_by_correlation(
    df,
    threshold=0.7,
    method='pearson',
    keep='first'           # 'first'保留第一个，'none'都移除
)
```

## 4. VIF分析器 - deepanalyze.analysis.feature_correlation.VIFAnalyzer
```python
from deepanalyze.analysis.feature_correlation import VIFAnalyzer

# 计算VIF（方差膨胀因子）
vif_table = VIFAnalyzer.calculate_vif(df, feature_cols=None)
# 返回: DataFrame with columns ['feature', 'VIF']

# 迭代移除高VIF特征
df_filtered, removed_features, final_vif = VIFAnalyzer.filter_by_vif(
    df,
    threshold=5.0,         # VIF阈值
    max_iterations=10
)
```

## 5. 特征分箱器 - deepanalyze.analysis.feature_binning.FeatureBinner
```python
from deepanalyze.analysis.feature_binning import FeatureBinner

# 自动分箱
result = FeatureBinner.auto_bin(
    df,
    feature='age',
    n_bins=5,
    method='quantile'      # 'quantile'/'uniform'/'kmeans'
)
# 返回: {{'bin_edges': list, 'bin_labels': list, 'bin_statistics': list[dict]}}

# 自定义分箱
result = FeatureBinner.custom_bin(
    df,
    feature='age',
    bins=[0, 25, 35, 45, 60, 100]
)
```

## 6. 数据预处理器 - deepanalyze.analysis.preprocessing
```python
from deepanalyze.analysis.preprocessing import (
    DatetimeProcessor,     # 日期时间特征提取
    TextProcessor,         # 文本特征提取
    CategoricalProcessor,  # 分类变量处理
    ColumnCleaner,         # 列清洗（删除常量列、ID列等）
    GeneralPreprocessor    # 通用预处理器
)

# 示例：日期特征提取
result = DatetimeProcessor.extract_features(df, 'date_col')

# 示例：分类变量编码
result = CategoricalProcessor.one_hot_encode(df, 'category_col')
```

## 重要提示
- 优先使用上述本地组件，它们已针对评分卡开发场景优化
- 对于WOE分箱，如需更高精度可使用scorecardpy库作为补充
- 所有组件返回结果都包含status字段，请检查是否为'success'
"""


# =============================================================================
# Helper Functions
# =============================================================================

def get_task_meta() -> TaskMeta:
    """
    Get scorecard development task metadata.
    
    Returns:
        Task metadata dictionary
    """
    return SCORECARD_TASK_META


def get_sop_prompt_template() -> str:
    """
    Get SOP prompt template for LLM.
    
    Returns:
        Prompt template string
    """
    return SCORECARD_SOP_PROMPT_TEMPLATE


def build_sop_prompt(
    params: dict[str, str | int | float | bool],
    workspace_files_info: str = ""
) -> str:
    """
    Build SOP prompt with filled parameters.
    
    Args:
        params: Dictionary of parameter values
        workspace_files_info: Information about workspace files
        
    Returns:
        Filled prompt string
    """
    # Default values
    defaults: dict[str, str | int | float | bool | list] = {
        "special_values": "-9999,-999,-99999,-998,-9998,-99998",
        "force_categorical": [],
        "missing_threshold": 0.5,
        "test_ratio": 0.3,
        "binning_method": "tree",
        "bin_num_limit": 8,
        "iv_lower": 0.02,
        "iv_upper": 0.5,
        "vif_threshold": 5,
        "corr_threshold": 0.7,
        "use_stepwise": True,
        "stepwise_direction": "both",
        "significance_level": 0.05,
        "base_score": 600,
        "base_odds": 50,
        "pdo": 50,
        "use_fico_range": True,
        "fico_min": 300,
        "fico_max": 850,
        "workspace_files_info": workspace_files_info
    }
    
    # Merge with provided params
    filled_params: dict[str, str | int | float | bool] = {**defaults, **params}
    filled_params["workspace_files_info"] = workspace_files_info
    
    # Format prompt
    return SCORECARD_SOP_PROMPT_TEMPLATE.format(**filled_params)


def get_stage_info(stage_id: str) -> StageDict | dict[str, str | int]:
    """
    Get information about a specific stage.
    
    Args:
        stage_id: Stage identifier
        
    Returns:
        Stage information dictionary
    """
    for stage in SCORECARD_TASK_META["stages"]:
        if stage["id"] == stage_id:
            return stage
    return {}


def get_param_info(param_name: str) -> ParamDict | dict[str, str | int | float | bool]:
    """
    Get information about a specific parameter.
    
    Args:
        param_name: Parameter name
        
    Returns:
        Parameter information dictionary
    """
    # Check required params
    for param in SCORECARD_TASK_META["required_params"]:
        if param.get("name") == param_name:
            return param
    
    # Check optional params
    for param in SCORECARD_TASK_META["optional_params"]:
        if param.get("name") == param_name:
            return param
    
    return {}


def validate_params(params: dict[str, str | int | float | bool]) -> list[str]:
    """
    Validate parameters against metadata constraints.
    
    Args:
        params: Dictionary of parameter values
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []
    
    # Check required params
    for param in SCORECARD_TASK_META["required_params"]:
        param_name = param.get("name", "")
        is_required = param.get("required", False)
        allow_empty = param.get("allow_empty", False)
        if is_required and param_name not in params:
            if not allow_empty:
                errors.append(f"缺少必需参数: {param.get('label', '')}")
    
    # Check numeric constraints
    for param in SCORECARD_TASK_META["optional_params"]:
        param_name = param.get("name", "")
        if param_name in params and param.get("type") == "number":
            value = params[param_name]
            if isinstance(value, (int, float)):
                min_val = param.get("min")
                max_val = param.get("max")
                if min_val is not None and value < min_val:
                    errors.append(f"{param.get('label', '')} 不能小于 {min_val}")
                if max_val is not None and value > max_val:
                    errors.append(f"{param.get('label', '')} 不能大于 {max_val}")
    
    return errors


# =============================================================================
# Export
# =============================================================================

__all__ = [
    'SCORECARD_TASK_META',
    'SCORECARD_SOP_PROMPT_TEMPLATE',
    'get_task_meta',
    'get_sop_prompt_template',
    'build_sop_prompt',
    'get_stage_info',
    'get_param_info',
    'validate_params'
]
