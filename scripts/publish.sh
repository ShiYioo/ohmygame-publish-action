#!/usr/bin/env bash
# Publishes a static site to OhMyGame's cloud publish API.
# Reverse-engineered from the official desktop client (src/daemon/publish/client.ts);
# the API is versioned (/v1) but undocumented - expect occasional breakage.
set -euo pipefail

GAME_ID="${INPUT_GAME_ID:-}"
EMAIL="${INPUT_EMAIL:-}"
PASSWORD="${INPUT_PASSWORD:-}"
REFRESH_TOKEN="${INPUT_REFRESH_TOKEN:-}"
SITE_DIR="${INPUT_SITE_DIR:-dist}"
TITLE="${INPUT_TITLE:-}"
DESCRIPTION="${INPUT_DESCRIPTION:-}"
API_URL="${INPUT_API_URL:-https://cloud.ohmygame.ai}"
DRY_RUN="${INPUT_DRY_RUN:-false}"

SUPABASE_URL="https://bxrkwxorrudhyoggwcrt.supabase.co"
SUPABASE_KEY="sb_publishable_Men4Oz_0ZZhyLpFDtceA7Q_oMnJE5IJ"
MAX_BYTES=$((100 * 1024 * 1024))

log() { echo "[ohmygame-publish] $*"; }
die() { echo "::error::$*" >&2; exit 1; }

# Runners have python3; local Git-Bash on Windows has a python3 stub that
# just opens the Microsoft Store, so verify the interpreter actually runs.
PY=python3
"$PY" -c 'import json' >/dev/null 2>&1 || PY=python
jsonget() { printf '%s' "$1" | "$PY" -c "import json,sys; print(json.load(sys.stdin)$2)" 2>/dev/null; }

command -v curl >/dev/null || die "curl is required"

# Zip the staging dir, excluding the archive itself. Uses the zip binary when
# present (runners) and python's zipfile otherwise (local Git-Bash on Windows).
make_zip() { # make_zip <source-dir> <out.zip>
  if command -v zip >/dev/null; then
    (cd "$1" && zip -qr "$2" . -x "$(basename "$2")")
  else
    "$PY" -c 'import sys, zipfile, os
src, out = sys.argv[1], os.path.abspath(sys.argv[2])
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(src):
        for f in files:
            full = os.path.join(root, f)
            if os.path.abspath(full) == out: continue
            z.write(full, os.path.relpath(full, src).replace(os.sep, "/"))' "$1" "$2"
  fi
}

[ -f "$SITE_DIR/index.html" ] || die "'$SITE_DIR/index.html' not found. Build the game first (default site-dir is dist)."

# --- 1. Authenticate -----------------------------------------------------------
# Email+password creates a fresh session every run and never expires.
# The refresh token rotates as the desktop app is used and needs occasional renewal.
if [ -n "$EMAIL" ] && [ -n "$PASSWORD" ]; then
  log "Authenticating with email+password..."
  BODY=$("$PY" -c 'import json,sys; print(json.dumps({"email": sys.argv[1], "password": sys.argv[2]}))' "$EMAIL" "$PASSWORD")
  GRANT="password"
elif [ -n "$REFRESH_TOKEN" ]; then
  log "Authenticating with refresh token..."
  BODY=$("$PY" -c 'import json,sys; print(json.dumps({"refresh_token": sys.argv[1]}))' "$REFRESH_TOKEN")
  GRANT="refresh_token"
else
  die "Provide email+password (recommended) or refresh-token."
fi
AUTH=$(curl -fsS -X POST "$SUPABASE_URL/auth/v1/token?grant_type=$GRANT" \
  -H "apikey: $SUPABASE_KEY" -H "Content-Type: application/json" \
  -d "$BODY") || die "Could not authenticate (check credentials / network)"
ACCESS_TOKEN=$(jsonget "$AUTH" '.get("access_token","")')
[ -n "$ACCESS_TOKEN" ] || die "Refresh token rejected. Re-extract it from the OhMyGame desktop app (see README)."
log "Authenticated."

# --- 2. Package the site as the desktop client would -------------------------
STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT
cp -r "$SITE_DIR"/. "$STAGING"/
ZIP="$STAGING/game.zip"
make_zip "$STAGING" "$ZIP" || die "zip failed"
SIZE=$(wc -c <"$ZIP" | tr -d ' ')
[ "$SIZE" -le "$MAX_BYTES" ] || die "Artifact is $SIZE bytes; OhMyGame's limit is 100 MiB"
SHA256=$(sha256sum "$ZIP" | cut -d' ' -f1)
log "Artifact ready: $SIZE bytes (sha256 $SHA256)"

if [ "$DRY_RUN" = "true" ]; then
  log "Dry run: skipping upload."
  echo "game-id=$GAME_ID" >>"$GITHUB_OUTPUT"
  exit 0
fi

# --- 3. Create the game on first publish -------------------------------------
if [ -z "$GAME_ID" ]; then
  [ -n "$TITLE" ] || die "First publish needs a title (no game-id given)."
  log "No game-id given; creating a new game..."
  BODY=$("$PY" -c 'import json,sys; print(json.dumps({"title": sys.argv[1], "description": sys.argv[2]}))' "$TITLE" "${DESCRIPTION:-}")
  CREATED=$(curl -fsS -X POST "$API_URL/v1/games" \
    -H "authorization: Bearer $ACCESS_TOKEN" \
    -H "idempotency-key: gh-action-first-$SHA256" \
    -H "Content-Type: application/json" -d "$BODY") || die "Game creation failed"
  GAME_ID=$(jsonget "$CREATED" '["id"]')
  log "Created game $GAME_ID"
fi

# --- 4. Upload the deployment (republishing keeps the same play URL) ---------
log "Uploading deployment to game $GAME_ID..."
UPLOAD=$(curl -fsS -X POST "$API_URL/v1/games/$GAME_ID/deployments" \
  -H "authorization: Bearer $ACCESS_TOKEN" \
  -H "idempotency-key: gh-action-$GAME_ID-$SHA256" \
  -F "metadata={\"artifactSha256\":\"$SHA256\",\"artifactBytes\":$SIZE};type=application/json" \
  -F "artifact=@$ZIP;type=application/zip;filename=game.zip") || die "Upload failed"

GAME_JSON=$(curl -fsS "$API_URL/v1/games/$GAME_ID" -H "authorization: Bearer $ACCESS_TOKEN") || die "Upload ok but listing the game failed"
PLAY_URL=$(jsonget "$GAME_JSON" '["playUrl"]')
DEPLOYMENT_ID=$(jsonget "$UPLOAD" '["deployment"]["id"]')

echo "game-id=$GAME_ID" >>"$GITHUB_OUTPUT"
echo "play-url=$PLAY_URL" >>"$GITHUB_OUTPUT"
echo "deployment-id=$DEPLOYMENT_ID" >>"$GITHUB_OUTPUT"
log "Published: $PLAY_URL (deployment $DEPLOYMENT_ID)"
