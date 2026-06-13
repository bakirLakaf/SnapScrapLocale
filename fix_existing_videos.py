import os
import sys
import json
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from webapp.thumbnail_generator import generate_full_video_thumbnail

def fix_video(youtube, video_id, display_name, hashtags_str, is_part1=False, is_part2=False):
    print(f"🔧 Fixing Video: {video_id} ({display_name})...")
    
    sup = "https://creators.sa/saudisnap"
    tt = "https://www.tiktok.com/@dari_falah"
    
    if "ضاري" in display_name or "dari" in display_name.lower():
        extra_h = "#ضاري_الفلاح #Dari #TeamFalcons"
    elif "أصيل" in display_name or "asel" in display_name.lower():
        extra_h = "#أصيل_المبلع #Asel #المبلع"
    else:
        extra_h = ""

    desc = (
        f"🔥 شاهدوا تجميعة أقوى وأحدث سنابات {display_name} لهذا اليوم!\n"
        "استمتعوا بالمشاهدة ولا تنسوا دعمنا بالاشتراك وتفعيل جرس التنبيهات 🔔 ليصلكم كل جديد.\n\n"
        f"💬 للدعم : {sup}\n"
        f"📱 تابعونا على تيك توك: {tt}\n\n"
        f"#Shorts #SaudiArabia #Dari #Saudi #Snapchat {extra_h} #Arabic\n"
        f"#سنابات #تجميعة #{display_name.replace(' ','_')} {hashtags_str}"
    )

    resp = youtube.videos().list(part="snippet", id=video_id).execute()
    if not resp["items"]:
        return False
    
    snippet = resp["items"][0]["snippet"]
    snippet["description"] = desc
    youtube.videos().update(part="snippet", body={"id": video_id, "snippet": snippet}).execute()
    print(f"✅ Metadata updated for {video_id}")
    return True

def main():
    token_dir = BASE_DIR / "stories" / "tokens"
    # Token 12 is the one for 'سنابات ضاري الفلاح'
    t_path = token_dir / "token_12_UCg5d06i5nWe5FihOOilC-Kg.json"
    
    try:
        creds = Credentials.from_authorized_user_file(str(t_path), ["https://www.googleapis.com/auth/youtube.force-ssl"])
        if creds.expired and creds.refresh_token: creds.refresh(Request())
        youtube = build("youtube", "v3", credentials=creds)
        
        # FIXING THE CASE-SENSITIVE ID: zKJ3TBsFtus (Capital K)
        fix_video(youtube, "zKJ3TBsFtus", "ضاري الفلاح", "#ضاري_الفلاح #فالكونز", is_part1=True)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
