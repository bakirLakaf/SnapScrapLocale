#!/usr/bin/env python3
"""SnapScrap Web App - واجهة ويب حديثة."""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
import functools
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, redirect, render_template, request, session, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from webapp.models import db, User, ConnectedChannel
from webapp.billing import billing_bp

BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2048 * 1024 * 1024  # 2GB
app.config["UPLOAD_FOLDER"] = BASE_DIR / "uploads"
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'super-secret-default-key-123')
# Prevent XSS & Session Hijacking
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Trust reverse proxies for HTTPS scheme
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configure database
db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'snapscrap.db'}")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"].mkdir(exist_ok=True)

app.register_blueprint(billing_bp)

from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app.config["WTF_CSRF_SECRET_KEY"] = os.environ.get("FLASK_CSRF_SECRET_KEY", "csrf-token-secret-xyz-444")
csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri="memory://"
)

from flask_wtf.csrf import CSRFError
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return jsonify({"ok": False, "error": "انتهت الجلسة (CSRF). يرجى تحديث الصفحة والمحاولة مجدداً."}), 400

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def load_translations():
    t_file = BASE_DIR / "webapp" / "translations.json"
    if t_file.exists():
        with open(t_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

translations = load_translations()

def get_current_language():
    return session.get('lang', 'ar')

def _(key):
    lang = get_current_language()
    return translations.get(lang, {}).get(key, key)

@app.context_processor
def inject_translations():
    from flask_wtf.csrf import generate_csrf
    return dict(_=_, current_lang=get_current_language(), csrf_token=generate_csrf())

@app.route("/set_lang/<lang>")
def set_lang(lang):
    if lang in ["ar", "en", "fr"]:
        session['lang'] = lang
    return redirect(request.referrer or url_for('landing'))

# Auto-Migration for V2 SQLite (Add new columns without dropping data)
with app.app_context():
    db.create_all()
    try:
        from sqlalchemy import text
        # Attempt to query the newly added V2 columns
        db.session.execute(text("SELECT is_admin FROM user LIMIT 1"))
    except Exception:
        db.session.rollback()
        print("Migrating local database: Checking missing columns in User table...")
        columns_to_add = [
            ("subscription_tier", "VARCHAR(50) DEFAULT 'free'"),
            ("stripe_customer_id", "VARCHAR(255)"),
            ("created_at", "DATETIME"),
            ("is_admin", "BOOLEAN DEFAULT 0")
        ]
        for col_name, col_def in columns_to_add:
            try:
                db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}"))
                db.session.commit()
                print(f"Added column {col_name}.")
            except Exception:
                db.session.rollback()
                pass

@app.before_request
def require_login():
    if not current_user.is_authenticated:
        try:
            user = User.query.filter_by(username='local_admin').first()
            if not user:
                user = User(username='local_admin', password_hash='', subscription_tier='enterprise', is_admin=True)
                db.session.add(user)
                db.session.commit()
            login_user(user)
        except Exception:
            pass


ACCOUNTS_KEY = "accounts"
SCHEDULE_KEY = "schedule"
tasks = {}

import queue
import threading

# Task Queue System
pipeline_queue = queue.Queue()

# Task History Log System
HISTORY_FILE = BASE_DIR / "task_history.json"

def save_task_history(task_id, task_data):
    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
    history.append({
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "status": task_data.get("status", "unknown"),
        "message": task_data.get("message", "")
    })
    history = history[-100:] # Keep last 100 tasks
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Failed to save task history:", e)

def pipeline_worker():
    while True:
        task = pipeline_queue.get()
        if task is None: break
        target_func, task_id, args, kwargs = task
        if task_id in tasks:
            # If the user cancelled it while it was in queue, skip it
            if tasks[task_id].get("cancel_requested"):
                tasks[task_id]["status"] = "error"
                tasks[task_id]["message"] = "تم تشخيص إلغاء المستخدم للعملية قبل بدءها."
                save_task_history(task_id, tasks[task_id])
                pipeline_queue.task_done()
                continue
            
            tasks[task_id]["status"] = "running"
            tasks[task_id]["message"] = "تم سحب العملية من الطابور.. جاري التحضير للمسار..."
        try:
            target_func(*args, **kwargs)
        except Exception as e:
            if task_id in tasks:
                tasks[task_id]["status"] = "error"
                tasks[task_id]["message"] = f"Crash in pipeline worker: {e}"
        finally:
            if task_id in tasks:
                save_task_history(task_id, tasks[task_id])
        pipeline_queue.task_done()

threading.Thread(target=pipeline_worker, daemon=True).start()



def get_user_config_file(user_id=None):
    if user_id is None:
        if current_user and current_user.is_authenticated:
            user_id = current_user.id
        else:
            return None
    user_dir = BASE_DIR / "stories" / "config"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / f"webapp_config_{user_id}.json"


def load_config(user_id=None):
    """Load webapp config."""
    config_file = get_user_config_file(user_id)
    if config_file and config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(config, user_id=None):
    """Save webapp config."""
    config_file = get_user_config_file(user_id)
    if not config_file:
        return
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())


def get_accounts(user_id=None):
    """Get accounts list: [{username, checked, avatar}, ...]. Auto-reads from stories folder."""
    cfg = load_config(user_id)
    accounts = cfg.get(ACCOUNTS_KEY, [])
    
    # Auto-add existing folders
    existing_usernames = {a["username"] for a in accounts}
    new_accounts_added = False
    
    for folder_type in ["merged", "not merged"]:
        path = BASE_DIR / "stories" / folder_type
        if path.exists():
            for folder in os.listdir(path):
                f_path = path / folder
                if f_path.is_dir() and not folder.startswith(".") and folder not in ("config", "tokens"):
                    if folder not in existing_usernames:
                        accounts.append({"username": folder, "checked": True, "avatar": None})
                        existing_usernames.add(folder)
                        new_accounts_added = True
                        
    if new_accounts_added:
        save_accounts(accounts, user_id)
        
    return accounts


def save_accounts(accounts, user_id=None):
    """Save accounts."""
    cfg = load_config(user_id)
    cfg[ACCOUNTS_KEY] = accounts
    save_config(cfg, user_id)


def get_schedule(user_id=None):
    """Get schedule: {enabled, hour, minute, merge}."""
    cfg = load_config(user_id)
    return cfg.get(SCHEDULE_KEY, {"enabled": False, "hour": 9, "minute": 0, "merge": False})


def save_schedule(schedule, user_id=None):
    """Save schedule."""
    cfg = load_config(user_id)
    cfg[SCHEDULE_KEY] = schedule
    save_config(cfg, user_id)


def get_merged_folders():
    """List username/date folders that have merged videos."""
    result = []
    stories_dir = BASE_DIR / "stories" / "merged"
    try:
        items = os.listdir(stories_dir)
    except OSError:
        return []
    for username in items:
        user_path = stories_dir / username
        if not user_path.is_dir() or username.startswith(".") or username in ("webapp", "build", "dist", "uploads"):
            continue
        try:
            subdirs = os.listdir(user_path)
        except OSError:
            continue
        for d in subdirs:
            merged_path = user_path / d
            if merged_path.is_dir() and list(merged_path.glob("merged_*.mp4")):
                result.append({"username": username, "date": d})
    return sorted(result, key=lambda x: (x["username"], x["date"]), reverse=True)


