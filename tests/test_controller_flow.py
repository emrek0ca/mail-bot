from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mail_bot.app_controller import AppController
from mail_bot.database import Database


class ControllerFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mailbot.db")
        self.controller = AppController(self.db)
        self.company_id = self.db.insert_company({"name": "Acme", "city": "Istanbul", "website": "https://example.com"})

    def tearDown(self) -> None:
        self.controller.shutdown()
        self.tempdir.cleanup()

    def test_reject_company_updates_status_and_history(self) -> None:
        self.controller.reject_company(self.company_id, "Uygun degil")
        company = self.db.get_company(self.company_id)
        assert company is not None
        self.assertEqual(company.status, "rejected")
        interactions = self.controller.get_interactions(self.company_id)
        self.assertEqual(interactions[0].stage, "rejected")
        self.assertIn("Uygun degil", interactions[0].note or "")

    def test_clear_companies_removes_records_and_emits_event(self) -> None:
        self.db.add_interaction(self.company_id, "found", "Maps sonucu")
        self.controller.clear_companies()
        self.assertEqual(self.controller.list_companies(), [])
        events = self.controller.poll_events()
        event_types = [event["type"] for event in events]
        self.assertIn("companies_cleared", event_types)
