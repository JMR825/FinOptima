import os
from pathlib import Path
import pandas as pd
import yfinance as yf
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
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "sample_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_live_stock_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetches historical market data and appends real-time live trading prices."""
    print(f"Fetching live data for {symbol}...")
    ticker = yf.Ticker(symbol)
    
    # 1. Fetch 1 year of historical daily bars
    df = ticker.history(period=period)
    if df.empty:
        print(f"Warning: No data found for {symbol}")
        return pd.DataFrame()
        
    df = df.reset_index()
    
    # 2. Extract and format the historical records
    formatted_df = pd.DataFrame({
        "date": df["Date"].dt.strftime("%Y-%m-%d"),
        "open": df["Open"].round(2),
        "high": df["High"].round(2),
        "low": df["Low"].round(2),
        "close": df["Close"].round(2),
        "volume": df["Volume"].astype(int)
    })
    
    try:
        # 3. Pull the active, live price and today's volume snapshot
        live_price = round(float(ticker.fast_info['lastPrice']), 2)
        live_volume = int(ticker.fast_info['lastVolume'])
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 4. If the last row isn't today yet, append the live price as a fresh row
        if formatted_df.empty or formatted_df.iloc[-1]["date"] != today_str:
            live_row = pd.DataFrame([{
                "date": today_str,
                "open": live_price,
                "high": live_price,
                "low": live_price,
                "close": live_price,
                "volume": live_volume
            }])
            formatted_df = pd.concat([formatted_df, live_row], ignore_index=True)
        else:
            # If today's market has closed but has active post-market activity, update it
            formatted_df.loc[formatted_df.index[-1], "close"] = live_price
            
    except Exception as e:
        print(f"Notice: Live intraday price skip for {symbol} (using last close): {e}")

    return formatted_df
if __name__ == "__main__":
    for symbol in SYMBOLS:
        df = fetch_live_stock_data(symbol, period="1y")
        # Fetches past year up to today
        if not df.empty:
            path = OUTPUT_DIR / f"{symbol}.csv"
            df.to_csv(path, index=False)
            print(f"Successfully saved live data to {path}")
