#!/usr/bin/env python3
"""
دمج كل 6 فيديوهات من مجلد المستخدم في فيديو واحد (مناسب لـ Shorts).
يستخدم ffmpeg من النظام أو من الحزمة imageio-ffmpeg.
"""
import os
import re
import sys
import subprocess
import tempfile
from datetime import date

# Fix Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

USE_EN = os.environ.get("SNAPSCRAP_LANG", "").lower() == "en" or "--en" in sys.argv
if "--en" in sys.argv:
    sys.argv = [a for a in sys.argv if a != "--en"]

def load_config():
    """Load config from file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, "gui_config.json")
    if os.path.exists(config_file):
        try:
            import json
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

config = load_config()
CHUNK_SIZE = config.get("chunk_size", 7)
VIDEO_QUALITY = config.get("video_quality", 23)  # CRF value
MERGED_DIR = "merged" # Only used as a fallback or name
# تنسيق Shorts عمودي
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920


def find_ffmpeg():
    """Find ffmpeg: first in PATH, then from imageio-ffmpeg package."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
        return "ffmpeg"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    return None


def get_video_files(folder):
    """Get sorted list of .mp4 files (by number). Supports 1.mp4, 2.mp4 and old ETag names."""
    if not os.path.isdir(folder):
        return []
    files = []
    for f in os.listdir(folder):
        if f.lower().endswith(".mp4"):
            path = os.path.join(folder, f)
            if os.path.isfile(path):
                # ترتيب رقمي: 1, 2, 3, ...
                num_match = re.match(r"^(\d+)", f)
                num = int(num_match.group(1)) if num_match else 999999
                files.append((num, f, path))
    files.sort(key=lambda x: x[0])
    return [t[1:] for t in files]  # (filename, fullpath)


