import re
import os

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Polish "Add Accounts" card
content = content.replace('class="card add-card"', 'class="card add-card text-center card-compact"')
content = content.replace('class="card-header"', 'class="card-header" style="justify-content: center;"')
# Bulk button fix - more robust regex
content = re.sub(r'<button type="button" id="btnBulkAdd".*?>إضافة جملة / حساب واحد</button>', 
                 '<button type="button" id="btnBulkAdd" class="btn-bulk-add">إضافة جملة / حساب واحد</button>', 
                 content, flags=re.DOTALL)
# Refresh icon fix
content = content.replace('(Daily Picks) <span id="refreshSuggested" style="cursor:pointer; font-size:0.9rem; margin-right:5px;">↻</span>', 
                          ' <span id="refreshSuggested" class="btn-refresh"><i class="fa-solid fa-rotate"></i></span>')
content = content.replace('(Daily Picks) <span id="refreshSuggested" style="cursor:pointer; font-size:0.9rem; margin-right:5px;">↻</span>', 
                          ' <span id="refreshSuggested" class="btn-refresh"><i class="fa-solid fa-rotate"></i></span>')

# 2. Cleanup Headers (Remove English)
content = content.replace('(YouTube Army)', '')
content = content.replace('(Manual Bridge)', '')
content = content.replace('(Daily Picks)', '')
content = content.replace('(ACTIVE)', '')
content = content.replace('(IDLE)', '')

# 3. Compact long cards
# YouTube Army
content = content.replace('class="card army-card highlight"', 'class="card army-card highlight card-compact text-center"')
# TikTok Upload
content = content.replace('class="card tiktok-card highlight"', 'class="card tiktok-card highlight card-compact text-center"')
# Cleanup (تنظيف)
content = content.replace('class="card cleaning-card"', 'class="card cleaning-card card-compact text-center"')

# 4. Fix Duplicate/XP elements in YouTube Upload
# Look for the YouTube Upload section and fix its rows
content = content.replace('<h2>YouTube Upload</h2>', '<h2>رفع يوتيوب</h2>')
content = content.replace('↻ مجلدات', '<i class="fa-solid fa-rotate"></i>')
content = content.replace('↻ قنوات', '<i class="fa-solid fa-rotate"></i>')

# 5. Fix alignment in YouTube Army header
content = content.replace('style="flex-direction: column; align-items: flex-start;"', 'style="flex-direction: column; align-items: center;"')

# 6. Global Language icons cleanup
# Replace English abbreviations or titles that look like XP labels
content = content.replace('<h3>YouTube Upload</h3>', '<h3>رفع يوتيوب</h3>')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully applied luxury polish to index.html")
