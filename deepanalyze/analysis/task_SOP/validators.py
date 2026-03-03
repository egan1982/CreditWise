"""
验证器模块 - 规则质量验证与评分卡质量验证

本模块包含用于评估模型和规则质量的验证器类：
- RuleValidator: 规则质量验证器（行业标准版）
- ScorecardValidator: 评分卡质量验证器

这些验证器在报告生成阶段使用，提供标准化的质量评估报告。
"""

from typing import Any
import numpy as np
import pandas as pd


def _safe_eval_rule(df: pd.DataFrame, rule: str, df_name: str = 'df') -> pd.Series:
    """
    安全执行规则表达式
    
    Args:
        df: 数据DataFrame
        rule: 规则表达式
        df_name: DataFrame变量名
        
    Returns:
        布尔Series，表示每行是否满足规则
    """
    # 替换 df_name 为实际的 DataFrame 引用
    rule_expr = rule.replace(f'{df_name}[', 'df[')
    
    # 创建安全的执行环境
    safe_globals = {
        '__builtins__': {},
        'df': df,
        'pd': pd,
        'np': np
    }
    
    try:
        result = eval(rule_expr, safe_globals)
        if isinstance(result, pd.Series):
            return result.astype(bool)
        else:
            return pd.Series([False] * len(df), index=df.index)
    except Exception:
        return pd.Series([False] * len(df), index=df.index)


