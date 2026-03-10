# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnusedParameter=false, reportUnusedVariable=false, reportUnnecessaryComparison=false, reportMissingParameterType=false, reportUnknownLambdaType=false, reportUnnecessaryTypeIgnoreComment=false, reportImplicitRelativeImport=false, reportAssignmentType=false, reportReturnType=false, reportOperatorIssue=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false, reportOptionalIterable=false, reportOptionalOperand=false, reportOptionalSubscript=false, reportMissingTypeArgument=false, reportUninitializedInstanceVariable=false, reportPossiblyUnboundVariable=false, reportUnannotatedClassAttribute=false, reportUnusedCallResult=false, reportImplicitStringConcatenation=false, reportUnusedFunction=false, reportRedeclaration=false, reportPrivateUsage=false
"""
Rule Mining Task SOP Module

Provides standardized workflow for decision tree based rule mining and evaluation.
This module encapsulates the complete rule mining pipeline:
0a. Data Preprocessing - Feature name mapping, drop useless columns, basic cleaning
0b. [Optional] Feature Engineering - Missing value handling, IV calculation, One-Hot encoding
1. Rule Generation - Generate candidate rules from decision trees
2. Rule Filtering - Filter rules by direction and validity
3. Rule Evaluation - Calculate recall, bad_rate, lift, hit_rate
4. Rule Selection - Select optimal rule set using greedy algorithm

Business Scenario: Risk control / Anti-fraud rule mining and effect evaluation
"""

import logging
import numpy as np
import pandas as pd
import re
from itertools import combinations
from sklearn import tree
from typing import Callable, Any
import warnings

logger = logging.getLogger(__name__)

# Import general preprocessing utilities
from ..preprocessing import (
    DatetimeProcessor,
    TextProcessor,
    CategoricalProcessor,
    ColumnCleaner
)

# Import code templates for pseudocode generation
from deepanalyze.analysis.task_SOP.code_templates import format_code_template  # type: ignore[reportImplicitRelativeImport]

# Import validators from unified validators module
from deepanalyze.analysis.task_SOP.validators import RuleValidator  # type: ignore[reportImplicitRelativeImport, reportAssignmentType]

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Type alias for progress callback
# Internal progress callback: (current, total)
ProgressCallback = Callable[[int, int], None] | None
# Stage progress callback (unified signature): (stage_id, progress_percent, message, code?, output_preview?)
# Extended to support optional code and output_preview parameters
StageProgressCallback = (
    Callable[[str, float, str], None] | 
    Callable[[str, float, str, str | None], None] |
    Callable[[str, float, str, str | None, dict[str, Any] | None], None] | 
    None
)


class TaskStoppedException(Exception):
    """Exception raised when task execution is stopped by user (expert mode pause)."""
    pass


def _safe_eval_rule(df: pd.DataFrame, rule: str, df_name: str = 'df') -> pd.Series:
    """
    Safely evaluate a rule expression on a DataFrame using pandas.eval().
    
    This function replaces unsafe eval() calls by:
    1. Transforming rule format from "(col <= val)" to pandas-compatible format
    2. Using pandas.eval() with local_dict for safe evaluation
    
    Args:
        df: DataFrame to evaluate rule on
        rule: Rule string in format "(col1 <= val1) & (col2 > val2)"
        df_name: Name prefix used in rule (will be stripped)
        
    Returns:
        Boolean Series indicating which rows match the rule
        
    Example:
        >>> rule = "(age <= 30) & (income > 50000)"
        >>> mask = _safe_eval_rule(df, rule)
    """
    # Remove df prefix if present: (df.col <= val) -> (col <= val)
    rule_clean = rule.replace(f'({df_name}.', '(').replace(f'{df_name}[', '[')
    
    # Use pandas.eval() with local_dict for safe evaluation
    try:
        result = pd.eval(rule_clean, local_dict={df_name: df, **{col: df[col] for col in df.columns}})
        if isinstance(result, pd.Series):
            return result
        else:
            # If result is scalar (e.g., all True/False), broadcast to Series
            return pd.Series([bool(result)] * len(df), index=df.index)
    except Exception:
        # Fallback: try DataFrame.eval() method
        try:
            return df.eval(rule_clean)
        except Exception:
            # Last resort: return all False
            return pd.Series([False] * len(df), index=df.index)


def _transform_rule_for_df(rule: str, df_prefix: str = 'df') -> str:
    """
    Transform rule string to add DataFrame prefix for column access.
    
    Args:
        rule: Rule string like "(col <= val)"
        df_prefix: DataFrame variable name to prefix
        
    Returns:
        Transformed rule like "(df['col'] <= val)"
    """
    # Pattern: (column_name operator value)
    # Transform to: (df['column_name'] operator value)
    import re
    
    def replace_column(match: re.Match[str]) -> str:
        col_name = match.group(1)
        operator = match.group(2)
        value = match.group(3)
        return f"({df_prefix}['{col_name}'] {operator} {value})"
    
    # Match pattern: (column_name <= value) or (column_name > value) etc.
    pattern = r'\(([a-zA-Z_][a-zA-Z0-9_]*)\s*(<=|>=|<|>|==|!=)\s*([^)]+)\)'
    return re.sub(pattern, replace_column, rule)


