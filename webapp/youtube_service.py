import json
import os
import re
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

BASE_DIR = Path(__file__).resolve().parent.parent
TOKENS_DIR = BASE_DIR / "stories" / "tokens"
MERGED_DIR = "merged" # Only used as a fallback or name
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
]

CONFIG_KEY = "youtube_channels"

def get_user_id():
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return current_user.id
    except (RuntimeError, ImportError, AttributeError, Exception):
        pass
    return os.environ.get("SNAPSCRAP_USER_ID", "1")

def get_user_dir(user_id=None):
    uid = user_id if user_id is not None else get_user_id()
    d = BASE_DIR / "stories"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_tokens_dir(user_id=None):
    d = get_user_dir(user_id) / "tokens"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _safe_channel_id(channel_id):
    """Make channel ID safe for filename (replace non-alphanumeric)."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", channel_id) if channel_id else "default"

def _token_path(channel_id, user_id=None):
    """Get token file path for a channel."""
    tdir = get_tokens_dir(user_id)
    if not channel_id:
        return tdir / "token.json"
    return tdir / f"token_{_safe_channel_id(channel_id)}.json"

def get_webapp_config_file(user_id=None):
    return get_user_dir(user_id) / "webapp_config.json"

def load_webapp_config(user_id=None):
    cfg_file = get_webapp_config_file(user_id)
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_webapp_config(config, user_id=None):
    cfg_file = get_webapp_config_file(user_id)
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_youtube_channels_config(user_id=None):
    """Get list of connected channels from config."""
    cfg = load_webapp_config(user_id)
    return cfg.get(CONFIG_KEY, [])

def save_youtube_channels(channels, user_id=None):
    """Save connected channels to config."""
    cfg = load_webapp_config(user_id)
    cfg[CONFIG_KEY] = channels
    save_webapp_config(cfg, user_id)

# --- Token Health & Cooldown Management ---

def get_token_health_file(user_id=None):
    return get_user_dir(user_id) / "token_health.json"

def load_token_health(user_id=None):
    f = get_token_health_file(user_id)
    if f.exists():
        try:
            with open(f, "r", encoding="utf-8") as f_obj:
                return json.load(f_obj)
        except Exception:
            pass
    return {}

def save_token_health(health_data, user_id=None):
    f = get_token_health_file(user_id)
    with open(f, "w", encoding="utf-8") as f_obj:
        json.dump(health_data, f_obj, indent=2, ensure_ascii=False)

def update_token_status(token_path, status="active", user_id=None, cooldown_hours=0):
    """Update token health status. status: 'active', 'cooldown', 'invalid'."""
    health = load_token_health(user_id)
    token_key = str(Path(token_path).name)
    if token_key not in health:
        health[token_key] = {}
    
    health[token_key]["status"] = status
    if status == "cooldown" and cooldown_hours > 0:
        until = datetime.now() + timedelta(hours=cooldown_hours)
        health[token_key]["cooldown_until"] = until.isoformat()
    elif status == "active":
        health[token_key].pop("cooldown_until", None)
        
    save_token_health(health, user_id)

def is_token_usable(token_path, user_id=None):
    """Check if token is not in cooldown and not invalid."""
    health = load_token_health(user_id)
    token_key = str(Path(token_path).name)
    if token_key not in health:
        return True
    
    h = health[token_key]
    if h.get("status") == "invalid":
        return False
        
    if "cooldown_until" in h:
        try:
            until = datetime.fromisoformat(h["cooldown_until"])
            if datetime.now() < until:
                return False
        except Exception:
            pass
            
    return True


def _migrate_legacy_token():
    """If token.json exists but no channels in config, migrate it."""
    channels = get_youtube_channels_config()
    default_token = get_tokens_dir() / "token.json"
    if channels or not default_token.exists():
        return
    youtube, err = get_youtube_service(channel_id=None)
    if err:
        return
    try:
        resp = youtube.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        if items:
            c = items[0]
            ch_id = c["id"]
            title = c["snippet"].get("title", "YouTube")
            token_path = _token_path(ch_id)
            if token_path != default_token:
                import shutil
                shutil.copy(default_token, token_path)
            save_youtube_channels([{"id": ch_id, "title": title}])
    except Exception:
        pass


def _get_all_tokens_for_channel(channel_id, user_id=None):
    tdir = get_tokens_dir(user_id)
    if not channel_id:
        return [tdir / "token.json"]
    
    safe_id = _safe_channel_id(channel_id)
    tokens = []
    
    if tdir.exists():
        for p in tdir.glob("token*.json"):
            # 1. token_CHANNELID.json
            if p.name == f"token_{safe_id}.json":
                tokens.append(p)
            # 2. token_CHANNELID_123.json (manual uploads)
            elif p.name.startswith(f"token_{safe_id}_"):
                tokens.append(p)
            # 3. token_123_CHANNELID.json (OAuth)
            elif p.name.endswith(f"_{safe_id}.json") and p.name.startswith("token"):
                tokens.append(p)

    if not tokens:
        tokens.append(tdir / f"token_{safe_id}.json")
    # Sort by modification time (freshest first)
    return sorted(tokens, key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True)


def _get_client_secrets():
    secrets_dir = Path(__file__).resolve().parent / "client_secrets"
    secrets = []
    if secrets_dir.exists():
        for p in secrets_dir.glob("client_secret*.json"):
            if p.name == "client_secrets.json":
                continue
            secrets.append(p)
    if not secrets:
        # Fallback to local file if it exists
        if (secrets_dir / "client_secrets.json").exists():
            secrets.append(secrets_dir / "client_secrets.json")
    return sorted(secrets)

def _get_token_for_secret(channel_id, user_id, secret_path):
    secret_name = secret_path.stem
    suffix = secret_name.replace("client_secret", "")
    tdir = get_tokens_dir(user_id)
    if not channel_id:
        return tdir / f"token{suffix}.json"
    return tdir / f"token{suffix}_{_safe_channel_id(channel_id)}.json"

def get_youtube_service(channel_id=None, token_path_override=None, client_secret_path=None):
    """Get YouTube API service with high robustness. Tries multiple token/secret combinations."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError("Install: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")

    user_id = get_user_id()
    
    # 1. Gather potential tokens
    potential_tokens = []
    if token_path_override:
        potential_tokens = [Path(token_path_override)]
    elif channel_id:
        potential_tokens = _get_all_tokens_for_channel(channel_id, user_id)
    else:
        # Try default token.json then first channel's tokens
        p_token = get_tokens_dir(user_id) / "token.json"
        if p_token.exists():
            potential_tokens.append(p_token)
        channels = get_youtube_channels_config(user_id)
        if channels:
            potential_tokens.extend(_get_all_tokens_for_channel(channels[0]["id"], user_id))

    # De-duplicate and filter out known invalid tokens
    seen_paths = set()
    filtered_tokens = []
    for p in potential_tokens:
        if p not in seen_paths and p.exists():
            if is_token_usable(p, user_id): # This checks for 'invalid' status
                filtered_tokens.append(p)
            seen_paths.add(p)

    if not filtered_tokens:
        return None, "لم يتم العثور على أي قناة متصلة صالحة. يرجى إضافة قناة أولاً."

    # 2. Gather all available secrets
    all_secrets = _get_client_secrets()
    if client_secret_path and Path(client_secret_path).exists():
        # Prioritize override secret
        p_secret = Path(client_secret_path)
        if p_secret in all_secrets: all_secrets.remove(p_secret)
        all_secrets.insert(0, p_secret)

    errors = []
    
    # 3. Outer loop: Tokens
    for token_path in filtered_tokens:
        # Inner loop: Secrets (Cross-Try)
        # We'll prioritize the secret that "matches" the token number if applicable
        current_secrets_to_try = list(all_secrets)
        match = re.search(r"token_(\d+)_", token_path.name)
        if match:
            # Look for client_secret_XX.json
            guess_name = f"client_secret_{match.group(1)}.json"
            for i, s in enumerate(current_secrets_to_try):
                if s.name == guess_name:
                    current_secrets_to_try.insert(0, current_secrets_to_try.pop(i))
                    break

        for secret_path in current_secrets_to_try:
            try:
                with open(token_path, "r") as f:
                    token_data = json.load(f)
                
                # Inject secret data if needed
                with open(secret_path, "r") as f:
                    secret_data = json.load(f)
                    key = "installed" if "installed" in secret_data else "web" if "web" in secret_data else None
                    if key:
                        token_data["client_id"] = secret_data[key]["client_id"]
                        token_data["client_secret"] = secret_data[key]["client_secret"]
                
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        try:
                            creds.refresh(Request())
                            # Save refreshed token
                            with open(token_path, "w") as f:
                                f.write(creds.to_json())
                        except Exception as e:
                            err_str = str(e)
                            if "deleted_client" in err_str or "invalid_grant" in err_str:
                                # This token or its client is permanently dead
                                update_token_status(token_path, status="invalid", user_id=user_id)
                                errors.append(f"Token {token_path.name} is permanently invalid: {err_str}")
                                break # Move to next token, this one is dead for ALL secrets usually
                            else:
                                raise e # Try next secret for this token?
                
                # Final check: can we actually build a service?
                service = build("youtube", "v3", credentials=creds)
                # Test connectivity
                service.channels().list(part="id", mine=True).execute()
                
                return service, None

            except Exception as e:
                err_str = str(e)
                if "deleted_client" in err_str:
                    # The client secret itself is dead. Move to next secret.
                    continue
                elif "invalid_grant" in err_str:
                    # Token revoked. Mark as invalid and move to next token.
                    update_token_status(token_path, status="invalid", user_id=user_id)
                    errors.append(f"Token {token_path.name} was revoked.")
                    break # Next token
                else:
                    errors.append(f"Trying {token_path.name} with {secret_path.name} failed: {e}")
                    continue

    final_err = " | ".join(errors[-3:]) if errors else "No valid tokens found in the army."
    return None, f"فشل الاتصال بكل الحسابات المتاحة: {final_err}"



