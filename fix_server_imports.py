"""
Fix script: replaces every `emergentintegrations` AI import in backend/server.py
with the equivalent import from app.services.ai_client (the shim we built earlier).

Usage (from your repo root, e.g. C:\\Users\\Rishikesh\\Desktop\\OEMLinker):
    python fix_server_imports.py
"""

import re
import shutil
import sys
from pathlib import Path

SERVER_PATH = Path("backend/server.py")
EXPECTED_MIN_REPLACEMENTS = 8

def main():
    if not SERVER_PATH.exists():
        print(f"ERROR: {SERVER_PATH} not found. Run this script from your repo root "
              f"(the folder containing 'backend/' and 'frontend/').")
        sys.exit(1)

    backup_path = SERVER_PATH.with_suffix(".py.bak")
    shutil.copy2(SERVER_PATH, backup_path)
    print(f"Backup created: {backup_path}")

    content = SERVER_PATH.read_text(encoding="utf-8")
    original_content = content

    pattern_openai = re.compile(r"from emergentintegrations\.llm\.openai import ([\w,\s]+)")
    count_openai = len(pattern_openai.findall(content))
    content = pattern_openai.sub(lambda m: f"from app.services.ai_client import {m.group(1)}", content)

    pattern_chat = re.compile(r"from emergentintegrations\.llm\.chat import ([\w,\s]+)")
    count_chat = len(pattern_chat.findall(content))
    content = pattern_chat.sub(lambda m: f"from app.services.ai_client import {m.group(1)}", content)

    pattern_stripe = re.compile(r"from emergentintegrations\.payments\.stripe\.checkout import [\w,\s]+")
    stripe_matches = pattern_stripe.findall(content)

    total_replaced = count_openai + count_chat

    if content == original_content:
        print("WARNING: No changes were made. File content is identical to backup.")
        sys.exit(0)

    SERVER_PATH.write_text(content, encoding="utf-8")

    print()
    print("=" * 60)
    print(f"Replaced {count_openai} 'emergentintegrations.llm.openai' import(s)")
    print(f"Replaced {count_chat} 'emergentintegrations.llm.chat' import(s)")
    print(f"Total AI imports fixed: {total_replaced}")
    print()
    if stripe_matches:
        print(f"NOTE: Found {len(stripe_matches)} Stripe import(s) - LEFT UNCHANGED "
              f"(confirmed dead code, you use Razorpay).")
        for s in stripe_matches:
            print(f"  - {s.strip()}")
    print("=" * 60)

    if total_replaced < EXPECTED_MIN_REPLACEMENTS:
        print()
        print(f"WARNING: Expected at least {EXPECTED_MIN_REPLACEMENTS} replacements, "
              f"only found {total_replaced}.")
        print('Check remaining with: Get-Content backend\\server.py | Select-String -Pattern "emergentintegrations.llm"')
    else:
        print()
        print("Looks complete. Verify with:")
        print('    Get-Content backend\\server.py | Select-String -Pattern "emergentintegrations.llm"')
        print("(should return nothing)")

    print()
    print("If something looks wrong, restore the backup with:")
    print(f"    Copy-Item {backup_path} {SERVER_PATH} -Force")

if __name__ == "__main__":
    main()