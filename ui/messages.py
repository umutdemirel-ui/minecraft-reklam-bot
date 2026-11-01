from __future__ import annotations

import tkinter.messagebox as messagebox

import customtkinter as ctk

from core.config import ConfigError
from database.models import Message, validate_message
from ui.theme import GREEN, MUTED, RED, TEXT, Card, button, entry, font, label


class MessageDialog(ctk.CTkToplevel):
    def __init__(self, app, message: Message | None = None):
        super().__init__(app)
        self.app, self.message = app, message
        self.title("Mesajı düzenle" if message else "Yeni mesaj")
        self.geometry("560x530")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()
        self.title_var = ctk.StringVar(value=message.title if message else "")
        self.interval_var = ctk.StringVar(value=str(message.interval_seconds if message else app.settings.interval_seconds))
        self.active_var = ctk.BooleanVar(value=message.active if message else True)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=26, pady=24)
        label(body, "MESAJ DETAYLARI", 11, MUTED, "bold").pack(anchor="w", pady=(0, 16))
        label(body, "Mesaj başlığı", 13, TEXT).pack(anchor="w")
        entry(body, self.title_var, placeholder_text="Örn. Skyblock market").pack(fill="x", pady=(5, 14))
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")
        label(row, "Mesaj içeriği", 13, TEXT).pack(side="left")
        self.counter = label(row, "", 11)
        self.counter.pack(side="right")
        self.content = ctk.CTkTextbox(body, height=120, corner_radius=8, border_width=1,
                                     font=font(14), wrap="word")
        self.content.pack(fill="x", pady=(5, 6))
        if message:
            self.content.insert("1.0", message.content)
        self.content.bind("<KeyRelease>", self._count)
        self.content.bind("<<Paste>>", lambda event: self.after_idle(self._count))
        label(body, f"Tek satır · En fazla {app.settings.max_message_length} karakter · Komutlar (/) kapalı", 11).pack(anchor="w")
        row2 = ctk.CTkFrame(body, fg_color="transparent")
        row2.pack(fill="x", pady=(18, 8))
        label(row2, "Bu mesajın aralığı (saniye)", 13, TEXT).pack(side="left")
        entry(row2, self.interval_var, width=100).pack(side="right")
        label(body, "Genel aralık ve sunucu alt sınırından büyük olan uygulanır.", 11).pack(anchor="w")
        ctk.CTkSwitch(body, "Mesaj etkin", variable=self.active_var, progress_color=RED,
                      font=font()).pack(anchor="w", pady=18)
        self.error = label(body, "", 12, RED, wraplength=490)
        self.error.pack(anchor="w")
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", side="bottom")
        button(actions, "Kaydet", self.save, primary=True).pack(side="right")
        button(actions, "Vazgeç", self.destroy, width=90).pack(side="right", padx=8)
        self._count()
        self.after(100, lambda: self.attributes("-topmost", False))
        self.bind("<Escape>", lambda event: self.destroy())

    def _count(self, event=None):
        count = len(self.content.get("1.0", "end-1c").strip())
        self.counter.configure(text=f"{count} / {self.app.settings.max_message_length}",
                               text_color=RED if count > self.app.settings.max_message_length else MUTED)

    def save(self):
        try:
            interval = int(self.interval_var.get())
            title, content, interval = validate_message(self.title_var.get(), self.content.get("1.0", "end-1c"),
                                                         interval, self.app.settings.max_message_length)
            if self.message:
                self.app.db.update_message(self.message.id, title, content, self.active_var.get(), interval,
                                           self.app.settings.max_message_length)
            else:
                self.app.db.add_message(title, content, self.active_var.get(), interval,
                                        self.app.settings.max_message_length)
            self.app.messages_changed()
            self.destroy()
        except (ValueError, ConfigError) as exc:
            self.error.configure(text=str(exc) if isinstance(exc, ConfigError) else "Aralık tam sayı olmalı.")
        except Exception as exc:
            self.app.handle_error("Mesaj kaydedilemedi", exc)


class Messages(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(8, 16))
        self.summary = label(top, "Mesaj kuyruğu", 13)
        self.summary.pack(side="left")
        button(top, "+  Yeni mesaj", lambda: MessageDialog(app), primary=True, width=140).pack(side="right")
        label(self, "Mesajlar aşağıdaki sırayla gönderilir. Etkinlik, içerik veya sıra değişirse oturum duraklatılır ve kuyruk başa alınır.",
              12, wraplength=780).pack(anchor="w", padx=14, pady=(0, 14))
        self.list = ctk.CTkFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True, padx=14)
        self.refresh()

    def refresh(self):
        for child in self.list.winfo_children():
            child.destroy()
        messages = self.app.db.messages()
        self.summary.configure(text=f"{len(messages)} mesaj  /  {sum(m.active for m in messages)} etkin")
        if not messages:
            empty = Card(self.list)
            empty.pack(fill="x", pady=8)
            label(empty, "İlk mesajınızla başlayın.", 22, TEXT, "bold").pack(anchor="w", padx=24, pady=(28, 8))
            label(empty, "Başlık verin, sohbet metnini yazın ve gönderim aralığını seçin.\n"
                  "Örnek: Marketim açıldı! Uygun fiyatlar için beklerim.", 13, wraplength=650).pack(anchor="w", padx=24, pady=(0, 20))
            button(empty, "+  Mesaj ekle", lambda: MessageDialog(self.app), primary=True).pack(anchor="w", padx=24, pady=(0, 24))
        for index, message in enumerate(messages, 1):
            self._row(index, message)

    def _row(self, index, message):
        card = Card(self.list)
        card.pack(fill="x", pady=(0, 10))
        card.grid_columnconfigure(1, weight=1)
        label(card, f"{index:02d}", 18, RED, "bold", family="Consolas").grid(row=0, column=0, rowspan=2, padx=18, pady=18, sticky="n")
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.grid(row=0, column=1, sticky="ew", pady=16)
        label(content, message.title, 15, TEXT, "bold", wraplength=470).pack(anchor="w")
        label(content, message.content, 13, MUTED, wraplength=540).pack(anchor="w", pady=(5, 0))
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=0, column=2, padx=18, sticky="e")
        var = ctk.BooleanVar(value=message.active)
        ctk.CTkSwitch(actions, text="Etkin" if message.active else "Pasif", variable=var,
                      font=font(11), width=76, progress_color=GREEN,
                      command=lambda m=message, v=var: self.toggle(m, v.get())).pack(anchor="e", pady=(0, 8))
        row = ctk.CTkFrame(actions, fg_color="transparent")
        row.pack(anchor="e")
        button(row, "Düzenle", lambda m=message: MessageDialog(self.app, m), width=78).pack(side="left", padx=(0, 6))
        button(row, "Sil", lambda m=message: self.delete(m), danger=True, width=52).pack(side="left")
        label(card, f"Aralık ≥ {message.interval_seconds} saniye   ·   Sıra #{index}", 11).grid(row=1, column=1, sticky="w", pady=(0, 12))

    def toggle(self, message, active):
        try:
            self.app.db.update_message(message.id, message.title, message.content, active,
                                       message.interval_seconds, self.app.settings.max_message_length)
            self.app.messages_changed()
        except Exception as exc:
            self.app.handle_error("Mesaj güncellenemedi", exc)
            self.refresh()

    def delete(self, message):
        if messagebox.askyesno("Mesajı sil", f"“{message.title}” silinsin mi? Geçmiş kayıtları korunur.", parent=self):
            try:
                self.app.db.delete_message(message.id)
                self.app.messages_changed()
            except Exception as exc:
                self.app.handle_error("Mesaj silinemedi", exc)
