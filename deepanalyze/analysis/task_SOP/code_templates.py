# -*- coding: utf-8 -*-
"""
Pipeline阶段伪代码模板

为每个任务类型的各个阶段提供Python伪代码模板，
用于在前端展示Pipeline执行的逻辑。
"""

from typing import Dict, Any

# =============================================================================
# 评分卡开发任务 - 阶段伪代码模板
# =============================================================================

SCORECARD_CODE_TEMPLATES: Dict[str, str] = {
    "data_loading": '''# 数据加载与预处理
import pandas as pd
from deepanalyze.analysis.preprocessing import DataPreprocessor

# 加载数据
df = pd.read_csv("{file_path}")
print(f"数据集形状: {{df.shape}}")

# 初始化预处理器
preprocessor = DataPreprocessor(
    missing_threshold={missing_threshold}
)

# 特殊值替换（-9999/-999/-99999 等替换为 NaN）
df = preprocessor.replace_special_values(df)

# 缺失率/同值率质量筛选（移除缺失率或同值率 ≥ 0.95 的特征）
df, removed_features = preprocessor.var_filter(df, target_col="{target_col}")

# 数据集划分（支持 sample_type_col 手动标注 / time_col 时间划分 / 随机划分）
train_df, test_df, oot_df = preprocessor.split_data(
    df=df,
    target_col="{target_col}",
    sample_type_col="{sample_type_col}",
    test_ratio={test_ratio}
)
print(f"训练集: {{len(train_df)}}, 测试集: {{len(test_df)}}, OOT: {{len(oot_df) if oot_df is not None else 0}}")

# 异常值检测
outlier_info = preprocessor.detect_outliers(df=df, method='iqr', threshold=1.5)
print(f"检测到异常值特征数: {{len(outlier_info)}}")
''',

    "woe_binning": '''# WOE分箱
from deepanalyze.analysis.woe import WOETransformer

# 初始化WOE分箱器
woe_transformer = WOETransformer(
    method="{bin_method}",          # tree / chimerge / quantile
    bin_num_limit={bin_num_limit},  # 每个变量最大分箱数
    use_scorecardpy={use_high_precision}  # True=高精度模式(scorecardpy)
)

# 执行WOE分箱与转换
df_woe, bins, iv_table = woe_transformer.fit_transform(
    df=train_df,
    target_col="{target_col}",
    feature_cols=feature_cols
)

# IV值分布（strong≥0.1 / medium 0.02-0.1 / weak<0.02）
print(f"分箱特征数: {{len(iv_table)}}")
print(f"IV范围: {{iv_table['total_iv'].min():.4f}} - {{iv_table['total_iv'].max():.4f}}")
''',

    "feature_selection": '''# 特征筛选
# 注：逐步回归（stepwise）和系数方向验证在下一阶段（模型训练）中执行
from deepanalyze.analysis.feature_selection import FeatureSelector

# 初始化特征选择器
selector = FeatureSelector(
    iv_lower={iv_lower},        # IV 下限（低于此值剔除）
    iv_upper={iv_upper},        # IV 上限（高于此值可能存在数据泄露）
    corr_threshold={corr_threshold},  # 相关系数阈值（高相关特征对保留IV较高者）
    vif_threshold={vif_threshold}     # VIF 阈值（多重共线性筛选）
)

# 执行筛选：IV筛选 → 相关性筛选 → VIF筛选
selected_features, selection_detail = selector.select_features(
    df=df_woe, iv_table=iv_table, woe_cols=woe_cols
)

print(f"筛选前特征数: {{len(woe_cols)}}")
print(f"筛选后特征数: {{len(selected_features)}}")

# 筛选原因统计
for reason, count in selection_detail['removed_reasons'].items():
    print(f"  {{reason}}: {{count}} 个特征")
''',

    "model_training": '''# 模型训练
from deepanalyze.analysis.modeling import LogisticRegressionModel

# 准备训练数据
X_train = df_woe[selected_features]
y_train = df_woe["{target_col}"]

# 初始化模型
model = LogisticRegressionModel(
    use_stepwise={use_stepwise},
    stepwise_direction="{stepwise_direction}",
    significance_level={significance_level}
)

# 训练模型
model.fit(X_train, y_train)

# 获取模型系数
coefficients = model.get_coefficients()
print(f"模型截距: {{model.intercept_:.4f}}")
print(f"入模特征数: {{len(coefficients)}}")

# 显著性检验
significance_result = model.significance_test()
for feature, pvalue in significance_result.items():
    print(f"  {{feature}}: p-value={{pvalue:.4f}}")
''',

    "score_scaling": '''# 评分刻度转换
from deepanalyze.analysis.scorecard import ScorecardBuilder

# 初始化评分卡构建器
builder = ScorecardBuilder(
    base_score={base_score},
    base_odds={base_odds},
    pdo={pdo}
)

# 生成评分卡
scorecard = builder.build(
    model=model,
    bins=bins_result,
    woe_values=woe_values
)

# 计算评分
train_scores = builder.predict_score(train_df)
test_scores = builder.predict_score(test_df)

print(f"训练集评分范围: {{train_scores.min():.0f}} - {{train_scores.max():.0f}}")
print(f"测试集评分范围: {{test_scores.min():.0f}} - {{test_scores.max():.0f}}")
''',

    "model_evaluation": '''# 模型评估
from deepanalyze.analysis.evaluation import ModelEvaluator

# 初始化评估器
evaluator = ModelEvaluator()

# 计算评估指标
train_metrics = evaluator.evaluate(
    y_true=y_train,
    y_pred=model.predict_proba(X_train),
    scores=train_scores
)

test_metrics = evaluator.evaluate(
    y_true=y_test,
    y_pred=model.predict_proba(X_test),
    scores=test_scores
)

# 打印结果
print("训练集指标:")
print(f"  AUC: {{train_metrics['auc']:.4f}}")
print(f"  KS: {{train_metrics['ks']:.4f}}")
print(f"  Gini: {{train_metrics['gini']:.4f}}")

print("测试集指标:")
print(f"  AUC: {{test_metrics['auc']:.4f}}")
print(f"  KS: {{test_metrics['ks']:.4f}}")
print(f"  Gini: {{test_metrics['gini']:.4f}}")

# 过拟合检测
overfit_ratio = train_metrics['auc'] / test_metrics['auc']
if overfit_ratio > 1.05:
    print(f"⚠️ 警告: 可能存在过拟合 (AUC比值: {{overfit_ratio:.3f}})")
''',

    "report_generation": '''# 报告生成
from deepanalyze.analysis.report import ReportGenerator

# 初始化报告生成器
report_gen = ReportGenerator()

# 生成评分卡报告
report = report_gen.generate_scorecard_report(
    scorecard=scorecard,
    train_metrics=train_metrics,
    test_metrics=test_metrics,
    iv_table=iv_table,
    bins=bins_result
)

# 生成图表
charts = report_gen.generate_charts(
    train_scores=train_scores,
    test_scores=test_scores,
    y_train=y_train,
    y_test=y_test
)

print(f"报告生成完成")
print(f"  包含 {{len(charts)}} 个图表")
print(f"  评分卡变量数: {{len(scorecard)}}")
'''
}


