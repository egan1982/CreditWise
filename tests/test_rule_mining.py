"""
Unit tests for Rule Mining SOP Module

Tests core classes and pipeline functionality:
- DataPreprocessor
- FeatureEngineer
- SingleVarRuleMiner
- RuleMiner
- RuleEvaluator
- RuleSelector
- RuleMiningPipeline
- Visualization functions
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import warnings

warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deepanalyze.analysis.task_SOP.rule_mining import (
    DataPreprocessor,
    FeatureEngineer,
    SingleVarRuleMiner,
    RuleMiner,
    RuleEvaluator,
    RuleSelector,
    RuleMiningPipeline
)

from deepanalyze.analysis.task_SOP.rule_mining_viz import (
    plot_cumulative_metrics,
    plot_rule_distribution,
    plot_rule_comparison,
    generate_rule_summary_html,
    HAS_MATPLOTLIB,
    HAS_PLOTLY
)


class TestDataPreprocessor(unittest.TestCase):
    """Test cases for DataPreprocessor class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 200
        
        cls.df = pd.DataFrame({
            'fuuid': [f'user_{i}' for i in range(n_samples)],
            'f0': np.random.randint(20, 60, n_samples),  # age
            'f1': np.random.randint(20000, 150000, n_samples),  # income
            'f2': np.random.choice(['A', 'B', 'C'], n_samples),  # channel
            'constant_col': 1,  # constant column
            'target': np.random.randint(0, 2, n_samples),
            'weight': np.ones(n_samples)
        })
        
        cls.name_mapping = {'f0': 'age', 'f1': 'income', 'f2': 'channel'}
    
    def test_init(self):
        """Test DataPreprocessor initialization"""
        preprocessor = DataPreprocessor(
            id_cols=['fuuid'],
            name_mapping=self.name_mapping
        )
        self.assertEqual(preprocessor.id_cols, ['fuuid'])
        self.assertEqual(preprocessor.name_mapping, self.name_mapping)
    
    def test_rename_features(self):
        """Test feature renaming"""
        preprocessor = DataPreprocessor(name_mapping=self.name_mapping)
        df_renamed = preprocessor.rename_features(self.df.copy())
        
        self.assertIn('age', df_renamed.columns)
        self.assertIn('income', df_renamed.columns)
        self.assertIn('channel', df_renamed.columns)
        self.assertNotIn('f0', df_renamed.columns)
    
    def test_drop_id_columns(self):
        """Test ID column dropping"""
        preprocessor = DataPreprocessor(id_cols=['fuuid'])
        df_clean, dropped = preprocessor.drop_id_columns(self.df.copy())
        
        self.assertNotIn('fuuid', df_clean.columns)
        self.assertIn('fuuid', dropped)
    
    def test_drop_constant_columns(self):
        """Test constant column detection (no longer drops, just detects)"""
        preprocessor = DataPreprocessor()
        # 使用新的检测方法（不删除）
        detected = preprocessor._detect_constant_columns(
            self.df.copy(),
            exclude_cols=['target', 'weight']
        )
        
        # 常量列应该被检测到
        self.assertIn('constant_col', detected)
    
    def test_preprocess_full(self):
        """Test full preprocessing pipeline"""
        preprocessor = DataPreprocessor(
            id_cols=['fuuid'],
            name_mapping=self.name_mapping
        )
        
        df_processed, info = preprocessor.preprocess(
            self.df.copy(),
            target_col='target',
            weight_col='weight',
            do_onehot=True,
            categorical_cols=['f2']  # Will be renamed to 'channel'
        )
        
        # 新逻辑：不再删除ID列和常量列，只标记
        # ID列和常量列仍然存在于 df_processed 中
        self.assertIn('fuuid', df_processed.columns)
        self.assertIn('constant_col', df_processed.columns)
        
        # Check target and weight preserved
        self.assertIn('target', df_processed.columns)
        self.assertIn('weight', df_processed.columns)
        
        # Check info dict - 新增 detected_* 字段
        self.assertIn('detected_id_cols', info)
        self.assertIn('detected_constant_cols', info)
        # 旧字段保留但值为空（兼容性）
        self.assertIn('dropped_id_cols', info)
        self.assertIn('dropped_constant_cols', info)
        self.assertEqual(info['dropped_id_cols'], [])
        self.assertEqual(info['dropped_constant_cols'], [])
    
    def test_detect_datetime_columns(self):
        """Test datetime column detection"""
        # Create test data with datetime column
        df_with_datetime = self.df.copy()
        df_with_datetime['create_time'] = pd.date_range('2024-01-01', periods=len(df_with_datetime), freq='h')
        df_with_datetime['date_str'] = df_with_datetime['create_time'].astype(str)
        
        preprocessor = DataPreprocessor()
        datetime_cols = preprocessor.detect_datetime_columns(
            df_with_datetime,
            exclude_cols=['target', 'weight']
        )
        
        self.assertIn('create_time', datetime_cols)
    
    def test_preprocess_datetime(self):
        """Test datetime preprocessing"""
        # Create test data with datetime column
        n_samples = 100
        df_with_datetime = pd.DataFrame({
            'create_time': pd.date_range('2024-01-01', periods=n_samples, freq='h'),
            'value': np.random.randn(n_samples),
            'target': np.random.randint(0, 2, n_samples)
        })
        
        preprocessor = DataPreprocessor(datetime_indicator='_dt_')
        df_processed, new_cols = preprocessor.preprocess_datetime(
            df_with_datetime,
            datetime_cols=['create_time'],
            extract_features=['year', 'month', 'dayofweek', 'hour', 'days_since']
        )
        
        # Check original column removed
        self.assertNotIn('create_time', df_processed.columns)
        
        # Check derived columns created
        self.assertIn('create_time_dt_year', df_processed.columns)
        self.assertIn('create_time_dt_month', df_processed.columns)
        self.assertIn('create_time_dt_dayofweek', df_processed.columns)
        self.assertIn('create_time_dt_hour', df_processed.columns)
        self.assertIn('create_time_dt_days_since', df_processed.columns)
        
        # Check new_cols list
        self.assertEqual(len(new_cols), 5)
        
        # Check values are numeric
        self.assertTrue(df_processed['create_time_dt_year'].dtype in [np.int64, np.int32, np.float64])
    
    def test_detect_text_columns(self):
        """Test text column detection"""
        # Create test data with text column
        n_samples = 100
        df_with_text = pd.DataFrame({
            'description': ['This is a long description text that should be detected as text column ' * 2 + str(i) for i in range(n_samples)],
            'short_code': ['A', 'B', 'C'] * 33 + ['A'],  # Low cardinality, not text
            'value': np.random.randn(n_samples),
            'target': np.random.randint(0, 2, n_samples)
        })
        
        preprocessor = DataPreprocessor()
        text_cols = preprocessor.detect_text_columns(
            df_with_text,
            exclude_cols=['target'],
            min_unique_ratio=0.5,
            min_avg_length=20
        )
        
        self.assertIn('description', text_cols)
        self.assertNotIn('short_code', text_cols)
    
    def test_preprocess_text(self):
        """Test text preprocessing"""
        # Create test data with text column
        n_samples = 50
        df_with_text = pd.DataFrame({
            'comment': [
                '这是一条投诉信息，服务很差',
                'Great service, very satisfied!',
                '一般般，没什么特别的',
                '',
                '12345 测试数据',
            ] * 10,
            'value': np.random.randn(n_samples),
            'target': np.random.randint(0, 2, n_samples)
        })
        
        preprocessor = DataPreprocessor(text_indicator='_txt_')
        df_processed, new_cols = preprocessor.preprocess_text(
            df_with_text,
            text_cols=['comment'],
            extract_features=['length', 'word_count', 'has_digits', 'has_chinese', 'is_empty'],
            keywords={'has_complaint': ['投诉', '差']}
        )
        
        # Check original column removed
        self.assertNotIn('comment', df_processed.columns)
        
        # Check derived columns created
        self.assertIn('comment_txt_length', df_processed.columns)
        self.assertIn('comment_txt_word_count', df_processed.columns)
        self.assertIn('comment_txt_has_digits', df_processed.columns)
        self.assertIn('comment_txt_has_chinese', df_processed.columns)
        self.assertIn('comment_txt_is_empty', df_processed.columns)
        self.assertIn('comment_txt_has_complaint', df_processed.columns)
        
        # Check keyword detection
        complaint_flags = df_processed['comment_txt_has_complaint'].values
        self.assertEqual(complaint_flags[0], 1)  # First row has '投诉' and '差'
        self.assertEqual(complaint_flags[1], 0)  # Second row has no complaint keywords
    
    def test_preprocess_with_datetime_and_text(self):
        """Test full preprocessing with datetime and text columns"""
        # Create comprehensive test data
        n_samples = 50
        df_full = pd.DataFrame({
            'user_id': [f'user_{i}' for i in range(n_samples)],
            'create_time': pd.date_range('2024-01-01', periods=n_samples, freq='D'),
            'comment': ['This is a test comment ' + str(i) * 5 for i in range(n_samples)],
            'category': np.random.choice(['A', 'B', 'C'], n_samples),
            'amount': np.random.randint(100, 10000, n_samples),
            'target': np.random.randint(0, 2, n_samples),
            'weight': np.ones(n_samples)
        })
        
        preprocessor = DataPreprocessor(
            id_cols=['user_id'],
            datetime_indicator='_dt_',
            text_indicator='_txt_'
        )
        
        df_processed, info = preprocessor.preprocess(
            df_full,
            target_col='target',
            weight_col='weight',
            do_onehot=True,
            do_datetime=True,
            do_text=True,
            categorical_cols=['category'],
            datetime_cols=['create_time'],
            text_cols=['comment'],
            datetime_features=['year', 'month', 'days_since'],
            text_features=['length', 'word_count']
        )
        
        # Check ID column removed
        self.assertNotIn('user_id', df_processed.columns)
        
        # Check datetime derived columns
        self.assertIn('create_time_dt_year', df_processed.columns)
        self.assertIn('create_time_dt_month', df_processed.columns)
        self.assertIn('create_time_dt_days_since', df_processed.columns)
        
        # Check text derived columns
        self.assertIn('comment_txt_length', df_processed.columns)
        self.assertIn('comment_txt_word_count', df_processed.columns)
        
        # Check One-Hot columns
        self.assertTrue(any('category_is_' in col for col in df_processed.columns))
        
        # Check info dict
        self.assertIn('datetime_derived', info)
        self.assertIn('text_derived', info)


