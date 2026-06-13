import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Print all Jinja expressions for manual inspection
expressions = re.findall(r'\{\{.*?\}\}', content)
print("--- JINJA EXPRESSIONS ---")
for exp in expressions:
    print(exp)
print("--------------------------")

# 2. Fix known structural issues
# Find where dashboard-grid ends and move it to the real end of cards
# The grid starts at <div class="dashboard-grid">
# It should end before status-section

# Let's rebuild the main-content area properly
cards_pattern = r'<div class="dashboard-grid">.*?</div> <!-- End Dashboard Grid -->'
# Actually, I'll just rewrite the whole section from 141 to 681 carefully.

# Fix the specific "get" error if found
# If I see {{ schedule.hour }} and it's rendering a method, it might be because of a typo.
# I will change them to a safer form: session.get('schedule', {}).hour etc.
# But for now, let's just use try/get in JS context or better template logic.

# 3. Add missing icons
content = content.replace('<h2>رفع تيك توك</h2>', '<span class="badge">📱</span>\n                    <h2>رفع تيك توك</h2>')
content = content.replace('<h2>تنظيف</h2>', '<span class="badge">🧹</span>\n                    <h2>تنظيف</h2>')

# 4. Fix the </div> issue
# I see line 457: </div> followed by 458: </section>
# This is inside Batch Pipeline Card? No, Batch Pipeline ends at 456.
# So 457/458 are EXTRA. I'll remove them.
content = content.replace('</section>\n                </div>\n            </section>', '</section>', 1)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)
