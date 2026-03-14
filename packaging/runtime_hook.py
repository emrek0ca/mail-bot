from __future__ import annotations

import os
import sys
from pathlib import Path

app_name = "Mail Bot"
user_browser_dir = Path.home() / "Library" / "Application Support" / app_name / "playwright-browsers"
user_browser_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(user_browser_dir))
