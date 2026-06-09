"""
AI 分析评估 System Prompt 模块

Phase 1: 从前端迁移 prompt 定义到后端
- buildOverallAnalysisPrompt -> get_overall_analysis_prompt
- buildStageAnalysisPrompt -> get_stage_analysis_prompt

参考: docs/system_prompt_guide.md 第4章设计规范
"""
# pyright: reportOptionalMemberAccess=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportAny=false
# pyright: reportExplicitAny=false
# pyright: reportDeprecated=false
# pyright: reportUnusedFunction=false
# pyright: reportUnusedParameter=false

from __future__ import annotations
from typing import Any, Optional
import json


# =============================================================================
# 常量定义
# =============================================================================

# 阶段名称映射（中文显示名）
STAGE_NAME_MAP = {
    # 评分卡开发阶段
    "data_loading": "数据加载",
    "preprocessing": "数据预处理",
    "woe_binning": "WOE分箱",
    "feature_selection": "特征筛选",
    "feature_engineering": "特征工程",
    "model_training": "模型训练",
    "model_evaluation": "模型评估",
    "score_scaling": "评分转换",
    "report_generation": "报告生成",
    # 规则挖掘阶段
    "generating_rules": "规则生成",
    "filtering_rules": "规则筛选",
    "rule_filtering": "规则筛选",
    "selecting_rules": "最优规则选择",
    "rule_selection": "最优规则选择",
    "evaluating_rules": "规则评估",
    "rule_mining": "规则挖掘",
}

# 阶段角色配置
STAGE_ROLE_CONFIG = {
    # 评分卡开发阶段
    "data_loading": {
        "role": "信贷风控数据分析专家",
        "expertise": "信贷风控数据预处理与质量评估",
        "focusPoints": [
            "数据完整性（高缺失特征数量。⚠️注意：系统采用WOE分箱自动将缺失值作为单独分箱处理，无需建议插补；如需剔除高缺失变量，可调整缺失率阈值参数）",
            "坏账率水平是否符合预期（通常2%-10%为正常范围）",
            "异常值情况（是否需要特殊处理）",
            "数据集划分是否合理（训练/测试/OOT比例）"
        ]
    },
    "preprocessing": {
        "role": "信贷风控数据分析专家",
        "expertise": "信贷风控数据预处理与质量评估",
        "focusPoints": [
            "数据完整性（高缺失特征数量。⚠️注意：系统采用WOE分箱自动将缺失值作为单独分箱处理，无需建议插补；如需剔除高缺失变量，可调整缺失率阈值参数）",
            "坏账率水平是否符合预期（通常2%-10%为正常范围）",
            "异常值情况（是否需要特殊处理）",
            "数据集划分是否合理（训练/测试/OOT比例）"
        ]
    },
    "woe_binning": {
        "role": "信贷风控特征工程专家",
        "expertise": "WOE分箱与IV值分析",
        "focusPoints": [
            "IV值分布是否合理（强：≥0.1，中：0.02-0.1，弱：<0.02）",
            "是否存在IV过高的可疑特征（IV>0.5可能存在信息泄露）",
            "特征单调性情况（非单调特征可能难以解释）"
        ]
    },
    "feature_selection": {
        "role": "信贷风控特征工程专家",
        "expertise": "特征筛选与变量选择",
        "focusPoints": [
            "特征筛选比例是否合理（通常保留20%-50%）",
            "IV分布是否均衡（避免过度依赖少数强特征）",
            "相关性移除是否合理（高相关特征保留IV更高的）",
            "VIF筛选是否有效（移除多重共线性特征）",
            "是否有重要特征被误删除的风险"
        ]
    },
    "feature_engineering": {
        "role": "信贷风控特征工程专家",
        "expertise": "特征筛选与变量选择",
        "focusPoints": [
            "特征筛选比例是否合理（通常保留20%-50%）",
            "IV分布是否均衡",
            "是否有重要特征被误删除的风险"
        ]
    },
    "model_training": {
        "role": "信贷风控建模专家",
        "expertise": "逻辑回归模型训练与系数分析",
        "focusPoints": [
            "逐步回归特征筛选结果是否合理（如启用，关注移除的特征数量和原因）",
            "模型系数符号是否符合业务逻辑（正系数=风险增加）",
            "特征P值是否显著（P<0.001极显著，P<0.01高度显著，P<0.05显著，P<0.1边缘显著）",
            "标准误是否正常（系数/标准误>2为正常，<1可能存在多重共线性）",
            "置信区间是否包含0（包含0表示特征可能不显著，考虑移除）",
            "迭代验证是否收敛（B+方案：关注移除特征及原因）",
            "最终入模特征数量是否合适（一般5-15个为宜）",
            "截距项是否在合理范围（通常为负值）"
        ],
        "note": "本阶段聚焦模型训练过程，模型区分能力（AUC/KS）将在【模型评估】阶段详细分析"
    },
    "model_evaluation": {
        "role": "信贷风控模型评估专家",
        "expertise": "模型性能评估与风险分析",
        "focusPoints": [
            "模型区分能力（KS≥0.2、AUC≥0.7为合格，KS≥0.3、AUC≥0.75为良好）",
            "过拟合风险（训练集与测试集KS/AUC差异<0.05为正常）",
            "模型稳定性（PSI<0.1为稳定，0.1-0.25轻微偏移，≥0.25不稳定）",
            "特征稳定性（CSI<0.1稳定，0.1-0.25轻微漂移，≥0.25显著漂移，关注CSI异常的特征是否影响模型整体PSI）",
            "排序性分析-单调性（评分从低到高，坏样本率应单调递减，违反说明排序能力存在局部缺陷）",
            "排序性分析-首组Lift（最低分段的风险倍数，≥2为良好，≥2.5为优秀，反映低分段的风险识别能力）",
            "排序性分析-末组Lift（最高分段的风险倍数，≤0.5为良好，≤0.3为优秀，反映高分段的优质客户识别能力）",
            "评分分布形态（分布应呈近似正态或合理偏态，好坏样本均值差应明显，标准差不宜过小导致区分度不足）",
            "评分分布集中度（各分箱样本占比应相对均匀，避免极端集中或稀疏分箱影响策略制定）"
        ]
    },
    "score_scaling": {
        "role": "信贷风控评分卡专家",
        "expertise": "评分卡设计与评分转换",
        "focusPoints": [
            "基准分和PDO设置是否合理（行业惯例：基准分600-660，PDO20-50）",
            "评分范围是否符合业务需求（理论范围应覆盖300-850，实际分布集中度）",
            "变量得分贡献是否合理（各变量最大贡献度差异不宜过大）",
            "评分分布统计（均值、标准差、IQR是否有足够区分度）"
        ]
    },
    "report_generation": {
        "role": "信贷风控报告分析专家",
        "expertise": "模型报告解读与业务建议",
        "focusPoints": [
            "报告内容是否完整覆盖关键环节",
            "是否有需要特别关注的风险点",
            "模型是否具备上线条件"
        ]
    },
    # 规则挖掘阶段
    "generating_rules": {
        "role": "规则策略分析专家",
        "expertise": "风控规则生成与参数优化",
        "focusPoints": [
            "规则生成数量是否充足（为后续筛选提供足够候选）",
            "挖掘模式选择是否合理（单变量vs多变量）",
            "决策树参数设置是否恰当"
        ]
    },
    "filtering_rules": {
        "role": "规则策略分析专家",
        "expertise": "风控规则筛选与质量评估",
        "focusPoints": [
            "筛选条件设置是否合理（Lift阈值、命中率上限）",
            "单调性校验的筛选效果",
            "有效规则数量是否满足业务需求",
            "过滤率是否在合理范围（通常50%-90%）"
        ]
    },
    "rule_filtering": {
        "role": "规则策略分析专家",
        "expertise": "风控规则筛选与质量评估",
        "focusPoints": [
            "筛选条件设置是否合理（Lift阈值、命中率上限）",
            "单调性校验的筛选效果",
            "有效规则数量是否满足业务需求",
            "过滤率是否在合理范围（通常50%-90%）"
        ]
    },
    "selecting_rules": {
        "role": "规则策略分析专家",
        "expertise": "最优规则集选择与组合优化",
        "focusPoints": [
            "最优规则数量是否适中（通常3-8条）",
            "累计命中率与召回率的平衡",
            "规则集的整体提升度",
            "选择模式是否符合业务目标",
            "OOT时间稳定性（如有验证数据，关注命中率CV是否<0.25）"
        ]
    },
    "rule_selection": {
        "role": "规则策略分析专家",
        "expertise": "最优规则集选择与组合优化",
        "focusPoints": [
            "最优规则数量是否适中（通常3-8条）",
            "累计命中率与召回率的平衡",
            "规则集的整体提升度",
            "选择模式是否符合业务目标"
        ]
    },
    "evaluating_rules": {
        "role": "规则策略分析专家",
        "expertise": "规则效果评估",
        "focusPoints": [
            "规则过滤效果是否达到预期",
            "过滤条件设置是否合理"
        ]
    },
    "rule_mining": {
        "role": "规则策略分析专家",
        "expertise": "风控规则挖掘与策略设计",
        "focusPoints": [
            "规则数量与质量的平衡",
            "规则覆盖率和精准率",
            "规则的业务可解释性"
        ]
    }
}

# 规则挖掘任务 preprocessing 阶段专用配置
RULE_MINING_PREPROCESSING_CONFIG = {
    "role": "规则策略数据分析师",
    "expertise": "风控规则挖掘数据预处理",
    "focusPoints": [
        "数据完整性（缺失率是否在可接受范围）",
        "坏账率水平是否适合规则挖掘（通常3%-15%较理想，过低则正样本稀缺难以挖掘有效规则，过高则说明风控前置策略可能存在问题）",
        "类别不平衡处理策略是否合理（如果 imbalance_analysis 显示 severity 为中度/重度，检查 applied_strategy 是否已启用 class_weight；如果用户选择了'不处理'但 bad_rate<10%，建议调整'类别不平衡处理'参数为'自动选择'）",
        "异常值情况说明（注意：规则挖掘中异常值可能是高风险信号，当前系统仅检测不处理，用户可根据业务需求决定是否在源数据中预处理。禁止建议WOE分箱，规则挖掘需保留原始特征值）",
        "数据集划分（训练集/测试集）比例是否合理（注意：规则挖掘任务无OOT验证集概念）",
        "特征数量是否适中"
    ]
}


# =============================================================================
# 辅助函数
# =============================================================================

