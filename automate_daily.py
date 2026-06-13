import os
import sys
import datetime
import subprocess
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent))

from webapp.youtube_service import upload_from_folder, load_webapp_config

def automate():
    print("🚀 Starting Daily Automation...")
    
    # 1. Determine dates
    # If starting at 00:00 Algeria, we are looking at snaps from 'yesterday'
    now = datetime.datetime.now()
    target_date = now - datetime.timedelta(days=1)
    date_str = target_date.strftime("%Y-%m-%d")
    print(f"📅 Target Date (Snaps from): {date_str}")

    # 2. Scheduling Logic: 9:00 PM KSA (UTC+3)
    # We want to post 'tomorrow' (the day we are currently in, which is the day after we scraped)
    # 9:00 PM KSA = 18:00 UTC
    publish_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
    # If for some reason we are already past 18:00 UTC, schedule for next day
    if publish_time < now:
        publish_time += datetime.timedelta(days=1)
        
    publish_at = publish_time.strftime("%Y-%m-%dT%H:00:00Z")
    print(f"⏰ Scheduled for (UTC): {publish_at}")

    # 3. Load accounts
    config = load_webapp_config()
    accounts = config.get("accounts", [])
    if not accounts:
        # Try to find accounts in the newer webapp_config logic
        from webapp.app import get_accounts
        accounts = get_accounts()

    if not accounts:
        print("⚠️ No accounts found. Please configure them in the dashboard.")
        return

    for acc in accounts:
        username = acc.get("username")
        influencer = acc.get("influencer_name", username)
        if not username: continue
        
        print(f"\n--- Processing: {influencer} ({username}) ---")
        
        # 4. Scrape & Merge using CLI tools
        print(f"🔍 Downloading today's snaps for {username}...")
        try:
            # Step A: Download
            subprocess.run(["python", "SnapScrap.py", username], check=True)
            # Step B: Merge (every 8 for shorts and 'all' for long)
            subprocess.run(["python", "merge_videos.py", username, date_str, "--all"], check=True)
            subprocess.run(["python", "merge_videos.py", username, date_str], check=True)
            print(f"✅ Download and Merge complete for {username}")
        except Exception as e:
            print(f"❌ Scraping/Merging failed for {username}: {e}")
            continue
        
        # 5. Upload (Scheduled)
        merge_dir = Path("stories/merged") / username / date_str
        long_video = merge_dir / "merged_all.mp4"
        
        if long_video.exists():
            print(f"📤 Uploading and Scheduling for {username}...")
            try:
                result = upload_from_folder(
                    username=username,
                    date_str=date_str,
                    privacy="private",
                    upload_type="both",
                    publish_at=publish_at
                )
                if result.get("success"):
                    print(f"✅ [SUCCESS] Uploaded and Scheduled for {username}")
                else:
                    print(f"❌ [FAILED] {result.get('error')}")
            except Exception as e:
                print(f"❌ Upload error: {e}")
        else:
            print(f"⚠️ Skipping {username}: 'merged_all.mp4' not found.")

if __name__ == "__main__":
    automate()

if __name__ == "__main__":
    automate()
