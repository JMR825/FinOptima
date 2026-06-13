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

import pandas as pd
import yfinance as yf

from app.config import get_settings
from app.utils.exceptions import InvalidSymbolError

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "live_data"

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

    def __init__(self, cache_ttl_seconds: int = 45):
        self.cache_ttl_seconds = cache_ttl_seconds
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / "daily").mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / "intraday").mkdir(parents=True, exist_ok=True)

    @property
    def source_name(self) -> str:
        return "yfinance"

    def _cache_path(self, symbol: str, mode: str, interval: str) -> Path:
        sym = symbol.upper()
        mode = _normalize_mode(mode)
        if mode == "daily":
            return CACHE_DIR / "daily" / f"{sym}.csv"
        return CACHE_DIR / "intraday" / interval / f"{sym}.csv"

    def _legacy_cache_path(self, symbol: str, mode: str) -> Path:
        """Backward-compatible path before interval subfolders."""
        sym = symbol.upper()
        return CACHE_DIR / mode / f"{sym}.csv"

    def _is_stale(self, path: Path, mode: str) -> bool:
        if not path.exists():
            return True
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age = (datetime.now(timezone.utc) - mtime).total_seconds()
        if _normalize_mode(mode) == "daily":
            return age > 3600  # refresh daily cache hourly
        return age > self.cache_ttl_seconds

    def _load_cache(self, path: Path) -> Optional[pd.DataFrame]:
        if not path.exists():
            return None
        try:
            df = pd.read_csv(path)
            for col in OHLCV_COLUMNS:
                if col not in df.columns:
                    return None
            return df.sort_values("date").reset_index(drop=True)
        except Exception as exc:
            logger.warning("Failed to read cache %s: %s", path, exc)
            return None

    def _save_cache(self, path: Path, df: pd.DataFrame) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)

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
        cache_path = self._cache_path(sym, mode, resolved_interval)
        
        if not cache_path.exists():
            logger.info(f"💾 Ticker dataset for {sym} not found in local cache. Generating new dataset on-demand...")
            refresh = True  # Forces the system to ignore cache logic and pull fresh data

        if not refresh:
            cached = self._load_cache(cache_path)
            if cached is not None and not self._is_stale(cache_path, mode):
                return cached
            # Try legacy path for intraday (pre-interval subfolder)
            if mode == "intraday":
                legacy = self._legacy_cache_path(sym, mode)
                cached = self._load_cache(legacy)
                if cached is not None and not self._is_stale(legacy, mode):
                    self._save_cache(cache_path, cached)
                    return cached

        try:
            logger.info(f"📡 Fetching live rows from yfinance to write {sym}.csv...")
            df = await asyncio.to_thread(
                self._download_sync, sym, resolved_period, resolved_interval, mode
            )
            self._save_cache(cache_path, df)
            logger.info(f"✅ New dataset successfully created on disk at: {cache_path}")
            return df
        except InvalidSymbolError:
            raise
        except Exception as exc:
            logger.error("yfinance download failed for %s: %s", sym, exc)
            cached = self._load_cache(cache_path)
            if cached is not None:
                return cached
            raise InvalidSymbolError(sym) from exc


class MarketDataService:
    """Orchestrates yfinance fetching with disk cache."""

    def __init__(self):
        self.settings = get_settings()
        self._provider = YFinanceDataProvider(cache_ttl_seconds=self.settings.default_refresh_interval)
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
