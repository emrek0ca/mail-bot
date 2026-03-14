from __future__ import annotations

from typing import Protocol

from ..models import Settings
from .gemini_client import clear_shared_clients as clear_gemini_clients
from .gemini_client import get_shared_client as get_shared_gemini_client
from .openai_client import clear_shared_clients as clear_openai_clients
from .openai_client import get_shared_client as get_shared_openai_client


class AIClient(Protocol):
    async def generate(self, prompt: str) -> str: ...


def get_ai_client(settings: Settings) -> AIClient:
    if settings.normalized_provider == "openai":
        return get_shared_openai_client(settings.openai_api_key, settings.normalized_openai_model)
    return get_shared_gemini_client(settings.gemini_api_key, settings.normalized_model)


def clear_all_clients() -> None:
    clear_gemini_clients()
    clear_openai_clients()
