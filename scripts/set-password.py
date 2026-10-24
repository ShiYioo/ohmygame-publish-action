#!/usr/bin/env python
"""Set a password on an OhMyGame account that was created via GitHub/Google.

OhMyGame's reset email logs you straight in instead of showing a password
form, so use the tokens in the URL you land on:

1. Trigger the reset email (see README) and open the link.
2. You land on https://www.ohmygame.ai/#access_token=...&refresh_token=...
   Copy the FULL URL from the address bar.
3. Run:
       python scripts/set-password.py "<pasted URL>" "<new password>"

The script refreshes the session, sets the password, and signs in with it to
verify. The desktop app is not affected.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

SUPABASE = "https://bxrkwxorrudhyoggwcrt.supabase.co"
SUPABASE_KEY = "sb_publishable_Men4Oz_0ZZhyLpFDtceA7Q_oMnJE5IJ"


def post(path, body):
    request = urllib.request.Request(
        SUPABASE + path, data=json.dumps(body).encode(), method="POST",
        headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    url, password = sys.argv[1], sys.argv[2]
    if len(password) < 6:
        sys.exit("Password must be at least 6 characters.")
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).fragment))
    refresh_token = params.get("refresh_token")
    if not refresh_token:
        sys.exit("No refresh_token in that URL. Copy the full www.ohmygame.ai/#... address after opening the reset link.")

    email = post("/auth/v1/token?grant_type=refresh_token", {"refresh_token": refresh_token})
    access = email["access_token"]
    email_addr = email["user"]["email"]

    update = urllib.request.Request(
        SUPABASE + "/auth/v1/user", data=json.dumps({"password": password}).encode(), method="PUT",
        headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json", "Authorization": f"Bearer {access}"},
    )
    urllib.request.urlopen(update, timeout=30).read()

    verify = post("/auth/v1/token?grant_type=password", {"email": email_addr, "password": password})
    if "access_token" not in verify:
        sys.exit("Password was set but verification sign-in failed.")
    print(f"Password set and verified for {email_addr}. Use it as the email+password inputs of the action.")


if __name__ == "__main__":
    main()
