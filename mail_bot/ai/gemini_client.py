from __future__ import annotations

import asyncio
import time
from typing import Any

from .. import DEFAULT_GEMINI_MODEL


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model_name: str | None = None,
        *,
        min_interval_seconds: float = 4.5,
        retry_delay_seconds: float = 60.0,
        max_retries: int = 3,
        model: Any | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.model_name = (model_name or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
        self.min_interval_seconds = min_interval_seconds
        self.retry_delay_seconds = retry_delay_seconds
        self.max_retries = max_retries
        self._model = model
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        if not self.api_key:
            raise RuntimeError("Gemini API key ayarlanmamis.")
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError("google-generativeai paketi kurulu degil.") from exc
        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model_name)
        return self._model

    async def generate(self, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self._lock:
                    elapsed = time.time() - self._last_request_time
                    if elapsed < self.min_interval_seconds:
                        await asyncio.sleep(self.min_interval_seconds - elapsed)
                    model = self._ensure_model()
                    response = await asyncio.to_thread(model.generate_content, prompt)
                    self._last_request_time = time.time()
                text = _extract_response_text(response)
                if not text:
                    raise RuntimeError("Gemini bos yanit dondu.")
                return text.strip()
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries and _is_rate_limit_error(exc):
                    await asyncio.sleep(self.retry_delay_seconds)
                    continue
                break
        raise RuntimeError(f"Gemini istegi basarisiz: {last_error}") from last_error


_CLIENT_CACHE: dict[tuple[str, str], GeminiClient] = {}


def get_shared_client(api_key: str, model_name: str | None = None) -> GeminiClient:
    normalized_model = (model_name or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    cache_key = (api_key.strip(), normalized_model)
    client = _CLIENT_CACHE.get(cache_key)
    if client is None:
        client = GeminiClient(api_key, normalized_model)
        _CLIENT_CACHE[cache_key] = client
    return client


def clear_shared_clients() -> None:
    _CLIENT_CACHE.clear()


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "resource_exhausted" in text or "rate limit" in text


def _extract_response_text(response: Any) -> str:
    direct = getattr(response, "text", None)
    if isinstance(direct, str) and direct.strip():
        return direct

    candidates = getattr(response, "candidates", None) or []
    collected: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                collected.append(str(text))
    return "\n".join(segment.strip() for segment in collected if segment and segment.strip()).strip()
