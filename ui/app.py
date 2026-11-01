"""Composition root and sole owner of Tk widgets. Workers communicate through queues."""
from __future__ import annotations

import logging
import queue
import tkinter.messagebox as messagebox

import customtkinter as ctk

from core.config import AppPaths, Settings
from core.hotkeys import HotkeyManager
from core.keyboard_adapter import DesktopKeyboard
from core.message_engine import MessageEngine
from core.minecraft_detector import detector_for_title
from core.safety_manager import SafetyManager
from core.scheduler import AutomationController
from core.window_monitor import WindowMonitor
from database.database import Database
from ui.dashboard import Dashboard
from ui.history import History
from ui.messages import Messages
from ui.scheduler_view import SchedulerView
from ui.settings import SettingsView
from ui.theme import BG, CARD_ALT, GREEN, MUTED, RED, RED_TINT, SIDEBAR, TEXT, apply_theme, font, label

LOG = logging.getLogger(__name__)
PAGES = {
    "dashboard": ("Dashboard", "Kontrol sizde. Gönderim yalnızca doğru pencerede.", "01"),
    "messages": ("Mesaj yönetimi", "Bir kez yazın. İzinli sunucularda, belirlediğiniz sırayla gönderin.", "02"),
    "scheduler": ("Zamanlayıcı", "Sunucu kurallarına saygılı, öngörülebilir bir gönderim ritmi.", "03"),
    "history": ("Gönderim geçmişi", "Her girişimin zamanı, sonucu ve hata ayrıntısı.", "04"),
    "settings": ("Ayarlar", "Pencere, güvenlik, tema ve verileriniz.", "05"),
}


