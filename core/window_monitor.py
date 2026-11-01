"""Low-frequency, cancellable background monitor; only the latest detection is retained."""
from __future__ import annotations

import threading

from core.minecraft_detector import Detection, MinecraftDetector


class WindowMonitor:
    def __init__(self, detector: MinecraftDetector, interval: float = 1.0):
        self.interval = interval
        self._detector = detector
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._selected = None
        self._latest = Detection("WAITING", "Pencere denetimi başlatılıyor.")
        self._thread = threading.Thread(target=self._run, name="window-monitor", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def configure(self, detector: MinecraftDetector) -> None:
        with self._lock:
            self._detector = detector
        self.refresh()

    def select(self, hwnd: int | None) -> None:
        with self._lock:
            self._selected = hwnd
        self.refresh()

    def refresh(self) -> None:
        self._wake.set()

    @property
    def latest(self) -> Detection:
        with self._lock:
            return self._latest

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                detector, selected = self._detector, self._selected
            result = detector.scan(selected)
            with self._lock:
                self._latest = result
            self._wake.wait(self.interval)
            self._wake.clear()

    def shutdown(self) -> None:
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=2.0)
