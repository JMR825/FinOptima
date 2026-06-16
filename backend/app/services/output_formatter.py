"""
Format pipeline outputs into dashboard-ready JSON structures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
import pandas as pd


def format_price_history(price_data: Dict[str, pd.DataFrame], limit: int = 90) -> Dict[str, List[dict]]:
    """Convert price DataFrames to serializable price point lists."""
    history = {}
    for symbol, df in price_data.items():
        recent = df.tail(limit)
        history[symbol] = [
            {
                "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": round(float(row["volume"]), 0),
            }
            for _, row in recent.iterrows()
        ]
    return history


def format_risk_analysis(per_asset: Dict[str, Dict[str, float]], corr: Dict[str, Dict[str, float]]) -> dict:
    return {
        "volatility": {s: m["volatility"] for s, m in per_asset.items()},
        "sharpe_ratio": {s: m["sharpe_ratio"] for s, m in per_asset.items()},
        "max_drawdown": {s: m["max_drawdown"] for s, m in per_asset.items()},
        "correlation_matrix": corr,
    }


def build_full_response(
    live_prices: List[dict],
    predictions: List[dict],
    portfolio: dict,
    risk_analysis: dict,
    price_history: dict,
    cluster_summary: dict,
    model_comparison: dict,
    data_source: str,
    warnings: List[str],
    mode: str = "daily",
    message: str = "Analysis complete",
) -> Dict[str, Any]:
    """Assemble the complete dashboard response."""
    return {
        "success": True,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_source": data_source,
        "mode": mode,
        "live_prices": live_prices,
        "predictions": predictions,
        "portfolio": {
            "expected_return": portfolio["expected_return"],
            "expected_volatility": portfolio["expected_volatility"],
            "sharpe_ratio": portfolio["sharpe_ratio"],
            "max_drawdown": portfolio["max_drawdown"],
            "portfolio_var_95": portfolio.get("portfolio_var_95", 0.0),
            "portfolio_cvar_95": portfolio.get("portfolio_cvar_95", 0.0),
            "blended_expected_returns": portfolio.get("blended_expected_returns", []),
            "weights": portfolio["weights"],
            "recommendation_summary": portfolio["recommendation_summary"],
        },
        "risk_analysis": risk_analysis,
        "price_history": price_history,
        "cluster_summary": cluster_summary,
        "model_comparison": model_comparison,
        "warnings": warnings,
    }