def delete_all_tokens(user_id=None):
    """Delete all token files to reset authentication state, keeping client secrets."""
    deleted_count = 0
    
    # 1. Delete all tokens in user's tokens directory
    tdir = get_tokens_dir(user_id)
    if tdir.exists():
        for p in tdir.glob("*.json"):
            try:
                p.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting token {p.name}: {e}")
                
    return deleted_count

def get_authorization_url(redirect_uri):
    """Get Google OAuth URL for adding a new channel."""
    flow, err = get_oauth_flow(redirect_uri)
    if err:
        return None, err, None, None
    auth_url, state = flow.authorization_url(access_type="offline", prompt="consent")
    code_verifier = getattr(flow, 'code_verifier', None)
    return auth_url, state, code_verifier, getattr(flow, 'associated_secret_path', None)


def get_oauth_flow(redirect_uri, force_secret_path=None):
    """Create OAuth flow for web redirect."""
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        return None, "Install google-auth-oauthlib"
    client_secrets = _get_client_secrets()
    if not client_secrets:
        return None, "Place client_secret.json in project folder"

    user_id = get_user_id()
    
    # Defaults
    client_path = client_secrets[0]
    
    if force_secret_path and Path(force_secret_path).exists():
        client_path = Path(force_secret_path)
    else:
        # For OAuth flow, if we know who the user is, let's find a secret that hasn't been authorized yet
        # to naturally distribute tokens.
        for secret in client_secrets:
            token_for_this = _get_token_for_secret(None, user_id, secret)
            if not token_for_this.exists():
                client_path = secret
                break
            
    try:
        flow = Flow.from_client_secrets_file(str(client_path), SCOPES, redirect_uri=redirect_uri)
        # Store which secret we are using
        flow.associated_secret_path = client_path
        return flow, None
    except Exception as e:
        import traceback
        return None, f"Flow error: {str(e)}\n{traceback.format_exc()}"


