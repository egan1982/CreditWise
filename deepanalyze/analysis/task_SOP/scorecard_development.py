# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUninitializedInstanceVariable=false, reportImplicitRelativeImport=false, reportMissingTypeStubs=false, reportUnusedParameter=false, reportUnannotatedClassAttribute=false, reportUnusedVariable=false, reportUnknownLambdaType=false, reportUnusedCallResult=false, reportUnnecessaryComparison=false, reportUnnecessaryIsInstance=false
"""
Scorecard Development Task SOP Module

Provides standardized workflow for credit scorecard development.
This module encapsulates the complete scorecard building pipeline:
1. Data Preprocessing - Missing value handling, outlier detection, data splitting
2. WOE Transformation - WOE binning, IV calculation, WOE encoding
3. Feature Selection - IV filtering, correlation analysis, VIF testing
4. Model Training - Logistic regression, stepwise selection, coefficient checking
5. Score Scaling - Score transformation, scorecard generation
6. Model Evaluation - KS/AUC calculation, ROC curve, PSI stability

Business Scenario: Credit risk scorecard development for financial institutions

Architecture Note:
- This module follows the "task-layer delegation" pattern established by rule_mining.py
- FeatureSelector delegates to CorrelationAnalyzer and VIFAnalyzer (底层 tools)
- WOETransformer encapsulates scorecardpy for WOE/IV operations
- All task classes focus on workflow orchestration, not algorithm implementation
"""

import pandas as pd
import numpy as np
import scorecardpy as sc
from sklearn.linear_model import LogisticRegression
from typing import Any, Callable, Literal
import warnings

# Import bottom-layer tools (following rule_mining.py pattern)
from deepanalyze.analysis.feature_correlation import CorrelationAnalyzer, VIFAnalyzer

# Import new statistical model and score transformer (upgrade plan)
from deepanalyze.analysis.statistical_model import StatisticalLogisticRegression
from deepanalyze.analysis.score_transformer import ScoreTransformer

# Import code templates for pseudocode generation
from deepanalyze.analysis.task_SOP.code_templates import format_code_template

# Import validators from unified validators module
from deepanalyze.analysis.task_SOP.validators import ScorecardValidator

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Type alias for internal progress callback: (stage, current, total)
ProgressCallback = Callable[[str, int, int], None] | None


def _format_bin_interval(bin_str: str) -> str:
    """
    Format bin interval string to improve readability.
    
    Handles floating-point precision issues in bin intervals like:
    - "[0.20999999999999999, 0.75999999999999997)" -> "[0.21, 0.76)"
    - "[-inf, 40.0)" -> "[-inf, 40)"
    
    Args:
        bin_str: Original bin string from scorecardpy
        
    Returns:
        Formatted bin string with cleaned numbers
    """
    import re
    
    if not bin_str or not isinstance(bin_str, str):
        return str(bin_str) if bin_str else ""
    
    def format_number(match: re.Match) -> str:
        """Format a single number, rounding to reasonable precision."""
        num_str = match.group(0)
        
        # Handle special cases
        if num_str in ('inf', '-inf', 'nan'):
            return num_str
        
        try:
            num = float(num_str)
            # If it's effectively an integer, show as integer
            if num == int(num) and abs(num) < 1e10:
                return str(int(num))
            # Otherwise round to 2 decimal places
            return f"{num:.2f}".rstrip('0').rstrip('.')
        except (ValueError, OverflowError):
            return num_str
    
    # Pattern to match numbers (including scientific notation and inf)
    number_pattern = r'-?(?:inf|nan|\d+\.?\d*(?:e[+-]?\d+)?)'
    
    return re.sub(number_pattern, format_number, bin_str, flags=re.IGNORECASE)


class TaskStoppedException(Exception):
    """Exception raised when task execution is stopped by user."""
    pass


