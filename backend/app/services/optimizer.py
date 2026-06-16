"""
Portfolio weight optimization using mean-variance framework.

Supports max Sharpe ratio and minimum volatility objectives with
long-only constraints (weights sum to 1).

Reads directly from the in-memory {symbol: DataFrame} dict produced
by the market data + preprocessing pipeline. All covariance math uses
BLAS-backed `@` matrix multiplication.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from app.services.risk_metrics import (
    TRADING_DAYS,
    RISK_FREE_RATE,
    portfolio_risk,
    portfolio_var_95,
    portfolio_cvar_95,
)

RISK_PREFS = {"low": 0.5, "medium": 1.0, "high": 1.5}


def _returns_matrix(processed: Dict[str, pd.DataFrame]) -> Tuple[List[str], np.ndarray, np.ndarray]:
    """Build mean returns and covariance directly from RAM-resident dict."""
    symbols = list(processed.keys())

    returns_df = pd.DataFrame(
        {symbol: processed[symbol]["daily_return"] for symbol in symbols}
    ).dropna()

    if returns_df.empty or returns_df.shape[0] < 2 or returns_df.shape[1] < 2:
        n = len(symbols)
        return symbols, np.zeros(n), np.eye(n) * 1e-4

    returns_values = returns_df.to_numpy(copy=False)
    mean_returns = returns_values.mean(axis=0) * TRADING_DAYS
    cov = np.cov(returns_values, rowvar=False) * TRADING_DAYS

    return symbols, mean_returns, cov


def _black_litterman_blend(
    mean_returns: np.ndarray,
    cov: np.ndarray,
    predictions: List[Dict],
    symbols: List[str],
) -> np.ndarray:
    """Compute Black-Litterman posterior expected returns via matrix inversion."""
    n = len(mean_returns)
    w_eq = np.ones(n) / n

    mkt_ret = mean_returns @ w_eq
    mkt_var = w_eq @ cov @ w_eq
    delta = max((mkt_ret - RISK_FREE_RATE) / mkt_var, 0.5) if mkt_var > 0 else 2.5

    pi = delta * cov @ w_eq

    tau = 0.05
    pred_map = {p["symbol"]: p["predicted_return"] * TRADING_DAYS for p in predictions}
    Q = np.array([pred_map.get(s, pi[i]) for i, s in enumerate(symbols)])

    P = np.eye(n)
    omega = tau * np.diag(np.diag(cov))

    tau_cov_inv = np.linalg.inv(tau * cov)
    omega_inv = np.linalg.inv(omega)

    M_inv = np.linalg.inv(tau_cov_inv + P.T @ omega_inv @ P)
    bl_returns = M_inv @ (tau_cov_inv @ pi + P.T @ omega_inv @ Q)

    return bl_returns


def _optimize_weights(
    mean_returns: np.ndarray,
    cov: np.ndarray,
    goal: Literal["max_sharpe", "min_volatility"],
    risk_multiplier: float = 1.0,
) -> np.ndarray:
    n = len(mean_returns)
    MAX_SINGLE_WEIGHT = 0.40

    def portfolio_vol(w: np.ndarray) -> float:
        return float(np.sqrt(w @ cov @ w))

    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "ineq", "fun": lambda w: MAX_SINGLE_WEIGHT - w},
    ]
    bounds = [(0.0, MAX_SINGLE_WEIGHT) for _ in range(n)]
    x0 = np.ones(n) / n

    if goal == "min_volatility":
        result = minimize(portfolio_vol, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    else:
        def neg_sharpe(w: np.ndarray) -> float:
            ret = w @ mean_returns
            vol = portfolio_vol(w)
            if vol == 0:
                return 0.0
            return -(ret - RISK_FREE_RATE) / (vol * risk_multiplier)

        result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)

    weights = result.x if result.success else x0
    weights = np.clip(weights, 0.0, MAX_SINGLE_WEIGHT)

    total_w = weights.sum()
    return weights / total_w if total_w > 0 else x0


def optimize_portfolio(
    processed: Dict[str, pd.DataFrame],
    predictions: List[Dict],
    budget: float,
    risk_preference: Literal["low", "medium", "high"] = "medium",
    optimization_goal: Literal["max_sharpe", "min_volatility"] = "max_sharpe",
    **kwargs,
) -> Dict:
    """
    Optimize portfolio weights using Black-Litterman expected returns
    and Capital Defense Allocation Guards (max 40% single-asset cap).
    """
    if any(df.empty or len(df) < 5 for df in processed.values()):
        symbols = list(processed.keys())
        n = len(symbols)
        equal_weight = 1.0 / n if n > 0 else 0.0
        weights = {s: round(equal_weight, 4) for s in symbols}
        budget_alloc = {s: round(equal_weight * budget, 2) for s in symbols}
        return {
            "expected_return": 0.0,
            "expected_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "portfolio_var_95": 0.0,
            "portfolio_cvar_95": 0.0,
            "blended_expected_returns": [],
            "weights": weights,
            "budget_allocation": budget_alloc,
            "recommendation_summary": (
                "Markets are currently closed for the weekend. Showing a baseline "
                "equal-weight asset distribution profile."
            ),
        }

    symbols, mean_returns, cov = _returns_matrix(processed)

    bl_returns = _black_litterman_blend(mean_returns, cov, predictions, symbols)

    risk_mult = RISK_PREFS.get(risk_preference, 1.0)
    weights_arr = _optimize_weights(bl_returns, cov, optimization_goal, risk_mult)

    weights = dict(zip(symbols, np.round(weights_arr, 4).tolist()))
    port_return, port_vol, port_sharpe, port_mdd, port_var, port_cvar = portfolio_risk(weights, processed)
    summary = _build_recommendation(weights, optimization_goal, risk_preference, port_sharpe)
    budget_alloc = {symbol: round(weight * budget, 2) for symbol, weight in weights.items()}

    blended_returns_list = [
        {"symbol": s, "blended_return": round(float(r), 6)}
        for s, r in zip(symbols, bl_returns)
    ]

    return {
        "expected_return": round(port_return, 4),
        "expected_volatility": round(port_vol, 4),
        "sharpe_ratio": round(port_sharpe, 4),
        "max_drawdown": round(port_mdd, 4),
        "portfolio_var_95": port_var,
        "portfolio_cvar_95": port_cvar,
        "blended_expected_returns": blended_returns_list,
        "weights": weights,
        "budget_allocation": budget_alloc,
        "recommendation_summary": summary,
    }


def _build_recommendation(
    weights: Dict[str, float],
    goal: str,
    risk_pref: str,
    sharpe: float,
) -> str:
    top = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
    top_str = ", ".join(f"{s} ({w*100:.1f}%)" for s, w in top)
    goal_label = "maximum Sharpe ratio" if goal == "max_sharpe" else "minimum volatility"
    return (
        f"Optimized for {goal_label} with {risk_pref} risk preference. "
        f"Top allocations: {top_str}. "
        f"Expected portfolio Sharpe ratio: {sharpe:.2f}. "
        f"Diversify across clusters for balanced exposure."
    )
