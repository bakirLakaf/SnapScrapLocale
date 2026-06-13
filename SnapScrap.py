#!/usr/bin/env python3
"""SnapScrap - Download public Snapchat stories."""
__author__ = "https://codeberg.org/allendema"

import json
import os
import subprocess
import sys
import time
from datetime import date
from time import sleep

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from download_tracker import is_downloaded, mark_downloaded

# Fix Unicode print on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# English output if Arabic appears broken in CMD (use --en or set SNAPSCRAP_LANG=en)
USE_EN = os.environ.get("SNAPSCRAP_LANG", "").lower() == "en" or "--en" in sys.argv
if "--en" in sys.argv:
    sys.argv = [a for a in sys.argv if a != "--en"]

# Parse --skip-first N
SKIP_FIRST = 0
if "--skip-first" in sys.argv:
    idx = sys.argv.index("--skip-first")
    try:
        SKIP_FIRST = int(sys.argv[idx+1])
        sys.argv.pop(idx) # removed '--skip-first'
        sys.argv.pop(idx) # removed 'N'
    except (IndexError, ValueError):
        sys.argv.pop(idx)

# Parse --date YYYY-MM-DD
TARGET_DATE = date.today().strftime("%Y-%m-%d")
if "--date" in sys.argv:
    idx = sys.argv.index("--date")
    try:
        TARGET_DATE = sys.argv[idx+1]
        sys.argv.pop(idx) # removed '--date'
        sys.argv.pop(idx) # removed 'YYYY-MM-DD'
    except (IndexError, ValueError):
        sys.argv.pop(idx)

# Parse --today-only
TODAY_ONLY = False
if "--today-only" in sys.argv:
    TODAY_ONLY = True
    sys.argv.remove("--today-only")

# Parse --custom-links "link1,link2"
CUSTOM_LINKS = []
if "--custom-links" in sys.argv:
    idx = sys.argv.index("--custom-links")
    try:
        links_str = sys.argv[idx+1]
        CUSTOM_LINKS = [link.strip() for link in links_str.split(",") if link.strip()]
        sys.argv.pop(idx) # removed '--custom-links'
        sys.argv.pop(idx) # removed links string
    except IndexError:
        sys.argv.pop(idx)



def show_help():
    """عرض قائمة بجميع الأوامر المتاحة."""
    if USE_EN:
        h = """
SnapScrap - Command list
------------------------
1) Download stories:
   python SnapScrap.py <username>
   python SnapScrap.py <username> --merge   (download then merge)
   Example: python SnapScrap.py dary_1256 --merge
   Output folder: username\\YYYY-MM-DD\\

2) Merge videos (every 8 per file, or all in one):
   python merge_videos.py <username> [YYYY-MM-DD] [--all]
   Without --all: merged_1.mp4, merged_2.mp4, ...
   With --all:   merged_all.mp4 (single video)
   Example: python merge_videos.py dary_1256
            python merge_videos.py dary_1256 2025-02-15 --all
   Output: username\\YYYY-MM-DD\\merged\\

3) Upload to YouTube Shorts:
   python upload_youtube_shorts.py <username> [YYYY-MM-DD] [private|public|unlisted]
   Example: python upload_youtube_shorts.py dary_1256 private
   (Requires client_secret.json from Google Cloud)

Per-script help:
   python SnapScrap.py help
   python merge_videos.py --help
   python upload_youtube_shorts.py --help

From CMD: use run.bat (e.g. run.bat help, run.bat dary_1256 --merge)
Or: run.bat en help   for English output if Arabic looks wrong.

Do NOT type < > or [ ] - they are placeholders. Use real values:
  python merge_videos.py dary_1256 2026-02-15 --all
"""
    else:
        h = """
+------------------------------------------------------------------+
|              SnapScrap - Command list                             |
+------------------------------------------------------------------+
| 1) Download stories:                                              |
|    python SnapScrap.py <username>                                |
|    python SnapScrap.py <username> --merge                        |
|    Example: python SnapScrap.py dary_1256 --merge                 |
|    Output folder: username\\YYYY-MM-DD\\                          |
+------------------------------------------------------------------+
| 2) Merge videos:                                                  |
|    python merge_videos.py <username> [YYYY-MM-DD] [--all]         |
|    Without --all: merged_1, merged_2, ... (every 8 videos)       |
|    With --all: merged_all.mp4 (one video)                         |
|    Example: python merge_videos.py dary_1256 --all                |
+------------------------------------------------------------------+
| 3) Upload YouTube Shorts:                                         |
|    python upload_youtube_shorts.py <username> [date] [privacy]    |
|    Example: python upload_youtube_shorts.py dary_1256 private     |
+------------------------------------------------------------------+
| Per-script help: python SnapScrap.py help  |  merge_videos --help |
| From CMD: run.bat help  or  run.bat en help (English)             |
|                                                                  |
| Do NOT type the symbols < > or [ ] - use real values, e.g.:       |
|   python merge_videos.py dary_1256 2026-02-15 --all               |
+------------------------------------------------------------------+
"""
    print(h.strip())


