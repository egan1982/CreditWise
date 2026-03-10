"""
[ARCHIVED] Scorecard API - WOE/IV Analysis Endpoints

Provides RESTful API endpoints for scorecard analysis, WOE calculation, 
and feature importance evaluation.

NOTE: This router is NOT registered in create_app() and has no effect at runtime.
      Scorecard analysis is served via the SOP task pipeline (/sop/*).
      The standalone /v1/scorecard/* endpoints here were never deployed.
      See docs/routing_architecture_guide.md for the authoritative route map.
      Retained for reference only — do not import or register without review.
"""

import json
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from fastapi import APIRouter, Body, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
import logging
import io

from deepanalyze.analysis.woe import WOECalculator
from deepanalyze.analysis.feature_binning import FeatureBinner
from deepanalyze.analysis.iv_analysis import IVAnalyzer

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1/scorecard", tags=["scorecard"])


# Request/Response Models
class WOECalculationRequest(BaseModel):
    """WOE calculation request model"""
    data: List[Dict[str, Any]] = Field(..., description="Data records")
    feature: str = Field(..., description="Feature column name")
    target: str = Field(..., description="Target column name (binary: 0/1)")
    n_bins: int = Field(default=5, ge=2, le=20, description="Number of bins")
    method: str = Field(default='quantile', description="Binning method: quantile, uniform, kmeans")


class IVAnalysisRequest(BaseModel):
    """IV analysis request model"""
    data: List[Dict[str, Any]] = Field(..., description="Data records")
    target: str = Field(..., description="Target column name")
    features: Optional[List[str]] = Field(default=None, description="Feature list (None = all numeric)")
    n_bins: int = Field(default=5, ge=2, le=20, description="Number of bins")
    method: str = Field(default='quantile', description="Binning method")


class FeatureSelectionRequest(BaseModel):
    """Feature selection request model"""
    data: List[Dict[str, Any]] = Field(..., description="Data records")
    target: str = Field(..., description="Target column name")
    iv_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="IV threshold")
    features: Optional[List[str]] = Field(default=None, description="Feature list (None = all numeric)")


class FeatureBinningRequest(BaseModel):
    """Feature binning request model"""
    data: List[Dict[str, Any]] = Field(..., description="Data records")
    feature: str = Field(..., description="Feature column name")
    n_bins: int = Field(default=5, ge=2, le=20, description="Number of bins")
    method: str = Field(default='quantile', description="Binning method: quantile, uniform, kmeans")


class CustomBinningRequest(BaseModel):
    """Custom binning request model"""
    data: List[Dict[str, Any]] = Field(..., description="Data records")
    feature: str = Field(..., description="Feature column name")
    bins: List[float] = Field(..., description="Bin edges")


class ScorecardRequest(BaseModel):
    """Scorecard building request model"""
    data: List[Dict[str, Any]] = Field(..., description="Training data")
    target: str = Field(..., description="Target column name")
    features: List[str] = Field(..., description="Feature list")
    iv_threshold: float = Field(default=0.1, description="IV threshold for feature selection")


