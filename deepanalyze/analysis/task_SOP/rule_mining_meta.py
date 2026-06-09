"""
Rule Mining Task Metadata and SOP Prompt Template

Provides task definition for WebUI integration:
- Task metadata (stages, parameters, outputs)
- LLM SOP prompt template for guided execution
- Chat entry configuration (trigger keywords, summary)
"""

from typing import Any, Dict, List

# 导入统一类型定义（可选，用于类型提示）
# from .types import TaskMetaDict

# =============================================================================
# Task Metadata Definition
# =============================================================================

RULE_MINING_TASK_META: Dict[str, Any] = {
    # Basic Info
    "task_id": "rule_mining",
    "task_name": "规则挖掘",
    "task_name_en": "Rule Mining",
    "description": "基于决策树/阈值分箱的风控策略规则挖掘与效果评估",
    "category": "风控建模",
    "icon": "🔍",
    "estimated_time": "3-10分钟",
    
    # ========== Chat 入口配置（新增） ==========
    "task_type": "sop",  # 任务类型：sop（有固定流程）
    "trigger_keywords": [
        "规则挖掘", "挖掘规则", "风控规则", "策略规则", "策略挖掘",
        "rule mining", "mining rules", "风险规则", "拒绝规则",
        "黑名单规则", "反欺诈规则", "欺诈规则"
    ],
    "chat_summary": "从数据中自动挖掘风控策略规则，支持单特征阈值规则和多特征组合规则，输出最优规则集及效果评估",
    "required_params_summary": "数据文件、目标变量（0/1二分类，1为坏样本）",
    
    # Workflow Stages (v2.0: 合并 filtering_rules + evaluating_rules 为 rule_filtering)
    "stages": [
        {"id": "preprocessing", "name": "数据预处理", "progress_weight": 10},
        {"id": "feature_engineering", "name": "特征工程（可选）", "progress_weight": 12},
        {"id": "generating_rules", "name": "规则生成", "progress_weight": 28},
        {"id": "rule_filtering", "name": "规则筛选", "progress_weight": 20},
        {"id": "selecting_rules", "name": "最优选择", "progress_weight": 18},
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
            "stage": "preprocessing"
        },
        {
            "name": "weight_col",
            "type": "column_select",
            "label": "权重列",
            "label_en": "Weight Column",
            "description": "样本权重列（可选，无则默认为1）",
            "required": False,
            "allow_empty": True,
            "stage": "preprocessing"
        },
        {
            "name": "exclude_cols",
            "type": "column_multi_select",
            "label": "排除变量",
            "label_en": "Exclude Columns",
            "description": "额外指定不参与规则挖掘的列。系统会自动检测并排除ID列、时间列、样本标识列等非特征列，此处可补充指定其他需排除的列",
            "required": False,
            "allow_empty": True,
            "stage": "preprocessing"
        }
    ],
    
    # Optional Parameters
    "optional_params": [
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
            "description": "当坏样本率<10%时建议启用。auto模式会根据坏账率自动决定是否使用类别加权（bad_rate<10%→class_weight，否则→不处理）",
            "stage": "preprocessing",
            "advanced": False
        },
        # Data Split Parameters (与评分卡任务保持一致)
        {
            "name": "test_ratio",
            "type": "number",
            "label": "测试集比例",
            "label_en": "Test Ratio",
            "default": 0.3,
            "min": 0,
            "max": 0.5,
            "step": 0.05,
            "allow_empty": True,
            "description": "测试集占总数据的比例（0或留空表示不划分测试集，全部用于训练）",
            "stage": "preprocessing"
        },
        {
            "name": "sample_type_col",
            "type": "column_select",
            "label": "样本类型列（手动划分）",
            "label_en": "Sample Type Column",
            "default": None,
            "required": False,
            "allow_empty": True,
            "description": "用于手动划分训练集/测试集/OOT验证集的列。列值应为 train/test/oot（或0/1/2）。设置后将忽略测试集比例和时间列参数",
            "stage": "preprocessing"
        },
        # P1-5: OOT 验证相关参数
        {
            "name": "time_col",
            "type": "column_select",
            "label": "时间列（智能OOT划分）",
            "label_en": "Time Column (Smart OOT Split)",
            "default": None,
            "required": False,
            "allow_empty": True,
            "description": "用于智能OOT划分的时间列。设置后将按时间顺序自动选取最近的数据作为OOT验证集。支持日期(YYYY-MM-DD)、数值(YYYYMM)等格式",
            "stage": "preprocessing",
            "show_when": {"sample_type_col": None}
        },
        {
            "name": "oot_ratio",
            "type": "number",
            "label": "OOT验证集比例",
            "label_en": "OOT Validation Ratio",
            "default": 0.0,
            "min": 0.0,
            "max": 0.3,
            "step": 0.05,
            "allow_empty": True,
            "description": "OOT验证集占总数据的比例（0表示不划分OOT）。仅在设置时间列时生效",
            "stage": "preprocessing",
            "show_when": {"time_col": {"$ne": None}}
        },
        
        # Mining Mode Selection
        {
            "name": "mining_mode",
            "type": "radio",
            "label": "规则挖掘模式",
            "label_en": "Mining Mode",
            "options": [
                {"value": "single", "label": "🎯 单特征规则（阈值分箱）"},
                {"value": "multi", "label": "🌲 多特征组合规则（决策树）"}
            ],
            "default": "multi",
            "description": "单特征规则简单直观，多特征规则可捕捉交互效应",
            "stage": "generating_rules"
        },
        
        # Feature Engineering Toggle
        {
            "name": "enable_feature_engineering",
            "type": "checkbox",
            "label": "启用特征工程预处理",
            "label_en": "Enable Feature Engineering",
            "default": True,
            "description": "对原始数据进行缺失值处理、IV筛选等预处理（推荐启用，可自动筛选有效特征）",
            "stage": "feature_engineering"
        },
        
        # Feature Engineering Parameters
        {
            "name": "special_values",
            "type": "text",
            "label": "特殊缺失值",
            "label_en": "Special Missing Values",
            "default": "-9999,-999,-99999,-998,-9998,-99998",
            "allow_empty": True,
            "show_when": {"enable_feature_engineering": True},
            "description": "额外视为缺失值的特殊数值，逗号分隔。系统已默认将 NaN、None、空字符串识别为缺失值，此处可补充业务系统中常见的缺失标记（如-9999、-999等）。留空表示不额外指定",
            "stage": "preprocessing"
        },
        {
            "name": "force_categorical",
            "type": "column_multi_select",
            "label": "指定分类变量",
            "label_en": "Force Categorical Columns",
            "default": [],
            "allow_empty": True,
            "show_when": {"enable_feature_engineering": True},
            "description": "手动指定为分类变量的列（如省份编码、行业编码等）。用于系统无法自动识别的编码型分类变量",
            "stage": "preprocessing"
        },
        {
            "name": "force_numeric",
            "type": "column_multi_select",
            "label": "指定数值变量",
            "label_en": "Force Numeric Columns",
            "default": [],
            "allow_empty": True,
            "show_when": {"enable_feature_engineering": True},
            "description": "手动指定为数值变量的列（如账户数、交易次数等）。用于防止系统将有序数值特征误判为分类变量进行One-Hot编码",
            "stage": "preprocessing"
        },
        {
            "name": "missing_threshold",
            "type": "number",
            "label": "缺失率阈值",
            "label_en": "Missing Threshold",
            "default": 0.5,
            "min": 0.1,
            "max": 0.9,
            "step": 0.1,
            "show_when": {"enable_feature_engineering": True},
            "description": "缺失率超过此阈值的变量将被剔除",
            "stage": "feature_engineering"
        },
        {
            "name": "iv_threshold",
            "type": "number",
            "label": "IV阈值",
            "label_en": "IV Threshold",
            "default": 0.02,
            "min": 0.01,
            "max": 0.5,
            "step": 0.01,
            "show_when": {"enable_feature_engineering": True},
            "description": "IV值低于此阈值的变量将被剔除",
            "stage": "feature_engineering"
        },
        
        # Single-Variable Mode Parameters
        {
            "name": "n_bins",
            "type": "number",
            "label": "分箱数量",
            "label_en": "Number of Bins",
            "default": 10,
            "min": 5,
            "max": 20,
            "step": 1,
            "show_when": {"mining_mode": "single"},
            "description": "每个特征的分箱数量",
            "stage": "generating_rules"
        },
        {
            "name": "bin_method",
            "type": "select",
            "label": "分箱方式",
            "label_en": "Binning Method",
            "options": [
                {"value": "quantile", "label": "等频分箱", "description": "按样本数量均分，每组样本量相同，适合分布均匀的特征"},
                {"value": "uniform", "label": "等距分箱", "description": "按数值范围均分，每组区间宽度相同，适合分布均匀的特征"},
                {"value": "chi2", "label": "卡方分箱", "description": "基于目标变量的统计显著性合并分箱，生成更有区分度的阈值"},
                {"value": "tree", "label": "决策树最佳分箱", "description": "使用单变量决策树寻找最优分割点，生成最大化信息增益的阈值"},
                {"value": "custom", "label": "自定义阈值", "description": "手动指定每个特征的分箱阈值，JSON格式: {\"feature_name\": [threshold1, threshold2, ...]}"}
            ],
            "default": "quantile",
            "show_when": {"mining_mode": "single"},
            "description": "分箱方法选择",
            "stage": "generating_rules"
        },
        {
            "name": "rule_directions",
            "type": "select",
            "label": "规则方向",
            "label_en": "Rule Directions",
            "options": [
                {"value": "both", "label": "双向（<= 和 >）"},
                {"value": "<=", "label": "仅 <="},
                {"value": ">", "label": "仅 >"}
            ],
            "default": "both",
            "show_when": {"mining_mode": "single"},
            "description": "生成规则的方向",
            "stage": "generating_rules"
        },
        {
            "name": "custom_thresholds",
            "type": "string",
            "label": "自定义阈值",
            "label_en": "Custom Thresholds",
            "default": "",
            "show_when": {"bin_method": "custom"},
            "description": "每个特征的自定义分箱阈值，JSON格式: {\"feature_name\": [threshold1, threshold2, ...]}",
            "stage": "generating_rules"
        },
        
        # Multi-Variable Mode Parameters
        {
            "name": "use_full_tree",
            "type": "radio",
            "label": "多特征挖掘方法",
            "label_en": "Multi-Variable Mining Method",
            "options": [
                {"value": True, "label": "全特征树 - 使用所有特征训练单棵决策树，速度快，可视化清晰"},
                {"value": False, "label": "组合树 - 遍历特征组合训练多棵树，规则更丰富，速度较慢"}
            ],
            "default": False,
            "stage": "generating_rules"
        },
        {
            "name": "n_vars",
            "type": "number",
            "label": "变量组合数",
            "label_en": "Variables per Combination",
            "default": 2,
            "min": 2,
            "max": 5,
            "step": 1,
            "show_when": {"mining_mode": "multi"},
            "description": "每条规则包含的变量数量",
            "stage": "generating_rules"
        },
        {
            "name": "max_depth",
            "type": "number",
            "label": "决策树深度",
            "label_en": "Max Tree Depth",
            "default": 3,
            "min": 2,
            "max": 8,
            "step": 1,
            "show_when": {"mining_mode": "multi"},
            "description": "决策树的最大深度",
            "stage": "generating_rules"
        },
        {
            "name": "min_samples_leaf",
            "type": "number",
            "label": "叶节点最小样本比例",
            "label_en": "Min Samples Leaf Ratio",
            "default": 0.01,
            "min": 0.001,
            "max": 0.05,
            "step": 0.001,
            "show_when": {"mining_mode": "multi"},
            "description": "叶节点最小样本占比，降低此值可生成更多规则",
            "stage": "generating_rules"
        },
        
        # Common Filtering Parameters (used in rule_filtering stage - 合并后的阶段)
        {
            "name": "min_lift_filter",
            "type": "number",
            "label": "最小Lift阈值（单条规则）",
            "label_en": "Min Lift Threshold (Single Rule)",
            "default": 3.5,
            "min": 1.0,
            "max": 10.0,
            "step": 0.5,
            "description": "Lift低于此阈值的单条规则将被过滤",
            "stage": "rule_filtering"
        },
        {
            "name": "max_hit_rate_filter",
            "type": "number",
            "label": "最大命中率阈值（单条规则）",
            "label_en": "Max Hit Rate (Single Rule)",
            "default": 0.03,
            "min": 0.01,
            "max": 0.50,
            "step": 0.01,
            "description": "命中率超过此阈值的单条规则将被过滤",
            "stage": "rule_filtering"
        },
        {
            "name": "max_hit_rate_select",
            "type": "number",
            "label": "最大命中率（规则集）",
            "label_en": "Max Hit Rate (Rule Set)",
            "default": 0.2,
            "min": 0.05,
            "max": 0.5,
            "step": 0.05,
            "description": "规则集的命中率上限（业务目标约束）",
            "stage": "selecting_rules"
        },
        # 风险目标参数（规则集级别约束）
        {
            "name": "min_recall_ruleset",
            "type": "number",
            "label": "最低召回率（规则集）",
            "label_en": "Min Recall (Rule Set)",
            "default": None,
            "min": 0.05,
            "max": 0.8,
            "step": 0.05,
            "required": False,
            "allow_empty": True,
            "description": "规则集需达到的最低坏样本召回率（可选，风险覆盖目标）",
            "stage": "selecting_rules"
        },
        {
            "name": "min_bad_rate_ruleset",
            "type": "number",
            "label": "最低坏账率（规则集）",
            "label_en": "Min Bad Rate (Rule Set)",
            "default": None,
            "min": 0.005,
            "max": 0.9,
            "step": 0.005,
            "required": False,
            "allow_empty": True,
            "description": "规则集累计坏账率不低于此值（可选，确保规则集足够精准）",
            "stage": "selecting_rules",
            "group": "bad_rate_range"
        },
        {
            "name": "target_bad_rate_ruleset",
            "type": "number",
            "label": "目标坏账率（规则集）",
            "label_en": "Target Bad Rate (Rule Set)",
            "default": None,
            "min": 0.001,
            "max": 0.5,
            "step": 0.001,
            "required": False,
            "allow_empty": True,
            "description": "策略应用后的目标坏账率，系统自动计算所需召回率。公式: 召回率 = 1 - (目标坏账率/原始坏账率) × (1-最大命中率)",
            "stage": "selecting_rules",
            "tooltip": "以终为始：设置期望达到的坏账率，系统自动推导所需的召回率目标"
        },
        {
            "name": "min_lift_ruleset",
            "type": "number",
            "label": "最低提升度（规则集）",
            "label_en": "Min Lift (Rule Set)",
            "default": None,
            "min": 1.5,
            "max": 10.0,
            "step": 0.5,
            "required": False,
            "allow_empty": True,
            "description": "规则集需达到的最低整体提升度（可选，区别于单条规则的min_lift_filter）",
            "stage": "selecting_rules"
        },
        {
            "name": "allow_overlap",
            "type": "checkbox",
            "label": "允许规则重叠",
            "label_en": "Allow Rule Overlap",
            "default": False,
            "description": "允许多条规则命中相同样本（独立选择模式）。关闭则使用贪婪算法，每条规则选中后移除其命中样本",
            "stage": "selecting_rules"
        },
        
        # P1-5: OOT 验证参数（selecting_rules 阶段）
        {
            "name": "enable_oot_validation",
            "type": "checkbox",
            "label": "启用OOT稳定性验证",
            "label_en": "Enable OOT Validation",
            "default": False,
            "description": "在OOT验证集上评估规则的时间稳定性（命中率跨期变化）",
            "stage": "selecting_rules",
            "advanced": True,
            "disabled_when": {
                "$and": [
                    {"sample_type_col": None},
                    {"time_col": None}
                ]
            },
            "disabled_reason": "需先在数据预处理阶段配置「时间列」（智能OOT划分）或「样本类型列」（含oot标注），否则无OOT数据可用"
        },
        {
            "name": "enable_stability_filter",
            "type": "checkbox",
            "label": "基于稳定性筛选规则",
            "label_en": "Enable Stability Filter",
            "default": False,
            "description": "启用后，将过滤掉在OOT上表现不稳定的规则（命中率CV超过阈值）",
            "stage": "selecting_rules",
            "show_when": {"enable_oot_validation": True},
            "advanced": True,
            "disabled_when": {
                "$and": [
                    {"sample_type_col": None},
                    {"time_col": None}
                ]
            },
            "disabled_reason": "需先在数据预处理阶段配置「时间列」或「样本类型列」以获得OOT数据"
        },
        {
            "name": "cv_threshold",
            "type": "number",
            "label": "变异系数阈值",
            "label_en": "CV Threshold",
            "default": 0.35,
            "min": 0.2,
            "max": 0.5,
            "step": 0.05,
            "description": "命中率变异系数超过此阈值的规则将被标记为不稳定。CV=标准差/均值，越小越稳定",
            "stage": "selecting_rules",
            "show_when": {"enable_oot_validation": True},
            "advanced": True
        },
        
        # Advanced: Prior Rules Evaluation (used in report_generation stage for prior_analysis)
        {
            "name": "prior_rules",
            "type": "prior_rules_input",
            "label": "先验规则（可选）",
            "label_en": "Prior Rules",
            "default": "",
            "description": "已有的生产规则列表。支持手动输入（每行一条表达式）或上传CSV文件（结构化/表达式格式）",
            "placeholder": "例如：\n(age > 30)\n(income < 5000)",
            "stage": "report_generation",
            "advanced": True,
            "options": {
                "accept_formats": [".csv"],
                "template_download": True,
                "enable_validation": True
            }
        },
        
        # Advanced: Amount Column for Amount Analysis (used in report_generation stage for amount_analysis)
        {
            "name": "amount_col",
            "type": "column_combobox",
            "label": "损失金额列（可选）",
            "label_en": "Loss Amount Column",
            "description": "用于金额维度分析的预期损失金额列（如逾期金额、风险敞口金额）。启用后将计算规则拦截的损失金额、金额召回率、金额Lift等指标。支持从数据列中选择或手动输入列名。注意：请确保该列为非负数值类型且无缺失值（NaN会被跳过导致指标偏差，负值会拉低总金额导致Lift异常）",
            "required": False,
            "allow_empty": True,
            "allow_custom": True,
            "stage": "report_generation",
            "advanced": True
        }
    ],
    
    # Output Definitions
    "outputs": [
        {"id": "preprocessing_info", "name": "预处理信息", "type": "json"},
        {"id": "iv_table", "name": "IV值表", "type": "table", "show_when": {"enable_feature_engineering": True}},
        {"id": "all_rules", "name": "全部候选规则", "type": "table"},
        {"id": "direction_table", "name": "特征分裂方向", "type": "table"},
        {"id": "filtered_rules", "name": "过滤后规则", "type": "table"},
        {"id": "evaluated_rules", "name": "评估后规则", "type": "table"},
        {"id": "optimal_rules", "name": "最优规则集", "type": "table"},
        {"id": "cumulative_chart", "name": "累计指标曲线", "type": "chart"},
        {"id": "prior_analysis", "name": "先验规则分析", "type": "table", "show_when": {"prior_rules": "not_empty"}},
        {"id": "amount_analysis", "name": "金额维度分析", "type": "json", "show_when": {"amount_col": "not_empty"}},
        {"id": "psi_report", "name": "规则PSI稳定性报告", "type": "table"},
        {"id": "tree_structure", "name": "决策树结构", "type": "json", "show_when": {"mining_mode": "multi", "use_full_tree": True}},
        {"id": "rule_source_stats", "name": "规则来源统计", "type": "json", "show_when": {"mining_mode": "multi", "use_full_tree": False}}
    ]
}


