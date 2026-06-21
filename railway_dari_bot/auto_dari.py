#!/usr/bin/env python3
"""
auto_dari.py — بوت يومي مستقل لـ Railway (Cron).

يقوم بالتسلسل التالي مرة واحدة ثم ينطفئ:
  1. فك حزمة التوكنات/الأسرار (TOKENS_BUNDLE) إلى أماكنها على الـ Volume.
  2. تحميل سنابات حساب ضاري الفلاح (dary_1256).
  3. دمج الفيديو الطويل فقط (merged_all.mp4) عبر --long-only.
  4. رفع merged_all.mp4 فقط على القناة المستهدفة مع جدولة النشر.
  5. حذف كل مجلدات الحساب (merged + not merged) بعد نجاح الرفع.

ملاحظة: هذا الملف لا يلمس أي كود موجود في المشروع — يستدعيه فقط كـ "صندوق أدوات".
كل الإعدادات تُقرأ من متغيرات البيئة (انظر README.md).
"""
import base64
import io
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# جذر المشروع = المجلد الأب لمجلد هذا السكربت (railway_dari_bot/)
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ── الإعدادات (متغيرات بيئة قابلة للتحكم) ──────────────────────────────────
SNAP_USERNAME = os.environ.get("SNAP_USERNAME", "dary_1256")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "UCg5d06i5nWe5FihOOilC-Kg")
INFLUENCER_NAME = os.environ.get("INFLUENCER_NAME", "ضاري الفلاح")
USER_ID = os.environ.get("SNAPSCRAP_USER_ID", "1")

# الجزائر = UTC+1 (بدون توقيت صيفي)
ALGERIA_TZ = timezone(timedelta(hours=1))
# ساعة النشر المجدول بتوقيت الجزائر (الافتراضي 23:00)
PUBLISH_HOUR_DZ = int(os.environ.get("PUBLISH_HOUR_DZ", "23"))
PUBLISH_MINUTE_DZ = int(os.environ.get("PUBLISH_MINUTE_DZ", "0"))
# privacy: عند الجدولة يجب أن تكون private (شرط يوتيوب)
DELETE_AFTER_UPLOAD = os.environ.get("DELETE_AFTER_UPLOAD", "1") == "1"
# حد خيوط ffmpeg لتفادي نفاد الذاكرة (OOM) على حاويات Railway المحدودة
FFMPEG_THREADS = os.environ.get("FFMPEG_THREADS", "2")
# إعادة تحميل قسرية: تتجاهل سجل التتبّع (download_history.json) وتُعيد تنزيل سنابات
# اليوم من جديد. مفيدة لإعادة معالجة تاريخ سبق التعامل معه (الافتراضي: معطّل).
FORCE_RELOAD = os.environ.get("FORCE_RELOAD", "0") == "1"
# أصغر حجم مقبول للفيديو المدمج (أقل من ذلك = تالف/ناقص)
MIN_VALID_BYTES = 100 * 1024

STORIES_DIR = REPO_ROOT / "stories"
TOKENS_DIR = STORIES_DIR / "tokens"
CLIENT_SECRETS_DIR = REPO_ROOT / "webapp" / "client_secrets"


def log(msg):
    print(f"[{datetime.now(ALGERIA_TZ).strftime('%Y-%m-%d %H:%M:%S')} DZ] {msg}", flush=True)


