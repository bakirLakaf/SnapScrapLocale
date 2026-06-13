# هيكل مشروع SnapScrap

## تنظيم الملفات

```
SnapScrap.py/
├── webapp/                    # تطبيق الويب (Flask)
│   ├── app.py                 # نقطة الدخول + API
│   ├── youtube_service.py     # رفع يوتيوب + قائمة القنوات
│   ├── templates/
│   │   └── index.html         # القالب الرئيسي
│   └── static/
│       ├── style.css          # التنسيقات
│       └── app.js             # منطق الواجهة
│
├── SnapScrap.py               # تنزيل السنابات (سكريبت أساسي)
├── merge_videos.py            # دمج الفيديوهات (Shorts / كامل)
├── upload_youtube_shorts.py   # رفع يوتيوب (سطر أوامر)
├── download_tracker.py        # تتبع التنزيلات
├── batch_processor.py         # معالجة دفعات
├── daily_automation.py        # أتمتة يومية
├── snapscrap_gui.py           # واجهة حاسوب (اختياري)
│
├── gui_config.json            # إعدادات (chunk_size, title_template)
├── webapp_config.json         # حسابات + جدولة (يُنشأ تلقائياً)
├── requirements.txt           # متطلبات الحاسوب
├── requirements_web.txt       # متطلبات تطبيق الويب
├── run_web.bat                # تشغيل الويب
├── run.bat                    # تشغيل سطر الأوامر
├── build_exe.py               # بناء EXE
└── FEATURES_AND_NOTES.md      # الميزات والملاحظات
```

## مجلدات يتم إنشاؤها أثناء التشغيل

| المجلد | الوظيفة |
|--------|---------|
| `username/YYYY-MM-DD/` | سنابات منسخة (مثل `dary_1256/2026-02-16/`) |
| `username/YYYY-MM-DD/merged/` | فيديوهات مدمجة (`merged_1.mp4`, `merged_all.mp4`) |
| `uploads/` | ملفات مؤقتة عند رفع ملف من الويب |
| `build/`, `dist/` | مخرجات PyInstaller |

## ملفات التكوين (يُنشأ تلقائياً أو يُستثنى من Git)

- `webapp_config.json` — حسابات السناب + الجدولة
- `token.json` — رمز يوتيوب (بعد الربط)
- `client_secret.json` — من Google Cloud Console

## تشغيل تطبيق الويب

```bash
pip install -r requirements_web.txt
python webapp/app.py
# أو: run_web.bat
```

## API الرئيسية

| المسار | الوظيفة |
|--------|---------|
| `GET /` | الصفحة الرئيسية |
| `GET/POST /api/accounts` | الحسابات |
| `POST /api/download` | تنزيل حساب واحد |
| `POST /api/download-selected` | تنزيل المحدد |
| `POST /api/merge` | دمج (merge_mode: shorts\|full\|both) |
| `POST /api/upload` | رفع من مجلد |
| `POST /api/upload-file` | رفع ملف |
| `POST /api/upload-all` | رفع كل المجلدات |
| `POST /api/clear-batch` | مسح مجلد |
| `GET /api/merged-folders` | قائمة المجلدات المدمجة |
| `GET /api/youtube/channels` | قنوات يوتيوب |
| `GET /api/task/<id>` | حالة المهمة |