def _safe_get(data: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    """安全获取嵌套字典值，处理None和非dict类型"""
    if data is None:
        return default
    result: Any = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result if result is not None else default


def _format_number(value: Any, digits: int = 4, as_percent: bool = False) -> str:
    """格式化数字"""
    if value is None:
        return "N/A"
    try:
        num = float(value)
        if as_percent:
            return f"{num * 100:.{digits}f}%"
        return f"{num:.{digits}f}"
    except (ValueError, TypeError):
        return "N/A"




# 保留备用的辅助函数
def _format_list(items: list[Any], max_items: int = 5, separator: str = ", ") -> str:  # noqa: F841  # noqa: F841
    """格式化列表（暂未使用，保留用于未来扩展）"""
    if not items:
        return "N/A"
    display = items[:max_items]
    result = separator.join(str(item) for item in display)
    if len(items) > max_items:
        result += f"... 等{len(items)}个"
    return result


def _unwrap_data(data: Any) -> Any:
    """解包后端 safe_serialize 序列化的数据格式 {type: "dict", data: {...}}"""
    if isinstance(data, dict) and "type" in data and "data" in data:
        return data["data"]
    return data


# =============================================================================
# 整体分析 Prompt 构建
# =============================================================================

def get_overall_analysis_prompt(task_type_name: str, result: dict[str, Any]) -> str:
    """
    构建任务整体分析的提示词
    
    Args:
        task_type_name: 任务类型名称（"评分卡开发" 或 "规则挖掘"）
        result: 任务结果数据，包含 outputs 和 stages
    
    Returns:
        完整的分析提示词字符串
    """
    outputs = result.get("outputs", result) or {}
    stages = result.get("stages", {}) or {}
    
    if task_type_name in ("评分卡开发", "scorecard_dev"):
        return _build_scorecard_overall_prompt(outputs, stages)
    else:
        return _build_rule_mining_overall_prompt(outputs, stages)


def _build_scorecard_overall_prompt(outputs: dict[str, Any], stages: dict[str, Any]) -> str:
    """构建评分卡开发整体分析 Prompt"""
    
    # ========== 1. 样本及特征概况（从stages获取）==========
    preprocessing_data = _safe_get(stages, "preprocessing", "output_preview", default={}) or {}
    if not preprocessing_data:
        preprocessing_data = _safe_get(stages, "data_loading", "output_preview", default={}) or {}
    woe_binning_data = _safe_get(stages, "woe_binning", "output_preview", default={}) or {}
    feature_selection_data = _safe_get(stages, "feature_selection", "output_preview", default={}) or {}
    
    sample_rows = (preprocessing_data or {}).get("rows") or (preprocessing_data or {}).get("total_rows", "N/A")
    target_rate = (preprocessing_data or {}).get("target_rate")
    sample_bad_rate = _format_number(target_rate, 2, as_percent=True) if target_rate is not None else "N/A"
    
    # 原始特征数：优先从var_filter_result.input_features获取（质量筛选前的真正原始特征数）
    # 否则使用feature_count或columns（这些是质量筛选后的特征数）
    var_filter_result = (preprocessing_data or {}).get("var_filter_result") or {}
    if var_filter_result and var_filter_result.get("input_features"):
        original_feature_count = var_filter_result.get("input_features")
    else:
        original_feature_count = (preprocessing_data or {}).get("feature_count") or (preprocessing_data or {}).get("columns", "N/A")
    
    # ========== 2. 特征筛选过程 ==========
    woe_total_features = (woe_binning_data or {}).get("total_features", "N/A")
    iv_range = (woe_binning_data or {}).get("iv_range") or {}
    fe_before_count = (feature_selection_data or {}).get("before_count") or woe_total_features
    fe_after_count = (feature_selection_data or {}).get("after_count") or (feature_selection_data or {}).get("selected_count", "N/A")
    
    # ========== 3. 模型性能（从multi_dataset_metrics获取）==========
    multi_metrics_raw = _unwrap_data(outputs.get("multi_dataset_metrics"))
    multi_metrics = multi_metrics_raw if isinstance(multi_metrics_raw, dict) else {}
    train_metrics = multi_metrics.get("train") or {}
    test_metrics = multi_metrics.get("test") or {}
    oot_metrics = multi_metrics.get("oot")
    
    train_ks = train_metrics.get("ks", "N/A")
    test_ks = test_metrics.get("ks", "N/A")
    train_auc = train_metrics.get("auc", "N/A")
    test_auc = test_metrics.get("auc", "N/A")
    oot_ks = oot_metrics.get("ks") if oot_metrics else None
    oot_auc = oot_metrics.get("auc") if oot_metrics else None
    
    # 过拟合检测 - 优先使用后端已生成的警告信息（使用用户配置的阈值）
    overfit_warning_raw = _unwrap_data(outputs.get("overfit_warning"))
    model_eval_overfit = _safe_get(stages, "model_evaluation", "output_preview", "overfit_warning", default=None)
    overfit_warning = overfit_warning_raw or model_eval_overfit or ""
    
    # 如果后端没有生成警告但有明显差异，添加提示（作为后备）
    if not overfit_warning and isinstance(train_ks, (int, float)) and isinstance(test_ks, (int, float)):
        ks_diff = abs(train_ks - test_ks)
        if ks_diff > 0.05:  # 后备阈值，主逻辑由后端使用用户配置阈值
            overfit_warning = f"⚠️ KS差异{ks_diff:.3f}，存在过拟合风险"
    
    # ========== 3.1. 模型整体有效性 - 似然比检验（金标准）==========
    # 2026-02-11: 与前端Tab对齐，优先从 model_fit 获取，回退到 model_statistics
    model_training_data = _safe_get(stages, "model_training", "output_preview", default={}) or {}
    
    # 优先数据源（与前端 ModelStatisticsPanel 保持一致）
    model_fit = model_training_data.get("model_fit", {})
    lr_pvalue = model_fit.get("lr_pvalue")
    
    # 回退数据源（兼容旧格式）
    if lr_pvalue is None:
        model_statistics = model_training_data.get("model_statistics", {})
        if model_statistics:
            lr_pvalue = model_statistics.get("lr_pvalue")
    
    # 格式化似然比检验结果
    lr_test_str = "未计算"
    lr_test_warning = ""
    if lr_pvalue is not None and isinstance(lr_pvalue, (int, float)):
        if lr_pvalue < 0.001:
            lr_test_str = f"<0.001 (极显著)"
        elif lr_pvalue < 0.01:
            lr_test_str = f"{lr_pvalue:.4f} (高度显著)"
        elif lr_pvalue < 0.05:
            lr_test_str = f"{lr_pvalue:.4f} (显著)"
        else:
            lr_test_str = f"{lr_pvalue:.4f} (不显著)"
            lr_test_warning = "⚠️ 似然比检验不显著(p≥0.05)，模型整体有效性存疑"
    
    # ========== 4. 稳定性分析（PSI）==========
    model_eval_data = _safe_get(stages, "model_evaluation", "output_preview", default={}) or {}
    
    # PSI数据获取优先级：
    # 1. stages.model_evaluation.output_preview.psi_result（新结构，dict）
    # 2. outputs.psi_result（新结构，dict）
    # 3. outputs.psi（旧结构，直接数值）
    psi_result = (model_eval_data or {}).get("psi_result")
    if not psi_result:
        psi_result_raw = _unwrap_data(outputs.get("psi_result"))
        psi_result = psi_result_raw if isinstance(psi_result_raw, dict) else None
    
    # 从psi_result中提取数值
    psi = None
    psi_comparison = ""
    if isinstance(psi_result, dict):
        psi = psi_result.get("value")
        psi_comparison = psi_result.get("comparison", "")
    
    # 兜底：旧格式直接存数值
    if psi is None:
        psi_raw = _unwrap_data(outputs.get("psi"))
        psi = psi_raw if isinstance(psi_raw, (int, float)) else None
    
    psi_status = "未计算"
    if isinstance(psi, (int, float)):
        if psi < 0.1:
            psi_status = f"{psi:.4f} (稳定)"
        elif psi < 0.25:
            psi_status = f"{psi:.4f} (轻微偏移)"
        else:
            psi_status = f"{psi:.4f} (不稳定)"
        # 添加比较说明（如"训练集 vs OOT"）
        if psi_comparison:
            psi_status += f" [{psi_comparison}]"
    
    # ========== 4.1. CSI 特征稳定性（与PSI互补）==========
    csi_report = (model_eval_data or {}).get("csi_train_vs_oot") or (model_eval_data or {}).get("csi_train_vs_test")
    csi_section = ""
    if csi_report and isinstance(csi_report, dict):
        csi_features = csi_report.get("features", [])
        csi_summary = csi_report.get("summary", {})
        csi_comparison = csi_report.get("comparison", "")
        if csi_features:
            total = csi_summary.get("total_features", len(csi_features))
            stable = csi_summary.get("stable", 0)
            slight = csi_summary.get("slight_change", 0)
            significant = csi_summary.get("significant_change", 0)
            csi_section = f"\n- CSI特征稳定性（{csi_comparison}）: 共{total}个入模特征，稳定{stable}个，轻微漂移{slight}个，显著漂移{significant}个"
            # 列出不稳定特征
            unstable = [f for f in csi_features if f.get("csi", 0) >= 0.1]
            if unstable:
                csi_section += "\n  需关注特征: " + ", ".join(
                    f"{f['feature']}(CSI={_format_number(f['csi'])})" for f in unstable[:5]
                )

    # ========== 4.5. Gini系数（从AUC计算）==========
    train_gini = "N/A"
    test_gini = "N/A"
    if isinstance(train_auc, (int, float)):
        train_gini = f"{(2 * train_auc - 1):.4f}"
    if isinstance(test_auc, (int, float)):
        test_gini = f"{(2 * test_auc - 1):.4f}"
    
    # ========== 4.6. 排序性分析（从score_distribution获取）==========
    # 行业标准：优先OOT数据（更能反映真实业务表现），其次测试集
    score_distribution = (model_eval_data or {}).get("score_distribution", {})
    oot_dist = score_distribution.get("oot", {}) if isinstance(score_distribution, dict) else {}
    test_dist = score_distribution.get("test") or {} if isinstance(score_distribution, dict) else {}
    train_dist = score_distribution.get("train") or {} if isinstance(score_distribution, dict) else {}
    
    # 确定主要评估数据集：优先OOT，其次测试集
    primary_dist = oot_dist if oot_dist else test_dist
    primary_dist_label = "OOT验证集" if oot_dist else "测试集"
    
    # 兼容旧格式（直接存储score_distribution而非嵌套结构）
    if not primary_dist and not train_dist and isinstance(score_distribution, dict):
        if "rank_ordering_analysis" in score_distribution or "ranking_analysis" in score_distribution:
            primary_dist = score_distribution
            primary_dist_label = "测试集"  # 旧格式默认是测试集
    
    # 获取排序性分析结果（优先主评估数据集，兜底训练集）
    rank_ordering_analysis = primary_dist.get("rank_ordering_analysis", {})
    if not rank_ordering_analysis:
        rank_ordering_analysis = train_dist.get("rank_ordering_analysis", {})
    
    # 解析排序性分析数据
    monotonicity_status = "未计算"
    first_lift_str = "N/A"
    last_lift_str = "N/A"
    rank_ordering_summary = ""
    
    if rank_ordering_analysis:
        # 单调性检验
        monotonicity = rank_ordering_analysis.get("monotonicity", {})
        is_monotonic = monotonicity.get("is_monotonic", True)
        violations = monotonicity.get("violations", [])
        
        if is_monotonic:
            monotonicity_status = "✓ 通过"
        else:
            monotonicity_status = f"✗ 不通过（{len(violations)}处违反）"
        
        # Lift分析
        lift_analysis = rank_ordering_analysis.get("lift_analysis", {})
        first_lift = lift_analysis.get("first_decile_lift")
        last_lift = lift_analysis.get("last_decile_lift")
        
        if first_lift is not None:
            first_lift_rating = "优秀" if first_lift >= 2.5 else ("良好" if first_lift >= 2 else ("合格" if first_lift >= 1.5 else "偏低"))
            first_lift_str = f"{first_lift:.2f}（{first_lift_rating}）"
        
        if last_lift is not None:
            last_lift_rating = "优秀" if last_lift <= 0.3 else ("良好" if last_lift <= 0.5 else ("合格" if last_lift <= 0.8 else "偏高"))
            last_lift_str = f"{last_lift:.2f}（{last_lift_rating}）"
        
        # 构建排序性分析摘要（动态显示数据集来源）
        rank_ordering_summary = f"""
### 6. 排序性分析（基于{primary_dist_label}Decile分箱）
- 单调性检验: {monotonicity_status}
- 首组Lift: {first_lift_str}
- 末组Lift: {last_lift_str}"""
    
    # ========== 4.7. 评分分布形态分析（从score_distribution获取）==========
    score_distribution_summary = ""
    dist_summary = primary_dist.get("summary", {}) or train_dist.get("summary", {})
    dist_bins = primary_dist.get("bins", []) or train_dist.get("bins", [])
    
    if dist_summary or dist_bins:
        score_distribution_summary = "\n\n### 7. 评分分布形态"
        
        # 好坏样本分离度
        good_mean = dist_summary.get("good_mean")
        bad_mean = dist_summary.get("bad_mean")
        if good_mean is not None and bad_mean is not None:
            score_diff = abs(good_mean - bad_mean)
            separation_rating = "优秀" if score_diff >= 60 else ("良好" if score_diff >= 40 else ("合格" if score_diff >= 20 else "偏低"))
            score_distribution_summary += f"\n- 好坏样本分离度: 好样本均值{good_mean:.1f}, 坏样本均值{bad_mean:.1f}（差值{score_diff:.1f}分，{separation_rating}）"
        
        # 分布集中度（从bins数据分析）
        if dist_bins and len(dist_bins) >= 3:
            # 注意：bins数据中的样本数字段名是"total"而不是"count"
            bin_counts = [b.get("total", 0) or b.get("count", 0) for b in dist_bins]
            total_count = sum(bin_counts)
            if total_count > 0:
                bin_ratios = [c / total_count for c in bin_counts]
                max_ratio = max(bin_ratios)
                min_ratio = min(bin_ratios)
                ratio_range = max_ratio - min_ratio
                uniformity = "均匀" if ratio_range < 0.08 else ("较均匀" if ratio_range < 0.15 else "不均匀")
                score_distribution_summary += f"\n- 分布集中度: {uniformity}（最大占比{max_ratio*100:.1f}%, 最小占比{min_ratio*100:.1f}%）"
    
    # ========== 5. 评分卡概况 ==========
    # 根据 scorecard_result_adjustment_design.md 第7.4.1节：
    # "AI分析Prompt尽量从outputs获取数据，减少对stages的依赖"
    # 数据来源优先级：outputs.scorecard > stages.score_scaling.output_preview
    
    # 从 outputs 获取评分卡数据（主要数据源，与Tab展示一致）
    scorecard_raw = _unwrap_data(outputs.get("scorecard"))
    
    # stages 作为后备数据源
    score_scaling_data = _safe_get(stages, "score_scaling", "output_preview", default={}) or {}
    scorecard_preview = (score_scaling_data or {}).get("scorecard_preview", [])
    model_training_data = _safe_get(stages, "model_training", "output_preview", default={}) or {}
    
    # 计算入模变量数：
    # 1. 优先从 outputs.scorecard 字典中获取（排除 basepoints）- 与Tab展示一致
    # 2. 其次使用 stages.score_scaling.output_preview.scorecard_preview 作为后备
    # 3. 再次从 model_training 的 coefficients 获取（排除截距项）
    # 4. 最后使用 num_variables 字段
    if isinstance(scorecard_raw, dict) and len(scorecard_raw) > 0:
        # 后端存储的 scorecard 是字典格式 {变量名: DataFrame}
        # 排除 basepoints 常数项
        var_names = [k for k in scorecard_raw.keys() if k != "basepoints"]
        scorecard_var_count = len(var_names)
        top_vars = var_names[:5]
    elif isinstance(scorecard_raw, list) and len(scorecard_raw) > 0:
        # 兼容旧格式（列表）
        scorecard_var_count = len(scorecard_raw)
        top_vars = []
        for v in scorecard_raw[:5]:
            var_name = v.get("variable") or v.get("feature", "Unknown")
            top_vars.append(var_name)
    elif scorecard_preview and isinstance(scorecard_preview, list):
        # 后备：从 stages.score_scaling.output_preview.scorecard_preview 获取
        scorecard_var_count = len([item for item in scorecard_preview if item.get("variable") != "basepoints"])
        top_vars = [item.get("variable", "Unknown") for item in scorecard_preview[:5]]
    elif model_training_data:
        # 后备：从 model_training 的 coefficients 获取入模特征数
        coefficients = model_training_data.get("coefficients", []) or model_training_data.get("all_coefficients", [])
        scorecard_var_count = len(coefficients) if coefficients else 0
        top_vars = [c.get("feature", "Unknown") for c in coefficients[:5]] if coefficients else []
    else:
        # 最后尝试从 score_scaling 的 num_variables 字段获取
        scorecard_var_count = (score_scaling_data or {}).get("num_variables", 0)
        top_vars = []
    
    base_score_raw = _unwrap_data(outputs.get("base_score"))
    pdo_raw = _unwrap_data(outputs.get("pdo"))
    # 优先从 outputs 获取 base_score 和 pdo（与Tab展示一致）
    # stages 作为后备
    base_score = (base_score_raw if isinstance(base_score_raw, (int, float)) else None) or (score_scaling_data or {}).get("base_score") or 600
    pdo = (pdo_raw if isinstance(pdo_raw, (int, float)) else None) or (score_scaling_data or {}).get("pdo") or 50
    
    # Top变量示例
    top_vars_example = ", ".join(str(v) for v in top_vars) if top_vars else "暂无数据"
    vars_suffix = f" 等{scorecard_var_count}个变量" if scorecard_var_count > 5 else ""
    
    # ========== 6. IV分布 ==========
    iv_table_unwrapped = _unwrap_data(outputs.get("iv_table"))
    if isinstance(iv_table_unwrapped, list):
        iv_table = iv_table_unwrapped
    elif isinstance(iv_table_unwrapped, dict):
        iv_table = list(iv_table_unwrapped.values())
    else:
        iv_table = []
    
    # IV分布统计
    iv_dist_stats = "暂无数据"
    if iv_table:
        strong_iv = sum(1 for v in iv_table if (v.get("iv") or 0) >= 0.1)
        medium_iv = sum(1 for v in iv_table if 0.02 <= (v.get("iv") or 0) < 0.1)
        weak_iv = sum(1 for v in iv_table if (v.get("iv") or 0) < 0.02)
        iv_dist_stats = f"强(≥0.1): {strong_iv}, 中(0.02-0.1): {medium_iv}, 弱(<0.02): {weak_iv}"
    
    # OOT信息 - 判断是否有OOT数据
    has_oot = oot_ks is not None or oot_auc is not None
    
    # ========== 构建模型性能展示（有OOT时优先OOT）==========
    # 行业标准：OOT验证集最能反映模型在实际业务中的表现
    # 2026-02-11: 添加似然比检验作为模型整体有效性金标准
    if has_oot:
        # 有OOT时：OOT指标优先展示，测试集作为参照
        oot_gini = f"{(2 * oot_auc - 1):.4f}" if isinstance(oot_auc, (int, float)) else "N/A"
        performance_section = f"""### 3. 模型性能
- **似然比检验p值**: {lr_test_str}{' [模型整体有效性金标准，p<0.05为显著]' if lr_pvalue is not None else ''}
{f"- {lr_test_warning}" if lr_test_warning else ""}
- OOT验证集 KS: {oot_ks if oot_ks is not None else 'N/A'}
- OOT验证集 AUC: {oot_auc if oot_auc is not None else 'N/A'}
- OOT验证集 Gini: {oot_gini}
- 测试集 KS: {test_ks}
- 测试集 AUC: {test_auc}
- 测试集 Gini: {test_gini}
- 训练集 KS: {train_ks}
- 训练集 AUC: {train_auc}
- 训练集 Gini: {train_gini}"""
    else:
        # 无OOT时：测试集指标优先展示
        performance_section = f"""### 3. 模型性能
- **似然比检验p值**: {lr_test_str}{' [模型整体有效性金标准，p<0.05为显著]' if lr_pvalue is not None else ''}
{f"- {lr_test_warning}" if lr_test_warning else ""}
- 测试集 KS: {test_ks}
- 测试集 AUC: {test_auc}
- 测试集 Gini: {test_gini}
- 训练集 KS: {train_ks}
- 训练集 AUC: {train_auc}
- 训练集 Gini: {train_gini}"""
    
    return f"""## 角色设定
你是一位资深的信贷风控建模专家，专长领域：评分卡开发与模型评估。

## 任务
请对本次评分卡开发任务的整体结果进行专业、全面的分析和评估。

## 分析范围约束
**重要**：请严格聚焦于模型开发层面的分析，不要延伸到以下下游业务应用领域：
- 风险定价（如利率定价、保费计算）
- 授信策略（如额度分配、审批规则）
- 贷后管理（如催收策略、预警机制）
- 业务运营（如产品设计、营销策略）

你的建议应围绕：模型性能优化、特征工程改进、数据质量提升、过拟合控制等技术维度。

## 任务执行结果

### 1. 样本及特征概况
- 样本总量: {sample_rows}条
- 坏样本率: {sample_bad_rate}
- 原始特征数: {original_feature_count}个

### 2. 特征筛选过程（中间结果，非最终入模数）
- WOE分箱特征数: {woe_total_features}
- IV范围: {_format_number(iv_range.get('min'))} ~ {_format_number(iv_range.get('max'))}
- IV/VIF筛选后特征数: {fe_after_count}（从{fe_before_count}筛选，这是中间结果）
- IV分布: {iv_dist_stats}

{performance_section}
{f'- {overfit_warning}' if overfit_warning else ''}

### 4. 稳定性分析
- PSI: {psi_status}{csi_section}

### 5. 评分卡概况（最终结果）
- **最终入模变量数**: {scorecard_var_count}个（经逐步回归/系数验证后的实际入模数，请以此为准）
- 基准分: {base_score}
- PDO: {pdo}
- 主要变量: {top_vars_example}{vars_suffix}
{rank_ordering_summary}{score_distribution_summary}

## 指标说明
- **似然比检验（Likelihood Ratio Test）**: 模型整体有效性金标准，检验模型是否比基准模型（仅截距项）显著更好。p<0.05表示模型整体有效，p<0.01高度显著，p<0.001极显著
- **KS（Kolmogorov-Smirnov）**: 好坏样本累计分布差的最大值，反映模型区分能力
- **AUC（Area Under ROC Curve）**: ROC曲线下面积，评估模型整体判别能力
- **Gini**: 2*AUC-1，与AUC等价但更直观（0-1范围，越高越好）
- **PSI（Population Stability Index）**: 评分分布稳定性指标，<0.1稳定，0.1-0.25轻微偏移，≥0.25不稳定
- **CSI（Characteristic Stability Index）**: 各入模特征的分布稳定性指标，计算方法与PSI相同但针对各特征的WOE分箱分布，用于定位PSI劣化的根因特征
- **首组Lift**: 最高分段的坏样本率/整体坏样本率，理想值≥2（高分段应少坏样本）
- **末组Lift**: 最低分段的坏样本率/整体坏样本率，理想值≤0.5（低分段应多坏样本）
- **好坏样本分离度**: 好/坏样本评分均值差，≥60分优秀，≥40分良好，≥20分合格

## 重点关注维度
1. **模型整体有效性（首要）**: 似然比检验p<0.05为模型有效的前提条件，p≥0.05说明模型整体不显著，需谨慎使用
2. 模型区分能力（KS≥0.2、AUC≥0.7、Gini≥0.4为合格，KS≥0.3、AUC≥0.75、Gini≥0.5为良好）
3. 过拟合风险（训练集与测试集KS/AUC差异<0.05为正常）
4. 模型稳定性（PSI<0.1为稳定；CSI关注各特征分布漂移，CSI≥0.1的特征需重点分析）
5. 排序性（单调性应通过，首组Lift≥2、末组Lift≤0.5为优秀）
6. 评分分布形态（好坏样本分离度应明显，分布应相对均匀）
7. 入模变量合理性（数量适中、IV分布合理、业务可解释）


## 输出格式要求
**重要**：直接输出分析内容，禁止自我介绍或开场白（如"作为...专家，我..."）。按以下结构输出：

**样本与特征分析** 1-2句话，评价样本量、坏样本率、以及最终入模变量数是否合理（注意：请使用「评分卡概况」中的「最终入模变量数」，而非「特征筛选过程」中的中间结果）

**模型整体有效性** 1-2句话，优先评价似然比检验结果（p<0.05为有效前提），若p≥0.05必须明确指出模型整体不显著

**模型性能分析** 2-3句话，评价KS/AUC/Gini指标，是否存在过拟合风险

**排序性与分布分析** 1-2句话，评价单调性、首尾Lift、评分分布形态是否符合预期

**综合评估** 2-3句话，客观总结本次评分卡开发的整体情况，包括主要优点、存在的问题点、稳定性结论（PSI+CSI），以及是否具备业务应用条件

**优化建议** 1-3条具体可行的建议"""


def _build_rule_mining_overall_prompt(outputs: dict[str, Any], stages: dict[str, Any]) -> str:
    """构建规则挖掘整体分析 Prompt"""
    
    # ========== 1. 最优规则数据 ==========
    optimal_rules_raw = _unwrap_data(outputs.get("optimal_rules"))
    rules = optimal_rules_raw if isinstance(optimal_rules_raw, list) else []
    
    total_rules = len(rules)
    avg_lift = "N/A"
    avg_bad_rate = "N/A"
    if total_rules > 0:
        lift_sum = sum(r.get("lift", 0) for r in rules)
        bad_rate_sum = sum(r.get("bad_rate", 0) for r in rules)
        avg_lift = f"{lift_sum / total_rules:.2f}"
        avg_bad_rate = f"{bad_rate_sum / total_rules * 100:.2f}%"
    
    # 累计指标（最后一条规则的累计值）
    last_rule = rules[-1] if rules else {}
    cum_recall = f"{last_rule.get('dev_cum_recall', 0) * 100:.2f}%" if last_rule.get('dev_cum_recall') else "N/A"
    cum_hit_rate = f"{last_rule.get('dev_cum_hit_rate', 0) * 100:.2f}%" if last_rule.get('dev_cum_hit_rate') else "N/A"
    cum_bad_rate = f"{last_rule.get('dev_cum_bad_rate', 0) * 100:.2f}%" if last_rule.get('dev_cum_bad_rate') else "N/A"
    cum_lift = f"{last_rule.get('dev_cum_lift', 0):.2f}" if last_rule.get('dev_cum_lift') else "N/A"
    
    # Top规则示例
    rules_example_lines = []
    for i, r in enumerate(rules[:3]):
        lift = f"提升度={r.get('lift', 0):.1f}" if r.get('lift') else ""
        bad_rate = f"坏账率={r.get('bad_rate', 0) * 100:.1f}%" if r.get('bad_rate') else ""
        metrics = ", ".join(filter(None, [lift, bad_rate]))
        rules_example_lines.append(f"{i + 1}. {r.get('rule', 'N/A')} ({metrics})")
    rules_example = "\n".join(rules_example_lines) if rules_example_lines else "暂无规则数据"
    
    # ========== 2. 样本及特征数据（从stages获取）==========
    preprocessing_data = _safe_get(stages, "preprocessing", "output_preview", default={}) or {}
    fe_data = _safe_get(stages, "feature_engineering", "output_preview", default={}) or {}
    
    sample_rows = (preprocessing_data or {}).get("rows") or (preprocessing_data or {}).get("total_rows", "N/A")
    target_rate = (preprocessing_data or {}).get("target_rate") or (preprocessing_data or {}).get("bad_rate")
    sample_bad_rate = "N/A"
    if target_rate is not None:
        sample_bad_rate = f"{float(target_rate) * 100:.2f}%" if isinstance(target_rate, (int, float)) else str(target_rate)
    feature_count = (fe_data or {}).get("after_count") or (fe_data or {}).get("selected_count") or preprocessing_data.get("feature_count", "N/A")
    
    # ========== 2.5. 任务参数配置（从rule_filtering阶段获取）==========
    rule_filtering_data = _safe_get(stages, "rule_filtering", "output_preview", default={}) or {}
    filter_criteria = (rule_filtering_data or {}).get("filter_criteria") or {}
    min_lift_threshold = filter_criteria.get("min_lift", "N/A")
    max_hit_rate_threshold = filter_criteria.get("max_hit_rate", "N/A")
    # 格式化阈值显示
    min_lift_threshold_str = f"{min_lift_threshold}" if min_lift_threshold != "N/A" else "N/A"
    max_hit_rate_threshold_str = f"{max_hit_rate_threshold * 100:.1f}%" if isinstance(max_hit_rate_threshold, (int, float)) else "N/A"
    
    # ========== 2.6. 规则选择模式（贪婪/重叠）==========
    rule_selection_data = _safe_get(stages, "rule_selection", "output_preview", default={}) or {}
    allow_overlap = (rule_selection_data or {}).get("allow_overlap", False)
    selection_mode_str = "允许重叠（独立选择）" if allow_overlap else "贪婪算法（不允许重叠）"

    # ========== 3. 筛选过程数据 ==========
    all_rules_raw = _unwrap_data(outputs.get("all_rules_with_status"))
    all_rules_array = all_rules_raw if isinstance(all_rules_raw, list) else []
    total_candidate_rules = len(all_rules_array)
    rejected_rules = [r for r in all_rules_array if not r.get("is_optimal")]
    rejected_count = len(rejected_rules)
    
    # 从 stages.rule_selection.output_preview.filter_summary 获取筛选统计
    filter_summary = (rule_selection_data or {}).get("filter_summary") or {}
    
    # 构建淘汰原因分布
    rejection_reasons: dict[str, int] = {}
    
    # 方案1：从 filter_summary 获取
    if filter_summary.get("direction_removed", 0) > 0:
        rejection_reasons["单调性校验移除"] = filter_summary["direction_removed"]
    if filter_summary.get("bad_rate_zero_removed", 0) > 0:
        rejection_reasons["坏账率为0移除"] = filter_summary["bad_rate_zero_removed"]
    if filter_summary.get("lift_removed", 0) > 0:
        rejection_reasons["最小Lift阈值移除"] = filter_summary["lift_removed"]
    if filter_summary.get("hit_rate_removed", 0) > 0:
        rejection_reasons["最大命中率移除"] = filter_summary["hit_rate_removed"]
    
    # 方案2：如果 filter_summary 没数据，从规则的布尔字段逐条统计
    if not rejection_reasons and all_rules_array:
        for r in all_rules_array:
            if r.get("is_optimal"):
                continue
            if not r.get("direction_valid"):
                rejection_reasons["单调性校验移除"] = rejection_reasons.get("单调性校验移除", 0) + 1
            elif r.get("bad_rate_valid") is False:
                rejection_reasons["坏账率为0移除"] = rejection_reasons.get("坏账率为0移除", 0) + 1
            elif r.get("lift_valid") is False:
                rejection_reasons["最小Lift阈值移除"] = rejection_reasons.get("最小Lift阈值移除", 0) + 1
            elif r.get("hit_rate_valid") is False:
                rejection_reasons["最大命中率移除"] = rejection_reasons.get("最大命中率移除", 0) + 1
            elif r.get("is_valid") and not r.get("is_optimal"):
                reason = r.get("rejection_reason", "未入选最优集")
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            else:
                rejection_reasons["其他原因"] = rejection_reasons.get("其他原因", 0) + 1
    
    # 格式化淘汰原因（按数量降序，最多显示5个）
    reason_entries = sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)[:5]
    total_rejected_from_reasons = sum(count for _, count in reason_entries)
    
    rejection_summary_lines = []
    if reason_entries:
        for reason, count in reason_entries:
            pct = f"{count / total_rejected_from_reasons * 100:.0f}" if total_rejected_from_reasons > 0 else "0"
            rejection_summary_lines.append(f"  - {reason}: {count}条 ({pct}%)")
    rejection_summary = "\n".join(rejection_summary_lines) if rejection_summary_lines else "  - 无淘汰记录"
    
    # ========== 4. 质量验证数据 ==========
    validation_report_raw = _unwrap_data(outputs.get("validation_report"))
    validation_report = validation_report_raw if isinstance(validation_report_raw, dict) else {}
    quality_score = validation_report.get("quality_score")
    quality_score_str = f"{quality_score:.1f}" if isinstance(quality_score, (int, float)) else "N/A"
    
    overlap_report = validation_report.get("overlap_report", {})
    avg_overlap = overlap_report.get("avg_overlap")
    avg_overlap_str = f"{avg_overlap * 100:.1f}%" if isinstance(avg_overlap, (int, float)) else "0%"
    
    validation_issues = validation_report.get("warnings") or validation_report.get("issues") or []
    issues_summary_lines = [f"  - {issue}" for issue in validation_issues[:3]] if validation_issues else ["  - 无质量问题"]
    issues_summary = "\n".join(issues_summary_lines)
    
    # ========== 5. 稳定性数据（PSI）==========
    psi_report_raw = _unwrap_data(outputs.get("psi_report"))
    psi_report = psi_report_raw if isinstance(psi_report_raw, list) else []
    
    stable_rules = sum(1 for r in psi_report if (r.get("psi") or 0) < 0.1)
    unstable_rules = sum(1 for r in psi_report if (r.get("psi") or 0) >= 0.25)
    avg_psi = "N/A"
    if psi_report:
        psi_sum = sum(r.get("psi", 0) for r in psi_report)
        avg_psi = f"{psi_sum / len(psi_report):.3f}"
    
    psi_status = "未计算PSI"
    if psi_report:
        psi_status = f"{stable_rules}/{len(psi_report)}条稳定 (PSI<0.1), {unstable_rules}条不稳定 (PSI≥0.25), 平均PSI={avg_psi}"
    
    # P1-5: OOT 稳定性数据
    oot_stability_raw = _unwrap_data(outputs.get("oot_stability_report"))
    oot_stability_section = ""
    if oot_stability_raw and isinstance(oot_stability_raw, dict):
        overall_hr = oot_stability_raw.get("overall_hit_rate", {})
        counts = oot_stability_raw.get("stability_counts", {})
        bonus = oot_stability_raw.get("stability_score_bonus", 0)
        cv = overall_hr.get("cv", 0)
        oot_stability_section = (
            f"\n\n### 6.5 OOT时间稳定性验证"
            f"\n- 整体命中率CV: {cv:.4f}"
            f" (训练集{overall_hr.get('train', 0):.2%} / 测试集{overall_hr.get('test', 0):.2%} / OOT{overall_hr.get('oot', 0):.2%})"
            f"\n- 规则稳定性: 高度稳定{counts.get('highly_stable', 0)}条, 稳定{counts.get('stable', 0)}条, 中等{counts.get('moderate', 0)}条, 不稳定{counts.get('unstable', 0)}条"
            f"\n- 稳定性评分: {'+' if bonus >= 0 else ''}{bonus}分"
        )
    
    return f"""## 角色设定
你是一位资深的规则策略分析专家，专长领域：风控规则挖掘与策略评估。

## 任务
请对本次规则挖掘任务的整体结果进行专业、全面的分析和评估。

## 分析范围约束
**重要**：请严格聚焦于规则挖掘层面的分析，不要延伸到以下下游业务应用领域：
- 自动化决策系统（如规则引擎部署、实时决策）
- 人工审核流程（如审批流程设计、复核机制）
- 拒绝/通过策略（如分层准入、白名单策略）
- 业务运营（如客群运营、营销触达）

你的建议应围绕：规则筛选参数调整、规则质量提升、重叠度优化、稳定性改进等技术维度。

## 任务参数配置（用户设定的筛选阈值）
- 最小Lift阈值（单条规则筛选）: {min_lift_threshold_str}
- 最大命中率阈值（单条规则筛选）: {max_hit_rate_threshold_str}
- 规则选择模式: {selection_mode_str}
**注意**: 上述阈值是用户配置的筛选参数，用于过滤单条规则。如需调整，应建议修改这些参数值。

## 任务执行结果

### 1. 样本及特征概况
- 样本总量: {sample_rows}条
- 坏样本率: {sample_bad_rate}
- 筛选后特征数: {feature_count}个（用于规则生成）

### 2. 规则挖掘结果（入选规则的统计指标）
- 候选规则数: {total_candidate_rules}条
- 最终入选: {total_rules}条
- 入选规则平均提升度: {avg_lift}（各入选规则Lift的算术平均值）
- 入选规则平均坏账率: {avg_bad_rate}

### 3. 累计效果（规则集叠加后的整体效果）
- 累计召回率: {cum_recall}（规则集命中的坏样本占总坏样本比例）
- 累计命中率: {cum_hit_rate}（规则集命中的样本占总样本比例）
- 累计坏账率: {cum_bad_rate}（规则集命中样本中的坏样本比例）
- 累计提升度: {cum_lift}（累计坏账率/总体坏账率，反映规则集整体区分能力）

### 4. 规则筛选过程
- 淘汰规则数: {rejected_count}条
- 主要淘汰原因:
{rejection_summary}

### 5. 质量验证
- 质量评分: {quality_score_str}/100
- 规则重叠度: {avg_overlap_str}
- 验证问题:
{issues_summary}

### 6. 稳定性分析（PSI）
{psi_status}{oot_stability_section}

### 7. Top规则示例
{rules_example}

## 指标说明
- **平均提升度**: 入选规则各自Lift的算术平均，反映单条规则的平均质量
- **累计提升度**: 规则集整体的Lift（累计坏账率/总体坏账率），反映规则组合的整体效果
- **最小Lift阈值**: 用户配置的筛选参数，低于此值的单条规则会被过滤
- **命中率CV**: 变异系数(标准差/均值)，衡量规则在训练集/测试集/OOT上的命中率波动，<0.15高度稳定，0.15-0.25稳定，0.25-0.35中等，>0.35不稳定

## 重点关注维度
1. 规则质量（单条规则Lift是否≥2，坏账率是否显著高于总体）
2. 累计效果（召回率与命中率的平衡是否合理，累计提升度是否达标）
3. 筛选策略（淘汰原因分布是否合理，筛选阈值是否需要调整）
4. 规则重叠度（⚠️注意：贪婪算法模式下规则天然互斥、重叠度为0，这是算法特性而非需要优化的问题，不要建议做互斥性检验或重叠度优化；仅在允许重叠模式下，较高重叠度才需关注效率损耗）
5. 稳定性（PSI是否在可接受范围，OOT命中率CV是否<0.25）
6. 规则数量是否适中（6条以内较理想）

## 输出格式要求
**重要**：直接输出分析内容，禁止自我介绍或开场白（如"作为...专家，我..."）。按以下结构输出：

**样本与特征分析** 1-2句话，评价样本量和坏样本率是否合理，特征数量是否适中

**规则挖掘质量** 2-3句话，评价规则的提升度、坏账率、累计效果

**筛选过程分析** 1-2句话，评价淘汰规则的原因分布是否合理

**综合评估** 2-3句话，客观总结本次规则挖掘的整体情况，包括规则集的主要优点、存在的问题点，以及是否具备策略上线条件

**优化建议** 1-3条具体可行的建议，每条建议必须对应系统中可调整的参数或可操作的功能。如需调整Lift阈值，应明确指出调整"最小Lift阈值"参数"""


