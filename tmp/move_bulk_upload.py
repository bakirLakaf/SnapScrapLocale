import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Identify and remove Bulk Upload card from its current position
bulk_card_pattern = r'<!-- YouTube Bulk Upload Card -->\s+<section class="card bulk-card highlight text-center" id="section-bulk">.*?</section>'
bulk_card_match = re.search(bulk_card_pattern, content, flags=re.DOTALL)

if bulk_card_match:
    bulk_card_html = bulk_card_match.group(0)
    content = content.replace(bulk_card_html, '')
    
    # 2. Insert it after the Schedule section
    schedule_end_tag = '</section> <!-- End of Schedule -->' # I'll add this marker or find the real end
    # Finding the end of the Schedule section
    schedule_pattern = r'<!-- Schedule Setting Card -->\s+<section id="section-schedule" class="card schedule-card text-center">.*?</section>'
    content = re.sub(schedule_pattern, r'\g<0>\n\n            ' + bulk_card_html, content, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully moved Bulk Upload card to fill the gap under Schedule.")
