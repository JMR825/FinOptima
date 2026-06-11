"""
Market data service with pluggable provider architecture.

Supports Alpha Vantage as the default provider and falls back to local
sample CSV data when the API key is missing, rate limits are hit, or
requests fail.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
import pandas as pd

from app.config import get_settings
from app.utils.exceptions import (
    APIKeyMissingError,
    APIRateLimitError,
    InvalidSymbolError,
)

logger = logging.getLogger(__name__)

SAMPLE_DATA_DIR = Path(__file__).resolve().parents[3] / "sample_data"
AVAILABLE_SAMPLE_SYMBOLS = {"AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM"}


class MarketDataProvider(ABC):
    """Abstract base for swappable market data providers."""

    @abstractmethod
    async def fetch_daily(self, symbol: str) -> pd.DataFrame:
        pass

    @abstractmethod
    async def fetch_intraday(self, symbol: str) -> pd.DataFrame:
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass


class AlphaVantageProvider(MarketDataProvider):
    """Alpha Vantage REST API provider."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def source_name(self) -> str:
        return "alphavantage"

    async def _request(self, params: Dict[str, str]) -> dict:
        params["apikey"] = self.api_key
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        if "Note" in data or "Information" in data:
            raise APIRateLimitError(data.get("Note") or data.get("Information", ""))

        if "Error Message" in data:
            raise InvalidSymbolError(params.get("symbol", "UNKNOWN"))

        return data

    def _parse_daily(self, data: dict, symbol: str) -> pd.DataFrame:
        series = data.get("Time Series (Daily)") or data.get("Time Series (Daily Adjusted)")
        if not series:
            raise InvalidSymbolError(symbol)

        rows = []
        for date_str, values in series.items():
            rows.append(
                {
                    "date": pd.to_datetime(date_str),
                    "open": float(values.get("1. open", values.get("open", 0))),
                    "high": float(values.get("2. high", values.get("high", 0))),
                    "low": float(values.get("3. low", values.get("low", 0))),
                    "close": float(values.get("4. close", values.get("close", 0))),
                    "volume": float(values.get("5. volume", values.get("volume", 0))),
                }
            )

        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        return df.tail(252)

    def _parse_intraday(self, data: dict, symbol: str) -> pd.DataFrame:
        series = None
        for key in data:
            if "Time Series" in key:
                series = data[key]
                break
        if not series:
            raise InvalidSymbolError(symbol)

        rows = []
        for ts, values in series.items():
            rows.append(
                {
                    "date": pd.to_datetime(ts),
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": float(values["5. volume"]),
                }
            )

        return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    async def fetch_daily(self, symbol: str) -> pd.DataFrame:
        data = await self._request(
            {"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": symbol, "outputsize": "compact"}
        )
        return self._parse_daily(data, symbol)

    async def fetch_intraday(self, symbol: str) -> pd.DataFrame:
        data = await self._request(
            {"function": "TIME_SERIES_INTRADAY", "symbol": symbol, "interval": "5min", "outputsize": "compact"}
        )
        return self._parse_intraday(data, symbol)


class SampleDataProvider(MarketDataProvider):
    """Local CSV sample data for offline demo and API fallback."""

    @property
    def source_name(self) -> str:
        return "sample_data"

    def _load_csv(self, symbol: str) -> pd.DataFrame:
        symbol = symbol.upper()
        if symbol not in AVAILABLE_SAMPLE_SYMBOLS:
            raise InvalidSymbolError(symbol)

        path = SAMPLE_DATA_DIR / f"{symbol}.csv"
        if not path.exists():
            raise InvalidSymbolError(symbol)

        df = pd.read_csv(path, parse_dates=["date"])
        return df.sort_values("date").reset_index(drop=True)

    async def fetch_daily(self, symbol: str) -> pd.DataFrame:
        return self._load_csv(symbol)

    async def fetch_intraday(self, symbol: str) -> pd.DataFrame:
        df = self._load_csv(symbol)
        # Simulate intraday by repeating last 30 daily rows with hourly timestamps
        recent = df.tail(30).copy()
        intraday_rows = []
        for _, row in recent.iterrows():
            for hour in range(9, 16):
                ts = row["date"].replace(hour=hour, minute=30)
                intraday_rows.append(
                    {
                        "date": ts,
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": row["volume"] / 7,
                    }
                )
        return pd.DataFrame(intraday_rows)


class MarketDataService:
    """Orchestrates provider selection, fetching, and graceful fallback."""

    def __init__(self):
        self.settings = get_settings()
        self._provider: Optional[MarketDataProvider] = None
        self._using_fallback = False
        self._warnings: List[str] = []

    def _build_provider(self, force_sample: bool = False) -> MarketDataProvider:
        if force_sample or self.settings.market_data_provider == "sample":
            return SampleDataProvider()

        if not self.settings.alpha_vantage_api_key:
            self._warnings.append("API key missing — using sample data fallback.")
            self._using_fallback = True
            return SampleDataProvider()

        return AlphaVantageProvider(self.settings.alpha_vantage_api_key)

    @property
    def provider(self) -> MarketDataProvider:
        if self._provider is None:
            self._provider = self._build_provider()
        return self._provider

    @property
    def warnings(self) -> List[str]:
        return self._warnings

    @property
    def data_source(self) -> str:
        return self.provider.source_name

    def reset_warnings(self):
        self._warnings = []

    async def fetch_daily_prices(self, symbols: List[str]) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
        """Fetch adjusted daily prices for multiple symbols."""
        self.reset_warnings()
        results: Dict[str, pd.DataFrame] = {}
        errors: List[str] = []

        for symbol in symbols:
            sym = symbol.upper().strip()
            try:
                results[sym] = await self.provider.fetch_daily(sym)
            except (APIRateLimitError, APIKeyMissingError) as exc:
                logger.warning("Falling back to sample data: %s", exc.message)
                self._warnings.append(str(exc.message))
                self._using_fallback = True
                self._provider = SampleDataProvider()
                results[sym] = await self._provider.fetch_daily(sym)
            except InvalidSymbolError as exc:
                errors.append(exc.message)
            except httpx.HTTPError as exc:
                logger.error("HTTP error for %s: %s", sym, exc)
                self._warnings.append(f"Request failed for {sym}; using sample data if available.")
                try:
                    self._provider = SampleDataProvider()
                    results[sym] = await self._provider.fetch_daily(sym)
                except InvalidSymbolError:
                    errors.append(f"Could not fetch data for {sym}")

        return results, errors

    async def fetch_live_prices(self, symbols: List[str]) -> Tuple[List[dict], List[str]]:
        """Fetch latest price snapshot for dashboard live section."""
        daily_data, errors = await self.fetch_daily_prices(symbols)
        now = datetime.now(timezone.utc).isoformat()
        live_prices = []

        for symbol, df in daily_data.items():
            if df.empty:
                continue
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            change_pct = ((latest["close"] - prev["close"]) / prev["close"]) * 100 if prev["close"] else 0.0
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
