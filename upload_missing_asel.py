import os
import sys
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from webapp.youtube_service import upload_from_folder

def main():
    print("🚀 Triggering upload for Asel's missing full video (31-03)...")
    # Corrected argument: privacy="private"
    res = upload_from_folder("asel.alm", "2026-03-31", privacy="private", upload_type="full", publish_time="2026-03-31T18:00:00Z")
    print(f"📦 Upload Result: {res}")

if __name__ == "__main__":
    main()
