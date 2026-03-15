from __future__ import annotations

from ..models import CompanyRecord, Settings
from .lead_strategy import LeadStrategy


def compose_mail_message(strategy: LeadStrategy, settings: Settings) -> tuple[str, str]:
    """
    Yapay zekanin urettigi mail subject ve body'yi alir, kullanici imzasini ekleyerek dondurur.
    """
    subject = strategy.mail_subject.strip()
    if not subject:
        applicant = settings.user_name.strip() or "Aday"
        subject = f"{settings.user_title or 'Profesyonel'} Başvurusu - {applicant}"

    body = strategy.mail_body.strip()
    if not body:
        body = "Merhaba,\n\nEkteki ozgecmisimi inceleyebilirsiniz.\n\nIyi calismalar."

    signature = _build_signature(settings)
    final_body = f"{body}\n\n{signature}"
    return subject, final_body.strip()


def _build_signature(settings: Settings) -> str:
    lines = [settings.user_name.strip() or "Ad Soyad"]
    if settings.user_phone.strip():
        lines.append(settings.user_phone.strip())
    for link in (settings.linkedin_url.strip(), settings.portfolio_url.strip(), settings.github_url.strip()):
        if link:
            lines.append(link)
    return "\n".join(lines)
