#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="$PROJECT_ROOT/dist/Mail Bot.app"
ZIP_PATH="$PROJECT_ROOT/dist/MailBot-macOS.zip"

if [ ! -d "$APP_PATH" ]; then
  echo "App bulunamadi: $APP_PATH" >&2
  exit 1
fi

STAGE_DIR="$(mktemp -d /tmp/mailbot-export.XXXXXX)"
STAGE_APP="$STAGE_DIR/Mail Bot.app"

ditto "$APP_PATH" "$STAGE_APP"
xattr -cr "$STAGE_APP"
ditto -c -k --keepParent "$STAGE_APP" "$ZIP_PATH"

echo "Archive built: $ZIP_PATH"
