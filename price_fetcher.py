import requests
import pandas as pd
import numpy as np

HTTP_TIMEOUT = 10

def calculate_rsi(prices, period=14):
    """Calculate RSI from a list of prices."""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum()/period
    down = -seed[seed < 0].sum()/period
    rs = up/down
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100./(1. + rs)

    for i in range(period, len(prices)):
        delta = deltas[i-1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up/down
        rsi[i] = 100. - 100./(1. + rs)
        
    return rsi[-1]

def get_market_data(symbol: str) -> dict:
    """
    Fetch comprehensive market data:
    - Price & 24h Change
    - RSI (4H, 14)
    - Funding Rate
    - Open Interest
    """
    # Ensure symbol format
    if not symbol.endswith("-USDT"):
        instId = f"{symbol}-USDT"
    else:
        instId = symbol
        
    swap_instId = instId.replace("-USDT", "-USDT-SWAP")
    
    result = {
        "price": 0.0,
        "change_24h": 0.0,
        "rsi_4h": 50.0,
        "funding_rate": 0.0,
        "open_interest": 0.0
    }
    
    # 1. Ticker (Price & Change)
    try:
        url = f"https://www.okx.com/api/v5/market/ticker?instId={instId}"
        resp = requests.get(url, timeout=HTTP_TIMEOUT)
        data = resp.json()
        if data.get("code") == "0" and data.get("data"):
            ticker = data["data"][0]
            last = float(ticker["last"])
            open24h = float(ticker["open24h"])
            change_pct = ((last - open24h) / open24h) * 100 if open24h else 0.0
            result["price"] = last
            result["change_24h"] = change_pct
    except Exception as e:
        print(f"⚠️ Ticker failed for {symbol}: {e}")

    # 2. RSI (Candles 4H)
    try:
        url = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar=4H&limit=100"
        resp = requests.get(url, timeout=HTTP_TIMEOUT)
        data = resp.json()
        if data.get("code") == "0" and data.get("data"):
            # OKX returns [ts, o, h, l, c, ...] newest first
            candles = data["data"]
            closes = [float(c[4]) for c in candles]
            closes.reverse() # Oldest first
            result["rsi_4h"] = calculate_rsi(closes)
    except Exception as e:
        print(f"⚠️ RSI failed for {symbol}: {e}")

    # 3. Funding Rate
    try:
        url = f"https://www.okx.com/api/v5/public/funding-rate?instId={swap_instId}"
        resp = requests.get(url, timeout=HTTP_TIMEOUT)
        data = resp.json()
        if data.get("code") == "0" and data.get("data"):
            result["funding_rate"] = float(data["data"][0]["fundingRate"]) * 100 # %
    except Exception as e:
        print(f"⚠️ Funding failed for {symbol}: {e}")

    # 4. Open Interest
    try:
        url = f"https://www.okx.com/api/v5/public/open-interest?instId={swap_instId}"
        resp = requests.get(url, timeout=HTTP_TIMEOUT)
        data = resp.json()
        if data.get("code") == "0" and data.get("data"):
            # oi is in contracts usually, but let's just use it as a raw number for trend
            # Or use oiCcy if available for coin amount
            result["open_interest"] = float(data["data"][0]["oi"]) 
    except Exception as e:
        print(f"⚠️ OI failed for {symbol}: {e}")
        
    return result

if __name__ == "__main__":
    print(get_market_data("BTC"))
    print(f"ETH: {get_current_price('ETH')}")
