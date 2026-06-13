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

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models.schemas import (
    AnalyzeRequest,
    ClusterRequest,
    FullAnalysisRequest,
    LiveDataRequest,
    OptimizeRequest,
    PredictRequest,
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


def _resolve_mode(request) -> str:
    """Use mode field, falling back to period_type for backward compatibility."""
    return getattr(request, "mode", None) or getattr(request, "period_type", "daily")


async def _fetch_and_preprocess(
    symbols: List[str],
    mode: str = "daily",
    interval: Optional[str] = None,
    period: Optional[str] = None,
    refresh: bool = False,
):
    symbols = [s.upper().strip() for s in symbols if s.strip()]
    price_data, errors = await market_service.fetch_prices(
        symbols, mode=mode, interval=interval, period=period, refresh=refresh
    )
    if len(symbols) < 2:
        return JSONResponse(
            status_code=400,
            content={"detail": {"message": "Optimization requires at least 2 tickers. Please add another stock to calculate weights."}}
        )
    
    price_data, errors = await market_service.fetch_daily_prices(symbols, period_type=mode)
    
    if not price_data:
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "errors": errors,
                    "message": "No data fetched — check ticker symbols and try again",
                }
            },
        )
    processed = preprocess_all(price_data, period_type=mode)
    return price_data, processed, errors


@router.get("/health")
async def health_check():
    settings = get_settings()
    return {
        "status": "healthy",
        "provider": "yfinance",
        "market_data_provider": settings.market_data_provider,
        "lstm_enabled": settings.enable_lstm,
        "cache_dir": "live_data",
    }


@router.post("/live-data")
async def live_data(request: LiveDataRequest):
    """Fetch latest market prices."""
    mode = _resolve_mode(request)
    live_prices, errors = await market_service.fetch_live_prices(
        request.symbols,
        mode=mode,
        interval=request.interval,
        period=request.period,
        refresh=request.refresh_cache,
    )
    return {
        "live_prices": live_prices,
        "data_source": market_service.data_source,
        "mode": mode,
        "warnings": market_service.warnings + errors,
    }


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """Preprocess data and compute risk metrics."""
    mode = _resolve_mode(request)
    res = await _fetch_and_preprocess(
        request.symbols,
        mode=mode,
        interval=request.interval,
        period=request.period,
        refresh=request.refresh_cache,
    )
    if isinstance(res, JSONResponse):
        return res
    _, processed, errors = res

    per_asset = compute_per_asset_risk(processed)
    corr = correlation_matrix(processed)
    return {
        "risk_analysis": format_risk_analysis(per_asset, corr),
        "symbols_analyzed": list(processed.keys()),
        "mode": mode,
        "warnings": market_service.warnings + errors,
    }


@router.post("/predict")
async def predict(request: PredictRequest):
    """Run ML predictions."""
    settings = get_settings()
    mode = _resolve_mode(request)
    res = await _fetch_and_preprocess(
        request.symbols,
        mode=mode,
        interval=request.interval,
        period=request.period,
        refresh=request.refresh_cache,
    )
    if isinstance(res, JSONResponse):
        return res
    _, processed, errors = res

    reg_preds, model_comparison = predict_all_regression(processed, period_type=mode)
    enable_lstm = request.enable_lstm if request.enable_lstm is not None else settings.enable_lstm

    if request.prediction_mode in ("lstm", "ensemble") and enable_lstm:
        lstm_preds = predict_all_lstm(processed, period_type=mode)
        if request.prediction_mode == "ensemble":
            predictions = ensemble_predictions(reg_preds, lstm_preds)
        else:
            predictions = lstm_preds if lstm_preds else reg_preds
    else:
        predictions = reg_preds

    return {
        "predictions": predictions,
        "model_comparison": model_comparison,
        "mode": mode,
        "warnings": market_service.warnings + errors,
    }


@router.post("/cluster")
async def cluster(request: ClusterRequest):
    """Cluster stocks by risk/return features."""
    mode = _resolve_mode(request)
    res = await _fetch_and_preprocess(
        request.symbols,
        mode=mode,
        interval=request.interval,
        period=request.period,
        refresh=request.refresh_cache,
    )
    if isinstance(res, JSONResponse):
        return res
    _, processed, errors = res

    label_map, summary = cluster_stocks(processed)
    return {
        "cluster_labels": label_map,
        "cluster_summary": summary,
        "mode": mode,
        "warnings": market_service.warnings + errors,
    }


@router.post("/optimize")
async def optimize(request: OptimizeRequest):
    """Optimize portfolio weights."""
    mode = _resolve_mode(request)
    res = await _fetch_and_preprocess(
        request.symbols,
        mode=mode,
        interval=request.interval,
        period=request.period,
        refresh=request.refresh_cache,
    )
    if isinstance(res, JSONResponse):
        return res
    _, processed, errors = res

    reg_preds, _ = predict_all_regression(processed, period_type=mode)
    portfolio = optimize_portfolio(
        processed,
        reg_preds,
        request.budget,
        request.risk_preference,
        request.optimization_goal,
    )
    return {
        "portfolio": portfolio,
        "mode": mode,
        "warnings": market_service.warnings + errors,
    }


@router.post("/full-analysis")
async def full_analysis(request: FullAnalysisRequest):
    """Run the complete pipeline and return dashboard-ready JSON."""
    settings = get_settings()
    symbols = [s.upper().strip() for s in request.symbols if s.strip()]
    mode = _resolve_mode(request)

    try:
        price_data, errors = await market_service.fetch_prices(
            symbols,
            mode=mode,
            interval=request.interval,
            period=request.period,
            refresh=request.refresh_cache,
        )
        if not price_data:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "message": "Could not fetch data for any symbol",
                        "errors": errors,
                    }
                },
            )

        live_prices, live_errors = await market_service.fetch_live_prices(
            symbols,
            mode=mode,
            interval=request.interval,
            period=request.period,
            refresh=False,
        )
        processed = preprocess_all(price_data, period_type=mode)

        reg_preds, model_comparison = predict_all_regression(processed, period_type=mode)
        enable_lstm = request.enable_lstm if request.enable_lstm is not None else settings.enable_lstm

        if request.prediction_mode in ("lstm", "ensemble") and enable_lstm:
            lstm_preds = predict_all_lstm(processed, period_type=mode)
            if request.prediction_mode == "ensemble":
                predictions = ensemble_predictions(reg_preds, lstm_preds)
            elif lstm_preds:
                predictions = lstm_preds
            else:
                predictions = reg_preds
        else:
            predictions = reg_preds

        label_map, cluster_summary = cluster_stocks(processed)
        predictions = apply_cluster_labels(predictions, label_map)

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

        per_asset = compute_per_asset_risk(processed)
        corr = correlation_matrix(processed)
        risk_analysis = format_risk_analysis(per_asset, corr)
        price_history = format_price_history(price_data)

        all_warnings = market_service.warnings + errors + live_errors
        if len(price_data) == 1:
            sym = list(price_data.keys())[0]
            all_warnings.append(
                f"Single-ticker analysis: 100% allocation to {sym}. Add more tickers for diversified optimization."
            )

        return build_full_response(
            live_prices=live_prices,
            predictions=predictions,
            portfolio=portfolio,
            risk_analysis=risk_analysis,
            price_history=price_history,
            cluster_summary=cluster_summary,
            model_comparison=model_comparison,
            data_source=market_service.data_source,
            mode=mode,
            warnings=all_warnings,
        )

    except PortfolioOptimizerError as exc:
        return JSONResponse(status_code=400, content={"detail": {"code": exc.code, "message": exc.message}})
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"detail": {"message": str(exc)}})
