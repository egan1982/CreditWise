"""
General Data Preprocessing Module

Provides reusable data preprocessing utilities for various analysis tasks:
- Datetime column detection and feature extraction
- Text column detection and feature extraction
- Categorical column detection and One-Hot encoding
- ID/constant column detection and removal

These utilities can be used independently or integrated into task-specific pipelines.
"""

import pandas as pd
import numpy as np
import re
import logging
from typing import Any
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

logger = logging.getLogger(__name__)


class DatetimeProcessor:
    """
    Datetime column processor for feature extraction.
    
    Provides automatic detection and feature extraction from datetime columns,
    converting temporal data into numeric features suitable for machine learning.
    
    Supported features:
    - year: Year (e.g., 2024)
    - month: Month (1-12)
    - day: Day of month (1-31)
    - dayofweek: Day of week (0=Monday, 6=Sunday)
    - hour: Hour (0-23)
    - minute: Minute (0-59)
    - quarter: Quarter (1-4)
    - is_weekend: Weekend flag (0/1)
    - is_month_start: Month start flag (0/1)
    - is_month_end: Month end flag (0/1)
    - days_since: Days since reference date
    
    Example:
        >>> processor = DatetimeProcessor(indicator='_dt_')
        >>> df_processed, new_cols = processor.process(df, datetime_cols=['create_time'])
    """
    
    # All supported datetime features
    SUPPORTED_FEATURES = [
        'year', 'month', 'day', 'dayofweek', 'hour', 'minute',
        'quarter', 'is_weekend', 'is_month_start', 'is_month_end', 'days_since'
    ]
    
    # Default features to extract
    DEFAULT_FEATURES = ['year', 'month', 'dayofweek', 'hour', 'days_since']
    
    def __init__(self, indicator: str = '_dt_'):
        """
        Initialize DatetimeProcessor.
        
        Args:
            indicator: String indicator for derived column names (default: '_dt_')
                       Example: 'create_time' -> 'create_time_dt_year'
        """
        self.indicator = indicator
        self.processed_cols_: list[str] = []
        self.derived_mapping_: dict[str, list[str]] = {}
    
    @staticmethod
    def detect(
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None,
        sample_size: int = 100
    ) -> list[str]:
        """
        Auto-detect datetime columns in a DataFrame.
        
        Detection logic:
        1. Columns with datetime64 dtype are detected
        2. Object columns that can be parsed as datetime are detected
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from detection
            sample_size: Number of rows to sample for parsing test
            
        Returns:
            List of detected datetime column names
        """
        exclude_cols = exclude_cols or []
        datetime_cols: list[str] = []
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            
            # Check if already datetime type
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                datetime_cols.append(col)
            # Check if object type that looks like datetime
            elif df[col].dtype == 'object':
                sample = df[col].dropna().head(sample_size)
                if len(sample) > 0:
                    try:
                        pd.to_datetime(sample, errors='raise')
                        datetime_cols.append(col)
                    except (ValueError, TypeError):
                        pass
        
        return datetime_cols
    
    def extract_features(
        self,
        df: pd.DataFrame,
        datetime_cols: list[str] | None = None,
        features: list[str] | None = None,
        reference_date: pd.Timestamp | None = None,
        exclude_cols: list[str] | None = None,
        drop_original: bool = True
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Extract numeric features from datetime columns.
        
        Args:
            df: Input DataFrame
            datetime_cols: Datetime columns to process (auto-detects if None)
            features: Features to extract (see SUPPORTED_FEATURES)
                      Defaults to DEFAULT_FEATURES if None
            reference_date: Reference date for 'days_since' calculation
                           Defaults to max date in each column
            exclude_cols: Columns to exclude from processing
            drop_original: Whether to drop original datetime columns (default: True)
            
        Returns:
            Tuple of (processed DataFrame, list of new column names)
        """
        df_result = df.copy()
        new_cols: list[str] = []
        exclude_cols = exclude_cols or []
        
        # Use default features if not specified
        if features is None:
            features = self.DEFAULT_FEATURES.copy()
        
        # Validate features
        invalid_features = set(features) - set(self.SUPPORTED_FEATURES)
        if invalid_features:
            raise ValueError(f"Unsupported features: {invalid_features}. "
                           f"Supported: {self.SUPPORTED_FEATURES}")
        
        # Auto-detect datetime columns if not provided
        if datetime_cols is None:
            datetime_cols = self.detect(df_result, exclude_cols)
        else:
            datetime_cols = [c for c in datetime_cols if c not in exclude_cols and c in df_result.columns]
        
        if not datetime_cols:
            return df_result, new_cols
        
        for col in datetime_cols:
            # Convert to datetime if not already
            if not pd.api.types.is_datetime64_any_dtype(df_result[col]):
                try:
                    df_result[col] = pd.to_datetime(df_result[col], errors='coerce')
                except Exception:
                    continue
            
            derived_cols: list[str] = []
            dt_accessor = df_result[col].dt
            
            # Extract each requested feature
            feature_extractors = {
                'year': lambda: dt_accessor.year,
                'month': lambda: dt_accessor.month,
                'day': lambda: dt_accessor.day,
                'dayofweek': lambda: dt_accessor.dayofweek,
                'hour': lambda: dt_accessor.hour,
                'minute': lambda: dt_accessor.minute,
                'quarter': lambda: dt_accessor.quarter,
                'is_weekend': lambda: (dt_accessor.dayofweek >= 5).astype(int),
                'is_month_start': lambda: dt_accessor.is_month_start.astype(int),
                'is_month_end': lambda: dt_accessor.is_month_end.astype(int),
            }
            
            for feature in features:
                if feature in feature_extractors:
                    new_col = f"{col}{self.indicator}{feature}"
                    df_result[new_col] = feature_extractors[feature]()
                    derived_cols.append(new_col)
                elif feature == 'days_since':
                    # Special handling for days_since
                    ref_date = reference_date if reference_date else df_result[col].max()
                    if pd.notna(ref_date):
                        new_col = f"{col}{self.indicator}days_since"
                        df_result[new_col] = (ref_date - df_result[col]).dt.days
                        derived_cols.append(new_col)
            
            # Record mapping
            self.derived_mapping_[col] = derived_cols
            new_cols.extend(derived_cols)
            
            # Drop original column if requested
            if drop_original:
                df_result = df_result.drop(columns=[col])
        
        self.processed_cols_ = datetime_cols
        return df_result, new_cols
    
    def process(
        self,
        df: pd.DataFrame,
        datetime_cols: list[str] | None = None,
        features: list[str] | None = None,
        reference_date: pd.Timestamp | None = None,
        exclude_cols: list[str] | None = None,
        drop_original: bool = True
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Alias for extract_features() for convenience.
        """
        return self.extract_features(
            df, datetime_cols, features, reference_date, exclude_cols, drop_original
        )


class TextProcessor:
    """
    Text column processor for feature extraction.
    
    Provides automatic detection and feature extraction from text columns,
    converting textual data into numeric features suitable for machine learning.
    
    Supported features:
    - length: Character count
    - word_count: Word count (split by whitespace)
    - has_digits: Contains digits flag (0/1)
    - has_chinese: Contains Chinese characters flag (0/1)
    - has_english: Contains English letters flag (0/1)
    - has_special: Contains special characters flag (0/1)
    - is_empty: Is empty or whitespace only flag (0/1)
    - digit_ratio: Ratio of digit characters
    - upper_ratio: Ratio of uppercase characters
    
    Additionally supports custom keyword detection.
    
    Example:
        >>> processor = TextProcessor(indicator='_txt_')
        >>> df_processed, new_cols = processor.process(
        ...     df, text_cols=['comment'],
        ...     keywords={'has_complaint': ['投诉', '差评']}
        ... )
    """
    
    # All supported text features
    SUPPORTED_FEATURES = [
        'length', 'word_count', 'has_digits', 'has_chinese', 'has_english',
        'has_special', 'is_empty', 'digit_ratio', 'upper_ratio'
    ]
    
    # Default features to extract
    DEFAULT_FEATURES = ['length', 'word_count']
    
    def __init__(self, indicator: str = '_txt_'):
        """
        Initialize TextProcessor.
        
        Args:
            indicator: String indicator for derived column names (default: '_txt_')
                       Example: 'comment' -> 'comment_txt_length'
        """
        self.indicator = indicator
        self.processed_cols_: list[str] = []
        self.derived_mapping_: dict[str, list[str]] = {}
    
    @staticmethod
    def detect(
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None,
        min_unique_ratio: float = 0.5,
        min_avg_length: int = 20
    ) -> list[str]:
        """
        Auto-detect text columns in a DataFrame.
        
        Detection logic:
        - Object/string dtype columns
        - High cardinality (unique ratio >= min_unique_ratio)
        - Long average length (>= min_avg_length)
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from detection
            min_unique_ratio: Minimum ratio of unique values to total rows
            min_avg_length: Minimum average string length
            
        Returns:
            List of detected text column names
        """
        exclude_cols = exclude_cols or []
        text_cols: list[str] = []
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            
            if df[col].dtype != 'object':
                continue
            
            # Check unique ratio (high cardinality)
            unique_ratio = df[col].nunique() / len(df) if len(df) > 0 else 0
            
            # Check average length
            avg_length = df[col].dropna().astype(str).str.len().mean()
            
            if unique_ratio >= min_unique_ratio and avg_length >= min_avg_length:
                text_cols.append(col)
        
        return text_cols
    
    def extract_features(
        self,
        df: pd.DataFrame,
        text_cols: list[str] | None = None,
        features: list[str] | None = None,
        keywords: dict[str, list[str]] | None = None,
        exclude_cols: list[str] | None = None,
        drop_original: bool = True
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Extract numeric features from text columns.
        
        Args:
            df: Input DataFrame
            text_cols: Text columns to process (auto-detects if None)
            features: Features to extract (see SUPPORTED_FEATURES)
                      Defaults to DEFAULT_FEATURES if None
            keywords: Dict of {feature_name: [keyword_list]} for keyword detection
                      Example: {'has_complaint': ['投诉', '不满', '差评']}
            exclude_cols: Columns to exclude from processing
            drop_original: Whether to drop original text columns (default: True)
            
        Returns:
            Tuple of (processed DataFrame, list of new column names)
        """
        df_result = df.copy()
        new_cols: list[str] = []
        exclude_cols = exclude_cols or []
        
        # Use default features if not specified
        if features is None:
            features = self.DEFAULT_FEATURES.copy()
        
        # Validate features
        invalid_features = set(features) - set(self.SUPPORTED_FEATURES)
        if invalid_features:
            raise ValueError(f"Unsupported features: {invalid_features}. "
                           f"Supported: {self.SUPPORTED_FEATURES}")
        
        # Auto-detect text columns if not provided
        if text_cols is None:
            text_cols = self.detect(df_result, exclude_cols)
        else:
            text_cols = [c for c in text_cols if c not in exclude_cols and c in df_result.columns]
        
        if not text_cols:
            return df_result, new_cols
        
        for col in text_cols:
            derived_cols: list[str] = []
            
            # Ensure string type
            str_series = df_result[col].fillna('').astype(str)
            
            # Feature extraction mapping
            feature_extractors = {
                'length': lambda s: s.str.len(),
                'word_count': lambda s: s.str.split().str.len(),
                'has_digits': lambda s: s.str.contains(r'\d', regex=True).astype(int),
                'has_chinese': lambda s: s.str.contains(r'[\u4e00-\u9fff]', regex=True).astype(int),
                'has_english': lambda s: s.str.contains(r'[a-zA-Z]', regex=True).astype(int),
                'has_special': lambda s: s.str.contains(r'[!@#$%^&*(),.?":{}|<>]', regex=True).astype(int),
                'is_empty': lambda s: (s.str.strip() == '').astype(int),
                'digit_ratio': lambda s: s.apply(lambda x: sum(c.isdigit() for c in x) / max(len(x), 1)),
                'upper_ratio': lambda s: s.apply(lambda x: sum(c.isupper() for c in x) / max(len(x), 1)),
            }
            
            for feature in features:
                if feature in feature_extractors:
                    new_col = f"{col}{self.indicator}{feature}"
                    df_result[new_col] = feature_extractors[feature](str_series)
                    derived_cols.append(new_col)
            
            # Keyword detection
            if keywords:
                for feature_name, keyword_list in keywords.items():
                    if keyword_list:
                        new_col = f"{col}{self.indicator}{feature_name}"
                        pattern = '|'.join(re.escape(kw) for kw in keyword_list)
                        df_result[new_col] = str_series.str.contains(
                            pattern, regex=True, case=False
                        ).astype(int)
                        derived_cols.append(new_col)
            
            # Record mapping
            self.derived_mapping_[col] = derived_cols
            new_cols.extend(derived_cols)
            
            # Drop original column if requested
            if drop_original:
                df_result = df_result.drop(columns=[col])
        
        self.processed_cols_ = text_cols
        return df_result, new_cols
    
    def process(
        self,
        df: pd.DataFrame,
        text_cols: list[str] | None = None,
        features: list[str] | None = None,
        keywords: dict[str, list[str]] | None = None,
        exclude_cols: list[str] | None = None,
        drop_original: bool = True
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Alias for extract_features() for convenience.
        """
        return self.extract_features(
            df, text_cols, features, keywords, exclude_cols, drop_original
        )


class CategoricalProcessor:
    """
    Categorical column processor for encoding.
    
    Provides automatic detection and encoding of categorical columns.
    Currently supports One-Hot encoding, with potential for other methods.
    
    Example:
        >>> processor = CategoricalProcessor(indicator='_is_')
        >>> df_processed, new_cols = processor.onehot_encode(df, categorical_cols=['category'])
    """
    
    def __init__(self, indicator: str = '_is_'):
        """
        Initialize CategoricalProcessor.
        
        Args:
            indicator: String indicator for encoded column names (default: '_is_')
                       Example: 'category' with value 'A' -> 'category_is_A'
        """
        self.indicator = indicator
        self.processed_cols_: list[str] = []
        self.encoding_mapping_: dict[str, list[Any]] = {}
    
    @staticmethod
    def _is_categorical_int(col_data: 'pd.Series', col_name: str | None = None) -> tuple[bool, str]:
        """
        Detect if an integer column is likely a categorical variable.
        
        Uses layered "OR" logic to identify different types of encoded categorical variables:
        1. Small range continuous encoding (e.g., 0-9, 1-5 for education level)
        2. Sparse encoding (e.g., 10,20,30,40,90,99 for marital status)
        3. Binary variables (e.g., 0/1 for gender)
        4. Medium sparse encoding (e.g., province codes 11-65 with 31 values)
        
        Exclusion logic for ordinal numeric features:
        - If values start from 0 or 1 and are mostly consecutive, likely ordinal numeric
        - Examples: account count (0-71), transaction count (0-50)
        
        Args:
            col_data: Integer column data (pandas Series)
            col_name: Column name for logging (optional)
            
        Returns:
            Tuple of (is_categorical: bool, detection_reason: str)
        """
        unique_vals = sorted(col_data.dropna().unique())
        n_unique = len(unique_vals)
        
        if n_unique == 0:
            return False, "empty"
        
        min_val, max_val = unique_vals[0], unique_vals[-1]
        value_range = max_val - min_val + 1
        sparsity = n_unique / value_range if value_range > 0 else 1.0
        
        # ========== 排除条件：有序数值特征 ==========
        # 特征：从0或1开始，值域较大，稀疏度较高（接近连续）
        # 典型场景：账户数(0-71)、交易次数(0-50)、逾期天数(0-90)
        is_ordinal_numeric = (
            min_val in [0, 1] and           # 从0或1开始（计数特征的典型起点）
            max_val > 20 and                # 值域较大（超过评分/等级的典型范围）
            sparsity >= 0.3 and             # 稀疏度较高（值分布较连续）
            n_unique >= 10                  # 有足够多的唯一值
        )
        
        if is_ordinal_numeric:
            reason = f"ordinal_numeric(min={min_val}, max={max_val}, sparsity={sparsity:.2f})"
            if col_name:
                logger.info(
                    f"列 '{col_name}' 识别为有序数值特征，不进行One-Hot编码 "
                    f"(唯一值={n_unique}, 范围={min_val}-{max_val}, 稀疏度={sparsity:.2f})。"
                    f"如需强制编码，请使用 force_categorical 参数指定。"
                )
            return False, reason
        
        # ========== 列名特征检测（排除计数/统计类特征） ==========
        
        # 计数/统计类特征的关键词模式（这类特征不应该 One-Hot 编码）
        # 使用包含匹配：只要列名包含这些关键词就排除
        import re
        col_lower = col_name.lower() if col_name else ''
        
        # 计数类关键词（包含即排除）
        count_keywords = [
            'cnt',           # 计数缩写（如 account_cnt, overduecnt_i）
            'count',         # 计数全称
            'num',           # 数量（注意：会匹配 number）
            'times',         # 次数
            'days',          # 天数
            'months',        # 月数
            'overdue',       # 逾期
            'delinq',        # 逾期（英文缩写）
            'past_due',      # 逾期
            'balance',       # 余额
            'amount',        # 金额
            'amt',           # 金额缩写
            'sum',           # 求和
            'total',         # 总计
            'avg',           # 平均
            'ratio',         # 比率
            'rate',          # 比率
            'pct',           # 百分比
            'percent',       # 百分比
        ]
        
        is_count_feature = any(kw in col_lower for kw in count_keywords)
        
        # ========== 识别条件 ==========
        
        # Condition 1: Small range encoding (e.g., 1-5, 1-10)
        # Covers: education level (1-5), rating (1-10)
        # 注意：排除从0开始的小范围（可能是计数特征），除非是明确的二值变量
        is_small_range = (
            n_unique <= 15 and
            min_val >= 1 and              # 从1开始（不是0），排除计数特征
            max_val < 20
        )
        
        # Condition 1b: Small range starting from 0, but NOT a count feature
        # 从0开始的小范围，但列名不含计数关键词
        is_small_range_from_zero = (
            n_unique <= 10 and            # 更严格的唯一值限制
            min_val == 0 and
            max_val < 15 and              # 更严格的最大值限制
            not is_count_feature          # 列名不含计数关键词
        )
        
        # Condition 2: Sparse encoding (e.g., 10,20,30,40,90,99)
        # Covers: marital status, occupation codes with gaps
        is_sparse_encoding = (
            n_unique <= 15 and
            sparsity < 0.3 and 
            max_val < 1000 and
            not is_count_feature          # 排除计数特征
        )
        
        # Condition 3: Binary variables (0/1 or 1/2)
        # Special case for common binary encodings
        is_binary = (
            n_unique == 2 and 
            min_val >= 0 and 
            max_val <= 2
        )
        
        # Condition 4: Medium sparse encoding (e.g., province codes 11-65)
        # Covers: province codes, city codes, industry codes
        # 收紧条件：要求稀疏度更低，排除可能是计数特征的情况
        is_medium_sparse = (
            10 < n_unique <= 50 and      # Medium cardinality
            sparsity < 0.5 and           # 更严格：稀疏度 < 0.5（原来是0.7）
            max_val < 100 and            # Reasonable value range
            min_val >= 1 and             # 不从0开始（计数特征通常从0开始）
            not is_count_feature         # 排除计数特征
        )
        
        # Determine detection reason
        if is_binary:
            reason = "binary"
        elif is_small_range:
            reason = "small_range"
        elif is_small_range_from_zero:
            reason = "small_range_from_zero"
        elif is_sparse_encoding:
            reason = "sparse_encoding"
        elif is_medium_sparse:
            reason = "medium_sparse"
        else:
            reason = "not_categorical"
            # 添加更详细的排除原因
            if is_count_feature:
                reason = "excluded_count_feature"
        
        is_categorical = is_small_range or is_small_range_from_zero or is_sparse_encoding or is_binary or is_medium_sparse
        
        # Log when detected by condition 4 (medium sparse) only
        # This condition has higher false positive risk for numeric features
        if is_medium_sparse and not (is_small_range or is_small_range_from_zero or is_sparse_encoding or is_binary):
            if col_name:
                logger.warning(
                    f"列 '{col_name}' 通过中等稀疏条件识别为分类变量 "
                    f"(唯一值={n_unique}, 范围={min_val}-{max_val}, 稀疏度={sparsity:.2f})。"
                    f"如果该列是有序数值（如账户数、交易次数），请使用 force_numeric 参数排除。"
                )
        
        # Log when count feature is excluded
        if is_count_feature and col_name:
            logger.info(
                f"列 '{col_name}' 因列名含计数关键词被排除为分类变量 "
                f"(唯一值={n_unique}, 范围={min_val}-{max_val})"
            )
        
        return is_categorical, reason
    
    @staticmethod
    def detect(
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None,
        max_categories: int = 50,
        force_categorical: list[str] | None = None,
        force_numeric: list[str] | None = None,
        return_report: bool = False
    ) -> 'list[str] | tuple[list[str], dict[str, Any]]':
        """
        Auto-detect categorical columns in a DataFrame.
        
        Detection logic (layered "OR"):
        - Object/category dtype columns with <= max_categories unique values
        - Integer columns matching categorical patterns:
          * Small range (0-19, <=15 unique values)
          * Sparse encoding (sparsity < 0.3, e.g., 10,20,30,40,90,99)
          * Binary (2 unique values, 0-2 range)
          * Medium sparse (10-50 unique, sparsity < 0.5, max < 100, min >= 1)
        - User-specified columns (force_categorical)
        
        Exclusion logic:
        - Ordinal numeric features (start from 0/1, large range, high sparsity)
        - User-specified numeric columns (force_numeric)
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from detection
            max_categories: Maximum unique values to consider as categorical (default: 50)
            force_categorical: User-specified columns to force as categorical
            force_numeric: User-specified columns to force as numeric (not One-Hot encoded)
            return_report: If True, return (cols, report) tuple with detection details
            
        Returns:
            List of detected categorical column names, or
            Tuple of (cols, report) if return_report=True
        """
        exclude_cols = exclude_cols or []
        force_categorical = force_categorical or []
        force_numeric = force_numeric or []
        categorical_cols: list[str] = []
        
        # Detection report for transparency
        detection_report: dict[str, Any] = {
            'auto_detected': [],      # Columns auto-detected as categorical
            'force_categorical': [],  # User-specified categorical
            'force_numeric': [],      # User-specified numeric (excluded)
            'ordinal_numeric': [],    # Auto-detected as ordinal numeric (excluded)
            'skipped_high_cardinality': [],  # Skipped due to too many categories
            'details': {}             # Per-column detection details
        }
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            
            # User-specified numeric columns (highest priority - exclude from categorical)
            if col in force_numeric:
                detection_report['force_numeric'].append(col)
                detection_report['details'][col] = {
                    'is_categorical': False,
                    'reason': 'force_numeric',
                    'source': 'user_specified'
                }
                continue
            
            # User-specified categorical columns (second priority)
            if col in force_categorical:
                categorical_cols.append(col)
                detection_report['force_categorical'].append(col)
                detection_report['details'][col] = {
                    'is_categorical': True,
                    'reason': 'force_categorical',
                    'source': 'user_specified'
                }
                continue
            
            # Object/category types
            if df[col].dtype in ['object', 'category']:
                n_unique = df[col].nunique()
                if n_unique <= max_categories:
                    categorical_cols.append(col)
                    detection_report['auto_detected'].append(col)
                    detection_report['details'][col] = {
                        'is_categorical': True,
                        'reason': 'object_or_category_dtype',
                        'source': 'auto_detect',
                        'n_unique': n_unique
                    }
                else:
                    detection_report['skipped_high_cardinality'].append(col)
                    detection_report['details'][col] = {
                        'is_categorical': False,
                        'reason': 'high_cardinality',
                        'source': 'auto_detect',
                        'n_unique': n_unique
                    }
            # Integer columns: use smart detection
            elif df[col].dtype in ['int64', 'int32', 'int16', 'int8']:
                is_cat, reason = CategoricalProcessor._is_categorical_int(df[col], col_name=col)
                if is_cat:
                    categorical_cols.append(col)
                    detection_report['auto_detected'].append(col)
                else:
                    if reason.startswith('ordinal_numeric'):
                        detection_report['ordinal_numeric'].append(col)
                
                detection_report['details'][col] = {
                    'is_categorical': is_cat,
                    'reason': reason,
                    'source': 'auto_detect'
                }
        
        # Log summary
        if detection_report['ordinal_numeric']:
            logger.info(
                f"[CategoricalProcessor] 识别为有序数值特征（不进行One-Hot）: "
                f"{detection_report['ordinal_numeric']}"
            )
        if detection_report['auto_detected']:
            logger.info(
                f"[CategoricalProcessor] 自动检测为分类变量: "
                f"{detection_report['auto_detected']}"
            )
        
        if return_report:
            return categorical_cols, detection_report
        return categorical_cols
    
    def onehot_encode(
        self,
        df: pd.DataFrame,
        categorical_cols: list[str] | None = None,
        max_categories: int = 50,
        exclude_cols: list[str] | None = None,
        force_categorical: list[str] | None = None,
        force_numeric: list[str] | None = None,
        drop_original: bool = True
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        One-Hot encode categorical columns.
        
        Args:
            df: Input DataFrame
            categorical_cols: Columns to encode (auto-detects if None)
            max_categories: Maximum categories per column (skip if exceeded, default: 50)
            exclude_cols: Columns to exclude from encoding
            force_categorical: User-specified columns to force as categorical
            force_numeric: User-specified columns to force as numeric (not encoded)
            drop_original: Whether to drop original columns (default: True)
            
        Returns:
            Tuple of (encoded DataFrame, list of new column names)
        """
        df_result = df.copy()
        new_cols: list[str] = []
        exclude_cols = exclude_cols or []
        force_categorical = force_categorical or []
        force_numeric = force_numeric or []
        
        # Auto-detect if not provided
        if categorical_cols is None:
            categorical_cols = self.detect(
                df_result, exclude_cols, max_categories, 
                force_categorical, force_numeric
            )
        else:
            # Merge user-provided and force_categorical, exclude force_numeric
            categorical_cols = list(set(categorical_cols) | set(force_categorical))
            categorical_cols = [
                c for c in categorical_cols 
                if c not in exclude_cols 
                and c not in force_numeric 
                and c in df_result.columns
            ]
        
        if not categorical_cols:
            return df_result, new_cols
        
        for col in categorical_cols:
            n_unique = df_result[col].nunique()
            
            if n_unique > max_categories:
                continue
            
            # Get unique values
            unique_vals = df_result[col].dropna().unique()
            self.encoding_mapping_[col] = list(unique_vals)
            
            # Create One-Hot columns
            for val in unique_vals:
                new_col = f"{col}{self.indicator}{val}"
                df_result[new_col] = (df_result[col] == val).astype(int)
                new_cols.append(new_col)
            
            # Drop original column if requested
            if drop_original:
                df_result = df_result.drop(columns=[col])
        
        self.processed_cols_ = categorical_cols
        return df_result, new_cols
    
    def process(
        self,
        df: pd.DataFrame,
        categorical_cols: list[str] | None = None,
        max_categories: int = 20,
        exclude_cols: list[str] | None = None,
        drop_original: bool = True
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Alias for onehot_encode() for convenience.
        """
        return self.onehot_encode(
            df, categorical_cols, max_categories, exclude_cols, drop_original
        )


class ColumnCleaner:
    """
    Column cleaner for removing useless columns.
    
    Provides utilities for detecting and removing:
    - ID columns (by name pattern or explicit list)
    - Constant columns (single unique value)
    - High missing rate columns
    
    Example:
        >>> cleaner = ColumnCleaner(id_patterns=['id', 'uuid', 'key'])
        >>> df_clean, dropped = cleaner.clean(df, exclude_cols=['target'])
    """
    
    # Common ID column patterns (严格边界匹配版)
    # 注意：这些模式将使用边界匹配，只匹配：开头、结尾、或被下划线/非字母包围的位置
    DEFAULT_ID_PATTERNS = [
        # 英文 ID 模式（高置信度）
        'id', 'uuid', 'guid', 'pk', 'fk',
        # 带前缀的ID模式
        '_id', 'idx',
        # 序号/流水号模式（高置信度）
        'serial_no', 'serial_num', 'seq_no', 'seq_num',
        # 中文拼音模式（完整词）
        'bianhao', 'xulie', 'liushui', 'xuhao',
    ]
    
    # ID列名的精确匹配列表（列名完全等于这些值时才匹配）
    DEFAULT_ID_EXACT_NAMES = [
        'no', 'num', 'index', 'key', 'code', 'serial', 'seq', 'number',
    ]
    
    # 时间列名模式（严格边界匹配版）
    DEFAULT_TIME_PATTERNS = [
        # 时间戳模式（高置信度）
        'datetime', 'timestamp', 'created_at', 'updated_at', 'modified_at',
        'created_time', 'updated_time', 'create_time', 'update_time',
        # 日期模式（作为独立词或带下划线）
        '_date', 'date_', '_time', 'time_',
        # 中文拼音模式（完整词）
        'riqi', 'shijian',
    ]
    
    # 时间列名的精确匹配列表
    DEFAULT_TIME_EXACT_NAMES = [
        'date', 'time', 'dt', 'ts', 'year', 'month', 'day', 'hour', 'minute',
        'created', 'updated', 'modified', 'expired',
    ]
    
    # 样本类型列名模式
    DEFAULT_SAMPLE_TYPE_PATTERNS = [
        'sample_type', 'sampletype', 'sample', 'set_type', 'settype',
        'data_type', 'datatype', 'dataset', 'data_set',
        'train_test', 'traintest', 'split', 'fold',
        'is_train', 'is_test', 'is_oot', 'is_valid', 'is_validation',
    ]
    
    def __init__(
        self,
        id_cols: list[str] | None = None,
        id_patterns: list[str] | None = None,
        drop_cols: list[str] | None = None
    ):
        """
        Initialize ColumnCleaner.
        
        Args:
            id_cols: Explicit list of ID columns to drop
            id_patterns: Patterns to match ID column names (case-insensitive)
            drop_cols: Additional columns to drop
        """
        self.id_cols = id_cols or []
        self.id_patterns = id_patterns or []
        self.drop_cols = drop_cols or []
        self.dropped_id_cols_: list[str] = []
        self.dropped_constant_cols_: list[str] = []
        self.dropped_missing_cols_: list[str] = []
        self.dropped_additional_cols_: list[str] = []
    
    def detect_id_columns(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> list[str]:
        """
        Detect ID columns by name patterns with strict boundary matching.
        
        使用边界匹配避免误判：
        - 模式必须是独立词（被下划线、数字或字符串边界包围）
        - 例如：'id' 匹配 'user_id', 'ID', 但不匹配 'valid', 'video'
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from detection
            
        Returns:
            List of detected ID column names
        """
        import re
        
        exclude_cols = exclude_cols or []
        id_cols: list[str] = []
        
        patterns = self.id_patterns if self.id_patterns else self.DEFAULT_ID_PATTERNS
        exact_names = self.DEFAULT_ID_EXACT_NAMES
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            
            col_lower = col.lower()
            matched = False
            
            # 1. 精确匹配：列名完全等于某个精确名称
            if col_lower in exact_names:
                matched = True
            
            # 2. 边界匹配：模式作为独立词出现
            if not matched:
                for pattern in patterns:
                    pattern_lower = pattern.lower()
                    # 匹配：开头/结尾/被下划线或数字包围
                    # 例如：user_id, id_user, 123id, id123
                    regex = rf'(^|[_\d]){re.escape(pattern_lower)}([_\d]|$)'
                    if re.search(regex, col_lower):
                        matched = True
                        break
            
            if matched:
                id_cols.append(col)
        
        return id_cols
    
    def detect_time_columns(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> list[str]:
        """
        Detect time/date columns by name patterns and data type with strict matching.
        
        使用边界匹配避免误判：
        - 列名模式必须是独立词（被下划线、数字或字符串边界包围）
        - 例如：'date' 匹配 'create_date', 但不匹配 'update_count'
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from detection
            
        Returns:
            List of detected time column names
        """
        import re
        
        exclude_cols = exclude_cols or []
        time_cols: list[str] = []
        
        patterns = self.DEFAULT_TIME_PATTERNS
        exact_names = self.DEFAULT_TIME_EXACT_NAMES
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            
            col_lower = col.lower()
            
            # 1. 精确匹配：列名完全等于某个精确名称
            name_match = col_lower in exact_names
            
            # 2. 边界匹配：模式作为独立词出现
            if not name_match:
                for pattern in patterns:
                    pattern_lower = pattern.lower()
                    # 匹配：开头/结尾/被下划线或数字包围
                    regex = rf'(^|[_\d]){re.escape(pattern_lower)}([_\d]|$)'
                    if re.search(regex, col_lower):
                        name_match = True
                        break
            
            # 3. 检查数据类型（datetime类型直接判定为时间列）
            dtype_match = pd.api.types.is_datetime64_any_dtype(df[col])
            
            # 4. 检查数据内容（仅对object类型且列名不像特征名的列进行内容解析）
            # 注意：不对数值型或计数类特征进行日期解析，避免误判
            content_match = False
            if not dtype_match and not name_match and df[col].dtype == 'object':
                # 跳过列名包含常见非时间关键词的列（如 Cnt, Count, Num, Ratio, Rate, Amt, Amount 等）
                non_time_keywords = ['cnt', 'count', 'num', 'ratio', 'rate', 'amt', 'amount', 
                                     'score', 'flag', 'type', 'status', 'level', 'idx', 'index']
                if not any(kw in col_lower for kw in non_time_keywords):
                    sample = df[col].dropna().head(100)
                    if len(sample) > 0:
                        # 额外检查：样本值必须像日期字符串（包含 - / : 或长度>=6）
                        sample_str = sample.astype(str)
                        looks_like_date = sample_str.str.contains(r'[-/:]', regex=True).mean() > 0.5 or \
                                          (sample_str.str.len() >= 6).mean() > 0.8
                        if looks_like_date:
                            try:
                                parsed = pd.to_datetime(sample, errors='coerce')
                                valid_ratio = parsed.notna().sum() / len(sample)
                                content_match = valid_ratio > 0.8
                            except Exception:
                                pass
            
            if name_match or dtype_match or content_match:
                time_cols.append(col)
        
        return time_cols
    
    def detect_sample_type_columns(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> list[str]:
        """
        Detect sample type columns (train/test/oot split indicators).
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from detection
            
        Returns:
            List of detected sample type column names
        """
        exclude_cols = exclude_cols or []
        sample_type_cols: list[str] = []
        
        # 常见的样本类型值
        sample_type_values = {
            'train', 'test', 'oot', 'valid', 'validation', 'dev', 'eval',
            'training', 'testing', 'holdout', 'out_of_time',
            '训练', '测试', '验证', '样本外',
        }
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            
            col_lower = col.lower()
            
            # 1. 检查列名模式
            name_match = any(pattern in col_lower for pattern in self.DEFAULT_SAMPLE_TYPE_PATTERNS)
            
            # 2. 检查数据内容（是否包含 train/test/oot 等值）
            content_match = False
            if df[col].dtype == 'object' or df[col].nunique() <= 5:
                unique_vals = set(str(v).lower().strip() for v in df[col].dropna().unique())
                # 如果列的唯一值与样本类型值有交集
                if unique_vals & sample_type_values:
                    content_match = True
            
            if name_match or content_match:
                sample_type_cols.append(col)
        
        return sample_type_cols
    
    def detect_high_cardinality_id_columns(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None,
        uniqueness_threshold: float = 0.95
    ) -> list[str]:
        """
        Detect ID-like columns by high cardinality (nearly unique values).
        
        These are likely to be IDs, serial numbers, or other non-predictive columns.
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from detection
            uniqueness_threshold: Ratio of unique values to total rows (default 0.95)
            
        Returns:
            List of detected high-cardinality column names
        """
        exclude_cols = exclude_cols or []
        high_card_cols: list[str] = []
        
        n_rows = len(df)
        if n_rows == 0:
            return high_card_cols
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            
            # 只检查非数值列或整数列（浮点数不太可能是ID）
            if pd.api.types.is_float_dtype(df[col]):
                continue
            
            n_unique = df[col].nunique()
            uniqueness = n_unique / n_rows
            
            if uniqueness >= uniqueness_threshold:
                high_card_cols.append(col)
        
        return high_card_cols
    
    def detect_non_feature_columns(
        self,
        df: pd.DataFrame,
        target_col: str | None = None,
        exclude_cols: list[str] | None = None,
        check_id: bool = True,
        check_time: bool = True,
        check_sample_type: bool = True,
        check_high_cardinality: bool = True,
        uniqueness_threshold: float = 0.95
    ) -> dict[str, list[str]]:
        """
        Comprehensive detection of non-feature columns.
        
        Detects columns that should not be used as features in modeling:
        - ID columns (by name pattern)
        - Time columns (by name pattern and data type)
        - Sample type columns (train/test/oot indicators)
        - High cardinality columns (likely IDs)
        
        Args:
            df: Input DataFrame
            target_col: Target column to exclude from detection
            exclude_cols: Additional columns to exclude from detection
            check_id: Whether to check for ID columns
            check_time: Whether to check for time columns
            check_sample_type: Whether to check for sample type columns
            check_high_cardinality: Whether to check for high cardinality columns
            uniqueness_threshold: Threshold for high cardinality detection
            
        Returns:
            Dictionary with keys: 'id_cols', 'time_cols', 'sample_type_cols', 
            'high_cardinality_cols', 'all_non_feature_cols'
        """
        exclude_cols = list(exclude_cols or [])
        if target_col:
            exclude_cols.append(target_col)
        
        result: dict[str, list[str]] = {
            'id_cols': [],
            'time_cols': [],
            'sample_type_cols': [],
            'high_cardinality_cols': [],
            'all_non_feature_cols': []
        }
        
        all_detected: set[str] = set()
        
        if check_id:
            id_cols = self.detect_id_columns(df, exclude_cols)
            result['id_cols'] = id_cols
            all_detected.update(id_cols)
        
        if check_time:
            time_cols = self.detect_time_columns(df, exclude_cols)
            result['time_cols'] = time_cols
            all_detected.update(time_cols)
        
        if check_sample_type:
            sample_type_cols = self.detect_sample_type_columns(df, exclude_cols)
            result['sample_type_cols'] = sample_type_cols
            all_detected.update(sample_type_cols)
        
        if check_high_cardinality:
            # 排除已检测的列，避免重复
            exclude_for_cardinality = list(set(exclude_cols) | all_detected)
            high_card_cols = self.detect_high_cardinality_id_columns(
                df, exclude_for_cardinality, uniqueness_threshold
            )
            result['high_cardinality_cols'] = high_card_cols
            all_detected.update(high_card_cols)
        
        result['all_non_feature_cols'] = list(all_detected)
        
        return result
    
    def drop_id_columns(
        self,
        df: pd.DataFrame,
        id_cols: list[str] | None = None,
        auto_detect: bool = False,
        exclude_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Drop ID columns from DataFrame.
        
        Args:
            df: Input DataFrame
            id_cols: ID columns to drop (uses self.id_cols if None)
            auto_detect: Whether to auto-detect ID columns by patterns
            exclude_cols: Columns to exclude from dropping
            
        Returns:
            Tuple of (cleaned DataFrame, list of dropped columns)
        """
        exclude_cols = exclude_cols or []
        
        if id_cols is None:
            id_cols = self.id_cols.copy()
        
        if auto_detect:
            detected = self.detect_id_columns(df, exclude_cols)
            id_cols = list(set(id_cols + detected))
        
        cols_to_drop = [c for c in id_cols if c in df.columns and c not in exclude_cols]
        self.dropped_id_cols_ = cols_to_drop
        
        return df.drop(columns=cols_to_drop, errors='ignore'), cols_to_drop
    
    def drop_constant_columns(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Drop columns with constant values (only one unique value).
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from dropping
            
        Returns:
            Tuple of (cleaned DataFrame, list of dropped columns)
        """
        exclude_cols = exclude_cols or []
        constant_cols: list[str] = []
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            if df[col].nunique(dropna=True) <= 1:
                constant_cols.append(col)
        
        self.dropped_constant_cols_ = constant_cols
        return df.drop(columns=constant_cols, errors='ignore'), constant_cols
    
    def drop_high_missing_columns(
        self,
        df: pd.DataFrame,
        threshold: float = 0.9,
        exclude_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Drop columns with high missing rate.
        
        Args:
            df: Input DataFrame
            threshold: Missing rate threshold (0-1), columns above this are dropped
            exclude_cols: Columns to exclude from dropping
            
        Returns:
            Tuple of (cleaned DataFrame, list of dropped columns)
        """
        exclude_cols = exclude_cols or []
        high_missing_cols: list[str] = []
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            missing_rate = df[col].isna().mean()
            if missing_rate >= threshold:
                high_missing_cols.append(col)
        
        self.dropped_missing_cols_ = high_missing_cols
        return df.drop(columns=high_missing_cols, errors='ignore'), high_missing_cols
    
    def drop_additional_columns(
        self,
        df: pd.DataFrame,
        drop_cols: list[str] | None = None
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Drop additional specified columns.
        
        Args:
            df: Input DataFrame
            drop_cols: Columns to drop (uses self.drop_cols if None)
            
        Returns:
            Tuple of (cleaned DataFrame, list of dropped columns)
        """
        if drop_cols is None:
            drop_cols = self.drop_cols
        
        cols_to_drop = [c for c in drop_cols if c in df.columns]
        self.dropped_additional_cols_ = cols_to_drop
        
        return df.drop(columns=cols_to_drop, errors='ignore'), cols_to_drop
    
    def clean(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None,
        drop_id: bool = True,
        drop_constant: bool = True,
        drop_high_missing: bool = False,
        missing_threshold: float = 0.9,
        auto_detect_id: bool = False
    ) -> tuple[pd.DataFrame, dict[str, list[str]]]:
        """
        Run complete column cleaning.
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from all cleaning operations
            drop_id: Whether to drop ID columns
            drop_constant: Whether to drop constant columns
            drop_high_missing: Whether to drop high missing rate columns
            missing_threshold: Missing rate threshold for dropping
            auto_detect_id: Whether to auto-detect ID columns by patterns
            
        Returns:
            Tuple of (cleaned DataFrame, dict of dropped columns by category)
        """
        df_result = df.copy()
        exclude_cols = exclude_cols or []
        
        dropped_info: dict[str, list[str]] = {
            'id_cols': [],
            'constant_cols': [],
            'high_missing_cols': [],
            'additional_cols': []
        }
        
        # Drop ID columns
        if drop_id:
            df_result, dropped = self.drop_id_columns(
                df_result, auto_detect=auto_detect_id, exclude_cols=exclude_cols
            )
            dropped_info['id_cols'] = dropped
        
        # Drop constant columns
        if drop_constant:
            df_result, dropped = self.drop_constant_columns(df_result, exclude_cols)
            dropped_info['constant_cols'] = dropped
        
        # Drop high missing columns
        if drop_high_missing:
            df_result, dropped = self.drop_high_missing_columns(
                df_result, missing_threshold, exclude_cols
            )
            dropped_info['high_missing_cols'] = dropped
        
        # Drop additional columns
        if self.drop_cols:
            df_result, dropped = self.drop_additional_columns(df_result)
            dropped_info['additional_cols'] = dropped
        
        return df_result, dropped_info


class GeneralPreprocessor:
    """
    General-purpose data preprocessor combining all preprocessing utilities.
    
    Provides a unified interface for:
    - Column cleaning (ID, constant, high missing)
    - Datetime feature extraction
    - Text feature extraction
    - Categorical encoding (One-Hot)
    
    All operations are optional and configurable.
    
    Example:
        >>> preprocessor = GeneralPreprocessor(id_cols=['user_id'])
        >>> df_processed, info = preprocessor.preprocess(
        ...     df, 
        ...     exclude_cols=['target'],
        ...     do_datetime=True,
        ...     do_text=True,
        ...     do_categorical=True
        ... )
    """
    
    def __init__(
        self,
        id_cols: list[str] | None = None,
        drop_cols: list[str] | None = None,
        datetime_indicator: str = '_dt_',
        text_indicator: str = '_txt_',
        categorical_indicator: str = '_is_'
    ):
        """
        Initialize GeneralPreprocessor.
        
        Args:
            id_cols: ID columns to drop
            drop_cols: Additional columns to drop
            datetime_indicator: Indicator for datetime derived columns
            text_indicator: Indicator for text derived columns
            categorical_indicator: Indicator for categorical encoded columns
        """
        self.cleaner = ColumnCleaner(id_cols=id_cols, drop_cols=drop_cols)
        self.datetime_processor = DatetimeProcessor(indicator=datetime_indicator)
        self.text_processor = TextProcessor(indicator=text_indicator)
        self.categorical_processor = CategoricalProcessor(indicator=categorical_indicator)
    
    def preprocess(
        self,
        df: pd.DataFrame,
        exclude_cols: list[str] | None = None,
        # Cleaning options
        drop_id: bool = True,
        drop_constant: bool = True,
        drop_high_missing: bool = False,
        missing_threshold: float = 0.9,
        # Datetime options
        do_datetime: bool = True,
        datetime_cols: list[str] | None = None,
        datetime_features: list[str] | None = None,
        # Text options
        do_text: bool = True,
        text_cols: list[str] | None = None,
        text_features: list[str] | None = None,
        text_keywords: dict[str, list[str]] | None = None,
        # Categorical options
        do_categorical: bool = True,
        categorical_cols: list[str] | None = None,
        max_categories: int = 20
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Run complete preprocessing pipeline.
        
        Args:
            df: Input DataFrame
            exclude_cols: Columns to exclude from all processing
            drop_id: Whether to drop ID columns
            drop_constant: Whether to drop constant columns
            drop_high_missing: Whether to drop high missing columns
            missing_threshold: Missing rate threshold
            do_datetime: Whether to process datetime columns
            datetime_cols: Datetime columns (auto-detect if None)
            datetime_features: Datetime features to extract
            do_text: Whether to process text columns
            text_cols: Text columns (auto-detect if None)
            text_features: Text features to extract
            text_keywords: Keywords for text detection
            do_categorical: Whether to encode categorical columns
            categorical_cols: Categorical columns (auto-detect if None)
            max_categories: Maximum categories for One-Hot encoding
            
        Returns:
            Tuple of (processed DataFrame, preprocessing info dict)
        """
        df_result = df.copy()
        exclude_cols = exclude_cols or []
        
        info: dict[str, Any] = {}
        
        # Step 1: Clean columns
        df_result, dropped_info = self.cleaner.clean(
            df_result,
            exclude_cols=exclude_cols,
            drop_id=drop_id,
            drop_constant=drop_constant,
            drop_high_missing=drop_high_missing,
            missing_threshold=missing_threshold
        )
        info['dropped'] = dropped_info
        
        # Step 2: Process datetime columns
        if do_datetime:
            df_result, datetime_new_cols = self.datetime_processor.process(
                df_result,
                datetime_cols=datetime_cols,
                features=datetime_features,
                exclude_cols=exclude_cols
            )
            info['datetime_cols'] = self.datetime_processor.processed_cols_
            info['datetime_derived'] = self.datetime_processor.derived_mapping_
            info['datetime_new_cols'] = datetime_new_cols
        
        # Step 3: Process text columns
        if do_text:
            df_result, text_new_cols = self.text_processor.process(
                df_result,
                text_cols=text_cols,
                features=text_features,
                keywords=text_keywords,
                exclude_cols=exclude_cols
            )
            info['text_cols'] = self.text_processor.processed_cols_
            info['text_derived'] = self.text_processor.derived_mapping_
            info['text_new_cols'] = text_new_cols
        
        # Step 4: Encode categorical columns
        if do_categorical:
            df_result, categorical_new_cols = self.categorical_processor.process(
                df_result,
                categorical_cols=categorical_cols,
                max_categories=max_categories,
                exclude_cols=exclude_cols
            )
            info['categorical_cols'] = self.categorical_processor.processed_cols_
            info['categorical_mapping'] = self.categorical_processor.encoding_mapping_
            info['categorical_new_cols'] = categorical_new_cols
        
        return df_result, info
