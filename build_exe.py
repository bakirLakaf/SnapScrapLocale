#!/usr/bin/env python3
"""
تحويل SnapScrap GUI إلى ملف exe باستخدام PyInstaller.
"""
import os
import sys
import subprocess

def build_exe():
    """Build executable using PyInstaller."""
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gui_script = os.path.join(script_dir, "snapscrap_gui.py")
    spec_file = os.path.join(script_dir, "SnapScrap.spec")
    
    if not os.path.exists(gui_script):
        print(f"Error: {gui_script} not found!")
        return False
    
    # Use spec file if exists, otherwise build command
    # Use python -m PyInstaller instead of pyinstaller directly (works when not in PATH)
    # Ensure build directories exist (fixes FileNotFoundError on some Windows setups)
    build_dir = os.path.join(script_dir, "build", "SnapScrap")
    dist_dir = os.path.join(script_dir, "dist")
    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    if os.path.exists(spec_file):
        print("Using SnapScrap.spec file...")
        cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_file]
    else:
        # Required Python files to include
        required_files = [
            "SnapScrap.py",
            "merge_videos.py",
            "daily_automation.py",
            "batch_processor.py",
            "download_tracker.py",
            "upload_youtube_shorts.py",
        ]
        
        # Build PyInstaller command
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",  # Single executable file
            "--windowed",  # No console window (GUI only)
            "--name", "SnapScrap",  # Output name
            "--hidden-import", "tkinter",
            "--hidden-import", "bs4",
            "--hidden-import", "requests",
            "--hidden-import", "googleapiclient",
            "--hidden-import", "google_auth_oauthlib",
            "--hidden-import", "google.auth",
            "--hidden-import", "imageio_ffmpeg",
            "--collect-all", "tkinter",
            "--noconfirm",  # Overwrite without asking
        ]
        
        # Add icon if exists
        icon_path = os.path.join(script_dir, "icon.ico")
        if os.path.exists(icon_path):
            cmd.extend(["--icon", icon_path])
        
        # Add required files
        for file in required_files:
            file_path = os.path.join(script_dir, file)
            if os.path.exists(file_path):
                # Windows format: source;destination
                cmd.extend(["--add-data", f"{file_path};."])
        
        # Add the main GUI script
        cmd.append(gui_script)
    
    print("Building executable...")
    print(f"Command: {' '.join(cmd)}")
    print(f"Working directory: {script_dir}")
    
    try:
        result = subprocess.run(cmd, cwd=script_dir, check=True)
        exe_path = os.path.join(script_dir, "dist", "SnapScrap.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n✓ Build successful!")
            print(f"Executable location: {exe_path}")
            print(f"File size: {size_mb:.1f} MB")
            print(f"\nNote: Make sure all .py files are in the same folder as the exe!")
            return True
        else:
            print(f"\n✗ Build completed but exe not found at {exe_path}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        print("\nTry running manually:")
        print(f"  python -m PyInstaller --onefile --windowed --name SnapScrap snapscrap_gui.py")
        return False
    except FileNotFoundError as e:
        print(f"Error: PyInstaller not found: {e}")
        print("Install it with: pip install pyinstaller")
        print("Or try: python -m pip install pyinstaller")
        return False


if __name__ == "__main__":
    success = build_exe()
    sys.exit(0 if success else 1)
