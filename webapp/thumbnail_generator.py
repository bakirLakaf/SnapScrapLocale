import os
import sys
import cv2
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
from pathlib import Path
import datetime

# For Arabic shaping
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC_SHAPER = True
except ImportError:
    HAS_ARABIC_SHAPER = False

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = r"C:\Windows\Fonts\arial.ttf"

def generate_full_video_thumbnail(video_path, output_path, username, date_str):
    """
    Extracts the first frame of the video and adds a custom yellow slanted box with Arabic text.
    """
    if not os.path.exists(video_path):
        print(f"❌ الفيديو غير موجود: {video_path}")
        return False

    # 1. Extract first frame using OpenCV
    cap = cv2.VideoCapture(video_path)
    success, frame = cap.read()
    if not success:
        print("❌ فشل استخراج الفريم الأول من الفيديو.")
        cap.release()
        return False
    
    # Convert BGR to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    cap.release()

    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Prepare texts
    # If the username contains spaces or Arabic, use it as is. Otherwise format it as a username.
    if " " in username or any("\u0600" <= c <= "\u06FF" for c in username):
        display_name = username
    else:
        display_name = username.replace("_", " ").title()
    # Main title
    main_text = f"سنابات {display_name} | {date_str} 🔥"
    # Call to action text
    cta_text = "لا تنسى الإشتراك و اللايك"

    def process_arabic(text):
        if HAS_ARABIC_SHAPER:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        return text

    bidi_main = process_arabic(main_text)
    bidi_cta = process_arabic(cta_text)

    if not HAS_ARABIC_SHAPER:
        print("⚠️ تنبيه: مكتبات تحسين الخط العربي مفقودة. قد لا يظهر النص بشكل صحيح.")

    # 2. Add boxes
    # Font settings
    try:
        font_size_main = 60
        font_size_cta = 45
        font_main = ImageFont.truetype(FONT_PATH, font_size_main)
        font_cta = ImageFont.truetype(FONT_PATH, font_size_cta)
    except Exception:
        font_main = ImageFont.load_default()
        font_cta = ImageFont.load_default()

    # -- YELLOW BOX (Main Title) --
    box_width = int(width * 0.75)
    box_height = 120
    box_x = (width - box_width) // 2
    box_y = height // 2 - 100 # Moved up slightly
    
    yellow_box = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 0))
    y_draw = ImageDraw.Draw(yellow_box)
    y_draw.rectangle([0, 0, box_width, box_height], fill=(255, 255, 0)) # Yellow
    
    # Draw title
    t_bbox = y_draw.textbbox((0, 0), bidi_main, font=font_main)
    tw, th = t_bbox[2] - t_bbox[0], t_bbox[3] - t_bbox[1]
    y_draw.text(((box_width - tw) // 2, (box_height - th) // 2 - 10), bidi_main, font=font_main, fill=(0, 0, 0))
    
    # Rotate and paste
    rotated_yellow = yellow_box.rotate(4, expand=True, resample=Image.BICUBIC)
    img.paste(rotated_yellow, (box_x, box_y), rotated_yellow)

    # -- RED BOX (CTA) --
    cta_box_width = int(box_width * 0.8)
    cta_box_height = 80
    cta_x = (width - cta_box_width) // 2
    cta_y = box_y + box_height + 10 # Right below yellow box
    
    red_box = Image.new('RGBA', (cta_box_width, cta_box_height), (0, 0, 0, 0))
    r_draw = ImageDraw.Draw(red_box)
    r_draw.rectangle([0, 0, cta_box_width, cta_box_height], fill=(255, 0, 0)) # Red
    
    # Draw CTA text
    c_bbox = r_draw.textbbox((0, 0), bidi_cta, font=font_cta)
    cw, ch = c_bbox[2] - c_bbox[0], c_bbox[3] - c_bbox[1]
    r_draw.text(((cta_box_width - cw) // 2, (cta_box_height - ch) // 2 - 5), bidi_cta, font=font_cta, fill=(255, 255, 255))
    
    # Rotate slightly differently for "organic" feel or same
    rotated_red = red_box.rotate(4, expand=True, resample=Image.BICUBIC)
    img.paste(rotated_red, (cta_x, cta_y), rotated_red)

    # 3. Save resulting thumbnail
    img.save(output_path, quality=95)
    print(f"✅ تم إنشاء الصورة المصغرة بنجاح: {output_path}")
    return True

if __name__ == "__main__":
    # Test only
    if len(sys.argv) > 1:
        v_path = sys.argv[1]
        o_path = sys.argv[2]
        u_name = sys.argv[3]
        d_str = sys.argv[4]
        generate_full_video_thumbnail(v_path, o_path, u_name, d_str)
    else:
        print("Usage: python thumbnail_generator.py <video_path> <output_path> <username> <date_str>")
