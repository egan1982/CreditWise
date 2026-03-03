"""
Feature Correlation and Multicollinearity Analysis Module

Provides tools for detecting feature correlations and multicollinearity:
- Correlation matrix calculation (Pearson/Spearman/Kendall)
- VIF (Variance Inflation Factor) calculation
- Correlation-based feature filtering
- VIF-based feature filtering

This is a general-purpose底层 tool module that can be used by various analysis tasks.
Designed to be reusable and independent of any specific business logic.

Architecture Note:
- This module follows the "bottom-layer tool" pattern established by preprocessing.py
- It provides pure data analysis capabilities without business logic
- Task-level modules (like scorecard_development.py) should delegate to these tools
"""

import pandas as pd
import numpy as np
from typing import Literal, Optional
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings

warnings.filterwarnings('ignore')


class CorrelationAnalyzer:
    """
    Feature correlation analyzer.
    
    Provides correlation matrix calculation and correlation-based feature filtering
    for detecting redundant features.
    
    Supported correlation methods:
    - pearson: Linear correlation (default)
    - spearman: Rank correlation
    - kendall: Rank correlation (robust to outliers)
    
    Example:
        >>> analyzer = CorrelationAnalyzer()
        >>> corr_matrix = analyzer.calculate_correlation(df, method='pearson')
        >>> high_corr_pairs = analyzer.find_high_correlation(corr_matrix, threshold=0.7)
        >>> df_filtered, removed, pairs = analyzer.filter_by_correlation(df, threshold=0.7)
    """
    
    @staticmethod
    def calculate_correlation(
        df: pd.DataFrame,
        feature_cols: Optional[list[str]] = None,
        method: Literal['pearson', 'spearman', 'kendall'] = 'pearson'
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix for features.
        
        Args:
            df: Input DataFrame
            feature_cols: Feature columns to calculate (defaults to all numeric)
            method: Correlation method ('pearson'/'spearman'/'kendall')
            
        Returns:
            Correlation matrix DataFrame
        """
        if feature_cols is None:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        return df[feature_cols].corr(method=method)
    
    @staticmethod
    def find_high_correlation(
        corr_matrix: pd.DataFrame,
        threshold: float = 0.7
    ) -> list[tuple[str, str, float]]:
        """
        Find feature pairs with high correlation.
        
        Args:
            corr_matrix: Correlation matrix
            threshold: Correlation threshold (absolute value)
            
        Returns:
            List of (feature1, feature2, correlation_value) tuples
        """
        high_corr_pairs: list[tuple[str, str, float]] = []
        
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > threshold:
                    high_corr_pairs.append((
                        corr_matrix.columns[i],
                        corr_matrix.columns[j],
                        corr_val
                    ))
        
        return sorted(high_corr_pairs, key=lambda x: abs(x[2]), reverse=True)
    
    @staticmethod
    def filter_by_correlation(
        df: pd.DataFrame,
        feature_cols: Optional[list[str]] = None,
        threshold: float = 0.7,
        method: Literal['pearson', 'spearman', 'kendall'] = 'pearson',
        keep: Literal['first', 'none'] = 'first'
    ) -> tuple[pd.DataFrame, list[str], list[tuple[str, str, float]]]:
        """
        Filter features based on correlation threshold.
        
        Strategy: For each pair with |corr| > threshold, remove one feature.
        
        Args:
            df: Input DataFrame
            feature_cols: Feature columns to check (defaults to all numeric)
            threshold: Correlation threshold (absolute value)
            method: Correlation method
            keep: 'first' - keep first feature in pair, 'none' - remove both
            
        Returns:
            Tuple of (filtered DataFrame, list of removed features, list of high correlation pairs)
        """
        if feature_cols is None:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        corr_matrix = CorrelationAnalyzer.calculate_correlation(
            df, feature_cols, method
        )
        high_corr_pairs = CorrelationAnalyzer.find_high_correlation(
            corr_matrix, threshold
        )
        
        # Determine features to remove
        removed_features: set[str] = set()
        for feat1, feat2, _ in high_corr_pairs:
            if keep == 'first':
                # Remove second feature
                if feat2 not in removed_features:
                    removed_features.add(feat2)
            elif keep == 'none':
                # Remove both features
                removed_features.add(feat1)
                removed_features.add(feat2)
        
        # Filter DataFrame
        remaining_features = [f for f in feature_cols if f not in removed_features]
        df_filtered = df[remaining_features]
        
        return df_filtered, list(removed_features), high_corr_pairs


class VIFAnalyzer:
    """
    Variance Inflation Factor (VIF) analyzer for multicollinearity detection.
    
    VIF measures how much the variance of a regression coefficient is inflated
    due to multicollinearity with other features.
    
    VIF interpretation:
    - VIF = 1: No correlation with other features
    - VIF = 1-5: Moderate correlation
    - VIF = 5-10: High correlation (consider removal)
    - VIF > 10: Severe multicollinearity (should remove)
    
    Example:
        >>> analyzer = VIFAnalyzer()
        >>> vif_table = analyzer.calculate_vif(df)
        >>> df_filtered, removed, final_vif = analyzer.filter_by_vif(df, threshold=5)
    """
    
    @staticmethod
    def calculate_vif(
        df: pd.DataFrame,
        feature_cols: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """
        Calculate VIF for all features.
        
        Args:
            df: Input DataFrame
            feature_cols: Feature columns to calculate (defaults to all numeric)
            
        Returns:
            DataFrame with columns: feature, VIF
        """
        if feature_cols is None:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        df_features = df[feature_cols].dropna()
        
        vif_data: list[dict[str, str | float]] = []
        for i, col in enumerate(df_features.columns):
            try:
                vif = variance_inflation_factor(df_features.values, i)
                vif_data.append({
                    'feature': col,
                    'VIF': round(vif, 2)
                })
            except Exception as e:
                # Handle singular matrix or other computation errors
                vif_data.append({
                    'feature': col,
                    'VIF': np.inf
                })
        
        # 处理空数据情况
        if not vif_data:
            return pd.DataFrame(columns=['feature', 'VIF'])
        
        return pd.DataFrame(vif_data).sort_values('VIF', ascending=False)
    
    @staticmethod
    def filter_by_vif(
        df: pd.DataFrame,
        feature_cols: Optional[list[str]] = None,
        threshold: float = 5.0,
        max_iterations: int = 10
    ) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
        """
        Iteratively remove features with high VIF.
        
        Algorithm:
        1. Calculate VIF for all features
        2. Remove feature with highest VIF if > threshold
        3. Repeat until all VIF < threshold or max_iterations reached
        
        Args:
            df: Input DataFrame
            feature_cols: Feature columns to check (defaults to all numeric)
            threshold: VIF threshold (default: 5.0)
            max_iterations: Maximum iterations to prevent infinite loop
            
        Returns:
            Tuple of (filtered DataFrame, list of removed features, final VIF table)
        """
        if feature_cols is None:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        remaining_features = feature_cols.copy()
        removed_features: list[str] = []
        
        for iteration in range(max_iterations):
            # Calculate VIF
            vif_table = VIFAnalyzer.calculate_vif(df, remaining_features)
            
            # Check if all VIF < threshold
            max_vif_row = vif_table.iloc[0]
            if max_vif_row['VIF'] <= threshold:
                break
            
            # Remove feature with highest VIF
            feature_to_remove = max_vif_row['feature']
            remaining_features.remove(feature_to_remove)
            removed_features.append(feature_to_remove)
        
        # Final VIF table
        final_vif_table = VIFAnalyzer.calculate_vif(df, remaining_features)
        
        # Filter DataFrame
        df_filtered = df[remaining_features]
        
        return df_filtered, removed_features, final_vif_table