# =============================================================================
# 阶段分析 Prompt 构建
# =============================================================================

def get_stage_analysis_prompt(
    stage_id: str,
    stage_name: str,
    data: dict[str, Any],
    task_type: Optional[str] = None
) -> str:
    """
    构建阶段分析的提示词
    
    Args:
        stage_id: 阶段ID
        stage_name: 阶段名称
        data: 阶段输出数据
        task_type: 任务类型（可选，用于判断规则挖掘/评分卡）
    
    Returns:
        完整的阶段分析提示词字符串
    """
    stage_display_name = STAGE_NAME_MAP.get(stage_id, stage_name)
    
    # 判断是否为规则挖掘任务
    is_rule_mining_task = (
        stage_id == "preprocessing" and data.get("quality_score") is not None
    ) or task_type == "rule_mining"
    
    # 获取角色配置
    if is_rule_mining_task and stage_id == "preprocessing":
        role_config = RULE_MINING_PREPROCESSING_CONFIG
    else:
        role_config = STAGE_ROLE_CONFIG.get(stage_id, {
            "role": "信贷风控数据分析专家",
            "expertise": "信贷风控数据分析与建模",
            "focusPoints": ["执行结果的合理性", "是否存在异常"]
        })
    
    # 构建数据描述
    data_description = _build_stage_data_description(stage_id, data)
    
    # 构建关注点列表
    focus_points_list = "\n".join(
        f"{i + 1}. {point}" 
        for i, point in enumerate(role_config["focusPoints"])
    )
    
    # 如果有阶段说明（note），添加到关注点列表后
    stage_note = role_config.get("note", "")
    note_section = f"\n\n**注意**: {stage_note}" if stage_note else ""
    
    # 判断任务类型上下文
    is_rule_mining_context = (
        "rule" in stage_id or
        stage_id in ("generating_rules", "filtering_rules", "selecting_rules") or
        is_rule_mining_task
    )
    
    task_type_context = (
        "**重要提示**：当前是【规则挖掘任务】，不是评分卡建模任务。规则挖掘的目标是发现高风险人群的规则特征，用于策略拦截；与建模不同，不需要WOE分箱、逻辑回归等建模步骤。请在分析中使用「规则挖掘」而非「建模」相关表述。"
        if is_rule_mining_context
        else "**任务类型**：评分卡建模任务"
    )

    # ── 参数建议格式要求（用于一键调参重跑功能）──────────────────────────
    # 获取当前阶段可调参数 key 列表，约束 LLM 只输出已知参数名
    stage_available_params = _get_stage_available_params(stage_id, task_type)
    if stage_available_params:
        params_hint = (
            f"\n\n## 参数建议（必须遵守）\n"
            f"如果你在分析中提到了任何调参建议（如'建议调整'、'可以提高'、'适当降低'等），**必须**在分析文本末尾另起一行输出以下格式，不得省略：\n"
            f"SUGGESTED_PARAMS: {{\"param_key\": value, ...}}\n"
            f"如果没有任何调参建议，则省略此行。\n"
            f"可调整的参数键名（只能使用以下键名）：{', '.join(stage_available_params)}\n"
            f"示例：SUGGESTED_PARAMS: {{\"max_depth\": 5, \"min_samples_leaf\": 0.02}}"
        )
    else:
        params_hint = ""
    # ──────────────────────────────────────────────────────────────────────

    return f"""## 角色设定
你是一位{role_config['role']}，专长领域：{role_config['expertise']}。

{task_type_context}

## 任务
请对"{stage_display_name}"阶段的执行结果进行专业分析和评估。

## 阶段结果数据
{data_description}

## 重点关注维度
{focus_points_list}{note_section}

## 输出要求
**重要**：直接输出分析内容，禁止自我介绍或开场白（如"作为...专家，我..."、"您好！我是..."）。
1. 用2-3句话概括本阶段执行情况，结合上述关注维度进行专业点评
2. 在文中自然融入关键指标状态（如"关键指标：【正常】"），不要单独列出"关键指标评估"段落
3. 如有问题或优化空间，给出1-2条具体可行的建议
4. **格式要求**：输出为连贯的段落式文字，禁止使用格式化列表（如"- xxx：yyy"），控制在150字以内{params_hint}"""


