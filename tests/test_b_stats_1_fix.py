"""
B-STATS-1 修复验证测试

测试目标：
1. class_weight='balanced' 时，加权似然计算使 pseudo_r2 > 0、lr_pvalue < 0.05
2. 无 class_weight 时行为不变（向后兼容）
3. _compute_effective_weights 正确合并 class_weight 和 sample_weight
4. summary() 中包含 class_weight_applied 标记

Bug 描述：
  使用 class_weight='balanced' 时，_calculate_model_fit_stats 用无加权似然公式，
  但 predict_proba 来自加权训练的模型，导致 log_likelihood < null_log_likelihood，
  伪R² 为负（如 -204%），似然比 p=1.0。

运行方式：
    cd workspace/DeepAnalyze
    python -m pytest tests/test_b_stats_1_fix.py -v -s
"""

import numpy as np
import pandas as pd
import pytest
import sys
import warnings
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

warnings.filterwarnings("ignore")


def make_imbalanced_data(n=5000, bad_rate=0.05, seed=42):
    """构造不平衡二分类数据（模拟真实评分卡场景）"""
    rng = np.random.RandomState(seed)
    n_bad = int(n * bad_rate)
    n_good = n - n_bad

    # 好客户特征
    good_f1 = rng.normal(0.3, 0.2, n_good)
    good_f2 = rng.normal(0.2, 0.15, n_good)
    good_f3 = rng.normal(0.1, 0.1, n_good)

    # 坏客户特征（WOE值更高）
    bad_f1 = rng.normal(0.8, 0.3, n_bad)
    bad_f2 = rng.normal(0.6, 0.2, n_bad)
    bad_f3 = rng.normal(0.4, 0.15, n_bad)

    df = pd.DataFrame({
        'f1_woe': np.concatenate([good_f1, bad_f1]),
        'f2_woe': np.concatenate([good_f2, bad_f2]),
        'f3_woe': np.concatenate([good_f3, bad_f3]),
        'target': np.concatenate([np.zeros(n_good), np.ones(n_bad)])
    })
    # 打乱顺序
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


# ============================================================
# T1: class_weight='balanced' 时统计量正确
# ============================================================

class TestWeightedStatistics:
    """验证 class_weight='balanced' 时加权似然统计量正确"""

    def test_pseudo_r2_positive_with_balanced(self):
        """T1: class_weight='balanced' 时 pseudo_r2 应为正值（修复前为负）"""
        from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression

        df = make_imbalanced_data(n=5000, bad_rate=0.05)
        X = df[['f1_woe', 'f2_woe', 'f3_woe']]
        y = df['target']

        model = StatisticalLogisticRegression(
            calculate_stats=True,
            penalty=None, C=1e10,
            solver='lbfgs', max_iter=1000,
            fit_intercept=True,
            class_weight='balanced'
        )
        model.fit(X, y)
        stats = model.summary()

        pseudo_r2 = stats['pseudo_r2']
        lr_pvalue = stats['lr_pvalue']
        log_ll = stats['log_likelihood']
        null_ll = stats['null_log_likelihood']

        print(f"\n  [balanced] pseudo_r2={pseudo_r2:.4f}, lr_pvalue={lr_pvalue}, "
              f"log_ll={log_ll:.2f}, null_ll={null_ll:.2f}")

        # 核心断言：修复后 pseudo_r2 应为正值
        assert pseudo_r2 > 0, f"pseudo_r2 should be > 0 with balanced class_weight, got {pseudo_r2}"

        # 核心断言：修复后 lr_pvalue 应远小于 0.05
        assert lr_pvalue is not None and lr_pvalue < 0.05, \
            f"lr_pvalue should be < 0.05 with significant features, got {lr_pvalue}"

        # log_likelihood 应大于 null_log_likelihood（模型比零模型好）
        assert log_ll > null_ll, \
            f"log_likelihood ({log_ll}) should be > null_log_likelihood ({null_ll})"

        # class_weight_applied 应为 True
        assert stats.get('class_weight_applied') is True, \
            f"class_weight_applied should be True, got {stats.get('class_weight_applied')}"

        print(f"  ✅ PASS — pseudo_r2={pseudo_r2:.4f}, lr_pvalue={lr_pvalue:.6f}")

    def test_features_still_significant_with_balanced(self):
        """T2: class_weight='balanced' 时特征 p 值应与无加权时一致性（都显著）"""
        from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression

        df = make_imbalanced_data(n=5000, bad_rate=0.05)
        X = df[['f1_woe', 'f2_woe', 'f3_woe']]
        y = df['target']

        model = StatisticalLogisticRegression(
            calculate_stats=True,
            penalty=None, C=1e10,
            solver='lbfgs', max_iter=1000,
            fit_intercept=True,
            class_weight='balanced'
        )
        model.fit(X, y)
        stats = model.summary()

        # 检查各特征p值
        for feat_info in stats['summary']:
            feat = feat_info['feature']
            if feat == 'const':
                continue
            pval = feat_info['p_value']
            coef = feat_info['coef']
            print(f"  {feat}: coef={coef:.4f}, p_value={pval:.6f}")
            # WOE特征应显著（p < 0.05）且系数为正
            assert pval < 0.05, f"{feat} should be significant, got p={pval}"
            assert coef > 0, f"{feat} should have positive coefficient, got {coef}"

        print("  ✅ PASS — all features significant with positive coefficients")