# ── 1. فك حزمة التوكنات من TOKENS_BUNDLE ───────────────────────────────────
def restore_tokens_bundle():
    """
    يفك TOKENS_BUNDLE (tar.gz مرمّز base64) إلى:
      - stories/tokens/*.json
      - webapp/client_secrets/*.json
    التوكنات: تُستخرج فقط إن لم تكن موجودة على الـ Volume (للحفاظ على المحدّثة).
    الأسرار (client_secrets): تُستخرج دائماً (ثابتة وغير موجودة على الـ Volume).
    """
    bundle = os.environ.get("TOKENS_BUNDLE", "").strip()
    if not bundle:
        log("⚠️ لا يوجد TOKENS_BUNDLE في البيئة — أعتمد على ما هو موجود على الـ Volume.")
        return

    TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    CLIENT_SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        raw = base64.b64decode(bundle)
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
            members = tar.getmembers()
            extracted_tokens, extracted_secrets = 0, 0
            for m in members:
                if not m.isfile():
                    continue
                name = m.name.replace("\\", "/")
                data = tar.extractfile(m).read()

                if name.startswith("tokens/"):
                    dest = TOKENS_DIR / Path(name).name
                    if dest.exists():
                        continue  # حافظ على التوكن المحدّث على الـ Volume
                    dest.write_bytes(data)
                    extracted_tokens += 1
                elif name.startswith("client_secrets/"):
                    dest = CLIENT_SECRETS_DIR / Path(name).name
                    dest.write_bytes(data)  # دائماً
                    extracted_secrets += 1

            log(f"✅ تم فك الحزمة: {extracted_tokens} توكن جديد، {extracted_secrets} ملف أسرار.")
    except Exception as e:
        log(f"❌ فشل فك TOKENS_BUNDLE: {e}")
        raise


# ── 2. ضمان وجود إعدادات الحساب (الاسم الحقيقي للمؤثر) ──────────────────────
def ensure_account_config():
    """يتأكد أن إعدادات الحساب تحوي influencer_name الصحيح حتى تظهر الهاشتاقات والاسم."""
    try:
        from webapp.app import get_accounts, save_accounts
    except Exception as e:
        log(f"⚠️ تعذّر تحميل إعدادات الحساب: {e}")
        return

    try:
        accounts = get_accounts(USER_ID)
        found = None
        for a in accounts:
            if a.get("username") == SNAP_USERNAME:
                found = a
                break
        if found is None:
            accounts.append({
                "username": SNAP_USERNAME,
                "checked": True,
                "avatar": None,
                "influencer_name": INFLUENCER_NAME,
            })
        elif found.get("influencer_name") != INFLUENCER_NAME:
            found["influencer_name"] = INFLUENCER_NAME
        save_accounts(accounts, USER_ID)
        log(f"✅ إعدادات الحساب جاهزة: {SNAP_USERNAME} → {INFLUENCER_NAME}")
    except Exception as e:
        log(f"⚠️ تعذّر حفظ إعدادات الحساب: {e}")


# ── 3. حساب وقت النشر المجدول (UTC) ────────────────────────────────────────
def compute_publish_at():
    """يُرجع وقت النشر بصيغة يوتيوب (UTC) عند الساعة المحددة بتوقيت الجزائر اليوم."""
    now_dz = datetime.now(ALGERIA_TZ)
    target_dz = now_dz.replace(hour=PUBLISH_HOUR_DZ, minute=PUBLISH_MINUTE_DZ, second=0, microsecond=0)
    # إن كان الوقت قد فات اليوم، انقله لليوم التالي
    if target_dz <= now_dz + timedelta(minutes=5):
        target_dz += timedelta(days=1)
    target_utc = target_dz.astimezone(timezone.utc)
    return target_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), target_dz


