import os
import json

from datetime import datetime
from server import analyze_all, clean_nan



async def main():
    print(f"[{datetime.now()}] 🚀 Starting Daily Update...")
    
    # 1. Run Analysis
    try:
        data = await analyze_all(force_refresh=True)
        
        # Ensure data is clean
        data = clean_nan(data)
        
        # Save to file
        with open("latest_analysis.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("✅ Analysis saved to latest_analysis.json")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return

    # 2. Update GitHub via API (No git CLI needed)
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = "yuqiaowu/news_analyse" # Hardcoded for simplicity
    file_path = "latest_analysis.json"
    
    if not github_token:
        print("❌ GITHUB_TOKEN not found.")
    else:
        try:
            import requests
            import base64
            
            # 1. Get current SHA of the file
            url = f"https://api.github.com/repos/{repo_name}/contents/{file_path}"
            headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            sha = None
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                sha = resp.json().get("sha")
                
            # 2. Prepare content
            content_str = json.dumps(data, indent=2, ensure_ascii=False)
            content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
            
            # 3. Push update
            payload = {
                "message": "Update market analysis data [skip ci]",
                "content": content_b64,
                "branch": "main"
            }
            if sha:
                payload["sha"] = sha
                
            resp = requests.put(url, headers=headers, json=payload)
            
            if resp.status_code in [200, 201]:
                 print("✅ Data pushed to GitHub successfully via API!")
            else:
                 print(f"❌ GitHub API failed: {resp.status_code} {resp.text}")

        except Exception as e:
            print(f"❌ GitHub operations failed: {e}")

    # 3. Trigger Vercel Deploy (Since we used [skip ci])
    vercel_hook = os.getenv("VERCEL_DEPLOY_HOOK")
    if vercel_hook:
        if not vercel_hook.startswith("http"):
            vercel_hook = "https://" + vercel_hook
            
        try:
            import requests
            print(f"[{datetime.now()}] 🚀 Triggering Vercel deployment...")
            response = requests.post(vercel_hook)
            if response.status_code == 200:
                print("✅ Vercel deployment triggered successfully!")
            else:
                print(f"❌ Failed to trigger Vercel: {response.status_code} {response.text}")
        except Exception as e:
            print(f"❌ Failed to trigger Vercel: {e}")
    else:
        print("⚠️ VERCEL_DEPLOY_HOOK not found. Skipping Vercel trigger.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
