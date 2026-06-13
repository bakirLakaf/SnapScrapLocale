import os
import sys
import json
from pathlib import Path
from datetime import datetime
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

    video_id = "TGGJRLUdoJY"
    print(f"🧐 Checking Video Status: {video_id}...")
    
    resp = youtube.videos().list(part="snippet,status", id=video_id).execute()
    if not resp["items"]:
        print("❌ Video not found.")
        return
    
    video = resp["items"][0]
    snippet = video["snippet"]
    status = video["status"]
    
    print(f"Current Title: {snippet['title']}")
    print(f"Privacy Status: {status['privacyStatus']}")
    print(f"Publish At: {status.get('publishAt', 'NOT SCHEDULED')}")
    
    # RENAME to correct Arabic name
    clean_title = "سنابات أصيل | يوم 2026-03-31"
    snippet["title"] = clean_title
    
    # Restore Premium Description
    display_name = "أصيل"
    sup = "https://creators.sa/saudisnap"; tt = "https://www.tiktok.com/@dari_falah"
    desc = (
        f"🔥 شاهدوا تجميعة أقوى وأحدث سنابات {display_name} لهذا اليوم!\n"
        "استمتعوا بالمشاهدة ولا تنسوا دعمنا بالاشتراك وتفعيل جرس التنبيهات 🔔 ليصلكم كل جديد.\n\n"
        f"💬 للدعم : {sup}\n"
        f"📱 تابعونا على تيك توك: {tt}\n\n"
        f"#Shorts #SaudiArabia #Dari #Saudi #Snapchat #أصيل_المبلع #Asel #المبلع #Arabic\n"
        f"#سنابات #تجميعة #أصيل"
    )
    snippet["description"] = desc
    
    # Update
    # Important: if it's already scheduled, we don't want to change privacyStatus back to private 
    # if it might mess it up, but the API requires it to be private if publishAt is there.
    body = {"id": video_id, "snippet": snippet}
    if "publishAt" in status:
        body["status"] = {"privacyStatus": "private", "publishAt": status["publishAt"]}
    
    youtube.videos().update(part="snippet,status", body=body).execute()
    print(f"✅ Polished! Title set to: {clean_title}")
    if "publishAt" in status:
        print(f"📅 Confirmed: Scheduled for {status['publishAt']} (UTC)")

if __name__ == "__main__":
    main()
