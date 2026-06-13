#!/usr/bin/env python3
"""
أتمتة يومية: تحميل، دمج، ونشر على يوتيوب.
"""
import os
import sys
import subprocess
from datetime import date, datetime

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    try:
        from webapp.app import app, User, get_accounts, get_schedule
    except ImportError as e:
        print("Failed to import Flask app:", e)
        sys.exit(1)

    print(f"[{datetime.now()}] Starting SnapScrap SaaS Global Automation")

    with app.app_context():
        users = User.query.all()
        if not users:
            print("No users found in database.")
            return

        for user in users:
            schedule = get_schedule(user.id)
            if not schedule or not schedule.get("enabled"):
                continue

            # In a real SaaS, we would check schedule['hour'] against current time.
            # Simplified for cron trigger.
            accounts = get_accounts(user.id)
            active = [a["username"] for a in accounts if a.get("checked")]
            if not active:
                continue

            print(f"\nProcessing User ID {user.id} ({user.username}) - {len(active)} accounts")
            
            env = os.environ.copy()
            env["SNAPSCRAP_USER_ID"] = str(user.id)
            env["SNAPSCRAP_LANG"] = "en"
            
            date_str = date.today().strftime("%Y-%m-%d")

            for username in active:
                print(f" -> Downloading: {username}")
                subprocess.run([sys.executable, str(os.path.join(script_dir, "SnapScrap.py")), username], env=env, cwd=script_dir)
                
                if schedule.get("merge"):
                    print(f" -> Merging: {username}")
                    subprocess.run([sys.executable, str(os.path.join(script_dir, "merge_videos.py")), username, date_str], env=env, cwd=script_dir)
                    subprocess.run([sys.executable, str(os.path.join(script_dir, "merge_videos.py")), username, date_str, "--all"], env=env, cwd=script_dir)
                
                # Assume auto upload if they had schedule enabled (could add a config for this)
                print(f" -> Uploading: {username}")
                try:
                    from webapp.youtube_service import upload_from_folder
                    os.environ["SNAPSCRAP_USER_ID"] = str(user.id)
                    upload_from_folder(username, date_str, "private")
                    
                    folder_path = os.path.join(script_dir, "stories", "not merged", username, date_str)
                except Exception as e:
                    print(f"    Upload err: {e}")

    print(f"\n[{datetime.now()}] Global Automation Complete.")

if __name__ == "__main__":
    main()
