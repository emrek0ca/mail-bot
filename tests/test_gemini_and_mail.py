from __future__ import annotations

import unittest

from mail_bot.ai.gemini_client import GeminiClient


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _PartOnlyResponse:
    def __init__(self) -> None:
        self.text = ""
        self.candidates = [type("Candidate", (), {"content": type("Content", (), {"parts": [type("Part", (), {"text": "OK"})()]})()})()]


class _FakeModel:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_content(self, prompt: str) -> _FakeResponse:
        self.calls.append(prompt)
        return _FakeResponse("KONU: Merhaba\n\nGovde")


class GeminiAndMailTests(unittest.IsolatedAsyncioTestCase):
    async def test_selected_model_used(self) -> None:
        model = _FakeModel()
        client = GeminiClient("key", "gemini-custom", min_interval_seconds=0, retry_delay_seconds=0, model=model)
        text = await client.generate("prompt")
        self.assertEqual(text, "KONU: Merhaba\n\nGovde")
        self.assertEqual(client.model_name, "gemini-custom")
        self.assertEqual(model.calls, ["prompt"])

    async def test_falls_back_to_candidate_parts_when_text_empty(self) -> None:
        class _PartModel:
            def generate_content(self, prompt: str):
                return _PartOnlyResponse()

        client = GeminiClient("key", "gemini-custom", min_interval_seconds=0, retry_delay_seconds=0, model=_PartModel())
        text = await client.generate("prompt")
        self.assertEqual(text, "OK")
