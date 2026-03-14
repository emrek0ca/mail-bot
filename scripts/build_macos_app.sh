#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_PYTHON="/opt/homebrew/bin/python3.11"
if [ -x "$DEFAULT_PYTHON" ]; then
  PYTHON_BIN="${PYTHON_BIN:-$DEFAULT_PYTHON}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3.11}"
fi

cd "$PROJECT_ROOT"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python bulunamadi: $PYTHON_BIN" >&2
  exit 1
fi

echo "Using Python: $PYTHON_BIN"

"$PYTHON_BIN" -m pip install -r build-requirements.txt

rm -rf "$PROJECT_ROOT/build" "$PROJECT_ROOT/dist"
"$PYTHON_BIN" -m PyInstaller --noconfirm MailBot.spec

APP_PATH="$PROJECT_ROOT/dist/Mail Bot.app"
ZIP_PATH="$PROJECT_ROOT/dist/MailBot-macOS.zip"

if [ -d "$APP_PATH" ]; then
  # Local .app'i temizle ve imzala ki tiklaninca calissin (Gatekeeper hatasi vermesin)
  xattr -cr "$APP_PATH" || true
  codesign --force --deep --sign - "$APP_PATH" || true

  STAGE_DIR="$(mktemp -d /tmp/mailbot-export.XXXXXX)"
  STAGE_APP="$STAGE_DIR/Mail Bot.app"
  ditto "$APP_PATH" "$STAGE_APP"
  ditto -c -k --keepParent "$STAGE_APP" "$ZIP_PATH"
  echo "App built: $APP_PATH"
  echo "Archive built: $ZIP_PATH"
else
  echo "Build tamamlanmadi: $APP_PATH bulunamadi" >&2
  exit 1
fi
