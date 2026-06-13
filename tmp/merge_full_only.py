import os
import sys
import subprocess
from datetime import date
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from merge_videos import get_video_files, find_ffmpeg, merge_chunk
from webapp.youtube_service import upload_single_file

def main():
    username = "dary_1256"
    date_str = date.today().strftime("%Y-%m-%d")
    
    # Paths
    not_merged_dir = BASE_DIR / "stories" / "not merged" / username / date_str
    merged_dir = BASE_DIR / "stories" / "merged" / username / date_str
    merged_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = merged_dir / "merged_all.mp4"
    
    print(f"--- STARTING FULL MERGE ONLY ---")
    print(f"Source: {not_merged_dir}")
    print(f"Output: {output_file}")
    
    # 1. Get files
    videos = get_video_files(str(not_merged_dir))
    if not videos:
        print("No videos found to merge!")
        return
    
    # 2. Merge
    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        print("FFMPEG not found!")
        return
        
    paths = [p for _, p in videos]
    
    print(f"Merging {len(paths)} videos into {output_file}...")
    try:
        merge_chunk(ffmpeg_exe, paths, str(output_file))
        print("Merge successful!")
    except Exception as e:
        print(f"Merge FAILED: {e}")
        return
        
    # 3. Upload
    print("Starting Upload to YouTube...")
    
    title = f"سنابات ضاري الفلاح | {date_str} - كاملة"
    
    try:
        result = upload_single_file(str(output_file), title=title, privacy="public")
        if result.get("success"):
            print(f"UPLOAD SUCCESSFUL! Video URL: {result.get('url')}")
        else:
            print(f"UPLOAD FAILED: {result.get('error')}")
    except Exception as e:
        print(f"Upload FAILED (Exception): {e}")

if __name__ == "__main__":
    main()