class RuleValidator:
    """
    规则质量验证器（行业标准版）
    
    基于信贷风控行业通用标准，在规则生成后自动检测规则集质量问题，包括：
    
    核心指标（权重较高）：
    - 区分度评估：基于Lift评估规则区分好坏客户的能力
    - 召回率评估：规则集对坏客户的捕获能力
    - 稳定性评估：规则在不同样本集上的稳定性（由PSI单独评估）
    
    辅助指标（权重较低）：
    - 覆盖率检测：规则集总体命中样本比例
    - 重叠度检测：规则间命中样本重叠度（Jaccard相似度）
    - 冗余检测：规则A完全包含规则B
    - 复杂度评估：规则的可解释性
    
    评分体系（满分100分）：
    - 区分度得分：30分（核心）- 基于平均Lift和最小Lift
    - 召回率得分：25分（核心）- 基于累计坏客户召回率
    - 覆盖率得分：15分 - 整体覆盖率合理性
    - 独立性得分：15分 - 规则间重叠度和冗余度
    - 复杂度得分：15分 - 规则可解释性
    """
    
    # ========== 行业标准阈值配置 ==========
    # 区分度（Lift）阈值 - 信贷风控行业标准
    LIFT_EXCELLENT = 3.0      # 优秀：Lift >= 3
    LIFT_GOOD = 2.0           # 良好：Lift >= 2
    LIFT_ACCEPTABLE = 1.5     # 可接受：Lift >= 1.5
    LIFT_POOR = 1.0           # 差：Lift < 1.5
    
    # 召回率阈值 - 信贷风控行业标准
    RECALL_EXCELLENT = 0.30   # 优秀：召回率 >= 30%
    RECALL_GOOD = 0.20        # 良好：召回率 >= 20%
    RECALL_ACCEPTABLE = 0.10  # 可接受：召回率 >= 10%
    
    # 覆盖率阈值 - 规则覆盖总样本比例
    COVERAGE_MIN = 0.005      # 最小覆盖率 0.5%（避免过拟合）
    COVERAGE_MAX = 0.50       # 最大覆盖率 50%（避免规则过宽）
    COVERAGE_OPTIMAL_MIN = 0.01  # 最优覆盖率下限 1%
    COVERAGE_OPTIMAL_MAX = 0.30  # 最优覆盖率上限 30%
    
    # 重叠度阈值 - Jaccard相似度
    OVERLAP_WARNING = 0.50    # 重叠度警告阈值 50%
    OVERLAP_OPTIMAL = 0.30    # 最优重叠度上限 30%
    
    # 复杂度阈值 - 规则条件数
    COMPLEXITY_OPTIMAL = 3    # 最优条件数 <= 3
    COMPLEXITY_MAX = 5        # 最大条件数警告阈值
    
    # ========== 评分权重配置 ==========
    WEIGHT_DISCRIMINATION = 30  # 区分度权重
    WEIGHT_RECALL = 25          # 召回率权重
    WEIGHT_COVERAGE = 15        # 覆盖率权重
    WEIGHT_INDEPENDENCE = 15    # 独立性权重（重叠+冗余）
    WEIGHT_COMPLEXITY = 15      # 复杂度权重
    
    def __init__(
        self,
        min_coverage: float = 0.005,     # 最小覆盖率阈值
        max_coverage: float = 0.50,      # 最大覆盖率阈值
        max_conflict_rate: float = 0.30, # 最大冲突率阈值（放宽，规则重叠是正常的）
        max_overlap_rate: float = 0.50,  # 重叠度警告阈值
        min_lift: float = 1.5,           # 最小Lift阈值
        min_recall: float = 0.10         # 最小召回率阈值
    ):
        """
        初始化规则验证器
        
        Args:
            min_coverage: 最小覆盖率阈值，低于此值警告（默认0.5%）
            max_coverage: 最大覆盖率阈值，高于此值警告（默认50%）
            max_conflict_rate: 最大冲突率阈值（默认30%）
            max_overlap_rate: 重叠度警告阈值（默认50%）
            min_lift: 最小Lift阈值（默认1.5）
            min_recall: 最小召回率阈值（默认10%）
        """
        self.min_coverage = min_coverage
        self.max_coverage = max_coverage
        self.max_conflict_rate = max_conflict_rate
        self.max_overlap_rate = max_overlap_rate
        self.min_lift = min_lift
        self.min_recall = min_recall
    
    def validate(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame,
        target_col: str = 'target',
        weight_col: str | None = None
    ) -> dict[str, Any]:
        """
        执行完整规则质量验证（行业标准版）
        
        Args:
            rules_df: 规则DataFrame，需包含'rule'列，可选'lift', 'recall', 'hit_rate'等列
            df: 数据DataFrame
            target_col: 目标列名
            weight_col: 权重列名（可选）
            
        Returns:
            验证报告字典，包含：
            - discrimination_report: 区分度报告（核心）
            - recall_report: 召回率报告（核心）
            - coverage_report: 覆盖率报告
            - overlap_report: 重叠度报告
            - redundancy_report: 冗余检测报告
            - complexity_report: 复杂度报告
            - conflict_report: 冲突检测报告（兼容旧版）
            - warnings: 警告信息列表
            - quality_score: 综合质量分 (0-100)
            - score_breakdown: 各维度得分明细
        """
        if 'rule' not in rules_df.columns or len(rules_df) == 0:
            return {
                'discrimination_report': {'status': 'error', 'message': '规则集为空'},
                'recall_report': {'status': 'error', 'message': '规则集为空'},
                'coverage_report': {'status': 'error', 'message': '规则集为空'},
                'overlap_report': {'status': 'error', 'message': '规则集为空'},
                'redundancy_report': {'status': 'error', 'message': '规则集为空'},
                'complexity_report': {'status': 'error', 'message': '规则集为空'},
                'conflict_report': {'status': 'error', 'message': '规则集为空'},
                'warnings': ['规则集为空'],
                'quality_score': 0.0,
                'score_breakdown': {}
            }
        
        # 执行各项检测
        results: dict[str, Any] = {
            'discrimination_report': self._check_discrimination(rules_df, df, target_col),
            'recall_report': self._check_recall(rules_df, df, target_col),
            'coverage_report': self._check_coverage(rules_df, df, weight_col),
            'overlap_report': self._check_overlap(rules_df, df),
            'redundancy_report': self._check_redundancy(rules_df, df),
            'complexity_report': self._check_complexity(rules_df),
            'conflict_report': self._check_conflicts(rules_df, df),
            'warnings': [],
            'quality_score': 0.0,
            'score_breakdown': {}
        }
        
        # 汇总警告
        results['warnings'] = self._collect_warnings(results)
        
        # 计算综合质量分（加权评分）
        score_breakdown = self._calculate_score_breakdown(results)
        results['score_breakdown'] = score_breakdown
        results['quality_score'] = sum(score_breakdown.values())
        
        return results
    
    def _check_discrimination(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame,
        target_col: str
    ) -> dict[str, Any]:
        """
        检查规则区分度（核心指标）
        
        基于Lift评估规则区分好坏客户的能力
        行业标准：平均Lift >= 2为良好，>= 3为优秀
        """
        # 优先从rules_df获取已计算的lift
        if 'lift' in rules_df.columns:
            lift_values = rules_df['lift'].dropna().tolist()
        else:
            # 重新计算lift
            lift_values = self._calculate_lifts(rules_df, df, target_col)
        
        if not lift_values:
            return {
                'avg_lift': 0.0,
                'min_lift': 0.0,
                'max_lift': 0.0,
                'lift_distribution': {},
                'status': 'error',
                'message': '无法计算Lift'
            }
        
        avg_lift = float(np.mean(lift_values))
        min_lift = float(np.min(lift_values))
        max_lift = float(np.max(lift_values))
        
        # 分布统计
        excellent_count = sum(1 for l in lift_values if l >= self.LIFT_EXCELLENT)
        good_count = sum(1 for l in lift_values if self.LIFT_GOOD <= l < self.LIFT_EXCELLENT)
        acceptable_count = sum(1 for l in lift_values if self.LIFT_ACCEPTABLE <= l < self.LIFT_GOOD)
        poor_count = sum(1 for l in lift_values if l < self.LIFT_ACCEPTABLE)
        
        # 判断状态
        if avg_lift >= self.LIFT_EXCELLENT and min_lift >= self.LIFT_GOOD:
            status = 'excellent'
        elif avg_lift >= self.LIFT_GOOD and min_lift >= self.LIFT_ACCEPTABLE:
            status = 'good'
        elif avg_lift >= self.LIFT_ACCEPTABLE:
            status = 'acceptable'
        else:
            status = 'warning'
        
        return {
            'avg_lift': round(avg_lift, 2),
            'min_lift': round(min_lift, 2),
            'max_lift': round(max_lift, 2),
            'lift_distribution': {
                'excellent': excellent_count,  # Lift >= 3
                'good': good_count,            # 2 <= Lift < 3
                'acceptable': acceptable_count, # 1.5 <= Lift < 2
                'poor': poor_count             # Lift < 1.5
            },
            'status': status,
            'thresholds': {
                'excellent': self.LIFT_EXCELLENT,
                'good': self.LIFT_GOOD,
                'acceptable': self.LIFT_ACCEPTABLE
            }
        }
    
    def _calculate_lifts(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame,
        target_col: str
    ) -> list[float]:
        """计算各规则的Lift值"""
        if target_col not in df.columns:
            return []
        
        base_rate = df[target_col].mean()
        if base_rate == 0:
            return []
        
        lift_values: list[float] = []
        for rule in rules_df['rule'].tolist():
            try:
                hit_mask = _safe_eval_rule(df, rule, 'df')
                if hit_mask.sum() > 0:
                    rule_rate = df.loc[hit_mask, target_col].mean()
                    lift = rule_rate / base_rate
                    lift_values.append(lift)
            except Exception:
                pass
        
        return lift_values
    
    def _check_recall(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame,
        target_col: str
    ) -> dict[str, Any]:
        """
        检查召回率（核心指标）
        
        评估规则集对坏客户的捕获能力
        行业标准：累计召回率 >= 20%为良好，>= 30%为优秀
        """
        if target_col not in df.columns:
            return {
                'cumulative_recall': 0.0,
                'individual_recalls': [],
                'status': 'error',
                'message': f'目标列 {target_col} 不存在'
            }
        
        total_bad = df[target_col].sum()
        if total_bad == 0:
            return {
                'cumulative_recall': 0.0,
                'individual_recalls': [],
                'status': 'error',
                'message': '无坏客户样本'
            }
        
        # 优先从rules_df获取已计算的recall
        if 'recall' in rules_df.columns:
            individual_recalls = rules_df['recall'].dropna().tolist()
            # 计算累计召回（考虑规则重叠，使用实际命中计算）
            cumulative_recall = self._calculate_cumulative_recall(rules_df, df, target_col)
        else:
            # 重新计算
            individual_recalls = []
            total_hit_mask = pd.Series([False] * len(df), index=df.index)
            
            for rule in rules_df['rule'].tolist():
                try:
                    hit_mask = _safe_eval_rule(df, rule, 'df')
                    rule_recall = df.loc[hit_mask, target_col].sum() / total_bad
                    individual_recalls.append(float(rule_recall))
                    total_hit_mask = total_hit_mask | hit_mask
                except Exception:
                    pass
            
            cumulative_recall = df.loc[total_hit_mask, target_col].sum() / total_bad
        
        # 判断状态
        if cumulative_recall >= self.RECALL_EXCELLENT:
            status = 'excellent'
        elif cumulative_recall >= self.RECALL_GOOD:
            status = 'good'
        elif cumulative_recall >= self.RECALL_ACCEPTABLE:
            status = 'acceptable'
        else:
            status = 'warning'
        
        return {
            'cumulative_recall': round(float(cumulative_recall), 4),
            'individual_recalls': [round(r, 4) for r in individual_recalls[:10]],  # 只返回前10条
            'total_bad_samples': int(total_bad),
            'status': status,
            'thresholds': {
                'excellent': self.RECALL_EXCELLENT,
                'good': self.RECALL_GOOD,
                'acceptable': self.RECALL_ACCEPTABLE
            }
        }
    
    def _calculate_cumulative_recall(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame,
        target_col: str
    ) -> float:
        """计算累计召回率（考虑规则重叠）"""
        total_bad = df[target_col].sum()
        if total_bad == 0:
            return 0.0
        
        total_hit_mask = pd.Series([False] * len(df), index=df.index)
        for rule in rules_df['rule'].tolist():
            try:
                hit_mask = _safe_eval_rule(df, rule, 'df')
                total_hit_mask = total_hit_mask | hit_mask
            except Exception:
                pass
        
        return df.loc[total_hit_mask, target_col].sum() / total_bad
    
    def _check_complexity(self, rules_df: pd.DataFrame) -> dict[str, Any]:
        """
        检查规则复杂度
        
        评估规则的可解释性
        行业标准：单条规则条件数 <= 3为最优，<= 5为可接受
        """
        complexity_values: list[int] = []
        
        for rule in rules_df['rule'].tolist():
            # 计算规则中的条件数（通过统计 & 和 | 的数量 + 1）
            n_conditions = rule.count('&') + rule.count('|') + 1
            complexity_values.append(n_conditions)
        
        if not complexity_values:
            return {
                'avg_complexity': 0,
                'max_complexity': 0,
                'complexity_distribution': {},
                'status': 'error'
            }
        
        avg_complexity = np.mean(complexity_values)
        max_complexity = max(complexity_values)
        
        # 分布统计
        simple_count = sum(1 for c in complexity_values if c <= self.COMPLEXITY_OPTIMAL)
        moderate_count = sum(1 for c in complexity_values if self.COMPLEXITY_OPTIMAL < c <= self.COMPLEXITY_MAX)
        complex_count = sum(1 for c in complexity_values if c > self.COMPLEXITY_MAX)
        
        # 判断状态
        if avg_complexity <= self.COMPLEXITY_OPTIMAL and max_complexity <= self.COMPLEXITY_MAX:
            status = 'excellent'
        elif avg_complexity <= self.COMPLEXITY_MAX:
            status = 'good'
        else:
            status = 'warning'
        
        return {
            'avg_complexity': round(float(avg_complexity), 1),
            'max_complexity': int(max_complexity),
            'complexity_distribution': {
                'simple': simple_count,      # <= 3 条件
                'moderate': moderate_count,  # 4-5 条件
                'complex': complex_count     # > 5 条件
            },
            'status': status,
            'thresholds': {
                'optimal': self.COMPLEXITY_OPTIMAL,
                'max': self.COMPLEXITY_MAX
            }
        }
    
    def _check_coverage(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame,
        weight_col: str | None = None
    ) -> dict[str, Any]:
        """
        检查规则覆盖率
        
        评估规则集覆盖总样本的比例
        行业标准：覆盖率在1%-30%为最优，0.5%-50%为可接受
        """
        n_samples = len(df)
        if n_samples == 0:
            return {'total_coverage': 0.0, 'rule_coverages': [], 'status': 'error'}
        
        # 计算每条规则的覆盖率 - 使用向量化操作替代iterrows
        rule_coverages: list[dict[str, Any]] = []
        total_hit_mask = pd.Series([False] * n_samples, index=df.index)
        
        for rule in rules_df['rule'].tolist():
            try:
                # Use safe rule evaluation instead of eval()
                hit_mask = _safe_eval_rule(df, rule, 'df')
                coverage = hit_mask.sum() / n_samples
                rule_coverages.append({
                    'rule': rule,
                    'coverage': round(coverage, 4),
                    'hit_count': int(hit_mask.sum())
                })
                total_hit_mask = total_hit_mask | hit_mask
            except Exception:
                rule_coverages.append({
                    'rule': rule,
                    'coverage': 0.0,
                    'hit_count': 0,
                    'error': True
                })
        
        total_coverage = total_hit_mask.sum() / n_samples
        
        # 判断状态（使用新标准）
        if self.COVERAGE_OPTIMAL_MIN <= total_coverage <= self.COVERAGE_OPTIMAL_MAX:
            status = 'excellent'
        elif self.COVERAGE_MIN <= total_coverage <= self.COVERAGE_MAX:
            status = 'good'
        elif total_coverage < self.COVERAGE_MIN:
            status = 'warning_low'
        else:
            status = 'warning_high'
        
        return {
            'total_coverage': round(total_coverage, 4),
            'rule_coverages': rule_coverages,
            'status': status,
            'thresholds': {
                'min': self.min_coverage,
                'max': self.max_coverage,
                'optimal_min': self.COVERAGE_OPTIMAL_MIN,
                'optimal_max': self.COVERAGE_OPTIMAL_MAX
            }
        }
    
    def _check_conflicts(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame
    ) -> dict[str, Any]:
        """
        检查规则冲突
        
        冲突定义：多条规则同时命中同一样本（对于互斥规则场景）
        注意：在规则挖掘场景中，规则通常不是互斥的，此处检测的是高重叠情况
        """
        n_samples = len(df)
        if n_samples == 0 or len(rules_df) < 2:
            return {'conflict_rate': 0.0, 'conflicts': [], 'status': 'ok'}
        
        # 计算每个样本被多少条规则命中 - 使用向量化操作替代iterrows
        hit_counts = pd.Series([0] * n_samples, index=df.index)
        
        for rule in rules_df['rule'].tolist():
            try:
                # Use safe rule evaluation instead of eval()
                hit_mask = _safe_eval_rule(df, rule, 'df')
                hit_counts = hit_counts + hit_mask.astype(int)
            except Exception:
                pass
        
        # 被多条规则命中的样本比例
        multi_hit_rate = (hit_counts > 1).sum() / n_samples
        
        # 统计冲突分布
        conflict_distribution = hit_counts.value_counts().sort_index().to_dict()
        
        status = 'warning' if multi_hit_rate > self.max_conflict_rate else 'ok'
        
        return {
            'conflict_rate': round(multi_hit_rate, 4),
            'conflict_distribution': conflict_distribution,
            'status': status,
            'threshold': self.max_conflict_rate
        }
    
    def _check_overlap(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame
    ) -> dict[str, Any]:
        """
        检查规则重叠度
        
        使用Jaccard相似度衡量规则间的重叠程度
        """
        n_rules = len(rules_df)
        if n_rules < 2:
            return {'avg_overlap': 0.0, 'overlaps': [], 'status': 'ok'}
        
        # 计算每条规则的命中掩码 - 使用向量化操作替代iterrows
        hit_masks: list[tuple[str, pd.Series]] = []
        for rule in rules_df['rule'].tolist():
            try:
                # Use safe rule evaluation instead of eval()
                hit_mask = _safe_eval_rule(df, rule, 'df')
                hit_masks.append((rule, hit_mask))
            except Exception:
                pass
        
        # 计算两两规则间的Jaccard相似度
        overlaps: list[dict[str, Any]] = []
        jaccard_values: list[float] = []
        
        for i in range(len(hit_masks)):
            for j in range(i + 1, len(hit_masks)):
                rule1, mask1 = hit_masks[i]
                rule2, mask2 = hit_masks[j]
                
                intersection = (mask1 & mask2).sum()
                union = (mask1 | mask2).sum()
                
                if union > 0:
                    jaccard = intersection / union
                    jaccard_values.append(jaccard)
                    
                    if jaccard > self.max_overlap_rate:
                        overlaps.append({
                            'rule1': rule1[:50] + '...' if len(rule1) > 50 else rule1,
                            'rule2': rule2[:50] + '...' if len(rule2) > 50 else rule2,
                            'jaccard': round(jaccard, 4)
                        })
        
        avg_overlap = np.mean(jaccard_values) if jaccard_values else 0.0
        status = 'warning' if avg_overlap > self.max_overlap_rate else 'ok'
        
        return {
            'avg_overlap': round(float(avg_overlap), 4),
            'high_overlap_pairs': overlaps[:10],  # 只返回前10对高重叠规则
            'status': status,
            'threshold': self.max_overlap_rate
        }
    
    def _check_redundancy(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame
    ) -> dict[str, Any]:
        """
        检查规则冗余
        
        冗余定义：规则A的命中样本完全包含规则B的命中样本
        """
        n_rules = len(rules_df)
        if n_rules < 2:
            return {'redundant_rules': [], 'status': 'ok'}
        
        # 计算每条规则的命中掩码 - 使用向量化操作替代iterrows
        hit_masks: list[tuple[str, pd.Series]] = []
        for rule in rules_df['rule'].tolist():
            try:
                # Use safe rule evaluation instead of eval()
                hit_mask = _safe_eval_rule(df, rule, 'df')
                hit_masks.append((rule, hit_mask))
            except Exception:
                pass
        
        # 检查包含关系
        redundant_rules: list[dict[str, str]] = []
        
        for i in range(len(hit_masks)):
            for j in range(len(hit_masks)):
                if i == j:
                    continue
                    
                rule1, mask1 = hit_masks[i]
                rule2, mask2 = hit_masks[j]
                
                # 检查mask2是否完全被mask1包含
                if mask2.sum() > 0 and (mask1 & mask2).sum() == mask2.sum():
                    redundant_rules.append({
                        'containing_rule': rule1[:50] + '...' if len(rule1) > 50 else rule1,
                        'redundant_rule': rule2[:50] + '...' if len(rule2) > 50 else rule2
                    })
        
        status = 'warning' if len(redundant_rules) > 0 else 'ok'
        
        return {
            'redundant_rules': redundant_rules[:10],  # 只返回前10对
            'redundant_count': len(redundant_rules),
            'status': status
        }
    
    def _collect_warnings(self, results: dict[str, Any]) -> list[str]:
        """汇总所有警告信息（行业标准版）"""
        warnings: list[str] = []
        
        # 区分度警告（核心指标）
        discrimination = results.get('discrimination_report', {})
        if discrimination.get('status') == 'warning':
            avg_lift = discrimination.get('avg_lift', 0)
            min_lift = discrimination.get('min_lift', 0)
            warnings.append(f"规则区分度不足（平均Lift={avg_lift:.1f}，最小Lift={min_lift:.1f}），建议提高Lift阈值或优化规则")
        
        # 召回率警告（核心指标）
        recall = results.get('recall_report', {})
        if recall.get('status') == 'warning':
            cumulative_recall = recall.get('cumulative_recall', 0)
            warnings.append(f"坏客户召回率偏低（{cumulative_recall:.1%}），建议增加规则数量或放宽规则条件")
        
        # 覆盖率警告
        coverage = results.get('coverage_report', {})
        if coverage.get('status') == 'warning_low':
            warnings.append(f"规则覆盖率过低 ({coverage.get('total_coverage', 0):.1%})，可能存在过拟合风险")
        elif coverage.get('status') == 'warning_high':
            warnings.append(f"规则覆盖率过高 ({coverage.get('total_coverage', 0):.1%})，规则可能过于宽泛")
        
        # 重叠警告
        overlap = results.get('overlap_report', {})
        if overlap.get('status') == 'warning':
            warnings.append(f"规则平均重叠度较高 ({overlap.get('avg_overlap', 0):.1%})，建议合并相似规则")
        
        # 冗余警告
        redundancy = results.get('redundancy_report', {})
        if redundancy.get('status') == 'warning':
            warnings.append(f"存在 {redundancy.get('redundant_count', 0)} 对冗余规则，建议删除被包含的规则")
        
        # 复杂度警告
        complexity = results.get('complexity_report', {})
        if complexity.get('status') == 'warning':
            warnings.append(f"规则复杂度较高（平均{complexity.get('avg_complexity', 0):.1f}个条件），可能影响可解释性")
        
        # 冲突警告（兼容旧版，但不作为主要指标）
        conflict = results.get('conflict_report', {})
        if conflict.get('status') == 'warning':
            warnings.append(f"规则重叠率较高 ({conflict.get('conflict_rate', 0):.1%})，多条规则命中相同样本")
        
        return warnings
    
    def _calculate_score_breakdown(self, results: dict[str, Any]) -> dict[str, float]:
        """
        计算各维度得分明细（加权评分体系）
        
        评分体系（满分100分）：
        - 区分度得分：30分（核心）
        - 召回率得分：25分（核心）
        - 覆盖率得分：15分
        - 独立性得分：15分（重叠+冗余）
        - 复杂度得分：15分
        """
        scores: dict[str, float] = {}
        
        # ========== 区分度得分 (30分) ==========
        discrimination = results.get('discrimination_report', {})
        disc_status = discrimination.get('status', 'error')
        avg_lift = discrimination.get('avg_lift', 0)
        
        if disc_status == 'excellent':
            disc_score = self.WEIGHT_DISCRIMINATION  # 30分
        elif disc_status == 'good':
            disc_score = self.WEIGHT_DISCRIMINATION * 0.85  # 25.5分
        elif disc_status == 'acceptable':
            disc_score = self.WEIGHT_DISCRIMINATION * 0.70  # 21分
        elif disc_status == 'warning':
            # 根据Lift值线性递减
            if avg_lift >= 1.0:
                disc_score = self.WEIGHT_DISCRIMINATION * 0.50 * (avg_lift / self.LIFT_ACCEPTABLE)
            else:
                disc_score = self.WEIGHT_DISCRIMINATION * 0.20
        else:
            disc_score = 0
        
        scores['discrimination'] = round(disc_score, 1)
        
        # ========== 召回率得分 (25分) ==========
        recall = results.get('recall_report', {})
        recall_status = recall.get('status', 'error')
        cumulative_recall = recall.get('cumulative_recall', 0)
        
        if recall_status == 'excellent':
            recall_score = self.WEIGHT_RECALL  # 25分
        elif recall_status == 'good':
            recall_score = self.WEIGHT_RECALL * 0.85  # 21.25分
        elif recall_status == 'acceptable':
            recall_score = self.WEIGHT_RECALL * 0.70  # 17.5分
        elif recall_status == 'warning':
            # 根据召回率线性递减
            recall_score = self.WEIGHT_RECALL * 0.50 * (cumulative_recall / self.RECALL_ACCEPTABLE) if cumulative_recall > 0 else 0
        else:
            recall_score = 0
        
        scores['recall'] = round(recall_score, 1)
        
        # ========== 覆盖率得分 (15分) ==========
        coverage = results.get('coverage_report', {})
        cov_status = coverage.get('status', 'error')
        
        if cov_status == 'excellent':
            cov_score = self.WEIGHT_COVERAGE  # 15分
        elif cov_status == 'good':
            cov_score = self.WEIGHT_COVERAGE * 0.85  # 12.75分
        elif cov_status == 'warning_low':
            cov_score = self.WEIGHT_COVERAGE * 0.50  # 7.5分
        elif cov_status == 'warning_high':
            cov_score = self.WEIGHT_COVERAGE * 0.60  # 9分
        else:
            cov_score = 0
        
        scores['coverage'] = round(cov_score, 1)
        
        # ========== 独立性得分 (15分) ==========
        # 重叠度和冗余度各占一半
        overlap = results.get('overlap_report', {})
        redundancy = results.get('redundancy_report', {})
        
        # 重叠度得分 (7.5分)
        overlap_status = overlap.get('status', 'ok')
        avg_overlap = overlap.get('avg_overlap', 0)
        if overlap_status == 'ok':
            if avg_overlap <= self.OVERLAP_OPTIMAL:
                overlap_score = 7.5
            else:
                overlap_score = 7.5 * (1 - (avg_overlap - self.OVERLAP_OPTIMAL) / (self.OVERLAP_WARNING - self.OVERLAP_OPTIMAL))
        else:
            # warning状态，根据重叠度递减
            overlap_score = max(0, 7.5 * 0.5 * (1 - avg_overlap))
        
        # 冗余度得分 (7.5分)
        redundancy_status = redundancy.get('status', 'ok')
        redundant_count = redundancy.get('redundant_count', 0)
        if redundancy_status == 'ok':
            redundancy_score = 7.5
        else:
            # 每对冗余扣0.5分，最多扣7.5分
            redundancy_score = max(0, 7.5 - redundant_count * 0.5)
        
        scores['independence'] = round(overlap_score + redundancy_score, 1)
        
        # ========== 复杂度得分 (15分) ==========
        complexity = results.get('complexity_report', {})
        comp_status = complexity.get('status', 'error')
        
        if comp_status == 'excellent':
            comp_score = self.WEIGHT_COMPLEXITY  # 15分
        elif comp_status == 'good':
            comp_score = self.WEIGHT_COMPLEXITY * 0.80  # 12分
        elif comp_status == 'warning':
            avg_complexity = complexity.get('avg_complexity', 5)
            # 根据复杂度递减
            comp_score = max(0, self.WEIGHT_COMPLEXITY * 0.50 * (self.COMPLEXITY_MAX / avg_complexity))
        else:
            comp_score = 0
        
        scores['complexity'] = round(comp_score, 1)
        
        return scores
    
    def _calculate_quality_score(self, results: dict[str, Any]) -> float:
        """计算综合质量分 (0-100) - 旧版兼容方法"""
        # 使用新的加权评分体系
        score_breakdown = self._calculate_score_breakdown(results)
        return round(sum(score_breakdown.values()), 1)