def run_task(task_id, task_type, **kwargs):
    """Run task in background."""
    user_id = current_user.id if current_user and current_user.is_authenticated else ""
    
    def _run():
        try:
            if task_type == "download":
                _run_download(task_id, kwargs.get("username"), kwargs.get("merge", False), user_id, today_only=kwargs.get("today_only", False), custom_links=kwargs.get("custom_links", ""))
            elif task_type == "download_batch":
                _run_download_batch(task_id, kwargs.get("usernames", []), kwargs.get("merge", False), user_id, today_only=kwargs.get("today_only", False), custom_links=kwargs.get("custom_links", ""))
            elif task_type == "merge":
                _run_merge(task_id, kwargs.get("username"), kwargs.get("date_str"), kwargs.get("merge_mode", "shorts"), user_id)
            elif task_type == "upload":
                _run_upload(
                    task_id, 
                    kwargs.get("username"), 
                    kwargs.get("date_str"), 
                    kwargs.get("privacy", "private"), 
                    kwargs.get("upload_type", "shorts"), 
                    kwargs.get("channel_id"), 
                    user_id,
                    custom_long_title=kwargs.get("custom_long_title"),
                    custom_thumb_path=kwargs.get("custom_thumb_path")
                )
            elif task_type == "upload_file":
                _run_upload_file(
                    task_id, 
                    kwargs.get("file_path"), 
                    kwargs.get("title"), 
                    kwargs.get("privacy", "private"), 
                    kwargs.get("channel_id"), 
                    user_id,
                    thumbnail_path=kwargs.get("thumbnail_path")
                )
        except Exception as e:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = str(e)

    threading.Thread(target=_run, daemon=True).start()


