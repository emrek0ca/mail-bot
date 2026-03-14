from __future__ import annotations

import asyncio

from .ai.gemini_client import GeminiClient
from .ai.openai_client import OpenAIClient
from .mailer.gmail_sender import validate_gmail_credentials
from .models import IntegrationCheckResult, Settings
from .scraper.maps_scraper import validate_playwright_setup


async def check_ai(settings: Settings) -> IntegrationCheckResult:
    if settings.normalized_provider == "openai":
        return await check_openai(settings)
    return await check_gemini(settings)


async def check_gemini(settings: Settings) -> IntegrationCheckResult:
    if not settings.gemini_api_key.strip():
        return IntegrationCheckResult("gemini", False, "Gemini API key girilmemis.")
    try:
        client = GeminiClient(settings.gemini_api_key, settings.normalized_model, min_interval_seconds=0, retry_delay_seconds=1)
        reply = await client.generate("Sadece su metni yaz: OK")
        normalized = reply.strip().upper()
        if "OK" not in normalized:
            return IntegrationCheckResult("gemini", False, f"Beklenmeyen Gemini yaniti: {reply[:120]}")
        return IntegrationCheckResult("gemini", True, f"Gemini baglantisi hazir. Model: {settings.normalized_model}")
    except Exception as exc:
        return IntegrationCheckResult("gemini", False, str(exc))


async def check_openai(settings: Settings) -> IntegrationCheckResult:
    if not settings.openai_api_key.strip():
        return IntegrationCheckResult("openai", False, "OpenAI API key girilmemis.")
    try:
        client = OpenAIClient(settings.openai_api_key, settings.normalized_openai_model, min_interval_seconds=0, retry_delay_seconds=1)
        reply = await client.generate("Sadece su metni yaz: OK")
        normalized = reply.strip().upper()
        if "OK" not in normalized:
            return IntegrationCheckResult("openai", False, f"Beklenmeyen OpenAI yaniti: {reply[:120]}")
        return IntegrationCheckResult("openai", True, f"OpenAI baglantisi hazir. Model: {settings.normalized_openai_model}")
    except Exception as exc:
        return IntegrationCheckResult("openai", False, str(exc))


async def check_gmail(settings: Settings) -> IntegrationCheckResult:
    if not settings.gmail_address or not settings.gmail_app_password:
        return IntegrationCheckResult("gmail", False, "Gmail adresi veya uygulama sifresi eksik.")
    result = await asyncio.to_thread(validate_gmail_credentials, settings.gmail_address, settings.gmail_app_password)
    if result.ok:
        return IntegrationCheckResult("gmail", True, "Gmail SMTP girisi basarili.")
    return IntegrationCheckResult("gmail", False, result.error_message or "Gmail SMTP dogrulamasi basarisiz.")


async def check_playwright() -> IntegrationCheckResult:
    result = await validate_playwright_setup()
    if result.ok:
        return result
    return result
