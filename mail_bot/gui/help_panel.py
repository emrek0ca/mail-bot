from __future__ import annotations

import customtkinter as ctk


class HelpPanel(ctk.CTkScrollableFrame):
    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(
            master,
            fg_color=("#F7F7F2", "#1E241E"),
            corner_radius=22,
            border_width=1,
            border_color=("#E1E4DA", "#313831"),
        )
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self) -> None:
        title = ctk.CTkLabel(
            self,
            text="Yardım ve Kullanım Kılavuzu",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=("#21261F", "#DDE4DC"),
        )
        title.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="w")

        sections = [
            (
                "🚀 Başlangıç",
                "Mail Bot, Google Maps verilerini kullanarak şirketleri bulur ve AI desteği ile kişiselleştirilmiş "
                "başvuru mailleri hazırlar. Kullanmaya başlamak için Ayarlar sekmesinden API anahtarlarınızı girin.",
            ),
            (
                "🔑 Gemini / OpenAI API Key",
                "• Gemini için: Google AI Studio üzerinden ücretsiz bir API anahtarı alabilirsiniz.\n"
                "• OpenAI için: OpenAI platformu üzerinden ücretli (veya varsa kredili) anahtar alabilirsiniz.\n"
                "Uygulama, şirketin web sitesini analiz etmek ve mail yazmak için bu zekayı kullanır.",
            ),
            (
                "✉️ Gmail Uygulama Şifresi",
                "Gmail adresinizle mail gönderebilmek için standart şifreniz yerine 'Uygulama Şifresi' kullanmalısınız.\n"
                "1. Google Hesabınızda 2 Adımlı Doğrulamayı açın.\n"
                "2. Güvenlik sekmesinden 'Uygulama Şifreleri' kısmına gidin.\n"
                "3. 'Mail' ve 'Mac/Windows' seçerek şifre üretin ve kopyalayıp Ayarlar'a yapıştırın.",
            ),
            (
                "📄 CV ve Portfolyo",
                "Gönderilecek maillere otomatik olarak PDF dosyalarınızı ekleyebilirsiniz. Ayarlar'da "
                "ana CV, ikincil CV ve portfolyo yollarını belirleyin.",
            ),
            (
                "🔍 Şirket Arama",
                "Arama sekmesinde bir sektör (örn: 'Yazılım', 'Dijital Ajans') ve bir şehir girin.\n"
                "Uygulama şirketleri bulur, web sitelerini tarar ve sizin için bir 'Uygunluk Skoru' belirler.",
            ),
            (
                "✅ Onay ve Gönderim",
                "İşletmeler sekmesinde hazırlanan taslakları görebilirsiniz. Bir kayda tıklayıp 'Önizle' "
                "diyerek maili düzenleyebilir ve onaylayabilirsiniz. 'Tüm Onaylıları Gönder' butonu ile "
                "onayladığınız tüm mailler sırayla gönderilir.",
            ),
        ]

        for i, (head, body) in enumerate(sections):
            row = i + 1
            f = ctk.CTkFrame(self, fg_color="transparent")
            f.grid(row=row, column=0, padx=24, pady=10, sticky="ew")
            f.grid_columnconfigure(0, weight=1)

            h = ctk.CTkLabel(
                f,
                text=head,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=("#3B473C", "#A8C7AD"),
            )
            h.grid(row=0, column=0, sticky="w")

            b = ctk.CTkLabel(
                f,
                text=body,
                justify="left",
                wraplength=900,
                text_color=("#566258", "#A3ADA4"),
            )
            b.grid(row=1, column=0, pady=(4, 0), sticky="w")