class DataPreprocessor:
    """
    Data preprocessor for scorecard development.
    
    Provides basic data cleaning and preprocessing:
    - Missing value checking and handling
    - Special value replacement (e.g., -9999 -> NaN)
    - Outlier detection (optional)
    - Train/test data splitting
    
    Note: Does not include feature engineering (WOE/IV), that's WOETransformer's job
    
    Attributes:
        missing_threshold: Threshold for missing rate (default: 0.5)
        test_ratio: Test set ratio (default: 0.3)
        random_state: Random seed (default: 42)
        special_values: List of values to treat as missing (default: common missing markers)
    """
    
    # Common special values used as missing markers in financial data
    DEFAULT_SPECIAL_VALUES = [-9999, -999, -99999, -998, -9998, -99998]
    
    def __init__(
        self,
        missing_threshold: float = 0.95,  # 缺失率阈值，默认95%较宽松（行业惯例通常50%）
        test_ratio: float = 0.3,
        random_state: int = 42,
        special_values: list[float] | None = None,
        time_col: str | None = None,
        oot_ratio: float = 0.1
    ):
        """
        Initialize DataPreprocessor.
        
        Args:
            missing_threshold: Variables with missing rate above this are dropped (default: 0.95, industry convention is usually 0.5)
            test_ratio: Ratio for test set split
            random_state: Random seed for reproducibility
            special_values: List of values to treat as missing (None = use defaults)
            time_col: Time column for smart OOT split (optional)
            oot_ratio: OOT validation set ratio when using time-based split
        """
        self.missing_threshold = missing_threshold
        self.test_ratio = test_ratio
        self.random_state = random_state
        self.special_values = special_values if special_values is not None else self.DEFAULT_SPECIAL_VALUES
        self.time_col = time_col
        self.oot_ratio = oot_ratio
        self.missing_report_: pd.DataFrame | None = None
        self.removed_vars_: list[str] = []
        self.outlier_report_: dict[str, Any] = {}
        self.special_value_report_: dict[str, int] = {}  # Track replaced values per column
    
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
        
        self.missing_report_ = pd.DataFrame(missing_info).sort_values('missing_rate', ascending=False)
        return self.missing_report_
    
    def handle_missing(
        self,
        df: pd.DataFrame,
        threshold: float | None = None,
        exclude_cols: list[str] | None = None,
        strategy: str = 'drop'
    ) -> pd.DataFrame:
        """
        Handle missing values.
        
        Args:
            df: Input dataframe
            threshold: Missing rate threshold (uses self.missing_threshold if not provided)
            exclude_cols: Columns to exclude from dropping
            strategy: Handling strategy ('drop' only for now)
            
        Returns:
            DataFrame with missing values handled
        """
        if threshold is None:
            threshold = self.missing_threshold
        
        exclude_cols = exclude_cols or []
        missing_df = self.check_missing(df, exclude_cols)
        
        # Find columns to drop
        high_missing = missing_df[missing_df['missing_rate'] > threshold]
        cols_to_drop = [c for c in high_missing['variable'].tolist() if c not in exclude_cols]
        
        # Drop columns
        df_result = df.drop(columns=cols_to_drop)
        self.removed_vars_ = cols_to_drop
        
        return df_result
    
    def detect_outliers(
        self,
        df: pd.DataFrame,
        feature_cols: list[str] | None = None,
        method: str = 'iqr',
        threshold: float = 1.5,
        exclude_cols: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Detect outliers using IQR or Z-score method.
        
        Args:
            df: Input dataframe
            feature_cols: Feature columns to check (defaults to all numeric)
            method: Detection method ('iqr' or 'zscore')
            threshold: Threshold for outlier detection (1.5 for IQR, 3.0 for zscore)
            exclude_cols: Columns to exclude from checking
            
        Returns:
            Dict with outlier information per column:
            - count: Number of outliers
            - percentage: Percentage of outliers
            - lower_bound: Lower bound (IQR method)
            - upper_bound: Upper bound (IQR method)
            - Q1, Q3, IQR: Quartile statistics (IQR method)
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
            elif method == 'zscore':
                mean = float(col_data.mean())
                std = float(col_data.std())
                if std == 0:
                    continue
                z_scores = np.abs((df[col] - mean) / std)
                outlier_mask = z_scores > threshold
                outlier_count = outlier_mask.sum()
                
                outlier_info[col] = {
                    'count': int(outlier_count),
                    'percentage': round(outlier_count / len(df) * 100, 2),
                    'mean': round(mean, 4),
                    'std': round(std, 4),
                    'threshold': threshold,
                    'method': 'zscore'
                }
        
        self.outlier_report_ = outlier_info
        return outlier_info
    
    def get_outlier_summary(self, outlier_info: dict[str, Any] | None = None) -> pd.DataFrame:
        """
        Generate outlier detection summary as DataFrame.
        
        Args:
            outlier_info: Outlier info dict (uses self.outlier_report_ if not provided)
            
        Returns:
            DataFrame with columns: variable, outlier_count, outlier_pct, lower_bound, upper_bound
        """
        if outlier_info is None:
            outlier_info = getattr(self, 'outlier_report_', {})
        
        if not outlier_info:
            return pd.DataFrame(columns=['variable', 'outlier_count', 'outlier_pct', 'lower_bound', 'upper_bound'])
        
        summary_data = []
        for var, info in outlier_info.items():
            row = {
                'variable': var,
                'outlier_count': info.get('count', 0),
                'outlier_pct': info.get('percentage', 0),
                'lower_bound': info.get('lower_bound', None),
                'upper_bound': info.get('upper_bound', None)
            }
            summary_data.append(row)
        
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('outlier_pct', ascending=False)
        return summary_df
    
    def split_data(
        self,
        df: pd.DataFrame,
        target_col: str,
        test_ratio: float | None = None,
        random_state: int | None = None,
        sample_type_col: str | None = None,
        time_col: str | None = None,
        oot_ratio: float | None = None
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
        """
        Split data into train, test, and optionally OOT sets.
        
        Supports three split modes:
        1. Manual split: Use sample_type_col to specify train/test/oot labels
        2. Time-based OOT: Use time_col to automatically select recent data as OOT
        3. Random split: Simple stratified random split (train/test only)
        
        Args:
            df: Input dataframe
            target_col: Target column name
            test_ratio: Test set ratio (uses self.test_ratio if not provided)
            random_state: Random seed (uses self.random_state if not provided)
            sample_type_col: Column name containing sample type labels.
                If provided, data will be split based on this column's values:
                - 'train' -> training set
                - 'test' -> test set  
                - 'oot' or 'validation' -> OOT validation set
            time_col: Column name containing time/date values for time-based OOT split.
                If provided with oot_ratio > 0, the most recent data will be used as OOT.
                Supports datetime, date string (YYYY-MM-DD, YYYY/MM/DD HH:MM:SS), or numeric (e.g., 202301) formats.
                Uses self.time_col if not provided.
            oot_ratio: Ratio of data to use as OOT (0.0 = no OOT, 0.1 = 10% most recent data)
                Only used when time_col is provided and sample_type_col is not.
                Uses self.oot_ratio if not provided.
            
        Returns:
            Tuple of (train_df, test_df, oot_df)
            oot_df is None if no OOT data is available
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if test_ratio is None:
            test_ratio = self.test_ratio
        if random_state is None:
            random_state = self.random_state
        if time_col is None:
            time_col = self.time_col
        if oot_ratio is None:
            oot_ratio = self.oot_ratio
        
        # Mode 1: Manual split based on sample_type column
        if sample_type_col and sample_type_col in df.columns:
            logger.info(f"Using manual split based on column: {sample_type_col}")
            # Split based on sample_type column
            sample_types = df[sample_type_col].str.lower().str.strip()
            
            train_df = df[sample_types == 'train'].drop(columns=[sample_type_col])
            test_df = df[sample_types == 'test'].drop(columns=[sample_type_col])
            
            # Check for OOT data (accept 'oot', 'validation', 'val')
            oot_mask = sample_types.isin(['oot', 'validation', 'val'])
            oot_df = df[oot_mask].drop(columns=[sample_type_col]) if oot_mask.any() else None
            
            # Validate that we have training data
            if len(train_df) == 0:
                raise ValueError(f"No training data found. Column '{sample_type_col}' must contain 'train' values.")
            
            # If no test data, use random split from train
            if len(test_df) == 0:
                train_ratio = 1.0 - test_ratio
                data_split = sc.split_df(train_df, y=target_col, ratio=train_ratio, seed=random_state)
                train_df = data_split['train']
                test_df = data_split['test']
            
            if oot_df is not None:
                logger.info(f"Manual split: train={len(train_df)}, test={len(test_df)}, oot={len(oot_df)}")
            else:
                logger.info(f"Manual split: train={len(train_df)}, test={len(test_df)}, oot=None")
            
            return train_df, test_df, oot_df
        
        # Mode 2: Time-based OOT split
        if time_col and time_col in df.columns and oot_ratio > 0:
            logger.info(f"Using time-based OOT split: time_col={time_col}, oot_ratio={oot_ratio}")
            
            # Parse time column
            time_series = self._parse_time_column(df[time_col])
            
            if time_series is not None:
                # Sort by time and determine OOT cutoff
                df_sorted = df.copy()
                df_sorted['_time_parsed'] = time_series
                df_sorted = df_sorted.sort_values('_time_parsed')
                
                # Calculate OOT cutoff index
                n_total = len(df_sorted)
                n_oot = int(n_total * oot_ratio)
                
                if n_oot > 0:
                    # Split: earlier data for train/test, latest data for OOT
                    oot_cutoff_idx = n_total - n_oot
                    df_train_test = df_sorted.iloc[:oot_cutoff_idx].drop(columns=['_time_parsed'])
                    oot_df = df_sorted.iloc[oot_cutoff_idx:].drop(columns=['_time_parsed'])
                    
                    # Get time range info for logging
                    oot_time_min = df_sorted['_time_parsed'].iloc[oot_cutoff_idx]
                    oot_time_max = df_sorted['_time_parsed'].iloc[-1]
                    logger.info(f"OOT time range: {oot_time_min} to {oot_time_max}")
                    
                    # Remove time_col from feature set if needed (keep original data)
                    # Note: time_col will be excluded from features in feature selection stage
                    
                    # Split train/test from non-OOT data (use sklearn to avoid scorecardpy pandas compat issue)
                    from sklearn.model_selection import train_test_split
                    train_df, test_df = train_test_split(
                        df_train_test, test_size=test_ratio, random_state=random_state,
                        stratify=df_train_test[target_col]
                    )
                    
                    logger.info(f"Time-based split: train={len(train_df)}, test={len(test_df)}, oot={len(oot_df)}")
                    return train_df, test_df, oot_df
                else:
                    logger.warning(f"OOT ratio {oot_ratio} results in 0 OOT samples, falling back to random split")
            else:
                logger.warning(f"Could not parse time column '{time_col}', falling back to random split")
        
        # Mode 3: Random stratified split (no OOT)
        # Use sklearn to avoid scorecardpy's rep_blank_na() pandas compat issue
        logger.info(f"Using random stratified split: test_ratio={test_ratio}")
        from sklearn.model_selection import train_test_split
        train_df, test_df = train_test_split(
            df, test_size=test_ratio, random_state=random_state,
            stratify=df[target_col]
        )
        
        logger.info(f"Random split: train={len(train_df)}, test={len(test_df)}, oot=None")
        return train_df, test_df, None
    
    def _parse_time_column(self, col: pd.Series) -> pd.Series | None:
        """
        Parse time column to datetime for sorting.
        
        Supports multiple formats:
        - datetime/Timestamp
        - date strings (YYYY-MM-DD, YYYY/MM/DD, YYYY-MM-DD HH:MM:SS, YYYY/MM/DD HH:MM:SS, etc.)
        - numeric formats (YYYYMM, YYYYMMDD)
        
        Args:
            col: Time column series
            
        Returns:
            Parsed datetime series, or None if parsing fails
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Already datetime
        if pd.api.types.is_datetime64_any_dtype(col):
            logger.info("Time column is already datetime type")
            return col
        
        # Try to parse as datetime string with common formats
        if pd.api.types.is_string_dtype(col) or pd.api.types.is_object_dtype(col):
            # Common datetime formats to try explicitly
            datetime_formats = [
                '%Y-%m-%d %H:%M:%S',      # 2024-10-20 17:48:11
                '%Y/%m/%d %H:%M:%S',      # 2024/10/20 17:48:11
                '%Y-%m-%d',               # 2024-10-20
                '%Y/%m/%d',               # 2024/10/20
                '%Y-%m-%d %H:%M',         # 2024-10-20 17:48
                '%Y/%m/%d %H:%M',         # 2024/10/20 17:48
                '%d-%m-%Y %H:%M:%S',      # 20-10-2024 17:48:11
                '%d/%m/%Y %H:%M:%S',      # 20/10/2024 17:48:11
                '%d-%m-%Y',               # 20-10-2024
                '%d/%m/%Y',               # 20/10/2024
            ]
            
            for fmt in datetime_formats:
                try:
                    parsed = pd.to_datetime(col, format=fmt, errors='coerce')
                    valid_ratio = parsed.notna().mean()
                    if valid_ratio > 0.9:  # At least 90% valid
                        logger.info(f"Parsed time column with format '{fmt}' (valid ratio: {valid_ratio:.2%})")
                        return parsed
                except Exception:
                    continue
        
        # Fallback: let pandas infer the format
        try:
            parsed = pd.to_datetime(col, errors='coerce')
            valid_ratio = parsed.notna().mean()
            if valid_ratio > 0.9:  # At least 90% valid
                logger.info(f"Parsed time column with pandas auto-inference (valid ratio: {valid_ratio:.2%})")
                return parsed
        except Exception:
            pass
        
        # Try numeric formats (YYYYMM or YYYYMMDD)
        if pd.api.types.is_numeric_dtype(col):
            col_int = col.dropna().astype(int)
            sample_val = col_int.iloc[0] if len(col_int) > 0 else 0
            
            # YYYYMMDD format (e.g., 20230115)
            if 19000101 <= sample_val <= 21001231:
                try:
                    parsed = pd.to_datetime(col.astype(int).astype(str), format='%Y%m%d', errors='coerce')
                    valid_ratio = parsed.notna().mean()
                    if valid_ratio > 0.9:
                        logger.info(f"Parsed time column as YYYYMMDD format (valid ratio: {valid_ratio:.2%})")
                        return parsed
                except Exception:
                    pass
            
            # YYYYMM format (e.g., 202301)
            if 190001 <= sample_val <= 210012:
                try:
                    # Convert YYYYMM to YYYYMMDD by appending '01'
                    parsed = pd.to_datetime(col.astype(int).astype(str) + '01', format='%Y%m%d', errors='coerce')
                    valid_ratio = parsed.notna().mean()
                    if valid_ratio > 0.9:
                        logger.info(f"Parsed time column as YYYYMM format (valid ratio: {valid_ratio:.2%})")
                        return parsed
                except Exception:
                    pass
            
            # Plain numeric (treat as sortable value)
            logger.info("Using numeric column directly for time-based sorting")
            return col
        
        logger.warning(f"Could not parse time column, dtype={col.dtype}")
        return None
    
    def detect_time_columns(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Detect potential time columns in the dataframe.
        
        Returns a list of candidate time columns with their detected format.
        
        Args:
            df: Input dataframe
            
        Returns:
            List of dicts with 'column', 'format', 'sample_values' keys
        """
        import logging
        logger = logging.getLogger(__name__)
        
        candidates = []
        
        # Common time column name patterns
        time_patterns = [
            'date', 'time', 'dt', 'month', 'year', 'period', 'day',
            '日期', '时间', '月份', '年份', '期数', 'apply_date', 'loan_date',
            'create_time', 'update_time', 'obs_date', 'observation_date'
        ]
        
        for col in df.columns:
            col_lower = col.lower()
            
            # Check column name patterns
            name_match = any(pattern in col_lower for pattern in time_patterns)
            
            # Check if parseable as time
            parsed = self._parse_time_column(df[col])
            is_parseable = parsed is not None
            
            if name_match or is_parseable:
                # Determine format
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    fmt = 'datetime'
                elif pd.api.types.is_numeric_dtype(df[col]):
                    sample = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else 0
                    if isinstance(sample, (int, float)):
                        sample_int = int(sample)
                        if 19000101 <= sample_int <= 21001231:
                            fmt = 'YYYYMMDD'
                        elif 190001 <= sample_int <= 210012:
                            fmt = 'YYYYMM'
                        else:
                            fmt = 'numeric'
                    else:
                        fmt = 'numeric'
                else:
                    fmt = 'string'
                
                # Get sample values
                samples = df[col].dropna().head(3).tolist()
                
                candidates.append({
                    'column': col,
                    'format': fmt,
                    'sample_values': samples,
                    'name_match': name_match,
                    'parseable': is_parseable
                })
                
                logger.info(f"Detected time column candidate: {col} (format={fmt})")
        
        # Sort by relevance (name match + parseable first)
        candidates.sort(key=lambda x: (x['name_match'] and x['parseable'], x['parseable']), reverse=True)
        
        return candidates
    
    def preprocess(
        self,
        df: pd.DataFrame,
        target_col: str,
        exclude_cols: list[str] | None = None,
        do_split: bool = True,
        progress_callback: ProgressCallback = None
    ) -> tuple[pd.DataFrame, pd.DataFrame | None, dict[str, Any]]:
        """
        Complete preprocessing pipeline.
        
        Args:
            df: Input dataframe
            target_col: Target column name
            exclude_cols: Columns to exclude from preprocessing
            do_split: Whether to split data
            progress_callback: Progress callback function
            
        Returns:
            Tuple of (train_df, test_df, preprocessing_info)
        """
        exclude_cols = exclude_cols or []
        exclude_cols.append(target_col)
        
        total_steps = 3 if do_split else 2
        current_step = 0
        
        # Step 1: Replace special values with NaN
        current_step += 1
        if progress_callback:
            progress_callback("替换特殊缺失值", current_step, total_steps)
        
        df_replaced = self.replace_special_values(df, exclude_cols=exclude_cols)
        
        # Step 2: Handle missing values
        current_step += 1
        if progress_callback:
            progress_callback("处理缺失值", current_step, total_steps)
        
        df_clean = self.handle_missing(df_replaced, exclude_cols=exclude_cols)
        
        # Step 3: Split data (optional)
        train_df = df_clean
        test_df = None
        if do_split:
            current_step += 1
            if progress_callback:
                progress_callback("分割数据", current_step, total_steps)
            
            train_df, test_df = self.split_data(df_clean, target_col)
        
        # Prepare info
        info = {
            'original_shape': df.shape,
            'cleaned_shape': df_clean.shape,
            'removed_vars': self.removed_vars_,
            'missing_report': self.missing_report_,
            'special_value_report': self.special_value_report_,
            'special_values_used': self.special_values,
            'train_shape': train_df.shape,
            'test_shape': test_df.shape if test_df is not None else None
        }
        
        return train_df, test_df, info


class WOETransformer:
    """
    WOE transformer (encapsulates scorecardpy).
    
    Provides WOE binning and transformation workflow orchestration:
    - Variable filtering (missing rate/IV/constant value)
    - WOE automatic binning
    - Binning adjustment (optional)
    - WOE transformation
    - IV value extraction
    
    Note: Delegates to scorecardpy, only responsible for workflow orchestration
    
    Attributes:
        iv_limit: IV threshold for variable filtering (default: 0.02)
        missing_limit: Missing rate limit (default: 0.95)
        identical_limit: Constant value ratio limit (default: 0.95)
        bin_num_limit: Maximum number of bins (default: 8)
        method: Binning method ('tree'/'chimerge'/'quantile', default: 'tree')
        use_scorecardpy: Whether to use scorecardpy for binning (high precision mode)
        enforce_monotonicity: Whether to enforce WOE monotonicity
    """
    
    def __init__(
        self,
        iv_limit: float = 0.02,
        missing_limit: float = 0.95,
        identical_limit: float = 0.95,
        bin_num_limit: int = 8,
        method: str = 'tree',
        use_scorecardpy: bool = False,
        enforce_monotonicity: bool = True
    ):
        """
        Initialize WOETransformer.
        
        Args:
            iv_limit: IV threshold for variable filtering
            missing_limit: Missing rate threshold
            identical_limit: Constant value ratio threshold
            bin_num_limit: Maximum number of bins
            method: Binning method
            use_scorecardpy: If True, use scorecardpy.woebin for tree/chimerge binning
                           (slower but produces more monotonic WOE and higher IV)
            enforce_monotonicity: If True, enforce WOE monotonicity by merging bins
        """
        self.iv_limit = iv_limit
        self.missing_limit = missing_limit
        self.identical_limit = identical_limit
        self.bin_num_limit = bin_num_limit
        self.method = method
        self.use_scorecardpy = use_scorecardpy
        self.enforce_monotonicity = enforce_monotonicity
        self.bins_: dict[str, Any] | None = None
        self.iv_table_: pd.DataFrame | None = None
        self.filtered_vars_: list[str] = []
        self.monotonicity_report_: dict[str, Any] = {}
    
    def filter_variables(
        self,
        df: pd.DataFrame,
        target_col: str,
        feature_cols: list[str] | None = None
    ) -> list[str]:
        """
        Filter variables by missing rate, IV, and constant value.
        
        Uses scorecardpy.var_filter() for initial screening.
        
        Args:
            df: Input dataframe
            target_col: Target column name
            feature_cols: Feature columns to filter (defaults to all except target)
            
        Returns:
            List of filtered variable names
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if feature_cols is None:
            feature_cols = [c for c in df.columns if c != target_col]
        
        logger.info(f"Filtering {len(feature_cols)} features...")
        
        # Use scorecardpy's var_filter
        df_subset = df[[target_col] + feature_cols].copy()
        filtered_df = sc.var_filter(
            df_subset,
            y=target_col,
            iv_limit=self.iv_limit,
            missing_limit=self.missing_limit,
            identical_limit=self.identical_limit
        )
        
        self.filtered_vars_ = [c for c in filtered_df.columns if c != target_col]
        logger.info(f"After filtering: {len(self.filtered_vars_)} features remain")
        return self.filtered_vars_
    
    def auto_binning(
        self,
        df: pd.DataFrame,
        target_col: str,
        features: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Automatic WOE binning.
        
        Supports two modes:
        - Fast mode (default): Uses built-in WOECalculator with quantile binning
        - High precision mode (use_scorecardpy=True): Uses scorecardpy.woebin 
          with tree/chimerge for more monotonic WOE and higher IV
        
        Args:
            df: Input dataframe
            target_col: Target column name
            features: Features to bin (defaults to all filtered variables)
            
        Returns:
            Binning dictionary compatible with scorecardpy format
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if features is None:
            features = self.filtered_vars_
        
        logger.info(f"Starting WOE binning for {len(features)} features...")
        logger.info(f"Mode: {'High Precision (scorecardpy)' if self.use_scorecardpy else 'Fast (WOECalculator)'}")
        logger.info(f"Method: {self.method}, Enforce monotonicity: {self.enforce_monotonicity}")
        
        # 记录输入特征数（用于前端展示计算过程）
        self._input_feature_count = len(features)
        
        # Check for problematic features (all NaN, constant, etc.)
        valid_features = []
        pre_filtered_features = []  # 记录预先过滤的特征
        for feat in features:
            col = df[feat]
            if col.isna().all():
                logger.warning(f"Skipping {feat}: all NaN")
                pre_filtered_features.append({"feature": feat, "reason": "全部为NaN"})
                continue
            if col.nunique() <= 1:
                logger.warning(f"Skipping {feat}: constant value")
                pre_filtered_features.append({"feature": feat, "reason": "常量值"})
                continue
            # Skip non-numeric features
            if not pd.api.types.is_numeric_dtype(col):
                logger.warning(f"Skipping {feat}: non-numeric")
                pre_filtered_features.append({"feature": feat, "reason": "非数值类型"})
                continue
            valid_features.append(feat)
        
        # 记录预先过滤的特征
        self._pre_filtered_features = pre_filtered_features
        
        logger.info(f"Valid features: {len(valid_features)} (pre-filtered: {len(pre_filtered_features)})")
        
        if self.use_scorecardpy:
            # High precision mode: use scorecardpy.woebin
            bins = self._binning_scorecardpy(df, target_col, valid_features, logger)
        else:
            # Fast mode: use built-in WOECalculator
            bins = self._binning_fast(df, target_col, valid_features, logger)
        
        # Apply monotonicity enforcement if enabled
        if self.enforce_monotonicity:
            bins = self._enforce_monotonicity(bins, logger)
        
        logger.info(f"WOE binning completed, got {len(bins)} bins")
        
        self.bins_ = bins
        return bins
    
    def _binning_scorecardpy(
        self,
        df: pd.DataFrame,
        target_col: str,
        features: list[str],
        logger: Any
    ) -> dict[str, Any]:
        """
        High precision binning using scorecardpy.woebin.
        
        Supports tree/chimerge methods for optimal monotonic binning.
        """
        logger.info(f"Using scorecardpy.woebin with method='{self.method}'")
        
        try:
            # Prepare data subset
            df_subset = df[[target_col] + features].copy()
            input_feature_count = len(features)
            
            # Call scorecardpy.woebin
            # 注意：scorecardpy默认会过滤常量列(ignore_const_cols=True)和日期列(ignore_datetime_cols=True)
            # 这可能导致输入特征数和输出bins数不一致
            bins = sc.woebin(
                df_subset,
                y=target_col,
                method=self.method,
                bin_num_limit=self.bin_num_limit,
                # scorecardpy的默认行为是忽略常量列，这里保持默认以确保分箱质量
                # 但我们需要记录哪些特征被过滤掉了
            )
            
            output_feature_count = len(bins)
            logger.info(f"scorecardpy.woebin: {input_feature_count} features in → {output_feature_count} bins out")
            
            # 记录被scorecardpy过滤掉的特征（用于调试和用户理解）
            if output_feature_count < input_feature_count:
                binned_features = set(bins.keys())
                filtered_by_scorecardpy = [f for f in features if f not in binned_features]
                logger.warning(f"scorecardpy filtered {len(filtered_by_scorecardpy)} features: {filtered_by_scorecardpy[:10]}{'...' if len(filtered_by_scorecardpy) > 10 else ''}")
                logger.warning("Possible reasons: constant columns in train set, datetime columns, or binning failures")
                
                # 保存过滤信息供后续使用（通过实例属性）
                self._scorecardpy_filtered_features = filtered_by_scorecardpy
            else:
                self._scorecardpy_filtered_features = []
            
            return bins
            
        except Exception as e:
            logger.error(f"scorecardpy.woebin failed: {e}")
            logger.info("Falling back to fast mode...")
            return self._binning_fast(df, target_col, features, logger)
    
    def _binning_fast(
        self,
        df: pd.DataFrame,
        target_col: str,
        features: list[str],
        logger: Any
    ) -> dict[str, Any]:
        """
        Fast binning using built-in WOECalculator.
        
        Uses quantile binning for speed (especially on Windows).
        """
        from deepanalyze.analysis.woe import WOECalculator
        
        bins = {}
        # In fast mode, always use quantile regardless of method setting
        woe_method = 'quantile'
        
        for i, feat in enumerate(features):
            if (i + 1) % 10 == 0:
                logger.info(f"Processing feature {i+1}/{len(features)}: {feat}")
            
            try:
                result = WOECalculator.calculate_woe(
                    df, feat, target_col, 
                    n_bins=self.bin_num_limit, 
                    method=woe_method
                )
                
                if result.get('status') == 'success':
                    # Convert to scorecardpy-compatible format
                    bin_df = pd.DataFrame(result['bins'])
                    bin_df['variable'] = feat
                    bin_df['total_iv'] = result['iv']
                    bins[feat] = bin_df
            except Exception as e:
                logger.warning(f"Failed to bin {feat}: {e}")
                continue
        
        return bins
    
    def _check_monotonicity(self, woe_values: list[float]) -> dict[str, Any]:
        """
        Check if WOE values are monotonic.
        
        Returns:
            Dict with 'is_monotonic', 'direction', 'violations' info
        """
        if len(woe_values) < 2:
            return {'is_monotonic': True, 'direction': 'N/A', 'violations': []}
        
        increasing = all(x <= y for x, y in zip(woe_values, woe_values[1:]))
        decreasing = all(x >= y for x, y in zip(woe_values, woe_values[1:]))
        
        violations = []
        if not increasing and not decreasing:
            for i in range(len(woe_values) - 1):
                # Check for direction changes
                if i > 0:
                    prev_diff = woe_values[i] - woe_values[i-1]
                    curr_diff = woe_values[i+1] - woe_values[i]
                    if prev_diff * curr_diff < 0:  # Direction changed
                        violations.append(i)
        
        return {
            'is_monotonic': increasing or decreasing,
            'direction': 'increasing' if increasing else ('decreasing' if decreasing else 'non-monotonic'),
            'violations': violations
        }
    
    def _enforce_monotonicity(
        self,
        bins: dict[str, Any],
        logger: Any
    ) -> dict[str, Any]:
        """
        Enforce WOE monotonicity by merging adjacent bins that violate monotonicity.
        
        Strategy:
        1. Determine dominant direction (increasing or decreasing)
        2. Merge adjacent bins that violate the direction
        3. Recalculate WOE after merging
        """
        logger.info("Checking and enforcing WOE monotonicity...")
        
        enforced_bins = {}
        self.monotonicity_report_ = {}
        
        for var_name, bin_df in bins.items():
            if 'woe' not in bin_df.columns:
                enforced_bins[var_name] = bin_df
                continue
            
            woe_values = bin_df['woe'].tolist()
            check_result = self._check_monotonicity(woe_values)
            
            self.monotonicity_report_[var_name] = {
                'original_bins': len(woe_values),
                'original_monotonic': check_result['is_monotonic'],
                'original_direction': check_result['direction'],
                'adjusted': False
            }
            
            if check_result['is_monotonic']:
                # Already monotonic, keep as is
                enforced_bins[var_name] = bin_df
            else:
                # Need to enforce monotonicity
                logger.info(f"Variable '{var_name}' is non-monotonic, enforcing...")
                
                # Simple strategy: keep the bin_df but log the issue
                # Full merging would require recalculating WOE which needs original data
                # For now, we just flag it in the report
                enforced_bins[var_name] = bin_df
                self.monotonicity_report_[var_name]['adjusted'] = False
                self.monotonicity_report_[var_name]['note'] = 'Non-monotonic, consider manual adjustment'
                
                logger.warning(f"Variable '{var_name}' has non-monotonic WOE: {woe_values}")
        
        # Summary
        total = len(self.monotonicity_report_)
        monotonic = sum(1 for v in self.monotonicity_report_.values() if v['original_monotonic'])
        logger.info(f"Monotonicity check: {monotonic}/{total} variables are monotonic")
        
        return enforced_bins
    
    def manual_binning(
        self,
        df: pd.DataFrame,
        target_col: str,
        breaks_list: dict[str, list[float]]
    ) -> dict[str, Any]:
        """
        Manual WOE binning with specified breakpoints.
        
        Args:
            df: Input dataframe
            target_col: Target column name
            breaks_list: Dict of feature name -> list of breakpoints
            
        Returns:
            Binning dictionary
        """
        bins = sc.woebin(
            df,
            y=target_col,
            breaks_list=breaks_list
        )
        
        self.bins_ = bins
        return bins
    
    def adjust_binning(
        self,
        bins: dict[str, Any],
        adjustments: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Adjust binning rules.
        
        Args:
            bins: Original binning dictionary
            adjustments: Adjustment specifications
            
        Returns:
            Adjusted binning dictionary
        """
        # Use scorecardpy's woebin_adj
        adjusted_bins = sc.woebin_adj(bins, **adjustments)
        self.bins_ = adjusted_bins
        return adjusted_bins
    
    def transform(
        self,
        df: pd.DataFrame,
        bins: dict[str, Any] | None = None
    ) -> pd.DataFrame:
        """
        Apply WOE transformation to dataframe using vectorized operations.
        
        Args:
            df: Input dataframe
            bins: Binning dictionary (uses self.bins_ if not provided)
            
        Returns:
            WOE-transformed dataframe with _woe suffix columns
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if bins is None:
            bins = self.bins_
        
        if bins is None:
            raise ValueError("Bins not available. Run auto_binning() or manual_binning() first.")
        
        # Try to use scorecardpy's woebin_ply for maximum efficiency
        if self.use_scorecardpy:
            try:
                df_woe = sc.woebin_ply(df, bins)
                logger.info(f"WOE transformation completed using scorecardpy.woebin_ply")
                return df_woe
            except Exception as e:
                logger.warning(f"scorecardpy.woebin_ply failed: {e}, falling back to vectorized method")
        
        # Vectorized fallback implementation
        df_woe = df.copy()
        
        for var_name, bin_df in bins.items():
            if var_name not in df.columns:
                logger.warning(f"Variable {var_name} not in dataframe, skipping")
                continue
            
            woe_col_name = f"{var_name}_woe"
            
            if 'woe' not in bin_df.columns or 'bin' not in bin_df.columns:
                df_woe[woe_col_name] = 0.0
                logger.warning(f"No WOE mapping for {var_name}, using 0")
                continue
            
            # Parse bin edges and WOE values once
            bin_edges = []
            woe_values_list = []
            
            for _, row in bin_df.iterrows():
                bin_str = str(row['bin'])
                try:
                    if ',' in bin_str:
                        parts = bin_str.strip('()[]').split(',')
                        low_str = parts[0].strip()
                        high_str = parts[1].strip()
                        
                        low = float(low_str) if low_str not in ['', '-inf', 'inf'] else float('-inf')
                        high = float(high_str) if high_str not in ['', 'inf', '-inf'] else float('inf')
                        
                        bin_edges.append((low, high))
                        woe_values_list.append(float(row['woe']))
                except (ValueError, IndexError):
                    continue
            
            if not bin_edges:
                df_woe[woe_col_name] = 0.0
                continue
            
            # Vectorized WOE assignment using pd.cut
            # Build bin edges array for pd.cut
            edges = sorted(set([e[0] for e in bin_edges] + [e[1] for e in bin_edges]))
            
            # Create WOE mapping: bin_label -> woe_value
            woe_map = {}
            for (low, high), woe in zip(bin_edges, woe_values_list):
                # Find the bin index for this edge pair
                for i in range(len(edges) - 1):
                    if edges[i] == low and edges[i+1] == high:
                        woe_map[i] = woe
                        break
            
            # Use pd.cut with right=False for [a, b) intervals
            col_values = df[var_name].values
            woe_result = np.zeros(len(col_values), dtype=float)
            
            # Vectorized bin assignment
            for i, (low, high) in enumerate(bin_edges):
                if i < len(woe_values_list):
                    mask = (col_values >= low) & (col_values < high)
                    # Handle inf edge case
                    if high == float('inf'):
                        mask = col_values >= low
                    woe_result[mask] = woe_values_list[i]
            
            # Handle NaN values
            nan_mask = pd.isna(df[var_name])
            woe_result[nan_mask] = 0.0
            
            df_woe[woe_col_name] = woe_result
        
        return df_woe
    
    def get_iv_table(
        self,
        bins: dict[str, Any] | None = None
    ) -> pd.DataFrame:
        """
        Extract IV values from binning dictionary.
        
        Args:
            bins: Binning dictionary (uses self.bins_ if not provided)
            
        Returns:
            DataFrame with columns: variable, iv
        """
        if bins is None:
            bins = self.bins_
        
        if bins is None:
            raise ValueError("Bins not available. Run auto_binning() or manual_binning() first.")
        
        iv_data: list[dict[str, str | float]] = []
        for var_name, bin_df in bins.items():
            iv_value = bin_df['total_iv'].iloc[0]
            iv_data.append({
                'variable': var_name,
                'iv': round(iv_value, 4)
            })
        
        # 处理空数据情况
        if not iv_data:
            import logging
            logging.getLogger(__name__).warning("No IV data available - bins dictionary is empty")
            self.iv_table_ = pd.DataFrame(columns=['variable', 'iv'])
            return self.iv_table_
        
        self.iv_table_ = pd.DataFrame(iv_data).sort_values('iv', ascending=False)
        return self.iv_table_
    
    def fit_transform(
        self,
        df: pd.DataFrame,
        target_col: str,
        features: list[str] | None = None,
        progress_callback: ProgressCallback = None
    ) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
        """
        Complete WOE transformation pipeline.
        
        Optimized: Skip var_filter() to avoid duplicate woebin() calls.
        var_filter() internally calls woebin() to compute IV, causing redundant computation.
        Instead, we directly call woebin() and filter by IV afterwards.
        
        Args:
            df: Input dataframe
            target_col: Target column name
            features: Feature columns (optional)
            progress_callback: Progress callback function
            
        Returns:
            Tuple of (woe_transformed_df, bins_dict, iv_table)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 使用更细粒度的进度：总共5个检查点
        # 0% - 开始准备特征
        # 20% - 特征准备完成，开始分箱
        # 60% - 分箱完成，开始转换
        # 80% - 转换完成，开始IV过滤
        # 100% - 全部完成
        
        # Step 1: Prepare features
        # 注意：数据质量筛选（缺失率、同值率）已在数据加载阶段的var_filter中完成
        # 这里直接使用传入的features列表，不再进行重复筛选
        if progress_callback:
            progress_callback("准备特征", 0, 100)
        
        if features is None:
            # Get all numeric/categorical features except target
            # 仅当没有传入features时才自动获取（通常不会走到这里）
            features = [c for c in df.columns if c != target_col]
            logger.info(f"Auto-detected {len(features)} features (no pre-filtering in fit_transform)")
        else:
            logger.info(f"Using {len(features)} pre-filtered features from data_loading stage")
        
        self.filtered_vars_ = features
        
        if progress_callback:
            progress_callback("特征准备完成", 20, 100)
        
        # Step 2: Auto binning (single woebin call for all features)
        # 这是最耗时的步骤
        logger.info(f"Starting WOE binning for {len(features)} features...")
        bins = self.auto_binning(df, target_col, features)
        
        # 分箱完成后更新进度
        if progress_callback:
            progress_callback("分箱完成", 60, 100)
        
        # Step 3: Transform
        df_woe = self.transform(df, bins)
        
        if progress_callback:
            progress_callback("转换完成", 80, 100)
        
        # Step 4: Get IV table and add low_iv marker (方案1优化：标记而非删除)
        # WOE阶段职责是"转换"，不做IV筛选删除，IV筛选统一在特征筛选阶段执行
        iv_table = self.get_iv_table(bins)
        
        # 标记低IV变量（不删除），便于后续分析和追溯
        if self.iv_limit > 0:
            iv_table['low_iv'] = iv_table['iv'] < self.iv_limit
            low_iv_count = iv_table['low_iv'].sum()
            high_iv_count = len(iv_table) - low_iv_count
            logger.info(f"IV distribution: {high_iv_count} features >= {self.iv_limit}, {low_iv_count} features < {self.iv_limit} (marked, not removed)")
        else:
            iv_table['low_iv'] = False
        
        # 不再删除低IV变量，保留完整的bins和df_woe供后续分析
        # IV筛选将在特征筛选阶段统一执行
        
        if progress_callback:
            progress_callback("WOE处理完成", 99, 100)  # 使用99%，让run方法发送最终的100%
        
        return df_woe, bins, iv_table


class FeatureSelector:
    """
    Feature selector for scorecard development.
    
    Provides feature selection workflow orchestration, ✅ KEY: delegates to底层 tools
    1. IV value filtering
    2. Correlation filtering (delegates to CorrelationAnalyzer)
    3. VIF testing (delegates to VIFAnalyzer)
    4. Stepwise regression (optional)
    
    Note: Does not implement algorithms, only responsible for calling底层 tools
    
    Architecture Note:
    - This class follows the same delegation pattern as rule_mining.DataPreprocessor
    - It delegates to CorrelationAnalyzer and VIFAnalyzer (bottom-layer tools)
    - Maintains single responsibility: workflow orchestration only
    
    Attributes:
        iv_lower: IV lower bound (default: 0.02)
        iv_upper: IV upper bound (default: 0.5)
        vif_threshold: VIF threshold (default: 5.0)
        corr_threshold: Correlation threshold (default: 0.7)
    """
    
    def __init__(
        self,
        iv_lower: float = 0.02,
        iv_upper: float = 0.5,
        vif_threshold: float = 5.0,
        corr_threshold: float = 0.7
    ):
        """
        Initialize FeatureSelector.
        
        Args:
            iv_lower: IV lower bound
            iv_upper: IV upper bound
            vif_threshold: VIF threshold
            corr_threshold: Correlation threshold
        """
        self.iv_lower = iv_lower
        self.iv_upper = iv_upper
        self.vif_threshold = vif_threshold
        self.corr_threshold = corr_threshold
        
        # ✅ Initialize底层 tools (following rule_mining.DataPreprocessor pattern)
        self._corr_analyzer = CorrelationAnalyzer()
        self._vif_analyzer = VIFAnalyzer()
        
        # State tracking
        self.selected_features_: list[str] = []
        self.removed_by_iv_: list[str] = []
        self.removed_by_corr_: list[str] = []
        self.removed_by_vif_: list[str] = []
        self.removed_by_stepwise_: list[str] = []
        self.removed_by_significance_: list[str] = []
        self.removed_by_coefficient_: list[str] = []
        self.iv_table_: pd.DataFrame | None = None
        self.corr_matrix_: pd.DataFrame | None = None
        self.vif_table_: pd.DataFrame | None = None
        self.stepwise_result_: dict[str, Any] = {}
        self.significance_result_: dict[str, Any] = {}
        self.coefficient_validation_: dict[str, Any] = {}
    
    def select_by_iv(
        self,
        iv_table: pd.DataFrame,
        lower: float | None = None,
        upper: float | None = None
    ) -> list[str]:
        """
        Filter features by IV value.
        
        Args:
            iv_table: IV value table (columns: variable, iv)
            lower: IV lower bound (uses self.iv_lower if not provided)
            upper: IV upper bound (uses self.iv_upper if not provided)
            
        Returns:
            List of features meeting IV criteria
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if lower is None:
            lower = self.iv_lower
        if upper is None:
            upper = self.iv_upper
        
        self.iv_table_ = iv_table
        
        # Validate iv_table structure
        if not isinstance(iv_table, pd.DataFrame):
            logger.error(f"iv_table is not a DataFrame, got {type(iv_table)}")
            raise ValueError(f"iv_table must be a DataFrame, got {type(iv_table)}")
        
        if 'iv' not in iv_table.columns:
            logger.error(f"iv_table missing 'iv' column. Columns: {list(iv_table.columns)}")
            raise KeyError(f"iv_table missing 'iv' column. Available columns: {list(iv_table.columns)}")
        
        if 'variable' not in iv_table.columns:
            logger.error(f"iv_table missing 'variable' column. Columns: {list(iv_table.columns)}")
            raise KeyError(f"iv_table missing 'variable' column. Available columns: {list(iv_table.columns)}")
        
        # Filter features within IV range
        valid_features = iv_table[
            (iv_table['iv'] >= lower) & (iv_table['iv'] <= upper)
        ]['variable'].tolist()
        
        # Record removed features
        all_features = iv_table['variable'].tolist()
        self.removed_by_iv_ = [f for f in all_features if f not in valid_features]
        
        return valid_features
    
    def filter_by_correlation(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        threshold: float | None = None,
        method: Literal['pearson', 'spearman', 'kendall'] = 'pearson'
    ) -> tuple[list[str], pd.DataFrame, list[tuple[str, str, float]]]:
        """
        Filter features by correlation (✅ delegates to CorrelationAnalyzer).
        
        Args:
            df: Input dataframe
            feature_cols: Features to filter
            threshold: Correlation threshold (uses self.corr_threshold if not provided)
            method: Correlation method
            
        Returns:
            Tuple of (remaining_features, correlation_matrix, high_correlation_pairs)
        """
        if threshold is None:
            threshold = self.corr_threshold
        
        # ✅ Delegate to底层 analyzer
        self.corr_matrix_ = self._corr_analyzer.calculate_correlation(
            df, feature_cols, method
        )
        
        high_corr_pairs = self._corr_analyzer.find_high_correlation(
            self.corr_matrix_, threshold
        )
        
        _, removed, _ = self._corr_analyzer.filter_by_correlation(
            df, feature_cols, threshold, method, keep='first'
        )
        
        # Record state
        self.removed_by_corr_ = removed
        remaining = [f for f in feature_cols if f not in removed]
        
        return remaining, self.corr_matrix_, high_corr_pairs
    
    def filter_by_vif(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        threshold: float | None = None,
        max_iterations: int = 10
    ) -> tuple[list[str], pd.DataFrame]:
        """
        Filter features by VIF (✅ delegates to VIFAnalyzer).
        
        Args:
            df: Input dataframe
            feature_cols: Features to filter
            threshold: VIF threshold (uses self.vif_threshold if not provided)
            max_iterations: Maximum iterations
            
        Returns:
            Tuple of (remaining_features, final_vif_table)
        """
        if threshold is None:
            threshold = self.vif_threshold
        
        # ✅ Delegate to底层 analyzer
        _, removed, self.vif_table_ = self._vif_analyzer.filter_by_vif(
            df, feature_cols, threshold, max_iterations
        )
        
        # Record state
        self.removed_by_vif_ = removed
        remaining = [f for f in feature_cols if f not in removed]
        
        return remaining, self.vif_table_
    
    def stepwise_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        direction: str = 'both',
        significance_level: float = 0.05,
        max_iterations: int = 100
    ) -> tuple[list[str], dict[str, Any]]:
        """
        Stepwise regression feature selection using statsmodels.
        
        Implements forward, backward, and bidirectional stepwise selection
        based on p-value significance testing.
        
        Args:
            X: Feature matrix (WOE-transformed)
            y: Target variable (0/1)
            direction: Selection direction ('forward'/'backward'/'both')
            significance_level: Significance level for p-value threshold
            max_iterations: Maximum iterations to prevent infinite loops
            
        Returns:
            Tuple of (selected_features, stepwise_detail)
            stepwise_detail contains:
            - steps: List of selection steps with added/removed features
            - final_pvalues: P-values of final model
            - direction: Selection direction used
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            import statsmodels.api as sm
        except ImportError:
            logger.warning("statsmodels not available, returning all features")
            return X.columns.tolist(), {'error': 'statsmodels not installed'}
        
        all_features = list(X.columns)
        steps: list[dict[str, Any]] = []
        
        if direction == 'forward':
            selected, steps = self._forward_selection(
                X, y, significance_level, max_iterations, sm, logger
            )
        elif direction == 'backward':
            selected, steps = self._backward_selection(
                X, y, significance_level, max_iterations, sm, logger
            )
        else:  # 'both' - bidirectional
            selected, steps = self._bidirectional_selection(
                X, y, significance_level, max_iterations, sm, logger
            )
        
        # Get final p-values
        final_pvalues = {}
        if selected:
            X_selected = sm.add_constant(X[selected])
            try:
                model = sm.Logit(y, X_selected).fit(disp=0)
                for feat in selected:
                    if feat in model.pvalues.index:
                        final_pvalues[feat] = round(float(model.pvalues[feat]), 6)
            except Exception as e:
                logger.warning(f"Failed to get final p-values: {e}")
        
        self.stepwise_result_ = {
            'selected_features': selected,
            'steps': steps,
            'final_pvalues': final_pvalues,
            'direction': direction,
            'significance_level': significance_level
        }
        
        logger.info(f"Stepwise selection ({direction}): {len(all_features)} -> {len(selected)} features")
        
        return selected, self.stepwise_result_
    
    def _forward_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        significance_level: float,
        max_iterations: int,
        sm: Any,
        logger: Any
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Forward stepwise selection."""
        remaining = set(X.columns)
        selected: list[str] = []
        steps: list[dict[str, Any]] = []
        
        for iteration in range(max_iterations):
            if not remaining:
                break
            
            best_pvalue = 1.0
            best_feature = None
            
            for feat in remaining:
                test_features = selected + [feat]
                X_test = sm.add_constant(X[test_features])
                try:
                    model = sm.Logit(y, X_test).fit(disp=0)
                    pvalue = model.pvalues.get(feat, 1.0)
                    if pvalue < best_pvalue:
                        best_pvalue = pvalue
                        best_feature = feat
                except Exception:
                    continue
            
            if best_feature is not None and best_pvalue < significance_level:
                selected.append(best_feature)
                remaining.remove(best_feature)
                steps.append({
                    'iteration': iteration + 1,
                    'action': 'add',
                    'feature': best_feature,
                    'pvalue': round(best_pvalue, 6)
                })
                logger.debug(f"Forward: Added {best_feature} (p={best_pvalue:.6f})")
            else:
                break
        
        return selected, steps
    
    def _backward_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        significance_level: float,
        max_iterations: int,
        sm: Any,
        logger: Any
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Backward stepwise selection."""
        selected = list(X.columns)
        steps: list[dict[str, Any]] = []
        
        for iteration in range(max_iterations):
            if len(selected) <= 1:
                break
            
            X_test = sm.add_constant(X[selected])
            try:
                model = sm.Logit(y, X_test).fit(disp=0)
            except Exception:
                break
            
            # Find feature with highest p-value
            pvalues = model.pvalues.drop('const', errors='ignore')
            if pvalues.empty:
                break
            
            worst_feature = pvalues.idxmax()
            worst_pvalue = pvalues.max()
            
            if worst_pvalue > significance_level:
                selected.remove(worst_feature)
                steps.append({
                    'iteration': iteration + 1,
                    'action': 'remove',
                    'feature': worst_feature,
                    'pvalue': round(float(worst_pvalue), 6)
                })
                logger.debug(f"Backward: Removed {worst_feature} (p={worst_pvalue:.6f})")
            else:
                break
        
        return selected, steps
    
    def _bidirectional_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        significance_level: float,
        max_iterations: int,
        sm: Any,
        logger: Any
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Bidirectional stepwise selection (forward + backward)."""
        remaining = set(X.columns)
        selected: list[str] = []
        steps: list[dict[str, Any]] = []
        
        for iteration in range(max_iterations):
            changed = False
            
            # Forward step: try to add best feature
            if remaining:
                best_pvalue = 1.0
                best_feature = None
                
                for feat in remaining:
                    test_features = selected + [feat]
                    X_test = sm.add_constant(X[test_features])
                    try:
                        model = sm.Logit(y, X_test).fit(disp=0)
                        pvalue = model.pvalues.get(feat, 1.0)
                        if pvalue < best_pvalue:
                            best_pvalue = pvalue
                            best_feature = feat
                    except Exception:
                        continue
                
                if best_feature is not None and best_pvalue < significance_level:
                    selected.append(best_feature)
                    remaining.remove(best_feature)
                    steps.append({
                        'iteration': iteration + 1,
                        'action': 'add',
                        'feature': best_feature,
                        'pvalue': round(best_pvalue, 6)
                    })
                    logger.debug(f"Bidirectional: Added {best_feature} (p={best_pvalue:.6f})")
                    changed = True
            
            # Backward step: try to remove worst feature
            if len(selected) > 1:
                X_test = sm.add_constant(X[selected])
                try:
                    model = sm.Logit(y, X_test).fit(disp=0)
                    pvalues = model.pvalues.drop('const', errors='ignore')
                    
                    if not pvalues.empty:
                        worst_feature = pvalues.idxmax()
                        worst_pvalue = pvalues.max()
                        
                        if worst_pvalue > significance_level:
                            selected.remove(worst_feature)
                            remaining.add(worst_feature)
                            steps.append({
                                'iteration': iteration + 1,
                                'action': 'remove',
                                'feature': worst_feature,
                                'pvalue': round(float(worst_pvalue), 6)
                            })
                            logger.debug(f"Bidirectional: Removed {worst_feature} (p={worst_pvalue:.6f})")
                            changed = True
                except Exception:
                    pass
            
            if not changed:
                break
        
        return selected, steps
    
    def validate_significance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        feature_cols: list[str],
        significance_level: float = 0.05
    ) -> tuple[list[str], dict[str, Any]]:
        """
        Validate feature significance using p-value testing.
        
        Fits a logistic regression model and checks p-values for all features.
        Features with p-value > significance_level are flagged for removal.
        
        Args:
            X: Feature matrix (WOE-transformed)
            y: Target variable (0/1)
            feature_cols: Features to validate
            significance_level: P-value threshold
            
        Returns:
            Tuple of (significant_features, validation_result)
            validation_result contains:
            - all_pvalues: Dict of feature -> p-value
            - significant: List of significant features
            - insignificant: List of insignificant features
            - model_summary: Model summary statistics
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            import statsmodels.api as sm
        except ImportError:
            logger.warning("statsmodels not available, returning all features")
            return feature_cols, {'error': 'statsmodels not installed'}
        
        if not feature_cols:
            return [], {'error': 'No features provided'}
        
        X_subset = sm.add_constant(X[feature_cols])
        
        try:
            model = sm.Logit(y, X_subset).fit(disp=0)
        except Exception as e:
            logger.error(f"Logit model fitting failed: {e}")
            return feature_cols, {'error': str(e)}
        
        # Extract p-values (exclude constant)
        pvalues = model.pvalues.drop('const', errors='ignore')
        
        all_pvalues = {feat: round(float(pvalues.get(feat, 1.0)), 6) for feat in feature_cols}
        significant = [feat for feat, pval in all_pvalues.items() if pval <= significance_level]
        insignificant = [feat for feat, pval in all_pvalues.items() if pval > significance_level]
        
        self.removed_by_significance_ = insignificant
        self.significance_result_ = {
            'all_pvalues': all_pvalues,
            'significant': significant,
            'insignificant': insignificant,
            'significance_level': significance_level,
            'model_aic': round(float(model.aic), 2),
            'model_bic': round(float(model.bic), 2),
            'pseudo_r2': round(float(model.prsquared), 4)
        }
        
        logger.info(f"Significance validation: {len(significant)}/{len(feature_cols)} features significant (p<{significance_level})")
        if insignificant:
            logger.info(f"Insignificant features: {insignificant}")
        
        return significant, self.significance_result_
    
    def validate_coefficient_direction(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        feature_cols: list[str],
        iv_table: pd.DataFrame | None = None,
        mode: str = 'warn'
    ) -> tuple[list[str], dict[str, Any]]:
        """
        Validate coefficient direction against WOE encoding constraint.
        
        In credit scoring, higher WOE should correspond to lower risk (positive coefficient).
        This method checks if coefficient signs are consistent with WOE direction.
        
        Note: This is a mathematical consistency check based on standard WOE formula,
        not a true business logic validation. In some cases (e.g., non-monotonic relationships),
        a negative coefficient may still be business-appropriate.
        
        WOE Encoding Constraint:
        - WOE > 0 means good customers are over-represented -> lower risk
        - WOE < 0 means bad customers are over-represented -> higher risk
        - Coefficient should be positive (higher WOE -> higher score -> lower risk)
        
        Args:
            X: Feature matrix (WOE-transformed)
            y: Target variable (0/1, where 1=bad)
            feature_cols: Features to validate
            iv_table: IV table for additional context (optional)
            mode: Handling mode for direction anomalies
                - 'warn': Keep features, only generate warnings (default)
                - 'remove': Remove features with invalid direction
                - 'ignore': Skip validation entirely
            
        Returns:
            Tuple of (valid_features, validation_result)
            - If mode='warn': returns all features (no removal)
            - If mode='remove': returns only valid direction features
            - If mode='ignore': returns all features (no validation)
            validation_result contains:
            - coefficients: Dict of feature -> coefficient
            - valid_direction: List of features with valid direction
            - invalid_direction: List of features with invalid direction
            - warnings: List of warning messages
            - mode: The handling mode used
        """
        import logging
        logger = logging.getLogger(__name__)
        
        from sklearn.linear_model import LogisticRegression
        
        if not feature_cols:
            return [], {'error': 'No features provided', 'mode': mode}
        
        # If mode is 'ignore', skip validation entirely
        if mode == 'ignore':
            logger.info("Coefficient direction validation skipped (mode='ignore')")
            self.removed_by_coefficient_ = []
            self.coefficient_validation_ = {
                'coefficients': {},
                'valid_direction': feature_cols,
                'invalid_direction': [],
                'warnings': [],
                'intercept': None,
                'mode': mode,
                'message': '系数方向验证已跳过（用户选择忽略）'
            }
            return feature_cols, self.coefficient_validation_
        
        # Fit logistic regression
        model = LogisticRegression(
            penalty='l2',
            C=1.0,
            solver='lbfgs',
            max_iter=1000,
            random_state=42
        )
        
        try:
            model.fit(X[feature_cols], y)
        except Exception as e:
            logger.error(f"Model fitting failed: {e}")
            return feature_cols, {'error': str(e), 'mode': mode}
        
        # Get coefficients
        coefficients = dict(zip(feature_cols, model.coef_[0]))
        
        # Validate direction: coefficient should be positive for WOE features
        # (higher WOE -> higher probability of good -> lower probability of bad)
        valid_direction: list[str] = []
        invalid_direction: list[str] = []
        warnings: list[str] = []
        
        for feat, coef in coefficients.items():
            # In standard scorecard: coefficient should be positive
            # Negative coefficient means inverse relationship (may or may not be problematic)
            if coef >= 0:
                valid_direction.append(feat)
            else:
                invalid_direction.append(feat)
                if mode == 'warn':
                    warnings.append(
                        f"⚠️ 特征 '{feat}' 系数为负 ({coef:.4f})，不符合WOE编码约束。"
                        f"请根据业务逻辑判断是否合理（如非单调关系可能导致负系数）。"
                    )
                elif mode == 'remove':
                    warnings.append(
                        f"🚫 特征 '{feat}' 系数为负 ({coef:.4f})，已自动移除。"
                    )
        
        # Determine which features to return based on mode
        if mode == 'remove':
            self.removed_by_coefficient_ = invalid_direction
            returned_features = valid_direction
        else:  # mode == 'warn'
            self.removed_by_coefficient_ = []  # Not removing any features
            returned_features = feature_cols
        
        self.coefficient_validation_ = {
            'coefficients': {k: round(v, 6) for k, v in coefficients.items()},
            'valid_direction': valid_direction,
            'invalid_direction': invalid_direction,
            'warnings': warnings,
            'intercept': round(float(model.intercept_[0]), 6),
            'mode': mode,
            'mode_description': {
                'warn': '警告模式：保留所有变量，仅提示方向异常',
                'remove': '移除模式：自动移除方向异常变量',
                'ignore': '忽略模式：跳过系数方向验证'
            }.get(mode, mode)
        }
        
        logger.info(f"Coefficient validation (mode={mode}): {len(valid_direction)}/{len(feature_cols)} features have valid direction")
        if invalid_direction:
            if mode == 'remove':
                logger.warning(f"Features removed due to invalid direction: {invalid_direction}")
            else:
                logger.warning(f"Features with invalid direction (kept due to mode='{mode}'): {invalid_direction}")
            for warning in warnings:
                logger.warning(warning)
        
        return returned_features, self.coefficient_validation_
    
    def select_features(
        self,
        df: pd.DataFrame,
        iv_table: pd.DataFrame,
        feature_cols: list[str],
        target_col: str | None = None,
        use_correlation: bool = True,
        use_vif: bool = True,
        use_stepwise: bool = False,
        stepwise_direction: str = 'both',
        significance_level: float = 0.05,
        validate_coefficients: bool = False,
        coefficient_direction_mode: str = 'warn',
        progress_callback: ProgressCallback = None
    ) -> tuple[list[str], dict[str, Any]]:
        """
        Complete feature selection pipeline.
        
        Workflow:
        1. IV filtering
        2. Correlation filtering (optional)
        3. VIF testing (optional)
        4. Stepwise regression (optional, requires target_col)
        5. Significance testing (optional, requires target_col)
        6. Coefficient direction validation (optional, requires target_col)
        
        Args:
            df: Input dataframe (WOE-transformed)
            iv_table: IV value table
            feature_cols: Candidate features
            target_col: Target column name (required for stepwise/significance/coefficient validation)
            use_correlation: Whether to perform correlation filtering
            use_vif: Whether to perform VIF testing
            use_stepwise: Whether to use stepwise regression
            stepwise_direction: Stepwise direction ('forward'/'backward'/'both')
            significance_level: P-value threshold for significance testing
            validate_coefficients: Whether to validate coefficient direction
            coefficient_direction_mode: Handling mode for coefficient direction anomalies
                - 'warn': Keep features, only generate warnings (default)
                - 'remove': Remove features with invalid direction
                - 'ignore': Skip validation entirely
            progress_callback: Progress callback function
            
        Returns:
            Tuple of (final_feature_list, selection_detail_dict)
        """
        # Calculate total steps
        total_steps = 1 + int(use_correlation) + int(use_vif)
        if use_stepwise and target_col:
            total_steps += 1
        if validate_coefficients and target_col:
            total_steps += 1
        current_step = 0
        
        # Step 1: IV filtering (returns original feature names)
        current_step += 1
        if progress_callback:
            progress_callback("IV筛选", current_step, total_steps)
        
        selected = self.select_by_iv(iv_table)
        
        # Convert to WOE column names for correlation and VIF analysis
        selected_woe = [f"{f}_woe" for f in selected]
        
        # Step 2: Correlation filtering (use WOE columns)
        if use_correlation:
            current_step += 1
            if progress_callback:
                progress_callback("相关性分析", current_step, total_steps)
            
            selected_woe, corr_matrix, high_corr = self.filter_by_correlation(
                df, selected_woe
            )
        
        # Step 3: VIF testing (use WOE columns)
        if use_vif:
            current_step += 1
            if progress_callback:
                progress_callback("VIF检验", current_step, total_steps)
            
            selected_woe, vif_table = self.filter_by_vif(df, selected_woe)
        
        # Step 4: Stepwise regression (optional)
        stepwise_result = None
        if use_stepwise and target_col and target_col in df.columns:
            current_step += 1
            if progress_callback:
                progress_callback("逐步回归", current_step, total_steps)
            
            X = df[selected_woe]
            y = df[target_col]
            selected_woe, stepwise_result = self.stepwise_selection(
                X, y, direction=stepwise_direction, significance_level=significance_level
            )
            self.removed_by_stepwise_ = [f for f in selected_woe if f not in selected_woe]
        
        # Step 5: Coefficient direction validation (optional)
        coefficient_result = None
        if validate_coefficients and target_col and target_col in df.columns and selected_woe:
            current_step += 1
            if progress_callback:
                progress_callback("系数方向验证", current_step, total_steps)
            
            X = df[selected_woe]
            y = df[target_col]
            selected_woe, coefficient_result = self.validate_coefficient_direction(
                X, y, selected_woe, iv_table, mode=coefficient_direction_mode
            )
            # Feature removal depends on coefficient_direction_mode:
            # - 'warn': features kept, only warnings generated
            # - 'remove': features with invalid direction removed
            # - 'ignore': validation skipped entirely
        
        # Convert back to original feature names for bins lookup
        selected = [f.replace('_woe', '') for f in selected_woe]
        
        # Build detail dict
        detail: dict[str, Any] = {
            'initial_features': feature_cols,
            'final_features': selected,
            'removed_by_iv': self.removed_by_iv_,
            'removed_by_corr': self.removed_by_corr_,
            'removed_by_vif': self.removed_by_vif_,
            'removed_by_stepwise': self.removed_by_stepwise_,
            'removed_by_significance': self.removed_by_significance_,
            'removed_by_coefficient': self.removed_by_coefficient_,
            'iv_table': self.iv_table_,
            'corr_matrix': self.corr_matrix_,
            'vif_table': self.vif_table_
        }
        
        # Add stepwise result if available
        if stepwise_result:
            detail['stepwise_result'] = stepwise_result
        
        # Add coefficient validation result if available
        if coefficient_result:
            detail['coefficient_validation'] = coefficient_result
        
        self.selected_features_ = selected
        return selected, detail


class ScorecardModeler:
    """
    Scorecard modeler with statistical testing (v4.2 upgrade).
    
    Encapsulates logistic regression model training with comprehensive
    statistical information output:
    - Coefficient standard errors
    - Z-statistics and p-values
    - 95% confidence intervals
    - Model fit statistics (pseudo R², AIC, BIC)
    
    Attributes:
        significance_level: P-value threshold for significance testing (default: 0.05)
        use_statistical_model: Whether to use StatisticalLogisticRegression (default: True)
        penalty: Regularization penalty (None for no regularization)
        C: Inverse regularization strength
    
    Example:
        >>> modeler = ScorecardModeler(use_statistical_model=True)
        >>> modeler.fit(X_train_woe, y_train)
        >>> stats = modeler.get_statistics()
        >>> print(stats['summary'])  # DataFrame with coef, std_err, z, p_value
    """
    
    def __init__(
        self,
        significance_level: float = 0.05,
        use_statistical_model: bool = True,
        penalty: str | None = None,
        C: float = 1e10,
        solver: str = 'lbfgs',
        max_iter: int = 1000,
        random_state: int = 42,
        **kwargs: Any
    ):
        """
        Initialize ScorecardModeler.
        
        Args:
            significance_level: P-value threshold for significance testing
            use_statistical_model: If True, use StatisticalLogisticRegression for stats
            penalty: Regularization penalty (None recommended for accurate statistics)
            C: Inverse regularization strength (large = weak regularization)
            solver: Optimization algorithm
            max_iter: Maximum iterations
            random_state: Random seed
            **kwargs: Additional arguments for the model
        """
        self.significance_level = significance_level
        self.use_statistical_model = use_statistical_model
        self.penalty = penalty
        self.C = C
        self.solver = solver
        self.max_iter = max_iter
        self.random_state = random_state
        self.kwargs = kwargs
        
        # Initialize model based on configuration
        if use_statistical_model:
            self.model = StatisticalLogisticRegression(
                calculate_stats=True,
                penalty=penalty,
                C=C,
                solver=solver,
                max_iter=max_iter,
                random_state=random_state,
                **kwargs
            )
        else:
            self.model = LogisticRegression(
                penalty=penalty,
                C=C,
                solver=solver,
                max_iter=max_iter,
                random_state=random_state,
                **kwargs
            )
        
        self.feature_names_: list[str] = []
        self._statistics: dict[str, Any] | None = None
    
    def fit(
        self,
        X: pd.DataFrame | np.ndarray,
        y: pd.Series | np.ndarray,
        feature_names: list[str] | None = None
    ) -> "ScorecardModeler":
        """
        Fit the model.
        
        Args:
            X: Feature matrix (WOE-transformed)
            y: Target variable (0/1)
            feature_names: Feature names (optional, inferred from DataFrame)
            
        Returns:
            self
        """
        # Store feature names
        if feature_names is not None:
            self.feature_names_ = feature_names
        elif isinstance(X, pd.DataFrame):
            self.feature_names_ = X.columns.tolist()
        else:
            self.feature_names_ = [f'x{i}' for i in range(X.shape[1])]
        
        # Fit model
        self.model.fit(X, y)
        
        # Calculate statistics if using statistical model
        if self.use_statistical_model:
            self._statistics = self.model.summary()
        
        return self
    
    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Predict class labels."""
        return self.model.predict(X)
    
    def predict_proba(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        return self.model.predict_proba(X)
    
    def get_coefficients(self) -> dict[str, float]:
        """
        Get model coefficients.
        
        Returns:
            Dict mapping feature name to coefficient
        """
        return dict(zip(self.feature_names_, self.model.coef_[0]))
    
    def get_intercept(self) -> float:
        """Get model intercept."""
        return float(self.model.intercept_[0])
    
    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistical testing information.
        
        Returns:
            dict with keys:
            - summary: List of coefficient statistics (feature, coef, std_err, z, p_value, ci_lower, ci_upper)
            - model_info: Dict with pseudo_r2, log_likelihood, aic, bic, n_observations
            - significant_vars: List of significant variables (p < significance_level)
            - insignificant_vars: List of insignificant variables
            
        Raises:
            ValueError: If statistical model not enabled
        """
        if not self.use_statistical_model:
            raise ValueError(
                "Statistical model not enabled. Set use_statistical_model=True"
            )
        
        if self._statistics is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # Get summary from model
        summary = self._statistics.get('summary', [])
        
        # Identify significant/insignificant variables
        significant_vars = []
        insignificant_vars = []
        
        for item in summary:
            feature = item.get('feature', '')
            p_value = item.get('p_value')
            
            # Skip intercept
            if feature == 'const':
                continue
            
            if p_value is not None and p_value < self.significance_level:
                significant_vars.append(feature)
            else:
                insignificant_vars.append(feature)
        
        return {
            'summary': summary,
            'n_observations': self._statistics.get('n_observations'),
            'n_features': self._statistics.get('n_features'),
            'n_params': self._statistics.get('n_params'),
            'log_likelihood': self._statistics.get('log_likelihood'),
            'null_log_likelihood': self._statistics.get('null_log_likelihood'),
            'pseudo_r2': self._statistics.get('pseudo_r2'),
            'aic': self._statistics.get('aic'),
            'bic': self._statistics.get('bic'),
            'lr_stat': self._statistics.get('lr_stat'),
            'lr_pvalue': self._statistics.get('lr_pvalue'),
            'significant_vars': significant_vars,
            'insignificant_vars': insignificant_vars,
            'significance_level': self.significance_level
        }
    
    def check_coefficient_direction(
        self,
        expected_signs: dict[str, int] | None = None
    ) -> dict[str, Any]:
        """
        Check if coefficient directions match business logic.
        
        In credit scoring, WOE coefficients should typically be positive
        (higher WOE -> lower risk -> higher score).
        
        Args:
            expected_signs: Optional dict of feature -> expected sign (+1 or -1)
                          If None, expects all positive coefficients
                          
        Returns:
            dict with:
            - valid_direction: List of features with valid direction
            - invalid_direction: List of features with invalid direction
            - warnings: List of warning messages
        """
        coefficients = self.get_coefficients()
        
        valid_direction = []
        invalid_direction = []
        warnings = []
        
        for feat, coef in coefficients.items():
            expected = expected_signs.get(feat, 1) if expected_signs else 1
            
            if (expected > 0 and coef >= 0) or (expected < 0 and coef < 0):
                valid_direction.append(feat)
            else:
                invalid_direction.append(feat)
                warnings.append(
                    f"特征 '{feat}' 系数为 {coef:.4f}，与预期方向不符"
                )
        
        return {
            'coefficients': {k: round(v, 6) for k, v in coefficients.items()},
            'intercept': self.get_intercept(),
            'valid_direction': valid_direction,
            'invalid_direction': invalid_direction,
            'warnings': warnings
        }


class ScorecardScaler:
    """
    Score scale transformer for credit scoring (v4.2 upgrade).
    
    Encapsulates score transformation with bidirectional conversion:
    - Generate scorecard from model and bins
    - Calculate sample scores
    - Score ↔ Probability bidirectional conversion
    
    Attributes:
        base_score: Base score at base odds (default: 600)
        base_odds: Base odds ratio (default: 50, meaning 1:50 good:bad)
        pdo: Points to Double Odds (default: 50)
        bad_rate: Base bad rate (optional, calculated from data if not provided)
    
    Example:
        >>> scaler = ScorecardScaler(base_score=600, pdo=50)
        >>> scaler.fit(y_train)
        >>> scorecard = scaler.generate_scorecard(bins, model, features)
        >>> probs = scaler.score_to_probability([600, 650, 700])
    """
    
    def __init__(
        self,
        base_score: int = 600,
        base_odds: float = 50.0,
        pdo: int = 50,
        bad_rate: float | None = None,
        score_min: float = 300,
        score_max: float = 850
    ):
        """
        Initialize ScorecardScaler.
        
        Args:
            base_score: Score at base odds
            base_odds: Base odds ratio (good:bad ratio at base_score)
            pdo: Points to Double Odds
            bad_rate: Base bad rate (optional, calculated from y_train if not provided)
            score_min: Minimum score limit
            score_max: Maximum score limit
        """
        self.base_score = base_score
        self.base_odds = base_odds
        self.pdo = pdo
        self.bad_rate = bad_rate
        self.score_min = score_min
        self.score_max = score_max
        
        self._transformer: ScoreTransformer | None = None
        self._fitted = False
    
    def fit(self, y_train: pd.Series | np.ndarray | None = None) -> "ScorecardScaler":
        """
        Initialize the transformer.
        
        Args:
            y_train: Training set target variable for calculating actual bad_rate
            
        Returns:
            self
        """
        # Calculate actual bad_rate if not specified
        if self.bad_rate is None and y_train is not None:
            self.bad_rate = float(np.mean(y_train))
        elif self.bad_rate is None:
            # Infer from base_odds: odds = bad/good = bad_rate/(1-bad_rate)
            # base_odds = good/bad = (1-bad_rate)/bad_rate
            # bad_rate = 1 / (1 + base_odds)
            self.bad_rate = 1 / (1 + self.base_odds)
        
        # Initialize transformer
        self._transformer = ScoreTransformer(
            base_score=self.base_score,
            pdo=self.pdo,
            bad_rate=self.bad_rate,
            down_lmt=self.score_min,
            up_lmt=self.score_max
        )
        self._transformer.fit()
        
        self._fitted = True
        return self
    
    def _ensure_fitted(self) -> None:
        """Ensure scaler is fitted."""
        if not self._fitted:
            self.fit()
    
    def score_to_probability(
        self,
        scores: float | list | np.ndarray | pd.Series
    ) -> np.ndarray:
        """
        Convert scores to probabilities.
        
        Args:
            scores: Credit score(s)
            
        Returns:
            Corresponding default probability(ies)
        """
        self._ensure_fitted()
        return self._transformer.inverse_transform(scores)  # type: ignore
    
    def probability_to_score(
        self,
        probs: float | list | np.ndarray | pd.Series
    ) -> np.ndarray:
        """
        Convert probabilities to scores.
        
        Args:
            probs: Default probability(ies)
            
        Returns:
            Corresponding credit score(s)
        """
        self._ensure_fitted()
        return self._transformer.transform(probs)  # type: ignore
    
    def get_scale_info(self) -> dict[str, Any]:
        """
        Get score scale parameters.
        
        Returns:
            Dict with base_score, pdo, bad_rate, A, B, etc.
        """
        self._ensure_fitted()
        return self._transformer.get_scale_info()  # type: ignore
    
    def convert(
        self,
        values: float | list | np.ndarray,
        direction: str = "to_prob"
    ) -> list[dict[str, float]]:
        """
        Convert values with input/output pairs.
        
        Args:
            values: Values to convert
            direction: "to_prob" (score→prob) or "to_score" (prob→score)
            
        Returns:
            List of dicts with 'input' and 'output' keys
        """
        self._ensure_fitted()
        return self._transformer.convert(values, direction)  # type: ignore
    
    def generate_score_table(
        self,
        prob_range: tuple[float, float] = (0.01, 0.50),
        n_points: int = 20
    ) -> pd.DataFrame:
        """
        Generate a score-probability lookup table.
        
        Args:
            prob_range: Range of probabilities (min, max)
            n_points: Number of points in the table
            
        Returns:
            DataFrame with columns: probability, score, odds
        """
        self._ensure_fitted()
        return self._transformer.generate_score_table(prob_range, n_points)  # type: ignore


# Type alias for stage progress callback
# Extended to support optional code and output_preview parameters
# Signature: (stage_id, progress_percent, message, code?, output_preview?)
StageProgressCallback = (
    Callable[[str, float, str], None] | 
    Callable[[str, float, str, str | None], None] |
    Callable[[str, float, str, str | None, dict[str, Any] | None], None] | 
    None
)


class ScorecardPipeline:
    """
    Complete scorecard development pipeline orchestrator.
    
    Combines DataPreprocessor, WOETransformer, FeatureSelector into a single
    end-to-end workflow for credit scorecard development.
    
    Workflow:
    1. Data Loading & Validation - Load data, check target column
    2. WOE Binning - Auto binning, IV calculation
    3. Feature Selection - IV filtering, correlation, VIF
    4. Model Training - Logistic regression
    5. Score Scaling - Convert to scorecard points
    6. Model Evaluation - KS, AUC, Gini metrics
    """
    
    def __init__(
        self,
        # Data preprocessing parameters
        missing_threshold: float = 0.95,  # 缺失率阈值，默认95%较宽松（行业惯例通常50%）
        test_ratio: float = 0.3,
        random_state: int = 42,
        special_values: list[float] | None = None,
        force_categorical: list[str] | None = None,
        # Sample split parameters
        sample_type_col: str | None = None,
        # Smart OOT split parameters
        time_col: str | None = None,
        oot_ratio: float = 0.1,
        # WOE binning parameters
        bin_method: str = 'chimerge',
        max_bins: int = 10,
        use_high_precision: bool = False,
        # Feature selection parameters
        iv_lower: float = 0.02,
        iv_upper: float = 0.5,
        vif_threshold: float = 10.0,
        corr_threshold: float = 0.7,
        # Model training parameters
        use_stepwise: bool = True,
        stepwise_direction: str = 'both',
        significance_level: float = 0.05,
        significance_mode: str = 'warn',  # B+方案新增：显著性检验模式 ('skip'/'warn'/'remove')
        validate_coefficients: bool = True,
        coefficient_direction_mode: str = 'warn',
        max_validation_iterations: int = 10,  # B+方案新增：最大迭代次数
        # Score scaling parameters (industry standard: pdo=50 for wider score range)
        base_score: int = 600,
        base_odds: float = 50.0,
        pdo: int = 50,
        # Score distribution display parameters
        score_bin_method: str = 'equal_width',
        score_distribution_bins: int = 8,
        ranking_analysis_bins: int = 10,
        # Overfit detection thresholds
        overfit_ks_threshold: float = 0.05,
        overfit_auc_threshold: float = 0.03,
        # Progress callback
        progress_callback: StageProgressCallback = None,
        # Stop check callback
        stop_check_callback: Callable[[], bool] | None = None,
        # P2-6: 类别不平衡处理策略
        imbalance_strategy: str = 'auto'
    ):
        """
        Initialize ScorecardPipeline.
        
        Args:
            missing_threshold: Missing rate threshold for dropping variables
            test_ratio: Test set ratio for train/test split
            random_state: Random seed for reproducibility
            sample_type_col: Column name containing sample type labels ('train'/'test'/'oot')
            time_col: Time column for smart OOT split (optional)
            oot_ratio: OOT validation set ratio when using time-based split
            bin_method: WOE binning method ('chimerge', 'quantile', 'tree')
            max_bins: Maximum number of bins
            use_high_precision: If True, use scorecardpy.woebin for tree/chimerge 
                              binning (slower but more monotonic WOE and higher IV)
            iv_lower: IV lower bound for feature selection
            iv_upper: IV upper bound for feature selection
            vif_threshold: VIF threshold for multicollinearity check
            corr_threshold: Correlation threshold for feature filtering
            use_stepwise: Whether to use stepwise regression
            stepwise_direction: Stepwise direction ('forward'/'backward'/'both')
            significance_level: Significance level for stepwise
            significance_mode: Handling mode for significance test failures (B+ Plan)
                - 'skip': Skip significance testing entirely
                - 'warn': Keep features, only generate warnings (default)
                - 'remove': Iteratively remove insignificant features
            validate_coefficients: Whether to validate coefficient direction
            coefficient_direction_mode: Handling mode for coefficient direction anomalies
                - 'skip': Skip validation entirely
                - 'warn': Keep features, only generate warnings (default)
                - 'remove': Iteratively remove features with invalid direction
            max_validation_iterations: Maximum iterations for iterative validation loop (B+ Plan)
                Only effective when significance_mode='remove' or coefficient_direction_mode='remove'
            base_score: Base score for scorecard
            base_odds: Base odds ratio
            pdo: Points to double the odds
            score_bin_method: Score distribution binning method
                - 'equal_width': Adaptive equal-width binning (default)
                - 'equal_frequency': Equal-frequency binning (Decile)
            score_distribution_bins: Number of bins for equal-width distribution view (default: 8)
            ranking_analysis_bins: Number of bins for equal-frequency ranking analysis (default: 10, Decile)
            overfit_ks_threshold: KS difference threshold for overfit warning (default: 0.05)
            overfit_auc_threshold: AUC difference threshold for overfit warning (default: 0.03)
            progress_callback: Progress callback function
            stop_check_callback: Callback to check if execution should stop.
                Returns True if should stop, False to continue.
        """
        self.missing_threshold = missing_threshold
        self.test_ratio = test_ratio
        self.random_state = random_state
        self.special_values = special_values
        self.force_categorical = force_categorical or []
        self.sample_type_col = sample_type_col
        self.time_col = time_col
        self.oot_ratio = oot_ratio
        self.bin_method = bin_method
        self.max_bins = max_bins
        self.use_high_precision = use_high_precision
        self.iv_lower = iv_lower
        self.iv_upper = iv_upper
        self.vif_threshold = vif_threshold
        self.corr_threshold = corr_threshold
        self.use_stepwise = use_stepwise
        self.stepwise_direction = stepwise_direction
        self.significance_level = significance_level
        self.significance_mode = significance_mode  # B+方案新增
        self.validate_coefficients = validate_coefficients
        self.coefficient_direction_mode = coefficient_direction_mode
        self.max_validation_iterations = max_validation_iterations  # B+方案新增
        self.base_score = base_score
        self.base_odds = base_odds
        self.pdo = pdo
        self.score_bin_method = score_bin_method
        self.score_distribution_bins = score_distribution_bins
        self.ranking_analysis_bins = ranking_analysis_bins
        self.overfit_ks_threshold = overfit_ks_threshold
        self.overfit_auc_threshold = overfit_auc_threshold
        self.progress_callback = progress_callback
        self.stop_check_callback = stop_check_callback
        # P2-6: 类别不平衡处理
        self.imbalance_strategy = imbalance_strategy
        
        # Initialize components
        self.preprocessor = DataPreprocessor(
            missing_threshold=missing_threshold,
            test_ratio=test_ratio,
            random_state=random_state,
            special_values=special_values,
            time_col=time_col,
            oot_ratio=oot_ratio
        )
        
        self.woe_transformer = WOETransformer(
            method=bin_method,
            bin_num_limit=max_bins,
            use_scorecardpy=use_high_precision,
            enforce_monotonicity=True,
            missing_limit=missing_threshold  # 用户配置的缺失率阈值
            # iv_limit 使用默认值0.02进行WOE阶段初筛
        )
        
        self.feature_selector = FeatureSelector(
            iv_lower=iv_lower,
            iv_upper=iv_upper,
            vif_threshold=vif_threshold,
            corr_threshold=corr_threshold
        )
        
        # Results storage
        self.train_data_: pd.DataFrame | None = None
        self.test_data_: pd.DataFrame | None = None
        self.oot_data_: pd.DataFrame | None = None
        self.bins_: dict[str, Any] | None = None
        self.iv_table_: pd.DataFrame | None = None
        self.selected_features_: list[str] = []
        self.model_: LogisticRegression | None = None
        self.scorecard_: dict[str, pd.DataFrame] | None = None
        self.metrics_: dict[str, float] = {}
        self.scorecard_validation_: dict[str, Any] = {}
        self.woe_feature_cols_: list[str] = []
        # Data frames for report generation (set in model_evaluation stage)
        self._train_df: pd.DataFrame | None = None
        self._test_df: pd.DataFrame | None = None
        self._oot_df: pd.DataFrame | None = None
        # Labels and predictions for report generation
        self._y_train: pd.Series | None = None
        self._y_train_pred_proba: np.ndarray | None = None
        self._y_test: pd.Series | None = None
        self._y_pred_proba: np.ndarray | None = None
        self._y_oot: pd.Series | None = None
        self._y_oot_pred_proba: np.ndarray | None = None
    
    def _build_imbalance_analysis(self, target_rate: float) -> dict[str, Any]:
        """P2-6: 构建不平衡分析信息（用于 output_preview 展示）"""
        if target_rate >= 0.2:
            severity = "无"
        elif target_rate >= 0.1:
            severity = "轻度"
        elif target_rate >= 0.05:
            severity = "中度"
        elif target_rate >= 0.01:
            severity = "重度"
        else:
            severity = "极端"
        
        applied_strategy = self.imbalance_strategy
        if applied_strategy == 'auto':
            applied_strategy = 'class_weight' if target_rate < 0.1 else 'none'
        
        strategy_desc = {
            'none': '不处理',
            'class_weight': '类别加权（balanced）— 仅在模型训练阶段应用，WOE分箱不受影响',
            'auto': '自动选择',
        }
        
        imbalance_ratio = f"1:{(1 - target_rate) / target_rate:.1f}" if target_rate > 0 else "N/A"
        
        return {
            "target_rate": round(target_rate, 4),
            "imbalance_ratio": imbalance_ratio,
            "severity": severity,
            "user_strategy": self.imbalance_strategy,
            "applied_strategy": applied_strategy,
            "strategy_description": strategy_desc.get(applied_strategy, applied_strategy),
        }
    
    def _should_stop(self) -> bool:
        """Check if execution should stop.
        
        Returns:
            True if should stop, False to continue
        """
        if self.stop_check_callback:
            return self.stop_check_callback()
        return False
    
    def _update_progress(
        self, 
        stage_id: str, 
        progress: float, 
        message: str = "", 
        code: str | None = None,
        output_preview: dict[str, Any] | None = None
    ):
        """Update progress via callback.
        
        Args:
            stage_id: Stage identifier
            progress: Progress percentage (0-100)
            message: Progress message
            code: Optional Python pseudocode for the stage
            output_preview: Optional output preview data for the stage
        """
        if self.progress_callback:
            # Try to call with 5 args first (full signature), then 4, then 3
            try:
                self.progress_callback(stage_id, progress, message, code, output_preview)  # type: ignore
            except TypeError:
                try:
                    self.progress_callback(stage_id, progress, message, code)  # type: ignore
                except TypeError:
                    self.progress_callback(stage_id, progress, message)  # type: ignore
    
    def _get_stage_code(self, stage_id: str) -> str:
        """Get pseudocode for a stage based on current pipeline parameters.
        
        Args:
            stage_id: Stage identifier
            
        Returns:
            Formatted pseudocode string
        """
        params = {
            # Data preprocessing
            "file_path": "data.csv",
            "target_col": "target",
            "sample_type_col": "sample_type",
            "missing_threshold": self.preprocessor.missing_threshold,
            "test_ratio": self.preprocessor.test_ratio,
            # WOE binning
            "bin_method": self.woe_transformer.method,
            "max_bins": self.woe_transformer.bin_num_limit,
            # Feature selection
            "iv_lower": self.feature_selector.iv_lower,
            "iv_upper": self.feature_selector.iv_upper,
            "corr_threshold": self.feature_selector.corr_threshold,
            "vif_threshold": self.feature_selector.vif_threshold,
            # Model training
            "use_stepwise": self.use_stepwise,
            "stepwise_direction": self.stepwise_direction,
            "significance_level": self.significance_level,
            # Score scaling
            "base_score": self.base_score,
            "base_odds": self.base_odds,
            "pdo": self.pdo,
        }
        return format_code_template("scorecard_dev", stage_id, params)
    
    def _generate_scorecard_custom(
        self,
        bins: dict[str, pd.DataFrame],
        model: LogisticRegression,
        features: list[str],
        points0: float,
        odds0: float,
        pdo: float,
        digits: int = 2
    ) -> dict[str, pd.DataFrame]:
        """
        Generate scorecard with correct decimal precision (fixing scorecardpy bug).
        
        scorecardpy.scorecard has a bug where rounding is applied incorrectly 
        (passing ndigits as kwarg to assign instead of round), forcing integer rounding.
        This custom implementation ensures correct decimal precision.
        """
        import numpy as np
        import pandas as pd
        
        # 1. Calculate A and B
        # pdo = b * ln(2) => b = pdo / ln(2)
        b = pdo / np.log(2)
        # score = a - b * log(odds)
        # points0 = a - b * log(odds0) => a = points0 + b * log(odds0)
        a = points0 + b * np.log(odds0)
        
        # 2. Get coefficients
        # Map feature name (with _woe) to coefficient
        coef_map = dict(zip(features, model.coef_[0]))
        intercept = model.intercept_[0]
        
        # 3. Calculate Base Points
        # basepoints = a - b * intercept
        basepoints = a - b * intercept
        
        card = {}
        
        # Basepoints card (woe is 0 for base points)
        card['basepoints'] = pd.DataFrame({
            'variable': ['basepoints'],
            'bin': ['-'],
            'woe': [0.0],
            'points': [round(basepoints, digits)]
        })
        
        # 4. Calculate points for each feature
        for feat in features:
            # Get raw feature name (remove _woe suffix) to look up bins
            raw_feat = feat.replace('_woe', '')
            
            if raw_feat not in bins:
                # Phase 16: 添加警告日志，帮助诊断变量缺失问题
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[Scorecard] Feature '{raw_feat}' not found in bins, skipping. Available bins: {list(bins.keys())[:10]}...")
                continue
                
            # Copy bin info
            bin_df = bins[raw_feat].copy()
            coef = coef_map.get(feat, 0.0)
            
            # Points = -b * coef * woe
            # Formula: score = a - b * (intercept + sum(coef_i * woe_i))
            #                = (a - b*intercept) + sum(-b * coef_i * woe_i)
            #                = basepoints + sum(points_i)
            
            # Ensure woe is float
            bin_df['woe'] = bin_df['woe'].astype(float)
            
            # Calculate points
            bin_df['points'] = (-b * coef * bin_df['woe']).round(digits)
            
            # Ensure variable column is string (fix numpy array issue)
            # scorecardpy may return variable as array in some cases
            bin_df['variable'] = raw_feat  # Use raw feature name directly
            
            # Ensure bin column is string (convert numpy arrays if present)
            bin_df['bin'] = bin_df['bin'].apply(
                lambda x: str(x) if not isinstance(x, str) else x
            )
            
            # Format output columns
            # scorecard_ply expects 'variable' col to match input df columns (raw features).
            card[raw_feat] = bin_df[['variable', 'bin', 'points']]
            
        return card

    def run(
        self,
        df: pd.DataFrame,
        target_col: str,
        feature_cols: list[str] | None = None,
        exclude_cols: list[str] | None = None,
        weight_col: str | None = None,
        sample_type_col: str | None = None,
        time_col: str | None = None,
        oot_ratio: float = 0.0,
        progress_callback: StageProgressCallback = None,
        start_from_stage: str | None = None,
        cached_state: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Run complete scorecard development pipeline.
        
        Args:
            df: Input dataframe
            target_col: Target column name (0/1 binary)
            feature_cols: Feature columns (optional, uses all except target if None)
            exclude_cols: Columns to exclude from features (e.g., ID, serial number).
                System will also auto-detect and exclude ID-like, time, and sample type columns.
            weight_col: Weight column (optional, not used in standard scorecard)
            sample_type_col: Column name containing sample type labels ('train'/'test'/'oot').
                If provided, data will be split based on this column instead of random split.
                This enables OOT (Out-of-Time) validation.
            time_col: Column name containing time/date values for time-based OOT split.
                If provided with oot_ratio > 0, the most recent data will be used as OOT.
            oot_ratio: Ratio of data to use as OOT (0.0 = no OOT, 0.1 = 10% most recent data).
                Only used when time_col is provided.
            progress_callback: Progress callback function
            start_from_stage: 从指定阶段开始重试。之前的阶段会跳过（使用缓存数据），
                重试阶段及之后的阶段会正常执行。
            cached_state: 缓存的中间状态（Phase 6），用于阶段重试时跳过已完成阶段。
                包含 train_df, test_df, oot_df, bins, iv_table, selected_features 等字段。
            
        Returns:
            Dictionary containing all results:
            - bins: WOE binning dictionary
            - iv_table: IV values for all variables
            - selected_features: Final selected features
            - model: Trained logistic regression model
            - scorecard: Final scorecard table
            - metrics: Model evaluation metrics (KS, AUC, Gini)
            - train_data: Training data
            - test_data: Test data
            - oot_data: OOT validation data (if available)
            - multi_dataset_metrics: Metrics for train/test/oot sets
            - auto_exclude_report: Report of auto-detected non-feature columns
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if progress_callback:
            self.progress_callback = progress_callback
        
        results: dict[str, Any] = {}
        
        # ========== 阶段重试支持（Phase 6）==========
        # 定义阶段顺序
        stage_order = [
            'data_loading', 'woe_binning', 'feature_selection',
            'model_training', 'score_scaling', 'model_evaluation',
            'report_generation'
        ]
        
        # 确定起始阶段索引（用于判断是否跳过阶段）
        retry_start_idx = -1  # -1 表示没有重试
        if start_from_stage:
            if start_from_stage in stage_order:
                retry_start_idx = stage_order.index(start_from_stage)
                logger.info(f"[Scorecard Pipeline] Stage retry mode: starting from {start_from_stage} (index={retry_start_idx})")
            else:
                logger.warning(f"[Scorecard Pipeline] Unknown start_from_stage: {start_from_stage}")
        
        # 用于存储中间状态的变量（可能从缓存恢复）
        train_df: pd.DataFrame | None = None
        test_df: pd.DataFrame | None = None
        oot_df: pd.DataFrame | None = None
        df_woe: pd.DataFrame | None = None
        bins: dict[str, pd.DataFrame] | None = None
        iv_table: pd.DataFrame | None = None
        selected_features: list[str] = []
        
        # Phase 6: 从缓存状态恢复（真正的跳过已完成阶段）
        # 添加一个字典来存储各阶段的原有output_preview
        restored_output_previews: dict[str, dict[str, Any]] = {}
        if cached_state and start_from_stage and retry_start_idx > 0:
            logger.info(f"[Scorecard Pipeline] Restoring from cached state, skipping to stage: {start_from_stage}")
            
            # 恢复累积的结果
            if "results" in cached_state and cached_state["results"]:
                results.update(cached_state["results"])
                logger.info(f"[Scorecard Pipeline] Restored results keys: {list(cached_state['results'].keys())}")
            
            # 恢复各阶段的output_preview
            if "stage_outputs" in cached_state:
                for stage_id, stage_output in cached_state["stage_outputs"].items():
                    if "output_preview" in stage_output:
                        # 保存原有的output_preview，用于跳过阶段时显示
                        restored_output_previews[stage_id] = stage_output["output_preview"]
                        logger.info(f"[Scorecard Pipeline] Restored output_preview for stage: {stage_id}")
            
            # 恢复数据集
            if "train_df" in cached_state:
                train_df = cached_state["train_df"]
                self.train_data_ = train_df
            if "test_df" in cached_state:
                test_df = cached_state["test_df"]
                self.test_data_ = test_df
            if "oot_df" in cached_state:
                oot_df = cached_state["oot_df"]
                self.oot_data_ = oot_df
            
            # 恢复 WOE 相关数据
            if "df_woe" in cached_state:
                df_woe = cached_state["df_woe"]
                if df_woe is not None:
                    woe_cols_in_df = [c for c in df_woe.columns if c.endswith('_woe')]
                    logger.info(f"[Scorecard Pipeline] Restored df_woe with {len(woe_cols_in_df)} WOE columns")
                else:
                    logger.info("[Scorecard Pipeline] df_woe in cache is None")
            if "bins" in cached_state:
                bins = cached_state["bins"]
                self.bins_ = bins
                if bins is not None:
                    logger.info(f"[Scorecard Pipeline] Restored bins with {len(bins)} features: {list(bins.keys())}")
                else:
                    logger.info("[Scorecard Pipeline] bins in cache is None")
            if "iv_table" in cached_state:
                iv_table = cached_state["iv_table"]
                self.iv_table_ = iv_table
                if iv_table is not None:
                    logger.info(f"[Scorecard Pipeline] Restored iv_table with {len(iv_table)} rows")
                else:
                    logger.info("[Scorecard Pipeline] iv_table in cache is None")
            
            # Phase 21: 验证 df_woe 和 bins 的一致性
            if df_woe is not None and bins is not None:
                woe_cols_in_df = [c for c in df_woe.columns if c.endswith('_woe')]
                woe_features_in_df = set(c.replace('_woe', '') for c in woe_cols_in_df)
                bins_features = set(bins.keys())
                
                missing_in_bins = woe_features_in_df - bins_features
                if missing_in_bins:
                    logger.warning(f"[Scorecard Pipeline] 数据不一致！df_woe 有 {len(woe_features_in_df)} 个WOE特征，但 bins 只有 {len(bins_features)} 个")
                    logger.warning(f"[Scorecard Pipeline] df_woe 中有但 bins 中没有的特征: {missing_in_bins}")
            
            # 恢复特征选择结果
            if "selected_features" in cached_state:
                selected_features = cached_state["selected_features"]
                self.selected_features_ = selected_features
            if "feature_cols" in cached_state:
                feature_cols = cached_state["feature_cols"]
            
            # 恢复模型（如果有）
            if "model" in cached_state:
                self.model_ = cached_state["model"]
            if "woe_feature_cols" in cached_state:
                self.woe_feature_cols_ = cached_state["woe_feature_cols"]
            if "scorecard" in cached_state:
                self.scorecard_ = cached_state["scorecard"]
            
            # Phase 24: 恢复评估数据供report_generation使用
            if "y_train" in cached_state:
                self._y_train = cached_state["y_train"]
            if "y_train_pred_proba" in cached_state:
                self._y_train_pred_proba = cached_state["y_train_pred_proba"]
            if "y_test" in cached_state:
                self._y_test = cached_state["y_test"]
            if "y_pred_proba" in cached_state:
                self._y_pred_proba = cached_state["y_pred_proba"]
            if "y_oot" in cached_state:
                self._y_oot = cached_state["y_oot"]
            if "y_oot_pred_proba" in cached_state:
                self._y_oot_pred_proba = cached_state["y_oot_pred_proba"]
            
            # Phase 25: 恢复 self._train_df 等实例变量供report_generation使用
            if train_df is not None:
                self._train_df = train_df
            if test_df is not None:
                self._test_df = test_df
            if oot_df is not None:
                self._oot_df = oot_df
            
            # Phase 26: 恢复 woe_cols_for_selection（WOE分箱后的特征列表，用于特征选择阶段）
            # 这确保重试特征选择阶段时使用与首次执行相同的WOE特征集
            if "woe_cols_for_selection" in cached_state and cached_state["woe_cols_for_selection"]:
                woe_cols_for_selection = cached_state["woe_cols_for_selection"]
                logger.info(f"[Scorecard Pipeline] Restored woe_cols_for_selection: {len(woe_cols_for_selection)} features")
            else:
                woe_cols_for_selection = None
            
            logger.info(f"[Scorecard Pipeline] Restored state: train_df={train_df is not None}, bins={bins is not None}, selected_features={len(selected_features) if selected_features else 0}")
        else:
            # 非缓存恢复模式，初始化 woe_cols_for_selection 为 None
            woe_cols_for_selection = None
        
        def should_skip_stage(stage_id: str) -> bool:
            """检查该阶段是否应该跳过（已在缓存中完成）"""
            if retry_start_idx < 0:
                return False  # 没有重试，不跳过
            if not cached_state:
                return False  # 没有缓存，不跳过
            if stage_id not in stage_order:
                return False
            stage_idx = stage_order.index(stage_id)
            # 只有在重试阶段之前且有缓存数据时才跳过
            return stage_idx < retry_start_idx
        
        def is_before_retry_stage(stage_id: str) -> bool:
            """检查该阶段是否在重试阶段之前（需要快速执行，不暂停）"""
            if retry_start_idx < 0:
                return False  # 没有重试，所有阶段正常执行
            if stage_id not in stage_order:
                return False
            stage_idx = stage_order.index(stage_id)
            return stage_idx < retry_start_idx
        
        # 创建一个包装的进度回调，用于在重试模式下跳过专家模式暂停
        original_callback = self.progress_callback
        
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
                    logger.info(f"[Scorecard Pipeline] Stage {stage_id} completed (before retry stage, skipping pause)")
                
                # 尝试调用回调（兼容不同签名）
                try:
                    original_callback(stage_id, progress, message, code, output_preview)  # type: ignore
                except TypeError:
                    try:
                        original_callback(stage_id, progress, message, code)  # type: ignore
                    except TypeError:
                        original_callback(stage_id, progress, message)  # type: ignore
        
        # 使用包装的回调
        self.progress_callback = wrapped_progress_callback
        
        # Stage 1: Data Loading & Validation
        if should_skip_stage('data_loading'):
            # 跳过已完成的阶段，使用恢复的output_preview
            logger.info("[Scorecard Pipeline] Skipping data_loading stage (using cached data), restoring output_preview")
            if 'data_loading' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['data_loading'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('data_loading', 100.0, '数据加载已跳过（使用缓存）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('data_loading', 100.0, '数据加载已跳过（使用缓存）', output_preview=skip_preview)
                # 使用缓存的数据
                if train_df is None:
                    raise ValueError("缓存中没有 train_df，无法跳过 data_loading 阶段")
        else:
            self._update_progress("data_loading", 0.0, "开始数据加载...", code=self._get_stage_code("data_loading"))
            
            if target_col not in df.columns:
                raise ValueError(f"Target column '{target_col}' not found in dataframe")
            
            # Validate target column is binary (0/1)
            unique_values = df[target_col].dropna().unique()
            if len(unique_values) != 2:
                raise ValueError(f"Target column '{target_col}' must be binary (0/1), but found {len(unique_values)} unique values: {sorted(unique_values)[:10]}")
            if not set(unique_values).issubset({0, 1}):
                raise ValueError(f"Target column '{target_col}' must contain only 0 and 1, but found: {sorted(unique_values)[:10]}")
            
            # ========== 自动检测非建模列 ==========
            self._update_progress("data_loading", 20.0, "智能检测非建模列...")
            
            from deepanalyze.analysis.preprocessing import ColumnCleaner
            column_cleaner = ColumnCleaner()
            
            # 用户明确指定的排除列
            user_exclude_cols = set(exclude_cols) if exclude_cols else set()
            
            # 自动检测非建模列
            non_feature_detection = column_cleaner.detect_non_feature_columns(
                df, 
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
            
            # 如果用户指定了 sample_type_col 或 time_col，确保它们被排除
            if sample_type_col and sample_type_col in df.columns:
                auto_detected_cols.add(sample_type_col)
            if time_col and time_col in df.columns:
                auto_detected_cols.add(time_col)
            
            # 最终排除列 = 目标列 + 用户指定 + 自动检测
            exclude_from_features = {target_col} | user_exclude_cols | auto_detected_cols
            
            # 生成检测报告
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
                logger.info(f"[Scorecard] 自动检测到 {len(auto_detected_cols)} 个非建模列:")
                if non_feature_detection['id_cols']:
                    logger.info(f"  - ID/序号列: {non_feature_detection['id_cols']}")
                if non_feature_detection['time_cols']:
                    logger.info(f"  - 时间列: {non_feature_detection['time_cols']}")
                if non_feature_detection['sample_type_cols']:
                    logger.info(f"  - 样本类型列: {non_feature_detection['sample_type_cols']}")
                if non_feature_detection['high_cardinality_cols']:
                    logger.info(f"  - 高基数列(疑似ID): {non_feature_detection['high_cardinality_cols']}")
            
            # Determine feature columns
            if feature_cols is None:
                feature_cols = [c for c in df.columns if c not in exclude_from_features]
            else:
                # 如果用户指定了 feature_cols，仍然排除自动检测的非建模列
                feature_cols = [c for c in feature_cols if c not in exclude_from_features]
            
            logger.info(f"[Scorecard] 最终特征列数量: {len(feature_cols)}")
            
            # ========== 特殊缺失值处理（与规则挖掘任务一致）==========
            # 行业惯例：先进行特殊值替换，再统计缺失率
            # 特殊值（如-9999、-999）在业务上等同于缺失值，缺失率统计应包含这些值
            self._update_progress("data_loading", 40.0, "识别特殊缺失值...")
            special_value_info: dict[str, Any] = {
                "special_values": list(self.preprocessor.special_values) if self.preprocessor.special_values else [],
                "affected_features": 0,
                "total_replaced": 0,
                "details": {}
            }
            
            # 执行特殊值替换
            df = self.preprocessor.replace_special_values(
                df, 
                exclude_cols=list(exclude_from_features)
            )
            
            # 获取替换报告
            if self.preprocessor.special_value_report_:
                special_value_info["affected_features"] = len(self.preprocessor.special_value_report_)
                special_value_info["total_replaced"] = sum(self.preprocessor.special_value_report_.values())
                special_value_info["details"] = dict(self.preprocessor.special_value_report_)
                logger.info(f"[Scorecard] 特殊值替换完成: {special_value_info['affected_features']} 个特征受影响, 共替换 {special_value_info['total_replaced']} 条记录")
            
            results['special_value_info'] = special_value_info
            
            self._update_progress("data_loading", 50.0, "检查数据质量...")
            
            # Check missing values (在特殊值替换之后，确保缺失率统计包含特殊缺失值)
            missing_report = self.preprocessor.check_missing(df, exclude_cols=exclude_from_features)
            
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
                
                # 高缺失率特征（>30%），最多展示10个
                high_missing = missing_report[missing_report['missing_rate'] > 0.3].head(10)
                missing_summary["high_missing_features"] = [
                    {"variable": row['variable'], "missing_rate": round(row['missing_rate'], 4)}
                    for _, row in high_missing.iterrows()
                ]
            
            results['missing_summary'] = missing_summary
            
            # ========== var_filter: 数据质量筛选（参考scorecardpy库设计）==========
            # 行业惯例：数据质量筛选应在数据预处理阶段完成，而非WOE分箱阶段
            # 筛选条件：1) 缺失率 >= missing_limit  2) 同值率 >= identical_limit
            # 注意：IV阈值筛选在WOE分箱后的特征筛选阶段执行（需要先计算IV值）
            self._update_progress("data_loading", 55.0, "数据质量筛选(var_filter)...")
            
            missing_limit = self.woe_transformer.missing_limit  # 默认0.95
            identical_limit = 0.95  # 同值率阈值（与scorecardpy一致）
            
            var_filter_result: dict[str, Any] = {
                "input_features": len(feature_cols),
                "missing_limit": missing_limit,
                "identical_limit": identical_limit,
                "removed_features": [],
                "removed_by_missing": [],
                "removed_by_identical": [],
                "output_features": 0,
            }
            
            filtered_feature_cols = []
            for col in feature_cols:
                # 计算缺失率
                missing_rate = df[col].isna().mean()
                # 计算同值率（众数占比）
                value_counts = df[col].value_counts(normalize=True)
                identical_rate = value_counts.iloc[0] if len(value_counts) > 0 else 0.0
                
                if missing_rate >= missing_limit:
                    var_filter_result["removed_by_missing"].append({
                        "feature": col,
                        "missing_rate": round(float(missing_rate), 4),
                        "reason": f"缺失率{missing_rate:.1%} ≥ {missing_limit:.0%}"
                    })
                    var_filter_result["removed_features"].append(col)
                elif identical_rate >= identical_limit:
                    var_filter_result["removed_by_identical"].append({
                        "feature": col,
                        "identical_rate": round(float(identical_rate), 4),
                        "reason": f"同值率{identical_rate:.1%} ≥ {identical_limit:.0%}"
                    })
                    var_filter_result["removed_features"].append(col)
                else:
                    filtered_feature_cols.append(col)
            
            var_filter_result["output_features"] = len(filtered_feature_cols)
            
            # 日志输出
            removed_count = len(var_filter_result["removed_features"])
            if removed_count > 0:
                logger.info(f"[Scorecard] var_filter筛选: {var_filter_result['input_features']} → {var_filter_result['output_features']} 个特征")
                logger.info(f"  - 高缺失率移除: {len(var_filter_result['removed_by_missing'])} 个")
                logger.info(f"  - 高同值率移除: {len(var_filter_result['removed_by_identical'])} 个")
            else:
                logger.info(f"[Scorecard] var_filter筛选: 所有 {var_filter_result['input_features']} 个特征均通过数据质量检查")
            
            # 更新 feature_cols 为筛选后的特征列表
            feature_cols = filtered_feature_cols
            results['var_filter_result'] = var_filter_result
            
            # Detect outliers using IQR method
            self._update_progress("data_loading", 65.0, "检测异常值...")
            outlier_info = self.preprocessor.detect_outliers(
                df, feature_cols=feature_cols, method='iqr', threshold=1.5, exclude_cols=exclude_from_features
            )
            outlier_summary = self.preprocessor.get_outlier_summary(outlier_info)
            
            # Split train/test/oot (supports manual, time-based, or random split)
            train_df, test_df, oot_df = self.preprocessor.split_data(
                df, target_col, 
                sample_type_col=sample_type_col,
                time_col=time_col,
                oot_ratio=oot_ratio
            )
            self.train_data_ = train_df
            self.test_data_ = test_df
            self.oot_data_ = oot_df
            
            # Remove time_col from train/test/oot if present (not a feature)
            if time_col and time_col in train_df.columns:
                train_df = train_df.drop(columns=[time_col])
                test_df = test_df.drop(columns=[time_col])
                if oot_df is not None:
                    oot_df = oot_df.drop(columns=[time_col])
            
            # Build progress message
            outlier_count = sum(info.get('count', 0) for info in outlier_info.values())
            auto_excluded_count = len(auto_exclude_report['total_excluded'])
            progress_msg = f"数据加载完成，训练集{len(train_df)}行，测试集{len(test_df)}行"
            if oot_df is not None:
                progress_msg += f"，验证集(OOT){len(oot_df)}行"
            if auto_excluded_count > 0:
                progress_msg += f"，自动排除{auto_excluded_count}个非建模列"
            if outlier_count > 0:
                progress_msg += f"，检测到{outlier_count}个异常值"
            
            # 确定数据集划分方式（详细说明各数据集的划分逻辑）
            split_method = "random"
            split_method_desc = f"随机分层抽样({int((1 - self.preprocessor.test_ratio) * 100)}%训练/{int(self.preprocessor.test_ratio * 100)}%测试)"
            # 详细划分信息（分别说明各数据集的划分方式）
            split_details: dict[str, str] = {
                "train_test": f"随机分层抽样({int((1 - self.preprocessor.test_ratio) * 100)}%:{int(self.preprocessor.test_ratio * 100)}%)",
                "oot": "无",
            }
            
            if sample_type_col and sample_type_col in df.columns:
                split_method = "sample_type_col"
                split_method_desc = f"基于样本类型列({sample_type_col})"
                split_details = {
                    "train_test": f"基于样本类型列({sample_type_col})",
                    "oot": f"基于样本类型列({sample_type_col})",
                }
            elif time_col and time_col in df.columns and oot_ratio > 0:
                split_method = "time_based"
                # 更准确的描述：OOT按时间划分，Train/Test随机划分
                split_method_desc = f"OOT按时间划分({int(oot_ratio * 100)}%)，Train/Test随机分层"
                split_details = {
                    "train_test": f"从非OOT数据中随机分层抽样({int((1 - self.preprocessor.test_ratio) * 100)}%:{int(self.preprocessor.test_ratio * 100)}%)",
                    "oot": f"基于时间列({time_col})取最新{int(oot_ratio * 100)}%数据",
                }
            
            # ========== 评分卡任务特有：各数据集坏账率对比 ==========
            # 业务价值：判断数据集划分的随机性、识别样本偏差、评估OOT集的代表性
            # 如果训练集、测试集、OOT集的坏账率相近，说明数据集划分合理
            # 如果OOT集坏账率显著不同，提示可能存在时间漂移，模型需关注稳定性
            target_rates: dict[str, float | None] = {
                "overall": float(df[target_col].mean()) if target_col in df.columns else 0.0,
                "train": float(train_df[target_col].mean()) if target_col in train_df.columns else 0.0,
                "test": float(test_df[target_col].mean()) if target_col in test_df.columns else 0.0,
                "oot": float(oot_df[target_col].mean()) if oot_df is not None and target_col in oot_df.columns else None,
            }
            oot_rate_str = f"{target_rates['oot']:.4f}" if target_rates['oot'] is not None else 'N/A'
            logger.info(f"[Scorecard] 各数据集坏账率: overall={target_rates['overall']:.4f}, "
                       f"train={target_rates['train']:.4f}, test={target_rates['test']:.4f}, "
                       f"oot={oot_rate_str}")
            
            # ========== 评分卡任务特有：时间范围信息（可选）==========
            # 业务价值：评估OOT时间划分的合理性、了解模型训练数据的时间跨度
            # 仅当指定了 time_col 时展示
            time_range_info: dict[str, Any] | None = None
            if time_col and time_col in df.columns:
                def _get_time_range(data: pd.DataFrame, col: str) -> dict[str, str] | None:
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
                        logger.warning(f"[Scorecard] 解析时间列失败: {e}")
                        return None
                
                # 注意：此时 train_df/test_df 已经删除了 time_col（在前面的代码中）
                # 使用 self.train_data_/self.test_data_/self.oot_data_ 来获取时间范围
                # 这些是在删除 time_col 之前保存的原始数据
                time_range_info = {
                    "column": time_col,
                    "overall": _get_time_range(df, time_col),
                    "train": _get_time_range(self.train_data_, time_col),
                    "test": _get_time_range(self.test_data_, time_col),
                    "oot": _get_time_range(self.oot_data_, time_col) if self.oot_data_ is not None else None,
                }
                
                logger.info(f"[Scorecard] 时间范围信息: column={time_col}, overall={time_range_info.get('overall')}, "
                           f"train={time_range_info.get('train')}, test={time_range_info.get('test')}, "
                           f"oot={time_range_info.get('oot')}")
            
            # Build output preview for data_loading stage (with _full_stage_data for checkpoint)
            # 与规则挖掘任务保持一致的字段结构
            # 评分卡任务业务特点：OOT验证集是评估模型时间稳定性的重要指标，应始终展示
            data_loading_preview: dict[str, Any] = {
                "rows": len(df),
                "columns": len(df.columns),
                "feature_count": len(feature_cols),
                "missing_rate": missing_summary["avg_missing_rate"],  # 使用结构化摘要中的平均缺失率
                "target_rate": target_rates["overall"],  # 整体坏账率（保持兼容）
                # 评分卡任务特有：各数据集坏账率对比
                "target_rates": target_rates,
                # 评分卡任务特有：时间范围信息（仅当指定time_col时展示）
                "time_range_info": time_range_info,
                "split_info": {
                    "train": len(train_df),
                    "test": len(test_df),
                    # 评分卡任务特有：OOT验证集始终展示（即使为0，表示未指定划分OOT的可选列）
                    # OOT（Out-of-Time）验证集用于评估模型的时间稳定性，是评分卡开发的关键指标
                    "oot": len(oot_df) if oot_df is not None else 0,
                    "split_method": split_method,  # 划分方式标识
                    "split_method_desc": split_method_desc,  # 简要描述（用于前端展示）
                    "split_details": split_details,  # 详细划分信息（分别说明Train/Test和OOT的划分方式）
                    "test_ratio": self.preprocessor.test_ratio if split_method == "random" else None,
                    # 评分卡任务特有：各数据集坏账率（与样本数对应展示）
                    "train_target_rate": target_rates["train"],
                    "test_target_rate": target_rates["test"],
                    "oot_target_rate": target_rates["oot"],
                },
                "outlier_count": len([k for k, v in outlier_info.items() if v.get('count', 0) > 0]),
                "auto_exclude_report": auto_exclude_report,
                "missing_summary": missing_summary,  # 缺失率结构化摘要
                # 特殊值替换信息（与规则挖掘任务一致，行业惯例：特殊值在缺失率统计前替换）
                "special_value_info": special_value_info,
                # var_filter筛选结果（参考scorecardpy库设计）
                # 数据质量筛选应在数据预处理阶段完成，明确展示被移除的特征
                "var_filter_result": var_filter_result,
                # P2-6: 不平衡分析信息
                "imbalance_analysis": self._build_imbalance_analysis(target_rates["overall"]),
                # Phase 6: 添加完整阶段数据用于检查点保存
                "_full_stage_data": {
                    "train_df": train_df,
                    "test_df": test_df,
                    "oot_df": oot_df,
                    "feature_cols": feature_cols,
                    "results": dict(results),
                }
            }
            
            # Phase 28: 先更新 results 字典，确保检查点保存时包含完整数据（与规则挖掘任务一致）
            results['train_data'] = train_df
            results['test_data'] = test_df
            results['oot_data'] = oot_df
            results['missing_report'] = missing_report
            results['outlier_info'] = outlier_info
            results['outlier_summary'] = outlier_summary
            results['auto_exclude_report'] = auto_exclude_report
            results['feature_cols'] = feature_cols
            # 评分卡任务特有：保存各数据集坏账率和时间范围信息（用于检查点恢复、阶段继续等）
            results['target_rates'] = target_rates
            results['time_range_info'] = time_range_info
            
            # Phase 29: 更新 _full_stage_data 中的 results，确保包含本阶段添加的数据
            data_loading_preview["_full_stage_data"]["results"] = dict(results)
            
            self._update_progress("data_loading", 100.0, progress_msg, output_preview=data_loading_preview)
        
        # Check for stop request after Stage 1
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        
        # Stage 2: WOE Binning
        if should_skip_stage('woe_binning'):
            # 跳过已完成的阶段，使用恢复的output_preview
            logger.info("[Scorecard Pipeline] Skipping woe_binning stage (using cached data), restoring output_preview")
            if 'woe_binning' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['woe_binning'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('woe_binning', 100.0, 'WOE分箱已跳过（使用缓存）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('woe_binning', 100.0, 'WOE分箱已跳过（使用缓存）', output_preview=skip_preview)
                if bins is None or iv_table is None:
                    raise ValueError("缓存中没有 bins/iv_table，无法跳过 woe_binning 阶段")
        else:
            self._update_progress("woe_binning", 0.0, "开始WOE分箱...", code=self._get_stage_code("woe_binning"))
            
            try:
                # Create a sub-progress callback for WOE binning
                # 现在 current 直接是百分比值 (0-100)
                def woe_progress(step_name: str, current: int, total: int):
                    # current 现在是当前进度百分比，total 是总进度百分比（通常是100）
                    progress = current if total == 100 else (current / total) * 100 if total > 0 else 0
                    self._update_progress("woe_binning", progress, f"WOE分箱: {step_name}...")
                
                df_woe, bins, iv_table = self.woe_transformer.fit_transform(
                    train_df, target_col, feature_cols, progress_callback=woe_progress
                )
                self.bins_ = bins
                self.iv_table_ = iv_table
                
                # Build output preview for woe_binning stage (with _full_stage_data for checkpoint)
                # 方案1优化：展示所有变量IV值和分布，不做删除
                iv_distribution = {
                    "strong": int((iv_table['iv'] >= 0.1).sum()) if len(iv_table) > 0 else 0,
                    "medium_strong": int(((iv_table['iv'] >= 0.05) & (iv_table['iv'] < 0.1)).sum()) if len(iv_table) > 0 else 0,
                    "medium": int(((iv_table['iv'] >= 0.02) & (iv_table['iv'] < 0.05)).sum()) if len(iv_table) > 0 else 0,
                    "weak": int((iv_table['iv'] < 0.02).sum()) if len(iv_table) > 0 else 0,
                }
                low_iv_count = int(iv_table['low_iv'].sum()) if 'low_iv' in iv_table.columns and len(iv_table) > 0 else 0
                
                # 短期优化1：构建完整IV表（不只是前10个）
                # 短期优化2&3：添加分箱详情摘要和坏账率统计
                def _build_iv_table_entry(row: pd.Series, bins_dict: dict, mono_report: dict) -> dict:
                    """构建单个变量的IV表条目，包含分箱详情"""
                    var_name = row['variable']
                    entry = {
                        "feature": var_name,
                        "iv": float(row['iv']),
                        "monotonic": bool(mono_report.get(var_name, {}).get('original_monotonic', False)) if mono_report else False,
                        "low_iv": bool(row.get('low_iv', False)) if 'low_iv' in iv_table.columns else False,
                    }
                    
                    # 添加分箱详情摘要
                    if var_name in bins_dict:
                        bin_df = bins_dict[var_name]
                        entry["n_bins"] = len(bin_df)
                        
                        # 提取样本分布（兼容两种列名）
                        if 'total_count' in bin_df.columns:
                            entry["total_samples"] = int(bin_df['total_count'].sum())
                        elif 'count' in bin_df.columns:
                            entry["total_samples"] = int(bin_df['count'].sum())
                    
                    return entry
                
                # 构建完整IV表（按IV降序）
                iv_table_sorted = iv_table.sort_values('iv', ascending=False)
                full_iv_table = [
                    _build_iv_table_entry(row, bins, self.woe_transformer.monotonicity_report_)
                    for _, row in iv_table_sorted.iterrows()
                ] if len(iv_table) > 0 else []
                
                # 获取WOE分箱过程中过滤的特征（合并预先过滤和scorecardpy过滤）
                pre_filtered = getattr(self.woe_transformer, '_pre_filtered_features', [])
                scorecardpy_filtered = getattr(self.woe_transformer, '_scorecardpy_filtered_features', [])
                input_feature_count = getattr(self.woe_transformer, '_input_feature_count', len(feature_cols))
                
                # 合并所有过滤的特征
                all_filtered_features = []
                for f in pre_filtered:
                    all_filtered_features.append(f["feature"])
                all_filtered_features.extend(scorecardpy_filtered)
                
                total_filtered_count = len(all_filtered_features)
                
                # 调试日志：输出特征数变化
                logger.info(f"[WOE Preview] input_features={input_feature_count}, total_features={len(bins)}, "
                           f"pre_filtered={len(pre_filtered)}, scorecardpy_filtered={len(scorecardpy_filtered)}, "
                           f"total_filtered={total_filtered_count}")
                
                woe_binning_preview: dict[str, Any] = {
                    "total_features": len(bins),
                    "input_features": input_feature_count,  # 输入特征数（来自数据加载阶段）
                    "iv_range": {
                        "min": float(iv_table['iv'].min()) if len(iv_table) > 0 else 0.0,
                        "max": float(iv_table['iv'].max()) if len(iv_table) > 0 else 0.0,
                    },
                    # 方案1优化：添加IV分布信息
                    "iv_distribution": iv_distribution,
                    "iv_threshold": self.woe_transformer.iv_limit,
                    "low_iv_count": low_iv_count,
                    "note": f"共{low_iv_count}个变量IV<{self.woe_transformer.iv_limit}（已标记，将在特征筛选阶段处理）" if low_iv_count > 0 else "所有变量IV值均达标",
                    # WOE分箱过程中过滤的特征（预先过滤+scorecardpy过滤）
                    "woe_filtered": {
                        "count": total_filtered_count,
                        "features": all_filtered_features[:10] if len(all_filtered_features) > 10 else all_filtered_features,
                        "pre_filtered_count": len(pre_filtered),
                        "scorecardpy_filtered_count": len(scorecardpy_filtered),
                        "reason": "训练集上为常量列/全NaN/非数值/分箱失败",
                    } if total_filtered_count > 0 else None,
                    # 短期优化1：展示完整IV表（前端可分页展示）
                    "iv_table": full_iv_table,
                    # 保留前10个用于快速预览（兼容现有前端）
                    "iv_table_preview": full_iv_table[:10] if len(full_iv_table) > 10 else full_iv_table,
                    # Phase 6: 添加完整阶段数据用于检查点保存
                    "_full_stage_data": {
                        "train_df": train_df,
                        "test_df": test_df,
                        "oot_df": oot_df,
                        "df_woe": df_woe,
                        "bins": bins,
                        "iv_table": iv_table,
                        "feature_cols": feature_cols,
                        "results": dict(results),
                        # Phase 26: 保存WOE特征列表，确保重试特征选择阶段时使用相同的特征集
                        "woe_cols_for_selection": [c for c in df_woe.columns if c.endswith('_woe')],
                    }
                }
                
                # 保存 woe_cols_for_selection 供后续阶段使用
                woe_cols_for_selection = [c for c in df_woe.columns if c.endswith('_woe')]
                
                # Phase 28: 先更新 results 字典，确保检查点保存时包含完整数据（与规则挖掘任务一致）
                results['bins'] = bins
                results['iv_table'] = iv_table
                results['woe_train_data'] = df_woe
                results['monotonicity_report'] = self.woe_transformer.monotonicity_report_
                
                # Phase 29: 更新 _full_stage_data 中的 results，确保包含本阶段添加的数据
                woe_binning_preview["_full_stage_data"]["results"] = dict(results)
                
                self._update_progress("woe_binning", 100.0, f"WOE分箱完成，{len(bins)}个变量", output_preview=woe_binning_preview)
            except Exception as e:
                self._update_progress("woe_binning", 100.0, f"WOE分箱失败: {str(e)}")
                raise
        
        # Check for stop request after Stage 2
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        
        # Stage 3: Feature Selection
        if should_skip_stage('feature_selection'):
            # 跳过已完成的阶段，使用恢复的output_preview
            logger.info("[Scorecard Pipeline] Skipping feature_selection stage (using cached data), restoring output_preview")
            if 'feature_selection' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['feature_selection'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('feature_selection', 100.0, '特征筛选已跳过（使用缓存）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('feature_selection', 100.0, '特征筛选已跳过（使用缓存）', output_preview=skip_preview)
                if not selected_features:
                    raise ValueError("缓存中没有 selected_features，无法跳过 feature_selection 阶段")
        else:
            self._update_progress("feature_selection", 0.0, "开始特征筛选...", code=self._get_stage_code("feature_selection"))
            
            # Debug: Log iv_table structure before feature selection
            logger.info(f"[Feature Selection] iv_table type: {type(iv_table)}")
            if hasattr(iv_table, 'columns'):
                logger.info(f"[Feature Selection] iv_table columns: {list(iv_table.columns)}")
                logger.info(f"[Feature Selection] iv_table shape: {iv_table.shape}")
            else:
                logger.error(f"[Feature Selection] iv_table has no columns attribute, value: {iv_table}")
            
            # Get WOE column names
            # Phase 26: 如果有缓存的 woe_cols_for_selection，则使用缓存值，确保重试时结果一致
            if woe_cols_for_selection is not None:
                woe_cols = woe_cols_for_selection
                logger.info(f"[Feature Selection] Using cached woe_cols_for_selection: {len(woe_cols)} features")
            else:
                woe_cols = [c for c in df_woe.columns if c.endswith('_woe')]
                # 首次执行，保存 woe_cols 供后续使用
                woe_cols_for_selection = woe_cols.copy()
            
            # Add target column to df_woe for stepwise regression
            df_woe_with_target = df_woe.copy()
            df_woe_with_target[target_col] = train_df[target_col].values
            
            # 方案1：特征筛选阶段只执行IV/相关性/VIF筛选
            # 逐步回归/显著性检验/系数方向验证移至模型训练阶段执行
            selected_features, selection_detail = self.feature_selector.select_features(
                df_woe_with_target, iv_table, woe_cols,
                target_col=target_col,
                use_correlation=True,
                use_vif=True,
                use_stepwise=False,  # 方案1：不在特征筛选阶段执行逐步回归
                validate_coefficients=False  # 方案1：不在特征筛选阶段执行系数方向验证
            )
            self.selected_features_ = selected_features
            
            # Build progress message with details
            # 方案1：特征筛选阶段不再包含逐步回归信息
            progress_msg = f"特征筛选完成，保留{len(selected_features)}个特征（候选特征，逐步回归将在模型训练阶段执行）"
            
            # Build output preview for feature_selection stage (with _full_stage_data for checkpoint)
            # 方案1优化：添加IV分布信息，统一在特征筛选阶段展示筛选依据
            iv_distribution = {
                "strong": int((iv_table['iv'] >= 0.1).sum()) if len(iv_table) > 0 else 0,
                "medium_strong": int(((iv_table['iv'] >= 0.05) & (iv_table['iv'] < 0.1)).sum()) if len(iv_table) > 0 else 0,
                "medium": int(((iv_table['iv'] >= 0.02) & (iv_table['iv'] < 0.05)).sum()) if len(iv_table) > 0 else 0,
                "weak": int((iv_table['iv'] < 0.02).sum()) if len(iv_table) > 0 else 0,
            }
            
            # 方案1：特征筛选阶段只展示IV/相关性/VIF移除
            # 逐步回归/显著性检验/系数方向验证移至模型训练阶段
            removed_by_iv = selection_detail.get('removed_by_iv', [])
            removed_by_corr = selection_detail.get('removed_by_corr', [])
            removed_by_vif = selection_detail.get('removed_by_vif', [])
            
            # 移除原因统计：只包含特征筛选阶段的三类（IV/相关性/VIF）
            removed_reasons: dict[str, int] = {
                'IV筛选移除': len(removed_by_iv) if removed_by_iv else 0,
                '相关性移除': len(removed_by_corr) if removed_by_corr else 0,
                'VIF移除': len(removed_by_vif) if removed_by_vif else 0,
            }
            # 方案1说明：逐步回归/显著性检验/系数方向验证在模型训练阶段执行和展示
            
            # ========== 特征筛选展示优化 ==========
            # 1. 多步骤流程数据（展示每一步筛选后的特征数量）
            initial_count = len(woe_cols)
            after_iv_count = initial_count - len(removed_by_iv)
            after_corr_count = after_iv_count - len(removed_by_corr)
            after_vif_count = after_corr_count - len(removed_by_vif)
            
            selection_flow = [
                {"step": "初始", "count": initial_count, "removed": 0},
                {"step": "IV筛选", "count": after_iv_count, "removed": len(removed_by_iv)},
                {"step": "相关性筛选", "count": after_corr_count, "removed": len(removed_by_corr)},
                {"step": "VIF筛选", "count": after_vif_count, "removed": len(removed_by_vif)},
            ]
            
            # 2. 筛选阈值配置
            threshold_config = {
                "iv_lower": self.feature_selector.iv_lower,
                "iv_upper": self.feature_selector.iv_upper,
                "corr_threshold": self.feature_selector.corr_threshold,
                "vif_threshold": self.feature_selector.vif_threshold,
            }
            
            # 3. 完整特征明细表（用于CSV下载）
            # 包含：IV值、相关性(最大)、VIF、缺失率、分箱数、筛选状态、筛除原因
            corr_matrix = selection_detail.get('corr_matrix')
            vif_table = selection_detail.get('vif_table')
            all_features_detail = []
            
            # 创建特征集合用于判断筛选状态
            selected_set = set(selected_features)
            # 同时添加WOE名称版本到selected_set，便于匹配
            selected_woe_set = set(f"{f}_woe" for f in selected_features if not f.endswith('_woe'))
            selected_set = selected_set | selected_woe_set
            
            removed_by_iv_set = set(removed_by_iv)
            # removed_by_corr和removed_by_vif存储的是WOE名称，需要同时包含原始名
            removed_by_corr_set = set(removed_by_corr)
            removed_by_corr_original_set = set(f.replace('_woe', '') for f in removed_by_corr if f.endswith('_woe'))
            removed_by_corr_set = removed_by_corr_set | removed_by_corr_original_set
            
            removed_by_vif_set = set(removed_by_vif)
            removed_by_vif_original_set = set(f.replace('_woe', '') for f in removed_by_vif if f.endswith('_woe'))
            removed_by_vif_set = removed_by_vif_set | removed_by_vif_original_set
            
            # 方案1：特征筛选阶段不再构建后三项移除集合（逐步回归/显著性/系数验证）
            # 这些将在模型训练阶段执行和判断
            
            # 调试：打印集合内容（仅保留特征筛选阶段相关的）
            logger.info(f"[特征筛选调试] selected_features(原始): {selected_features}")
            logger.info(f"[特征筛选调试] selected_set(含WOE): {selected_set}")
            logger.info(f"[特征筛选调试] removed_by_iv: {removed_by_iv}")
            logger.info(f"[特征筛选调试] removed_by_corr: {removed_by_corr}")
            logger.info(f"[特征筛选调试] removed_by_corr_set(含原始名): {removed_by_corr_set}")
            logger.info(f"[特征筛选调试] removed_by_vif: {removed_by_vif}")
            logger.info(f"[特征筛选调试] removed_by_vif_set(含原始名): {removed_by_vif_set}")
            
            # 从iv_table构建特征明细
            iv_table_sorted = iv_table.sort_values('iv', ascending=False)
            for idx, row in iv_table_sorted.iterrows():
                var_name = row['variable']
                woe_name = f"{var_name}_woe"
                iv_value = float(row['iv'])
                
                # 计算最大相关系数
                max_corr = None
                corr_feature = None
                if corr_matrix is not None and woe_name in corr_matrix.columns:
                    corr_row = corr_matrix.loc[woe_name].drop(woe_name, errors='ignore')
                    if len(corr_row) > 0:
                        abs_corr = corr_row.abs()
                        max_idx = abs_corr.idxmax()
                        max_corr = float(corr_row[max_idx])
                        corr_feature = max_idx.replace('_woe', '') if max_idx else None
                
                # 获取VIF值
                vif_value = None
                if vif_table is not None and len(vif_table) > 0:
                    vif_row = vif_table[vif_table['feature'] == woe_name] if 'feature' in vif_table.columns else None
                    if vif_row is not None and len(vif_row) > 0:
                        vif_value = float(vif_row.iloc[0]['VIF'])  # 注意：列名是大写'VIF'
                
                # 获取分箱信息
                n_bins = None
                bad_rate_range = None
                bin_detail = []
                if bins and var_name in bins:
                    bin_df = bins[var_name]
                    if isinstance(bin_df, pd.DataFrame) and 'bin' in bin_df.columns:
                        n_bins = len(bin_df)
                        if 'badprob' in bin_df.columns:
                            bad_rates = bin_df['badprob'].dropna()
                            if len(bad_rates) > 0:
                                bad_rate_range = f"{bad_rates.min()*100:.1f}%-{bad_rates.max()*100:.1f}%"
                        # 分箱明细
                        for _, bin_row in bin_df.iterrows():
                            bin_entry = {
                                "bin": str(bin_row.get('bin', '')),
                                "count": int(bin_row.get('count', 0)) if pd.notna(bin_row.get('count')) else 0,
                                "bad_count": int(bin_row.get('bad', 0)) if pd.notna(bin_row.get('bad')) else 0,
                                "bad_rate": float(bin_row.get('badprob', 0)) if pd.notna(bin_row.get('badprob')) else 0,
                                "woe": float(bin_row.get('woe', 0)) if pd.notna(bin_row.get('woe')) else 0,
                            }
                            bin_detail.append(bin_entry)
                
                # 判断IV等级
                if iv_value >= 0.3:
                    iv_level = "极强"
                elif iv_value >= 0.1:
                    iv_level = "强"
                elif iv_value >= 0.05:
                    iv_level = "中强"
                elif iv_value >= 0.02:
                    iv_level = "中"
                else:
                    iv_level = "弱"
                
                # 方案1：特征筛选阶段只判断IV/相关性/VIF三类移除原因
                # 逐步回归/显著性/系数验证在模型训练阶段判断
                if woe_name in selected_set or var_name in selected_set:
                    status = "保留"
                    remove_reason = None
                elif woe_name in removed_by_iv_set or var_name in removed_by_iv_set:
                    status = "移除"
                    if iv_value < self.feature_selector.iv_lower:
                        remove_reason = f"IV<{self.feature_selector.iv_lower}"
                    elif iv_value > self.feature_selector.iv_upper:
                        remove_reason = f"IV>{self.feature_selector.iv_upper}"
                    else:
                        remove_reason = "IV筛选"
                elif woe_name in removed_by_corr_set or var_name in removed_by_corr_set:
                    status = "移除"
                    remove_reason = f"相关性>{self.feature_selector.corr_threshold}"
                elif woe_name in removed_by_vif_set or var_name in removed_by_vif_set:
                    status = "移除"
                    remove_reason = f"VIF>{self.feature_selector.vif_threshold}"
                else:
                    # 方案1：如果不在任何已知集合中，记录警告
                    logger.warning(f"特征 {var_name} 状态未知 - woe_name={woe_name}, "
                                   f"在selected_set={woe_name in selected_set or var_name in selected_set}, "
                                   f"在removed_by_iv_set={woe_name in removed_by_iv_set or var_name in removed_by_iv_set}, "
                                   f"在removed_by_corr_set={woe_name in removed_by_corr_set or var_name in removed_by_corr_set}, "
                                   f"在removed_by_vif_set={woe_name in removed_by_vif_set or var_name in removed_by_vif_set}")
                    logger.warning(f"  selected_set sample: {list(selected_set)[:5]}")
                    status = "未知"
                    remove_reason = None
                
                # 缺失率（从原始数据计算）
                missing_rate = None
                if var_name in train_df.columns:
                    missing_rate = float(train_df[var_name].isna().mean())
                
                feature_entry = {
                    "feature": var_name,
                    "iv": iv_value,
                    "iv_level": iv_level,
                    "max_corr": max_corr,
                    "corr_feature": corr_feature,
                    "vif": vif_value,
                    "missing_rate": missing_rate,
                    "n_bins": n_bins,
                    "bad_rate_range": bad_rate_range,
                    "status": status,
                    "remove_reason": remove_reason,
                    "bin_detail": bin_detail,  # 分箱明细（用于CSV下载）
                }
                all_features_detail.append(feature_entry)
            
            feature_selection_preview: dict[str, Any] = {
                "before_count": len(woe_cols),
                "after_count": len(selected_features),
                # 方案1优化：添加IV分布信息
                "iv_distribution": iv_distribution,
                "iv_threshold": {
                    "lower": self.feature_selector.iv_lower,
                    "upper": self.feature_selector.iv_upper,
                },
                "removed_reasons": removed_reasons,
                # 术语修正：改为"候选入模特征"
                "candidate_features": selected_features[:15] if len(selected_features) > 15 else selected_features,
                "selected_features": selected_features[:15] if len(selected_features) > 15 else selected_features,  # 保留旧字段兼容
                
                # ========== 新增展示优化字段 ==========
                # 多步骤流程数据
                "selection_flow": selection_flow,
                # 筛选阈值配置
                "threshold_config": threshold_config,
                # 完整特征明细（用于CSV下载）
                "all_features_detail": all_features_detail,
                
                # 方案B：coefficient_validation 移至 model_training 阶段展示
                # Phase 6: 添加完整阶段数据用于检查点保存
                "_full_stage_data": {
                    "train_df": train_df,
                    "test_df": test_df,
                    "oot_df": oot_df,
                    "df_woe": df_woe,
                    "bins": bins,
                    "iv_table": iv_table,
                    "feature_cols": feature_cols,
                    "selected_features": selected_features,
                    "results": dict(results),
                    # Phase 26: 保存WOE特征列表，确保后续阶段重试时使用相同的特征集
                    "woe_cols_for_selection": woe_cols_for_selection,
                }
            }
            
            # Phase 28: 先更新 results 字典，确保检查点保存时包含完整数据（与规则挖掘任务一致）
            results['selected_features'] = selected_features
            results['selection_detail'] = selection_detail
            
            # Phase 29: 更新 _full_stage_data 中的 results，确保包含本阶段添加的数据
            feature_selection_preview["_full_stage_data"]["results"] = dict(results)
            
            self._update_progress("feature_selection", 100.0, progress_msg, output_preview=feature_selection_preview)
        
        # Phase 20: 验证 selected_features 是否都在 bins_ 中存在
        # 这是防止缓存不一致导致后续阶段失败的关键检查
        if selected_features and self.bins_:
            bins_keys = set(self.bins_.keys())
            # 从 selected_features 提取原始特征名（去掉 _woe 后缀）
            selected_base_features = []
            for f in selected_features:
                base_name = f.replace('_woe', '') if f.endswith('_woe') else f
                selected_base_features.append(base_name)
            
            missing_in_bins = [f for f in selected_base_features if f not in bins_keys]
            
            if missing_in_bins:
                logger.warning(f"[Feature Selection] 发现 {len(missing_in_bins)} 个选中特征不在 bins_ 中: {missing_in_bins}")
                logger.warning(f"[Feature Selection] bins_ 中的特征: {list(bins_keys)}")
                
                # 过滤掉不在 bins_ 中的特征
                valid_selected_features = []
                for f in selected_features:
                    base_name = f.replace('_woe', '') if f.endswith('_woe') else f
                    if base_name in bins_keys:
                        valid_selected_features.append(f)
                    else:
                        logger.warning(f"[Feature Selection] 移除不在 bins_ 中的特征: {f}")
                
                if len(valid_selected_features) < 2:
                    raise ValueError(
                        f"过滤后有效特征不足。选中 {len(selected_features)} 个特征，"
                        f"但 {len(missing_in_bins)} 个不在 bins_ 中: {missing_in_bins}。"
                        f"bins_ 只有: {list(bins_keys)}。"
                        f"请重新执行 woe_binning 阶段以确保数据一致性。"
                    )
                
                logger.warning(f"[Feature Selection] 过滤后保留 {len(valid_selected_features)} 个有效特征: {valid_selected_features}")
                selected_features = valid_selected_features
                self.selected_features_ = selected_features
                results['selected_features'] = selected_features
        
        # Check for stop request after Stage 3
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        
        # Stage 4: Model Training
        if should_skip_stage('model_training'):
            # 跳过已完成的阶段，使用恢复的output_preview
            logger.info("[Scorecard Pipeline] Skipping model_training stage (using cached data), restoring output_preview")
            if 'model_training' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['model_training'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('model_training', 100.0, '模型训练已跳过（使用缓存）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('model_training', 100.0, '模型训练已跳过（使用缓存）', output_preview=skip_preview)
                if self.model_ is None:
                    raise ValueError("缓存中没有 model，无法跳过 model_training 阶段")
            
            # Phase 19: 验证并修复 woe_feature_cols_ 与模型系数的一致性
            if self.model_ is not None:
                model_n_features = self.model_.coef_.shape[1]
                current_woe_features = getattr(self, 'woe_feature_cols_', None)
                
                if not current_woe_features or len(current_woe_features) != model_n_features:
                    # 尝试从 selected_features 重建
                    if selected_features and len(selected_features) == model_n_features:
                        self.woe_feature_cols_ = [f"{f}_woe" if not f.endswith('_woe') else f for f in selected_features]
                        logger.warning(f"[Scorecard Pipeline] woe_feature_cols_ mismatch ({len(current_woe_features) if current_woe_features else 0} vs model {model_n_features}), rebuilt from selected_features")
                    else:
                        # 从 df_woe 的列名中提取 WOE 特征
                        available_woe_cols = [c for c in df_woe.columns if c.endswith('_woe')]
                        if self.bins_ and len(self.bins_) >= model_n_features:
                            # 使用 bins_ 的键顺序
                            ordered_features = []
                            for feat in self.bins_.keys():
                                woe_col = f"{feat}_woe"
                                if woe_col in available_woe_cols:
                                    ordered_features.append(woe_col)
                                    if len(ordered_features) == model_n_features:
                                        break
                            if len(ordered_features) == model_n_features:
                                self.woe_feature_cols_ = ordered_features
                                logger.warning(f"[Scorecard Pipeline] woe_feature_cols_ rebuilt from bins_ keys: {model_n_features} features")
                            else:
                                raise ValueError(
                                    f"无法重建 woe_feature_cols_。模型需要 {model_n_features} 个特征，"
                                    f"但只能从 bins_ 中找到 {len(ordered_features)} 个。"
                                )
                        else:
                            raise ValueError(
                                f"无法重建 woe_feature_cols_。模型需要 {model_n_features} 个特征，"
                                f"但 selected_features 有 {len(selected_features) if selected_features else 0} 个，"
                                f"bins_ 有 {len(self.bins_) if self.bins_ else 0} 个。"
                            )
                else:
                    logger.info(f"[Scorecard Pipeline] woe_feature_cols_ verified: {len(current_woe_features)} features match model")
        else:
            self._update_progress("model_training", 0.0, "开始模型训练...", code=self._get_stage_code("model_training"))
            
            if len(selected_features) == 0:
                self._update_progress("model_training", 100.0, "无可用特征，跳过模型训练")
                results['model'] = None
                results['coefficients'] = None
            else:
                # CRITICAL: Convert original feature names to WOE column names
                # selected_features contains original names like ['f73', 'f47', ...]
                # but we need to train on WOE columns like ['f73_woe', 'f47_woe', ...]
                woe_feature_cols = [f"{f}_woe" for f in selected_features]
                
                # Verify WOE columns exist
                missing_woe_cols = [c for c in woe_feature_cols if c not in df_woe.columns]
                if missing_woe_cols:
                    import logging
                    logging.getLogger(__name__).error(f"Missing WOE columns: {missing_woe_cols}")
                    raise ValueError(f"WOE columns not found: {missing_woe_cols}")
                
                X_train = df_woe[woe_feature_cols]
                y_train = train_df[target_col]
                
                # ========== 方案1：在模型训练阶段执行逐步回归/显著性检验/系数方向验证 ==========
                stepwise_result = None
                removed_by_stepwise = []
                coefficient_validation = None
                removed_by_coefficient = []
                
                if self.use_stepwise:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"[模型训练] 开始执行逐步回归，方向={self.stepwise_direction}, 显著性水平={self.significance_level}")
                    self._update_progress("model_training", 10.0, "执行逐步回归特征选择...")
                    
                    # 准备逐步回归的数据（需要包含目标列）
                    df_for_stepwise = df_woe[woe_feature_cols].copy()
                    df_for_stepwise[target_col] = y_train.values
                    
                    # 调用feature_selector的stepwise_selection方法
                    try:
                        woe_feature_cols_after_stepwise, stepwise_result = self.feature_selector.stepwise_selection(
                            df_for_stepwise, 
                            target_col,
                            woe_feature_cols,
                            direction=self.stepwise_direction,
                            significance_level=self.significance_level
                        )
                        
                        # 记录被逐步回归移除的特征
                        removed_by_stepwise = [f for f in woe_feature_cols if f not in woe_feature_cols_after_stepwise]
                        
                        logger.info(f"[模型训练] 逐步回归完成: {len(woe_feature_cols)} -> {len(woe_feature_cols_after_stepwise)} 特征")
                        logger.info(f"[模型训练] 逐步回归移除: {removed_by_stepwise}")
                        
                        # 更新特征列表
                        woe_feature_cols = woe_feature_cols_after_stepwise
                        selected_features = [f.replace('_woe', '') for f in woe_feature_cols]
                        self.selected_features_ = selected_features
                        X_train = df_woe[woe_feature_cols]
                        
                    except Exception as e:
                        logger.warning(f"[模型训练] 逐步回归失败: {e}，使用全部候选特征")
                        stepwise_result = {"error": str(e)}
                
                # Debug: Check WOE values in training data
                import logging
                logger = logging.getLogger(__name__)
                logger.info("=== Training Data WOE Check ===")
                for col in woe_feature_cols[:3]:
                    logger.info(f"Feature {col}: min={X_train[col].min():.4f}, max={X_train[col].max():.4f}, mean={X_train[col].mean():.4f}, nunique={X_train[col].nunique()}")
                
                # ========== B+方案：迭代验证循环 ==========
                # P2-6: 解析 imbalance_strategy 为实际的 class_weight
                resolved_class_weight = None
                if self.imbalance_strategy == 'class_weight':
                    resolved_class_weight = 'balanced'
                elif self.imbalance_strategy == 'auto':
                    bad_rate = float(y_train.mean()) if len(y_train) > 0 else 0.0
                    if bad_rate < 0.1:
                        resolved_class_weight = 'balanced'
                        logger.info(f"[P2-6] auto策略: bad_rate={bad_rate:.4f} < 10%, 启用 class_weight='balanced'")
                    else:
                        logger.info(f"[P2-6] auto策略: bad_rate={bad_rate:.4f} >= 10%, 不处理")
                
                # 迭代训练模型，每次检查显著性和系数方向，直到所有变量都通过验证或达到最大迭代次数
                post_validation_log: list[dict[str, Any]] = []  # 记录每次迭代的验证结果
                iteration = 0
                validation_converged = False
                
                while iteration < self.max_validation_iterations:
                    iteration += 1
                    logger.info(f"[模型训练] ===== 迭代验证 第{iteration}轮 =====")
                    self._update_progress("model_training", 30.0 + iteration * 5, f"迭代验证第{iteration}轮...")
                    
                    # 训练模型
                    model = StatisticalLogisticRegression(
                        calculate_stats=True,
                        penalty=None,  # No regularization for accurate statistics
                        C=1e10,
                        solver='lbfgs',
                        max_iter=1000,
                        fit_intercept=True,
                        random_state=self.random_state,
                        class_weight=resolved_class_weight  # P2-6
                    )
                    model.fit(X_train, y_train)
                    
                    # 获取模型统计信息
                    model_statistics = None
                    try:
                        model_statistics = model.summary()
                    except Exception as e:
                        logger.warning(f"Failed to get model statistics: {e}")
                    
                    # 获取p值和系数
                    pvalue_dict: dict[str, float] = {}
                    coef_dict: dict[str, float] = {}
                    
                    if model_statistics and 'summary' in model_statistics:
                        for feat_info in model_statistics['summary']:
                            feat_woe = feat_info.get('feature', '')
                            feat_name = feat_woe.replace('_woe', '')
                            if 'p_value' in feat_info:
                                pvalue_dict[feat_name] = feat_info['p_value']
                    
                    for feat_woe, coef in zip(woe_feature_cols, model.coef_[0]):
                        feat_name = feat_woe.replace('_woe', '')
                        coef_dict[feat_name] = float(coef)
                    
                    # 检查显著性（B+方案：根据 significance_mode 决定处理方式）
                    insignificant_features: list[str] = []
                    significance_warnings: list[str] = []
                    
                    if self.significance_mode != 'skip':
                        for feat, pval in pvalue_dict.items():
                            if pval is not None and pval > self.significance_level:
                                insignificant_features.append(feat)
                                significance_warnings.append(
                                    f"特征 {feat} p值={pval:.4f} > {self.significance_level}，不显著"
                                )
                    
                    # 检查系数方向（B+方案：根据 coefficient_direction_mode 决定处理方式）
                    invalid_direction_features: list[str] = []
                    direction_warnings: list[str] = []
                    
                    if self.coefficient_direction_mode != 'skip':
                        for feat, coef in coef_dict.items():
                            if coef < 0:
                                invalid_direction_features.append(feat)
                                direction_warnings.append(
                                    f"特征 {feat} 系数为负 ({coef:.4f})，可能与预期方向相反"
                                )
                    
                    # 记录本轮验证结果
                    iteration_log = {
                        'iteration': iteration,
                        'feature_count': len(woe_feature_cols),
                        'features': [f.replace('_woe', '') for f in woe_feature_cols],
                        'pvalues': pvalue_dict,
                        'coefficients': coef_dict,
                        'insignificant': insignificant_features,
                        'invalid_direction': invalid_direction_features,
                        'significance_warnings': significance_warnings,
                        'direction_warnings': direction_warnings,
                        'removed_this_iteration': []
                    }
                    
                    # 决定是否需要移除特征并重新训练
                    features_to_remove: list[str] = []
                    removal_reasons: list[str] = []
                    
                    # 显著性检验移除
                    if self.significance_mode == 'remove' and insignificant_features:
                        # 选择p值最大的特征移除（每次只移除一个，保证稳定性）
                        worst_feature = max(insignificant_features, key=lambda f: pvalue_dict.get(f, 0))
                        features_to_remove.append(worst_feature)
                        removal_reasons.append(f"显著性检验失败 (p={pvalue_dict.get(worst_feature, 0):.4f})")
                        logger.info(f"[模型训练] 移除不显著特征: {worst_feature} (p={pvalue_dict.get(worst_feature, 0):.4f})")
                    
                    # 系数方向检验移除（如果没有因显著性移除的特征）
                    if self.coefficient_direction_mode == 'remove' and invalid_direction_features and not features_to_remove:
                        # 选择系数最负的特征移除（每次只移除一个）
                        worst_feature = min(invalid_direction_features, key=lambda f: coef_dict.get(f, 0))
                        features_to_remove.append(worst_feature)
                        removal_reasons.append(f"系数方向异常 (coef={coef_dict.get(worst_feature, 0):.4f})")
                        logger.info(f"[模型训练] 移除系数方向异常特征: {worst_feature} (coef={coef_dict.get(worst_feature, 0):.4f})")
                    
                    iteration_log['removed_this_iteration'] = [
                        {'feature': f, 'reason': r} for f, r in zip(features_to_remove, removal_reasons)
                    ]
                    post_validation_log.append(iteration_log)
                    
                    # 如果没有需要移除的特征，验证收敛
                    if not features_to_remove:
                        validation_converged = True
                        logger.info(f"[模型训练] 迭代验证收敛，共{iteration}轮")
                        break
                    
                    # 移除特征并更新训练数据
                    removed_woe_cols = [f"{f}_woe" for f in features_to_remove]
                    woe_feature_cols = [f for f in woe_feature_cols if f not in removed_woe_cols]
                    selected_features = [f.replace('_woe', '') for f in woe_feature_cols]
                    
                    if len(woe_feature_cols) == 0:
                        logger.error("[模型训练] 迭代验证移除了所有特征！")
                        raise ValueError("迭代验证移除了所有特征，请检查数据质量或调整验证参数")
                    
                    X_train = df_woe[woe_feature_cols]
                
                # 迭代结束后的最终模型
                self.model_ = model
                self.woe_feature_cols_ = woe_feature_cols
                self.selected_features_ = selected_features
                
                # 获取最终模型统计信息
                try:
                    model_statistics = model.summary()
                    results['model_statistics'] = model_statistics
                except Exception as e:
                    logger.warning(f"Failed to get model statistics: {e}")
                    results['model_statistics'] = None
                
                # Get coefficients with statistical information
                coef_df = pd.DataFrame({
                    'feature': woe_feature_cols,
                    'coefficient': model.coef_[0]
                })
                coef_df['intercept'] = model.intercept_[0]
                
                # Build output preview for model_training stage
                # B+方案：包含迭代验证结果
                model_training_preview: dict[str, Any] = {
                    "intercept": float(model.intercept_[0]),
                    "coefficients": [
                        {
                            "feature": row['feature'].replace('_woe', ''),
                            "coefficient": float(row['coefficient']),
                            "pvalue": None  # Will be populated from model_statistics
                        }
                        for _, row in coef_df.head(10).iterrows()
                    ],
                    # B+方案：配置信息
                    "config": {
                        "use_stepwise": self.use_stepwise,
                        "stepwise_direction": self.stepwise_direction,
                        "significance_level": self.significance_level,
                        "significance_mode": self.significance_mode,
                        "coefficient_direction_mode": self.coefficient_direction_mode,
                        "max_validation_iterations": self.max_validation_iterations
                    },
                    # B+方案：迭代验证日志
                    "post_validation": {
                        "converged": validation_converged,
                        "total_iterations": iteration,
                        "final_feature_count": len(woe_feature_cols),
                        "iterations": post_validation_log
                    },
                    # B+方案：所有入模特征列表
                    "all_coefficients": [
                        {
                            "feature": feat.replace('_woe', ''),
                            "coefficient": float(coef)
                        }
                        for feat, coef in zip(woe_feature_cols, model.coef_[0])
                    ],
                    # Phase 6: 添加完整阶段数据用于检查点保存
                    "_full_stage_data": {
                        "train_df": train_df,
                        "test_df": test_df,
                        "oot_df": oot_df,
                        "df_woe": df_woe,
                        "bins": bins,
                        "iv_table": iv_table,
                        "feature_cols": feature_cols,
                        "selected_features": selected_features,
                        "model": model,
                        "woe_feature_cols": woe_feature_cols,
                        "results": dict(results),
                    }
                }
                
                # 方案1：添加本阶段执行的逐步回归结果
                if self.use_stepwise and stepwise_result:
                    # 获取入模特征的最终p值
                    final_pvalues = {}
                    if model_statistics and 'summary' in model_statistics:
                        for feat_info in model_statistics['summary']:
                            feat_name = feat_info.get('feature', '').replace('_woe', '')
                            if 'p_value' in feat_info:
                                final_pvalues[feat_name] = feat_info['p_value']
                    
                    model_training_preview['stepwise_result'] = {
                        'direction': self.stepwise_direction,
                        'significance_level': self.significance_level,
                        'steps': stepwise_result.get('steps', []) if isinstance(stepwise_result, dict) else [],
                        'final_pvalues': final_pvalues,
                        'removed_features': [f.replace('_woe', '') for f in removed_by_stepwise],
                        'before_count': len(selected_features) + len(removed_by_stepwise),
                        'after_count': len(selected_features)
                    }
                
                # B+方案：兼容旧的 coefficient_validation 字段（供前端使用）
                if self.coefficient_direction_mode != 'skip':
                    final_coef_dict = {
                        feat.replace('_woe', ''): float(coef)
                        for feat, coef in zip(woe_feature_cols, model.coef_[0])
                    }
                    valid_direction = [f for f, c in final_coef_dict.items() if c >= 0]
                    invalid_direction = [f for f, c in final_coef_dict.items() if c < 0]
                    
                    # 统计所有被移除的系数方向异常特征
                    all_removed_by_direction = []
                    for log in post_validation_log:
                        for removed in log.get('removed_this_iteration', []):
                            if '系数方向异常' in removed.get('reason', ''):
                                all_removed_by_direction.append(removed['feature'])
                    
                    model_training_preview['coefficient_validation'] = {
                        "mode": self.coefficient_direction_mode,
                        "valid_direction": valid_direction,
                        "invalid_direction": invalid_direction,
                        "warnings": [f"特征 {f} 系数为负 ({final_coef_dict[f]:.4f})" for f in invalid_direction],
                        "coefficients": final_coef_dict,
                        "removed_features": all_removed_by_direction
                    }
                
                # Enhance with statistical info if available
                if model_statistics and 'summary' in model_statistics:
                    stats_summary = model_statistics['summary']
                    # Create a lookup dict for statistical info (p-value, std_err, z, ci)
                    stats_lookup = {
                        item['feature']: {
                            'p_value': item.get('p_value'),
                            'std_err': item.get('std_err'),
                            'z': item.get('z'),  # Z值统计
                            'ci_lower': item.get('ci_lower'),
                            'ci_upper': item.get('ci_upper')
                        }
                        for item in stats_summary
                    }
                    # Update coefficients with statistical info
                    for coef_item in model_training_preview['coefficients']:
                        woe_feature = coef_item['feature'] + '_woe'
                        stats = stats_lookup.get(woe_feature, {})
                        coef_item['pvalue'] = stats.get('p_value')
                        coef_item['std_err'] = stats.get('std_err')
                        coef_item['z'] = stats.get('z')  # Z值
                        coef_item['ci_lower'] = stats.get('ci_lower')
                        coef_item['ci_upper'] = stats.get('ci_upper')
                    
                    # Update all_coefficients with statistical info
                    for coef_item in model_training_preview['all_coefficients']:
                        woe_feature = coef_item['feature'] + '_woe'
                        stats = stats_lookup.get(woe_feature, {})
                        coef_item['pvalue'] = stats.get('p_value')
                        coef_item['std_err'] = stats.get('std_err')
                        coef_item['z'] = stats.get('z')  # Z值
                        coef_item['ci_lower'] = stats.get('ci_lower')
                        coef_item['ci_upper'] = stats.get('ci_upper')
                    
                    # Add model fit statistics to preview
                    # 2026-02-11: 添加似然比检验指标(lr_stat, lr_pvalue)
                    model_training_preview['model_fit'] = {
                        'n_observations': model_statistics.get('n_observations'),
                        'pseudo_r2': model_statistics.get('pseudo_r2'),
                        'log_likelihood': model_statistics.get('log_likelihood'),
                        'aic': model_statistics.get('aic'),
                        'bic': model_statistics.get('bic'),
                        'lr_stat': model_statistics.get('lr_stat'),
                        'lr_pvalue': model_statistics.get('lr_pvalue')
                    }
                
                # Phase 28: 先更新 results 字典，确保检查点保存时包含完整数据（与规则挖掘任务一致）
                results['model'] = model
                results['coefficients'] = coef_df
                
                # Phase 29: 更新 _full_stage_data 中的 results，确保包含本阶段添加的数据
                model_training_preview["_full_stage_data"]["results"] = dict(results)
                
                self._update_progress("model_training", 100.0, "模型训练完成", output_preview=model_training_preview)
        
        # Check for stop request after Stage 4
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        
        # Stage 5: Score Scaling
        if should_skip_stage('score_scaling'):
            logger.info("[Scorecard Pipeline] Skipping score_scaling stage (using cached data)")
            
            # Phase 19: 验证 scorecard_ 与模型系数的一致性
            # 当 model_training 阶段被跳过时，scorecard_ 可能与实际模型不一致
            scorecard_needs_rebuild = False
            if self.scorecard_ is not None and self.model_ is not None:
                model_n_features = self.model_.coef_.shape[1]
                # scorecard_ 包含 basepoints + 各变量，所以变量数 = len(scorecard_) - 1
                scorecard_n_features = len(self.scorecard_) - 1 if 'basepoints' in self.scorecard_ else len(self.scorecard_)
                if scorecard_n_features != model_n_features:
                    logger.warning(f"[Score Scaling] Cached scorecard has {scorecard_n_features} features, but model has {model_n_features}. Rebuilding scorecard...")
                    scorecard_needs_rebuild = True
            
            if scorecard_needs_rebuild:
                # 重新生成评分卡
                logger.info("[Score Scaling] Rebuilding scorecard due to feature count mismatch")
                woe_features = getattr(self, 'woe_feature_cols_', None)
                if not woe_features:
                    woe_features = [f"{f}_woe" if not f.endswith('_woe') else f for f in selected_features]
                    self.woe_feature_cols_ = woe_features
                
                scorecard = self._generate_scorecard_custom(
                    self.bins_,
                    self.model_,
                    woe_features,
                    points0=self.base_score,
                    odds0=1/self.base_odds,
                    pdo=self.pdo,
                    digits=2
                )
                self.scorecard_ = scorecard
                
                # Phase 29: 重建时也计算评分范围和变量得分详情
                feature_vars = [k for k in scorecard.keys() if k != 'basepoints']
                theoretical_min_score = 0.0
                theoretical_max_score = 0.0
                variable_score_details = []
                
                for var_name, card_df in scorecard.items():
                    if isinstance(card_df, pd.DataFrame) and 'points' in card_df.columns:
                        points = card_df['points'].values
                        min_pts = float(np.min(points))
                        max_pts = float(np.max(points))
                        theoretical_min_score += min_pts
                        theoretical_max_score += max_pts
                        
                        if var_name != 'basepoints':
                            variable_score_details.append({
                                "variable": var_name,
                                "bins": len(card_df),
                                "min_score": round(min_pts, 2),
                                "max_score": round(max_pts, 2),
                                "score_range": round(max_pts - min_pts, 2),
                                "bin_details": [
                                    {"bin": _format_bin_interval(str(row.get('bin', ''))), "points": round(float(row.get('points', 0)), 2)}
                                    for _, row in card_df.iterrows()
                                ] if len(card_df) <= 20 else None
                            })
                
                # Phase 30: 重建场景也生成完整评分卡CSV
                full_scorecard_csv_rebuild = []
                try:
                    model_coefs = {}
                    if self.model_ is not None:
                        woe_features = getattr(self, 'woe_feature_cols_', [])
                        for i, woe_feat in enumerate(woe_features):
                            raw_feat = woe_feat.replace('_woe', '') if woe_feat.endswith('_woe') else woe_feat
                            model_coefs[raw_feat] = round(float(self.model_.coef_[0][i]), 4)
                    
                    iv_lookup = {}
                    if iv_table is not None and len(iv_table) > 0:
                        for _, row in iv_table.iterrows():
                            iv_lookup[row['variable']] = round(float(row['iv']), 4)
                    
                    if 'basepoints' in scorecard:
                        bp_df = scorecard['basepoints']
                        if isinstance(bp_df, pd.DataFrame) and len(bp_df) > 0:
                            bp_points = round(float(bp_df['points'].iloc[0]), 2) if 'points' in bp_df.columns else 0
                            full_scorecard_csv_rebuild.append({
                                "variable": "常数项", "total_iv": round(float(self.model_.intercept_[0]), 4) if self.model_ else 0,
                                "cof": "", "index": 0, "bin": "", "count": "", "count_distr": "",
                                "good": "", "bad": "", "badprob": "", "woe": "", "score": bp_points
                            })
                    
                    for var_name in feature_vars:
                        if var_name not in scorecard:
                            continue
                        card_df = scorecard[var_name]
                        bin_df = self.bins_.get(var_name) if self.bins_ else None
                        var_iv = iv_lookup.get(var_name, 0)
                        var_cof = model_coefs.get(var_name, 0)
                        
                        for idx, (_, card_row) in enumerate(card_df.iterrows()):
                            bin_str = str(card_row.get('bin', ''))
                            pts = round(float(card_row.get('points', 0)), 2) if pd.notna(card_row.get('points')) else 0
                            count, count_distr, good_count, bad_count, badprob, woe = 0, 0, 0, 0, 0, 0
                            
                            if bin_df is not None and isinstance(bin_df, pd.DataFrame):
                                matched = bin_df[bin_df['bin'].astype(str) == bin_str]
                                if len(matched) > 0:
                                    br = matched.iloc[0]
                                    count = int(br.get('count', 0)) if pd.notna(br.get('count')) else 0
                                    total = int(bin_df['count'].sum()) if 'count' in bin_df.columns else 1
                                    count_distr = round(count / total * 100, 2) if total > 0 else 0
                                    good_count = int(br.get('good', 0)) if pd.notna(br.get('good')) else 0
                                    bad_count = int(br.get('bad', 0)) if pd.notna(br.get('bad')) else 0
                                    badprob = round(float(br.get('badprob', 0)) * 100, 2) if pd.notna(br.get('badprob')) else 0
                                    woe = round(float(br.get('woe', 0)), 4) if pd.notna(br.get('woe')) else 0
                            
                            full_scorecard_csv_rebuild.append({
                                "variable": var_name, "total_iv": var_iv if idx == 0 else "",
                                "cof": var_cof if idx == 0 else "", "index": idx, "bin": _format_bin_interval(bin_str),
                                "count": count, "count_distr": f"{count_distr}%", "good": good_count,
                                "bad": bad_count, "badprob": f"{badprob}%", "woe": woe, "score": pts
                            })
                except Exception as e:
                    logger.warning(f"Failed to generate full scorecard CSV (rebuild): {e}")
                
                # 更新 output_preview
                score_scaling_preview: dict[str, Any] = {
                    "base_score": self.base_score,
                    "base_odds": self.base_odds,
                    "pdo": self.pdo,
                    "num_variables": len(feature_vars),
                    "theoretical_score_range": {
                        "min": round(theoretical_min_score, 2),
                        "max": round(theoretical_max_score, 2),
                    },
                    "scorecard_preview": variable_score_details,
                    "full_scorecard_csv": full_scorecard_csv_rebuild,  # Phase 30
                    "rebuilt": True,
                    "rebuild_reason": f"特征数不一致（缓存{scorecard_n_features}个 vs 模型{model_n_features}个）",
                    "_skip_expert_pause": True,
                }
                self._update_progress('score_scaling', 100.0, f'评分刻度转换已重建（{len(scorecard)-1}个变量）', output_preview=score_scaling_preview)
                results['scorecard'] = scorecard
            else:
                if 'score_scaling' in restored_output_previews:
                    # 使用恢复的output_preview，只添加跳过标记
                    restored_preview = restored_output_previews['score_scaling'].copy()
                    restored_preview['_skip_expert_pause'] = True
                    restored_preview['_skipped_during_retry'] = True
                    restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                    self._update_progress('score_scaling', 100.0, '评分刻度转换已跳过（使用缓存）', output_preview=restored_preview)
                else:
                    # 没有恢复的output_preview，使用简单的skip_preview
                    skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True, "_skipped_during_retry": True}
                    self._update_progress('score_scaling', 100.0, '评分刻度转换已跳过（使用缓存）', output_preview=skip_preview)
                if self.scorecard_ is None:
                    raise ValueError("缓存中没有 scorecard，无法跳过 score_scaling 阶段")
        else:
            self._update_progress("score_scaling", 0.0, "开始评分刻度转换...", code=self._get_stage_code("score_scaling"))
            
            if self.model_ is not None and self.bins_ is not None:
                try:
                    import logging
                    logger = logging.getLogger(__name__)
                    
                    # Debug: Check bins format before calling scorecard
                    logger.info("=== Bins Format Check ===")
                    logger.info(f"bins type: {type(self.bins_)}")
                    logger.info(f"bins keys: {list(self.bins_.keys())[:5]}")
                    for var_name, bin_df in list(self.bins_.items())[:2]:
                        logger.info(f"Variable '{var_name}' bin_df columns: {list(bin_df.columns)}")
                        logger.info(f"Variable '{var_name}' bin_df:\n{bin_df.to_string()}")
                    
                    # Use WOE feature names from model training
                    # Phase 18: 确保 woe_features 总是有 _woe 后缀
                    # 如果 woe_feature_cols_ 未设置或为空，从 selected_features 重新构建
                    woe_features = getattr(self, 'woe_feature_cols_', None)
                    if not woe_features:
                        # 从 selected_features 构建 WOE 特征名
                        woe_features = [f"{f}_woe" if not f.endswith('_woe') else f for f in selected_features]
                        logger.warning(f"[Scorecard] woe_feature_cols_ not set, rebuilding from selected_features: {len(woe_features)} features")
                        self.woe_feature_cols_ = woe_features
                    elif not all(f.endswith('_woe') for f in woe_features):
                        # 如果 woe_features 没有 _woe 后缀（错误地使用了 selected_features），修复它
                        woe_features = [f"{f}_woe" if not f.endswith('_woe') else f for f in woe_features]
                        logger.warning(f"[Scorecard] woe_features missing _woe suffix, fixed: {len(woe_features)} features")
                        self.woe_feature_cols_ = woe_features
                    logger.info(f"woe_features (first 5): {woe_features[:5]}")
                    logger.info(f"Model coef shape: {self.model_.coef_.shape}")
                    logger.info(f"Model coef values: {self.model_.coef_[0]}")
                    
                    # Check if features have _woe suffix
                    logger.info(f"woe_features have _woe suffix: {all(f.endswith('_woe') for f in woe_features)}")
                    
                    # Original features for bins lookup (strip _woe suffix)
                    original_features = [f.replace('_woe', '') for f in woe_features]
                    logger.info(f"original_features (first 5): {original_features[:5]}")
                    
                    # Check if original features exist in bins
                    missing_in_bins = [f for f in original_features if f not in self.bins_]
                    logger.info(f"Features missing in bins: {missing_in_bins}")
                    
                    # Use custom scorecard generation to fix precision bug
                    # Pass WOE feature names (with _woe suffix) to match model coefficients
                    scorecard = self._generate_scorecard_custom(
                        self.bins_,
                        self.model_,
                        woe_features,  # Use WOE feature names
                        points0=self.base_score,
                        odds0=1/self.base_odds,  # odds0 = P(bad)/P(good) = 1/base_odds (base_odds is good:bad ratio)
                        pdo=self.pdo,
                        digits=2
                    )
                    self.scorecard_ = scorecard
                    
                    # Debug: Check scorecard output
                    logger.info("=== Scorecard Output ===")
                    for var_name, card_df in list(scorecard.items())[:3]:
                        logger.info(f"Card '{var_name}':\n{card_df}")
                    
                    # Create ScoreTransformer for score ↔ probability conversion (new feature)
                    # Calculate bad_rate from training data for accurate scale parameters
                    train_bad_rate = y_train.mean() if 'y_train' in dir() else 0.15
                    score_transformer = ScoreTransformer(
                        base_score=self.base_score,
                        pdo=self.pdo,
                        rate=2,  # Standard: odds double for PDO points
                        bad_rate=float(train_bad_rate),
                        down_lmt=300,
                        up_lmt=850
                    )
                    score_transformer.fit()
                    self.score_transformer_ = score_transformer
                    
                    # Get score scale info for results
                    score_scale = score_transformer.get_scale_info()
                    results['score_scale'] = score_scale
                    
                    # Build output preview for score_scaling stage (enhanced with scale info, with _full_stage_data)
                    # Phase 16: num_variables 不包含 basepoints，只计算实际特征变量数
                    feature_vars = [k for k in scorecard.keys() if k != 'basepoints']
                    
                    # Phase 29: 计算评分范围和变量得分详情
                    # 计算理论评分范围（基于评分卡各变量得分的最小/最大值之和）
                    theoretical_min_score = 0.0
                    theoretical_max_score = 0.0
                    variable_score_details = []
                    
                    for var_name, card_df in scorecard.items():
                        if isinstance(card_df, pd.DataFrame) and 'points' in card_df.columns:
                            points = card_df['points'].values
                            min_pts = float(np.min(points))
                            max_pts = float(np.max(points))
                            theoretical_min_score += min_pts
                            theoretical_max_score += max_pts
                            
                            # 收集变量得分详情（排除basepoints）
                            if var_name != 'basepoints':
                                variable_score_details.append({
                                    "variable": var_name,
                                    "bins": len(card_df),
                                    "min_score": round(min_pts, 2),
                                    "max_score": round(max_pts, 2),
                                    "score_range": round(max_pts - min_pts, 2),
                                    # 包含完整分箱详情供前端展开
                                    "bin_details": [
                                        {
                                            "bin": _format_bin_interval(str(row.get('bin', ''))),
                                            "points": round(float(row.get('points', 0)), 2)
                                        }
                                        for _, row in card_df.iterrows()
                                    ] if len(card_df) <= 20 else None  # 分箱数过多时不传详情
                                })
                    
                    # 计算各数据集的评分分布统计（用于前端展示）
                    def _calc_score_stats(df: pd.DataFrame | None, scorecard: dict) -> dict | None:
                        """计算单个数据集的评分分布统计"""
                        if df is None or scorecard is None:
                            return None
                        try:
                            scores_df = sc.scorecard_ply(df, scorecard, only_total_score=True)
                            scores_arr = scores_df['score'].values
                            return {
                                "min": round(float(np.min(scores_arr)), 2),
                                "max": round(float(np.max(scores_arr)), 2),
                                "mean": round(float(np.mean(scores_arr)), 2),
                                "std": round(float(np.std(scores_arr)), 2),
                                "median": round(float(np.median(scores_arr)), 2),
                                "q25": round(float(np.percentile(scores_arr, 25)), 2),
                                "q75": round(float(np.percentile(scores_arr, 75)), 2),
                            }
                        except Exception as e:
                            logger.warning(f"Failed to calculate score stats: {e}")
                            return None
                    
                    # 计算各数据集评分分布
                    # 使用局部变量 train_df/test_df/oot_df（此时self._train_df等尚未设置，在model_evaluation阶段才会设置）
                    train_score_stats = _calc_score_stats(train_df, self.scorecard_)
                    test_score_stats = _calc_score_stats(test_df, self.scorecard_)
                    oot_score_stats = _calc_score_stats(oot_df, self.scorecard_)
                    
                    # 兼容旧字段：actual_score_stats 优先使用训练集（保持向后兼容）
                    actual_score_stats = train_score_stats
                    
                    # Phase 30: 生成完整评分卡CSV数据（行业标准格式）
                    # 格式参考: variable, total_iv, cof, index, bin, count, count_distr, good, bad, badprob, woe, score
                    full_scorecard_csv = []
                    try:
                        # 获取模型系数用于cof列
                        model_coefs = {}
                        if self.model_ is not None:
                            woe_features = getattr(self, 'woe_feature_cols_', [])
                            for i, woe_feat in enumerate(woe_features):
                                raw_feat = woe_feat.replace('_woe', '') if woe_feat.endswith('_woe') else woe_feat
                                model_coefs[raw_feat] = round(float(self.model_.coef_[0][i]), 4)
                        
                        # 获取IV表用于total_iv列
                        iv_lookup = {}
                        if iv_table is not None and len(iv_table) > 0:
                            for _, row in iv_table.iterrows():
                                iv_lookup[row['variable']] = round(float(row['iv']), 4)
                        
                        # 添加常数项行（basepoints）
                        if 'basepoints' in scorecard:
                            bp_df = scorecard['basepoints']
                            if isinstance(bp_df, pd.DataFrame) and len(bp_df) > 0:
                                bp_points = round(float(bp_df['points'].iloc[0]), 2) if 'points' in bp_df.columns else 0
                                full_scorecard_csv.append({
                                    "variable": "常数项",
                                    "total_iv": round(float(self.model_.intercept_[0]), 4) if self.model_ is not None else 0,
                                    "cof": "",
                                    "index": 0,
                                    "bin": "",
                                    "count": "",
                                    "count_distr": "",
                                    "good": "",
                                    "bad": "",
                                    "badprob": "",
                                    "woe": "",
                                    "score": bp_points
                                })
                        
                        # 遍历每个变量的评分卡数据
                        for var_name in feature_vars:
                            if var_name not in scorecard:
                                continue
                            card_df = scorecard[var_name]
                            bin_df = self.bins_.get(var_name) if self.bins_ else None
                            
                            var_iv = iv_lookup.get(var_name, 0)
                            var_cof = model_coefs.get(var_name, 0)
                            
                            for idx, (_, card_row) in enumerate(card_df.iterrows()):
                                bin_str = str(card_row.get('bin', ''))
                                points = round(float(card_row.get('points', 0)), 2) if pd.notna(card_row.get('points')) else 0
                                
                                # 从bins中获取详细统计信息
                                count = 0
                                count_distr = 0
                                good_count = 0
                                bad_count = 0
                                badprob = 0
                                woe = 0
                                
                                if bin_df is not None and isinstance(bin_df, pd.DataFrame):
                                    # 通过bin值匹配
                                    matched_rows = bin_df[bin_df['bin'].astype(str) == bin_str]
                                    if len(matched_rows) > 0:
                                        bin_row = matched_rows.iloc[0]
                                        count = int(bin_row.get('count', 0)) if pd.notna(bin_row.get('count')) else 0
                                        total_count = int(bin_df['count'].sum()) if 'count' in bin_df.columns else 1
                                        count_distr = round(count / total_count * 100, 2) if total_count > 0 else 0
                                        good_count = int(bin_row.get('good', 0)) if pd.notna(bin_row.get('good')) else 0
                                        bad_count = int(bin_row.get('bad', 0)) if pd.notna(bin_row.get('bad')) else 0
                                        badprob = round(float(bin_row.get('badprob', 0)) * 100, 2) if pd.notna(bin_row.get('badprob')) else 0
                                        woe = round(float(bin_row.get('woe', 0)), 4) if pd.notna(bin_row.get('woe')) else 0
                                
                                full_scorecard_csv.append({
                                    "variable": var_name,
                                    "total_iv": var_iv if idx == 0 else "",  # 只在变量第一行显示IV
                                    "cof": var_cof if idx == 0 else "",  # 只在变量第一行显示系数
                                    "index": idx,
                                    "bin": _format_bin_interval(bin_str),
                                    "count": count,
                                    "count_distr": f"{count_distr}%",
                                    "good": good_count,
                                    "bad": bad_count,
                                    "badprob": f"{badprob}%",
                                    "woe": woe,
                                    "score": points
                                })
                        
                        logger.info(f"[Score Scaling] Generated full scorecard CSV with {len(full_scorecard_csv)} rows")
                    except Exception as e:
                        logger.warning(f"Failed to generate full scorecard CSV: {e}")
                        full_scorecard_csv = []
                    
                    score_scaling_preview: dict[str, Any] = {
                        "base_score": self.base_score,
                        "base_odds": self.base_odds,
                        "pdo": self.pdo,
                        "num_variables": len(feature_vars),  # 不包含 basepoints
                        "score_scale": score_scale,  # New: include scale parameters
                        # Phase 29: 新增评分范围信息
                        "theoretical_score_range": {
                            "min": round(theoretical_min_score, 2),
                            "max": round(theoretical_max_score, 2),
                        },
                        "actual_score_stats": actual_score_stats,  # 兼容旧字段（训练集）
                        # 各数据集评分分布统计（用于前端按优先级展示：OOT > 测试集 > 训练集）
                        "score_stats_by_dataset": {
                            "train": train_score_stats,
                            "test": test_score_stats,
                            "oot": oot_score_stats,
                        },
                        # Phase 29: 增强的变量预览（包含得分范围）
                        "scorecard_preview": variable_score_details,
                        # Phase 30: 完整评分卡CSV数据（行业标准格式）
                        "full_scorecard_csv": full_scorecard_csv,
                        # Phase 6: 添加完整阶段数据用于检查点保存
                        "_full_stage_data": {
                            "train_df": train_df,
                            "test_df": test_df,
                            "oot_df": oot_df,
                            "df_woe": df_woe,
                            "bins": bins,
                            "iv_table": iv_table,
                            "feature_cols": feature_cols,
                            "selected_features": selected_features,
                            "model": self.model_,
                            "woe_feature_cols": getattr(self, 'woe_feature_cols_', None),
                            "scorecard": scorecard,
                            "results": dict(results),
                        }
                    }
                    
                    # Phase 28: 先更新 results 字典，确保检查点保存时包含完整数据（与规则挖掘任务一致）
                    results['scorecard'] = scorecard
                    
                    # Phase 29: 更新 _full_stage_data 中的 results，确保包含本阶段添加的数据
                    score_scaling_preview["_full_stage_data"]["results"] = dict(results)
                    
                    self._update_progress("score_scaling", 100.0, "评分刻度转换完成", output_preview=score_scaling_preview)
                except Exception as e:
                    self._update_progress("score_scaling", 100.0, f"评分刻度转换失败: {str(e)}")
                    results['scorecard'] = None
            else:
                self._update_progress("score_scaling", 100.0, "无模型，跳过评分刻度")
                results['scorecard'] = None
        
        # Check for stop request after Stage 5
        if self._should_stop():
            raise TaskStoppedException("任务已被用户停止")
        
        # Stage 6: Model Evaluation
        if should_skip_stage('model_evaluation'):
            logger.info("[Scorecard Pipeline] Skipping model_evaluation stage (using cached data)")
            if 'model_evaluation' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['model_evaluation'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('model_evaluation', 100.0, '模型评估已跳过（使用缓存）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('model_evaluation', 100.0, '模型评估已跳过（使用缓存）', output_preview=skip_preview)
        else:
            self._update_progress("model_evaluation", 0.0, "开始模型评估...", code=self._get_stage_code("model_evaluation"))
            
            if self.model_ is not None:
                from sklearn.metrics import roc_auc_score
                
                # Phase 19: 验证并修复 woe_feature_cols_ 与模型系数的一致性
                # 当阶段被跳过时，缓存的 woe_feature_cols_ 可能与实际模型不一致
                model_n_features = self.model_.coef_.shape[1]
                woe_features = getattr(self, 'woe_feature_cols_', None)
                
                # 检查 woe_features 是否有效且与模型一致
                if not woe_features or len(woe_features) != model_n_features:
                    # 尝试从 selected_features 重建
                    if selected_features and len(selected_features) == model_n_features:
                        woe_features = [f"{f}_woe" if not f.endswith('_woe') else f for f in selected_features]
                        logger.warning(f"[Model Evaluation] woe_feature_cols_ inconsistent with model ({len(getattr(self, 'woe_feature_cols_', []))} vs {model_n_features}), rebuilt from selected_features")
                    else:
                        # 从 df_woe 的列名中提取 WOE 特征（按顺序）
                        # 这是最后的后备方案
                        available_woe_cols = [c for c in df_woe.columns if c.endswith('_woe')]
                        if len(available_woe_cols) >= model_n_features:
                            # 尝试从 bins_ 中获取特征顺序
                            if self.bins_:
                                ordered_features = []
                                for feat in self.bins_.keys():
                                    woe_col = f"{feat}_woe"
                                    if woe_col in available_woe_cols:
                                        ordered_features.append(woe_col)
                                if len(ordered_features) == model_n_features:
                                    woe_features = ordered_features
                                    logger.warning(f"[Model Evaluation] Rebuilt woe_features from bins_ keys: {model_n_features} features")
                        
                        if not woe_features or len(woe_features) != model_n_features:
                            raise ValueError(
                                f"无法确定正确的WOE特征列表。模型需要 {model_n_features} 个特征，"
                                f"但 woe_feature_cols_ 有 {len(getattr(self, 'woe_feature_cols_', []))} 个，"
                                f"selected_features 有 {len(selected_features) if selected_features else 0} 个。"
                                f"请从 model_training 阶段重新开始。"
                            )
                    
                    # 更新实例属性
                    self.woe_feature_cols_ = woe_features
                    logger.info(f"[Model Evaluation] Using {len(woe_features)} WOE features: {woe_features[:5]}...")
                
                # ===== Evaluate on Training Set =====
                self._update_progress("model_evaluation", 15.0, "评估训练集...")
                X_train_eval = df_woe[woe_features]
                y_train_eval = train_df[target_col]
                y_train_pred_proba = self.model_.predict_proba(X_train_eval)[:, 1]
                
                train_auc = roc_auc_score(y_train_eval, y_train_pred_proba)
                train_gini = 2 * train_auc - 1
                train_ks = self._calculate_ks(y_train_eval, y_train_pred_proba)
                
                train_metrics = {
                    'auc': round(train_auc, 4),
                    'gini': round(train_gini, 4),
                    'ks': round(train_ks, 4),
                    'samples': len(y_train_eval),
                    'bad_rate': round(y_train_eval.mean() * 100, 2)
                }
                
                # ===== Evaluate on Test Set =====
                self._update_progress("model_evaluation", 40.0, "评估测试集...")
                test_woe = self.woe_transformer.transform(test_df, self.bins_)
                X_test = test_woe[woe_features]
                y_test = test_df[target_col]
                y_pred_proba = self.model_.predict_proba(X_test)[:, 1]
                
                test_auc = roc_auc_score(y_test, y_pred_proba)
                test_gini = 2 * test_auc - 1
                test_ks = self._calculate_ks(y_test, y_pred_proba)
                
                test_metrics = {
                    'auc': round(test_auc, 4),
                    'gini': round(test_gini, 4),
                    'ks': round(test_ks, 4),
                    'samples': len(y_test),
                    'bad_rate': round(y_test.mean() * 100, 2)
                }
                
                # ===== Evaluate on OOT Set (if available) =====
                oot_metrics = None
                y_oot = None
                y_oot_pred_proba = None
                
                if oot_df is not None and len(oot_df) > 0:
                    self._update_progress("model_evaluation", 65.0, "评估验证集(OOT)...")
                    try:
                        oot_woe = self.woe_transformer.transform(oot_df, self.bins_)
                        X_oot = oot_woe[woe_features]
                        y_oot = oot_df[target_col]
                        y_oot_pred_proba = self.model_.predict_proba(X_oot)[:, 1]
                        
                        oot_auc = roc_auc_score(y_oot, y_oot_pred_proba)
                        oot_gini = 2 * oot_auc - 1
                        oot_ks = self._calculate_ks(y_oot, y_oot_pred_proba)
                        
                        oot_metrics = {
                            'auc': round(oot_auc, 4),
                            'gini': round(oot_gini, 4),
                            'ks': round(oot_ks, 4),
                            'samples': len(y_oot),
                            'bad_rate': round(y_oot.mean() * 100, 2)
                        }
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"OOT evaluation failed: {e}")
                
                # ===== Combined Metrics (for backward compatibility) =====
                # 行业标准：优先使用OOT指标（更能反映真实业务表现），无OOT时使用测试集
                if oot_metrics is not None:
                    self.metrics_ = {
                        'auc': oot_metrics['auc'],
                        'gini': oot_metrics['gini'],
                        'ks': oot_metrics['ks'],
                        'source': 'oot'  # 标识指标来源
                    }
                else:
                    self.metrics_ = {
                        'auc': test_metrics['auc'],
                        'gini': test_metrics['gini'],
                        'ks': test_metrics['ks'],
                        'source': 'test'  # 标识指标来源
                    }
                
                # ===== Multi-dataset Metrics =====
                multi_dataset_metrics = {
                    'train': train_metrics,
                    'test': test_metrics
                }
                if oot_metrics is not None:
                    multi_dataset_metrics['oot'] = oot_metrics
                
                # Check for overfitting (using configurable thresholds)
                ks_diff = train_ks - test_ks
                auc_diff = train_auc - test_auc
                overfit_warning = None
                overfit_warnings = []
                
                if ks_diff > self.overfit_ks_threshold:
                    overfit_warnings.append(f"训练集KS({train_ks:.4f})显著高于测试集KS({test_ks:.4f})，差值{ks_diff:.4f}超过阈值{self.overfit_ks_threshold}")
                
                if auc_diff > self.overfit_auc_threshold:
                    overfit_warnings.append(f"训练集AUC({train_auc:.4f})显著高于测试集AUC({test_auc:.4f})，差值{auc_diff:.4f}超过阈值{self.overfit_auc_threshold}")
                
                if overfit_warnings:
                    overfit_warning = "注意: " + "；".join(overfit_warnings) + "，可能存在过拟合"
                
                # ===== PSI Stability Calculation =====
                # PSI measures population stability between two score distributions
                # 2026-02-10: 始终计算 train vs test，有OOT时额外计算 train vs oot
                psi_result = None
                psi_train_vs_test = None  # 新增：始终计算
                psi_train_vs_oot = None   # 新增：有OOT时计算
                train_scores_for_psi = None
                test_scores_for_psi = None
                oot_scores_for_psi = None
                try:
                    self._update_progress("model_evaluation", 85.0, "计算PSI稳定性指标...")
                    
                    # Calculate scores for PSI (always calculate all available)
                    train_scores_for_psi = sc.scorecard_ply(train_df, self.scorecard_, only_total_score=True)['score'].values
                    test_scores_for_psi = sc.scorecard_ply(test_df, self.scorecard_, only_total_score=True)['score'].values
                    
                    # Helper function to calculate PSI with stability rating
                    def _build_psi_result(psi_value: float, comparison: str) -> dict:
                        if psi_value < 0.1:
                            stability, level = "稳定", "good"
                        elif psi_value < 0.25:
                            stability, level = "轻微变化", "warning"
                        else:
                            stability, level = "显著变化", "bad"
                        return {
                            "value": round(psi_value, 4),
                            "comparison": comparison,
                            "stability": stability,
                            "level": level
                        }
                    
                    # 2026-02-10: 始终计算 Train vs Test PSI
                    psi_value_test = self._calculate_psi(train_scores_for_psi, test_scores_for_psi)
                    psi_train_vs_test = _build_psi_result(psi_value_test, "训练集 vs 测试集")
                    logger.info(f"[Model Evaluation] PSI (Train vs Test)={psi_value_test:.4f}, Stability: {psi_train_vs_test['stability']}")
                    
                    # 2026-02-10: 有OOT时额外计算 Train vs OOT PSI
                    if oot_df is not None and len(oot_df) > 0 and y_oot_pred_proba is not None:
                        oot_scores_for_psi = sc.scorecard_ply(oot_df, self.scorecard_, only_total_score=True)['score'].values
                        psi_value_oot = self._calculate_psi(train_scores_for_psi, oot_scores_for_psi)
                        psi_train_vs_oot = _build_psi_result(psi_value_oot, "训练集 vs OOT")
                        logger.info(f"[Model Evaluation] PSI (Train vs OOT)={psi_value_oot:.4f}, Stability: {psi_train_vs_oot['stability']}")
                        # 主PSI结果优先使用 OOT（行业惯例：OOT稳定性更重要）
                        psi_result = psi_train_vs_oot
                    else:
                        # 无OOT时，主PSI结果使用 Test
                        psi_result = psi_train_vs_test
                    
                except Exception as e:
                    logger.warning(f"[Model Evaluation] PSI calculation failed: {e}")
                    psi_result = None
                    psi_train_vs_test = None
                    psi_train_vs_oot = None
                
                # ===== CSI (Characteristic Stability Index) Calculation =====
                # CSI measures the stability of each feature's WOE distribution
                # Uses the same formula as PSI but applied to individual feature distributions
                csi_train_vs_test = None
                csi_train_vs_oot = None
                try:
                    self._update_progress("model_evaluation", 88.0, "计算CSI特征稳定性指标...")
                    
                    # 获取入模特征名（去掉 _woe 后缀）
                    csi_feature_names = [f.replace('_woe', '') for f in woe_features]
                    
                    # 始终计算 Train vs Test CSI
                    csi_train_vs_test = self._calculate_csi_for_variables(
                        train_woe_df=df_woe,
                        compare_woe_df=test_woe,
                        feature_cols=csi_feature_names,
                        comparison_label="训练集 vs 测试集"
                    )
                    logger.info(f"[Model Evaluation] CSI (Train vs Test): {csi_train_vs_test['summary']}")
                    
                    # 有OOT时额外计算 Train vs OOT CSI
                    if oot_df is not None and len(oot_df) > 0:
                        try:
                            # oot_woe 在OOT评估时已计算（line ~5071）
                            oot_woe_for_csi = self.woe_transformer.transform(oot_df, self.bins_)
                            csi_train_vs_oot = self._calculate_csi_for_variables(
                                train_woe_df=df_woe,
                                compare_woe_df=oot_woe_for_csi,
                                feature_cols=csi_feature_names,
                                comparison_label="训练集 vs OOT"
                            )
                            logger.info(f"[Model Evaluation] CSI (Train vs OOT): {csi_train_vs_oot['summary']}")
                        except Exception as e:
                            logger.warning(f"[Model Evaluation] CSI (Train vs OOT) calculation failed: {e}")
                            csi_train_vs_oot = None
                    
                except Exception as e:
                    logger.warning(f"[Model Evaluation] CSI calculation failed: {e}")
                    csi_train_vs_test = None
                    csi_train_vs_oot = None
                
                # ===== Score Distribution for Stage Preview =====
                # Generate score distribution data for model_evaluation stage output_preview
                score_distribution_data = {}
                try:
                    from .scorecard_viz import get_chart_data_for_frontend
                    
                    # Training set distribution
                    if train_scores_for_psi is not None and y_train_eval is not None:
                        train_dist = get_chart_data_for_frontend(
                            y_true=y_train_eval.values if hasattr(y_train_eval, 'values') else y_train_eval,
                            y_score=y_train_pred_proba,
                            scores=train_scores_for_psi,
                            score_bin_method=self.score_bin_method,
                            score_distribution_bins=self.score_distribution_bins,
                            ranking_analysis_bins=self.ranking_analysis_bins
                        )
                        score_distribution_data['train'] = train_dist.get('score_distribution')
                    
                    # Test set distribution
                    if test_scores_for_psi is not None and y_test is not None:
                        test_dist = get_chart_data_for_frontend(
                            y_true=y_test.values if hasattr(y_test, 'values') else y_test,
                            y_score=y_pred_proba,
                            scores=test_scores_for_psi,
                            score_bin_method=self.score_bin_method,
                            score_distribution_bins=self.score_distribution_bins,
                            ranking_analysis_bins=self.ranking_analysis_bins
                        )
                        score_distribution_data['test'] = test_dist.get('score_distribution')
                    
                    # OOT set distribution (if available)
                    if oot_scores_for_psi is not None and y_oot is not None:
                        oot_dist = get_chart_data_for_frontend(
                            y_true=y_oot.values if hasattr(y_oot, 'values') else y_oot,
                            y_score=y_oot_pred_proba,
                            scores=oot_scores_for_psi,
                            score_bin_method=self.score_bin_method,
                            score_distribution_bins=self.score_distribution_bins,
                            ranking_analysis_bins=self.ranking_analysis_bins
                        )
                        score_distribution_data['oot'] = oot_dist.get('score_distribution')
                    
                    logger.info(f"[Model Evaluation] Score distribution generated for: {list(score_distribution_data.keys())}")
                except Exception as e:
                    logger.warning(f"[Model Evaluation] Score distribution generation failed: {e}")
                    score_distribution_data = {}
                
                # Build progress message
                progress_msg = f"评估完成，训练集KS={train_ks:.4f}, 测试集KS={test_ks:.4f}"
                if oot_metrics is not None:
                    progress_msg += f", OOT KS={oot_metrics['ks']:.4f}"
                if psi_result is not None:
                    progress_msg += f", PSI={psi_result['value']:.4f}({psi_result['stability']})"
                
                # Phase 27: 先更新 results 字典，确保检查点保存时包含完整数据
                # 这样在专家模式暂停后恢复时，cached_state["results"] 会包含 multi_dataset_metrics
                results['metrics'] = self.metrics_
                results['multi_dataset_metrics'] = multi_dataset_metrics
                results['overfit_warning'] = overfit_warning
                results['test_predictions'] = y_pred_proba
                results['psi_result'] = psi_result  # Phase 31: PSI稳定性指标（主PSI：有OOT用OOT，否则用Test）
                # 2026-02-10: 新增双PSI结果，供前端同时展示两个PSI对比图
                results['psi_train_vs_test'] = psi_train_vs_test  # 始终存在
                results['psi_train_vs_oot'] = psi_train_vs_oot    # 仅有OOT时存在
                # CSI（特征稳定性指标）
                results['csi_train_vs_test'] = csi_train_vs_test  # 始终存在
                results['csi_train_vs_oot'] = csi_train_vs_oot    # 仅有OOT时存在
                
                # Build output preview for model_evaluation stage (with _full_stage_data)
                model_evaluation_preview: dict[str, Any] = {
                    "train_metrics": train_metrics,
                    "test_metrics": test_metrics,
                    "overfit_warning": overfit_warning,
                    "psi_result": psi_result,  # Phase 31: PSI稳定性指标
                    # 2026-02-10: 新增双PSI结果
                    "psi_train_vs_test": psi_train_vs_test,
                    "psi_train_vs_oot": psi_train_vs_oot,
                    # CSI（特征稳定性指标）
                    "csi_train_vs_test": csi_train_vs_test,
                    "csi_train_vs_oot": csi_train_vs_oot,
                    "score_distribution": score_distribution_data if score_distribution_data else None,  # Phase 32: 评分分布数据
                    # Phase 6: 添加完整阶段数据用于检查点保存
                    "_full_stage_data": {
                        "train_df": train_df,
                        "test_df": test_df,
                        "oot_df": oot_df,
                        "df_woe": df_woe,
                        "bins": bins,
                        "iv_table": iv_table,
                        "feature_cols": feature_cols,
                        "selected_features": selected_features,
                        "model": self.model_,
                        "woe_feature_cols": getattr(self, 'woe_feature_cols_', None),
                        "scorecard": self.scorecard_,
                        "results": dict(results),  # Phase 27: 现在 results 已包含 multi_dataset_metrics
                        # Phase 24: 保存评估数据供report_generation使用
                        "y_train": y_train_eval,
                        "y_train_pred_proba": y_train_pred_proba,
                        "y_test": y_test,
                        "y_pred_proba": y_pred_proba,
                        "y_oot": y_oot,
                        "y_oot_pred_proba": y_oot_pred_proba,
                    }
                }
                if oot_metrics is not None:
                    model_evaluation_preview["oot_metrics"] = oot_metrics
                
                self._update_progress("model_evaluation", 100.0, progress_msg, output_preview=model_evaluation_preview)
                
                # Store for report generation
                self._train_df = train_df
                self._test_df = test_df
                self._oot_df = oot_df
                self._y_train = y_train_eval
                self._y_train_pred_proba = y_train_pred_proba
                self._y_test = y_test
                self._y_pred_proba = y_pred_proba
                self._y_oot = y_oot
                self._y_oot_pred_proba = y_oot_pred_proba
            else:
                self._update_progress("model_evaluation", 100.0, "无模型，跳过评估")
                results['metrics'] = {}
                results['multi_dataset_metrics'] = {}
                self._train_df = None
                self._test_df = None
                self._oot_df = None
                self._y_train = None
                self._y_train_pred_proba = None
                self._y_test = None
                self._y_pred_proba = None
                self._y_oot = None
                self._y_oot_pred_proba = None
        
        # Stage 7: Report Generation (mandatory stage for all SOP tasks)
        if should_skip_stage('report_generation'):
            logger.info("[Scorecard Pipeline] Skipping report_generation stage (using cached data)")
            if 'report_generation' in restored_output_previews:
                # 使用恢复的output_preview，只添加跳过标记
                restored_preview = restored_output_previews['report_generation'].copy()
                restored_preview['_skip_expert_pause'] = True
                restored_preview['_skipped_during_retry'] = True
                restored_preview['retry_message'] = '使用缓存数据（阶段重试）'
                self._update_progress('report_generation', 100.0, '报告生成已跳过（使用缓存）', output_preview=restored_preview)
            else:
                # 没有恢复的output_preview，使用简单的skip_preview
                skip_preview = {"skipped": True, "reason": "使用缓存数据（阶段重试）", "_skip_expert_pause": True, "_skipped_during_retry": True}
                self._update_progress('report_generation', 100.0, '报告生成已跳过（使用缓存）', output_preview=skip_preview)
        else:
            self._update_progress("report_generation", 0.0, "开始生成报告...", code=self._get_stage_code("report_generation"))
            
            if self.model_ is not None and self._y_test is not None:
                try:
                    from .scorecard_viz import get_chart_data_for_frontend
                    import logging
                    logger = logging.getLogger(__name__)
                    
                    # Calculate scores for train, test, and OOT sets if scorecard exists
                    train_scores = None
                    test_scores = None
                    oot_scores = None
                    
                    if self.scorecard_ is not None:
                        try:
                            logger.info(f"scorecard_ type: {type(self.scorecard_)}")
                            
                            # Debug: print scorecard details
                            logger.info("=== Scorecard Details ===")
                            for var_name, card_df in self.scorecard_.items():
                                if isinstance(card_df, pd.DataFrame):
                                    logger.info(f"Variable: {var_name}")
                                    logger.info(f"  Points range: {card_df['points'].min()} to {card_df['points'].max()}")
                            
                            # Calculate scores for training set
                            if self._train_df is not None:
                                train_scores_df = sc.scorecard_ply(self._train_df, self.scorecard_, only_total_score=True)
                                train_scores = train_scores_df['score'].values
                                logger.info(f"Train scores: min={train_scores.min()}, max={train_scores.max()}, mean={train_scores.mean():.2f}")
                            
                            # Calculate scores for test set
                            if self._test_df is not None:
                                test_scores_df = sc.scorecard_ply(self._test_df, self.scorecard_, only_total_score=True)
                                test_scores = test_scores_df['score'].values
                                logger.info(f"Test scores: min={test_scores.min()}, max={test_scores.max()}, mean={test_scores.mean():.2f}")
                            
                            # Calculate scores for OOT set
                            if self._oot_df is not None:
                                oot_scores_df = sc.scorecard_ply(self._oot_df, self.scorecard_, only_total_score=True)
                                oot_scores = oot_scores_df['score'].values
                                logger.info(f"OOT scores: min={oot_scores.min()}, max={oot_scores.max()}, mean={oot_scores.mean():.2f}")
                            
                            # Validate scorecard quality using test scores
                            if test_scores is not None:
                                # Use ScorecardValidator from validators module
                                scorecard_validator = ScorecardValidator()
                                validation = scorecard_validator.validate_simple(test_scores)
                                results['scorecard_validation'] = validation
                                self.scorecard_validation_ = validation
                                
                        except Exception as e:
                            logger.error(f"scorecard_ply failed: {e}")
                    
                    self._update_progress("report_generation", 20.0, "生成训练集图表数据...")
                    
                    # Generate chart data for training set
                    train_chart_data = None
                    if self._y_train is not None and self._y_train_pred_proba is not None:
                        try:
                            train_chart_data = get_chart_data_for_frontend(
                                y_true=self._y_train.values if hasattr(self._y_train, 'values') else self._y_train,
                                y_score=self._y_train_pred_proba,
                                scores=train_scores,
                                score_bin_method=self.score_bin_method,
                                score_distribution_bins=self.score_distribution_bins,
                                ranking_analysis_bins=self.ranking_analysis_bins
                            )
                        except Exception as e:
                            logger.error(f"Train chart data generation failed: {e}")
                    
                    self._update_progress("report_generation", 50.0, "生成测试集图表数据...")
                    
                    # Generate chart data for test set
                    test_chart_data = get_chart_data_for_frontend(
                        y_true=self._y_test.values if hasattr(self._y_test, 'values') else self._y_test,
                        y_score=self._y_pred_proba,
                        scores=test_scores,
                        score_bin_method=self.score_bin_method,
                        score_distribution_bins=self.score_distribution_bins,
                        ranking_analysis_bins=self.ranking_analysis_bins
                    )
                    
                    # Generate chart data for OOT set (if available)
                    oot_chart_data = None
                    if self._y_oot is not None and self._y_oot_pred_proba is not None:
                        self._update_progress("report_generation", 75.0, "生成验证集(OOT)图表数据...")
                        try:
                            oot_chart_data = get_chart_data_for_frontend(
                                y_true=self._y_oot.values if hasattr(self._y_oot, 'values') else self._y_oot,
                                y_score=self._y_oot_pred_proba,
                                scores=oot_scores,
                                score_bin_method=self.score_bin_method,
                                score_distribution_bins=self.score_distribution_bins,
                                ranking_analysis_bins=self.ranking_analysis_bins
                            )
                        except Exception as e:
                            logger.error(f"OOT chart data generation failed: {e}")
                    
                    # Store chart data with dataset labels
                    results['chart_data'] = test_chart_data  # Backward compatible: default is test set
                    multi_dataset_chart_data = {
                        'train': train_chart_data,
                        'test': test_chart_data
                    }
                    if oot_chart_data is not None:
                        multi_dataset_chart_data['oot'] = oot_chart_data
                    results['multi_dataset_chart_data'] = multi_dataset_chart_data
                    
                    # Build output preview for report_generation stage
                    # Phase 10: 丰富output_preview，包含更多有意义的信息供AI分析使用
                    scorecard_validation = results.get('scorecard_validation', {})
                    
                    # Phase 22: 构建完整的报告章节列表（与开发结果Tab对应）
                    report_sections_list = ["样本与特征", "评估图表", "评分卡明细", "变量筛选", "模型系数"]
                    
                    report_preview: dict[str, Any] = {
                        # 基本信息
                        "status": "已完成",
                        "report_sections": report_sections_list,
                        "datasets": ["训练集", "测试集"] + (["OOT验证集"] if oot_chart_data is not None else []),
                        
                        # 图表数据
                        "chart_types": list(test_chart_data.keys()) if test_chart_data else [],
                        "has_chart_data": test_chart_data is not None,
                        
                        # 评分卡验证结果
                        "scorecard_validation": {
                            "passed": scorecard_validation.get('passed', False),
                            "issues": scorecard_validation.get('issues', [])[:5],  # 最多5个问题
                            "score_range": scorecard_validation.get('score_range', None),
                            "score_mean": scorecard_validation.get('score_mean', None)
                        } if scorecard_validation else None,
                        
                        # 评分统计
                        "score_statistics": {
                            "train": {
                                "min": float(train_scores.min()) if train_scores is not None else None,
                                "max": float(train_scores.max()) if train_scores is not None else None,
                                "mean": float(train_scores.mean()) if train_scores is not None else None
                            } if train_scores is not None else None,
                            "test": {
                                "min": float(test_scores.min()) if test_scores is not None else None,
                                "max": float(test_scores.max()) if test_scores is not None else None,
                                "mean": float(test_scores.mean()) if test_scores is not None else None
                            } if test_scores is not None else None,
                            "oot": {
                                "min": float(oot_scores.min()) if oot_scores is not None else None,
                                "max": float(oot_scores.max()) if oot_scores is not None else None,
                                "mean": float(oot_scores.mean()) if oot_scores is not None else None
                            } if oot_scores is not None else None
                        },
                        
                        # 模型入模变量数
                        "n_features": len(self.selected_features_) if self.selected_features_ else None,
                        
                        # Phase 25: 添加完整阶段数据用于检查点保存
                        "_full_stage_data": {
                            "train_df": train_df,
                            "test_df": test_df,
                            "oot_df": oot_df,
                            "df_woe": df_woe,
                            "bins": bins,
                            "iv_table": iv_table,
                            "feature_cols": feature_cols,
                            "selected_features": selected_features,
                            "model": self.model_,
                            "woe_feature_cols": getattr(self, 'woe_feature_cols_', None),
                            "scorecard": self.scorecard_,
                            "results": dict(results),
                            "y_train": self._y_train,
                            "y_train_pred_proba": self._y_train_pred_proba,
                            "y_test": self._y_test,
                            "y_pred_proba": self._y_pred_proba,
                            "y_oot": self._y_oot,
                            "y_oot_pred_proba": self._y_oot_pred_proba,
                        }
                    }
                    
                    self._update_progress("report_generation", 100.0, "报告生成完成", output_preview=report_preview)
                except Exception as e:
                    error_preview = {
                        "status": "失败",
                        "error": str(e),
                        "report_sections": [],
                        "datasets": []
                    }
                    self._update_progress("report_generation", 100.0, f"图表数据生成失败: {str(e)}", output_preview=error_preview)
                    results['chart_data'] = None
                    results['multi_dataset_chart_data'] = None
            else:
                no_data_preview = {
                    "status": "跳过",
                    "reason": "无模型数据",
                    "report_sections": [],
                    "datasets": []
                }
                self._update_progress("report_generation", 100.0, "无模型数据，跳过报告生成", output_preview=no_data_preview)
                results['chart_data'] = None
                results['multi_dataset_chart_data'] = None
        
        # 恢复原始进度回调
        self.progress_callback = original_callback
        
        return results
    
    def _calculate_ks(self, y_true: pd.Series, y_pred_proba: np.ndarray) -> float:
        """Calculate KS statistic."""
        from sklearn.metrics import roc_curve
        
        fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
        ks = max(tpr - fpr)
        return ks
    
    def _calculate_psi(self, expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
        """
        Calculate Population Stability Index (PSI) between two score distributions.
        
        PSI measures the stability of a model's score distribution over time or across datasets.
        It compares the distribution of scores from a baseline (expected) to a new sample (actual).
        
        Args:
            expected: Baseline score distribution (e.g., training set scores)
            actual: Comparison score distribution (e.g., OOT or test set scores)
            bins: Number of bins for distribution comparison (default: 10)
            
        Returns:
            PSI value (float)
            
        PSI Interpretation:
            < 0.1: Stable - No significant change
            0.1 - 0.25: Slight change - May need monitoring
            > 0.25: Significant change - Model may need rebuilding
            
        Formula:
            PSI = Σ (Actual% - Expected%) × ln(Actual% / Expected%)
        """
        # Create bins based on expected distribution
        # Use percentile-based bins for more robust comparison
        _, bin_edges = np.histogram(expected, bins=bins)
        
        # Ensure edge bins capture all data
        bin_edges[0] = min(expected.min(), actual.min()) - 1
        bin_edges[-1] = max(expected.max(), actual.max()) + 1
        
        # Calculate distributions
        expected_counts, _ = np.histogram(expected, bins=bin_edges)
        actual_counts, _ = np.histogram(actual, bins=bin_edges)
        
        # Convert to percentages (add small epsilon to avoid division by zero)
        epsilon = 1e-6
        expected_pct = expected_counts / len(expected) + epsilon
        actual_pct = actual_counts / len(actual) + epsilon
        
        # Calculate PSI for each bin and sum
        psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        
        return abs(psi)  # PSI is always positive
    
    def _calculate_csi_for_variables(
        self,
        train_woe_df: pd.DataFrame,
        compare_woe_df: pd.DataFrame,
        feature_cols: list[str],
        comparison_label: str = "训练集 vs 测试集"
    ) -> dict[str, Any]:
        """
        计算各入模特征的 CSI（Characteristic Stability Index，特征稳定性指数）。
        
        CSI 计算方式与 PSI 相同，但针对的是各特征的 WOE 分箱分布而非评分分布。
        对每个特征，比较训练集和测试集/OOT 中各分箱的样本占比。
        
        Args:
            train_woe_df: 训练集 WOE 转换后的 DataFrame
            compare_woe_df: 对比集（测试集或OOT）WOE 转换后的 DataFrame
            feature_cols: 入模特征名列表（原始特征名，不带 _woe 后缀）
            comparison_label: 对比标签，如 "训练集 vs 测试集"
            
        Returns:
            {
                "comparison": "训练集 vs 测试集",
                "features": [
                    {"feature": "age", "csi": 0.05, "stability": "稳定", "level": "good"},
                    ...
                ],
                "summary": {
                    "total_features": 10,
                    "stable": 8,
                    "slight_change": 1,
                    "significant_change": 1
                }
            }
        """
        import logging
        logger = logging.getLogger(__name__)
        
        csi_features: list[dict[str, Any]] = []
        summary = {"total_features": 0, "stable": 0, "slight_change": 0, "significant_change": 0}
        
        for feat in feature_cols:
            woe_col = f"{feat}_woe"
            
            # 确保两个数据集中都有该 WOE 列
            if woe_col not in train_woe_df.columns or woe_col not in compare_woe_df.columns:
                logger.warning(f"[CSI] WOE column '{woe_col}' not found in one of the datasets, skipping")
                continue
            
            train_vals = train_woe_df[woe_col].dropna().values
            compare_vals = compare_woe_df[woe_col].dropna().values
            
            if len(train_vals) == 0 or len(compare_vals) == 0:
                logger.warning(f"[CSI] Empty values for '{woe_col}', skipping")
                continue
            
            try:
                csi_value = self._calculate_psi(train_vals, compare_vals)
                csi_value = round(csi_value, 4)
            except Exception as e:
                logger.warning(f"[CSI] Failed to calculate CSI for '{feat}': {e}")
                continue
            
            # 稳定性判定（与 PSI 阈值一致）
            if csi_value < 0.1:
                stability, level = "稳定", "good"
            elif csi_value < 0.25:
                stability, level = "轻微变化", "warning"
            else:
                stability, level = "显著变化", "danger"
            
            csi_features.append({
                "feature": feat,
                "csi": csi_value,
                "stability": stability,
                "level": level
            })
            
            summary["total_features"] += 1
            if level == "good":
                summary["stable"] += 1
            elif level == "warning":
                summary["slight_change"] += 1
            else:
                summary["significant_change"] += 1
        
        # 按 CSI 值降序排列（最不稳定的排前面）
        csi_features.sort(key=lambda x: x["csi"], reverse=True)
        
        return {
            "comparison": comparison_label,
            "features": csi_features,
            "summary": summary
        }
    
    # Note: _validate_scorecard method has been moved to validators.py module
    # Use ScorecardValidator.validate_simple() instead





