import os
import sys
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def main():
    token_path = BASE_DIR / "stories" / "tokens" / "token_12_UCg5d06i5nWe5FihOOilC-Kg.json"
    if not token_path.exists():
        print("❌ Token not found.")
        return

    creds = Credentials.from_authorized_user_file(str(token_path), ["https://www.googleapis.com/auth/youtube.force-ssl"])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    youtube = build("youtube", "v3", credentials=creds)
    
    # List channel's recent videos
    resp = youtube.search().list(part="snippet", forMine=True, type="video", maxResults=50).execute()
    print(f"--- Recent Videos for Channel: ---")
    for item in resp.get("items", []):
        v_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        print(f"ID: {v_id} | Title: {title}")

if __name__ == "__main__":
    main()