def _run_download(task_id, username, do_merge, user_id="", today_only=False, custom_links=""):
    tasks[task_id]["status"] = "running"
    tasks[task_id]["message"] = f"Downloading {username}..."
    cmd = [sys.executable, str(BASE_DIR / "SnapScrap.py"), username]
    if do_merge:
        cmd.append("--merge")
    if today_only:
        cmd.append("--today-only")
    if custom_links:
        cmd.extend(["--custom-links", custom_links])
    env = os.environ.copy()
    env["SNAPSCRAP_LANG"] = "en"
    if user_id:
        env["SNAPSCRAP_USER_ID"] = str(user_id)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(cmd, cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
    for line in iter(proc.stdout.readline, ""):
        if not line: break
        line = line.strip()
        if line.startswith("[PROGRESS]"):
            progress_str = line.split("]")[1].strip()
            tasks[task_id]["message"] = f"Downloading {username}: {progress_str} snaps..."
    proc.wait()
    if proc.returncode != 0:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = "Download failed"
        return
    tasks[task_id]["status"] = "done"
    tasks[task_id]["message"] = f"Downloaded {username}!"


def _run_download_batch(task_id, usernames, do_merge, user_id="", today_only=False, custom_links=""):
    total = len(usernames)
    done = 0
    failed = []
    for username in usernames:
        tasks[task_id]["status"] = "running"
        tasks[task_id]["message"] = f"Downloading {username} ({done + 1}/{total})...."
        cmd = [sys.executable, str(BASE_DIR / "SnapScrap.py"), username]
        if do_merge:
            cmd.append("--merge")
        if today_only:
            cmd.append("--today-only")
        if custom_links:
            cmd.extend(["--custom-links", custom_links])
        env = os.environ.copy()
        env["SNAPSCRAP_LANG"] = "en"
        if user_id:
            env["SNAPSCRAP_USER_ID"] = str(user_id)
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(cmd, cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
        for line in iter(proc.stdout.readline, ""):
            if not line: break
            line = line.strip()
            if line.startswith("[PROGRESS]"):
                progress_str = line.split("]")[1].strip()
                tasks[task_id]["message"] = f"Downloading {username} ({done + 1}/{total}): {progress_str} snaps..."
        proc.wait()
        if proc.returncode != 0:
            failed.append(username)
        else:
            done += 1
    tasks[task_id]["status"] = "done" if not failed else ("error" if done == 0 else "done")
    tasks[task_id]["message"] = f"Downloaded {done}/{total}" + (f" — failed: {', '.join(failed)}" if failed else "")


def _run_merge(task_id, username, date_str, merge_mode="both", user_id=""):
    """merge_mode: 'both' is now forced as merge_videos.py handles both natively."""
    tasks[task_id]["status"] = "running"
    env = os.environ.copy()
    env["SNAPSCRAP_LANG"] = "en"
    if user_id:
        env["SNAPSCRAP_USER_ID"] = str(user_id)
        
    tasks[task_id]["message"] = "Merging videos (Shorts and Full)..."
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [sys.executable, str(BASE_DIR / "merge_videos.py"), username, date_str]
    proc = subprocess.Popen(cmd, cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, encoding="utf-8", errors="replace")
    for line in iter(proc.stdout.readline, ""):
        if not line: break
        line = line.strip()
        if line.startswith("[PROGRESS]"):
            progress_str = line.split("]")[1].strip()
            tasks[task_id]["message"] = f"Merging videos: {progress_str} ..."
    proc.wait()
    if proc.returncode != 0:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = "Merge failed"
        return
    
    tasks[task_id]["status"] = "done"
    tasks[task_id]["message"] = "Merge complete!"


def _run_upload(task_id, username, date_str, privacy, upload_type="both", channel_id=None, user_id="", **kwargs):
    tasks[task_id]["status"] = "running"
    tasks[task_id]["message"] = "Connecting to YouTube..."
    try:
        from webapp.youtube_service import upload_from_folder
        if user_id:
            os.environ["SNAPSCRAP_USER_ID"] = str(user_id)
        
        def update_progress(msg):
            tasks[task_id]["message"] = msg
            
        custom_long_title = kwargs.get("custom_long_title")
        custom_thumb_path = kwargs.get("custom_thumb_path")

        # Hardcode upload_type="both" to satisfy user requirements
        result = upload_from_folder(
            username, 
            date_str, 
            privacy, 
            upload_type="both", 
            channel_id=channel_id, 
            progress_callback=update_progress,
            custom_long_title=custom_long_title,
            custom_thumb_path=custom_thumb_path
        )
        if result.get("success"):
            tasks[task_id]["status"] = "done"
            tasks[task_id]["message"] = f"Uploaded {result.get('count', 0)} videos!"
        else:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = result.get("error", "Upload failed")
    except ImportError:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = "Install: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = str(e)


def _run_upload_file(task_id, file_path, title, privacy, channel_id=None, user_id="", **kwargs):
    tasks[task_id]["status"] = "running"
    tasks[task_id]["message"] = "Uploading to YouTube..."
    try:
        from webapp.youtube_service import upload_single_file
        if user_id:
            os.environ["SNAPSCRAP_USER_ID"] = str(user_id)
            
        def update_progress(msg):
            tasks[task_id]["message"] = msg
            
        thumbnail_path = kwargs.get("thumbnail_path")
        result = upload_single_file(file_path, title or "Snapchat Short", privacy, channel_id=channel_id, progress_callback=update_progress, thumbnail_path=thumbnail_path)
        if result.get("success"):
            tasks[task_id]["status"] = "done"
            tasks[task_id]["message"] = f"Uploaded! {result.get('url', '')}"
        else:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = result.get("error", "Upload failed")
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = str(e)
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

def _run_pipeline(task_id, username, date_str, privacy, upload_type="both", channel_id=None, user_id="", **kwargs):
    import shutil
    from datetime import datetime
    publish_at = kwargs.get("publish_at")
    skip_first = kwargs.get("skip_first", 0)
    
    # Convert local datetime-local string (YYYY-MM-DDTHH:mm) to UTC ISO (YYYY-MM-DDTHH:mm:ssZ)
    if publish_at:
        try:
            import datetime as dt_mod
            # datetime-local is usually YYYY-MM-DDTHH:mm
            dt = datetime.strptime(publish_at, "%Y-%m-%dT%H:%M")
            # Convert naive local time to UTC ISO for YouTube
            utc_dt = dt.astimezone(dt_mod.timezone.utc)
            publish_at = utc_dt.strftime("%Y-%m-%dT%H:%M:00Z")
            privacy = "private" # Must be private for scheduling
        except Exception as e:
            print(f"Error parsing publish_at: {e}")
            publish_at = None

    tasks[task_id]["status"] = "running"
    
    if tasks[task_id].get("cancel_requested"):
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = "تم إلغاء العملية بناء على طلب المستخدم."
        return

    # Check if merged files already exist to skip download/merge
    merged_folder = BASE_DIR / "stories" / "merged" / username / date_str

    def _has_uploadable_merged():
        """Check if merged folder has mp4 files NOT yet uploaded."""
        if not merged_folder.exists():
            return False
        meta = merged_folder / "uploaded_youtube" / "upload_meta.json"
        uploaded_paths = set()
        if meta.exists():
            try:
                import json as _json
                with open(meta, "r", encoding="utf-8") as f:
                    uploaded_paths = {h.get("path") for h in _json.load(f)}
            except: pass
        for f in merged_folder.iterdir():
            if f.is_file() and f.suffix == '.mp4' and f.name not in uploaded_paths:
                return True
        return False

    # Check if we have merged files.
    # If it's a long video request, we specifically need merged_all.mp4
    has_merged_files = merged_folder.exists() and not kwargs.get("force") and any(
        f.is_file() and f.suffix == '.mp4' for f in merged_folder.iterdir()
    )
    
    skip_to_upload = has_merged_files
    if upload_type == "long" and not (merged_folder / "merged_all.mp4").exists():
        skip_to_upload = False # Force download/merge track to get the full video

    if not skip_to_upload:
        # 1. Download
        tasks[task_id]["message"] = f"Pipeline: Downloading {username}..."
        env = os.environ.copy()
        if user_id:
            env["SNAPSCRAP_USER_ID"] = str(user_id)
        if kwargs.get("force"):
            env["SNAPSCRAP_FORCE_RELOAD"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        import sys
        cmd1 = [sys.executable, str(BASE_DIR / "SnapScrap.py"), username]
        if skip_first > 0:
            cmd1.extend(["--skip-first", str(skip_first)])
        if kwargs.get("today_only"):
            cmd1.append("--today-only")
        if kwargs.get("custom_links"):
            cmd1.extend(["--custom-links", kwargs.get("custom_links")])
        proc1 = subprocess.Popen(cmd1, cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, encoding="utf-8", errors="replace")
        last_output = ""
        for line in iter(proc1.stdout.readline, ""):
            if not line: break
            line = line.strip()
            last_output = line
            if line.startswith("[PROGRESS]"):
                progress_str = line.split("]")[1].strip()
                tasks[task_id]["message"] = f"Pipeline: Downloading {username} ({progress_str})..."
        proc1.wait()
        if proc1.returncode != 0:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = f"Download failed (code {proc1.returncode}): {last_output}"
            return

        # Verify if anything was downloaded
        path = BASE_DIR / "stories" / "not merged" / username / date_str
        new_downloads = path.exists() and any(f.is_file() for f in path.iterdir())

        if not new_downloads:
            # No new downloads — check for existing unuploaded merged files
            if _has_uploadable_merged():
                tasks[task_id]["message"] = f"Pipeline: لا سنابات جديدة، لكن يوجد فيديوهات جاهزة للرفع لـ {username}..."
                skip_to_upload = True
            elif merged_folder.exists() and any(f.is_file() and f.suffix == '.mp4' for f in merged_folder.iterdir()):
                # Check if we need the long video and it's missing
                if upload_type == "long" and not (merged_folder / "merged_all.mp4").exists():
                    tasks[task_id]["message"] = f"Pipeline: فيديو طويل مفقود لـ {username}، جاري الدمج..."
                    skip_to_upload = False # Force merge
                else:
                    # All merged files already uploaded
                    tasks[task_id]["status"] = "done"
                    tasks[task_id]["message"] = f"✅ كل فيديوهات {username} مرفوعة بالفعل على يوتيوب. لا يوجد جديد."
                    return
            else:
                tasks[task_id]["status"] = "done"
                tasks[task_id]["message"] = f"اكتمل المسار: لا توجد سنابات جديدة اليوم لحساب ({username})."
                return

        if not skip_to_upload:
            # 2. Merge
            tasks[task_id]["message"] = f"Pipeline: Merging {username} videos..."
            cmd2 = [sys.executable, str(BASE_DIR / "merge_videos.py"), username, date_str, "--all"]
            if upload_type == "long":
                cmd2.append("--long-only")
            proc2 = subprocess.Popen(cmd2, cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, encoding="utf-8", errors="replace")
            last_output = ""
            for line in iter(proc2.stdout.readline, ""):
                if not line: break
                line = line.strip()
                last_output = line
                if line.startswith("[PROGRESS]"):
                    progress_str = line.split("]")[1].strip()
                    tasks[task_id]["message"] = f"Pipeline: Merging {username} ({progress_str})..."
            proc2.wait()
            if proc2.returncode != 0:
                tasks[task_id]["status"] = "error"
                tasks[task_id]["message"] = f"Merge failed (code {proc2.returncode}): {last_output}"
                return

            # Verify if anything was merged
            if not merged_folder.exists() or not any(f.is_file() and f.suffix == '.mp4' for f in merged_folder.iterdir()):
                tasks[task_id]["status"] = "error"
                tasks[task_id]["message"] = "Merge finished but no output files were created. Check logs."
                return
    else:
        tasks[task_id]["message"] = f"Pipeline: Found existing merged files for {username}. Skipping to upload..."
        import time
        time.sleep(1)

    # 3. Upload
    tasks[task_id]["message"] = f"Pipeline: Uploading {username} to YouTube..."
    try:
        from webapp.youtube_service import upload_from_folder
        if user_id:
            os.environ["SNAPSCRAP_USER_ID"] = str(user_id)
            
        def update_progress(msg):
            tasks[task_id]["message"] = f"Pipeline (Uploading): {msg}"
            
        # Use the upload_type parameter from function arguments
        result = upload_from_folder(
            username, 
            date_str, 
            privacy, 
            upload_type=upload_type, 
            channel_id=channel_id, 
            progress_callback=update_progress,
            user_id=user_id,
            publish_at=publish_at,
            custom_long_title=kwargs.get("custom_long_title"),
            custom_thumb_path=kwargs.get("custom_thumb_path")
        )
        if not result.get("success"):
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = result.get("error", "Upload failed")
            return
            
        shorts = result.get("shorts", 0)
        fulls = result.get("fulls", 0)
        final_msg = (
            f"🏆 تم إنجاز العملية الشاملة لحساب [{username}] بنجاح!\n"
            f"📊 التفاصيل: ({fulls}) فيديو طويل و ({shorts}) شورتس. "
            f"إجمالي: {shorts + fulls} فيديو."
        )
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = str(e)
        return

    # 4. Delete/Cleanup
    tasks[task_id]["message"] = f"Pipeline: Cleaning up {username} folders..."
    try:
        # Delete unmerged folder for today
        raw_folder = BASE_DIR / "stories" / "not merged" / username / date_str
        if raw_folder.exists() and raw_folder.is_dir():
            shutil.rmtree(raw_folder)
        # The merged files are in stories/merged/username/date/
        merged_folder = BASE_DIR / "stories" / "merged" / username / date_str
        if merged_folder.exists() and merged_folder.is_dir():
            # Only delete if user has 'Cleanup' enabled in GUI (automated)
            # Or just leave it for now if we want to be safe
            pass
        
        # NOTE: Using the structured merged folder from snapscrap_gui logic if applicable
        # We rely on upload_from_folder having finished. It looks for stories/username/merged/username_date
        # Removed redundant cleanup logic
        pass
            
    except Exception as e:
        print(f"Cleanup error in pipeline: {e}")
    
    tasks[task_id]["status"] = "done"
    if result.get('count', 0) == 0 and not (result.get('shorts', 0) or result.get('fulls', 0)):
        tasks[task_id]["message"] = f"✅ كل فيديوهات {username} مرفوعة بالفعل على يوتيوب."
    else:
        tasks[task_id]["message"] = final_msg


def scheduler_loop():
    """Background scheduler - run at scheduled time daily."""
    last_date = None
    while True:
        time.sleep(30)
        sched = get_schedule()
        if not sched.get("enabled"):
            continue
        now = datetime.now()
        h, m = sched.get("hour", 9), sched.get("minute", 0)
        if now.hour == h and now.minute == m and last_date != now.date():
            accounts = [a["username"] for a in get_accounts() if a.get("checked")]
            if accounts:
                last_date = now.date()
                task_id = f"batch_{now.strftime('%Y%m%d_%H%M')}"
                tasks[task_id] = {"status": "running", "message": "Scheduled run..."}
                run_task(task_id, "download_batch", usernames=accounts, merge=sched.get("merge", False))


def start_scheduler():
    threading.Thread(target=scheduler_loop, daemon=True).start()


start_scheduler()

def fetch_snapchat_info(username):
    """Fetch public profile info (Bitmoji, Bio) from Snapchat."""
    url = f"https://story.snapchat.com/@{username}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if not r.ok:
            return {}
        soup = BeautifulSoup(r.content, "html.parser")
        next_data = soup.find(id="__NEXT_DATA__")
        if not next_data:
            return {}
        data = json.loads(next_data.string)
        props = data.get("props", {}).get("pageProps", {})
        user_profile = props.get("userProfile", {})
        public_info = user_profile.get("publicProfileInfo", {})
        user_info = user_profile.get("userInfo", {})
        
        # Try finding snapcode/bitmoji in publicProfileInfo first, then userInfo
        avatar = public_info.get("snapcodeImageUrl") or user_info.get("snapcodeImageUrl") or user_info.get("bitmoji3dAvatarId") 
        # Note: bitmoji3dAvatarId needs constructing url, snapcodeImageUrl is direct. 
        # Typically snapcodeImageUrl is what we want or 'squareImageURL'
        
        if not avatar:
             # Fallback to older keys if structure changed
             avatar = public_info.get("squareHeroImageUrl")
        
        return {"avatar": avatar}
    except Exception:
        return {}

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if not username or not password:
            flash("اسم المستخدم وكلمة المرور مطلوبان", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("اسم المستخدم محجوز، اختر اسماً آخر", "danger")
            return redirect(url_for("register"))
        
        try:
            user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("dashboard"))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("register"))
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("بيانات الدخول غير صحيحة", "danger")
    return render_template("auth.html", mode="login")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/api/pipeline", methods=["POST"])
@login_required
def api_pipeline():
    data = request.json or {}
    username = data.get("username")
    date_str = data.get("date")
    privacy = data.get("privacy", "public")
    upload_type = data.get("upload_type", "shorts")
    channel_id = data.get("channel_id")
    force = data.get("force", False)
    
    publish_at = data.get("publish_at")
    skip_first = data.get("skip_first", 0)
    custom_long_title = data.get("custom_long_title")
    custom_thumb_path = data.get("custom_thumb_path")
    today_only = data.get("today_only", False)
    custom_links = data.get("custom_links", "")
    
    import threading
    task_id = "pl_" + str(int(time.time()))
    tasks[task_id] = {"status": "queued", "message": "العملية في طابور الانتظار...", "cancel_requested": False, "skip_requested": False}
    
    # Put in queue instead of creating isolated thread
    args = (task_id, username, date_str, privacy, upload_type, channel_id, current_user.id)
    kwargs = {
        "force": force, 
        "publish_at": publish_at, 
        "skip_first": skip_first, 
        "custom_long_title": custom_long_title,
        "custom_thumb_path": custom_thumb_path,
        "today_only": today_only,
        "custom_links": custom_links
    }
    pipeline_queue.put((_run_pipeline, task_id, args, kwargs))
    
    return jsonify({"ok": True, "task_id": task_id})

@app.route("/api/cancel_task/<task_id>", methods=["POST"])
@login_required
def api_cancel_task(task_id):
    if task_id in tasks:
        tasks[task_id]["cancel_requested"] = True
        return jsonify({"ok": True, "message": "تم طلب الإلغاء"})
    return jsonify({"ok": False, "error": "المهمة غير موجودة"})

@app.route("/api/skip_task/<task_id>", methods=["POST"])
@login_required
def api_skip_task(task_id):
    if task_id in tasks:
        tasks[task_id]["skip_requested"] = True
        return jsonify({"ok": True, "message": "تم طلب التخطي"})
    return jsonify({"ok": False, "error": "المهمة غير موجودة"})

@app.route("/api/run-setup-bot", methods=["POST"])
@login_required
def api_run_setup_bot():
    try:
        import subprocess
        setup_script = BASE_DIR.parent / "SnapScrap_Local/setup_bot.py"
        subprocess.Popen([sys.executable, str(setup_script)], cwd=str(BASE_DIR.parent))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/")
def landing():
    if current_user.is_authenticated:
        err = request.args.get("youtube_error")
        conn = request.args.get("youtube_connected")
        if err:
            return redirect(url_for("dashboard", youtube_error=err))
        if conn:
            return redirect(url_for("dashboard", youtube_connected=conn))
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash("غير مصرح لك بالدخول إلى لوحة التحكم", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin")
@admin_required
def admin_dashboard():
    from webapp.models import User, ConnectedChannel
    users = User.query.all()
    channel_count = ConnectedChannel.query.count()
    return render_template("admin.html", users=users, total_channels=channel_count)

@app.route("/admin/change_tier/<int:user_id>", methods=["POST"])
@admin_required
def admin_change_tier(user_id):
    from webapp.models import User
    user = User.query.get_or_404(user_id)
    new_tier = request.form.get("tier")
    if new_tier in ["free", "pro", "enterprise"]:
        user.subscription_tier = new_tier
        db.session.commit()
        flash(f"تم تغيير باقة حساب {user.username} إلى {new_tier}.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    from webapp.models import User, ConnectedChannel
    user = User.query.get_or_404(user_id)
    if not getattr(user, 'is_admin', False):
        ConnectedChannel.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash(f"تم حذف حساب {user.username} بنجاح.", "success")
    else:
        flash("خطأ: لا يمكنك حذف حساب مدير آخر أو حسابك الشخصي.", "danger")
    return redirect(url_for('admin_dashboard'))

@app.route("/dashboard")
@login_required
def dashboard():
    try:
        from webapp.youtube_service import get_youtube_channels_config, _get_all_tokens_for_channel, _get_client_secrets, _get_token_for_secret
        
        raw_channels = get_youtube_channels_config(current_user.id)
        enriched_channels = []
        for c in raw_channels:
            ch_id = c.get("id", "")
            if ch_id.startswith("unknown"):
                continue # Hide placeholders from dropdown
            tokens = _get_all_tokens_for_channel(ch_id, current_user.id)
            c["token_count"] = len(tokens)
            enriched_channels.append(c)

        # Build Unified Army Status
        all_secrets = _get_client_secrets()
        army_soldiers = []
        for s in all_secrets:
            # Check for a generic token (marks it as authorized)
            token = _get_token_for_secret(None, current_user.id, s)
            army_soldiers.append({
                "secret_name": s.name,
                "is_active": token.exists(),
                "token_path": str(token) if token.exists() else None
            })

        config = load_config(current_user.id)
        teams_config = config.get("teams_config", {})

        return render_template(
            "index.html",
            merged_folders=get_merged_folders(),
            accounts=get_accounts(current_user.id),
            schedule=get_schedule(),
            youtube_channels=enriched_channels,
            army_soldiers=army_soldiers,
            total_client_secrets=len(all_secrets),
            is_admin=getattr(current_user, 'is_admin', False)
        )
    except Exception as e:
        import traceback
        return "<pre>" + traceback.format_exc() + "</pre>", 500


@app.route("/api/download_single_story", methods=["POST"])
@limiter.limit("10 per minute")
def api_download_single_story():
    url = request.json.get("url", "").strip()
    if not url:
        return jsonify({"error": "رابط القصة مطلوب"})
    
    try:
        import requests, json, re
        from bs4 import BeautifulSoup
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        if "t.snapchat.com" in url:
            r = requests.get(url, allow_redirects=True, timeout=10)
            url = r.url
            
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        next_data = soup.find(id="__NEXT_DATA__")
        if not next_data:
            return jsonify({"error": "لم يتم العثور على بيانات سناب شات من الرابط."})
            
        media_url = None
        match = re.search(r'"mediaUrl":\s*"([^"]+)"', next_data.string)
        if match:
            media_url = match.group(1)
        
        if not media_url:
            return jsonify({"error": "الرابط لا يحتوي على ميديا متاحة"})
            
        # Download temp file
        import tempfile
        r = requests.get(media_url, stream=True, headers=headers)
        ext = ".mp4" if "video" in r.headers.get('Content-Type', '') else ".jpeg"
        fd, path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                f.write(chunk)
                
        return jsonify({"success": True, "download_url": url_for('serve_single_download', path=path, _external=True)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/download_temp")
@login_required
def serve_single_download():
    path = request.args.get("path")
    if path and os.path.exists(path):
        from flask import send_file
        return send_file(path, as_attachment=True, download_name=f"snapchat_story{os.path.splitext(path)[1]}")
    return "File not found", 404

@app.route("/api/accounts", methods=["GET", "POST", "DELETE"])
def api_accounts():
    if request.method == "GET":
        return jsonify(get_accounts())
    data = request.get_json() or {}
    action = data.get("action")
    accounts = get_accounts()
    
    if action == "add":
        max_accounts = 999
        if len(accounts) >= max_accounts:
            return jsonify({"ok": False, "error": f"You reached your limit of {max_accounts} accounts. Upgrade to add more."})
            
        username = (data.get("username") or "").strip().lower()
        team = data.get("team", "Other")
        if not username:
            return jsonify({"ok": False, "error": "Username required"})
        if any(a.get("username") == username for a in accounts):
            return jsonify({"ok": False, "error": "Already exists"})
        
        info = fetch_snapchat_info(username)
        influencer_name = data.get("influencer_name", "")
        custom_hashtags = data.get("custom_hashtags", "")
        accounts.append({"username": username, "checked": True, "avatar": info.get("avatar"), "influencer_name": influencer_name, "custom_hashtags": custom_hashtags, "team": team})
        save_accounts(accounts, current_user.id)
        
    elif action == "add_bulk":
        max_accounts = 999
        
        raw = data.get("usernames") or data.get("text") or ""
        if isinstance(raw, list):
            usernames = [str(u).strip().lower() for u in raw if str(u).strip()]
        else:
            usernames = [u.strip().lower() for u in str(raw).replace(",", "\n").splitlines() if u.strip()]
        
        team = data.get("team", "Other")
        added = 0
        skipped = []
        for u in usernames:
            if len(accounts) >= max_accounts:
                skipped.append(u)
                continue
            if any(a.get("username") == u for a in accounts):
                skipped.append(u)
                continue
            
            # Fetch info (might be slow for many accounts, but acceptable for typical usage)
            info = fetch_snapchat_info(u)
            accounts.append({"username": u, "checked": True, "avatar": info.get("avatar"), "team": team})
            added += 1
            
        save_accounts(accounts, current_user.id)
        return jsonify({
            "ok": True,
            "added": added,
            "skipped": skipped,
            "accounts": get_accounts(current_user.id)
        })
    elif action == "set_team":
        username = data.get("username")
        team = data.get("team", "Other")
        for a in accounts:
            if a.get("username") == username:
                a["team"] = team
                break
        save_accounts(accounts, current_user.id)
        return jsonify({"ok": True, "accounts": get_accounts(current_user.id)})
    elif action == "remove":
        username = data.get("username")
        accounts = [a for a in accounts if a.get("username") != username]
        save_accounts(accounts, current_user.id)
    elif action == "toggle":
        username = data.get("username")
        for a in accounts:
            if a.get("username") == username:
                a["checked"] = not a.get("checked")
        save_accounts(accounts, current_user.id)
    elif action == "set_checked":
        username = data.get("username")
        checked = data.get("checked", True)
        for a in accounts:
            if a.get("username") == username:
                a["checked"] = checked
                break
        save_accounts(accounts, current_user.id)
        return jsonify({"ok": True, "accounts": get_accounts(current_user.id)})
    elif action == "set_influencer":
        username = data.get("username")
        influencer_name = data.get("influencer_name", "")
        for a in accounts:
            if a.get("username") == username:
                a["influencer_name"] = influencer_name
                break
        save_accounts(accounts, current_user.id)
        return jsonify({"ok": True, "accounts": get_accounts(current_user.id)})
    elif action == "set_hashtags":
        username = data.get("username")
        custom_hashtags = data.get("custom_hashtags", "")
        for a in accounts:
            if a.get("username") == username:
                a["custom_hashtags"] = custom_hashtags
                break
        save_accounts(accounts, current_user.id)
        return jsonify({"ok": True, "accounts": get_accounts(current_user.id)})
    elif action == "set_all_checked":
        checked = data.get("checked", True)
        for a in accounts:
            a["checked"] = checked
        save_accounts(accounts, current_user.id)
        return jsonify({"ok": True, "accounts": get_accounts(current_user.id)})
    return jsonify({"ok": True, "accounts": get_accounts(current_user.id)})


@app.route("/api/teams", methods=["POST"])
@login_required
def api_teams():
    data = request.get_json() or {}
    action = data.get("action")
    user_id = current_user.id
    
    if action == "set_team_hashtags":
        team_name = data.get("team")
        hashtags = data.get("hashtags")
        config = load_config(user_id)
        teams_config = config.get("teams_config", {})
        if team_name not in teams_config:
            teams_config[team_name] = {}
        teams_config[team_name]["hashtags"] = hashtags
        config["teams_config"] = teams_config
        save_config(config, user_id)
        return jsonify({"ok": True})
    elif action == "set_team_checked":
        team_name = data.get("team")
        checked = data.get("checked", True)
        accounts = get_accounts(user_id)
        for a in accounts:
            if a.get("team") == team_name:
                a["checked"] = checked
        save_accounts(accounts, user_id)
        return jsonify({"ok": True, "accounts": get_accounts(user_id)})
    
    return jsonify({"ok": False, "error": "Unknown action"})


@app.route("/api/open-folder", methods=["POST"])
def api_open_folder():
    """Open folder in OS explorer."""
    data = request.get_json() or {}
    username = data.get("username")
    date_str = data.get("date")
    
    if not username:
        return jsonify({"ok": False, "error": "Username required"})
    
    # Path logic
    target_path = BASE_DIR / "stories"
    if date_str:
        # If date is provided, try to open the merged folder or not merged folder
        p = target_path / "merged" / username / date_str
        if not p.exists():
            p = target_path / "not merged" / username / date_str
            if not p.exists():
                p = target_path / "not merged" / username # Fallback
        target_path = p
    else:
        target_path = target_path / "not merged" / username
    
    if not target_path.exists():
        return jsonify({"ok": False, "error": "Folder not found"})

    try:
        if os.name == 'nt':  # Windows
            getattr(os, 'startfile')(str(target_path))
        elif sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', str(target_path)])
        else:  # Linux
            subprocess.Popen(['xdg-open', str(target_path)])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    if not username:
        return jsonify({"ok": False, "error": "Username required"})
    task_id = f"dl_{username}_{date.today().isoformat()}_{os.urandom(2).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    run_task(task_id, "download", username=username, merge=data.get("merge", False), today_only=data.get("today_only", False), custom_links=data.get("custom_links", ""))
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/download-selected", methods=["POST"])
def api_download_selected():
    data = request.get_json() or {}
    usernames = [u.strip() for u in (data.get("usernames") or []) if u.strip()]
    if not usernames:
        return jsonify({"ok": False, "error": "Select at least one account"})
    task_id = f"batch_{date.today().isoformat()}_{os.urandom(4).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    run_task(task_id, "download_batch", usernames=usernames, merge=data.get("merge", False), today_only=data.get("today_only", False), custom_links=data.get("custom_links", ""))
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/schedule", methods=["GET", "POST"])
def api_schedule():
    if request.method == "GET":
        return jsonify(get_schedule())
    data = request.get_json() or {}
    schedule = {
        "enabled": bool(data.get("enabled")),
        "hour": int(data.get("hour", 9)) % 24,
        "minute": int(data.get("minute", 0)) % 60,
        "merge": bool(data.get("merge")),
    }
    save_schedule(schedule)
    return jsonify({"ok": True, "schedule": schedule})


@app.route("/api/merge", methods=["POST"])
def api_merge():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    date_str = (data.get("date") or "").strip() or date.today().strftime("%Y-%m-%d")
    if not username:
        return jsonify({"ok": False, "error": "Username required"})
    task_id = f"merge_{username}_{date_str}_{os.urandom(2).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    merge_mode = data.get("merge_mode") or data.get("mergeMode") or "shorts"  # shorts | full | both
    run_task(task_id, "merge", username=username, date_str=date_str, merge_mode=merge_mode)
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/upload", methods=["POST"])
@login_required
def api_upload():
    user_id = current_user.id if current_user and current_user.is_authenticated else ""
    print(f"DEBUG: api_upload for user_id={user_id}")
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    date_str = (data.get("date") or "").strip() or date.today().strftime("%Y-%m-%d")
    privacy = data.get("privacy") or "private"
    upload_type = data.get("upload_type") or "shorts"
    channel_id = data.get("channel_id") or None
    
    custom_long_title = data.get("custom_long_title")
    custom_thumb_path = data.get("custom_thumb_path")

    if not username:
        return jsonify({"ok": False, "error": "Username required"})
    task_id = f"upload_{username}_{date_str}_{os.urandom(2).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    run_task(task_id, "upload", username=username, date_str=date_str, privacy=privacy, upload_type=upload_type, channel_id=channel_id, user_id=user_id, custom_long_title=custom_long_title, custom_thumb_path=custom_thumb_path)
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/upload-file", methods=["POST"])
def api_upload_file():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file"})
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"ok": False, "error": "No file selected"})
    if not f.filename.lower().endswith((".mp4", ".webm", ".mov")):
        return jsonify({"ok": False, "error": "Only video files (.mp4, .webm, .mov)"})
    filename = secure_filename(f.filename) or "video.mp4"
    file_path = app.config["UPLOAD_FOLDER"] / filename
    f.save(str(file_path))
    
    # Handle optional thumbnail
    thumbnail_path = None
    if "thumbnail" in request.files:
        tf = request.files["thumbnail"]
        if tf.filename != "":
            import uuid
            uid = uuid.uuid4().hex[:8]
            t_filename = f"thumb_{uid}_{secure_filename(tf.filename)}"
            thumb_dir = app.config["UPLOAD_FOLDER"] / "thumbs"
            thumb_dir.mkdir(parents=True, exist_ok=True)
            thumbnail_path = str(thumb_dir / t_filename)
            tf.save(thumbnail_path)

    title = (request.form.get("title") or filename).replace(".mp4", "")
    privacy = request.form.get("privacy") or "private"
    channel_id = request.form.get("channel_id") or None
    task_id = f"uf_{os.urandom(4).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}
    run_task(task_id, "upload_file", file_path=str(file_path), title=title, privacy=privacy, channel_id=channel_id, thumbnail_path=thumbnail_path)
    return jsonify({"ok": True, "task_id": task_id})

@app.route("/api/upload-temp-thumb", methods=["POST"])
@login_required
def api_upload_temp_thumb():
    if "thumb_file" not in request.files:
        return jsonify({"ok": False, "error": "No file"})
    f = request.files["thumb_file"]
    if f.filename == "":
        return jsonify({"ok": False, "error": "No file selected"})
    if not f.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return jsonify({"ok": False, "error": "صيغة غير مدعومة. يسمح بالصور فقط."})
    
    import uuid
    uid = uuid.uuid4().hex[:8]
    filename = secure_filename(f.filename) or f"thumb_{uid}.jpg"
    thumb_dir = app.config["UPLOAD_FOLDER"] / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = thumb_dir / f"{uid}_{filename}"
    f.save(str(file_path))
    return jsonify({"ok": True, "path": str(file_path)})

@limiter.exempt
@app.route("/api/task_history")
@login_required
def api_task_history():
    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
    return jsonify({"ok": True, "history": history})

@limiter.exempt
@app.route("/api/task/<task_id>")
def api_task(task_id):
    return jsonify(tasks.get(task_id, {"status": "unknown"}))


@app.route("/api/merged-folders")
def api_merged_folders():
    return jsonify(get_merged_folders())


# حسابات فرق صناعة المحتوى السعودية (مقترحة)
SUGGESTED_ACCOUNTS = [
    {"username": "falconsesports", "label": "فالكونز Falcons"},
    {"username": "teamfalconsgg", "label": "فالكونز Falcons"},
    {"username": "poweresports", "label": "باور Power"},
    {"username": "snap.topz", "label": "تي يو TU Topz"},
]


@limiter.exempt
@app.route("/api/suggested-accounts")
def api_suggested_accounts():
    return jsonify({"accounts": SUGGESTED_ACCOUNTS})


@limiter.exempt
@app.route("/api/youtube/channels")
def api_youtube_channels():
    try:
        from webapp.youtube_service import list_connected_channels
        all_ch = list_connected_channels()
        if isinstance(all_ch, list):
            # Filter out unknown placeholders
            filtered = [c for c in all_ch if not c.get("id", "").startswith("unknown")]
            return jsonify(filtered)
        return jsonify(all_ch)
    except ImportError:
        return jsonify({"ok": False, "error": "Install google-api-python-client", "channels": []})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "channels": []})


@app.route("/api/youtube/refresh", methods=["POST"])
def api_youtube_refresh():
    try:
        from webapp.youtube_service import refresh_channels
        res = refresh_channels()
        if res.get("ok") and isinstance(res.get("channels"), list):
            res["channels"] = [c for c in res["channels"] if not c.get("id", "").startswith("unknown")]
        return jsonify(res)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "channels": []})


