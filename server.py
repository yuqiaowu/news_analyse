import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Import local modules
from datetime import datetime
from news_fetcher import gather_news, fetch_fed_futures, fetch_japan_context, fetch_liquidity_monitor
from price_fetcher import get_market_data

# ... (imports remain same)

load_dotenv()

from contextlib import asynccontextmanager
import subprocess

# Background Scheduler
async def run_scheduler():
    while True:
        print(f"[{datetime.now()}] ⏰ Scheduler waking up...")
        try:
            # Run daily_update.py as a subprocess
            process = await asyncio.create_subprocess_exec(
                "python", "daily_update.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                print(f"[Scheduler] Output: {stdout.decode()}")
            if stderr:
                print(f"[Scheduler] Error: {stderr.decode()}")
                
        except Exception as e:
            print(f"[Scheduler] Failed to run update: {e}")
            
        # Sleep for 4 hours (14400 seconds)
        print(f"[{datetime.now()}] 💤 Scheduler sleeping for 4 hours...")
        await asyncio.sleep(4 * 60 * 60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background task
    print("🚀 Server starting up. Initializing background scheduler...")
    asyncio.create_task(run_scheduler())
    yield
    # Shutdown
    print("🛑 Server shutting down.")

app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY not found in .env")
else:
    genai.configure(api_key=GEMINI_API_KEY)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r") as f:
        return f.read()

async def call_gemini_global_analysis(market_data: List[dict], news_context: str, custom_prompt: Optional[str] = None):
    """
    Call Gemini for a holistic market analysis.
    """
    model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
    
    if custom_prompt:
        prompt = custom_prompt
    else:
        market_str = "\n".join([
            f"- {d['symbol']}: Price ${d['price']:,.2f} | 24h {d['change_24h']:+.2f}% | RSI(4H) {d['rsi_4h']:.1f} | Funding {d['funding_rate']:.4f}% | OI {d['open_interest']:.0f}" 
            for d in market_data
        ])
        
        prompt = f"""
        You are a professional crypto market analyst using the "Narrative vs Reality Check" framework.
        
        **Task**: Analyze the market state by comparing News Narratives vs. Market Reality (Price/RSI/Funding/OI).
        
        **Market Data**:
        {market_str}
        
        **News Context**:
        {news_context}
        
        **Analysis Logic (Narrative vs Reality Check)**:
        1. **News Timing**: Is the news fresh (Impulse) or old (Priced In)?
        2. **Market Reaction**: 
           - **Impulse**: Fresh good news + Price rising + Volume/OI rising.
           - **Priced In**: Good news + Price stalling/dropping.
           - **Divergence**: Good news + Price dropping (Distribution) OR Bad news + Price rising (Accumulation).
        3. **Sentiment & Positioning**:
           - **Oversold**: RSI < 30 & Big Drop.
           - **Crowded Shorts**: Negative Funding + Price Drop (Potential Squeeze).
           - **Aggressive Shorting**: Price Drop + OI Rising.
        
        **Output Format (JSON ONLY)**:
        {{
            "global_summary_cn": "<Markdown text, Simplified Chinese, max 200 words. Summarize the dominant narrative and the reality check. MUST BE PURE CHINESE.>",
            "global_summary_en": "<Markdown text, English, max 200 words. Translate the summary above.>",
            "news_analysis": [
                {{
                    "title_cn": "<News Title (Chinese)>",
                    "title_en": "<News Title (English)>",
                    "classification": "IMPULSE" | "PRICED IN" | "DISTRIBUTION" | "DIVERGENCE" | "NEUTRAL",
                    "reason_cn": "<Why? Chinese>",
                    "reason_en": "<Why? English>"
                }},
                ... (Analyze top 8-10 key news items)
            ],
            "coins": {{
                "BTC": {{ 
                    "sentiment": "Bullish"|"Bearish"|"Neutral", 
                    "score": 0-100, 
                    "comment_cn": "<Short Chinese comment.>",
                    "comment_en": "<Short English comment.>"
                }},
                "ETH": {{ ... }},
                "SOL": {{ ... }},
                "BNB": {{ ... }},
                "DOGE": {{ ... }}
            }}
        }}
        """
    
    try:
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini Global Error: {e}")
        return {
            "global_summary": f"分析失败: {str(e)}",
            "coins": {}
        }

# Global Cache
CACHE_FILE = "latest_analysis.json"
CACHE_EXPIRY = 4 * 60 * 60  # 4 hours

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Check if expired
                ts = datetime.fromisoformat(data["timestamp"])
                if (datetime.now() - ts).total_seconds() < CACHE_EXPIRY:
                    return data
        except Exception as e:
            print(f"⚠️ Cache load failed: {e}")
    return None

@app.get("/api/analyze_all")
async def analyze_all(force_refresh: bool = False):
    # 1. Try Cache First
    if not force_refresh:
        cached_data = load_cache()
        if cached_data:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📦 Serving cached analysis.")
            return cached_data

    start_time = datetime.now()
    print(f"[{start_time.strftime('%H:%M:%S')}] 🚀 Starting FRESH analysis...")

    symbols = ["BTC", "ETH", "SOL", "BNB", "DOGE"]
    
    # 2. Fetch News Globally
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📰 Fetching news...")
    all_news = await asyncio.to_thread(gather_news)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ News fetched.")
    
    # Prepare News Context
    news_text = "=== Macro / Calendar ===\n"
    for item in all_news.get("macro", {}).get("items", [])[:5]:
        news_text += f"- {item.get('title')}\n"
    for item in all_news.get("calendar", {}).get("items", [])[:5]:
        news_text += f"- {item.get('title')}\n"
        
    news_text += "\n=== Crypto News ===\n"
    # Mix top news from categories
    crypto_news = []
    crypto_news.extend(all_news.get("bitcoin", {}).get("items", [])[:5])
    crypto_news.extend(all_news.get("ethereum", {}).get("items", [])[:5])
    crypto_news.extend(all_news.get("general", {}).get("items", [])[:5])
    
    for item in crypto_news:
        news_text += f"- {item.get('title')} ({item.get('published')})\n"

    # 3. Fetch Market Data Concurrently
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 Fetching prices...")
    tasks = [asyncio.to_thread(get_market_data, s) for s in symbols]
    market_results = await asyncio.gather(*tasks)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Prices fetched.")
    
    market_data = []
    for s, res in zip(symbols, market_results):
        res["symbol"] = s
        market_data.append(res)
        
    # 4. Call Gemini ONCE
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 Calling Gemini 2.5...")
    
    # Fetch Fed Futures (Move here to include in prompt)
    fed_data = fetch_fed_futures()
    fed_str = f"Implied Rate: {fed_data.get('implied_rate', 'N/A')}% | Zone: {fed_data.get('zone', 'N/A')} | Trend: {fed_data.get('trend', 'N/A')} | 5D Change: {fed_data.get('change_5d_bps', 'N/A')} bps"
    
    # Fetch Japan Macro (USD/JPY)
    japan_data = fetch_japan_context()
    japan_str = f"USD/JPY: {japan_data.get('price', 'N/A')} | Zone: {japan_data.get('zone', 'N/A')} | Trend: {japan_data.get('trend', 'N/A')} | 5D Change: {japan_data.get('change_5d_pct', 'N/A')}%"

    # Fetch Global Liquidity Monitor (DXY, US10Y, VIX)
    liq_data = fetch_liquidity_monitor()
    
    # Helper to format string safely
    def fmt_liq(key):
        d = liq_data.get(key)
        if not d: return "N/A"
        return f"{d.get('price')} (Trend: {d.get('trend')})"

    liq_str = f"DXY: {fmt_liq('dxy')} | US10Y: {fmt_liq('us10y')} | VIX: {fmt_liq('vix')}"

    # Update prompt to force analyzing ALL news
    market_str = "\n".join([
        f"- {d['symbol']}: Price ${d['price']:,.2f} | 24h {d['change_24h']:+.2f}% | RSI(4H) {d['rsi_4h']:.1f} | Funding {d['funding_rate']:.4f}% | OI {d['open_interest']:.0f}" 
        for d in market_data
    ])
    
    prompt = f"""
    You are a professional crypto market analyst using a "Dual-Layer Analysis" framework: **Macro Liquidity Layer** + **News Narrative Layer**.
    
    **Task**: Analyze the market state by synthesizing Global Liquidity conditions with News Narratives.
    
    **CRITICAL INSTRUCTION**: 
    1. **Layer 1: Liquidity Check**: First, analyze the "Macro Context" (Fed Rate, Japan Carry Trade, DXY/US10Y/VIX). Is the global money tap opening (Risk On) or closing (Risk Off)?
    2. **Layer 2: Narrative Check**: Then, analyze the "News Context". Are the stories bullish or bearish?
    3. **Synthesis**: Compare Layer 1 and Layer 2.
       - **Perfect Storm (Bullish)**: Liquidity Loose + Good News.
       - **Perfect Storm (Bearish)**: Liquidity Tight + Bad News.
       - **Divergence**: Liquidity Tight but News Good (Sell the Rally?). Liquidity Loose but News Bad (Buy the Dip?).
    
    **Market Data**:
    {market_str}
    
    **News Context**:
    {news_text}
    
    **Macro Context**:
    - **Fed Rate Expectations**: {fed_str}
    - **Japan Macro (USD/JPY)**: {japan_str}
    - **Global Liquidity (Risk Conditions)**: {liq_str}
    
    **Analysis Logic**:
    1. **News Timing**: Is the news fresh (Impulse) or old (Priced In)?
    2. **Market Reaction**:
       - **Impulse**: Fresh good news + Price rising + Volume/OI rising.
       - **Priced In**: Good news + Price stalling/dropping.
       - **Divergence**: Good news + Price dropping (Distribution) OR Bad news + Price rising (Accumulation).
    3. **Sentiment & Positioning**:
       - **Oversold**: RSI < 30 & Big Drop.
       - **Crowded Shorts**: Negative Funding + Price Drop (Potential Squeeze).
       - **Aggressive Shorting**: Price Drop + OI Rising.

    **Output Format (JSON ONLY)**:
    {{
        "global_summary": "<Markdown text, Chinese (Simplified), max 250 words. MUST BE IN CHINESE. Start with a 'Liquidity Status' sentence (e.g., '全球流动性正在收紧...'). Then synthesize with the dominant news narrative.>",
        "news_analysis": [
            {{
                "title": "<News Title>",
                "classification": "IMPULSE" | "PRICED IN" | "DISTRIBUTION" | "DIVERGENCE" | "NEUTRAL",
                "reason": "<Why? e.g. 'Good news but price dropped' (Chinese)>"
            }},
            ... (Analyze ALL provided news items)
        ],
        "coins": {{
            "BTC": {{
                "sentiment": "Bullish"|"Bearish"|"Neutral",
                "score": 0-100,
                "comment": "<Short Chinese comment. Use labels like 'Impulse', 'Priced In', 'Oversold', 'Crowded Shorts' etc.>"
            }},
            "ETH": {{ ... }},
            "SOL": {{ ... }},
            "BNB": {{ ... }},
            "DOGE": {{ ... }}
        }}
    }}
    """
    
    analysis_result = await call_gemini_global_analysis(market_data, news_text, prompt) # Pass prompt explicitly
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Gemini analysis complete.")
    
    # 5. Format Response
    # Handle legacy cache: if _cn/_en missing, fallback to old keys
    g_summary = analysis_result.get("global_summary", "")
    
    # Fed Futures already fetched above
    
    response_data = {
        "timestamp": datetime.now().isoformat(),
        "global_summary_cn": analysis_result.get("global_summary_cn", g_summary),
        "global_summary_en": analysis_result.get("global_summary_en", g_summary),
        "news_analysis": analysis_result.get("news_analysis", []),
        "fed_futures": fed_data,
        "japan_macro": japan_data,
        "liquidity_monitor": liq_data,
        "coins": []
    }
    
    coins_analysis = analysis_result.get("coins", {})
    
    for m_data in market_data:
        sym = m_data["symbol"]
        c_analysis = coins_analysis.get(sym, {"sentiment": "Neutral", "score": 50})
        
        # Fallback for comments
        raw_comment = c_analysis.get("comment", "")
        
        response_data["coins"].append({
            "symbol": sym,
            "price": m_data["price"],
            "change_24h": m_data["change_24h"],
            "rsi_4h": m_data.get("rsi_4h", 50),
            "funding_rate": m_data.get("funding_rate", 0),
            "open_interest": m_data.get("open_interest", 0),
            "sentiment": c_analysis.get("sentiment", "Neutral"),
            "score": c_analysis.get("score", 50),
            "comment_cn": c_analysis.get("comment_cn", raw_comment),
            "comment_en": c_analysis.get("comment_en", raw_comment)
        })

    # Helper to clean NaN
    def clean_nan(obj):
        if isinstance(obj, float):
            import math
            if math.isnan(obj):
                return None
        elif isinstance(obj, dict):
            return {k: clean_nan(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_nan(v) for v in obj]
        return obj

    response_data = clean_nan(response_data)
        
    # Save to JSON for user inspection
    with open("latest_analysis.json", "w", encoding="utf-8") as f:
        json.dump(response_data, f, indent=2, ensure_ascii=False)
        
    # Also save raw news for debugging
    with open("latest_news_context.json", "w", encoding="utf-8") as f:
        json.dump({"news_text": news_text}, f, indent=2, ensure_ascii=False)
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏁 Request finished in {(datetime.now() - start_time).total_seconds():.2f}s")
    return response_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
