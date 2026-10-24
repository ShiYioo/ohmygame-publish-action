#!/usr/bin/env python
"""Print a working OhMyGame refresh token from the local desktop app's storage.

Scans the Electron Local Storage leveldb for every refresh token, then tries
each against the auth service (newest first) and prints the first one that
works. Use it to refresh a CI secret when the action reports
"Refresh token rejected":

    python scripts/extract-token.py | gh secret set OHMYGAME_REFRESH_TOKEN

Set HTTPS_PROXY if supabase.co is unreachable from your machine.
"""
import glob
import json
import os
import re
import subprocess
import sys
import urllib.request

SUPABASE_URL = "https://bxrkwxorrudhyoggwcrt.supabase.co/auth/v1/token?grant_type=refresh_token"
SUPABASE_KEY = "sb_publishable_Men4Oz_0ZZhyLpFDtceA7Q_oMnJE5IJ"

HOME = os.path.expanduser("~")
CANDIDATE_DIRS = [
    os.path.join(HOME, "AppData", "Roaming", "ohmygame"),          # Windows
    os.path.join(HOME, "Library", "Application Support", "ohmygame"),  # macOS
    os.path.join(HOME, ".config", "ohmygame"),                     # Linux
]


def candidates():
    tokens = []
    for base in CANDIDATE_DIRS:
        for f in glob.glob(os.path.join(base, "Local Storage", "leveldb", "*")):
            if not f.endswith((".log", ".ldb")):
                continue
            try:
                data = open(f, "rb").read()
            except OSError:
                continue
            for match in re.findall(rb'"refresh_token":"([A-Za-z0-9_-]+)"', data):
                token = match.decode()
                if token not in tokens:
                    tokens.append(token)
    return tokens


def works(token):
    body = json.dumps({"refresh_token": token}).encode()
    request = urllib.request.Request(
        SUPABASE_URL, data=body, method="POST",
        headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return "access_token" in json.load(response)
    except Exception:
        return False


def main():
    tokens = candidates()
    if not tokens:
        sys.exit("No OhMyGame session found. Sign in to the desktop app first.")
    # The newest token is the one still honoured; test from most recent back.
    for token in reversed(tokens):
        if works(token):
            print(token)
            return
    sys.exit("All stored tokens were rejected. Sign in to the desktop app and retry.")


if __name__ == "__main__":
    main()
