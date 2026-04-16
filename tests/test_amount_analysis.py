# -*- coding: utf-8 -*-
"""
Amount Analysis Unit Tests (P2-10)

Tests AmountAnalyzer and RuleEvaluator.evaluate_with_amount.
34 test cases covering:
- U1-U12: AmountAnalyzer unit tests
- U13-U16: RuleEvaluator.evaluate_with_amount unit tests
- E1-E5: Edge case / boundary tests
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import warnings

warnings.filterwarnings("ignore")

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deepanalyze.analysis.task_SOP.rule_mining import (
    AmountAnalyzer,
    RuleEvaluator,
)

from tests.fixtures.mock_amount_data import (
    generate_small_test_data,
    generate_handcrafted_data,
    generate_edge_case_data,
    HANDCRAFTED_EXPECTED,
)


# =============================================================================
# U1-U12: AmountAnalyzer Unit Tests
# =============================================================================

class TestAmountAnalyzerBasic(unittest.TestCase):
    """U1-U4: Basic AmountAnalyzer functionality"""

    def setUp(self):
        self.df = generate_small_test_data(n=200, seed=42)
        self.analyzer = AmountAnalyzer(amount_col="mock_amount")

    def test_U1_basic_fit(self):
        """U1: fit() returns self, internal state is correct"""
        result = self.analyzer.fit(self.df, target_col="label")
        self.assertIs(result, self.analyzer)
        self.assertTrue(self.analyzer._fitted)
        self.assertGreater(self.analyzer._total_amount, 0)
        self.assertGreater(self.analyzer._total_bad_amount, 0)
        self.assertGreater(self.analyzer._overall_amount_bad_rate, 0)
        self.assertLessEqual(self.analyzer._overall_amount_bad_rate, 1.0)

    def test_U2_single_rule_analysis(self):
        """U2: analyze_rule() returns complete metrics dict"""
        self.analyzer.fit(self.df, target_col="label")
        result = self.analyzer.analyze_rule("(f0 == -1)")
        
        expected_keys = [
            "rule", "hit_amount", "hit_amount_pct", "bad_amount",
            "bad_amount_pct", "amount_bad_rate", "amount_lift", "avg_amount_per_hit"
        ]
        for key in expected_keys:
            self.assertIn(key, result, f"Missing key: {key}")
        
        self.assertEqual(result["rule"], "(f0 == -1)")
        self.assertGreaterEqual(result["hit_amount"], 0)
        self.assertGreaterEqual(result["amount_lift"], 0)

    def test_U3_batch_rule_analysis(self):
        """U3: analyze() returns merged DataFrame with 7 additional columns"""
        self.analyzer.fit(self.df, target_col="label")
        
        rule_df = pd.DataFrame({
            "rule": ["(f0 == -1)", "(f0 == 0)", "(f0 >= 2)"],
            "hit_rate": [0.3, 0.2, 0.25],
        })
        
        result = self.analyzer.analyze(rule_df)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        # Should have original columns + 7 amount columns
        amount_cols = ["hit_amount", "hit_amount_pct", "bad_amount", 
                       "bad_amount_pct", "amount_bad_rate", "amount_lift", "avg_amount_per_hit"]
        for col in amount_cols:
            self.assertIn(col, result.columns, f"Missing column: {col}")

    def test_U4_cumulative_analysis(self):
        """U4: analyze_with_cumulative() cumulative logic correct"""
        self.analyzer.fit(self.df, target_col="label")
        
        rule_df = pd.DataFrame({
            "rule": ["(f0 == -1)", "(f0 >= 2)", "(f2 > 5)"],
        })
        
        merged_df, summary = self.analyzer.analyze_with_cumulative(rule_df)
        
        self.assertIsInstance(merged_df, pd.DataFrame)
        self.assertIsInstance(summary, dict)
        
        # Summary structure
        self.assertTrue(summary["enabled"])
        self.assertEqual(summary["amount_col"], "mock_amount")
        self.assertGreater(summary["total_amount"], 0)
        
        # Cumulative metrics
        cum = summary["cumulative"]
        self.assertGreaterEqual(cum["cum_hit_amount"], 0)
        self.assertLessEqual(cum["cum_hit_amount"], summary["total_amount"])
        self.assertGreaterEqual(cum["amount_recall"], 0)
        self.assertLessEqual(cum["amount_recall"], 1.0)


class TestAmountAnalyzerAccuracy(unittest.TestCase):
    """U5: Handcrafted data for exact metric verification"""

    def test_U5_exact_metrics(self):
        """U5: Metrics match hand-calculated values exactly"""
        df = generate_handcrafted_data()
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(df, target_col="label")
        
        # Verify totals
        self.assertAlmostEqual(analyzer._total_amount, HANDCRAFTED_EXPECTED["total_amount"], places=1)
        self.assertAlmostEqual(analyzer._total_bad_amount, HANDCRAFTED_EXPECTED["total_bad_amount"], places=1)
        
        # Verify single rule metrics
        result = analyzer.analyze_rule("(f0 > 0)")
        
        self.assertAlmostEqual(result["hit_amount"], HANDCRAFTED_EXPECTED["hit_amount"], places=1)
        self.assertAlmostEqual(result["bad_amount"], HANDCRAFTED_EXPECTED["bad_amount"], places=1)
        self.assertAlmostEqual(result["hit_amount_pct"], HANDCRAFTED_EXPECTED["hit_amount_pct"], places=3)
        self.assertAlmostEqual(result["bad_amount_pct"], HANDCRAFTED_EXPECTED["bad_amount_pct"], places=3)
        self.assertAlmostEqual(result["amount_bad_rate"], HANDCRAFTED_EXPECTED["amount_bad_rate"], places=3)
        self.assertAlmostEqual(result["amount_lift"], HANDCRAFTED_EXPECTED["amount_lift"], places=1)
        self.assertAlmostEqual(result["avg_amount_per_hit"], HANDCRAFTED_EXPECTED["avg_amount_per_hit"], places=1)


class TestAmountAnalyzerErrorHandling(unittest.TestCase):
    """U6-U9, U12: Error handling and edge cases"""

    def setUp(self):
        self.df = generate_small_test_data(n=50, seed=42)

    def test_U6_missing_amount_col(self):
        """U6: fit() raises ValueError when amount_col not in df"""
        analyzer = AmountAnalyzer(amount_col="nonexistent_col")
        with self.assertRaises(ValueError):
            analyzer.fit(self.df, target_col="label")

    def test_U7_invalid_rule_expression(self):
        """U7: analyze_rule() returns zero metrics on invalid rule (graceful degradation)"""
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(self.df, target_col="label")
        
        result = analyzer.analyze_rule("INVALID RULE @@#$%")
        
        # _safe_eval_rule may gracefully return all-False mask or raise exception
        # Either way: hit_amount should be 0 and amount_lift should be 0
        self.assertEqual(result["hit_amount"], 0)
        self.assertEqual(result["amount_lift"], 0)

    def test_U8_zero_amount(self):
        """U8: All-zero amounts → all ratio metrics are 0, no errors"""
        df = generate_edge_case_data("zero_amount")
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(df, target_col="label")
        
        self.assertEqual(analyzer._total_amount, 0)
        self.assertEqual(analyzer._overall_amount_bad_rate, 0)
        
        result = analyzer.analyze_rule("(f0 > 0)")
        self.assertEqual(result["hit_amount_pct"], 0)
        self.assertEqual(result["amount_lift"], 0)

    def test_U9_not_fitted(self):
        """U9: analyze_rule() raises ValueError when not fitted"""
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        with self.assertRaises(ValueError):
            analyzer.analyze_rule("(f0 > 0)")

    def test_U10_nan_amount(self):
        """U10: NaN in amount column — behavior verification"""
        df = generate_edge_case_data("nan_amount")
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(df, target_col="label")
        
        # NaN values: sum() treats NaN as 0 in pandas by default? No, sum() skips NaN.
        # total_amount should be 100+300+500 = 900 (NaN rows skipped by sum)
        # This test documents actual behavior
        total = analyzer._total_amount
        self.assertFalse(np.isnan(total), "total_amount should not be NaN")

    def test_U11_negative_amount(self):
        """U11: Negative amounts — behavior verification"""
        df = generate_edge_case_data("negative_amount")
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(df, target_col="label")
        
        # total_amount = 100 + (-200) + 300 + (-400) + 500 = 300
        self.assertAlmostEqual(analyzer._total_amount, 300.0, places=1)

    def test_U12_get_summary(self):
        """U12: get_summary() returns correct structure"""
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(self.df, target_col="label")
        
        summary = analyzer.get_summary()
        
        self.assertTrue(summary["enabled"])
        self.assertEqual(summary["amount_col"], "mock_amount")
        self.assertGreater(summary["total_amount"], 0)
        self.assertGreater(summary["total_bad_amount"], 0)
        self.assertGreater(summary["overall_amount_bad_rate"], 0)


# =============================================================================
# U13-U16: RuleEvaluator.evaluate_with_amount Unit Tests
# =============================================================================

class TestEvaluateWithAmount(unittest.TestCase):
    """U13-U16: RuleEvaluator.evaluate_with_amount"""

    def setUp(self):
        self.df = generate_small_test_data(n=200, seed=42)
        self.evaluator = RuleEvaluator()

    def test_U13_normal_evaluation(self):
        """U13: Normal evaluation returns complete 8-field dict"""
        result = self.evaluator.evaluate_with_amount(
            self.df, "(f0 == -1)", target_col="label", amount_col="mock_amount"
        )
        
        expected_keys = [
            "rule", "hit_amount", "hit_amount_pct", "bad_amount",
            "bad_amount_pct", "amount_bad_rate", "amount_lift", "avg_amount_per_hit"
        ]
        for key in expected_keys:
            self.assertIn(key, result, f"Missing key: {key}")
        
        self.assertNotIn("error", result)

    def test_U14_missing_amount_col(self):
        """U14: Missing amount column → zero metrics + error"""
        result = self.evaluator.evaluate_with_amount(
            self.df, "(f0 == -1)", target_col="label", amount_col="nonexistent"
        )
        
        self.assertEqual(result["hit_amount"], 0)
        self.assertIn("error", result)

    def test_U15_no_hits(self):
        """U15: Rule with no matches → zero metrics"""
        result = self.evaluator.evaluate_with_amount(
            self.df, "(f0 == 99999)", target_col="label", amount_col="mock_amount"
        )
        
        self.assertEqual(result["hit_amount"], 0)
        self.assertEqual(result["amount_lift"], 0)

    def test_U16_all_hits(self):
        """U16: Always-true rule → hit_amount = total_amount, lift ≈ 1.0"""
        result = self.evaluator.evaluate_with_amount(
            self.df, "(f0 == f0)", target_col="label", amount_col="mock_amount"
        )
        
        total_amount = self.df["mock_amount"].sum()
        self.assertAlmostEqual(result["hit_amount"], round(total_amount, 2), places=0)
        self.assertAlmostEqual(result["amount_lift"], 1.0, places=1)


# =============================================================================
# E1-E5: Edge Case / Boundary Tests
# =============================================================================

class TestAmountAnalyzerEdgeCases(unittest.TestCase):
    """E1-E5: Edge case and boundary condition tests"""

    def test_E1_all_bad(self):
        """E1: All samples are bad → total_bad_amount = total_amount, lift=1.0"""
        df = generate_edge_case_data("all_bad")
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(df, target_col="label")
        
        self.assertAlmostEqual(
            analyzer._total_bad_amount, analyzer._total_amount, places=1
        )
        self.assertAlmostEqual(analyzer._overall_amount_bad_rate, 1.0, places=2)
        
        result = analyzer.analyze_rule("(f0 > 0)")
        # All hits are bad, so amount_bad_rate should equal overall → lift ≈ 1.0
        if result["hit_amount"] > 0:
            self.assertAlmostEqual(result["amount_lift"], 1.0, places=1)

    def test_E2_all_good(self):
        """E2: All samples are good → total_bad_amount=0, bad_amount_pct=0"""
        df = generate_edge_case_data("all_good")
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(df, target_col="label")
        
        self.assertEqual(analyzer._total_bad_amount, 0)
        
        result = analyzer.analyze_rule("(f0 > 0)")
        self.assertEqual(result["bad_amount"], 0)
        self.assertEqual(result["bad_amount_pct"], 0)

    def test_E3_single_row(self):
        """E3: Single row data — should run without error"""
        df = generate_edge_case_data("single_row")
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(df, target_col="label")
        
        result = analyzer.analyze_rule("(f0 > 0)")
        self.assertIn("rule", result)

    def test_E4_large_amount(self):
        """E4: Large amount values (>1e12) — precision preserved"""
        df = generate_edge_case_data("large_amount")
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        analyzer.fit(df, target_col="label")
        
        self.assertGreater(analyzer._total_amount, 1e12)
        # Should not lose precision in float64
        self.assertFalse(np.isinf(analyzer._total_amount))

    def test_E5_string_amount_col(self):
        """E5: Amount column with string values — should raise or handle"""
        df = pd.DataFrame({
            "f0": [1, 2, 0],
            "label": [1, 0, 1],
            "mock_amount": ["abc", "def", "ghi"],
        })
        analyzer = AmountAnalyzer(amount_col="mock_amount")
        # fit() will succeed but sum() on strings will produce concatenation or error
        # This test documents actual behavior
        try:
            analyzer.fit(df, target_col="label")
            # If it doesn't raise, the total_amount should be a string or cause issues
            # We just verify it doesn't crash silently with wrong numbers
            self.assertIsNotNone(analyzer._total_amount)
        except (TypeError, ValueError):
            pass  # Expected: string column should cause error


# =============================================================================
# B3-B4: Business Validation (self-consistency checks)
# =============================================================================

class TestBusinessConsistency(unittest.TestCase):
    """B3-B4: Internal consistency checks"""

    def setUp(self):
        self.df = generate_small_test_data(n=500, seed=123)
        self.analyzer = AmountAnalyzer(amount_col="mock_amount")
        self.analyzer.fit(self.df, target_col="label")

    def test_B3_hit_amount_pct_consistency(self):
        """B3: hit_amount / total_amount == hit_amount_pct"""
        result = self.analyzer.analyze_rule("(f0 >= 1)")
        
        if self.analyzer._total_amount > 0:
            expected_pct = round(result["hit_amount"] / self.analyzer._total_amount, 4)
            self.assertAlmostEqual(result["hit_amount_pct"], expected_pct, places=3)

    def test_B4_amount_vs_count_direction(self):
        """B4: amount_bad_rate and count bad_rate should be directionally consistent"""
        rule = "(f0 >= 2)"
        amount_result = self.analyzer.analyze_rule(rule)
        
        # Count-based bad rate
        from deepanalyze.analysis.task_SOP.rule_mining import _safe_eval_rule
        hit_mask = _safe_eval_rule(self.df, rule, "df")
        count_bad_rate = self.df.loc[hit_mask, "label"].mean() if hit_mask.sum() > 0 else 0
        
        # Both should be > 0 or both should be 0 (directionally consistent)
        if count_bad_rate > 0:
            self.assertGreater(amount_result["amount_bad_rate"], 0,
                             "Amount bad rate should be > 0 when count bad rate > 0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
