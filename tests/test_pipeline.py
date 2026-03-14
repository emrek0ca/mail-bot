from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mail_bot.ai.lead_strategy import LeadStrategy
from mail_bot.database import Database
from mail_bot.main_pipeline import process_company
from mail_bot.models import Settings
from mail_bot.scraper.company_research import ResearchBundle


class _Notifier:
    def __init__(self) -> None:
        self.logs: list[str] = []
        self.refreshed: list[int] = []

    async def log(self, message: str) -> None:
        self.logs.append(message)

    async def refresh_company(self, company_id: int) -> None:
        self.refreshed.append(company_id)

    async def request_manual_email(self, company_id: int, company_name: str) -> str | None:
        return "manual@example.com"


class _FakeGemini:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.responses = iter(["Kucuk ekip"])

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return next(self.responses)


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mailbot.db")
        self.db.init_db()
        self.company_id = self.db.insert_company(
            {
                "name": "Acme - Uzun Listeleme Basligi",
                "city": "Istanbul",
                "website": "https://example.com",
                "category": "Yazilim",
            }
        )
        self.notifier = _Notifier()
        self.settings = Settings(gemini_api_key="key", gemini_model="gemini-custom", user_name="Emre", user_title="Developer")

    async def asyncTearDown(self) -> None:
        self.db.close()
        self.tempdir.cleanup()

    async def test_pipeline_updates_draft(self) -> None:
        fake_client = _FakeGemini()
        strategy = LeadStrategy(
            lead_type="job",
            fit_score=82,
            fit_reasons=["Hiring sinyali var."],
            company_summary="Ozet",
            research_summary="Kucuk ekip",
            recommended_profile_variant="Odak: full stack",
            recommended_cta="Gorusmek isterim.",
            routing_reason="Ise alim sinyali",
            value_prop_brief="Teknik katkı",
            recommended_reference_project="Portal projesi",
            mail_subject="Yazılım Geliştirici Başvurusu - Emre",
            mail_body="Acme firmasında CV'm ekte.",
            recommended_attachment_key="all"
        )
        research = ResearchBundle(
            visited_urls=["https://example.com"],
            page_texts={"home": "Website text"},
            combined_text="Website text",
            hiring_signal_score=75,
            digital_need_score=35,
            company_size_guess="orta",
            decision_maker_candidates=["CTO - tech@example.com"],
            detected_tech_stack=["React", "Node.js"],
            has_active_job_board_postings=True,
            weak_signal=False,
        )
        with (
            patch("mail_bot.main_pipeline.find_email", new=AsyncMock(return_value=type("R", (), {"email": "jobs@example.com", "source": "scraped", "error": None})())),
            patch("mail_bot.main_pipeline.enrich_company_website", new=AsyncMock(return_value=research)),
            patch("mail_bot.main_pipeline.plan_lead_strategy", new=AsyncMock(return_value=strategy)),
            patch("mail_bot.main_pipeline.get_ai_client", return_value=fake_client),
        ):
            await process_company(self.company_id, self.settings, self.db, self.notifier)

        company = self.db.get_company(self.company_id)
        self.assertIsNotNone(company)
        assert company is not None
        self.assertEqual(company.email, "jobs@example.com")
        self.assertEqual(company.lead_type, "job")
        self.assertEqual(company.fit_score, 82)
        self.assertEqual(company.mail_subject, "Yazılım Geliştirici Başvurusu - Emre")
        self.assertIn("CV'm ekte.", company.mail_draft or "")
        self.assertIn("Acme", company.mail_draft or "")
        self.assertNotIn("Uzun Listeleme Basligi", company.mail_draft or "")

    async def test_sent_company_is_not_reprocessed(self) -> None:
        self.db.update_company(self.company_id, status="sent", sent_at="2026-03-13 10:00:00")
        fake_client = _FakeGemini()
        with (
            patch("mail_bot.main_pipeline.find_email", new=AsyncMock()),
            patch("mail_bot.main_pipeline.enrich_company_website", new=AsyncMock()),
            patch("mail_bot.main_pipeline.plan_lead_strategy", new=AsyncMock()),
            patch("mail_bot.main_pipeline.get_ai_client", return_value=fake_client),
        ):
            await process_company(self.company_id, self.settings, self.db, self.notifier)

        company = self.db.get_company(self.company_id)
        assert company is not None
        self.assertEqual(company.status, "sent")
        self.assertTrue(any("Daha once mail gonderildi" in message for message in self.notifier.logs))
