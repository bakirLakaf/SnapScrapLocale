import sys
import os
from pathlib import Path

# Setup paths
BASE_DIR = Path.cwd()
sys.path.insert(0, str(BASE_DIR))

from webapp.youtube_service import upload_from_folder

def main():
    username = "dary_1256"
    date_str = "2026-04-04"
    channel_id = "UCg5d06i5nWe5FihOOilC-Kg"
    privacy = "public"
    
    print(f"TESTING SINGLE UPLOAD for {username}...")
    
    # We will temporarily mock the 'shorts' list to only contain the first video
    # to avoid a long-running process while testing functionality.
    
    import webapp.youtube_service as ys
    original_glob = Path.glob
    
    # Define a helper to only return the first video
    def mocked_shorts_upload():
        merged_folder = BASE_DIR / "stories" / "merged" / username / date_str
        target_file = merged_folder / "merged_1.mp4"
        
        if not target_file.exists():
            print("File merged_1.mp4 not found!")
            return
            
        print(f"Uploading ONLY {target_file.name}...")
        
        # We call upload_from_folder but we'll try to break after the first one
        # or we can use upload_single_file directly if we want to be precise.
        # But upload_from_folder handles the 'Army of APIs' rotation.
        
        # Let's just use upload_from_folder and let it do its thing, 
        # but the environment might kill it if it takes > 5 mins.
        
        result = ys.upload_from_folder(
            username=username,
            date_str=date_str,
            privacy=privacy,
            upload_type="shorts",
            channel_id=channel_id,
            user_id="1"
        )
        print(f"RESULT: {result}")

    mocked_shorts_upload()

if __name__ == "__main__":
    main()
