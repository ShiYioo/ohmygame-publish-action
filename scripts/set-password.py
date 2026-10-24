#!/usr/bin/env python
"""Set a password on your OhMyGame account, interactively, in one command.

OhMyGame accounts are created through GitHub/Google and have no password.
This script walks you through adding one so CI can sign in with email+password:

    python scripts/set-password.py you@example.com

It sends the reset email, waits for you to open it and paste the landing URL,
sets the password you choose, and verifies it by signing in.

Set HTTPS_PROXY if supabase.co is unreachable from your machine.
"""
import getpass
import json
import os
import sys
import urllib.parse
import urllib.request

SUPABASE = "https://bxrkwxorrudhyoggwcrt.supabase.co"
SUPABASE_KEY = "sb_publishable_Men4Oz_0ZZhyLpFDtceA7Q_oMnJE5IJ"


def request_json(method, path, body=None, bearer=None):
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    request = urllib.request.Request(
        SUPABASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:200]
        sys.exit(f"Request failed ({error.code}): {detail}")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    email = sys.argv[1]

    print(f"[1/4] Sending the password-reset email to {email} ...")
    request_json("POST", "/auth/v1/recover", {"email": email})
    print("      Sent. Check your inbox (and spam folder).")

    print("[2/4] Open the email and click its link.")
    print("      The link opens www.ohmygame.ai and logs you in - that is expected;")
    print("      there is no password form. Just copy the FULL URL from the address bar")
    print("      (it looks like https://www.ohmygame.ai/#access_token=...&refresh_token=...)")
    url = input("      Paste it here: ").strip()

    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).fragment))
    refresh_token = params.get("refresh_token")
    if not refresh_token:
        sys.exit("That URL has no refresh_token. Make sure you copied the whole address bar URL.")

    print("[3/4] Choose a new password (min 6 chars).")
    try:
        password = getpass.getpass("(input hidden): ")
    except Exception:
        # getpass needs a real console; fall back to visible input.
        password = input("(visible input, no console detected): ")
    if len(password) < 6:
        sys.exit("Password must be at least 6 characters.")

    session = request_json("POST", "/auth/v1/token?grant_type=refresh_token", {"refresh_token": refresh_token})
    request_json("PUT", "/auth/v1/user", {"password": password}, bearer=session["access_token"])

    print("[4/4] Verifying with email+password sign-in ...")
    verified = request_json("POST", "/auth/v1/token?grant_type=password", {"email": email, "password": password})
    if "access_token" not in verified:
        sys.exit("Password was set, but verification sign-in failed - rerun with a fresh reset email.")
    print(f"Done. Keep these for the action's email/password inputs:\n  email:    {email}\n  password: (the one you just chose)")


if __name__ == "__main__":
    main()
