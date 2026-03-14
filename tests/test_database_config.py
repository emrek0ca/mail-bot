from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mail_bot.config import load_settings, save_settings
from mail_bot.database import Database
from mail_bot.models import Settings


class DatabaseConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "mailbot.db"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self) -> None:
        self.db.close()
        self.tempdir.cleanup()

    def test_settings_persist_model(self) -> None:
        settings = Settings(
            ai_provider="openai",
            gemini_api_key="abc",
            gemini_model="gemini-pro",
            openai_model="gpt-5-mini",
            user_name="Emre",
            user_phone="05551234567",
            github_url="https://github.com/emre",
            target_roles="Backend Engineer",
        )
        save_settings(settings, self.db)
        loaded = load_settings(self.db)
        self.assertEqual(loaded.ai_provider, "openai")
        self.assertEqual(loaded.gemini_model, "gemini-pro")
        self.assertEqual(loaded.openai_model, "gpt-5-mini")
        self.assertEqual(loaded.user_name, "Emre")
        self.assertEqual(loaded.user_phone, "05551234567")
        self.assertEqual(loaded.github_url, "https://github.com/emre")
        self.assertEqual(loaded.target_roles, "Backend Engineer")

    def test_default_model_is_used_when_blank(self) -> None:
        settings = Settings(gemini_model="")
        save_settings(settings, self.db)
        loaded = load_settings(self.db)
        self.assertEqual(loaded.normalized_model, "gemini-2.5-flash")

    def test_legacy_model_is_upgraded(self) -> None:
        settings = Settings(gemini_model="gemini-1.5-flash")
        save_settings(settings, self.db)
        loaded = load_settings(self.db)
        self.assertEqual(loaded.normalized_model, "gemini-2.5-flash")

    def test_openai_model_defaults_when_blank(self) -> None:
        settings = Settings(ai_provider="openai", openai_model="")
        save_settings(settings, self.db)
        loaded = load_settings(self.db)
        self.assertEqual(loaded.normalized_openai_model, "gpt-5-mini")

    def test_upsert_preserves_existing_sent_company(self) -> None:
        company_id = self.db.insert_company(
            {
                "name": "Acme",
                "city": "Istanbul",
                "website": "https://example.com",
                "status": "sent",
                "sent_at": "2026-03-13 10:00:00",
            }
        )
        matched_id, created = self.db.upsert_company(
            {
                "name": "Acme",
                "city": "Istanbul",
                "website": "https://example.com",
                "phone": "555",
            }
        )
        self.assertFalse(created)
        self.assertEqual(matched_id, company_id)
        company = self.db.get_company(company_id)
        assert company is not None
        self.assertEqual(company.status, "sent")
        self.assertEqual(company.phone, "555")

    def test_interactions_are_recorded(self) -> None:
        company_id = self.db.insert_company({"name": "Acme", "city": "Istanbul", "website": "https://example.com"})
        self.db.add_interaction(company_id, "found", "Maps sonucu")
        self.db.add_interaction(company_id, "draft_ready", "Taslak olustu")
        company = self.db.get_company(company_id)
        assert company is not None
        self.assertEqual(company.last_contact_stage, "draft_ready")
        interactions = self.db.list_interactions(company_id)
        self.assertEqual(len(interactions), 2)
        self.assertEqual(interactions[0].stage, "draft_ready")