def _get_stage_available_params(stage_id: str, task_type: Optional[str] = None) -> list[str]:
    """从 TaskMeta 获取指定阶段的可调参数 key 列表，用于约束 LLM 的参数建议输出"""
    try:
        from deepanalyze.analysis.task_SOP.registry import get_registry
        registry = get_registry()
        # 按 task_type 优先匹配，其次遍历所有任务
        task_ids = []
        if task_type == "rule_mining":
            task_ids = ["rule_mining"]
        elif task_type == "scorecard_dev":
            task_ids = ["scorecard_dev"]
        else:
            task_ids = list(registry._tasks.keys()) if hasattr(registry, '_tasks') else []

        for task_id in task_ids:
            task_def = registry.get_task(task_id)
            if not task_def:
                continue
            params = [
                p.name
                for p in task_def.params
                if hasattr(p, 'stage') and getattr(p, 'stage', None) == stage_id
            ]
            if params:
                return params
    except Exception:
        pass
    return []


def _build_stage_data_description(stage_id: str, data: dict[str, Any]) -> str:
    """根据阶段ID构建数据描述"""
    
    if stage_id in ("data_loading", "preprocessing"):
        return _build_data_loading_description(data)
    elif stage_id == "woe_binning":
        return _build_woe_binning_description(data)
    elif stage_id in ("feature_selection", "feature_engineering"):
        return _build_feature_selection_description(data)
    elif stage_id == "model_training":
        return _build_model_training_description(data)
    elif stage_id == "model_evaluation":
        return _build_model_evaluation_description(data)
    elif stage_id == "evaluating_rules":
        return _build_evaluating_rules_description(data)
    elif stage_id == "score_scaling":
        return _build_score_scaling_description(data)
    elif stage_id == "generating_rules":
        return _build_generating_rules_description(data)
    elif stage_id in ("filtering_rules", "rule_filtering"):
        return _build_filtering_rules_description(data)
    elif stage_id in ("selecting_rules", "rule_selection"):
        return _build_selecting_rules_description(data)
    elif stage_id == "rule_mining":
        return _build_rule_mining_description(data)
    elif stage_id == "report_generation":
        return _build_report_generation_description(data)
    else:
        # 默认：JSON 格式输出
        return f"\n{json.dumps(data, ensure_ascii=False, indent=2)[:500]}"


