import os

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Repair TikTok onclick
content = content.replace('onclick="window.open"', 'onclick="window.open(\'https://www.tiktok.com/upload\', \'_blank\')"')

# 2. Reconstruct the main JS block (Army actions)
# We find the start of the block and the end.
js_block = """
                <script>
                    async function deleteAllTokens() {
                        if (!confirm('تحذير: هذا سيحذف جميع المفاتيح (Tokens) و Client Secrets للمشروع بالكامل. هل أنت متأكد؟')) return;
                        try {
                            const res = await fetch('/api/youtube/delete_tokens', {
                                method: 'POST',
                                headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content }
                            });
                            const data = await res.json();
                            if (data.ok) {
                                alert(`تم حذف ${data.deleted} ملف توكن بنجاح! سيتم تحديث الصفحة.`);
                                window.location.reload();
                            } else {
                                alert('خطأ أثناء الحذف: ' + data.error);
                            }
                        } catch (err) {
                            console.error(err);
                            alert('حدث خطأ بالاتصال');
                        }
                    }

                    function submitSecretUpload() {
                        const fileInput = document.getElementById('secretFileInput');
                        if (!fileInput.files.length) return;

                        const formData = new FormData();
                        for (let i = 0; i < fileInput.files.length; i++) {
                            formData.append('secret_files', fileInput.files[i]);
                        }

                        fetch('/api/youtube/upload_client_secret', {
                            method: 'POST',
                            headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content },
                            body: formData
                        })
                            .then(res => res.json())
                            .then(data => {
                                if (data.ok) {
                                    alert(`تم رفع ${fileInput.files.length} ملف (Client Secret) بنجاح!`);
                                    window.location.reload();
                                } else {
                                    alert('خطأ: ' + (data.error || "تأكد من اختيار ملف صحیح"));
                                }
                                fileInput.value = "";
                            })
                            .catch(err => {
                                console.error(err);
                                alert('حدث خطأ أثناء الرفع');
                            });
                    }

                    function showTokenUpload(channelId) {
                        document.getElementById('tokenChannelId').value = channelId;
                        document.getElementById('tokenFileInput').click();
                    }

                    async function submitTokenUpload() {
                        const fileInput = document.getElementById('tokenFileInput');
                        if (!fileInput.files || !fileInput.files.length) return;

                        const channelId = document.getElementById('tokenChannelId').value;
                        let successCount = 0;
                        let errorCount = 0;

                        for (let i = 0; i < fileInput.files.length; i++) {
                            const formData = new FormData();
                            formData.append('channel_id', channelId);
                            formData.append('token_file', fileInput.files[i]);
                            try {
                                const res = await fetch('/api/youtube/upload_token', {
                                    method: 'POST',
                                    body: formData
                                });
                                const data = await res.json();
                                if (data.ok) successCount++;
                                else errorCount++;
                            } catch (err) {
                                console.error(err);
                                errorCount++;
                            }
                        }

                        if (errorCount === 0) {
                            alert(`تمت إضافة ${successCount} جنود احتياطية بنجاح! 🛡️`);
                        } else {
                            alert(`تمت إضافة ${successCount} بنجاح، وفشل ${errorCount} مفتاح.`);
                        }

                        fileInput.value = "";
                        window.location.reload();
                    }
                </script>
"""

# Find the start of the broken block
start_marker = '<script>'
# Since there are multiple <script> tags, we need the one inside the army section.
# We'll search for 'async function deleteAllTokens'
import re
pattern = re.compile(r'\s*<script>\s*async function deleteAllTokens.*?async function submitTokenUpload.*?<\/script>', re.DOTALL)
content = pattern.sub(js_block, content)

# 3. Final verification of the Footer script
footer_js = """
    <script src="{{ url_for('static', filename='app.js') }}?v=1.6"></script>
    <script>
        setTimeout(() => {
            if (window.initApp) {
                console.log('App initialized');
            }
        }, 1000);
    </script>
"""
footer_pattern = re.compile(r'\s*<script src="{{ url_for }}.*?<\/script>\s*<script>.*?<\/script>', re.DOTALL)
content = footer_pattern.sub(footer_js, content)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully repaired JS and url_for in index.html")
