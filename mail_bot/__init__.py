from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Mail Bot"
PACKAGE_ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PACKAGE_ROOT))
USER_DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
DATA_DIR = USER_DATA_DIR
ASSETS_DIR = RESOURCE_ROOT / "assets"
DEFAULT_DB_PATH = DATA_DIR / "mailbot.db"
DEFAULT_AI_PROVIDER = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DAILY_GMAIL_LIMIT = 500
RECOMMENDED_FIT_SCORE = 70
BROWSERS_DIR = USER_DATA_DIR / "playwright-browsers"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BROWSERS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BROWSERS_DIR))
