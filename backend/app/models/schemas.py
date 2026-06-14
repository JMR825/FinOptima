"""Pydantic request/response models for the portfolio optimization API."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

DashboardMode = Literal["daily", "intraday"]


class MarketDataOptions(BaseModel):
    """Shared market data parameters for all analysis endpoints."""

    mode: DashboardMode = Field("daily", description="Dashboard mode: daily (Trading Day) or intraday")
    interval: Optional[str] = Field(None, description="yfinance interval override (e.g. 5m, 15m, 1h, 1d)")
    period: Optional[str] = Field(None, description="yfinance period override (e.g. 1y, 5d, 1mo)")
    refresh_cache: bool = Field(False, description="Force re-download from yfinance even if cache exists")


class LiveDataRequest(MarketDataOptions):
    symbols: List[str] = Field(..., min_length=1, max_length=10)


class AnalyzeRequest(MarketDataOptions):
    symbols: List[str] = Field(..., min_length=1, max_length=10)
    period_type: DashboardMode = "daily"  # backward compat alias for mode


class PredictRequest(MarketDataOptions):
    symbols: List[str] = Field(..., min_length=1, max_length=10)
    prediction_mode: Literal["regression", "lstm", "ensemble"] = "ensemble"
    enable_lstm: Optional[bool] = None
    period_type: DashboardMode = "daily"


class ClusterRequest(MarketDataOptions):
    symbols: List[str] = Field(..., min_length=1, max_length=10)
    period_type: DashboardMode = "daily"


class OptimizeRequest(MarketDataOptions):
    symbols: List[str] = Field(..., min_length=1, max_length=10)
    budget: float = Field(10000, gt=0)
    risk_preference: Literal["low", "medium", "high"] = "medium"
    optimization_goal: Literal["max_sharpe", "min_volatility"] = "max_sharpe"
    period_type: DashboardMode = "daily"


class FullAnalysisRequest(MarketDataOptions):
    symbols: List[str] = Field(..., min_length=1, max_length=10)
    budget: float = Field(10000, gt=0)
    risk_preference: Literal["low", "medium", "high"] = "medium"
    optimization_goal: Literal["max_sharpe", "min_volatility"] = "max_sharpe"
    prediction_mode: Literal["regression", "lstm", "ensemble"] = "ensemble"
    enable_lstm: bool = True
    period_type: DashboardMode = "daily"


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
    mode: str
    live_prices: List[LivePrice]
    predictions: List[StockPrediction]
    portfolio: PortfolioMetrics
    risk_analysis: RiskAnalysis
    price_history: Dict[str, List[PricePoint]]
    cluster_summary: Dict[str, Any]
    model_comparison: Dict[str, Any]
    warnings: List[str] = []
