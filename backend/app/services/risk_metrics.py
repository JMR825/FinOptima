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


def portfolio_var_95(port_return: float, port_vol: float) -> float:
    z_95 = 1.645
    return round(z_95 * port_vol - port_return, 4)


def portfolio_cvar_95(port_return: float, port_vol: float) -> float:
    z_95 = 1.645
    pdf_z = np.exp(-z_95**2 / 2) / np.sqrt(2 * np.pi)
    return round(port_vol * pdf_z / 0.05 - port_return, 4)


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
    period_type: str = "daily"
) -> Tuple[float, float, float, float, float, float]:
    """
    Compute expected portfolio return, volatility, Sharpe, max drawdown,
    VaR (95%), and CVaR (95%) using historical return covariance.
    All array ops use NumPy views to avoid RAM cloning on Render free tier.
    """
    if period_type == "intraday" and any(len(df) < 5 for df in processed.values()):
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    symbols = [s for s in weights if weights[s] > 0 and s in processed]
    if not symbols:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    returns_df = pd.DataFrame(
        {s: processed[s]["daily_return"].values for s in symbols}
    ).dropna()

    cov = returns_df.to_numpy(copy=False)
    mean_returns = cov.mean(axis=0) * TRADING_DAYS
    cov = np.cov(cov, rowvar=False) * TRADING_DAYS

    w = np.array([weights[s] for s in symbols])
    w = w / w.sum()

    port_return = float(np.dot(w, mean_returns))
    port_vol = float(np.sqrt(np.dot(w.T, np.dot(cov, w))))

    if port_vol > 0:
        port_sharpe = (port_return - RISK_FREE_RATE) / port_vol
    else:
        port_sharpe = 0.0

    price_arr = np.column_stack(
        [processed[s]["close"].to_numpy(copy=False) for s in symbols]
    )
    weighted_prices = price_arr @ w
    port_mdd = max_drawdown(pd.Series(weighted_prices))

    port_var = portfolio_var_95(port_return, port_vol)
    port_cvar = portfolio_cvar_95(port_return, port_vol)

    return port_return, port_vol, port_sharpe, port_mdd, port_var, port_cvar
