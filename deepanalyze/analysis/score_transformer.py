# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false
"""
Score Transformer Module

Provides bidirectional transformation between probability and credit score.

The standard credit score scaling formula:
    Score = A - B * log(odds)
    where:
    - odds = p / (1 - p), p is the probability of default
    - A and B are constants derived from base_score, PDO, and base_odds

Key Parameters:
- base_score: Score at base odds (e.g., 660)
- pdo: Points to Double Odds (e.g., 75 points to double the odds)
- base_odds: Odds at base score (e.g., 1:50 = 0.02)

This module enables:
1. Probability → Score transformation (forward)
2. Score → Probability transformation (inverse)
3. Batch transformations
4. Score scale information retrieval
"""

import numpy as np
import pandas as pd
from typing import Any


class ScoreTransformer:
    """
    Score scale transformer for credit scoring.
    
    Implements the standard credit score scaling formula used in financial institutions.
    Supports bidirectional transformation between probability and score.
    
    Formula:
        Score = A - B * log(p / (1-p))
        where:
        - A = base_score + B * log(base_odds)
        - B = PDO / log(rate)
        - rate: odds ratio for PDO points (typically 2)
    
    Example:
        >>> transformer = ScoreTransformer(base_score=660, pdo=75, bad_rate=0.15)
        >>> transformer.fit()
        >>> scores = transformer.transform([0.1, 0.2, 0.3])  # prob → score
        >>> probs = transformer.inverse_transform([600, 700, 800])  # score → prob
    """
    
    def __init__(
        self,
        base_score: float = 660,
        pdo: float = 75,
        rate: float = 2,
        bad_rate: float = 0.15,
        down_lmt: float = 300,
        up_lmt: float = 850
    ):
        """
        Initialize ScoreTransformer.
        
        Args:
            base_score: Score at base odds (default: 660)
            pdo: Points to Double Odds - score change for doubling odds (default: 75)
            rate: Odds multiplication factor for PDO points (default: 2)
            bad_rate: Base bad rate used to calculate base odds (default: 0.15)
            down_lmt: Minimum score limit (default: 300)
            up_lmt: Maximum score limit (default: 850)
        """
        self.base_score = base_score
        self.pdo = pdo
        self.rate = rate
        self.bad_rate = bad_rate
        self.down_lmt = down_lmt
        self.up_lmt = up_lmt
        
        # Calculated parameters (set in fit())
        self.base_odds_: float = 0.0
        self.A_: float = 0.0
        self.B_: float = 0.0
        self._fitted: bool = False
        
    def fit(self, X: Any = None, y: Any = None) -> "ScoreTransformer":
        """
        Calculate scale parameters A and B.
        
        The X and y parameters are ignored (for sklearn pipeline compatibility).
        
        Returns:
            self
        """
        # Calculate base odds from bad rate
        # odds = bad / good = bad_rate / (1 - bad_rate)
        self.base_odds_ = self.bad_rate / (1 - self.bad_rate)
        
        # Calculate B: points per unit log-odds
        # PDO = B * log(rate), so B = PDO / log(rate)
        self.B_ = self.pdo / np.log(self.rate)
        
        # Calculate A: intercept
        # base_score = A - B * log(base_odds)
        # A = base_score + B * log(base_odds)
        self.A_ = self.base_score + self.B_ * np.log(self.base_odds_)
        
        self._fitted = True
        return self
    
    def _ensure_fitted(self) -> None:
        """Ensure transformer is fitted before transformation."""
        if not self._fitted:
            self.fit()
    
    def transform(self, proba: float | list | np.ndarray | pd.Series) -> np.ndarray:
        """
        Transform probability to score.
        
        Formula: Score = A - B * log(p / (1-p))
        
        Args:
            proba: Probability values (single value, list, or array)
            
        Returns:
            Score values as numpy array
        """
        self._ensure_fitted()
        
        # Convert to numpy array
        proba_arr = np.asarray(proba).ravel()
        
        # Clip probabilities to avoid log(0) or log(inf)
        proba_clipped = np.clip(proba_arr, 1e-10, 1 - 1e-10)
        
        # Calculate odds
        odds = proba_clipped / (1 - proba_clipped)
        
        # Calculate scores
        scores = self.A_ - self.B_ * np.log(odds)
        
        # Clip to score limits
        scores = np.clip(scores, self.down_lmt, self.up_lmt)
        
        return scores
    
    def inverse_transform(self, scores: float | list | np.ndarray | pd.Series) -> np.ndarray:
        """
        Transform score to probability.
        
        Formula: p = 1 / (1 + exp((A - Score) / B))
        
        Args:
            scores: Score values (single value, list, or array)
            
        Returns:
            Probability values as numpy array
        """
        self._ensure_fitted()
        
        # Convert to numpy array
        scores_arr = np.asarray(scores).ravel()
        
        # Calculate probability from score
        # Score = A - B * log(odds)
        # log(odds) = (A - Score) / B
        # odds = exp((A - Score) / B)
        # p = odds / (1 + odds) = 1 / (1 + 1/odds) = 1 / (1 + exp(-(A - Score) / B))
        proba = 1 / (1 + np.exp((self.A_ - scores_arr) / self.B_))
        
        return proba
    
    def get_scale_info(self) -> dict[str, Any]:
        """
        Get score scale parameters.
        
        Returns:
            Dictionary containing:
            - base_score: Score at base odds
            - pdo: Points to Double Odds
            - rate: Odds multiplication factor
            - bad_rate: Base bad rate
            - base_odds: Calculated base odds
            - A: Scale intercept
            - B: Scale slope
            - down_lmt: Minimum score
            - up_lmt: Maximum score
        """
        self._ensure_fitted()
        
        return {
            "base_score": self.base_score,
            "pdo": self.pdo,
            "rate": self.rate,
            "bad_rate": round(self.bad_rate, 4),
            "base_odds": round(self.base_odds_, 4),
            "A": round(self.A_, 2),
            "B": round(self.B_, 2),
            "down_lmt": self.down_lmt,
            "up_lmt": self.up_lmt,
        }
    
    def convert(
        self,
        values: float | list | np.ndarray,
        direction: str = "to_score"
    ) -> list[dict[str, float]]:
        """
        Convert values with input/output pairs.
        
        Args:
            values: Values to convert
            direction: "to_score" (prob→score) or "to_prob" (score→prob)
            
        Returns:
            List of dicts with 'input' and 'output' keys
        """
        self._ensure_fitted()
        
        values_arr = np.asarray(values).ravel()
        
        if direction == "to_score":
            outputs = self.transform(values_arr)
        elif direction == "to_prob":
            outputs = self.inverse_transform(values_arr)
        else:
            raise ValueError(f"Invalid direction: {direction}. Use 'to_score' or 'to_prob'.")
        
        return [
            {"input": float(v), "output": round(float(o), 4)}
            for v, o in zip(values_arr, outputs)
        ]
    
    def score_to_rating(
        self,
        scores: float | list | np.ndarray,
        rating_breaks: list[float] | None = None,
        rating_labels: list[str] | None = None
    ) -> np.ndarray:
        """
        Convert scores to rating grades.
        
        Args:
            scores: Score values
            rating_breaks: Score breakpoints for ratings (default: standard breaks)
            rating_labels: Rating labels (default: AAA to D)
            
        Returns:
            Rating grades as numpy array
        """
        if rating_breaks is None:
            rating_breaks = [0, 550, 600, 650, 700, 750, 800, float('inf')]
        
        if rating_labels is None:
            rating_labels = ['D', 'C', 'B', 'BB', 'BBB', 'A', 'AA']
        
        scores_arr = np.asarray(scores).ravel()
        
        # Use pd.cut for binning
        ratings = pd.cut(
            scores_arr,
            bins=rating_breaks,
            labels=rating_labels,
            right=False
        )
        
        return np.asarray(ratings)
    
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
        
        probs = np.linspace(prob_range[0], prob_range[1], n_points)
        scores = self.transform(probs)
        odds = probs / (1 - probs)
        
        return pd.DataFrame({
            "probability": np.round(probs, 4),
            "score": np.round(scores, 0).astype(int),
            "odds": np.round(odds, 4),
        })


def create_score_transformer(
    base_score: float = 660,
    pdo: float = 75,
    bad_rate: float = 0.15,
    **kwargs: Any
) -> ScoreTransformer:
    """
    Convenience function to create and fit a ScoreTransformer.
    
    Args:
        base_score: Score at base odds
        pdo: Points to Double Odds
        bad_rate: Base bad rate
        **kwargs: Additional arguments for ScoreTransformer
        
    Returns:
        Fitted ScoreTransformer instance
    """
    transformer = ScoreTransformer(
        base_score=base_score,
        pdo=pdo,
        bad_rate=bad_rate,
        **kwargs
    )
    transformer.fit()
    return transformer