@app.route("/api/youtube/upload_token", methods=["POST"])
@login_required
def api_youtube_upload_token():
    try:
        if 'token_file' not in request.files:
            return jsonify({"ok": False, "error": "No file part"})
        file = request.files['token_file']
        channel_id = request.form.get("channel_id")
        if file.filename == '' or not channel_id:
            return jsonify({"ok": False, "error": "No selected file or channel"})
            
        if not file.filename.endswith(".json"):
            return jsonify({"ok": False, "error": "Only .json files are allowed"})

        from webapp.youtube_service import get_tokens_dir, _safe_channel_id
        import time
        import uuid
        
        tdir = get_tokens_dir(current_user.id)
        safe_id = _safe_channel_id(channel_id)
        ts = int(time.time())
        uid = uuid.uuid4().hex[:6]
        
        filename = f"token_{ts}_{uid}_{safe_id}.json"
        save_path = tdir / filename
        file.save(str(save_path))
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/youtube/upload_client_secret", methods=["POST"])
@login_required
def api_youtube_upload_client_secret():
    try:
        files = request.files.getlist('secret_files')
        if not files or files[0].filename == '':
            return jsonify({"ok": False, "error": "No selected file"})
            
        import time
        import uuid
        from pathlib import Path
        
        # Clear existing non-default client secrets first so invalid ones don't get stuck
        secrets_dir = BASE_DIR / "webapp" / "client_secrets"
        secrets_dir.mkdir(parents=True, exist_ok=True)
        try:
            for p in secrets_dir.glob("client_secret*.json"):
                if p.name != "client_secrets.json":
                    p.unlink()
        except:
            pass

        uploaded_count = 0
        for file in files:
            if file and file.filename.endswith(".json"):
                try:
                    content = file.read().decode('utf-8', errors='ignore')
                    if "1a2b3c4d5e6f" in content or "YOUR_CLIENT_ID" in content:
                        return jsonify({"ok": False, "error": "الملف الذي رفعته يحتوي على بيانات وهمية. يرجى الحصول على ملف حقيقي من Google Cloud."})
                    file.seek(0)
                except Exception:
                    file.seek(0)
                    
                ts = int(time.time())
                uid = uuid.uuid4().hex[:6]
                filename = f"client_secret_{ts}_{uid}_{uploaded_count}.json"
                save_path = secrets_dir / filename
                file.save(str(save_path))
                uploaded_count += 1


        if uploaded_count == 0:
            return jsonify({"ok": False, "error": "Only .json files are allowed"})
            
        return jsonify({"ok": True, "count": uploaded_count})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/youtube/delete_tokens", methods=["POST"])
