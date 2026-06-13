import os
import re

html_path = r'w:\AntiGravity\SnapScrap_Local\webapp\templates\index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Navigation Bar at the top of app-content
nav_html = """
            <!-- Quick Navigation Header -->
            <nav class="quick-nav">
                <div class="nav-scroll-container">
                    <a href="#section-add" class="nav-link"><i class="fa-solid fa-user-plus"></i> إضافة</a>
                    <a href="#section-download" class="nav-link"><i class="fa-solid fa-download"></i> سريع</a>
                    <a href="#section-merge" class="nav-link"><i class="fa-solid fa-object-group"></i> دمج</a>
                    <a href="#section-schedule" class="nav-link"><i class="fa-solid fa-clock"></i> جدولة</a>
                    <a href="#section-upload" class="nav-link"><i class="fa-solid fa-upload"></i> يوتيوب</a>
                    <a href="#section-pipeline" class="nav-link"><i class="fa-solid fa-bolt"></i> متكامل</a>
                    <a href="#section-batch" class="nav-link"><i class="fa-solid fa-fire"></i> شامل</a>
                    <a href="#section-army" class="nav-link"><i class="fa-solid fa-shield-halved"></i> الجيش</a>
                    <a href="#section-tiktok" class="nav-link"><i class="fa-brands fa-tiktok"></i> تيك توك</a>
                    <a href="#section-clean" class="nav-link"><i class="fa-solid fa-trash-can"></i> تنظيف</a>
                </div>
            </nav>
"""

# Insert nav inside app-content, after the Stripe banner if it exists, or at the start
if '<div class="banner-stripe">' in content:
    content = content.replace('</div>\n\n            <div class="dashboard-grid">', '</div>\n' + nav_html + '\n            <div class="dashboard-grid">', 1)
else:
    content = content.replace('<div class="dashboard-grid">', nav_html + '\n            <div class="dashboard-grid">', 1)

# 2. Add IDs to cards
# Add Accounts
content = content.replace('<!-- Add Accounts Card -->\n            <section class="card"', '<!-- Add Accounts Card -->\n            <section id="section-add" class="card"', 1)
# Quick Downloader (or similar)
content = content.replace('<!-- Quick Downloader Card -->\n            <section class="card"', '<!-- Quick Downloader Card -->\n            <section id="section-download" class="card"', 1)
# Merge
content = content.replace('<!-- Manual Merge Card -->\n            <section class="card"', '<!-- Manual Merge Card -->\n            <section id="section-merge" class="card"', 1)
# Schedule
content = content.replace('<!-- Schedule Setting Card -->\n            <section class="card"', '<!-- Schedule Setting Card -->\n            <section id="section-schedule" class="card"', 1)
# Upload
content = content.replace('<!-- YouTube Simple Upload Card -->\n            <section class="card"', '<!-- YouTube Simple Upload Card -->\n            <section id="section-upload" class="card"', 1)
# Pipeline
content = content.replace('<!-- Full Pipeline Card -->\n            <section class="card', '<!-- Full Pipeline Card -->\n            <section id="section-pipeline" class="card', 1)
# Batch Pipeline
content = content.replace('<!-- Batch Pipeline Card -->\n            <section class="card', '<!-- Batch Pipeline Card -->\n            <section id="section-batch" class="card', 1)
# Army
content = content.replace('<!-- Unified YouTube Army Card -->\n            <section class="card', '<!-- Unified YouTube Army Card -->\n            <section id="section-army" class="card', 1)
# TikTok
content = content.replace('<!-- TikTok Card -->\n            <section class="card"', '<!-- TikTok Card -->\n            <section id="section-tiktok" class="card"', 1)
# Clean
content = content.replace('<!-- Clear batch Card -->\n            <section class="card"', '<!-- Clear batch Card -->\n            <section id="section-clean" class="card"', 1)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully added Navigation Header and section IDs to index.html.")
