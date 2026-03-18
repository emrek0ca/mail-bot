from __future__ import annotations

from .database import Database
from .models import Settings
from .secure_store import SECRET_KEYS, SecureStoreError, load_secrets, migrate_legacy_secrets, save_secrets


def load_settings(db: Database | None = None) -> Settings:
    database = db or Database()
    database.init_db()
    settings = database.load_settings()
    merged = settings.as_mapping()
    db_secret_values = {key: database.get_setting(key, "") for key in SECRET_KEYS}
    try:
        migrate_legacy_secrets(database.get_setting, database.set_setting)
        secure_values = load_secrets()
        # If DB still has a secret value, it is the freshest fallback and must win
        # over any stale keychain value left from an earlier failed save.
        for key in SECRET_KEYS:
            merged[key] = db_secret_values.get(key, "").strip() or secure_values.get(key, "").strip()
    except SecureStoreError:
        for key in SECRET_KEYS:
            merged[key] = database.get_setting(key, "")
    return Settings.from_mapping(merged)


def save_settings(settings: Settings, db: Database | None = None) -> None:
    database = db or Database()
    database.init_db()
    stored_values = settings.as_mapping()
    try:
        # Secret'lari guvenli depoya kaydetmeyi dene
        save_secrets({key: getattr(settings, key) for key in SECRET_KEYS})
        # Eger basariliysa, DB'de bos birak (guvenlik icin)
        # NOT: Sadece deger gercekten varsa ve kaydedildiyse DB'den temizliyoruz
        for key in SECRET_KEYS:
            val = getattr(settings, key, "").strip()
            if val:
                stored_values[key] = ""
    except SecureStoreError:
        # Keyring hatasi varsa DB'deki veriyi oldugu gibi birak
        for key in SECRET_KEYS:
            stored_values[key] = getattr(settings, key)
    database.save_settings(Settings.from_mapping(stored_values))