def _build_data_loading_description(data: dict[str, Any]) -> str:
    """数据加载/预处理阶段描述"""
    # 解析排除变量信息
    auto_exclude_report = data.get("auto_exclude_report", {})
    user_specified = auto_exclude_report.get("user_specified", [])
    auto_detected = auto_exclude_report.get("auto_detected", {})
    total_excluded = auto_exclude_report.get("total_excluded", [])
    
    exclude_info = ""
    if total_excluded:
        exclude_info = f"\n- 排除变量数: {len(total_excluded)}"
        if user_specified:
            exclude_info += f"\n  - 用户指定: {', '.join(user_specified)}"
        if auto_detected.get("id_cols"):
            exclude_info += f"\n  - 自动检测ID列: {', '.join(auto_detected['id_cols'])}"
        if auto_detected.get("time_cols"):
            exclude_info += f"\n  - 自动检测时间列: {', '.join(auto_detected['time_cols'])}"
    
    # 衍生特征信息
    derived_features = data.get("derived_features", {})
    derived_info = ""
    if derived_features.get("total_derived", 0) > 0:
        derived_info = f"\n- 衍生特征数: {derived_features['total_derived']}"
        if derived_features.get("onehot_count", 0) > 0:
            derived_info += f"\n  - One-Hot编码: +{derived_features['onehot_count']}个"
        if derived_features.get("datetime_count", 0) > 0:
            derived_info += f"\n  - 日期时间衍生: +{derived_features['datetime_count']}个"
        if derived_features.get("text_count", 0) > 0:
            derived_info += f"\n  - 文本衍生: +{derived_features['text_count']}个"
    
    rows = data.get("rows")
    rows_str = f"{rows:,}" if isinstance(rows, int) else "N/A"
    feature_count = data.get("feature_count") or data.get("columns", "N/A")
    total_features = feature_count
    if derived_features.get("total_derived", 0) > 0 and isinstance(feature_count, int):
        total_features = feature_count + derived_features["total_derived"]
    
    missing_rate = data.get("missing_rate")
    missing_str = f"{missing_rate * 100:.1f}%" if missing_rate is not None else "N/A"
    
    target_rate = data.get("target_rate")
    target_str = f"{target_rate * 100:.2f}%" if target_rate is not None else "N/A"
    
    # ========== 缺失率详细信息（使用 missing_summary 结构化数据）==========
    missing_summary = data.get("missing_summary", {})
    missing_detail_str = ""
    if missing_summary:
        # 缺失率分布统计（帮助AI评估数据整体质量）
        distribution = missing_summary.get("distribution", {})
        if distribution:
            dist_parts = []
            if distribution.get("no_missing", 0) > 0:
                dist_parts.append(f"无缺失: {distribution['no_missing']}个")
            if distribution.get("low", 0) > 0:
                dist_parts.append(f"低(0-10%): {distribution['low']}个")
            if distribution.get("medium", 0) > 0:
                dist_parts.append(f"中(10-30%): {distribution['medium']}个")
            if distribution.get("high", 0) > 0:
                dist_parts.append(f"高(30-50%): {distribution['high']}个")
            if distribution.get("very_high", 0) > 0:
                dist_parts.append(f"极高(>50%): {distribution['very_high']}个")
            if dist_parts:
                missing_detail_str = f"\n- 缺失率分布: {', '.join(dist_parts)}"
        
        # 高缺失率特征预警（>30%）
        high_missing_features = missing_summary.get("high_missing_features", [])
        if high_missing_features:
            high_missing_names = [f.get("variable") or f.get("name") for f in high_missing_features[:5]]
            high_missing_str = ", ".join(high_missing_names)
            suffix = f"等{len(high_missing_features)}个" if len(high_missing_features) > 5 else ""
            missing_detail_str += f"\n- ⚠️ 高缺失率特征(>30%): {high_missing_str}{suffix}"
    
    # ========== 特殊值替换信息（信贷风控数据的常见预处理）==========
    special_value_info = data.get("special_value_info", {})
    special_value_str = ""
    if special_value_info:
        affected = special_value_info.get("affected_features", 0)
        total_replaced = special_value_info.get("total_replaced", 0)
        if affected > 0 and total_replaced > 0:
            special_value_str = f"\n- 特殊值替换: {affected}个特征受影响，共替换{total_replaced:,}条记录"
            # 说明特殊值类型（如-9999等）
            special_values = special_value_info.get("special_values", [])
            if special_values:
                special_value_str += f"（特殊值: {', '.join(str(v) for v in special_values[:5])}）"
    
    # 数据集划分信息（包含OOT验证集）
    split_info = data.get("split_info", {})
    split_str = ""
    if split_info:
        train = split_info.get("train")
        test = split_info.get("test")
        oot = split_info.get("oot")
        train_str = f"{train:,}" if isinstance(train, int) else "N/A"
        test_str = f"{test:,}" if isinstance(test, int) else "N/A"
        split_str = f"\n- 数据集划分: 训练集 {train_str}, 测试集 {test_str}"
        # OOT验证集信息
        if isinstance(oot, int) and oot > 0:
            split_str += f", OOT验证集 {oot:,}"
        elif isinstance(oot, int) and oot == 0:
            split_str += "（未设置OOT验证集）"
        
        # 划分方式（优先使用详细信息，否则使用简要描述）
        split_details = split_info.get("split_details")
        if split_details:
            split_str += f"\n- 划分方式:"
            split_str += f"\n  - 训练集/测试集: {split_details.get('train_test', 'N/A')}"
            split_str += f"\n  - OOT验证集: {split_details.get('oot', 'N/A')}"
        else:
            split_method_desc = split_info.get("split_method_desc") or split_info.get("split_method")
            if split_method_desc:
                split_str += f"\n- 划分方式: {split_method_desc}"
    
    # 各数据集坏账率（评分卡任务特有）
    target_rates = data.get("target_rates", {})
    target_rates_str = ""
    if target_rates:
        rates_parts = []
        if target_rates.get("train") is not None:
            rates_parts.append(f"训练集 {target_rates['train'] * 100:.2f}%")
        if target_rates.get("test") is not None:
            rates_parts.append(f"测试集 {target_rates['test'] * 100:.2f}%")
        if target_rates.get("oot") is not None:
            rates_parts.append(f"OOT {target_rates['oot'] * 100:.2f}%")
        if rates_parts:
            target_rates_str = f"\n- 各数据集坏账率: {', '.join(rates_parts)}"
    
    # 时间范围信息（评分卡任务特有，当使用时间划分时）
    time_range_info = data.get("time_range_info")
    time_range_str = ""
    if time_range_info:
        time_col = time_range_info.get("column", "")
        time_range_str = f"\n- 时间划分列: {time_col}"
        
        train_range = time_range_info.get("train")
        test_range = time_range_info.get("test")
        oot_range = time_range_info.get("oot")
        
        if train_range:
            time_range_str += f"\n  - 训练集: {train_range.get('min', 'N/A')} ~ {train_range.get('max', 'N/A')}"
        if test_range:
            time_range_str += f"\n  - 测试集: {test_range.get('min', 'N/A')} ~ {test_range.get('max', 'N/A')}"
        if oot_range:
            time_range_str += f"\n  - OOT验证集: {oot_range.get('min', 'N/A')} ~ {oot_range.get('max', 'N/A')}"
    
    outlier_count = data.get("outlier_count")
    outlier_str = f"\n- 异常值特征数: {outlier_count}" if outlier_count is not None else ""
    
    derived_total_str = ""
    if derived_features.get("total_derived", 0) > 0:
        derived_total_str = f"\n- 衍生后特征数: {total_features}"
    
    # ========== 数据质量评估（规则挖掘任务特有）==========
    # 注意：quality_score 不再注入 AI prompt，避免 AI 引用一个用户在 UI 上看不到的评分造成困惑。
    # quality_score 仍在后端计算，用于特征工程阶段跳过时的提示文案和内部 needs_feature_engineering 判定。
    quality_str = ""
    quality_issues = data.get("quality_issues", [])
    if quality_issues:
        issues_text = "; ".join(str(issue) for issue in quality_issues[:3])
        quality_str = f"\n- 数据质量注意事项: {issues_text}"
    
    # ========== var_filter数据质量筛选（评分卡任务特有，参考scorecardpy库设计）==========
    var_filter_str = ""
    var_filter_result = data.get("var_filter_result")
    if var_filter_result:
        input_features = var_filter_result.get("input_features", 0)
        output_features = var_filter_result.get("output_features", 0)
        removed_count = len(var_filter_result.get("removed_features", []))
        if removed_count > 0:
            var_filter_str = f"\n- var_filter筛选: {input_features} → {output_features} 个特征（移除{removed_count}个）"
            # 移除原因明细
            removed_by_missing = var_filter_result.get("removed_by_missing", [])
            removed_by_identical = var_filter_result.get("removed_by_identical", [])
            if removed_by_missing:
                missing_limit = var_filter_result.get("missing_limit", 0.95)
                var_filter_str += f"\n  - 高缺失率(≥{missing_limit:.0%}): {len(removed_by_missing)}个"
            if removed_by_identical:
                identical_limit = var_filter_result.get("identical_limit", 0.95)
                var_filter_str += f"\n  - 高同值率(≥{identical_limit:.0%}): {len(removed_by_identical)}个"
    
    # ========== P2-6: 类别不平衡分析信息 ==========
    imbalance_str = ""
    imbalance_analysis = data.get("imbalance_analysis")
    if imbalance_analysis and isinstance(imbalance_analysis, dict):
        severity = imbalance_analysis.get("severity", "")
        applied = imbalance_analysis.get("applied_strategy", "")
        user_strategy = imbalance_analysis.get("user_strategy", "")
        desc = imbalance_analysis.get("strategy_description", "")
        ratio = imbalance_analysis.get("imbalance_ratio", "")
        imbalance_str = f"\n- 类别不平衡: 程度={severity}, 比例={ratio}, 用户选择={user_strategy}, 实际策略={applied}（{desc}）"
    
    return f"""
- 总行数: {rows_str}
- 可用特征数: {feature_count}（已排除目标列和用户指定的排除变量）{derived_total_str}{var_filter_str}
- 平均缺失率: {missing_str}{missing_detail_str}{special_value_str}
- 坏账率: {target_str}{split_str}{target_rates_str}{time_range_str}{outlier_str}{quality_str}{imbalance_str}{derived_info}{exclude_info}"""


def _build_woe_binning_description(data: dict[str, Any]) -> str:
    """WOE分箱阶段描述"""
    iv_table = data.get("iv_table", [])
    top_iv_features = []
    for f in iv_table[:5]:
        feature = f.get("feature", "N/A")
        iv = f.get("iv")
        iv_str = f"{iv:.4f}" if iv is not None else "N/A"
        top_iv_features.append(f"{feature}: IV={iv_str}")
    top_iv_str = ", ".join(top_iv_features) if top_iv_features else "N/A"
    
    total_features = data.get("total_features", "N/A")
    input_features = data.get("input_features", total_features)  # 输入特征数（来自数据加载阶段）
    iv_range = data.get("iv_range") or {}
    iv_max = _format_number(iv_range.get("max"))
    iv_min = _format_number(iv_range.get("min"))
    
    # WOE分箱过程中过滤的特征信息（合并预先过滤和scorecardpy过滤）
    woe_filtered_str = ""
    woe_filtered = data.get("woe_filtered")
    if woe_filtered and woe_filtered.get("count", 0) > 0:
        filtered_count = woe_filtered["count"]
        filtered_reason = woe_filtered.get("reason", "常量列/全NaN/非数值/分箱失败")
        filtered_features = woe_filtered.get("features", [])
        feature_preview = ", ".join(filtered_features[:5]) if filtered_features else ""
        if len(filtered_features) > 5:
            feature_preview += f"... (共{len(filtered_features)}个)"
        woe_filtered_str = f"\n- 分箱过程过滤: {filtered_count}个特征被过滤 ({filtered_reason})"
        if feature_preview:
            woe_filtered_str += f"\n  - 过滤特征: {feature_preview}"
    
    # 如果输入和输出特征数不同，添加说明
    feature_flow_str = ""
    if input_features != total_features and isinstance(input_features, int) and isinstance(total_features, int):
        feature_flow_str = f"\n- 特征流转: {input_features} → {total_features} (分箱过程过滤{input_features - total_features}个)"
    
    return f"""
- 分箱特征数: {total_features}{feature_flow_str}{woe_filtered_str}
- 最大IV: {iv_max}
- 最小IV: {iv_min}
- Top 5 IV特征: {top_iv_str}"""


def _build_feature_selection_description(data: dict[str, Any]) -> str:
    """特征筛选阶段描述"""
    selected_count = data.get("after_count") or data.get("selected_count") or len(data.get("selected_features", []))
    original_count = data.get("before_count") or data.get("original_count")
    removed_count = (original_count - selected_count) if original_count and selected_count else data.get("removed_features", [])
    if isinstance(removed_count, list):
        removed_count = len(removed_count)
    
    # IV分布统计
    iv_dist_info = ""
    iv_distribution = data.get("iv_distribution")
    if iv_distribution:
        total_iv = sum([
            iv_distribution.get("strong", 0),
            iv_distribution.get("medium_strong", 0),
            iv_distribution.get("medium", 0),
            iv_distribution.get("weak", 0)
        ])
        iv_dist_info = f"""
- IV分布（筛选前{total_iv}个特征的IV统计，非移除数）: 强(≥0.1): {iv_distribution.get('strong', 0)}, 中强(0.05-0.1): {iv_distribution.get('medium_strong', 0)}, 中(0.02-0.05): {iv_distribution.get('medium', 0)}, 弱(<0.02): {iv_distribution.get('weak', 0)}"""
    
    iv_threshold = data.get("iv_threshold")
    if iv_threshold:
        iv_dist_info += f"\n- IV筛选阈值: {iv_threshold}（低于此阈值的特征被移除）"
    
    # One-Hot 统计
    onehot_stats = data.get("onehot_stats", {})
    onehot_info = ""
    if onehot_stats.get("original_count", 0) > 0:
        after_onehot = (original_count or 0) - onehot_stats.get("original_count", 0) + onehot_stats.get("derived_count", 0)
        onehot_info = f" → {after_onehot}（One-Hot后）"
        onehot_detail = f"\n- One-Hot编码: {onehot_stats['original_count']}列被编码为{onehot_stats.get('derived_count', 0)}个二值特征（净增{onehot_stats.get('derived_count', 0) - onehot_stats['original_count']}个）"
    else:
        onehot_detail = ""
    
    selected_features = data.get("selected_features", [])
    selected_str = ""
    if selected_features:
        display = selected_features[:10]
        selected_str = f"\n- 保留特征: {', '.join(display)}{'...' if len(selected_features) > 10 else ''}"
    
    selection_method = data.get("selection_method")
    method_str = f"\n- 筛选方法: {selection_method}" if selection_method else ""
    
    warning = data.get("warning")
    warning_str = f"\n- ⚠️ 警告: {warning}" if warning else ""
    
    # P1-4: datetime/text 衍生信息（从预处理阶段移入）
    derived_features = data.get("derived_features", {})
    derivation_str = ""
    if derived_features.get("total_derived", 0) > 0:
        dt_info = derived_features.get("datetime", {})
        txt_info = derived_features.get("text", {})
        parts = []
        if dt_info.get("derived_count", 0) > 0:
            parts.append(f"日期时间衍生+{dt_info['derived_count']}个(来源:{','.join(dt_info.get('source_cols', [])[:3])})")
        if txt_info.get("derived_count", 0) > 0:
            parts.append(f"文本衍生+{txt_info['derived_count']}个(来源:{','.join(txt_info.get('source_cols', [])[:3])})")
        if parts:
            derivation_str = f"\n- 特征衍生: {', '.join(parts)}"
    
    return f"""
- 特征变化流程: {original_count or 'N/A'}{onehot_info} → {selected_count or 'N/A'}（IV筛选后）{onehot_detail}{derivation_str}
- IV筛选移除: {removed_count or 'N/A'}个特征{iv_dist_info}{selected_str}{method_str}{warning_str}"""


