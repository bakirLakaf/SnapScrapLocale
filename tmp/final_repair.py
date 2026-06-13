import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix checkoutStripe
stripe_js = """
            <script>
                function checkoutStripe() {
                    fetch('/api/create-checkout-session', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    }).then(res => res.json()).then(data => {
                        if (data.checkout_url) window.location.href = data.checkout_url;
                        else alert('Error starting session');
                    }).catch(err => console.error(err));
                }
            </script>
"""
stripe_pattern = re.compile(r'\s*<script>\s*function checkoutStripe.*?<\/script>', re.DOTALL)
content = stripe_pattern.sub(stripe_js, content)

# 2. Fix broken CSS in Quick Downloader card
content = content.replace('style="margin-bottom: 24px; background: rgba; border-color: var;">', 
                          'class="card text-center card-compact" style="margin-bottom: 24px;">')

# 3. Ensure "Baqat Majania" banner has correct styles
content = content.replace('style="background: linear-gradient; padding: 18px 24px; border-radius: 16px; margin-bottom: 24px; color: white; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 25px rgba;">',
                          'class="upgrade-banner premium-glow"')

# 4. Fix any remaining "btn btn-primary btn-block" that might have lost padding or look XP
# (Actually most are fine now)

# 5. One more check for (Selected) or other English text
content = content.replace('(Selected)', '')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully applied Final Luxury Repair to index.html")
