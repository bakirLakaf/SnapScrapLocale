import os
import subprocess
import sys

def find_ffmpeg():
    print("Checking PATH for 'ffmpeg'...")
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("Found in PATH: 'ffmpeg'")
        return "ffmpeg"
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Not in PATH: {e}")

    print("\nChecking imageio-ffmpeg package...")
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"imageio_ffmpeg.get_ffmpeg_exe() returned: {exe}")
        if exe and os.path.isfile(exe):
            print("Verified file exists.")
            return exe
        else:
            print("File does NOT exist or path is empty.")
    except Exception as e:
        print(f"Error importing imageio-ffmpeg: {e}")
    
    return None

if __name__ == "__main__":
    res = find_ffmpeg()
    print(f"\nFinal result: {res}")