def _build_model_training_description(data: dict[str, Any]) -> str:
    """模型训练阶段描述
    
    注：AUC/KS 等模型性能指标在 model_evaluation 阶段评估，
    本阶段聚焦于模型系数、显著性、迭代验证等训练过程信息。
    """
    coefficients = data.get("coefficients", [])
    feature_count = len(coefficients) or len(data.get("feature_importance", {}).keys())
    
    intercept = data.get("intercept")
    intercept_str = _format_number(intercept)
    
    # B+方案：展示配置信息
    config = data.get("config", {})
    config_str = ""
    if config:
        sig_mode = config.get("significance_mode", "warn")
        coef_mode = config.get("coefficient_direction_mode", "warn")
        max_iter = config.get("max_validation_iterations", 10)
        config_str = f"\n- 验证配置: 显著性={sig_mode}, 系数方向={coef_mode}, 最大迭代={max_iter}"
    
    # B+方案：展示迭代验证结果
    post_validation = data.get("post_validation", {})
    validation_str = ""
    if post_validation:
        converged = post_validation.get("converged", False)
        total_iter = post_validation.get("total_iterations", 0)
        final_count = post_validation.get("final_feature_count", feature_count)
        iterations = post_validation.get("iterations", [])
        
        # 2026-02-10: 提取初始特征数（第一轮迭代的特征数）
        initial_count = iterations[0].get("feature_count") if iterations else feature_count
        
        # 统计总共移除的特征
        all_removed = []
        for iter_log in iterations:
            for removed in iter_log.get("removed_this_iteration", []):
                all_removed.append(f"{removed['feature']}({removed['reason']})")
        
        status = "✓收敛" if converged else "达到最大迭代"
        # 2026-02-10: 修复特征变化描述，正确展示初始→最终特征数
        if all_removed:
            removed_preview = ', '.join(all_removed[:3])
            suffix = f"...等{len(all_removed)}个" if len(all_removed) > 3 else ""
            validation_str = f"\n- 迭代验证: {initial_count}→{final_count}个特征（{total_iter}轮{status}，移除{len(all_removed)}个: {removed_preview}{suffix}）"
        else:
            validation_str = f"\n- 迭代验证: {total_iter}轮{status}，{initial_count}个特征全部保留"
    
    # 方案1：新增逐步回归结果展示（兼容旧结构）
    stepwise_result = data.get("stepwise_result", {})
    stepwise_str = ""
    if stepwise_result:
        removed_by_stepwise = stepwise_result.get("removed_features", [])
        before_count = stepwise_result.get("before_count")
        after_count = stepwise_result.get("after_count")
        if removed_by_stepwise:
            removed_preview = ', '.join(str(f) for f in removed_by_stepwise[:5])
            suffix = f"...等{len(removed_by_stepwise)}个" if len(removed_by_stepwise) > 5 else ""
            stepwise_str = f"\n- 逐步回归: {before_count or 'N/A'} → {after_count or feature_count}特征，移除{len(removed_by_stepwise)}个 ({removed_preview}{suffix})"
        elif before_count:
            stepwise_str = f"\n- 逐步回归: 全部{before_count}个特征通过（未移除）"
    
    # 方案1：新增系数方向验证结果展示（兼容旧结构，B+方案已在post_validation中包含）
    coefficient_validation = data.get("coefficient_validation", {})
    coef_valid_str = ""
    if coefficient_validation and not post_validation:  # 如果有post_validation则不重复展示
        invalid_direction = coefficient_validation.get("invalid_direction", [])
        removed_by_coef = coefficient_validation.get("removed_features", [])
        mode = coefficient_validation.get("mode", "warn")
        if invalid_direction:
            invalid_preview = ', '.join(str(f) for f in invalid_direction[:3])
            suffix = f"等{len(invalid_direction)}个" if len(invalid_direction) > 3 else ""
            if removed_by_coef:
                coef_valid_str = f"\n- 系数方向验证: 移除{len(removed_by_coef)}个异常特征 ({invalid_preview}{suffix})"
            else:
                coef_valid_str = f"\n- 系数方向验证: {len(invalid_direction)}个特征系数为负（{mode}模式，{invalid_preview}{suffix}）"
        else:
            coef_valid_str = "\n- 系数方向验证: 全部通过"
    
    # B+方案：展示全部入模特征（如果有）
    all_coefficients = data.get("all_coefficients", [])
    all_coef_str = ""
    if all_coefficients and len(all_coefficients) > len(coefficients):
        all_coef_str = f"\n- 全部入模特征: {len(all_coefficients)}个"
    
    # 使用完整系数列表进行分析（如果有）
    analysis_coefficients = all_coefficients if all_coefficients else coefficients
    
    # 展示 Top 5 特征的系数和P值
    top_coeffs = []
    for c in coefficients[:5]:
        feature = c.get("feature", "N/A")
        coef = c.get("coefficient")
        pvalue = c.get("pvalue")
        coef_str = _format_number(coef)
        pvalue_str = _format_number(pvalue)
        # 判断显著性
        sig_mark = ""
        if pvalue is not None:
            if pvalue < 0.01:
                sig_mark = "**"
            elif pvalue < 0.05:
                sig_mark = "*"
        top_coeffs.append(f"{feature}(系数={coef_str}, P={pvalue_str}{sig_mark})")
    
    top_coeffs_str = f"\n- Top 5 特征: {', '.join(top_coeffs)}" if top_coeffs else ""
    
    # P值整体判断
    pvalue_summary = ""
    if analysis_coefficients:
        pvalues = [c.get("pvalue") for c in analysis_coefficients if c.get("pvalue") is not None]
        if pvalues:
            sig_count = sum(1 for p in pvalues if p < 0.05)
            high_sig_count = sum(1 for p in pvalues if p < 0.01)
            pvalue_summary = f"\n- P值显著性: {sig_count}/{len(pvalues)}个特征P<0.05显著，其中{high_sig_count}个P<0.01高度显著"
    
    # === 新增：标准误和置信区间异常检测 ===
    std_err_warnings = []  # 场景1：标准误异常大
    ci_contains_zero = []  # 场景2：置信区间包含0
    ci_too_wide = []       # 场景3：置信区间过宽
    
    for c in analysis_coefficients:
        feature = c.get("feature", "N/A")
        coef = c.get("coefficient")
        std_err = c.get("std_err")
        ci_lower = c.get("ci_lower")
        ci_upper = c.get("ci_upper")
        
        # 场景1：标准误异常大（标准误 > 系数绝对值，说明系数/标准误 < 1）
        if std_err is not None and coef is not None and abs(coef) > 0:
            ratio = abs(coef) / std_err
            if ratio < 1:  # 系数/标准误 < 1，异常大
                std_err_warnings.append(f"{feature}(系数/标准误={ratio:.2f})")
            elif ratio < 2:  # 1 < 系数/标准误 < 2，需关注
                std_err_warnings.append(f"{feature}(系数/标准误={ratio:.2f},边缘)")
        
        # 场景2：置信区间包含0（特征可能不显著）
        if ci_lower is not None and ci_upper is not None:
            if ci_lower <= 0 <= ci_upper:
                ci_contains_zero.append(feature)
            
            # 场景3：置信区间过宽（区间宽度 > 系数绝对值的2倍）
            ci_width = ci_upper - ci_lower
            if coef is not None and abs(coef) > 0:
                if ci_width > abs(coef) * 2:
                    ci_too_wide.append(f"{feature}(区间宽度={ci_width:.4f})")
    
    # 构建异常检测报告
    diagnostic_str = ""
    if std_err_warnings:
        diagnostic_str += f"\n- ⚠️ 标准误偏大: {', '.join(std_err_warnings[:3])}"
        if len(std_err_warnings) > 3:
            diagnostic_str += f"等{len(std_err_warnings)}个"
        diagnostic_str += " [可能原因:多重共线性，建议:计算VIF/启用逐步回归/使用L1正则化]"
    
    if ci_contains_zero:
        diagnostic_str += f"\n- ⚠️ 置信区间包含0: {', '.join(ci_contains_zero[:3])}"
        if len(ci_contains_zero) > 3:
            diagnostic_str += f"等{len(ci_contains_zero)}个"
        diagnostic_str += " [特征可能不显著，建议:检查IV值/考虑移除/重新分箱]"
    
    if ci_too_wide and not ci_contains_zero:  # 如果已有包含0的警告，不重复提示宽度问题
        diagnostic_str += f"\n- ⚠️ 置信区间过宽: {', '.join(ci_too_wide[:3])}"
        if len(ci_too_wide) > 3:
            diagnostic_str += f"等{len(ci_too_wide)}个"
        diagnostic_str += " [估计不稳定，建议:增加样本量/简化模型/检查类别平衡]"
    
    # 如果没有异常，给出正面评价
    if not diagnostic_str and analysis_coefficients:
        has_std_err = any(c.get("std_err") is not None for c in analysis_coefficients)
        if has_std_err:
            diagnostic_str = "\n- ✓ 标准误和置信区间: 所有特征统计指标正常"
    
    # === 新增：模型拟合指标（2026-02-11 行业惯例补充）===
    model_fit = data.get("model_fit", {})
    fit_metrics_str = ""
    if model_fit:
        lr_pvalue = model_fit.get("lr_pvalue")
        pseudo_r2 = model_fit.get("pseudo_r2")
        aic = model_fit.get("aic")
        bic = model_fit.get("bic")
        
        # 似然比检验是模型整体显著性的金标准（行业惯例）
        if lr_pvalue is not None:
            lr_sig = "✓显著" if lr_pvalue < 0.05 else "✗不显著"
            fit_metrics_str += f"\n- 似然比检验: P={_format_number(lr_pvalue)} ({lr_sig}) - 评估模型整体有效性"
        
        # 伪R²提供拟合优度参考
        if pseudo_r2 is not None:
            fit_metrics_str += f"\n- 伪R²: {(pseudo_r2 * 100):.2f}% (McFadden，评分卡通常5-20%)"
        
        # AIC/BIC作为参考
        if aic is not None and bic is not None:
            fit_metrics_str += f"\n- 信息准则: AIC={_format_number(aic)}, BIC={_format_number(bic)}"
    
    # 注：AUC/KS 等性能指标在 model_evaluation 阶段评估，此处不展示
    return f"""
- 入模特征数: {feature_count or 'N/A'}{config_str}{stepwise_str}{validation_str}{coef_valid_str}{all_coef_str}
- 截距项: {intercept_str}{fit_metrics_str}{top_coeffs_str}{pvalue_summary}{diagnostic_str}"""


