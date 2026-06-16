"""
Data preprocessing pipeline for stock price time series.

Cleans missing values, sorts chronologically, and engineers features
used by regression, clustering, and LSTM modules. Supports both Daily 
and Intraday frequency tracking loops.
"""

from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd

SEQUENCE_LENGTH = 20
MIN_ROWS = 40


def clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
    """Remove missing values and ensure chronological order."""
    data = df.copy()
    data = data.dropna(subset=["close"])
    
    # Safely sort string dates or datetime string intervals chronologically
    data = data.sort_values("date").reset_index(drop=True)
    data["close"] = data["close"].astype(float)
    return data


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate periodic log and simple returns."""
    data = df.copy()
    data["daily_return"] = data["close"].pct_change()
    data["log_return"] = np.log(data["close"] / data["close"].shift(1))
    return data


def add_moving_averages(df: pd.DataFrame, windows: tuple = (5, 10, 20)) -> pd.DataFrame:
    """Add simple moving averages for trend features."""
    data = df.copy()
    for w in windows:
        data[f"sma_{w}"] = data["close"].rolling(window=w, min_periods=1).mean()
    return data


def add_rolling_volatility(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Rolling standard deviation of returns."""
    data = df.copy()
    data["rolling_volatility"] = data["daily_return"].rolling(window=window, min_periods=5).std()
    return data


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Relative Strength Index momentum indicator."""
    data = df.copy()
    delta = data["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    data["rsi"] = 100 - (100 / (1 + rs))
    data["rsi"] = data["rsi"].fillna(50.0)
    return data


def add_momentum(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """Price momentum over a lookback window."""
    data = df.copy()
    data["momentum"] = data["close"].pct_change(periods=window)
    return data


def preprocess_symbol_data(df: pd.DataFrame, period_type: str = "daily") -> pd.DataFrame:
    """Full preprocessing pipeline for a single symbol with adaptive windows."""
    if df is None or df.empty or len(df) < 2:
        return pd.DataFrame()
    data = clean_price_data(df)
    data = add_returns(data)
    
    # ⚡ OPTIMIZATION: Shift window limits depending on execution frequency
    if period_type == "intraday":
        # Intraday 5-min tracking benefits from larger lookbacks (e.g. 12 bars = 1 hour)
        sma_windows = (12, 24, 78)  # 78 bars equals roughly 1 full trading day
        vol_window = 24
        rsi_period = 14
        mom_window = 12
    else:
        # Standard daily layout parameters matching original setup
        sma_windows = (5, 10, 20)
        vol_window = 20
        rsi_period = 14
        mom_window = 10

    data = add_moving_averages(data, windows=sma_windows)
    data = add_rolling_volatility(data, window=vol_window)
    data = add_rsi(data, period=rsi_period)
    data = add_momentum(data, window=mom_window)
    
    # Backfill or clean drop edge values safely
    data = data.dropna().reset_index(drop=True)
    return data


def preprocess_all(price_data: Dict[str, pd.DataFrame], period_type: str = "daily") -> Dict[str, pd.DataFrame]:
    """Preprocess price data for all symbols, routing period context."""
    return {symbol: preprocess_symbol_data(df, period_type=period_type) for symbol, df in price_data.items()}


def build_feature_matrix(processed: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Aggregate per-symbol features for clustering.

    Features: average return, volatility, momentum, RSI deviation from 50.
    """
    rows = []
    for symbol, df in processed.items():
        if len(df) < 20:
            continue
        rows.append(
            {
                "symbol": symbol,
                "avg_return": df["daily_return"].mean(),
                "volatility": df["daily_return"].std(),
                "momentum": df["momentum"].iloc[-1] if "momentum" in df else 0.0,
                "rsi": df["rsi"].iloc[-1] if "rsi" in df else 50.0,
                "beta_proxy": df["daily_return"].std() / (df["daily_return"].std() + 1e-6),
            }
        )
    return pd.DataFrame(rows).set_index("symbol")