class TestFeatureEngineer(unittest.TestCase):
    """Test cases for FeatureEngineer class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 200
        
        cls.df = pd.DataFrame({
            'age': np.random.randint(20, 60, n_samples),
            'income': np.random.randint(20000, 150000, n_samples),
            'credit_score': np.random.randint(300, 850, n_samples),
            'target': np.random.randint(0, 2, n_samples),
            'weight': np.ones(n_samples)
        })
        
        # Add some missing values
        cls.df.loc[0:10, 'age'] = np.nan
        cls.df.loc[5:15, 'income'] = np.nan
    
    def test_check_missing(self):
        """Test missing value checking"""
        engineer = FeatureEngineer()
        missing_report = engineer.check_missing(
            self.df,
            exclude_cols=['target', 'weight']
        )
        
        self.assertIsInstance(missing_report, pd.DataFrame)
        self.assertIn('missing_count', missing_report.columns)
        self.assertIn('missing_rate', missing_report.columns)
    
    def test_handle_missing(self):
        """Test missing value handling"""
        engineer = FeatureEngineer(missing_threshold=0.5)
        df_clean, dropped = engineer.handle_missing(
            self.df.copy(),
            exclude_cols=['target', 'weight']
        )
        
        # No columns should be dropped (missing rate < 0.5)
        self.assertEqual(len(dropped), 0)
        
        # Missing values should be filled
        self.assertEqual(df_clean['age'].isnull().sum(), 0)
        self.assertEqual(df_clean['income'].isnull().sum(), 0)
    
    def test_calculate_iv(self):
        """Test IV calculation"""
        engineer = FeatureEngineer()
        
        # Fill missing first
        df_clean = self.df.copy().fillna(self.df.median())
        
        iv_table = engineer.calculate_iv(
            df_clean,
            target_col='target',
            weight_col='weight',
            feature_cols=['age', 'income', 'credit_score']
        )
        
        self.assertIsInstance(iv_table, pd.DataFrame)
        self.assertIn('iv', iv_table.columns)
        self.assertEqual(len(iv_table), 3)


class TestSingleVarRuleMiner(unittest.TestCase):
    """Test cases for SingleVarRuleMiner class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 500
        
        # Create data with clear patterns
        cls.df = pd.DataFrame({
            'age': np.random.randint(18, 70, n_samples),
            'income': np.random.randint(10000, 200000, n_samples),
            'target': np.zeros(n_samples),
            'weight': np.ones(n_samples)
        })
        
        # Create pattern: young + low income = bad
        bad_mask = (cls.df['age'] < 30) & (cls.df['income'] < 50000)
        cls.df.loc[bad_mask, 'target'] = 1
        
        # Add some noise
        noise_idx = np.random.choice(n_samples, size=50, replace=False)
        cls.df.loc[noise_idx, 'target'] = 1 - cls.df.loc[noise_idx, 'target']
    
    def test_init(self):
        """Test SingleVarRuleMiner initialization"""
        miner = SingleVarRuleMiner(n_bins=10, bin_method='quantile')
        self.assertEqual(miner.n_bins, 10)
        self.assertEqual(miner.bin_method, 'quantile')
    
    def test_generate_rules(self):
        """Test rule generation"""
        miner = SingleVarRuleMiner(n_bins=5, directions='both')
        
        rules = miner.generate_rules(
            self.df,
            feature_cols=['age', 'income'],
            target_col='target',
            weight_col='weight'
        )
        
        self.assertIsInstance(rules, pd.DataFrame)
        self.assertIn('rule', rules.columns)
        self.assertIn('used_var', rules.columns)
        self.assertGreater(len(rules), 0)
        
        # Check rule format
        sample_rule = rules['rule'].iloc[0]
        self.assertTrue('(' in sample_rule and ')' in sample_rule)
    
    def test_binary_feature_detection(self):
        """Test binary feature detection"""
        miner = SingleVarRuleMiner(n_bins=5, directions='both')
        
        # Test indicator-based detection
        self.assertTrue(miner.is_binary_feature('channel_is_A', None))
        self.assertTrue(miner.is_binary_feature('desc_txt_has_urgent', None))
        self.assertTrue(miner.is_binary_feature('is_flag_active', None))
        self.assertFalse(miner.is_binary_feature('age', None))
        
        # Test value-based detection
        binary_series = pd.Series([0, 1, 0, 1, 1, 0])
        self.assertTrue(miner.is_binary_feature('some_col', binary_series))
        
        non_binary_series = pd.Series([0, 1, 2, 3])
        self.assertFalse(miner.is_binary_feature('some_col', non_binary_series))
    
    def test_binary_feature_rules(self):
        """Test that binary features use == direction"""
        np.random.seed(42)
        n_samples = 200
        
        # Create data with binary features
        df = pd.DataFrame({
            'age': np.random.randint(18, 70, n_samples),
            'channel_is_A': np.random.randint(0, 2, n_samples),  # Binary feature by name
            'has_flag': np.random.choice([0, 1], n_samples),  # Binary feature by values
            'target': np.random.randint(0, 2, n_samples),
            'weight': np.ones(n_samples)
        })
        
        miner = SingleVarRuleMiner(n_bins=5, directions='both')
        rules = miner.generate_rules(
            df,
            feature_cols=['age', 'channel_is_A', 'has_flag'],
            target_col='target',
            weight_col='weight'
        )
        
        # Check that binary features have == direction
        binary_rules = rules[rules['used_var'] == 'channel_is_A']
        self.assertTrue(all(binary_rules['direction'] == '=='))
        
        # Check that numeric features have <= or > direction
        numeric_rules = rules[rules['used_var'] == 'age']
        self.assertTrue(all(numeric_rules['direction'].isin(['<=', '>'])))


