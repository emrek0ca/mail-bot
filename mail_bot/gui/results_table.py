from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Callable

import customtkinter as ctk

from ..models import CompanyRecord


STATUS_COLORS = {
    "pending": "#C8A94C",
    "ready": "#5E89B8",
    "approved": "#4D8F65",
    "sent": "#2E6E46",
    "rejected": "#8C5B6E",
    "error": "#B45A5A",
    "skipped": "#8B8F88",
    "followup_ready": "#9B59B6",
}


class ResultsTable(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_preview: Callable[[], None],
        on_send_approved: Callable[[], None],
        on_skip: Callable[[], None],
        on_clear: Callable[[], None],
        on_export: Callable[[str], None],
        on_approve_selected: Callable[[list[int]], None],
    ) -> None:
        super().__init__(master, fg_color=("#F7F7F2", "#1E241E"), corner_radius=22, border_width=1, border_color=("#E1E4DA", "#313831"))
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._companies: dict[int, CompanyRecord] = {}
        self.lead_filter_var = tk.StringVar(value="tum")
        self.history_filter_var = tk.StringVar(value="tum")
        self.recommended_only_var = tk.BooleanVar(value=False)
        self._build(on_preview, on_send_approved, on_skip, on_clear, on_export, on_approve_selected)

    def _build(
        self,
        on_preview: Callable[[], None],
        on_send_approved: Callable[[], None],
        on_skip: Callable[[], None],
        on_clear: Callable[[], None],
        on_export: Callable[[str], None],
        on_approve_selected: Callable[[list[int]], None],
    ) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(14, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")
        
        title = ctk.CTkLabel(title_frame, text="Isletmeler", font=ctk.CTkFont(size=20, weight="bold"), text_color=("#21261F", "#DDE4DC"))
        title.grid(row=0, column=0, sticky="w")
        
        self.stats_label = ctk.CTkLabel(title_frame, text="Taranan: 0 | Mail: 0 | Onay Bekleyen: 0", text_color=("#566258", "#A3ADA4"), font=ctk.CTkFont(size=12))
        self.stats_label.grid(row=0, column=1, padx=(16, 0), sticky="w")

        filters = ctk.CTkFrame(header, fg_color="transparent")
        filters.grid(row=1, column=0, pady=(10, 0), sticky="w")
        ctk.CTkSwitch(
            filters,
            text="Sadece oncelikli",
            variable=self.recommended_only_var,
            button_color="#A8C7AD",
            progress_color="#D8E8D7",
            command=self._render_all,
        ).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkOptionMenu(
            filters,
            values=["tum", "job"],
            variable=self.lead_filter_var,
            command=lambda _value: self._render_all(),
            fg_color=("#E6ECE4", "#2A332B"),
            button_color=("#D8E8D7", "#3B473C"),
            button_hover_color=("#C7DDC6", "#4C5C4D"),
            text_color=("#263027", "#DDE4DC"),
            dropdown_fg_color=("#FBFBF8", "#212621"),
            dropdown_text_color=("#263027", "#DDE4DC"),
            width=140,
        ).grid(row=0, column=1, padx=(0, 10))
        ctk.CTkOptionMenu(
            filters,
            values=["tum", "aktif", "gonderilenler", "reddedilenler"],
            variable=self.history_filter_var,
            command=lambda _value: self._render_all(),
            fg_color=("#E6ECE4", "#2A332B"),
            button_color=("#D8E8D7", "#3B473C"),
            button_hover_color=("#C7DDC6", "#4C5C4D"),
            text_color=("#263027", "#DDE4DC"),
            dropdown_fg_color=("#FBFBF8", "#212621"),
            dropdown_text_color=("#263027", "#DDE4DC"),
            width=140,
        ).grid(row=0, column=2)

        action_frame = ctk.CTkFrame(header, fg_color="transparent")
        action_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        ctk.CTkButton(
            action_frame,
            text="Onizle",
            width=110,
            fg_color=("#E6ECE4", "#2A332B"),
            hover_color=("#DCE5DA", "#354035"),
            text_color=("#263027", "#DDE4DC"),
            command=on_preview,
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            action_frame,
            text="Tum Onaylilari Gonder",
            width=170,
            fg_color=("#D8E8D7", "#3B473C"),
            hover_color=("#C7DDC6", "#4C5C4D"),
            text_color=("#213126", "#DDE4DC"),
            command=on_send_approved,
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            action_frame,
            text="Secilenleri Onayla",
            width=140,
            fg_color=("#D8E8D7", "#3B473C"),
            hover_color=("#C7DDC6", "#4C5C4D"),
            text_color=("#213126", "#DDE4DC"),
            command=lambda: on_approve_selected(self.selected_company_ids()),
        ).grid(row=0, column=2, padx=(0, 8))

        ctk.CTkButton(
            action_frame,
            text="Secilenleri Atla",
            width=120,
            fg_color=("#EEEAE5", "#2D2D2D"),
            hover_color=("#E4DDD7", "#3B3B3B"),
            text_color=("#48443F", "#A3ADA4"),
            command=on_skip,
        ).grid(row=0, column=3, padx=(0, 8))

        ctk.CTkButton(
            action_frame,
            text="Disa Aktar",
            width=110,
            fg_color="#E6ECE4",
            hover_color="#DCE5DA",
            text_color="#263027",
            command=lambda: self._handle_export(on_export),
        ).grid(row=0, column=3, padx=(0, 8))

        ctk.CTkButton(
            action_frame,
            text="Listeyi Temizle",
            width=125,
            fg_color="#F0E7E3",
            hover_color="#E8DCD6",
            text_color="#5A463D",
            command=on_clear,
        ).grid(row=0, column=4)

        table_shell = ctk.CTkFrame(self, fg_color=("#FBFBF8", "#1A1F1A"), corner_radius=18)
        table_shell.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        table_shell.grid_rowconfigure(0, weight=1)
        table_shell.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        
        is_dark = ctk.get_appearance_mode() == "Dark"
        tree_bg = "#1A1F1A" if is_dark else "#FBFBF8"
        tree_fg = "#DDE4DC" if is_dark else "#243024"
        head_bg = "#2A332B" if is_dark else "#EFF3EC"
        head_fg = "#A3ADA4" if is_dark else "#566258"

        style.configure(
            "MailBot.Treeview",
            background=tree_bg,
            fieldbackground=tree_bg,
            foreground=tree_fg,
            rowheight=34,
            borderwidth=0,
            relief="flat",
        )
        style.configure(
            "MailBot.Treeview.Heading",
            background=head_bg,
            foreground=head_fg,
            borderwidth=0,
            relief="flat",
            padding=(10, 8),
        )

        columns = ("name", "city", "lead_type", "score", "email", "stage", "action")
        self.tree = ttk.Treeview(table_shell, columns=columns, show="headings", style="MailBot.Treeview")
        self.tree.heading("name", text="Ad")
        self.tree.heading("city", text="Sehir")
        self.tree.heading("lead_type", text="Lead Tipi")
        self.tree.heading("score", text="Skor")
        self.tree.heading("email", text="Email")
        self.tree.heading("stage", text="Son Temas")
        self.tree.heading("action", text="Oneri")
        self.tree.column("name", width=220, anchor=tk.W)
        self.tree.column("city", width=100, anchor=tk.W)
        self.tree.column("lead_type", width=120, anchor=tk.W)
        self.tree.column("score", width=70, anchor=tk.W)
        self.tree.column("email", width=210, anchor=tk.W)
        self.tree.column("stage", width=120, anchor=tk.W)
        self.tree.column("action", width=110, anchor=tk.W)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(table_shell, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<ButtonRelease-1>", lambda event: self._handle_tree_open(event, on_preview))
        self.tree.bind("<Return>", lambda event: self._handle_tree_open(event, on_preview))

        for tag, color in STATUS_COLORS.items():
            self.tree.tag_configure(tag, foreground=color)

    def upsert_company(self, company: CompanyRecord) -> None:
        self._companies[company.id] = company
        self._render_all()

    def clear(self) -> None:
        self._companies.clear()
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

    def _render_all(self) -> None:
        wanted_items: list[CompanyRecord] = sorted(
            self._filtered_companies(),
            key=lambda company: (
                0 if company.is_recommended else 1,
                -(company.fit_score or -1),
                -company.id,
            ),
        )
        
        total = len(self._companies)
        sent = sum(1 for c in self._companies.values() if c.status == "sent")
        pending = sum(1 for c in self._companies.values() if c.status == "ready" or c.status == "followup_ready")
        self.stats_label.configure(text=f"Taranan: {total} | Mail Atilan: {sent} | Onay Bekleyen: {pending}")

        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        for company in wanted_items:
            values = (
                company.name,
                company.city or "-",
                company.lead_type_label,
                company.fit_score_display,
                company.email or "-",
                company.last_contact_stage_label,
                company.recommended_action_label,
            )
            self.tree.insert("", "end", iid=str(company.id), values=values, tags=(company.ui_status_key,))

    def _filtered_companies(self) -> list[CompanyRecord]:
        companies = list(self._companies.values())
        if self.recommended_only_var.get():
            companies = [company for company in companies if company.is_recommended]
        lead_filter = self.lead_filter_var.get()
        if lead_filter != "tum":
            companies = [company for company in companies if company.lead_type == lead_filter]
        history_filter = self.history_filter_var.get()
        if history_filter == "aktif":
            companies = [company for company in companies if company.status not in {"sent", "rejected"}]
        elif history_filter == "gonderilenler":
            companies = [company for company in companies if company.status == "sent"]
        elif history_filter == "reddedilenler":
            companies = [company for company in companies if company.status == "rejected"]
        return companies

    def selected_company_ids(self) -> list[int]:
        selection = self.tree.selection()
        ids: list[int] = []
        for item in selection:
            try:
                ids.append(int(item))
            except ValueError:
                continue
        return ids

    def selected_company_id(self) -> int | None:
        ids = self.selected_company_ids()
        return ids[0] if ids else None

    def _handle_tree_open(self, event: tk.Event[tk.Misc], on_preview: Callable[[], None]) -> None:
        if getattr(event, "keysym", None):
            if self.selected_company_id() is not None:
                on_preview()
            return
        row_id = self.tree.identify_row(getattr(event, "y", 0))
        region = self.tree.identify("region", getattr(event, "x", 0), getattr(event, "y", 0))
        if not row_id or region not in {"cell", "tree"}:
            return
        self.tree.selection_set(row_id)
        self.tree.focus(row_id)
        on_preview()

    def _handle_export(self, on_export: Callable[[str], None]) -> None:
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Listeyi Kaydet",
            initialfile=f"mailbot_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
        if path:
            on_export(path)
