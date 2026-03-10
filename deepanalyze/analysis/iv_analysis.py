"""
Information Value (IV) Analysis Module

Provides IV calculation and feature importance analysis for feature selection.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from .woe import WOECalculator
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)


class IVAnalyzer:
    """Information Value (IV) analyzer for feature importance assessment"""
    
    @staticmethod
    def analyze_features(
        df: pd.DataFrame,
        target: str,
        features: Optional[List[str]] = None,
        n_bins: int = 5,
        method: str = 'quantile'
    ) -> Dict[str, Any]:
        """
        Analyze IV for multiple features
        
        Args:
            df: DataFrame containing features and target
            target: Target variable name (binary 0/1)
            features: List of feature names to analyze (None = all numeric)
            n_bins: Number of bins for discretization
            method: Binning method ('quantile', 'uniform', 'kmeans')
            
        Returns:
            Dictionary with IV analysis results for all features
        """
        try:
            if target not in df.columns:
                raise ValueError(f"Target '{target}' not found in DataFrame")
            
            # Auto-select numeric features if not provided
            if features is None:
                features = df.select_dtypes(include=[np.number]).columns.tolist()
                if target in features:
                    features.remove(target)
            
            if not features:
                raise ValueError("No numeric features found to analyze")
            
            results = []
            
            for feature in features:
                if feature not in df.columns:
                    results.append({
                        'feature': feature,
                        'iv': 0.0,
                        'status': 'error',
                        'error': f"Feature '{feature}' not found"
                    })
                    continue
                
                # Skip non-numeric features
                if not pd.api.types.is_numeric_dtype(df[feature]):
                    results.append({
                        'feature': feature,
                        'iv': 0.0,
                        'status': 'skipped',
                        'reason': 'Non-numeric feature'
                    })
                    continue
                
                # Calculate WOE (which includes IV)
                woe_result = WOECalculator.calculate_woe(
                    df, feature, target, n_bins, method
                )
                
                if woe_result.get('status') == 'success':
                    results.append({
                        'feature': feature,
                        'iv': woe_result['iv'],
                        'strength': woe_result['strength'],
                        'interpretation': woe_result['interpretation'],
                        'predictive': woe_result['predictive'],
                        'n_bins': woe_result['n_bins'],
                        'status': 'success'
                    })
                else:
                    results.append({
                        'feature': feature,
                        'iv': 0.0,
                        'status': 'error',
                        'error': woe_result.get('error', 'Unknown error')
                    })
            
            # Sort by IV in descending order
            successful_results = [r for r in results if r.get('status') == 'success']
            successful_results.sort(key=lambda x: x['iv'], reverse=True)
            
            failed_results = [r for r in results if r.get('status') != 'success']
            
            all_results = successful_results + failed_results
            
            # Add ranking
            for i, result in enumerate(successful_results):
                result['rank'] = i + 1
            
            return {
                'status': 'success',
                'target': target,
                'total_features': len(features),
                'analyzed_features': len(successful_results),
                'skipped_features': len([r for r in results if r.get('status') == 'skipped']),
                'error_features': len([r for r in results if r.get('status') == 'error']),
                'results': all_results,
                'summary': IVAnalyzer._generate_summary(successful_results)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'results': []
            }
    
    @staticmethod
    def feature_selection(
        df: pd.DataFrame,
        target: str,
        iv_threshold: float = 0.1,
        features: Optional[List[str]] = None,
        n_bins: int = 5,
        method: str = 'quantile'
    ) -> Dict[str, Any]:
        """
        Select features based on IV threshold
        
        Args:
            df: DataFrame containing features and target
            target: Target variable name (binary 0/1)
            iv_threshold: IV threshold for feature selection
            features: List of feature names to analyze (None = all numeric)
            n_bins: Number of bins for discretization
            method: Binning method
            
        Returns:
            Dictionary with selected features and analysis
        """
        try:
            # First analyze all features
            analysis_result = IVAnalyzer.analyze_features(
                df, target, features, n_bins, method
            )
            
            if analysis_result.get('status') != 'success':
                return analysis_result
            
            # Filter features by IV threshold
            results = analysis_result['results']
            selected_features = [
                r for r in results 
                if r.get('status') == 'success' and r['iv'] >= iv_threshold
            ]
            
            selected_feature_names = [f['feature'] for f in selected_features]
            
            return {
                'status': 'success',
                'target': target,
                'iv_threshold': iv_threshold,
                'total_features': len(results),
                'selected_count': len(selected_features),
                'selected_features': selected_feature_names,
                'selection_details': selected_features,
                'removed_features': [
                    r for r in results 
                    if r.get('status') == 'success' and r['iv'] < iv_threshold
                ]
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'selected_features': []
            }
    
    @staticmethod
    def _generate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from IV analysis results"""
        if not results:
            return {
                'total_features': 0,
                'avg_iv': 0.0,
                'max_iv': 0.0,
                'min_iv': 0.0,
                'strong_predictors': 0,
                'medium_predictors': 0,
                'weak_predictors': 0
            }
        
        iv_values = [r['iv'] for r in results if 'iv' in r]
        
        strong = len([r for r in results if r.get('iv', 0) >= 0.3])
        medium = len([r for r in results if 0.1 <= r.get('iv', 0) < 0.3])
        weak = len([r for r in results if 0.02 <= r.get('iv', 0) < 0.1])
        
        return {
            'total_features': len(results),
            'avg_iv': float(np.mean(iv_values)) if iv_values else 0.0,
            'max_iv': float(np.max(iv_values)) if iv_values else 0.0,
            'min_iv': float(np.min(iv_values)) if iv_values else 0.0,
            'strong_predictors': strong,
            'medium_predictors': medium,
            'weak_predictors': weak
        }