# ── حد خيوط ffmpeg (تفادي OOM دون تعديل merge_videos.py) ────────────────────
def setup_ffmpeg_thread_limit():
    """
    ينشئ wrapper باسم ffmpeg في مقدمة PATH يحقن -threads للحد من استهلاك الذاكرة.
    السبب: merge_videos.py يستدعي ffmpeg من PATH دون تحديد -threads، فيختار x264
    عدد خيوط = عدد المعالجات (60 على Railway) → نفاد الذاكرة وقتل العملية (SIGKILL 9).
    لا يلمس أي كود أصلي — مجرد اعتراض لاستدعاء ffmpeg.
    """
    if sys.platform == "win32":
        return  # غير مطلوب محلياً على ويندوز
    real = shutil.which("ffmpeg")
    if not real:
        log("⚠️ لم يُعثر على ffmpeg في PATH — تخطّي حد الخيوط.")
        return
    # غلاف Python: يحقن -threads قبل ملف الإخراج مباشرة (خيار إخراج) ليحد من
    # المُرمِّز x264 — وهو مصدر استهلاك الذاكرة. وضعه قبل -i يحد المُفكِّك فقط (لا يكفي).
    # استدعاءات الفحص (مثل -version) تمر دون تعديل.
    content = (
        f"#!{sys.executable}\n"
        "import os, sys\n"
        f"REAL = {real!r}\n"
        f"T = {FFMPEG_THREADS!r}\n"
        "args = sys.argv[1:]\n"
        "passthrough = ('-version', '-buildconf', '-encoders', '-decoders',\n"
        "               '-formats', '-codecs', '-h', '-help', '-L', '-licenses')\n"
        "if args and args[0] in passthrough:\n"
        "    os.execv(REAL, [REAL] + args)\n"
        "if args:\n"
        "    # أدرج -threads قبل آخر وسيط (ملف الإخراج) ليُطبَّق على المُرمِّز\n"
        "    args = args[:-1] + ['-threads', T] + [args[-1]]\n"
        "os.execv(REAL, [REAL] + args)\n"
    )
    # مرشّحات قابلة للتنفيذ — نتجنّب /tmp لأنه قد يكون noexec على Railway
    candidates = [
        REPO_ROOT / ".ffwrap_bin",
        Path.home() / ".ffwrap_bin",
        Path("/usr/local/ffwrap_bin"),
    ]
    for bin_dir in candidates:
        try:
            bin_dir.mkdir(parents=True, exist_ok=True)
            wrapper = bin_dir / "ffmpeg"
            wrapper.write_text(content, encoding="utf-8")
            os.chmod(wrapper, 0o755)
            # تحقّق فعلي أن الموقع قابل للتنفيذ (يكشف noexec)
            test = subprocess.run([str(wrapper), "-version"], capture_output=True, text=True)
            if test.returncode == 0:
                os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
                log(f"🧵 تم تفعيل حد خيوط ffmpeg = {FFMPEG_THREADS} (عبر {bin_dir})")
                return
            log(f"⚠️ {bin_dir} غير قابل للتنفيذ (noexec؟) — أجرّب موقعاً آخر.")
        except Exception as e:
            log(f"⚠️ تعذّر إنشاء الغلاف في {bin_dir}: {e}")
            continue
    log("⚠️ تعذّر تفعيل غلاف حد الخيوط — قد يحدث نفاد ذاكرة أثناء الدمج.")


# ── التحقق من سلامة الفيديو المدمج ──────────────────────────────────────────
def validate_video(path):
    """يُرجع True إن كان الفيديو مكتملاً وقابلاً للقراءة (له مدة/moov)."""
    if not path.exists() or path.stat().st_size < MIN_VALID_BYTES:
        return False
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return True  # تعذّر التحقق العميق — نكتفي بفحص الحجم
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        dur = (r.stdout or "").strip()
        return r.returncode == 0 and dur not in ("", "N/A") and float(dur) > 0
    except Exception:
        return False


# ── 4. تشغيل أمر فرعي ──────────────────────────────────────────────────────
def run_cmd(cmd, label, extra_env=None):
    log(f"▶️ {label}: {' '.join(str(c) for c in cmd)}")
    env = os.environ.copy()
    env["SNAPSCRAP_LANG"] = "en"
    env["SNAPSCRAP_USER_ID"] = str(USER_ID)
    env["PYTHONUNBUFFERED"] = "1"
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env)
    if proc.returncode != 0:
        log(f"⚠️ {label} انتهى برمز {proc.returncode}")
    return proc.returncode == 0


# ── 5. الحذف بعد الرفع ─────────────────────────────────────────────────────
def cleanup_account(date_str):
    for kind in ("merged", "not merged"):
        folder = STORIES_DIR / kind / SNAP_USERNAME / date_str
        if folder.exists():
            try:
                shutil.rmtree(folder)
                log(f"🗑️ حُذف: {folder.relative_to(REPO_ROOT)}")
            except Exception as e:
                log(f"⚠️ تعذّر حذف {folder}: {e}")
        # نظّف مجلد الحساب الأب إن أصبح فارغاً
        parent = STORIES_DIR / kind / SNAP_USERNAME
        if parent.exists() and not any(parent.iterdir()):
            try:
                parent.rmdir()
            except Exception:
                pass


