from __future__ import annotations

from dataclasses import replace

import customtkinter as ctk

from core.config import integer
from ui.theme import MUTED, RED, TEXT, Card, button, entry, label, section


class SchedulerView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.variables = {}
        section(self, "Ritmi siz belirleyin.", "Sunucu kuralı, genel aralık ve mesaj aralığı közül en uzun süre uygulanır.")
        card = Card(self)
        card.pack(fill="x", padx=22, pady=8)
        label(card, "MESAJ GÖNDERİM ARALIĞI", 10, MUTED, "bold").pack(anchor="w", padx=22, pady=(20, 10))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=22)
        self.variables["interval_minutes"] = ctk.StringVar()
        self.variables["interval_remainder"] = ctk.StringVar()
        entry(row, self.variables["interval_minutes"], width=85).pack(side="left")
        label(row, "dakika", 13).pack(side="left", padx=(8, 22))
        entry(row, self.variables["interval_remainder"], width=85).pack(side="left")
        label(row, "saniye", 13).pack(side="left", padx=8)
        presets = ctk.CTkFrame(card, fg_color="transparent")
        presets.pack(anchor="w", padx=22, pady=16)
        for seconds in (120, 180, 300):
            button(presets, f"{seconds} sn", lambda value=seconds: self.set_preset(value), width=92).pack(side="left", padx=(0, 8))
        label(card, "Ek bekleme, seçilen etkin aralığa eklenir. Örn. 180 sn aralık + 10 sn ek bekleme = 190 sn.",
              12, wraplength=720).pack(anchor="w", padx=22, pady=(0, 20))

        section(self, "Oturum davranışı")
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=22)
        grid.grid_columnconfigure((0, 1), weight=1, uniform="schedule")
        fields = [
            ("message_gap_seconds", "Mesajlar arası ek bekleme", "saniye · 0–3600"),
            ("start_delay_seconds", "Başlangıç gecikmesi", "saniye · 3–300"),
            ("session_limit_minutes", "Çalışma süresi sınırı", "dakika · 0 = sınırsız"),
            ("server_min_interval_seconds", "Sunucunun minimum aralığı", "saniye · sunucu kuralını girin"),
        ]
        for index, (key, title, hint) in enumerate(fields):
            box = Card(grid)
            box.grid(row=index // 2, column=index % 2, sticky="ew", padx=5, pady=6)
            label(box, title, 14, TEXT, "bold").pack(anchor="w", padx=18, pady=(16, 4))
            label(box, hint, 11).pack(anchor="w", padx=18)
            self.variables[key] = ctk.StringVar()
            entry(box, self.variables[key]).pack(fill="x", padx=18, pady=(12, 18))
        loop_card = Card(self)
        loop_card.pack(fill="x", padx=27, pady=14)
        self.loop_var = ctk.BooleanVar()
        ctk.CTkSwitch(loop_card, text="Otomatik döngü", variable=self.loop_var,
                      progress_color=RED, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=18, pady=(16, 6))
        label(loop_card, "Kapalıyken etkin mesajlar bir kez gönderilir. Açıkken liste baştan devam eder.",
              12, wraplength=700).pack(anchor="w", padx=18, pady=(0, 16))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=22, pady=(4, 22))
        button(actions, "Zamanlamayı kaydet", self.save, primary=True, width=190).pack(side="right")
        self.feedback = label(actions, "Değişiklikler etkin oturumu duraklatır.", 12, wraplength=460)
        self.feedback.pack(side="left")
        self.refresh()

    def refresh(self):
        settings = self.app.settings
        self.variables["interval_minutes"].set(str(settings.interval_seconds // 60))
        self.variables["interval_remainder"].set(str(settings.interval_seconds % 60))
        for key in ("message_gap_seconds", "start_delay_seconds", "server_min_interval_seconds"):
            self.variables[key].set(str(getattr(settings, key)))
        self.variables["session_limit_minutes"].set(str(settings.session_limit_seconds // 60))
        self.loop_var.set(settings.loop)

    def set_preset(self, seconds):
        self.variables["interval_minutes"].set(str(seconds // 60))
        self.variables["interval_remainder"].set(str(seconds % 60))

    def save(self):
        try:
            minutes = integer(self.variables["interval_minutes"].get(), "Dakika", 0, 1440)
            remainder = integer(self.variables["interval_remainder"].get(), "Saniye", 0, 59)
            limit = integer(self.variables["session_limit_minutes"].get(), "Çalışma sınırı", 0, 10080)
            settings = replace(self.app.settings,
                               interval_seconds=minutes * 60 + remainder,
                               message_gap_seconds=integer(self.variables["message_gap_seconds"].get(), "Ek bekleme", 0, 3600),
                               start_delay_seconds=integer(self.variables["start_delay_seconds"].get(), "Başlangıç gecikmesi", 3, 300),
                               server_min_interval_seconds=integer(self.variables["server_min_interval_seconds"].get(), "Sunucu alt sınırı", 30, 86400),
                               session_limit_seconds=limit * 60, loop=self.loop_var.get())
            self.app.save_settings(settings)
            self.feedback.configure(text="Kaydedildi. Uygulamak için Başlat / Sürdür düğmesini kullanın.", text_color=TEXT)
        except Exception as exc:
            self.app.handle_error("Zamanlama kaydedilemedi", exc)
            self.feedback.configure(text=str(exc), text_color=RED)
