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

from webapp.youtube_service import get_youtube_service, upload_from_folder
from webapp.thumbnail_generator import generate_full_video_thumbnail

def get_service(token_path):
    creds = Credentials.from_authorized_user_file(str(token_path), ["https://www.googleapis.com/auth/youtube.force-ssl"])
    if creds.expired and creds.refresh_token: creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)

def restore_video(youtube, video_id, clean_title, display_name, hashtags_str):
    print(f"🔧 Restoring Video: {video_id} -> '{clean_title}'")
    # Metadata
    sup = "https://creators.sa/saudisnap"; tt = "https://www.tiktok.com/@dari_falah"
    if "ضاري" in display_name or "dari" in display_name.lower():
        extra_h = "#ضاري_الفلاح #Dari #TeamFalcons"
    elif "أصيل" in display_name or "asel" in display_name.lower():
        extra_h = "#أصيل_المبلع #Asel #المبلع"
    else: extra_h = ""

    desc = (
        f"🔥 شاهدوا تجميعة أقوى وأحدث سنابات {display_name} لهذا اليوم!\n"
        "استمتعوا بالمشاهدة ولا تنسوا دعمنا بالاشتراك وتفعيل جرس التنبيهات 🔔 ليصلكم كل جديد.\n\n"
        f"💬 للدعم : {sup}\n"
        f"📱 تابعونا على تيك توك: {tt}\n\n"
        f"#Shorts #SaudiArabia #Dari #Saudi #Snapchat {extra_h} #Arabic\n"
        f"#سنابات #تجميعة #{display_name.replace(' ','_')} " + " ".join([f"#{h.strip('#')}" for h in hashtags_str.split()])
    )

    try:
        resp = youtube.videos().list(part="snippet", id=video_id).execute()
        if not resp["items"]: return False
        snippet = resp["items"][0]["snippet"]
        snippet["title"] = clean_title
        snippet["description"] = desc
        youtube.videos().update(part="snippet", body={"id": video_id, "snippet": snippet}).execute()
        print(f"✅ Success!")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    token_dir = BASE_DIR / "stories" / "tokens"
    token_dari = token_dir / "token_12_UCg5d06i5nWe5FihOOilC-Kg.json"
    
    y_dari = get_service(token_dari)

    # 1. Fix Dari Full Videos (30-03)
    # Part 1 (zKJ3TBsFtus) - case sensitive!
    restore_video(y_dari, "zKJ3TBsFtus", "سنابات ضاري الفلاح | يوم 2026-03-30 | الجزء 1", "ضاري الفلاح", "#ضاري_الفلاح")
    # Part 2 (RM4hAuFp1-c)
    restore_video(y_dari, "RM4hAuFp1-c", "سنابات ضاري الفلاح | يوم 2026-03-30 | الجزء 2", "ضاري الفلاح", "#ضاري_الفلاح")

    # 2. Fix Asel 28-03 Full (7yYmRWogwBY)
    restore_video(y_dari, "7yYmRWogwBY", "سنابات أصيل | يوم 2026-03-28", "أصيل", "#أصيل #المبلع")

    # 3. Fix ALL Asel Shorts from today (31-03)
    asel_shorts = {
        "heAaOMSSsBE": 1, "LwoiyNa2Jkw": 2, "CuMx8mgo36E": 3, "30sOVeZLoa0": 4,
        "TyoeXjBJHKA": 5, "Lsgu_lfz-NM": 6, "RO9XsWgN2fA": 7, "aROSG1xYsmI": 8
    }
    for v_id, part in asel_shorts.items():
        title = f"سنابات أصيل | يوم 2026-03-31 | الجزء {part}"
        restore_video(y_dari, v_id, title, "أصيل", "#أصيل #المبلع")

    # 4. UPLOAD Missing Asel Full Video (31-03)
    print("🚀 Triggering upload for Asel's missing full video (31-03)...")
    merged_folder = BASE_DIR / "stories" / "merged" / "asel.alm" / "2026-03-31"
    # We use upload_from_folder with upload_type="full" to specifically do the combined video
    # and provide the user's requested scheduling time for today.
    # Note: user put 19:00 locally. In +01:00 this is 18:00 UTC.
    res = upload_from_folder("asel.alm", "2026-03-31", privacy_status="private", upload_type="full", publish_time="2026-03-31T18:00:00Z")
    print(f"📦 Upload Result: {res}")

if __name__ == "__main__":
    main()
