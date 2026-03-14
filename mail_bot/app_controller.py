from __future__ import annotations

import asyncio
import queue
import threading
from datetime import datetime
from typing import Any

from . import DAILY_GMAIL_LIMIT
from .ai.client_factory import clear_all_clients
from .background import BackgroundRunner
from .config import load_settings as load_app_settings
from .config import save_settings as save_app_settings
from .database import Database
from .integrations import check_ai, check_gmail, check_playwright
from .main_pipeline import process_company, process_followup_company
from .mailer.gmail_sender import send_mail
from .models import CompanyRecord, IntegrationCheckResult, SearchQuery, Settings
from .security import sanitize_header, validate_recipient_email
from .scraper.company_research import reject_company_candidate
from .scraper.maps_scraper import search_companies


class AppController:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()
        self.db.init_db()
        self.runner = BackgroundRunner()
        self.ui_events: queue.Queue[dict[str, Any]] = queue.Queue()
        self._manual_email_futures: dict[int, asyncio.Future[str | None]] = {}
        self._manual_email_lock = threading.Lock()
        self._search_future = None
        self._search_lock = threading.Lock()
        self._active_send_ids: set[int] = set()
        self._send_lock = threading.Lock()

    def load_settings(self) -> Settings:
        return load_app_settings(self.db)

    def save_settings(self, settings: Settings) -> None:
        try:
            save_app_settings(settings, self.db)
            clear_all_clients()
            self._emit("settings_saved", settings=settings)
        except Exception as exc:
            self._emit("alert", level="error", message=str(exc))

    def list_companies(self) -> list[CompanyRecord]:
        return self.db.list_companies()

    def get_company(self, company_id: int) -> CompanyRecord | None:
        return self.db.get_company(company_id)

    def get_interactions(self, company_id: int):
        return self.db.list_interactions(company_id)

    def clear_companies(self) -> None:
        with self._search_lock:
            if self._search_future and not self._search_future.done():
                self._emit("alert", level="info", message="Tarama sirasinda liste temizlenemez.")
                return
        with self._send_lock:
            if self._active_send_ids:
                self._emit("alert", level="info", message="Gonderim sirasinda liste temizlenemez.")
                return
        self.db.clear_companies()
        self._emit("companies_cleared")
        self._emit("search_state", message="Hazir.", progress=0.0)
        self._emit("log", message="Isletme listesi temizlendi.")

    def poll_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while True:
            try:
                events.append(self.ui_events.get_nowait())
            except queue.Empty:
                break
        return events

    def start_search(self, sector: str, city: str, limit: int, settings: Settings | None = None) -> None:
        query = SearchQuery(sector=sector, city=city, limit=limit)
        with self._search_lock:
            if self._search_future and not self._search_future.done():
                self._emit("alert", level="info", message="Zaten calisan bir tarama var.")
                return
        runtime_settings = settings or self.load_settings()
        
        # Update search history
        query_str = f"{sector} | {city}".strip()
        history = [q.strip() for q in runtime_settings.search_history.split(";") if q.strip()]
        if query_str in history:
            history.remove(query_str)
        history.insert(0, query_str)
        runtime_settings.search_history = ";".join(history[:10])
        
        try:
            save_app_settings(runtime_settings, self.db)
            clear_all_clients()
        except Exception as exc:
            self._emit("alert", level="error", message=str(exc))
            return
        self._emit("search_state", message="Google Maps taramasi baslatildi.", progress=0.0)
        future = self.runner.submit(self._run_search(query, runtime_settings))
        with self._search_lock:
            self._search_future = future

    def save_draft(
        self,
        company_id: int,
        email: str,
        subject: str,
        body: str,
        lead_type: str | None = None,
        cta: str | None = None,
    ) -> None:
        normalized = self._validate_edit_payload(email, subject, body)
        if not normalized:
            return
        fields = dict(
            email=normalized["email"],
            mail_subject=normalized["subject"],
            mail_draft=body.strip(),
            lead_type="job",
        )
        if cta is not None:
            fields["recommended_cta"] = cta.strip()
        self.db.update_company(company_id, **fields)
        self.db.add_interaction(company_id, "draft_ready", "Taslak guncellendi")
        self._emit_company(company_id)
        self._emit("log", message=f"Taslak guncellendi: #{company_id}")

    def approve_company(self, company_id: int, email: str, subject: str, body: str, lead_type: str | None = None, cta: str | None = None) -> None:
        normalized = self._validate_edit_payload(email, subject, body)
        if not normalized:
            return
        fields = dict(
            email=normalized["email"],
            mail_subject=normalized["subject"],
            mail_draft=body.strip(),
            status="approved",
            error_message=None,
            lead_type="job",
        )
        if cta is not None:
            fields["recommended_cta"] = cta.strip()
        self.db.update_company(
            company_id,
            **fields,
        )
        self.db.add_interaction(company_id, "approved", "job")
        self._emit_company(company_id)
        self._emit("log", message=f"Mail onaylandi: #{company_id}")

    def skip_company(self, company_id: int) -> None:
        self.db.update_company(company_id, status="skipped")
        self.db.add_interaction(company_id, "skipped", "Kullanici atladi")
        self._emit_company(company_id)
        self._emit("log", message=f"Kayit atlandi: #{company_id}")

    def reject_company(self, company_id: int, note: str | None = None) -> None:
        self.db.update_company(company_id, status="rejected")
        self.db.add_interaction(company_id, "rejected", note or "Kullanici reddetti")
        self._emit_company(company_id)
        self._emit("log", message=f"Kayit reddedildi: #{company_id}")

    def send_company_now(self, company_id: int) -> None:
        if self._mark_sending(company_id):
            self._emit("alert", level="info", message="Bu kayit zaten gonderiliyor.")
            return
        self.runner.submit(self._send_single_company(company_id))

    def send_approved(self) -> None:
        self.runner.submit(self._send_all_approved())

    def check_followups(self) -> None:
        self.runner.submit(self._run_followups())

    def run_integration_check(self, service: str, settings: Settings) -> None:
        if service == "ai":
            self.runner.submit(self._run_single_check(service, settings))
        elif service == "gmail":
            self.runner.submit(self._run_single_check(service, settings))
        elif service == "playwright":
            self.runner.submit(self._run_single_check(service, settings))
        else:
            self._emit("alert", level="error", message=f"Bilinmeyen servis testi: {service}")

    def resolve_manual_email(self, company_id: int, email: str | None) -> None:
        with self._manual_email_lock:
            future = self._manual_email_futures.pop(company_id, None)
        if future and not future.done():
            self.runner.loop.call_soon_threadsafe(future.set_result, email.strip() if email else None)

    def export_to_csv(self, file_path: str) -> None:
        import csv
        try:
            data = self.db.list_companies_raw()
            if not data:
                self._emit("alert", level="info", message="Disa aktarilacak kayit bulunamadi.")
                return
            
            headers = list(data[0].keys())
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
            
            self._emit("log", message=f"Liste disa aktarildi: {file_path}")
            self._emit("alert", level="info", message=f"Liste basariyla disa aktarildi:\n{file_path}")
        except Exception as exc:
            self._emit("alert", level="error", message=f"Disa aktarma hatasi: {exc}")

    def shutdown(self) -> None:
        self.runner.stop()
        self.db.close()

    async def log(self, message: str) -> None:
        self._emit("log", message=message)

    async def refresh_company(self, company_id: int) -> None:
        self._emit_company(company_id)

    async def request_manual_email(self, company_id: int, company_name: str) -> str | None:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str | None] = loop.create_future()
        with self._manual_email_lock:
            self._manual_email_futures[company_id] = future
        self._emit("manual_email_required", company_id=company_id, company_name=company_name)
        return await future

    async def _run_search(self, query: SearchQuery, settings: Settings) -> None:
        company_ids: list[int] = []
        seen_company_ids: set[int] = set()

        async def on_company(raw_company: dict[str, Any]) -> None:
            rejection_reason = reject_company_candidate(raw_company, query)
            if rejection_reason:
                self._emit("log", message=f"Lead elendi: {raw_company.get('name', 'Isimsiz')} -> {rejection_reason}")
                return
            company_id, created = self.db.upsert_company(raw_company)
            if company_id in seen_company_ids:
                return
            seen_company_ids.add(company_id)
            company_ids.append(company_id)
            if created:
                self.db.add_interaction(company_id, "found", "Google Maps sonucu")
            company = self.db.get_company(company_id)
            if company and not created and company.status == "sent":
                self._emit("log", message=f"Daha once mail gonderilen kayit bulundu: {company.name}")
            self._emit_company(company_id)
            self._emit(
                "search_state",
                message=f"{len(company_ids)} sirket bulundu.",
                progress=min(len(company_ids) / max(query.limit, 1), 1.0),
            )

        try:
            self._emit(
                "log",
                message=f"AI saglayicisi: {settings.active_provider_label} | Model: {settings.active_model}",
            )
            ai_check = await check_ai(settings)
            if not ai_check.ok:
                self._emit("search_state", message="Tarama baslamadi. AI ayari gecersiz.", progress=0.0)
                self._emit("alert", level="error", message=ai_check.message)
                self._emit("log", message=f"AI preflight hatasi: {ai_check.message}")
                return
            await search_companies(query, on_company=on_company)
            self._emit("log", message=f"Taranan sirket sayisi: {len(company_ids)}")
            total = max(len(company_ids), 1)
            for index, company_id in enumerate(company_ids, start=1):
                self._emit(
                    "search_state",
                    message=f"Sirketler hazirlaniyor ({index}/{total})",
                    progress=min(index / total, 1.0),
                )
                await process_company(company_id, settings, self.db, self, query)
            self._emit("search_state", message="Tarama ve taslak hazirlama tamamlandi.", progress=1.0)
        except Exception as exc:
            self._emit("search_state", message=f"Islem durdu: {exc}", progress=0.0)
            self._emit("log", message=f"Arama hatasi: {exc}")
        finally:
            with self._search_lock:
                self._search_future = None

    async def _run_single_check(self, service: str, settings: Settings) -> None:
        self._emit("integration_check_started", service=service)
        try:
            if service == "ai":
                result = await check_ai(settings)
            elif service == "gmail":
                result = await check_gmail(settings)
            else:
                result = await check_playwright()
        except Exception as exc:
            result = IntegrationCheckResult(service=service, ok=False, message=str(exc))
        self._emit("integration_check_finished", result=result)

    async def _send_all_approved(self) -> None:
        settings = self.load_settings()
        approved = self.db.list_by_status("approved")
        if not approved:
            self._emit("log", message="Gonderilecek onayli mail yok.")
            return
        for company in approved:
            if self._mark_sending(company.id):
                continue
            await self._deliver_company(company, settings)

    async def _run_followups(self) -> None:
        settings = self.load_settings()
        sent_companies = self.db.list_by_status("sent")
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        
        followups_needed = [
            c for c in sent_companies 
            if c.followup_due_at and c.followup_due_at <= now
        ]
        
        if not followups_needed:
            self._emit("log", message="Zamani gelmis takip (follow-up) maili yok.")
            return
            
        self._emit("log", message=f"{len(followups_needed)} sirket icin follow-up taslagi hazirlaniyor...")
        for company in followups_needed:
            await process_followup_company(company.id, settings, self.db, self)
        
        self._emit("log", message="Follow-up hazirliklari tamamlandi.")

    async def _send_single_company(self, company_id: int) -> None:
        settings = self.load_settings()
        company = self.db.get_company(company_id)
        if not company:
            self._unmark_sending(company_id)
            return
        if company.status != "approved":
            self.db.update_company(company_id, status="approved")
            company = self.db.get_company(company_id)
        if company:
            await self._deliver_company(company, settings)

    async def _deliver_company(self, company: CompanyRecord, settings: Settings) -> None:
        try:
            if self.db.get_daily_send_count(datetime.now()) >= DAILY_GMAIL_LIMIT:
                self._emit("log", message="Gunluk Gmail limiti doldu. Gonderim durduruldu.")
                return
            if not company.email:
                manual_email = await self.request_manual_email(company.id, company.name)
                if not manual_email:
                    self.db.update_company(company.id, status="skipped", error_message="Email girilmedi.")
                    self._emit_company(company.id)
                    self._emit("log", message=f"Mail atlandi: {company.name}")
                    return
                self.db.update_company(company.id, email=validate_recipient_email(manual_email), email_source="manual")
                company = self.db.get_company(company.id) or company
            if not settings.gmail_address or not settings.gmail_app_password:
                self.db.update_company(company.id, status="error", error_message="Gmail ayarlari eksik.")
                self._emit_company(company.id)
                return

            selected_attachments = []
            rec_key = company.recommended_attachment_key or "all"
            if rec_key == "primary_cv" and settings.cv_path:
                selected_attachments.append(settings.cv_path)
            elif rec_key == "secondary_cv" and settings.cv_path_secondary:
                selected_attachments.append(settings.cv_path_secondary)
            elif rec_key == "portfolio" and settings.portfolio_pdf_path:
                selected_attachments.append(settings.portfolio_pdf_path)
            elif rec_key == "all":
                selected_attachments = settings.attachment_paths

            result = await asyncio.to_thread(
                send_mail,
                settings.gmail_address,
                settings.gmail_app_password,
                company.email or "",
                company.mail_subject or f"{company.name} icin basvuru",
                company.mail_draft or "",
                None,
                selected_attachments,
                company.thread_reference,
            )
            if result.ok:
                from datetime import timedelta
                now = datetime.now()
                due_date = now + timedelta(days=3)
                
                self.db.update_company(
                    company.id, 
                    status="sent", 
                    sent_at=now.isoformat(sep=" ", timespec="seconds"),
                    thread_reference=result.message_id or company.thread_reference,
                    followup_due_at=due_date.isoformat(sep=" ", timespec="seconds"),
                )
                self.db.add_interaction(company.id, "sent", "Mail gonderildi")
                self.db.increment_daily_send_count()
                self._emit("log", message=f"Mail gonderildi: {company.name}")
            else:
                self.db.update_company(company.id, status="error", error_message=result.error_message)
                self.db.add_interaction(company.id, "error", result.error_message or "Gonderim hatasi")
                self._emit("log", message=f"Gonderim hatasi: {company.name} -> {result.error_message}")
            self._emit_company(company.id)
        finally:
            self._unmark_sending(company.id)

    def _emit_company(self, company_id: int) -> None:
        company = self.db.get_company(company_id)
        if company:
            self._emit("company_updated", company=company)

    def _emit(self, event_type: str, **payload: Any) -> None:
        self.ui_events.put({"type": event_type, **payload})

    def _mark_sending(self, company_id: int) -> bool:
        with self._send_lock:
            if company_id in self._active_send_ids:
                return True
            self._active_send_ids.add(company_id)
            return False

    def _unmark_sending(self, company_id: int) -> None:
        with self._send_lock:
            self._active_send_ids.discard(company_id)

    def _validate_edit_payload(self, email: str, subject: str, body: str) -> dict[str, str] | None:
        try:
            normalized_email = validate_recipient_email(email)
            normalized_subject = sanitize_header(subject, "Konu")
            if not body.strip():
                raise ValueError("Mail govdesi bos olamaz.")
            return {"email": normalized_email, "subject": normalized_subject}
        except ValueError as exc:
            self._emit("alert", level="error", message=str(exc))
            return None
