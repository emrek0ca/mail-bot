from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from . import DATA_DIR, DEFAULT_DB_PATH
from .models import CompanyRecord, InteractionRecord, Settings


SETTINGS_KEYS = (
    "ai_provider",
    "gemini_api_key",
    "gemini_model",
    "openai_api_key",
    "openai_model",
    "gmail_address",
    "gmail_app_password",
    "cv_path",
    "cv_path_secondary",
    "portfolio_pdf_path",
    "user_name",
    "user_title",
    "user_phone",
    "github_url",
    "linkedin_url",
    "portfolio_url",
    "target_roles",
    "expertise_areas",
    "project_highlights",
    "service_value_prop",
    "theme",
    "search_history",
)

COMPANY_EXTRA_COLUMNS: dict[str, str] = {
    "lead_type": "TEXT",
    "fit_score": "INTEGER",
    "fit_reasons": "TEXT",
    "hiring_signal_score": "INTEGER",
    "digital_need_score": "INTEGER",
    "company_size_guess": "TEXT",
    "decision_maker_candidates": "TEXT",
    "research_summary": "TEXT",
    "recommended_profile_variant": "TEXT",
    "recommended_attachment_key": "TEXT",
    "recommended_cta": "TEXT",
    "last_contact_stage": "TEXT",
    "routing_reason": "TEXT",
    "value_prop_brief": "TEXT",
    "recommended_reference_project": "TEXT",
    "thread_reference": "TEXT",
    "followup_due_at": "DATETIME",
}


