import os
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError

# TikTok Session Profile
SESSION_PATH = os.path.join(os.environ.get("USERPROFILE", ""), "SnapScrap_TikTok_Session")

def ensure_page(context):
    """Ensure the page is open and ready."""
    if not context.pages:
        page = context.new_page()
    else:
        page = context.pages[0]
    return page

def upload_to_tiktok(video_path, caption):
    """Automate the upload of a video to TikTok Studio."""
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return False

    with sync_playwright() as p:
        # We try to launch a persistent context (the one the user logged into)
        browser = p.chromium.launch_persistent_context(
            SESSION_PATH,
            headless=False, # TikTok Studio is detection-heavy, headless=False is safer
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = ensure_page(browser)
        
        try:
            print(f"🚀 Navigating to TikTok Studio Upload...")
            # Use 'domcontentloaded' instead of 'load' for much faster navigation
            page.goto("https://www.tiktok.com/tiktokstudio/upload?from=upload", wait_until="domcontentloaded", timeout=60000)
            
            # 1. Upload the video
            print(f"📤 Selecting video: {video_path}")
            # TikTok's input is often hidden; wait for it to be attached, not necessarily visible
            file_input = page.wait_for_selector('input[type="file"]', state="attached", timeout=60000)
            file_input.set_input_files(video_path)
            
            # 2. Wait for the upload/processing to start and the form to appear
            print("⏳ Waiting for processing and caption area...")
            
            # Dismiss any popups like "Turn on automatic content checks?"
            # We want them OFF as per user request.
            try:
                # Look for the 'Cancel' or 'X' on the prompt
                cancel_btn = page.locator('button:has-text("Cancel"), button:has-text("إلغاء"), .jsx-3940428579')
                if cancel_btn.count() > 0:
                    print("🧹 Dismissing 'Content Checks' prompt (keeping them OFF)...")
                    cancel_btn.first.click()
                    time.sleep(1)
            except:
                pass

            # We wait for the caption box (Draft.js editor)
            # Both selectors are common, but .public-DraftEditor-content is very specific to Draft.js
            caption_selector = '.public-DraftEditor-content, div[role="textbox"][contenteditable="true"]'
            print(f"🔍 Waiting for caption box with selector: {caption_selector}")
            caption_box = page.wait_for_selector(caption_selector, timeout=60000)
            
            # 3. Enter Caption
            print(f"📝 Entering caption: {caption}")
            # Focus the box first
            caption_box.click()
            time.sleep(1)
            
            # Draft.js often needs keyboard interaction
            page.keyboard.down("Control")
            page.keyboard.press("a")
            page.keyboard.up("Control")
            page.keyboard.press("Backspace")
            time.sleep(0.5)
            
            # Type the new caption slowly
            page.keyboard.type(caption, delay=70)
            time.sleep(2)
            
            # 4. Handle Toggles (Ensure they are OFF)
            print("⚙️ Checking Settings (Copyright/Content checks)...")
            try:
                # If these are ON, they might slow down the Post button activation.
                # We turn them OFF as per user request.
                toggles = page.locator('button[role="switch"][aria-checked="true"]')
                for i in range(toggles.count()):
                    print(f"📉 Turning OFF toggle {i+1}...")
                    toggles.nth(i).click()
                    time.sleep(0.5)
            except:
                pass

            # 5. Wait for the Video to reach 100% Uploaded
            print("⏳ Monitoring upload progress (Waiting for purely 100%)...")
            # The ONLY reliable indicator that upload is 100% done is when the "Cancel" button 
            # next to the progress bar turns into a "Replace" (or "استبدال") button, or the size (MB) appears.
            
            replace_selectors = [
                 'button:has-text("Replace")',
                 'button:has-text("استبدال")',
                 # The SVG icon inside the replace button
                 '.tiktok-upload-success-icon',
                 # The file size indicator like (32.14MB). Playwright string regex.
                 'text=/.*MB.*/' 
            ]
            
            found_uploaded = False
            for step in range(120): # 10 minutes total (5s * 120)
                try:
                    for sel in replace_selectors:
                        elements = page.query_selector_all(sel)
                        for el in elements:
                            if el.is_visible():
                                print(f"✅ Upload 100% confirmed by: {sel}")
                                found_uploaded = True
                                break
                        if found_uploaded:
                            break
                except Exception as e:
                    print(f"⚠️ Error checking selectors: {e}")
                
                if found_uploaded:
                    break
                
                # Check for progress string to reassure us
                if step % 3 == 0:
                    print("... Still uploading, waiting for 100% completion indicator ...")
                
                time.sleep(5)
            
            if not found_uploaded:
                print("⚠️ Warning: Did not clearly see the 'Replace' button, but proceeding carefully...")

            # 6 & 7. Wait for Post button and click until successful
            print("📣 Searching for Post button (نشر) and attempting to click...")
            # Scroll to the bottom first to ensure footer is rendered/visible
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            # Turn off any remaining active toggles (Copyright/Content Check) before posting
            print("⚙️ Ensuring all Checks are turned OFF...")
            try:
                for toggle_sel in ['button[role="switch"][aria-checked="true"]', 'input[type="checkbox"]:checked']:
                    active_toggles = page.query_selector_all(toggle_sel)
                    for t in active_toggles:
                        try:
                            t.scroll_into_view_if_needed()
                            t.click(force=True)
                            time.sleep(1)
                            # Handle confirmation popups like "Stop copyright checking?"
                            for confirm_sel in ['button:has-text("Stop")', 'button:has-text("إيقاف")', 'button:has-text("Confirm")', 'button:has-text("تأكيد")']:
                                confirm_btns = page.query_selector_all(confirm_sel)
                                for cb in confirm_btns:
                                    if cb.is_visible():
                                        cb.click(force=True)
                                        time.sleep(0.5)
                            print("📉 Turned OFF an active toggle and confirmed.")
                        except: pass
            except: pass

            success_indicators = [
                'text="Manage your posts"',
                'text="uploaded to TikTok"',
                'text="تم الرفع"',
                'text="إدارة المنشورات"',
                'text="View profile"',
                'text="عرض الملف الشخصي"'
            ]

            confirm_found = False
            for attempt in range(60): # 5 minutes total (60 * 5s)
                # --- Step A: Check if successfully posted ---
                # Check URL first (Most reliable)
                if "upload" not in page.url.lower() or "tiktokstudio/content" in page.url.lower():
                    print("🎉 Success confirmed via URL change!")
                    confirm_found = True
                    break

                for selector in success_indicators:
                    try:
                        elements = page.query_selector_all(selector)
                        for el in elements:
                            if el.is_visible():
                                print(f"🎉 Success confirmed via: {selector}")
                                confirm_found = True
                                break
                    except:
                        pass
                    if confirm_found: break
                
                if confirm_found:
                    break
                
                # --- Step B: Check for 'Post now' popup ---
                try:
                    # 'Post now', 'النشر الآن', 'Post anyway'
                    for sel in ['button:has-text("Post now")', 'button:has-text("النشر الآن")', 'button:has-text("Post anyway")']:
                        btns = page.query_selector_all(sel)
                        for btn in btns:
                            if btn.is_visible():
                                print(f"⚠️ 'Continue to post' popup detected! Clicking {sel}...")
                                btn.evaluate('node => node.click()')
                                time.sleep(3)
                except:
                    pass

                # --- Step C: Try to find and click the main Post button ---
                # We specifically look for exact or close matches to avoid clicking other things
                post_button_selectors = [
                    'button:has-text("Post")',
                    'button:has-text("نشر")',
                    'div[role="button"]:has-text("Post")',
                    'div[role="button"]:has-text("نشر")'
                ]
                
                try:
                    for sel in post_button_selectors:
                        btns = page.query_selector_all(sel)
                        for btn in btns:
                            # Avoid matching "Manage your posts" by ensuring it's not a huge string
                            text = btn.inner_text().strip().lower()
                            if text in ["post", "نشر"]:
                                if btn.is_visible() and not btn.is_disabled():
                                    btn.scroll_into_view_if_needed()
                                    # Press Escape to dismiss any lingering popups or tooltips covering the button
                                    page.keyboard.press("Escape")
                                    time.sleep(1) # Breathe before clicking
                                    print(f"🎯 Clicking POST button natively via {sel} (Text: {text})")
                                    # Use native playwright click WITHOUT force to see what intercepts it
                                    btn.click(timeout=5000, force=False)
                                    time.sleep(4) # Wait to see if it triggers navigation/success
                                    break # Break the btn loop to re-check success
                except Exception as e:
                    print(f"⚠️ Click attempt skipped: {e}")
                    pass
                
                print(f"⏳ Waiting for Post button to process or success indicator ({attempt*5}s)...")
                time.sleep(5)

            if not confirm_found:
                raise Exception("Could not verify success after clicking Post for 5 minutes.")

            print("✅ Video is officially posted. Safe to close.")
            time.sleep(5)
            # Add a bit more time just to ensure TikTok registers the completion
            return True

        except Exception as e:
            print(f"❌ TikTok Upload Error: {e}")
            # Take a debug screenshot
            try:
                page.screenshot(path=f"debug_tiktok_error_{int(time.time())}.png")
            except:
                pass
            return False
        finally:
            browser.close()


if __name__ == "__main__":
    # Test call
    # upload_to_tiktok("test.mp4", "Test Caption #fyp")
    pass
