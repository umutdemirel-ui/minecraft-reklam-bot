"""Explicit consent, input interlocks and a latched emergency stop."""
from __future__ import annotations

import threading

from core.config import Settings
from database.models import Message, validate_message


class SafetyError(RuntimeError):
    pass


class SafetyManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._emergency = threading.Event()
        self.reason = ""

    @property
    def emergency(self) -> bool:
        return self._emergency.is_set()

    def trip(self, reason: str = "F8 acil durdurma") -> None:
        with self._lock:
            if not self.reason:
                self.reason = reason
            self._emergency.set()

    def reset_for_explicit_start(self) -> None:
        """Only called from the user's Start action, never from a timer or focus event."""
        with self._lock:
            self._emergency.clear()
            self.reason = ""

    @staticmethod
    def validate_start(settings: Settings, messages: list[Message], *, windows: bool,
                       hotkey_ready: bool) -> None:
        settings.validate()
        if not windows:
            raise SafetyError("Klavye otomasyonu yalnızca Windows'ta kullanılabilir.")
        if not settings.automation_allowed:
            raise SafetyError("Ayarlar'da sunucunun bu otomasyona açıkça izin verdiğini onaylayın.")
        if not settings.default_chat_confirmed:
            raise SafetyError("Ayarlar'da varsayılan T sohbet kısayolunu ve açık sohbet/menü koşulunu onaylayın.")
        if not hotkey_ready:
            raise SafetyError("F8 güvenlik kısayolu hazır değil. Ayarlar'dan yeniden deneyin.")
        if not messages:
            raise SafetyError("Önce etkin bir mesaj ekleyin.")
        for message in messages:
            if message.active:
                validate_message(message.title, message.content, message.interval_seconds,
                                 settings.max_message_length)
