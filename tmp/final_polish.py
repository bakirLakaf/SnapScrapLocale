import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix Escaped Single Quotes (the backslashes)
content = content.replace("\\'", "'")

# 2. Fix Jinja2 dictionary access (The .get issue)
# Check for common mistakes like {{ schedule.hour }} if it should be .get
# Or {{ schedule.get }} without ()
content = re.sub(r'value="{{ schedule\.hour }}"', 'value="{{ schedule.hour if schedule.hour is defined else 9 }}"', content)
content = re.sub(r'value="{{ schedule\.minute }}"', 'value="{{ schedule.minute if schedule.minute is defined else 0 }}"', content)
# Ensure any other .get calls are correct (though grep didn't find them, better safe)

# 3. Handle the "Bulk Upload" Card Relocation properly
# First, let's find it if it still exists (maybe as 'bulk-card')
bulk_card_pattern = r'<!-- YouTube Bulk Upload Card -->.*?<section class="card bulk-card highlight text-center".*?</section>'
bulk_card_match = re.search(bulk_card_pattern, content, flags=re.DOTALL)

if bulk_card_match:
    bulk_card_html = bulk_card_match.group(0)
    # Remove it from its current position
    content = content.replace(bulk_card_html, '')
    # Insert it under the Schedule card
    # Find the end of schedule card
    schedule_pattern = r'<!-- Schedule Setting Card -->.*?<section id="section-schedule" class="card schedule-card text-center">.*?</section>'
    content = re.sub(schedule_pattern, r'\g<0>\n\n            ' + bulk_card_html, content, flags=re.DOTALL)
else:
    # If it was accidentally deleted, let's re-create it under schedule
    new_bulk_card = """
            <!-- YouTube Bulk Upload Card -->
            <section class="card bulk-card highlight text-center" id="section-bulk">
                <div class="card-header">
                    <span class="badge">📦</span>
                    <h2>رفع الكل</h2>
                </div>
                <p style="margin-bottom: 15px; color: var(--text-muted);">رفع جميع المجلدات الجاهزة وتوزيعها على القنوات</p>
                <div class="form">
                    <div class="input-row">
                        <select id="bulkUploadChannel">
                            <option value="">اختر القناة</option>
                        </select>
                    </div>
                    <button type="button" id="uploadAll" class="btn btn-primary btn-block">
                        <i class="fa-solid fa-play"></i> بدء الرفع الشامل
                    </button>
                    <p id="bulkUploadStatus" style="margin-top: 10px; font-size: 0.9rem;"></p>
                </div>
            </section>"""
    schedule_pattern = r'<!-- Schedule Setting Card -->.*?<section id="section-schedule" class="card schedule-card text-center">.*?</section>'
    content = re.sub(schedule_pattern, r'\g<0>\n\n            ' + new_bulk_card, content, flags=re.DOTALL)

# 4. Standardize Card Headers Row layout again (just in case some were missed)
# Ensure badge and h2 are in a card-header row
content = re.sub(r'<div class="card-header" style="justify-content: center;">\s+<div class="header-main">\s+<span class="badge">(.*?)</span>\s+<h2>(.*?)</h2>\s+</div>',
                 r'<div class="card-header">\n                    <span class="badge">\1</span>\n                    <h2>\2</h2>', content, flags=re.DOTALL)

# Final Polish on Tabs design in HTML
content = content.replace('<div class="tabs-header">', '<div class="tabs-header" style="margin-bottom: 2rem;">', 1)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully cleaned up index.html, fixed Jinja/JS errors, and repositioned cards.")
