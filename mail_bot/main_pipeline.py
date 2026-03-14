from __future__ import annotations

from typing import Protocol

from .ai.client_factory import get_ai_client
from .ai.lead_strategy import plan_lead_strategy, plan_followup_strategy
from .ai.mail_writer import compose_mail_message
from .database import Database
from .models import SearchQuery, Settings
from .scraper.company_research import ResearchBundle, enrich_company_website
from .scraper.email_finder import find_email


class PipelineNotifier(Protocol):
    async def log(self, message: str) -> None: ...

    async def refresh_company(self, company_id: int) -> None: ...

    async def request_manual_email(self, company_id: int, company_name: str) -> str | None: ...


async def process_followup_company(
    company_id: int,
    config: Settings,
    db: Database,
    notifier: PipelineNotifier,
) -> None:
    company = db.get_company(company_id)
    if not company:
        return
    if company.status != "sent":
        return
    
    try:
        await notifier.log(f"Follow-up hazirlaniyor: {company.name}")
        client = get_ai_client(config)
        
        strategy = await plan_followup_strategy(client, company, config)
        
        db.update_company(
            company_id,
            status="ready",
            mail_subject=strategy.mail_subject,
            mail_draft=strategy.mail_body,
            error_message=None,
        )
        db.add_interaction(company_id, "followup_ready", "Otomatik takip taslagi hazir")
        
        await notifier.refresh_company(company_id)
        await notifier.log(f"Follow-up taslagi hazir: {company.name}")
    except Exception as exc:
        db.update_company(company_id, error_message=f"Follow-up hatasi: {exc}")
        db.add_interaction(company_id, "error", f"Follow-up hatasi: {exc}")
        await notifier.refresh_company(company_id)
        await notifier.log(f"Follow-up Hatasi: {company.name} -> {exc}")


async def process_company(
    company_id: int,
    config: Settings,
    db: Database,
    notifier: PipelineNotifier,
    search_query: SearchQuery | None = None,
) -> None:
    company = db.get_company(company_id)
    if not company:
        return
    try:
        if company.status in {"sent", "rejected"}:
            if company.status == "sent":
                await notifier.log(f"Daha once mail gonderildi, atlandi: {company.name}")
            else:
                await notifier.log(f"Daha once reddedilen kayit atlandi: {company.name}")
            await notifier.refresh_company(company_id)
            return
        await notifier.log(f"Sirket hazirlaniyor: {company.name}")
        if company.website:
            email_result = await find_email(company.website)
            email_value = email_result.email
            email_source = email_result.source
            if not email_value:
                manual_email = await notifier.request_manual_email(company_id, company.name)
                if manual_email:
                    email_value = manual_email
                    email_source = "manual"
                else:
                    db.update_company(company_id, status="skipped", error_message="Email bulunamadi")
                    db.add_interaction(company_id, "skipped", "Email bulunamadi")
                    await notifier.refresh_company(company_id)
                    return
            db.update_company(company_id, email=email_value, email_source=email_source, error_message=email_result.error)
        else:
            manual_email = await notifier.request_manual_email(company_id, company.name)
            if manual_email:
                db.update_company(company_id, email=manual_email, email_source="manual")
            else:
                db.update_company(company_id, status="skipped", error_message="Email bulunamadi")
                db.add_interaction(company_id, "skipped", "Email bulunamadi")
                await notifier.refresh_company(company_id)
                return

        company = db.get_company(company_id)
        if not company:
            return
        db.add_interaction(company_id, "enriched", "Email ve website hazirlandi")

        if not config.active_api_key:
            db.update_company(
                company_id,
                status="error",
                error_message=f"{config.active_provider_label} API key ayarlanmamis.",
            )
            await notifier.refresh_company(company_id)
            return

        effective_query = search_query or SearchQuery(sector=company.category or "", city=company.city or "", limit=20)
        research = await enrich_company_website(company.website, company.name) if company.website else _empty_research_bundle()
        
        db.update_company(
            company_id,
            hiring_signal_score=research.hiring_signal_score,
            digital_need_score=research.digital_need_score,
            company_size_guess=research.company_size_guess,
            decision_maker_candidates="\n".join(research.decision_maker_candidates),
            last_contact_stage="enriched",
        )
        
        client = get_ai_client(config)
        
        # TEK ASAMALI URETIM: Strateji ve mail ayni anda uretiliyor
        strategy = await plan_lead_strategy(client, company, config, effective_query, research)
        
        job_reasons = [reason for reason in strategy.fit_reasons if reason.strip()]
        if not job_reasons:
            job_reasons = ["Sirketin alanina uygun bir yazilim gelistirme basvurusu hazirlandi."]
            
        job_cta = "CV'm ekte. Uygun olursaniz kisa bir gorusmede detaylari konusabiliriz."
        
        db.update_company(
            company_id,
            company_summary=strategy.company_summary,
            lead_type=strategy.lead_type,
            fit_score=strategy.fit_score,
            fit_reasons="\n".join(job_reasons),
            research_summary=strategy.research_summary,
            recommended_profile_variant=strategy.recommended_profile_variant,
            recommended_attachment_key=strategy.recommended_attachment_key,
            recommended_cta=strategy.recommended_cta,
            routing_reason=strategy.routing_reason,
            value_prop_brief=strategy.value_prop_brief,
            recommended_reference_project=strategy.recommended_reference_project,
            error_message=None,
        )

        company = db.get_company(company_id)
        if not company:
            return

        subject, body = compose_mail_message(strategy, config)
        db.update_company(company_id, mail_subject=subject, mail_draft=body, error_message=None)
        db.add_interaction(company_id, "draft_ready", strategy.lead_type)
        
        await notifier.refresh_company(company_id)
        await notifier.log(f"Mail taslagi hazir: {company.name}")
        
    except Exception as exc:
        db.update_company(company_id, status="error", error_message=str(exc))
        db.add_interaction(company_id, "error", str(exc))
        await notifier.refresh_company(company_id)
        await notifier.log(f"Hata: {company.name} -> {exc}")


def _empty_research_bundle() -> ResearchBundle:
    return ResearchBundle(
        visited_urls=[],
        page_texts={},
        combined_text="",
        hiring_signal_score=0,
        digital_need_score=0,
        company_size_guess="bilinmiyor",
        decision_maker_candidates=[],
        detected_tech_stack=[],
        has_active_job_board_postings=False,
        weak_signal=True,
    )
