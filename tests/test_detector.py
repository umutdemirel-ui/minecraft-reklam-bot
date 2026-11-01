from dataclasses import replace

import pytest

from core.minecraft_detector import MinecraftDetector
from tests.conftest import FakeBackend


@pytest.mark.parametrize("title", ["Minecraft", "Minecraft* 1.21.4", "Minecraft 1.20.1 - Singleplayer",
                                   "Minecraft* 1.21.4 - Multiplayer", "Minecraft 25w31a"])
def test_java_titles(title, window):
    detector = MinecraftDetector(FakeBackend([replace(window, title=title)]))
    assert detector.scan().state == "ACTIVE"


@pytest.mark.parametrize("title", ["Minecraft Launcher", "Minecraft - Google Chrome", "My Minecraft server",
                                   "Minecraft.exe", "Discord"])
def test_lookalike_titles_rejected(title, window):
    detector = MinecraftDetector(FakeBackend([replace(window, title=title)]))
    assert detector.scan().state == "NOT_FOUND"


@pytest.mark.parametrize("process", ["chrome.exe", "Minecraft.Windows.exe", "explorer.exe"])
def test_non_java_process_rejected_even_with_game_title(process, window):
    detector = MinecraftDetector(FakeBackend([replace(window, process=process)]))
    assert detector.scan().state == "NOT_FOUND"


def test_multiple_candidates_require_explicit_selection(window):
    second = replace(window, hwnd=43, pid=124, active=False)
    detector = MinecraftDetector(FakeBackend([window, second]))
    assert detector.scan().state == "AMBIGUOUS"
    assert detector.scan().can_send is False
    assert detector.scan(43).state == "INACTIVE"
    assert detector.scan(42).state == "ACTIVE"


@pytest.mark.parametrize("change,state", [
    ({"active": False}, "INACTIVE"), ({"visible": False}, "MINIMIZED"),
    ({"minimized": True}, "MINIMIZED"), ({"responsive": False}, "UNRESPONSIVE"),
])
def test_unsafe_window_states(change, state, window):
    changed = replace(window, **change)
    detector = MinecraftDetector(FakeBackend([changed]))
    assert detector.scan().state == state
    assert detector.validate(window).state == state


def test_hwnd_reuse_and_process_restart_are_rejected(window):
    backend = FakeBackend([window])
    detector = MinecraftDetector(backend)
    assert detector.validate(window).can_send
    backend.windows[42] = replace(window, created_ticks=901)
    assert detector.validate(window).state == "LOST"
    backend.windows[42] = replace(window, pid=999)
    assert detector.validate(window).state == "LOST"
    backend.windows.clear()
    assert detector.scan(42).state == "LOST"


def test_enumeration_error_fails_closed(window):
    backend = FakeBackend([window])
    detector = MinecraftDetector(backend)
    backend.fail = True
    assert detector.scan().state == "ERROR"
    assert detector.validate(window).state == "ERROR"


def test_custom_exact_title_still_requires_java(window):
    backend = FakeBackend([replace(window, title="Özel Java istemcisi")])
    detector = MinecraftDetector(backend, "Özel Java istemcisi")
    assert detector.scan().can_send
    backend.windows[42] = replace(backend.windows[42], process="notepad.exe")
    assert not detector.scan().can_send


def test_unsupported_platform_never_sends(window):
    backend = FakeBackend([window])
    backend.supported = False
    assert not MinecraftDetector(backend).validate(window).can_send
