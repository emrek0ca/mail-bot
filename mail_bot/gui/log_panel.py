from __future__ import annotations

import customtkinter as ctk


class LogPanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color=("#F7F7F2", "#1E241E"), corner_radius=22, border_width=1, border_color=("#E1E4DA", "#313831"))
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(self, text="Log", font=ctk.CTkFont(size=20, weight="bold"), text_color=("#21261F", "#DDE4DC"))
        title.grid(row=0, column=0, padx=16, pady=(14, 10), sticky="w")

        self.textbox = ctk.CTkTextbox(self, fg_color=("#FBFBF8", "#1A1F1A"), text_color=("#314033", "#DDE4DC"), corner_radius=18)
        self.textbox.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        self.textbox.configure(state="disabled")

    def append(self, message: str) -> None:
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"{message}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