def add_channel_from_code(code, redirect_uri, code_verifier=None, secret_path=None):
    """Exchange auth code for token, get channel info, save and add to config. Returns (ok, error, channel_info)."""
    flow, err = get_oauth_flow(redirect_uri, force_secret_path=secret_path)
    if err:
        return False, err, None
    
    if code_verifier:
        flow.code_verifier = code_verifier
        
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
    except Exception as e:
        import traceback
        return False, f"Token Exchange Error: {str(e)}\n{traceback.format_exc()}", None

    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        youtube = build("youtube", "v3", credentials=creds)
        
        user_id = get_user_id()
        secret_path = getattr(flow, 'associated_secret_path', _get_client_secrets()[0] if _get_client_secrets() else None)
        
        ch_id = "unknown_channel"
        if secret_path:
            ch_id = f"unknown_{_safe_channel_id(secret_path.stem)}"
            
        title = "YouTube Channel (Quota Limited)"
        
        try:
            resp = youtube.channels().list(part="snippet", mine=True).execute()
            items = resp.get("items", [])
            if items:
                c = items[0]
                ch_id = c["id"]
                title = c["snippet"].get("title", "YouTube")
        except HttpError as e:
            if e.resp.status == 403:
                # Quota exceeded but token is valid! Let's proceed with placeholder
                print(f"⚠️ Quota exceeded. Saving token as '{ch_id}'.")
            else:
                raise e

        if secret_path:
            token_path = _get_token_for_secret(ch_id, user_id, secret_path)
            # Also save a generic token for the secret to mark it as used
            generic_token = _get_token_for_secret(None, user_id, secret_path)
            
            with open(token_path, "w") as f:
                f.write(creds.to_json())
            with open(generic_token, "w") as f:
                f.write(creds.to_json())

        channels = get_youtube_channels_config()
        if not any(x.get("id") == ch_id for x in channels):
            channels.append({"id": ch_id, "title": title})
            save_youtube_channels(channels)
        return True, None, {"id": ch_id, "title": title}
    except Exception as e:
        import traceback
        return False, str(e), None


