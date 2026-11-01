"""No real desktop input: guard/cancellation contracts around the Windows adapter."""
import os
from types import SimpleNamespace

import pytest

from core.keyboard_adapter import DesktopKeyboard, KeyboardError


def test_unsupported_platform_cannot_construct_keyboard(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    with pytest.raises(KeyboardError):
        DesktopKeyboard()


@pytest.mark.skipif(os.name != "nt", reason="Windows adapter")
def test_cancelled_guard_blocks_every_primitive():
    keyboard = DesktopKeyboard()
    calls = []
    def guard():
        calls.append(True)
        raise RuntimeError("cancel")
    for action in (lambda: keyboard.press("t", guard), lambda: keyboard.clear(guard),
                   lambda: keyboard.type_text("test", guard)):
        with pytest.raises(RuntimeError, match="cancel"):
            action()
    assert len(calls) == 3


@pytest.mark.skipif(os.name != "nt", reason="Windows adapter")
def test_only_expected_control_keys(monkeypatch):
    keyboard = DesktopKeyboard()
    calls = []
    monkeypatch.setattr(keyboard, "gui", SimpleNamespace(press=calls.append))
    keyboard.press("t", lambda: None)
    assert calls == ["t"]
    with pytest.raises(KeyboardError):
        keyboard.press("delete", lambda: None)
    assert calls == ["t"]