# =============================================================================
# 规则挖掘任务 - 阶段伪代码模板
# =============================================================================

RULE_MINING_CODE_TEMPLATES: Dict[str, str] = {
    "preprocessing": '''# 数据预处理
import pandas as pd
from deepanalyze.analysis.preprocessing import DataPreprocessor

# 加载数据
df = pd.read_csv("{file_path}")
print(f"数据集形状: {{df.shape}}")

# 初始化预处理器
preprocessor = DataPreprocessor(
    missing_threshold={missing_threshold}
)

# 缺失值处理
df_clean = preprocessor.handle_missing(df)

# 异常值检测与处理
df_processed = preprocessor.handle_outliers(
    df=df_clean,
    method='iqr'
)

print(f"预处理后数据形状: {{df_processed.shape}}")
''',

    "feature_engineering": '''# 特征工程（可选）
from deepanalyze.analysis.feature_engineering import FeatureEngineer

# 初始化特征工程器
engineer = FeatureEngineer(
    n_bins={n_bins},
    bin_method="{bin_method}"
)

# 特征分箱
df_binned = engineer.bin_features(
    df=df_processed,
    feature_cols=feature_cols
)

# 计算IV值
iv_table = engineer.calculate_iv(
    df=df_binned,
    target_col="{target_col}"
)

# 基于IV筛选特征
selected_features = iv_table[
    iv_table['iv'] >= {iv_threshold}
]['feature'].tolist()

print(f"IV筛选后特征数: {{len(selected_features)}}")
''',

    "generating_rules": '''# 规则生成
from deepanalyze.analysis.rule_mining import RuleGenerator

# 初始化规则生成器
generator = RuleGenerator(
    n_vars={n_vars},
    max_depth={max_depth},
    min_samples_leaf={min_samples_leaf}
)

# 生成规则
rules = generator.generate(
    df=df_processed,
    target_col="{target_col}",
    feature_cols=selected_features,
    rule_directions={rule_directions}
)

print(f"生成规则数量: {{len(rules)}}")

# 规则示例
for i, rule in enumerate(rules[:5]):
    print(f"规则{{i+1}}: {{rule['condition']}}")
    print(f"  命中率: {{rule['hit_rate']:.2%}}")
    print(f"  提升度: {{rule['lift']:.2f}}")
''',

    # v2.0: 合并 filtering_rules + evaluating_rules 为 rule_filtering
    "rule_filtering": '''# 规则过滤（方向过滤 + 效果评估）
from deepanalyze.analysis.rule_mining import RuleFilter, RuleEvaluator

# 初始化规则过滤器
filter = RuleFilter(
    min_lift={min_lift_filter},
    max_hit_rate={max_hit_rate_filter}
)

# 过滤规则（方向一致性 + 阈值筛选）
filtered_rules = filter.filter(
    rules=rules,
    df=df_processed,
    target_col="{target_col}"
)

print(f"过滤前规则数: {{len(rules)}}")
print(f"方向过滤后: {{filter.after_direction_filter}} 条")
print(f"最终保留: {{len(filtered_rules)}} 条")

# 初始化评估器
evaluator = RuleEvaluator()

# 评估规则效果
evaluation_results = evaluator.evaluate(
    rules=filtered_rules,
    df=df_processed,
    target_col="{target_col}"
)

# 打印评估结果
for rule_id, metrics in list(evaluation_results.items())[:5]:
    print(f"规则 {{rule_id}}:")
    print(f"  命中率: {{metrics['hit_rate']:.2%}}")
    print(f"  坏账率: {{metrics['bad_rate']:.2%}}")
    print(f"  提升度: {{metrics['lift']:.2f}}")
''',

    "selecting_rules": '''# 最优规则选择
from deepanalyze.analysis.rule_mining import RuleSelector

# 初始化规则选择器（含规则集级别风险目标参数）
selector = RuleSelector(
    max_hit_rate={max_hit_rate_select},
    min_recall_ruleset={min_recall_ruleset},      # 可选，最低召回率（规则集）
    min_bad_rate_ruleset={min_bad_rate_ruleset},  # 可选，最低坏账率（规则集）
    target_bad_rate_ruleset={target_bad_rate_ruleset},  # 可选，目标坏账率（规则集）- 自动计算所需召回率
    min_lift_ruleset={min_lift_ruleset}           # 可选，最低提升度（规则集）
)

# 选择最优规则组合
selected_rules = selector.select(
    rules=filtered_rules,
    evaluation_results=evaluation_results,
    max_rules=10
)

print(f"选择的规则数量: {{len(selected_rules)}}")

# 计算组合效果
combined_metrics = selector.evaluate_combination(
    rules=selected_rules,
    df=df_processed,
    target_col="{target_col}"
)

print(f"组合命中率: {{combined_metrics['hit_rate']:.2%}}")
print(f"组合坏账率: {{combined_metrics['bad_rate']:.2%}}")
print(f"组合提升度: {{combined_metrics['lift']:.2f}}")
''',

    "report_generation": '''# 报告生成
from deepanalyze.analysis.report import ReportGenerator

# 初始化报告生成器
report_gen = ReportGenerator()

# 生成规则挖掘报告
report = report_gen.generate_rule_mining_report(
    rules=selected_rules,
    evaluation_results=evaluation_results,
    combined_metrics=combined_metrics
)

# 生成图表
charts = report_gen.generate_rule_charts(
    rules=selected_rules,
    df=df_processed,
    target_col="{target_col}"
)

print(f"报告生成完成")
print(f"  包含 {{len(charts)}} 个图表")
print(f"  最终规则数: {{len(selected_rules)}}")
'''
}


