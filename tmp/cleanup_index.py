import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix Schedule Jinja Bug
content = content.replace('value="{{ schedule.get }}"', 'value="{{ schedule.hour }}"', 1)
content = content.replace('value="{{ schedule.get }}"', 'value="{{ schedule.minute }}"', 1)

# 2. Fix onclick handlers
# deleteAllTokens -> deleteAllTokens()
content = content.replace('onclick="deleteAllTokens"', 'onclick="deleteAllTokens()"')
# submitSecretUpload -> submitSecretUpload()
content = content.replace('onchange="submitSecretUpload"', 'onchange="submitSecretUpload()"')
# fix broken pipeline calls
content = re.sub(r'onclick="window\.handlePipeline && window\.handlePipeline"', 'onclick="handlePipeline()"', content)
content = re.sub(r'onclick="window\.runBatchPipeline && window\.runBatchPipeline"', 'onclick="runBatchPipeline()"', content)
# fix document.getElementById.click (Line 483)
content = content.replace('onclick="document.getElementById.click"', 'onclick="document.getElementById(\'secretFileInput\').click()"')

# 3. Clean up duplicate class attributes
# Finding patterns like class="card" class="card..."
content = re.sub(r'class="card"\s+class="card', 'class="card', content)

# 4. Remove card-compact from grid items to avoid margin:auto centering issues
# The user wants them side-by-side, which grid handles. manual centering fights grid.
content = content.replace(' card-compact', '')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully cleaned up index.html and fixed JS/Jinja bugs.")
