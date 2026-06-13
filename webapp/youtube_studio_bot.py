import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILE_DIR = BASE_DIR / "stories" / "config" / "chrome_profile"

def attach_related_video(short_id, target_video_query):
    """
    Automates YouTube Studio to attach a related video to a Short.
    Uses robust selectors and browser auto-recovery.
    """
    if not PROFILE_DIR.exists():
        print("❌ بطاقة الدخول غير موجودة. الرجاء تشغيل setup_bot.py أولاً.")
        return False

    print(f"🤖 [BOT] بدء تعيين الفيديو المرتبط للشورت: {short_id}")

    with sync_playwright() as p:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        browser = None
        page = None

        def ensure_page():
            nonlocal browser, page
            if not browser or not browser.is_connected():
                for attempt in range(3):
                    try:
                        # Cleanup old instances
                        os.system('wmic process where "commandline like \'%chrome_profile%\'" delete >nul 2>&1')
                        time.sleep(2)
                        browser = p.chromium.launch_persistent_context(
                            user_data_dir=str(PROFILE_DIR),
                            headless=False,
                            user_agent=user_agent,
                            args=["--disable-blink-features=AutomationControlled", "--mute-audio", "--no-sandbox"],
                            timeout=60000
                        )
                        page = browser.pages[0] if browser.pages else browser.new_page()
                        page.set_default_timeout(60000)
                        return True
                    except Exception as e:
                        print(f"⚠️ فشل تشغيل المتصفح ({attempt+1}): {e}")
                        time.sleep(5)
                return False
            return True

        try:
            if not ensure_page(): return False
            
            edit_url = f"https://studio.youtube.com/video/{short_id}/edit"
            page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)
            
            # Scroll to find the Related video section
            page.evaluate("window.scrollTo(0, 800)") 
            time.sleep(2)

            # Click Related video button
            clicked = False
            for sel in ["#related-video-button", "text='Related video'", "text='الفيديو المرتبط'", "text='None'", "text='لا يوجد'"]:
                try:
                    loc = page.locator(sel).first
                    if loc.is_visible(timeout=3000):
                        loc.click(force=True)
                        clicked = True
                        break
                except: continue
            
            if not clicked:
                print("   ❌ لم أتمكن من العثور على زر إضافة الفيديو المرتبط.")
                return False

            # Extract video ID from URL (e.g. https://youtu.be/ABC123 → ABC123)
            import re as _re
            search_query = target_video_query
            m = _re.search(r"(?:youtu\.be/|[?&]v=|/videos/)([A-Za-z0-9_-]{11})", target_video_query)
            if m:
                search_query = m.group(1)
                print(f"   🔍 البحث بمعرف الفيديو: {search_query}")
            else:
                print(f"   🔍 البحث بالعنوان: {search_query}")

            # Search by video ID for precise matching
            found_result = False
            for s_sel in ["input#search-yours", "input#search-input", "input[type='text']", "input"]:
                try:
                    s_loc = page.locator(s_sel).first
                    if s_loc.is_visible(timeout=3000):
                        s_loc.click()
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        page.keyboard.type(search_query, delay=50)
                        page.keyboard.press("Enter")
                        time.sleep(4)  # give more time for results to load
                        
                        # Click first Result
                        for r_sel in ["ytcp-video-list-cell-video", "ytcp-item-list-video-cell", "ytcp-video-row", "[test-id='video-list-cell']"]:
                            try:
                                r_loc = page.locator(r_sel).first
                                if r_loc.is_visible(timeout=5000):
                                    r_loc.click()
                                    found_result = True
                                    break
                            except: continue
                        if found_result: break
                except: continue
            
            if not found_result:
                print("   ❌ لم يتم العثور على الفيديو في نتائج البحث.")
                return False
            
            # Save
            save = "ytcp-button#save-button"
            page.wait_for_selector(save, timeout=10000)
            if not page.is_disabled(save):
                page.click(save)
                # Wait for save state
                for _ in range(10):
                    if page.is_disabled(save): break
                    time.sleep(1)
                print("✅ تم الربط والحفظ بنجاح!")
            else:
                print("⚠️ الفيديو مربوط بالفعل.")
            
            browser.close()
            return True
            
        except Exception as e:
            print(f"   ❌ حدث خطأ: {e}")
            if browser: browser.close()
            return False

if __name__ == "__main__":
    # For testing only
    if len(sys.argv) == 3:
        attach_related_video(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python youtube_studio_bot.py <SHORT_VIDEO_ID> <FULL_VIDEO_URL>")