def list_connected_channels():
    """List channels from config (our connected channels). Optionally refresh from API."""
    _migrate_legacy_token()
    channels = get_youtube_channels_config()
    # Filter out unknown placeholders at the source so they never leak to UI
    filtered = [c for c in channels if not c.get("id", "").startswith("unknown")]
    return {"ok": True, "channels": filtered}


def refresh_channels():
    """Re-fetch channel info from YouTube API for all connected channels."""
    _migrate_legacy_token()
    channels = get_youtube_channels_config()
    updated = []
    for ch in channels:
        ch_id = ch.get("id")
        if not ch_id:
            continue
        youtube, err = get_youtube_service(channel_id=ch_id)
        if err:
            continue
        try:
            resp = youtube.channels().list(part="snippet", id=ch_id).execute()
            items = resp.get("items", [])
            if items:
                title = items[0]["snippet"].get("title", ch.get("title", "YouTube"))
                updated.append({"id": ch_id, "title": title})
        except Exception:
            updated.append(ch)
    save_youtube_channels(updated)
    # Filter out unknown placeholders from the returned list too
    filtered = [c for c in updated if not c.get("id", "").startswith("unknown")]
    return {"ok": True, "channels": filtered}


def load_title_template():
    config_file = BASE_DIR / "gui_config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f).get("title_template", "سنابات {username} | يوم {date} | الجزء {part}")
        except Exception:
            pass
    return "سنابات {username} | يوم {date} | الجزء {part}"


def list_youtube_channels():
    """Legacy: list channels (now returns connected channels)."""
    return list_connected_channels()


def get_youtube_service_for_channel(channel_id):
    """Get YouTube service for a specific channel ID (from our connected list)."""
    return get_youtube_service(channel_id=channel_id)


