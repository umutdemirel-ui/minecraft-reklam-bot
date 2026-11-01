"""Conservative Java-window detection. Never activates a window or falls back to another app.

PyGetWindow enumerates windows; Win32 checks live titles, Java process identity, process start
time, responsiveness and foreground state. A HWND alone is not a durable identity.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Protocol

TITLE_PATTERN = re.compile(
    r"^Minecraft\*?(?:\s+(?:\d+\.\d+(?:\.\d+)?[A-Za-z0-9_.+-]*|\d{2}w\d{2}[a-z])"
    r"(?:\s+-\s+.+)?)?$",
    re.IGNORECASE,
)
JAVA_PROCESSES = {"java.exe", "javaw.exe"}


@dataclass(frozen=True)
class Window:
    hwnd: int
    title: str
    pid: int
    process: str
    created_ticks: int
    active: bool
    visible: bool
    minimized: bool
    responsive: bool

    @property
    def identity(self) -> tuple[int, int, int]:
        return self.hwnd, self.pid, self.created_ticks

    @property
    def label(self) -> str:
        return f"{self.title} · PID {self.pid}"


@dataclass(frozen=True)
class Detection:
    state: str
    detail: str
    window: Window | None = None
    candidates: tuple[Window, ...] = ()

    @property
    def can_send(self) -> bool:
        return self.state == "ACTIVE"


class WindowBackend(Protocol):
    supported: bool
    def enumerate(self) -> list[Window]: ...
    def inspect(self, hwnd: int) -> Window | None: ...


class MinecraftDetector:
    def __init__(self, backend: WindowBackend, exact_title: str = ""):
        self.backend = backend
        self.exact_title = exact_title.strip()

    def matches(self, window: Window) -> bool:
        if window.process.lower() not in JAVA_PROCESSES:
            return False
        return (window.title == self.exact_title if self.exact_title
                else bool(TITLE_PATTERN.fullmatch(window.title)))

    def scan(self, selected_hwnd: int | None = None) -> Detection:
        if not self.backend.supported:
            return Detection("UNSUPPORTED", "Otomasyon yalnızca Windows / Minecraft Java destekler.")
        try:
            candidates = tuple(w for w in self.backend.enumerate() if self.matches(w))
            if selected_hwnd is not None:
                window = next((w for w in candidates if w.hwnd == selected_hwnd), None)
                if window is None:
                    return Detection("LOST", "Seçilen Minecraft penceresi kapandı veya başlığı değişti.",
                                     candidates=candidates)
            elif len(candidates) > 1:
                return Detection("AMBIGUOUS", "Birden fazla Java penceresi var. Hedef pencereyi seçin.",
                                 candidates=candidates)
            elif not candidates:
                return Detection("NOT_FOUND", "Minecraft Java penceresi bulunamadı.")
            else:
                window = candidates[0]
            return self._classify(window, candidates)
        except Exception:
            # Do not retain a previously valid target after an enumeration error.
            return Detection("ERROR", "Pencere bilgisi alınamadı. Gönderim güvenli şekilde durduruldu.")

    def validate(self, expected: Window) -> Detection:
        """Fresh OS inspection, used immediately before EVERY input operation."""
        if not self.backend.supported:
            return Detection("UNSUPPORTED", "Bu işletim sisteminde klavye otomasyonu kapalı.")
        try:
            window = self.backend.inspect(expected.hwnd)
            if window is None or window.identity != expected.identity or not self.matches(window):
                return Detection("LOST", "Hedef pencere veya Java işlemi değişti.")
            return self._classify(window)
        except Exception:
            return Detection("ERROR", "Pencere doğrulanamadı; aktif odak varsayılmadı.")

    @staticmethod
    def _classify(window: Window, candidates: tuple[Window, ...] = ()) -> Detection:
        if not window.visible or window.minimized:
            return Detection("MINIMIZED", "Minecraft simge durumunda veya görünür değil.", window, candidates)
        if not window.responsive:
            return Detection("UNRESPONSIVE", "Minecraft yanıt vermiyor.", window, candidates)
        if not window.active:
            return Detection("INACTIVE", "Minecraft bulundu, ancak aktif pencere değil.", window, candidates)
        return Detection("ACTIVE", "Minecraft doğrulandı ve aktif pencere.", window, candidates)


class WindowsBackend:
    """All pointer/handle sizes are configured for both 32-bit and 64-bit Windows."""
    supported = os.name == "nt"

    def __init__(self):
        if not self.supported:
            return
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        u, k = self.user32, self.kernel32
        hwnd, handle = wintypes.HWND, wintypes.HANDLE
        dword = wintypes.DWORD
        u.GetForegroundWindow.restype = hwnd
        u.GetWindowTextLengthW.argtypes = [hwnd]
        u.GetWindowTextW.argtypes = [hwnd, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowThreadProcessId.argtypes = [hwnd, ctypes.POINTER(dword)]
        u.GetWindowThreadProcessId.restype = dword
        for name in ("IsWindow", "IsWindowVisible", "IsIconic", "IsHungAppWindow"):
            getattr(u, name).argtypes = [hwnd]
            getattr(u, name).restype = wintypes.BOOL
        k.OpenProcess.argtypes = [dword, wintypes.BOOL, dword]
        k.OpenProcess.restype = handle
        k.CloseHandle.argtypes = [handle]
        k.QueryFullProcessImageNameW.argtypes = [handle, dword, wintypes.LPWSTR, ctypes.POINTER(dword)]
        k.QueryFullProcessImageNameW.restype = wintypes.BOOL
        k.GetProcessTimes.argtypes = [handle] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        k.GetProcessTimes.restype = wintypes.BOOL

    def enumerate(self) -> list[Window]:
        import pygetwindow as gw
        result = []
        for window in gw.getAllWindows():
            hwnd = int(window._hWnd)
            # Cheap title prefilter; inspect always reads the LIVE title below.
            if self.exact_prefix_match(window.title):
                inspected = self.inspect(hwnd)
                if inspected is not None:
                    result.append(inspected)
        return result

    @staticmethod
    def exact_prefix_match(title: str) -> bool:
        return title.lower().startswith("minecraft")

    def inspect(self, hwnd: int) -> Window | None:
        ctypes, wt = self.ctypes, self.wintypes
        u, k = self.user32, self.kernel32
        if not u.IsWindow(hwnd):
            return None
        length = u.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        u.GetWindowTextW(hwnd, buffer, len(buffer))
        pid = wt.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_handle = k.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
        if not process_handle:
            return None
        try:
            buffer_path = ctypes.create_unicode_buffer(32768)
            size = wt.DWORD(len(buffer_path))
            if not k.QueryFullProcessImageNameW(process_handle, 0, buffer_path, ctypes.byref(size)):
                return None
            creation, exit_time, kernel_time, user_time = (wt.FILETIME() for _ in range(4))
            if not k.GetProcessTimes(process_handle, *(ctypes.byref(t) for t in
                                                      (creation, exit_time, kernel_time, user_time))):
                return None
            ticks = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
            process = buffer_path.value.replace("\\", "/").rsplit("/", 1)[-1]
        finally:
            k.CloseHandle(process_handle)
        return Window(hwnd, buffer.value, pid.value, process, ticks,
                      bool(u.GetForegroundWindow() == hwnd), bool(u.IsWindowVisible(hwnd)),
                      bool(u.IsIconic(hwnd)), not bool(u.IsHungAppWindow(hwnd)))


def detector_for_title(title: str) -> MinecraftDetector:
    backend = WindowsBackend()
    if backend.supported and title.strip():
        # Enumerate all top-level windows for a user-chosen title, still requiring a Java process.
        backend.exact_prefix_match = lambda _title: True
    return MinecraftDetector(backend, title)
