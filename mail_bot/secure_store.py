from __future__ import annotations

from typing import Iterable

SERVICE_NAME = "mail_bot"
SECRET_KEYS = ("gemini_api_key", "openai_api_key", "gmail_app_password")


class SecureStoreError(RuntimeError):
    pass


def get_secret(key: str) -> str:
    keyring = _load_keyring()
    try:
        return keyring.get_password(SERVICE_NAME, key) or ""
    except Exception as exc:
        raise SecureStoreError(f"Gizli veri okunamadi: {key}") from exc


def set_secret(key: str, value: str) -> None:
    keyring = _load_keyring()
    try:
        if value:
            keyring.set_password(SERVICE_NAME, key, value)
        else:
            try:
                keyring.delete_password(SERVICE_NAME, key)
            except Exception:
                pass
    except Exception as exc:
        raise SecureStoreError(f"Gizli veri kaydedilemedi: {key}") from exc


def load_secrets(keys: Iterable[str] = SECRET_KEYS) -> dict[str, str]:
    return {key: get_secret(key) for key in keys}


def save_secrets(values: dict[str, str]) -> None:
    for key, value in values.items():
        if key in SECRET_KEYS:
            set_secret(key, value.strip())


def migrate_legacy_secrets(getter, setter, keys: Iterable[str] = SECRET_KEYS) -> None:
    for key in keys:
        legacy_value = getter(key)
        if not legacy_value:
            continue
        if get_secret(key):
            setter(key, "")
            continue
        set_secret(key, legacy_value)
        setter(key, "")


def _load_keyring():
    try:
        import keyring
    except ImportError as exc:
        raise SecureStoreError("keyring paketi kurulu degil.") from exc
    return keyring
