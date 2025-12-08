import os
import json
import subprocess
from datetime import datetime
from server import analyze_all, clean_nan

def run_git_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {command}: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"❌ {command} failed: {e.stderr.strip()}")
        raise

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

    # 2. Git Push
    # Note: Railway needs GITHUB_TOKEN env var for authentication
    github_token = os.getenv("GITHUB_TOKEN")
    repo_url = os.getenv("REPO_URL", "https://github.com/yuqiaowu/news_analyse.git")
    
    if github_token:
        # Inject token into URL: https://TOKEN@github.com/user/repo.git
        auth_repo_url = repo_url.replace("https://", f"https://{github_token}@")
    else:
        print("⚠️ GITHUB_TOKEN not found. Assuming local or SSH auth.")
        auth_repo_url = repo_url

    try:
        run_git_command("git config user.name 'AI Analyst'")
        run_git_command("git config user.email 'ai@railway.app'")
        run_git_command("git add latest_analysis.json")
        
        # Check if there are changes
        status = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
        if not status.stdout.strip():
            print("No changes to commit.")
            return

        run_git_command("git commit -m 'Update market analysis data [skip ci]'")
        run_git_command(f"git push {auth_repo_url} main")
        print("✅ Data pushed to GitHub successfully!")
        
    except Exception as e:
        print(f"❌ Git operations failed: {e}")

    # 3. Trigger Vercel Deploy (Since we used [skip ci])
    vercel_hook = os.getenv("VERCEL_DEPLOY_HOOK")
    if vercel_hook:
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
