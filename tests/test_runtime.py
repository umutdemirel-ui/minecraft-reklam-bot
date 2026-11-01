import time

from core.minecraft_detector import MinecraftDetector
from core.single_instance import InstanceLock
from core.window_monitor import WindowMonitor
from tests.conftest import FakeBackend


def test_instance_lock_excludes_second_owner(tmp_path):
    first, second = InstanceLock(tmp_path / "lock"), InstanceLock(tmp_path / "lock")
    assert first.acquire()
    assert not second.acquire()
    first.release()
    assert second.acquire()
    second.release()


def test_monitor_refresh_and_shutdown(window):
    backend = FakeBackend([window])
    monitor = WindowMonitor(MinecraftDetector(backend), interval=10)
    monitor.start()
    end = time.monotonic() + 2
    while monitor.latest.state != "ACTIVE" and time.monotonic() < end:
        time.sleep(0.005)
    assert monitor.latest.state == "ACTIVE"
    backend.windows.clear()
    monitor.refresh()
    end = time.monotonic() + 2
    while monitor.latest.state != "NOT_FOUND" and time.monotonic() < end:
        time.sleep(0.005)
    assert monitor.latest.state == "NOT_FOUND"
    monitor.shutdown()
    assert not monitor._thread.is_alive()
