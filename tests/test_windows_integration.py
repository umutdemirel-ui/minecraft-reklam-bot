"""Native layout/API tests, run only on Windows CI. Synthetic desktop input is mocked."""
import os

import pytest

from core.minecraft_detector import WindowsBackend

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Native Windows integration")


def test_native_backend_enumerates_without_input():
    backend = WindowsBackend()
    assert backend.supported
    assert isinstance(backend.enumerate(), list)


def test_unicode_input_layout_and_surrogate_pair(monkeypatch):
    from core.keyboard_adapter import DesktopKeyboard
    keyboard = DesktopKeyboard()
    calls = []
    class API:
        def SendInput(self, count, array, size):
            assert size == (40 if __import__('struct').calcsize('P') == 8 else 28)
            calls.extend((array[i].ki.wScan, array[i].ki.dwFlags) for i in range(count))
            return count
    monkeypatch.setattr(keyboard, "user32", API())
    guards = []
    keyboard.type_text("Ğ😀", lambda: guards.append(True))
    assert len(guards) == 2
    assert calls == [(0x011E, 4), (0x011E, 6), (0xD83D, 4), (0xD83D, 6),
                     (0xDE00, 4), (0xDE00, 6)]
