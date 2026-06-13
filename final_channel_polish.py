import os
import sys
import json
from pathlib import Path
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from webapp.youtube_service import get_youtube_service

def fix_video(youtube, v_id, vid_type, clean_title, influencer_name):
    try:
        # Get existing snippet
        v_resp = youtube.videos().list(part="snippet", id=v_id).execute()
        if not v_resp["items"]: return False
        snippet = v_resp["items"][0]["snippet"]
        
        if vid_type == "short":
            # Shorts: Empty Desc, Hashtags in Title
            snippet["description"] = ""
            hashtags = "#Shorts #سنابات #أصيل #أصيل_المبلع #المبلع"
            snippet["title"] = f"{clean_title} {hashtags}"[:100]
        else:
            # Full Video: Premium Desc, Clean Title
            snippet["title"] = clean_title
            display_name = influencer_name
            sup = "https://creators.sa/saudisnap"; tt = "https://www.tiktok.com/@dari_falah"
            extra_h = "#ضاري_الفلاح #Dari" if "ضاري" in display_name else "#أصيل #Asel #أصيل_المبلع"
            snippet["description"] = (
                f"🔥 شاهدوا تجميعة أقوى وأحدث سنابات {display_name} لهذا اليوم!\n"
                "استمتعوا بالمشاهدة ولا تنسوا دعمنا بالاشتراك وتفعيل جرس التنبيهات 🔔 ليصلكم كل جديد.\n\n"
                f"💬 للدعم : {sup}\n"
                f"📱 تابعونا على تيك توك: {tt}\n\n"
                f"#Shorts #SaudiArabia #Snapchat {extra_h} #Arabic\n"
                f"#سنابات #تجميعة #{display_name.replace(' ','_')}"
            )
        
        youtube.videos().update(part="snippet", body={"id": v_id, "snippet": snippet}).execute()
        return True
    except Exception as e:
        print(f"❌ Error on {v_id}: {e}")
        return False

def main():
    channel_id = "UCg5d06i5nWe5FihOOilC-Kg"
    print(f"🧐 Getting service for channel {channel_id}...")
    youtube, err = get_youtube_service(channel_id=channel_id)
    if err:
        print(f"❌ Failed to get service: {err}")
        return

    targets = [
        {"id": "TGGJRLUdoJY", "type": "full", "title": "سنابات أصيل | يوم 2026-03-31", "name": "أصيل", "fixed": False},
        {"id": "zKJ3TBsFtus", "type": "full", "title": "سنابات ضاري الفلاح | يوم 2026-03-30 | الجزء 1", "name": "ضاري الفلاح", "fixed": False},
        {"id": "RM4hAuFp1-c", "type": "full", "title": "سنابات ضاري الفلاح | يوم 2026-03-30 | الجزء 2", "name": "ضاري الفلاح", "fixed": False},
        {"id": "7yYmRWogwBY", "type": "full", "title": "سنابات أصيل | يوم 2026-03-28", "name": "أصيل", "fixed": False},
        {"id": "heAaOMSSsBE", "type": "short", "title": "سنابات أصيل | يوم 2026-03-31 | الجزء 1", "name": "أصيل", "fixed": False},
        {"id": "LwoiyNa2Jkw", "type": "short", "title": "سنابات أصيل | يوم 2026-03-31 | الجزء 2", "name": "أصيل", "fixed": False},
        {"id": "CuMx8mgo36E", "type": "short", "title": "سنابات أصيل | يوم 2026-03-31 | الجزء 3", "name": "أصيل", "fixed": False},
        {"id": "30sOVeZLoa0", "type": "short", "title": "سنابات أصيل | يوم 2026-03-31 | الجزء 4", "name": "أصيل", "fixed": False},
        {"id": "TyoeXjBJHKA", "type": "short", "title": "سنابات أصيل | يوم 2026-03-31 | الجزء 5", "name": "أصيل", "fixed": False},
        {"id": "Lsgu_lfz-NM", "type": "short", "title": "سنابات أصيل | يوم 2026-03-31 | الجزء 6", "name": "أصيل", "fixed": False},
        {"id": "RO9XsWgN2fA", "type": "short", "title": "سنابات أصيل | يوم 2026-03-31 | الجزء 7", "name": "أصيل", "fixed": False},
        {"id": "aROSG1xYsmI", "type": "short", "title": "سنابات أصيل | يوم 2026-03-31 | الجزء 8", "name": "أصيل", "fixed": False}
    ]

    fixed_count = 0
    for t in targets:
        if fix_video(youtube, t["id"], t["type"], t["title"], t["name"]):
            print(f"✅ Fixed {t['id']} ({t['type']})")
            fixed_count += 1

    print(f"--- Final Status: {fixed_count}/{len(targets)} Fixed ---")

if __name__ == "__main__":
    main()