# ============================================================
# T3: 向后兼容（无 class_weight 时行为不变）
# ============================================================

class TestBackwardCompatibility:
    """验证无 class_weight 时统计量计算不变"""

    def test_no_class_weight_unchanged(self):
        """T3: 无 class_weight 时结果与修复前完全一致"""
        from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression

        df = make_imbalanced_data(n=3000, bad_rate=0.10)
        X = df[['f1_woe', 'f2_woe', 'f3_woe']]
        y = df['target']

        model = StatisticalLogisticRegression(
            calculate_stats=True,
            penalty=None, C=1e10,
            solver='lbfgs', max_iter=1000,
            fit_intercept=True,
            class_weight=None  # 无加权
        )
        model.fit(X, y)
        stats = model.summary()

        pseudo_r2 = stats['pseudo_r2']
        lr_pvalue = stats['lr_pvalue']

        print(f"\n  [no weight] pseudo_r2={pseudo_r2:.4f}, lr_pvalue={lr_pvalue}")

        # 无加权时也应该正常
        assert pseudo_r2 > 0, f"pseudo_r2 should be > 0, got {pseudo_r2}"
        assert lr_pvalue is not None and lr_pvalue < 0.05, f"lr_pvalue should be < 0.05, got {lr_pvalue}"

        # class_weight_applied 应为 False
        assert stats.get('class_weight_applied') is False, \
            f"class_weight_applied should be False when no class_weight, got {stats.get('class_weight_applied')}"

        print(f"  ✅ PASS — backward compatible, pseudo_r2={pseudo_r2:.4f}")

    def test_balanced_vs_unweighted_comparison(self):
        """T4: balanced 和 unweighted 的统计量应该都合理（但数值可能不同）"""
        from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression

        df = make_imbalanced_data(n=5000, bad_rate=0.05)
        X = df[['f1_woe', 'f2_woe', 'f3_woe']]
        y = df['target']

        # 无加权模型
        model_uw = StatisticalLogisticRegression(
            calculate_stats=True, penalty=None, C=1e10,
            solver='lbfgs', max_iter=1000, fit_intercept=True,
            class_weight=None
        )
        model_uw.fit(X, y)
        stats_uw = model_uw.summary()

        # 加权模型
        model_bw = StatisticalLogisticRegression(
            calculate_stats=True, penalty=None, C=1e10,
            solver='lbfgs', max_iter=1000, fit_intercept=True,
            class_weight='balanced'
        )
        model_bw.fit(X, y)
        stats_bw = model_bw.summary()

        print(f"\n  [unweighted] pseudo_r2={stats_uw['pseudo_r2']:.4f}, "
              f"lr_pvalue={stats_uw['lr_pvalue']}")
        print(f"  [balanced]   pseudo_r2={stats_bw['pseudo_r2']:.4f}, "
              f"lr_pvalue={stats_bw['lr_pvalue']}")

        # 两者都应为正且显著
        assert stats_uw['pseudo_r2'] > 0
        assert stats_bw['pseudo_r2'] > 0
        assert stats_uw['lr_pvalue'] < 0.05
        assert stats_bw['lr_pvalue'] < 0.05

        # 两者的 class_weight_applied 应不同
        assert stats_uw['class_weight_applied'] is False
        assert stats_bw['class_weight_applied'] is True

        print("  ✅ PASS — both models show reasonable statistics")


