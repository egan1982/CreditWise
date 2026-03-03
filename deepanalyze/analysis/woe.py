"""
Weight of Evidence (WOE) Calculator Module

Provides WOE calculation functionality for feature analysis in credit risk assessment.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')


class WOECalculator:
    """WOE (Weight of Evidence) calculation utility class"""
    
    @staticmethod
    def calculate_woe(
        df: pd.DataFrame,
        feature: str,
        target: str,
        n_bins: int = 5,
        method: str = 'quantile'
    ) -> Dict[str, Any]:
        """
        Calculate WOE and IV for a given feature
        
        Args:
            df: DataFrame containing feature and target
            feature: Feature name
            target: Target variable name (0/1 binary)
            n_bins: Number of bins for discretization
            method: Binning method ('quantile', 'uniform', 'kmeans')
            
        Returns:
            Dictionary with WOE values, IV, bins information, and interpretation
        """
        try:
            # Validate inputs
            if feature not in df.columns:
                raise ValueError(f"Feature '{feature}' not found in DataFrame")
            if target not in df.columns:
                raise ValueError(f"Target '{target}' not found in DataFrame")
            
            # Check target is binary
            unique_targets = df[target].unique()
            if len(unique_targets) != 2:
                raise ValueError(f"Target '{target}' must be binary, found {len(unique_targets)} unique values")
            
            # Create bins
            feature_data = df[feature].copy()
            
            if method == 'quantile':
                bins = pd.qcut(feature_data, q=n_bins, duplicates='drop', retbins=True)[1]
            elif method == 'uniform':
                bins = pd.cut(feature_data, bins=n_bins, retbins=True)[1]
            elif method == 'kmeans':
                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=n_bins, random_state=42, n_init=10)
                # Note: This kmeans implementation needs review, it returns labels not edges
                bins = np.sort(np.unique(kmeans.fit_predict(feature_data.values.reshape(-1, 1))))
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Adjust bins for scorecardpy compatibility: [a, b) format with -inf/inf
            if method in ['quantile', 'uniform']:
                bins = sorted(list(set(bins))) # Remove duplicates just in case
                if len(bins) >= 2:
                    bins[0] = float('-inf')
                    bins[-1] = float('inf')
                
                # Bin the feature using right=False for [a, b) intervals
                binned_feature = pd.cut(feature_data, bins=bins, right=False, duplicates='drop')
            else:
                # Fallback for kmeans or other methods (legacy behavior)
                binned_feature = pd.cut(feature_data, bins=bins, include_lowest=True, duplicates='drop')
            
            # Calculate distribution
            dist_table = pd.crosstab(binned_feature, df[target], margins=False)
            
            if dist_table.shape[1] != 2:
                raise ValueError("Target must have exactly 2 classes")
            
            # Get event and non-event counts
            event_col = max(dist_table.columns)
            non_event_col = min(dist_table.columns)
            
            events = dist_table[event_col].values
            non_events = dist_table[non_event_col].values
            
            # Total events and non-events
            total_events = events.sum()
            total_non_events = non_events.sum()
            
            if total_events == 0 or total_non_events == 0:
                raise ValueError("Insufficient event or non-event samples")
            
            # Calculate WOE for each bin
            woe_values = []
            iv_values = []
            bin_info = []
            
            for i in range(len(events)):
                # Calculate percentage of events and non-events
                pct_events = events[i] / total_events if total_events > 0 else 0
                pct_non_events = non_events[i] / total_non_events if total_non_events > 0 else 0
                
                # Avoid log(0) by adding small epsilon (0.5 adjustment or small constant)
                # Standard practice: add 0.5 to count if count is 0, or use a larger epsilon
                epsilon = 1e-4  # Changed from 1e-10 to 1e-4 to avoid extreme WOE values
                
                pct_events = max(pct_events, epsilon)
                pct_non_events = max(pct_non_events, epsilon)
                
                # Calculate WOE with clipping to avoid extreme values
                woe = np.log(pct_events / pct_non_events)
                
                # Clip WOE to reasonable range [-20, 20] is too wide, [-5, 5] is standard
                # But to avoid affecting IV too much, we use a wider range but not infinite
                woe = float(np.clip(woe, -10.0, 10.0))
                woe_values.append(woe)
                
                # Calculate IV contribution
                iv_contribution = (pct_events - pct_non_events) * woe
                iv_values.append(iv_contribution)
                
                # Store bin information
                bin_str = str(dist_table.index[i])
                # Remove space after comma to match scorecardpy format: [-inf,0.0)
                bin_str = bin_str.replace(', ', ',')
                
                bin_info.append({
                    'bin': bin_str,
                    'event_count': int(events[i]),
                    'non_event_count': int(non_events[i]),
                    'total_count': int(events[i] + non_events[i]),
                    'event_rate': float(events[i] / (events[i] + non_events[i]) if (events[i] + non_events[i]) > 0 else 0),
                    'pct_events': float(pct_events),
                    'pct_non_events': float(pct_non_events),
                    'woe': float(woe),
                    'iv_contribution': float(iv_contribution)
                })
            
            # Calculate total IV
            total_iv = sum(iv_values)
            
            # Interpret IV strength
            interpretation = WOECalculator._interpret_iv(total_iv)
            
            return {
                'feature': feature,
                'method': method,
                'n_bins': len(woe_values),
                'woe': [float(w) for w in woe_values],
                'iv': float(total_iv),
                'interpretation': interpretation,
                'strength': WOECalculator._get_strength_label(total_iv),
                'predictive': total_iv > 0.02,
                'bins': bin_info,
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'feature': feature
            }
    
    @staticmethod
    def _interpret_iv(iv_value: float) -> str:
        """Interpret IV value"""
        if iv_value < 0.02:
            return "无预测力 (Negligible)"
        elif iv_value < 0.1:
            return "弱预测力 (Weak)"
        elif iv_value < 0.3:
            return "中等预测力 (Medium)"
        elif iv_value < 0.5:
            return "强预测力 (Strong)"
        else:
            return "极强预测力 (Very Strong)"
    
    @staticmethod
    def _get_strength_label(iv_value: float) -> str:
        """Get simple strength label"""
        if iv_value < 0.02:
            return "无"
        elif iv_value < 0.1:
            return "弱"
        elif iv_value < 0.3:
            return "中"
        elif iv_value < 0.5:
            return "强"
        else:
            return "极强"
