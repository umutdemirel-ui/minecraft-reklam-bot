from dataclasses import replace

import pytest

from core.config import Settings
from core.minecraft_detector import Window
from database.database import Database


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


@pytest.fixture
def window():
    return Window(42, "Minecraft* 1.21.4 - Multiplayer", 123, "javaw.exe", 900,
                  True, True, False, True)


@pytest.fixture
def message(db):
    db.add_message("Market", "Marketim açıldı! Uygun fiyatlar için beklerim.", True, 180)
    return db.messages()[0]


@pytest.fixture
def settings():
    return replace(Settings(), automation_allowed=True, default_chat_confirmed=True,
                   start_delay_seconds=3)


class FakeBackend:
    supported = True

    def __init__(self, windows):
        self.windows = {w.hwnd: w for w in windows}
        self.fail = False
        self.inspections = 0

    def enumerate(self):
        if self.fail:
            raise OSError("enumeration failed")
        return list(self.windows.values())

    def inspect(self, hwnd):
        self.inspections += 1
        if self.fail:
            raise OSError("inspection failed")
        return self.windows.get(hwnd)


class FakeKeyboard:
    def __init__(self):
        self.calls = []
        self.fail_on = None
        self.enter_effect_then_fail = False
        self.on_type = None

    def _key(self, key, guard):
        guard()
        self.calls.append(key)
        if self.fail_on == key:
            if key == "enter" and self.enter_effect_then_fail:
                raise RuntimeError("Ambiguous Enter result")
            raise RuntimeError(f"Input failed: {key}")

    def press(self, key, guard):
        self._key(key, guard)

    def clear(self, guard):
        self._key("clear", guard)

    def type_text(self, text, guard):
        for char in text:
            guard()
            self.calls.append(char)
            if self.on_type:
                self.on_type(char)
            if self.fail_on == "type":
                raise RuntimeError("Input failed: type")
