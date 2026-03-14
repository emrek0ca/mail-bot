from __future__ import annotations

from tkinter import messagebox, simpledialog

import customtkinter as ctk

from ..app_controller import AppController
from ..models import CompanyRecord, IntegrationCheckResult, Settings
from .log_panel import LogPanel
from .mail_preview import MailPreviewDialog
from .results_table import ResultsTable
from .search_panel import SearchPanel
from .settings_panel import SettingsPanel


class MailBotApp(ctk.CTk):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self.controller = controller
        self._companies: dict[int, CompanyRecord] = {}

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("Mail Bot")
        self.geometry("1220x840")
        self.minsize(1080, 760)
        self.configure(fg_color="#EEF2EB")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build()
        self._load_initial_state()
        self.after(150, self._poll_events)

    def _build(self) -> None:
        shell = ctk.CTkFrame(self, fg_color="#EEF2EB")
        shell.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        shell.grid_rowconfigure(1, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(shell, text="Mail Bot", font=ctk.CTkFont(size=28, weight="bold"), text_color="#1F241E")
        title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.tabs = ctk.CTkTabview(
            shell,
            fg_color="#EEF2EB",
            segmented_button_fg_color="#E6ECE4",
            segmented_button_selected_color="#D8E8D7",
            segmented_button_selected_hover_color="#C7DDC6",
            segmented_button_unselected_color="#E6ECE4",
            segmented_button_unselected_hover_color="#DCE5DA",
            text_color="#2A342A",
            corner_radius=20,
        )
        self.tabs.grid(row=1, column=0, sticky="nsew")
        self.tabs.add("Arama")
        self.tabs.add("Isletmeler")
        self.tabs.add("Ayarlar")

        search_tab = self.tabs.tab("Arama")
        search_tab.grid_rowconfigure(0, weight=0)
        search_tab.grid_rowconfigure(1, weight=1)
        search_tab.grid_columnconfigure(0, weight=1)

        self.search_panel = SearchPanel(search_tab, self._handle_search)
        self.search_panel.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        self.log_panel = LogPanel(search_tab)
        self.log_panel.grid(row=1, column=0, sticky="nsew")

        businesses_tab = self.tabs.tab("Isletmeler")
        businesses_tab.grid_rowconfigure(0, weight=1)
        businesses_tab.grid_columnconfigure(0, weight=1)
        self.results_table = ResultsTable(
            businesses_tab,
            on_preview=self._open_preview,
            on_send_approved=self.controller.send_approved,
            on_skip=self._skip_selected,
            on_clear=self._clear_companies,
        )
        self.results_table.grid(row=0, column=0, sticky="nsew")

        settings_tab = self.tabs.tab("Ayarlar")
        settings_tab.grid_rowconfigure(0, weight=1)
        settings_tab.grid_columnconfigure(0, weight=1)
        self.settings_panel = SettingsPanel(settings_tab, self._save_settings, self._run_integration_check)
        self.settings_panel.grid(row=0, column=0, sticky="nsew")

    def _load_initial_state(self) -> None:
        settings = self.controller.load_settings()
        self.settings_panel.fill(settings)
        for company in self.controller.list_companies():
            self._companies[company.id] = company
            self.results_table.upsert_company(company)

    def _handle_search(self, sector: str, city: str, limit: int) -> None:
        if not sector or not city:
            messagebox.showwarning("Eksik Bilgi", "Sektor ve sehir alanlarini doldurun.")
            return
        self.controller.start_search(sector, city, limit, self.settings_panel.current_settings())

    def _save_settings(self, settings: Settings) -> None:
        self.controller.save_settings(settings)
        self.settings_panel.set_feedback("Ayarlar kaydedildi.")
        self.log_panel.append("Ayarlar kaydedildi.")

    def _run_integration_check(self, service: str, settings: Settings) -> None:
        self.controller.run_integration_check(service, settings)

    def _open_preview(self) -> None:
        company_id = self.results_table.selected_company_id()
        if company_id is None:
            messagebox.showinfo("Secim", "Once bir kayit secin.")
            return
        company = self.controller.get_company(company_id)
        if not company:
            messagebox.showerror("Kayit", "Secilen kayit bulunamadi.")
            return
        dialog = MailPreviewDialog(self, company, self.controller.get_interactions(company_id))
        self.wait_window(dialog)
        if not dialog.result:
            return
        action = dialog.result["action"]
        if action == "save":
            self.controller.save_draft(
                company_id,
                dialog.result["email"],
                dialog.result["subject"],
                dialog.result["body"],
                dialog.result.get("lead_type"),
                dialog.result.get("cta"),
            )
        elif action == "onayla":
            self.controller.approve_company(
                company_id,
                dialog.result["email"],
                dialog.result["subject"],
                dialog.result["body"],
                dialog.result.get("lead_type"),
                dialog.result.get("cta"),
            )
        elif action == "gonder":
            self.controller.approve_company(
                company_id,
                dialog.result["email"],
                dialog.result["subject"],
                dialog.result["body"],
                dialog.result.get("lead_type"),
                dialog.result.get("cta"),
            )
            self.controller.send_company_now(company_id)
        elif action == "skip":
            self.controller.skip_company(company_id)
        elif action == "reject":
            self.controller.reject_company(company_id, "Preview ekranindan reddedildi")

    def _skip_selected(self) -> None:
        company_id = self.results_table.selected_company_id()
        if company_id is None:
            messagebox.showinfo("Secim", "Once bir kayit secin.")
            return
        self.controller.skip_company(company_id)

    def _poll_events(self) -> None:
        for event in self.controller.poll_events():
            event_type = event["type"]
            if event_type == "company_updated":
                company: CompanyRecord = event["company"]
                self._companies[company.id] = company
                self.results_table.upsert_company(company)
            elif event_type == "log":
                self.log_panel.append(event["message"])
            elif event_type == "search_state":
                self.search_panel.set_status(event["message"], event["progress"])
            elif event_type == "manual_email_required":
                self._prompt_manual_email(event["company_id"], event["company_name"])
            elif event_type == "companies_cleared":
                self._companies.clear()
                self.results_table.clear()
            elif event_type == "settings_saved":
                self.settings_panel.set_feedback("Ayarlar kaydedildi.")
            elif event_type == "integration_check_started":
                self.settings_panel.set_feedback(f"{event['service']} testi calisiyor...")
            elif event_type == "integration_check_finished":
                result: IntegrationCheckResult = event["result"]
                self.settings_panel.set_feedback(result.message)
                self.log_panel.append(result.message)
            elif event_type == "alert":
                if event.get("level") == "error":
                    messagebox.showerror("Uyari", event["message"])
                else:
                    messagebox.showinfo("Bilgi", event["message"])
        self.after(150, self._poll_events)

    def _prompt_manual_email(self, company_id: int, company_name: str) -> None:
        email = simpledialog.askstring(
            "Email Girisi",
            f"{company_name} icin email bulunamadi.\nManuel email adresi girmek ister misiniz?",
            parent=self,
        )
        self.controller.resolve_manual_email(company_id, email)

    def _clear_companies(self) -> None:
        should_clear = messagebox.askyesno(
            "Listeyi Temizle",
            "Isletmeler listesindeki onceki kayitlar silinsin mi?\nBu islem kayitli taslaklari da temizler.",
            parent=self,
        )
        if should_clear:
            self.controller.clear_companies()

    def _on_close(self) -> None:
        self.controller.shutdown()
        self.destroy()
