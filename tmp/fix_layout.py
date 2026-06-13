import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix the broken Stripe Banner (around line 95)
# We find the pattern of the broken banner and replace it with a clean one.
# It was between {% if current_user.subscription_tier == 'free' %} and the end of the script tag.

new_banner = """
            <!-- Stripe Upgrade Banner -->
            {% if current_user.subscription_tier == 'free' %}
            <div class="upgrade-banner premium-glow">
                <div class="upgrade-info">
                    <h3 class="upgrade-title">
                        <i class="fa-solid fa-crown" style="color: #fbbf24;"></i> الباقة المجانية
                    </h3>
                    <p class="upgrade-desc">أنت حالياً تستخدم الباقة المجانية بحد أقصى 5 حسابات. للوصول لعدد أكبر وجدولة أسرع وجيش API، قم بالترقية للـ Pro.</p>
                </div>
                <button onclick="checkoutStripe()" class="btn btn-primary upgrade-btn">
                    ترقية إلى Pro
                </button>
            </div>
            
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
            {% endif %}
"""

# Try searching for the broken block
banner_pattern = re.compile(r'<!-- Stripe Upgrade Banner -->\s*\{% if current_user.subscription_tier == \'free\' %\}.*?\{% endif %\}', re.DOTALL)
content = banner_pattern.sub(new_banner, content)

# 2. Wrap Sections in dashboard-grid
# The cards start after the banner (Integrated Process is actually part of the cards usually)
# We want to wrap from "تنزيل قصة فورياً" or "إضافة حسابات" onwards if they aren't already.

# Find the start of the first card after the banner
# Let's wrap from line 124 (Quick Downloader) to line 691 (Clear Batch)
grid_start = '<div class="dashboard-grid">'
grid_end = '</div> <!-- End Dashboard Grid -->'

# We need to find the correct insertion points.
# Insertion 1: Before "Quick Downloader" or "Add Accounts"
# Let's find '<!-- Quick Downloader -->' or its section
content = content.replace('<!-- Quick Downloader -->', grid_start + '\n            <!-- Quick Downloader -->')

# Insertion 2: After the 'clear-card' section
# The previous multi_replace already added one, let's make sure it's correct.
# If it's not there, we add it.
if grid_end not in content:
   content = content.replace('            </section>\n\n            <section class="status-section"', '            </section>\n            ' + grid_end + '\n\n            <section class="status-section"')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully fixed HTML layout and applied grid.")
