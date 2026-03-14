from __future__ import annotations

import tkinter as tk
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from ..models import Settings


class SettingsPanel(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_save: Callable[[Settings], None],
        on_check: Callable[[str, Settings], None],
    ) -> None:
        super().__init__(master, fg_color="#F7F7F2", corner_radius=22, border_width=1, border_color="#E1E4DA")
        self.on_save = on_save
        self.on_check = on_check
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.vars = {
            "ai_provider": tk.StringVar(value="gemini"),
            "gemini_api_key": tk.StringVar(),
            "gemini_model": tk.StringVar(),
            "openai_api_key": tk.StringVar(),
            "openai_model": tk.StringVar(),
            "gmail_address": tk.StringVar(),
            "gmail_app_password": tk.StringVar(),
            "cv_path": tk.StringVar(),
            "cv_path_secondary": tk.StringVar(),
            "portfolio_pdf_path": tk.StringVar(),
            "user_name": tk.StringVar(),
            "user_title": tk.StringVar(),
            "user_phone": tk.StringVar(),
            "github_url": tk.StringVar(),
            "linkedin_url": tk.StringVar(),
            "portfolio_url": tk.StringVar(),
        }
        self.text_values = {
            "target_roles": "",
            "expertise_areas": "",
            "project_highlights": "",
            "service_value_prop": "",
        }
        self.textboxes: dict[str, ctk.CTkTextbox] = {}
        self.feedback_label: ctk.CTkLabel | None = None
        self._build()

    def _build(self) -> None:
        title = ctk.CTkLabel(self, text="Ayarlar", font=ctk.CTkFont(size=20, weight="bold"), text_color="#21261F")
        title.grid(row=0, column=0, padx=18, pady=(16, 4), sticky="w")

        subtitle = ctk.CTkLabel(
            self,
            text="AI saglayicisi, profil linkleri, CV seti ve basvuran bilgilerini buradan yonet.",
            text_color="#647067",
        )
        subtitle.grid(row=1, column=0, columnspan=2, padx=18, pady=(0, 14), sticky="w")

        ctk.CTkLabel(self, text="AI Saglayicisi", text_color="#445045").grid(
            row=2, column=0, padx=18, pady=(0, 6), sticky="w"
        )
        provider_menu = ctk.CTkOptionMenu(
            self,
            values=["gemini", "openai"],
            variable=self.vars["ai_provider"],
            height=40,
            fg_color="#E6ECE4",
            button_color="#D8E8D7",
            button_hover_color="#C7DDC6",
            text_color="#263027",
            dropdown_fg_color="#FBFBF8",
            dropdown_text_color="#263027",
        )
        provider_menu.grid(row=3, column=0, padx=18, pady=(0, 12), sticky="ew")

        fields = [
            ("Gemini API Key", "gemini_api_key"),
            ("Gemini Model", "gemini_model"),
            ("OpenAI API Key", "openai_api_key"),
            ("OpenAI Model", "openai_model"),
            ("Gmail Adresi", "gmail_address"),
            ("Gmail Uygulama Sifresi", "gmail_app_password"),
            ("Ad Soyad", "user_name"),
            ("Unvan / Meslek", "user_title"),
            ("Telefon", "user_phone"),
            ("GitHub", "github_url"),
            ("LinkedIn", "linkedin_url"),
            ("Portfolio URL", "portfolio_url"),
        ]
        for index, (label_text, key) in enumerate(fields):
            column = index % 2
            row = 4 + (index // 2) * 2
            ctk.CTkLabel(self, text=label_text, text_color="#445045").grid(
                row=row, column=column, padx=18, pady=(0, 6), sticky="w"
            )
            entry = ctk.CTkEntry(
                self,
                textvariable=self.vars[key],
                height=40,
                show="*" if "password" in key or "api_key" in key else None,
            )
            entry.grid(row=row + 1, column=column, padx=18, pady=(0, 12), sticky="ew")

        current_row = 4 + ((len(fields) + 1) // 2) * 2
        file_fields = [
            ("Ana CV", "cv_path", self._choose_cv),
            ("Ikinci CV", "cv_path_secondary", self._choose_secondary_cv),
            ("Portfolio PDF", "portfolio_pdf_path", self._choose_portfolio_pdf),
        ]
        for label_text, key, command in file_fields:
            ctk.CTkLabel(self, text=label_text, text_color="#445045").grid(row=current_row, column=0, padx=18, pady=(0, 6), sticky="w")
            frame = ctk.CTkFrame(self, fg_color="transparent")
            frame.grid(row=current_row + 1, column=0, columnspan=2, padx=18, pady=(0, 12), sticky="ew")
            frame.grid_columnconfigure(0, weight=1)
            ctk.CTkEntry(frame, textvariable=self.vars[key], height=40).grid(row=0, column=0, sticky="ew", padx=(0, 8))
            ctk.CTkButton(
                frame,
                text="Sec",
                width=90,
                fg_color="#E6ECE4",
                hover_color="#DCE5DA",
                text_color="#263027",
                command=command,
            ).grid(row=0, column=1)
            current_row += 2

        multiline_fields = [
            ("Hedef Roller", "target_roles", 80),
            ("Uzmanlik Alanlari", "expertise_areas", 80),
            ("Referans Projeler", "project_highlights", 110),
            ("Hizmet Deger Onerisi", "service_value_prop", 110),
        ]
        for index, (label_text, key, height) in enumerate(multiline_fields):
            column = index % 2
            row = current_row + (index // 2) * 2
            ctk.CTkLabel(self, text=label_text, text_color="#445045").grid(row=row, column=column, padx=18, pady=(0, 6), sticky="w")
            textbox = ctk.CTkTextbox(self, height=height, fg_color="#FBFBF8", text_color="#314033", corner_radius=16)
            textbox.grid(row=row + 1, column=column, padx=18, pady=(0, 12), sticky="nsew")
            self.textboxes[key] = textbox

        self.feedback_label = ctk.CTkLabel(self, text="", text_color="#647067")
        current_row += ((len(multiline_fields) + 1) // 2) * 2
        self.feedback_label.grid(row=current_row, column=0, columnspan=2, padx=18, pady=(0, 10), sticky="w")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=current_row + 1, column=0, columnspan=2, padx=18, pady=(0, 16), sticky="w")

        ctk.CTkButton(
            actions,
            text="Kaydet",
            fg_color="#D8E8D7",
            hover_color="#C7DDC6",
            text_color="#213126",
            command=self._save,
        ).grid(row=0, column=0, padx=(0, 10), sticky="w")
        ctk.CTkButton(
            actions,
            text="AI Test",
            fg_color="#E6ECE4",
            hover_color="#DCE5DA",
            text_color="#263027",
            command=lambda: self._check("ai"),
        ).grid(row=0, column=1, padx=(0, 10), sticky="w")
        ctk.CTkButton(
            actions,
            text="Gmail Test",
            fg_color="#E6ECE4",
            hover_color="#DCE5DA",
            text_color="#263027",
            command=lambda: self._check("gmail"),
        ).grid(row=0, column=2, padx=(0, 10), sticky="w")
        ctk.CTkButton(
            actions,
            text="Tarayici Test",
            fg_color="#E6ECE4",
            hover_color="#DCE5DA",
            text_color="#263027",
            command=lambda: self._check("playwright"),
        ).grid(row=0, column=3, sticky="w")

    def _choose_cv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            self.vars["cv_path"].set(path)

    def _choose_secondary_cv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            self.vars["cv_path_secondary"].set(path)

    def _choose_portfolio_pdf(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            self.vars["portfolio_pdf_path"].set(path)

    def fill(self, settings: Settings) -> None:
        for key, value in settings.as_mapping().items():
            if key in self.vars:
                self.vars[key].set(value)
            elif key in self.textboxes:
                self.text_values[key] = value
        for key, textbox in self.textboxes.items():
            textbox.delete("1.0", "end")
            textbox.insert("1.0", getattr(settings, key, self.text_values.get(key, "")))

    def set_feedback(self, text: str) -> None:
        if self.feedback_label:
            self.feedback_label.configure(text=text)

    def _save(self) -> None:
        self.on_save(self.current_settings())

    def _check(self, service: str) -> None:
        self.set_feedback("Servis testi calisiyor...")
        self.on_check(service, self.current_settings())

    def current_settings(self) -> Settings:
        values = {key: variable.get() for key, variable in self.vars.items()}
        for key, textbox in self.textboxes.items():
            values[key] = textbox.get("1.0", "end").strip()
        return Settings.from_mapping(values)
