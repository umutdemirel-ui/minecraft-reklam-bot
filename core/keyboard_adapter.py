"""PyAutoGUI keys + native Unicode SendInput; no clipboard replacement or focus stealing.

SendInput cannot be atomically bound to a HWND. The caller revalidates the exact foreground
process/window immediately before each primitive. This reduces, but cannot eliminate, the OS
focus-change race. Never claim otherwise or attempt to bypass game/server protections.
"""
from __future__ import annotations

import os
from typing import Callable, Protocol

Guard = Callable[[], None]


class KeyboardError(RuntimeError):
    pass


class KeyboardAdapter(Protocol):
    def press(self, key: str, guard: Guard) -> None: ...
    def clear(self, guard: Guard) -> None: ...
    def type_text(self, text: str, guard: Guard) -> None: ...


class DesktopKeyboard:
    def __init__(self):
        if os.name != "nt":
            raise KeyboardError("Klavye gönderimi bu işletim sisteminde kapalı.")
        import ctypes
        from ctypes import wintypes
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.04
        self.gui = pyautogui
        self.ctypes = ctypes
        ULONG_PTR = wintypes.WPARAM

        class MouseInput(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

        class KeyInput(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ULONG_PTR)]

        class HardwareInput(ctypes.Structure):
            _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                        ("wParamH", wintypes.WORD)]

        class InputUnion(ctypes.Union):
            _fields_ = [("mi", MouseInput), ("ki", KeyInput), ("hi", HardwareInput)]

        class Input(ctypes.Structure):
            _anonymous_ = ("data",)
            _fields_ = [("type", wintypes.DWORD), ("data", InputUnion)]

        self.Input = Input
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        self.user32.SendInput.restype = wintypes.UINT

    def press(self, key: str, guard: Guard) -> None:
        guard()
        if key not in ("t", "enter", "backspace"):
            raise KeyboardError("Desteklenmeyen tuş.")
        try:
            self.gui.press(key)
        except Exception as exc:
            raise KeyboardError(f"Tuş gönderilemedi ({key}): {type(exc).__name__}") from exc

    def clear(self, guard: Guard) -> None:
        guard()
        try:
            self.gui.hotkey("ctrl", "a")
        except Exception as exc:
            raise KeyboardError("Sohbet taslağı seçilemedi.") from exc
        self.press("backspace", guard)

    def type_text(self, text: str, guard: Guard) -> None:
        for character in text:
            guard()
            raw = character.encode("utf-16-le")
            # Constructing through the union avoids platform-specific padding assumptions.
            # Supplementary characters are sent as both UTF-16 surrogate units.
            events = []
            for index in range(0, len(raw), 2):
                scan = int.from_bytes(raw[index:index + 2], "little")
                for flags in (0x0004, 0x0006):
                    event = self.Input()
                    event.type = 1
                    event.ki.wVk = 0
                    event.ki.wScan = scan
                    event.ki.dwFlags = flags
                    events.append(event)
            array = (self.Input * len(events))(*events)
            sent = self.user32.SendInput(len(events), array, self.ctypes.sizeof(self.Input))
            if sent != len(events):
                raise KeyboardError("Unicode klavye girdisi eksik kaldı; Enter gönderilmedi.")
