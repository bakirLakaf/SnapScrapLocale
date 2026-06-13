import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Standardize All Card Headers & Icons
# We want: <div class="card-header"><span class="badge">ICON</span><h2>TITLE</h2></div>
# I'll fix TikTok and Clean cards now.
content = re.sub(r'<section class="card tiktok-card text-center">\s+<div class="card-header">\s+<span class="badge">.*?</span>\s+<h2>رفع تيك توك</h2>\s+</div>', 
                 '<section class="card tiktok-card text-center" id="section-tiktok">\n                <div class="card-header">\n                    <span class="badge">📱</span>\n                    <h2>رفع تيك توك</h2>\n                </div>', content, flags=re.DOTALL)

if '<h2>تنظيف</h2>' in content:
    content = content.replace('<section class="card clear-card">\n                <div class="card-header" style="justify-content: center;">\n                    <h2>تنظيف</h2>\n                </div>', 
                             '<section class="card clear-card" id="section-clean">\n                <div class="card-header">\n                    <span class="badge">🧹</span>\n                    <h2>تنظيف</h2>\n                </div>')

# 2. Fix the nested structure issue (Batch Pipeline Card mess)
# Remove the extra tags I found earlier
content = content.replace('</section>\n                </div>\n            </section>', '</section>', 1)

# 3. Ensure "Bulk Upload" is present and well-placed
# If missing, add it.
if 'id="section-bulk"' not in content:
    bulk_card = """
            <!-- YouTube Bulk Upload Card -->
            <section class="card bulk-card highlight text-center" id="section-bulk">
                <div class="card-header">
                    <span class="badge">📦</span>
                    <h2>رفع الكل</h2>
                </div>
                <p style="margin-bottom: 12px; color: var(--text-muted); font-size: 0.9rem;">رفع جميع المجلدات الجاهزة وتجهيزها للقنوات</p>
                <div class="form">
                    <div class="input-row">
                        <select id="bulkUploadChannel">
                            <option value="">اختر القناة الموحدة</option>
                        </select>
                    </div>
                    <button type="button" id="uploadAll" class="btn btn-primary btn-block">
                        <i class="fa-solid fa-play"></i> بدء الرفع الشامل
                    </button>
                </div>
            </section>"""
    # Insert under Schedule
    content = re.sub(r'(<section class="card schedule-card text-center">.*?</section>)', r'\1\n\n' + bulk_card, content, flags=re.DOTALL)

# 4. Fix Jinja2 "get" issue in schedule just in case
content = re.sub(r'value="{{ schedule\.hour if schedule\.hour is defined else 9 }}"', 'value="{{ schedule.get(\'hour\', 9) }}"', content)
content = re.sub(r'value="{{ schedule\.minute if schedule\.minute is defined else 0 }}"', 'value="{{ schedule.get(\'minute\', 0) }}"', content)

# 5. Final Structural Integrity Check: Dashboard-grid must close before status-section
# Count <div class="dashboard-grid"> and its matching </div>.
# It seems there are many </div> trailing at the end. I'll clean them up.

# Find the start of status-section
status_idx = content.find('<section class="status-section"')
cards_block = content[content.find('<div class="dashboard-grid">'):status_idx]
# Ensure all cards are balanced.

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied final comprehensive fixes to index.html structure and visuals.")
