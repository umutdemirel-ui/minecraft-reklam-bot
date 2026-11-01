from __future__ import annotations

import customtkinter as ctk

from ui.theme import (AMBER, BORDER, CARD_ALT, GREEN, MONO, MUTED, RED, TEXT,
                      Card, button, clock, font, label)

STATE_LABELS = {
    "ACTIVE": ("Minecraft aktif", GREEN),
    "INACTIVE": ("Minecraft aktif pencere değil", AMBER),
    "NOT_FOUND": ("Minecraft bulunamadı", MUTED),
    "LOST": ("Hedef pencere kaybedildi", RED),
    "AMBIGUOUS": ("Hedef pencere seçimi gerekli", AMBER),
    "MINIMIZED": ("Minecraft görünür değil", AMBER),
    "UNRESPONSIVE": ("Minecraft yanıt vermiyor", RED),
    "UNSUPPORTED": ("Windows otomasyonu kullanılamıyor", AMBER),
    "ERROR": ("Pencere doğrulanamadı", RED),
    "WAITING": ("Pencere denetimi başlatılıyor", MUTED),
}


class Dashboard(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        # Small displays scroll instead of clipping Start/Pause/Stop below the viewport.
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._last_window_labels = None
        self._syncing = False

        connection = Card(self)
        connection.grid(row=0, column=0, sticky="ew", padx=24, pady=(4, 12))
        connection.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(connection, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=20, pady=12)
        label(left, "CANLI BAĞLANTI", 10, MUTED, "bold").pack(anchor="w")
        self.connection_label = label(left, "Minecraft aranıyor…", 23, TEXT, "bold")
        self.connection_label.pack(anchor="w", pady=(7, 3))
        self.window_label = label(left, "Java işlemi ve pencere odağı doğrulanıyor.", 12, wraplength=360)
        self.window_label.pack(anchor="w")
        right = ctk.CTkFrame(connection, fg_color="transparent")
        right.grid(row=0, column=1, padx=20, pady=18, sticky="e")
        label(right, "SONRAKİ MESAJ", 10, MUTED, "bold").pack(anchor="e")
        self.countdown = label(right, "—", 36, RED, "bold", family=MONO)
        self.countdown.pack(anchor="e")
        self.phase_label = label(right, "Otomasyon beklemede", 11)
        self.phase_label.pack(anchor="e")
        select_row = ctk.CTkFrame(connection, fg_color="transparent")
        select_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 12))
        select_row.grid_columnconfigure(1, weight=1)
        label(select_row, "Hedef", 12).grid(row=0, column=0, padx=(0, 12))
        self.window_menu = ctk.CTkOptionMenu(select_row, values=["Otomatik tespit"],
                                            command=self._select_window, fg_color=CARD_ALT,
                                            button_color=BORDER, button_hover_color=RED,
                                            text_color=TEXT, font=font(12), height=32,
                                            dynamic_resizing=False, width=330)
        self.window_menu.grid(row=0, column=1, sticky="ew")
        button(select_row, "Yenile", app.refresh_windows, width=76).grid(row=0, column=2, padx=(10, 0))

        metrics = ctk.CTkFrame(self, fg_color="transparent")
        metrics.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        self.metrics = {}
        for index, (key, caption, value) in enumerate([
            ("messages", "KAYITLI MESAJ", "0"), ("sent", "BU OTURUMDA GÖNDERİLEN", "0"),
            ("total", "TOPLAM GÖNDERİM", "0"), ("elapsed", "AKTİF ÇALIŞMA", "00:00"),
        ]):
            metrics.grid_columnconfigure(index, weight=1, uniform="metrics")
            card = Card(metrics)
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0 if index == 3 else 6))
            label(card, caption, 9, MUTED, "bold").pack(anchor="w", padx=16, pady=(10, 3))
            metric = label(card, value, 27, TEXT, "bold", family=MONO)
            metric.pack(anchor="w", padx=16, pady=(0, 9))
            self.metrics[key] = metric

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 16))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)
        queue = Card(body)
        queue.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        label(queue, "SIRADAKİ MESAJ", 10, MUTED, "bold").pack(anchor="w", padx=20, pady=(20, 10))
        self.next_title = label(queue, "Henüz mesaj yok", 19, TEXT, "bold", wraplength=310)
        self.next_title.pack(anchor="w", padx=20)
        self.next_content = label(queue, "Mesaj yönetimi ekranından ilk mesajınızı ekleyin.",
                                  14, TEXT, wraplength=310)
        self.next_content.pack(anchor="w", fill="x", padx=20, pady=(10, 12))
        self.next_interval = label(queue, "", 12)
        self.next_interval.pack(anchor="w", padx=20)
        self.last_label = label(queue, "Son gönderim: —", 11, wraplength=310)
        self.last_label.pack(anchor="w", padx=20, pady=(18, 20), side="bottom")

        controls = Card(body)
        controls.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        label(controls, "OTOMASYON KONTROLÜ", 10, MUTED, "bold").pack(anchor="w", padx=18, pady=(12, 6))
        self.status_label = label(controls, "Durduruldu", 18, TEXT, "bold")
        self.status_label.pack(anchor="w", padx=18)
        self.reason_label = label(controls, "Başlatmak için hazır", 12, wraplength=215)
        self.reason_label.pack(anchor="w", fill="x", padx=18, pady=(3, 8))
        self.start_button = button(controls, "Başlat", app.start, primary=True)
        self.start_button.pack(fill="x", padx=18, pady=(0, 6))
        row = ctk.CTkFrame(controls, fg_color="transparent")
        row.pack(fill="x", padx=18)
        row.grid_columnconfigure((0, 1), weight=1)
        self.pause_button = button(row, "Duraklat", app.pause, width=100)
        self.pause_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.stop_button = button(row, "Durdur", app.stop, danger=True, width=100)
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        label(controls, "F8  ·  Her zaman acil durdurur", 11, RED, "bold").pack(anchor="w", padx=18, pady=(10, 12))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 18))
        bottom.grid_columnconfigure(0, weight=1)
        self.safety_note = label(bottom, "", 12, AMBER, wraplength=800)
        self.safety_note.grid(row=0, column=0, sticky="w")
        button(bottom, "Güvenlik ayarları", lambda: app.navigate("settings"), width=150).grid(row=0, column=1)

    def _select_window(self, choice):
        if self._syncing:
            return
        hwnd = self._window_map.get(choice)
        self.app.select_window(hwnd)

    def update_view(self, state, detection, stats):
        title, color = STATE_LABELS.get(detection.state, ("Pencere durumu bilinmiyor", AMBER))
        if state["mode"] == "paused":
            title = "Otomasyon duraklatıldı"
            color = AMBER
        self.connection_label.configure(text=title, text_color=color)
        self.window_label.configure(text=(detection.window.title + "  ·  " if detection.window else "") + detection.detail)
        self.countdown.configure(text=clock(state["remaining"]) if state["mode"] in ("running", "paused") else "—")
        self.phase_label.configure(text={"countdown": "Gönderime kalan süre", "sending": "Gönderiliyor",
                                        "paused": "Sayaç duraklatıldı"}.get(state["phase"], "Otomasyon beklemede"))
        for key, value in (("messages", stats["messages"]), ("sent", state["sent"]),
                           ("total", stats["sent"]), ("elapsed", clock(state["elapsed"]))):
            self.metrics[key].configure(text=str(value))
        self.next_title.configure(text=state["next_title"])
        self.next_content.configure(text=state["next_content"][:180] + ("…" if len(state["next_content"]) > 180 else ""))
        self.next_interval.configure(text=f"Sonraki gönderim aralığı: {state['next_interval']} sn" if state["next_interval"] else "")
        self.status_label.configure(text={"running": "Çalışıyor", "paused": "Duraklatıldı", "stopped": "Durduruldu"}[state["mode"]])
        self.reason_label.configure(text=state["reason"])
        self.start_button.configure(text="Sürdür" if state["mode"] == "paused" else "Başlat",
                                    state="normal" if state["mode"] != "running" else "disabled")
        self.pause_button.configure(state="normal" if state["mode"] == "running" else "disabled")
        self.stop_button.configure(state="disabled" if state["mode"] == "stopped" else "normal")
        self.window_menu.configure(state="disabled" if state["mode"] == "running" else "normal")
        self._syncing = True
        candidates = detection.candidates or ((detection.window,) if detection.window else ())
        self._window_map = {"Otomatik tespit": None}
        for window in candidates:
            self._window_map[f"{window.title} · PID {window.pid}"] = window.hwnd
        values = list(self._window_map)
        if values != self._last_window_labels:
            self.window_menu.configure(values=values)
            self._last_window_labels = values
        selected = next((text for text, hwnd in self._window_map.items() if hwnd == state["target_hwnd"]), values[0])
        if self.window_menu.get() != selected:
            self.window_menu.set(selected)
        self._syncing = False
        missing = []
        if not self.app.settings.automation_allowed:
            missing.append("Sunucu izni onayı bekleniyor")
        if not self.app.settings.default_chat_confirmed:
            missing.append("Varsayılan T sohbet düzeni onayı bekleniyor")
        if not self.app.hotkeys.ready:
            missing.append("F8 kısayolu hazır değil")
        self.safety_note.configure(text="  ·  ".join(missing) if missing else
                                   "Koruma etkin: yalnızca doğrulanmış, aktif Java penceresine gönderim.")

    def update_last(self, attempt):
        self.last_label.configure(text=f"Son gönderim: {attempt.content[:100]}" if attempt else "Son gönderim: —")
