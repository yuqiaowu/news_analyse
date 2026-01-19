import asyncio
import os
import json
from server import analyze_all

async def reproduce():
    print("Starting reproduction...")
    try:
        data = await analyze_all(force_refresh=True)
        print("Analysis complete!")
        print(f"Timestamp: {data.get('timestamp')}")
        print(f"News items count: {len(data.get('news_analysis', []))}")
        print(f"Coins count: {len(data.get('coins', []))}")
        
        # Check if news analysis is missing
        if not data.get('news_analysis'):
            print("⚠️ News analysis is EMPTY!")
        else:
            print("✅ News analysis found.")
            
        # Check if summary is missing
        if not data.get('global_summary_cn'):
            print("⚠️ Global summary (CN) is EMPTY!")
        else:
            print("✅ Global summary (CN) found.")

    except Exception as e:
        print(f"❌ Error during analysis: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce())
