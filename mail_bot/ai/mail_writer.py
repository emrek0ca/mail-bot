from __future__ import annotations

from ..models import CompanyRecord, Settings
from .lead_strategy import LeadStrategy


def compose_mail_message(strategy: LeadStrategy, settings: Settings, company: CompanyRecord | None = None) -> tuple[str, str]:
    """
    Yapay zekanin urettigi mail subject ve body'yi alir, placeholder'lari temizler
    ve kullanici imzasini ekleyerek dondurur.
    """
    subject = strategy.mail_subject.strip()
    body = strategy.mail_body.strip()

    # Placeholder temizleme (AI bazen unutabiliyor)
    if company:
        placeholders = {
            "[Sirket Adi]": company.name,
            "[Şirket Adı]": company.name,
            "[Sirket]": company.name,
            "{company_name}": company.name,
            "[Isim]": "Yetkili",
            "[İsim]": "Yetkili",
            "[Yetkili]": "Yetkili",
            "[Adiniz]": settings.user_name,
            "[Adınız]": settings.user_name,
        }
        for key, val in placeholders.items():
            subject = subject.replace(key, val)
            body = body.replace(key, val)

    if not subject:
        applicant = settings.user_name.strip() or "Aday"
        subject = f"{settings.user_title or 'Profesyonel'} Başvurusu - {applicant}"

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
