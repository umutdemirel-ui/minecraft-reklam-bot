"""Real worker-thread tests with injected clock/backend/engine; never real keyboard input."""
import threading
import time
from dataclasses import replace

import pytest

from core.message_engine import SendResult
from core.minecraft_detector import MinecraftDetector
from core.safety_manager import SafetyError, SafetyManager
from core.scheduler import AutomationController
from tests.conftest import FakeBackend


class Clock:
    def __init__(self):
        self.value = 100.0
    def __call__(self):
        return self.value


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.result = "sent"
        self.entered = threading.Event()
        self.release = None
    def send(self, message, target, cancel, cooldown):
        self.calls.append((message.id, cooldown))
        self.entered.set()
        if self.release:
            self.release.wait(2)
        return SendResult(self.result, str(len(self.calls)), "Test failure" if self.result != "sent" else "")


def wait_for(predicate, timeout=3):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("Worker did not reach expected state")


@pytest.fixture
def runtime(db, window, message):
    db.add_message("İkinci", "İkinci mesaj", True, 120)
    backend, clock, engine, safety = FakeBackend([window]), Clock(), FakeEngine(), SafetyManager()
    controller = AutomationController(db, MinecraftDetector(backend), lambda: engine, safety,
                                      lambda: True, clock=clock)
    yield controller, backend, clock, engine, safety
    controller.shutdown()
    assert not controller.alive


def test_preview_does_not_start_automation(runtime, db):
    controller, backend, clock, engine, safety = runtime
    controller.preview_next(db.messages(active_only=True))
    assert controller.snapshot()["next_title"] == "Market"
    assert controller.snapshot()["mode"] == "stopped"
    clock.value += 1000
    assert engine.calls == []


def test_start_rotation_and_focus_loss_pause(runtime, settings, db, window):
    controller, backend, clock, engine, safety = runtime
    controller.start(settings, db.messages(active_only=True))
    wait_for(lambda: controller._rotation.due_at > 0)
    assert engine.calls == []
    clock.value += 4
    wait_for(lambda: len(engine.calls) == 1)
    assert engine.calls[0] == (1, 180)
    wait_for(lambda: controller.snapshot()["reason"].startswith("Sonraki mesaj"))
    clock.value += 0.3
    backend.windows[42] = replace(window, active=False)
    wait_for(lambda: controller.snapshot()["mode"] == "paused")
    clock.value += 1000
    assert len(engine.calls) == 1  # no focus-based automatic resume
    backend.windows[42] = window
    remaining = controller.snapshot()["remaining"]
    controller.resume(settings, db.messages(active_only=True))
    clock.value += remaining + 1
    wait_for(lambda: len(engine.calls) == 2)
    assert engine.calls[1][0] == 2


def test_f8_stops_and_old_result_cannot_change_new_session(runtime, settings, db):
    controller, backend, clock, engine, safety = runtime
    engine.release = threading.Event()
    controller.start(settings, db.messages(active_only=True))
    wait_for(lambda: controller._rotation.due_at > 0)
    clock.value += 4
    assert engine.entered.wait(2)
    previous_due = controller._rotation.due_at
    controller.emergency_stop()
    assert safety.emergency
    assert controller.snapshot()["mode"] == "stopped"
    engine.release.set()
    engine.release = None
    controller.start(settings, db.messages(active_only=True))
    assert not safety.emergency
    assert controller.snapshot()["sent"] == 0
    wait_for(lambda: controller._rotation.due_at != previous_due)
    clock.value += 4
    wait_for(lambda: len(engine.calls) == 2)
    assert controller.snapshot()["sent"] == 1


def test_failure_is_not_retried_and_resume_advances(runtime, settings, db):
    controller, backend, clock, engine, safety = runtime
    engine.result = "unknown"
    controller.start(settings, db.messages(active_only=True))
    wait_for(lambda: controller._rotation.due_at > 0)
    clock.value += 4
    wait_for(lambda: controller.snapshot()["mode"] == "paused")
    assert len(engine.calls) == 1
    engine.result = "sent"
    controller.resume(settings, db.messages(active_only=True))
    clock.value += 181
    wait_for(lambda: len(engine.calls) == 2)
    assert engine.calls[1][0] == 2


def test_message_change_resets_queue_on_resume(runtime, settings, db):
    controller, backend, clock, engine, safety = runtime
    controller.start(settings, db.messages(active_only=True))
    wait_for(lambda: controller._rotation.due_at > 0)
    clock.value += 4
    wait_for(lambda: len(engine.calls) == 1)
    db.add_message("Yeni ilk", "Yeni içerik", True, 300)
    # Put the new message first by rebuilding the active domain list in test order.
    messages = list(reversed(db.messages(active_only=True)))
    controller.messages_changed()
    assert controller.snapshot()["mode"] == "paused"
    controller.resume(settings, messages)
    clock.value += 4
    wait_for(lambda: len(engine.calls) == 2)
    assert engine.calls[1] == (messages[0].id, 300)


def test_runtime_limit_and_no_loop(runtime, settings, db):
    controller, backend, clock, engine, safety = runtime
    settings = replace(settings, loop=False, session_limit_seconds=60)
    controller.start(settings, db.messages(active_only=True))
    wait_for(lambda: controller._rotation.due_at > 0)
    clock.value += 4
    wait_for(lambda: len(engine.calls) == 1)
    clock.value += 60
    wait_for(lambda: controller.snapshot()["mode"] == "stopped")
    assert len(engine.calls) == 1
    assert "sınırı" in controller.snapshot()["reason"]


def test_no_hotkey_or_consent_blocks_worker(runtime, settings, db):
    controller, backend, clock, engine, safety = runtime
    controller.hotkey_ready = lambda: False
    with pytest.raises(SafetyError):
        controller.start(settings, db.messages())
    assert engine.calls == []


def test_persisted_cooldown_applies_to_new_session(runtime, settings, db):
    controller, backend, clock, engine, safety = runtime
    db.begin_attempt("previous", "previous", db.messages()[0], 300)
    controller.start(settings, db.messages())
    wait_for(lambda: controller.snapshot()["remaining"] > 290)
    clock.value += 4
    time.sleep(0.15)
    assert engine.calls == []