def _build_model_evaluation_description(data: dict[str, Any]) -> str:
    """模型评估阶段描述
    
    包含以下评估维度：
    1. 区分能力：AUC/KS（训练集、测试集、OOT）
    2. 稳定性：PSI（评分分布稳定性）
    3. 过拟合检测：训练/测试集指标差异
    4. 排序性分析：单调性检验、首尾Lift分析（基于Decile等频分箱）
    """
    train_metrics = data.get("train_metrics", {})
    test_metrics = data.get("test_metrics", {})
    oot_metrics = data.get("oot_metrics", {})
    
    test_ks = data.get("test_ks") or test_metrics.get("ks") or data.get("ks")
    test_auc = data.get("test_auc") or test_metrics.get("auc") or data.get("auc")
    train_ks = data.get("train_ks") or train_metrics.get("ks")
    train_auc = data.get("train_auc") or train_metrics.get("auc")
    gini = data.get("gini") or test_metrics.get("gini")
    overfit_warning = data.get("overfit_warning")
    
    # OOT指标（如有）- 判断是否有OOT数据
    oot_ks = oot_metrics.get("ks") if oot_metrics else None
    oot_auc = oot_metrics.get("auc") if oot_metrics else None
    oot_gini = oot_metrics.get("gini") if oot_metrics else None
    has_oot = oot_ks is not None or oot_auc is not None
    
    # PSI 支持两种格式：直接数值 或 psi_result 字典
    psi = data.get("psi")
    psi_result = data.get("psi_result")
    psi_str = ""
    
    if psi_result and isinstance(psi_result, dict):
        # psi_result 格式: {"value": 0.002, "comparison": "训练集 vs 测试集", "stability": "稳定", "level": "good"}
        psi_value = psi_result.get("value")
        psi_stability = psi_result.get("stability", "")
        psi_comparison = psi_result.get("comparison", "")
        if psi_value is not None:
            psi_str = f"\n- PSI: {_format_number(psi_value)} ({psi_stability}，{psi_comparison})"
    elif psi is not None:
        # 直接数值格式
        psi_str = f"\n- PSI: {_format_number(psi)}"
    
    _gini_str = f"\n- Gini: {_format_number(gini)}" if gini is not None else ""  # 保留备用
    warning_str = f"\n- ⚠️ 过拟合警告: {overfit_warning}" if overfit_warning else ""
    
    # ========== CSI 特征稳定性（与 PSI 互补）==========
    # CSI 监控各入模特征的分布变化，定位 PSI 劣化的根因
    csi_str = ""
    csi_report = data.get("csi_train_vs_oot") or data.get("csi_train_vs_test")
    if csi_report and isinstance(csi_report, dict):
        csi_features = csi_report.get("features", [])
        csi_summary = csi_report.get("summary", {})
        csi_comparison = csi_report.get("comparison", "")
        
        if csi_features:
            total = csi_summary.get("total_features", len(csi_features))
            stable = csi_summary.get("stable", 0)
            slight = csi_summary.get("slight_change", 0)
            significant = csi_summary.get("significant_change", 0)
            
            csi_str = f"\n\n### CSI 特征稳定性（{csi_comparison}）"
            csi_str += f"\n- 总特征数: {total}，稳定: {stable}，轻微漂移: {slight}，显著漂移: {significant}"
            
            # 列出不稳定的特征（CSI ≥ 0.1）
            unstable_features = [f for f in csi_features if f.get("csi", 0) >= 0.1]
            if unstable_features:
                csi_str += "\n- 需关注特征:"
                for feat in unstable_features[:5]:
                    csi_str += f"\n  - {feat['feature']}: CSI={_format_number(feat['csi'])}（{feat.get('stability', '')}）"
                if len(unstable_features) > 5:
                    csi_str += f"\n  - ...等{len(unstable_features)}个特征"
            else:
                csi_str += "\n- 所有入模特征分布稳定（CSI均<0.1）"
    
    # ========== 区分能力指标展示（有OOT时优先OOT）==========
    # 行业标准：OOT验证集最能反映模型在实际业务中的表现
    if has_oot:
        # 有OOT时：优先展示OOT指标
        primary_auc = oot_auc
        primary_ks = oot_ks
        primary_gini = oot_gini if oot_gini is not None else (2 * oot_auc - 1 if isinstance(oot_auc, (int, float)) else None)
        primary_label = "OOT验证集"
        # 测试集作为参照
        secondary_str = f"""
- 测试集 AUC: {_format_number(test_auc)}
- 测试集 KS: {_format_number(test_ks)}"""
    else:
        # 无OOT时：使用测试集指标
        primary_auc = test_auc
        primary_ks = test_ks
        primary_gini = gini
        primary_label = "测试集"
        secondary_str = ""
    
    # 构建主要指标展示（按重要性：主评估数据集 → 测试集 → 训练集）
    primary_gini_str = f"\n- {primary_label} Gini: {_format_number(primary_gini)}" if primary_gini is not None else ""
    
    # ========== 排序性分析（行业标准：优先OOT，其次测试集）==========
    rank_ordering_str = ""
    score_distribution = data.get("score_distribution", {})
    
    # 优先使用OOT数据，其次测试集（行业标准）
    oot_dist = score_distribution.get("oot", {}) if isinstance(score_distribution, dict) else {}
    test_dist = score_distribution.get("test") or {} if isinstance(score_distribution, dict) else {}
    train_dist = score_distribution.get("train") or {} if isinstance(score_distribution, dict) else {}
    
    # 确定主要评估数据集：优先OOT，其次测试集
    primary_dist = oot_dist if oot_dist else test_dist
    primary_dist_label = "OOT验证集" if oot_dist else "测试集"
    
    # 兼容旧格式（直接存储score_distribution而非嵌套结构）
    if not primary_dist and not train_dist and isinstance(score_distribution, dict):
        if "rank_ordering_analysis" in score_distribution or "ranking_analysis" in score_distribution:
            primary_dist = score_distribution
            primary_dist_label = "测试集"  # 旧格式默认是测试集
    
    # 获取排序性分析结果
    rank_ordering_analysis = primary_dist.get("rank_ordering_analysis", {})
    if not rank_ordering_analysis:
        rank_ordering_analysis = train_dist.get("rank_ordering_analysis", {})
    
    if rank_ordering_analysis:
        # 单调性检验
        monotonicity = rank_ordering_analysis.get("monotonicity", {})
        is_monotonic = monotonicity.get("is_monotonic", True)
        violations = monotonicity.get("violations", [])
        violation_details = monotonicity.get("violation_details", [])
        
        monotonicity_status = "✓ 通过" if is_monotonic else f"✗ 不通过（{len(violations)}处违反）"
        rank_ordering_str += f"\n\n### 排序性分析（基于{primary_dist_label}Decile分箱）"
        rank_ordering_str += f"\n- 单调性检验: {monotonicity_status}"
        
        # 如果有违反，列出详情（最多3个）
        if violation_details:
            rank_ordering_str += "\n  违反详情:"
            for detail in violation_details[:3]:
                _ = detail.get("prev_bin", "")  # prev_bin保留备用
                curr_bin = detail.get("curr_bin", "")
                prev_rate = detail.get("prev_bad_rate", 0)
                curr_rate = detail.get("curr_bad_rate", 0)
                diff = detail.get("diff", 0)
                rank_ordering_str += f"\n  - {curr_bin}: 坏样本率从{prev_rate:.2f}%上升到{curr_rate:.2f}%（+{diff}%）"
            if len(violation_details) > 3:
                rank_ordering_str += f"\n  - ...等{len(violation_details)}处"
        
        # Lift分析
        lift_analysis = rank_ordering_analysis.get("lift_analysis", {})
        first_lift = lift_analysis.get("first_decile_lift")
        last_lift = lift_analysis.get("last_decile_lift")
        first_bin = lift_analysis.get("first_decile_bin", "")
        last_bin = lift_analysis.get("last_decile_bin", "")
        first_bad_rate = lift_analysis.get("first_decile_bad_rate")
        last_bad_rate = lift_analysis.get("last_decile_bad_rate")
        
        if first_lift is not None:
            # 首组Lift评级
            first_lift_rating = "优秀" if first_lift >= 2.5 else ("良好" if first_lift >= 2 else ("合格" if first_lift >= 1.5 else "偏低"))
            rank_ordering_str += f"\n- 首组Lift: {first_lift:.2f}（{first_lift_rating}，{first_bin}，坏样本率{first_bad_rate:.2f}%）"
        
        if last_lift is not None:
            # 末组Lift评级
            last_lift_rating = "优秀" if last_lift <= 0.3 else ("良好" if last_lift <= 0.5 else ("合格" if last_lift <= 0.8 else "偏高"))
            rank_ordering_str += f"\n- 末组Lift: {last_lift:.2f}（{last_lift_rating}，{last_bin}，坏样本率{last_bad_rate:.2f}%）"
    
    # ========== 评分分布摘要（增强版：包含分布形态分析）==========
    summary_str = ""
    dist_summary = primary_dist.get("summary", {}) or train_dist.get("summary", {})
    if dist_summary:
        total_samples = dist_summary.get("total_samples")
        overall_bad_rate = dist_summary.get("overall_bad_rate")
        good_mean = dist_summary.get("good_mean")
        bad_mean = dist_summary.get("bad_mean")
        
        if total_samples is not None:
            summary_str += f"\n\n### 评分分布统计"
            summary_str += f"\n- 样本总量: {total_samples:,}"
            if overall_bad_rate is not None:
                summary_str += f"（坏样本率{overall_bad_rate:.2f}%）"
            if good_mean is not None and bad_mean is not None:
                score_diff = abs(good_mean - bad_mean)
                # 评价好坏样本分离度
                separation_rating = "优秀" if score_diff >= 60 else ("良好" if score_diff >= 40 else ("合格" if score_diff >= 20 else "偏低"))
                summary_str += f"\n- 好样本均值: {good_mean:.1f}, 坏样本均值: {bad_mean:.1f}（差值{score_diff:.1f}分，分离度{separation_rating}）"
    
    # ========== 评分分布形态分析（从bins数据提取）==========
    dist_bins = primary_dist.get("bins", []) or train_dist.get("bins", [])
    distribution_analysis = primary_dist.get("distribution_analysis", {}) or train_dist.get("distribution_analysis", {})
    
    if distribution_analysis or dist_bins:
        summary_str += "\n\n### 评分分布形态分析"
        
        # 从distribution_analysis获取更丰富的统计信息
        if distribution_analysis:
            # 标准差和分布范围
            score_std = distribution_analysis.get("score_std")
            score_range = distribution_analysis.get("score_range")
            score_iqr = distribution_analysis.get("score_iqr")
            if score_std is not None:
                summary_str += f"\n- 评分标准差: {score_std:.1f}"
            if score_range:
                summary_str += f"\n- 评分范围: {score_range[0]:.0f} ~ {score_range[1]:.0f}"
            if score_iqr:
                summary_str += f" (IQR: {score_iqr[0]:.0f} ~ {score_iqr[1]:.0f})"
        
        # 从bins数据分析分布集中度
        if dist_bins and len(dist_bins) >= 3:
            # 计算样本占比的变异系数，评估分布均匀度
            # 注意：bins数据中的样本数字段名是"total"而不是"count"
            bin_counts = [b.get("total", 0) or b.get("count", 0) for b in dist_bins]
            total_count = sum(bin_counts)
            if total_count > 0:
                bin_ratios = [c / total_count for c in bin_counts]
                max_ratio = max(bin_ratios)
                min_ratio = min(bin_ratios)
                
                # 找出最集中和最稀疏的分箱
                max_idx = bin_ratios.index(max_ratio)
                min_idx = bin_ratios.index(min_ratio)
                max_bin = dist_bins[max_idx].get("bin", f"第{max_idx+1}组")
                min_bin = dist_bins[min_idx].get("bin", f"第{min_idx+1}组")
                
                # 评估分布均匀度
                ratio_range = max_ratio - min_ratio
                uniformity = "均匀" if ratio_range < 0.08 else ("较均匀" if ratio_range < 0.15 else "不均匀")
                
                summary_str += f"\n- 分布集中度: {uniformity}（最大{max_bin}: {max_ratio*100:.1f}%, 最小{min_bin}: {min_ratio*100:.1f}%）"
                
                # 如果分布极度不均匀，给出警告
                if ratio_range >= 0.15:
                    summary_str += f"\n- ⚠️ 注意: 分布不均可能影响策略分段效果，建议检查分箱合理性"
    
    return f"""
### 区分能力指标
- {primary_label} AUC: {_format_number(primary_auc)}
- {primary_label} KS: {_format_number(primary_ks)}{primary_gini_str}{secondary_str}
- 训练集 AUC: {_format_number(train_auc)}
- 训练集 KS: {_format_number(train_ks)}

### 稳定性与过拟合{psi_str}{warning_str}{csi_str}{rank_ordering_str}{summary_str}"""


def _build_evaluating_rules_description(data: dict[str, Any]) -> str:
    """规则评估阶段描述"""
    before_count = data.get("before_count") or data.get("beforeCount", 0)
    after_count = data.get("after_count") or data.get("afterCount", 0)
    filter_criteria = data.get("filter_criteria") or data.get("filterCriteria", {})
    
    filter_rate = "N/A"
    if before_count > 0:
        filter_rate = f"{(before_count - after_count) / before_count * 100:.1f}"
    
    max_hit_rate = filter_criteria.get("max_hit_rate")
    min_lift = filter_criteria.get("min_lift")
    
    max_hit_str = f"\n- 最大命中率阈值: {max_hit_rate}" if max_hit_rate is not None else ""
    min_lift_str = f"\n- 最小提升度阈值: {min_lift}" if min_lift is not None else ""
    
    eval_stats = data.get("evaluation_stats")
    eval_str = f"\n- 评估统计: {json.dumps(eval_stats, ensure_ascii=False)}" if eval_stats else ""
    
    return f"""
- 过滤前规则数: {before_count or 'N/A'}
- 过滤后规则数: {after_count or 'N/A'}
- 过滤率: {filter_rate}%{max_hit_str}{min_lift_str}{eval_str}"""


def _build_score_scaling_description(data: dict[str, Any]) -> str:
    """评分转换阶段描述 - Phase 29增强版"""
    base_score = data.get("base_score") or data.get("baseScore")
    base_odds = data.get("base_odds") or data.get("baseOdds")
    pdo = data.get("pdo") or data.get("PDO")
    num_variables = data.get("num_variables") or data.get("numVariables") or len(data.get("scorecard_preview", []))
    
    # Phase 29: 新增理论评分范围
    theoretical_range = data.get("theoretical_score_range", {})
    theoretical_min = theoretical_range.get("min")
    theoretical_max = theoretical_range.get("max")
    theoretical_str = ""
    if theoretical_min is not None and theoretical_max is not None:
        theoretical_span = theoretical_max - theoretical_min
        theoretical_str = f"\n- 理论评分范围: {theoretical_min:.0f} ~ {theoretical_max:.0f}（区间{theoretical_span:.0f}分）"
    
    # Phase 29: 新增实际评分分布统计
    actual_stats = data.get("actual_score_stats", {})
    actual_str = ""
    if actual_stats:
        actual_min = actual_stats.get("min")
        actual_max = actual_stats.get("max")
        actual_mean = actual_stats.get("mean")
        actual_std = actual_stats.get("std")
        actual_median = actual_stats.get("median")
        q25 = actual_stats.get("q25")
        q75 = actual_stats.get("q75")
        
        if actual_min is not None and actual_max is not None:
            actual_str = f"\n- 实际评分分布: {actual_min:.0f} ~ {actual_max:.0f}"
            if actual_mean is not None:
                actual_str += f"，均值{actual_mean:.0f}"
            if actual_std is not None:
                actual_str += f"，标准差{actual_std:.1f}"
            if actual_median is not None:
                actual_str += f"，中位数{actual_median:.0f}"
            if q25 is not None and q75 is not None:
                actual_str += f"，IQR[{q25:.0f},{q75:.0f}]"
    
    # Phase 29: 变量得分详情
    scorecard_preview = data.get("scorecard_preview", [])
    var_score_details = []
    max_contribution = 0
    min_contribution = float('inf')
    
    for v in scorecard_preview:
        var_name = v.get("variable")
        if var_name == "basepoints":
            continue
        score_range = v.get("score_range")
        if score_range is not None:
            var_score_details.append(f"{var_name}(±{score_range:.0f})")
            max_contribution = max(max_contribution, score_range)
            min_contribution = min(min_contribution, score_range)
    
    var_str = ""
    if var_score_details:
        # 只显示前5个变量的得分贡献
        display_vars = var_score_details[:5]
        var_str = f"\n- 变量得分贡献: {', '.join(display_vars)}"
        if len(var_score_details) > 5:
            var_str += f"...（共{len(var_score_details)}个变量）"
        
        # 贡献度差异分析
        if max_contribution > 0 and min_contribution < float('inf'):
            contribution_ratio = max_contribution / min_contribution if min_contribution > 0 else float('inf')
            if contribution_ratio > 5:
                var_str += f"\n  ⚠️ 变量贡献度差异较大（最大/最小={contribution_ratio:.1f}倍）"
    
    # 诊断场景
    diagnostics = []
    
    # 1. 基准分合理性检查
    if base_score is not None:
        if base_score < 500 or base_score > 750:
            diagnostics.append(f"基准分{base_score}偏离常规范围(500-750)，请确认业务需求")
    
    # 2. PDO合理性检查
    if pdo is not None:
        if pdo < 15 or pdo > 60:
            diagnostics.append(f"PDO={pdo}偏离常规范围(15-60)，评分敏感度可能异常")
    
    # 3. 评分区分度检查
    if actual_stats.get("std") is not None:
        std = actual_stats["std"]
        if std < 30:
            diagnostics.append(f"评分标准差仅{std:.1f}，区分度可能不足，建议增大PDO")
    
    # 4. 评分范围检查
    if theoretical_min is not None and theoretical_max is not None:
        if theoretical_min < 200 or theoretical_max > 950:
            diagnostics.append("评分范围超出常规区间(200-950)，可能影响业务应用")
    
    diagnostics_str = ""
    if diagnostics:
        diagnostics_str = "\n\n【诊断提示】\n" + "\n".join(f"- {d}" for d in diagnostics)
    
    return f"""
- 基准分: {base_score or 'N/A'}
- 基准Odds: {base_odds or 'N/A'}（对应违约率约{100/(1+(base_odds or 1)):.2f}%）
- PDO: {pdo or 'N/A'}
- 评分卡变量数: {num_variables or 'N/A'}{theoretical_str}{actual_str}{var_str}{diagnostics_str}"""


