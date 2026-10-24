# ohmygame-publish-action

Publish (or update) a web game on [OhMyGame](https://ohmygame.ai) straight from GitHub Actions. Republishing keeps the same play URL, so this gives you "push to GitHub → game updated" for games published with the OhMyGame desktop app.

> **How it works.** This calls OhMyGame's cloud publish API (`cloud.ohmygame.ai/v1`), reverse-engineered from the open-source desktop client. It is not an officially supported API; if OhMyGame changes it, this action may break (please open an issue).

## Usage

```yaml
- uses: your-name/ohmygame-publish-action@v1
  with:
    game-id: c17c197e-58f0-4c5a-b791-a9f320526e67
    email: ${{ secrets.OHMYGAME_EMAIL }}
    password: ${{ secrets.OHMYGAME_PASSWORD }}
    site-dir: dist   # directory containing index.html, after your build step
```

### Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `game-id` | unless first publish | — | The game to update. Find yours in the desktop app's publish URL, or `GET https://cloud.ohmygame.ai/v1/me/games`. |
| `email` + `password` | one auth method | — | **Recommended.** OhMyGame account email and password; each run signs in fresh and never expires. Store as secrets. |
| `refresh-token` | one auth method | — | Alternative: Supabase refresh token extracted from the desktop app. Needs occasional renewal (see FAQ). |
| `site-dir` | no | `dist` | Built static site; must contain `index.html` at its root. Max 100 MiB. |
| `title` / `description` | no | — | Used when creating a new game (omit `game-id`), or pass to update the listing. |
| `api-url` | no | `https://cloud.ohmygame.ai` | Publish API base. |
| `dry-run` | no | `false` | Authenticate and validate the artifact without uploading. |

### Outputs

`game-id`, `play-url`, `deployment-id`.

## Setting up authentication (once, no maintenance)

OhMyGame accounts sign in with GitHub/Google in the desktop app, but the underlying auth service (Supabase) also accepts **email + password**. Your account email already exists — it just has no password yet, because the account was created through GitHub/Google OAuth. You can add one:

1. Trigger a password-reset email for your account email (check spam). Either use a "Forgot password" UI if you find one, or call it directly:

   ```sh
   curl -X POST https://bxrkwxorrudhyoggwcrt.supabase.co/auth/v1/recover \
     -H "apikey: sb_publishable_Men4Oz_0ZZhyLpFDtceA7Q_oMnJE5IJ" \
     -H "Content-Type: application/json" \
     -d '{"email":"you@example.com"}'
   ```

2. Open the link in the email. **Surprise: there is no "set a new password" form** — the link logs you straight in and lands on `https://www.ohmygame.ai/#access_token=...&refresh_token=...`. That's not a bug you can fix; OhMyGame simply doesn't have a reset-password page. Copy the **full URL** from the address bar.
3. Set your password with the helper:

   ```sh
   python scripts/set-password.py "<pasted URL>" "<your new password>"
   ```

4. Add two repository **Actions secrets**: `OHMYGAME_EMAIL` and `OHMYGAME_PASSWORD`.

### How set-password.py works (and why it's safe)

The reset link you opened is itself proof that you control the account's email — Supabase exchanged it for a login session, and put that session's tokens in the landing URL. `set-password.py` uses exactly that session, through Supabase's standard API, in three steps:

1. Takes the `refresh_token` from the URL and exchanges it for a fresh access token (`POST /auth/v1/token?grant_type=refresh_token`). This is the same call the website itself would make.
2. Calls the standard "update current user" endpoint **while signed in as you** (`PUT /auth/v1/user` with `{"password": ...}`). Supabase allows a signed-in user to change their own password; this is the API behind any "change password" page.
3. Verifies by signing in with the new email+password (`grant_type=password`) — the exact flow every workflow run will use.

No security boundary is bypassed: the email link came to your inbox, the session belongs to you, and the password is set on your own account. Your GitHub/Google sign-in for the desktop app keeps working unchanged — a Supabase account can have OAuth identities and a password side by side.

Notes:

- The URL's tokens expire after about an hour and single use; if step 3 fails, resend the email (step 1) and use the newest link.
- Set HTTPS_PROXY if supabase.co is unreachable from your machine.
- To change the password later, just rerun the whole flow with a new password.

Done — every workflow run signs in fresh; nothing ever expires and the desktop app is unaffected.

### Alternative: refresh token (not recommended)

The desktop app's session token also works but rotates as the app is used, so it goes stale and needs occasional renewal. Only use it if you cannot set a password:

- Extract: `python scripts/extract-token.py` (from the machine with the desktop app signed in; quit and reopen the app first so the newest session is on disk).
- Renew when the action reports `Refresh token rejected`: `python scripts/extract-token.py | gh secret set OHMYGAME_REFRESH_TOKEN -R <owner>/<repo>`

## FAQ

**Why email+password instead of a token?**

The desktop app's session token rotates every time the app refreshes (roughly hourly), so a copy stored in CI goes stale and needs manual renewal. A password grants a brand-new session on every run — it never expires, works from any IP, and signing in this way does not affect or sign out the desktop app.

**I use the refresh-token method and got "Refresh token rejected".**

The desktop app moved the token chain forward. Renew the secret (command above) from the signed-in machine — or switch to email+password and be done with it. If the script finds no working token while the app is running, fully quit and reopen the app first (no re-login needed).

## Limitations

- Runs on `ubuntu-latest` / `macos-latest` runners (needs `bash`, `curl`, and `python3`/`python`). Not for `windows` runners.
- Interactive-story projects that need OhMyGame's Published Player are not supported; this action is for plain static web games (the `dist/` you'd otherwise zip by hand).
- The API is unofficial; pin to a tag (`@v1`) rather than `@main` for stability.
- Password auth depends on the email provider staying enabled in OhMyGame's auth service; if it is ever turned off, fall back to the refresh-token method.

## License

MIT
