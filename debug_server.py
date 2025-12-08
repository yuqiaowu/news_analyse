
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load env
load_dotenv()

print("--- 1. Testing Imports ---")
try:
    import google.generativeai as genai
    import requests
    import pandas
    import numpy
    import yfinance
    print("✅ Imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

print("\n--- 2. Testing Gemini Config ---")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY not found")
else:
    print(f"✅ GEMINI_API_KEY found: {api_key[:5]}...")
    try:
        genai.configure(api_key=api_key)
        print("✅ Gemini configured")
    except Exception as e:
        print(f"❌ Gemini configure failed: {e}")

print("\n--- 3. Testing Price Fetcher ---")
try:
    from price_fetcher import get_market_data
    data = get_market_data("BTC")
    print(f"✅ Price Fetcher result: {data}")
except Exception as e:
    print(f"❌ Price Fetcher failed: {e}")

print("\n--- 4. Testing News Fetcher ---")
try:
    from news_fetcher import gather_news, fetch_liquidity_monitor
    
    print("Testing Liquidity Monitor...")
    liq = fetch_liquidity_monitor()
    print(f"✅ Liquidity Data: {liq}")

    # Run sync for test
    news = gather_news()
    print(f"✅ News Fetcher result keys: {news.keys()}")
except Exception as e:
    print(f"❌ News Fetcher failed: {e}")

print("\n--- 5. Testing Gemini Generation ---")
try:
    model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
    response = model.generate_content("Hello, are you working?")
    print(f"✅ Gemini Response: {response.text}")
except Exception as e:
    print(f"❌ Gemini Generation failed: {e}")
