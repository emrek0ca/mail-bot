from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from ..security import normalize_public_url


async def read_website_summary_text(url: str) -> str:
    try:
        normalized_url = normalize_public_url(url)
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=_headers()) as client:
            response = await client.get(normalized_url)
            response.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "img"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:2000]


def _headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
    }