class App(ctk.CTk):
    def __init__(self, paths: AppPaths, db: Database, settings: Settings, *, smoke_test=False):
        apply_theme(settings.theme)
        super().__init__(fg_color=BG)
        self.paths, self.db, self.settings = paths, db, settings
        self.smoke_test = smoke_test
        self.ui_events = queue.Queue()
        self._closed = False
        self._data_tick = 0
        self._stats = {"messages": 0, "active": 0, "sent": 0, "unknown": 0}
        self.title("Minecraft Auto Advertiser")
        width, height = min(1240, self.winfo_screenwidth() - 60), min(820, self.winfo_screenheight() - 70)
        self.geometry(f"{max(980, width)}x{max(660, height)}")
        self.minsize(980, 660)
        if paths.resources.joinpath("assets", "icon.ico").exists():
            try:
                self.iconbitmap(str(paths.resources / "assets" / "icon.ico"))
            except Exception:
                pass
        self.safety = SafetyManager()
        self.hotkeys = HotkeyManager(self._emergency)
        if not smoke_test:
            self.hotkeys.register()
        self.detector = detector_for_title(settings.window_title)
        self.controller = AutomationController(db, self.detector, self._engine_factory, self.safety,
                                               lambda: self.hotkeys.ready)
        self.controller.configure(settings, self.detector)
        self.monitor = WindowMonitor(self.detector)
        self.monitor.start()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.report_callback_exception = self._tk_error
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 18))
        header.grid_columnconfigure(0, weight=1)
        self.page_title = label(header, "Dashboard", 28, TEXT, "bold")
        self.page_title.grid(row=0, column=0, sticky="w")
        self.page_subtitle = label(header, PAGES["dashboard"][1], 12, wraplength=510)
        self.page_subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.local_badge = ctk.CTkLabel(header, text="JAVA EDITION  /  WINDOWS", font=font(9, "bold"),
                                       fg_color=CARD_ALT, text_color=MUTED, corner_radius=6,
                                       width=164, height=28)
        self.local_badge.grid(row=0, column=1, rowspan=2, sticky="e", padx=(14, 0))
        container = ctk.CTkFrame(main, fg_color="transparent")
        container.grid(row=1, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        self.pages = {
            "dashboard": Dashboard(container, self),
            "messages": Messages(container, self),
            "scheduler": SchedulerView(container, self),
            "history": History(container, self),
            "settings": SettingsView(container, self),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.current_page = "dashboard"
        self.navigate("dashboard")
        self.refresh_data()
        self.after(100, self._pump)
        if smoke_test:
            self.after(1200, self.close)

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=218, corner_radius=0, fg_color=SIDEBAR)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=22, pady=(28, 30))
        mark = ctk.CTkLabel(brand, text="A", width=38, height=38, corner_radius=9,
                            fg_color=RED, text_color="white", font=font(26, "bold"))
        mark.pack(side="left", padx=(0, 10))
        text = ctk.CTkFrame(brand, fg_color="transparent")
        text.pack(side="left")
        label(text, "AUTO", 17, TEXT, "bold").pack(anchor="w")
        label(text, "ADVERTISER", 10, MUTED, "bold").pack(anchor="w")
        label(sidebar, "ÇALIŞMA ALANI", 9, MUTED, "bold").pack(anchor="w", padx=24, pady=(0, 10))
        self.nav_buttons = {}
        for key, (title, _, number) in PAGES.items():
            nav = ctk.CTkButton(sidebar, text=f"{number}   {title}", anchor="w", height=44,
                                corner_radius=8, font=font(13), fg_color="transparent",
                                hover_color=CARD_ALT, text_color=MUTED,
                                command=lambda name=key: self.navigate(name))
            nav.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[key] = nav
        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=18, pady=22)
        safety = ctk.CTkFrame(bottom, fg_color=RED_TINT, corner_radius=10)
        safety.pack(fill="x", pady=(0, 18))
        label(safety, "F8", 23, RED, "bold", family="Consolas").pack(anchor="w", padx=16, pady=(12, 0))
        label(safety, "ACİL DURDURMA", 9, RED, "bold").pack(anchor="w", padx=16)
        label(safety, "Her ekrandan.\nOtomasyonu anında durdurur.", 10, wraplength=150).pack(anchor="w", padx=16, pady=(6, 14))
        self.sidebar_status = label(bottom, "Yerel veri  ·  v1.0.0", 10)
        self.sidebar_status.pack(anchor="w", padx=4)
        label(bottom, "MINECRAFT AUTO ADVERTISER", 8, MUTED, "bold").pack(anchor="w", padx=4, pady=(4, 0))

    def _engine_factory(self):
        return MessageEngine(self.db, self.controller.detector, DesktopKeyboard())

    def navigate(self, name):
        self.pages[name].tkraise()
        self.current_page = name
        title, subtitle, _ = PAGES[name]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        for key, nav in self.nav_buttons.items():
            nav.configure(fg_color=RED_TINT if key == name else "transparent",
                          text_color=RED if key == name else MUTED)
        if name == "history":
            self.pages[name].refresh()
        elif name == "settings":
            self.pages[name].update_hotkey()

    def start(self):
        try:
            messages = self.db.messages(active_only=True)
            if self.controller.snapshot()["mode"] == "paused":
                self.controller.resume(self.settings, messages)
            else:
                self.controller.start(self.settings, messages)
        except Exception as exc:
            self.handle_error("Otomasyon başlatılamadı", exc)

    def pause(self):
        self.controller.pause()

    def stop(self):
        self.controller.stop()

    def _emergency(self):
        # No Tk access from the global keyboard hook thread.
        self.controller.emergency_stop()

    def select_window(self, hwnd):
        try:
            self.controller.select_window(hwnd)
            self.monitor.select(hwnd)
        except Exception as exc:
            self.handle_error("Hedef değiştirilemedi", exc)

    def refresh_windows(self):
        self.monitor.refresh()

    def messages_changed(self):
        try:
            self.controller.messages_changed()
            self.refresh_data()
        except Exception as exc:
            self.handle_error("Mesaj listesi yenilenemedi", exc)

    def save_settings(self, settings):
        settings.validate()
        self.controller.stop("Ayarlar değiştirildi. Oturumu yeniden başlatın.")
        # Persist first: a failed write must not leave mismatched active settings.
        self.db.save_settings(settings)
        self.settings = settings
        self.detector = detector_for_title(settings.window_title)
        self.controller.configure(settings, self.detector)
        self.monitor.configure(self.detector)
        apply_theme(settings.theme)
        self.pages["scheduler"].refresh()
        self.pages["settings"].refresh()
        self.refresh_data()

    def refresh_data(self):
        self._stats = self.db.stats()
        self.controller.preview_next(self.db.messages(active_only=True))
        state = self.controller.snapshot()
        self.pages["dashboard"].update_view(state, self.monitor.latest, self._stats)
        self.pages["dashboard"].update_last(self.db.last_sent())
        self.pages["messages"].refresh()
        self.sidebar_status.configure(text="F8 etkin  ·  Yerel veri" if self.hotkeys.ready else "F8 kullanılamıyor  ·  Ayarlar",
                                      text_color=GREEN if self.hotkeys.ready else RED)

    def _pump(self):
        if self._closed:
            return
        try:
            for _ in range(60):
                try:
                    event = self.controller.events.get_nowait()
                except queue.Empty:
                    break
                if event["kind"] == "history":
                    self._stats = self.db.stats()
                    self.pages["history"].refresh()
                    self.pages["dashboard"].update_last(self.db.last_sent())
                elif event["kind"] == "emergency":
                    self.pages["dashboard"].reason_label.configure(text=event["state"]["reason"])
            for _ in range(20):
                try:
                    kind, payload = self.ui_events.get_nowait()
                except queue.Empty:
                    break
                if kind == "backup":
                    self.pages["settings"].backup_result(payload)
                elif kind == "error":
                    self.pages["settings"].backup_result(payload[1], error=True)
            self.pages["dashboard"].update_view(self.controller.snapshot(), self.monitor.latest, self._stats)
            self._data_tick += 1
            if self._data_tick % 30 == 0:
                self.pages["dashboard"].update_last(self.db.last_sent())
                self.pages["settings"].update_hotkey()
        except Exception as exc:
            self._tk_error(type(exc), exc, None)
            return  # A persistent database/UI failure must not create an endless dialog loop.
        if not self._closed:
            self.after(150, self._pump)

    def handle_error(self, title, exc):
        LOG.exception(title, exc_info=(type(exc), exc, exc.__traceback__))
        self.controller.pause(f"{title}. Güvenlik için otomasyon duraklatıldı.")
        messagebox.showerror(title, str(exc), parent=self)

    def _tk_error(self, exc_type, value, traceback):
        LOG.error("UI error", exc_info=(exc_type, value, traceback))
        self.controller.stop("Arayüz hatası nedeniyle durduruldu.")
        messagebox.showerror("Beklenmeyen hata", "İşlem tamamlanamadı. Otomasyon güvenli şekilde durduruldu.\n"
                             f"Ayrıntı: {exc_type.__name__}. Log: {self.paths.logs}", parent=self)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.controller.shutdown()
        self.monitor.shutdown()
        self.hotkeys.unregister()
        self.destroy()
