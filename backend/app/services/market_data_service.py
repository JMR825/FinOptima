"""
Market data service — yfinance-only, 100% in-memory provider.

No disk cache. All OHLCV + lightweight features live in a transient
{symbol: DataFrame} dict until the request completes.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import atexit
import os
import tempfile

import numpy as np
import pandas as pd
import yfinance as yf

# Redirect yfinance's timezone cache to a per-process temp dir.
# Prevents "database is locked" errors on Render's ephemeral filesystem
# where multiple workers or deploys would conflict on the default location
# inside the read-only package directory.
_tz_cache_dir = tempfile.mkdtemp(prefix="yf_tz_")
yf.set_tz_cache_location(os.path.join(_tz_cache_dir, "tz_cache.sqlite"))

from app.config import get_settings
from app.utils.exceptions import InvalidSymbolError

logger = logging.getLogger(__name__)

OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]

MODE_DEFAULTS: Dict[str, Dict[str, str]] = {
    "daily": {"period": "1y", "interval": "1d"},
    "intraday": {"period": "5d", "interval": "5m"},
}

VALID_INTRADAY_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}


def _normalize_mode(mode: str) -> str:
    return "intraday" if mode == "intraday" else "daily"


def _resolve_params(mode: str, interval: Optional[str], period: Optional[str]) -> Tuple[str, str]:
    mode = _normalize_mode(mode)
    defaults = MODE_DEFAULTS[mode]
    resolved_interval = interval or defaults["interval"]
    resolved_period = period or defaults["period"]
    if mode == "intraday" and resolved_interval not in VALID_INTRADAY_INTERVALS:
        resolved_interval = defaults["interval"]
    return resolved_period, resolved_interval


def _vectorized_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Vectorized RSI — no Python loops."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute daily_return and RSI in-memory on the fly."""
    out = df.copy()
    out["daily_return"] = out["close"].pct_change()
    out["rsi"] = _vectorized_rsi(out["close"])
    return out.dropna(subset=["close"]).reset_index(drop=True)