# =============================================================================
# 工具函数
# =============================================================================

def get_code_template(task_id: str, stage_id: str) -> str:
    """获取指定任务和阶段的代码模板
    
    Args:
        task_id: 任务ID
        stage_id: 阶段ID
        
    Returns:
        代码模板字符串
    """
    if task_id == "scorecard_dev":
        return SCORECARD_CODE_TEMPLATES.get(stage_id, "")
    elif task_id == "rule_mining":
        return RULE_MINING_CODE_TEMPLATES.get(stage_id, "")
    return ""


def format_code_template(
    task_id: str,
    stage_id: str,
    params: Dict[str, Any]
) -> str:
    """格式化代码模板，填充参数
    
    Args:
        task_id: 任务ID
        stage_id: 阶段ID
        params: 参数字典
        
    Returns:
        格式化后的代码字符串
    """
    template = get_code_template(task_id, stage_id)
    if not template:
        return ""
    
    # 设置默认值
    defaults = {
        # 通用
        "file_path": "data.csv",
        "target_col": "target",
        "sample_type_col": "sample_type",
        # 数据预处理
        "missing_threshold": 0.95,
        "test_ratio": 0.3,
        # WOE分箱
        "bin_method": "tree",
        "bin_num_limit": 8,
        "use_high_precision": True,
        # 特征选择
        "iv_lower": 0.02,
        "iv_upper": 0.5,
        "corr_threshold": 0.7,
        "vif_threshold": 10,
        # 模型训练
        "use_stepwise": True,
        "stepwise_direction": "both",
        "significance_level": 0.05,
        # 评分刻度
        "base_score": 600,
        "base_odds": 50,
        "pdo": 20,
        # 规则挖掘
        "n_bins": 10,
        "iv_threshold": 0.02,
        "n_vars": 3,
        "max_depth": 3,
        "min_samples_leaf": 100,
        "min_lift_filter": 1.5,
        "max_hit_rate_filter": 0.3,
        "max_hit_rate_select": 0.2,
        "rule_directions": "['both']",
    }
    
    # 合并默认值和实际参数
    format_params = {**defaults, **params}
    
    try:
        return template.format(**format_params)
    except KeyError:
        # 如果有未匹配的参数，返回原始模板
        return template


