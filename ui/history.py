from __future__ import annotations

import tkinter.messagebox as messagebox
from datetime import datetime
from tkinter import ttk

import customtkinter as ctk

from ui.theme import CARD, button, label

STATUS = {"sent": "Gönderildi*", "failed": "Başarısız", "aborted": "Kesildi",
          "unknown": "Belirsiz", "pending": "Hazırlanıyor", "sending": "Gönderiliyor"}


class History(ctk.CTkFrame):
    PAGE_SIZE = 100

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.page = 0
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(8, 14))
        self.summary = label(top, "Gönderim kayıtları", 13)
        self.summary.pack(side="left")
        button(top, "Geçmişi temizle", self.clear, danger=True, width=145).pack(side="right")
        button(top, "Yenile", self.refresh, width=80).pack(side="right", padx=8)
        table_frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        table_frame.pack(fill="both", expand=True, padx=24)
        style = ttk.Style(self)
        style.theme_use("clam")
        dark = ctk.get_appearance_mode() == "Dark"
        table_bg, table_text = ("#171A20", "#F2F3F5") if dark else ("#FFFFFF", "#171B22")
        heading_bg, heading_text = ("#22262E", "#AEB5C0") if dark else ("#E9EBEF", "#626B78")
        style.configure("History.Treeview", background=table_bg, fieldbackground=table_bg,
                        foreground=table_text, rowheight=38, borderwidth=0, font=("Segoe UI", 10))
        style.configure("History.Treeview.Heading", background=heading_bg, foreground=heading_text,
                        borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("History.Treeview", background=[("selected", "#542B2B")], foreground=[("selected", "#FFFFFF")])
        columns = ("time", "title", "content", "status", "error")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", style="History.Treeview", selectmode="browse")
        for column, title, width in (("time", "Zaman (yerel)", 150), ("title", "Başlık", 130),
                                     ("content", "Mesaj", 290), ("status", "Durum", 100), ("error", "Ayrıntı", 210)):
            self.table.heading(column, text=title)
            self.table.column(column, width=width, minwidth=75, stretch=column == "content")
        scrollbar = ctk.CTkScrollbar(table_frame, orientation="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.pack(side="right", fill="y", padx=6, pady=8)
        self.table.tag_configure("unknown", foreground="#EFC174")
        self.table.tag_configure("failed", foreground="#F47E77")
        self.table.tag_configure("aborted", foreground="#AEB5C0")
        self.table.bind("<Double-1>", self.detail)
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=24, pady=14)
        label(bottom, "* Enter gönderildi; sunucunun mesajı kabul ettiği doğrulanmış değildir.", 11,
              wraplength=630).pack(side="left")
        button(bottom, "→", lambda: self.turn(1), width=38).pack(side="right")
        button(bottom, "←", lambda: self.turn(-1), width=38).pack(side="right", padx=6)
        self.page_label = label(bottom, "1", 12)
        self.page_label.pack(side="right", padx=6)
        self.refresh()

    def refresh(self):
        self.table.delete(*self.table.get_children())
        rows = self.app.db.history(self.PAGE_SIZE, self.page * self.PAGE_SIZE)
        self.rows = {row.id: row for row in rows}
        for row in rows:
            try:
                when = datetime.fromisoformat(row.created_at).astimezone().strftime("%d.%m.%Y %H:%M:%S")
            except ValueError:
                when = row.created_at
            self.table.insert("", "end", iid=row.id, values=(when, row.title, row.content.replace("\n", " "),
                              STATUS.get(row.status, row.status), row.error), tags=(row.status,))
        self.summary.configure(text=f"Kayıt aralığı {self.page * self.PAGE_SIZE + 1}–{self.page * self.PAGE_SIZE + len(rows)}")
        self.page_label.configure(text=f"Sayfa {self.page + 1}")

    def turn(self, direction):
        if direction > 0 and len(self.rows) < self.PAGE_SIZE:
            return
        self.page = max(0, self.page + direction)
        self.refresh()

    def detail(self, event=None):
        selected = self.table.selection()
        if not selected:
            return
        row = self.rows[selected[0]]
        messagebox.showinfo("Gönderim ayrıntısı", f"{row.title}\n\n{row.content}\n\n"
                            f"Durum: {STATUS.get(row.status, row.status)}\n{row.error or 'Ek hata bilgisi yok.'}\n\n"
                            f"Kayıt: {row.id}", parent=self)

    def clear(self):
        if not messagebox.askyesno("Geçmişi temizle", "Tüm gönderim kayıtları silinsin mi?\n"
                                   "Mesajlar, ayarlar ve son gönderim bekleme süresi korunur.\nBu işlem geri alınamaz.", parent=self):
            return
        try:
            self.app.controller.stop("Geçmiş temizleniyor. Oturumu yeniden başlatın.")
            self.app.db.clear_history()
            self.page = 0
            self.app.refresh_data()
        except Exception as exc:
            self.app.handle_error("Geçmiş temizlenemedi", exc)
