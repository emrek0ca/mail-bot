from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ..models import CompanyRecord, InteractionRecord


class MailPreviewDialog(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTkBaseClass, company: CompanyRecord, interactions: list[InteractionRecord] | None = None) -> None:
        super().__init__(master)
        self.company = company
        self.interactions = interactions or []
        self.result: dict[str, str] | None = None

        self.title(f"Mail Onizleme - {company.name}")
        self.geometry("860x760")
        self.minsize(760, 620)
        self.resizable(True, True)
        self.configure(fg_color=("#EEF2EB", "#141814"))
        self.transient(master)
        self.grab_set()

        self.email_var = tk.StringVar(value=company.email or "")
        self.subject_var = tk.StringVar(value=company.mail_subject or "")
        self.lead_type_var = tk.StringVar(value="job")
        self.cta_var = tk.StringVar(value=company.recommended_cta or "")
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        shell = ctk.CTkFrame(self, fg_color=("#F7F7F2", "#1E241E"), corner_radius=24, border_width=1, border_color=("#DFE4DA", "#313831"))
        shell.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=0)
        shell.grid_columnconfigure(0, weight=1)

        content = ctk.CTkScrollableFrame(shell, fg_color="transparent")
        content.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        content.grid_columnconfigure(1, weight=1)

        summary = ctk.CTkFrame(content, fg_color=("#FBFBF8", "#252B25"), corner_radius=18, border_width=1, border_color=("#E4E8DF", "#3B423B"))
        summary.grid(row=0, column=0, columnspan=2, padx=18, pady=(18, 14), sticky="nsew")
        summary.grid_columnconfigure(1, weight=1)
        info_rows = [
            ("Lead Tipi", self.company.lead_type_label),
            ("Skor", self.company.fit_score_display),
            ("Oneri", self.company.recommended_action_label),
            ("Son Temas", self.company.last_contact_stage_label),
            ("Neden", self.company.fit_reasons or "-"),
            ("Arastirma", self.company.research_summary or self.company.company_summary or "-"),
            ("Karar Verici", self.company.decision_maker_candidates or "-"),
            ("Profil Varyanti", self.company.recommended_profile_variant or "-"),
            ("Referans Proje", self.company.recommended_reference_project or "-"),
        ]
        
        # Ek zeka sinyallerini varsa ekle
        # Veritabaninda dogrudan detected_tech_stack veya has_active_job_board_postings 
        # tutulmuyorsa, su an icin "Arastirma" alaninda gozukuyor.
        # Gelecekte ek alanlar acilirsa buraya eklenebilir.

        for row_index, (label_text, value) in enumerate(info_rows):
            ctk.CTkLabel(summary, text=label_text, text_color=("#445045", "#A3ADA4")).grid(row=row_index, column=0, padx=14, pady=(10 if row_index == 0 else 6, 0), sticky="nw")
            ctk.CTkLabel(summary, text=value, text_color=("#263027", "#DDE4DC"), justify="left", wraplength=500).grid(
                row=row_index,
                column=1,
                padx=(4, 14),
                pady=(10 if row_index == 0 else 6, 0),
                sticky="w",
            )

        ctk.CTkLabel(content, text="Mod", text_color=("#445045", "#A3ADA4")).grid(row=1, column=0, padx=18, pady=(0, 8), sticky="w")
        ctk.CTkOptionMenu(
            content,
            values=["job"],
            variable=self.lead_type_var,
            fg_color=("#E6ECE4", "#2A332B"),
            button_color=("#D8E8D7", "#3B473C"),
            button_hover_color=("#C7DDC6", "#4C5C4D"),
            text_color=("#263027", "#DDE4DC"),
            dropdown_fg_color=("#FBFBF8", "#252B25"),
            dropdown_text_color=("#263027", "#DDE4DC"),
        ).grid(row=1, column=1, padx=18, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(content, text="Kime", text_color=("#445045", "#A3ADA4")).grid(row=2, column=0, padx=18, pady=(0, 8), sticky="w")
        ctk.CTkEntry(content, textvariable=self.email_var, height=40).grid(row=2, column=1, padx=18, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(content, text="Konu", text_color=("#445045", "#A3ADA4")).grid(row=3, column=0, padx=18, pady=(0, 8), sticky="w")
        ctk.CTkEntry(content, textvariable=self.subject_var, height=40).grid(row=3, column=1, padx=18, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(content, text="Onerilen CTA", text_color=("#445045", "#A3ADA4")).grid(row=4, column=0, padx=18, pady=(0, 8), sticky="w")
        ctk.CTkEntry(content, textvariable=self.cta_var, height=40).grid(row=4, column=1, padx=18, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(content, text="Gecmis Etkilesim", text_color=("#445045", "#A3ADA4")).grid(row=5, column=0, padx=18, pady=(0, 8), sticky="nw")
        self.history_text = ctk.CTkTextbox(content, height=140, fg_color=("#FBFBF8", "#252B25"), text_color=("#314033", "#DDE4DC"), corner_radius=18)
        self.history_text.grid(row=5, column=1, padx=18, pady=(0, 12), sticky="nsew")
        self.history_text.insert("1.0", self._history_text())
        self.history_text.configure(state="disabled")

        ctk.CTkLabel(content, text="Mail Govdesi", text_color=("#445045", "#A3ADA4")).grid(row=6, column=0, padx=18, pady=(0, 8), sticky="nw")
        self.body_text = ctk.CTkTextbox(content, height=300, fg_color=("#FBFBF8", "#252B25"), text_color=("#314033", "#DDE4DC"), corner_radius=18)
        self.body_text.grid(row=7, column=0, columnspan=2, padx=18, pady=(0, 18), sticky="nsew")
        self.body_text.insert("1.0", self.company.mail_draft or "")

        button_frame = ctk.CTkFrame(shell, fg_color=("#F7F7F2", "#1E241E"))
        button_frame.grid(row=1, column=0, padx=18, pady=(0, 18), sticky="ew")

        primary_text = "Gonder" if self.company.status == "approved" else "Onayla"
        ctk.CTkButton(
            button_frame,
            text=primary_text,
            fg_color=("#D8E8D7", "#3B473C"),
            hover_color=("#C7DDC6", "#4C5C4D"),
            text_color=("#213126", "#DDE4DC"),
            command=lambda: self._finish(primary_text.lower()),
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            button_frame,
            text="Kaydet",
            fg_color=("#E6ECE4", "#2A332B"),
            hover_color=("#DCE5DA", "#354035"),
            text_color=("#263027", "#DDE4DC"),
            command=lambda: self._finish("save"),
        ).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(
            button_frame,
            text="Atla",
            fg_color=("#EEEAE5", "#2D2D2D"),
            hover_color=("#E4DDD7", "#3B3B3B"),
            text_color=("#48443F", "#A3ADA4"),
            command=lambda: self._finish("skip"),
        ).grid(row=0, column=2)
        ctk.CTkButton(
            button_frame,
            text="Reddet",
            fg_color=("#F0E3E8", "#3B2A2F"),
            hover_color=("#E7D5DD", "#4D383F"),
            text_color=("#5A3744", "#E4A4B8"),
            command=lambda: self._finish("reject"),
        ).grid(row=0, column=3, padx=(8, 0))

    def _finish(self, action: str) -> None:
        self.result = {
            "action": action,
            "email": self.email_var.get().strip(),
            "subject": self.subject_var.get().strip(),
            "body": self.body_text.get("1.0", "end").strip(),
            "lead_type": self.lead_type_var.get().strip(),
            "cta": self.cta_var.get().strip(),
        }
        self.destroy()

    def _history_text(self) -> str:
        if not self.interactions:
            return "Henuz kayitli etkileşim yok."
        lines: list[str] = []
        for item in self.interactions[:8]:
            note = f" - {item.note}" if item.note else ""
            lines.append(f"{item.created_at or '-'} | {item.stage}{note}")
        return "\n".join(lines)
