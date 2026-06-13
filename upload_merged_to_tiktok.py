import os
import re
import json
from pathlib import Path
from webapp.tiktok_bot import upload_to_tiktok

# Configuration
BASE_MERGED_DIR = Path("w:/AntiGravity/SnapScrap_Local/stories/merged")
CONFIG_DIR = Path("w:/AntiGravity/SnapScrap_Local/stories/config")
HASHTAGS = "#fyp #for_your_page #سنابات #يوميات #ستوريات"

def load_all_configs():
    """Load all webapp_config_*.json files and return a username -> influencer_name map."""
    name_map = {}
    if not CONFIG_DIR.exists():
        return name_map
        
    for cfg_file in CONFIG_DIR.glob("webapp_config_*.json"):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                accounts = cfg.get("accounts", [])
                for acc in accounts:
                    username = acc.get("username")
                    display = acc.get("influencer_name") or username
                    name_map[username] = display
        except Exception as e:
            print(f"⚠️ Error loading config {cfg_file.name}: {e}")
    return name_map

def get_pending_videos(name_map):
    """Scan all user folders for pending videos."""
    pending = []
    if not BASE_MERGED_DIR.exists():
        return []
        
    user_folders = [d for d in BASE_MERGED_DIR.iterdir() if d.is_dir()]
    
    for user_dir in user_folders:
        username = user_dir.name
        display_name = name_map.get(username, username)
        
        # Tracking file location
        track_file = user_dir / "tiktok_uploaded.txt"
        uploaded_set = set()
        if track_file.exists():
            uploaded_set = set(track_file.read_text(encoding="utf-8").splitlines())
            
        for date_folder in sorted(user_dir.iterdir(), reverse=True):
            if not date_folder.is_dir():
                continue
                
            date_str = date_folder.name
            # Look in main date folder and uploaded_youtube subfolder
            search_paths = [date_folder, date_folder / "uploaded_youtube"]
            
            for path in search_paths:
                if not path.exists():
                    continue
                for video_file in sorted(path.glob("merged_*.mp4")):
                    if "merged_all" in video_file.name:
                        continue
                    
                    vid_id = f"{date_str}/{video_file.name}"
                    if vid_id in uploaded_set:
                        continue
                        
                    match = re.search(r"merged_(\d+)\.mp4", video_file.name)
                    part = match.group(1) if match else "1"
                    
                    pending.append({
                        "username": username,
                        "display_name": display_name,
                        "track_file": track_file,
                        "id": vid_id,
                        "path": str(video_file),
                        "date": date_str,
                        "part": part,
                        "title": f"سنابات {display_name} | يوم {date_str} | الجزء {part}"
                    })
    return pending

def save_uploaded(track_file, vid_id):
    with open(track_file, "a", encoding="utf-8") as f:
        f.write(vid_id + "\n")

def main():
    print("🔍 Scanning for pending TikTok uploads...")
    name_map = load_all_configs()
    videos = get_pending_videos(name_map)
    
    if not videos:
        print("✅ No pending videos found. Everything is uploaded!")
        return
        
    print(f"🎬 Found {len(videos)} pending videos across all accounts.")
    
    success_count = 0
    for i, vid in enumerate(videos):
        print(f"\n--- [{i+1}/{len(videos)}] Client: {vid['display_name']} | Part {vid['part']} ---")
        caption = f"{vid['title']}\n\n{HASHTAGS}"
        
        # Retry logic for the browser-based upload
        max_retries = 3
        upload_success = False
        for attempt in range(max_retries):
            try:
                print(f"🚀 Upload attempt {attempt+1}/{max_retries}...")
                if upload_to_tiktok(vid["path"], caption):
                    upload_success = True
                    break
                else:
                    print(f"⚠️ Attempt {attempt+1} failed.")
            except Exception as e:
                print(f"⚠️ Unexpected error during attempt {attempt+1}: {e}")
            
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10
                print(f"⏳ Waiting {wait_time}s before retry...")
                import time
                time.sleep(wait_time)
        
        if upload_success:
            success_count += 1
            print(f"✅ Successful upload!")
            save_uploaded(vid["track_file"], vid["id"])
            
            # Move to uploaded_tiktok folder
            try:
                import shutil
                video_path = Path(vid["path"])
                # The archive should be in user_dir/uploaded_tiktok
                archive_dir = Path(vid["path"]).parent.parent / "uploaded_tiktok"
                archive_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(video_path), str(archive_dir / video_path.name))
                print(f"📦 Moved to archive.")
            except Exception as mv_err:
                print(f"⚠️ Failed to move file: {mv_err}")
        else:
            print(f"❌ Failed all {max_retries} attempts for {vid['path']}. Skipping to next...")
            
    print(f"\n🏁 Batch Complete! Uploaded {success_count}/{len(videos)} videos.")

if __name__ == "__main__":
    main()
