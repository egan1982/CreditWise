"""
Scorecard and WOE/IV Analysis Module

Provides statistical analysis tools for credit risk assessment and feature engineering.

Submodules:
- woe: WOE (Weight of Evidence) calculation
- feature_binning: Feature binning/discretization
- iv_analysis: IV (Information Value) analysis
- preprocessing: General data preprocessing utilities (datetime, text, categorical)
- feature_correlation: Correlation analysis and VIF testing (NEW)
- task_SOP: Standardized task workflows (Rule Mining, Scorecard Development)
"""

from .woe import WOECalculator
from .feature_binning import FeatureBinner
from .iv_analysis import IVAnalyzer
from .preprocessing import (
    DatetimeProcessor,
    TextProcessor,
    CategoricalProcessor,
    ColumnCleaner,
    GeneralPreprocessor
)
from .feature_correlation import CorrelationAnalyzer, VIFAnalyzer
from .task_SOP import RuleMiner, RuleEvaluator, RuleSelector

# New modules for upgrade plan
from .statistical_model import StatisticalLogisticRegression, fit_statistical_logistic_regression
from .score_transformer import ScoreTransformer, create_score_transformer
from .excel_report import ExcelReportGenerator, generate_excel_report
from .word_report import generate_word_report

__all__ = [
    # WOE/IV Analysis
    'WOECalculator', 
    'FeatureBinner', 
    'IVAnalyzer',
    # General Preprocessing
    'DatetimeProcessor',
    'TextProcessor',
    'CategoricalProcessor',
    'ColumnCleaner',
    'GeneralPreprocessor',
    # Correlation Analysis & VIF (NEW)
    'CorrelationAnalyzer',
    'VIFAnalyzer',
    # Rule Mining
    'RuleMiner',
    'RuleEvaluator', 
    'RuleSelector',
    # Statistical Model (NEW)
    'StatisticalLogisticRegression',
    'fit_statistical_logistic_regression',
    # Score Transformer (NEW)
    'ScoreTransformer',
    'create_score_transformer',
    # Excel Report (NEW)
    'ExcelReportGenerator',
    'generate_excel_report',
    # Word Report (NEW)
    'generate_word_report',
]
