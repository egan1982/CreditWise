"""
Feature Binning Module

Provides feature binning/discretization functionality for data preprocessing.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)


class FeatureBinner:
    """Feature binning utility class for discretization"""
    
    @staticmethod
    def auto_bin(
        df: pd.DataFrame,
        feature: str,
        n_bins: int = 5,
        method: str = 'quantile',
        include_labels: bool = True
    ) -> Dict[str, Any]:
        """
        Automatically bin a feature
        
        Args:
            df: DataFrame containing the feature
            feature: Feature name to bin
            n_bins: Number of bins
            method: Binning method ('quantile', 'uniform', 'kmeans')
            include_labels: Whether to include bin labels
            
        Returns:
            Dictionary with binning results
        """
        try:
            if feature not in df.columns:
                raise ValueError(f"Feature '{feature}' not found in DataFrame")
            
            feature_data = df[feature].copy()
            
            # Remove NaN values
            valid_data = feature_data.dropna()
            
            if len(valid_data) == 0:
                raise ValueError("No valid data after removing NaN values")
            
            # Perform binning based on method
            if method == 'quantile':
                binned, bins = pd.qcut(valid_data, q=n_bins, duplicates='drop', retbins=True)
            elif method == 'uniform':
                binned, bins = pd.cut(valid_data, bins=n_bins, retbins=True)
            elif method == 'kmeans':
                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=n_bins, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(valid_data.values.reshape(-1, 1))
                unique_clusters = np.sort(np.unique(cluster_labels))
                bin_edges = []
                for c in unique_clusters:
                    bin_edges.append(valid_data[cluster_labels == c].max())
                bins = np.sort(np.unique(bin_edges))
                binned = pd.cut(valid_data, bins=bins, include_lowest=True)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Generate bin labels
            bin_labels = []
            for i in range(len(bins) - 1):
                bin_labels.append(f"[{bins[i]:.2f}, {bins[i+1]:.2f}]")
            
            # Get bin statistics
            bin_stats = []
            for i, label in enumerate(bin_labels):
                if i < len(bins) - 1:
                    mask = (valid_data >= bins[i]) & (valid_data < bins[i+1])
                    if i == len(bins) - 2:  # Last bin includes right boundary
                        mask = (valid_data >= bins[i]) & (valid_data <= bins[i+1])
                    
                    bin_values = valid_data[mask]
                    bin_stats.append({
                        'bin_label': label,
                        'count': int(len(bin_values)),
                        'percentage': float(len(bin_values) / len(valid_data) * 100),
                        'min': float(bin_values.min()),
                        'max': float(bin_values.max()),
                        'mean': float(bin_values.mean()),
                        'median': float(bin_values.median()),
                        'std': float(bin_values.std())
                    })
            
            return {
                'status': 'success',
                'feature': feature,
                'method': method,
                'n_bins': len(bin_labels),
                'bin_edges': [float(b) for b in bins],
                'bin_labels': bin_labels,
                'bin_statistics': bin_stats,
                'total_records': int(len(valid_data)),
                'null_records': int(len(feature_data) - len(valid_data))
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'feature': feature
            }
    
    @staticmethod
    def custom_bin(
        df: pd.DataFrame,
        feature: str,
        bins: List[float],
        include_lowest: bool = True
    ) -> Dict[str, Any]:
        """
        Bin feature with custom bin edges
        
        Args:
            df: DataFrame containing the feature
            feature: Feature name
            bins: List of bin edges
            include_lowest: Include lowest boundary
            
        Returns:
            Dictionary with binning results
        """
        try:
            if feature not in df.columns:
                raise ValueError(f"Feature '{feature}' not found in DataFrame")
            
            feature_data = df[feature].copy()
            valid_data = feature_data.dropna()
            
            # Sort bins
            bins = sorted(bins)
            
            # Perform custom binning
            binned = pd.cut(valid_data, bins=bins, include_lowest=include_lowest)
            
            # Generate bin labels
            bin_labels = []
            for i in range(len(bins) - 1):
                bin_labels.append(f"[{bins[i]:.2f}, {bins[i+1]:.2f}]")
            
            # Get bin statistics
            bin_stats = []
            for i, label in enumerate(bin_labels):
                if i < len(bins) - 1:
                    if include_lowest and i == 0:
                        mask = (valid_data >= bins[i]) & (valid_data <= bins[i+1])
                    elif i == len(bins) - 2:
                        mask = (valid_data >= bins[i]) & (valid_data <= bins[i+1])
                    else:
                        mask = (valid_data > bins[i]) & (valid_data <= bins[i+1])
                    
                    bin_values = valid_data[mask]
                    if len(bin_values) > 0:
                        bin_stats.append({
                            'bin_label': label,
                            'count': int(len(bin_values)),
                            'percentage': float(len(bin_values) / len(valid_data) * 100),
                            'min': float(bin_values.min()),
                            'max': float(bin_values.max()),
                            'mean': float(bin_values.mean()),
                            'median': float(bin_values.median()),
                            'std': float(bin_values.std())
                        })
            
            return {
                'status': 'success',
                'feature': feature,
                'method': 'custom',
                'n_bins': len(bin_labels),
                'bin_edges': [float(b) for b in bins],
                'bin_labels': bin_labels,
                'bin_statistics': bin_stats,
                'total_records': int(len(valid_data)),
                'null_records': int(len(feature_data) - len(valid_data))
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'feature': feature
            }
