"""Non-suppressing global F8 hook. Registration failure is visible and blocks Start."""
from __future__ import annotations

import threading
from typing import Callable


class HotkeyManager:
    def __init__(self, callback: Callable[[], None], module=None):
        self.callback = callback
        self.module = module
        self._handle = None
        self._lock = threading.Lock()
        self.error = ""

    @property
    def ready(self) -> bool:
        return self._handle is not None

    def register(self) -> bool:
        with self._lock:
            if self.ready:
                return True
            try:
                if self.module is None:
                    import keyboard
                    self.module = keyboard
                self._handle = self.module.add_hotkey("f8", self.callback, suppress=False,
                                                      trigger_on_release=False)
                self.error = ""
                return True
            except Exception as exc:
                self.error = f"F8 kaydedilemedi: {type(exc).__name__}. Arayüzdeki Durdur kullanılabilir."
                return False

    def unregister(self) -> None:
        with self._lock:
            if self._handle is not None and self.module is not None:
                try:
                    self.module.remove_hotkey(self._handle)
                except (KeyError, ValueError, AttributeError):
                    pass
                self._handle = None
