"""Auto-generate sample CSV files when missing."""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SAMPLE_DATA_DIR = Path(__file__).resolve().parents[3] / "sample_data"

SYMBOLS = {
    "AAPL": 175.0,
    "MSFT": 380.0,
    "GOOGL": 140.0,
    "AMZN": 155.0,
    "TSLA": 220.0,
    "META": 480.0,
    "NVDA": 480.0,
    "JPM": 185.0,
}


def ensure_sample_data():
    """Create sample CSV files if they do not exist."""
    SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for symbol, start_price in SYMBOLS.items():
        path = SAMPLE_DATA_DIR / f"{symbol}.csv"
        if path.exists():
            continue
        np.random.seed(hash(symbol) % 2**32)
        days = 300
        dates = [datetime.now() - timedelta(days=days - i) for i in range(days)]
        prices = [start_price]
        for _ in range(days - 1):
            prices.append(prices[-1] * (1 + np.random.normal(0.0005, 0.018)))

        rows = []
        for date, close in zip(dates, prices):
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(close * (1 + np.random.normal(0, 0.004)), 2),
                    "high": round(close * (1 + abs(np.random.normal(0, 0.008))), 2),
                    "low": round(close * (1 - abs(np.random.normal(0, 0.008))), 2),
                    "close": round(close, 2),
                    "volume": int(np.random.uniform(5e6, 30e6)),
                }
            )
        pd.DataFrame(rows).to_csv(path, index=False)
