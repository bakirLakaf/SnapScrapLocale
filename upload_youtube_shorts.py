#!/usr/bin/env python3
"""
رفع الفيديوهات المدمجة (من مجلد merged) إلى يوتيوب كـ Shorts.
يحتاج: تفعيل YouTube Data API v3 وحساب Google وملف OAuth (client_secret.json).
"""
import os
import sys
import glob
from datetime import date

# Fix Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("ثبّت الحزم أولاً: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
MERGED_DIR = "merged" # Only used as a fallback or name


import random

def _find_client_secret(script_dir):
    """Find client_secret.json - pick random if multiple exist to balance quota."""
    parent = os.path.dirname(script_dir)
    secrets = []
    for d in (script_dir, parent):
        for p in glob.glob(os.path.join(d, "client_secret*.json")):
            if "client_secrets.json" not in p:
                secrets.append(p)
    if secrets:
        chosen = random.choice(secrets)
        print(f"تم اختيار ملف الـ API: {os.path.basename(chosen)}")
        return chosen
    
    for d in (script_dir, parent):
        for name in ("client_secret.json", "client_secrets.json"):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    return None


def get_youtube_service(script_dir):
    """OAuth and return YouTube API service."""
    creds = None
    client_path = _find_client_secret(script_dir)
    if not client_path:
        print("ضع ملف client_secret.json (من Google Cloud Console) في مجلد المشروع.")
        print("كيف: https://developers.google.com/youtube/v3/quickstart/python")
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(client_path))[0]
    suffix = base_name.replace("client_secret", "")
    token_name = f"token{suffix}.json"
    
    token_path = os.path.join(os.path.dirname(client_path), token_name)
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, file_path, title, description, privacy="private"):
    """Upload one video to YouTube."""
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["Shorts", "Snapchat"],
            "categoryId": "22",
        },
        "status": {"privacyStatus": privacy},
    }
    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True, chunksize=1024 * 1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    return response.get("id")


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("استخدام: python upload_youtube_shorts.py <username> [YYYY-MM-DD] [public|private|unlisted]")
        print("مثال:   python upload_youtube_shorts.py dary_1256 private")
        print("         python upload_youtube_shorts.py dary_1256 2025-02-15 public")
        print("\nقائمة كل الأوامر: python SnapScrap.py help")
        sys.exit(0)
    if len(sys.argv) < 2:
        print("استخدام: python upload_youtube_shorts.py <username> [YYYY-MM-DD] [public|private|unlisted]")
        print("مثال:   python upload_youtube_shorts.py dary_1256 private")
        print("         python upload_youtube_shorts.py dary_1256 2025-02-15 public")
        sys.exit(1)

    username = sys.argv[1]
    date_str = date.today().strftime("%Y-%m-%d")
    privacy = "private"
    if len(sys.argv) >= 3:
        if sys.argv[2] in ("public", "private", "unlisted"):
            privacy = sys.argv[2]
        else:
            date_str = sys.argv[2]
            if len(sys.argv) >= 4:
                privacy = sys.argv[3]
    if privacy not in ("public", "private", "unlisted"):
        privacy = "private"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    merged_folder = os.path.join(script_dir, "stories", "merged", username, date_str)
    if not os.path.isdir(merged_folder):
        print(f"لا يوجد مجلد مدمج: {merged_folder}")
        print("شغّل أولاً: python merge_videos.py", username, date_str)
        sys.exit(1)

    videos = sorted(glob.glob(os.path.join(merged_folder, "merged_*.mp4")))
    if not videos:
        print(f"لا توجد فيديوهات merged_*.mp4 في: {merged_folder}")
        sys.exit(1)

    print("تسجيل الدخول إلى يوتيوب (ستفتح المتصفح)...")
    youtube = get_youtube_service(script_dir)

    for path in videos:
        name = os.path.basename(path)
        title = f"{username} - {name}"
        description = "من Snapchat Stories\n\n#Shorts"
        print(f"رفع: {name} ...")
        try:
            vid_id = upload_video(youtube, path, title, description, privacy)
            print(f"  تم: https://www.youtube.com/watch?v={vid_id}")
        except Exception as e:
            print(f"  خطأ: {e}")

    print("\nانتهى.")


if __name__ == "__main__":
    main()
