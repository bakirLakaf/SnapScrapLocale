import os
import json
import sys
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

BASE_DIR = Path(__file__).resolve().parent
SECRETS_DIR = BASE_DIR / "webapp" / "client_secrets"
TOKENS_DIR = BASE_DIR / "stories" / "tokens"

def test_token(token_path):
    print(f"🔍 Testing {token_path.name}...")
    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        youtube = build("youtube", "v3", credentials=creds)
        resp = youtube.channels().list(part="snippet", mine=True).execute()
        ch_name = resp["items"][0]["snippet"]["title"]
        print(f"  ✅ HEALTHY: Accesses channel '{ch_name}'")
        return True
    except Exception as e:
        err_msg = str(e).split("\n")[0]
        print(f"  ⚠️ DEAD: {err_msg}")
        return False

def main():
    print("=== YouTube Pipeline Health Audit ===")
    print(f"Secrets Path: {SECRETS_DIR}")
    print(f"Tokens Path: {TOKENS_DIR}\n")

    if not TOKENS_DIR.exists():
        print("❌ Tokens directory not found!")
        return

    tokens = list(TOKENS_DIR.glob("token*.json"))
    if not tokens:
        print("❌ No tokens found in stories/tokens")
    else:
        healthy_count = 0
        for t in tokens:
            if test_token(t):
                healthy_count += 1
        
        print(f"\n--- Audit Summary ---")
        print(f"Total Tokens Checked: {len(tokens)}")
        print(f"Healthy Tokens: {healthy_count}")
        print(f"Dead Tokens: {len(tokens) - healthy_count}")

    # Check client secrets
    secrets = list(SECRETS_DIR.glob("client_secret*.json"))
    print(f"\nTotal Client Secrets: {len(secrets)}")
    for s in secrets:
        print(f" - {s.name}")

if __name__ == "__main__":
    main()
