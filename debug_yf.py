
import yfinance as yf
import pandas as pd

def test_ticker(symbol):
    print(f"\n--- Testing {symbol} ---")
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        print(hist)
        if hist.empty:
            print("❌ Empty history")
        else:
            print(f"✅ Last Close: {hist['Close'].iloc[-1]}")
    except Exception as e:
        print(f"❌ Error: {e}")

tickers = ["DX-Y.NYB", "^TNX", "^VIX", "GC=F"] # Added Gold for reference
for t in tickers:
    test_ticker(t)
