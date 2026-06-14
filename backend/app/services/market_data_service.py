"""
Market data service — yfinance-only provider with disk caching.

Cache layout:
    live_data/daily/{SYMBOL}.csv          (1d bars)
    live_data/intraday/{INTERVAL}/{SYMBOL}.csv  (e.g. 5m, 15m, 1h)
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys,os
import pandas as pd
import yfinance as yf
from app.config import get_settings
from app.utils.exceptions import InvalidSymbolError

logger = logging.getLogger(__name__)


OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]

# Default fetch params per dashboard mode
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
    """yfinance fetcher with local disk cache."""


    @property
    def source_name(self) -> str:
        return "yfinance"

    def _download_sync(self, symbol: str, period: str, interval: str, mode: str) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)
        if df.empty:
            raise InvalidSymbolError(symbol)

        df = df.reset_index()
        if "Datetime" in df.columns:
            date_strings = pd.to_datetime(df["Datetime"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        elif "Date" in df.columns:
            if mode == "intraday":
                date_strings = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_strings = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        else:
            raise InvalidSymbolError(symbol)

        min_rows = 5 if mode == "daily" else 20
        formatted = pd.DataFrame(
            {
                "date": date_strings,
                "open": df["Open"].round(4),
                "high": df["High"].round(4),
                "low": df["Low"].round(4),
                "close": df["Close"].round(4),
                "volume": df["Volume"].astype(float),
            }
        ).sort_values("date").reset_index(drop=True)

        if len(formatted) < min_rows:
            raise InvalidSymbolError(symbol)
        return formatted

    async def fetch(
        self,
        symbol: str,
        mode: str = "daily",
        interval: Optional[str] = None,
        period: Optional[str] = None,
        refresh: bool = False,
    ) -> pd.DataFrame:
        sym = symbol.upper().strip()
        mode = _normalize_mode(mode)
        resolved_period, resolved_interval = _resolve_params(mode, interval, period)
        
        try:
            logger.info(f"📡 Requesting 100%% live market stream from yfinance for {sym}...")
            return await asyncio.to_thread(
                self._download_sync, sym, resolved_period, resolved_interval, mode
            )
        except Exception as exc:
            logger.error("Real-time stream download failed for %s: %s", sym, exc)
            raise InvalidSymbolError(sym) from exc


class MarketDataService:
    """Orchestrates yfinance fetching with disk cache."""

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
        """Fetch OHLCV history for one or more symbols."""
        self.reset_warnings()
        results: Dict[str, pd.DataFrame] = {}
        errors: List[str] = []

        for symbol in symbols:
            sym = symbol.upper().strip()
            if not sym:
                continue
            try:
                results[sym] = await self._provider.fetch(
                    sym, mode=mode, interval=interval, period=period, refresh=refresh
                )
            except InvalidSymbolError:
                errors.append(f"Could not fetch data for {sym} - invalid symbol or no yfinance data")
            except Exception as exc:
                logger.error("Unexpected error fetching %s: %s", sym, exc)
                errors.append(f"Failed to fetch {sym}: {exc}")

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
        """Latest price snapshot from cached or freshly fetched bars."""
        price_data, errors = await self.fetch_prices(
            symbols, mode=mode, interval=interval, period=period, refresh=refresh
        )
        now = datetime.now(timezone.utc).isoformat()
        live_prices = []
        for symbol, df in price_data.items():
            if df.empty:
                continue
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            change_pct = (
                ((latest["close"] - prev["close"]) / prev["close"]) * 100
                if prev["close"]
                else 0.0
            )
            live_prices.append(
                {
                    "symbol": symbol,
                    "price": round(float(latest["close"]), 2),
                    "change_pct": round(float(change_pct), 2),
                    "last_updated": now,
                    "source": self.data_source,
                }
            )
        return live_prices, errors
