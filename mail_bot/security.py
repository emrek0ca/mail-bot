from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse, urlunparse

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".lan", ".home", ".arpa")
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def validate_recipient_email(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("Email adresi bos olamaz.")
    _ensure_no_newlines(candidate, "Email")
    if not EMAIL_REGEX.fullmatch(candidate):
        raise ValueError("Email adresi gecersiz.")
    return candidate


def sanitize_header(value: str, field_name: str) -> str:
    cleaned = value.strip()
    _ensure_no_newlines(cleaned, field_name)
    return cleaned


def normalize_public_url(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("URL bos olamaz.")
    if "://" in candidate and not candidate.startswith(("http://", "https://")):
        raise ValueError("Yalnizca http/https URL desteklenir.")
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Yalnizca http/https URL desteklenir.")
    if not parsed.hostname:
        raise ValueError("URL host bilgisi eksik.")
    if parsed.username or parsed.password:
        raise ValueError("Kullanici bilgisi iceren URL desteklenmez.")

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in BLOCKED_HOSTS or hostname.endswith(BLOCKED_HOST_SUFFIXES):
        raise ValueError("Yerel ag veya local host URL'leri engellendi.")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None

    if ip and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
        raise ValueError("Ozel veya yerel IP adreslerine istek atilamaz.")

    normalized = parsed._replace(fragment="")
    return urlunparse(normalized)


def _ensure_no_newlines(value: str, field_name: str) -> None:
    if "\r" in value or "\n" in value:
        raise ValueError(f"{field_name} alaninda satir basi karakteri kullanilamaz.")
