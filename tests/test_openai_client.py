from __future__ import annotations

import unittest

from mail_bot.ai.mail_writer import compose_mail_message
from mail_bot.ai.openai_client import OpenAIClient
from mail_bot.ai.lead_strategy import LeadStrategy
from mail_bot.models import CompanyRecord, Settings


class _FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class _FallbackResponse:
    def __init__(self) -> None:
        self.output_text = ""
        self.output = [type("Item", (), {"content": [type("Part", (), {"text": "OK"})()]})()]


class _FakeResponsesAPI:
    def __init__(self, response) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def create(self, *, model: str, input: str):
        self.calls.append((model, input))
        return self.response


class _FakeOpenAI:
    def __init__(self, response) -> None:
        self.responses = _FakeResponsesAPI(response)


class OpenAIClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_selected_model_used(self) -> None:
        fake_client = _FakeOpenAI(_FakeResponse("KONU: Merhaba\nGovde"))
        client = OpenAIClient("key", "gpt-5-mini", min_interval_seconds=0, retry_delay_seconds=0, client=fake_client)
        text = await client.generate("prompt")
        self.assertEqual(text, "KONU: Merhaba\nGovde")
        self.assertEqual(fake_client.responses.calls, [("gpt-5-mini", "prompt")])

    async def test_falls_back_to_output_parts_when_output_text_empty(self) -> None:
        client = OpenAIClient("key", "gpt-5-mini", min_interval_seconds=0, retry_delay_seconds=0, client=_FakeOpenAI(_FallbackResponse()))
        text = await client.generate("prompt")
        self.assertEqual(text, "OK")

    def test_compose_mail_message_builds_structured_job_mail(self) -> None:
        strategy = LeadStrategy(
            lead_type="job",
            fit_score=90,
            fit_reasons=[],
            company_summary="Ozet",
            research_summary="Arastirma",
            recommended_profile_variant="Odak",
            recommended_cta="CTA",
            routing_reason="Reason",
            value_prop_brief="Brief",
            recommended_reference_project="Proje",
            mail_subject="Test Konusu",
            mail_body="Test Govdesi",
            recommended_attachment_key="primary_cv"
        )
        settings = Settings(
            user_name="Emre Koca",
            user_title="Developer",
            target_roles="Backend Developer, Full Stack Developer",
            expertise_areas="Python, FastAPI, React",
            user_phone="05551234567",
            linkedin_url="https://linkedin.com/in/emrekoca",
        )
        subject, body = compose_mail_message(strategy, settings)
        self.assertEqual(subject, "Test Konusu")
        self.assertIn("Test Govdesi", body)
        self.assertIn("Emre Koca", body)
        self.assertIn("05551234567", body)
        self.assertIn("https://linkedin.com/in/emrekoca", body)