class DataPreprocessor:
    """
    Data preprocessor for rule mining.
    
    Provides comprehensive data preprocessing steps:
    - Feature name mapping (anonymous names to business names)
    - Drop useless columns (ID columns, constant columns, etc.)
    - Datetime column processing (extract year/month/day/hour/days_since features)
    - Text column processing (extract length/word_count/keyword features)
    - One-Hot encoding for categorical variables
    
    This class delegates to the general preprocessing utilities from
    deepanalyze.analysis.preprocessing module.
    
    Attributes:
        id_cols (list[str]): ID columns to drop
        drop_cols (list[str]): Additional columns to drop
        name_mapping (dict[str, str]): Feature name mapping dict
        onehot_indicator (str): Indicator string for One-Hot encoded columns
        datetime_indicator (str): Indicator string for datetime derived columns
        text_indicator (str): Indicator string for text derived columns
    """
    
    def __init__(
        self,
        id_cols: list[str] | None = None,
        drop_cols: list[str] | None = None,
        name_mapping: dict[str, str] | None = None,
        onehot_indicator: str = '_is_',
        datetime_indicator: str = '_dt_',
        text_indicator: str = '_txt_'
    ):
        """
        Initialize DataPreprocessor.
        
        Args:
            id_cols: ID columns to drop (e.g., ['fuuid', 'user_id'])
            drop_cols: Additional columns to drop
            name_mapping: Feature name mapping dict (e.g., {'f0': 'age', 'f1': 'income'})
            onehot_indicator: String indicator for One-Hot encoded columns (default: '_is_')
            datetime_indicator: String indicator for datetime derived columns (default: '_dt_')
            text_indicator: String indicator for text derived columns (default: '_txt_')
        """
        self.id_cols: list[str] = id_cols or []
        self.drop_cols: list[str] = drop_cols or []
        self.name_mapping: dict[str, str] = name_mapping or {}
        self.onehot_indicator: str = onehot_indicator
        self.datetime_indicator: str = datetime_indicator
        self.text_indicator: str = text_indicator
        
        # Initialize general preprocessing utilities
        self._cleaner = ColumnCleaner(id_cols=self.id_cols, drop_cols=self.drop_cols)
        self._datetime_processor = DatetimeProcessor(indicator=datetime_indicator)
        self._text_processor = TextProcessor(indicator=text_indicator)
        self._categorical_processor = CategoricalProcessor(indicator=onehot_indicator)
        
        # State tracking (for backward compatibility)
        self.dropped_cols_: list[str] = []
        self.renamed_cols_: dict[str, str] = {}
        self.onehot_mapping_: dict[str, list[Any]] = {}
        self.constant_cols_: list[str] = []
        self.datetime_cols_: list[str] = []
        self.datetime_derived_: dict[str, list[str]] = {}
        self.text_cols_: list[str] = []
        self.text_derived_: dict[str, list[str]] = {}
    
    def load_name_mapping(
        self,
        mapping_file: str,
        key_col: str = 'feature_code',
        value_col: str = 'feature_name'
    ) -> dict[str, str]:
        """
        Load feature name mapping from CSV file.
        
        Args:
            mapping_file: Path to mapping CSV file
            key_col: Column name for feature codes
            value_col: Column name for feature names
            
        Returns:
            Dict mapping feature codes to feature names
        """
        mapping_df: pd.DataFrame = pd.read_csv(mapping_file)
        self.name_mapping = dict(zip(mapping_df[key_col], mapping_df[value_col]))
        return self.name_mapping
    
    def rename_features(
        self,
        df: pd.DataFrame,
        mapping: dict[str, str] | None = None
    ) -> pd.DataFrame:
        """
        Rename feature columns using mapping dict.
        
        Args:
            df: Input dataframe
            mapping: Feature name mapping dict (uses self.name_mapping if not provided)
            
        Returns:
            DataFrame with renamed columns
        """
        if mapping is None:
            mapping = self.name_mapping
        
        if not mapping:
            return df
        
        # Only rename columns that exist in df
        rename_dict = {k: v for k, v in mapping.items() if k in df.columns}
        self.renamed_cols_ = rename_dict
        
        return df.rename(columns=rename_dict)
    
    def drop_id_columns(
        self,
        df: pd.DataFrame,
        id_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Drop ID columns from dataframe.
        
        Args:
            df: Input dataframe
            id_cols: ID columns to drop (uses self.id_cols if not provided)
            
        Returns:
            Tuple of (processed DataFrame, list of dropped columns)
        """
        if id_cols is None:
            id_cols = self.id_cols
        
        cols_to_drop = [c for c in id_cols if c in df.columns]
        self.dropped_cols_.extend(cols_to_drop)
        
        return df.drop(columns=cols_to_drop, errors='ignore'), cols_to_drop
    
    def drop_constant_columns(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Drop columns with constant values (only one unique value).
        
        Args:
            df: Input dataframe
            exclude_cols: Columns to exclude from checking
            
        Returns:
            Tuple of (processed DataFrame, list of dropped columns)
        """
        exclude_cols = exclude_cols or []
        constant_cols = []
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            if df[col].nunique(dropna=True) <= 1:
                constant_cols.append(col)
        
        self.constant_cols_ = constant_cols
        self.dropped_cols_.extend(constant_cols)
        
        return df.drop(columns=constant_cols, errors='ignore'), constant_cols
    
    def drop_additional_columns(
        self,
        df: pd.DataFrame,
        drop_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Drop additional specified columns.
        
        Args:
            df: Input dataframe
            drop_cols: Columns to drop (uses self.drop_cols if not provided)
            
        Returns:
            Tuple of (processed DataFrame, list of dropped columns)
        """
        if drop_cols is None:
            drop_cols = self.drop_cols
        
        cols_to_drop = [c for c in drop_cols if c in df.columns]
        self.dropped_cols_.extend(cols_to_drop)
        
        return df.drop(columns=cols_to_drop, errors='ignore'), cols_to_drop
    
    def detect_datetime_columns(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> list[str]:
        """
        Auto-detect datetime columns.
        
        Delegates to DatetimeProcessor.detect() from preprocessing module.
        
        Args:
            df: Input dataframe
            exclude_cols: Columns to exclude from detection
            
        Returns:
            List of datetime column names
        """
        return DatetimeProcessor.detect(df, exclude_cols)
    
    def preprocess_datetime(
        self,
        df: pd.DataFrame,
        datetime_cols: list[str] | None = None,
        reference_date: pd.Timestamp | None = None,
        extract_features: list[str] | None = None,
        exclude_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Preprocess datetime columns by extracting numeric features.
        
        Delegates to DatetimeProcessor.extract_features() from preprocessing module.
        
        Args:
            df: Input dataframe
            datetime_cols: Datetime columns to process (auto-detects if None)
            reference_date: Reference date for calculating days_since
            extract_features: Features to extract (year, month, dayofweek, hour, days_since, etc.)
            exclude_cols: Columns to exclude from processing
            
        Returns:
            Tuple of (processed DataFrame, list of new derived column names)
        """
        df_result, new_cols = self._datetime_processor.extract_features(
            df,
            datetime_cols=datetime_cols,
            features=extract_features,
            reference_date=reference_date,
            exclude_cols=exclude_cols,
            drop_original=True
        )
        
        # Update state for backward compatibility
        self.datetime_cols_ = self._datetime_processor.processed_cols_
        self.datetime_derived_ = self._datetime_processor.derived_mapping_
        
        return df_result, new_cols
    
    def detect_text_columns(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None,
        min_unique_ratio: float = 0.5,
        min_avg_length: int = 20
    ) -> list[str]:
        """
        Auto-detect text columns (high cardinality string columns with long values).
        
        Delegates to TextProcessor.detect() from preprocessing module.
        
        Args:
            df: Input dataframe
            exclude_cols: Columns to exclude from detection
            min_unique_ratio: Minimum ratio of unique values to total rows
            min_avg_length: Minimum average string length to consider as text
            
        Returns:
            List of text column names
        """
        return TextProcessor.detect(df, exclude_cols, min_unique_ratio, min_avg_length)
    
    def preprocess_text(
        self,
        df: pd.DataFrame,
        text_cols: list[str] | None = None,
        extract_features: list[str] | None = None,
        keywords: dict[str, list[str]] | None = None,
        exclude_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Preprocess text columns by extracting numeric features.
        
        Delegates to TextProcessor.extract_features() from preprocessing module.
        
        Args:
            df: Input dataframe
            text_cols: Text columns to process (auto-detects if None)
            extract_features: Features to extract (length, word_count, has_digits, etc.)
            keywords: Dict of {feature_name: [keyword_list]} for keyword detection
            exclude_cols: Columns to exclude from processing
            
        Returns:
            Tuple of (processed DataFrame, list of new derived column names)
        """
        df_result, new_cols = self._text_processor.extract_features(
            df,
            text_cols=text_cols,
            features=extract_features,
            keywords=keywords,
            exclude_cols=exclude_cols,
            drop_original=True
        )
        
        # Update state for backward compatibility
        self.text_cols_ = self._text_processor.processed_cols_
        self.text_derived_ = self._text_processor.derived_mapping_
        
        return df_result, new_cols
    
    def detect_categorical_columns(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None,
        max_categories: int = 20
    ) -> list[str]:
        """
        Auto-detect categorical columns.
        
        Delegates to CategoricalProcessor.detect() from preprocessing module.
        
        Args:
            df: Input dataframe
            exclude_cols: Columns to exclude
            max_categories: Maximum unique values to consider as categorical
            
        Returns:
            List of categorical column names
        """
        return CategoricalProcessor.detect(df, exclude_cols, max_categories)
    
    def onehot_encode(
        self,
        df: pd.DataFrame,
        categorical_cols: list[str] | None = None,
        max_categories: int = 50,
        force_categorical: list[str] | None = None,
        force_numeric: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        One-Hot encode categorical variables.
        
        Delegates to CategoricalProcessor.onehot_encode() from preprocessing module.
        
        Args:
            df: Input dataframe
            categorical_cols: Columns to encode (auto-detects if not provided)
            max_categories: Maximum categories per variable (default: 50)
            force_categorical: User-specified columns to force as categorical
            force_numeric: User-specified columns to force as numeric (not encoded)
            
        Returns:
            Tuple of (encoded DataFrame, list of new column names)
        """
        df_result, new_cols = self._categorical_processor.onehot_encode(
            df,
            categorical_cols=categorical_cols,
            max_categories=max_categories,
            force_categorical=force_categorical,
            force_numeric=force_numeric,
            drop_original=True
        )
        
        # Update state for backward compatibility
        self.onehot_mapping_ = self._categorical_processor.encoding_mapping_
        
        return df_result, new_cols
    
    def preprocess(
        self,
        df: pd.DataFrame,
        target_col: str,
        weight_col: str | None = None,
        exclude_cols: list[str] | None = None,
        do_onehot: bool = True,
        do_datetime: bool = True,
        do_text: bool = True,
        categorical_cols: list[str] | None = None,
        force_categorical: list[str] | None = None,
        force_numeric: list[str] | None = None,
        datetime_cols: list[str] | None = None,
        text_cols: list[str] | None = None,
        datetime_features: list[str] | None = None,
        text_features: list[str] | None = None,
        text_keywords: dict[str, list[str]] | None = None,
        progress_callback: ProgressCallback = None
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Run complete data preprocessing.
        
        与评分卡第一阶段保持一致的逻辑：
        - 不删除任何列（ID列、常量列等），只标记需要排除的列
        - 后续阶段（特征工程/规则生成）会根据标记进行筛选
        - 用户指定的排除变量不会进行任何衍生处理（行业惯例）
        
        Steps:
        1. Rename features using mapping
        2. Detect ID columns (mark only, no drop)
        3. Detect constant columns (mark only, no drop)
        4. Detect additional columns to exclude (mark only, no drop)
        5. Preprocess datetime columns (extract year/month/day/hour/days_since)
        6. Preprocess text columns (extract length/word_count/keywords)
        7. One-Hot encode categorical variables (optional)
        
        Args:
            df: Input dataframe
            target_col: Target column name (excluded from processing)
            weight_col: Weight column name (excluded from processing)
            exclude_cols: User-specified columns to exclude from all processing 
                         (including datetime/text derivation). These columns will 
                         not be processed or derived in any way.
            do_onehot: Whether to perform One-Hot encoding (default: True)
            do_datetime: Whether to preprocess datetime columns (default: True)
            do_text: Whether to preprocess text columns (default: True)
            categorical_cols: Categorical columns for One-Hot encoding (auto-detect if None)
            force_categorical: User-specified columns to force as categorical
            force_numeric: User-specified columns to force as numeric (not One-Hot encoded).
                          Use this for ordinal numeric features that might be misdetected as 
                          categorical (e.g., account count, transaction count).
            datetime_cols: Datetime columns to process (auto-detect if None)
            text_cols: Text columns to process (auto-detect if None)
            datetime_features: Datetime features to extract (default: ['year', 'month', 'dayofweek', 'hour', 'days_since'])
            text_features: Text features to extract (default: ['length', 'word_count'])
            text_keywords: Dict of {feature_name: [keyword_list]} for keyword detection
            progress_callback: Progress callback(step, total_steps)
            
        Returns:
            Tuple of (processed DataFrame, preprocessing info dict)
        """
        # 构建完整的排除列列表
        # 包含：目标列 + 权重列 + 用户指定的排除列
        all_exclude_cols: list[str] = [target_col]
        if weight_col:
            all_exclude_cols.append(weight_col)
        if exclude_cols:
            all_exclude_cols.extend([c for c in exclude_cols if c not in all_exclude_cols])
        
        import logging
        logger = logging.getLogger(__name__)
        if exclude_cols:
            logger.info(f"[DataPreprocessor] 用户指定排除列（不进行衍生）: {exclude_cols}")
        if force_numeric:
            logger.info(f"[DataPreprocessor] 用户指定数值列（不进行One-Hot）: {force_numeric}")
        
        total_steps = 7
        df_processed = df.copy()
        
        # Step 1: Rename features
        if progress_callback:
            progress_callback(1, total_steps)
        df_processed = self.rename_features(df_processed)
        
        # Step 2: Detect ID columns (mark only, no drop - 与评分卡一致)
        if progress_callback:
            progress_callback(2, total_steps)
        # 只检测，不删除；返回检测到的ID列列表
        detected_id_cols = self._detect_id_columns(df_processed)
        
        # Step 3: Detect constant columns (mark only, no drop - 与评分卡一致)
        if progress_callback:
            progress_callback(3, total_steps)
        # 只检测，不删除；返回检测到的常量列列表
        detected_constant_cols = self._detect_constant_columns(df_processed, all_exclude_cols)
        
        # Step 4: Detect additional columns to exclude (mark only, no drop - 与评分卡一致)
        if progress_callback:
            progress_callback(4, total_steps)
        # 只检测，不删除；返回需要排除的额外列列表
        detected_additional_cols = list(self.drop_cols) if self.drop_cols else []
        
        # Step 5: Preprocess datetime columns
        # 注意：排除列不进行日期衍生
        datetime_new_cols: list[str] = []
        if do_datetime:
            if progress_callback:
                progress_callback(5, total_steps)
            df_processed, datetime_new_cols = self.preprocess_datetime(
                df_processed,
                datetime_cols=datetime_cols,
                extract_features=datetime_features,
                exclude_cols=all_exclude_cols  # 使用完整的排除列列表
            )
        
        # Step 6: Preprocess text columns
        # 注意：排除列不进行文本衍生（行业惯例）
        text_new_cols: list[str] = []
        if do_text:
            if progress_callback:
                progress_callback(6, total_steps)
            df_processed, text_new_cols = self.preprocess_text(
                df_processed,
                text_cols=text_cols,
                extract_features=text_features,
                keywords=text_keywords,
                exclude_cols=all_exclude_cols  # 使用完整的排除列列表
            )
        
        # Step 7: One-Hot encode (optional)
        onehot_cols: list[str] = []
        if do_onehot:
            if progress_callback:
                progress_callback(7, total_steps)
            df_processed, onehot_cols = self.onehot_encode(
                df_processed, 
                categorical_cols=categorical_cols,
                force_categorical=force_categorical,
                force_numeric=force_numeric  # 用户指定的数值列不进行One-Hot编码
            )
        
        # Build info dict (与评分卡一致，标记检测到的列而非删除的列)
        info = {
            'renamed_cols': self.renamed_cols_,
            # 改为 detected_* 而非 dropped_*，表示只是检测标记
            'detected_id_cols': detected_id_cols,
            'detected_constant_cols': detected_constant_cols,
            'detected_additional_cols': detected_additional_cols,
            # 保留旧字段名以兼容，但值为空（不再删除）
            'dropped_id_cols': [],
            'dropped_constant_cols': [],
            'dropped_additional_cols': [],
            'datetime_cols': self.datetime_cols_,
            'datetime_derived': self.datetime_derived_,
            'datetime_new_cols': datetime_new_cols,
            'text_cols': self.text_cols_,
            'text_derived': self.text_derived_,
            'text_new_cols': text_new_cols,
            'onehot_mapping': self.onehot_mapping_,
            'onehot_new_cols': onehot_cols,
            'total_dropped': 0  # 不再删除列
        }
        
        return df_processed, info
    
    def _detect_id_columns(self, df: pd.DataFrame) -> list[str]:
        """
        Detect ID columns without dropping them.
        
        Args:
            df: Input dataframe
            
        Returns:
            List of detected ID column names
        """
        detected = []
        # 用户指定的ID列
        for col in self.id_cols:
            if col in df.columns:
                detected.append(col)
        return detected
    
    def _detect_constant_columns(
        self, 
        df: pd.DataFrame, 
        exclude_cols: list[str] | None = None
    ) -> list[str]:
        """
        Detect constant columns (columns with only one unique value) without dropping them.
        
        Args:
            df: Input dataframe
            exclude_cols: Columns to exclude from detection
            
        Returns:
            List of detected constant column names
        """
        exclude_cols = exclude_cols or []
        constant_cols = []
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            # Check if column has only one unique value (excluding NaN)
            if df[col].nunique(dropna=True) <= 1:
                constant_cols.append(col)
        
        return constant_cols
    
    @staticmethod
    def assess_data_quality(
        df: pd.DataFrame,
        target_col: str,
        weight_col: str | None = None,
        missing_threshold: float = 0.3,
        high_cardinality_threshold: int = 50,
        low_variance_threshold: float = 0.01
    ) -> dict[str, Any]:
        """
        Assess data quality to determine if feature engineering is needed.
        
        This method analyzes the input data and returns quality metrics that can be used
        to automatically decide whether feature engineering preprocessing should be applied.
        
        Quality checks performed:
        1. Missing rate analysis - columns with high missing rates need imputation/removal
        2. Data type analysis - non-numeric columns need encoding
        3. Cardinality analysis - high cardinality categorical columns may need special handling
        4. Variance analysis - low variance columns provide little information
        5. Target correlation - check if features have reasonable correlation with target
        
        Args:
            df: Input dataframe
            target_col: Target column name
            weight_col: Weight column name (optional)
            missing_threshold: Threshold for flagging high missing rate (default: 0.3)
            high_cardinality_threshold: Threshold for high cardinality (default: 50)
            low_variance_threshold: Threshold for low variance ratio (default: 0.01)
            
        Returns:
            Dict containing:
            - needs_feature_engineering: bool - recommended whether to enable feature engineering
            - quality_score: float - overall quality score (0-100)
            - issues: list[str] - list of detected issues
            - metrics: dict - detailed quality metrics
            - recommendations: list[str] - recommended actions
        """
        exclude_cols = [target_col]
        if weight_col:
            exclude_cols.append(weight_col)
        
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        n_rows = len(df)
        n_features = len(feature_cols)
        
        issues: list[str] = []
        recommendations: list[str] = []
        metrics: dict[str, Any] = {
            'n_rows': n_rows,
            'n_features': n_features,
            'missing_analysis': {},
            'type_analysis': {},
            'cardinality_analysis': {},
            'variance_analysis': {}
        }
        
        # 1. Missing rate analysis
        high_missing_cols: list[str] = []
        any_missing_cols: list[str] = []
        for col in feature_cols:
            missing_rate = df[col].isna().mean()
            if missing_rate > 0:
                any_missing_cols.append(col)
            if missing_rate > missing_threshold:
                high_missing_cols.append(col)
        
        metrics['missing_analysis'] = {
            'cols_with_missing': len(any_missing_cols),
            'cols_high_missing': len(high_missing_cols),
            'high_missing_cols': high_missing_cols[:10],  # Top 10
            'avg_missing_rate': df[feature_cols].isna().mean().mean() if feature_cols else 0
        }
        
        if high_missing_cols:
            issues.append(f"{len(high_missing_cols)}个特征缺失率超过{missing_threshold*100:.0f}%")
            recommendations.append("建议启用特征工程以自动处理高缺失率变量")
        
        # 2. Data type analysis
        numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = [c for c in feature_cols if c not in numeric_cols]
        object_cols = df[feature_cols].select_dtypes(include=['object']).columns.tolist()
        
        metrics['type_analysis'] = {
            'numeric_cols': len(numeric_cols),
            'categorical_cols': len(categorical_cols),
            'object_cols': len(object_cols),
            'numeric_ratio': len(numeric_cols) / n_features if n_features > 0 else 0
        }
        
        if object_cols:
            issues.append(f"{len(object_cols)}个文本/对象类型特征需要编码")
            recommendations.append("建议启用特征工程以自动进行One-Hot编码")
        
        # 3. Cardinality analysis (for categorical columns)
        high_cardinality_cols: list[str] = []
        for col in categorical_cols + object_cols:
            n_unique = df[col].nunique()
            if n_unique > high_cardinality_threshold:
                high_cardinality_cols.append(col)
        
        metrics['cardinality_analysis'] = {
            'high_cardinality_cols': len(high_cardinality_cols),
            'high_cardinality_list': high_cardinality_cols[:10]
        }
        
        if high_cardinality_cols:
            issues.append(f"{len(high_cardinality_cols)}个特征类别数过多(>{high_cardinality_threshold})")
        
        # 4. Variance analysis (for numeric columns)
        low_variance_cols: list[str] = []
        constant_cols: list[str] = []
        for col in numeric_cols:
            col_data = df[col].dropna()
            if len(col_data) == 0:
                continue
            if col_data.nunique() <= 1:
                constant_cols.append(col)
            elif col_data.std() / (col_data.mean() + 1e-10) < low_variance_threshold:
                low_variance_cols.append(col)
        
        metrics['variance_analysis'] = {
            'constant_cols': len(constant_cols),
            'low_variance_cols': len(low_variance_cols),
            'constant_list': constant_cols[:10],
            'low_variance_list': low_variance_cols[:10]
        }
        
        if constant_cols:
            issues.append(f"{len(constant_cols)}个常量特征（只有单一值）")
        
        # 5. Calculate overall quality score
        # Higher score = better quality = less need for feature engineering
        score = 100.0
        
        # Deduct for missing values
        avg_missing = metrics['missing_analysis']['avg_missing_rate']
        score -= min(30, avg_missing * 100)  # Max 30 points deduction
        
        # Deduct for non-numeric columns
        non_numeric_ratio = 1 - metrics['type_analysis']['numeric_ratio']
        score -= min(20, non_numeric_ratio * 40)  # Max 20 points deduction
        
        # Deduct for high cardinality
        if n_features > 0:
            high_card_ratio = len(high_cardinality_cols) / n_features
            score -= min(15, high_card_ratio * 50)  # Max 15 points deduction
        
        # Deduct for constant/low variance columns
        if n_features > 0:
            useless_ratio = (len(constant_cols) + len(low_variance_cols)) / n_features
            score -= min(15, useless_ratio * 50)  # Max 15 points deduction
        
        score = max(0, min(100, score))
        
        # 6. Determine if feature engineering is needed
        # If quality score is below 70, recommend feature engineering
        needs_fe = bool(score < 70 or len(issues) >= 2)  # 显式转换为 Python bool，避免 numpy.bool_ 序列化问题
        
        if needs_fe:
            recommendations.insert(0, f"数据质量评分: {score:.1f}/100，建议启用特征工程预处理")
        else:
            recommendations.insert(0, f"数据质量评分: {score:.1f}/100，数据质量良好，可跳过特征工程")
        
        return {
            'needs_feature_engineering': needs_fe,
            'quality_score': float(round(score, 1)),  # 显式转换为 Python float
            'issues': issues,
            'metrics': metrics,
            'recommendations': recommendations
        }
    
    def check_missing(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Check missing rate for all columns.
        
        Args:
            df: Input dataframe
            exclude_cols: Columns to exclude from checking
            
        Returns:
            DataFrame with columns: variable, missing_count, missing_rate
        """
        exclude_cols = exclude_cols or []
        check_cols = [c for c in df.columns if c not in exclude_cols]
        
        missing_info: list[dict[str, str | int | float]] = []
        for col in check_cols:
            missing_count = int(df[col].isnull().sum())
            missing_rate = missing_count / len(df) if len(df) > 0 else 0.0
            missing_info.append({
                'variable': col,
                'missing_count': missing_count,
                'missing_rate': round(missing_rate, 4)
            })
        
        return pd.DataFrame(missing_info).sort_values('missing_rate', ascending=False)
    
    def detect_outliers(
        self,
        df: pd.DataFrame,
        feature_cols: list[str] | None = None,
        method: str = 'iqr',
        threshold: float = 1.5,
        exclude_cols: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Detect outliers using IQR method (与评分卡一致).
        
        Args:
            df: Input dataframe
            feature_cols: Feature columns to check (defaults to all numeric)
            method: Detection method ('iqr' only for now)
            threshold: IQR multiplier threshold (default: 1.5)
            exclude_cols: Columns to exclude from checking
            
        Returns:
            Dict with outlier information per column:
            - count: Number of outliers
            - percentage: Percentage of outliers
            - lower_bound: Lower bound
            - upper_bound: Upper bound
        """
        exclude_cols = exclude_cols or []
        
        if feature_cols is None:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        else:
            # 过滤掉非数值列，只保留数值类型的列
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [c for c in feature_cols if c in numeric_cols]
        
        feature_cols = [c for c in feature_cols if c not in exclude_cols]
        
        outlier_info: dict[str, Any] = {}
        
        for col in feature_cols:
            col_data = df[col].dropna()
            if len(col_data) == 0:
                continue
            
            if method == 'iqr':
                Q1 = float(col_data.quantile(0.25))
                Q3 = float(col_data.quantile(0.75))
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
                outlier_count = outlier_mask.sum()
                
                outlier_info[col] = {
                    'count': int(outlier_count),
                    'percentage': round(outlier_count / len(df) * 100, 2),
                    'Q1': round(Q1, 4),
                    'Q3': round(Q3, 4),
                    'IQR': round(IQR, 4),
                    'lower_bound': round(lower_bound, 4),
                    'upper_bound': round(upper_bound, 4),
                    'method': 'iqr'
                }
        
        return outlier_info


class FeatureEngineer:
    """
    Feature engineering preprocessor for rule mining.
    
    Provides optional preprocessing steps for raw data:
    - Special value replacement (e.g., -9999 -> NaN)
    - Missing value handling
    - IV calculation and variable pre-selection
    - One-Hot encoding for categorical variables
    
    Note: This is different from scorecard feature engineering which uses WOE encoding.
    Rule mining uses One-Hot encoding because decision trees can handle binary features directly.
    
    Attributes:
        missing_threshold (float): Threshold for missing rate, variables above this are dropped
        iv_threshold (float): Threshold for IV value, variables below this are dropped
        onehot_indicator (str): Indicator string for One-Hot encoded columns
        special_values (list[float]): Values to treat as missing
    """
    
    # Common special values used as missing markers in financial data
    DEFAULT_SPECIAL_VALUES = [-9999, -999, -99999, -998, -9998, -99998]
    
    def __init__(
        self,
        missing_threshold: float = 0.5,
        iv_threshold: float = 0.02,
        onehot_indicator: str = '_is_',
        special_values: list[float] | None = None
    ):
        """
        Initialize FeatureEngineer.
        
        Args:
            missing_threshold: Variables with missing rate above this are dropped (default: 0.5)
            iv_threshold: Variables with IV below this are dropped (default: 0.02)
            onehot_indicator: String indicator for One-Hot encoded columns (default: '_is_')
            special_values: List of values to treat as missing (None = use defaults)
        """
        self.missing_threshold: float = missing_threshold
        self.iv_threshold: float = iv_threshold
        self.onehot_indicator: str = onehot_indicator
        self.special_values: list[float] = special_values if special_values is not None else self.DEFAULT_SPECIAL_VALUES
        self.iv_table_: pd.DataFrame | None = None
        self.dropped_vars_: list[str] = []
        self.dropped_missing_: list[str] = []  # 因缺失率过高被剔除的变量
        self.onehot_mapping_: dict[str, list[Any]] = {}
        self.special_value_report_: dict[str, int] = {}
    
    def replace_special_values(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Replace special values with NaN.
        
        Args:
            df: Input dataframe
            exclude_cols: Columns to exclude from replacement
            
        Returns:
            DataFrame with special values replaced by NaN
        """
        if not self.special_values:
            return df
            
        exclude_cols = exclude_cols or []
        df_result = df.copy()
        
        # Only process numeric columns
        numeric_cols = df_result.select_dtypes(include=[np.number]).columns
        cols_to_process = [c for c in numeric_cols if c not in exclude_cols]
        
        total_replaced = 0
        for col in cols_to_process:
            # Count replacements before
            mask = df_result[col].isin(self.special_values)
            replaced_count = mask.sum()
            if replaced_count > 0:
                df_result.loc[mask, col] = np.nan
                self.special_value_report_[col] = int(replaced_count)
                total_replaced += replaced_count
        
        if total_replaced > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Replaced {total_replaced} special values with NaN in {len(self.special_value_report_)} columns")
        
        return df_result
    
    def check_missing(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Check missing rate for all columns.
        
        Args:
            df: Input dataframe
            exclude_cols: Columns to exclude from checking
            
        Returns:
            DataFrame with columns: variable, missing_count, missing_rate
        """
        exclude_cols = exclude_cols or []
        check_cols = [c for c in df.columns if c not in exclude_cols]
        
        missing_info: list[dict[str, str | int | float]] = []
        for col in check_cols:
            missing_count = df[col].isnull().sum()
            missing_rate = missing_count / len(df)
            missing_info.append({
                'variable': col,
                'missing_count': missing_count,
                'missing_rate': round(missing_rate, 4)
            })
        
        return pd.DataFrame(missing_info).sort_values('missing_rate', ascending=False)
    
    def handle_missing(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Drop variables with missing rate above threshold.
        
        Args:
            df: Input dataframe
            exclude_cols: Columns to exclude from dropping
            
        Returns:
            Tuple of (processed DataFrame, list of dropped columns)
        """
        exclude_cols = exclude_cols or []
        missing_df = self.check_missing(df, exclude_cols)
        
        # Find columns to drop
        high_missing = missing_df[missing_df['missing_rate'] > self.missing_threshold]
        cols_to_drop = [c for c in high_missing['variable'].tolist() if c not in exclude_cols]
        
        # Drop columns
        df_result = df.drop(columns=cols_to_drop)
        self.dropped_vars_.extend(cols_to_drop)
        self.dropped_missing_.extend(cols_to_drop)  # 单独记录因缺失率被剔除的变量
        
        return df_result, cols_to_drop
    
    def calculate_iv(
        self,
        df: pd.DataFrame,
        target_col: str,
        weight_col: str | None = None,
        feature_cols: list[str] | None = None,
        n_bins: int = 10
    ) -> pd.DataFrame:
        """
        Calculate Information Value (IV) for all features.
        
        Uses simple equal-frequency binning for continuous variables.
        
        Args:
            df: Input dataframe
            target_col: Target column name
            weight_col: Sample weight column name (optional)
            feature_cols: Feature columns to calculate IV (optional, defaults to all numeric)
            n_bins: Number of bins for continuous variables
            
        Returns:
            DataFrame with columns: variable, iv, predictive_power
        """
        df_copy = df.copy()
        
        # Set default weight
        if weight_col is None or weight_col not in df_copy.columns:
            df_copy['_weight_'] = 1
            weight_col = '_weight_'
        
        # Determine feature columns
        if feature_cols is None:
            exclude = [target_col, weight_col, '_weight_']
            # Use select_dtypes for robust numeric type detection (handles int32, float32, etc.)
            numeric_cols = df_copy.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [c for c in numeric_cols if c not in exclude]
        
        iv_results: list[dict[str, str | float]] = []
        
        for col in feature_cols:
            try:
                # Bin the variable
                df_temp = df_copy[[col, target_col, weight_col]].dropna()
                
                if pd.Series(df_temp[col]).nunique() <= n_bins:
                    # Categorical or low cardinality
                    df_temp['bin'] = df_temp[col]
                else:
                    # Continuous - use quantile binning
                    df_temp['bin'] = pd.qcut(df_temp[col], q=n_bins, duplicates='drop')
                
                # Calculate WOE and IV
                df_temp_typed: pd.DataFrame = df_temp  # type assertion
                grouped_raw = df_temp_typed.groupby('bin').agg({  # pyright: ignore[reportUnknownMemberType]
                    weight_col: 'sum',
                    target_col: lambda x: (x * df_temp_typed.loc[x.index, weight_col]).sum()
                })
                grouped = grouped_raw.rename(columns={weight_col: 'total', target_col: 'bad'})
                
                grouped['good'] = grouped['total'] - grouped['bad']
                
                total_bad = grouped['bad'].sum()
                total_good = grouped['good'].sum()
                
                if total_bad == 0 or total_good == 0:
                    iv_results.append({'variable': col, 'iv': 0, 'predictive_power': 'None'})
                    continue
                
                grouped['bad_pct'] = grouped['bad'] / total_bad
                grouped['good_pct'] = grouped['good'] / total_good
                
                # Avoid division by zero
                grouped['bad_pct'] = grouped['bad_pct'].replace(0, 0.0001)  # pyright: ignore[reportUnknownMemberType]
                grouped['good_pct'] = grouped['good_pct'].replace(0, 0.0001)  # pyright: ignore[reportUnknownMemberType]
                
                grouped['woe'] = np.log(grouped['bad_pct'] / grouped['good_pct'])
                grouped['iv_bin'] = (grouped['bad_pct'] - grouped['good_pct']) * grouped['woe']
                
                iv = grouped['iv_bin'].sum()
                
                # Determine predictive power
                if iv < 0.02:
                    power = 'Weak'
                elif iv < 0.1:
                    power = 'Medium'
                elif iv < 0.3:
                    power = 'Strong'
                else:
                    power = 'Very Strong'
                
                iv_results.append({
                    'variable': col,
                    'iv': round(iv, 4),
                    'predictive_power': power
                })
                
            except Exception as e:
                iv_results.append({'variable': col, 'iv': 0, 'predictive_power': 'Error'})
        
        self.iv_table_ = pd.DataFrame(iv_results).sort_values('iv', ascending=False)
        return self.iv_table_
    
    def filter_by_iv(
        self,
        df: pd.DataFrame,
        iv_table: pd.DataFrame | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Filter variables by IV threshold.
        
        Args:
            df: Input dataframe
            iv_table: IV table (optional, uses cached if not provided)
            
        Returns:
            Tuple of (filtered DataFrame, list of kept columns)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if iv_table is None:
            iv_table = self.iv_table_
        
        if iv_table is None:
            raise ValueError("IV table not available. Call calculate_iv first.")
        
        # Get variables above threshold
        valid_vars = iv_table[iv_table['iv'] >= self.iv_threshold]['variable'].tolist()
        dropped_vars = iv_table[iv_table['iv'] < self.iv_threshold]['variable'].tolist()
        
        # 添加详细的IV筛选日志
        logger.info(f"[FeatureEngineer] IV筛选统计:")
        logger.info(f"  - IV阈值: {self.iv_threshold}")
        logger.info(f"  - 总特征数: {len(iv_table)}")
        logger.info(f"  - 通过筛选: {len(valid_vars)} ({len(valid_vars)/len(iv_table)*100:.1f}%)")
        logger.info(f"  - 被剔除: {len(dropped_vars)} ({len(dropped_vars)/len(iv_table)*100:.1f}%)")
        
        # 输出IV分布统计
        if len(iv_table) > 0:
            iv_stats = {
                'IV >= 0.1 (Strong)': (iv_table['iv'] >= 0.1).sum(),
                'IV >= 0.05 (Medium-Strong)': ((iv_table['iv'] >= 0.05) & (iv_table['iv'] < 0.1)).sum(),
                'IV >= 0.02 (Medium)': ((iv_table['iv'] >= 0.02) & (iv_table['iv'] < 0.05)).sum(),
                'IV < 0.02 (Weak)': (iv_table['iv'] < 0.02).sum()
            }
            logger.info(f"  - IV分布: {iv_stats}")
            
            # 如果筛选后特征太少，发出警告
            if len(valid_vars) <= 3:
                logger.warning(f"[FeatureEngineer] 警告: IV筛选后只剩{len(valid_vars)}个特征，可能导致规则数量不足！")
                logger.warning(f"  - 建议降低IV阈值（当前: {self.iv_threshold}）或检查数据质量")
                # 输出被剔除的前10个特征（IV最高的）
                if len(dropped_vars) > 0:
                    dropped_df = iv_table[iv_table['variable'].isin(dropped_vars)].head(10)
                    logger.warning(f"  - 被剔除的高IV特征（前10）: {dropped_df[['variable', 'iv']].to_dict('records')}")
        
        self.dropped_vars_.extend(dropped_vars)
        
        # Keep only valid variables (plus any non-feature columns)
        keep_cols = [c for c in df.columns if c in valid_vars or c not in iv_table['variable'].tolist()]
        
        return pd.DataFrame(df[keep_cols]), list(valid_vars)
    
    def onehot_encode(
        self,
        df: pd.DataFrame,
        categorical_cols: list[str] | None = None,
        max_categories: int = 50,
        force_categorical: list[str] | None = None,
        force_numeric: list[str] | None = None,
        exclude_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        One-Hot encode categorical variables.
        
        Uses improved detection logic that identifies:
        - Object/category dtype columns
        - Integer columns with categorical patterns (small range, sparse encoding, etc.)
        - User-specified force_categorical columns
        
        Exclusion logic:
        - Ordinal numeric features (auto-detected)
        - User-specified force_numeric columns
        
        Args:
            df: Input dataframe
            categorical_cols: Columns to encode (optional, auto-detects if None)
            max_categories: Maximum categories per variable (skip if more, default: 50)
            force_categorical: User-specified columns to force as categorical
            force_numeric: User-specified columns to force as numeric (not encoded)
            exclude_cols: Columns to exclude from encoding (e.g., target, weight)
            
        Returns:
            Tuple of (encoded DataFrame, list of new column names)
        """
        from ..preprocessing import CategoricalProcessor
        
        df_result = df.copy()
        new_cols: list[str] = []
        force_categorical = force_categorical or []
        force_numeric = force_numeric or []
        exclude_cols = exclude_cols or []
        
        # Auto-detect categorical columns using improved logic
        if categorical_cols is None:
            categorical_cols = CategoricalProcessor.detect(
                df_result, 
                exclude_cols=exclude_cols, 
                max_categories=max_categories,
                force_categorical=force_categorical,
                force_numeric=force_numeric
            )
        else:
            # Merge user-provided and force_categorical, exclude force_numeric
            categorical_cols = list(set(categorical_cols) | set(force_categorical))
            categorical_cols = [
                c for c in categorical_cols 
                if c in df_result.columns 
                and c not in exclude_cols 
                and c not in force_numeric
            ]
        
        for col in categorical_cols:
            n_unique = df_result[col].nunique()
            
            if n_unique > max_categories:
                # Skip high-cardinality columns
                continue
            
            # Create One-Hot columns
            unique_vals = df_result[col].dropna().unique()
            self.onehot_mapping_[col] = list(unique_vals)
            
            for val in unique_vals:
                new_col = f"{col}{self.onehot_indicator}{val}"
                df_result[new_col] = (df_result[col] == val).astype(int)
                new_cols.append(new_col)
            
            # Drop original column
            df_result = df_result.drop(columns=[col])
        
        return df_result, new_cols
    
    def preprocess(
        self,
        df: pd.DataFrame,
        target_col: str,
        weight_col: str | None = None,
        feature_cols: list[str] | None = None,
        force_categorical: list[str] | None = None,
        force_numeric: list[str] | None = None,
        progress_callback: ProgressCallback = None
    ) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
        """
        Run complete feature engineering preprocessing.
        
        Steps (行业标准顺序):
        1. Replace special values with NaN
        2. Handle missing values
        3. One-Hot encode categorical variables (先编码)
        4. Calculate IV for all features including One-Hot derived columns (再计算IV)
        5. Filter by IV (统一筛选)
        
        Args:
            df: Input dataframe
            target_col: Target column name
            weight_col: Sample weight column name (optional)
            feature_cols: Feature columns to process (if provided, only these columns 
                         will be processed; other columns in df will be excluded from 
                         IV calculation and feature selection)
            force_categorical: User-specified columns to force as categorical
            force_numeric: User-specified columns to force as numeric (not One-Hot encoded)
            progress_callback: Progress callback(step, total_steps)
            
        Returns:
            Tuple of (processed DataFrame, IV table, feature column list)
        """
        exclude_cols = [target_col]
        if weight_col:
            exclude_cols.append(weight_col)
        
        # 构建允许处理的特征列集合
        # 如果指定了 feature_cols，则只处理这些列（及其 One-Hot 衍生列）
        allowed_feature_cols: set[str] | None = None
        if feature_cols is not None:
            allowed_feature_cols = set(feature_cols)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[FeatureEngineer] 使用指定的特征列: {len(allowed_feature_cols)} 个")
        
        total_steps = 5
        
        # Step 1: Replace special values with NaN
        if progress_callback:
            progress_callback(1, total_steps)
        df_processed = self.replace_special_values(df, exclude_cols)
        
        # Step 2: Handle missing values
        if progress_callback:
            progress_callback(2, total_steps)
        df_processed, dropped_missing = self.handle_missing(df_processed, exclude_cols)
        
        # Step 3: One-Hot encode (先编码，再计算IV - 行业标准)
        if progress_callback:
            progress_callback(3, total_steps)
        df_processed, onehot_cols = self.onehot_encode(
            df_processed,
            force_categorical=force_categorical,
            force_numeric=force_numeric,  # 用户指定的数值列不进行One-Hot编码
            exclude_cols=exclude_cols  # Exclude target and weight columns from encoding
        )
        
        # Step 4: Calculate IV for all features (including One-Hot derived columns)
        if progress_callback:
            progress_callback(4, total_steps)
        
        # 获取所有特征列（包括 One-Hot 衍生列）
        exclude_from_iv = set(exclude_cols + ['_weight_'])
        
        # 构建 One-Hot 衍生列集合（用于判断哪些衍生列应该被包含）
        onehot_mapping = getattr(self, 'onehot_mapping_', {}) or {}
        onehot_indicator = getattr(self, 'onehot_indicator', '_is_')
        onehot_derived_cols: set[str] = set()
        for orig_col, unique_values in onehot_mapping.items():
            for val in unique_values:
                derived_col_name = f"{orig_col}{onehot_indicator}{val}"
                onehot_derived_cols.add(derived_col_name)
        
        # 确定要计算 IV 的特征列
        if allowed_feature_cols is not None:
            # 只处理指定的特征列 + 这些特征列产生的 One-Hot 衍生列
            # 衍生列的原始列必须在 allowed_feature_cols 中
            allowed_derived_cols: set[str] = set()
            for orig_col, unique_values in onehot_mapping.items():
                if orig_col in allowed_feature_cols:
                    for val in unique_values:
                        derived_col_name = f"{orig_col}{onehot_indicator}{val}"
                        allowed_derived_cols.add(derived_col_name)
            
            # 特征列 = (指定的原始特征 - 被 One-Hot 删除的) + 允许的衍生列
            onehot_original_cols = set(onehot_mapping.keys())
            remaining_original = allowed_feature_cols - onehot_original_cols
            all_feature_cols = [c for c in df_processed.columns 
                               if c not in exclude_from_iv 
                               and (c in remaining_original or c in allowed_derived_cols)]
        else:
            # 没有指定 feature_cols，处理所有非排除列
            all_feature_cols = [c for c in df_processed.columns if c not in exclude_from_iv]
        
        iv_table = self.calculate_iv(df_processed, target_col, weight_col, all_feature_cols)
        
        # Step 5: Filter by IV (统一筛选所有特征)
        if progress_callback:
            progress_callback(5, total_steps)
        df_processed, valid_vars = self.filter_by_iv(df_processed, iv_table)
        
        # Get final feature columns (exclude target, weight, and internal _weight_ column)
        # 同时确保只返回在允许范围内的特征
        exclude_final = set(exclude_cols + ['_weight_'])
        if allowed_feature_cols is not None:
            # 只返回在允许范围内的特征（原始特征或其衍生列）
            onehot_original_cols = set(onehot_mapping.keys())
            remaining_original = allowed_feature_cols - onehot_original_cols
            allowed_derived_cols_final: set[str] = set()
            for orig_col, unique_values in onehot_mapping.items():
                if orig_col in allowed_feature_cols:
                    for val in unique_values:
                        derived_col_name = f"{orig_col}{onehot_indicator}{val}"
                        allowed_derived_cols_final.add(derived_col_name)
            
            final_feature_cols = [c for c in df_processed.columns 
                                 if c not in exclude_final 
                                 and (c in remaining_original or c in allowed_derived_cols_final)]
        else:
            final_feature_cols = [c for c in df_processed.columns if c not in exclude_final]
        
        return df_processed, iv_table, final_feature_cols


class SingleVarRuleMiner:
    """
    Single variable rule miner.
    
    Generates candidate rules from single variable thresholds without using decision trees.
    This is useful for simple threshold-based rules in risk control scenarios.
    
    Rule format: 
    - Numeric variables: (variable <= threshold) or (variable > threshold)
    - Binary variables (0/1): (variable == 1) - uses equality direction
    
    Attributes:
        n_bins (int): Number of bins for threshold generation
        bin_method (str): Binning method ('quantile', 'uniform', 'custom')
        directions (list[str]): Rule directions to generate ('<=', '>', 'both')
        binary_indicators (list[str]): Indicator strings for binary feature detection
    """
    
    # Default indicator strings for binary features
    DEFAULT_BINARY_INDICATORS: list[str] = ['_is_', '_txt_has_', '_flag_', '_binary_']
    
    def __init__(
        self,
        n_bins: int = 10,
        bin_method: str = 'quantile',
        directions: str = 'both',
        binary_indicators: list[str] | None = None
    ):
        """
        Initialize SingleVarRuleMiner.
        
        Args:
            n_bins: Number of bins for threshold generation (default: 10)
            bin_method: Binning method - 'quantile' (equal frequency), 'uniform' (equal width), 
                       or 'custom' (provide custom thresholds)
            directions: Rule directions - '<=', '>', or 'both' (default: 'both')
            binary_indicators: List of indicator strings for binary feature detection
                              (default: ['_is_', '_txt_has_', '_flag_', '_binary_'])
        """
        self.n_bins: int = n_bins
        self.bin_method: str = bin_method
        self.directions: str = directions
        self.binary_indicators: list[str] = binary_indicators or self.DEFAULT_BINARY_INDICATORS
    
    def is_binary_feature(
        self,
        col_name: str,
        series: pd.Series | None = None
    ) -> bool:
        """
        Detect if a feature is binary (0/1 values only).
        
        Detection is based on:
        1. Column name contains binary indicator strings (e.g., '_is_', '_txt_has_')
        2. Data values are only 0 and 1 (if series provided)
        
        Args:
            col_name: Column name to check
            series: Optional series data for value-based detection
            
        Returns:
            True if the feature is binary
        """
        # Check by indicator strings in column name
        for indicator in self.binary_indicators:
            if indicator in col_name:
                return True
        
        # Check by data values if series provided
        if series is not None:
            unique_vals = series.dropna().unique()
            if len(unique_vals) <= 2:
                # Check if values are 0/1 or True/False
                val_set = set(unique_vals)
                if val_set <= {0, 1, 0.0, 1.0, True, False}:
                    return True
        
        return False
    
    def detect_binary_features(
        self,
        df: pd.DataFrame,
        feature_cols: list[str]
    ) -> tuple[list[str], list[str]]:
        """
        Separate features into binary and non-binary groups.
        
        Args:
            df: Input dataframe
            feature_cols: List of feature column names
            
        Returns:
            Tuple of (binary_cols, numeric_cols)
        """
        binary_cols: list[str] = []
        numeric_cols: list[str] = []
        
        for col in feature_cols:
            if col not in df.columns:
                continue
            if self.is_binary_feature(col, df[col]):
                binary_cols.append(col)
            else:
                numeric_cols.append(col)
        
        return binary_cols, numeric_cols
    
    def _get_thresholds(
        self,
        series: pd.Series,
        target: pd.Series | None = None,
        custom_thresholds: list[float] | None = None
    ) -> list[float]:
        """
        Get threshold values for a variable.
        
        Args:
            series: Variable values
            target: Target variable (required for chi2 and tree methods)
            custom_thresholds: Custom threshold list (for bin_method='custom')
            
        Returns:
            List of threshold values
        """
        if self.bin_method == 'custom' and custom_thresholds:
            return sorted(custom_thresholds)
        
        # Remove nulls
        valid_values = series.dropna()
        
        if len(valid_values) == 0:
            return []
        
        if self.bin_method == 'quantile':
            # Equal frequency binning
            try:
                quantiles = np.linspace(0, 1, self.n_bins + 1)[1:-1]
                thresholds_arr = np.quantile(valid_values, quantiles)
                thresholds: list[float] = sorted(set(float(x) for x in np.round(thresholds_arr, 4)))
            except Exception:
                thresholds = []
        elif self.bin_method == 'uniform':
            # Equal width binning
            min_val, max_val = valid_values.min(), valid_values.max()
            if min_val == max_val:
                return []
            thresholds_arr = np.linspace(min_val, max_val, self.n_bins + 1)[1:-1]
            thresholds = sorted(set(float(x) for x in np.round(thresholds_arr, 4)))
        elif self.bin_method == 'chi2':
            # Chi-square binning (supervised)
            thresholds = self._chi2_binning(series, target)
        elif self.bin_method == 'tree':
            # Decision tree optimal binning (supervised)
            thresholds = self._tree_binning(series, target)
        else:
            thresholds = []
        
        return list(thresholds)
    
    def _chi2_binning(
        self,
        series: pd.Series,
        target: pd.Series | None
    ) -> list[float]:
        """
        Chi-square based binning (卡方分箱).
        
        Merges adjacent bins with similar target distribution based on chi-square test.
        
        Args:
            series: Feature values
            target: Target variable (0/1)
            
        Returns:
            List of threshold values
        """
        if target is None:
            # Fallback to quantile if no target
            quantiles = np.linspace(0, 1, self.n_bins + 1)[1:-1]
            thresholds_arr = np.quantile(series.dropna(), quantiles)
            return sorted(set(float(x) for x in np.round(thresholds_arr, 4)))
        
        # Align series and target (remove nulls)
        mask = series.notna() & target.notna()
        x = series[mask].values
        y = target[mask].values
        
        if len(x) < self.n_bins * 2:
            # Not enough data, fallback to quantile
            quantiles = np.linspace(0, 1, self.n_bins + 1)[1:-1]
            thresholds_arr = np.quantile(x, quantiles)
            return sorted(set(float(x) for x in np.round(thresholds_arr, 4)))
        
        # Initial fine-grained binning (more bins than target)
        initial_bins = min(100, len(np.unique(x)))
        try:
            quantiles = np.linspace(0, 1, initial_bins + 1)
            bin_edges = np.unique(np.quantile(x, quantiles))
        except Exception:
            return []
        
        if len(bin_edges) < 3:
            return []
        
        # Assign each sample to a bin
        bin_indices = np.digitize(x, bin_edges[1:-1])
        
        # Calculate frequency table for each bin
        n_initial_bins = len(bin_edges) - 1
        freq_table = []
        for i in range(n_initial_bins):
            mask_bin = bin_indices == i
            n_total = np.sum(mask_bin)
            n_bad = np.sum(y[mask_bin]) if n_total > 0 else 0
            n_good = n_total - n_bad
            freq_table.append([n_good, n_bad])
        
        # Merge bins using chi-square criterion until reaching target bin count
        while len(freq_table) > self.n_bins:
            # Calculate chi-square for adjacent bin pairs
            chi2_values = []
            for i in range(len(freq_table) - 1):
                chi2_val = self._calc_chi2(freq_table[i], freq_table[i + 1])
                chi2_values.append(chi2_val)
            
            if not chi2_values:
                break
            
            # Find pair with minimum chi-square (most similar)
            min_idx = int(np.argmin(chi2_values))
            
            # Merge bins
            freq_table[min_idx] = [
                freq_table[min_idx][0] + freq_table[min_idx + 1][0],
                freq_table[min_idx][1] + freq_table[min_idx + 1][1]
            ]
            freq_table.pop(min_idx + 1)
            bin_edges = np.delete(bin_edges, min_idx + 1)
        
        # Return internal edges as thresholds
        thresholds = sorted(set(float(x) for x in np.round(bin_edges[1:-1], 4)))
        return thresholds
    
    def _calc_chi2(self, freq1: list[int], freq2: list[int]) -> float:
        """
        Calculate chi-square statistic for two bins.
        
        Args:
            freq1: [n_good, n_bad] for bin 1
            freq2: [n_good, n_bad] for bin 2
            
        Returns:
            Chi-square statistic
        """
        n1 = freq1[0] + freq1[1]
        n2 = freq2[0] + freq2[1]
        n_total = n1 + n2
        
        if n_total == 0:
            return float('inf')
        
        # Expected frequencies
        n_good_total = freq1[0] + freq2[0]
        n_bad_total = freq1[1] + freq2[1]
        
        if n_good_total == 0 or n_bad_total == 0:
            return float('inf')
        
        expected = [
            [n1 * n_good_total / n_total, n1 * n_bad_total / n_total],
            [n2 * n_good_total / n_total, n2 * n_bad_total / n_total]
        ]
        
        chi2 = 0.0
        observed = [freq1, freq2]
        for i in range(2):
            for j in range(2):
                if expected[i][j] > 0:
                    chi2 += (observed[i][j] - expected[i][j]) ** 2 / expected[i][j]
        
        return chi2
    
    def _tree_binning(
        self,
        series: pd.Series,
        target: pd.Series | None
    ) -> list[float]:
        """
        Decision tree based optimal binning (决策树最佳分箱).
        
        Uses a single-variable decision tree to find optimal split points.
        
        Args:
            series: Feature values
            target: Target variable (0/1)
            
        Returns:
            List of threshold values
        """
        if target is None:
            # Fallback to quantile if no target
            quantiles = np.linspace(0, 1, self.n_bins + 1)[1:-1]
            thresholds_arr = np.quantile(series.dropna(), quantiles)
            return sorted(set(float(x) for x in np.round(thresholds_arr, 4)))
        
        # Align series and target (remove nulls)
        mask = series.notna() & target.notna()
        x = series[mask].values.reshape(-1, 1)
        y = target[mask].values
        
        if len(x) < self.n_bins * 2:
            # Not enough data, fallback to quantile
            quantiles = np.linspace(0, 1, self.n_bins + 1)[1:-1]
            thresholds_arr = np.quantile(x.flatten(), quantiles)
            return sorted(set(float(t) for t in np.round(thresholds_arr, 4)))
        
        # Train a decision tree with limited depth
        # max_leaf_nodes controls the number of bins
        dt = tree.DecisionTreeClassifier(
            max_leaf_nodes=self.n_bins,
            min_samples_leaf=max(1, int(len(x) * 0.01)),  # At least 1% samples per leaf
            random_state=42
        )
        
        try:
            dt.fit(x, y)
        except Exception:
            # Fallback to quantile
            quantiles = np.linspace(0, 1, self.n_bins + 1)[1:-1]
            thresholds_arr = np.quantile(x.flatten(), quantiles)
            return sorted(set(float(t) for t in np.round(thresholds_arr, 4)))
        
        # Extract thresholds from tree
        thresholds_set: set[float] = set()
        
        def extract_thresholds(node_id: int = 0) -> None:
            """Recursively extract split thresholds from tree."""
            if dt.tree_.feature[node_id] != -2:  # -2 means leaf node
                threshold = float(dt.tree_.threshold[node_id])
                thresholds_set.add(round(threshold, 4))
                # Recurse to children
                left_child = dt.tree_.children_left[node_id]
                right_child = dt.tree_.children_right[node_id]
                if left_child != -1:
                    extract_thresholds(left_child)
                if right_child != -1:
                    extract_thresholds(right_child)
        
        extract_thresholds()
        
        return sorted(thresholds_set)
    
    def generate_rules(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        target_col: str,
        weight_col: str | None = None,
        custom_thresholds: dict[str, list[float]] | None = None,
        var_name_dict: dict[str, str] | None = None,
        progress_callback: ProgressCallback = None
    ) -> pd.DataFrame:
        """
        Generate single variable rules from all features.
        
        Automatically detects binary features and uses equality direction (==) for them,
        while using comparison directions (<=, >) for numeric features.
        
        Args:
            df: Input dataframe
            feature_cols: List of feature column names
            target_col: Target column name
            weight_col: Sample weight column name (optional, None for no weighting)
            custom_thresholds: Dict of custom thresholds per variable
            var_name_dict: Optional dict for variable name mapping
            progress_callback: Optional callback function(current, total) for progress
            
        Returns:
            DataFrame with columns: used_var, rule, threshold, direction
        """
        custom_thresholds = custom_thresholds or {}
        rules = []
        
        total_features = len(feature_cols)
        
        # Detect binary features
        binary_cols, numeric_cols = self.detect_binary_features(df, feature_cols)
        
        for idx, col in enumerate(feature_cols):
            # Skip non-numeric columns (use robust numeric type detection)
            if not pd.api.types.is_numeric_dtype(df[col]):
                continue
            
            # Check if this is a binary feature
            if col in binary_cols:
                # Binary feature: use equality direction (== 1)
                rule = f"({col} == 1)"
                rule_info: dict[str, Any] = {
                    'used_var': col,
                    'rule': rule,
                    'threshold': 1,
                    'direction': '=='
                }
                if var_name_dict and col in var_name_dict:
                    rule_info['rule_chinese'] = f"({var_name_dict[col]} == 1)"
                rules.append(rule_info)
            else:
                # Numeric feature: use comparison directions
                # Get thresholds (pass target for supervised binning methods)
                thresholds = self._get_thresholds(
                    df[col],
                    df[target_col] if self.bin_method in ['chi2', 'tree'] else None,
                    custom_thresholds.get(col)
                )
                
                # Generate rules for each threshold
                for threshold in thresholds:
                    if self.directions in ['<=', 'both']:
                        rule = f"({col} <= {threshold})"
                        rule_info = {
                            'used_var': col,
                            'rule': rule,
                            'threshold': threshold,
                            'direction': '<='
                        }
                        if var_name_dict and col in var_name_dict:
                            rule_info['rule_chinese'] = f"({var_name_dict[col]} <= {threshold})"
                        rules.append(rule_info)
                    
                    if self.directions in ['>', 'both']:
                        rule = f"({col} > {threshold})"
                        rule_info = {
                            'used_var': col,
                            'rule': rule,
                            'threshold': threshold,
                            'direction': '>'
                        }
                        if var_name_dict and col in var_name_dict:
                            rule_info['rule_chinese'] = f"({var_name_dict[col]} > {threshold})"
                        rules.append(rule_info)
            
            if progress_callback:
                progress_callback(idx + 1, total_features)
        
        if not rules:
            return pd.DataFrame(columns=['used_var', 'rule', 'threshold', 'direction'])
        
        rule_df = pd.DataFrame(rules)
        
        # Remove duplicates
        rule_df = rule_df.drop_duplicates(['rule']).reset_index(drop=True)
        
        return rule_df
    
    def generate_categorical_rules(
        self,
        df: pd.DataFrame,
        categorical_cols: list[str],
        target_col: str,
        weight_col: str | None = None,
        var_name_dict: dict[str, str] | None = None,
        progress_callback: ProgressCallback = None
    ) -> pd.DataFrame:
        """
        Generate rules for categorical variables (equality rules).
        
        Args:
            df: Input dataframe
            categorical_cols: List of categorical column names
            target_col: Target column name
            weight_col: Sample weight column name
            var_name_dict: Optional dict for variable name mapping
            progress_callback: Optional callback function(current, total) for progress
            
        Returns:
            DataFrame with categorical rules
        """
        rules = []
        total_cols = len(categorical_cols)
        
        for idx, col in enumerate(categorical_cols):
            unique_vals = df[col].dropna().unique()
            
            for val in unique_vals:
                # For string values, add quotes
                if isinstance(val, str):
                    rule = f"({col} == '{val}')"
                    rule_display = f"({var_name_dict.get(col, col)} == '{val}')" if var_name_dict else None
                else:
                    rule = f"({col} == {val})"
                    rule_display = f"({var_name_dict.get(col, col)} == {val})" if var_name_dict else None
                
                rule_info = {
                    'used_var': col,
                    'rule': rule,
                    'threshold': val,
                    'direction': '=='
                }
                if rule_display:
                    rule_info['rule_chinese'] = rule_display
                rules.append(rule_info)
            
            if progress_callback:
                progress_callback(idx + 1, total_cols)
        
        if not rules:
            return pd.DataFrame(columns=['used_var', 'rule', 'threshold', 'direction'])
        
        return pd.DataFrame(rules).drop_duplicates(['rule']).reset_index(drop=True)
    
    def filter_by_direction(
        self,
        rule_df: pd.DataFrame,
        direction_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Filter single variable rules by expected direction.
        
        Args:
            rule_df: DataFrame with rules
            direction_df: DataFrame with expected directions per variable
            
        Returns:
            Filtered rules DataFrame
        """
        if direction_df is None or direction_df.empty:
            return rule_df
        
        # Build direction lookup
        dir_lookup = dict(zip(direction_df['var'], direction_df['direction']))
        
        # 使用向量化操作替代iterrows以提高性能
        def should_keep_rule(row: pd.Series) -> bool:
            var = row['used_var']
            rule_dir = row['direction']
            
            # If variable has expected direction, filter by it
            if var in dir_lookup:
                expected_dir = dir_lookup[var]
                # Binary features (==) always pass through
                # Or rule direction matches expected direction
                return rule_dir == '==' or expected_dir == '==' or rule_dir == expected_dir
            else:
                # No direction constraint, keep all
                return True
        
        mask = rule_df.apply(should_keep_rule, axis=1)
        filtered_df = rule_df[mask].reset_index(drop=True)
        
        return filtered_df


class RuleMiner:
    """
    Decision tree based rule miner.
    
    Generates candidate rules from multi-variable decision trees and determines
    feature split directions for rule filtering.
    
    Attributes:
        min_samples_leaf (float): Minimum samples ratio for leaf nodes (default: 0.01)
        max_depth (int): Maximum depth of decision tree (default: 5)
        n_vars (int): Number of variables per combination (default: 3)
        max_onehot_vars (int): Maximum one-hot encoded variables per combination (default: 2)
    """
    
    def __init__(
        self,
        min_samples_leaf: float = 0.01,
        max_depth: int = 5,
        n_vars: int = 3,
        max_onehot_vars: int = 2
    ):
        """
        Initialize RuleMiner.
        
        Args:
            min_samples_leaf: Minimum samples ratio for leaf nodes
            max_depth: Maximum depth of decision tree
            n_vars: Number of variables per combination
            max_onehot_vars: Maximum one-hot encoded variables per combination
        """
        self.min_samples_leaf: float = min_samples_leaf
        self.max_depth: int = max_depth
        self.n_vars: int = n_vars
        self.max_onehot_vars: int = max_onehot_vars
        # 保存最后训练的决策树（用于可视化）
        self.last_tree_: Any = None
        self.last_tree_features_: list[str] = []
        # One-Hot 映射信息（用于规则可读性转换）
        self.onehot_mapping_: dict[str, list[Any]] = {}  # {原始列: [唯一值列表]}
        self.onehot_indicator_: str = '_is_'  # One-Hot 指示符
    
    def set_onehot_mapping(
        self,
        onehot_mapping: dict[str, list[Any]],
        onehot_indicator: str = '_is_'
    ) -> None:
        """
        Set One-Hot encoding mapping for rule readability conversion.
        
        Args:
            onehot_mapping: Mapping of original column to unique values
                           e.g., {'f67': ['Visa', 'Mastercard', ...]}
            onehot_indicator: Indicator string used in One-Hot column names (default: '_is_')
        """
        self.onehot_mapping_ = onehot_mapping or {}
        self.onehot_indicator_ = onehot_indicator
    
    def _convert_onehot_condition(self, condition: str) -> str:
        """
        Convert One-Hot encoded condition to human-readable form.
        
        Examples:
            (f67_is_Visa <= 0.5) -> (f67 != 'Visa')
            (f67_is_Visa > 0.5)  -> (f67 == 'Visa')
            (f74_is_1 <= 0.5)    -> (f74 != 1)
            (f74_is_1 > 0.5)     -> (f74 == 1)
        
        Args:
            condition: Original condition string like "(f67_is_Visa <= 0.5)"
            
        Returns:
            Human-readable condition or original if not One-Hot
        """
        import re
        
        # 构建 One-Hot 衍生列到原始列和值的映射
        if not self.onehot_mapping_:
            return condition
        
        # 尝试匹配 One-Hot 条件模式
        # 模式: (feature_name <= threshold) 或 (feature_name > threshold)
        pattern = r'\(([^\s]+)\s*(<=|>)\s*([0-9.]+)\)'
        match = re.match(pattern, condition.strip())
        
        if not match:
            return condition
        
        feature_name = match.group(1)
        operator = match.group(2)
        threshold = float(match.group(3))
        
        # 检查是否是 One-Hot 衍生列
        for orig_col, unique_values in self.onehot_mapping_.items():
            for val in unique_values:
                derived_name = f"{orig_col}{self.onehot_indicator_}{val}"
                if feature_name == derived_name:
                    # 找到匹配的 One-Hot 衍生列
                    # 对于二值特征（0/1），阈值通常是 0.5
                    # <= 0.5 表示值为 0，即不等于该类别
                    # > 0.5 表示值为 1，即等于该类别
                    if threshold == 0.5 or (0.4 <= threshold <= 0.6):
                        if operator == '<=':
                            # 值为 0，不等于该类别
                            val_str = f"'{val}'" if isinstance(val, str) else str(val)
                            return f"({orig_col} != {val_str})"
                        else:  # operator == '>'
                            # 值为 1，等于该类别
                            val_str = f"'{val}'" if isinstance(val, str) else str(val)
                            return f"({orig_col} == {val_str})"
                    else:
                        # 非标准阈值，保持原样但添加注释
                        val_str = f"'{val}'" if isinstance(val, str) else str(val)
                        if operator == '<=':
                            return f"({orig_col} != {val_str})"  # 仍然转换，因为二值特征
                        else:
                            return f"({orig_col} == {val_str})"
        
        # 不是 One-Hot 衍生列，返回原样
        return condition
    
    def convert_rule_to_readable(self, rule: str) -> str:
        """
        Convert entire rule string to human-readable form.
        
        Args:
            rule: Rule string like "(f67_is_Visa <= 0.5) & (f74_is_1 > 0.5)"
            
        Returns:
            Human-readable rule like "(f67 != 'Visa') & (f74 == 1)"
        """
        if not rule or not self.onehot_mapping_:
            return rule
        
        # 分割规则为单个条件
        conditions = rule.split(' & ')
        readable_conditions = []
        
        for cond in conditions:
            readable_cond = self._convert_onehot_condition(cond.strip())
            readable_conditions.append(readable_cond)
        
        return ' & '.join(readable_conditions)
    
    def _get_rules_from_tree(
        self,
        df: pd.DataFrame,
        x_ls: list[str],
        target: str,
        weight: str,
        if_all_nodes: bool = False,
        var_name_dict: dict[str, str] | None = None
    ) -> pd.DataFrame:
        """
        Extract rules from decision tree nodes using tree_ structure traversal.
        
        Args:
            df: Input dataframe
            x_ls: List of feature names
            target: Target column name
            weight: Sample weight column name
            if_all_nodes: If True, extract from all nodes; if False, only leaf nodes
            var_name_dict: Optional dict for variable name mapping (to Chinese etc.)
            
        Returns:
            DataFrame with columns: used_var, rule, [rule_chinese]
        """
        import logging
        logger = logging.getLogger(__name__)
        
        df_copy = df.copy()
        
        # Build decision tree
        # min_samples_leaf supports float (ratio) in sklearn, but type stubs only show int
        min_leaf = int(len(df_copy) * self.min_samples_leaf) if self.min_samples_leaf < 1 else int(self.min_samples_leaf)
        min_leaf = max(1, min_leaf)  # Ensure at least 1 sample
        
        # 计算 min_samples_split：至少是 min_samples_leaf 的 2 倍，确保能够分裂
        min_split = max(2, min_leaf * 2)
        
        # 添加调试日志（改为info级别）
        logger.info(f"[_get_rules_from_tree] Building tree with: samples={len(df_copy)}, "
                    f"features={len(x_ls)}, min_leaf={min_leaf}, min_split={min_split}, max_depth={self.max_depth}")
        
        clf = tree.DecisionTreeClassifier(
            random_state=312,
            min_samples_leaf=min_leaf,
            min_samples_split=min_split,
            max_depth=self.max_depth
        ).fit(
            df_copy.loc[:, x_ls],
            df_copy[target],
            sample_weight=np.asarray(df_copy[weight].values)
        )
        
        # 添加调试日志（改为info级别以便诊断）
        logger.info(f"[_get_rules_from_tree] Tree built: actual_depth={clf.get_depth()}, leaves={clf.get_n_leaves()}, "
                   f"max_depth_param={self.max_depth}, min_leaf_param={self.min_samples_leaf}, min_leaf_actual={min_leaf}, min_split={min_split}")
        
        # 如果树深度异常浅，输出更多诊断信息
        if clf.get_depth() <= 1 and self.max_depth > 1:
            tree_ = clf.tree_
            logger.warning(f"[_get_rules_from_tree] Tree is unexpectedly shallow! Diagnostics:")
            logger.warning(f"  - Root node samples: {tree_.n_node_samples[0]}")
            logger.warning(f"  - Root node impurity: {tree_.impurity[0]:.4f}")
            if tree_.children_left[0] != -1:  # 有子节点
                left_child = tree_.children_left[0]
                right_child = tree_.children_right[0]
                logger.warning(f"  - Left child samples: {tree_.n_node_samples[left_child]}, impurity: {tree_.impurity[left_child]:.4f}")
                logger.warning(f"  - Right child samples: {tree_.n_node_samples[right_child]}, impurity: {tree_.impurity[right_child]:.4f}")
                logger.warning(f"  - Split feature: {x_ls[tree_.feature[0]]}, threshold: {tree_.threshold[0]:.4f}")
        
        # 保存决策树用于可视化
        self.last_tree_ = clf
        self.last_tree_features_ = x_ls.copy()
        
        # Extract rules using tree_ structure traversal (more reliable than text parsing)
        tree_ = clf.tree_
        rule_ls: list[str] = []
        
        def recurse(node_id: int, conditions: list[str]) -> None:
            """Recursively traverse tree and extract rules."""
            # Check if leaf node (feature[node] == TREE_UNDEFINED == -2)
            if tree_.feature[node_id] == -2:
                # Leaf node: save rule if conditions exist
                if conditions:
                    rule = " & ".join(conditions)
                    rule_ls.append(rule)
                return
            
            # Internal node: get feature name and threshold
            feature_idx = tree_.feature[node_id]
            feature_name = x_ls[feature_idx]
            threshold = tree_.threshold[node_id]
            
            # Format threshold (avoid scientific notation for small numbers)
            if abs(threshold) < 0.0001 and threshold != 0:
                thresh_str = f"{threshold:.6f}"
            else:
                thresh_str = f"{threshold:.4f}".rstrip('0').rstrip('.')
            
            # Left child: feature <= threshold
            left_condition = f"({feature_name} <= {thresh_str})"
            left_child = tree_.children_left[node_id]
            
            # Right child: feature > threshold
            right_condition = f"({feature_name} > {thresh_str})"
            right_child = tree_.children_right[node_id]
            
            if if_all_nodes:
                # Extract rule for current internal node
                if conditions:
                    rule_ls.append(" & ".join(conditions + [left_condition]))
                    rule_ls.append(" & ".join(conditions + [right_condition]))
                else:
                    rule_ls.append(left_condition)
                    rule_ls.append(right_condition)
            
            # Recurse to children
            recurse(left_child, conditions + [left_condition])
            recurse(right_child, conditions + [right_condition])
        
        # Start recursion from root node (node_id=0)
        recurse(0, [])
        
        # Generate human-readable rules (convert One-Hot conditions)
        rule_readable_ls: list[str] = []
        for rule in rule_ls:
            readable_rule = self.convert_rule_to_readable(rule)
            rule_readable_ls.append(readable_rule)
        
        # Generate Chinese rules if mapping provided
        rule_chi_ls: list[str] = []
        if var_name_dict:
            # 对可读规则进行中文变量名替换
            for rule in rule_readable_ls:
                rule_chi = rule
                # 替换原始变量名（One-Hot 转换后的）
                for orig_col in self.onehot_mapping_.keys():
                    if orig_col in var_name_dict:
                        rule_chi = rule_chi.replace(f"({orig_col} ", f"({var_name_dict[orig_col]} ")
                # 替换普通变量名
                for var in x_ls:
                    if var in var_name_dict:
                        rule_chi = rule_chi.replace(var, var_name_dict[var])
                rule_chi_ls.append(rule_chi)
        
        # 构建返回 DataFrame
        result_df = pd.DataFrame({
            'used_var': [' & '.join(x_ls)] * len(rule_ls),
            'rule': rule_ls,  # 原始规则（技术形式）
            'rule_readable': rule_readable_ls,  # 可读规则（One-Hot 转换后）
        })
        
        if var_name_dict:
            result_df['rule_chinese'] = rule_chi_ls
        
        return result_df
    
    def generate_rules(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        target_col: str,
        weight_col: str | None = None,
        onehot_indicator: str = '_is_',
        var_name_dict: dict[str, str] | None = None,
        progress_callback: ProgressCallback = None
    ) -> pd.DataFrame:
        """
        Generate candidate rules from all variable combinations.
        
        Args:
            df: Input dataframe with features, target and weight
            feature_cols: List of feature column names
            target_col: Target column name
            weight_col: Sample weight column name (optional, None for no weighting)
            onehot_indicator: String indicator for one-hot encoded columns
            var_name_dict: Optional dict for variable name mapping
            progress_callback: Optional callback function(current, total) for progress
            
        Returns:
            DataFrame with all generated rules
        """
        df_dev = df.copy()
        
        # Handle weight column - create default if not provided
        actual_weight_col: str
        if weight_col is None or weight_col not in df_dev.columns:
            df_dev['_weight_'] = 1
            actual_weight_col = '_weight_'
        else:
            actual_weight_col = weight_col
        
        var_ls = feature_cols
        
        # Calculate total combinations
        total_combinations = 0
        for combo in combinations(range(len(var_ls)), self.n_vars):
            vars_in_combo = [var_ls[i] for i in combo]
            onehot_count = sum(1 for v in vars_in_combo if onehot_indicator in v)
            if onehot_count <= self.max_onehot_vars:
                total_combinations += 1
        
        # Generate rules from all combinations
        rule_df = pd.DataFrame()
        processed = 0
        
        for combo in combinations(range(len(var_ls)), self.n_vars):
            vars_in_combo = [var_ls[i] for i in combo]
            
            # Skip combinations with too many one-hot variables
            onehot_count = sum(1 for v in vars_in_combo if onehot_indicator in v)
            if onehot_count > self.max_onehot_vars:
                continue
            
            # Prepare data
            df_subset = df_dev[[target_col, actual_weight_col] + vars_in_combo].dropna()
            
            # Generate rules from decision tree
            try:
                res = self._get_rules_from_tree(
                    df_subset,
                    vars_in_combo,
                    target=target_col,
                    weight=actual_weight_col,
                    var_name_dict=var_name_dict
                )
                rule_df = pd.concat([rule_df, res], ignore_index=True)
            except Exception as e:
                # Skip failed combinations
                pass
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total_combinations)
        
        # Remove duplicates
        rule_df = rule_df.drop_duplicates(['rule']).reset_index(drop=True)
        
        return rule_df
    
    def get_split_direction(
        self,
        df: pd.DataFrame,
        target_col: str,
        weight_col: str | None = None,
        skip_cols: list[str] | None = None,
        min_samples_leaf: float = 0.02,
        max_depth: int = 3,
        binary_indicators: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Determine feature split direction using single-variable decision trees.
        
        Binary features (0/1 values) are automatically detected and assigned '==' direction
        instead of using decision tree inference, as <= / > directions are meaningless for them.
        
        Args:
            df: Input dataframe
            target_col: Target column name
            weight_col: Sample weight column name (optional, None for no weighting)
            skip_cols: Columns to skip
            min_samples_leaf: Minimum samples ratio for direction tree
            max_depth: Maximum depth for direction tree
            binary_indicators: Indicator strings for binary feature detection
                              (default: ['_is_', '_txt_has_', '_flag_', '_binary_'])
            
        Returns:
            DataFrame with columns: var, cutoff, badRate, pct, lift, direction
        """
        # Default binary indicators
        if binary_indicators is None:
            binary_indicators = ['_is_', '_txt_has_', '_flag_', '_binary_']
        
        def is_binary_feature(col_name: str, series: pd.Series) -> bool:
            """Check if a feature is binary (0/1 values only)."""
            # Check by indicator strings
            for indicator in binary_indicators:
                if indicator in col_name:
                    return True
            # Check by data values
            unique_vals = series.dropna().unique()
            if len(unique_vals) <= 2:
                val_set = set(unique_vals)
                if val_set <= {0, 1, 0.0, 1.0, True, False}:
                    return True
            return False
        
        def get_split_point(x, target, weight, min_samples_leaf, max_depth):
            clf = tree.DecisionTreeClassifier(
                random_state=312,
                min_samples_leaf=min_samples_leaf,
                max_depth=max_depth
            ).fit(x, target, sample_weight=weight)
            
            # Access tree internals (not covered by type stubs)
            tree_obj: Any = clf.tree_  # type: ignore[attr-defined]
            temp = pd.DataFrame(zip(
                tree_obj.feature,
                tree_obj.threshold,
                tree_obj.children_left,
                tree_obj.children_right
            ))
            temp.columns = ['t', 'split', 'left', 'right']
            
            leaf_indices = temp[(temp.left == -1) | (temp.right == -1)].index
            return list(temp[
                temp.left.isin(leaf_indices) | temp.right.isin(leaf_indices)
            ]['split'])
        
        df_copy = df.copy()
        
        # Handle weight column - create default if not provided
        actual_weight_col: str
        if weight_col is None or weight_col not in df_copy.columns:
            df_copy['_weight_'] = 1
            actual_weight_col = '_weight_'
        else:
            actual_weight_col = weight_col
        
        skip_cols = (skip_cols or []) + [target_col]
        if weight_col:
            skip_cols.append(weight_col)
        skip_cols.append('_weight_')
        
        # Calculate total bad rate
        df_copy['prob'] = df_copy[target_col] * df_copy[actual_weight_col]
        total_badrate = round(df_copy['prob'].sum() / df_copy[actual_weight_col].sum(), 4)
        
        var_ls, cut_ls, badrate_ls, pct_ls, dir_ls = [], [], [], [], []
        
        def is_small_discrete_int(series: pd.Series, max_unique: int = 20) -> bool:
            """
            检查是否为小范围离散整数特征。
            这类特征不适合用决策树+连续分箱，应该按离散值直接分组。
            
            条件：
            1. 唯一值数量 <= max_unique
            2. 所有值都是整数（或可转换为整数）
            3. 值域范围 <= max_unique * 2
            """
            unique_vals = series.dropna().unique()
            if len(unique_vals) > max_unique:
                return False
            # 检查是否都是整数
            try:
                for v in unique_vals:
                    if float(v) != int(float(v)):
                        return False
            except (ValueError, TypeError):
                return False
            # 检查值域范围
            val_range = float(max(unique_vals)) - float(min(unique_vals))
            return val_range <= max_unique * 2
        
        def get_discrete_direction(
            df: pd.DataFrame, 
            var: str, 
            target_col: str, 
            weight_col: str
        ) -> tuple[str, float, float, str] | None:
            """
            对小范围离散整数特征，直接按值分组计算坏账率，找最优切分方向。
            
            返回: (cutoff, badrate, pct, direction) 或 None
            """
            # 按离散值分组计算坏账率
            df_temp = df[[var, target_col, weight_col, 'prob']].copy()
            grouped = df_temp.groupby(var).agg({
                weight_col: 'sum',
                'prob': 'sum'
            })
            grouped['badRate'] = grouped['prob'] / grouped[weight_col]
            grouped['pct'] = grouped[weight_col] / grouped[weight_col].sum()
            
            if len(grouped) < 2:
                return None
            
            # 找到坏账率最高和最低的值
            sorted_by_badrate = grouped['badRate'].sort_values(ascending=False)
            high_bad_val = sorted_by_badrate.index[0]
            low_bad_val = sorted_by_badrate.index[-1]
            
            # 计算累积坏账率来确定最优切分点
            # 按值排序
            sorted_vals = sorted(grouped.index.tolist())
            best_cutoff = None
            best_lift = 0
            best_direction = None
            best_badrate = 0
            best_pct = 0
            
            total_badrate = df_temp['prob'].sum() / df_temp[weight_col].sum()
            
            for i in range(len(sorted_vals) - 1):
                threshold = (sorted_vals[i] + sorted_vals[i + 1]) / 2
                
                # 计算 <= threshold 的坏账率
                mask_le = df_temp[var] <= threshold
                if mask_le.sum() > 0 and (~mask_le).sum() > 0:
                    bad_le = df_temp.loc[mask_le, 'prob'].sum() / df_temp.loc[mask_le, weight_col].sum()
                    pct_le = df_temp.loc[mask_le, weight_col].sum() / df_temp[weight_col].sum()
                    lift_le = bad_le / total_badrate if total_badrate > 0 else 0
                    
                    # 计算 > threshold 的坏账率
                    bad_gt = df_temp.loc[~mask_le, 'prob'].sum() / df_temp.loc[~mask_le, weight_col].sum()
                    pct_gt = df_temp.loc[~mask_le, weight_col].sum() / df_temp[weight_col].sum()
                    lift_gt = bad_gt / total_badrate if total_badrate > 0 else 0
                    
                    # 选择 lift 更高的方向
                    if lift_le > best_lift:
                        best_lift = lift_le
                        best_cutoff = f"(-inf, {threshold}]"
                        best_direction = '<='
                        best_badrate = bad_le
                        best_pct = pct_le
                    if lift_gt > best_lift:
                        best_lift = lift_gt
                        best_cutoff = f"({threshold}, inf)"
                        best_direction = '>'
                        best_badrate = bad_gt
                        best_pct = pct_gt
            
            if best_cutoff is None:
                return None
            
            return (best_cutoff, round(best_badrate, 4), round(best_pct, 4), best_direction)
        
        for var in df_copy.columns:
            if var in skip_cols or var == 'prob':
                continue
            
            # Check if this is a binary feature
            if is_binary_feature(var, df_copy[var]):
                # Binary feature: use '==' direction, calculate bad rate for value=1
                var_ls.append(var)
                cut_ls.append('== 1')
                
                # Calculate bad rate for binary feature (value == 1)
                mask_1 = df_copy[var] == 1
                if mask_1.sum() > 0:
                    badrate_1 = round(
                        df_copy.loc[mask_1, 'prob'].sum() / df_copy.loc[mask_1, actual_weight_col].sum(), 4
                    )
                    pct_1 = round(df_copy.loc[mask_1, actual_weight_col].sum() / df_copy[actual_weight_col].sum(), 4)
                else:
                    badrate_1 = 0.0
                    pct_1 = 0.0
                
                badrate_ls.append(badrate_1)
                pct_ls.append(pct_1)
                dir_ls.append('==')
                continue
            
            # 新增：检查是否为小范围离散整数特征
            if is_small_discrete_int(df_copy[var]):
                result = get_discrete_direction(df_copy, var, target_col, actual_weight_col)
                if result:
                    cutoff_str, badrate, pct, direction = result
                    var_ls.append(var)
                    cut_ls.append(cutoff_str)
                    badrate_ls.append(badrate)
                    pct_ls.append(pct)
                    dir_ls.append(direction)
                    logger.debug(f"[get_split_direction] 特征 '{var}' 使用离散分组方法: cutoff={cutoff_str}, dir={direction}")
                else:
                    logger.warning(f"[get_split_direction] 特征 '{var}' 离散分组方法无法确定方向，跳过")
                continue
            
            # 原有逻辑：使用决策树确定方向（适用于连续特征）
            try:
                cutoff = get_split_point(
                    np.asarray(df_copy[var].values).reshape(-1, 1),
                    df_copy[target_col],
                    df_copy[actual_weight_col].values,
                    min_samples_leaf,
                    max_depth
                )
            except Exception as e:
                logger.warning(f"[get_split_direction] 特征 '{var}' 决策树异常: {e}")
                continue
            
            # 检查 cutoff 是否为空（决策树无法找到有效切分点）
            if not cutoff:
                # 特征的值分布可能太集中，无法切分
                unique_vals = df_copy[var].dropna().unique()
                logger.warning(
                    f"[get_split_direction] 特征 '{var}' 决策树无法找到有效切分点，跳过 "
                    f"(唯一值数={len(unique_vals)}, 示例={sorted(unique_vals)[:5]})"
                )
                continue
            
            var_ls.append(var)
            
            # Get tree result
            df_temp = df_copy[[var, target_col, actual_weight_col, 'prob']].copy()
            bins = [-np.inf] + sorted(cutoff) + [np.inf]
            df_temp[var] = pd.cut(
                df_temp[var],
                bins=bins,
                duplicates='drop'
            )
            
            # 检查 pd.cut 后的实际区间数
            unique_bins = df_temp[var].dropna().unique()
            if len(unique_bins) <= 1:
                logger.warning(
                    f"[get_split_direction] 特征 '{var}' 分箱后只有 {len(unique_bins)} 个区间 "
                    f"(cutoff={cutoff})，跳过此特征"
                )
                var_ls.pop()  # 移除刚添加的 var
                continue
            
            tmp_df = pd.DataFrame(
                df_temp.groupby([var])[[actual_weight_col, 'prob']].sum().apply(
                    lambda x: round(x['prob'] / x[actual_weight_col], 4), axis=1
                ).rename('badRate')
            )
            
            # 再次检查分组数（groupby 可能合并了一些区间）
            if len(tmp_df) <= 1:
                logger.warning(
                    f"[get_split_direction] 特征 '{var}' groupby 后只有 {len(tmp_df)} 个分组，跳过此特征"
                )
                var_ls.pop()  # 移除刚添加的 var
                continue
            
            # Check if max bad rate occurs at edges
            max_bound = tmp_df['badRate'].idxmax()
            
            if 'inf' in str(max_bound):
                badrate_ls.append(tmp_df['badRate'].max())
                cut_ls.append(str(max_bound))
                pct_ls.append(round(
                    df_temp.loc[df_temp[var] == max_bound, actual_weight_col].sum() / 
                    df_temp[actual_weight_col].sum(), 4
                ))
                if '-inf' in str(max_bound):
                    dir_ls.append('<=')
                else:
                    dir_ls.append('>')
            else:
                # Max bad rate not at edges, merge with both sides
                bound_ls = str(max_bound).split(', ')
                tmp_df2 = df[[var, target_col]].copy()
                tmp_df2[actual_weight_col] = df_copy[actual_weight_col]
                tmp_df2['prob'] = tmp_df2[target_col] * tmp_df2[actual_weight_col]
                
                up_badrate = (
                    tmp_df2.loc[tmp_df2[var] > float(bound_ls[0][1:]), 'prob'].sum() /
                    tmp_df2.loc[tmp_df2[var] > float(bound_ls[0][1:]), actual_weight_col].sum()
                )
                down_badrate = (
                    tmp_df2.loc[tmp_df2[var] <= float(bound_ls[-1][:-1]), 'prob'].sum() /
                    tmp_df2.loc[tmp_df2[var] <= float(bound_ls[-1][:-1]), actual_weight_col].sum()
                )
                
                if up_badrate > down_badrate:
                    badrate_ls.append(round(up_badrate, 4))
                    cut_ls.append(f"{bound_ls[0]}, inf)")
                    pct_ls.append(round(
                        tmp_df2.loc[tmp_df2[var] > float(bound_ls[0][1:]), actual_weight_col].sum() /
                        tmp_df2[actual_weight_col].sum(), 4
                    ))
                    dir_ls.append('>')
                else:
                    badrate_ls.append(round(down_badrate, 4))
                    cut_ls.append(f"(-inf, {bound_ls[-1]}")
                    pct_ls.append(round(
                        tmp_df2.loc[tmp_df2[var] <= float(bound_ls[-1][:-1]), actual_weight_col].sum() /
                        tmp_df2[actual_weight_col].sum(), 4
                    ))
                    dir_ls.append('<=')
        
        return pd.DataFrame({
            'var': var_ls,
            'cutoff': cut_ls,
            'badRate': badrate_ls,
            'pct': pct_ls,
            'lift': np.round(np.array(badrate_ls) / total_badrate, 4),
            'direction': dir_ls
        })
    
    def filter_rules(
        self,
        rule_df: pd.DataFrame,
        direction_df: pd.DataFrame,
        score_vars: list[str] | None = None,
        score_direction: str = '>'
    ) -> pd.DataFrame:
        """
        Filter rules by direction and validity.
        
        Args:
            rule_df: DataFrame with candidate rules
            direction_df: DataFrame with feature split directions
            score_vars: List of score variables that should have specific direction
            score_direction: Expected direction for score variables (default: '>')
            
        Returns:
            Filtered rules DataFrame
        """
        import logging
        logger = logging.getLogger(__name__)
        
        rule_df_filtered = rule_df.copy()
        initial_count = len(rule_df_filtered)
        logger.info(f"[RuleMiner.filter_rules] 初始规则数: {initial_count}")
        
        # Filter by score variable direction
        if score_vars:
            wrong_dir = '<=' if score_direction == '>' else '>'
            for var in score_vars:
                before_count = len(rule_df_filtered)
                rule_df_filtered = rule_df_filtered.loc[
                    [False if f'{var} {wrong_dir}' in x else True 
                     for x in rule_df_filtered.rule]
                ].reset_index(drop=True)
                after_count = len(rule_df_filtered)
                if before_count != after_count:
                    logger.info(f"[RuleMiner.filter_rules] score_vars过滤 {var}: {before_count} -> {after_count}")
        
        # Filter by invalid features (cutoff is (-inf, inf])
        # 注意：正常情况下不应该有 (-inf, inf] 的 cutoff，因为：
        # 1. 二值特征使用 '==' 方向
        # 2. 小范围离散整数特征使用 get_discrete_direction 方法
        # 3. 连续特征使用决策树，无效切分点会被跳过
        # 这个过滤是最后的防线，防止意外情况
        invalid_vars = set(
            direction_df.loc[direction_df.cutoff == '(-inf, inf]', 'var'].values
        )
        logger.info(f"[RuleMiner.filter_rules] direction_df行数: {len(direction_df)}, invalid_vars数量: {len(invalid_vars)}")
        if invalid_vars:
            logger.info(f"[RuleMiner.filter_rules] invalid_vars示例: {list(invalid_vars)[:5]}")
        
        # 兜底保护：如果 invalid_vars 会导致过滤掉过多规则（>80%），则放宽限制
        # 这说明上游的方向计算逻辑可能有遗漏的边界情况，需要排查
        if invalid_vars and len(rule_df_filtered) > 0:
            affected_rules = rule_df_filtered.used_var.apply(
                lambda x: any(v in invalid_vars for v in x.split(' & '))
            ).sum()
            affected_ratio = affected_rules / len(rule_df_filtered)
            if affected_ratio > 0.8:
                logger.warning(
                    f"[RuleMiner.filter_rules] invalid_vars 会过滤掉 {affected_ratio*100:.1f}% 的规则 "
                    f"({affected_rules}/{len(rule_df_filtered)})，已跳过此过滤条件。"
                    f"请检查 get_split_direction 方法对这些特征的处理逻辑: {list(invalid_vars)[:5]}"
                )
                invalid_vars = set()  # 清空，不进行过滤
        
        # 调试：检查规则中使用的特征是否在 direction_df 中
        if len(rule_df_filtered) > 0:
            all_rule_vars: set[str] = set()
            for used_var in rule_df_filtered['used_var']:
                all_rule_vars.update(used_var.split(' & '))
            direction_vars = set(direction_df['var'].tolist())
            missing_vars = all_rule_vars - direction_vars
            if missing_vars:
                logger.warning(f"[RuleMiner.filter_rules] 规则中有 {len(missing_vars)} 个特征不在direction_df中: {list(missing_vars)[:10]}")
        
        before_invalid_filter = len(rule_df_filtered)
        
        # 详细记录每条规则为什么被过滤
        filtered_reasons = []
        for idx, row in rule_df_filtered.iterrows():
            used_vars = row['used_var'].split(' & ')
            invalid_in_rule = [v for v in used_vars if v in invalid_vars]
            if invalid_in_rule:
                filtered_reasons.append({
                    'rule': row['rule'][:50],  # 截取前50字符
                    'invalid_vars': invalid_in_rule
                })
        
        if filtered_reasons and len(filtered_reasons) <= 10:
            for reason in filtered_reasons:
                logger.info(f"[RuleMiner.filter_rules] 被过滤规则: {reason['rule']}... | 无效特征: {reason['invalid_vars']}")
        elif filtered_reasons:
            logger.info(f"[RuleMiner.filter_rules] 共有 {len(filtered_reasons)} 条规则因 invalid_vars 被过滤（显示前5条）")
            for reason in filtered_reasons[:5]:
                logger.info(f"[RuleMiner.filter_rules] 被过滤规则: {reason['rule']}... | 无效特征: {reason['invalid_vars']}")
        
        rule_selected = rule_df_filtered.used_var.apply(
            lambda x: not any(
                v in invalid_vars for v in x.split(' & ')
            )
        )
        rule_df_filtered = rule_df_filtered.loc[rule_selected].reset_index(drop=True)
        after_invalid_filter = len(rule_df_filtered)
        
        logger.info(f"[RuleMiner.filter_rules] invalid_vars过滤: {before_invalid_filter} -> {after_invalid_filter}")
        logger.info(f"[RuleMiner.filter_rules] 最终规则数: {len(rule_df_filtered)} (从 {initial_count} 条过滤)")
        
        return rule_df_filtered


class RuleEvaluator:
    """
    Rule effect evaluator.
    
    Calculates recall, bad_rate, lift, and hit_rate for each rule.
    """
    
    def evaluate_rules(
        self,
        df: pd.DataFrame,
        rule_df: pd.DataFrame,
        target_col: str = 'target',
        weight_col: str | None = None,
        progress_callback: ProgressCallback = None
    ) -> pd.DataFrame:
        """
        Calculate metrics for each rule.
        
        Args:
            df: Input dataframe
            rule_df: DataFrame with rules
            target_col: Target column name
            weight_col: Sample weight column name (optional, None for no weighting)
            progress_callback: Optional callback function(current, total) for progress
            
        Returns:
            DataFrame with rule metrics: recall, bad_rate, lift, hit_rate
        """
        df_copy = df.copy()
        
        # Handle weight column - create default if not provided
        actual_weight_col: str
        if weight_col is None or weight_col not in df_copy.columns:
            df_copy['_weight_'] = 1
            actual_weight_col = '_weight_'
        else:
            actual_weight_col = weight_col
        
        # Calculate totals
        total_weight = df_copy[actual_weight_col].sum()
        total_bad = df_copy.loc[df_copy[target_col] == 1, actual_weight_col].sum()
        total_badrate = total_bad / total_weight
        
        rule_ls = rule_df.rule.tolist()
        recall_ls, badrate_ls, lift_ls, hitrate_ls = [], [], [], []
        
        for idx, rule in enumerate(rule_ls):
            try:
                # Use safe rule evaluation instead of eval()
                rule_hit = _safe_eval_rule(df_copy, rule, 'df_copy')
                hit_weight = df_copy.loc[rule_hit, actual_weight_col].sum()
                
                if hit_weight < 1:
                    recall, badrate, lift = 0, 0, 0
                else:
                    hit_bad = df_copy.loc[rule_hit & (df_copy[target_col] == 1), actual_weight_col].sum()
                    recall = round(hit_bad / total_bad, 4)
                    badrate = round(hit_bad / hit_weight, 4)
                    lift = round(badrate / total_badrate, 1)
                
                hitrate = round(hit_weight / total_weight, 4)
            except Exception:
                recall, badrate, lift, hitrate = 0, 0, 0, 0
            
            recall_ls.append(recall)
            badrate_ls.append(badrate)
            lift_ls.append(lift)
            hitrate_ls.append(hitrate)
            
            if progress_callback:
                progress_callback(idx + 1, len(rule_ls))
        
        result_df = pd.DataFrame({
            'rule': rule_ls,
            'recall': recall_ls,
            'bad_rate': badrate_ls,
            'lift': lift_ls,
            'hit_rate': hitrate_ls
        })
        
        # Ensure rule column types match to avoid merge errors
        rule_df = rule_df.copy()
        rule_df['rule'] = rule_df['rule'].astype(str)
        result_df['rule'] = result_df['rule'].astype(str)
        
        return rule_df.merge(result_df, how='left', on='rule')
    
    def filter_by_metrics(
        self,
        rule_info_df: pd.DataFrame,
        max_hit_rate: float = 0.03,
        min_lift: float = 3.5
    ) -> pd.DataFrame:
        """
        Filter rules by metric thresholds.
        
        Args:
            rule_info_df: DataFrame with rule metrics
            max_hit_rate: Maximum hit rate threshold
            min_lift: Minimum lift threshold
            
        Returns:
            Filtered rules DataFrame
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        total_rules = len(rule_info_df)
        
        # 诊断日志：分析过滤原因
        # 首先过滤坏账率为0的规则（这些规则无风险识别能力）
        bad_rate_pass = rule_info_df.bad_rate > 0 if 'bad_rate' in rule_info_df.columns else pd.Series([True] * len(rule_info_df))
        hit_rate_pass = rule_info_df.hit_rate < max_hit_rate
        lift_pass = rule_info_df.lift > min_lift
        all_pass = bad_rate_pass & hit_rate_pass & lift_pass
        
        bad_rate_fail_count = (~bad_rate_pass).sum() if 'bad_rate' in rule_info_df.columns else 0
        hit_rate_fail_count = (~hit_rate_pass).sum()
        lift_fail_count = (~lift_pass).sum()
        both_fail_count = (~hit_rate_pass & ~lift_pass).sum()
        pass_count = all_pass.sum()
        
        _logger.info(f"[filter_by_metrics] 过滤参数: max_hit_rate={max_hit_rate}, min_lift={min_lift}")
        _logger.info(f"[filter_by_metrics] 输入规则数: {total_rules}")
        if bad_rate_fail_count > 0:
            _logger.info(f"[filter_by_metrics] 坏账率为0: {bad_rate_fail_count}条")
        _logger.info(f"[filter_by_metrics] 命中率超标(>={max_hit_rate}): {hit_rate_fail_count}条")
        _logger.info(f"[filter_by_metrics] Lift不足(<={min_lift}): {lift_fail_count}条")
        _logger.info(f"[filter_by_metrics] 两项均不达标: {both_fail_count}条")
        _logger.info(f"[filter_by_metrics] 通过筛选: {pass_count}条")
        
        # 输出命中率和Lift的分布统计
        if total_rules > 0:
            _logger.info(f"[filter_by_metrics] 命中率分布: min={rule_info_df.hit_rate.min():.4f}, max={rule_info_df.hit_rate.max():.4f}, median={rule_info_df.hit_rate.median():.4f}")
            _logger.info(f"[filter_by_metrics] Lift分布: min={rule_info_df.lift.min():.2f}, max={rule_info_df.lift.max():.2f}, median={rule_info_df.lift.median():.2f}")
        
        return rule_info_df[all_pass].reset_index(drop=True)
    
    def calculate_rule_psi(
        self,
        rules_df: pd.DataFrame,
        df_base: pd.DataFrame,
        df_compare: pd.DataFrame,
        target_col: str = 'target',
        weight_col: str | None = None
    ) -> pd.DataFrame:
        """
        计算规则PSI（Population Stability Index）
        
        用于检测规则在不同时间段/样本集的稳定性
        
        Args:
            rules_df: 规则DataFrame，需包含'rule'列
            df_base: 基准样本（开发样本）
            df_compare: 对比样本（验证样本/新样本）
            target_col: 目标列名
            weight_col: 权重列名（可选）
            
        Returns:
            DataFrame with columns: rule, hit_rate_base, hit_rate_compare, psi, stability
            
        PSI阈值说明:
            < 0.1: 稳定
            0.1 - 0.25: 轻微变化
            > 0.25: 显著变化
        """
        psi_results: list[dict[str, Any]] = []
        
        # 使用列表遍历替代iterrows以提高性能
        for rule in rules_df['rule'].tolist():
            try:
                # 计算基准样本命中率 - 使用安全的规则评估
                hit_base_mask = _safe_eval_rule(df_base, rule, 'df_base')
                hit_base = hit_base_mask.mean()
                
                # 计算对比样本命中率
                hit_compare_mask = _safe_eval_rule(df_compare, rule, 'df_compare')
                hit_compare = hit_compare_mask.mean()
                
                # 计算PSI
                # PSI = (actual% - expected%) * ln(actual% / expected%)
                if hit_base > 0 and hit_compare > 0:
                    psi = (hit_compare - hit_base) * np.log(hit_compare / hit_base)
                    psi = abs(psi)  # PSI取绝对值
                else:
                    psi = np.nan
                
                # 稳定性评级
                if pd.isna(psi):
                    stability = 'N/A'
                elif psi < 0.1:
                    stability = '稳定'
                elif psi < 0.25:
                    stability = '轻微变化'
                else:
                    stability = '显著变化'
                
                psi_results.append({
                    'rule': rule,
                    'hit_rate_base': round(float(hit_base), 4),
                    'hit_rate_compare': round(float(hit_compare), 4),
                    'psi': round(float(psi), 4) if not pd.isna(psi) else None,
                    'stability': stability
                })
            except Exception as e:
                psi_results.append({
                    'rule': rule,
                    'hit_rate_base': None,
                    'hit_rate_compare': None,
                    'psi': None,
                    'stability': 'error',
                    'error': str(e)
                })
        
        return pd.DataFrame(psi_results)
    
    def calculate_rule_psi_by_time(
        self,
        rules_df: pd.DataFrame,
        df: pd.DataFrame,
        time_col: str,
        target_col: str = 'target',
        n_periods: int = 2
    ) -> pd.DataFrame:
        """
        按时间分割计算规则PSI
        
        当没有单独的验证集时，可以按时间将数据分割成多个时期进行PSI计算
        
        Args:
            rules_df: 规则DataFrame
            df: 完整数据集
            time_col: 时间列名
            target_col: 目标列名
            n_periods: 分割的时期数（默认2，即前后对比）
            
        Returns:
            PSI计算结果DataFrame
        """
        # 按时间排序
        df_sorted = df.sort_values(time_col).reset_index(drop=True)
        
        # 分割数据
        split_size = len(df_sorted) // n_periods
        df_base = df_sorted.iloc[:split_size]
        df_compare = df_sorted.iloc[-split_size:]
        
        return self.calculate_rule_psi(rules_df, df_base, df_compare, target_col)
    
    def evaluate_with_prior(
        self,
        df: pd.DataFrame,
        rule: str,
        prior_rules: list[str],
        target_col: str = 'target',
        weight_col: str | None = None
    ) -> dict[str, Any]:
        """
        Evaluate rule with prior rules - calculate incremental contribution.
        
        This method evaluates how much a new rule contributes beyond existing rules.
        Useful for:
        - Assessing new rules against production rule set
        - Rule optimization and pruning
        - Understanding rule overlap
        
        Args:
            df: Input dataframe
            rule: Rule expression to evaluate
            prior_rules: List of existing rule expressions
            target_col: Target column name
            weight_col: Sample weight column name (optional)
            
        Returns:
            Dictionary containing:
            - rule: The evaluated rule
            - standalone_recall: Recall when rule is applied alone
            - incremental_recall: Additional recall beyond prior rules
            - standalone_hit_rate: Hit rate when rule is applied alone
            - incremental_hit_rate: Additional hit rate beyond prior rules
            - overlap_with_prior: Overlap ratio with prior rules
            - marginal_contribution: Marginal contribution (same as incremental_recall)
        """
        df_copy = df.copy()
        
        # Handle weight column
        actual_weight_col: str
        if weight_col is None or weight_col not in df_copy.columns:
            df_copy['_weight_'] = 1
            actual_weight_col = '_weight_'
        else:
            actual_weight_col = weight_col
        
        # Calculate totals
        total_weight = df_copy[actual_weight_col].sum()
        total_bad = df_copy.loc[df_copy[target_col] == 1, actual_weight_col].sum()
        
        # Calculate prior rules combined hit
        prior_hit = pd.Series(False, index=df_copy.index)
        for pr in prior_rules:
            if not pr or not pr.strip():
                continue
            try:
                # Use safe rule evaluation instead of eval()
                prior_hit |= _safe_eval_rule(df_copy, pr, 'df_copy')
            except Exception:
                continue
        
        # Calculate current rule hit
        try:
            # Use safe rule evaluation instead of eval()
            rule_hit = _safe_eval_rule(df_copy, rule, 'df_copy')
        except Exception:
            return {
                'rule': rule,
                'standalone_recall': 0,
                'incremental_recall': 0,
                'standalone_hit_rate': 0,
                'incremental_hit_rate': 0,
                'overlap_with_prior': 0,
                'marginal_contribution': 0,
                'error': 'Failed to evaluate rule'
            }
        
        # Calculate standalone metrics
        rule_hit_weight = df_copy.loc[rule_hit, actual_weight_col].sum()
        rule_hit_bad = df_copy.loc[rule_hit & (df_copy[target_col] == 1), actual_weight_col].sum()
        
        standalone_recall = rule_hit_bad / total_bad if total_bad > 0 else 0
        standalone_hit_rate = rule_hit_weight / total_weight if total_weight > 0 else 0
        
        # Calculate incremental metrics (excluding prior hits)
        incremental_hit = rule_hit & ~prior_hit
        incremental_hit_weight = df_copy.loc[incremental_hit, actual_weight_col].sum()
        incremental_hit_bad = df_copy.loc[incremental_hit & (df_copy[target_col] == 1), actual_weight_col].sum()
        
        incremental_recall = incremental_hit_bad / total_bad if total_bad > 0 else 0
        incremental_hit_rate = incremental_hit_weight / total_weight if total_weight > 0 else 0
        
        # Calculate overlap with prior
        overlap_hit = rule_hit & prior_hit
        overlap_weight = df_copy.loc[overlap_hit, actual_weight_col].sum()
        overlap_ratio = overlap_weight / rule_hit_weight if rule_hit_weight > 0 else 0
        
        return {
            'rule': rule,
            'standalone_recall': round(standalone_recall, 4),
            'incremental_recall': round(incremental_recall, 4),
            'standalone_hit_rate': round(standalone_hit_rate, 4),
            'incremental_hit_rate': round(incremental_hit_rate, 4),
            'overlap_with_prior': round(overlap_ratio, 4),
            'marginal_contribution': round(incremental_recall, 4)
        }
    
    def evaluate_rules_with_prior(
        self,
        df: pd.DataFrame,
        rule_df: pd.DataFrame,
        prior_rules: list[str],
        target_col: str = 'target',
        weight_col: str | None = None,
        progress_callback: ProgressCallback = None
    ) -> pd.DataFrame:
        """
        Evaluate multiple rules with prior rules.
        
        Args:
            df: Input dataframe
            rule_df: DataFrame with rules (must have 'rule' column)
            prior_rules: List of existing rule expressions
            target_col: Target column name
            weight_col: Sample weight column name (optional)
            progress_callback: Progress callback function
            
        Returns:
            DataFrame with prior analysis results merged
        """
        results = []
        rule_ls = rule_df['rule'].tolist()
        
        for idx, rule in enumerate(rule_ls):
            result = self.evaluate_with_prior(
                df, rule, prior_rules, target_col, weight_col
            )
            results.append(result)
            
            if progress_callback:
                progress_callback(idx + 1, len(rule_ls))
        
        prior_df = pd.DataFrame(results)
        
        # Ensure rule column types match to avoid merge errors
        rule_df = rule_df.copy()
        rule_df['rule'] = rule_df['rule'].astype(str)
        prior_df['rule'] = prior_df['rule'].astype(str)
        
        return rule_df.merge(prior_df, on='rule', how='left')
    
    def evaluate_with_amount(
        self,
        df: pd.DataFrame,
        rule: str,
        target_col: str = 'target',
        amount_col: str = 'amount',
        weight_col: str | None = None
    ) -> dict[str, Any]:
        """
        Evaluate rule with amount dimension analysis.
        
        This method calculates amount-based metrics for risk assessment:
        - How much exposure (amount) does the rule capture?
        - What's the bad amount captured?
        - Amount-based lift and bad rate
        
        Useful for:
        - Risk exposure assessment
        - Loss prevention analysis
        - Rule prioritization by financial impact
        
        Args:
            df: Input dataframe
            rule: Rule expression to evaluate
            target_col: Target column name (0/1 binary)
            amount_col: Amount column name (loan amount, transaction amount, etc.)
            weight_col: Sample weight column name (optional)
            
        Returns:
            Dictionary containing:
            - rule: The evaluated rule
            - hit_amount: Total amount captured by rule
            - hit_amount_pct: Percentage of total amount captured
            - bad_amount: Bad amount captured by rule
            - bad_amount_pct: Percentage of total bad amount captured
            - amount_bad_rate: Bad rate in amount dimension
            - amount_lift: Lift in amount dimension
            - avg_amount_per_hit: Average amount per hit sample
        """
        df_copy = df.copy()
        
        # Validate amount column
        if amount_col not in df_copy.columns:
            return {
                'rule': rule,
                'hit_amount': 0,
                'hit_amount_pct': 0,
                'bad_amount': 0,
                'bad_amount_pct': 0,
                'amount_bad_rate': 0,
                'amount_lift': 0,
                'avg_amount_per_hit': 0,
                'error': f'Amount column "{amount_col}" not found'
            }
        
        # Calculate totals
        total_amount = df_copy[amount_col].sum()
        total_bad_amount = df_copy.loc[df_copy[target_col] == 1, amount_col].sum()
        overall_amount_bad_rate = total_bad_amount / total_amount if total_amount > 0 else 0
        
        # Evaluate rule
        try:
            # Use safe rule evaluation instead of eval()
            rule_hit = _safe_eval_rule(df_copy, rule, 'df_copy')
        except Exception:
            return {
                'rule': rule,
                'hit_amount': 0,
                'hit_amount_pct': 0,
                'bad_amount': 0,
                'bad_amount_pct': 0,
                'amount_bad_rate': 0,
                'amount_lift': 0,
                'avg_amount_per_hit': 0,
                'error': 'Failed to evaluate rule'
            }
        
        # Calculate amount metrics
        hit_amount = df_copy.loc[rule_hit, amount_col].sum()
        bad_amount = df_copy.loc[rule_hit & (df_copy[target_col] == 1), amount_col].sum()
        hit_count = rule_hit.sum()
        
        hit_amount_pct = hit_amount / total_amount if total_amount > 0 else 0
        bad_amount_pct = bad_amount / total_bad_amount if total_bad_amount > 0 else 0
        amount_bad_rate = bad_amount / hit_amount if hit_amount > 0 else 0
        amount_lift = amount_bad_rate / overall_amount_bad_rate if overall_amount_bad_rate > 0 else 0
        avg_amount_per_hit = hit_amount / hit_count if hit_count > 0 else 0
        
        return {
            'rule': rule,
            'hit_amount': round(hit_amount, 2),
            'hit_amount_pct': round(hit_amount_pct, 4),
            'bad_amount': round(bad_amount, 2),
            'bad_amount_pct': round(bad_amount_pct, 4),
            'amount_bad_rate': round(amount_bad_rate, 4),
            'amount_lift': round(amount_lift, 2),
            'avg_amount_per_hit': round(avg_amount_per_hit, 2)
        }
    
    def evaluate_rules_with_amount(
        self,
        df: pd.DataFrame,
        rule_df: pd.DataFrame,
        target_col: str = 'target',
        amount_col: str = 'amount',
        weight_col: str | None = None,
        progress_callback: ProgressCallback = None
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Evaluate multiple rules with amount dimension.
        
        Args:
            df: Input dataframe
            rule_df: DataFrame with rules (must have 'rule' column)
            target_col: Target column name
            amount_col: Amount column name
            weight_col: Sample weight column name (optional)
            progress_callback: Progress callback function
            
        Returns:
            Tuple of:
            - DataFrame with amount analysis results merged
            - Summary dict with total amount metrics
        """
        results = []
        rule_ls = rule_df['rule'].tolist()
        
        for idx, rule in enumerate(rule_ls):
            result = self.evaluate_with_amount(
                df, rule, target_col, amount_col, weight_col
            )
            results.append(result)
            
            if progress_callback:
                progress_callback(idx + 1, len(rule_ls))
        
        amount_df = pd.DataFrame(results)
        
        # Ensure rule column types match to avoid merge errors
        rule_df = rule_df.copy()
        rule_df['rule'] = rule_df['rule'].astype(str)
        amount_df['rule'] = amount_df['rule'].astype(str)
        
        merged_df = rule_df.merge(amount_df, on='rule', how='left')
        
        # Calculate cumulative amount metrics
        total_amount = df[amount_col].sum()
        total_bad_amount = df.loc[df[target_col] == 1, amount_col].sum()
        
        # Calculate cumulative metrics (assuming rules are already sorted by priority)
        cum_hit_amount = 0
        cum_bad_amount = 0
        hit_sample_indices: set = set()
        
        for rule in rule_ls:
            try:
                # Use safe rule evaluation instead of eval()
                rule_hit = _safe_eval_rule(df, rule, 'df')
                rule_hit_indices = set(df[rule_hit].index.tolist())
                
                # New hits only (for cumulative)
                new_hit_indices = rule_hit_indices - hit_sample_indices
                hit_sample_indices.update(rule_hit_indices)
                
                cum_hit_amount += df.loc[list(new_hit_indices), amount_col].sum()
                cum_bad_amount += df.loc[
                    list(new_hit_indices) & set(df[df[target_col] == 1].index.tolist()),
                    amount_col
                ].sum() if new_hit_indices else 0
            except Exception:
                continue
        
        summary = {
            'total_amount': round(total_amount, 2),
            'total_bad_amount': round(total_bad_amount, 2),
            'cumulative': {
                'cum_hit_amount': round(cum_hit_amount, 2),
                'cum_bad_amount': round(cum_bad_amount, 2),
                'amount_recall': round(cum_bad_amount / total_bad_amount, 4) if total_bad_amount > 0 else 0
            },
            'rules_amount': results
        }
        
        return merged_df, summary


class PriorRuleAnalyzer:
    """
    Prior rule incremental contribution analyzer (v6.2 upgrade).
    
    Analyzes how much a new rule contributes beyond existing (prior) rules.
    This is essential for:
    - Assessing new rules against production rule set
    - Rule optimization and pruning
    - Understanding rule overlap and redundancy
    
    Attributes:
        prior_rules: List of existing rule expressions
        
    Example:
        >>> analyzer = PriorRuleAnalyzer(prior_rules=["(age <= 25)", "credit_score <= 550"])
        >>> analyzer.fit(df, target_col='target')
        >>> results = analyzer.analyze(rule_df)
        >>> print(results[['rule', 'standalone_recall', 'incremental_recall', 'overlap_rate']])
    """
    
    def __init__(
        self,
        prior_rules: list[str] | None = None,
        weight_col: str | None = None
    ):
        """
        Initialize PriorRuleAnalyzer.
        
        Args:
            prior_rules: List of existing rule expressions
            weight_col: Sample weight column name (optional)
        """
        self.prior_rules = prior_rules or []
        self.weight_col = weight_col
        
        # Fitted attributes
        self._df: pd.DataFrame | None = None
        self._target_col: str = 'target'
        self._prior_hit: pd.Series | None = None
        self._total_weight: float = 0
        self._total_bad: float = 0
        self._fitted = False
    
    def fit(
        self,
        df: pd.DataFrame,
        target_col: str = 'target',
        weight_col: str | None = None
    ) -> "PriorRuleAnalyzer":
        """
        Fit the analyzer with data and calculate prior rules combined hit.
        
        Args:
            df: Input dataframe
            target_col: Target column name (0/1 binary)
            weight_col: Sample weight column name (optional, overrides init value)
            
        Returns:
            self
        """
        self._df = df.copy()
        self._target_col = target_col
        
        # Handle weight column
        actual_weight_col: str
        if weight_col is not None:
            self.weight_col = weight_col
        
        if self.weight_col is None or self.weight_col not in self._df.columns:
            self._df['_weight_'] = 1
            actual_weight_col = '_weight_'
        else:
            actual_weight_col = self.weight_col
        
        self._actual_weight_col = actual_weight_col
        
        # Calculate totals
        self._total_weight = self._df[actual_weight_col].sum()
        self._total_bad = self._df.loc[self._df[target_col] == 1, actual_weight_col].sum()
        
        # Calculate prior rules combined hit
        self._prior_hit = pd.Series(False, index=self._df.index)
        for pr in self.prior_rules:
            if not pr or not pr.strip():
                continue
            try:
                # Use safe rule evaluation instead of eval()
                self._prior_hit |= _safe_eval_rule(self._df, pr, 'self._df')
            except Exception:
                continue
        
        # Calculate prior rules metrics
        prior_hit_weight = self._df.loc[self._prior_hit, actual_weight_col].sum()
        prior_hit_bad = self._df.loc[
            self._prior_hit & (self._df[target_col] == 1), actual_weight_col
        ].sum()
        
        self._prior_metrics = {
            'prior_hit_rate': round(prior_hit_weight / self._total_weight, 4) if self._total_weight > 0 else 0,
            'prior_recall': round(prior_hit_bad / self._total_bad, 4) if self._total_bad > 0 else 0,
            'prior_hit_count': int(self._prior_hit.sum()),
            'prior_bad_count': int((self._prior_hit & (self._df[target_col] == 1)).sum())
        }
        
        self._fitted = True
        return self
    
    def _ensure_fitted(self) -> None:
        """Ensure analyzer is fitted."""
        if not self._fitted:
            raise ValueError("Analyzer not fitted. Call fit() first.")
    
    def analyze_rule(self, rule: str) -> dict[str, Any]:
        """
        Analyze a single rule's incremental contribution.
        
        Args:
            rule: Rule expression to evaluate
            
        Returns:
            Dictionary containing:
            - rule: The evaluated rule
            - standalone_recall: Recall when rule is applied alone
            - standalone_hit_rate: Hit rate when rule is applied alone
            - incremental_recall: Additional recall beyond prior rules
            - incremental_hit_rate: Additional hit rate beyond prior rules
            - overlap_rate: Overlap ratio with prior rules
            - marginal_contribution: incremental_recall / standalone_recall
        """
        self._ensure_fitted()
        
        df = self._df
        target_col = self._target_col
        weight_col = self._actual_weight_col
        
        # Evaluate current rule
        try:
            # Use safe rule evaluation instead of eval()
            rule_hit = _safe_eval_rule(df, rule, 'df')
        except Exception:
            return {
                'rule': rule,
                'standalone_recall': 0,
                'standalone_hit_rate': 0,
                'incremental_recall': 0,
                'incremental_hit_rate': 0,
                'overlap_rate': 0,
                'marginal_contribution': 0,
                'error': 'Failed to evaluate rule'
            }
        
        # Calculate standalone metrics
        rule_hit_weight = df.loc[rule_hit, weight_col].sum()
        rule_hit_bad = df.loc[rule_hit & (df[target_col] == 1), weight_col].sum()
        
        standalone_recall = rule_hit_bad / self._total_bad if self._total_bad > 0 else 0
        standalone_hit_rate = rule_hit_weight / self._total_weight if self._total_weight > 0 else 0
        
        # Calculate incremental metrics (excluding prior hits)
        incremental_hit = rule_hit & ~self._prior_hit
        incremental_hit_weight = df.loc[incremental_hit, weight_col].sum()
        incremental_hit_bad = df.loc[incremental_hit & (df[target_col] == 1), weight_col].sum()
        
        incremental_recall = incremental_hit_bad / self._total_bad if self._total_bad > 0 else 0
        incremental_hit_rate = incremental_hit_weight / self._total_weight if self._total_weight > 0 else 0
        
        # Calculate overlap with prior
        overlap_hit = rule_hit & self._prior_hit
        overlap_weight = df.loc[overlap_hit, weight_col].sum()
        overlap_rate = overlap_weight / rule_hit_weight if rule_hit_weight > 0 else 0
        
        # Marginal contribution
        marginal_contribution = incremental_recall / standalone_recall if standalone_recall > 0 else 0
        
        return {
            'rule': rule,
            'standalone_recall': round(standalone_recall, 4),
            'standalone_hit_rate': round(standalone_hit_rate, 4),
            'incremental_recall': round(incremental_recall, 4),
            'incremental_hit_rate': round(incremental_hit_rate, 4),
            'overlap_rate': round(overlap_rate, 4),
            'marginal_contribution': round(marginal_contribution, 4)
        }
    
    def analyze(
        self,
        rule_df: pd.DataFrame,
        progress_callback: ProgressCallback = None
    ) -> pd.DataFrame:
        """
        Analyze multiple rules' incremental contribution.
        
        Args:
            rule_df: DataFrame with rules (must have 'rule' column)
            progress_callback: Progress callback function(current, total)
            
        Returns:
            DataFrame with prior analysis results merged
        """
        self._ensure_fitted()
        
        results = []
        rule_ls = rule_df['rule'].tolist()
        
        for idx, rule in enumerate(rule_ls):
            result = self.analyze_rule(rule)
            results.append(result)
            
            if progress_callback:
                progress_callback(idx + 1, len(rule_ls))
        
        prior_df = pd.DataFrame(results)
        
        # Ensure rule column types match to avoid merge errors
        rule_df = rule_df.copy()
        rule_df['rule'] = rule_df['rule'].astype(str)
        prior_df['rule'] = prior_df['rule'].astype(str)
        
        return rule_df.merge(prior_df, on='rule', how='left')
    
    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of prior rules analysis.
        
        Returns:
            Dictionary with prior rules metrics and configuration
        """
        self._ensure_fitted()
        
        return {
            'enabled': len(self.prior_rules) > 0,
            'prior_rules': self.prior_rules,
            'prior_rules_count': len(self.prior_rules),
            'prior_metrics': self._prior_metrics,
            'total_samples': int(self._total_weight),
            'total_bad': int(self._total_bad)
        }


class AmountAnalyzer:
    """
    Amount dimension analyzer for rule evaluation (v6.2 upgrade).
    
    Analyzes rules from a financial/amount perspective:
    - How much exposure (amount) does the rule capture?
    - What's the bad amount captured?
    - Amount-based lift and bad rate
    
    Useful for:
    - Risk exposure assessment
    - Loss prevention analysis
    - Rule prioritization by financial impact
    
    Attributes:
        amount_col: Amount column name (loan amount, transaction amount, etc.)
        
    Example:
        >>> analyzer = AmountAnalyzer(amount_col='loan_amount')
        >>> analyzer.fit(df, target_col='target')
        >>> results = analyzer.analyze(rule_df)
        >>> print(results[['rule', 'hit_amount', 'bad_amount', 'amount_lift']])
    """
    
    def __init__(
        self,
        amount_col: str = 'amount',
        weight_col: str | None = None
    ):
        """
        Initialize AmountAnalyzer.
        
        Args:
            amount_col: Amount column name
            weight_col: Sample weight column name (optional)
        """
        self.amount_col = amount_col
        self.weight_col = weight_col
        
        # Fitted attributes
        self._df: pd.DataFrame | None = None
        self._target_col: str = 'target'
        self._total_amount: float = 0
        self._total_bad_amount: float = 0
        self._overall_amount_bad_rate: float = 0
        self._fitted = False
    
    def fit(
        self,
        df: pd.DataFrame,
        target_col: str = 'target',
        amount_col: str | None = None
    ) -> "AmountAnalyzer":
        """
        Fit the analyzer with data.
        
        Args:
            df: Input dataframe
            target_col: Target column name (0/1 binary)
            amount_col: Amount column name (optional, overrides init value)
            
        Returns:
            self
            
        Raises:
            ValueError: If amount column not found in dataframe
        """
        if amount_col is not None:
            self.amount_col = amount_col
        
        if self.amount_col not in df.columns:
            raise ValueError(f"Amount column '{self.amount_col}' not found in dataframe")
        
        self._df = df.copy()
        self._target_col = target_col
        
        # Calculate totals
        self._total_amount = self._df[self.amount_col].sum()
        self._total_bad_amount = self._df.loc[self._df[target_col] == 1, self.amount_col].sum()
        self._overall_amount_bad_rate = (
            self._total_bad_amount / self._total_amount 
            if self._total_amount > 0 else 0
        )
        
        self._fitted = True
        return self
    
    def _ensure_fitted(self) -> None:
        """Ensure analyzer is fitted."""
        if not self._fitted:
            raise ValueError("Analyzer not fitted. Call fit() first.")
    
    def analyze_rule(self, rule: str) -> dict[str, Any]:
        """
        Analyze a single rule from amount dimension.
        
        Args:
            rule: Rule expression to evaluate
            
        Returns:
            Dictionary containing:
            - rule: The evaluated rule
            - hit_amount: Total amount captured by rule
            - hit_amount_pct: Percentage of total amount captured
            - bad_amount: Bad amount captured by rule
            - bad_amount_pct: Percentage of total bad amount captured (amount recall)
            - amount_bad_rate: Bad rate in amount dimension
            - amount_lift: Lift in amount dimension
            - avg_amount_per_hit: Average amount per hit sample
        """
        self._ensure_fitted()
        
        df = self._df
        target_col = self._target_col
        amount_col = self.amount_col
        
        # Evaluate rule
        try:
            # Use safe rule evaluation instead of eval()
            rule_hit = _safe_eval_rule(df, rule, 'df')
        except Exception:
            return {
                'rule': rule,
                'hit_amount': 0,
                'hit_amount_pct': 0,
                'bad_amount': 0,
                'bad_amount_pct': 0,
                'amount_bad_rate': 0,
                'amount_lift': 0,
                'avg_amount_per_hit': 0,
                'error': 'Failed to evaluate rule'
            }
        
        # Calculate amount metrics
        hit_amount = df.loc[rule_hit, amount_col].sum()
        bad_amount = df.loc[rule_hit & (df[target_col] == 1), amount_col].sum()
        hit_count = rule_hit.sum()
        
        hit_amount_pct = hit_amount / self._total_amount if self._total_amount > 0 else 0
        bad_amount_pct = bad_amount / self._total_bad_amount if self._total_bad_amount > 0 else 0
        amount_bad_rate = bad_amount / hit_amount if hit_amount > 0 else 0
        amount_lift = amount_bad_rate / self._overall_amount_bad_rate if self._overall_amount_bad_rate > 0 else 0
        avg_amount_per_hit = hit_amount / hit_count if hit_count > 0 else 0
        
        return {
            'rule': rule,
            'hit_amount': round(hit_amount, 2),
            'hit_amount_pct': round(hit_amount_pct, 4),
            'bad_amount': round(bad_amount, 2),
            'bad_amount_pct': round(bad_amount_pct, 4),
            'amount_bad_rate': round(amount_bad_rate, 4),
            'amount_lift': round(amount_lift, 2),
            'avg_amount_per_hit': round(avg_amount_per_hit, 2)
        }
    
    def analyze(
        self,
        rule_df: pd.DataFrame,
        progress_callback: ProgressCallback = None
    ) -> pd.DataFrame:
        """
        Analyze multiple rules from amount dimension.
        
        Args:
            rule_df: DataFrame with rules (must have 'rule' column)
            progress_callback: Progress callback function(current, total)
            
        Returns:
            DataFrame with amount analysis results merged
        """
        self._ensure_fitted()
        
        results = []
        rule_ls = rule_df['rule'].tolist()
        
        for idx, rule in enumerate(rule_ls):
            result = self.analyze_rule(rule)
            results.append(result)
            
            if progress_callback:
                progress_callback(idx + 1, len(rule_ls))
        
        amount_df = pd.DataFrame(results)
        
        # Ensure rule column types match to avoid merge errors
        rule_df = rule_df.copy()
        rule_df['rule'] = rule_df['rule'].astype(str)
        amount_df['rule'] = amount_df['rule'].astype(str)
        
        return rule_df.merge(amount_df, on='rule', how='left')
    
    def analyze_with_cumulative(
        self,
        rule_df: pd.DataFrame,
        progress_callback: ProgressCallback = None
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Analyze rules with cumulative amount metrics.
        
        Args:
            rule_df: DataFrame with rules (must have 'rule' column, sorted by priority)
            progress_callback: Progress callback function(current, total)
            
        Returns:
            Tuple of:
            - DataFrame with amount analysis results merged
            - Summary dict with cumulative amount metrics
        """
        self._ensure_fitted()
        
        # Get individual rule analysis
        merged_df = self.analyze(rule_df, progress_callback)
        
        # Calculate cumulative metrics
        df = self._df
        target_col = self._target_col
        amount_col = self.amount_col
        rule_ls = rule_df['rule'].tolist()
        
        cum_hit_amount = 0
        cum_bad_amount = 0
        hit_sample_indices: set = set()
        
        for rule in rule_ls:
            try:
                # Use safe rule evaluation instead of eval()
                rule_hit = _safe_eval_rule(df, rule, 'df')
                rule_hit_indices = set(df[rule_hit].index.tolist())
                
                # New hits only (for cumulative)
                new_hit_indices = rule_hit_indices - hit_sample_indices
                hit_sample_indices.update(rule_hit_indices)
                
                if new_hit_indices:
                    new_hit_list = list(new_hit_indices)
                    cum_hit_amount += df.loc[new_hit_list, amount_col].sum()
                    
                    bad_in_new = df.loc[new_hit_list][df.loc[new_hit_list, target_col] == 1]
                    cum_bad_amount += bad_in_new[amount_col].sum()
            except Exception:
                continue
        
        summary = {
            'enabled': True,
            'amount_col': self.amount_col,
            'total_amount': round(self._total_amount, 2),
            'total_bad_amount': round(self._total_bad_amount, 2),
            'overall_amount_bad_rate': round(self._overall_amount_bad_rate, 4),
            'cumulative': {
                'cum_hit_amount': round(cum_hit_amount, 2),
                'cum_bad_amount': round(cum_bad_amount, 2),
                'cum_hit_amount_pct': round(cum_hit_amount / self._total_amount, 4) if self._total_amount > 0 else 0,
                'amount_recall': round(cum_bad_amount / self._total_bad_amount, 4) if self._total_bad_amount > 0 else 0
            }
        }
        
        return merged_df, summary
    
    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of amount analysis configuration.
        
        Returns:
            Dictionary with amount analysis metrics and configuration
        """
        self._ensure_fitted()
        
        return {
            'enabled': True,
            'amount_col': self.amount_col,
            'total_amount': round(self._total_amount, 2),
            'total_bad_amount': round(self._total_bad_amount, 2),
            'overall_amount_bad_rate': round(self._overall_amount_bad_rate, 4)
        }


class RuleSelector:
    """
    Optimal rule set selector using greedy algorithm.
    
    Selects the best rule set that maximizes bad rate capture within hit rate limit.
    Supports multi-objective constraints including recall, precision, and lift targets.
    """
    
    def select_optimal_rules(
        self,
        df: pd.DataFrame,
        rule_df: pd.DataFrame,
        target_col: str = 'target',
        weight_col: str | None = None,
        # 业务目标约束
        max_hit_rate: float = 0.1,
        # 规则集级别风险目标约束
        min_recall_ruleset: float | None = None,
        min_bad_rate_ruleset: float | None = None,
        target_bad_rate_ruleset: float | None = None,  # 目标坏账率（规则集）- 策略应用后的目标坏账率
        min_lift_ruleset: float | None = None,
        # 其他参数
        allow_overlap: bool = True,
        var_name_dict: dict[str, str] | None = None,
        progress_callback: ProgressCallback = None
    ) -> pd.DataFrame:
        """
        Select optimal rule set with multi-objective constraints.
        
        Supports two modes:
        - allow_overlap=True (default): Independent selection, rules may overlap on same samples
        - allow_overlap=False: Greedy algorithm, remove hit samples after each selection
        
        Algorithm (Greedy mode, allow_overlap=False):
        1. Sort rules by bad rate (descending)
        2. Select rule with highest bad rate
        3. Remove samples hit by selected rule
        4. Repeat until cumulative hit rate exceeds limit
        
        Algorithm (Overlap mode, allow_overlap=True):
        1. Sort rules by bad rate (descending)
        2. Select rules in order until cumulative hit rate exceeds limit
        3. Rules may hit overlapping samples
        
        Multi-objective constraints (v2.0, v2.1):
        - max_hit_rate: Hard constraint, stop when exceeded (业务目标)
        - min_recall_ruleset: Soft target, continue adding rules if not met (风险覆盖目标)
        - min_bad_rate_ruleset: Soft target, continue adding rules if not met (最低坏账率)
        - target_bad_rate_ruleset: Auto-calculate min_recall based on target bad rate (目标坏账率)
        - min_lift_ruleset: Soft target, continue adding rules if not met (提升度目标)
        
        Args:
            df: Input dataframe
            rule_df: DataFrame with evaluated rules
            target_col: Target column name
            weight_col: Sample weight column name (optional, None for no weighting)
            max_hit_rate: Maximum cumulative hit rate limit (hard constraint)
            min_recall_ruleset: Minimum recall target for rule set (optional, soft target)
            min_bad_rate_ruleset: Minimum bad_rate target for rule set (optional, soft target)
            target_bad_rate_ruleset: Target bad rate after applying rules (optional, auto-calculates min_recall)
            min_lift_ruleset: Minimum lift target for rule set (optional, soft target)
            allow_overlap: Whether to allow rule overlap (True=independent, False=greedy)
            var_name_dict: Optional dict for variable name mapping
            progress_callback: Optional callback function(current, total) for progress
            
        Returns:
            DataFrame with optimal rule set and cumulative metrics
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        mode_str = "允许重叠" if allow_overlap else "贪婪算法"
        _logger.info(f"[select_optimal_rules] 开始选择最优规则集 (模式: {mode_str})")
        _logger.info(f"[select_optimal_rules] 输入规则数: {len(rule_df)}, 最大命中率（规则集）: {max_hit_rate}")
        _logger.info(f"[select_optimal_rules] 风险目标: min_recall={min_recall_ruleset}, min_bad_rate={min_bad_rate_ruleset}, target_bad_rate={target_bad_rate_ruleset}, min_lift={min_lift_ruleset}")
        
        dev_df = df.copy()
        rule_ls = rule_df.rule.tolist()
        
        # Handle weight column - create default if not provided
        actual_weight_col: str
        if weight_col is None or weight_col not in dev_df.columns:
            dev_df['_weight_'] = 1
            actual_weight_col = '_weight_'
        else:
            actual_weight_col = weight_col
        
        # Calculate totals
        total_dev_weight = dev_df[actual_weight_col].sum()
        total_dev_bad = dev_df.loc[dev_df[target_col] == 1, actual_weight_col].sum()
        total_dev_bad_rate = total_dev_bad / total_dev_weight
        
        # ===== 目标坏账率自动转换为召回率 =====
        # 公式推导: new_bad_rate = original_bad_rate * (1 - recall) / (1 - hit_rate)
        # 解出: recall = 1 - (target_bad_rate / original_bad_rate) * (1 - max_hit_rate)
        effective_min_recall = min_recall_ruleset
        if target_bad_rate_ruleset is not None and total_dev_bad_rate > 0:
            if target_bad_rate_ruleset >= total_dev_bad_rate:
                _logger.warning(f"[select_optimal_rules] 目标坏账率{target_bad_rate_ruleset:.4f} >= 原始坏账率{total_dev_bad_rate:.4f}，无需规则干预")
            else:
                # 计算达到目标坏账率所需的最低召回率
                calculated_recall = 1 - (target_bad_rate_ruleset / total_dev_bad_rate) * (1 - max_hit_rate)
                calculated_recall = max(0, min(1, calculated_recall))  # 限制在[0,1]范围
                _logger.info(f"[select_optimal_rules] 目标坏账率{target_bad_rate_ruleset:.4f} -> 计算所需召回率: {calculated_recall:.4f}")
                _logger.info(f"[select_optimal_rules] 推导公式: recall = 1 - ({target_bad_rate_ruleset:.4f} / {total_dev_bad_rate:.4f}) * (1 - {max_hit_rate})")
                
                # 如果用户也设置了 min_recall_ruleset，取较大值
                if effective_min_recall is not None:
                    if calculated_recall > effective_min_recall:
                        _logger.info(f"[select_optimal_rules] 目标坏账率推导的召回率{calculated_recall:.4f} > 用户设置的{effective_min_recall:.4f}，采用较大值")
                    effective_min_recall = max(effective_min_recall, calculated_recall)
                else:
                    effective_min_recall = calculated_recall
                
                _logger.info(f"[select_optimal_rules] 最终有效召回率目标: {effective_min_recall:.4f}")
        
        def check_targets_met(cum_bad_num: float, cum_hit_num: float) -> tuple[bool, dict[str, Any], bool]:
            """检查风险目标是否达成
            
            Returns:
                tuple: (all_soft_targets_met, targets_status, hard_constraint_violated)
                - all_soft_targets_met: 所有软目标是否达成
                - targets_status: 各目标详细状态
                - hard_constraint_violated: 硬约束是否被违反（max_bad_rate_ruleset）
            """
            targets_status: dict[str, Any] = {}
            all_met = True
            hard_violated = False
            
            # 计算当前指标
            current_recall = cum_bad_num / total_dev_bad if total_dev_bad > 0 else 0
            current_precision = cum_bad_num / cum_hit_num if cum_hit_num > 0 else 0
            current_lift = current_precision / total_dev_bad_rate if total_dev_bad_rate > 0 else 0
            
            # 检查召回率目标（软目标）- 包含目标坏账率转换后的召回率
            if effective_min_recall is not None:
                met = current_recall >= effective_min_recall
                targets_status['recall'] = {'target': effective_min_recall, 'current': round(current_recall, 4), 'met': met, 'type': 'min', 'from_target_bad_rate': target_bad_rate_ruleset is not None}
                if not met:
                    all_met = False
            
            # 检查最低坏账率目标（软目标）
            if min_bad_rate_ruleset is not None:
                met = current_precision >= min_bad_rate_ruleset
                targets_status['min_bad_rate'] = {'target': min_bad_rate_ruleset, 'current': round(current_precision, 4), 'met': met, 'type': 'min'}
                if not met:
                    all_met = False
            
            # 目标坏账率检查（通过召回率间接实现）
            # target_bad_rate_ruleset 已在函数开始时转换为 min_recall_ruleset
            # 这里只记录目标坏账率的达成状态供参考
            if target_bad_rate_ruleset is not None:
                # 估算当前策略应用后的坏账率
                # 公式: new_bad_rate = original_bad_rate * (1 - recall) / (1 - hit_rate)
                current_hit_rate = cum_hit_num / total_dev_weight if total_dev_weight > 0 else 0
                if current_hit_rate < 1:
                    estimated_bad_rate = total_dev_bad_rate * (1 - current_recall) / (1 - current_hit_rate)
                else:
                    estimated_bad_rate = 0
                met = estimated_bad_rate <= target_bad_rate_ruleset
                targets_status['target_bad_rate'] = {'target': target_bad_rate_ruleset, 'current': round(estimated_bad_rate, 4), 'met': met, 'type': 'target'}
                # 目标坏账率不作为硬约束，而是通过召回率软目标实现
            
            # 检查提升度目标（软目标）
            if min_lift_ruleset is not None:
                met = current_lift >= min_lift_ruleset
                targets_status['lift'] = {'target': min_lift_ruleset, 'current': round(current_lift, 4), 'met': met, 'type': 'min'}
                if not met:
                    all_met = False
            
            return all_met, targets_status, hard_violated
        
        if allow_overlap:
            # ========== 允许重叠模式 ==========
            # 按坏账率排序，依次选择规则直到累计命中率超过阈值
            # 规则之间可以命中相同的样本
            
            # 性能优化：直接使用 rule_df 中已有的 bad_rate 列排序，避免重复计算
            # rule_df 在 rule_filtering 阶段已经计算过每条规则的 bad_rate
            rule_badrates = []
            has_bad_rate_col = 'bad_rate' in rule_df.columns
            
            if has_bad_rate_col:
                # 优化路径：使用已有的 bad_rate 列
                _logger.info(f"[select_optimal_rules] 使用已有 bad_rate 列排序（优化模式）")
                for idx, row in rule_df.iterrows():
                    rule = row['rule']
                    bad_rate = float(row.get('bad_rate', 0)) if pd.notna(row.get('bad_rate')) else 0
                    # hit_total 和 hit_bad 在选择阶段会重新计算，这里只用于排序
                    rule_badrates.append((rule, bad_rate, 0, 0))
            else:
                # 兼容路径：重新计算 bad_rate（当 rule_df 没有 bad_rate 列时）
                _logger.info(f"[select_optimal_rules] 重新计算 bad_rate（兼容模式）")
                for rule in rule_ls:
                    try:
                        # Use safe rule evaluation instead of eval()
                        rule_hit = _safe_eval_rule(dev_df, rule, 'dev_df')
                        hit_bad = dev_df.loc[rule_hit & (dev_df[target_col] == 1), actual_weight_col].sum()
                        hit_total = dev_df.loc[rule_hit, actual_weight_col].sum()
                        bad_rate = hit_bad / hit_total if hit_total > 0 else 0
                        rule_badrates.append((rule, bad_rate, hit_total, hit_bad))
                    except Exception:
                        rule_badrates.append((rule, 0, 0, 0))
            
            # 按坏账率降序排序
            rule_badrates.sort(key=lambda x: x[1], reverse=True)
            
            # 使用集合追踪已命中的样本索引，计算真实累计命中率
            hit_sample_indices: set = set()
            cum_dev_hit_num, cum_dev_bad_num = 0.0, 0.0
            final_rule_ls = []
            cum_dev_hitrate_ls, cum_dev_badrate_ls = [], []
            iteration = 0
            
            for rule, bad_rate, hit_total, hit_bad in rule_badrates:
                if bad_rate == 0:
                    continue
                
                try:
                    # 获取当前规则命中的样本索引 - 使用安全的规则评估
                    rule_hit_mask = _safe_eval_rule(dev_df, rule, 'dev_df')
                    rule_hit_indices = set(dev_df[rule_hit_mask].index.tolist())
                    
                    # 计算新增命中的样本（去重后）
                    new_hit_indices = rule_hit_indices - hit_sample_indices
                    overlap_count = len(rule_hit_indices) - len(new_hit_indices)
                    _logger.info(f"[allow_overlap] 规则命中: {len(rule_hit_indices)}, 新增: {len(new_hit_indices)}, 重叠: {overlap_count}")
                    new_hit_weight = dev_df.loc[list(new_hit_indices), actual_weight_col].sum() if new_hit_indices else 0
                    
                    # 计算新的累计命中率
                    new_cum_hit_num = cum_dev_hit_num + new_hit_weight
                    new_cum_hit_rate = new_cum_hit_num / total_dev_weight
                    
                    # 计算新增的坏样本（提前计算，用于目标检查）
                    new_bad_indices = new_hit_indices & set(dev_df[dev_df[target_col] == 1].index.tolist())
                    new_bad_weight = dev_df.loc[list(new_bad_indices), actual_weight_col].sum() if new_bad_indices else 0
                    new_cum_bad_num = cum_dev_bad_num + new_bad_weight
                    
                    # 目标坏账率通过召回率约束实现，不再作为硬约束检查
                    # target_bad_rate_ruleset 已在函数开始时转换为 effective_min_recall
                    
                    # 检查是否应该停止（多目标约束 v2.0）
                    if new_cum_hit_rate > max_hit_rate:
                        # 命中率超限，检查风险目标是否已达成
                        targets_met, targets_status, _ = check_targets_met(cum_dev_bad_num, cum_dev_hit_num)
                        if targets_met or not any([effective_min_recall, min_bad_rate_ruleset, min_lift_ruleset]):
                            # 目标已达成或没有设置目标，停止选择
                            _logger.info(f"[select_optimal_rules] 停止选择: 累计命中率{new_cum_hit_rate:.4f} > 阈值{max_hit_rate}")
                            _logger.info(f"[select_optimal_rules] 已选规则数: {len(final_rule_ls)}, 目标达成状态: {targets_status}")
                            break
                        else:
                            # 目标未达成，记录警告但仍停止（命中率是硬约束）
                            _logger.warning(f"[select_optimal_rules] 命中率超限但目标未达成: {targets_status}")
                            _logger.info(f"[select_optimal_rules] 停止选择: 累计命中率{new_cum_hit_rate:.4f} > 阈值{max_hit_rate} (硬约束)")
                            break
                    
                    # 更新累计值
                    hit_sample_indices.update(rule_hit_indices)
                    cum_dev_hit_num = new_cum_hit_num
                    cum_dev_bad_num = new_cum_bad_num
                    
                    final_rule_ls.append(rule)
                    cum_dev_hitrate_ls.append(cum_dev_hit_num)
                    cum_dev_badrate_ls.append(cum_dev_bad_num)
                    
                    # 检查风险目标达成状态
                    targets_met, targets_status, _ = check_targets_met(cum_dev_bad_num, cum_dev_hit_num)
                    _logger.info(f"[select_optimal_rules] 选中第{len(final_rule_ls)}条规则, 累计命中率: {cum_dev_hit_num/total_dev_weight:.4f}, 规则坏账率: {bad_rate:.4f}, 目标状态: {targets_status}")
                    
                    iteration += 1
                    if progress_callback:
                        progress_callback(iteration, len(rule_df))
                        
                except Exception as e:
                    _logger.warning(f"[select_optimal_rules] 规则处理异常: {rule}, 错误: {e}")
                    continue
            
            # 记录最终目标达成状态
            final_targets_met, final_targets_status, _ = check_targets_met(cum_dev_bad_num, cum_dev_hit_num)
            _logger.info(f"[select_optimal_rules] 选择完成: 共选中{len(final_rule_ls)}条规则, 最终目标状态: {final_targets_status}")
            
        else:
            # ========== 贪婪算法模式（不允许重叠） ==========
            # 选中一条规则后，移除其命中的样本，剩余规则在剩余样本上重新计算坏账率
            
            cum_dev_hit_num, cum_dev_bad_num = 0.0, 0.0
            final_rule_ls = []
            cum_dev_hitrate_ls, cum_dev_badrate_ls = [], []
            iteration = 0
            # 记录因样本消耗导致坏账率变为0的规则（用于淘汰原因判断）
            self._greedy_exhausted_rules: set[str] = set()
            
            while len(rule_ls) > 0:
                # Find rule with max bad rate on remaining samples
                tmp_badrate_ls = []
                for rule in rule_ls:
                    try:
                        # Use safe rule evaluation instead of eval()
                        rule_hit = _safe_eval_rule(dev_df, rule, 'dev_df')
                        hit_bad = dev_df.loc[rule_hit & (dev_df[target_col] == 1), actual_weight_col].sum()
                        hit_total = dev_df.loc[rule_hit, actual_weight_col].sum()
                        tmp_badrate_ls.append(hit_bad / hit_total if hit_total > 0 else 0)
                    except Exception:
                        tmp_badrate_ls.append(0)
                
                if max(tmp_badrate_ls) == 0:
                    _logger.info(f"[select_optimal_rules] 停止选择: 剩余{len(rule_ls)}条规则在剩余样本上坏账率均为0")
                    _logger.info(f"[select_optimal_rules] 已选规则数: {len(final_rule_ls)}, 剩余样本数: {len(dev_df)}")
                    # 记录这些规则为"样本被消耗"类型
                    self._greedy_exhausted_rules = set(str(r) for r in rule_ls)
                    break
                
                rule = rule_ls[tmp_badrate_ls.index(max(tmp_badrate_ls))]
                
                # Remove used rule
                rule_ls.remove(rule)
                
                # Check if cumulative hit rate exceeds limit
                try:
                    # Use safe rule evaluation instead of eval()
                    rule_hit = _safe_eval_rule(dev_df, rule, 'dev_df')
                    new_dev_hit_num = cum_dev_hit_num + dev_df.loc[rule_hit, actual_weight_col].sum()
                    new_dev_bad_num = cum_dev_bad_num + dev_df.loc[rule_hit & (dev_df[target_col] == 1), actual_weight_col].sum()
                except Exception:
                    continue
                
                # 目标坏账率通过召回率约束实现，不再作为硬约束检查
                # target_bad_rate_ruleset 已在函数开始时转换为 effective_min_recall
                
                new_cum_hit_rate = new_dev_hit_num / total_dev_weight
                if new_cum_hit_rate > max_hit_rate:
                    # 检查风险目标是否已达成
                    targets_met, targets_status, _ = check_targets_met(cum_dev_bad_num, cum_dev_hit_num)
                    _logger.info(f"[select_optimal_rules] 停止选择: 累计命中率{new_cum_hit_rate:.4f} > 阈值{max_hit_rate}")
                    _logger.info(f"[select_optimal_rules] 已选规则数: {len(final_rule_ls)}, 目标状态: {targets_status}")
                    break
                
                # Calculate cumulative metrics
                cum_dev_hit_num = new_dev_hit_num
                cum_dev_bad_num = new_dev_bad_num
                
                final_rule_ls.append(rule)
                cum_dev_hitrate_ls.append(cum_dev_hit_num)
                cum_dev_badrate_ls.append(cum_dev_bad_num)
                
                # 检查风险目标达成状态
                targets_met, targets_status, _ = check_targets_met(cum_dev_bad_num, cum_dev_hit_num)
                _logger.info(f"[select_optimal_rules] 选中第{len(final_rule_ls)}条规则, 累计命中率: {cum_dev_hit_num/total_dev_weight:.4f}, 目标状态: {targets_status}")
                
                # Remove hit samples - use safe evaluation
                try:
                    rule_hit = _safe_eval_rule(dev_df, rule, 'dev_df')
                    dev_df = dev_df[~rule_hit]
                except Exception:
                    pass
                
                iteration += 1
                if progress_callback:
                    progress_callback(iteration, len(rule_df))
        
        # ========== 目标回溯优化阶段 (v2.2) ==========
        # 当风控目标（提升度/坏账率）未达成时，从后往前移除规则尝试逼近目标
        # 
        # 【重要】两种模式的差异处理：
        # 1. 允许重叠模式：规则按原始坏账率排序，移除末尾规则（坏账率较低）可提高整体提升度
        # 2. 贪婪算法模式：每轮选当前最高坏账率，移除末尾规则不一定能提高提升度
        #    - 因为后选的规则在"剩余样本"上计算，可能坏账率实际很高
        #    - 但从累计指标角度，后选规则的边际贡献通常较低，仍可尝试优化
        # 
        # 注意：召回率目标通过增加规则实现，减少规则会降低召回率，因此不在此优化范围内
        
        def recalculate_cumulative_metrics(rules_list: list, hitrate_list: list, badrate_list: list) -> tuple:
            """重新计算累计指标"""
            if len(rules_list) == 0:
                return 0.0, 0.0, 0.0, 0.0
            final_cum_hit = hitrate_list[-1] if hitrate_list else 0
            final_cum_bad = badrate_list[-1] if badrate_list else 0
            cum_hit_rate = final_cum_hit / total_dev_weight if total_dev_weight > 0 else 0
            cum_bad_rate = final_cum_bad / final_cum_hit if final_cum_hit > 0 else 0
            cum_recall = final_cum_bad / total_dev_bad if total_dev_bad > 0 else 0
            cum_lift = cum_bad_rate / total_dev_bad_rate if total_dev_bad_rate > 0 else 0
            return cum_hit_rate, cum_bad_rate, cum_recall, cum_lift
        
        # 检查是否需要回溯优化
        need_backtrack = False
        backtrack_target_type = None  # 'lift' 或 'bad_rate'
        
        if len(final_rule_ls) > 1:
            # 检查最终目标达成状态
            final_targets_met, final_targets_status, _ = check_targets_met(cum_dev_bad_num, cum_dev_hit_num)
            
            if not final_targets_met:
                # 判断是否是提升度或坏账率目标未达成（这些目标可以通过减少规则来改善）
                if 'lift' in final_targets_status and not final_targets_status['lift']['met']:
                    need_backtrack = True
                    backtrack_target_type = 'lift'
                    _logger.info(f"[select_optimal_rules] 提升度目标未达成 (目标: {min_lift_ruleset}, 当前: {final_targets_status['lift']['current']}), 启动回溯优化")
                elif 'min_bad_rate' in final_targets_status and not final_targets_status['min_bad_rate']['met']:
                    need_backtrack = True
                    backtrack_target_type = 'bad_rate'
                    _logger.info(f"[select_optimal_rules] 坏账率目标未达成 (目标: {min_bad_rate_ruleset}, 当前: {final_targets_status['min_bad_rate']['current']}), 启动回溯优化")
        
        if need_backtrack:
            original_rule_count = len(final_rule_ls)
            best_rule_count = original_rule_count
            best_metrics = recalculate_cumulative_metrics(final_rule_ls, cum_dev_hitrate_ls, cum_dev_badrate_ls)
            best_gap = float('inf')  # 与目标的差距
            
            # 计算初始差距
            if backtrack_target_type == 'lift' and min_lift_ruleset:
                best_gap = max(0, min_lift_ruleset - best_metrics[3])  # [3] = cum_lift
            elif backtrack_target_type == 'bad_rate' and min_bad_rate_ruleset:
                best_gap = max(0, min_bad_rate_ruleset - best_metrics[1])  # [1] = cum_bad_rate
            
            # 根据模式选择不同的回溯策略
            # 【注意】两种模式都使用全量搜索，因为：
            # - 允许重叠模式：累计指标不是单调的（新规则可能高度重叠导致边际贡献不确定）
            # - 贪婪算法模式：规则选择顺序动态变化
            
            if allow_overlap:
                # ===== 允许重叠模式：全量搜索最优前缀 =====
                # 虽然规则按原始坏账率排序，但累计指标是去重后计算的，不保证单调
                _logger.info(f"[backtrack] 允许重叠模式: 开始全量搜索优化, 初始规则数: {original_rule_count}, 目标类型: {backtrack_target_type}, 初始差距: {best_gap:.4f}")
                
                # 遍历所有可能的规则数（从n-1到1）
                for target_count in range(original_rule_count - 1, 0, -1):
                    test_hitrate_ls = cum_dev_hitrate_ls[:target_count]
                    test_badrate_ls = cum_dev_badrate_ls[:target_count]
                    
                    # 重新计算指标
                    new_metrics = recalculate_cumulative_metrics(final_rule_ls[:target_count], test_hitrate_ls, test_badrate_ls)
                    new_hit_rate, new_bad_rate, new_recall, new_lift = new_metrics
                    
                    # 计算新的差距
                    new_gap = float('inf')
                    if backtrack_target_type == 'lift' and min_lift_ruleset:
                        new_gap = max(0, min_lift_ruleset - new_lift)
                    elif backtrack_target_type == 'bad_rate' and min_bad_rate_ruleset:
                        new_gap = max(0, min_bad_rate_ruleset - new_bad_rate)
                    
                    _logger.info(f"[backtrack-overlap] 尝试规则数: {target_count}, 提升度: {new_lift:.2f}, 坏账率: {new_bad_rate:.4f}, 命中率: {new_hit_rate:.4f}, 差距: {new_gap:.4f}")
                    
                    # 记录最优解（差距最小）
                    if new_gap < best_gap:
                        best_gap = new_gap
                        best_rule_count = target_count
                        _logger.info(f"[backtrack-overlap] 找到更优解: {best_rule_count}条规则, 差距减少到: {best_gap:.4f}")
                    
                    # 如果已经达成目标，停止
                    if new_gap == 0:
                        _logger.info(f"[backtrack-overlap] 目标已达成, 最优规则数: {best_rule_count}")
                        break
            else:
                # ===== 贪婪算法模式：全量搜索最优子集 =====
                # 贪婪模式下规则选择顺序不完全按坏账率，需要遍历所有可能的前缀子集
                _logger.info(f"[backtrack] 贪婪算法模式: 开始全量搜索优化, 初始规则数: {original_rule_count}, 目标类型: {backtrack_target_type}, 初始差距: {best_gap:.4f}")
                
                # 遍历所有可能的规则数（从n-1到1）
                for target_count in range(original_rule_count - 1, 0, -1):
                    test_hitrate_ls = cum_dev_hitrate_ls[:target_count]
                    test_badrate_ls = cum_dev_badrate_ls[:target_count]
                    
                    # 重新计算指标
                    new_metrics = recalculate_cumulative_metrics(final_rule_ls[:target_count], test_hitrate_ls, test_badrate_ls)
                    new_hit_rate, new_bad_rate, new_recall, new_lift = new_metrics
                    
                    # 计算新的差距
                    new_gap = float('inf')
                    if backtrack_target_type == 'lift' and min_lift_ruleset:
                        new_gap = max(0, min_lift_ruleset - new_lift)
                    elif backtrack_target_type == 'bad_rate' and min_bad_rate_ruleset:
                        new_gap = max(0, min_bad_rate_ruleset - new_bad_rate)
                    
                    _logger.info(f"[backtrack-greedy] 尝试规则数: {target_count}, 提升度: {new_lift:.2f}, 坏账率: {new_bad_rate:.4f}, 命中率: {new_hit_rate:.4f}, 差距: {new_gap:.4f}")
                    
                    # 记录最优解（差距最小）
                    if new_gap < best_gap:
                        best_gap = new_gap
                        best_rule_count = target_count
                        _logger.info(f"[backtrack-greedy] 找到更优解: {best_rule_count}条规则, 差距减少到: {best_gap:.4f}")
                    
                    # 如果已经达成目标，停止
                    if new_gap == 0:
                        _logger.info(f"[backtrack-greedy] 目标已达成, 最优规则数: {best_rule_count}")
                        break
            
            # 应用最优解
            if best_rule_count < original_rule_count:
                removed_count = original_rule_count - best_rule_count
                final_rule_ls = final_rule_ls[:best_rule_count]
                cum_dev_hitrate_ls = cum_dev_hitrate_ls[:best_rule_count]
                cum_dev_badrate_ls = cum_dev_badrate_ls[:best_rule_count]
                
                # 更新累计值
                cum_dev_hit_num = cum_dev_hitrate_ls[-1] if cum_dev_hitrate_ls else 0
                cum_dev_bad_num = cum_dev_badrate_ls[-1] if cum_dev_badrate_ls else 0
                
                final_metrics = recalculate_cumulative_metrics(final_rule_ls, cum_dev_hitrate_ls, cum_dev_badrate_ls)
                _logger.info(f"[backtrack] 回溯优化完成: 移除{removed_count}条规则 ({original_rule_count} -> {best_rule_count})")
                _logger.info(f"[backtrack] 优化后指标: 命中率={final_metrics[0]:.4f}, 坏账率={final_metrics[1]:.4f}, 召回率={final_metrics[2]:.4f}, 提升度={final_metrics[3]:.2f}")
            else:
                _logger.info(f"[backtrack] 回溯优化未能改善目标, 保持原规则数: {original_rule_count}")
        
        # Build result DataFrame
        cum_df = pd.DataFrame({
            'rule': final_rule_ls,
            'dev_cum_recall': cum_dev_badrate_ls,
            'dev_cum_bad_rate': cum_dev_badrate_ls,
            'dev_cum_lift': cum_dev_badrate_ls,
            'dev_cum_hit_rate': cum_dev_hitrate_ls
        })
        
        if len(cum_df) > 0:
            cum_df['dev_cum_recall'] = round(cum_df['dev_cum_recall'] / total_dev_bad, 4)
            cum_df['dev_cum_bad_rate'] = round(
                cum_df['dev_cum_bad_rate'] / cum_df['dev_cum_hit_rate'], 4
            )
            cum_df['dev_cum_lift'] = round(
                cum_df['dev_cum_bad_rate'] / total_dev_bad_rate, 1
            )
            cum_df['dev_cum_hit_rate'] = round(
                cum_df['dev_cum_hit_rate'] / total_dev_weight, 4
            )
        
        # Merge with original rule info
        # Ensure rule column types match (both as string) to avoid merge errors
        # Phase: 保留单条规则的原始指标（hit_rate, recall, bad_rate），与累计指标区分
        merge_cols = ['used_var', 'rule', 'lift']
        # 添加单条规则的原始指标列（如果存在）
        for col in ['hit_rate', 'recall', 'bad_rate']:
            if col in rule_df.columns:
                merge_cols.append(col)
        if var_name_dict and 'rule_chinese' in rule_df.columns:
            merge_cols.insert(2, 'rule_chinese')
        
        # Convert rule columns to string type to ensure consistent merge
        rule_df_subset = rule_df[merge_cols].copy()
        rule_df_subset['rule'] = rule_df_subset['rule'].astype(str)
        cum_df['rule'] = cum_df['rule'].astype(str)
        
        return rule_df_subset.merge(
            cum_df, how='inner', on='rule'
        ).sort_values(['dev_cum_hit_rate']).reset_index(drop=True)


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
        min_lift = discrimination.get('min_lift', 0)
        
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


class RuleInterpreter:
    """
    规则业务解读器
    
    将规则表达式转换为更易理解的业务解读文本
    """
    
    # 运算符映射
    OPERATOR_MAP: dict[str, str] = {
        '<=': '不超过',
        '>=': '不低于',
        '<': '小于',
        '>': '大于',
        '==': '等于',
        '!=': '不等于',
        '&': '且',
        '|': '或'
    }
    
    def __init__(
        self,
        var_name_dict: dict[str, str] | None = None,
        var_desc_dict: dict[str, str] | None = None,
        default_template: str = "{var_name}{operator}{value}"
    ):
        """
        初始化规则解读器
        
        Args:
            var_name_dict: 变量名映射字典 (如 {'age': '年龄', 'income': '收入'})
            var_desc_dict: 变量描述字典 (如 {'age': '用户年龄（岁）'})
            default_template: 默认解读模板
        """
        self.var_name_dict = var_name_dict or {}
        self.var_desc_dict = var_desc_dict or {}
        self.default_template = default_template
    
    def interpret(
        self,
        rule: str,
        var_name_dict: dict[str, str] | None = None,
        var_desc_dict: dict[str, str] | None = None
    ) -> str:
        """
        将规则转换为业务可读的解读文本
        
        Args:
            rule: 规则表达式 (如 "(age <= 25) & (income <= 5000)")
            var_name_dict: 变量名映射字典（覆盖实例级别）
            var_desc_dict: 变量描述字典（覆盖实例级别）
            
        Returns:
            业务解读文本 (如 "年龄不超过25 且 收入不超过5000的用户")
        """
        name_dict = var_name_dict or self.var_name_dict
        
        # 解析规则
        interpreted_parts: list[str] = []
        
        # 分割条件（按 & 和 |）
        # 简单实现：按 & 分割
        conditions = re.split(r'\s*&\s*', rule)
        
        for condition in conditions:
            interpreted = self._interpret_condition(condition.strip(), name_dict)
            if interpreted:
                interpreted_parts.append(interpreted)
        
        if not interpreted_parts:
            return rule  # 无法解读，返回原规则
        
        return ' 且 '.join(interpreted_parts) + '的用户'
    
    def _interpret_condition(
        self,
        condition: str,
        name_dict: dict[str, str]
    ) -> str:
        """解读单个条件"""
        # 去除括号
        condition = condition.strip('()')
        
        # 匹配模式：变量名 运算符 值
        patterns = [
            (r'(\w+)\s*<=\s*([\d.]+)', '不超过'),
            (r'(\w+)\s*>=\s*([\d.]+)', '不低于'),
            (r'(\w+)\s*<\s*([\d.]+)', '小于'),
            (r'(\w+)\s*>\s*([\d.]+)', '大于'),
            (r'(\w+)\s*==\s*([\d.]+)', '等于'),
            (r'(\w+)\s*!=\s*([\d.]+)', '不等于'),
            (r'(\w+)\s*==\s*["\']([^"\']+)["\']', '为'),
            (r'(\w+)\s*!=\s*["\']([^"\']+)["\']', '不为'),
        ]
        
        for pattern, operator_text in patterns:
            match = re.match(pattern, condition)
            if match:
                var_name = match.group(1)
                value = match.group(2)
                
                # 获取中文变量名
                display_name = name_dict.get(var_name, var_name)
                
                return f"{display_name}{operator_text}{value}"
        
        # 无法匹配，返回原条件
        return condition
    
    def interpret_rules_batch(
        self,
        rules_df: pd.DataFrame,
        var_name_dict: dict[str, str] | None = None
    ) -> pd.DataFrame:
        """
        批量解读规则
        
        Args:
            rules_df: 规则DataFrame，需包含'rule'列
            var_name_dict: 变量名映射字典
            
        Returns:
            添加'rule_interpretation'列的DataFrame
        """
        name_dict = var_name_dict or self.var_name_dict
        
        rules_df = rules_df.copy()
        rules_df['rule_interpretation'] = rules_df['rule'].apply(
            lambda r: self.interpret(r, name_dict)
        )
        
        return rules_df


class RuleMiningPipeline:
    """
    Complete rule mining pipeline orchestrator.
    
    Combines DataPreprocessor, FeatureEngineer (optional), RuleMiner/SingleVarRuleMiner, 
    RuleEvaluator, and RuleSelector into a single end-to-end workflow.
    
    Supports two rule mining modes:
    - 'single': Single variable rules (threshold-based, no decision tree)
    - 'multi': Multi-variable combination rules (decision tree-based)
    
    Workflow:
    0a. Data Preprocessing - Feature name mapping, drop useless columns, One-Hot encoding
    0b. [Optional] Feature Engineering - Missing handling, IV calculation, variable selection
    1. Rule Generation - Generate candidate rules (single-var or multi-var)
    2. Rule Filtering - Filter rules by direction and validity
    3. Rule Evaluation - Calculate recall, bad_rate, lift, hit_rate
    4. Rule Selection - Select optimal rule set using greedy algorithm
    """
    
    def __init__(
        self,
        # Rule mining mode
        mining_mode: str = 'multi',
        # Data preprocessing parameters
        id_cols: list[str] | None = None,
        drop_cols: list[str] | None = None,
        name_mapping: dict[str, str] | None = None,
        categorical_cols: list[str] | None = None,
        force_categorical: list[str] | None = None,
        force_numeric: list[str] | None = None,
        # Feature engineering parameters (optional)
        enable_feature_engineering: bool = False,
        missing_threshold: float = 0.5,
        iv_threshold: float = 0.02,
        special_values: list[float] | None = None,
        # Single-var rule generation parameters
        n_bins: int = 10,
        bin_method: str = 'quantile',
        rule_directions: str = 'both',
        # Multi-var rule generation parameters
        use_full_tree: bool = False,  # 默认使用组合树，规则更丰富
        min_samples_leaf: float = 0.005,  # 降低默认值，允许生成更多规则
        max_depth: int = 5,
        n_vars: int = 3,
        max_onehot_vars: int = 2,
        # Rule filtering parameters (单条规则筛选)
        max_hit_rate_filter: float = 0.10,
        min_lift_filter: float = 2.0,
        # Rule selection parameters (规则集选择)
        max_hit_rate_select: float = 0.20,
        allow_overlap: bool = True,
        # 规则集级别风险目标参数
        min_recall_ruleset: float | None = None,
        min_bad_rate_ruleset: float | None = None,
        target_bad_rate_ruleset: float | None = None,  # 目标坏账率（规则集）- 策略应用后的目标坏账率
        min_lift_ruleset: float | None = None,
        onehot_indicator: str = '_is_',
        # Progress callback (for executor integration)
        progress_callback: StageProgressCallback = None,
        # Stop check callback (for executor integration)
        stop_check_callback: Callable[[], bool] | None = None
    ):
        """
        Initialize pipeline with configuration.
        
        Args:
            mining_mode: Rule mining mode - 'single' (single variable) or 'multi' (multi-variable combination)
            id_cols: ID columns to drop (e.g., ['fuuid', 'user_id'])
            drop_cols: Additional columns to drop
            name_mapping: Feature name mapping dict (e.g., {'f0': 'age'})
            categorical_cols: Categorical columns for One-Hot encoding
            force_categorical: User-specified columns to force as categorical (for encoded variables like province codes)
            force_numeric: User-specified columns to force as numeric (not One-Hot encoded).
                          Use this for ordinal numeric features that might be misdetected as 
                          categorical (e.g., account count, transaction count).
            enable_feature_engineering: Whether to enable feature engineering preprocessing
            missing_threshold: Missing rate threshold for dropping variables
            iv_threshold: IV threshold for variable selection
            n_bins: Number of bins for single-var threshold generation
            bin_method: Binning method for single-var - 'quantile', 'uniform', or 'custom'
            rule_directions: Rule directions for single-var - '<=', '>', or 'both'
            use_full_tree: Whether to generate a full-feature decision tree for visualization (multi-var)
            min_samples_leaf: Minimum samples ratio for tree nodes (multi-var)
            max_depth: Maximum tree depth (multi-var)
            n_vars: Variables per combination (multi-var)
            max_onehot_vars: Maximum one-hot variables per combination (multi-var)
            max_hit_rate_filter: Hit rate threshold for single rule filtering
            min_lift_filter: Lift threshold for single rule filtering
            max_hit_rate_select: Hit rate limit for rule set selection (hard constraint)
            allow_overlap: Whether to allow rule overlap (True=independent selection, False=greedy algorithm)
            min_recall_ruleset: Minimum recall target for rule set (optional, soft target)
            min_bad_rate_ruleset: Minimum bad_rate target for rule set (optional, soft target)
            target_bad_rate_ruleset: Target bad rate after applying rules (optional, auto-calculates min_recall)
            min_lift_ruleset: Minimum lift target for rule set (optional, soft target)
            onehot_indicator: String indicator for One-Hot encoded columns
            progress_callback: Progress callback for executor integration
            stop_check_callback: Stop check callback for executor integration
        """
        if mining_mode not in ['single', 'multi']:
            raise ValueError(f"mining_mode must be 'single' or 'multi', got '{mining_mode}'")
        
        self.mining_mode: str = mining_mode
        self.use_full_tree: bool = use_full_tree
        self.enable_feature_engineering: bool = enable_feature_engineering
        self.onehot_indicator: str = onehot_indicator
        self.categorical_cols: list[str] | None = categorical_cols
        self.force_categorical: list[str] | None = force_categorical
        self.force_numeric: list[str] | None = force_numeric
        
        # 保存规则生成参数（用于 output_preview 展示）
        # 多变量模式参数
        self.n_vars: int = n_vars
        self.max_depth: int = max_depth
        self.min_samples_leaf: float = min_samples_leaf
        self.max_onehot_vars: int = max_onehot_vars
        # 单变量模式参数
        self.n_bins: int = n_bins
        self.bin_method: str = bin_method
        self.rule_directions: str = rule_directions
        
        # Full-feature tree for visualization (will be set during rule generation)
        self.full_tree_: Any = None
        self.full_tree_features_: list[str] = []
        
        # Rule source statistics for combination tree mode (will be set during rule generation)
        self.rule_source_stats_: dict[str, Any] | None = None
        
        # Initialize data preprocessor (always enabled)
        self.preprocessor: DataPreprocessor = DataPreprocessor(
            id_cols=id_cols,
            drop_cols=drop_cols,
            name_mapping=name_mapping,
            onehot_indicator=onehot_indicator
        )
        
        # Initialize feature engineer (optional)
        self.feature_engineer: FeatureEngineer | None = FeatureEngineer(
            missing_threshold=missing_threshold,
            iv_threshold=iv_threshold,
            onehot_indicator=onehot_indicator,
            special_values=special_values
        ) if enable_feature_engineering else None
        
        # Initialize rule miner based on mode
        self.miner: SingleVarRuleMiner | RuleMiner
        if mining_mode == 'single':
            self.miner = SingleVarRuleMiner(
                n_bins=n_bins,
                bin_method=bin_method,
                directions=rule_directions
            )
        else:
            self.miner = RuleMiner(
                min_samples_leaf=min_samples_leaf,
                max_depth=max_depth,
                n_vars=n_vars,
                max_onehot_vars=max_onehot_vars
            )
        
        self.evaluator: RuleEvaluator = RuleEvaluator()
        self.selector: RuleSelector = RuleSelector()
        
        self.max_hit_rate_filter: float = max_hit_rate_filter
        self.min_lift_filter: float = min_lift_filter
        self.max_hit_rate_select: float = max_hit_rate_select
        self.allow_overlap: bool = allow_overlap
        # 规则集级别风险目标参数
        self.min_recall_ruleset: float | None = min_recall_ruleset
        self.min_bad_rate_ruleset: float | None = min_bad_rate_ruleset
        self.target_bad_rate_ruleset: float | None = target_bad_rate_ruleset
        self.min_lift_ruleset: float | None = min_lift_ruleset
        self._progress_callback: StageProgressCallback = progress_callback
        self._stop_check_callback: Callable[[], bool] | None = stop_check_callback
        
        # 日志：记录实际使用的参数
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"[RuleMiningPipeline] Initialized with filter params: min_lift={min_lift_filter}, max_hit_rate_filter={max_hit_rate_filter}, max_hit_rate_select={max_hit_rate_select}, allow_overlap={allow_overlap}")
        _logger.info(f"[RuleMiningPipeline] Risk targets: min_recall={min_recall_ruleset}, min_bad_rate={min_bad_rate_ruleset}, target_bad_rate={target_bad_rate_ruleset}, min_lift={min_lift_ruleset}")
        if mining_mode == 'single':
            _logger.info(f"[RuleMiningPipeline] Single-var binning params: n_bins={n_bins}, bin_method={bin_method}, rule_directions={rule_directions}")
    
    def _should_stop(self) -> bool:
        """Check if execution should stop (for expert mode pause support).
        
        Returns:
            True if should stop, False to continue
        """
        if self._stop_check_callback:
            return self._stop_check_callback()
        return False
    
    def _generate_rule_source_stats(self, rules_df: pd.DataFrame, feature_cols: list[str]) -> None:
        """Generate rule source statistics for combination tree mode.
        
        Analyzes which feature combinations produced which rules, providing
        insights into rule origins when decision tree visualization is not applicable.
        
        Args:
            rules_df: DataFrame with 'used_var' and 'rule' columns
            feature_cols: List of all feature column names
        """
        if rules_df.empty or 'used_var' not in rules_df.columns:
            self.rule_source_stats_ = None
            return
        
        # 统计每个特征组合产生的规则数 - 使用value_counts替代iterrows
        combo_counts = rules_df['used_var'].value_counts().to_dict()
        
        # 按规则数排序
        sorted_combos = sorted(combo_counts.items(), key=lambda x: x[1], reverse=True)
        
        # 统计每个特征出现在多少条规则中 - 使用向量化操作
        feature_rule_counts: dict[str, int] = {f: 0 for f in feature_cols}
        rules_list = rules_df['rule'].tolist()
        for feature in feature_cols:
            count = sum(1 for rule in rules_list if feature in rule)
            feature_rule_counts[feature] = count
        
        # 按出现次数排序
        sorted_features = sorted(feature_rule_counts.items(), key=lambda x: x[1], reverse=True)
        # 只保留出现过的特征
        sorted_features = [(f, c) for f, c in sorted_features if c > 0]
        
        self.rule_source_stats_ = {
            "total_rules": len(rules_df),
            "total_combinations": len(combo_counts),
            "combination_stats": [
                {"combination": combo, "rule_count": count, "percentage": round(count / len(rules_df) * 100, 1)}
                for combo, count in sorted_combos  # 展示全部组合（前端有滚动条）
            ],
            "feature_importance": [
                {"feature": feature, "rule_count": count, "percentage": round(count / len(rules_df) * 100, 1)}
                for feature, count in sorted_features  # 展示全部特征（前端有滚动条）
            ]
        }
        
        logger.info(f"[Pipeline] Rule source stats generated: {len(combo_counts)} combinations, {len(sorted_features)} features, "
                   f"top combo: {sorted_combos[0][0] if sorted_combos else 'N/A'} ({sorted_combos[0][1] if sorted_combos else 0} rules)")
    
    def _build_rules_filtering_status(
        self,
        all_rules: pd.DataFrame,
        filtered_rules: pd.DataFrame,
        evaluated_rules: pd.DataFrame,
        final_rules: pd.DataFrame,
        max_hit_rate: float,
        min_lift: float
    ) -> list[dict[str, Any]]:
        """
        构建全量规则的筛选状态数据，用于CSV下载。
        
        展示每条规则在筛选过程中的状态：
        - 方向过滤是否通过
        - 指标评估结果
        - 阈值筛选是否通过
        - 最终是否为有效规则
        
        Args:
            all_rules: 生成的全部规则
            filtered_rules: 方向过滤后的规则
            evaluated_rules: 评估后的规则（含指标，阈值筛选前）
            final_rules: 最终有效规则（阈值筛选后）
            max_hit_rate: 最大命中率阈值
            min_lift: 最小Lift阈值
            
        Returns:
            规则筛选状态列表，每条规则包含完整的筛选信息
        """
        # 获取各阶段规则集合（用于判断是否通过）
        filtered_rule_set = set(filtered_rules['rule'].astype(str).tolist()) if len(filtered_rules) > 0 else set()
        final_rule_set = set(final_rules['rule'].astype(str).tolist()) if len(final_rules) > 0 else set()
        
        # 构建评估指标映射（rule -> metrics）
        metrics_map: dict[str, dict[str, float]] = {}
        if len(evaluated_rules) > 0:
            for _, row in evaluated_rules.iterrows():
                rule_str = str(row['rule'])
                metrics_map[rule_str] = {
                    'recall': float(row.get('recall', 0)) if pd.notna(row.get('recall')) else 0,
                    'bad_rate': float(row.get('bad_rate', 0)) if pd.notna(row.get('bad_rate')) else 0,
                    'lift': float(row.get('lift', 0)) if pd.notna(row.get('lift')) else 0,
                    'hit_rate': float(row.get('hit_rate', 0)) if pd.notna(row.get('hit_rate')) else 0,
                }
        
        result = []
        for _, row in all_rules.iterrows():
            rule_str = str(row['rule'])
            
            # 判断各阶段是否通过
            direction_valid = rule_str in filtered_rule_set
            metrics = metrics_map.get(rule_str, {})
            
            # 只有通过方向过滤的规则才有指标
            if direction_valid and metrics:
                hit_rate = metrics.get('hit_rate', 0)
                bad_rate = metrics.get('bad_rate', 0)
                lift = metrics.get('lift', 0)
                bad_rate_valid = bad_rate > 0  # 坏账率必须大于0
                hit_rate_valid = hit_rate < max_hit_rate
                lift_valid = lift > min_lift
                is_valid = rule_str in final_rule_set
                
                # 确定过滤原因（按优先级判断）
                if is_valid:
                    filter_reason = ""
                elif not bad_rate_valid:
                    # 坏账率为0的规则优先标记（无风险识别能力）
                    filter_reason = "坏账率为0（无风险识别能力）"
                elif not hit_rate_valid and not lift_valid:
                    filter_reason = f"命中率超标({hit_rate:.4f}>={max_hit_rate}) 且 Lift不足({lift:.2f}<={min_lift})"
                elif not hit_rate_valid:
                    filter_reason = f"命中率超标({hit_rate:.4f}>={max_hit_rate})"
                elif not lift_valid:
                    filter_reason = f"Lift不足({lift:.2f}<={min_lift})"
                else:
                    filter_reason = "未知原因"
            else:
                # 未通过单调性校验，没有指标
                bad_rate_valid = False
                hit_rate_valid = False
                lift_valid = False
                is_valid = False
                filter_reason = "单调性校验不通过（规则方向与特征单调方向不一致）"
            
            result.append({
                'rule': rule_str,
                'recall': metrics.get('recall', None),
                'bad_rate': metrics.get('bad_rate', None),
                'lift': metrics.get('lift', None),
                'hit_rate': metrics.get('hit_rate', None),
                'direction_valid': direction_valid,
                'bad_rate_valid': bad_rate_valid if direction_valid else None,
                'hit_rate_valid': hit_rate_valid if direction_valid else None,
                'lift_valid': lift_valid if direction_valid else None,
                'is_valid': is_valid,
                'filter_reason': filter_reason
            })
        
        return result
    
    def _update_progress(
        self, 
        stage_id: str, 
        progress: float, 
        message: str = "", 
        code: str | None = None,
        output_preview: dict[str, Any] | None = None
    ) -> None:
        """Update progress via callback.
        
        Args:
            stage_id: Stage identifier
            progress: Progress percentage (0-100)
            message: Progress message
            code: Optional Python pseudocode for the stage
            output_preview: Optional output preview data for the stage
        """
        if self._progress_callback:
            # Try to call with 5 args first (full signature), then 4, then 3
            try:
                self._progress_callback(stage_id, progress, message, code, output_preview)  # type: ignore
            except TypeError:
                try:
                    self._progress_callback(stage_id, progress, message, code)  # type: ignore
                except TypeError:
                    self._progress_callback(stage_id, progress, message)  # type: ignore
    
    def _get_stage_code(self, stage_id: str) -> str:
        """Get pseudocode for a stage based on current pipeline parameters.
        
        Args:
            stage_id: Stage identifier
            
        Returns:
            Formatted pseudocode string
        """
        # Build params based on mining mode
        params: dict[str, object] = {
            # Data preprocessing
            "file_path": "data.csv",
            "target_col": "target",
            "missing_threshold": 0.5,
            # Rule filtering
            "min_lift_filter": self.min_lift_filter,
            "max_hit_rate_filter": self.max_hit_rate_filter,
            # Rule selection
            "max_hit_rate_select": self.max_hit_rate_select,
        }
        
        # Add mode-specific params
        if self.mining_mode == 'single' and isinstance(self.miner, SingleVarRuleMiner):
            params.update({
                "n_bins": self.miner.n_bins,
                "bin_method": self.miner.bin_method,
                "rule_directions": str(self.miner.directions),
                "iv_threshold": 0.02,
            })
        elif isinstance(self.miner, RuleMiner):
            params.update({
                "n_vars": self.miner.n_vars,
                "max_depth": self.miner.max_depth,
                "min_samples_leaf": self.miner.min_samples_leaf,
                "iv_threshold": 0.02,
            })
        
        return format_code_template("rule_mining", stage_id, params)
    
    def load_name_mapping(
        self,
        mapping_file: str,
        key_col: str = 'feature_code',
        value_col: str = 'feature_name'
    ) -> dict[str, str]:
        """
        Load feature name mapping from CSV file.
        
        Args:
            mapping_file: Path to mapping CSV file
            key_col: Column name for feature codes
            value_col: Column name for feature names
            
        Returns:
            Dict mapping feature codes to feature names
        """
        return self.preprocessor.load_name_mapping(mapping_file, key_col, value_col)
    
    def run(
        self,
        df: pd.DataFrame,
        target_col: str,
        weight_col: str | None = None,
        feature_cols: list[str] | None = None,
        exclude_cols: list[str] | None = None,
        score_vars: list[str] | None = None,
        var_name_dict: dict[str, str] | None = None,
        skip_preprocessing: bool = False,
        custom_thresholds: dict[str, list[float]] | None = None,
        prior_rules: list[str] | None = None,
        amount_col: str | None = None,
        psi_time_col: str | None = None,
        # 数据集划分参数（可选，与评分卡一致）
        sample_type_col: str | None = None,
        test_ratio: float = 0.0,
        progress_callback: StageProgressCallback = None,
        start_from_stage: str | None = None,
        cached_state: dict[str, Any] | None = None
    ) -> dict[str, pd.DataFrame | dict[str, Any]]:
        """
        Run complete rule mining pipeline.
        
        Args:
            df: Input dataframe
            target_col: Target column name
            weight_col: Weight column name (optional, None for no weighting)
            feature_cols: Feature column names (None to auto-detect)
            exclude_cols: Columns to exclude from features (e.g., ID, serial number).
                System will also auto-detect and exclude ID-like, time, and sample type columns.
            score_vars: Score variables with specific direction
            var_name_dict: Variable name mapping for rule display
            skip_preprocessing: Skip data preprocessing (use when data is already clean)
            custom_thresholds: Custom thresholds for single-var mining (dict[var_name, list[threshold]])
            prior_rules: Prior rule expressions for incremental contribution analysis (v6.2)
            amount_col: Amount column name for amount dimension analysis (v6.2)
            psi_time_col: Time column for PSI stability calculation (v6.3). Supports date (YYYY-MM-DD), 
                numeric (YYYYMM) formats. If provided, data will be split by time for PSI calculation.
                If None, auto-detect time columns or use random split.
            sample_type_col: Column name containing sample type labels ('train'/'test').
                If provided, data will be split based on this column. Optional for rule mining.
            test_ratio: Ratio of data to use as test set (0.0 = no split, 0.2 = 20% test).
                Only used when sample_type_col is not provided. Default 0.0 (no split).
            progress_callback: Progress callback(stage, current, total)
            start_from_stage: 从指定阶段开始重试。之前的阶段会跳过（使用缓存数据），
                重试阶段及之后的阶段会正常执行。
            cached_state: 缓存的中间状态（Phase 6 新增），用于阶段重试时跳过已完成阶段。
                包含 df_processed, results, stage_outputs 等字段。
            
        Returns:
            Dict with keys: 
                - 'mining_mode': Rule mining mode used ('single' or 'multi')
                - 'preprocessing': Data preprocessing info
                - 'feature_engineering' (if enabled): IV table and preprocessing info
                - 'all_rules': All generated rules
                - 'direction': Feature split directions
                - 'filtered_rules': Rules after filtering
                - 'evaluated_rules': Rules with metrics
                - 'optimal_rules': Final optimal rule set
                - 'prior_analysis' (if prior_rules provided): Prior rule analysis results (v6.2)
                - 'amount_analysis' (if amount_col provided): Amount dimension analysis (v6.2)
                - 'split_info' (if data split enabled): Train/test split information
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 记录关键参数
        logger.info(f"[RuleMining] run() called with test_ratio={test_ratio}, sample_type_col={sample_type_col}")
        
        results: dict[str, Any] = {'mining_mode': self.mining_mode}
        df_processed = df.copy()
        
        # Store progress callback for _update_progress method (only if provided)
        # This allows the callback set in __init__ to be used if run() is called without one
        if progress_callback is not None:
            self._progress_callback = progress_callback
        
        # 阶段重试支持：定义阶段顺序 (v2.0: 合并 filtering_rules + evaluating_rules 为 rule_filtering)
        stage_order = [
            'preprocessing', 'feature_engineering', 'generating_rules', 
            'rule_filtering', 'selecting_rules',
            'prior_analysis', 'amount_analysis', 'report_generation'
        ]
        
        # 确定起始阶段索引（用于判断是否跳过阶段）
        retry_start_idx = -1  # -1 表示没有重试
        if start_from_stage:
            if start_from_stage in stage_order:
                retry_start_idx = stage_order.index(start_from_stage)
                logger.info(f"[Pipeline] Stage retry mode: starting from {start_from_stage} (index={retry_start_idx})")
            else:
                logger.warning(f"[Pipeline] Unknown start_from_stage: {start_from_stage}")
        
        # Phase 6: 从缓存状态恢复（真正的跳过已完成阶段）
        # 添加一个字典来存储各阶段的原有output_preview
        restored_output_previews: dict[str, dict[str, Any]] = {}
        if cached_state and start_from_stage and retry_start_idx > 0:
            logger.info(f"[Pipeline] Restoring from cached state, skipping to stage: {start_from_stage}")
            logger.info(f"[Pipeline] retry_start_idx={retry_start_idx}, stage_order={stage_order}")
            logger.info(f"[Pipeline] cached_state keys: {list(cached_state.keys())}")
            logger.info(f"[Pipeline] 'df_processed' in cached_state: {'df_processed' in cached_state}")
            if "df_processed" in cached_state:
                logger.info(f"[Pipeline] cached_state['df_processed'] is None: {cached_state['df_processed'] is None}")
            
            # 恢复处理后的 DataFrame
            if "df_processed" in cached_state and cached_state["df_processed"] is not None:
                df_processed = cached_state["df_processed"]
                logger.info(f"[Pipeline] Restored df_processed: {len(df_processed)} rows, {len(df_processed.columns)} cols")
            else:
                logger.warning(f"[Pipeline] df_processed NOT restored! Using original df with {len(df_processed)} rows, {len(df_processed.columns)} cols")
            
            # 恢复累积的结果
            if "results" in cached_state and cached_state["results"]:
                results.update(cached_state["results"])
                logger.info(f"[Pipeline] Restored results keys: {list(cached_state['results'].keys())}")
            
            # 恢复各阶段的输出到 results
            if "stage_outputs" in cached_state:
                logger.info(f"[Pipeline] Restoring stage_outputs: {list(cached_state['stage_outputs'].keys())}")
                for stage_id, stage_output in cached_state["stage_outputs"].items():
                    logger.info(f"[Pipeline] Processing stage_output for {stage_id}, keys: {list(stage_output.keys())}")
                    if stage_id not in results:
                        # 从 stage_output 中提取结果（排除 df_processed 等大型对象）
                        if "results" in stage_output:
                            results.update(stage_output["results"])
                        # 也可以直接使用 output_preview 中的关键数据
                        if "output_preview" in stage_output:
                            # 保存原有的output_preview，用于跳过阶段时显示
                            restored_output_previews[stage_id] = stage_output["output_preview"]
                            logger.info(f"[Pipeline] Restored output_preview for stage: {stage_id}, has _skip_expert_pause: {stage_output['output_preview'].get('_skip_expert_pause')}")
            
            # 恢复 feature_cols（如果在缓存中）
            if "feature_cols" in cached_state and cached_state["feature_cols"]:
                feature_cols = cached_state["feature_cols"]
                logger.info(f"[Pipeline] Restored feature_cols: {len(feature_cols)} features")
            
            # 恢复 feature_cols_for_rules（规则生成阶段使用的特征列表，已排除数据泄露特征）
            # 这确保重试规则生成阶段时使用与首次执行相同的特征集
            if "feature_cols_for_rules" in cached_state and cached_state["feature_cols_for_rules"]:
                feature_cols_for_rules = cached_state["feature_cols_for_rules"]
                logger.info(f"[Pipeline] Restored feature_cols_for_rules: {len(feature_cols_for_rules)} features (for rule generation)")
            else:
                feature_cols_for_rules = None
            
            # 恢复决策树用于可视化（Full Tree 模式）
            if "full_tree" in cached_state and cached_state["full_tree"] is not None:
                self.full_tree_ = cached_state["full_tree"]
                self.full_tree_features_ = cached_state.get("full_tree_features", [])
                logger.info(f"[Pipeline] Restored full_tree: depth={self.full_tree_.get_depth()}, leaves={self.full_tree_.get_n_leaves()}, features={len(self.full_tree_features_)}")
            
            # 恢复规则来源统计（组合树模式）
            if "rule_source_stats" in cached_state and cached_state["rule_source_stats"] is not None:
                self.rule_source_stats_ = cached_state["rule_source_stats"]
                logger.info(f"[Pipeline] Restored rule_source_stats: {self.rule_source_stats_.get('total_combinations', 0)} combinations")
        else:
            # 非缓存恢复模式，初始化 feature_cols_for_rules 为 None
            feature_cols_for_rules = None
        
        def should_skip_stage(stage_id: str) -> bool:
            """检查该阶段是否应该跳过（已在缓存中完成）"""
            if retry_start_idx < 0:
                logger.info(f"[Pipeline] should_skip_stage({stage_id}): False (retry_start_idx={retry_start_idx})")
                return False  # 没有重试，不跳过
            if not cached_state:
                logger.info(f"[Pipeline] should_skip_stage({stage_id}): False (no cached_state)")
                return False  # 没有缓存，不跳过
            if stage_id not in stage_order:
                logger.warning(f"[Pipeline] should_skip_stage({stage_id}): False (stage_id not in stage_order)")
                return False
            stage_idx = stage_order.index(stage_id)
            should_skip = stage_idx < retry_start_idx
            logger.info(f"[Pipeline] should_skip_stage({stage_id}): {should_skip} (stage_idx={stage_idx}, retry_start_idx={retry_start_idx})")
            # 只有在重试阶段之前且有缓存数据时才跳过
            return should_skip
        
        def is_before_retry_stage(stage_id: str) -> bool:
            """检查该阶段是否在重试阶段之前（需要快速执行，不暂停）"""
            if retry_start_idx < 0:
                return False  # 没有重试，所有阶段正常执行
            if stage_id not in stage_order:
                return False
            stage_idx = stage_order.index(stage_id)
            return stage_idx < retry_start_idx
        
        # 创建一个包装的进度回调，用于在重试模式下跳过专家模式暂停
        original_callback = self._progress_callback
        
        def wrapped_progress_callback(
            stage_id: str, 
            progress: float, 
            message: str = "",
            code: str | None = None,
            output_preview: dict[str, Any] | None = None
        ) -> None:
            """包装的进度回调，在重试模式下跳过之前阶段的暂停"""
            if original_callback:
                # 如果是重试阶段之前的阶段，且进度为100%，添加标记
                if is_before_retry_stage(stage_id) and progress >= 100:
                    # 添加标记告诉 executor 不要暂停
                    if output_preview is None:
                        output_preview = {}
                    output_preview['_skip_expert_pause'] = True
                    logger.info(f"[Pipeline] Stage {stage_id} completed (before retry stage, skipping pause)")
                
                original_callback(stage_id, progress, message, code, output_preview)
        
        # 使用包装的回调
        self._progress_callback = wrapped_progress_callback
        
        # Stage 0a: Data Preprocessing
        if should_skip_stage('preprocessing'):
            # 跳过已完成的阶段，使用恢复的output_preview
            logger.info("[Pipeline] Skipping preprocessing stage (using cached data), restoring output_preview")
            if 'preprocessing' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['preprocessing'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                logger.info(f"[Pipeline] Using restored output_preview for preprocessing, keys: {list(restored_preview.keys())}")
                self._update_progress('preprocessing', 100.0, '数据预处理已跳过（使用缓存）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True, "_skipped_during_retry": True}
                logger.info(f"[Pipeline] Using skip_preview for preprocessing (no restored output_preview)")
                self._update_progress('preprocessing', 100.0, '数据预处理已跳过（使用缓存）', output_preview=skip_preview)
        elif not skip_preprocessing:
            self._update_progress('preprocessing', 0.0, '开始数据预处理...', code=self._get_stage_code('preprocessing'))
            
            # ========== 自动检测非建模列（与评分卡一致） ==========
            self._update_progress('preprocessing', 10.0, '智能检测非建模列...')
            
            from deepanalyze.analysis.preprocessing import ColumnCleaner
            column_cleaner = ColumnCleaner()
            
            # 用户明确指定的排除列
            user_exclude_cols = set(exclude_cols) if exclude_cols else set()
            
            # 自动检测非建模列
            non_feature_detection = column_cleaner.detect_non_feature_columns(
                df_processed, 
                target_col=target_col,
                exclude_cols=list(user_exclude_cols),
                check_id=True,
                check_time=True,
                check_sample_type=True,
                check_high_cardinality=True,
                uniqueness_threshold=0.95
            )
            
            # 合并所有需要排除的列
            auto_detected_cols = set(non_feature_detection['all_non_feature_cols'])
            
            # 如果用户指定了 weight_col、sample_type_col 或 psi_time_col，确保它们被排除（与评分卡一致）
            if weight_col and weight_col in df_processed.columns:
                auto_detected_cols.add(weight_col)
            if sample_type_col and sample_type_col in df_processed.columns:
                auto_detected_cols.add(sample_type_col)
            if psi_time_col and psi_time_col in df_processed.columns:
                auto_detected_cols.add(psi_time_col)
            
            # 最终排除列 = 目标列 + 用户指定 + 自动检测
            exclude_from_features = {target_col} | user_exclude_cols | auto_detected_cols
            
            logger.info(f"[RuleMining] 排除列构建: target_col={target_col}, user_exclude_cols={user_exclude_cols}, auto_detected_cols={auto_detected_cols}")
            logger.info(f"[RuleMining] exclude_from_features={exclude_from_features}")
            
            # 生成检测报告（与评分卡一致）
            auto_exclude_report: dict[str, Any] = {
                'user_specified': list(user_exclude_cols),
                'auto_detected': {
                    'id_cols': non_feature_detection['id_cols'],
                    'time_cols': non_feature_detection['time_cols'],
                    'sample_type_cols': non_feature_detection['sample_type_cols'],
                    'high_cardinality_cols': non_feature_detection['high_cardinality_cols'],
                },
                'total_excluded': list(exclude_from_features - {target_col}),
            }
            
            # 日志输出检测结果
            if auto_detected_cols:
                logger.info(f"[RuleMining] 自动检测到 {len(auto_detected_cols)} 个非建模列:")
                if non_feature_detection['id_cols']:
                    logger.info(f"  - ID/序号列: {non_feature_detection['id_cols']}")
                if non_feature_detection['time_cols']:
                    logger.info(f"  - 时间列: {non_feature_detection['time_cols']}")
                if non_feature_detection['sample_type_cols']:
                    logger.info(f"  - 样本类型列: {non_feature_detection['sample_type_cols']}")
                if non_feature_detection['high_cardinality_cols']:
                    logger.info(f"  - 高基数列(疑似ID): {non_feature_detection['high_cardinality_cols']}")
            
            # 计算特征列（与评分卡一致：排除目标列和非建模列后的列）
            preprocessing_feature_cols = [c for c in df_processed.columns if c not in exclude_from_features]
            
            logger.info(f"[RuleMining] 最终特征列数量: {len(preprocessing_feature_cols)}")
            
            # 行业惯例：先进行特殊值替换，再统计缺失率
            # 特殊值（如-9999、-999）在业务上等同于缺失值，缺失率统计应包含这些值
            self._update_progress('preprocessing', 12.0, '识别特殊缺失值...')
            special_value_info: dict[str, Any] = {
                "special_values": [],
                "affected_features": 0,
                "total_replaced": 0,
                "details": {}
            }
            
            if self.enable_feature_engineering and self.feature_engineer is not None:
                # 记录替换前的特殊值列表
                special_value_info["special_values"] = list(self.feature_engineer.special_values)
                
                # 执行特殊值替换
                df_processed = self.feature_engineer.replace_special_values(
                    df_processed, 
                    exclude_cols=list(exclude_from_features)
                )
                
                # 获取替换报告
                replace_report = self.feature_engineer.special_value_report_
                if replace_report:
                    special_value_info["affected_features"] = len(replace_report)
                    special_value_info["total_replaced"] = sum(replace_report.values())
                    special_value_info["details"] = dict(replace_report)
                    logger.info(f"[RuleMining] 特殊值替换完成: {special_value_info['affected_features']} 个特征受影响, 共替换 {special_value_info['total_replaced']} 条记录")
            
            results['special_value_info'] = special_value_info
            
            # 检查缺失值（在特殊值替换之后，确保缺失率统计包含特殊缺失值）
            self._update_progress('preprocessing', 15.0, '检查数据质量...')
            missing_report = self.preprocessor.check_missing(df_processed, exclude_cols=list(exclude_from_features))
            results['missing_report'] = missing_report
            
            # 构建缺失率结构化摘要（missing_summary）
            missing_summary: dict[str, Any] = {
                "avg_missing_rate": float(missing_report['missing_rate'].mean()) if len(missing_report) > 0 else 0.0,
                "max_missing_rate": float(missing_report['missing_rate'].max()) if len(missing_report) > 0 else 0.0,
                "min_missing_rate": float(missing_report['missing_rate'].min()) if len(missing_report) > 0 else 0.0,
                "total_features": len(missing_report),
                "features_with_missing": int((missing_report['missing_rate'] > 0).sum()) if len(missing_report) > 0 else 0,
                "high_missing_features": [],  # 高缺失率特征列表（>30%）
                "distribution": {
                    "no_missing": 0,      # 0%
                    "low": 0,             # 0-10%
                    "medium": 0,          # 10-30%
                    "high": 0,            # 30-50%
                    "very_high": 0,       # >50%
                }
            }
            
            if len(missing_report) > 0:
                # 计算缺失率分布
                rates = missing_report['missing_rate']
                missing_summary["distribution"]["no_missing"] = int((rates == 0).sum())
                missing_summary["distribution"]["low"] = int(((rates > 0) & (rates <= 0.1)).sum())
                missing_summary["distribution"]["medium"] = int(((rates > 0.1) & (rates <= 0.3)).sum())
                missing_summary["distribution"]["high"] = int(((rates > 0.3) & (rates <= 0.5)).sum())
                missing_summary["distribution"]["very_high"] = int((rates > 0.5).sum())
                
                # 高缺失率特征列表（>30%）
                high_missing_mask = rates > 0.3
                if high_missing_mask.any():
                    high_missing_df = missing_report[high_missing_mask].head(10)
                    missing_summary["high_missing_features"] = [
                        {"name": row['variable'], "rate": float(row['missing_rate'])}
                        for _, row in high_missing_df.iterrows()
                    ]
            
            results['missing_summary'] = missing_summary
            
            # Auto-detect if feature engineering is needed based on data quality
            # This is only done when enable_feature_engineering is set to 'auto' or True
            self._update_progress('preprocessing', 20.0, '评估数据质量...')
            quality_assessment = DataPreprocessor.assess_data_quality(
                df_processed, target_col, weight_col
            )
            results['data_quality'] = quality_assessment
            
            # If feature engineering is enabled but data quality is good, we can still proceed
            # The quality assessment is informational and stored in results
            self._update_progress('preprocessing', 40.0, 
                f"数据质量评估完成 (评分: {quality_assessment['quality_score']}/100)")
            
            # Determine if One-Hot should be done here or in feature engineering
            # For single-var mode, we typically don't need One-Hot encoding
            do_onehot = not self.enable_feature_engineering and self.mining_mode == 'multi'
            
            # 传入用户指定的排除列，确保这些列不进行任何衍生处理（行业惯例）
            df_processed, preprocess_info = self.preprocessor.preprocess(
                df_processed,
                target_col=target_col,
                weight_col=weight_col,
                exclude_cols=list(exclude_from_features),  # 用户指定的排除列不进行衍生
                do_onehot=do_onehot,
                categorical_cols=self.categorical_cols,
                force_categorical=self.force_categorical
            )
            
            # 将自动检测结果添加到 preprocess_info
            preprocess_info['auto_exclude_report'] = auto_exclude_report
            preprocess_info['preprocessing_feature_cols'] = preprocessing_feature_cols
            results['preprocessing'] = preprocess_info
            results['auto_exclude_report'] = auto_exclude_report
            # v2.6: 保存原始坏账率到results，供后续阶段使用（避免重复计算）
            results['original_bad_rate'] = float(df_processed[target_col].mean()) if target_col in df_processed.columns else 0.0
            
            # 异常值检测（与评分卡一致）
            self._update_progress('preprocessing', 75.0, '检测异常值...')
            outlier_info = self.preprocessor.detect_outliers(
                df_processed, feature_cols=preprocessing_feature_cols, 
                method='iqr', threshold=1.5, exclude_cols=list(exclude_from_features)
            )
            results['outlier_info'] = outlier_info
            
            # 可选的数据集划分（与评分卡一致）
            split_info: dict[str, Any] | None = None
            train_df: pd.DataFrame | None = None
            test_df: pd.DataFrame | None = None
            
            if sample_type_col and sample_type_col in df_processed.columns:
                # 基于样本类型列划分
                self._update_progress('preprocessing', 80.0, '按样本类型划分数据集...')
                train_df = df_processed[df_processed[sample_type_col].isin(['train', 'Train', 'TRAIN', 0])].copy()
                test_df = df_processed[df_processed[sample_type_col].isin(['test', 'Test', 'TEST', 1])].copy()
                
                if len(train_df) > 0 and len(test_df) > 0:
                    # 计算训练集和测试集的坏账率
                    train_target_rate = train_df[target_col].mean() if len(train_df) > 0 else 0
                    test_target_rate = test_df[target_col].mean() if len(test_df) > 0 else 0
                    split_info = {
                        "train": len(train_df),
                        "test": len(test_df),
                        "train_target_rate": train_target_rate,
                        "test_target_rate": test_target_rate,
                        "split_method": "sample_type_col",
                    }
                    results['train_data'] = train_df
                    results['test_data'] = test_df
                    logger.info(f"[RuleMining] 数据集划分完成: 训练集 {len(train_df)} 行 (坏账率 {train_target_rate:.2%}), 测试集 {len(test_df)} 行 (坏账率 {test_target_rate:.2%})")
                else:
                    logger.warning(f"[RuleMining] 样本类型列 {sample_type_col} 划分失败，使用全量数据")
            elif test_ratio > 0:
                # 基于比例随机划分
                self._update_progress('preprocessing', 80.0, f'随机划分数据集 (测试集比例: {test_ratio:.0%})...')
                from sklearn.model_selection import train_test_split
                train_df, test_df = train_test_split(
                    df_processed, test_size=test_ratio, random_state=42, stratify=df_processed[target_col]
                )
                # 计算训练集和测试集的坏账率
                train_target_rate = train_df[target_col].mean() if len(train_df) > 0 else 0
                test_target_rate = test_df[target_col].mean() if len(test_df) > 0 else 0
                split_info = {
                    "train": len(train_df),
                    "test": len(test_df),
                    "train_target_rate": train_target_rate,
                    "test_target_rate": test_target_rate,
                    "split_method": "random",
                    "test_ratio": test_ratio,
                }
                results['train_data'] = train_df
                results['test_data'] = test_df
                logger.info(f"[RuleMining] 数据集随机划分完成: 训练集 {len(train_df)} 行 (坏账率 {train_target_rate:.2%}), 测试集 {len(test_df)} 行 (坏账率 {test_target_rate:.2%})")
            
            if split_info:
                results['split_info'] = split_info
            
            # 计算时间范围信息（与评分卡一致）
            # 优先使用用户指定的 psi_time_col，否则自动检测时间列
            time_range_info: dict[str, Any] | None = None
            effective_time_col: str | None = None
            
            if psi_time_col and psi_time_col in df_processed.columns:
                effective_time_col = psi_time_col
                logger.info(f"[RuleMining] 使用用户指定的时间列计算时间范围: {psi_time_col}")
            else:
                # 自动检测时间列（与 PSI 计算时的逻辑一致）
                time_keywords = ['time', 'date', 'period', '日期', '时间', '期数', 'month', '月份']
                time_cols = [c for c in df_processed.columns 
                             if any(kw in c.lower() for kw in time_keywords)]
                if time_cols:
                    effective_time_col = time_cols[0]
                    logger.info(f"[RuleMining] 自动检测到时间列: {effective_time_col}")
            
            if effective_time_col:
                def _get_time_range(data: pd.DataFrame | None, col: str) -> dict[str, str] | None:
                    """获取数据集的时间范围"""
                    if data is None or col not in data.columns or len(data) == 0:
                        return None
                    try:
                        time_series = pd.to_datetime(data[col], errors='coerce')
                        valid_times = time_series.dropna()
                        if len(valid_times) == 0:
                            return None
                        min_time = valid_times.min()
                        max_time = valid_times.max()
                        # 格式化为日期字符串（YYYY-MM-DD）
                        return {
                            "min": min_time.strftime('%Y-%m-%d') if pd.notna(min_time) else None,
                            "max": max_time.strftime('%Y-%m-%d') if pd.notna(max_time) else None,
                        }
                    except Exception as e:
                        logger.warning(f"[RuleMining] 解析时间列失败: {e}")
                        return None
                
                time_range_info = {
                    "column": effective_time_col,
                    "overall": _get_time_range(df_processed, effective_time_col),
                    "train": _get_time_range(train_df, effective_time_col) if train_df is not None else None,
                    "test": _get_time_range(test_df, effective_time_col) if test_df is not None else None,
                }
                
                logger.info(f"[RuleMining] 时间范围信息: column={effective_time_col}, "
                           f"overall={time_range_info.get('overall')}, "
                           f"train={time_range_info.get('train')}, test={time_range_info.get('test')}")
            
            # Build output preview for preprocessing stage (与评分卡一致的字段)
            auto_excluded_count = len(auto_exclude_report['total_excluded'])
            outlier_feature_count = len([k for k, v in outlier_info.items() if v.get('count', 0) > 0])
            
            # 获取衍生列信息
            onehot_new_cols = preprocess_info.get('onehot_new_cols', [])
            datetime_new_cols = preprocess_info.get('datetime_new_cols', [])
            text_new_cols = preprocess_info.get('text_new_cols', [])
            
            # 更新特征列表，包含衍生特征（用于后续阶段）
            # preprocessing_feature_cols 是原始特征（preprocess之前），需要加上衍生特征
            all_derived_cols = onehot_new_cols + datetime_new_cols + text_new_cols
            post_preprocess_feature_cols = preprocessing_feature_cols + all_derived_cols
            
            progress_msg = f"数据预处理完成，{len(df_processed)}行"
            if auto_excluded_count > 0:
                progress_msg += f"，自动排除{auto_excluded_count}个非建模列"
            if split_info:
                progress_msg += f"，训练集{split_info['train']}行，测试集{split_info['test']}行"
            if outlier_feature_count > 0:
                progress_msg += f"，检测到{outlier_feature_count}个特征存在异常值"
            
            preprocessing_preview: dict[str, Any] = {
                # 与评分卡一致的字段
                "rows": len(df_processed),
                "columns": len(df_processed.columns),  # 处理后总列数
                "feature_count": len(preprocessing_feature_cols),  # 原始特征数（preprocess之前）
                "missing_rate": missing_summary["avg_missing_rate"],  # 使用结构化摘要中的平均缺失率
                "target_rate": float(df_processed[target_col].mean()) if target_col in df_processed.columns else 0.0,
                "auto_exclude_report": auto_exclude_report,  # 自动排除报告
                "missing_summary": missing_summary,  # 缺失率结构化摘要
                "outlier_count": len([k for k, v in outlier_info.items() if v.get('count', 0) > 0]),  # 异常值特征数
                # 特殊值替换信息（行业惯例：特殊值在缺失率统计前替换）
                "special_value_info": special_value_info,
                # 规则挖掘特有的字段
                "quality_score": quality_assessment['quality_score'],
                "quality_issues": quality_assessment['issues'][:3] if quality_assessment['issues'] else [],
                "needs_feature_engineering": quality_assessment['needs_feature_engineering'],
                # 衍生列信息
                "derived_features": {
                    "onehot_count": len(onehot_new_cols),  # One-Hot编码新增特征数
                    "datetime_count": len(datetime_new_cols),  # 日期时间衍生特征数
                    "text_count": len(text_new_cols),  # 文本衍生特征数
                    "total_derived": len(onehot_new_cols) + len(datetime_new_cols) + len(text_new_cols),
                },
                # Phase 6: 添加完整阶段数据用于检查点保存
                "_full_stage_data": {
                    "df_processed": df_processed,
                    "results": dict(results),  # 复制当前累积结果
                    "feature_cols": post_preprocess_feature_cols,  # 使用包含衍生特征的特征列
                }
            }
            
            # 添加数据集划分信息（如果有）
            if split_info:
                preprocessing_preview["split_info"] = split_info
            
            # 添加时间范围信息（如果有）
            if time_range_info:
                preprocessing_preview["time_range_info"] = time_range_info
            
            self._update_progress('preprocessing', 100.0, progress_msg, output_preview=preprocessing_preview)
        
        # Stage 0b: Feature Engineering (optional)
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        if should_skip_stage('feature_engineering'):
            # 跳过已完成的阶段，使用恢复的output_preview
            logger.info("[Pipeline] Skipping feature_engineering stage (using cached data), restoring output_preview")
            if 'feature_engineering' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['feature_engineering'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('feature_engineering', 100.0, '特征工程已跳过（使用缓存）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('feature_engineering', 100.0, '特征工程已跳过（使用缓存）', output_preview=skip_preview)
        elif self.enable_feature_engineering and self.feature_engineer is not None:
            self._update_progress('feature_engineering', 0.0, '开始特征工程...', code=self._get_stage_code('feature_engineering'))
            
            # 确定输入特征列表：优先使用缓存恢复的 feature_cols，否则使用预处理阶段产生的 post_preprocess_feature_cols
            # 注意：重试特征工程阶段时，预处理阶段被跳过，post_preprocess_feature_cols 不存在
            # 此时 feature_cols 应该已从缓存恢复
            if feature_cols:
                input_feature_cols = feature_cols
            elif 'post_preprocess_feature_cols' in dir():
                input_feature_cols = post_preprocess_feature_cols
            else:
                # 兜底：从 df_processed 中推断特征列（排除目标列和权重列）
                exclude_cols = {target_col}
                if weight_col:
                    exclude_cols.add(weight_col)
                input_feature_cols = [c for c in df_processed.columns if c not in exclude_cols]
                logger.warning(f"[Pipeline] feature_cols not available, inferred {len(input_feature_cols)} features from df_processed")
            
            # 保存特征工程前的特征数（用于output_preview）
            before_feature_count = len(input_feature_cols)
            
            df_processed, iv_table, feature_cols = self.feature_engineer.preprocess(
                df_processed, 
                target_col=target_col, 
                weight_col=weight_col,
                feature_cols=input_feature_cols,
                force_categorical=self.force_categorical,
                force_numeric=self.force_numeric  # 用户指定的数值列不进行One-Hot编码
            )
            
            results['feature_engineering'] = {
                'iv_table': iv_table,
                'dropped_vars': self.feature_engineer.dropped_vars_,
                'onehot_mapping': self.feature_engineer.onehot_mapping_,
                'final_feature_cols': feature_cols
            }
            
            # 获取 One-Hot 编码信息
            onehot_mapping = getattr(self.feature_engineer, 'onehot_mapping_', {}) or {}
            onehot_indicator = getattr(self.feature_engineer, 'onehot_indicator', '_is_')
            onehot_original_count = len(onehot_mapping)  # 被编码删除的原始列数
            onehot_derived_count = sum(len(vals) for vals in onehot_mapping.values())  # 产生的衍生列数
            
            # 新流程统计（One-Hot → IV计算 → IV筛选）
            # 计算 One-Hot 后、IV 筛选前的特征数
            # before_feature_count = 原始特征数（One-Hot 前）
            # after_onehot_count = 原始特征数 - One-Hot原始列 + One-Hot衍生列
            after_onehot_count = before_feature_count - onehot_original_count + onehot_derived_count
            
            # IV 分布统计（基于 One-Hot 后的所有特征，包括衍生列）
            iv_distribution = {}
            iv_removed_count = 0  # IV 筛选移除的特征数
            iv_removed_original = 0  # 其中原始特征数
            iv_removed_derived = 0  # 其中 One-Hot 衍生特征数
            
            # 构建 One-Hot 衍生列集合
            onehot_derived_cols: set[str] = set()
            for orig_col, unique_values in onehot_mapping.items():
                for val in unique_values:
                    derived_col_name = f"{orig_col}{onehot_indicator}{val}"
                    onehot_derived_cols.add(derived_col_name)
            
            if iv_table is not None and len(iv_table) > 0:
                iv_distribution = {
                    'strong': int((iv_table['iv'] >= 0.1).sum()),  # IV >= 0.1
                    'medium_strong': int(((iv_table['iv'] >= 0.05) & (iv_table['iv'] < 0.1)).sum()),  # 0.05 <= IV < 0.1
                    'medium': int(((iv_table['iv'] >= 0.02) & (iv_table['iv'] < 0.05)).sum()),  # 0.02 <= IV < 0.05
                    'weak': int((iv_table['iv'] < 0.02).sum())  # IV < 0.02
                }
                # IV 筛选移除的特征（IV < 阈值）
                iv_threshold = self.feature_engineer.iv_threshold
                removed_vars = iv_table[iv_table['iv'] < iv_threshold]['variable'].tolist()
                iv_removed_count = len(removed_vars)
                
                # 区分移除的原始特征和 One-Hot 衍生特征
                for var in removed_vars:
                    if var in onehot_derived_cols:
                        iv_removed_derived += 1
                    else:
                        iv_removed_original += 1
            
            # 最终特征数
            after_feature_count = len(feature_cols) if feature_cols else 0
            
            # 构建特征详情列表（用于CSV下载）
            feature_details: list[dict[str, Any]] = []
            if feature_cols:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[RuleMining] 构建特征详情: feature_cols数量={len(feature_cols)}, iv_table数量={len(iv_table) if iv_table is not None else 0}")
                logger.info(f"[RuleMining] onehot_mapping: {list(onehot_mapping.keys())}, 衍生列数: {onehot_derived_count}")
                
                # 构建 One-Hot 反向查找（衍生列 -> 原始列）
                onehot_reverse_lookup: dict[str, str] = {}
                for orig_col, unique_values in onehot_mapping.items():
                    for val in unique_values:
                        derived_col_name = f"{orig_col}{onehot_indicator}{val}"
                        onehot_reverse_lookup[derived_col_name] = orig_col
                
                # 构建 IV 值查找字典（新流程：所有特征都有独立 IV）
                iv_lookup: dict[str, float] = {}
                if iv_table is not None and len(iv_table) > 0:
                    for _, row in iv_table.iterrows():
                        iv_lookup[row['variable']] = row['iv']
                
                logger.info(f"[RuleMining] iv_lookup构建完成: {len(iv_lookup)}个特征有IV值")
                
                # 遍历所有筛选后保留的特征
                for idx, var_name in enumerate(feature_cols):
                    # 新流程：每个特征（包括 One-Hot 衍生列）都有独立计算的 IV
                    iv_value = iv_lookup.get(var_name, 0.0)
                    
                    # 判断特征来源
                    is_onehot_derived = var_name in onehot_derived_cols
                    feature_source = 'Derived (One-Hot)' if is_onehot_derived else 'Original'
                    orig_col = onehot_reverse_lookup.get(var_name, '')
                    
                    # 计算特征统计信息
                    col_stats: dict[str, Any] = {
                        'no': idx + 1,  # 序号
                        'feature_name': var_name,  # 特征名称
                        'data_type': str(df_processed[var_name].dtype) if var_name in df_processed.columns else 'unknown',
                        'iv': round(iv_value, 6),  # IV值（独立计算）
                        'iv_level': 'Strong' if iv_value >= 0.1 else ('Medium-Strong' if iv_value >= 0.05 else ('Medium' if iv_value >= 0.02 else 'Weak')),
                        'missing_rate': 0.0,  # 缺失率
                        'unique_count': 0,  # 唯一值数量
                        'source': feature_source,  # 来源
                        'derivation_method': 'One-Hot' if is_onehot_derived else '',  # 衍生方式
                        'original_feature': orig_col,  # One-Hot 原始列
                    }
                    
                    # 计算缺失率和唯一值
                    if var_name in df_processed.columns:
                        col_data = df_processed[var_name]
                        col_stats['missing_rate'] = round(col_data.isna().mean(), 4)
                        col_stats['unique_count'] = int(col_data.nunique())
                        
                        # 数值型特征的统计
                        if pd.api.types.is_numeric_dtype(col_data):
                            col_stats['min'] = round(float(col_data.min()), 4) if not col_data.isna().all() else None
                            col_stats['max'] = round(float(col_data.max()), 4) if not col_data.isna().all() else None
                            col_stats['mean'] = round(float(col_data.mean()), 4) if not col_data.isna().all() else None
                            col_stats['std'] = round(float(col_data.std()), 4) if not col_data.isna().all() else None
                    
                    feature_details.append(col_stats)
                
                logger.info(f"[RuleMining] 特征详情构建完成: {len(feature_details)}个特征")
            
            # 构建 One-Hot 编码统计
            onehot_stats: dict[str, Any] = {}
            if onehot_mapping:
                onehot_original_cols = list(onehot_mapping.keys())  # 被 One-Hot 编码的原始列
                # 计算保留的衍生列数（筛选后）
                retained_derived = sum(1 for f in feature_cols if f in onehot_derived_cols) if feature_cols else 0
                onehot_stats = {
                    "original_cols": onehot_original_cols,  # 原始列名列表
                    "original_count": onehot_original_count,  # 被编码的原始列数
                    "derived_count": onehot_derived_count,  # 产生的衍生列数
                    "retained_derived": retained_derived,  # IV筛选后保留的衍生列数
                    "removed_derived": iv_removed_derived,  # IV筛选移除的衍生列数
                }
            
            # Build output preview for feature_engineering stage
            # 新流程统计：缺失率筛选 → One-Hot → IV筛选
            # 注意：One-Hot 是转换操作（原始列→衍生列），不是纯删除
            # 所以"One-Hot编码删除原始列"不应放入removed_reasons，避免用户误算
            # One-Hot 信息已在 onehot_stats 区块单独展示
            removed_reasons: dict[str, int] = {}
            
            # 1. 缺失率筛选移除的特征
            dropped_missing = getattr(self.feature_engineer, 'dropped_missing_', []) or []
            if len(dropped_missing) > 0:
                removed_reasons["缺失率筛选移除"] = len(dropped_missing)
            
            # 2. IV筛选移除的特征
            if iv_removed_count > 0:
                # 区分移除的原始特征和衍生特征
                if iv_removed_original > 0:
                    removed_reasons["IV筛选移除(原始特征)"] = iv_removed_original
                if iv_removed_derived > 0:
                    removed_reasons["IV筛选移除(One-Hot衍生)"] = iv_removed_derived
            
            # One-Hot 是转换操作，不放入 added_reasons 避免误解
            # 信息已在 onehot_stats 区块展示
            added_reasons: dict[str, int] = {}
            
            # 构建缺失率筛选详情（始终输出，即使移除0个也显示，让用户知道该步骤已执行）
            missing_filter_stats: dict[str, Any] = {
                "threshold": self.feature_engineer.missing_threshold,
                "removed_count": len(dropped_missing),
                "removed_vars": dropped_missing[:20] if dropped_missing else [],  # 最多显示20个
                "has_more": len(dropped_missing) > 20 if dropped_missing else False
            }
            
            # 构建 selection_flow（特征变化流程），与前端展示保持一致
            # 流程：初始 → 缺失率筛选 → One-Hot后 → IV筛选
            selection_flow: list[dict[str, Any]] = []
            
            # Step 1: 初始特征数
            selection_flow.append({
                "step": "初始",
                "count": before_feature_count,
                "removed": 0,
                "added": 0
            })
            
            # Step 2: 缺失率筛选
            after_missing_count = before_feature_count - len(dropped_missing)
            selection_flow.append({
                "step": "缺失率筛选",
                "count": after_missing_count,
                "removed": len(dropped_missing),
                "added": 0
            })
            
            # Step 3: One-Hot编码后（如果有One-Hot操作）
            if onehot_original_count > 0 and onehot_derived_count > 0:
                selection_flow.append({
                    "step": "One-Hot后",
                    "count": after_onehot_count,
                    "removed": onehot_original_count,  # 原始分类列被移除
                    "added": onehot_derived_count  # 生成的哑变量列
                })
            
            # Step 4: IV筛选（最终结果）
            selection_flow.append({
                "step": "IV筛选",
                "count": after_feature_count,
                "removed": iv_removed_count,
                "added": 0
            })
            
            feature_engineering_preview: dict[str, Any] = {
                "before_count": before_feature_count,
                "after_onehot_count": after_onehot_count,  # One-Hot 后、IV筛选前的特征数
                "after_count": after_feature_count,
                "removed_reasons": removed_reasons,
                "added_reasons": added_reasons,
                "selected_features": feature_cols or [],  # 返回完整列表，前端负责截断显示
                "iv_threshold": self.feature_engineer.iv_threshold,
                "iv_distribution": iv_distribution,
                "onehot_stats": onehot_stats,  # One-Hot 编码统计
                "missing_filter_stats": missing_filter_stats,  # 缺失率筛选统计
                "selection_flow": selection_flow,  # 特征变化流程（前端展示用）
                "feature_details": feature_details,  # 特征详情列表（用于CSV下载）
                # Phase 6: 添加完整阶段数据用于检查点保存
                "_full_stage_data": {
                    "df_processed": df_processed,
                    "results": dict(results),
                    "feature_cols": feature_cols,
                    # 保存规则生成阶段使用的特征列表（已排除数据泄露特征）
                    # 确保重试时使用相同的特征集，生成一致的规则数量
                    "feature_cols_for_rules": feature_cols_for_rules,
                    # 保存决策树用于可视化（Full Tree 模式）
                    "full_tree": self.full_tree_,
                    "full_tree_features": self.full_tree_features_,
                }
            }
            
            # 如果筛选后特征太少，添加警告
            if len(feature_cols) <= 3:
                feature_engineering_preview["warning"] = f"IV筛选后只剩{len(feature_cols)}个特征，可能导致规则数量不足。建议降低IV阈值（当前: {self.feature_engineer.iv_threshold}）"
            
            self._update_progress('feature_engineering', 100.0, '特征工程完成', output_preview=feature_engineering_preview)
        else:
            # Feature engineering is disabled - mark stage as skipped with quality info
            skip_reason = "用户未启用特征工程预处理"
            skip_preview: dict[str, Any] = {"skipped": True, "reason": skip_reason}
            
            # Add quality assessment info if available
            if 'data_quality' in results:
                quality = results['data_quality']
                skip_preview['quality_score'] = quality['quality_score']
                skip_preview['recommendation'] = quality['recommendations'][0] if quality['recommendations'] else ""
                if quality['needs_feature_engineering']:
                    skip_reason = f"特征工程已跳过（建议启用：数据质量评分 {quality['quality_score']}/100）"
                else:
                    skip_reason = f"特征工程已跳过（数据质量良好：{quality['quality_score']}/100）"
            
            self._update_progress('feature_engineering', 100.0, skip_reason, output_preview=skip_preview)
        
        # ========== 自动检测非建模列 ==========
        # 参考评分卡开发任务的实现，智能检测并排除ID列、时间列、样本类型列等
        from deepanalyze.analysis.preprocessing import ColumnCleaner
        column_cleaner = ColumnCleaner()
        
        # 用户明确指定的排除列
        user_exclude_cols = set(exclude_cols) if exclude_cols else set()
        
        # 自动检测非建模列
        non_feature_detection = column_cleaner.detect_non_feature_columns(
            df_processed, 
            target_col=target_col,
            exclude_cols=list(user_exclude_cols),
            check_id=True,
            check_time=True,
            check_sample_type=True,
            check_high_cardinality=True,
            uniqueness_threshold=0.95
        )
        
        # 合并所有需要排除的列
        auto_detected_cols = set(non_feature_detection['all_non_feature_cols'])
        
        # 如果用户指定了 psi_time_col，确保它被排除
        if psi_time_col and psi_time_col in df_processed.columns:
            auto_detected_cols.add(psi_time_col)
        
        # 最终排除列 = 目标列 + 权重列 + 用户指定 + 自动检测
        exclude_from_features = {target_col, '_weight_'} | user_exclude_cols | auto_detected_cols
        if weight_col:
            exclude_from_features.add(weight_col)
        
        # 生成检测报告
        auto_exclude_report: dict[str, Any] = {
            'user_specified': list(user_exclude_cols),
            'auto_detected': {
                'id_cols': non_feature_detection['id_cols'],
                'time_cols': non_feature_detection['time_cols'],
                'sample_type_cols': non_feature_detection['sample_type_cols'],
                'high_cardinality_cols': non_feature_detection['high_cardinality_cols'],
            },
            'total_excluded': list(exclude_from_features - {target_col, '_weight_'}),
        }
        
        # 日志输出检测结果
        if auto_detected_cols:
            logger.info(f"[Pipeline] 自动检测到 {len(auto_detected_cols)} 个非建模列:")
            if non_feature_detection['id_cols']:
                logger.info(f"  - ID/序号列: {non_feature_detection['id_cols']}")
            if non_feature_detection['time_cols']:
                logger.info(f"  - 时间列: {non_feature_detection['time_cols']}")
            if non_feature_detection['sample_type_cols']:
                logger.info(f"  - 样本类型列: {non_feature_detection['sample_type_cols']}")
            if non_feature_detection['high_cardinality_cols']:
                logger.info(f"  - 高基数列(疑似ID): {non_feature_detection['high_cardinality_cols']}")
        
        # 保存排除报告到结果
        results['auto_exclude_report'] = auto_exclude_report
        
        # Auto-detect feature columns if not provided
        if feature_cols is None:
            # 只选择数值类型的列（决策树只能处理数值特征）
            # 排除 object/category/string 类型的列，避免 "could not convert string to float" 错误
            numeric_dtypes = ['int64', 'int32', 'int16', 'int8', 'float64', 'float32', 'float16', 'bool']
            feature_cols = [
                c for c in df_processed.columns 
                if c not in exclude_from_features and df_processed[c].dtype.name in numeric_dtypes
            ]
            
            # 记录被排除的非数值列
            non_numeric_cols = [
                c for c in df_processed.columns 
                if c not in exclude_from_features and df_processed[c].dtype.name not in numeric_dtypes
            ]
            if non_numeric_cols:
                logger.warning(
                    f"[Pipeline] 自动排除了 {len(non_numeric_cols)} 个非数值类型的列: "
                    f"{non_numeric_cols[:5]}{'...' if len(non_numeric_cols) > 5 else ''}"
                )
        else:
            # 如果用户指定了 feature_cols，仍然排除自动检测的非建模列
            feature_cols = [c for c in feature_cols if c not in exclude_from_features]
        
        logger.info(f"[Pipeline] 最终特征列数量: {len(feature_cols)}")
        
        # Validate feature columns before rule generation
        if not feature_cols or len(feature_cols) == 0:
            raise ValueError(
                "没有可用的特征列进行规则挖掘。可能的原因：\n"
                "1. 特征工程阶段筛选掉了所有变量（IV值都低于阈值）\n"
                "2. 数据中没有数值类型的特征列\n"
                "3. 所有特征列的缺失率都超过了阈值\n"
                "请检查数据质量或调整特征工程参数（如降低IV阈值、提高缺失率阈值）"
            )
        
        # 验证 feature_cols 中的列都是数值类型（防止用户手动指定了非数值列）
        numeric_dtypes = ['int64', 'int32', 'int16', 'int8', 'float64', 'float32', 'float16', 'bool']
        non_numeric_features = [
            c for c in feature_cols 
            if c in df_processed.columns and df_processed[c].dtype.name not in numeric_dtypes
        ]
        if non_numeric_features:
            logger.warning(
                f"[Pipeline] 检测到 {len(non_numeric_features)} 个非数值类型的特征列，将自动排除: "
                f"{non_numeric_features[:5]}{'...' if len(non_numeric_features) > 5 else ''}"
            )
            feature_cols = [c for c in feature_cols if c not in non_numeric_features]
            
            # 再次检查是否还有可用特征
            if not feature_cols:
                raise ValueError(
                    f"所有指定的特征列都是非数值类型，无法用于规则挖掘。\n"
                    f"非数值列: {non_numeric_features[:10]}{'...' if len(non_numeric_features) > 10 else ''}\n"
                    "请确保数据中包含数值类型的特征，或启用特征工程对分类变量进行 One-Hot 编码。"
                )
        
        # For multi-var mode, check if we have enough features for combinations
        if self.mining_mode == 'multi':
            assert isinstance(self.miner, RuleMiner)
            if len(feature_cols) < self.miner.n_vars:
                raise ValueError(
                    f"特征列数量不足：需要至少 {self.miner.n_vars} 个特征进行组合规则挖掘，"
                    f"但只有 {len(feature_cols)} 个可用特征。\n"
                    "请减少 n_vars 参数值，或调整特征工程参数以保留更多特征。"
                )
        
        # Stage 1: Generate rules (different logic based on mining_mode)
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        
        if should_skip_stage('generating_rules'):
            # 跳过已完成的阶段，从缓存恢复 all_rules 和 output_preview
            logger.info("[Pipeline] Skipping generating_rules stage (using cached data), restoring output_preview")
            all_rules = results.get('all_rules', pd.DataFrame())
            if 'generating_rules' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['generating_rules'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('generating_rules', 100.0, f'规则生成已跳过（使用缓存，共{len(all_rules)}条）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "total_rules": len(all_rules), "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('generating_rules', 100.0, f'规则生成已跳过（使用缓存，共{len(all_rules)}条）', output_preview=skip_preview)
        else:
            self._update_progress('generating_rules', 0.0, '开始生成规则...', code=self._get_stage_code('generating_rules'))
            
            # 设置 One-Hot 映射用于规则可读性转换
            onehot_mapping = getattr(self.feature_engineer, 'onehot_mapping_', {}) or {} if self.feature_engineer else {}
            onehot_indicator = getattr(self.feature_engineer, 'onehot_indicator', '_is_') if self.feature_engineer else '_is_'
            
            if self.mining_mode == 'single':
                # Single variable rule mining
                assert isinstance(self.miner, SingleVarRuleMiner)  # Type narrowing
                all_rules = self.miner.generate_rules(
                    df_processed, feature_cols, target_col, weight_col,
                    custom_thresholds=custom_thresholds,
                    var_name_dict=var_name_dict
                )
                # 单特征模式无规则来源统计
                self.rule_source_stats_: dict[str, Any] | None = None
                # 单特征模式不进行数据泄露检测，直接使用原始特征列表
                if feature_cols_for_rules is None:
                    feature_cols_for_rules = feature_cols.copy()
            elif self.use_full_tree:
                # Full-feature tree mining: 使用全特征树挖掘规则
                # 规则与可视化完全匹配
                logger.info("[Pipeline] Using full-feature tree for rule mining...")
                assert isinstance(self.miner, RuleMiner)  # Type narrowing
                
                # 设置 One-Hot 映射用于规则可读性转换
                self.miner.set_onehot_mapping(onehot_mapping, onehot_indicator)
                
                # Prepare data
                df_for_tree = df_processed.copy()
                actual_weight_col = weight_col if weight_col and weight_col in df_for_tree.columns else None
                if not actual_weight_col:
                    df_for_tree['_weight_'] = 1.0
                    actual_weight_col = '_weight_'
                
                df_for_tree = df_for_tree[[target_col, actual_weight_col] + feature_cols].dropna()
                
                # Phase 12: 检测并排除"完美分离特征"（可能存在数据泄露）
                # 这些特征能完美区分正负样本，通常是目标变量的衍生或泄露
                # 如果有缓存的 feature_cols_for_rules，则跳过检测，确保重试时结果一致
                if feature_cols_for_rules is not None:
                    # 使用缓存的特征列表（已排除数据泄露特征）
                    logger.info(f"[Pipeline] Using cached feature_cols_for_rules: {len(feature_cols_for_rules)} features (skipping leakage detection)")
                    feature_cols = feature_cols_for_rules
                    df_for_tree = df_for_tree[[target_col, actual_weight_col] + feature_cols]
                else:
                    # 首次执行，进行数据泄露检测
                    leaky_features: list[str] = []
                    for col in feature_cols:
                        if col not in df_for_tree.columns:
                            continue
                        # 计算每个特征值对应的正样本比例
                        try:
                            grouped = df_for_tree.groupby(col)[target_col].agg(['sum', 'count'])
                            # 如果某个特征的某些取值只有正样本或只有负样本，且覆盖了大部分数据
                            pure_positive = (grouped['sum'] == grouped['count']).sum()  # 纯正样本的分组数
                            pure_negative = (grouped['sum'] == 0).sum()  # 纯负样本的分组数
                            total_groups = len(grouped)
                            # 如果所有分组都是纯的（完美分离），标记为泄露特征
                            if total_groups > 0 and pure_positive + pure_negative == total_groups:
                                # 进一步检查：确保不是因为分组太细导致的
                                # 如果分组数少于10且完美分离，很可能是泄露
                                if total_groups <= 10:
                                    leaky_features.append(col)
                                    logger.warning(f"[Pipeline] Detected potential data leakage feature: {col} "
                                                 f"(perfectly separates target with {total_groups} groups)")
                        except Exception:
                            pass  # 忽略计算错误
                    
                    if leaky_features:
                        logger.warning(f"[Pipeline] Excluding {len(leaky_features)} potential leakage features: {leaky_features}")
                        feature_cols = [f for f in feature_cols if f not in leaky_features]
                        df_for_tree = df_for_tree[[target_col, actual_weight_col] + feature_cols]
                    
                    # 保存过滤后的特征列表，用于后续检查点保存
                    feature_cols_for_rules = feature_cols.copy()
                
                # 添加调试日志：目标变量分布
                target_dist = df_for_tree[target_col].value_counts()
                logger.info(f"[Pipeline] Full-tree input: samples={len(df_for_tree)}, features={len(feature_cols)}, "
                           f"target_dist={target_dist.to_dict()}, min_samples_leaf={self.miner.min_samples_leaf}, max_depth={self.miner.max_depth}")
                
                # Extract rules from full-feature tree
                all_rules = self.miner._get_rules_from_tree(
                    df_for_tree,
                    feature_cols,
                    target=target_col,
                    weight=actual_weight_col,
                    if_all_nodes=False,  # Only leaf nodes
                    var_name_dict=var_name_dict
                )
                
                # 保存全特征树用于可视化（已在 _get_rules_from_tree 中保存到 last_tree_）
                self.full_tree_ = self.miner.last_tree_
                self.full_tree_features_ = self.miner.last_tree_features_.copy()
                
                logger.info(f"[Pipeline] Full-feature tree mining completed: rules={len(all_rules)}, "
                           f"depth={self.full_tree_.get_depth()}, leaves={self.full_tree_.get_n_leaves()}, "
                           f"features={len(feature_cols)}")
                
                # Full Tree 模式无规则来源统计（规则都来自同一棵树）
                self.rule_source_stats_ = None
            else:
                # Multi-variable combination rule mining (decision tree)
                # 组合树模式：遍历特征组合，规则更丰富
                logger.info("[Pipeline] Using combination tree for rule mining...")
                assert isinstance(self.miner, RuleMiner)  # Type narrowing
                
                # 设置 One-Hot 映射用于规则可读性转换
                self.miner.set_onehot_mapping(onehot_mapping, onehot_indicator)
                
                all_rules = self.miner.generate_rules(
                    df_processed, feature_cols, target_col, weight_col,
                    onehot_indicator=self.onehot_indicator,
                    var_name_dict=var_name_dict
                )
                
                # 组合树模式：生成规则来源统计（用于替代决策树可视化）
                self._generate_rule_source_stats(all_rules, feature_cols)
                logger.info(f"[Pipeline] After _generate_rule_source_stats: rule_source_stats_={self.rule_source_stats_ is not None}, type={type(self.rule_source_stats_)}")
                
                # 组合树模式不生成全特征树
                self.full_tree_ = None
                self.full_tree_features_ = []
                
                # 组合树模式不进行数据泄露检测，直接使用原始特征列表
                if feature_cols_for_rules is None:
                    feature_cols_for_rules = feature_cols.copy()
                
                logger.info(f"[Pipeline] Combination tree mining completed: rules={len(all_rules)}")
            
            results['all_rules'] = all_rules
            
            # Build output preview for generating_rules stage
            # 准备规则预览数据（前10条，用于前端展示）
            rules_preview_data = []
            # 准备全量规则数据（用于CSV下载）
            all_rules_for_download = []
            if len(all_rules) > 0:
                # 预览列（前端表格展示）
                preview_cols = ['rule', 'used_var', 'support', 'confidence', 'lift', 'hit_rate', 'recall', 'bad_rate']
                available_cols = [c for c in preview_cols if c in all_rules.columns]
                if available_cols:
                    preview_df = all_rules[available_cols].head(10)
                    rules_preview_data = preview_df.to_dict('records')
                
                # 全量数据（CSV下载）- 包含所有可用列
                download_cols = ['rule', 'support', 'confidence', 'lift', 'hit_rate', 'recall', 'bad_rate']
                available_download_cols = [c for c in download_cols if c in all_rules.columns]
                if available_download_cols:
                    download_df = all_rules[available_download_cols].copy()
                    # 转换为可序列化的格式
                    all_rules_for_download = download_df.to_dict('records')
            
            generating_rules_preview: dict[str, Any] = {
                "total_rules": len(all_rules),
                "mining_mode": self.mining_mode,
                "has_full_tree": self.full_tree_ is not None,
                # 新增：用于前端展示和AI分析的参数信息
                "use_full_tree": self.use_full_tree if self.mining_mode == "multi" else None,
                "n_vars": self.n_vars if self.mining_mode == "multi" else None,
                "max_depth": self.max_depth if self.mining_mode == "multi" else None,
                "min_samples_leaf": self.min_samples_leaf if self.mining_mode == "multi" else None,
                "n_bins": self.n_bins if self.mining_mode == "single" else None,
                "bin_method": self.bin_method if self.mining_mode == "single" else None,
                # 规则预览数据（前10条，用于前端表格展示）
                "rules_preview": rules_preview_data,
                # 全量规则数据（用于CSV下载）
                "all_rules_for_download": all_rules_for_download,
                # Phase 6: 添加完整阶段数据用于检查点保存
                "_full_stage_data": {
                    "df_processed": df_processed,
                    "results": dict(results),
                    "feature_cols": feature_cols,
                    # 保存规则生成阶段使用的特征列表（已排除数据泄露特征）
                    # 确保重试时使用相同的特征集，生成一致的规则数量
                    "feature_cols_for_rules": feature_cols_for_rules,
                    # 保存决策树用于可视化（Full Tree 模式）
                    "full_tree": self.full_tree_,
                    "full_tree_features": self.full_tree_features_,
                    # 保存规则来源统计（组合树模式）
                    "rule_source_stats": self.rule_source_stats_,
                }
            }
            logger.info(f"[Pipeline] Saving _full_stage_data: rule_source_stats={self.rule_source_stats_ is not None}, full_tree={self.full_tree_ is not None}")
            
            self._update_progress('generating_rules', 100.0, f'规则生成完成，共{len(all_rules)}条', output_preview=generating_rules_preview)
        
        # Stage 2: Rule Filtering (v2.0: 合并原 filtering_rules + evaluating_rules)
        # 包含：方向过滤 + 指标评估 + 阈值筛选
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        
        if should_skip_stage('rule_filtering'):
            # 跳过已完成的阶段，从缓存恢复 output_preview
            logger.info("[Pipeline] Skipping rule_filtering stage (using cached data), restoring output_preview")
            evaluated_rules = results.get('evaluated_rules', pd.DataFrame())
            if 'rule_filtering' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['rule_filtering'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('rule_filtering', 100.0, f'规则筛选已跳过（使用缓存，有效规则{len(evaluated_rules)}条）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "after_count": len(evaluated_rules), "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('rule_filtering', 100.0, f'规则筛选已跳过（使用缓存，有效规则{len(evaluated_rules)}条）', output_preview=skip_preview)
        else:
            self._update_progress('rule_filtering', 0.0, '开始筛选规则...', code=self._get_stage_code('rule_filtering'))
            
            # Step 1: 方向过滤
            if self.mining_mode == 'single':
                # For single-var, we need to get direction from a separate method
                # Use RuleMiner's get_split_direction (create a temp instance if needed)
                temp_miner = RuleMiner()
                direction_df = temp_miner.get_split_direction(
                    df_processed, target_col, weight_col
                )
                results['direction'] = direction_df
                
                # Filter single-var rules by direction
                assert isinstance(self.miner, SingleVarRuleMiner)  # Type narrowing
                filtered_rules = self.miner.filter_by_direction(all_rules, direction_df)
            else:
                # Multi-var uses RuleMiner's built-in methods
                assert isinstance(self.miner, RuleMiner)  # Type narrowing for type checker
                direction_df = self.miner.get_split_direction(
                    df_processed, target_col, weight_col
                )
                results['direction'] = direction_df
                
                filtered_rules = self.miner.filter_rules(
                    all_rules, direction_df, score_vars=score_vars
                )
            results['filtered_rules'] = filtered_rules
            
            self._update_progress('rule_filtering', 40.0, f'方向过滤完成，剩余{len(filtered_rules)}条，开始评估指标...')
            
            # Step 2: 评估规则指标
            evaluated_rules = self.evaluator.evaluate_rules(
                df_processed, filtered_rules, target_col, weight_col
            )
            # BUG FIX: 保存筛选前的评估结果，用于构建全量规则状态
            evaluated_rules_before_filter = evaluated_rules.copy()
            
            self._update_progress('rule_filtering', 70.0, f'指标评估完成，开始阈值筛选...')
            
            # Step 3: 按阈值筛选
            final_evaluated_rules = self.evaluator.filter_by_metrics(
                evaluated_rules,
                max_hit_rate=self.max_hit_rate_filter,
                min_lift=self.min_lift_filter
            )
            results['evaluated_rules'] = final_evaluated_rules
            # BUG FIX: 更新 evaluated_rules 变量，确保后续 select_optimal_rules 使用筛选后的规则
            evaluated_rules = final_evaluated_rules
            
            # Build full rules filtering status for download
            # 构建全量规则筛选状态数据，用于CSV下载
            # BUG FIX: 使用筛选前的评估结果，确保被筛除的规则也有指标数据
            all_rules_with_status = self._build_rules_filtering_status(
                all_rules=all_rules,
                filtered_rules=filtered_rules,
                evaluated_rules=evaluated_rules_before_filter,  # 使用筛选前的数据
                final_rules=final_evaluated_rules,
                max_hit_rate=self.max_hit_rate_filter,
                min_lift=self.min_lift_filter
            )
            
            # 统计细分的筛选移除原因
            lift_removed = 0
            hit_rate_removed = 0
            bad_rate_zero_removed = 0
            for rule_status in all_rules_with_status:
                if rule_status.get('direction_valid') and not rule_status.get('is_valid'):
                    # 方向过滤通过但最终未通过的规则
                    if rule_status.get('bad_rate_valid') == False:
                        bad_rate_zero_removed += 1
                    if rule_status.get('lift_valid') == False:
                        lift_removed += 1
                    if rule_status.get('hit_rate_valid') == False:
                        hit_rate_removed += 1
            
            # Build output preview for rule_filtering stage (合并后的阶段)
            rule_filtering_preview: dict[str, Any] = {
                "generated_count": len(all_rules),
                "direction_filtered_count": len(filtered_rules),
                "after_count": len(final_evaluated_rules),
                "filter_criteria": {
                    "max_hit_rate": self.max_hit_rate_filter,
                    "min_lift": self.min_lift_filter
                },
                "filter_summary": {
                    "direction_removed": len(all_rules) - len(filtered_rules),
                    "bad_rate_zero_removed": bad_rate_zero_removed,
                    "lift_removed": lift_removed,
                    "hit_rate_removed": hit_rate_removed,
                    "total_removed": len(all_rules) - len(final_evaluated_rules)
                },
                # 全量规则筛选状态（用于CSV下载）
                "all_rules_with_status": all_rules_with_status,
                # Phase 6: 添加完整阶段数据用于检查点保存
                "_full_stage_data": {
                    "df_processed": df_processed,
                    "results": dict(results),
                    "feature_cols": feature_cols,
                    # 保存规则生成阶段使用的特征列表（已排除数据泄露特征）
                    # 确保重试时使用相同的特征集，生成一致的规则数量
                    "feature_cols_for_rules": feature_cols_for_rules,
                    # 保存决策树用于可视化（Full Tree 模式）
                    "full_tree": self.full_tree_,
                    "full_tree_features": self.full_tree_features_,
                }
            }
            
            self._update_progress('rule_filtering', 100.0, f'规则筛选完成，有效规则{len(evaluated_rules)}条', output_preview=rule_filtering_preview)
        
        # Stage 3: Select optimal rules
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        
        if should_skip_stage('selecting_rules'):
            # 跳过已完成的阶段，从缓存恢复 output_preview
            logger.info("[Pipeline] Skipping selecting_rules stage (using cached data), restoring output_preview")
            optimal_rules = results.get('optimal_rules', pd.DataFrame())
            # 恢复 all_rules_with_status（如果存在于缓存中）
            if 'all_rules_with_status' not in results and 'rule_filtering' in restored_output_previews:
                cached_status = restored_output_previews['rule_filtering'].get('all_rules_with_status', [])
                if cached_status:
                    # 添加 is_optimal 标记
                    optimal_rule_set = set(optimal_rules['rule'].astype(str).tolist()) if len(optimal_rules) > 0 else set()
                    results['all_rules_with_status'] = [
                        {**r, 'is_optimal': r['rule'] in optimal_rule_set} for r in cached_status
                    ]
            if 'selecting_rules' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['selecting_rules'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('selecting_rules', 100.0, f'最优规则选择已跳过（使用缓存，共{len(optimal_rules)}条）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "after_count": len(optimal_rules), "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('selecting_rules', 100.0, f'最优规则选择已跳过（使用缓存，共{len(optimal_rules)}条）', output_preview=skip_preview)
        else:
            self._update_progress('selecting_rules', 0.0, '开始选择最优规则集...', code=self._get_stage_code('selecting_rules'))
            
            optimal_rules = self.selector.select_optimal_rules(
                df_processed, evaluated_rules, target_col, weight_col,
                max_hit_rate=self.max_hit_rate_select,
                min_recall_ruleset=self.min_recall_ruleset,
                min_bad_rate_ruleset=self.min_bad_rate_ruleset,
                target_bad_rate_ruleset=self.target_bad_rate_ruleset,
                min_lift_ruleset=self.min_lift_ruleset,
                allow_overlap=self.allow_overlap,
                var_name_dict=var_name_dict
            )
            results['optimal_rules'] = optimal_rules
            
            # v2.2: 构建被淘汰规则统计（用于前端展示淘汰原因）
            # 比较 evaluated_rules（候选）和 optimal_rules（最优），找出被淘汰的规则
            optimal_rule_set_for_stats = set(optimal_rules['rule'].astype(str).tolist()) if len(optimal_rules) > 0 else set()
            rejected_rules_list = []
            
            # v2.6: 优先从results获取原始坏账率（数据预处理阶段已计算），避免重复计算
            original_bad_rate = results.get('original_bad_rate')
            if original_bad_rate is None:
                # 兼容旧任务：如果results中没有，重新计算
                original_bad_rate = df_processed[target_col].mean() if target_col in df_processed.columns else 0.0
            
            # 获取最优规则集的累计指标（v2.5: 提前计算，用于构建selecting_rules_preview）
            optimal_cum_hit_rate = 0.0
            optimal_cum_bad_rate = 0.0
            optimal_cum_recall = 0.0
            optimal_cum_lift = 0.0
            if len(optimal_rules) > 0:
                if 'dev_cum_hit_rate' in optimal_rules.columns:
                    optimal_cum_hit_rate = float(optimal_rules['dev_cum_hit_rate'].iloc[-1]) if pd.notna(optimal_rules['dev_cum_hit_rate'].iloc[-1]) else 0.0
                if 'dev_cum_bad_rate' in optimal_rules.columns:
                    optimal_cum_bad_rate = float(optimal_rules['dev_cum_bad_rate'].iloc[-1]) if pd.notna(optimal_rules['dev_cum_bad_rate'].iloc[-1]) else 0.0
                if 'dev_cum_recall' in optimal_rules.columns:
                    optimal_cum_recall = float(optimal_rules['dev_cum_recall'].iloc[-1]) if pd.notna(optimal_rules['dev_cum_recall'].iloc[-1]) else 0.0
                if 'dev_cum_lift' in optimal_rules.columns:
                    optimal_cum_lift = float(optimal_rules['dev_cum_lift'].iloc[-1]) if pd.notna(optimal_rules['dev_cum_lift'].iloc[-1]) else 0.0
            
            # Build output preview for selecting_rules stage
            selection_mode = "允许重叠" if self.allow_overlap else "贪婪算法"
            
            # 构建全量最优规则列表（用于CSV下载）
            # 注意：optimal_rules DataFrame 包含：
            #   - 单条规则指标：hit_rate, recall, bad_rate（原始值）
            #   - 累计指标：dev_cum_hit_rate, dev_cum_recall, dev_cum_bad_rate, dev_cum_lift
            all_optimal_rules_list = []
            if len(optimal_rules) > 0:
                for _, row in optimal_rules.iterrows():
                    all_optimal_rules_list.append({
                        "rule": row.get('rule', str(row.get('condition', ''))),
                        # 单条规则的原始指标
                        "hit_rate": float(row.get('hit_rate', 0)) if 'hit_rate' in row and pd.notna(row.get('hit_rate')) else None,
                        "bad_rate": float(row.get('bad_rate', 0)) if 'bad_rate' in row and pd.notna(row.get('bad_rate')) else None,
                        "lift": float(row.get('lift', 0)),
                        "recall": float(row.get('recall', 0)) if 'recall' in row and pd.notna(row.get('recall')) else None,
                        # 累计指标
                        "cumulative_hit_rate": float(row.get('dev_cum_hit_rate', 0)) if 'dev_cum_hit_rate' in row else None,
                        "cumulative_recall": float(row.get('dev_cum_recall', 0)) if 'dev_cum_recall' in row else None,
                        "cumulative_bad_rate": float(row.get('dev_cum_bad_rate', 0)) if 'dev_cum_bad_rate' in row else None,
                        "cumulative_lift": float(row.get('dev_cum_lift', 0)) if 'dev_cum_lift' in row else None,
                    })
            
            selecting_rules_preview: dict[str, Any] = {
                "before_count": len(evaluated_rules),
                "after_count": len(optimal_rules),
                "max_hit_rate": self.max_hit_rate_select,
                "selection_mode": selection_mode,
                "allow_overlap": self.allow_overlap,
                # 规则集级别风险目标配置
                "risk_targets": {
                    "min_recall_ruleset": self.min_recall_ruleset,
                    "min_bad_rate_ruleset": self.min_bad_rate_ruleset,
                    "target_bad_rate_ruleset": self.target_bad_rate_ruleset,
                    "min_lift_ruleset": self.min_lift_ruleset,
                },
                # v2.5: 规则集汇总指标（用于前端展示和淘汰原因参照）
                "ruleset_summary": {
                    "cumulative_hit_rate": optimal_cum_hit_rate,  # 累计命中率
                    "cumulative_recall": optimal_cum_recall,      # 累计召回率
                    "cumulative_bad_rate": optimal_cum_bad_rate,  # 命中样本的坏账率（非全样本）
                    "cumulative_lift": optimal_cum_lift,          # 累计提升度
                    # v2.6: 策略应用后的全样本坏账率（用于目标坏账率对比）
                    # 公式: new_bad_rate = original_bad_rate * (1 - recall) / (1 - hit_rate)
                    "estimated_overall_bad_rate": (
                        original_bad_rate * (1 - optimal_cum_recall) / (1 - optimal_cum_hit_rate)
                        if optimal_cum_hit_rate < 1 and original_bad_rate > 0
                        else None
                    ),
                    "original_bad_rate": original_bad_rate,  # 原始坏账率
                },
                "top_rules": [
                    {
                        "rule": row.get('rule', str(row.get('condition', ''))),
                        # 使用单条规则的原始指标
                        "hit_rate": float(row.get('hit_rate', 0)) if 'hit_rate' in row and pd.notna(row.get('hit_rate')) else float(row.get('dev_cum_hit_rate', 0)),
                        "lift": float(row.get('lift', 0))
                    }
                    for _, row in optimal_rules.head(5).iterrows()
                ] if len(optimal_rules) > 0 else [],
                # v2.0: 全量最优规则（用于CSV下载）
                "all_optimal_rules": all_optimal_rules_list,
                # Phase 6: 添加完整阶段数据用于检查点保存
                "_full_stage_data": {
                    "df_processed": df_processed,
                    "results": dict(results),
                    "feature_cols": feature_cols,
                    # 保存规则生成阶段使用的特征列表（已排除数据泄露特征）
                    # 确保重试时使用相同的特征集，生成一致的规则数量
                    "feature_cols_for_rules": feature_cols_for_rules,
                    # 保存决策树用于可视化（Full Tree 模式）
                    "full_tree": self.full_tree_,
                    "full_tree_features": self.full_tree_features_,
                }
            }
            
            # v2.2: 构建被淘汰规则统计（用于前端展示淘汰原因）
            # 比较 evaluated_rules（候选）和 optimal_rules（最优），找出被淘汰的规则
            optimal_rule_set_for_stats = set(optimal_rules['rule'].astype(str).tolist()) if len(optimal_rules) > 0 else set()
            rejected_rules_list = []
            
            # 判断选择停止的原因
            # v2.4: 更准确的停止原因判断
            # 
            # 贪婪模式下的停止原因分析：
            # 1. 命中率达上限：当累计命中率接近阈值时（≥50%），说明命中率空间是主要限制
            # 2. 样本被消耗：当累计命中率远未达到阈值时（<50%），说明是样本重叠导致
            # 3. 召回率目标达成：设置了召回率目标且已达成
            # 
            # 说明：贪婪模式下，即使当前累计命中率未达阈值，下一条规则可能因为
            # 会导致超限而未被选中。此时虽然"技术上"没达到阈值，但"实际上"
            # 是命中率限制导致的停止。使用50%作为分界点来区分这两种情况。
            
            # 计算命中率使用率（当前累计命中率 / 最大命中率阈值）
            hit_rate_usage = optimal_cum_hit_rate / self.max_hit_rate_select if self.max_hit_rate_select > 0 else 0
            hit_rate_limit_reached = hit_rate_usage >= 0.5  # 使用超过50%的命中率空间
            
            # 计算当前召回率，判断是否已达成目标
            # v2.6: 使用上面计算的original_bad_rate
            total_dev_bad = df_processed[target_col].sum() if target_col in df_processed.columns else 0
            current_recall = optimal_cum_recall  # 直接使用累计召回率
            
            # 判断召回率目标是否达成（包括目标坏账率转换的召回率）
            recall_target_met = False
            target_recall_value = None
            if self.min_recall_ruleset is not None:
                target_recall_value = self.min_recall_ruleset
            if self.target_bad_rate_ruleset is not None:
                # 目标坏账率已转换为召回率约束
                if original_bad_rate > 0 and self.target_bad_rate_ruleset < original_bad_rate:
                    converted_recall = 1 - (self.target_bad_rate_ruleset / original_bad_rate) * (1 - self.max_hit_rate_select)
                    if target_recall_value is not None:
                        target_recall_value = max(target_recall_value, converted_recall)
                    else:
                        target_recall_value = converted_recall
            
            if target_recall_value is not None and current_recall >= target_recall_value * 0.95:  # 允许5%误差
                recall_target_met = True
            
            # 从 evaluated_rules 中找出未被选中的规则，并按坏账率排序确定排名
            evaluated_rules_sorted = evaluated_rules.sort_values('bad_rate', ascending=False).reset_index(drop=True)
            rule_rank_map = {str(row['rule']): idx + 1 for idx, row in evaluated_rules_sorted.iterrows()}
            optimal_max_rank = max([rule_rank_map.get(r, 0) for r in optimal_rule_set_for_stats]) if optimal_rule_set_for_stats else 0
            
            for _, row in evaluated_rules.iterrows():
                rule_str = str(row.get('rule', row.get('condition', '')))
                if rule_str not in optimal_rule_set_for_stats:
                    # 判断淘汰原因
                    hit_rate = float(row.get('hit_rate', 0)) if 'hit_rate' in row and pd.notna(row.get('hit_rate')) else 0
                    bad_rate = float(row.get('bad_rate', 0)) if 'bad_rate' in row and pd.notna(row.get('bad_rate')) else 0
                    lift = float(row.get('lift', 0)) if 'lift' in row and pd.notna(row.get('lift')) else 0
                    rule_rank = rule_rank_map.get(rule_str, 0)
                    
                    # v2.5: 细化淘汰原因判断逻辑
                    # 
                    # 贪婪模式 vs 重叠模式的核心区别：
                    # - 贪婪模式：选中规则后移除其命中样本，剩余规则在剩余样本上重新计算坏账率
                    #   因此，即使原始坏账率很高的规则，也可能因为样本被先选中的规则消耗而没被选中
                    # - 重叠模式：按原始坏账率排序，依次选择直到命中率上限
                    #
                    # 淘汰原因优先级（贪婪模式）：
                    # 1. 目标已达成 - 召回率/目标坏账率达标后截断（明确的业务原因）
                    # 2. 命中率达上限 - 累计命中率超限后截断（明确的业务原因）
                    # 3. 样本被消耗 - 贪婪迭代中因样本被消耗而未被选中（默认原因）
                    #
                    # 淘汰原因优先级（重叠模式）：
                    # 1. 目标已达成
                    # 2. 命中率达上限
                    # 3. 排序靠后 - 按坏账率排序靠后未被选中
                    
                    if not self.allow_overlap:
                        # ========== 贪婪模式 ==========
                        # 贪婪模式下，未被选中的规则主要有三种情况：
                        # 1. 目标达成后被截断
                        # 2. 命中率达上限后被截断
                        # 3. 样本被消耗（包括：坏账率变0、命中样本与已选规则重叠等）
                        if recall_target_met and rule_rank > optimal_max_rank:
                            # 召回率目标达成后被截断
                            if self.target_bad_rate_ruleset is not None:
                                reason = "目标坏账率已达成"
                            else:
                                reason = "召回率目标已达成"
                        elif hit_rate_limit_reached and rule_rank > optimal_max_rank:
                            # 命中率达上限后被截断
                            reason = "命中率达上限"
                        else:
                            # 贪婪模式下的其他所有情况都归类为"样本被消耗"
                            # 包括：
                            # - 规则在迭代中坏账率变为0（被记录在_greedy_exhausted_rules中）
                            # - 规则的命中样本与已选规则高度重叠，在剩余样本上坏账率降低
                            # - 规则排名靠前但被更优规则"抢走"了样本
                            reason = "样本被消耗（贪婪模式）"
                    else:
                        # ========== 重叠模式 ==========
                        # 重叠模式按原始坏账率排序，未被选中主要是因为排序靠后
                        if recall_target_met and rule_rank > optimal_max_rank:
                            if self.target_bad_rate_ruleset is not None:
                                reason = "目标坏账率已达成"
                            else:
                                reason = "召回率目标已达成"
                        elif hit_rate_limit_reached and rule_rank > optimal_max_rank:
                            reason = "命中率达上限"
                        elif rule_rank > optimal_max_rank:
                            reason = f"排序靠后（坏账率第{rule_rank}名）"
                        else:
                            # 重叠模式下排名靠前但未被选中的特殊情况（理论上不应触发）
                            reason = "异常情况（请检查数据）"
                    
                    rejected_rules_list.append({
                        "rule": rule_str,
                        "hit_rate": hit_rate,
                        "bad_rate": bad_rate,
                        "lift": lift,
                        "reason": reason,
                        "rank": rule_rank,  # 添加排名信息
                    })
            
            # 按坏账率降序排列，展示被淘汰规则中坏账率最高的前10条
            rejected_rules_list.sort(key=lambda x: x['bad_rate'], reverse=True)
            
            # 统计淘汰原因分布 - 根据选择模式预定义所有可能的原因
            # 注：坏账率为0的规则在规则筛选阶段已被过滤，此处不再需要该原因
            # 贪婪模式的可能原因（v2.5: 移除"未被选中"，所有未被选中的规则都归类为"样本被消耗"）
            greedy_reasons = [
                "命中率达上限",
                "样本被消耗（贪婪模式）",
                "目标坏账率已达成",
                "召回率目标已达成",
            ]
            # 重叠模式的可能原因
            overlap_reasons = [
                "命中率达上限",
                "目标坏账率已达成",
                "召回率目标已达成",
                "排序靠后",  # 会带坏账率排名，需要特殊处理
                "异常情况（请检查数据）",  # 兜底分支，理论上不应触发
            ]
            
            # 根据当前模式选择原因列表
            possible_reasons = overlap_reasons if self.allow_overlap else greedy_reasons
            
            # 初始化所有可能原因为0
            reason_counts: dict[str, int] = {reason: 0 for reason in possible_reasons}
            
            # 统计实际的淘汰原因
            for r in rejected_rules_list:
                reason = r['reason']
                # 处理"排序靠后（坏账率第N名）"格式
                if reason.startswith("排序靠后"):
                    reason_counts["排序靠后"] = reason_counts.get("排序靠后", 0) + 1
                elif reason in reason_counts:
                    reason_counts[reason] += 1
                else:
                    # 未预定义的原因归入"未被选中"
                    reason_counts["未被选中"] = reason_counts.get("未被选中", 0) + 1
            
            # 计算总放弃数
            total_rejected = sum(reason_counts.values())
            
            selecting_rules_preview["rejected_rules_stats"] = {
                "total_rejected": total_rejected,
                "reason_distribution": reason_counts,
                "selection_mode": "overlap" if self.allow_overlap else "greedy",  # 标记当前模式
                "top_rejected_rules": rejected_rules_list,  # v2.3: 返回全部被淘汰规则（前端限定高度+滚动条）
            }
            
            self._update_progress('selecting_rules', 100.0, f'最优规则选择完成，共{len(optimal_rules)}条 ({selection_mode})', output_preview=selecting_rules_preview)
            
            # 更新 all_rules_with_status，添加 is_optimal 标记和淘汰原因
            # 用于前端"规则筛选过程"Tab展示和下载
            optimal_rule_set = set(optimal_rules['rule'].astype(str).tolist()) if len(optimal_rules) > 0 else set()
            
            # 构建淘汰原因映射（规则 -> 淘汰原因）
            rejection_reason_map = {r['rule']: r['reason'] for r in rejected_rules_list}
            rejection_rank_map = {r['rule']: r['rank'] for r in rejected_rules_list}
            
            all_rules_with_status_updated = []
            for rule_status in all_rules_with_status:
                rule_status_copy = dict(rule_status)
                rule_str = rule_status_copy['rule']
                rule_status_copy['is_optimal'] = rule_str in optimal_rule_set
                # v2.3: 添加淘汰原因（仅对未被选中的有效规则）
                if not rule_status_copy['is_optimal'] and rule_status_copy.get('is_valid', False):
                    rule_status_copy['rejection_reason'] = rejection_reason_map.get(rule_str, '未被选中')
                    rule_status_copy['rejection_rank'] = rejection_rank_map.get(rule_str)
                else:
                    rule_status_copy['rejection_reason'] = None
                    rule_status_copy['rejection_rank'] = None
                all_rules_with_status_updated.append(rule_status_copy)
            
            # 输出到 results，供前端使用
            results['all_rules_with_status'] = all_rules_with_status_updated
        
        # Stage 5b: Prior Rule Analysis (v6.2 - optional, if prior_rules provided)
        if prior_rules and len(prior_rules) > 0:
            if self._should_stop():
                raise TaskStoppedException("任务已被用户停止")
            
            if should_skip_stage('prior_analysis'):
                # 跳过已完成的阶段，从缓存恢复 output_preview
                logger.info("[Pipeline] Skipping prior_analysis stage (using cached data), restoring output_preview")
                if 'prior_analysis' in restored_output_previews:
                    restored_preview = restored_output_previews['prior_analysis'].copy()
                    restored_preview['_skip_expert_pause'] = True
                    restored_preview['_skipped_during_retry'] = True
                    restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                    self._update_progress('prior_analysis', 100.0, '先验规则分析已跳过（使用缓存）', output_preview=restored_preview)
                else:
                    skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True}
                    self._update_progress('prior_analysis', 100.0, '先验规则分析已跳过（使用缓存）', output_preview=skip_preview)
            else:
                self._update_progress('prior_analysis', 0.0, '开始先验规则分析...', code=self._get_stage_code('prior_analysis'))
            
            try:
                prior_analyzer = PriorRuleAnalyzer(prior_rules=prior_rules, weight_col=weight_col)
                prior_analyzer.fit(df_processed, target_col=target_col)
                
                # Analyze optimal rules with prior
                prior_results_df = prior_analyzer.analyze(optimal_rules)
                prior_summary = prior_analyzer.get_summary()
                
                results['prior_analysis'] = {
                    'enabled': True,
                    'prior_rules': prior_rules,
                    'results': prior_results_df,
                    'summary': prior_summary
                }
                
                # Build output preview
                prior_analysis_preview: dict[str, Any] = {
                    "prior_rules_count": len(prior_rules),
                    "prior_hit_rate": prior_summary['prior_metrics']['prior_hit_rate'],
                    "prior_recall": prior_summary['prior_metrics']['prior_recall'],
                    "avg_incremental_recall": float(prior_results_df['incremental_recall'].mean()) if 'incremental_recall' in prior_results_df.columns else 0,
                    "avg_overlap_rate": float(prior_results_df['overlap_rate'].mean()) if 'overlap_rate' in prior_results_df.columns else 0,
                    # Phase 25: 添加完整阶段数据用于检查点保存
                    "_full_stage_data": {
                        "df_processed": df_processed,
                        "results": dict(results),
                        "feature_cols": feature_cols,
                    }
                }
                
                self._update_progress('prior_analysis', 100.0, '先验规则分析完成', output_preview=prior_analysis_preview)
            except Exception as prior_err:
                results['prior_analysis'] = {
                    'enabled': False,
                    'error': str(prior_err)
                }
                results.setdefault('warnings', []).append(f'先验规则分析失败: {str(prior_err)}')
                self._update_progress('prior_analysis', 100.0, f'先验规则分析失败: {str(prior_err)}')
        else:
            results['prior_analysis'] = {'enabled': False}
        
        # Stage 5c: Amount Dimension Analysis (v6.2 - optional, if amount_col provided)
        if amount_col and amount_col in df_processed.columns:
            if self._should_stop():
                raise TaskStoppedException("任务已被用户停止")
            
            if should_skip_stage('amount_analysis'):
                # 跳过已完成的阶段，从缓存恢复 output_preview
                logger.info("[Pipeline] Skipping amount_analysis stage (using cached data), restoring output_preview")
                if 'amount_analysis' in restored_output_previews:
                    restored_preview = restored_output_previews['amount_analysis'].copy()
                    restored_preview['_skip_expert_pause'] = True
                    restored_preview['_skipped_during_retry'] = True
                    restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                    self._update_progress('amount_analysis', 100.0, '金额维度分析已跳过（使用缓存）', output_preview=restored_preview)
                else:
                    skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True}
                    self._update_progress('amount_analysis', 100.0, '金额维度分析已跳过（使用缓存）', output_preview=skip_preview)
            else:
                self._update_progress('amount_analysis', 0.0, '开始金额维度分析...', code=self._get_stage_code('amount_analysis'))
            
                try:
                    amount_analyzer = AmountAnalyzer(amount_col=amount_col, weight_col=weight_col)
                    amount_analyzer.fit(df_processed, target_col=target_col)
                    
                    # Analyze optimal rules with amount dimension
                    amount_results_df, amount_summary = amount_analyzer.analyze_with_cumulative(optimal_rules)
                    
                    results['amount_analysis'] = {
                        'enabled': True,
                        'amount_col': amount_col,
                        'results': amount_results_df,
                        'summary': amount_summary
                    }
                    
                    # Build output preview
                    amount_analysis_preview: dict[str, Any] = {
                        "amount_col": amount_col,
                        "total_amount": amount_summary['total_amount'],
                        "total_bad_amount": amount_summary['total_bad_amount'],
                        "cum_amount_recall": amount_summary['cumulative']['amount_recall'],
                        "avg_amount_lift": float(amount_results_df['amount_lift'].mean()) if 'amount_lift' in amount_results_df.columns else 0,
                        # Phase 25: 添加完整阶段数据用于检查点保存
                        "_full_stage_data": {
                            "df_processed": df_processed,
                            "results": dict(results),
                            "feature_cols": feature_cols,
                        }
                    }
                    
                    self._update_progress('amount_analysis', 100.0, '金额维度分析完成', output_preview=amount_analysis_preview)
                except Exception as amount_err:
                    results['amount_analysis'] = {
                        'enabled': False,
                        'error': str(amount_err)
                    }
                    results.setdefault('warnings', []).append(f'金额维度分析失败: {str(amount_err)}')
                    self._update_progress('amount_analysis', 100.0, f'金额维度分析失败: {str(amount_err)}')
        else:
            results['amount_analysis'] = {'enabled': False}
        
        # Stage 6: Report Generation (mandatory stage for all SOP tasks)
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        
        if should_skip_stage('report_generation'):
            # 跳过已完成的阶段，从缓存恢复 output_preview
            logger.info("[Pipeline] Skipping report_generation stage (using cached data), restoring output_preview")
            if 'report_generation' in restored_output_previews:
                restored_preview = restored_output_previews['report_generation'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('report_generation', 100.0, '报告生成已跳过（使用缓存）', output_preview=restored_preview)
            else:
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True}
                self._update_progress('report_generation', 100.0, '报告生成已跳过（使用缓存）', output_preview=skip_preview)
        else:
            self._update_progress('report_generation', 0.0, '开始生成报告...', code=self._get_stage_code('report_generation'))
        
            try:
                from .rule_mining_viz import get_chart_data_for_frontend
                
                self._update_progress('report_generation', 30.0, '生成报告图表数据...')
                
                chart_data = get_chart_data_for_frontend(
                    optimal_rules_df=optimal_rules,
                    evaluated_rules_df=evaluated_rules
                )
                results['chart_data'] = chart_data
                
                # Phase 1: 规则质量验证
                self._update_progress('report_generation', 50.0, '执行规则质量验证...')
                try:
                    validator = RuleValidator()
                    validation_report = validator.validate(
                        optimal_rules, df_processed, target_col, weight_col
                    )
                    results['validation_report'] = validation_report
                except Exception as val_err:
                    results['validation_report'] = None
                    results.setdefault('warnings', []).append(f'规则质量验证失败: {str(val_err)}')
                
                # Phase 2: 规则稳定性检测（PSI）- 如果有时间列或验证集
                self._update_progress('report_generation', 70.0, '计算规则稳定性...')
                try:
                    # 确定用于PSI计算的规则集（优先最优规则，其次过滤后规则）
                    psi_rules = optimal_rules if len(optimal_rules) > 0 else filtered_rules[:20]  # 最多取前20条
                    
                    # 确定用于PSI计算的时间列
                    # 优先级：1. 用户指定的psi_time_col  2. 自动检测  3. 随机分割
                    effective_time_col = None
                    
                    if psi_time_col and psi_time_col in df_processed.columns:
                        # 用户明确指定了时间列
                        effective_time_col = psi_time_col
                        logger.info(f"使用用户指定的PSI时间列: {psi_time_col}")
                    else:
                        # 自动检测时间列
                        time_keywords = ['time', 'date', 'period', '日期', '时间', '期数']
                        time_cols = [c for c in df_processed.columns 
                                     if any(kw in c.lower() for kw in time_keywords)]
                        if time_cols:
                            effective_time_col = time_cols[0]
                            logger.info(f"自动检测到PSI时间列: {effective_time_col}")
                    
                    if effective_time_col and len(psi_rules) > 0:
                        psi_report = self.evaluator.calculate_rule_psi_by_time(
                            psi_rules, df_processed, effective_time_col, target_col
                        )
                        results['psi_report'] = psi_report.to_dict('records')
                        results['psi_time_col_used'] = effective_time_col
                    else:
                        # 无时间列时，使用简单的随机分割
                        n_samples = len(df_processed)
                        if n_samples > 100 and len(psi_rules) > 0:
                            df_base = df_processed.iloc[:n_samples//2]
                            df_compare = df_processed.iloc[n_samples//2:]
                            psi_report = self.evaluator.calculate_rule_psi(
                                psi_rules, df_base, df_compare, target_col
                            )
                            results['psi_report'] = psi_report.to_dict('records')
                        else:
                            results['psi_report'] = []
                            logger.info(f"[PSI] 跳过PSI计算: n_samples={n_samples}, psi_rules={len(psi_rules)}")
                except Exception as psi_err:
                    results['psi_report'] = []
                    results.setdefault('warnings', []).append(f'PSI计算失败: {str(psi_err)}')
                
                # Phase 3: 决策树结构数据 / 规则来源统计（根据挖掘模式）
                self._update_progress('report_generation', 85.0, '生成可视化数据...')
                try:
                    logger.info(f"[TreeViz] mining_mode={self.mining_mode}, use_full_tree={self.use_full_tree}")
                    if self.mining_mode == 'multi':
                        if self.use_full_tree:
                            # Full Tree 模式：生成决策树可视化
                            if self.full_tree_ is not None:
                                # 调试：检查决策树数据
                                tree_obj = self.full_tree_.tree_
                                root_value = tree_obj.value[0]
                                logger.info(f"[TreeViz] Root node value shape: {root_value.shape}, value: {root_value}")
                                logger.info(f"[TreeViz] Root node samples: {root_value.sum()}, class0: {root_value[0][0]}, class1: {root_value[0][1]}")
                                
                                # 获取最优规则列表用于标记叶节点
                                optimal_rule_list = None
                                if len(optimal_rules) > 0 and 'rule' in optimal_rules.columns:
                                    optimal_rule_list = optimal_rules['rule'].astype(str).tolist()
                                    logger.info(f"[TreeViz] 传入最优规则数: {len(optimal_rule_list)}")
                                
                                from .rule_mining_viz import get_tree_structure_data
                                tree_data = get_tree_structure_data(
                                    self.full_tree_,
                                    feature_names=self.full_tree_features_,
                                    class_names=['Good', 'Bad'],
                                    optimal_rules=optimal_rule_list
                                )
                                results['tree_structure'] = tree_data
                                results['rule_source_stats'] = None  # Full Tree 模式无规则来源统计
                                logger.info(f"决策树可视化数据已生成（全特征树）: depth={tree_data.get('max_depth')}, leaves={tree_data.get('n_leaves')}, has_optimal_info={tree_data.get('has_optimal_info')}")
                                logger.info(f"[TreeViz] Root node in result: samples={tree_data['tree'].get('samples')}, bad_rate={tree_data['tree'].get('bad_rate')}")
                            else:
                                results['tree_structure'] = None
                                results['rule_source_stats'] = None
                                logger.warning("[TreeViz] Full tree not available")
                        else:
                            # 组合树模式：生成规则来源统计（替代决策树可视化）
                            results['tree_structure'] = None  # 组合树模式不展示决策树
                            rule_source_stats = getattr(self, 'rule_source_stats_', None)
                            logger.info(f"[RuleSource] Checking rule_source_stats_: hasattr={hasattr(self, 'rule_source_stats_')}, value_type={type(rule_source_stats)}, is_none={rule_source_stats is None}")
                            results['rule_source_stats'] = rule_source_stats
                            if results['rule_source_stats']:
                                logger.info(f"规则来源统计已生成: {results['rule_source_stats'].get('total_combinations', 0)} 个组合, keys={list(results['rule_source_stats'].keys())}")
                            else:
                                logger.warning("[RuleSource] Rule source stats not available - this indicates _generate_rule_source_stats was not called or returned None")
                    else:
                        # 单特征模式：无决策树可视化，无规则来源统计
                        results['tree_structure'] = None
                        results['rule_source_stats'] = None
                        logger.info(f"[TreeViz] Skipping viz: mining_mode={self.mining_mode}")
                except Exception as viz_err:
                    results['tree_structure'] = None
                    results['rule_source_stats'] = None
                    logger.error(f"[TreeViz] 可视化数据生成失败: {str(viz_err)}")
                    results.setdefault('warnings', []).append(f'可视化数据生成失败: {str(viz_err)}')
                
                # Build output preview for report_generation stage
                # Phase 10: 丰富output_preview，包含更多有意义的信息供AI分析使用
                validation_report = results.get('validation_report', {})
                psi_report = results.get('psi_report', [])
                
                # Phase 21: 构建完整的报告章节列表（与开发结果Tab对应）
                report_sections_list = ["样本及特征", "评估图表", "最优规则", "筛选过程", "质量验证", "稳定性"]
                # 附加分析（如有）
                if results.get('amount_analysis') or results.get('prior_analysis'):
                    report_sections_list.append("附加分析")
                # 决策树（如有）
                if results.get('tree_structure'):
                    report_sections_list.append("决策树")
                
                report_generation_preview: dict[str, Any] = {
                    # 基本信息
                    "status": "已完成",
                    "report_sections": report_sections_list,
                    
                    # 图表数据
                    "chart_types": list(chart_data.keys()) if chart_data else [],
                    "has_chart_data": chart_data is not None,
                    
                    # 规则质量验证结果（Phase 21: 添加overlap详细数据）
                    "quality_score": validation_report.get('quality_score', None) if validation_report else None,
                    "quality_level": validation_report.get('quality_level', None) if validation_report else None,
                    "validation_passed": validation_report.get('passed', False) if validation_report else False,
                    "validation_issues": validation_report.get('warnings', [])[:5] if validation_report else [],  # 最多5个问题
                    "overlap_info": {
                        "avg_overlap": validation_report.get('overlap_report', {}).get('avg_overlap', 0) if validation_report else 0,
                        "high_overlap_pairs": len(validation_report.get('overlap_report', {}).get('high_overlap_pairs', [])) if validation_report else 0
                    } if validation_report else None,
                    
                    # PSI稳定性结果
                    "psi_calculated": len(psi_report) > 0,
                    "psi_summary": {
                        "total_rules_checked": len(psi_report),
                        "stable_rules": len([r for r in psi_report if r.get('psi', 1) < 0.1]) if psi_report else 0,
                        "unstable_rules": len([r for r in psi_report if r.get('psi', 0) >= 0.25]) if psi_report else 0,
                        "avg_psi": sum(r.get('psi', 0) for r in psi_report) / len(psi_report) if psi_report else None
                    } if psi_report else None,
                    
                    # 最终规则集摘要
                    "final_rules_count": len(optimal_rules),
                    "total_rules_evaluated": len(evaluated_rules) if evaluated_rules is not None else 0,
                    
                    # 可视化数据
                    "has_tree_structure": results.get('tree_structure') is not None,
                    "has_rule_source_stats": results.get('rule_source_stats') is not None,
                    "mining_method": "full_tree" if self.use_full_tree else "combination_tree",
                    
                    # Phase 25: 添加完整阶段数据用于检查点保存
                    "_full_stage_data": {
                        "df_processed": df_processed,
                        "results": dict(results),
                        "feature_cols": feature_cols,
                    }
                }
                
                self._update_progress('report_generation', 100.0, '报告生成完成', output_preview=report_generation_preview)
            except Exception as e:
                self._update_progress('report_generation', 100.0, f'图表数据生成失败: {str(e)}')
                results['chart_data'] = None
        
        # Final completed status
        completed_preview: dict[str, Any] = {
            "total_rules_generated": len(all_rules),
            "final_optimal_rules": len(optimal_rules),
            "mining_mode": self.mining_mode,
            "quality_score": results.get('validation_report', {}).get('quality_score', None) if results.get('validation_report') else None
        }
        
        self._update_progress('completed', 100.0, '规则挖掘流程完成', output_preview=completed_preview)
        
        return results