class TestRuleMiner(unittest.TestCase):
    """Test cases for RuleMiner class (multi-variable)"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 500
        
        cls.df = pd.DataFrame({
            'age': np.random.randint(18, 70, n_samples),
            'income': np.random.randint(10000, 200000, n_samples),
            'credit_score': np.random.randint(300, 850, n_samples),
            'target': np.zeros(n_samples),
            'weight': np.ones(n_samples)
        })
        
        # Create pattern
        bad_mask = (cls.df['age'] < 30) & (cls.df['income'] < 50000)
        cls.df.loc[bad_mask, 'target'] = 1
        
        # Add noise
        noise_idx = np.random.choice(n_samples, size=50, replace=False)
        cls.df.loc[noise_idx, 'target'] = 1 - cls.df.loc[noise_idx, 'target']
    
    def test_init(self):
        """Test RuleMiner initialization"""
        miner = RuleMiner(max_depth=5, n_vars=3)
        self.assertEqual(miner.max_depth, 5)
        self.assertEqual(miner.n_vars, 3)
    
    def test_generate_rules(self):
        """Test multi-variable rule generation"""
        miner = RuleMiner(max_depth=3, n_vars=2, min_samples_leaf=0.05)
        
        rules = miner.generate_rules(
            self.df,
            feature_cols=['age', 'income', 'credit_score'],
            target_col='target',
            weight_col='weight'
        )
        
        self.assertIsInstance(rules, pd.DataFrame)
        self.assertIn('rule', rules.columns)
        self.assertGreater(len(rules), 0)
    
    def test_get_split_direction(self):
        """Test split direction calculation"""
        miner = RuleMiner()
        
        direction_df = miner.get_split_direction(
            self.df,
            target_col='target',
            weight_col='weight'
        )
        
        self.assertIsInstance(direction_df, pd.DataFrame)
        self.assertIn('direction', direction_df.columns)
    
    def test_get_split_direction_binary_features(self):
        """Test that binary features get == direction in split direction"""
        np.random.seed(42)
        n_samples = 300
        
        # Create data with binary features
        df = pd.DataFrame({
            'age': np.random.randint(18, 70, n_samples),
            'channel_is_A': np.random.randint(0, 2, n_samples),  # Binary by name
            'flag_txt_has_urgent': np.random.choice([0, 1], n_samples),  # Binary by name
            'target': np.random.randint(0, 2, n_samples),
            'weight': np.ones(n_samples)
        })
        
        miner = RuleMiner()
        direction_df = miner.get_split_direction(
            df,
            target_col='target',
            weight_col='weight'
        )
        
        # Check that binary features have == direction
        binary_dirs = direction_df[direction_df['var'].str.contains('_is_|_txt_has_')]
        if len(binary_dirs) > 0:
            self.assertTrue(all(binary_dirs['direction'] == '=='))
        
        # Check that numeric features have <= or > direction
        numeric_dirs = direction_df[direction_df['var'] == 'age']
        if len(numeric_dirs) > 0:
            self.assertTrue(all(numeric_dirs['direction'].isin(['<=', '>'])))


class TestRuleEvaluator(unittest.TestCase):
    """Test cases for RuleEvaluator class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 500
        
        cls.df = pd.DataFrame({
            'age': np.random.randint(18, 70, n_samples),
            'income': np.random.randint(10000, 200000, n_samples),
            'target': np.zeros(n_samples),
            'weight': np.ones(n_samples)
        })
        
        bad_mask = (cls.df['age'] < 30) & (cls.df['income'] < 50000)
        cls.df.loc[bad_mask, 'target'] = 1
        
        # Create sample rules
        cls.rules_df = pd.DataFrame({
            'rule': ['(age <= 30)', '(income <= 50000)', '(age <= 25)'],
            'used_var': ['age', 'income', 'age']
        })
    
    def test_evaluate_rules(self):
        """Test rule evaluation"""
        evaluator = RuleEvaluator()
        
        evaluated = evaluator.evaluate_rules(
            self.df,
            self.rules_df,
            target_col='target',
            weight_col='weight'
        )
        
        self.assertIsInstance(evaluated, pd.DataFrame)
        self.assertIn('recall', evaluated.columns)
        self.assertIn('bad_rate', evaluated.columns)
        self.assertIn('lift', evaluated.columns)
        self.assertIn('hit_rate', evaluated.columns)
    
    def test_filter_by_metrics(self):
        """Test metric-based filtering"""
        evaluator = RuleEvaluator()
        
        evaluated = evaluator.evaluate_rules(
            self.df,
            self.rules_df,
            target_col='target',
            weight_col='weight'
        )
        
        filtered = evaluator.filter_by_metrics(
            evaluated,
            max_hit_rate=0.5,
            min_lift=1.0
        )
        
        self.assertIsInstance(filtered, pd.DataFrame)
        # All remaining rules should meet criteria
        if len(filtered) > 0:
            self.assertTrue((filtered['hit_rate'] <= 0.5).all())
            self.assertTrue((filtered['lift'] >= 1.0).all())


