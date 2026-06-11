"""Pydantic request/response models for the portfolio optimization API."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StockInput(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=10)
    budget: float = Field(10000, gt=0)
    risk_preference: Literal["low", "medium", "high"] = "medium"
    prediction_mode: Literal["regression", "lstm", "ensemble"] = "ensemble"
    optimization_goal: Literal["max_sharpe", "min_volatility"] = "max_sharpe"
    enable_lstm: Optional[bool] = None


class LiveDataRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=10)


class AnalyzeRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=10)


class PredictRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=10)
    prediction_mode: Literal["regression", "lstm", "ensemble"] = "ensemble"
    enable_lstm: Optional[bool] = None


class ClusterRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=10)


class OptimizeRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=10)
    budget: float = Field(10000, gt=0)
    risk_preference: Literal["low", "medium", "high"] = "medium"
    optimization_goal: Literal["max_sharpe", "min_volatility"] = "max_sharpe"


class FullAnalysisRequest(StockInput):
    refresh_predictions: bool = True


class PricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class LivePrice(BaseModel):
    symbol: str
    price: float
    change_pct: Optional[float] = None
    last_updated: str
    source: str


class StockPrediction(BaseModel):
    symbol: str
    latest_price: float
    predicted_return: float
    trend: Literal["upward", "downward", "neutral"]
    confidence: float
    model_used: str
    cluster_label: int


class PortfolioMetrics(BaseModel):
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    weights: Dict[str, float]
    recommendation_summary: str


class RiskAnalysis(BaseModel):
    volatility: Dict[str, float]
    sharpe_ratio: Dict[str, float]
    max_drawdown: Dict[str, float]
    correlation_matrix: Dict[str, Dict[str, float]]


class FullAnalysisResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    data_source: str
    live_prices: List[LivePrice]
    predictions: List[StockPrediction]
    portfolio: PortfolioMetrics
    risk_analysis: RiskAnalysis
    price_history: Dict[str, List[PricePoint]]
    cluster_summary: Dict[str, Any]
    model_comparison: Dict[str, Any]
    warnings: List[str] = []
