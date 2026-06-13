"""
Retroactive YouTube Video Description Updater
Usage: run this script directly to update all videos in a specific channel's uploaded playlist.
"""

import sys
from pathlib import Path

# Add webapp directory to path so we can import services
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from youtube_service import (
    get_youtube_service,
    _get_client_secrets,
    _get_token_for_secret,
    _get_all_tokens_for_channel,
    _token_path,
    get_tokens_dir,
    get_user_id
)

def get_army_of_apis(channel_id):
    user_id = get_user_id()
    army = []
    used_tokens = set()
    all_secrets = _get_client_secrets()
    
    if all_secrets:
        # 1. Add tokens that match secrets by name
        for s in all_secrets:
            t = _get_token_for_secret(channel_id, user_id, s)
            if t.exists():
                army.append((t, s))
                used_tokens.add(str(t))
        
        # 2. Add all other tokens found for this channel (Reserve tokens)
        for t in _get_all_tokens_for_channel(channel_id, user_id):
            if str(t) not in used_tokens:
                army.append((t, all_secrets[0]))
                used_tokens.add(str(t))
    else:
        for t in _get_all_tokens_for_channel(channel_id, user_id):
            if t.exists():
                army.append((t, None))
                used_tokens.add(str(t))

    if not army:
        primary_token = _token_path(channel_id, user_id) if channel_id else (get_tokens_dir(user_id) / "token.json")
        default_secret = all_secrets[0] if all_secrets else None
        army.append((primary_token, default_secret))
    
    return army

def update_channel_videos(channel_id, additional_hashtags):
    """
    Fetches all videos from a channel's Uploads playlist and appends 'additional_hashtags'
    to their descriptions if not already present.
    """
    army = get_army_of_apis(channel_id)
    youtube = None
    
    for current_token, current_secret in army:
        yt, err = get_youtube_service(channel_id=channel_id, token_path_override=current_token, client_secret_path=current_secret)
        if not err:
            youtube = yt
            print(f"✅ Authenticated using token: {current_token.name}")
            break
            
    if not youtube:
        print(f"❌ Error getting YouTube service: Could not authenticate with any token.")
        return

    try:
        # Get the 'Uploads' playlist ID for the channel
        channel_resp = youtube.channels().list(part="contentDetails", id=channel_id).execute()
        if not channel_resp.get("items"):
            print("❌ Channel not found.")
            return
            
        uploads_playlist_id = channel_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        print(f"📥 Found Uploads Playlist ID: {uploads_playlist_id}")

        # Fetch videos in the playlist (paginated)
        video_ids = []
        next_page_token = None
        while True:
            playlist_resp = youtube.playlistItems().list(
                part="snippet", 
                playlistId=uploads_playlist_id, 
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            
            for item in playlist_resp.get("items", []):
                video_ids.append(item["snippet"]["resourceId"]["videoId"])
                
            next_page_token = playlist_resp.get("nextPageToken")
            if not next_page_token:
                break
                
        print(f"📺 Found {len(video_ids)} videos. Starting update...")

        # Update each video's description
        updated_count = 0
        for i in range(0, len(video_ids), 50): # Can update max 50 at a time via list API
            chunk = video_ids[i:i+50]
            videos_resp = youtube.videos().list(part="snippet,status", id=",".join(chunk)).execute()
            
            for video in videos_resp.get("items", []):
                vid_id = video["id"]
                current_title = video["snippet"]["title"]
                current_description = video["snippet"]["description"]
                
                base_title = current_title.replace(additional_hashtags, "").strip()
                new_title = f"{base_title} {additional_hashtags}"
                if len(new_title) > 100:
                    new_title = new_title[:100]
                    
                new_description = ""
                
                # Check if an update is actually needed (if title changed or description is not empty)
                if current_title != new_title or current_description != "":
                    
                    # We need to send categoryId too, otherwise it defaults to Film & Animation (1)
                    category_id = video["snippet"].get("categoryId", "22") 
                    
                    body = {
                        "id": vid_id,
                        "snippet": {
                            "title": new_title,
                            "description": new_description,
                            "categoryId": category_id,
                            "tags": video["snippet"].get("tags", [])
                        }
                    }
                    
                    # Try uploading with available tokens
                    success = False
                    for current_token, current_secret in army:
                        yt, err = get_youtube_service(channel_id=channel_id, token_path_override=current_token, client_secret_path=current_secret)
                        if err: continue
                        try:
                            yt.videos().update(part="snippet", body=body).execute()
                            print(f"✅ Updated: '{title}' (via {current_token.name})")
                            updated_count += 1
                            success = True
                            break # Move to next video
                        except Exception as e:
                            # 403 means this token lacks permission, try next
                            if "403" in str(e) or "insufficient authentication scopes" in str(e):
                                continue
                            print(f"⚠️ Error trying to update '{new_title}' with {current_token.name}: {e}")
                            
                    if not success:
                        print(f"❌ Failed to update '{new_title}': none of the tokens had permission.")
                else:
                    print(f"⏭️ Skipped (already updated): '{current_title}'")
                    
        print(f"\n🎉 Finished! Updated {updated_count} out of {len(video_ids)} videos.")

    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    # The channel ID to update
    CHANNEL_ID = "UCg5d06i5nWe5FihOOilC-Kg" # Dari's actual channel ID
    
    # The hashtags the user requested
    HASHTAGS = "#Shorts #SaudiArabia #Dari #Saudi #Snapchat #ضاري_الفلاح"
    
    print("-" * 40)
    print(f"Will apply hashtags: {HASHTAGS}")
    print("-" * 40)
    
    update_channel_videos(CHANNEL_ID, HASHTAGS)