# ============================================================
# T5: _compute_effective_weights 正确性
# ============================================================

class TestComputeEffectiveWeights:
    """验证 _compute_effective_weights 方法"""

    def test_no_weight_returns_none(self):
        """T5a: 无 class_weight 且无 sample_weight 时返回 None"""
        from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression

        model = StatisticalLogisticRegression(class_weight=None)
        y = np.array([0, 0, 0, 1, 1])
        result = model._compute_effective_weights(y, sample_weight=None)
        assert result is None, f"Expected None, got {result}"
        print("\n  ✅ T5a: no weight → None")

    def test_class_weight_balanced(self):
        """T5b: class_weight='balanced' 返回正确的样本权重"""
        from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression

        model = StatisticalLogisticRegression(class_weight='balanced')
        y = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 1])  # 80% good, 20% bad
        weights = model._compute_effective_weights(y, sample_weight=None)

        assert weights is not None
        assert len(weights) == 10

        # balanced 权重：w_class = n_samples / (n_classes * n_class_samples)
        # w_0 = 10 / (2 * 8) = 0.625
        # w_1 = 10 / (2 * 2) = 2.5
        expected_w0 = 10 / (2 * 8)
        expected_w1 = 10 / (2 * 2)

        for i, yi in enumerate(y):
            expected = expected_w1 if yi == 1 else expected_w0
            assert abs(weights[i] - expected) < 1e-6, \
                f"Weight at index {i} (y={yi}): expected {expected}, got {weights[i]}"

        print(f"\n  ✅ T5b: balanced weights correct (w0={expected_w0:.4f}, w1={expected_w1:.4f})")

    def test_combined_weights(self):
        """T5c: class_weight + sample_weight 正确叠加"""
        from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression

        model = StatisticalLogisticRegression(class_weight='balanced')
        y = np.array([0, 0, 1, 1])
        sample_weight = np.array([2.0, 1.0, 1.0, 3.0])

        weights = model._compute_effective_weights(y, sample_weight=sample_weight)

        # balanced: w_0 = 4/(2*2) = 1.0, w_1 = 4/(2*2) = 1.0
        # combined = class_weight * sample_weight
        assert weights is not None
        np.testing.assert_array_almost_equal(
            weights,
            np.array([1.0 * 2.0, 1.0 * 1.0, 1.0 * 1.0, 1.0 * 3.0])
        )
        print(f"\n  ✅ T5c: combined weights = {weights}")


# ============================================================
# T6: 极端不平衡场景
# ============================================================

class TestExtremeImbalance:
    """验证极端不平衡数据（bad_rate=1%）下统计量仍合理"""

    def test_extreme_imbalance_1pct(self):
        """T6: bad_rate=1% 时 class_weight='balanced' 统计量正确"""
        from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression

        df = make_imbalanced_data(n=10000, bad_rate=0.01)
        X = df[['f1_woe', 'f2_woe', 'f3_woe']]
        y = df['target']

        model = StatisticalLogisticRegression(
            calculate_stats=True,
            penalty=None, C=1e10,
            solver='lbfgs', max_iter=1000,
            fit_intercept=True,
            class_weight='balanced'
        )
        model.fit(X, y)
        stats = model.summary()

        pseudo_r2 = stats['pseudo_r2']
        lr_pvalue = stats['lr_pvalue']

        print(f"\n  [1% bad_rate, balanced] pseudo_r2={pseudo_r2:.4f}, lr_pvalue={lr_pvalue}")

        # 即使极端不平衡，加权后统计量也应合理
        assert pseudo_r2 > 0, f"pseudo_r2 should be > 0 even at 1% bad_rate, got {pseudo_r2}"
        assert lr_pvalue is not None and lr_pvalue < 0.05, \
            f"lr_pvalue should be < 0.05, got {lr_pvalue}"

        print(f"  ✅ PASS — extreme imbalance handled correctly")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