def user_input():
    """Get username from argument or user input."""
    args = [a for a in sys.argv[1:] if a not in ("--merge", "--en")]
    try:
        username = args[0]
    except IndexError:
        username = input("Enter a username: ")

    if args and args[0].lower() in ("help", "--help", "-h"):
        show_help()
        sys.exit(0)

    user_id = os.environ.get("SNAPSCRAP_USER_ID", "")
    # Removed user_id prefixing as requested to simplify paths
    path = os.path.join("stories", "not merged", username)
        
    date_str = TARGET_DATE
    date_folder = os.path.join(path, date_str)

    if os.path.exists(path):
        pass # removed this print statement to reduce console spam
    else:
        os.makedirs(path, exist_ok=True)
    os.makedirs(date_folder, exist_ok=True)
    os.chdir(date_folder)
    print(f"Download folder: {date_folder}" if USE_EN else f"التنزيل في مجلد: {date_folder}")
    return username


YELLOW = "\033[1;32;40m"
RED = "\033[31m"

# Modern User-Agent (Chrome on Windows)
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

# Setup Session with Retries
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("https://", adapter)
session.mount("http://", adapter)

base_url = "https://story.snapchat.com/@"
username = user_input()

mix = base_url + username
print(mix)


def get_json():
	"""Get json from the website"""

	try:
		r = session.get(mix, headers=headers, timeout=15)
	except Exception as e:
		sys.exit(f"{RED} Oh Snap! No connection with Snap! Error: {e}")

	if not r.ok:
		sys.exit(f"{RED} Oh Snap! No connection with Snap! Status: {r.status_code}")

	soup = BeautifulSoup(r.content, "html.parser")
	snaps_data = soup.find(id="__NEXT_DATA__")
	if not snaps_data:
		sys.exit(f"{RED} Oh Snap! Could not find data on the page!")
	
	snaps = snaps_data.string.strip()
	data = json.loads(snaps)

	return data


def profile_metadata(json_dict):
	"""Detect public profile, then print bio and bitmoji"""
	# if public
	try:
		bitmoji = json_dict["props"]["pageProps"]["userProfile"]["publicProfileInfo"]["snapcodeImageUrl"]
		bio = json_dict["props"]["pageProps"]["userProfile"]["publicProfileInfo"]["bio"]

	# if not public
	except KeyError:
		bitmoji = json_dict["props"]["pageProps"]["userProfile"]["userInfo"]["snapcodeImageUrl"]
		bio = json_dict["props"]["pageProps"]["userProfile"]["userInfo"]["displayName"]

		print(f"{YELLOW}Here is the Bio: \n {bio}\n")
		print(f"Bitmoji:\n {bitmoji}\n")
		print(f"{RED} This user is private.")

		sys.exit(1)

	print(f"{YELLOW}\nBio of the user:\n", bio)
	print(f"\nHere is the Bitmoji:\n {bitmoji} \n")

	print(f"Getting posts of: {username}\n")


