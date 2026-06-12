"""
FastAPI route handlers for the portfolio optimization system.

Endpoints:
  GET  /api/health
  POST /api/live-data
  POST /api/analyze
  POST /api/predict
  POST /api/cluster
  POST /api/optimize
  POST /api/full-analysis
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.schemas import (
    AnalyzeRequest,
    ClusterRequest,
    FullAnalysisRequest,
    LiveDataRequest,
    OptimizeRequest,
    PredictRequest,
    StockInput,
)
from app.services.clustering import apply_cluster_labels, cluster_stocks
from app.services.lstm_predictor import ensemble_predictions, predict_all_lstm
from app.services.market_data_service import MarketDataService
from app.services.optimizer import optimize_portfolio
from app.services.output_formatter import (
    build_full_response,
    format_price_history,
    format_risk_analysis,
)
from app.services.preprocessing import preprocess_all
from app.services.regression_predictor import predict_all_regression
from app.services.risk_metrics import compute_per_asset_risk, correlation_matrix
from app.utils.exceptions import PortfolioOptimizerError

router = APIRouter(prefix="/api")
market_service = MarketDataService()


async def _fetch_and_preprocess(symbols: List[str]):
    symbols = [s.upper().strip() for s in symbols]
    price_data, errors = await market_service.fetch_daily_prices(symbols)
    if not price_data:
        raise HTTPException(status_code=400, detail={"errors": errors, "message": "No data fetched"})
    processed = preprocess_all(price_data)
    return price_data, processed, errors


@router.get("/health")
async def health_check():
    settings = get_settings()
    return {
        "status": "healthy",
        "provider": settings.market_data_provider,
        "api_key_configured": bool(settings.alpha_vantage_api_key),
        "lstm_enabled": settings.enable_lstm,
    }


@router.post("/live-data")
async def live_data(request: LiveDataRequest):
    """Fetch latest market prices (real-time market data refresh)."""
    live_prices, errors = await market_service.fetch_live_prices(request.symbols)
    return {
        "live_prices": live_prices,
        "data_source": market_service.data_source,
        "warnings": market_service.warnings + errors,
    }


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """Preprocess data and compute risk metrics."""
    _, processed, errors = await _fetch_and_preprocess(request.symbols)
    per_asset = compute_per_asset_risk(processed)
    corr = correlation_matrix(processed)
    return {
        "risk_analysis": format_risk_analysis(per_asset, corr),
        "symbols_analyzed": list(processed.keys()),
        "warnings": market_service.warnings + errors,
    }


@router.post("/predict")
async def predict(request: PredictRequest):
    """Run ML predictions (real-time prediction refresh)."""
    settings = get_settings()
    _, processed, errors = await _fetch_and_preprocess(request.symbols)

    reg_preds, model_comparison = predict_all_regression(processed)
    enable_lstm = request.enable_lstm if request.enable_lstm is not None else settings.enable_lstm

    if request.prediction_mode in ("lstm", "ensemble") and enable_lstm:
        lstm_preds = predict_all_lstm(processed)
        if request.prediction_mode == "ensemble":
            predictions = ensemble_predictions(reg_preds, lstm_preds)
        else:
            predictions = lstm_preds if lstm_preds else reg_preds
    else:
        predictions = reg_preds

    return {
        "predictions": predictions,
        "model_comparison": model_comparison,
        "warnings": market_service.warnings + errors,
    }


@router.post("/cluster")
async def cluster(request: ClusterRequest):
    """Cluster stocks by risk/return features."""
    _, processed, errors = await _fetch_and_preprocess(request.symbols)
    label_map, summary = cluster_stocks(processed)
    return {
        "cluster_labels": label_map,
        "cluster_summary": summary,
        "warnings": market_service.warnings + errors,
    }


@router.post("/optimize")
async def optimize(request: OptimizeRequest):
    """Optimize portfolio weights."""
    _, processed, errors = await _fetch_and_preprocess(request.symbols)
    reg_preds, _ = predict_all_regression(processed)
    portfolio = optimize_portfolio(
        processed,
        reg_preds,
        request.budget,
        request.risk_preference,
        request.optimization_goal,
    )
    return {
        "portfolio": portfolio,
        "warnings": market_service.warnings + errors,
    }


@router.post("/full-analysis")
async def full_analysis(request: FullAnalysisRequest):
    """
    Run the complete pipeline and return dashboard-ready JSON.

    Separates:
    - Market data fetch (live prices from provider)
    - Prediction recompute (regression, optional LSTM, clustering, optimization)
    """
    settings = get_settings()
    symbols = [s.upper().strip() for s in request.symbols]

    try:
        price_data, errors = await market_service.fetch_daily_prices(symbols)
        if not price_data:
            raise HTTPException(
                status_code=400,
                detail={"message": "Could not fetch data for any symbol", "errors": errors},
            )
        if len(price_data) == 1:
    single_sym = list(price_data.keys())
    return JSONResponse(
        status_code=400,
        content={
            "detail": {
                "message": f"Optimization requires at least 2 tickers. Please add another stock alongside {single_sym} to optimize weights.",
                "errors": errors
            }
        }
    )
        live_prices, live_errors = await market_service.fetch_live_prices(symbols)
        processed = preprocess_all(price_data)

        # Predictions
        reg_preds, model_comparison = predict_all_regression(processed)
        enable_lstm = request.enable_lstm if request.enable_lstm is not None else settings.enable_lstm

        if request.prediction_mode in ("lstm", "ensemble") and enable_lstm:
            lstm_preds = predict_all_lstm(processed)
            if request.prediction_mode == "ensemble":
                predictions = ensemble_predictions(reg_preds, lstm_preds)
            elif lstm_preds:
                predictions = lstm_preds
            else:
                predictions = reg_preds
        else:
            predictions = reg_preds

        # Clustering
        label_map, cluster_summary = cluster_stocks(processed)
        predictions = apply_cluster_labels(predictions, label_map)

        # Merge weights into predictions
        portfolio = optimize_portfolio(
            processed,
            predictions,
            request.budget,
            request.risk_preference,
            request.optimization_goal,
        )
        weight_map = portfolio["weights"]
        for pred in predictions:
            pred["suggested_weight"] = weight_map.get(pred["symbol"], 0.0)

        # Risk analysis
        per_asset = compute_per_asset_risk(processed)
        corr = correlation_matrix(processed)
        risk_analysis = format_risk_analysis(per_asset, corr)
        price_history = format_price_history(price_data)

        all_warnings = market_service.warnings + errors + live_errors

        return build_full_response(
            live_prices=live_prices,
            predictions=predictions,
            portfolio=portfolio,
            risk_analysis=risk_analysis,
            price_history=price_history,
            cluster_summary=cluster_summary,
            model_comparison=model_comparison,
            data_source=market_service.data_source,
            warnings=all_warnings,
        )

    except PortfolioOptimizerError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": str(exc)})