# ── التسلسل الرئيسي ────────────────────────────────────────────────────────
def main():
    log("🚀 بدء بوت ضاري الفلاح اليومي على Railway")
    log(f"   الحساب: {SNAP_USERNAME} | القناة: {CHANNEL_ID}")

    # 0. استرجاع التوكنات + حد خيوط ffmpeg
    restore_tokens_bundle()
    ensure_account_config()
    setup_ffmpeg_thread_limit()

    # تاريخ السنابات = اليوم بتوقيت الجزائر.
    # نمرّره صراحةً إلى SnapScrap.py (--date) ليطابق مجلّد التحميل مجلّد الدمج،
    # وإلا فعند تجاوز منتصف الليل يختلف تاريخ الحاوية (UTC) عن تاريخ الجزائر.
    date_str = datetime.now(ALGERIA_TZ).strftime("%Y-%m-%d")
    log(f"📅 تاريخ السنابات: {date_str}")

    # 1. التحميل
    dl_env = None
    if FORCE_RELOAD:
        dl_env = {"SNAPSCRAP_FORCE_RELOAD": "1"}
        log("🔄 وضع إعادة التحميل القسري مفعّل — سيتم تجاهل سجل التتبّع وإعادة تنزيل سنابات اليوم.")
    ok = run_cmd(
        [sys.executable, str(REPO_ROOT / "SnapScrap.py"), SNAP_USERNAME, "--date", date_str],
        "تحميل السنابات",
        extra_env=dl_env,
    )
    if not ok:
        log("❌ فشل التحميل — إيقاف.")
        sys.exit(1)

    # 2. الدمج (الفيديو الطويل فقط)
    merge_ok = run_cmd(
        [sys.executable, str(REPO_ROOT / "merge_videos.py"), SNAP_USERNAME, date_str, "--long-only"],
        "دمج merged_all.mp4",
    )

    merged_all = STORIES_DIR / "merged" / SNAP_USERNAME / date_str / "merged_all.mp4"

    # 🛡️ بوابة أمان: لا رفع ولا حذف إلا إذا نجح الدمج وكان الفيديو سليماً
    if not merge_ok:
        log("❌ فشل الدمج (رمز خروج غير صفري) — إيقاف دون رفع أو حذف. المصادر محفوظة لإعادة المحاولة غداً.")
        sys.exit(1)
    if not merged_all.exists():
        log("❌ لم يُنشأ merged_all.mp4 (لا سنابات اليوم؟) — إيقاف دون رفع/حذف.")
        sys.exit(1)
    if not validate_video(merged_all):
        log("❌ الفيديو المدمج تالف أو ناقص (moov مفقود/حجم صغير) — إيقاف دون رفع/حذف. المصادر محفوظة.")
        sys.exit(1)
    log(f"✅ تم التحقق من سلامة الفيديو المدمج ({round(merged_all.stat().st_size / (1024*1024), 1)} MB).")

    # 3. الرفع (merged_all فقط + جدولة)
    publish_at, target_dz = compute_publish_at()
    log(f"⏰ النشر المجدول: {target_dz.strftime('%Y-%m-%d %H:%M')} الجزائر ({publish_at} UTC)")

    try:
        from webapp.youtube_service import upload_from_folder
        result = upload_from_folder(
            SNAP_USERNAME,
            date_str,
            privacy="private",          # إجباري عند الجدولة
            upload_type="full",         # merged_all فقط
            channel_id=CHANNEL_ID,
            publish_at=publish_at,
            user_id=USER_ID,
            progress_callback=lambda m: log(f"   📤 {m}"),
        )
    except Exception as e:
        log(f"❌ خطأ أثناء الرفع: {e}")
        sys.exit(1)

    if not result.get("success"):
        log(f"❌ فشل الرفع: {result.get('error')}")
        sys.exit(1)

    log(f"✅ تم الرفع بنجاح: {result.get('count', 0)} فيديو.")

    # 4. الحذف
    if DELETE_AFTER_UPLOAD:
        cleanup_account(date_str)
    else:
        log("ℹ️ تخطّي الحذف (DELETE_AFTER_UPLOAD=0)")

    log("🎉 اكتملت العملية بنجاح. إيقاف.")


if __name__ == "__main__":
    main()