def _build_generating_rules_description(data: dict[str, Any]) -> str:
    """规则生成阶段描述"""
    total_rules = data.get("total_rules") or data.get("totalRules", 0)
    mining_mode = data.get("mining_mode") or data.get("miningMode", "N/A")
    use_full_tree = data.get("use_full_tree") or data.get("useFullTree")
    n_vars = data.get("n_vars") or data.get("nVars")
    
    mode_display = "单变量规则" if mining_mode == "single" else ("多变量规则" if mining_mode == "multi" else mining_mode)
    
    full_tree_str = ""
    if mining_mode == "multi" and use_full_tree is not None:
        full_tree_str = f"\n- 多特征挖掘方法: {'全特征树' if use_full_tree else '组合树'}"
    
    n_vars_str = f"\n- 变量组合数: {n_vars}" if n_vars is not None else ""
    max_depth_str = f"\n- 决策树深度: {data.get('max_depth')}" if data.get("max_depth") is not None else ""
    min_samples_str = f"\n- 叶节点最小样本比例: {data.get('min_samples_leaf')}" if data.get("min_samples_leaf") is not None else ""
    tree_count_str = f"\n- 决策树数量: {data.get('tree_count')}" if data.get("tree_count") is not None else ""
    
    return f"""
- 生成规则数: {total_rules or 'N/A'}
- 挖掘模式: {mode_display}{full_tree_str}{n_vars_str}{max_depth_str}{min_samples_str}{tree_count_str}"""


def _build_filtering_rules_description(data: dict[str, Any]) -> str:
    """规则筛选阶段描述"""
    generated_count = data.get("generated_count") or data.get("before_count") or data.get("beforeCount", 0)
    monotonicity_filtered = data.get("direction_filtered_count") or generated_count
    after_count = data.get("after_count") or data.get("afterCount", 0)
    filter_criteria = data.get("filter_criteria") or {}
    filter_summary = data.get("filter_summary") or {}
    
    total_filter_rate = "N/A"
    if generated_count > 0:
        total_filter_rate = f"{(generated_count - after_count) / generated_count * 100:.1f}"
    
    direction_removed = filter_summary.get("direction_removed") or (generated_count - monotonicity_filtered)
    bad_rate_zero_removed = filter_summary.get("bad_rate_zero_removed", 0)
    lift_removed = filter_summary.get("lift_removed", "N/A")
    hit_rate_removed = filter_summary.get("hit_rate_removed", "N/A")
    
    min_lift = filter_criteria.get("min_lift", "N/A")
    max_hit_rate = filter_criteria.get("max_hit_rate", "N/A")
    
    # 坏账率为0移除行（仅当有此类移除时显示）
    bad_rate_zero_line = f"\n  - 坏账率为0: {bad_rate_zero_removed}条被移除" if bad_rate_zero_removed > 0 else ""
    
    # 构建清晰的筛选流程描述，避免 LLM 产生歧义
    # 使用"从X→Y"的流程表述，明确标注每步的输入输出数量
    return f"""
**筛选流程**:
1. 输入规则: {generated_count}条（规则生成阶段产出）
2. 单调性校验: {generated_count}→{monotonicity_filtered}（移除{direction_removed}条方向不一致的规则）{bad_rate_zero_line}
3. Lift阈值筛选: 移除{lift_removed}条（Lift<{min_lift}）
4. 命中率阈值筛选: 移除{hit_rate_removed}条（命中率>{max_hit_rate}）
5. 最终有效规则: {after_count}条

**筛选效果**: 从{generated_count}条筛选至{after_count}条，总过滤率{total_filter_rate}%
**筛选条件**: 最小Lift≥{min_lift}, 最大命中率≤{max_hit_rate}
（注意：本阶段仅关注筛选效果，规则生成参数如决策树深度、叶节点比例等属于上一阶段配置）"""


def _build_selecting_rules_description(data: dict[str, Any]) -> str:
    """最优规则选择阶段描述"""
    selected_count = data.get("after_count") or data.get("selected_count") or data.get("selectedCount") or len(data.get("optimal_rules") or [])
    candidate_count = data.get("before_count") or data.get("candidate_count") or data.get("candidateCount", 0)
    
    coverage = data.get("total_coverage")
    coverage_str = f"\n- 总覆盖率: {coverage * 100:.2f}%" if coverage is not None else ""
    
    avg_lift = data.get("avg_lift")
    avg_lift_str = f"\n- 平均提升度: {avg_lift:.2f}" if avg_lift is not None else ""
    
    selection_mode = data.get("selection_mode")
    mode_str = f"\n- 选择模式: {selection_mode}" if selection_mode else ""
    
    selection_method = data.get("selection_method")
    method_str = f"\n- 选择方法: {selection_method}" if selection_method else ""
    
    # P1-5: OOT 稳定性验证信息
    oot_stability = data.get("oot_stability")
    oot_str = ""
    if oot_stability and isinstance(oot_stability, dict):
        overall = oot_stability.get("overall_hit_rate", {})
        counts = oot_stability.get("stability_counts", {})
        bonus = oot_stability.get("stability_score_bonus", 0)
        overall_cv = overall.get("cv", 0)
        
        # 整体稳定性
        if overall_cv < 0.15:
            overall_level = "高度稳定"
        elif overall_cv < 0.25:
            overall_level = "稳定"
        elif overall_cv < 0.35:
            overall_level = "中等"
        else:
            overall_level = "不稳定"
        
        oot_str = (
            f"\n- OOT稳定性验证（{oot_stability.get('oot_samples', 0)}条验证数据）:"
            f"\n  整体命中率: 训练集{overall.get('train', 0):.2%} / 测试集{overall.get('test', 0):.2%} / OOT{overall.get('oot', 0):.2%}, CV={overall_cv:.4f}({overall_level})"
            f"\n  规则稳定性分布: 高度稳定{counts.get('highly_stable', 0)}条, 稳定{counts.get('stable', 0)}条, 中等{counts.get('moderate', 0)}条, 不稳定{counts.get('unstable', 0)}条"
            f"\n  稳定性评分加分: {'+' if bonus >= 0 else ''}{bonus}分"
        )
        
        # 列出不稳定规则（如果有）
        unstable = oot_stability.get("unstable_rules", [])
        if unstable:
            oot_str += f"\n  不稳定规则({len(unstable)}条): " + ", ".join(f'"{r[:50]}"' for r in unstable[:3])
            if len(unstable) > 3:
                oot_str += f"...等{len(unstable)}条"
    
    return f"""
- 候选规则数: {candidate_count or 'N/A'}
- 最优规则数: {selected_count or 'N/A'}{coverage_str}{avg_lift_str}{mode_str}{method_str}{oot_str}"""


def _build_rule_mining_description(data: dict[str, Any]) -> str:
    """规则挖掘阶段描述"""
    rule_count = data.get("rule_count") or len(data.get("rules", []))
    
    coverage = data.get("coverage")
    coverage_str = f"\n- 总覆盖率: {coverage * 100:.2f}%" if coverage is not None else ""
    
    precision = data.get("precision")
    precision_str = f"\n- 平均精准率: {precision * 100:.2f}%" if precision is not None else ""
    
    recall = data.get("recall")
    recall_str = f"\n- 平均召回率: {recall * 100:.2f}%" if recall is not None else ""
    
    rules = data.get("rules", [])[:3]
    rules_str = ""
    if rules:
        rule_lines = []
        for i, r in enumerate(rules):
            rule_text = r.get("rule") or r.get("condition") or r.get("name") or json.dumps(r, ensure_ascii=False)[:80]
            rule_lines.append(f"  {i + 1}. {rule_text}")
        rules_str = f"\n- Top 规则示例:\n{chr(10).join(rule_lines)}"
    
    return f"""
- 挖掘规则数: {rule_count or 'N/A'}{coverage_str}{precision_str}{recall_str}{rules_str}"""


def _build_report_generation_description(data: dict[str, Any]) -> str:
    """报告生成阶段描述"""
    status = data.get("status", "已完成")
    report_sections = data.get("report_sections", [])
    datasets = data.get("datasets", [])
    chart_types = data.get("chart_types", [])
    
    sections_str = f"\n- 报告章节: {', '.join(report_sections)}" if report_sections else ""
    datasets_str = f"\n- 评估数据集: {', '.join(datasets)}" if datasets else ""
    charts_str = f"\n- 包含图表: {', '.join(chart_types)}" if chart_types else ""
    
    has_chart = data.get("has_chart_data")
    chart_data_str = f"\n- 图表数据: {'已生成' if has_chart else '未生成'}" if has_chart is not None else ""
    
    quality_score = data.get("quality_score")
    quality_str = f"\n- 规则质量评分: {quality_score * 100:.1f}分" if quality_score is not None else ""
    
    quality_level = data.get("quality_level")
    level_str = f"\n- 质量等级: {quality_level}" if quality_level else ""
    
    validation_passed = data.get("validation_passed")
    validation_str = f"\n- 质量验证: {'通过' if validation_passed else '未通过'}" if validation_passed is not None else ""
    
    validation_issues = data.get("validation_issues", [])
    issues_str = ""
    if validation_issues:
        issue_lines = [f"  {i + 1}. {issue}" for i, issue in enumerate(validation_issues)]
        issues_str = f"\n- 验证问题:\n{chr(10).join(issue_lines)}"
    
    psi_summary = data.get("psi_summary", {})
    psi_str = ""
    if psi_summary:
        psi_str = f"""
- PSI稳定性分析:
  - 检测规则数: {psi_summary.get('total_rules_checked', 0)}
  - 稳定规则数(PSI<0.1): {psi_summary.get('stable_rules', 0)}
  - 不稳定规则数(PSI≥0.25): {psi_summary.get('unstable_rules', 0)}
  - 平均PSI: {_format_number(psi_summary.get('avg_psi'))}"""
    
    final_rules = data.get("final_rules_count")
    final_str = f"\n- 最终规则数: {final_rules}" if final_rules is not None else ""
    
    total_evaluated = data.get("total_rules_evaluated")
    evaluated_str = f"\n- 评估规则总数: {total_evaluated}" if total_evaluated is not None else ""
    
    has_tree = data.get("has_tree_structure")
    tree_str = f"\n- 决策树可视化: {'已生成' if has_tree else '未生成'}" if has_tree is not None else ""
    
    n_features = data.get("n_features")
    features_str = f"\n- 入模变量数: {n_features}" if n_features is not None else ""
    
    return f"""
- 报告状态: {status}{sections_str}{datasets_str}{charts_str}{chart_data_str}{quality_str}{level_str}{validation_str}{issues_str}{psi_str}{final_str}{evaluated_str}{tree_str}{features_str}"""


# =============================================================================
# 工厂函数（供外部调用）
# =============================================================================

def get_analysis_prompt(
    analysis_type: str,
    task_type: Optional[str] = None,
    stage_id: Optional[str] = None,
    stage_name: Optional[str] = None,
    data: Optional[dict[str, Any]] = None,
    result: Optional[dict[str, Any]] = None,
    analysis_depth: str = "standard"  # noqa: ARG001 - 保留用于未来扩展
) -> str:
    """
    获取 AI 分析提示词的统一工厂函数
    
    Args:
        analysis_type: 分析类型 ("overall" 或 "stage")
        task_type: 任务类型 ("scorecard_dev" 或 "rule_mining")
        stage_id: 阶段ID（stage分析必需）
        stage_name: 阶段名称（stage分析必需）
        data: 阶段数据（stage分析必需）
        result: 任务结果（overall分析必需）
        analysis_depth: 分析深度（预留，目前仅支持 "standard"）
    
    Returns:
        完整的分析提示词字符串
    """
    if analysis_type == "overall":
        if result is None:
            raise ValueError("Overall analysis requires 'result' parameter")
        task_type_name = "评分卡开发" if task_type == "scorecard_dev" else "规则挖掘"
        return get_overall_analysis_prompt(task_type_name, result)
    
    elif analysis_type == "stage":
        if stage_id is None or data is None:
            raise ValueError("Stage analysis requires 'stage_id' and 'data' parameters")
        return get_stage_analysis_prompt(
            stage_id=stage_id,
            stage_name=stage_name or stage_id,
            data=data,
            task_type=task_type
        )
    
    else:
        raise ValueError(f"Unknown analysis_type: {analysis_type}")


# =============================================================================
# AI 分析专用参数配置
# =============================================================================

AI_ANALYSIS_PARAMS = {
    "temperature": 0.3,        # 降低随机性，提高输出稳定性
    "frequency_penalty": 0.3,  # 温和抑制重复
    "presence_penalty": 0.2,   # 轻微鼓励多样性
    "max_tokens": 4096,        # 阶段分析输出限制
}