class TestRuleSelector(unittest.TestCase):
    """Test cases for RuleSelector class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 500
        
        cls.df = pd.DataFrame({
            'age': np.random.randint(18, 70, n_samples),
            'income': np.random.randint(10000, 200000, n_samples),
            'target': np.zeros(n_samples),
            'weight': np.ones(n_samples)
        })
        
        bad_mask = (cls.df['age'] < 30) & (cls.df['income'] < 50000)
        cls.df.loc[bad_mask, 'target'] = 1
        
        # Create evaluated rules
        cls.rules_df = pd.DataFrame({
            'rule': ['(age <= 30)', '(income <= 50000)', '(age <= 25)'],
            'used_var': ['age', 'income', 'age'],
            'recall': [0.6, 0.5, 0.3],
            'bad_rate': [0.4, 0.35, 0.5],
            'lift': [2.0, 1.8, 2.5],
            'hit_rate': [0.3, 0.28, 0.12]
        })
    
    def test_select_optimal_rules(self):
        """Test optimal rule selection"""
        selector = RuleSelector()
        
        optimal = selector.select_optimal_rules(
            self.df,
            self.rules_df,
            target_col='target',
            weight_col='weight',
            max_hit_rate=0.3
        )
        
        self.assertIsInstance(optimal, pd.DataFrame)
        self.assertIn('dev_cum_recall', optimal.columns)
        self.assertIn('dev_cum_hit_rate', optimal.columns)
        
        # Cumulative hit rate should not exceed limit
        if len(optimal) > 0:
            self.assertTrue(optimal['dev_cum_hit_rate'].iloc[-1] <= 0.3)


class TestRuleMiningPipeline(unittest.TestCase):
    """Test cases for RuleMiningPipeline class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        np.random.seed(42)
        n_samples = 500
        
        cls.df = pd.DataFrame({
            'fuuid': [f'user_{i}' for i in range(n_samples)],
            'f0': np.random.randint(18, 70, n_samples),
            'f1': np.random.randint(10000, 200000, n_samples),
            'f2': np.random.randint(300, 850, n_samples),
            'target': np.zeros(n_samples),
            'weight': np.ones(n_samples)
        })
        
        bad_mask = (cls.df['f0'] < 30) & (cls.df['f1'] < 50000)
        cls.df.loc[bad_mask, 'target'] = 1
        
        noise_idx = np.random.choice(n_samples, size=50, replace=False)
        cls.df.loc[noise_idx, 'target'] = 1 - cls.df.loc[noise_idx, 'target']
        
        cls.name_mapping = {'f0': 'age', 'f1': 'income', 'f2': 'credit_score'}
    
    def test_single_mode_pipeline(self):
        """Test single-variable mode pipeline"""
        pipeline = RuleMiningPipeline(
            mining_mode='single',
            id_cols=['fuuid'],
            name_mapping=self.name_mapping,
            n_bins=5,
            max_hit_rate_filter=0.1,
            min_lift_filter=1.5,
            max_hit_rate_select=0.2
        )
        
        results = pipeline.run(
            self.df.copy(),
            target_col='target',
            weight_col='weight'
        )
        
        self.assertIn('mining_mode', results)
        self.assertEqual(results['mining_mode'], 'single')
        self.assertIn('preprocessing', results)
        self.assertIn('all_rules', results)
        self.assertIn('optimal_rules', results)
    
    def test_multi_mode_pipeline(self):
        """Test multi-variable mode pipeline"""
        pipeline = RuleMiningPipeline(
            mining_mode='multi',
            id_cols=['fuuid'],
            name_mapping=self.name_mapping,
            max_depth=3,
            n_vars=2,
            max_hit_rate_filter=0.1,
            min_lift_filter=1.5,
            max_hit_rate_select=0.2
        )
        
        results = pipeline.run(
            self.df.copy(),
            target_col='target',
            weight_col='weight'
        )
        
        self.assertIn('mining_mode', results)
        self.assertEqual(results['mining_mode'], 'multi')
        self.assertIn('all_rules', results)