def download_media(json_dict):
	"""Print media URLs and download media."""
	from datetime import datetime
	date_str = TARGET_DATE
	skipped = 0
	downloaded = 0

	today_start_timestamp = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
	file_index = 1

	# 1. Process custom links first
	for file_url in CUSTOM_LINKS:
		if file_url == "": continue
		if is_downloaded(username, date_str, file_url):
			skipped += 1
			file_index += 1
			continue

		try:
			r = session.get(file_url, stream=True, headers=headers, timeout=20)
			r.raise_for_status()
		except Exception as e:
			print(f"{RED} Cannot make connection to download custom link {file_index}: {e}")
			file_index += 1
			continue

		if "image" in r.headers.get('Content-Type', ''): ext = ".jpeg"
		elif "video" in r.headers.get('Content-Type', ''): ext = ".mp4"
		else: ext = ".bin"

		file_name = f"{file_index}{ext}"
		if os.path.isfile(file_name):
			mark_downloaded(username, date_str, file_url, file_name)
			skipped += 1
			file_index += 1
			continue

		print(f"[PROGRESS] {file_index}/(Custom)")
		print(file_name)
		sleep(0.3)

		if r.status_code == 200:
			with open(file_name, 'wb') as f:
				for chunk in r: f.write(chunk)
			mark_downloaded(username, date_str, file_url, file_name)
			downloaded += 1
		else:
			print(f"{RED} Cannot download custom media {file_index}, Status: {r.status_code}")
		file_index += 1

	# 2. Process profile regular snaps
	try:
		story = json_dict["props"]["pageProps"].get("story")
		snap_list = story.get("snapList") if story else None
		if not snap_list:
			raise KeyError("No snaps found")

		total_snaps = len(snap_list)
		for num, i in enumerate(snap_list, start=1):
			if num <= SKIP_FIRST:
				print(f"[PROGRESS] {num}/{total_snaps}")
				print(f"Skipped (First {SKIP_FIRST} rule)...")
				skipped += 1
				continue

			if TODAY_ONLY:
				ts_val = i.get("timestampInSec", {}).get("value")
				if ts_val and int(ts_val) < today_start_timestamp:
					skipped += 1
					continue

			file_url = i["snapUrls"]["mediaUrl"]
			if file_url == "":
				print("There is a Story but no URL is provided by Snapchat.")
				continue

			if is_downloaded(username, date_str, file_url):
				skipped += 1
				continue

			try:
				r = session.get(file_url, stream=True, headers=headers, timeout=20)
				r.raise_for_status()
			except Exception as e:
				print(f"{RED} Cannot make connection to download media {file_index}: {e}")
				file_index += 1
				continue

			if "image" in r.headers.get('Content-Type', ''): ext = ".jpeg"
			elif "video" in r.headers.get('Content-Type', ''): ext = ".mp4"
			else: ext = ".bin"

			file_name = f"{file_index}{ext}"
			if os.path.isfile(file_name):
				mark_downloaded(username, date_str, file_url, file_name)
				skipped += 1
				file_index += 1
				continue

			print(f"[PROGRESS] {num}/{total_snaps}")
			print(file_name)
			sleep(0.3)

			if r.status_code == 200:
				with open(file_name, 'wb') as f:
					for chunk in r: f.write(chunk)
				mark_downloaded(username, date_str, file_url, file_name)
				downloaded += 1
			else:
				print(f"{RED} Cannot download media {file_index}, Status: {r.status_code}")
			file_index += 1

	except KeyError:
		print(f"{RED}No user stories found for the last 24h.")
	else:
		if skipped > 0:
			print(f"\nSkipped {skipped} already downloaded stories.")
		if downloaded > 0:
			print(f"\nDownloaded {downloaded} new stories.")
		if downloaded == 0 and skipped == 0:
			print("\nNo new stories found.")
		else:
			print("\nAt least one Story found. Successfully Downloaded.")


def main():
	start = time.perf_counter()
	do_merge = "--merge" in sys.argv

	data = get_json()
	profile_metadata(data)
	download_media(data)

	if do_merge:
		script_dir = os.path.dirname(os.path.abspath(__file__))
		merge_script = os.path.join(script_dir, "merge_videos.py")
		date_str = TARGET_DATE
		merge_msg = f"\n{YELLOW}Merging videos (date: {date_str})..." if USE_EN else f"\n{YELLOW}دمج كل 6 فيديوهات (تاريخ اليوم: {date_str})..."
		print(merge_msg)
		env = os.environ.copy()
		if USE_EN:
			env["SNAPSCRAP_LANG"] = "en"
		subprocess.run([sys.executable, merge_script, username, date_str], cwd=script_dir, env=env)

	end = time.perf_counter()
	total = end - start

	print(f"\n\nTotal time: {total}")


if __name__ == "__main__":
	main()
