"""
Portfolio and per-asset risk analytics.

Computes volatility, Sharpe ratio, maximum drawdown, and correlation matrix.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd


TRADING_DAYS = 252
RISK_FREE_RATE = 0.02


def annualized_volatility(returns: pd.Series) -> float:
    return float(returns.std() * np.sqrt(TRADING_DAYS))


def sharpe_ratio(returns: pd.Series, risk_free: float = RISK_FREE_RATE) -> float:
    excess = returns.mean() * TRADING_DAYS - risk_free
    vol = returns.std() * np.sqrt(TRADING_DAYS)
    if vol == 0 or np.isnan(vol):
        return 0.0
    return float(excess / vol)


def max_drawdown(prices: pd.Series) -> float:
    cumulative = prices / prices.iloc[0]
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return float(drawdown.min())


def compute_per_asset_risk(processed: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
    """Risk metrics for each symbol."""
    metrics: Dict[str, Dict[str, float]] = {}
    for symbol, df in processed.items():
        returns = df["daily_return"].dropna()
        metrics[symbol] = {
            "volatility": round(annualized_volatility(returns), 4),
            "sharpe_ratio": round(sharpe_ratio(returns), 4),
            "max_drawdown": round(max_drawdown(df["close"]), 4),
        }
    return metrics


def correlation_matrix(processed: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
    """Pairwise return correlations across assets."""
    returns_df = pd.DataFrame(
        {symbol: df.set_index("date")["daily_return"] for symbol, df in processed.items()}
    ).dropna()

    if returns_df.empty or returns_df.shape[1] < 2:
        symbols = list(processed.keys())
        return {s: {t: 1.0 if s == t else 0.0 for t in symbols} for s in symbols}

    corr = returns_df.corr().round(4)
    return corr.to_dict()


def portfolio_risk(
    weights: Dict[str, float],
    processed: Dict[str, pd.DataFrame],
) -> Tuple[float, float, float, float]:
    """
    Compute expected portfolio return, volatility, Sharpe, and max drawdown
    using historical return covariance.
    """
    symbols = [s for s in weights if weights[s] > 0 and s in processed]
    if not symbols:
        return 0.0, 0.0, 0.0, 0.0

    returns_df = pd.DataFrame(
        {s: processed[s]["daily_return"].values[-len(processed[s]) :] for s in symbols}
    ).dropna()

    w = np.array([weights[s] for s in symbols])
    w = w / w.sum()

    mean_returns = returns_df.mean().values * TRADING_DAYS
    cov = returns_df.cov().values * TRADING_DAYS

    port_return = float(np.dot(w, mean_returns))
    port_vol = float(np.sqrt(np.dot(w.T, np.dot(cov, w))))

    if port_vol > 0:
        port_sharpe = (port_return - RISK_FREE_RATE) / port_vol
    else:
        port_sharpe = 0.0

    # Approximate portfolio drawdown from weighted price series
    price_matrix = pd.DataFrame({s: processed[s]["close"].values for s in symbols})
    weighted_prices = (price_matrix * w).sum(axis=1)
    port_mdd = max_drawdown(weighted_prices)

    return port_return, port_vol, port_sharpe, port_mdd
