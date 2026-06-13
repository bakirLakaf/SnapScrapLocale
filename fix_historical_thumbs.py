import os
import sys
import re
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent))

from webapp.youtube_service import get_youtube_service, _get_all_tokens_for_channel, _get_client_secrets
from webapp.thumbnail_generator import generate_full_video_thumbnail
from googleapiclient.http import MediaIoBaseUpload

CHANNEL_ID = "UCg5d06i5nWe5FihOOilC-Kg"
INFLUENCER_NAME = "ضاري الفلاح"
USERNAME = "dary_1256"
MERGED_BASE = Path("stories/merged") / USERNAME

def fix_thumbs():
    print(f"🔄 Starting thumbnail fix for channel: {CHANNEL_ID} ({INFLUENCER_NAME})")
    
    youtube, err = get_youtube_service(channel_id=CHANNEL_ID)
    if err:
        print(f"❌ Error connecting to YouTube: {err}")
        return

    # List last 50 videos
    try:
        request = youtube.search().list(
            channelId=CHANNEL_ID,
            part="snippet",
            order="date",
            maxResults=50,
            type="video"
        )
        response = request.execute()
        videos = response.get("items", [])
    except Exception as e:
        print(f"❌ Error fetching videos: {e}")
        return

    print(f"📹 Found {len(videos)} videos. Processing...")

    for v in videos:
        video_id = v["id"]["videoId"]
        title = v["snippet"]["title"]
        print(f"--- Checking: {title} ({video_id}) ---")
        
        # Match date in title: e.g. "سنابات ضاري | يوم 2026-03-25"
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
        if not date_match:
            print("⚠️ No date found in title. Skipping.")
            continue
            
        date_str = date_match.group(1)
        video_path = MERGED_BASE / date_str / "merged_all.mp4"
        
        if not video_path.exists():
            # Try merged_1.mp4 if merged_all doesn't exist (maybe it was a single short)
            video_path = MERGED_BASE / date_str / "merged_1.mp4"
            
        if not video_path.exists():
            print(f"❌ Local video file not found for date {date_str}. Skipping.")
            continue

        # Generate new thumbnail
        thumb_path = MERGED_BASE / date_str / f"new_thumb_{video_id}.jpg"
        print(f"🎨 Generating new thumbnail for {date_str}...")
        
        if generate_full_video_thumbnail(str(video_path), str(thumb_path), INFLUENCER_NAME, date_str):
            # Upload to YouTube
            try:
                with open(str(thumb_path), "rb") as f:
                    youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaIoBaseUpload(f, mimetype="image/jpeg")
                    ).execute()
                print(f"✅ [SUCCESS] Thumbnail updated for: {video_id}")
            except Exception as up_err:
                print(f"❌ [FAILED] Error uploading thumb: {up_err}")
        else:
            print(f"❌ Failed to generate thumb for {video_id}")

if __name__ == "__main__":
    fix_thumbs()
