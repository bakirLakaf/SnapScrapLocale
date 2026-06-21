#!/usr/bin/env python3
"""
seed_tokens.py — أداة محلية (تُشغَّل على جهازك فقط، ليست على Railway).

تضغط كل توكنات اليوتيوب وملفات الأسرار في حزمة tar.gz مرمّزة base64،
ثم تطبعها / تحفظها في ملف لتنسخها داخل متغير البيئة TOKENS_BUNDLE على Railway.

الاستخدام:
    python railway_dari_bot/seed_tokens.py
    # → يُنشئ railway_dari_bot/tokens_bundle.txt  (انسخ محتواه إلى TOKENS_BUNDLE)

يشمل:
    stories/tokens/*.json            → tokens/
    webapp/client_secrets/*.json     → client_secrets/
"""
import base64
import io
import sys
import tarfile
from pathlib import Path

# إصلاح طباعة Unicode على كونسول ويندوز
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKENS_DIR = REPO_ROOT / "stories" / "tokens"
CLIENT_SECRETS_DIR = REPO_ROOT / "webapp" / "client_secrets"
OUTPUT = Path(__file__).resolve().parent / "tokens_bundle.txt"


def add_dir(tar, src_dir: Path, arc_prefix: str):
    count = 0
    if not src_dir.exists():
        print(f"⚠️ غير موجود: {src_dir}")
        return 0
    for p in sorted(src_dir.glob("*.json")):
        if not p.is_file():
            continue
        tar.add(str(p), arcname=f"{arc_prefix}/{p.name}")
        count += 1
    return count


def main():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        n_tokens = add_dir(tar, TOKENS_DIR, "tokens")
        n_secrets = add_dir(tar, CLIENT_SECRETS_DIR, "client_secrets")

    if n_tokens == 0 and n_secrets == 0:
        print("❌ لم يُعثر على أي توكنات أو أسرار. تأكد أنك في المجلد الصحيح.")
        return

    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    OUTPUT.write_text(encoded, encoding="utf-8")

    size_kb = len(encoded) / 1024
    print(f"✅ تم تجميع {n_tokens} توكن + {n_secrets} ملف أسرار.")
    print(f"   الحجم المرمّز: {size_kb:.1f} KB")
    print(f"   حُفظ في: {OUTPUT}")
    print()
    print("📋 الخطوة التالية:")
    print("   1. افتح الملف tokens_bundle.txt وانسخ كل محتواه.")
    print("   2. في Railway → Variables → أضف متغيراً اسمه TOKENS_BUNDLE وألصق المحتوى.")
    print("   ⚠️ لا ترفع tokens_bundle.txt إلى git (مضاف إلى .gitignore).")


if __name__ == "__main__":
    main()