# =============================================================================
# SOP Prompt Template
# =============================================================================

RULE_MINING_SOP_PROMPT_TEMPLATE = """
# Role
你是一名资深的银行风控策略专家，精通策略规则挖掘与效果评估。

# Instruction
请使用上传的数据集进行策略规则挖掘，生成最优风控规则集。
必须严格遵守以下标准工作流进行处理，不要跳过任何步骤：

## 阶段0a：数据预处理（必需）
- 如有特征名映射文件，进行特征名映射
- 智能检测非建模列（ID列、时间列、常量列）并标记排除
- **特殊缺失值替换**：将以下特殊值视为缺失值并替换为NaN：{special_values}
- 检测日期时间列和文本列（只标记，不衍生，衍生在特征工程阶段执行）
- **数据质量自动检测**：
  - 分析缺失率分布（高缺失率特征数量）
  - 分析数据类型分布（数值型/分类型/文本型比例）
  - 分析特征基数（高基数分类变量数量）
  - 分析特征方差（常量列/低方差列数量）
  - 计算数据质量评分（0-100分）
  - 输出质量问题列表和改进建议
- **分类变量识别与编码**：
  - 自动识别分类变量（object/category类型、小范围整数编码、稀疏编码等）
  - 用户指定的分类变量：{force_categorical}（如有指定，优先作为分类变量处理）
  - 对分类变量进行One-Hot编码（如不启用特征工程，编码列以`_is_`标识）
- **数据集划分**（支持三种模式，按优先级执行）：
  1. 手动标注模式：如指定 sample_type_col，按列值划分 train/test/oot
  2. 智能OOT模式：如指定 time_col + oot_ratio>0，按时间排序取最近N%为OOT，剩余随机划分train/test
  3. 随机划分模式：按 test_ratio 随机划分 train/test

## 阶段0b：特征工程预处理（根据数据质量自动决定或用户指定）
**执行条件判断**：
- 如果 enable_feature_engineering=True（用户明确启用）：执行特征工程
- 如果 enable_feature_engineering=False 但数据质量评分 < 70：建议启用特征工程，并在日志中提示
- 如果 enable_feature_engineering=False 且数据质量评分 >= 70：跳过特征工程，数据质量良好

**特征工程步骤**（当执行时）：
- **日期时间衍生**：从日期列提取 year/month/dayofweek/hour/days_since（衍生列以`_dt_`标识）
- **文本特征衍生**：从文本列提取 length/word_count（衍生列以`_txt_`标识）
- **分类变量编码**：对分类变量进行One-Hot编码（衍生列以`_is_`标识）
- 检查缺失值，对缺失率 > {missing_threshold} 的变量进行剔除
- 计算所有变量的 IV 值
- 剔除 IV < {iv_threshold} 的弱变量

## 阶段1：规则生成

### 如果 mining_mode='single'（单特征规则模式）：
- 使用 {bin_method} 分箱方法，将每个数值特征分为 {n_bins} 个区间
- 对每个分箱阈值生成 {rule_directions} 方向的规则
- 规则格式：`(age <= 25)`, `(income > 50000)`

### 如果 mining_mode='multi'（多特征组合规则模式）：
- 对所有特征进行 {n_vars} 变量组合
- 对每个组合构建决策树（max_depth={max_depth}, min_samples_leaf={min_samples_leaf}）
- 从决策树叶节点向上回溯，提取规则路径
- 规则格式：`(age <= 25.5) & (income <= 5000.0) & (channel_is_A > 0.5)`

## 阶段2：规则过滤
- 对每个特征单独构建决策树，确定其"风险方向"
- 二值型特征（One-Hot编码`_is_`、文本关键词`_txt_has_`等）自动使用`==`方向
- 过滤方向不一致的规则
- 排除切分点为 (-inf, inf] 的无效特征
- 如有评分类变量，强制指定方向

## 阶段3：规则效果评估
- 计算每条规则的 recall（召回率）
- 计算每条规则的 bad_rate（坏账率）
- 计算每条规则的 lift（提升倍数）
- 计算每条规则的 hit_rate（命中率）
- 过滤条件：hit_rate < {max_hit_rate_filter} 且 lift > {min_lift_filter}

## 阶段4：最优规则选择

### 如果 allow_overlap=True（允许规则重叠，默认模式）：
- 独立选择模式：规则可以命中相同的样本
- 按 bad_rate 从高到低排序选择规则
- 使用集合追踪已被任意规则命中的唯一样本索引
- 累计命中率 = 被命中的唯一样本数 / 总样本数
- 当累计 hit_rate > {max_hit_rate_select} 时停止
- 优点：可选择更多规则，规则间允许重叠

### 如果 allow_overlap=False（贪婪算法模式）：
- 贪婪选择模式：每轮移除已命中样本
- 每轮选择当前剩余样本中 bad_rate 最高的规则
- 选中规则后，从数据集中移除该规则命中的样本
- 在剩余样本上重新计算各规则的 bad_rate
- 当累计 hit_rate > {max_hit_rate_select} 时停止
- 优点：规则间互斥，无重复覆盖

- 输出最终的最优规则集及累计指标

## 阶段5：报告生成
- 生成规则挖掘结果的可视化报告
- 输出最优规则集的累计指标曲线图（累计召回率、累计命中率、累计Lift）
- 输出规则详情表格（包含 used_var, rule, lift, dev_cum_recall, dev_cum_bad_rate, dev_cum_hit_rate）
- 生成规则效果对比分析（各规则的边际贡献）
- 输出数据格式需符合前端图表组件要求

# Constraints
- 所有步骤必须按顺序执行，不可跳过
- 阶段0b（特征工程）根据用户设置或数据质量自动决定是否执行
- 数据质量检测结果必须输出到预处理阶段的日志中
- 规则必须具有业务可解释性
- 最终规则集的累计命中率不超过 {max_hit_rate_select}
- 输出结果需包含完整的规则表格和累计指标
- 报告生成阶段为必需阶段，用于生成前端展示所需的图表数据

# Data
{workspace_files_info}

# Available Local Components (优先使用以下项目组件)

## 1. 规则挖掘器 - deepanalyze.analysis.task_SOP.RuleMiner
```python
from deepanalyze.analysis.task_SOP import RuleMiner

# 多特征组合规则挖掘（决策树方法）
miner = RuleMiner(
    max_depth=5,           # 决策树最大深度
    min_samples_leaf=0.01, # 叶节点最小样本比例
    n_vars=3               # 每条规则包含的变量数
)
rules_df = miner.mine_rules(
    df,
    target='target',
    feature_cols=None      # 特征列（None=自动选择）
)
# 返回: DataFrame with columns ['rule', 'used_var', 'support', 'confidence', ...]
```

## 2. 单变量规则挖掘器 - deepanalyze.analysis.task_SOP.SingleVarRuleMiner
```python
from deepanalyze.analysis.task_SOP import SingleVarRuleMiner

# 单特征阈值规则挖掘
miner = SingleVarRuleMiner(
    n_bins=10,             # 分箱数量
    bin_method='quantile', # 分箱方法: 'quantile'/'uniform'/'chi2'/'tree'
    rule_directions='both' # 规则方向: 'both'/'<='/'>'
)
rules_df = miner.mine_rules(df, target='target', feature_cols=None)
```

## 3. 规则评估器 - deepanalyze.analysis.task_SOP.RuleEvaluator
```python
from deepanalyze.analysis.task_SOP import RuleEvaluator

# 评估规则效果
evaluator = RuleEvaluator()
evaluated_rules = evaluator.evaluate(
    rules_df,              # 规则DataFrame
    df,                    # 数据DataFrame
    target='target'
)
# 返回: DataFrame with columns ['rule', 'recall', 'bad_rate', 'lift', 'hit_rate', ...]
```

## 4. 规则选择器 - deepanalyze.analysis.task_SOP.RuleSelector
```python
from deepanalyze.analysis.task_SOP import RuleSelector

# 选择最优规则集
selector = RuleSelector(
    max_hit_rate=0.1,      # 最大命中率（规则集）
    min_lift=2.0,          # 最小Lift阈值
    allow_overlap=True     # 是否允许规则重叠
)
optimal_rules = selector.select(
    evaluated_rules,       # 评估后的规则DataFrame
    df,
    target='target'
)
# 返回: DataFrame with columns ['rule', 'cum_recall', 'cum_hit_rate', 'cum_bad_rate', ...]
```

## 5. 特征工程器 - deepanalyze.analysis.task_SOP.FeatureEngineer
```python
from deepanalyze.analysis.task_SOP import FeatureEngineer

# 特征预处理（缺失值处理、IV筛选、One-Hot编码）
engineer = FeatureEngineer(
    missing_threshold=0.5,  # 缺失率阈值
    iv_threshold=0.02       # IV阈值
)
df_processed, feature_info = engineer.process(
    df,
    target='target',
    special_values=[-9999, -999]  # 特殊缺失值
)
```

## 6. IV分析器 - deepanalyze.analysis.iv_analysis.IVAnalyzer
```python
from deepanalyze.analysis.iv_analysis import IVAnalyzer

# 批量计算IV值
result = IVAnalyzer.analyze_features(df, target='target', n_bins=5)
# 返回: {{'results': list[dict], 'summary': dict}}

# 基于IV阈值筛选特征
result = IVAnalyzer.feature_selection(df, target='target', iv_threshold=0.02)
# 返回: {{'selected_features': list[str], 'removed_features': list[dict]}}
```

## 7. 数据预处理器 - deepanalyze.analysis.preprocessing
```python
from deepanalyze.analysis.preprocessing import (
    DatetimeProcessor,     # 日期时间特征提取（衍生列以_dt_标识）
    TextProcessor,         # 文本特征提取（衍生列以_txt_标识）
    CategoricalProcessor,  # 分类变量处理（One-Hot编码列以_is_标识）
    ColumnCleaner,         # 列清洗（删除常量列、ID列等）
    GeneralPreprocessor    # 通用预处理器
)

# 示例：分类变量One-Hot编码
result = CategoricalProcessor.one_hot_encode(df, 'channel')
# 生成列: channel_is_A, channel_is_B, ...

# 示例：文本关键词匹配
result = TextProcessor.extract_keywords(df, 'text_col', keywords=['fraud', 'risk'])
# 生成列: text_col_txt_has_fraud, text_col_txt_has_risk, ...
```

## 8. 特征分箱器 - deepanalyze.analysis.feature_binning.FeatureBinner
```python
from deepanalyze.analysis.feature_binning import FeatureBinner

# 自动分箱
result = FeatureBinner.auto_bin(df, feature='age', n_bins=10, method='quantile')
# 返回: {{'bin_edges': list, 'bin_statistics': list[dict]}}

# 自定义分箱
result = FeatureBinner.custom_bin(df, feature='age', bins=[0, 25, 35, 45, 60, 100])
```

## 重要提示
- 优先使用上述本地组件，它们已针对规则挖掘场景优化
- RuleMiner用于多特征组合规则，SingleVarRuleMiner用于单特征阈值规则
- 规则评估和选择请使用RuleEvaluator和RuleSelector，确保指标计算一致
- 所有组件返回结果都包含status字段（如适用），请检查是否为'success'
"""


