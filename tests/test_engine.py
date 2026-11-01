import threading
from dataclasses import replace

from core.message_engine import MessageEngine
from core.minecraft_detector import MinecraftDetector
from tests.conftest import FakeBackend, FakeKeyboard


def make_engine(db, window, keyboard=None):
    backend = FakeBackend([window])
    keyboard = keyboard or FakeKeyboard()
    engine = MessageEngine(db, MinecraftDetector(backend), keyboard)
    engine.CHAT_OPEN_DELAY = 0
    engine.SETTLE_DELAY = 0
    return engine, backend, keyboard


def test_unicode_send_order_and_journal(db, window, message):
    message = replace(message, content="ĞÜŞİÖÇ market açıldı!")
    engine, backend, keyboard = make_engine(db, window)
    result = engine.send(message, window, threading.Event(), 180)
    assert result.status == "sent"
    assert keyboard.calls == ["t", "clear", *message.content, "enter"]
    assert keyboard.calls.count("enter") == 1
    assert db.history()[0].status == "sent"
    assert db.history()[0].content == message.content
    assert backend.inspections > len(message.content)


def test_inactive_target_never_receives_input(db, window, message):
    engine, backend, keyboard = make_engine(db, window)
    backend.windows[42] = replace(window, active=False)
    result = engine.send(message, window, threading.Event(), 180)
    assert result.status == "aborted"
    assert keyboard.calls == []
    assert db.history() == []


def test_focus_loss_during_typing_never_presses_enter(db, window, message):
    engine, backend, keyboard = make_engine(db, window)
    keyboard.on_type = lambda char: backend.windows.update({42: replace(window, active=False)})
    result = engine.send(message, window, threading.Event(), 180)
    assert result.status == "aborted"
    assert "enter" not in keyboard.calls
    assert db.history()[0].status == "aborted"


def test_f8_cancellation_before_input(db, window, message):
    engine, backend, keyboard = make_engine(db, window)
    cancel = threading.Event()
    cancel.set()
    result = engine.send(message, window, cancel, 180)
    assert result.status == "aborted"
    assert keyboard.calls == []


def test_chat_key_error_stops_without_retry(db, window, message):
    keyboard = FakeKeyboard()
    keyboard.fail_on = "t"
    engine, backend, _ = make_engine(db, window, keyboard)
    result = engine.send(message, window, threading.Event(), 180)
    assert result.status == "failed"
    assert keyboard.calls == ["t"]
    assert db.history()[0].status == "failed"


def test_journal_failure_prevents_all_keyboard_input(db, window, message, monkeypatch):
    engine, backend, keyboard = make_engine(db, window)
    def fail(*args):
        raise OSError("disk unavailable")
    monkeypatch.setattr(db, "begin_attempt", fail)
    assert engine.send(message, window, threading.Event(), 180).status == "failed"
    assert keyboard.calls == []


def test_ambiguous_enter_is_unknown_and_not_retried(db, window, message):
    keyboard = FakeKeyboard()
    keyboard.fail_on = "enter"
    keyboard.enter_effect_then_fail = True
    engine, backend, _ = make_engine(db, window, keyboard)
    result = engine.send(message, window, threading.Event(), 180)
    assert result.status == "unknown"
    assert keyboard.calls.count("enter") == 1
    assert db.history()[0].status == "unknown"
    assert db.stats()["sent"] == 0


def test_database_failure_after_enter_does_not_repeat(db, window, message, monkeypatch):
    engine, backend, keyboard = make_engine(db, window)
    monkeypatch.setattr(db, "finish_attempt", lambda *args: (_ for _ in ()).throw(OSError("disk")))
    result = engine.send(message, window, threading.Event(), 180)
    assert result.status == "unknown"
    assert keyboard.calls.count("enter") == 1
    assert db.history()[0].status == "sending"
    db.recover_interrupted()
    assert db.history()[0].status == "unknown"