def fast_concat(ffmpeg_exe, file_paths, output_path):
    """Fast concat for files that already have same encoding (like our chunks)."""
    if not file_paths:
        return
    # Verification: Ensure all source files exist and are not empty
    valid_paths = []
    for p in file_paths:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            valid_paths.append(p)
        else:
            print(f"⚠️ Warning: Skipping missing or empty file: {p}")
    
    if not valid_paths:
        print("❌ Error: No valid files to concat.")
        return

    list_fd, list_path = tempfile.mkstemp(suffix=".txt", text=True)
    try:
        with os.fdopen(list_fd, "w", encoding="utf-8") as f:
            for p in valid_paths:
                p_escaped = os.path.abspath(p).replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{p_escaped}'\n")
        cmd = [
            ffmpeg_exe, "-y",
            "-fflags", "+genpts",
            "-f", "concat", "-safe", "0",
            "-i", list_path, "-c", "copy", output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        try: os.unlink(list_path)
        except: pass

def merge_chunk(ffmpeg_exe, file_paths, output_path):
    """Merge video files into one using the concat demuxer and normalization filters."""
    if not file_paths:
        return
    
    import tempfile
    
    # We use the parent folder of the first file as the CWD to keep paths relative
    cwd = os.path.dirname(os.path.abspath(file_paths[0]))
    # The output path must be absolute because we are changing CWD
    output_path_abs = os.path.abspath(output_path)
    # The ffmpeg exe path should also be absolute
    ffmpeg_abs = os.path.abspath(ffmpeg_exe) if os.path.isfile(ffmpeg_exe) else ffmpeg_exe

    # Create temporary list file for ffmpeg concat demuxer IN THE SAME FOLDER as the snaps
    list_fd, list_path = tempfile.mkstemp(suffix=".txt", text=True, dir=cwd)
    try:
        with os.fdopen(list_fd, "w", encoding="utf-8") as f:
            for p in file_paths:
                # Use only the filename since the list file is in the same folder
                fname = os.path.basename(p)
                # Escape single quotes for the list file
                p_escaped = fname.replace("'", "'\\''")
                f.write(f"file '{p_escaped}'\n")
        
        # Normalization filters (30fps, 1080x1920, yuv420p)
        vf = (
            "fps=30,"
            f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,format=yuv420p"
        )
        af = "aresample=44100:async=1"

        # Use the list filename (basename) since FFmpeg is running in that cwd
        list_filename = os.path.basename(list_path)

        cmd = [
            ffmpeg_abs,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_filename,
            "-vf", vf,
            "-af", af,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(VIDEO_QUALITY),
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path_abs,
        ]
        
        # Run subprocess with cwd set to the snaps folder
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed: {e.stderr}", flush=True)
        raise e
    finally:
        try:
            if os.path.exists(list_path):
                os.unlink(list_path)
        except Exception:
            pass


def merge_videos_for_user(username, date_str=None, merge_all=False, long_only=False):
    """
    Programmatic entry point for merging videos.
    Returns: (success, message, merged_path)
    """
    if not date_str:
        from datetime import date
        date_str = date.today().strftime("%Y-%m-%d")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(script_dir, "stories", "not merged", username, date_str)
    merged_path = os.path.join(script_dir, "stories", "merged", username, date_str)
    
    raw_exists = os.path.isdir(folder)
    ffmpeg_exe = find_ffmpeg()
    
    if not ffmpeg_exe:
        return False, "ffmpeg not found", None

    videos = get_video_files(folder) if raw_exists else []
    os.makedirs(merged_path, exist_ok=True)
    
    # Check for existing chunks
    existing_chunks = sorted([f for f in os.listdir(merged_path) if f.startswith("merged_") and f.endswith(".mp4") and f != "merged_all.mp4"], 
                            key=lambda x: int(re.search(r"(\d+)", x).group(1)) if re.search(r"(\d+)", x) else 0)
    
    if not raw_exists and not merge_all:
        return False, f"Folder not found: {folder}", None
    elif not videos and not existing_chunks and not merge_all:
        return False, f"No videos to merge in {folder}", None

    # 1. Generate chunks for YouTube Shorts (Skip if raw missing or long_only requested)
    if raw_exists and not long_only:
        chunks = []
        for i in range(0, len(videos), CHUNK_SIZE):
            chunk = videos[i : i + CHUNK_SIZE]
            if chunk:
                chunks.append(chunk)

        print(f"PIPELINE: Merging {len(videos)} videos into {len(chunks)} shorts for {username}")
        for idx, chunk in enumerate(chunks, start=1):
            # Output progress for app.py to capture
            print(f"[PROGRESS] {idx}/{len(chunks)} shorts", flush=True)
            
            paths = [p for _, p in chunk]
            out_name = f"merged_{idx}.mp4"
            out_path = os.path.join(merged_path, out_name)

            # Check if output is newer than all inputs
            needs_merge = True
            if os.path.exists(out_path):
                out_mtime = os.path.getmtime(out_path)
                inputs_mtime = max((os.path.getmtime(p) for p in paths if os.path.exists(p)), default=0)
                if out_mtime > inputs_mtime:
                    needs_merge = False

            if not needs_merge:
                continue

            try:
                merge_chunk(ffmpeg_exe, paths, out_path)
            except Exception as e:
                print(f"Error merging chunk {idx} for {username}: {e}", flush=True)
                return False, str(e), None
    elif raw_exists and long_only:
        print(f"PIPELINE: Direct long-video merge for {username} ({len(videos)} videos)...")

    # 2. Generate full long video
    out_all_path = os.path.join(merged_path, "merged_all.mp4")
    
    if raw_exists and long_only:
        # Direct merge from raw snaps to merged_all.mp4
        all_paths = [p for _, p in videos]
        print(f"[PROGRESS] Creating direct long video...", flush=True)
        try:
            merge_chunk(ffmpeg_exe, all_paths, out_all_path)
            return True, "Direct merge success", merged_path
        except Exception as e:
            return False, f"Direct merge failed: {e}", None

    if raw_exists:
        chunk_paths = [os.path.join(merged_path, f"merged_{i+1}.mp4") for i in range(len(chunks))]
    else:
        chunk_paths = [os.path.join(merged_path, f) for f in existing_chunks]
    
    chunk_paths = [p for p in chunk_paths if os.path.exists(p)]
    
    if merge_all or (not raw_exists and existing_chunks):
        out_all_path = os.path.join(merged_path, "merged_all.mp4")
        needs_merge = True
        if os.path.exists(out_all_path):
            out_mtime = os.path.getmtime(out_all_path)
            inputs_mtime = max((os.path.getmtime(p) for p in chunk_paths if os.path.exists(p)), default=0)
            if out_mtime > inputs_mtime:
                needs_merge = False

        if needs_merge and chunk_paths:
            try:
                if len(chunk_paths) == 1:
                    import shutil
                    shutil.copy2(chunk_paths[0], out_all_path)
                else:
                    fast_concat(ffmpeg_exe, chunk_paths, out_all_path)
            except Exception as e:
                print(f"Error merging all for {username}: {e}")

    return True, "Success", merged_path


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python merge_videos.py <username> [YYYY-MM-DD] [--all] [--long-only]")
        sys.exit(0)
    
    merge_all = "--all" in sys.argv
    long_only = "--long-only" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--all", "--long-only", "--help", "-h", "--en")]
    
    if len(args) < 1:
        print("Usage: python merge_videos.py <username> [YYYY-MM-DD] [--all] [--long-only]")
        sys.exit(1)

    username = args[0]
    date_str = args[1] if len(args) > 1 else None
    
    success, msg, path = merge_videos_for_user(username, date_str, merge_all=merge_all, long_only=long_only)
    if success:
        print(f"PIPELINE_SUCCESS: {msg}")
        if path: print(f"Merged files in: {path}")
    else:
        print(f"PIPELINE_ERROR: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