class ScorecardValidator:
    """
    评分卡质量验证器
    
    评估评分卡模型的质量，包括：
    - 得分分布：得分唯一值数量、范围、标准差
    - 区分度：KS值、AUC等
    - 稳定性：PSI（需外部计算）
    
    评分体系（满分100分）：
    - 区分度得分：40分 - 基于KS值和AUC
    - 得分分布得分：30分 - 得分范围、唯一值、标准差
    - 稳定性得分：30分 - 基于PSI（如有）
    """
    
    # ========== 行业标准阈值配置 ==========
    # KS值阈值 - 信贷风控行业标准
    KS_EXCELLENT = 0.40       # 优秀：KS >= 40%
    KS_GOOD = 0.30            # 良好：KS >= 30%
    KS_ACCEPTABLE = 0.20      # 可接受：KS >= 20%
    
    # AUC阈值
    AUC_EXCELLENT = 0.80      # 优秀：AUC >= 0.80
    AUC_GOOD = 0.70           # 良好：AUC >= 0.70
    AUC_ACCEPTABLE = 0.60     # 可接受：AUC >= 0.60
    
    # 得分分布阈值
    UNIQUE_SCORES_MIN = 20     # 最少唯一得分数
    SCORE_RANGE_MIN = 50       # 最小得分范围
    SCORE_STD_MIN = 10         # 最小标准差
    
    # PSI阈值
    PSI_EXCELLENT = 0.10       # 优秀：PSI < 0.10
    PSI_ACCEPTABLE = 0.25      # 可接受：PSI < 0.25
    
    # ========== 评分权重配置 ==========
    WEIGHT_DISCRIMINATION = 40  # 区分度权重
    WEIGHT_DISTRIBUTION = 30    # 得分分布权重
    WEIGHT_STABILITY = 30       # 稳定性权重
    
    def __init__(
        self,
        min_unique_scores: int = 20,
        min_score_range: float = 50,
        min_score_std: float = 10
    ):
        """
        初始化评分卡验证器
        
        Args:
            min_unique_scores: 最少唯一得分数阈值
            min_score_range: 最小得分范围阈值
            min_score_std: 最小标准差阈值
        """
        self.min_unique_scores = min_unique_scores
        self.min_score_range = min_score_range
        self.min_score_std = min_score_std
    
    def validate(
        self,
        scores: np.ndarray,
        y_true: np.ndarray | None = None,
        y_pred_proba: np.ndarray | None = None,
        psi_value: float | None = None
    ) -> dict[str, Any]:
        """
        执行完整评分卡质量验证
        
        Args:
            scores: 评分卡得分数组
            y_true: 真实标签（用于计算KS/AUC）
            y_pred_proba: 预测概率（用于计算KS/AUC）
            psi_value: PSI值（外部计算传入）
            
        Returns:
            验证报告字典
        """
        results: dict[str, Any] = {
            'distribution_report': self._check_distribution(scores),
            'discrimination_report': {},
            'stability_report': {},
            'warnings': [],
            'quality_score': 0.0,
            'score_breakdown': {},
            'status': 'ok'
        }
        
        # 区分度检测（需要真实标签）
        if y_true is not None and y_pred_proba is not None:
            results['discrimination_report'] = self._check_discrimination(y_true, y_pred_proba)
        
        # 稳定性检测（需要PSI值）
        if psi_value is not None:
            results['stability_report'] = self._check_stability(psi_value)
        
        # 汇总警告
        results['warnings'] = self._collect_warnings(results)
        
        # 计算综合质量分
        score_breakdown = self._calculate_score_breakdown(results)
        results['score_breakdown'] = score_breakdown
        results['quality_score'] = sum(score_breakdown.values())
        
        # 设置整体状态
        if results['quality_score'] >= 80:
            results['status'] = 'excellent'
        elif results['quality_score'] >= 60:
            results['status'] = 'good'
        elif results['quality_score'] >= 40:
            results['status'] = 'acceptable'
        else:
            results['status'] = 'warning'
        
        return results
    
    def validate_simple(self, scores: np.ndarray) -> dict[str, Any]:
        """
        简单验证（仅检查得分分布，兼容旧版接口）
        
        Args:
            scores: 评分卡得分数组
            
        Returns:
            验证结果字典
        """
        import logging
        logger = logging.getLogger(__name__)
        
        validation: dict[str, Any] = {
            'unique_scores': int(len(np.unique(scores))),
            'score_min': float(np.min(scores)),
            'score_max': float(np.max(scores)),
            'score_range': float(np.max(scores) - np.min(scores)),
            'score_std': float(np.std(scores)),
            'score_mean': float(np.mean(scores)),
            'warnings': [],
            'status': 'ok'
        }
        
        # Warning: too few unique scores
        if validation['unique_scores'] < self.min_unique_scores:
            validation['warnings'].append(
                f"得分唯一值仅{validation['unique_scores']}个，区分度可能不足"
            )
            validation['status'] = 'warning'
        
        # Warning: score range too narrow
        if validation['score_range'] < self.min_score_range:
            validation['warnings'].append(
                f"得分范围仅{validation['score_range']:.1f}分，建议增大PDO参数"
            )
            validation['status'] = 'warning'
        
        # Warning: score std too small
        if validation['score_std'] < self.min_score_std:
            validation['warnings'].append(
                f"得分标准差仅{validation['score_std']:.2f}，样本区分度较低"
            )
            validation['status'] = 'warning'
        
        # Log validation results
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"Scorecard validation: {warning}")
        else:
            logger.info(f"Scorecard validation passed: range={validation['score_range']:.1f}, unique={validation['unique_scores']}")
        
        return validation
    
    def _check_distribution(self, scores: np.ndarray) -> dict[str, Any]:
        """检查得分分布"""
        unique_scores = int(len(np.unique(scores)))
        score_min = float(np.min(scores))
        score_max = float(np.max(scores))
        score_range = score_max - score_min
        score_std = float(np.std(scores))
        score_mean = float(np.mean(scores))
        
        # 判断状态
        issues = 0
        if unique_scores < self.UNIQUE_SCORES_MIN:
            issues += 1
        if score_range < self.SCORE_RANGE_MIN:
            issues += 1
        if score_std < self.SCORE_STD_MIN:
            issues += 1
        
        if issues == 0:
            status = 'excellent'
        elif issues == 1:
            status = 'good'
        elif issues == 2:
            status = 'acceptable'
        else:
            status = 'warning'
        
        return {
            'unique_scores': unique_scores,
            'score_min': round(score_min, 2),
            'score_max': round(score_max, 2),
            'score_range': round(score_range, 2),
            'score_std': round(score_std, 2),
            'score_mean': round(score_mean, 2),
            'status': status,
            'thresholds': {
                'min_unique_scores': self.UNIQUE_SCORES_MIN,
                'min_score_range': self.SCORE_RANGE_MIN,
                'min_score_std': self.SCORE_STD_MIN
            }
        }
    
    def _check_discrimination(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray
    ) -> dict[str, Any]:
        """检查区分度（KS/AUC）"""
        try:
            from sklearn.metrics import roc_auc_score, roc_curve
            
            # 计算AUC
            auc = roc_auc_score(y_true, y_pred_proba)
            
            # 计算KS
            fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
            ks = float(max(tpr - fpr))
            
            # 判断状态
            if ks >= self.KS_EXCELLENT and auc >= self.AUC_EXCELLENT:
                status = 'excellent'
            elif ks >= self.KS_GOOD and auc >= self.AUC_GOOD:
                status = 'good'
            elif ks >= self.KS_ACCEPTABLE and auc >= self.AUC_ACCEPTABLE:
                status = 'acceptable'
            else:
                status = 'warning'
            
            return {
                'ks': round(ks, 4),
                'auc': round(float(auc), 4),
                'status': status,
                'thresholds': {
                    'ks_excellent': self.KS_EXCELLENT,
                    'ks_good': self.KS_GOOD,
                    'ks_acceptable': self.KS_ACCEPTABLE,
                    'auc_excellent': self.AUC_EXCELLENT,
                    'auc_good': self.AUC_GOOD,
                    'auc_acceptable': self.AUC_ACCEPTABLE
                }
            }
        except Exception as e:
            return {
                'ks': 0.0,
                'auc': 0.0,
                'status': 'error',
                'message': str(e)
            }
    
    def _check_stability(self, psi_value: float) -> dict[str, Any]:
        """检查稳定性（PSI）"""
        if psi_value < self.PSI_EXCELLENT:
            status = 'excellent'
        elif psi_value < self.PSI_ACCEPTABLE:
            status = 'good'
        else:
            status = 'warning'
        
        return {
            'psi': round(psi_value, 4),
            'status': status,
            'thresholds': {
                'excellent': self.PSI_EXCELLENT,
                'acceptable': self.PSI_ACCEPTABLE
            }
        }
    
    def _collect_warnings(self, results: dict[str, Any]) -> list[str]:
        """汇总警告信息"""
        warnings: list[str] = []
        
        # 得分分布警告
        distribution = results.get('distribution_report', {})
        if distribution.get('status') == 'warning':
            if distribution.get('unique_scores', 0) < self.UNIQUE_SCORES_MIN:
                warnings.append(f"得分唯一值仅{distribution.get('unique_scores')}个，区分度可能不足")
            if distribution.get('score_range', 0) < self.SCORE_RANGE_MIN:
                warnings.append(f"得分范围仅{distribution.get('score_range'):.1f}分，建议增大PDO参数")
            if distribution.get('score_std', 0) < self.SCORE_STD_MIN:
                warnings.append(f"得分标准差仅{distribution.get('score_std'):.2f}，样本区分度较低")
        
        # 区分度警告
        discrimination = results.get('discrimination_report', {})
        if discrimination.get('status') == 'warning':
            ks = discrimination.get('ks', 0)
            auc = discrimination.get('auc', 0)
            warnings.append(f"模型区分度不足（KS={ks:.2%}，AUC={auc:.3f}），建议优化特征或模型")
        
        # 稳定性警告
        stability = results.get('stability_report', {})
        if stability.get('status') == 'warning':
            psi = stability.get('psi', 0)
            warnings.append(f"模型稳定性不足（PSI={psi:.3f}），建议检查数据分布变化")
        
        return warnings
    
    def _calculate_score_breakdown(self, results: dict[str, Any]) -> dict[str, float]:
        """计算各维度得分明细"""
        scores: dict[str, float] = {}
        
        # ========== 区分度得分 (40分) ==========
        discrimination = results.get('discrimination_report', {})
        disc_status = discrimination.get('status', 'error')
        
        if disc_status == 'excellent':
            disc_score = self.WEIGHT_DISCRIMINATION
        elif disc_status == 'good':
            disc_score = self.WEIGHT_DISCRIMINATION * 0.80
        elif disc_status == 'acceptable':
            disc_score = self.WEIGHT_DISCRIMINATION * 0.60
        elif disc_status == 'warning':
            disc_score = self.WEIGHT_DISCRIMINATION * 0.30
        else:
            # 无数据时给基础分
            disc_score = self.WEIGHT_DISCRIMINATION * 0.50
        
        scores['discrimination'] = round(disc_score, 1)
        
        # ========== 得分分布得分 (30分) ==========
        distribution = results.get('distribution_report', {})
        dist_status = distribution.get('status', 'error')
        
        if dist_status == 'excellent':
            dist_score = self.WEIGHT_DISTRIBUTION
        elif dist_status == 'good':
            dist_score = self.WEIGHT_DISTRIBUTION * 0.80
        elif dist_status == 'acceptable':
            dist_score = self.WEIGHT_DISTRIBUTION * 0.60
        elif dist_status == 'warning':
            dist_score = self.WEIGHT_DISTRIBUTION * 0.30
        else:
            dist_score = 0
        
        scores['distribution'] = round(dist_score, 1)
        
        # ========== 稳定性得分 (30分) ==========
        stability = results.get('stability_report', {})
        stab_status = stability.get('status', '')
        
        if stab_status == 'excellent':
            stab_score = self.WEIGHT_STABILITY
        elif stab_status == 'good':
            stab_score = self.WEIGHT_STABILITY * 0.80
        elif stab_status == 'warning':
            stab_score = self.WEIGHT_STABILITY * 0.40
        else:
            # 无PSI数据时给基础分
            stab_score = self.WEIGHT_STABILITY * 0.50
        
        scores['stability'] = round(stab_score, 1)
        
        return scores
