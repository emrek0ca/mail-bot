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
        self.manual_requests = 0

    async def log(self, message: str) -> None:
        return None

    async def refresh_company(self, company_id: int) -> None:
        return None

    async def request_manual_email(self, company_id: int, company_name: str) -> str | None:
        self.manual_requests += 1
        return "manual@example.com"


class _FakeGemini:
    def __init__(self) -> None:
        self.responses = iter(["Ozet"])

    async def generate(self, prompt: str) -> str:
        return next(self.responses)


class PipelineManualEmailTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mailbot.db")
        self.db.init_db()
        self.company_id = self.db.insert_company({"name": "Acme", "city": "Istanbul", "website": "https://example.com"})
        self.settings = Settings(gemini_api_key="key", user_name="Emre", user_title="Developer")
        self.notifier = _Notifier()

    async def asyncTearDown(self) -> None:
        self.db.close()
        self.tempdir.cleanup()

    async def test_pipeline_requests_manual_email_when_lookup_fails(self) -> None:
        fake_client = _FakeGemini()
        email_result = type("R", (), {"email": None, "source": "not_found", "error": None})()
        strategy = LeadStrategy(
            lead_type="job",
            fit_score=74,
            fit_reasons=["Dijital ihtiyac var."],
            company_summary="Ozet",
            research_summary="Ozet",
            recommended_profile_variant="Odak: otomasyon",
            recommended_cta="Goruselim.",
            routing_reason="Hizmet daha uygun",
            value_prop_brief="Hizli deger",
            recommended_reference_project="CRM projesi",
            mail_subject="Yazılım Geliştirici Başvurusu - Emre",
            mail_body="CV'm ekte.",
            recommended_attachment_key="all"
        )
        research = ResearchBundle(
            visited_urls=["https://example.com"],
            page_texts={"home": "Website text"},
            combined_text="Website text",
            hiring_signal_score=10,
            digital_need_score=80,
            company_size_guess="kucuk",
            decision_maker_candidates=[],
            detected_tech_stack=["WordPress"],
            has_active_job_board_postings=False,
            weak_signal=False,
        )
        with (
            patch("mail_bot.main_pipeline.find_email", new=AsyncMock(return_value=email_result)),
            patch("mail_bot.main_pipeline.enrich_company_website", new=AsyncMock(return_value=research)),
            patch("mail_bot.main_pipeline.plan_lead_strategy", new=AsyncMock(return_value=strategy)),
            patch("mail_bot.main_pipeline.get_ai_client", return_value=fake_client),
        ):
            await process_company(self.company_id, self.settings, self.db, self.notifier)

        company = self.db.get_company(self.company_id)
        assert company is not None
        self.assertEqual(company.email, "manual@example.com")
        self.assertEqual(company.email_source, "manual")
        self.assertEqual(company.lead_type, "job")
        self.assertEqual(company.mail_subject, "Yazılım Geliştirici Başvurusu - Emre")
        self.assertIn("CV'm ekte.", company.mail_draft or "")
        self.assertEqual(self.notifier.manual_requests, 1)