class Database:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()

    def _connect(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(self.db_path, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA foreign_keys=ON")
            self._local.connection = connection
        return connection

    def close(self) -> None:
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None

    def init_db(self) -> None:
        connection = self._connect()
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                category        TEXT,
                city            TEXT,
                address         TEXT,
                phone           TEXT,
                website         TEXT,
                email           TEXT,
                email_source    TEXT,
                company_summary TEXT,
                mail_draft      TEXT,
                mail_subject    TEXT,
                status          TEXT DEFAULT 'pending',
                sent_at         DATETIME,
                error_message   TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS interactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id  INTEGER NOT NULL,
                stage       TEXT NOT NULL,
                note        TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            );
            """
        )
        self._migrate_company_columns(connection)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_interactions_company_id ON interactions(company_id, created_at DESC)")
        connection.commit()
        existing = {row["key"] for row in connection.execute("SELECT key FROM settings")}
        for key in SETTINGS_KEYS:
            if key not in existing:
                connection.execute("INSERT INTO settings(key, value) VALUES(?, '')", (key,))
        connection.commit()

    def insert_company(self, company: dict[str, Any]) -> int:
        payload = {
            "name": company.get("name", "").strip() or "İsimsiz İşletme",
            "category": company.get("category"),
            "city": company.get("city"),
            "address": company.get("address"),
            "phone": company.get("phone"),
            "website": company.get("website"),
            "email": company.get("email"),
            "email_source": company.get("email_source"),
            "company_summary": company.get("company_summary"),
            "mail_draft": company.get("mail_draft"),
            "mail_subject": company.get("mail_subject"),
            "lead_type": company.get("lead_type"),
            "fit_score": company.get("fit_score"),
            "fit_reasons": company.get("fit_reasons"),
            "hiring_signal_score": company.get("hiring_signal_score"),
            "digital_need_score": company.get("digital_need_score"),
            "company_size_guess": company.get("company_size_guess"),
            "decision_maker_candidates": company.get("decision_maker_candidates"),
            "research_summary": company.get("research_summary"),
            "recommended_profile_variant": company.get("recommended_profile_variant"),
            "recommended_attachment_key": company.get("recommended_attachment_key"),
            "recommended_cta": company.get("recommended_cta"),
            "last_contact_stage": company.get("last_contact_stage"),
            "routing_reason": company.get("routing_reason"),
            "value_prop_brief": company.get("value_prop_brief"),
            "recommended_reference_project": company.get("recommended_reference_project"),
            "thread_reference": company.get("thread_reference"),
            "followup_due_at": company.get("followup_due_at"),
            "status": company.get("status", "pending"),
            "sent_at": company.get("sent_at"),
            "error_message": company.get("error_message"),
        }
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(["?"] * len(payload))
        values = list(payload.values())
        connection = self._connect()
        cursor = connection.execute(
            f"INSERT INTO companies ({columns}) VALUES ({placeholders})",
            values,
        )
        connection.commit()
        return int(cursor.lastrowid)

    def upsert_company(self, company: dict[str, Any]) -> tuple[int, bool]:
        existing_id = self.find_existing_company_id(company)
        if existing_id is None:
            return self.insert_company(company), True

        current = self.get_company(existing_id)
        update_fields: dict[str, Any] = {}
        if current is not None:
            for key in (
                "name",
                "category",
                "city",
                "address",
                "phone",
                "website",
                "email",
                "email_source",
                "lead_type",
                "fit_score",
                "fit_reasons",
                "hiring_signal_score",
                "digital_need_score",
                "company_size_guess",
                "decision_maker_candidates",
                "research_summary",
                "recommended_profile_variant",
                "recommended_attachment_key",
                "recommended_cta",
                "last_contact_stage",
                "routing_reason",
                "value_prop_brief",
                "recommended_reference_project",
                "thread_reference",
                "followup_due_at",
            ):
                incoming = company.get(key)
                existing_value = getattr(current, key)
                if incoming not in (None, "") and incoming != existing_value:
                    update_fields[key] = incoming
        if update_fields:
            self.update_company(existing_id, **update_fields)
        return existing_id, False

    def find_existing_company_id(self, company: dict[str, Any]) -> int | None:
        candidates: list[int] = []
        website = _normalize_match_value(company.get("website"))
        email = _normalize_match_value(company.get("email"))
        name = _normalize_match_value(company.get("name"))
        city = _normalize_match_value(company.get("city"))
        connection = self._connect()

        if website:
            row = connection.execute(
                "SELECT id FROM companies WHERE lower(trim(COALESCE(website, ''))) = ? ORDER BY id DESC LIMIT 1",
                (website,),
            ).fetchone()
            if row:
                candidates.append(int(row["id"]))
        if email:
            row = connection.execute(
                "SELECT id FROM companies WHERE lower(trim(COALESCE(email, ''))) = ? ORDER BY id DESC LIMIT 1",
                (email,),
            ).fetchone()
            if row:
                candidates.append(int(row["id"]))
        if name:
            row = connection.execute(
                """
                SELECT id FROM companies
                WHERE lower(trim(name)) = ?
                  AND lower(trim(COALESCE(city, ''))) = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (name, city or ""),
            ).fetchone()
            if row:
                candidates.append(int(row["id"]))

        return candidates[0] if candidates else None

    def update_company(self, company_id: int, **fields: Any) -> None:
        clean_fields = {key: value for key, value in fields.items() if key}
        if not clean_fields:
            return
        assignments = ", ".join(f"{key} = ?" for key in clean_fields)
        values = list(clean_fields.values()) + [company_id]
        connection = self._connect()
        connection.execute(f"UPDATE companies SET {assignments} WHERE id = ?", values)
        connection.commit()

    def get_company(self, company_id: int) -> CompanyRecord | None:
        row = self._connect().execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        return CompanyRecord.from_row(row) if row else None

    def list_companies(self) -> list[CompanyRecord]:
        rows = self._connect().execute("SELECT * FROM companies ORDER BY id DESC").fetchall()
        return [CompanyRecord.from_row(row) for row in rows]

    def list_by_status(self, status: str) -> list[CompanyRecord]:
        rows = self._connect().execute(
            "SELECT * FROM companies WHERE status = ? ORDER BY id ASC",
            (status,),
        ).fetchall()
        return [CompanyRecord.from_row(row) for row in rows]

    def list_interactions(self, company_id: int, limit: int = 20) -> list[InteractionRecord]:
        rows = self._connect().execute(
            "SELECT * FROM interactions WHERE company_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (company_id, limit),
        ).fetchall()
        return [InteractionRecord.from_row(row) for row in rows]

    def add_interaction(self, company_id: int, stage: str, note: str | None = None) -> None:
        connection = self._connect()
        connection.execute(
            "INSERT INTO interactions(company_id, stage, note) VALUES(?, ?, ?)",
            (company_id, stage, note),
        )
        connection.execute(
            "UPDATE companies SET last_contact_stage = ? WHERE id = ?",
            (stage, company_id),
        )
        connection.commit()

    def clear_companies(self) -> None:
        connection = self._connect()
        connection.execute("DELETE FROM interactions")
        connection.execute("DELETE FROM companies")
        connection.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self._connect().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if not row:
            return default
        return row["value"] or default

    def set_setting(self, key: str, value: str) -> None:
        connection = self._connect()
        connection.execute(
            """
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        connection.commit()

    def load_settings(self) -> Settings:
        rows = self._connect().execute(
            "SELECT key, value FROM settings WHERE key NOT LIKE 'sent_count_%'"
        ).fetchall()
        return Settings.from_mapping({row["key"]: row["value"] for row in rows})

    def save_settings(self, settings: Settings) -> None:
        for key, value in settings.as_mapping().items():
            self.set_setting(key, value)

    def daily_count_key(self, now: datetime | None = None) -> str:
        current = now or datetime.now()
        return f"sent_count_{current.strftime('%Y_%m_%d')}"

    def get_daily_send_count(self, now: datetime | None = None) -> int:
        raw_value = self.get_setting(self.daily_count_key(now), "0")
        try:
            return int(raw_value)
        except ValueError:
            return 0

    def increment_daily_send_count(self, amount: int = 1, now: datetime | None = None) -> int:
        key = self.daily_count_key(now)
        next_value = self.get_daily_send_count(now) + amount
        self.set_setting(key, str(next_value))
        return next_value

    def list_companies_raw(self) -> list[dict[str, Any]]:
        rows = self._connect().execute("SELECT * FROM companies ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def _migrate_company_columns(self, connection: sqlite3.Connection) -> None:
        existing = {row["name"] for row in connection.execute("PRAGMA table_info(companies)")}
        for column_name, column_type in COMPANY_EXTRA_COLUMNS.items():
            if column_name not in existing:
                connection.execute(f"ALTER TABLE companies ADD COLUMN {column_name} {column_type}")


def _normalize_match_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()
