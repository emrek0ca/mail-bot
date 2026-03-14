from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mail_bot.config import load_settings, save_settings
from mail_bot.database import Database
from mail_bot.models import Settings
from mail_bot.secure_store import SecureStoreError


class ConfigSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "mailbot.db")
        self.db.init_db()
        self.secret_store: dict[str, str] = {}

    def tearDown(self) -> None:
        self.db.close()
        self.tempdir.cleanup()

    def test_secrets_saved_outside_database(self) -> None:
        settings = Settings(
            gemini_api_key="secret-key",
            openai_api_key="openai-secret",
            gmail_app_password="app-pass",
            user_name="Emre",
        )
        with (
            patch("mail_bot.config.save_secrets", lambda values: self.secret_store.update(values)),
            patch("mail_bot.config.load_secrets", lambda: dict(self.secret_store)),
            patch("mail_bot.config.migrate_legacy_secrets", lambda getter, setter: None),
        ):
            save_settings(settings, self.db)
            loaded = load_settings(self.db)

        self.assertEqual(loaded.gemini_api_key, "secret-key")
        self.assertEqual(loaded.openai_api_key, "openai-secret")
        self.assertEqual(loaded.gmail_app_password, "app-pass")
        self.assertEqual(self.db.get_setting("gemini_api_key"), "")
        self.assertEqual(self.db.get_setting("openai_api_key"), "")
        self.assertEqual(self.db.get_setting("gmail_app_password"), "")

    def test_falls_back_to_database_when_secure_store_fails(self) -> None:
        settings = Settings(
            gemini_api_key="secret-key",
            openai_api_key="openai-secret",
            gmail_app_password="app-pass",
            user_name="Emre",
        )
        with (
            patch("mail_bot.config.save_secrets", side_effect=SecureStoreError("fail")),
            patch("mail_bot.config.load_secrets", side_effect=SecureStoreError("fail")),
            patch("mail_bot.config.migrate_legacy_secrets", side_effect=SecureStoreError("fail")),
        ):
            save_settings(settings, self.db)
            loaded = load_settings(self.db)

        self.assertEqual(loaded.gemini_api_key, "secret-key")
        self.assertEqual(loaded.openai_api_key, "openai-secret")
        self.assertEqual(loaded.gmail_app_password, "app-pass")
        self.assertEqual(self.db.get_setting("gemini_api_key"), "secret-key")
        self.assertEqual(self.db.get_setting("openai_api_key"), "openai-secret")
        self.assertEqual(self.db.get_setting("gmail_app_password"), "app-pass")

    def test_database_secret_wins_over_stale_secure_store_value(self) -> None:
        self.db.set_setting("gemini_api_key", "fresh-db-key")
        self.db.set_setting("openai_api_key", "fresh-openai-key")
        self.db.set_setting("gmail_app_password", "fresh-db-pass")
        with (
            patch(
                "mail_bot.config.load_secrets",
                return_value={
                    "gemini_api_key": "stale-keychain",
                    "openai_api_key": "stale-openai",
                    "gmail_app_password": "stale-pass",
                },
            ),
            patch("mail_bot.config.migrate_legacy_secrets", lambda getter, setter: None),
        ):
            loaded = load_settings(self.db)

        self.assertEqual(loaded.gemini_api_key, "fresh-db-key")
        self.assertEqual(loaded.openai_api_key, "fresh-openai-key")
        self.assertEqual(loaded.gmail_app_password, "fresh-db-pass")
