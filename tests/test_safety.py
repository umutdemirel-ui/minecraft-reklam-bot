from dataclasses import replace

import pytest

from core.hotkeys import HotkeyManager
from core.safety_manager import SafetyError, SafetyManager


def test_consent_and_hotkey_are_required(settings, message):
    for change in ({"automation_allowed": False}, {"default_chat_confirmed": False}):
        with pytest.raises(SafetyError):
            SafetyManager.validate_start(replace(settings, **change), [message], windows=True, hotkey_ready=True)
    with pytest.raises(SafetyError):
        SafetyManager.validate_start(settings, [message], windows=True, hotkey_ready=False)
    with pytest.raises(SafetyError):
        SafetyManager.validate_start(settings, [message], windows=False, hotkey_ready=True)


def test_overlong_existing_message_blocks_start(settings, message):
    with pytest.raises(ValueError):
        SafetyManager.validate_start(replace(settings, max_message_length=10), [message],
                                     windows=True, hotkey_ready=True)


def test_emergency_latches_until_explicit_reset():
    safety = SafetyManager()
    safety.trip()
    safety.trip("another reason")
    assert safety.emergency
    assert safety.reason == "F8 acil durdurma"
    safety.reset_for_explicit_start()
    assert not safety.emergency


def test_hotkey_failure_is_visible_and_cleanup_is_idempotent():
    class Module:
        def __init__(self):
            self.removed = []
            self.fail = True
        def add_hotkey(self, *args, **kwargs):
            if self.fail:
                raise OSError("permission")
            assert kwargs["suppress"] is False
            return "handle"
        def remove_hotkey(self, handle):
            self.removed.append(handle)
    module = Module()
    hotkey = HotkeyManager(lambda: None, module)
    assert not hotkey.register()
    assert not hotkey.ready
    assert "F8" in hotkey.error
    module.fail = False
    assert hotkey.register()
    hotkey.unregister()
    hotkey.unregister()
    assert module.removed == ["handle"]