class TestVisualization(unittest.TestCase):
    """Test cases for visualization functions"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        cls.optimal_rules_df = pd.DataFrame({
            'rule': ['(age <= 25)', '(income <= 30000)', '(score <= 500)'],
            'used_var': ['age', 'income', 'score'],
            'lift': [3.0, 2.5, 2.0],
            'dev_cum_recall': [0.3, 0.5, 0.65],
            'dev_cum_hit_rate': [0.05, 0.08, 0.10],
            'dev_cum_lift': [3.0, 2.8, 2.5]
        })
        
        cls.evaluated_rules_df = pd.DataFrame({
            'rule': [f'rule_{i}' for i in range(20)],
            'recall': np.random.uniform(0.1, 0.5, 20),
            'hit_rate': np.random.uniform(0.01, 0.1, 20),
            'lift': np.random.uniform(1.5, 4.0, 20),
            'bad_rate': np.random.uniform(0.2, 0.6, 20)
        })
    
    @unittest.skipUnless(HAS_PLOTLY, "Plotly not available")
    def test_plot_cumulative_metrics_plotly(self):
        """Test cumulative metrics plot with Plotly"""
        fig = plot_cumulative_metrics(
            self.optimal_rules_df,
            output_format='plotly',
            return_html=False
        )
        self.assertIsNotNone(fig)
    
    @unittest.skipUnless(HAS_MATPLOTLIB, "Matplotlib not available")
    def test_plot_cumulative_metrics_matplotlib(self):
        """Test cumulative metrics plot with Matplotlib"""
        fig = plot_cumulative_metrics(
            self.optimal_rules_df,
            output_format='matplotlib'
        )
        self.assertIsNotNone(fig)
    
    @unittest.skipUnless(HAS_PLOTLY, "Plotly not available")
    def test_plot_rule_distribution(self):
        """Test rule distribution plot"""
        fig = plot_rule_distribution(
            self.evaluated_rules_df,
            x_metric='hit_rate',
            y_metric='lift',
            color_metric='recall',
            output_format='plotly'
        )
        self.assertIsNotNone(fig)
    
    @unittest.skipUnless(HAS_PLOTLY, "Plotly not available")
    def test_plot_rule_comparison(self):
        """Test rule comparison plot"""
        fig = plot_rule_comparison(
            self.evaluated_rules_df,
            metrics=['recall', 'hit_rate', 'lift'],
            top_n=5,
            output_format='plotly'
        )
        self.assertIsNotNone(fig)
    
    @unittest.skipUnless(HAS_PLOTLY, "Plotly not available")
    def test_generate_rule_summary_html(self):
        """Test HTML summary generation"""
        html = generate_rule_summary_html(
            self.optimal_rules_df,
            self.evaluated_rules_df,
            include_charts=True
        )
        
        self.assertIsInstance(html, str)
        self.assertIn('规则挖掘结果摘要', html)
        self.assertIn('最优规则列表', html)


if __name__ == '__main__':
    unittest.main(verbosity=2)
