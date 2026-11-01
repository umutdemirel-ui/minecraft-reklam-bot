from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from core.config import integer
from core.startup import open_data_folder, set_startup
from ui.theme import GREEN, RED, TEXT, Card, button, entry, label, section


class SettingsView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        section(self, "Önce güvenlik.", "Bu uygulama sunucu kurallarını okuyamaz. İzinli sunucularda ve sunucunun gerektirdiği aralıklarla kullanın.")
        safety = Card(self)
        safety.pack(fill="x", padx=22, pady=8)
        self.allowed_var = ctk.BooleanVar()
        self.chat_var = ctk.BooleanVar()
        ctk.CTkCheckBox(safety, text="Sunucum bu otomatik sohbet mesajlarına açıkça izin veriyor.",
                        variable=self.allowed_var, font=ctk.CTkFont(size=13), checkbox_width=20,
                        checkbox_height=20,
                        ).pack(anchor="w", padx=20, pady=(20, 12))
        ctk.CTkCheckBox(safety, text="Varsayılan T sohbet düzenini kullanıyorum; gönderimde menü açık olmayacak.",
                        variable=self.chat_var, font=ctk.CTkFont(size=12), checkbox_width=20,
                        checkbox_height=20).pack(anchor="w", padx=20, pady=(0, 12))
        label(safety, "Sohbetin gerçekten açıldığını görüntüden doğrulama yapılmaz. T düzeni değişmişse otomasyonu kullanmayın.\n"
              "Farklı odak, yanıt vermeyen pencere, giriş hatası veya belirsiz sonuç güvenli duraklatma yaratır.",
              11, wraplength=760).pack(anchor="w", padx=20, pady=(0, 18))
        row = ctk.CTkFrame(safety, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        label(row, "Sunucu karakter sınırı", 13, TEXT).pack(side="left")
        self.length_var = ctk.StringVar()
        entry(row, self.length_var, width=85).pack(side="left", padx=12)
        label(row, "Java 1.19+ için en fazla 256; eski sürümlerde daha düşük olabilir.", 11,
              wraplength=440).pack(side="left")

        section(self, "Pencere tespiti", "Yalnızca java.exe / javaw.exe süreçleri kabul edilir. Launcher ve Bedrock pencereleri hedeflenmez.")
        detection = Card(self)
        detection.pack(fill="x", padx=22, pady=8)
        label(detection, "Tam pencere başlığı (isteğe bağlı)", 13, TEXT).pack(anchor="w", padx=20, pady=(16, 6))
        self.window_var = ctk.StringVar()
        entry(detection, self.window_var, placeholder_text="Boş bırakın: Minecraft / Minecraft* otomatik tespiti").pack(fill="x", padx=20)
        label(detection, "Özel başlık tam olarak eşleşmelidir. Birden fazla aday varsa Dashboard'dan hedef seçin.\n"
              "Uygulama pencereyi öne getirmez; Minecraft'ı siz öne getirmelisiniz.", 11,
              wraplength=750).pack(anchor="w", padx=20, pady=(8, 18))

        section(self, "Uygulama tercihleri")
        preferences = Card(self)
        preferences.pack(fill="x", padx=22, pady=8)
        row = ctk.CTkFrame(preferences, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=18)
        label(row, "Tema", 13, TEXT).pack(side="left")
        self.theme_var = ctk.StringVar()
        ctk.CTkOptionMenu(row, variable=self.theme_var, values=["Koyu", "Açık", "Sistem"], width=160).pack(side="left", padx=18)
        self.startup_var = ctk.BooleanVar()
        ctk.CTkSwitch(row, text="Windows başlangıcında uygulamayı aç", variable=self.startup_var,
                      font=ctk.CTkFont(size=12)).pack(side="right")
        label(preferences, "Başlangıç tercihi yalnızca uygulamayı açar; otomasyon asla kendiliğinden başlamaz.",
              11).pack(anchor="w", padx=20, pady=(0, 16))
        hotkey_row = ctk.CTkFrame(preferences, fg_color="transparent")
        hotkey_row.pack(fill="x", padx=20, pady=(0, 18))
        self.hotkey_label = label(hotkey_row, "", 12, GREEN, wraplength=570)
        self.hotkey_label.pack(side="left")
        button(hotkey_row, "F8'i yeniden kaydet", self.register_hotkey, width=160).pack(side="right")

        section(self, "Veriler ve yedekleme")
        data = Card(self)
        data.pack(fill="x", padx=22, pady=8)
        label(data, str(self.app.paths.data), 12, TEXT, wraplength=750).pack(anchor="w", padx=20, pady=(18, 6))
        label(data, "Mesajlar, ayarlar ve geçmiş SQLite'ta saklanır. Yedekleme tutarlı bir veritabanı kopyası oluşturur.",
              11, wraplength=750).pack(anchor="w", padx=20)
        actions = ctk.CTkFrame(data, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=16)
        self.backup_button = button(actions, "Veritabanını yedekle", self.backup, width=185)
        self.backup_button.pack(side="left")
        button(actions, "Veri klasörünü aç", lambda: open_data_folder(self.app.paths.data), width=155).pack(side="left", padx=10)
        self.backup_status = label(data, "", 11, wraplength=750)
        self.backup_status.pack(anchor="w", padx=20, pady=(0, 16))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=22, pady=22)
        button(bottom, "Ayarları kaydet", self.save, primary=True, width=165).pack(side="right")
        label(bottom, "Kilitli korumalar: aktif odak doğrulaması · yanlış hedef engeli\n"
              "F8 acil durdurma · otomatik yeniden deneme yok · komut gönderimi yok", 11,
              wraplength=580).pack(side="left")
        self.refresh()

    def refresh(self):
        settings = self.app.settings
        self.allowed_var.set(settings.automation_allowed)
        self.chat_var.set(settings.default_chat_confirmed)
        self.length_var.set(str(settings.max_message_length))
        self.window_var.set(settings.window_title)
        self.theme_var.set(settings.theme)
        self.startup_var.set(settings.launch_on_startup)
        self.update_hotkey()

    def update_hotkey(self):
        self.hotkey_label.configure(text="F8 acil durdurma etkin" if self.app.hotkeys.ready else self.app.hotkeys.error,
                                    text_color=GREEN if self.app.hotkeys.ready else RED)

    def register_hotkey(self):
        self.app.hotkeys.register()
        self.update_hotkey()
        self.app.refresh_data()

    def save(self):
        try:
            settings = replace(self.app.settings, automation_allowed=self.allowed_var.get(),
                               default_chat_confirmed=self.chat_var.get(), window_title=self.window_var.get().strip(),
                               theme=self.theme_var.get(), launch_on_startup=self.startup_var.get(),
                               max_message_length=integer(self.length_var.get(), "Karakter sınırı", 1, 256))
            previous = self.app.settings
            self.app.save_settings(settings)
            if settings.launch_on_startup != previous.launch_on_startup:
                try:
                    set_startup(settings.launch_on_startup)
                except Exception:
                    self.app.save_settings(previous)
                    raise
            self.backup_status.configure(text="Ayarlar kaydedildi.", text_color=GREEN)
        except Exception as exc:
            self.app.handle_error("Ayarlar kaydedilemedi", exc)
            self.backup_status.configure(text=str(exc), text_color=RED)
            self.refresh()

    def backup(self):
        filename = filedialog.asksaveasfilename(parent=self, title="Veritabanı yedeği",
                                               initialfile=f"AutoAdvertiser-{datetime.now():%Y%m%d-%H%M%S}.db",
                                               defaultextension=".db", filetypes=[("SQLite veritabanı", "*.db")])
        if not filename:
            return
        self.backup_button.configure(state="disabled", text="Yedekleniyor…")

        def work():
            try:
                self.app.db.backup(filename)
                self.app.ui_events.put(("backup", f"Yedek doğrulandı: {filename}"))
            except Exception as exc:
                self.app.ui_events.put(("error", ("Yedekleme başarısız", str(exc))))
        threading.Thread(target=work, name="database-backup", daemon=True).start()

    def backup_result(self, text, error=False):
        self.backup_button.configure(state="normal", text="Veritabanını yedekle")
        self.backup_status.configure(text=text, text_color=RED if error else GREEN)
