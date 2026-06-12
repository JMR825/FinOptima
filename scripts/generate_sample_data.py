import os
from pathlib import Path
import pandas as pd
import yfinance as yf
# Use your existing list of stock symbols
# Expanded asset dictionary mapped by sector for testing optimization constraints
SYMBOLS = [
    # original Tech/Finance
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM",
    # New Tech & Growth
    "NFLX", "AMD", "AVGO", "COST",
    # Consumer Staples & Defensive
    "KO", "PEP", "WMT", "PG",
    # Banking & Healthcare
    "V", "BAC", "JNJ", "UNH",
    # Energy & Industrials
    "XOM", "CAT", "GE", "LIN",
    # Diversified Market Benchmarks (ETFs)
    "SPY", "QQQ", "IWM", "GLD"
]
# Maintain your existing folder architecture
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "live_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_live_stock_data(symbol: str, period: str = "1d") -> pd.DataFrame:
  """Fetches real historical and real-time market data from Yahoo Finance."""
  print(f"Fetching live data for {symbol}...")
  # Download data via yfinance ticker object
  ticker = yf.Ticker(symbol)
  df = ticker.history(period=period)
  if df.empty:
    print(f"Warning: No data found for {symbol}")
    return pd.DataFrame()
  # Reset index to extract 'Date' and format it exactly like your original script
  df = df.reset_index()
  # Standardize columns to match your portfolio optimization requirements
  formatted_df = pd.DataFrame({
        "date": df["Date"].dt.strftime("%Y-%m-%d"),
        "open": df["Open"].round(2),
        "high": df["High"].round(2),
        "low": df["Low"].round(2),
        "close": df["Close"].round(2),
        "volume": df["Volume"].astype(int)
    })
  return formatted_df
if __name__ == "__main__":
  for symbol in SYMBOLS:
    df = fetch_live_stock_data(symbol, period="1y")
    # Fetches past year up to today
    if not df.empty:
      path = OUTPUT_DIR / f"{symbol}.csv"
      df.to_csv(path, index=False)
      print(f"Successfully saved live data to {path}")
