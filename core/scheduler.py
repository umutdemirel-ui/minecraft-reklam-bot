"""Deterministic monotonic scheduler and a single worker; Tk is never called from this module."""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable

from core.config import Settings
from core.message_engine import MessageEngine
from core.minecraft_detector import MinecraftDetector, Window
from core.safety_manager import SafetyError, SafetyManager
from database.database import Database
from database.models import Message

LOG = logging.getLogger(__name__)


def effective_interval(settings: Settings, message: Message) -> int:
    """The strictest base interval wins; the additional gap is then added."""
    settings.validate()
    return max(settings.interval_seconds, settings.server_min_interval_seconds,
               message.interval_seconds) + settings.message_gap_seconds


@dataclass
class Rotation:
    messages: tuple[Message, ...] = ()
    index: int = 0
    due_at: float = 0
    remaining: float = 0
    completed: bool = False
    loop: bool = True

    def start(self, messages: list[Message], now: float, delay: float, loop: bool) -> None:
        self.messages = tuple(m for m in messages if m.active)
        if not self.messages:
            raise SafetyError("Etkin mesaj bulunamadı.")
        self.index = 0
        self.due_at = now + delay
        self.remaining = delay
        self.completed = False
        self.loop = loop

    @property
    def current(self) -> Message:
        return self.messages[self.index]

    def advance(self, now: float, interval: float) -> None:
        self.index += 1
        if self.index >= len(self.messages):
            self.index = 0
            self.completed = not self.loop
        self.due_at = now + interval
        self.remaining = interval

    def pause(self, now: float) -> None:
        self.remaining = max(0.0, self.due_at - now)

    def resume(self, now: float) -> None:
        # At least 3 seconds to deliberately return to Minecraft; never auto-resume on focus.
        self.remaining = max(3.0, self.remaining)
        self.due_at = now + self.remaining

    def reset_list(self, messages: list[Message]) -> None:
        self.messages = tuple(m for m in messages if m.active)
        self.index = 0
        self.completed = not self.messages


