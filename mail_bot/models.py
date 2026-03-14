from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any

from . import DEFAULT_AI_PROVIDER, DEFAULT_GEMINI_MODEL, DEFAULT_OPENAI_MODEL, RECOMMENDED_FIT_SCORE

LEGACY_GEMINI_MODELS = {"gemini-1.5-flash"}
SUPPORTED_AI_PROVIDERS = {"gemini", "openai"}


@dataclass(slots=True)
class Settings:
    ai_provider: str = DEFAULT_AI_PROVIDER
    gemini_api_key: str = ""
    gemini_model: str = DEFAULT_GEMINI_MODEL
    openai_api_key: str = ""
    openai_model: str = DEFAULT_OPENAI_MODEL
    gmail_address: str = ""
    gmail_app_password: str = ""
    cv_path: str = ""
    cv_path_secondary: str = ""
    portfolio_pdf_path: str = ""
    user_name: str = ""
    user_title: str = ""
    user_phone: str = ""
    github_url: str = ""
    linkedin_url: str = ""
    portfolio_url: str = ""
    target_roles: str = ""
    expertise_areas: str = ""
    project_highlights: str = ""
    service_value_prop: str = ""
    theme: str = "System"
    search_history: str = ""

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> "Settings":
        known = {field.name: values.get(field.name, getattr(cls(), field.name)) for field in fields(cls)}
        settings = cls(**known)
        settings.ai_provider = _normalize_provider(settings.ai_provider)
        settings.gemini_model = _normalize_gemini_model_name(settings.gemini_model)
        settings.openai_model = _normalize_openai_model_name(settings.openai_model)
        return settings

    def as_mapping(self) -> dict[str, str]:
        data = {field.name: getattr(self, field.name) for field in fields(self)}
        data["ai_provider"] = self.normalized_provider
        data["gemini_model"] = self.normalized_model
        data["openai_model"] = self.normalized_openai_model
        return data

    @property
    def normalized_model(self) -> str:
        return _normalize_gemini_model_name(self.gemini_model)

    @property
    def normalized_openai_model(self) -> str:
        return _normalize_openai_model_name(self.openai_model)

    @property
    def normalized_provider(self) -> str:
        return _normalize_provider(self.ai_provider)

    @property
    def active_api_key(self) -> str:
        if self.normalized_provider == "openai":
            return self.openai_api_key.strip()
        return self.gemini_api_key.strip()

    @property
    def active_model(self) -> str:
        if self.normalized_provider == "openai":
            return self.normalized_openai_model
        return self.normalized_model

    @property
    def active_provider_label(self) -> str:
        if self.normalized_provider == "openai":
            return "OpenAI"
        return "Gemini"

    @property
    def attachment_paths(self) -> list[str]:
        return [path for path in (self.cv_path, self.cv_path_secondary, self.portfolio_pdf_path) if (path or "").strip()]

    @property
    def profile_links(self) -> list[str]:
        return [value.strip() for value in (self.portfolio_url, self.github_url, self.linkedin_url) if value.strip()]


