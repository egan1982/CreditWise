# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false
"""
Statistical Logistic Regression Model

Provides logistic regression with comprehensive statistical information output,
similar to statsmodels but based on sklearn for better compatibility.

Features:
- Standard errors for coefficients (based on Hessian matrix)
- Z-statistics and p-values
- Confidence intervals (95%)
- Model fit statistics (pseudo R², log-likelihood)

This module bridges the gap between sklearn's LogisticRegression and
statsmodels' detailed statistical output.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from scipy import stats
from typing import Any


class StatisticalLogisticRegression(LogisticRegression):
    """
    Logistic Regression with statistical information output.
    
    Extends sklearn's LogisticRegression to provide:
    - Coefficient standard errors
    - Z-statistics and p-values
    - 95% confidence intervals
    - Model fit statistics (pseudo R², log-likelihood, AIC, BIC)
    
    Example:
        >>> model = StatisticalLogisticRegression(calculate_stats=True)
        >>> model.fit(X_train, y_train)
        >>> stats = model.summary()
        >>> print(stats['summary'])  # DataFrame with coef, std_err, z, p_value, etc.
    """
    
    def __init__(
        self,
        calculate_stats: bool = True,
        penalty: str | None = None,
        C: float = 1e10,  # Very large C for minimal regularization (like statsmodels)
        solver: str = 'lbfgs',
        max_iter: int = 1000,
        fit_intercept: bool = True,
        class_weight: dict | str | None = None,
        random_state: int | None = None,
        **kwargs: Any
    ):
        """
        Initialize StatisticalLogisticRegression.
        
        Args:
            calculate_stats: Whether to calculate statistical information after fit
            penalty: Regularization penalty (None for no regularization, recommended for stats)
            C: Inverse of regularization strength (large = weak regularization)
            solver: Optimization algorithm
            max_iter: Maximum iterations for solver
            fit_intercept: Whether to fit intercept term
            class_weight: Class weights for imbalanced data
            random_state: Random seed
            **kwargs: Additional arguments passed to LogisticRegression
        """
        super().__init__(
            penalty=penalty,
            C=C,
            solver=solver,
            max_iter=max_iter,
            fit_intercept=fit_intercept,
            class_weight=class_weight,
            random_state=random_state,
            **kwargs
        )
        self.calculate_stats = calculate_stats
        self._stats: pd.DataFrame | None = None
        self._model_info: dict[str, Any] = {}
        self._feature_names: list[str] = []
        
    def fit(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        sample_weight: np.ndarray | None = None,
        **kwargs: Any
    ) -> "StatisticalLogisticRegression":
        """
        Fit the model and calculate statistical information.
        
        Args:
            X: Feature matrix
            y: Target vector
            sample_weight: Sample weights (optional)
            **kwargs: Additional arguments
            
        Returns:
            self
        """
        # Store feature names
        if isinstance(X, pd.DataFrame):
            self._feature_names = X.columns.tolist()
            X_array = X.values
        else:
            self._feature_names = [f"x{i}" for i in range(X.shape[1])]
            X_array = np.asarray(X)
            
        # Convert y to array
        y_array = np.asarray(y).ravel()
        
        # Fit the model
        super().fit(X_array, y_array, sample_weight=sample_weight)
        
        # Calculate statistics if requested
        if self.calculate_stats:
            self._calculate_statistics(X_array, y_array)
            
        return self
    
    def _calculate_statistics(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Calculate statistical information based on Hessian matrix.
        
        Uses the inverse of the Hessian (information matrix) to estimate
        the covariance matrix of coefficients, from which standard errors,
        z-statistics, and p-values are derived.
        
        Args:
            X: Feature matrix (numpy array)
            y: Target vector (numpy array)
        """
        n_samples, n_features = X.shape
        
        # Build design matrix with intercept if needed
        if self.fit_intercept:
            X_design = np.column_stack([np.ones(n_samples), X])
            coefs = np.concatenate([[self.intercept_[0]], self.coef_[0]])
            feature_names = ["const"] + self._feature_names
        else:
            X_design = X
            coefs = self.coef_[0]
            feature_names = self._feature_names
        
        n_params = len(coefs)
        
        # Get predicted probabilities
        proba = self.predict_proba(X)[:, 1]
        
        # Ensure probabilities are bounded away from 0 and 1
        proba = np.clip(proba, 1e-10, 1 - 1e-10)
        
        # Calculate Hessian matrix (negative second derivative of log-likelihood)
        # H = X^T * W * X, where W = diag(p * (1-p))
        W = proba * (1 - proba)
        
        # Compute Hessian efficiently
        # H_ij = sum_k X_ki * W_k * X_kj
        H = (X_design.T * W) @ X_design
        
        # Compute covariance matrix as inverse of Hessian
        try:
            # Try standard inverse first
            cov_matrix = np.linalg.inv(H)
            std_errors = np.sqrt(np.diag(cov_matrix))
        except np.linalg.LinAlgError:
            # If singular, try pseudo-inverse
            try:
                cov_matrix = np.linalg.pinv(H)
                std_errors = np.sqrt(np.maximum(np.diag(cov_matrix), 0))
            except Exception:
                std_errors = np.full(n_params, np.nan)
        
        # Calculate z-statistics
        with np.errstate(divide='ignore', invalid='ignore'):
            z_stats = coefs / std_errors
            z_stats = np.where(np.isfinite(z_stats), z_stats, np.nan)
        
        # Calculate p-values (two-tailed test)
        p_values = 2 * (1 - stats.norm.cdf(np.abs(z_stats)))
        p_values = np.where(np.isfinite(p_values), p_values, np.nan)
        
        # Calculate 95% confidence intervals
        ci_lower = coefs - 1.96 * std_errors
        ci_upper = coefs + 1.96 * std_errors
        
        # Build statistics DataFrame
        self._stats = pd.DataFrame({
            "feature": feature_names,
            "coef": np.round(coefs, 6),
            "std_err": np.round(std_errors, 6),
            "z": np.round(z_stats, 4),
            "p_value": np.round(p_values, 6),
            "ci_lower": np.round(ci_lower, 6),
            "ci_upper": np.round(ci_upper, 6),
        })
        
        # Add significance markers
        self._stats["significance"] = self._stats["p_value"].apply(self._get_significance_marker)
        
        # Calculate model fit statistics
        self._calculate_model_fit_stats(X, y, proba, n_params)
    
    def _get_significance_marker(self, p_value: float) -> str:
        """Get significance marker based on p-value."""
        if pd.isna(p_value):
            return ""
        if p_value < 0.001:
            return "***"
        elif p_value < 0.01:
            return "**"
        elif p_value < 0.05:
            return "*"
        elif p_value < 0.1:
            return "."
        return ""
    
    def _calculate_model_fit_stats(
        self,
        X: np.ndarray,
        y: np.ndarray,
        proba: np.ndarray,
        n_params: int
    ) -> None:
        """
        Calculate model fit statistics.
        
        Args:
            X: Feature matrix
            y: Target vector
            proba: Predicted probabilities
            n_params: Number of parameters in the model
        """
        n_samples = len(y)
        
        # Log-likelihood of fitted model
        log_likelihood = np.sum(
            y * np.log(proba + 1e-10) + 
            (1 - y) * np.log(1 - proba + 1e-10)
        )
        
        # Log-likelihood of null model (intercept only)
        null_proba = np.mean(y)
        null_log_likelihood = np.sum(
            y * np.log(null_proba + 1e-10) + 
            (1 - y) * np.log(1 - null_proba + 1e-10)
        )
        
        # McFadden's pseudo R-squared
        pseudo_r2 = 1 - (log_likelihood / null_log_likelihood) if null_log_likelihood != 0 else 0
        
        # AIC and BIC
        aic = -2 * log_likelihood + 2 * n_params
        bic = -2 * log_likelihood + np.log(n_samples) * n_params
        
        # Likelihood ratio test
        lr_stat = -2 * (null_log_likelihood - log_likelihood)
        lr_pvalue = 1 - stats.chi2.cdf(lr_stat, n_params - 1) if n_params > 1 else np.nan
        
        self._model_info = {
            "n_observations": n_samples,
            "n_features": X.shape[1],
            "n_params": n_params,
            "log_likelihood": round(log_likelihood, 4),
            "null_log_likelihood": round(null_log_likelihood, 4),
            "pseudo_r2": round(pseudo_r2, 4),
            "aic": round(aic, 4),
            "bic": round(bic, 4),
            "lr_stat": round(lr_stat, 4),
            "lr_pvalue": round(lr_pvalue, 6) if not np.isnan(lr_pvalue) else None,
        }
    
    def summary(self) -> dict[str, Any]:
        """
        Get model summary with statistical information.
        
        Returns:
            Dictionary containing:
            - summary: List of coefficient statistics (for JSON serialization)
            - n_observations: Number of samples
            - n_features: Number of features
            - n_params: Number of parameters
            - log_likelihood: Log-likelihood of fitted model
            - null_log_likelihood: Log-likelihood of null model
            - pseudo_r2: McFadden's pseudo R-squared
            - aic: Akaike Information Criterion
            - bic: Bayesian Information Criterion
            - lr_stat: Likelihood ratio test statistic
            - lr_pvalue: Likelihood ratio test p-value
            
        Raises:
            ValueError: If model hasn't been fitted or stats weren't calculated
        """
        if self._stats is None:
            raise ValueError(
                "Model statistics not available. "
                "Ensure calculate_stats=True and model is fitted."
            )
        
        return {
            "summary": self._stats.to_dict(orient="records"),
            **self._model_info
        }
    
    def summary_dataframe(self) -> pd.DataFrame:
        """
        Get coefficient statistics as DataFrame.
        
        Returns:
            DataFrame with columns: feature, coef, std_err, z, p_value, ci_lower, ci_upper, significance
        """
        if self._stats is None:
            raise ValueError("Model statistics not available.")
        return self._stats.copy()
    
    def print_summary(self) -> None:
        """Print formatted model summary to console."""
        if self._stats is None:
            print("Model statistics not available.")
            return
        
        print("=" * 80)
        print("Statistical Logistic Regression Results")
        print("=" * 80)
        print(f"Observations: {self._model_info.get('n_observations', 'N/A')}")
        print(f"Features: {self._model_info.get('n_features', 'N/A')}")
        print(f"Log-Likelihood: {self._model_info.get('log_likelihood', 'N/A')}")
        print(f"Pseudo R²: {self._model_info.get('pseudo_r2', 'N/A')}")
        print(f"AIC: {self._model_info.get('aic', 'N/A')}")
        print(f"BIC: {self._model_info.get('bic', 'N/A')}")
        print("-" * 80)
        print("\nCoefficients:")
        print(self._stats.to_string(index=False))
        print("\n" + "=" * 80)
        print("Significance: *** p<0.001, ** p<0.01, * p<0.05, . p<0.1")


def fit_statistical_logistic_regression(
    X: np.ndarray | pd.DataFrame,
    y: np.ndarray | pd.Series,
    **kwargs: Any
) -> tuple[StatisticalLogisticRegression, dict[str, Any]]:
    """
    Convenience function to fit statistical logistic regression.
    
    Args:
        X: Feature matrix
        y: Target vector
        **kwargs: Additional arguments for StatisticalLogisticRegression
        
    Returns:
        Tuple of (fitted model, summary dict)
        
    Example:
        >>> model, stats = fit_statistical_logistic_regression(X_train, y_train)
        >>> print(stats['pseudo_r2'])
    """
    model = StatisticalLogisticRegression(**kwargs)
    model.fit(X, y)
    return model, model.summary()