# =============================================================================
# Helper Functions
# =============================================================================

def get_task_meta() -> Dict[str, Any]:
    """
    Get rule mining task metadata.
    
    Returns:
        Task metadata dictionary
    """
    return RULE_MINING_TASK_META


def get_sop_prompt_template() -> str:
    """
    Get SOP prompt template for LLM.
    
    Returns:
        Prompt template string
    """
    return RULE_MINING_SOP_PROMPT_TEMPLATE


def build_sop_prompt(
    params: Dict[str, Any],
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
    defaults = {
        "mining_mode": "multi",
        "enable_feature_engineering": True,
        "special_values": "-9999,-999,-99999,-998,-9998,-99998",
        "force_categorical": [],
        "missing_threshold": 0.5,
        "iv_threshold": 0.02,
        "n_bins": 10,
        "bin_method": "quantile",
        "rule_directions": "both",
        "n_vars": 3,
        "max_depth": 5,
        "min_samples_leaf": 0.01,
        "min_lift_filter": 2.0,
        "max_hit_rate_filter": 0.10,
        "max_hit_rate_select": 0.20,
        "allow_overlap": True,
        "workspace_files_info": workspace_files_info
    }
    
    # Merge with provided params
    filled_params = {**defaults, **params}
    filled_params["workspace_files_info"] = workspace_files_info
    
    # Format prompt
    return RULE_MINING_SOP_PROMPT_TEMPLATE.format(**filled_params)


def get_stage_info(stage_id: str) -> Dict[str, Any]:
    """
    Get information about a specific stage.
    
    Args:
        stage_id: Stage identifier
        
    Returns:
        Stage information dictionary
    """
    for stage in RULE_MINING_TASK_META["stages"]:
        if stage["id"] == stage_id:
            return stage
    return {}


def get_param_info(param_name: str) -> Dict[str, Any]:
    """
    Get information about a specific parameter.
    
    Args:
        param_name: Parameter name
        
    Returns:
        Parameter information dictionary
    """
    # Check required params
    for param in RULE_MINING_TASK_META["required_params"]:
        if param["name"] == param_name:
            return param
    
    # Check optional params
    for param in RULE_MINING_TASK_META["optional_params"]:
        if param["name"] == param_name:
            return param
    
    return {}


def validate_params(params: Dict[str, Any]) -> List[str]:
    """
    Validate parameters against metadata constraints.
    
    Args:
        params: Dictionary of parameter values
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check required params
    for param in RULE_MINING_TASK_META["required_params"]:
        if param.get("required", False) and param["name"] not in params:
            errors.append(f"缺少必需参数: {param['label']}")
    
    # Check numeric constraints
    for param in RULE_MINING_TASK_META["optional_params"]:
        if param["name"] in params and param["type"] == "number":
            value = params[param["name"]]
            if "min" in param and value < param["min"]:
                errors.append(f"{param['label']} 不能小于 {param['min']}")
            if "max" in param and value > param["max"]:
                errors.append(f"{param['label']} 不能大于 {param['max']}")
    
    return errors


# =============================================================================
# Export
# =============================================================================

__all__ = [
    'RULE_MINING_TASK_META',
    'RULE_MINING_SOP_PROMPT_TEMPLATE',
    'get_task_meta',
    'get_sop_prompt_template',
    'build_sop_prompt',
    'get_stage_info',
    'get_param_info',
    'validate_params'
]