# =============================================================================
# 阶段伪代码生成器（用于 Code 栏实时展示）
# =============================================================================

class StageCodeGenerator:
    """阶段伪代码生成器
    
    为 Pipeline 执行过程生成简洁的伪代码，用于在前端 Code 栏实时展示。
    与完整代码模板不同，伪代码更简洁，突出关键操作。
    """
    
    # 规则挖掘任务的简洁伪代码模板
    RULE_MINING_PSEUDO_CODE: Dict[str, str] = {
        "preprocessing": '''# === 阶段 1: 数据预处理 ===
df = load_data("{file_path}")
df = preprocess(df, 
    force_categorical={force_categorical},
    target='{target_col}'
)''',
        "feature_engineering": '''# === 阶段 2: 特征工程 ===
df_binned = bin_features(
    df,
    n_bins={n_bins},
    method='{bin_method}'
)
iv_table = calculate_iv(df_binned, target='{target_col}')
selected_features = filter_by_iv(iv_table, threshold={iv_threshold})''',
        "generating_rules": '''# === 阶段 3: 规则生成 ===
rules = generate_rules(
    df[selected_features + ['{target_col}']],
    target='{target_col}',
    n_vars={n_vars},
    max_depth={max_depth},
    min_samples_leaf={min_samples_leaf},
    directions={rule_directions}
)''',
        # v2.0: 合并 filtering_rules + evaluating_rules 为 rule_filtering
        "rule_filtering": '''# === 阶段 4: 规则过滤（方向过滤 + 效果评估） ===
filtered_rules = filter_rules(
    rules,
    min_lift={min_lift_filter},
    max_hit_rate={max_hit_rate_filter}
)
evaluation = evaluate_rules(
    filtered_rules,
    df,
    target='{target_col}'
)''',
        "selecting_rules": '''# === 阶段 5: 规则选择 ===
final_rules = select_best_rules(
    filtered_rules,
    evaluation,
    max_hit_rate={max_hit_rate_select},
    allow_overlap={allow_overlap},
    min_recall_ruleset={min_recall_ruleset},
    min_bad_rate_ruleset={min_bad_rate_ruleset},
    target_bad_rate_ruleset={target_bad_rate_ruleset},
    min_lift_ruleset={min_lift_ruleset}
)''',
        "report_generation": '''# === 阶段 6: 报告生成 ===
report = generate_report(
    final_rules,
    evaluation,
    output_path='rule_mining_report.xlsx'
)'''
    }
    
    # 评分卡开发任务的简洁伪代码模板
    SCORECARD_PSEUDO_CODE: Dict[str, str] = {
        "data_loading": '''# === 阶段 1: 数据加载 ===
df = load_data("{file_path}")
df = replace_special_values(df)  # -9999/-999 等 → NaN
df = var_filter(df, target='{target_col}')  # 移除高缺失率/同值率特征
train_df, test_df, oot_df = split_data(
    df,
    target='{target_col}',
    test_ratio={test_ratio}
)''',
        "woe_binning": '''# === 阶段 2: WOE分箱 ===
woe_transformer = WOETransformer(
    method='{bin_method}',
    bin_num_limit={bin_num_limit},
    use_high_precision={use_high_precision}
)
df_woe, bins, iv_table = woe_transformer.fit_transform(
    train_df,
    target='{target_col}'
)''',
        "feature_selection": '''# === 阶段 3: 特征筛选 ===
# 注：逐步回归在下一阶段（模型训练）中执行
selected_features = select_features(
    df_woe,
    iv_table,
    iv_lower={iv_lower},
    iv_upper={iv_upper},
    corr_threshold={corr_threshold},
    vif_threshold={vif_threshold}
)''',
        "model_training": '''# === 阶段 4: 模型训练 ===
model = LogisticRegression(
    use_stepwise={use_stepwise},
    direction='{stepwise_direction}',
    significance={significance_level}
)
model.fit(df_woe[selected_features], df_woe['{target_col}'])''',
        "score_scaling": '''# === 阶段 5: 评分刻度 ===
scorecard = build_scorecard(
    model,
    bins,
    base_score={base_score},
    base_odds={base_odds},
    pdo={pdo}
)
train_scores = scorecard.predict(train_df)
test_scores = scorecard.predict(test_df)''',
        "model_evaluation": '''# === 阶段 6: 模型评估 ===
metrics = evaluate_model(
    model,
    train_df, test_df,
    train_scores, test_scores
)
# AUC, KS, Gini, PSI...''',
        "report_generation": '''# === 阶段 7: 报告生成 ===
report = generate_scorecard_report(
    scorecard,
    metrics,
    output_path='scorecard_report.xlsx'
)'''
    }
    
    @classmethod
    def generate_pseudo_code(cls, task_id: str, stage_id: str, params: Dict[str, Any]) -> str:
        """生成阶段伪代码
        
        Args:
            task_id: 任务ID
            stage_id: 阶段ID
            params: 参数字典
            
        Returns:
            格式化后的伪代码字符串
        """
        # 选择模板
        if task_id == "rule_mining":
            templates = cls.RULE_MINING_PSEUDO_CODE
        elif task_id == "scorecard_dev":
            templates = cls.SCORECARD_PSEUDO_CODE
        else:
            return f"# 执行阶段: {stage_id}"
        
        template = templates.get(stage_id, f"# 执行阶段: {stage_id}")
        
        # 设置默认值
        defaults = {
            "file_path": "data.csv",
            "target_col": "target",
            "force_categorical": "[]",
            "n_bins": 10,
            "bin_method": "tree",
            "iv_threshold": 0.02,
            "n_vars": 3,
            "max_depth": 3,
            "min_samples_leaf": 100,
            "rule_directions": "['both']",
            "min_lift_filter": 1.5,
            "max_hit_rate_filter": 0.3,
            "max_hit_rate_select": 0.2,
            "allow_overlap": True,
            "test_ratio": 0.3,
            "bin_num_limit": 8,
            "use_high_precision": True,
            "iv_lower": 0.02,
            "iv_upper": 0.5,
            "corr_threshold": 0.7,
            "vif_threshold": 10,
            "use_stepwise": True,
            "stepwise_direction": "both",
            "significance_level": 0.05,
            "base_score": 600,
            "base_odds": 50,
            "pdo": 20,
        }
        
        # 合并参数
        format_params = {**defaults, **params}
        
        try:
            return template.format(**format_params)
        except KeyError:
            return template
    
    @classmethod
    def generate_stage_result_comment(
        cls,
        stage_id: str,
        result_summary: Dict[str, Any],
        execution_time_ms: int
    ) -> str:
        """生成阶段结果注释
        
        Args:
            stage_id: 阶段ID
            result_summary: 结果摘要
            execution_time_ms: 执行时间（毫秒）
            
        Returns:
            结果注释字符串
        """
        lines = []
        
        # 添加结果摘要
        if result_summary:
            for key, value in result_summary.items():
                if isinstance(value, (int, float)):
                    if isinstance(value, float):
                        lines.append(f"# → {key}: {value:.4f}")
                    else:
                        lines.append(f"# → {key}: {value}")
                elif isinstance(value, str):
                    lines.append(f"# → {key}: {value}")
        
        # 添加执行时间
        if execution_time_ms:
            lines.append(f"# → 耗时: {execution_time_ms/1000:.1f}s")
        
        return "\n".join(lines) if lines else "# → 完成"


