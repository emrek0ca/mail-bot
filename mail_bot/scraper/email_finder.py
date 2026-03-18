from __future__ import annotations

import re
from html import unescape
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ..models import EmailLookupResult
from ..security import normalize_public_url

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PLACEHOLDER_PREFIXES = ("noreply@", "no-reply@", "example@", "test@", "demo@")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
CONTACT_PATHS = ("/contact", "/iletisim", "/hakkimizda", "/about", "/bize-ulasin")


GENERIC_PREFIXES = {"info", "contact", "hello", "iletisim", "bilgi", "destek", "support", "admin", "webmaster", "sales", "satis", "marketing"}
HIGH_PRIORITY_PREFIXES = {"ceo", "cto", "founder", "kurucu"}
HR_PREFIXES = {"ik", "hr", "career", "kariyer", "jobs", "insankaynaklari"}

def score_email(email: str) -> int:
    prefix = email.split('@')[0].lower()
    if prefix in HIGH_PRIORITY_PREFIXES:
        return 10
    if prefix in HR_PREFIXES:
        return 8
    if prefix in GENERIC_PREFIXES:
        return 1
    # Personal names like "emre@" or "john.doe@"
    return 5

async def find_email(website: str | None) -> EmailLookupResult:
    if not website:
        return EmailLookupResult(email=None, source="not_found", checked_urls=[], error="Website yok")

    try:
        normalized = normalize_website(website)
    except ValueError as exc:
        return EmailLookupResult(email=None, source="not_found", checked_urls=[], error=str(exc))
    checked_urls: list[str] = []
    found_emails: set[str] = set()
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=_headers()) as client:
            emails = await _scan_page(client, normalized, checked_urls)
            found_emails.update(emails)
            for suffix in CONTACT_PATHS:
                candidate_url = urljoin(normalized.rstrip("/") + "/", suffix.lstrip("/"))
                emails = await _scan_page(client, candidate_url, checked_urls)
                found_emails.update(emails)
            
            if found_emails:
                best_email = max(found_emails, key=score_email)
                return EmailLookupResult(email=best_email, source="scraped", checked_urls=checked_urls)
    except Exception as exc:
        if found_emails:
            best_email = max(found_emails, key=score_email)
            return EmailLookupResult(email=best_email, source="scraped", checked_urls=checked_urls, error=str(exc))
        guessed = guess_email_from_domain(normalized)
        if guessed:
            return EmailLookupResult(email=guessed, source="guessed", checked_urls=checked_urls, error=str(exc))
        return EmailLookupResult(email=None, source="not_found", checked_urls=checked_urls, error=str(exc))

    if found_emails:
        best_email = max(found_emails, key=score_email)
        return EmailLookupResult(email=best_email, source="scraped", checked_urls=checked_urls)

    guessed = guess_email_from_domain(normalized)
    if guessed:
        return EmailLookupResult(email=guessed, source="guessed", checked_urls=checked_urls)
    return EmailLookupResult(email=None, source="not_found", checked_urls=checked_urls)


def extract_valid_emails(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    raw_emails = set(EMAIL_REGEX.findall(unescape(html)))
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if href.lower().startswith("mailto:"):
            raw_emails.add(href.split(":", 1)[1].split("?", 1)[0].strip())
    valid = sorted(email for email in raw_emails if is_valid_email(email))
    return valid


def is_valid_email(value: str) -> bool:
    lowered = value.lower().strip()
    if not lowered or any(lowered.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES):
        return False
    if lowered.endswith(IMAGE_SUFFIXES):
        return False
    return bool(EMAIL_REGEX.fullmatch(lowered))


def normalize_website(website: str) -> str:
    return normalize_public_url(website)


def guess_email_from_domain(website: str) -> str | None:
    parsed = urlparse(normalize_website(website))
    domain = parsed.netloc.lower().removeprefix("www.")
    if not domain:
        return None
    # En olasi tahminleri siraliyoruz
    guesses = [
        f"info@{domain}",
        f"contact@{domain}",
        f"iletisim@{domain}",
        f"bilgi@{domain}",
    ]
    return guesses[0]


async def _scan_page(client: httpx.AsyncClient, url: str, checked_urls: list[str]) -> list[str]:
    checked_urls.append(url)
    try:
        response = await client.get(url)
        response.raise_for_status()
        return extract_valid_emails(response.text)
    except Exception:
        return []


def _headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
    }
