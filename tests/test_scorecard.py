"""
Unit tests for Scorecard Analysis Module

Tests WOE calculation, IV analysis, and feature binning functionality.
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deepanalyze.analysis.woe import WOECalculator
from deepanalyze.analysis.feature_binning import FeatureBinner
from deepanalyze.analysis.iv_analysis import IVAnalyzer


class TestWOECalculator(unittest.TestCase):
    """Test cases for WOE calculator"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 100
        
        # Generate synthetic data
        cls.df = pd.DataFrame({
            'age': np.random.randint(20, 60, n_samples),
            'income': np.random.randint(20000, 150000, n_samples),
            'credit_score': np.random.randint(300, 850, n_samples),
            'target': np.random.randint(0, 2, n_samples)
        })
    
    def test_woe_calculation_success(self):
        """Test successful WOE calculation"""
        result = WOECalculator.calculate_woe(
            self.df,
            'age',
            'target',
            n_bins=5,
            method='quantile'
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('woe', result)
        self.assertIn('iv', result)
        self.assertIn('bins', result)
        self.assertGreater(result['iv'], 0)
    
    def test_woe_invalid_feature(self):
        """Test WOE with invalid feature"""
        result = WOECalculator.calculate_woe(
            self.df,
            'invalid_feature',
            'target'
        )
        
        self.assertEqual(result['status'], 'error')
    
    def test_woe_invalid_target(self):
        """Test WOE with invalid target"""
        result = WOECalculator.calculate_woe(
            self.df,
            'age',
            'invalid_target'
        )
        
        self.assertEqual(result['status'], 'error')
    
    def test_iv_interpretation(self):
        """Test IV value interpretation"""
        self.assertEqual(
            WOECalculator._interpret_iv(0.01),
            "无预测力 (Negligible)"
        )
        self.assertEqual(
            WOECalculator._interpret_iv(0.05),
            "弱预测力 (Weak)"
        )
        self.assertEqual(
            WOECalculator._interpret_iv(0.15),
            "中等预测力 (Medium)"
        )
        self.assertEqual(
            WOECalculator._interpret_iv(0.35),
            "强预测力 (Strong)"
        )


class TestFeatureBinner(unittest.TestCase):
    """Test cases for Feature Binner"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        cls.df = pd.DataFrame({
            'age': np.random.randint(20, 60, 100),
            'income': np.random.randint(20000, 150000, 100)
        })
    
    def test_quantile_binning(self):
        """Test quantile binning"""
        result = FeatureBinner.auto_bin(
            self.df,
            'age',
            n_bins=5,
            method='quantile'
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['n_bins'], 5)
        self.assertGreater(len(result['bin_statistics']), 0)
    
    def test_uniform_binning(self):
        """Test uniform binning"""
        result = FeatureBinner.auto_bin(
            self.df,
            'age',
            n_bins=5,
            method='uniform'
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['n_bins'], 5)
    
    def test_custom_binning(self):
        """Test custom binning"""
        result = FeatureBinner.custom_bin(
            self.df,
            'age',
            bins=[20, 30, 40, 50, 60]
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('bin_statistics', result)
    
    def test_invalid_feature_binning(self):
        """Test binning with invalid feature"""
        result = FeatureBinner.auto_bin(
            self.df,
            'invalid_feature',
            n_bins=5
        )
        
        self.assertEqual(result['status'], 'error')


class TestIVAnalyzer(unittest.TestCase):
    """Test cases for IV Analyzer"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 100
        
        cls.df = pd.DataFrame({
            'age': np.random.randint(20, 60, n_samples),
            'income': np.random.randint(20000, 150000, n_samples),
            'credit_score': np.random.randint(300, 850, n_samples),
            'target': np.random.randint(0, 2, n_samples)
        })
    
    def test_analyze_features(self):
        """Test IV analysis for multiple features"""
        result = IVAnalyzer.analyze_features(
            self.df,
            'target',
            features=['age', 'income', 'credit_score'],
            n_bins=5
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['analyzed_features'], 3)
        self.assertGreater(len(result['results']), 0)
        self.assertIn('summary', result)
    
    def test_feature_selection(self):
        """Test feature selection by IV threshold"""
        result = IVAnalyzer.feature_selection(
            self.df,
            'target',
            iv_threshold=0.1,
            features=['age', 'income', 'credit_score']
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('selected_features', result)
        self.assertIsInstance(result['selected_features'], list)
    
    def test_auto_feature_selection(self):
        """Test automatic feature selection (all numeric features)"""
        result = IVAnalyzer.analyze_features(
            self.df,
            'target'
        )
        
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['analyzed_features'], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 200
        
        # Create more realistic data
        cls.df = pd.DataFrame({
            'age': np.random.randint(20, 70, n_samples),
            'income': np.random.randint(20000, 200000, n_samples),
            'credit_score': np.random.randint(300, 850, n_samples),
            'employment_years': np.random.randint(0, 40, n_samples),
            'target': np.concatenate([
                np.ones(int(n_samples * 0.3)),
                np.zeros(n_samples - int(n_samples * 0.3))
            ])
        })
    
    def test_end_to_end_scorecard_building(self):
        """Test complete scorecard building process"""
        # Step 1: Feature selection
        selection = IVAnalyzer.feature_selection(
            self.df,
            'target',
            iv_threshold=0.05,
            features=['age', 'income', 'credit_score', 'employment_years']
        )
        
        self.assertEqual(selection['status'], 'success')
        
        # Step 2: WOE calculation for selected features
        selected_features = selection['selected_features']
        
        for feature in selected_features:
            woe_result = WOECalculator.calculate_woe(
                self.df,
                feature,
                'target'
            )
            
            self.assertEqual(woe_result['status'], 'success')
            self.assertIn('woe', woe_result)
            self.assertIn('iv', woe_result)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestWOECalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestFeatureBinner))
    suite.addTests(loader.loadTestsFromTestCase(TestIVAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
