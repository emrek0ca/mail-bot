from __future__ import annotations

import tkinter as tk
from typing import Callable

import customtkinter as ctk


class SearchPanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, on_search: Callable[[str, str, int], None]) -> None:
        super().__init__(
            master,
            fg_color="#F7F7F2",
            corner_radius=22,
            border_width=1,
            border_color="#E1E4DA",
        )
        self.on_search = on_search
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_columnconfigure(3, weight=0)

        self.sector_var = tk.StringVar()
        self.city_var = tk.StringVar()
        self.limit_var = tk.StringVar(value="20")

        self._build()

    def _build(self) -> None:
        title = ctk.CTkLabel(self, text="Arama", font=ctk.CTkFont(size=20, weight="bold"), text_color="#21261F")
        title.grid(row=0, column=0, padx=18, pady=(16, 4), sticky="w")

        subtitle = ctk.CTkLabel(
            self,
            text="Google Maps uzerinden isletme bul ve taslaklarini hazirla.",
            text_color="#647067",
        )
        subtitle.grid(row=1, column=0, columnspan=4, padx=18, pady=(0, 14), sticky="w")

        self.sector_entry = ctk.CTkEntry(self, textvariable=self.sector_var, placeholder_text="Sektor", height=42)
        self.sector_entry.grid(row=2, column=0, padx=(18, 8), pady=(0, 12), sticky="ew")

        self.city_entry = ctk.CTkEntry(self, textvariable=self.city_var, placeholder_text="Sehir", height=42)
        self.city_entry.grid(row=2, column=1, padx=8, pady=(0, 12), sticky="ew")

        self.limit_entry = ctk.CTkEntry(self, textvariable=self.limit_var, placeholder_text="Kac sirket?", height=42)
        self.limit_entry.grid(row=2, column=2, padx=8, pady=(0, 12), sticky="ew")

        self.search_button = ctk.CTkButton(
            self,
            text="Tara",
            height=42,
            corner_radius=16,
            fg_color="#D8E8D7",
            hover_color="#C7DDC6",
            text_color="#213126",
            command=self._handle_search,
        )
        self.search_button.grid(row=2, column=3, padx=(8, 18), pady=(0, 12), sticky="ew")

        self.progress = ctk.CTkProgressBar(self, progress_color="#9CC4A5", fg_color="#E9EEE5")
        self.progress.grid(row=3, column=0, columnspan=3, padx=(18, 8), pady=(0, 8), sticky="ew")
        self.progress.set(0)
        
        self.btn_followups = ctk.CTkButton(
            self,
            text="Takipleri Kontrol Et",
            height=30,
            corner_radius=12,
            fg_color="#E6ECE4",
            hover_color="#DCE5DA",
            text_color="#263027",
            command=lambda: getattr(self.master.winfo_toplevel(), "controller").check_followups(),
        )
        self.btn_followups.grid(row=3, column=3, padx=(8, 18), pady=(0, 8), sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="Hazir.", text_color="#647067")
        self.status_label.grid(row=4, column=0, columnspan=4, padx=18, pady=(0, 16), sticky="w")

    def _handle_search(self) -> None:
        try:
            limit = max(1, int(self.limit_var.get().strip() or "20"))
        except ValueError:
            self.set_status("Sayi alani gecersiz.", 0.0)
            return
        self.on_search(self.sector_var.get().strip(), self.city_var.get().strip(), limit)

    def set_status(self, message: str, progress: float) -> None:
        self.status_label.configure(text=message)
        self.progress.set(max(0.0, min(progress, 1.0)))