def _format_symbol_frame(raw: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Normalize a single ticker's yfinance slice to standard OHLCV columns."""
    if raw.empty:
        raise InvalidSymbolError("empty")

    df = raw.reset_index()
    if "Datetime" in df.columns:
        if mode == "intraday":
            date_strings = pd.to_datetime(df["Datetime"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_strings = pd.to_datetime(df["Datetime"]).dt.strftime("%Y-%m-%d")
    elif "Date" in df.columns:
        if mode == "intraday":
            date_strings = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_strings = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    else:
        raise InvalidSymbolError("missing date column")

    formatted = pd.DataFrame(
        {
            "date": date_strings,
            "open": df["Open"].astype(float).round(4),
            "high": df["High"].astype(float).round(4),
            "low": df["Low"].astype(float).round(4),
            "close": df["Close"].astype(float).round(4),
            "volume": df["Volume"].astype(float),
        }
    ).sort_values("date").reset_index(drop=True)

    return formatted


class MarketDataProvider(ABC):
    @abstractmethod
    async def fetch(
        self,
        symbol: str,
        mode: str = "daily",
        interval: Optional[str] = None,
        period: Optional[str] = None,
        refresh: bool = False,
    ) -> pd.DataFrame:
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass


class YFinanceDataProvider(MarketDataProvider):
    """yfinance fetcher — single batch download, zero disk I/O."""

    @property
    def source_name(self) -> str:
        return "yfinance"

    def _batch_download_sync(
        self,
        symbols: List[str],
        period: str,
        interval: str,
        mode: str,
    ) -> Dict[str, pd.DataFrame]:
        cleaned_symbols = [s.upper().strip() for s in symbols if s and s.strip()]
        if not cleaned_symbols:
            return {}

        logger.info(
            "Requesting live batch market stream from yfinance for %d symbols...",
            len(cleaned_symbols),
        )

        raw = yf.download(
            cleaned_symbols,
            period=period,
            interval=interval,
            group_by="ticker",
            progress=False,
            auto_adjust=True,
            threads=True,
        )

        if raw is None or raw.empty:
            raise InvalidSymbolError(",".join(cleaned_symbols))

        multi_ticker = isinstance(raw.columns, pd.MultiIndex)
        min_rows = 5 if mode == "daily" else 20
        results: Dict[str, pd.DataFrame] = {}

        for sym in cleaned_symbols:
            try:
                if multi_ticker:
                    if sym not in raw.columns.get_level_values(0):
                        continue
                    sym_raw = raw[sym]
                else:
                    sym_raw = raw

                formatted = _format_symbol_frame(sym_raw, mode)
                if len(formatted) < min_rows:
                    continue

                results[sym] = _add_technical_features(formatted)
            except (KeyError, InvalidSymbolError, ValueError, TypeError) as exc:
                logger.warning("Skipping %s in batch parse: %s", sym, exc)

        if not results:
            raise InvalidSymbolError(",".join(cleaned_symbols))

        return results

    async def fetch_batch(
        self,
        symbols: List[str],
        mode: str = "daily",
        interval: Optional[str] = None,
        period: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict[str, pd.DataFrame]:
        mode = _normalize_mode(mode)
        resolved_period, resolved_interval = _resolve_params(mode, interval, period)
        return await asyncio.to_thread(
            self._batch_download_sync,
            symbols,
            resolved_period,
            resolved_interval,
            mode,
        )

    async def fetch(
        self,
        symbol: str,
        mode: str = "daily",
        interval: Optional[str] = None,
        period: Optional[str] = None,
        refresh: bool = False,
    ) -> pd.DataFrame:
        sym = symbol.upper().strip()
        batch = await self.fetch_batch(
            [sym], mode=mode, interval=interval, period=period, refresh=refresh
        )
        if sym not in batch:
            raise InvalidSymbolError(sym)
        return batch[sym]


class MarketDataService:
    """Orchestrates in-memory yfinance fetching."""

    def __init__(self):
        self.settings = get_settings()
        self._provider = YFinanceDataProvider()
        self._warnings: List[str] = []

    @property
    def provider(self) -> YFinanceDataProvider:
        return self._provider

    @property
    def warnings(self) -> List[str]:
        return self._warnings

    @property
    def data_source(self) -> str:
        return self._provider.source_name

    def reset_warnings(self):
        self._warnings = []

    async def fetch_prices(
        self,
        symbols: List[str],
        mode: str = "daily",
        interval: Optional[str] = None,
        period: Optional[str] = None,
        refresh: bool = False,
    ) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
        """Fetch OHLCV + daily_return + rsi for all symbols in one batch call."""
        self.reset_warnings()
        cleaned = [s.upper().strip() for s in symbols if s and s.strip()]
        if not cleaned:
            return {}, []

        try:
            results = await self._provider.fetch_batch(
                cleaned,
                mode=mode,
                interval=interval,
                period=period,
                refresh=refresh,
            )
        except InvalidSymbolError:
            return {}, [
                f"Could not fetch data for requested symbols: {', '.join(cleaned)}"
            ]
        except Exception as exc:
            logger.error("Batch market download failed: %s", exc)
            return {}, [f"Failed to fetch market data: {exc}"]

        errors: List[str] = []
        for sym in cleaned:
            if sym not in results:
                errors.append(
                    f"Could not fetch data for {sym} - invalid symbol or no yfinance data"
                )

        return results, errors

    async def fetch_daily_prices(
        self,
        symbols: List[str],
        period_type: str = "daily",
        interval: Optional[str] = None,
        period: Optional[str] = None,
        refresh: bool = False,
    ) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
        """Backward-compatible alias used by routes."""
        return await self.fetch_prices(
            symbols, mode=period_type, interval=interval, period=period, refresh=refresh
        )

    async def fetch_live_prices(
        self,
        symbols: List[str],
        mode: str = "daily",
        interval: Optional[str] = None,
        period: Optional[str] = None,
        refresh: bool = False,
    ) -> Tuple[List[dict], List[str]]:
        """Latest price snapshot from in-memory bars."""
        price_data, errors = await self.fetch_prices(
            symbols, mode=mode, interval=interval, period=period, refresh=refresh
        )
        return self._live_prices_from_data(price_data, mode=mode), errors

    def _live_prices_from_data(self, price_data: Dict[str, pd.DataFrame], mode: str = "daily") -> List[dict]:
        """Build live price snapshots from an already-fetched in-memory dict."""
        return self.live_prices_from_data(price_data, mode=mode)

    def live_prices_from_data(self, price_data: Dict[str, pd.DataFrame], mode: str = "daily") -> List[dict]:
        """
        Build live price snapshots with mode-aware change_pct:
        - daily:  % change from previous day's close
        - intraday: % change from ~1 hour ago
        """
        now = datetime.now(timezone.utc).isoformat()
        is_intraday = mode == "intraday"
        live_prices = []
        for symbol, df in price_data.items():
            if df is None or df.empty or len(df) < 1 or "close" not in df.columns:
                continue

            try:
                latest = df.iloc[-1]
                latest_close = float(latest["close"])

                if is_intraday and len(df) >= 2:
                    target = pd.Timestamp(latest["date"]) - pd.Timedelta(hours=1)
                    dates = pd.to_datetime(df["date"])
                    offset = (dates - target).abs().idxmin()
                    ref_idx = max(offset, 0)
                    if ref_idx == len(df) - 1:
                        ref_idx = max(len(df) - 2, 0)
                    prev_close = float(df.iloc[ref_idx]["close"])
                    change_pct = ((latest_close - prev_close) / prev_close) * 100 if prev_close != 0 else 0.0
                elif len(df) > 1:
                    prev_close = float(df.iloc[-2]["close"])
                    change_pct = ((latest_close - prev_close) / prev_close) * 100 if prev_close != 0 else 0.0
                else:
                    change_pct = 0.0

                if not np.isfinite(latest_close): latest_close = 0.0
                if not np.isfinite(change_pct): change_pct = 0.0

                live_prices.append({
                    "symbol": symbol,
                    "price": round(latest_close, 2),
                    "change_pct": round(change_pct, 2),
                    "last_updated": now,
                    "source": self.data_source,
                })
            except Exception as exc:
                logger.error(f"Error computing change for {symbol}: {str(exc)}")
                continue

        return live_prices