@login_required
def api_youtube_delete_tokens():
    try:
        from webapp.youtube_service import delete_all_tokens, save_youtube_channels
        
        # Delete tokens and secrets
        count = delete_all_tokens(current_user.id)
        
        # Also clear the connected channels list from webapp_config
        save_youtube_channels([], current_user.id)
        
        return jsonify({"ok": True, "deleted": count})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/youtube/connect")
def youtube_connect():
    """Redirect to Google OAuth to add a new channel."""
    try:
        from webapp.youtube_service import get_authorization_url
        base_url = request.url_root.rstrip("/")
        redirect_uri = f"{base_url}/youtube/callback"
        auth_url, state, code_verifier, secret_path = get_authorization_url(redirect_uri)
        if not auth_url:
            return redirect("/?youtube_error=" + quote(state or "Unknown error"))
        session["youtube_oauth_state"] = state
        session["youtube_oauth_secret"] = str(secret_path)
        if code_verifier:
            session["youtube_code_verifier"] = code_verifier
        return redirect(auth_url)
    except Exception as e:
        return redirect("/?youtube_error=" + quote(str(e)))


@app.route("/youtube/callback")
def youtube_callback():
    """OAuth callback - add channel and redirect home."""
    state = request.args.get("state")
    if state != session.get("youtube_oauth_state"):
        return redirect("/?youtube_error=Invalid+state")
    session.pop("youtube_oauth_state", None)
    
    code_verifier = session.pop("youtube_code_verifier", None)
    code = request.args.get("code")
    if not code:
        return redirect("/?youtube_error=No+code")
    try:
        from webapp.youtube_service import add_channel_from_code
        base_url = request.url_root.rstrip("/")
        redirect_uri = f"{base_url}/youtube/callback"
        secret_path = session.pop("youtube_oauth_secret", None)
        ok, err, ch = add_channel_from_code(code, redirect_uri, code_verifier=code_verifier, secret_path=secret_path)
        if ok:
            return redirect("/?youtube_connected=1")
        return redirect("/?youtube_error=" + quote(err or "Unknown"))
    except Exception as e:
        return redirect("/?youtube_error=" + quote(str(e)))


