import sys
import os
from pathlib import Path

# Setup paths
BASE_DIR = Path.cwd()
sys.path.insert(0, str(BASE_DIR))

from webapp.youtube_service import upload_from_folder

def main():
    username = "dary_1256"
    date_str = "2026-04-04"
    channel_id = "UCg5d06i5nWe5FihOOilC-Kg"
    privacy = "public"
    
    print(f"Starting upload for {username} on {date_str} to channel {channel_id}...")
    
    def progress_callback(msg):
        print(f"[PROGRESS] {msg}")

    result = upload_from_folder(
        username=username,
        date_str=date_str,
        privacy=privacy,
        upload_type="shorts",
        channel_id=channel_id,
        progress_callback=progress_callback,
        user_id="1" # Using webapp_config_1.json context
    )
    
    if result.get("success"):
        print(f"SUCCESS: Uploaded {result.get('count')} videos.")
    else:
        print(f"FAILED: {result.get('error')}")

if __name__ == "__main__":
    main()
