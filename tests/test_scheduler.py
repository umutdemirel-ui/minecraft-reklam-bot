from dataclasses import replace

import pytest

from core.config import Settings
from core.safety_manager import SafetyError
from core.scheduler import Rotation, effective_interval


def test_strictest_interval_wins_then_gap_added(message):
    settings = replace(Settings(), interval_seconds=120, server_min_interval_seconds=180,
                       message_gap_seconds=5)
    assert effective_interval(settings, message) == 185
    assert effective_interval(settings, replace(message, interval_seconds=300)) == 305
    assert effective_interval(replace(settings, interval_seconds=300), message) == 305


def test_sequential_rotation_loops_in_order(message):
    second = replace(message, id=2, content="İkinci mesaj")
    inactive = replace(message, id=3, active=False)
    rotation = Rotation()
    rotation.start([message, second, inactive], now=100, delay=10, loop=True)
    assert rotation.current == message
    assert rotation.due_at == 110
    rotation.advance(110, 180)
    assert rotation.current == second
    assert rotation.due_at == 290
    rotation.advance(290, 180)
    assert rotation.current == message
    assert not rotation.completed


def test_no_loop_completes_after_last_message(message):
    rotation = Rotation()
    rotation.start([message, replace(message, id=2)], 0, 3, False)
    rotation.advance(3, 180)
    rotation.advance(183, 180)
    assert rotation.completed


def test_pause_excludes_offline_time_and_resume_has_focus_grace(message):
    rotation = Rotation()
    rotation.start([message], 100, 10, True)
    rotation.pause(104)
    assert rotation.remaining == 6
    rotation.resume(1000)
    assert rotation.due_at == 1006
    rotation.pause(1001)
    rotation.resume(2000)
    assert rotation.due_at == 2005


def test_editing_messages_resets_to_first_without_clearing_cooldown(message):
    rotation = Rotation()
    rotation.start([message, replace(message, id=2)], 0, 10, True)
    rotation.advance(10, 180)
    rotation.reset_list([replace(message, id=3), message])
    assert rotation.current.id == 3
    assert rotation.due_at == 190


def test_empty_rotation_rejected():
    with pytest.raises(SafetyError):
        Rotation().start([], 0, 10, True)