@app.route("/youtube/stats")
@login_required
def youtube_stats():
    """Render the YouTube Channel Statistics page."""
    try:
        from webapp.youtube_service import get_youtube_channels_config
        channels = get_youtube_channels_config(current_user.id)
        return render_template("youtube_stats.html", channels=channels)
    except Exception as e:
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>", 500


@app.route("/api/youtube/stats/<channel_id>")
@login_required
def api_youtube_stats(channel_id):
    """API endpoint to get channel video statistics."""
    from webapp.youtube_service import get_channel_videos_stats
    return jsonify(get_channel_videos_stats(channel_id))

@limiter.exempt
@app.route("/api/youtube/token_status")
@login_required
def api_youtube_token_status():
    """List all tokens and their current health/cooldown status."""
    from webapp.youtube_service import get_tokens_dir, load_token_health
    tdir = get_tokens_dir(current_user.id)
    health = load_token_health(current_user.id)
    
    tokens = []
    if tdir.exists():
        for f in tdir.glob("*.json"):
            name = f.name
            h = health.get(name, {})
            status = h.get("status", "active")
            cooldown_until = h.get("cooldown_until")
            
            # Auto-check if cooldown expired
            if status == "cooldown" and cooldown_until:
                from datetime import datetime
                try:
                    until = datetime.fromisoformat(cooldown_until)
                    if datetime.now() > until:
                        status = "active"
                except: pass
                
            tokens.append({
                "id": name,
                "status": status,
                "cooldown_until": cooldown_until,
                "size": f.stat().st_size
            })
    return jsonify({"ok": True, "tokens": tokens})

