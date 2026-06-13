#!/usr/bin/env python3
"""
سكريبت رفع يدوي مستقل — يتجاوز Flask ويرفع مباشرة باستخدام التوكن الموجود
"""
import os, sys, json, re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
USERNAME  = "dary_1256"
DATE_STR  = "2026-03-30"
PRIVACY   = "public"

# ── مسارات ──────────────────────────────────────────────────────
merged_folder  = BASE_DIR / "stories" / "merged" / USERNAME / DATE_STR
archive_dir    = merged_folder / "uploaded_youtube"
meta_file      = archive_dir / "upload_meta.json"
tokens_dir     = BASE_DIR / "stories" / "tokens"
secrets_dir    = BASE_DIR / "webapp" / "client_secrets"

archive_dir.mkdir(exist_ok=True)

# ── تحميل السجل ──────────────────────────────────────────────────
upload_history = []
if meta_file.exists():
    try:
        upload_history = json.loads(meta_file.read_text(encoding="utf-8"))
    except: pass

def save_history(entry):
    upload_history.append(entry)
    meta_file.write_text(json.dumps(upload_history, indent=2, ensure_ascii=False), encoding="utf-8")

# ── ملفات الرفع ──────────────────────────────────────────────────
def get_num(p):
    m = re.search(r"merged_(\d+)\.mp4", p.name)
    return int(m.group(1)) if m else 999

shorts  = sorted([p for p in merged_folder.glob("merged_*.mp4") if "merged_all" not in p.name], key=get_num)
full    = merged_folder / "merged_all.mp4"
to_upload = []

already_shorts = len([h for h in upload_history if h.get("type") == "short"])
already_fulls  = len([h for h in upload_history if h.get("type") == "full"])

for path in shorts:
    arc = archive_dir / path.name
    hist = next((h for h in upload_history if h.get("path") == path.name), None)
    if hist and arc.exists() and abs(arc.stat().st_size - path.stat().st_size) < 1024:
        print(f"⏩ مرفوع مسبقاً (مُتحقق): {path.name}")
        continue
    m = re.search(r"merged_(\d+)\.mp4", path.name)
    file_idx = int(m.group(1)) if m else 1
    part = file_idx + already_shorts
    title = f"سنابات ضاري الفلاح | يوم {DATE_STR} | الجزء {part} #سنابات #ضاري_الفلاح #Shorts"[:100]
    to_upload.append(("short", path, title))

if full.exists():
    arc = archive_dir / full.name
    hist = next((h for h in upload_history if h.get("path") == full.name), None)
    if hist and arc.exists() and abs(arc.stat().st_size - full.stat().st_size) < 1024:
        print(f"⏩ مرفوع مسبقاً (مُتحقق): {full.name}")
    else:
        batch = already_fulls + 1
        base  = f"سنابات ضاري الفلاح | يوم {DATE_STR}"
        title = f"{base} | الجزء {batch}" if batch > 1 else base
        to_upload.insert(0, ("full", full, title[:100]))  # full first

if not to_upload:
    print("✅ لا يوجد ملفات جديدة للرفع.")
    sys.exit(0)

print(f"\n📋 سيتم رفع {len(to_upload)} فيديو:\n")
for vt, p, t in to_upload:
    print(f"  [{vt}] {p.name} → {t}")

# ── إيجاد التوكن والـ secret ─────────────────────────────────────
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseUpload

secrets = sorted(secrets_dir.glob("client_secret*.json")) if secrets_dir.exists() else []
if not secrets:
    secrets = sorted(BASE_DIR.glob("client_secret*.json"))

if not secrets:
    print("❌ لا يوجد client_secret! أضف ملف الـ secret في webapp/client_secrets/")
    sys.exit(1)

tokens = []
# البحث في stories/tokens/ أولاً
if tokens_dir.exists():
    tokens = sorted(tokens_dir.glob("token_*.json"))
    print(f"🔍 وجدت {len(tokens)} توكن في {tokens_dir}")
    for t in tokens:
        print(f"   - {t.name}")
# Fallback للجذر
if not tokens:
    t = BASE_DIR / "token.json"
    tokens = [t] if t.exists() else []
    print("🔍 استخدام token.json من المجلد الجذر كـ fallback")


if not tokens:
    print("❌ لا يوجد token! أضف token عبر لوحة التحكم.")
    sys.exit(1)

# prioritized tokens first
prioritized_tokens = [t for t in tokens if "token_12" in t.name]
other_tokens = [t for t in tokens if "token_12" not in t.name]
all_to_try = prioritized_tokens + other_tokens

# جرّب أول توكن صالح
youtube = None
for tok_path in all_to_try:
    for sec_path in secrets:
        try:
            print(f"🔄 تجربة: {tok_path.name} مع {sec_path.name}...")
            sec = json.loads(sec_path.read_text())
            sec_data = sec.get("installed") or sec.get("web") or {}
            tok = json.loads(tok_path.read_text())
            creds = Credentials(
                token=tok.get("token") or tok.get("access_token"),
                refresh_token=tok.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=tok.get("client_id") or sec_data.get("client_id"),
                client_secret=tok.get("client_secret") or sec_data.get("client_secret"),
            )
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            temp_service = build("youtube", "v3", credentials=creds)
            # اختبر الاتصال
            temp_service.channels().list(part="id", mine=True).execute()
            youtube = temp_service
            print(f"\n✅ الجندي جاهز: {tok_path.name}\n")
            break
        except Exception as e:
            # print(f"⚠️ {tok_path.name}: {e}") # keep logs quiet unless test fails
            pass
    if youtube:
        break

if not youtube:
    print("❌ فشل الاتصال بكل التوكنات!")
    sys.exit(1)

# ── الرفع ────────────────────────────────────────────────────────
for i, (vid_type, path, title) in enumerate(to_upload, 1):
    print(f"\n{'='*50}")
    print(f"🚀 [{i}/{len(to_upload)}] رفع {path.name}")
    print(f"   العنوان: {title}")
    
    if vid_type == "short":
        desc  = ""
        tags  = ["Shorts", "سنابات", "ضاري الفلاح"]
    else:
        desc  = (
            "🔥 شاهدوا تجميعة أقوى وأحدث سنابات ضاري الفلاح لهذا اليوم!\n"
            "استمتعوا بالمشاهدة ولا تنسوا دعمنا بالاشتراك وتفعيل جرس التنبيهات 🔔\n\n"
            "#سنابات #ضاري_الفلاح #تجميعة"
        )
        tags  = ["سنابات", "تجميعة", "ضاري الفلاح"]

    body = {
        "snippet": {"title": title, "description": desc, "tags": tags[:15], "categoryId": "22"},
        "status":  {"privacyStatus": PRIVACY},
    }
    try:
        with open(str(path), "rb") as vf:
            media    = MediaIoBaseUpload(vf, mimetype="video/mp4", resumable=True, chunksize=4*1024*1024)
            response = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        
        vid_id   = response.get("id", "")
        print(f"   ✅ تم الرفع! ID: {vid_id}")
        
        # أرشفة نسخة
        import shutil
        arc = archive_dir / path.name
        if arc.exists():
            arc = archive_dir / f"{path.stem}_{int(datetime.now().timestamp())}{path.suffix}"
        shutil.copy2(str(path), str(arc))
        
        save_history({"id": vid_id, "title": title, "type": vid_type, "path": path.name, "timestamp": str(datetime.now())})
        
    except Exception as e:
        print(f"   ❌ خطأ: {e}")

print(f"\n{'='*50}")
print("🏆 اكتمل الرفع اليدوي!")