def upload_from_folder(username, date_str, privacy="private", upload_type="shorts", channel_id=None, progress_callback=None, publish_time=None, user_id=None, publish_at=None, custom_long_title=None, **kwargs):
    """Cleanly upload merged videos with 'Army of APIs' and automatic numbering."""
    merged_folder = Path(BASE_DIR) / "stories" / "merged" / username / date_str
    if not merged_folder.is_dir():
        return {"success": True, "count": 0, "error": f"Folder not found: {username}/{date_str}"}

    try:
        from googleapiclient.http import MediaIoBaseUpload
        from googleapiclient.errors import HttpError
    except ImportError:
        return {"success": False, "error": "Missing dependencies"}

    user_id = user_id or get_user_id()
    publish_time = publish_time or publish_at
    display_name = username.replace("_", " ").title()
    custom_hashtags = ""
    
    # 0. Get Influencer Info
    try:
        from webapp.app import get_accounts
        accounts = get_accounts(user_id)
        for acc in accounts:
            if acc.get("username") == username:
                if acc.get("influencer_name"): display_name = acc["influencer_name"].strip()
                if acc.get("custom_hashtags"): custom_hashtags = acc["custom_hashtags"].strip()
                break
    except: pass

    try:
        from webapp.thumbnail_generator import generate_full_video_thumbnail
    except:
        def generate_full_video_thumbnail(*args, **kwargs): return False

    # 1. Prepare Upload List
    date_fmt = date_str
    title_template = load_title_template()
    metadata_file = merged_folder / "uploaded_youtube" / "upload_meta.json"
    archive_dir = merged_folder / "uploaded_youtube"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    upload_history = []
    if metadata_file.exists():
        try: upload_history = json.loads(metadata_file.read_text(encoding="utf-8"))
        except: pass

    def save_history(entry):
        if entry: upload_history.append(entry)
        metadata_file.write_text(json.dumps(upload_history, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_num(p):
        m = re.search(r"merged_(\d+)\.mp4", p.name)
        return int(m.group(1)) if m else 999

    shorts = sorted([p for p in merged_folder.glob("merged_*.mp4") if "merged_all" not in p.name], key=get_num)
    full_path = merged_folder / "merged_all.mp4"

    to_upload = []
    already_s = len([h for h in upload_history if h.get("type") == "short"])
    already_f = len([h for h in upload_history if h.get("type") == "full"])

    # Build Short List
    if upload_type in ("shorts", "both"):
        for path in shorts:
            if any(h.get("path") == path.name for h in upload_history): continue
            m = re.search(r"merged_(\d+)\.mp4", path.name)
            idx = int(m.group(1)) if m else 1
            part = idx + already_s
            title = title_template.format(username=display_name, date=date_fmt, part=part)
            to_upload.append(("short", path, title[:100]))

    # Build Full List
    if upload_type in ("full", "both", "long") and full_path.exists():
        if not any(h.get("path") == full_path.name for h in upload_history):
            batch = already_f + 1
            if custom_long_title:
                base = custom_long_title.replace("{username}", display_name).replace("{date}", date_fmt)
            else:
                base = title_template.format(username=display_name, date=date_fmt, part="1").replace(" | الجزء 1", "")
            full_title = f"{base} | الجزء {batch}" if batch > 1 else base
            to_upload.insert(0, ("full", full_path, full_title[:100])) # Process Full first

    if not to_upload:
        return {"success": True, "count": 0, "status": "Already uploaded."}

    # 2. Execution Loop
    army = []
    tdir = get_tokens_dir(user_id)
    if tdir.exists():
        tokens = sorted(tdir.glob("token*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        secrets = _get_client_secrets()
        for t in tokens:
            if is_token_usable(t, user_id):
                # Just add token, get_youtube_service will try match secrets
                army.append((t, None))

    if not army:
        return {"success": False, "error": "No valid soldiers in the Army of APIs."}

    uploaded = 0
    shorts_uploaded = 0
    fulls_uploaded = 0
    full_video_url = None
    shorts_to_process = []
    current_idx = 0

    for vid_type, path, title in to_upload:
        uploaded_this = False
        while not uploaded_this and current_idx < len(army):
            tok, sec_override = army[current_idx]
            try:
                youtube, err = get_youtube_service(channel_id=channel_id, token_path_override=tok)
                if err:
                    print(f"❌ Soldier {current_idx} failed: {err}")
                    current_idx += 1; continue

                print(f"🚀 Uploading {path.name} as '{title}'...")
                if progress_callback: progress_callback(f"رفع {uploaded+1}/{len(to_upload)}: {title}")
                
                # Metadata Build (Premium Template)
                hashtags = [t.replace("#","").strip() for t in custom_hashtags.split()] if custom_hashtags else []
                # Filter influencers (smart hashtags)
                if "ضاري" in display_name or "dari" in display_name.lower():
                    extra_h = "#ضاري_الفلاح #Dari #TeamFalcons"
                elif "أصيل" in display_name or "asel" in display_name.lower():
                    extra_h = "#أصيل_المبلع #Asel #المبلع"
                else:
                    extra_h = ""
                
                # Requested Template Links
                sup = "https://creators.sa/saudisnap"; tt = "https://www.tiktok.com/@dari_falah"
                
                if vid_type == "short":
                    # Shorts: Empty description, Hashtags in Title
                    desc = ""
                    tags = ["Shorts", "سنابات", display_name] + hashtags
                    # Append hashtags to title for Shorts
                    h_str = " #Shorts #سنابات " + " ".join([f"#{h}" for h in hashtags])
                    title = f"{title} {h_str}"[:100]
                else:
                    # Full Video: Premium Description, Clean Title
                    tags = ["سنابات", "تجميعة", display_name] + hashtags
                    desc = (
                        f"🔥 شاهدوا تجميعة أقوى وأحدث سنابات {display_name} لهذا اليوم!\n"
                        "استمتعوا بالمشاهدة ولا تنسوا دعمنا بالاشتراك وتفعيل جرس التنبيهات 🔔 ليصلكم كل جديد.\n\n"
                        f"💬 للدعم : {sup}\n"
                        f"📱 تابعونا على تيك توك: {tt}\n\n"
                        f"#Shorts #SaudiArabia #Dari #Saudi #Snapchat {extra_h} #Arabic\n"
                        f"#سنابات #تجميعة #{display_name.replace(' ','_')} " + " ".join([f"#{h}" for h in hashtags])
                    )
                
                body = {
                    "snippet": {"title": title, "description": desc, "tags": list(set(tags))[:15], "categoryId":"22"},
                    "status": {"privacyStatus": privacy}
                }
                
                # Publish staggered with safety buffer
                if publish_time and privacy == "private":
                    try:
                        base_t = datetime.strptime(publish_time, "%Y-%m-%dT%H:%M:%SZ")
                        # Use the video's index for staggering
                        offset_match = re.search(r"merged_(\d+)", path.name)
                        offset = int(offset_match.group(1)) if (vid_type=="short" and offset_match) else 0
                        staggered = base_t + timedelta(minutes=offset)
                        
                        # Safety Buffer: YouTube requires publishAt to be in the future.
                        # We ensure it's at least 5 mins from 'now' to allow for upload time.
                        now_utc = datetime.utcnow()
                        if staggered < now_utc + timedelta(minutes=5):
                            staggered = now_utc + timedelta(minutes=5 + offset)
                            
                        body["status"]["publishAt"] = staggered.strftime("%Y-%m-%dT%H:%M:%SZ")
                    except Exception as st_err:
                        print(f"⚠️ Error in staggering: {st_err}")

                # Upload
                with open(str(path), "rb") as vf:
                    media = MediaIoBaseUpload(vf, mimetype="video/mp4", resumable=True, chunksize=1024*1024)
                    resp = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
                
                v_id = resp.get("id")
                print(f"✅ Success! ID: {v_id}")

                if vid_type == "full":
                    full_video_url = f"https://youtu.be/{v_id}"; fulls_uploaded += 1
                    # Thumb handling
                    try:
                        t_path = merged_folder / f"thumb_{v_id}.jpg"
                        custom_thumb = kwargs.get("custom_thumb_path")
                        has_thumb = False
                        mime_type = "image/jpeg"
                        
                        if custom_thumb and os.path.exists(custom_thumb):
                            if progress_callback: progress_callback(f"استخدام الصورة المصغرة المخصصة للمهمة: {v_id}")
                            print(f"DEBUG: Found custom thumb at {custom_thumb}")
                            import shutil
                            shutil.copy2(custom_thumb, str(t_path))
                            has_thumb = True
                            
                            # Detect MIME type
                            ext = os.path.splitext(custom_thumb)[1].lower()
                            if ext == ".png": mime_type = "image/png"
                            elif ext == ".webp": mime_type = "image/webp"
                        else:
                            if progress_callback: progress_callback(f"توليد صورة مصغرة تلقائية لـ: {v_id}")
                            has_thumb = generate_full_video_thumbnail(str(path), str(t_path), display_name, date_str)
                            
                        if has_thumb and t_path.exists():
                            with open(str(t_path), "rb") as f:
                                youtube.thumbnails().set(
                                    videoId=v_id, 
                                    media_body=MediaIoBaseUpload(f, mimetype=mime_type)
                                ).execute()
                            print(f"✅ Thumbnail set for {v_id} (MIME: {mime_type})")
                        else:
                            print(f"⚠️ No thumbnail applied for {v_id}")
                            
                    except Exception as th_err:
                        print(f"❌ Thumbnail error for {v_id}: {th_err}")
                    
                    # Auto-Rename Part 1
                    if "الجزء 2" in title:
                        p1 = next((h for h in upload_history if h.get("type")=="full" and "الجزء" not in h.get("title","")), None)
                        if p1 and p1.get("id"):
                            try:
                                base_t = title_template.format(username=display_name, date=date_fmt, part="1").replace(" | الجزء 1","")
                                p1_title = f"{base_t} | الجزء 1"[:100]
                                # We MUST send the whole snippet to avoid wiping description/tags
                                p1_body = {
                                    "id": p1["id"],
                                    "snippet": {
                                        "title": p1_title,
                                        "description": desc,
                                        "tags": list(set(tags))[:15],
                                        "categoryId": "22"
                                    }
                                }
                                youtube.videos().update(part="snippet", body=p1_body).execute()
                                p1["title"] = p1_title
                            except: pass
                else:
                    shorts_uploaded += 1; shorts_to_process.append(v_id)

                # History & Archive
                arc = archive_dir / path.name
                if arc.exists(): arc = archive_dir / f"{path.stem}_{int(datetime.now().timestamp())}{path.suffix}"
                import shutil; shutil.copy2(str(path), str(arc))
                save_history({"id":v_id, "title":title, "type":vid_type, "path":path.name, "timestamp":str(datetime.now())})

                uploaded += 1; uploaded_this = True

            except Exception as e:
                msg = str(e).lower()
                print(f"❌ Soldier {current_idx} failed: {e}")
                if "quotaexceeded" in msg: update_token_status(tok, "cooldown", 24, user_id)
                elif "deleted_client" in msg or "invalid_grant" in msg: update_token_status(tok, "invalid", 0, user_id)
                current_idx += 1

    # 3. Post-Process (Related Video)
    if shorts_to_process:
        if not full_video_url:
            s_data = get_channel_videos_stats(channel_id, 5)
            if s_data.get("success") and s_data.get("videos"):
                for v in s_data["videos"]:
                    if v["id"] not in shorts_to_process: full_video_url = f"https://youtu.be/{v['id']}"; break
        
        if full_video_url:
            try:
                from webapp.youtube_studio_bot import attach_related_video
                for sid in shorts_to_process:
                    attach_related_video(sid, full_video_url)
            except Exception as e:
                print(f"⚠️ Error attaching related video: {e}")

    if to_upload and uploaded == 0:
        return {"success": False, "error": "لم يتم رفع أي فيديو. من المحتمل استنفاد الحصة (Quota) لجميع المفاتيح المتوفرة.", "count": 0, "shorts": 0, "fulls": 0}

    return {"success": True, "count": uploaded, "shorts": shorts_uploaded, "fulls": fulls_uploaded}


def upload_single_file(file_path, title, privacy="private", channel_id=None, progress_callback=None, publish_at=None, thumbnail_path=None):
    """Upload a single video file to YouTube."""
    if not os.path.isfile(file_path):
        return {"success": False, "error": "File not found"}

    youtube, err = get_youtube_service_for_channel(channel_id) if channel_id else get_youtube_service()
    if err:
        return {"success": False, "error": err}

    try:
        from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    except ImportError:
        return {"success": False, "error": "Missing google-api-python-client"}

    try:
        if publish_at:
            privacy = "private" # Scheduling requires private upload

        body = {
            "snippet": {"title": title, "description": "#Shorts #Snapchat", "tags": ["Shorts", "Snapchat"], "categoryId": "22"},
            "status": {"privacyStatus": privacy},
        }
        
        if publish_at:
            body["status"]["publishAt"] = publish_at

        with open(file_path, "rb") as video_file:
            media = MediaIoBaseUpload(video_file, mimetype="video/mp4", resumable=True, chunksize=1024 * 1024)
            if progress_callback:
                progress_callback(f"جاري الرفع: {title}")
            response = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        
        vid_id = response.get("id")
        
        # Upload thumbnail if available
        if vid_id and thumbnail_path and os.path.exists(thumbnail_path):
            try:
                if progress_callback:
                    progress_callback(f"جاري رفع الصورة المصغرة لـ: {title}")
                with open(thumbnail_path, "rb") as f:
                    youtube.thumbnails().set(
                        videoId=vid_id,
                        media_body=MediaIoBaseUpload(f, mimetype="image/jpeg")
                    ).execute()
            except Exception as thumb_err:
                print(f"Error uploading thumbnail for {vid_id}: {thumb_err}")

        return {"success": True, "url": f"https://www.youtube.com/watch?v={vid_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_channel_videos_stats(channel_id, max_results=20):
    """Get statistics for the most recent videos uploaded to a specific channel."""
    youtube, err = get_youtube_service_for_channel(channel_id) if channel_id else get_youtube_service()
    if err:
        return {"success": False, "error": err}
    
    try:
        # 1. Get channel's Uploads playlist ID
        channel_resp = youtube.channels().list(part="contentDetails,statistics", id=channel_id).execute()
        if not channel_resp.get("items"):
            return {"success": False, "error": "Channel not found"}
            
        uploads_playlist_id = channel_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        channel_stats = channel_resp["items"][0]["statistics"]
        
        # 2. Get videos in the Uploads playlist
        playlist_resp = youtube.playlistItems().list(
            part="snippet", 
            playlistId=uploads_playlist_id, 
            maxResults=max_results
        ).execute()
        
        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in playlist_resp.get("items", [])]
        
        if not video_ids:
            return {"success": True, "videos": [], "channel_stats": channel_stats}
            
        # 3. Get statistics for these videos
        videos_resp = youtube.videos().list(
            part="snippet,statistics", 
            id=",".join(video_ids)
        ).execute()
        
        videos = []
        for v in videos_resp.get("items", []):
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "published_at": v["snippet"]["publishedAt"],
                "views": v["statistics"].get("viewCount", "0"),
                "likes": v["statistics"].get("likeCount", "0"),
                "comments": v["statistics"].get("commentCount", "0"),
                "thumbnail": v["snippet"]["thumbnails"].get("medium", {}).get("url", "")
            })
            
        return {"success": True, "videos": videos, "channel_stats": channel_stats}
    except Exception as e:
        return {"success": False, "error": str(e)}