@app.route("/api/youtube/delete_token/<token_id>", methods=["DELETE"])
@login_required
def api_youtube_delete_single_token(token_id):
    """Delete a specific token file."""
    from webapp.youtube_service import get_tokens_dir
    tdir = get_tokens_dir(current_user.id)
    token_file = tdir / token_id
    if token_file.exists() and token_file.is_file():
        token_file.unlink()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Token not found"}), 404

@app.route("/api/thumbnail/preview", methods=["POST"])
@login_required
def api_thumbnail_preview():
    """Generate a temporary thumbnail preview."""
    data = request.get_json() or {}
    username = data.get("username")
    date_str = data.get("date") or date.today().strftime("%Y-%m-%d")
    
    if not username:
        return jsonify({"ok": False, "error": "Username required"})
        
    try:
        from webapp.thumbnail_generator import generate_full_video_thumbnail
        import tempfile
        import base64
        
        # Look for a video to use as source
        merged_folder = BASE_DIR / "stories" / "merged" / username / date_str
        video_path = merged_folder / "merged_all.mp4"
        if not video_path.exists():
            # Try a random short
            shorts = list(merged_folder.glob("merged_*.mp4"))
            if shorts:
                video_path = shorts[0]
        
        if not video_path.exists():
            return jsonify({"ok": False, "error": "No merged video found for preview. Please merge first."})
            
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            
        success = generate_full_video_thumbnail(str(video_path), tmp_path, username, date_str)
        if success:
            with open(tmp_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")
            os.remove(tmp_path)
            return jsonify({"ok": True, "image": img_data})
        else:
            return jsonify({"ok": False, "error": "Thumbnail generation failed"})
            
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


def _run_upload_all(task_id, folders, privacy, upload_type, channel_id=None, user_id=""):
    """Upload all merged folders to YouTube."""
    tasks[task_id]["status"] = "running"
    total = len(folders)
    uploaded_folders = 0
    total_videos = 0
    last_error = None
    try:
        from webapp.youtube_service import upload_from_folder
        if user_id:
            os.environ["SNAPSCRAP_USER_ID"] = str(user_id)
        for idx, f in enumerate(folders):
            tasks[task_id]["message"] = f"Uploading {f['username']}/{f['date']} ({idx + 1}/{total})..."
            r = upload_from_folder(f["username"], f["date"], privacy, upload_type, channel_id=channel_id)
            if r.get("success"):
                uploaded_folders += 1
                total_videos += r.get("count", 0)
            else:
                last_error = r.get("error", "Upload failed")
        tasks[task_id]["status"] = "done"
        tasks[task_id]["message"] = f"Uploaded {total_videos} videos from {uploaded_folders} folder(s)!"
        if last_error and uploaded_folders == 0:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = last_error
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["message"] = str(e)
        
        
@app.route("/api/upload-all", methods=["POST"])
def api_upload_all():
    user_id = current_user.id if current_user and current_user.is_authenticated else ""
    data = request.get_json() or {}
    folders = data.get("folders") or get_merged_folders()
    if not folders:
        return jsonify({"ok": False, "error": "No merged folders to upload"})
    privacy = data.get("privacy") or "private"
    upload_type = data.get("upload_type") or "shorts"
    channel_id = data.get("channel_id") or None
    task_id = f"upload_all_{os.urandom(4).hex()}"
    tasks[task_id] = {"status": "pending", "message": "Starting..."}

def _run_batch_pipeline(task_id, usernames, date_str, privacy, upload_type, channel_id=None, user_id="", force=False, publish_at=None, skip_first=0, custom_long_title=None, custom_thumb_path=None):
    """Run full pipeline for multiple users."""
    from datetime import datetime
    import time
    
    # Convert local datetime-local string to UTC ISO
    if publish_at:
        try:
            dt = datetime.strptime(publish_at, "%Y-%m-%dT%H:%M")
            publish_at = dt.strftime("%Y-%m-%dT%H:%M:00Z")
            privacy = "private" 
        except Exception as e:
            print(f"Error parsing batch publish_at: {e}")
            publish_at = None

    tasks[task_id]["status"] = "running"
    total = len(usernames)
    success_count = 0
    
    if force:
        os.environ["SNAPSCRAP_FORCE_RELOAD"] = "1"
    
    from webapp.youtube_service import upload_from_folder
    from merge_videos import merge_videos_for_user
    
    for idx, username in enumerate(usernames):
        if tasks[task_id].get("cancel_requested"):
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = "تم إلغاء العملية الكلية بناء على طلب المستخدم."
            break
            
        if tasks[task_id].get("skip_requested"):
            tasks[task_id]["skip_requested"] = False # Reset for the next iteration
            tasks[task_id]["message"] = f"[{username}] تم تجاوز الحساب بتدخل المستخدم..."
            time.sleep(1)
            continue
            
        tasks[task_id]["message"] = f"Processing {username} ({idx + 1}/{total})..."
        print(f"PIPELINE BATCH: Processing {username}...")
        
        try:
            # Smart Skip Check
            raw_path = BASE_DIR / "stories" / "not merged" / username / date_str
            merged_folder = BASE_DIR / "stories" / "merged" / username / date_str
            
            # Check if we already have the final merged video
            has_merged_all = merged_folder.exists() and (merged_folder / "merged_all.mp4").exists()
            
            if has_merged_all and not force:
                tasks[task_id]["message"] = f"[{username}] مدمج مسبقاً. فحص الرفع..."
                print(f"PIPELINE BATCH: {username} already merged. Skipping download/merge.")
            else:
                # 1. Download
                tasks[task_id]["message"] = f"[{username}] Downloading snaps..."
                
                env = os.environ.copy()
                if user_id: env["SNAPSCRAP_USER_ID"] = str(user_id)
                if force: env["SNAPSCRAP_FORCE_RELOAD"] = "1"
                env["PYTHONUNBUFFERED"] = "1"
                import sys
                
                cmd1 = [sys.executable, str(BASE_DIR / "SnapScrap.py"), username, "--date", date_str]
                if skip_first > 0:
                    cmd1.extend(["--skip-first", str(skip_first)])
                if kwargs.get("today_only"):
                    cmd1.append("--today-only")
                    
                proc1 = subprocess.Popen(cmd1, cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, encoding="utf-8", errors="replace")
                for line in iter(proc1.stdout.readline, ""):
                    if not line: break
                    if line.strip().startswith("[PROGRESS]"):
                        progress_str = line.strip().split("]")[1].strip()
                        tasks[task_id]["message"] = f"[{username}] Downloading... ({progress_str})"
                proc1.wait()
            
            # Empty Account Check: Skip merge/upload if no files
            path = BASE_DIR / "stories" / "not merged" / username / date_str
            merged_folder = BASE_DIR / "stories" / "merged" / username / date_str
            
            # DEBUG
            raw_exists = path.exists() and any(f.is_file() for f in path.iterdir())
            has_merged = merged_folder.exists() and any(f.is_file() and f.suffix == '.mp4' for f in merged_folder.iterdir())
            print(f"PIPELINE BATCH: {username} - Raw folder exists: {path.exists()}, Has files: {raw_exists}, Merged folder exists: {merged_folder.exists()}, Has files: {has_merged}")
            
            if not has_merged and not raw_exists:
                tasks[task_id]["message"] = f"[{username}] لا توجد سنابات. جاري التخطي..."
                print(f"PIPELINE BATCH: Skipping {username} because no files found for date {date_str}")
                time.sleep(1.5)
                continue
            
            if tasks[task_id].get("cancel_requested"): break
            if tasks[task_id].get("skip_requested"):
                tasks[task_id]["skip_requested"] = False
                continue
                
            # 2. Merge
            if not has_merged_all or force:
                tasks[task_id]["message"] = f"[{username}] Merging videos..."
                merge_videos_for_user(username, date_str)
            else:
                print(f"PIPELINE BATCH: {username} merged files found. Skipping merge step.")
            
            if tasks[task_id].get("cancel_requested"): break
            if tasks[task_id].get("skip_requested"):
                tasks[task_id]["skip_requested"] = False
                continue
            
            # 3. Upload
            if upload_type != "prepare":
                tasks[task_id]["message"] = f"[{username}] Uploading to YouTube ({upload_type})..."
                
                def update_progress(msg):
                    # Show account name prefixed to the upload progress
                    tasks[task_id]["message"] = f"[{username}] {msg}"
                
                upload_from_folder(
                    username, 
                    date_str, 
                    privacy, 
                    upload_type, 
                    channel_id=channel_id, 
                    user_id=user_id, 
                    publish_at=publish_at, 
                    progress_callback=update_progress,
                    custom_long_title=custom_long_title,
                    custom_thumb_path=custom_thumb_path
                )
            else:
                tasks[task_id]["message"] = f"[{username}] Prepared files. Skipping upload."
            
            success_count += 1
        except Exception as e:
            print(f"PIPELINE BATCH ERROR for {username}: {e}")
            
    if force:
        os.environ.pop("SNAPSCRAP_FORCE_RELOAD", None)
    tasks[task_id]["status"] = "done"
    tasks[task_id]["message"] = f"Batch Complete! Processed {success_count}/{total} accounts."

@app.route("/api/run-all-pipelines", methods=["POST"])
def api_run_all_pipelines():
    user_id = current_user.id if current_user and current_user.is_authenticated else ""
    data = request.get_json() or {}
    usernames = data.get("usernames")
    if not usernames:
        # Get all checked accounts
        accounts = get_accounts(user_id)
        usernames = [a["username"] for a in accounts if a.get("checked")]
    
    if not usernames:
        return jsonify({"ok": False, "error": "No accounts selected"})
        
    date_str = data.get("date") or date.today().strftime("%Y-%m-%d")
    privacy = data.get("privacy") or "private"
    upload_type = data.get("upload_type") or "shorts"
    channel_id = data.get("channel_id") or None
    force = data.get("force") or False
    publish_at = data.get("publish_at")
    skip_first = data.get("skip_first", 0)
    custom_long_title = data.get("custom_long_title")
    custom_thumb_path = data.get("custom_thumb_path")
    today_only = data.get("today_only", False)
    
    task_id = f"batch_pipe_{os.urandom(4).hex()}"
    tasks[task_id] = {"status": "queued", "message": "العملية في طابور الانتظار الكلي...", "cancel_requested": False, "skip_requested": False}
    
    args = (task_id, usernames, date_str, privacy, upload_type, channel_id, user_id)
    kwargs = {
        "force": force, 
        "publish_at": publish_at, 
        "skip_first": skip_first, 
        "custom_long_title": custom_long_title,
        "custom_thumb_path": custom_thumb_path,
        "today_only": today_only
    }
    pipeline_queue.put((_run_batch_pipeline, task_id, args, kwargs))
        
    return jsonify({"ok": True, "task_id": task_id})


@app.route("/api/clear-batch", methods=["POST"])
def api_clear_batch():
    """Delete username/date folder after upload (manual cleanup)."""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    date_str = (data.get("date") or "").strip()
    if not username or not date_str:
        return jsonify({"ok": False, "error": "Username and date required"})
    folder = BASE_DIR / "stories" / "not merged" / username / date_str
    if not folder.exists():
        folder = BASE_DIR / "stories" / "merged" / username / date_str
    if not folder.is_dir():
        return jsonify({"ok": False, "error": "Folder not found"})
    if username in ("webapp", "build", "dist", "uploads") or username.startswith("."):
        return jsonify({"ok": False, "error": "Cannot delete that folder"})
    try:
        import shutil
        shutil.rmtree(folder)
        return jsonify({"ok": True, "message": f"Deleted {username}/{date_str}"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.errorhandler(500)
def internal_error(exception):
    import traceback
    tb = traceback.format_exc()
    if tb.strip() == "NoneType: None":
        # Sometimes format_exc is empty. Try using original exception text
        return f"<pre>{str(exception)}</pre>", 500
    return f"<pre>{tb}</pre>", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)