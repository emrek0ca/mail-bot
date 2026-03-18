from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .. import RECOMMENDED_FIT_SCORE
from ..models import CompanyRecord, SearchQuery, Settings
from ..scraper.company_research import ResearchBundle


@dataclass(slots=True)
class LeadStrategy:
    lead_type: str
    fit_score: int
    fit_reasons: list[str]
    company_summary: str
    research_summary: str
    recommended_profile_variant: str
    recommended_cta: str
    routing_reason: str
    value_prop_brief: str
    recommended_reference_project: str
    mail_subject: str
    mail_body: str
    recommended_attachment_key: str


@dataclass(slots=True)
class FollowupStrategy:
    mail_subject: str
    mail_body: str


async def plan_followup_strategy(
    client,
    company: CompanyRecord,
    settings: Settings,
) -> FollowupStrategy:
    try:
        raw = await client.generate(build_followup_prompt(company, settings))
        data = json.loads(_extract_json_payload(raw) or "{}")
        subject = str(data.get("mail_subject") or f"Re: {company.mail_subject}").strip()
        body = str(data.get("mail_body") or "Merhaba,\n\nÖnceki mailimde ilettiğim konu hakkında bir gelişme var mı?\n\nİyi çalışmalar.").strip()
        return FollowupStrategy(mail_subject=subject, mail_body=body)
    except Exception as e:
        print(f"Hata: plan_followup_strategy basarisiz oldu: {e}")
        return FollowupStrategy(
            mail_subject=f"Re: {company.mail_subject}",
            mail_body="Merhaba,\n\nÖnceki mailimde ilettiğim konu hakkında bir gelişme var mı?\n\nİyi çalışmalar."
        )


def build_followup_prompt(company: CompanyRecord, settings: Settings) -> str:
    return f"""
Sen uzman bir B2B iletisim uzmanisin.
Amacin, asagidaki sirkete daha once attigimiz basvuru/tanisma mailine yanit alamadigimiz icin kisa, nazik ve hatirlatici bir "follow-up" (takip) maili yazmaktir.

Onceki Mailin Konusu: {company.mail_subject}
Onceki Mailin Icerigi:
{company.mail_draft[:1000]}

Gorev:
1. Yeni e-postanin konusu "Re: [Onceki Konu]" formatinda olmalidir.
2. Icerik cok kisa, profesyonel ve degeri tekrar hatirlatan tarzda olmalidir. Baskici degil, "belki gozden kacmistir" tonunda olmalidir. Maksimum 3-4 cumle.

KULLANICI PROFILI:
Ad: {settings.user_name}
Unvan: {settings.user_title}

Lutfen ciktini SADECE asagidaki JSON formatinda ver. Baska hicbir aciklama metni ekleme.

JSON semasi:
{{
  "mail_subject": "Re: Onceki Konu",
  "mail_body": "Sayin Yetkili,\\n\\n..."
}}
""".strip()

async def plan_lead_strategy(
    client,
    company: CompanyRecord,
    settings: Settings,
    search_query: SearchQuery,
    research: ResearchBundle,
) -> LeadStrategy:
    fallback = fallback_strategy(company, settings, search_query, research)
    try:
        raw = await client.generate(
            build_lead_strategy_prompt(company, settings, search_query, research, fallback)
        )
        return parse_lead_strategy_output(raw, fallback)
    except Exception as e:
        print(f"Hata: plan_lead_strategy basarisiz oldu: {e}")
        return fallback


