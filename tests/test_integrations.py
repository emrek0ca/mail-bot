from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from mail_bot.integrations import check_ai, check_gemini, check_gmail, check_openai, check_playwright
from mail_bot.models import IntegrationCheckResult, Settings


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_ai_check_routes_to_openai(self) -> None:
        with patch("mail_bot.integrations.check_openai", new=AsyncMock(return_value=IntegrationCheckResult("openai", True, "ok"))):
            result = await check_ai(Settings(ai_provider="openai", openai_api_key="key"))
        self.assertTrue(result.ok)
        self.assertEqual(result.service, "openai")

    async def test_gemini_check_reports_success(self) -> None:
        fake_client = AsyncMock()
        fake_client.generate.return_value = "OK"
        with patch("mail_bot.integrations.GeminiClient", return_value=fake_client):
            result = await check_gemini(Settings(gemini_api_key="key", gemini_model="gemini-test"))
        self.assertTrue(result.ok)
        self.assertIn("gemini-test", result.message)

    async def test_openai_check_reports_success(self) -> None:
        fake_client = AsyncMock()
        fake_client.generate.return_value = "OK"
        with patch("mail_bot.integrations.OpenAIClient", return_value=fake_client):
            result = await check_openai(Settings(ai_provider="openai", openai_api_key="key", openai_model="gpt-5-mini"))
        self.assertTrue(result.ok)
        self.assertIn("gpt-5-mini", result.message)

    async def test_gmail_check_reports_failure(self) -> None:
        with patch("mail_bot.integrations.validate_gmail_credentials", return_value=type("R", (), {"ok": False, "error_message": "auth fail"})()):
            result = await check_gmail(Settings(gmail_address="a@b.com", gmail_app_password="x"))
        self.assertFalse(result.ok)
        self.assertEqual(result.message, "auth fail")

    async def test_playwright_check_passes_through(self) -> None:
        expected = IntegrationCheckResult("playwright", True, "ready")
        with patch("mail_bot.integrations.validate_playwright_setup", new=AsyncMock(return_value=expected)):
            result = await check_playwright()
        self.assertTrue(result.ok)
        self.assertEqual(result.message, "ready")
