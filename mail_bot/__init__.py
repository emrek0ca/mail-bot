from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "Mail Bot"
PACKAGE_ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PACKAGE_ROOT))
USER_DATA_DIR = Path(user_data_dir(APP_NAME, appauthor=False))
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

# Proactive permission check
for d in [DATA_DIR, BROWSERS_DIR]:
    if not os.access(d, os.W_OK):
        print(f"HATA: {d} klasorune yazma yetkisi yok!", file=sys.stderr)

# Linux DISPLAY check
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    if not os.environ.get("WAYLAND_DISPLAY"):
        print("HATA: Grafik ekrani (DISPLAY) bulunamadi. GUI uygulamasi baslatilamaz.", file=sys.stderr)

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BROWSERS_DIR))