def build_lead_strategy_prompt(
    company: CompanyRecord,
    settings: Settings,
    search_query: SearchQuery,
    research: ResearchBundle,
    fallback: LeadStrategy,
) -> str:
    has_primary = bool(settings.cv_path)
    has_secondary = bool(settings.cv_path_secondary)
    has_portfolio = bool(settings.portfolio_pdf_path)
    attachment_options = []
    if has_primary:
        attachment_options.append("primary_cv")
    if has_secondary:
        attachment_options.append("secondary_cv")
    if has_portfolio:
        attachment_options.append("portfolio")
    attachment_options_str = ", ".join(attachment_options) or "none"

    return f"""
Sen dunya standartlarinda bir B2B Satis ve Is Gelistirme uzmanisin.
Amacin, asagidaki verileri kullanarak sirkete ozel, asla 'copy-paste' oldugu anlasilmayan, dogrudan bir insan tarafindan yazilmis hissi veren bir e-posta olusturmaktır.

STRATEJI KURALLARI:
1. SADECE bir is basvurusu yapma; sirketin bir problemini cozmeye veya bir ihtiyacini karsilamaya odaklan.
2. Eger 'Hiring Signal' yuksekse (is ilani varsa), o roldeki ihtiyaca atifta bulun.
3. Eger 'Digital Need' yuksekse, sirketin dijital varligindaki (web sitesi hizi, mobil uyum, rezervasyon sistemi eksikligi vb.) bir eksigi nazikce belirt.
4. Tespit edilen teknolojileri (Tech Stack) mutlaka mailin icinde 'deneyimim var' demek yerine 'bu yapidaki sirketlere nasil deger kattigini' anlatarak kullan.

MAIL YAZIM KURALLARI (KRITIK):
- KONU: Merak uyandiran, kisisel ve profesyonel olmali. Ornek: "{company.name} + {settings.user_name} | Bir Oneri", "{company.name} Ekibi Icin Ozellestirilmiş Cozum".
- GIRIS: "Merhaba [Isim/Yetkili]" ile basla. İlk cumlede sirketin son donemdeki bir basarisina, web sitesindeki bir detaya veya sektorundeki konumuna spesifik atif yap.
- GELISME: Sirketin su anki acisini (pain point) tahmin et ve cozumunu sun.
- CTA: Net bir soru veya kucuk bir istek ile bitir. (Ornek: "Salı gunu 5 dakikaniz var mi?")
- DIL: Profesyonel ama samimi. Robotik 'Sayin Yetkili' ifadelerinden mumkunse kacın (eger isim yoksa 'Ekip' de).

KULLANICI PROFILI (SENIN ROLUN):
Ad: {settings.user_name}
Unvan: {settings.user_title}
Uzmanlik: {settings.expertise_areas}
Deger Onerisi: {settings.service_value_prop}

SIRKET VERILERI:
Ad: {company.name}
Sektor/Kategori: {company.category}
Web Sitesi Ozeti: {research.combined_text[:4000]}
Tespit Edilen Teknolojiler: {", ".join(research.detected_tech_stack)}
Sosyal Medya Linkleri: {", ".join(research.social_links or [])}
Is Ilani Durumu: {"Aktif ilanlari var" if research.has_active_job_board_postings else "Bilinmiyor"}
Skorlar: Hiring: {research.hiring_signal_score}, Digital Need: {research.digital_need_score}

Lutfen ciktini SADECE asagidaki JSON formatinda ver.
{{
  "company_summary": "Sirketin ne yaptigina dair derin analiz.",
  "lead_type": "job|service",
  "fit_score": 0-100,
  "fit_reasons": ["spesifik neden 1", "spesifik neden 2"],
  "mail_subject": "Tiklanma orani yuksek konu basligi",
  "mail_body": "Kisisellestirilmis mail govdesi...",
  "recommended_attachment_key": "primary_cv|portfolio|all"
}}
""".strip()
""".strip()


def parse_lead_strategy_output(raw_text: str, fallback: LeadStrategy) -> LeadStrategy:
    payload = _extract_json_payload(raw_text)
    if not payload:
        return fallback
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return fallback
        
    lead_type = str(data.get("lead_type", fallback.lead_type)).strip().lower()
    if lead_type not in {"job", "service", "unclear"}:
        lead_type = fallback.lead_type
    
    fit_score = _safe_score(data.get("fit_score"), fallback.fit_score)
    if lead_type == "unclear":
        fit_score = min(fit_score, RECOMMENDED_FIT_SCORE - 5)
        
    fit_reasons = _normalize_string_list(data.get("fit_reasons")) or fallback.fit_reasons
    
    mail_body = str(data.get("mail_body") or fallback.mail_body).strip()
    custom_ps_note = str(data.get("custom_ps_note", "")).strip()
    if custom_ps_note and custom_ps_note not in mail_body:
        mail_body = f"{mail_body}\n\n{custom_ps_note}"
    
    return LeadStrategy(
        lead_type=lead_type,
        fit_score=fit_score,
        fit_reasons=fit_reasons,
        company_summary=str(data.get("company_summary") or fallback.company_summary).strip(),
        research_summary=str(data.get("research_summary") or fallback.research_summary).strip(),
        recommended_profile_variant=str(data.get("recommended_profile_variant") or fallback.recommended_profile_variant).strip(),
        recommended_cta=str(data.get("recommended_cta") or fallback.recommended_cta).strip(),
        routing_reason=str(data.get("routing_reason") or fallback.routing_reason).strip(),
        value_prop_brief=str(data.get("value_prop_brief") or fallback.value_prop_brief).strip(),
        recommended_reference_project=str(data.get("recommended_reference_project") or fallback.recommended_reference_project).strip(),
        mail_subject=str(data.get("mail_subject") or fallback.mail_subject).strip(),
        mail_body=mail_body,
        recommended_attachment_key=str(data.get("recommended_attachment_key") or fallback.recommended_attachment_key).strip(),
    )


def fallback_strategy(
    company: CompanyRecord,
    settings: Settings,
    search_query: SearchQuery,
    research: ResearchBundle,
) -> LeadStrategy:
    query_lower = f"{search_query.sector} {search_query.city}".lower()
    summary_lower = f"{company.name} {company.category or ''} {research.combined_text[:2000]}".lower()
    
    fit_reasons: list[str] = []
    alignment = 0
    if any(token and token in summary_lower for token in query_lower.split()):
        alignment += 12
        fit_reasons.append("Arama niyeti ile temel uyum var.")
    if research.hiring_signal_score >= 45:
        lead_type = "job"
        fit_reasons.append("Ise alim sinyali goruluyor.")
    elif research.digital_need_score >= 45:
        lead_type = "service"
        fit_reasons.append("Dijital ihtiyac sinyali belirgin.")
    else:
        lead_type = "unclear"
        fit_reasons.append("Net ise alim veya hizmet sinyali zayif.")
        
    if research.decision_maker_candidates:
        alignment += 10
        fit_reasons.append("Karar verici veya uygun temas noktasi bulundu.")
    if company.city and search_query.city and company.city.lower() == search_query.city.lower():
        alignment += 6
        fit_reasons.append("Sehir uyumu var.")
    if settings.expertise_areas and any(token in summary_lower for token in settings.expertise_areas.lower().split(",")):
        alignment += 8
        fit_reasons.append("Uzmanlik alanlariyla kesisim var.")
        
    fit_score = min(
        100,
        28 + alignment + int(research.hiring_signal_score * 0.35) + int(research.digital_need_score * 0.35),
    )
    if lead_type == "unclear":
        fit_score = min(fit_score, RECOMMENDED_FIT_SCORE - 5)
        
    recommended_reference_project = _pick_reference_project(settings)
    company_summary = "Sirket websitesinden yeterli anlamli ozet cikarilamadi."
    research_summary = "Sirketin dijital ve ekip yapisina gore kisa bir ilk temas hazirlandi."
    
    if lead_type == "service":
        cta = "Uygun gorurseniz size kisa bir kesif gorusmesi ve somut iyilestirme onerisi paylasabilirim."
        variant = (
            f"Odak: {settings.expertise_areas or settings.user_title or 'profesyonel hizmet'}\n"
            f"Kanıt: {recommended_reference_project}"
        )
        value_prop = settings.service_value_prop or f"Sirkete hizli deger uretecek bir {settings.user_title or 'profesyonel'} iyilestirme onerisi sun."
        routing_reason = "Hizmet ihtiyaci sinyali ise alim sinyalinden daha guclu."
    elif lead_type == "job":
        cta = "Uygun gorurseniz deneyimimi kisa bir gorusmede detaylandirmak isterim."
        variant = (
            f"Odak: {settings.target_roles or settings.user_title or 'uygun rol'}\n"
            f"Kanıt: {recommended_reference_project}"
        )
        value_prop = "Sirkete hizli adapte olup mesleki katki saglayacak aday profili olustur."
        routing_reason = "Ise alim ve ekip uyumu sinyalleri daha baskin."
    else:
        cta = "Uygun bulursaniz kisa bir tanisma gorusmesi yapabiliriz."
        variant = f"Odak: {settings.user_title or 'genel profesyonel profil'}\nKanıt: {recommended_reference_project}"
        value_prop = "Hem adaylik hem hizmet tarafina acik, temkinli bir konumlama kullan."
        routing_reason = "Sinyaller karisik; kontrollu bir ilk temas onerilir."
        
    applicant = settings.user_name.strip() or "Aday"
    mail_subject = f"{settings.user_title or 'İş'} Başvurusu - {applicant}"
    if lead_type == "service":
        mail_subject = f"{settings.user_title or 'Profesyonel'} Hizmetleri ve İş Birliği - {applicant}"
        
    mail_body = f"Merhaba,\n\n{company.name} ile ilgili arastirma yaparken dikkatimi cektiniz. Sizin gibi vizyoner yapilarda deneyimimle katki saglayabilecegimi dusunuyorum.\n\n{cta}"

    return LeadStrategy(
        lead_type=lead_type,
        fit_score=max(0, min(100, fit_score)),
        fit_reasons=fit_reasons[:4],
        company_summary=company_summary,
        research_summary=research_summary,
        recommended_profile_variant=variant,
        recommended_cta=cta,
        routing_reason=routing_reason,
        value_prop_brief=value_prop,
        recommended_reference_project=recommended_reference_project,
        mail_subject=mail_subject,
        mail_body=mail_body,
        recommended_attachment_key="all",
    )


def _extract_json_payload(raw_text: str) -> str:
    text = raw_text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start : end + 1]


def _normalize_string_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [segment.strip() for segment in value.split("\n") if segment.strip()]
    return []


def _safe_score(value, fallback: int) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return fallback


def _pick_reference_project(settings: Settings) -> str:
    projects = [item.strip() for item in (settings.project_highlights or "").splitlines() if item.strip()]
    if projects:
        return projects[0]
    links = settings.profile_links
    if links:
        return links[0]
    return "CV ve portfolyo"