def _normalize_provider(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in SUPPORTED_AI_PROVIDERS:
        return DEFAULT_AI_PROVIDER
    return normalized


def _normalize_gemini_model_name(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized or normalized in LEGACY_GEMINI_MODELS:
        return DEFAULT_GEMINI_MODEL
    return normalized


def _normalize_openai_model_name(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return DEFAULT_OPENAI_MODEL
    return normalized


@dataclass(slots=True)
class SearchQuery:
    sector: str
    city: str
    limit: int = 20

    @property
    def query_text(self) -> str:
        return f"{self.sector} {self.city}".strip()


@dataclass(slots=True)
class CompanyRecord:
    id: int
    name: str
    category: str | None = None
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    email_source: str | None = None
    company_summary: str | None = None
    mail_draft: str | None = None
    mail_subject: str | None = None
    lead_type: str | None = None
    fit_score: int | None = None
    fit_reasons: str | None = None
    hiring_signal_score: int | None = None
    digital_need_score: int | None = None
    company_size_guess: str | None = None
    decision_maker_candidates: str | None = None
    research_summary: str | None = None
    recommended_profile_variant: str | None = None
    recommended_attachment_key: str | None = None
    recommended_cta: str | None = None
    last_contact_stage: str | None = None
    routing_reason: str | None = None
    value_prop_brief: str | None = None
    recommended_reference_project: str | None = None
    thread_reference: str | None = None
    followup_due_at: str | None = None
    status: str = "pending"
    sent_at: str | None = None
    error_message: str | None = None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> "CompanyRecord":
        mapping = dict(row)
        for key in ("fit_score", "hiring_signal_score", "digital_need_score"):
            value = mapping.get(key)
            if value in (None, ""):
                mapping[key] = None
            else:
                try:
                    mapping[key] = int(value)
                except (TypeError, ValueError):
                    mapping[key] = None
        return cls(**mapping)

    @property
    def ui_status_key(self) -> str:
        if self.status == "error":
            return "error"
        if self.status == "skipped":
            return "skipped"
        if self.status == "rejected":
            return "rejected"
        if self.status == "sent":
            return "sent"
        if self.status == "approved":
            return "approved"
        if self.mail_draft:
            return "ready"
        return "pending"

    @property
    def ui_status_label(self) -> str:
        return {
            "pending": "Hazırlanıyor",
            "ready": "Mail Hazır",
            "approved": "Onaylandı",
            "sent": "Gönderildi",
            "rejected": "Reddedildi",
            "error": "Hata",
            "skipped": "Atlandı",
        }[self.ui_status_key]

    @property
    def created_display(self) -> str:
        if not self.created_at:
            return "-"
        try:
            value = datetime.fromisoformat(self.created_at.replace(" ", "T"))
        except ValueError:
            return self.created_at
        return value.strftime("%d.%m.%Y %H:%M")

    @property
    def fit_score_display(self) -> str:
        if self.fit_score is None:
            return "-"
        return str(self.fit_score)

    @property
    def lead_type_label(self) -> str:
        return {
            "job": "Is Basvurusu",
            "service": "Hizmet Teklifi",
            "unclear": "Belirsiz",
            None: "-",
            "": "-",
        }.get(self.lead_type, str(self.lead_type))

    @property
    def is_recommended(self) -> bool:
        return (self.fit_score or 0) >= RECOMMENDED_FIT_SCORE and self.lead_type in {"job", "service"} and self.status not in {"sent", "rejected", "error"}

    @property
    def recommended_action_label(self) -> str:
        if self.status == "sent":
            return "Tamamlandi"
        if self.status == "rejected":
            return "Tekrar etme"
        if self.lead_type == "unclear":
            return "Elle incele"
        if self.is_recommended:
            return "Oncelikli"
        if self.fit_score is None:
            return "Hazirlaniyor"
        return "Incele"

    @property
    def last_contact_stage_label(self) -> str:
        mapping = {
            "found": "Bulundu",
            "enriched": "Zenginlestirildi",
            "draft_ready": "Taslak Hazir",
            "approved": "Onaylandi",
            "sent": "Gonderildi",
            "skipped": "Atlandi",
            "rejected": "Reddedildi",
            "error": "Hata",
        }
        return mapping.get(self.last_contact_stage, self.last_contact_stage or "-")

    @property
    def fit_reason_items(self) -> list[str]:
        return _split_multiline_text(self.fit_reasons)

    @property
    def decision_maker_items(self) -> list[str]:
        return _split_multiline_text(self.decision_maker_candidates)

    @property
    def profile_variant_lines(self) -> list[str]:
        return _split_multiline_text(self.recommended_profile_variant)


@dataclass(slots=True)
class InteractionRecord:
    id: int
    company_id: int
    stage: str
    note: str | None = None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> "InteractionRecord":
        return cls(**dict(row))


@dataclass(slots=True)
class EmailLookupResult:
    email: str | None
    source: str
    checked_urls: list[str]
    error: str | None = None


@dataclass(slots=True)
class SendResult:
    ok: bool
    error_message: str | None = None
    smtp_code: int | None = None
    message_id: str | None = None


@dataclass(slots=True)
class IntegrationCheckResult:
    service: str
    ok: bool
    message: str


def _split_multiline_text(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip("- ").strip() for line in value.splitlines() if line.strip()]