# Helper functions
def _dataframe_from_list(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert list of dicts to DataFrame"""
    if not data:
        raise ValueError("Empty data provided")
    return pd.DataFrame(data)


def _validate_data(df: pd.DataFrame) -> None:
    """Validate DataFrame"""
    if df.empty:
        raise ValueError("DataFrame is empty")
    if len(df) < 10:
        raise ValueError("Insufficient data (minimum 10 records required)")


# API Endpoints

@router.post("/woe")
async def calculate_woe(request: WOECalculationRequest):
    """
    Calculate Weight of Evidence (WOE) for a feature
    
    Returns WOE values, IV score, bin statistics, and strength interpretation
    """
    try:
        # Convert data to DataFrame
        df = _dataframe_from_list(request.data)
        _validate_data(df)
        
        # Calculate WOE
        result = WOECalculator.calculate_woe(
            df,
            request.feature,
            request.target,
            request.n_bins,
            request.method
        )
        
        if result.get('status') == 'error':
            raise ValueError(result.get('error', 'WOE calculation failed'))
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"WOE calculation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="WOE calculation failed")


@router.post("/iv")
async def analyze_iv(request: IVAnalysisRequest):
    """
    Analyze Information Value (IV) for multiple features
    
    Returns IV scores for all features ranked by importance
    """
    try:
        # Convert data to DataFrame
        df = _dataframe_from_list(request.data)
        _validate_data(df)
        
        # Analyze IV
        result = IVAnalyzer.analyze_features(
            df,
            request.target,
            request.features,
            request.n_bins,
            request.method
        )
        
        if result.get('status') == 'error':
            raise ValueError(result.get('error', 'IV analysis failed'))
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"IV analysis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="IV analysis failed")


@router.post("/feature-selection")
async def select_features(request: FeatureSelectionRequest):
    """
    Select important features based on IV threshold
    
    Returns list of selected features and analysis details
    """
    try:
        # Convert data to DataFrame
        df = _dataframe_from_list(request.data)
        _validate_data(df)
        
        # Feature selection
        result = IVAnalyzer.feature_selection(
            df,
            request.target,
            request.iv_threshold,
            request.features
        )
        
        if result.get('status') == 'error':
            raise ValueError(result.get('error', 'Feature selection failed'))
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Feature selection error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="Feature selection failed")


@router.post("/binning")
async def bin_feature(request: FeatureBinningRequest):
    """
    Auto-bin a continuous feature
    
    Returns bin edges, bin statistics, and distribution information
    """
    try:
        # Convert data to DataFrame
        df = _dataframe_from_list(request.data)
        _validate_data(df)
        
        # Bin feature
        result = FeatureBinner.auto_bin(
            df,
            request.feature,
            request.n_bins,
            request.method
        )
        
        if result.get('status') == 'error':
            raise ValueError(result.get('error', 'Binning failed'))
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Feature binning error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="Feature binning failed")


@router.post("/custom-binning")
async def custom_bin_feature(request: CustomBinningRequest):
    """
    Bin a feature with custom bin edges
    
    Returns bin statistics with custom bin edges
    """
    try:
        # Convert data to DataFrame
        df = _dataframe_from_list(request.data)
        _validate_data(df)
        
        # Custom binning
        result = FeatureBinner.custom_bin(
            df,
            request.feature,
            request.bins
        )
        
        if result.get('status') == 'error':
            raise ValueError(result.get('error', 'Custom binning failed'))
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Custom binning error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="Custom binning failed")


@router.post("/scorecard")
async def build_scorecard(request: ScorecardRequest):
    """
    Build a credit scorecard
    
    Performs feature selection, WOE encoding, and scorecard building
    """
    try:
        # Convert data to DataFrame
        df = _dataframe_from_list(request.data)
        _validate_data(df)
        
        # Step 1: Select important features
        selection_result = IVAnalyzer.feature_selection(
            df,
            request.target,
            request.iv_threshold,
            request.features
        )
        
        if selection_result.get('status') != 'success':
            raise ValueError("Feature selection failed")
        
        selected_features = selection_result['selected_features']
        
        if not selected_features:
            raise ValueError(f"No features selected with IV threshold {request.iv_threshold}")
        
        # Step 2: Calculate WOE for each selected feature
        woe_results = []
        for feature in selected_features:
            woe = WOECalculator.calculate_woe(df, feature, request.target)
            if woe.get('status') == 'success':
                woe_results.append(woe)
        
        # Step 3: Generate scorecard
        scorecard = {
            'features': selected_features,
            'woe_results': woe_results,
            'feature_count': len(selected_features),
            'parameters': {
                'iv_threshold': request.iv_threshold,
                'total_features': len(request.features)
            }
        }
        
        return {
            "status": "success",
            "data": {
                'scorecard': scorecard,
                'feature_selection': selection_result,
                'woe_details': woe_results
            }
        }
        
    except Exception as e:
        logger.error(f"Scorecard building error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="Scorecard building failed")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "scorecard-api"
    }
