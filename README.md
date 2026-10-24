# ohmygame-publish-action

Publish (or update) a web game on [OhMyGame](https://ohmygame.ai) straight from GitHub Actions. Republishing keeps the same play URL, so this gives you "push to GitHub → game updated" for games published with the OhMyGame desktop app.

> **How it works.** This calls OhMyGame's cloud publish API (`cloud.ohmygame.ai/v1`), reverse-engineered from the open-source desktop client. It is not an officially supported API; if OhMyGame changes it, this action may break (please open an issue).

## Usage

```yaml
- uses: ShiYioo/ohmygame-publish-action@v1
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

OhMyGame accounts are created through GitHub/Google and have no password. CI needs one, so set it up first — one interactive command does everything:

```sh
python scripts/set-password.py you@example.com
```

The script then tells you what to do at each step:

1. It sends the reset email to your address (check spam if you don't see it).
2. You open the email and click the link. **The link logs you straight into www.ohmygame.ai — there is no password form, this is normal** (OhMyGame doesn't have a reset page). Copy the full URL from the address bar and paste it back into the script when it asks.
3. Type the password you want (input is hidden).
4. The script sets it, signs in to verify, and reminds you of the values.

Finally add two repository **Actions secrets**: `OHMYGAME_EMAIL` and `OHMYGAME_PASSWORD`. That's it — every workflow run signs in fresh; nothing ever expires.

Notes:

- If the script says the pasted URL has no `refresh_token` or verification fails, the link was stale — rerun the command and use the **newest** email.
- Set `HTTPS_PROXY` first if supabase.co is unreachable from your machine (e.g. China).
- Rerun the same command any time to change the password.
- Your GitHub/Google sign-in in the desktop app keeps working; OAuth and a password coexist on the same account.

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
