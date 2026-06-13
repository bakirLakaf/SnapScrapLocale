import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix Full Pipeline Actions (Individual)
# Shorts
content = re.sub(
    r'<button type="button" class="btn btn-accent btn-block btn-lg" onclick="handlePipeline\(\)">\s+<i class="fa-solid fa-play"></i> تشغيل متكاملة',
    r'<button type="button" class="btn btn-accent btn-block btn-lg" onclick="handlePipeline(\'shorts\', this)">\n                            <i class="fa-solid fa-bolt"></i> تشغيل Shorts ⚡',
    content
)
# Long
content = re.sub(
    r'<button type="button" class="btn btn-secondary btn-block" onclick="handlePipeline\(\)">\s+<i class="fa-solid fa-clapperboard"></i> تشغيل متكاملة',
    r'<button type="button" class="btn btn-secondary btn-block" onclick="handlePipeline(\'long\', this)">\n                            <i class="fa-solid fa-clapperboard"></i> تشغيل فيديو طويل 🎬',
    content
)
# Both
content = re.sub(
    r'<button type="button" class="btn btn-primary btn-block" onclick="handlePipeline\(\)">\s+<i class="fa-solid fa-wand-magic-sparkles"></i> تشغيل متكاملة',
    r'<button type="button" class="btn btn-primary btn-block" onclick="handlePipeline(\'both\', this)">\n                            <i class="fa-solid fa-fire"></i> تشغيل الشامل (الاثنين) 🔥',
    content
)
# Prepare
content = re.sub(
    r'<button type="button" class="btn btn-bot btn-block" onclick="handlePipeline\(\)">\s+<i class="fa-solid fa-box-archive"></i> تحميل ودمج فقط',
    r'<button type="button" class="btn btn-bot btn-block" onclick="handlePipeline(\'prepare\', this)">\n                            <i class="fa-solid fa-box-archive"></i> تحميل ودمج فقط 📦',
    content
)

# 2. Fix Batch Pipeline Actions (Global)
# Batch Shorts
content = re.sub(
    r'<button type="button" id="btnBatchPipeline" class="btn btn-accent btn-block btn-lg" onclick="runBatchPipeline\(\)">\s+<i class="fa-solid fa-bolt"></i> تشغيل الكل',
    r'<button type="button" id="btnBatchPipeline" class="btn btn-accent btn-block btn-lg" onclick="runBatchPipeline(\'shorts\')">\n                            <i class="fa-solid fa-bolt"></i> تشغيل الكل (Shorts) ⚡',
    content
)
# Batch Long
content = re.sub(
    r'<button type="button" id="btnBatchPipelineLong" class="btn btn-secondary btn-block" onclick="runBatchPipeline\(\)">\s+<i class="fa-solid fa-film"></i> تشغيل الكل',
    r'<button type="button" id="btnBatchPipelineLong" class="btn btn-secondary btn-block" onclick="runBatchPipeline(\'long\')">\n                            <i class="fa-solid fa-film"></i> تشغيل الكل (طويل) 🎬',
    content
)
# Batch Both
content = re.sub(
    r'<button type="button" id="btnBatchPipelineBoth" class="btn btn-primary btn-block" onclick="runBatchPipeline\(\)">\s+<i class="fa-solid fa-fire"></i> تشغيل الكل',
    r'<button type="button" id="btnBatchPipelineBoth" class="btn btn-primary btn-block" onclick="runBatchPipeline(\'both\')">\n                            <i class="fa-solid fa-fire"></i> العملية الكبرى (الاثنين) 🔥',
    content
)
# Batch Prepare
content = re.sub(
    r'<button type="button" id="btnBatchPipelinePrepare" class="btn btn-bot btn-block" onclick="runBatchPipeline\(\)">\s+<i class="fa-solid fa-box-archive"></i> دمج وتجهيز الكل فقط',
    r'<button type="button" id="btnBatchPipelinePrepare" class="btn btn-bot btn-block" onclick="runBatchPipeline(\'prepare\')">\n                            <i class="fa-solid fa-box-archive"></i> دمج وتجهيز الكل فقط 📦',
    content
)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully differentiated all pipeline buttons with unique labels and correct onclick handlers.")