class AutomationController:
    """Thread boundary: UI calls commands; workers publish immutable snapshot dictionaries.

    A generation token and cancellation event prevent an old send from changing a new session.
    There is at most one worker. All automatic focus/window/database/input failures latch PAUSED
    until a new explicit Resume/Start command. No failed or ambiguous send is retried.
    """
    def __init__(self, database: Database, detector: MinecraftDetector,
                 engine_factory: Callable[[], MessageEngine], safety: SafetyManager,
                 hotkey_ready: Callable[[], bool], *, clock=time.monotonic):
        self.db = database
        self.detector = detector
        self.engine_factory = engine_factory
        self.safety = safety
        self.hotkey_ready = hotkey_ready
        self.clock = clock
        self.events: queue.Queue[dict] = queue.Queue()
        self._commands: queue.Queue[tuple] = queue.Queue()
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._closing = False
        self._generation = 0
        self._rotation = Rotation()
        self._settings = Settings()
        self._revision = ""
        self._elapsed_base = 0.0
        self._active_since = 0.0
        self._window: Window | None = None
        self._target_hwnd: int | None = None
        self._sent = 0
        self._mode = "stopped"
        self._phase = "idle"
        self._reason = "Başlatmak için hazır"
        self._worker = threading.Thread(target=self._worker_loop, name="automation", daemon=True)
        self._worker.start()

    def snapshot(self) -> dict:
        with self._lock:
            now = self.clock()
            remaining = max(0.0, self._rotation.due_at - now) if self._mode == "running" else self._rotation.remaining
            elapsed = self._elapsed_base + (now - self._active_since if self._mode == "running" else 0)
            current = self._rotation.messages[self._rotation.index] if self._rotation.messages else None
            return {"mode": self._mode, "phase": self._phase, "reason": self._reason,
                    "remaining": remaining, "elapsed": elapsed, "sent": self._sent,
                    "next_title": current.title if current else "—",
                    "next_content": current.content if current else "Mesaj yönetimi ekranından mesaj ekleyin.",
                    "next_interval": effective_interval(self._settings, current) if current else 0,
                    "window": self._window, "target_hwnd": self._target_hwnd}

    def _publish(self, kind: str = "state", **extra) -> None:
        self.events.put({"kind": kind, "state": self.snapshot(), **extra})

    def configure(self, settings: Settings, detector: MinecraftDetector) -> None:
        self.pause("Ayarlar değişti. Kontrol edip sürdürün.")
        with self._lock:
            self._settings = settings
            self.detector = detector
            self._revision = ""  # force a fresh snapshot and rotation reset on resume
        self._publish()

    def messages_changed(self) -> None:
        with self._lock:
            was_sending = self._mode == "running" and self._phase == "sending"
            self.pause("Mesaj listesi değişti. Sıra başa alındı; sürdürmek için Başlat'a basın.")
            self._revision = ""
            # Do not mutate an in-flight worker's rotation. Resume loads the committed list.
            if not was_sending:
                self._rotation.reset_list(self.db.messages(active_only=True))
                self._rotation.remaining = 0
        self._publish()

    def preview_next(self, messages: list[Message]) -> None:
        """Show the first message of the next explicit Start without starting a timer."""
        with self._lock:
            if self._mode == "stopped":
                self._rotation.reset_list(messages)
                self._rotation.due_at = 0
                self._rotation.remaining = 0

    def select_window(self, hwnd: int | None) -> None:
        if self.snapshot()["mode"] == "running":
            raise SafetyError("Hedefi değiştirmeden önce otomasyonu duraklatın.")
        with self._lock:
            self._target_hwnd = hwnd
            self._window = None
        self._publish()

    def start(self, settings: Settings, messages: list[Message]) -> None:
        with self._lock:
            if self._closing or self._mode == "running":
                return
            SafetyManager.validate_start(settings, messages, windows=self.detector.backend.supported,
                                         hotkey_ready=self.hotkey_ready())
            self.safety.reset_for_explicit_start()
            self._settings = settings
            self._revision = self.db.revision()
            self._sent = 0
            self._elapsed_base = 0
            self._begin_locked("running", "countdown", "Başlangıç gecikmesi — Minecraft'ı öne getirin.")
            self._commands.put(("start", self._generation, self._cancel, messages, True))

    def resume(self, settings: Settings, messages: list[Message]) -> None:
        with self._lock:
            if self._mode != "paused" or self._closing:
                raise SafetyError("Sürdürülecek duraklatılmış oturum yok.")
            SafetyManager.validate_start(settings, messages, windows=self.detector.backend.supported,
                                         hotkey_ready=self.hotkey_ready())
            revision = self.db.revision()
            if revision != self._revision:
                self._rotation.reset_list(messages)
                self._revision = revision
            if not self._rotation.messages:
                raise SafetyError("Etkin mesaj bulunamadı.")
            self._rotation.resume(self.clock())
            self._begin_locked("running", "countdown", "Minecraft'ı öne getirin; sayaç devam ediyor.")
            self._commands.put(("start", self._generation, self._cancel, messages, False))

    def _begin_locked(self, mode: str, phase: str, reason: str) -> None:
        self._generation += 1
        self._cancel = threading.Event()
        self._mode, self._phase, self._reason = mode, phase, reason
        self._active_since = self.clock()
        self._publish()

    def pause(self, reason: str = "Kullanıcı duraklattı.") -> None:
        with self._lock:
            if self._mode != "running":
                return
            now = self.clock()
            self._rotation.pause(now)
            self._elapsed_base += now - self._active_since
            self._mode, self._phase, self._reason = "paused", "paused", reason
            self._cancel.set()
            self._publish()

    def stop(self, reason: str = "Kullanıcı durdurdu.") -> None:
        with self._lock:
            if self._mode == "running":
                self._elapsed_base += self.clock() - self._active_since
            self._generation += 1
            self._mode, self._phase, self._reason = "stopped", "idle", reason
            self._rotation.remaining = 0
            self._cancel.set()
            self._publish()

    def emergency_stop(self) -> None:
        self.safety.trip("F8 acil durdurma. Devam etmek için Başlat'ı kullanın.")
        self.stop(self.safety.reason)
        self._publish("emergency")

    def _pause_worker(self, token: int, reason: str) -> None:
        with self._lock:
            if token != self._generation or self._mode != "running":
                return
            now = self.clock()
            self._rotation.pause(now)
            self._elapsed_base += now - self._active_since
            self._mode, self._phase, self._reason = "paused", "paused", reason
            self._cancel.set()
            self._publish()

    def _stop_worker(self, token: int, reason: str) -> None:
        with self._lock:
            if token != self._generation:
                return
            now = self.clock()
            self._elapsed_base += now - self._active_since
            self._mode, self._phase, self._reason = "stopped", "idle", reason
            self._rotation.remaining = 0
            self._cancel.set()
            self._publish()

    def _worker_loop(self) -> None:
        while not self._closing:
            try:
                command = self._commands.get(timeout=0.1)
            except queue.Empty:
                continue
            if command[0] == "shutdown":
                return
            _, token, cancel, messages, fresh = command
            try:
                self._run_session(token, cancel, messages, fresh)
            except Exception as exc:
                LOG.exception("Automation stopped safely")
                self._pause_worker(token, f"Beklenmeyen hata güvenle duraklattı: {type(exc).__name__}")

    def _run_session(self, token: int, cancel: threading.Event, messages: list[Message], fresh: bool) -> None:
        with self._lock:
            if token != self._generation:
                return
            settings = self._settings
            detection = self.detector.scan(self._target_hwnd)
            self._window = detection.window
            if detection.window is None or detection.state in ("UNRESPONSIVE", "MINIMIZED"):
                self._pause_worker(token, detection.detail)
                return
            target = detection.window
            if fresh:
                delay = max(float(settings.start_delay_seconds),
                            self.db.cooldown_remaining(time.time()))
                self._rotation.start(messages, self.clock(), delay, settings.loop)
            focus_grace = True
            engine = self.engine_factory()
            last_publish = 0.0
            last_check = 0.0
        while not cancel.is_set():
            with self._lock:
                if token != self._generation or self._mode != "running":
                    return
                now = self.clock()
                elapsed = self._elapsed_base + now - self._active_since
                if settings.session_limit_seconds and elapsed >= settings.session_limit_seconds:
                    self._stop_worker(token, "Çalışma süresi sınırına ulaşıldı.")
                    return
                if now - last_check >= 0.25:
                    checked = self.detector.validate(target)
                    self._window = checked.window
                    last_check = now
                    if not checked.can_send and not (focus_grace and checked.state == "INACTIVE"):
                        self._pause_worker(token, checked.detail + " Otomatik devam edilmez.")
                        return
                if now < self._rotation.due_at:
                    self._phase = "countdown"
                    if now - last_publish >= 0.2:
                        self._publish()
                        last_publish = now
                    delay = min(0.1, self._rotation.due_at - now)
                else:
                    checked = self.detector.validate(target)
                    self._window = checked.window
                    if not checked.can_send:
                        self._pause_worker(token, checked.detail + " Otomatik devam edilmez.")
                        return
                    message = self._rotation.current
                    interval = effective_interval(settings, message)
                    self._phase = "sending"
                    self._reason = "Doğrulanmış pencereye gönderiliyor."
                    self._publish()
                    delay = 0.0
            if delay:
                cancel.wait(delay)
                continue
            result = engine.send(message, target, cancel, interval)
            # The journal may have committed just before Stop. Refresh persisted history even
            # when this generation is stale, but never mutate the new session's counters/state.
            self._publish("history")
            with self._lock:
                if token != self._generation:
                    return  # a stopped old session must never alter the new session
                self._rotation.advance(self.clock(), interval)
                focus_grace = False
                if result.status == "sent":
                    self._sent += 1
                self._publish("history")
                if result.status != "sent":
                    self._pause_worker(token, result.error or "Gönderim güvenli şekilde duraklatıldı.")
                    return
                if self._rotation.completed:
                    self._stop_worker(token, "Mesaj listesi tamamlandı. Döngü kapalı.")
                    return
                self._phase = "countdown"
                self._reason = "Sonraki mesaj bekleniyor. F8 ile her an durdurabilirsiniz."
                self._publish()

    @property
    def alive(self) -> bool:
        return self._worker.is_alive()

    def shutdown(self) -> None:
        self.stop("Uygulama kapatılıyor.")
        self._closing = True
        self._commands.put(("shutdown",))
        self._worker.join(timeout=2.0)
