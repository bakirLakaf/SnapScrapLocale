import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Standardize Card Headers to match new "Row" CSS
# Add Accounts
content = re.sub(
    r'<div class="card-header" style="justify-content: center;">\s+<div class="header-icons">\s+<span class="icon">(\S+)</span>\s+<h2>(.*?)</h2>\s+</div>\s+</div>',
    r'<div class="card-header">\n                    <span class="badge">\1</span>\n                    <h2>\2</h2>\n                </div>',
    content, flags=re.DOTALL
)

# Generic Card Headers (others)
header_patterns = [
    (r'<h2>تنزيل سريع</h2>\s+<p>دون إضافة للقائمة</p>', r'<span class="badge">📥</span>\n                    <h2>تنزيل سريع</h2>'),
    (r'<h2>دمج الفيديوهات</h2>', r'<span class="badge">🎬</span>\n                    <h2>دمج الفيديوهات</h2>'),
    (r'<h2>العملية الشاملة</h2>', r'<span class="badge">🔥</span>\n                    <h2>العملية الشاملة</h2>'),
    (r'<div class="header-main">\s+<span class="badge">⚡🔥</span>\s+<h2>العملية الشاملة</h2>\s+</div>', r'<span class="badge">🔥</span>\n                    <h2>العملية الشاملة</h2>'),
]

for pattern, replacement in header_patterns:
    content = re.sub(r'<div class="card-header" style="justify-content: center;">\s+' + pattern + r'\s+</div>', 
                     r'<div class="card-header">\n                    ' + replacement + r'\n                </div>', content, flags=re.DOTALL)

# Fix "Schedule" specifically
content = re.sub(
    r'<div class="card-header" style="justify-content: center;">\s+<div class="header-icons">\s+<span class="icon">⏰</span>\s+<h2>(.*?)</h2>\s+</div>\s+</div>',
    r'<div class="card-header">\n                    <span class="badge">⏰</span>\n                    <h2>\1</h2>\n                </div>',
    content, flags=re.DOTALL
)

# Fix "Upload" specifically
content = re.sub(
    r'<div class="card-header" style="justify-content: center;">\s+<div class="header-icons">\s+<span class="icon icon-yt">▶</span>\s+<h2>(.*?)</h2>\s+</div>\s+</div>',
    r'<div class="card-header">\n                    <span class="badge">▶</span>\n                    <h2>\1</h2>\n                </div>',
    content, flags=re.DOTALL
)

# Fix "Bulk Upload" (رفع الكل) specifically
content = re.sub(
    r'<section class="card bulk-card highlight text-center">\s+<div class="card-header" style="justify-content: center;">\s+<div class="header-icons">\s+<span class="icon icon-yt">▶</span>\s+<h2>رفع الكل</h2>\s+</div>\s+<p>رفع جميع المجلدات الجاهزة وتوزيعها على القنوات</p>\s+</div>',
    r'<section class="card bulk-card highlight text-center" id="section-bulk">\n                <div class="card-header">\n                    <span class="badge">📦</span>\n                    <h2>رفع الكل</h2>\n                </div>',
    content, flags=re.DOTALL
)

# 2. Fix Tabs class in Upload
content = content.replace('<div class="upload-tabs justify-center">', '<div class="tabs-header">', 1)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully standardized card headers and updated tabs structure.")
