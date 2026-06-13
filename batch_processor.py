#!/usr/bin/env python3
"""
معالجة متعددة الحسابات: تحميل ودمج ونشر لعدة حسابات.
"""
import os
import sys
from daily_automation import process_account

# Fix Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ACCOUNTS_FILE = "accounts.txt"


def load_accounts():
    """Load accounts from file or use default."""
    accounts = []
    
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        accounts.append(line)
        except Exception as e:
            print(f"Error reading {ACCOUNTS_FILE}: {e}")
    
    # If no file or empty, use example
    if not accounts:
        print(f"No accounts found in {ACCOUNTS_FILE}. Creating example file...")
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            f.write("# Add one username per line\n")
            f.write("# Example:\n")
            f.write("dary_1256\n")
            f.write("# account2\n")
            f.write("# account3\n")
        print(f"Created {ACCOUNTS_FILE}. Edit it and add your accounts.")
        return []
    
    return accounts


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python batch_processor.py [--no-upload] [privacy]")
        print("  Reads accounts from accounts.txt (one per line)")
        print("  privacy: private (default), public, or unlisted")
        print("Example: python batch_processor.py")
        print("         python batch_processor.py --no-upload")
        print("         python batch_processor.py public")
        sys.exit(0)
    
    auto_upload = "--no-upload" not in sys.argv
    privacy = "private"
    
    for arg in sys.argv[1:]:
        if arg in ("private", "public", "unlisted"):
            privacy = arg
    
    accounts = load_accounts()
    if not accounts:
        print("No accounts to process. Add accounts to accounts.txt")
        sys.exit(1)
    
    print(f"\nProcessing {len(accounts)} account(s)...")
    print(f"Auto-upload: {'Yes' if auto_upload else 'No'}")
    print(f"Privacy: {privacy}\n")
    
    success_count = 0
    failed = []
    
    do_merge = "--no-merge" not in sys.argv
    for idx, username in enumerate(accounts, start=1):
        print(f"\n[{idx}/{len(accounts)}] Account: {username}")
        try:
            if process_account(username, auto_upload, privacy, do_merge):
                success_count += 1
            else:
                failed.append(username)
        except Exception as e:
            print(f"Error processing {username}: {e}")
            failed.append(username)
    
    print(f"\n{'='*60}")
    print(f"Summary: {success_count}/{len(accounts)} accounts processed successfully")
    if failed:
        print(f"Failed: {', '.join(failed)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
