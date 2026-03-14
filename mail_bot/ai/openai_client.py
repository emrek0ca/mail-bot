from __future__ import annotations

import asyncio
import time
from typing import Any

from .. import DEFAULT_OPENAI_MODEL


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        model_name: str | None = None,
        *,
        min_interval_seconds: float = 1.0,
        retry_delay_seconds: float = 10.0,
        max_retries: int = 3,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.model_name = (model_name or DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
        self.min_interval_seconds = min_interval_seconds
        self.retry_delay_seconds = retry_delay_seconds
        self.max_retries = max_retries
        self._client = client
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise RuntimeError("OpenAI API key ayarlanmamis.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai paketi kurulu degil.") from exc
        self._client = OpenAI(api_key=self.api_key)
        return self._client

    async def generate(self, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self._lock:
                    elapsed = time.time() - self._last_request_time
                    if elapsed < self.min_interval_seconds:
                        await asyncio.sleep(self.min_interval_seconds - elapsed)
                    client = self._ensure_client()
                    response = await asyncio.to_thread(
                        client.responses.create,
                        model=self.model_name,
                        input=prompt,
                    )
                    self._last_request_time = time.time()
                text = _extract_response_text(response)
                if not text:
                    raise RuntimeError("OpenAI bos yanit dondu.")
                return text.strip()
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries and _is_retryable_error(exc):
                    await asyncio.sleep(self.retry_delay_seconds)
                    continue
                break
        raise RuntimeError(f"OpenAI istegi basarisiz: {last_error}") from last_error


_CLIENT_CACHE: dict[tuple[str, str], OpenAIClient] = {}


def get_shared_client(api_key: str, model_name: str | None = None) -> OpenAIClient:
    normalized_model = (model_name or DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    cache_key = (api_key.strip(), normalized_model)
    client = _CLIENT_CACHE.get(cache_key)
    if client is None:
        client = OpenAIClient(api_key, normalized_model)
        _CLIENT_CACHE[cache_key] = client
    return client


def clear_shared_clients() -> None:
    _CLIENT_CACHE.clear()


def _is_retryable_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "temporarily unavailable" in text


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = getattr(response, "output", None) or []
    collected: list[str] = []
    for item in output:
        content = getattr(item, "content", None) or []
        for part in content:
            text = getattr(part, "text", None)
            if text:
                collected.append(str(text))
    return "\n".join(segment.strip() for segment in collected if segment and segment.strip()).strip()
