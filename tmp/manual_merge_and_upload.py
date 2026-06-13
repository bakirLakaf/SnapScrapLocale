import os
import sys
import subprocess
import logging
from pathlib import Path

# Fix Windows printing crash
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)

# Setup paths
base_dir = Path(r"W:\AntiGravity\SnapScrap_Local")
sys.path.append(str(base_dir))

from webapp.youtube_service import upload_from_folder
from merge_videos import find_ffmpeg

folder = base_dir / "stories" / "merged" / "dary_1256" / "2026-03-23" / "uploaded_youtube"
out_path = folder / "merged_all.mp4"

# 1. Delete corrupted file if it exists
if out_path.exists():
    out_path.unlink()
    print("Deleted old corrupted merged_all.mp4")

# 2. Gather all merged_X.mp4 files and sort them numerically
merged_files = []
for p in folder.glob("merged_*.mp4"):
    if p.name != "merged_all.mp4":
        # Extract number from name
        try:
            num = int(p.stem.replace("merged_", ""))
            merged_files.append((num, p))
        except ValueError:
            pass

merged_files.sort(key=lambda x: x[0])

if not merged_files:
    print("No merged files found to combine!")
    sys.exit(1)

# 3. Create a concat txt file
list_path = folder / "concat_list.txt"
with open(list_path, "w", encoding="utf-8") as f:
    for _, p in merged_files:
        f.write(f"file '{p.name}'\n")

print(f"Prepared to merge {len(merged_files)} chunks into merged_all.mp4")

"""
# 4. Run FFmpeg to merge them losslessly without re-encoding!
ffmpeg_exe = find_ffmpeg()
if not ffmpeg_exe:
    print("Could not find ffmpeg globally or via imageio-ffmpeg")
    sys.exit(1)

ffmpeg_cmd = [
    ffmpeg_exe, "-y", "-f", "concat", "-safe", "0",
    "-i", str(list_path),
    "-c", "copy",
    str(out_path)
]

try:
    print("Running FFmpeg...")
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
    print("FFmpeg completed successfully!")
except subprocess.CalledProcessError as e:
    print(f"FFmpeg failed: {e.stderr.decode('utf-8', errors='replace')}")
    sys.exit(1)

# 5. Move merged_all.mp4 OUT of uploaded_youtube back to the main date folder so upload_from_folder finds it
final_out_path = base_dir / "stories" / "merged" / "dary_1256" / "2026-03-23" / "merged_all.mp4"
if final_out_path.exists():
    final_out_path.unlink()
import shutil
shutil.move(str(out_path), str(final_out_path))
print(f"Moved merged_all.mp4 to {final_out_path}")
"""

# 6. Call the Youtube Upload Service
print("Starting YouTube Upload Process for 'سنابات ضاري الفلاح'...")
res = upload_from_folder("dary_1256", "2026-03-23", privacy="public", upload_type="long", channel_id="UCg5d06i5nWe5FihOOilC-Kg")
print(f"Upload Result: {res}")
