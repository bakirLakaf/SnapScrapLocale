import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def main():
    token_dari = BASE_DIR / "stories" / "tokens" / "token_12_UCg5d06i5nWe5FihOOilC-Kg.json"
    creds = Credentials.from_authorized_user_file(str(token_dari), ["https://www.googleapis.com/auth/youtube.force-ssl"])
    if creds.expired and creds.refresh_token: creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds)

    # 1. FIX FULL VIDEO TITLE (أصيل)
    full_video_id = "TGGJRLUdoJY"
    print(f"🔧 Fixing Full Video: {full_video_id}")
    youtube.videos().update(part="snippet", body={
        "id": full_video_id,
        "snippet": {
            "title": "سنابات أصيل | يوم 2026-03-31",
            "description": "🔥 شاهدوا تجميعة أقوى وأحدث سنابات أصيل لهذا اليوم!\n\n💬 للدعم : https://creators.sa/saudisnap\n📱 تيك توك: https://www.tiktok.com/@dari_falah\n\n#Shorts #SaudiArabia #Asel #أصيل",
            "categoryId": "22"
        }
    }).execute()
    print("✅ Full video renamed to 'أصيل'")

    # 2. SCHEDULE ALL SHORTS (19:00 Local = 18:00 UTC)
    asel_shorts = [
        "heAaOMSSsBE", "LwoiyNa2Jkw", "CuMx8mgo36E", "30sOVeZLoa0",
        "TyoeXjBJHKA", "Lsgu_lfz-NM", "RO9XsWgN2fA", "aROSG1xYsmI"
    ]
    
    base_time = datetime(2026, 3, 31, 18, 0, 0) # 18:00 UTC
    
    for i, v_id in enumerate(asel_shorts):
        publish_at = (base_time + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        title = f"سنابات أصيل | يوم 2026-03-31 | الجزء {i+1}"
        print(f"📅 Scheduling Short {v_id} for {publish_at}...")
        
        # Get existing snippet to preserve it
        v_resp = youtube.videos().list(part="snippet", id=v_id).execute()
        if not v_resp["items"]: continue
        snippet = v_resp["items"][0]["snippet"]
        snippet["title"] = title
        
        youtube.videos().update(part="snippet,status", body={
            "id": v_id,
            "snippet": snippet,
            "status": {
                "privacyStatus": "private",
                "publishAt": publish_at
            }
        }).execute()
        print(f"✅ Short {i+1} Scheduled!")

if __name__ == "__main__":
    main()
