"""
Optional preload script — populates the live_data disk cache from yfinance.

Run manually or at deploy time. The backend also fetches missing tickers on demand.
"""

from pathlib import Path
import pandas as pd
import yfinance as yf

SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM",
    "NFLX", "AMD", "AVGO", "COST",
    "KO", "PEP", "WMT", "PG",
    "V", "BAC", "JNJ", "UNH",
    "XOM", "CAT", "GE", "LIN",
    "SPY", "QQQ", "IWM", "GLD",
    "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS",
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "BAJFINANCE.NS",
    "RELIANCE.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS",
    "ITC.NS", "HINDUNILVR.NS", "TATAMOTORS.NS", "M&M.NS", "MARUTI.NS",
    "BHARTIARTL.NS", "SUNPHARMA.NS", "JALAN.NS", "TATASTEEL.NS",
]

BASE_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "live_data"
DAILY_DIR = BASE_OUTPUT_DIR / "daily"
INTRADAY_DIR = BASE_OUTPUT_DIR / "intraday" / "5m"

DAILY_DIR.mkdir(parents=True, exist_ok=True)
INTRADAY_DIR.mkdir(parents=True, exist_ok=True)


def fetch_and_format(symbol: str, period: str, interval: str) -> pd.DataFrame:
    print(f"Fetching {interval} data for {symbol}...")
    df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
    if df.empty:
        print(f"Warning: No data found for {symbol}")
        return pd.DataFrame()

    df = df.reset_index()
    if "Datetime" in df.columns:
        dates = pd.to_datetime(df["Datetime"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        dates = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    return pd.DataFrame(
        {
            "date": dates,
            "open": df["Open"].round(4),
            "high": df["High"].round(4),
            "low": df["Low"].round(4),
            "close": df["Close"].round(4),
            "volume": df["Volume"].astype(float),
        }
    )


if __name__ == "__main__":
    print("Populating live_data cache from yfinance...")
    for symbol in SYMBOLS:
        df_daily = fetch_and_format(symbol, period="1y", interval="1d")
        if not df_daily.empty:
            df_daily.to_csv(DAILY_DIR / f"{symbol}.csv", index=False)

        df_intra = fetch_and_format(symbol, period="5d", interval="5m")
        if not df_intra.empty:
            df_intra.to_csv(INTRADAY_DIR / f"{symbol}.csv", index=False)

    print("Cache preload complete.")
