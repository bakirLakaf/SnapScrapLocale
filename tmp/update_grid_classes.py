import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Apply card-full to Army section
# Looking for '<!-- Unified YouTube Army Card -->'
content = content.replace('<!-- Unified YouTube Army Card -->', '<!-- Unified YouTube Army Card -->\n            <section class="card army-card highlight card-full text-center">', 1)
# Remove the old section tag that was there before
content = content.replace('<section class="card army-card highlight text-center">', '', 1)

# 2. Apply card-full to Full Pipeline if desired
content = content.replace('<!-- Full Pipeline Card -->', '<!-- Full Pipeline Card -->\n            <section class="card pipeline-card text-center card-full pink-gradient">', 1)
content = content.replace('<section class="card pipeline-card text-center pink-gradient">', '', 1)

# 3. Ensure TikTok is also maybe full or stays 2-column? 
# The user wants "side by side", so let's keep it 2-column.

# 4. Cleanup any leftover card-compact classes inside the grid area
# We already did this in the previous cleanup script, but just in case.
content = content.replace(' card-compact', '')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated grid classes for optimal layout.")
