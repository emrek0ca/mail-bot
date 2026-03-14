from __future__ import annotations

import unittest

from mail_bot.scraper.email_finder import extract_valid_emails, guess_email_from_domain, is_valid_email


class EmailFinderTests(unittest.TestCase):
    def test_extracts_email_and_mailto(self) -> None:
        html = """
        <html>
            <body>
                <a href="mailto:hello@example.com">Mail</a>
                <p>Reach us at contact@company.com</p>
            </body>
        </html>
        """
        emails = extract_valid_emails(html)
        self.assertEqual(emails, ["contact@company.com", "hello@example.com"])

    def test_filters_placeholder_and_images(self) -> None:
        self.assertFalse(is_valid_email("noreply@company.com"))
        self.assertFalse(is_valid_email("mail.png"))
        self.assertTrue(is_valid_email("jobs@company.com"))

    def test_guesses_domain_email(self) -> None:
        self.assertEqual(guess_email_from_domain("https://www.example.org"), "info@example.org")

