from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mail_bot.mailer.gmail_sender import send_mail
from mail_bot.security import normalize_public_url, validate_recipient_email


class _FakeSMTP:
    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.logged_in = None
        self.sent = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def login(self, username: str, password: str) -> None:
        self.logged_in = (username, password)

    def sendmail(self, from_addr: str, to_addr: str, message: str) -> None:
        self.sent = (from_addr, to_addr, message)


class SecurityAndSenderTests(unittest.TestCase):
    def test_blocks_local_urls(self) -> None:
        with self.assertRaises(ValueError):
            normalize_public_url("http://127.0.0.1/admin")
        with self.assertRaises(ValueError):
            normalize_public_url("file:///tmp/test")

    def test_email_validation_blocks_header_injection(self) -> None:
        with self.assertRaises(ValueError):
            validate_recipient_email("victim@example.com\nBcc:bad@example.com")

    def test_sender_rejects_injected_subject(self) -> None:
        result = send_mail(
            "sender@example.com",
            "secret",
            "target@example.com",
            "Merhaba\nBcc:attacker@example.com",
            "Body",
        )
        self.assertFalse(result.ok)

    def test_sender_uses_sanitized_fields(self) -> None:
        smtp_instances: list[_FakeSMTP] = []

        def factory(host: str, port: int, timeout: int):
            instance = _FakeSMTP(host, port, timeout)
            smtp_instances.append(instance)
            return instance

        with patch("mail_bot.mailer.gmail_sender.smtplib.SMTP_SSL", new=factory):
            result = send_mail("sender@example.com", "secret", "target@example.com", "Merhaba", "Body")

        self.assertTrue(result.ok)
        self.assertEqual(smtp_instances[0].logged_in, ("sender@example.com", "secret"))
        assert smtp_instances[0].sent is not None
        self.assertEqual(smtp_instances[0].sent[1], "target@example.com")

    def test_sender_attaches_multiple_files(self) -> None:
        smtp_instances: list[_FakeSMTP] = []

        def factory(host: str, port: int, timeout: int):
            instance = _FakeSMTP(host, port, timeout)
            smtp_instances.append(instance)
            return instance

        with tempfile.TemporaryDirectory() as tempdir:
            first = Path(tempdir) / "cv.pdf"
            second = Path(tempdir) / "portfolio.pdf"
            first.write_bytes(b"%PDF-1.4 one")
            second.write_bytes(b"%PDF-1.4 two")
            with patch("mail_bot.mailer.gmail_sender.smtplib.SMTP_SSL", new=factory):
                result = send_mail(
                    "sender@example.com",
                    "secret",
                    "target@example.com",
                    "Merhaba",
                    "Body",
                    attachment_paths=[str(first), str(second)],
                )

        self.assertTrue(result.ok)
        assert smtp_instances[0].sent is not None
        self.assertIn("cv.pdf", smtp_instances[0].sent[2])
        self.assertIn("portfolio.pdf", smtp_instances[0].sent[2])
