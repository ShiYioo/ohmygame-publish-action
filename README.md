# ohmygame-publish-action

Publish (or update) a web game on [OhMyGame](https://ohmygame.ai) straight from GitHub Actions. Republishing keeps the same play URL, so this gives you "push to GitHub → game updated" for games published with the OhMyGame desktop app.

> **How it works.** This calls OhMyGame's cloud publish API (`cloud.ohmygame.ai/v1`), reverse-engineered from the open-source desktop client. It is not an officially supported API; if OhMyGame changes it, this action may break (please open an issue).

## Usage

```yaml
- uses: your-name/ohmygame-publish-action@v1
  with:
    game-id: c17c197e-58f0-4c5a-b791-a9f320526e67
    refresh-token: ${{ secrets.OHMYGAME_REFRESH_TOKEN }}
    site-dir: dist   # directory containing index.html, after your build step
```

A complete workflow:

```yaml
name: Publish
on:
  push:
    branches: [main]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build        # produce dist/
      - uses: your-name/ohmygame-publish-action@v1
        with:
          game-id: ${{ vars.OHMYGAME_GAME_ID }}
          refresh-token: ${{ secrets.OHMYGAME_REFRESH_TOKEN }}
          site-dir: dist
```

### Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `game-id` | unless first publish | — | The game to update. Find yours in the desktop app's publish URL, or `GET https://cloud.ohmygame.ai/v1/me/games`. |
| `refresh-token` | yes | — | Your OhMyGame account's Supabase refresh token. **Store it as a secret.** |
| `site-dir` | no | `dist` | Built static site; must contain `index.html` at its root. Max 100 MiB. |
| `title` / `description` | no | — | Used when creating a new game (omit `game-id`), or pass to update the listing. |
| `api-url` | no | `https://cloud.ohmygame.ai` | Publish API base. |
| `dry-run` | no | `false` | Authenticate and validate the artifact without uploading. |

### Outputs

`game-id`, `play-url`, `deployment-id`.

## Getting your refresh token

The desktop app stores its session here after you sign in:

- **Windows**: `%APPDATA%\ohmygame\Local Storage\leveldb\` — search the files for `"refresh_token":"..."` and take the **last** match.
- **macOS**: `~/Library/Application Support/ohmygame/Local Storage/leveldb/`
- **Linux**: `~/.config/ohmygame/Local Storage/leveldb/`

Tips:

- Add `OHMYGAME_REFRESH_TOKEN` as a repository **Actions secret**, never commit it.
- Tokens rotate when the desktop app signs in. Refresh tokens are reusable for a while; if the action starts failing with "Refresh token rejected", sign in to the desktop app once and re-extract the latest token.
- Cover art: put a `__ohmygame/cover.webp` inside `site-dir` and it is included in the artifact, like the desktop client does.

## Limitations

- Runs on `ubuntu-latest` / `macos-latest` runners (needs `bash`, `curl`, and `python3`/`python`). Not for `windows` runners.
- Interactive-story projects that need OhMyGame's Published Player are not supported; this action is for plain static web games (the `dist/` you'd otherwise zip by hand).
- The API is unofficial; pin to a tag (`@v1`) rather than `@main` for stability.

## License

MIT