# =============================================================================
# 等效代码生成器（用于任务完成后复制执行）
# =============================================================================

class EquivalentCodeGenerator:
    """等效代码生成器
    
    生成可直接复制执行的完整等效代码，用于复现分析结果。
    """
    
    @classmethod
    def generate_rule_mining_code(cls, params: Dict[str, Any]) -> str:
        """生成规则挖掘等效代码
        
        Args:
            params: 任务参数
            
        Returns:
            完整的可执行代码
        """
        return f'''# === 规则挖掘等效代码 ===
# 以下代码可直接复制执行，复现本次分析结果

import pandas as pd
from deepanalyze.analysis.task_SOP.rule_mining import RuleMiningPipeline

# 加载数据
df = pd.read_csv("{params.get('file_path', 'data.csv')}")

# 配置参数
config = {{
    "target_col": "{params.get('target_col', 'target')}",
    "force_categorical": {params.get('force_categorical', [])},
    "n_bins": {params.get('n_bins', 10)},
    "bin_method": "{params.get('bin_method', 'tree')}",
    "iv_threshold": {params.get('iv_threshold', 0.02)},
    "n_vars": {params.get('n_vars', 3)},
    "max_depth": {params.get('max_depth', 3)},
    "min_samples_leaf": {params.get('min_samples_leaf', 100)},
    "min_lift_filter": {params.get('min_lift_filter', 1.5)},
    "max_hit_rate_filter": {params.get('max_hit_rate_filter', 0.3)},
    "max_hit_rate_select": {params.get('max_hit_rate_select', 0.2)},
    "allow_overlap": {params.get('allow_overlap', True)}
}}

# 执行规则挖掘
pipeline = RuleMiningPipeline(**config)
result = pipeline.run(
    df=df,
    target_col=config["target_col"]
)

# 导出结果
if "rules_df" in result:
    result["rules_df"].to_excel("rules_output.xlsx", index=False)
    print(f"规则已导出: rules_output.xlsx")
'''
    
    @classmethod
    def generate_scorecard_code(cls, params: Dict[str, Any]) -> str:
        """生成评分卡开发等效代码
        
        Args:
            params: 任务参数
            
        Returns:
            完整的可执行代码
        """
        return f'''# === 评分卡开发等效代码 ===
# 以下代码可直接复制执行，复现本次分析结果

import pandas as pd
from deepanalyze.analysis.task_SOP.scorecard_development import ScorecardPipeline

# 加载数据
df = pd.read_csv("{params.get('file_path', 'data.csv')}")

# 配置参数
config = {{
    "target_col": "{params.get('target_col', 'target')}",
    "test_ratio": {params.get('test_ratio', 0.3)},
    "bin_method": "{params.get('bin_method', 'tree')}",
    "bin_num_limit": {params.get('bin_num_limit', 8)},
    "use_high_precision": {params.get('use_high_precision', True)},
    "iv_lower": {params.get('iv_lower', 0.02)},
    "iv_upper": {params.get('iv_upper', 0.5)},
    "corr_threshold": {params.get('corr_threshold', 0.7)},
    "vif_threshold": {params.get('vif_threshold', 10)},
    "use_stepwise": {params.get('use_stepwise', True)},
    "stepwise_direction": "{params.get('stepwise_direction', 'both')}",
    "significance_level": {params.get('significance_level', 0.05)},
    "significance_mode": "{params.get('significance_mode', 'warn')}",
    "coefficient_direction_mode": "{params.get('coefficient_direction_mode', 'warn')}",
    "max_validation_iterations": {params.get('max_validation_iterations', 10)},
    "base_score": {params.get('base_score', 600)},
    "base_odds": {params.get('base_odds', 50)},
    "pdo": {params.get('pdo', 20)}
}}

# 执行评分卡开发
pipeline = ScorecardPipeline(**config)
result = pipeline.run(
    df=df,
    target_col=config["target_col"]
)

# 导出结果
if "scorecard" in result:
    # 导出评分卡
    scorecard_df = pd.concat(result["scorecard"].values())
    scorecard_df.to_excel("scorecard_output.xlsx", index=False)
    print(f"评分卡已导出: scorecard_output.xlsx")
'''
    
    @classmethod
    def generate_equivalent_code(cls, task_id: str, params: Dict[str, Any]) -> str:
        """生成等效代码
        
        Args:
            task_id: 任务ID
            params: 任务参数
            
        Returns:
            完整的可执行代码
        """
        if task_id == "rule_mining":
            return cls.generate_rule_mining_code(params)
        elif task_id == "scorecard_dev":
            return cls.generate_scorecard_code(params)
        else:
            return f"# 未知任务类型: {task_id}"


# =============================================================================
# 任务配置摘要生成器
# =============================================================================

def generate_task_config_summary(task_id: str, params: Dict[str, Any]) -> str:
    """生成任务配置摘要
    
    Args:
        task_id: 任务ID
        params: 任务参数
        
    Returns:
        配置摘要字符串
    """
    lines = ["# === 任务配置 ==="]
    
    if task_id == "rule_mining":
        lines.append(f"# 任务类型: 规则挖掘 (rule_mining)")
    elif task_id == "scorecard_dev":
        lines.append(f"# 任务类型: 评分卡开发 (scorecard_dev)")
    else:
        lines.append(f"# 任务类型: {task_id}")
    
    if params.get("file_path"):
        lines.append(f"# 数据文件: {params['file_path']}")
    
    lines.append("# 参数配置:")
    
    # 只显示关键参数
    key_params = ["target_col", "force_categorical", "n_bins", "bin_method", 
                  "iv_threshold", "n_vars", "max_depth", "allow_overlap",
                  "base_score", "pdo", "test_ratio"]
    
    for key in key_params:
        if key in params and params[key] is not None:
            lines.append(f"#   - {key}: {params[key]}")
    
    return "\n".join(lines)


__all__ = [
    'SCORECARD_CODE_TEMPLATES',
    'RULE_MINING_CODE_TEMPLATES',
    'get_code_template',
    'format_code_template',
    'StageCodeGenerator',
    'EquivalentCodeGenerator',
    'generate_task_config_summary',
]
