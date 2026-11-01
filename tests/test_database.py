import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.config import ConfigError, Settings
from database.database import Database
from database.models import Message


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


def test_settings_roundtrip_and_defaults(db):
    assert db.get_settings(Settings()) == Settings()
    changed = Settings(interval_seconds=300, automation_allowed=True)
    db.save_settings(changed)
    assert db.get_settings(Settings()) == changed


def test_message_crud_order_and_validation(db):
    first = db.add_message("Market", "Marketim açıldı!", True, 180)
    second = db.add_message("Etkinlik", "Etkinliğe beklerim.", False, 120)
    assert [m.id for m in db.messages()] == [first, second]
    assert [m.id for m in db.messages(active_only=True)] == [first]
    db.update_message(first, "Yeni başlık", "Yeni ürünler!", True, 300)
    assert db.messages()[0].content == "Yeni ürünler!"
    old_revision = db.revision()
    db.delete_message(second)
    assert len(db.messages()) == 1
    assert db.revision() != old_revision
    for content in ("", "/give test", "bir\niki", "x" * 257):
        with pytest.raises(ConfigError):
            db.add_message("Başlık", content, True, 180)


def test_journal_recovery_is_not_a_retry(db):
    message = Message(db.add_message("Market", "Beklerim!", True, 180), "Market", "Beklerim!", True, 180)
    db.begin_attempt("one", "session", message)
    db.mark_sending("one")
    db.set_cooldown(180)
    assert db.recover_interrupted() == 1
    assert db.history()[0].status == "unknown"
    assert db.recover_interrupted() == 0
    assert db.stats()["sent"] == 0
    assert db.cooldown_remaining(__import__('time').time()) > 170


def test_history_snapshot_survives_message_deletion(db):
    mid = db.add_message("Eski başlık", "Eski içerik", True, 180)
    message = db.messages()[0]
    db.begin_attempt("a", "s", message)
    db.finish_attempt("a", "sent")
    db.delete_message(mid)
    attempt = db.last_sent()
    assert attempt.content == "Eski içerik"
    assert attempt.message_id is None
    assert db.stats()["sent"] == 1


def test_history_cleanup_preserves_cooldown(db):
    mid = db.add_message("a", "içerik", True, 180)
    db.begin_attempt("a", "s", Message(mid, "a", "içerik", True, 180))
    db.set_cooldown(300)
    db.clear_history()
    assert db.history() == []
    assert db.cooldown_remaining(__import__('time').time()) > 290


def test_backup_is_consistent_and_readable(db, tmp_path):
    db.add_message("Türkçe", "Şişli'de mağazamız açıldı! ĞÜİÖÇ", True, 180)
    target = tmp_path / "backups" / "backup.db"
    db.backup(target)
    restored = Database(target)
    assert restored.messages()[0].content == "Şişli'de mağazamız açıldı! ĞÜİÖÇ"
    with pytest.raises(ConfigError):
        db.backup(db.path)


def test_parallel_history_writes(db):
    ids = [db.add_message("başlık", "içerik", True, 180) for _ in range(40)]
    def write(index):
        db.begin_attempt(str(index), "s", Message(ids[index], "başlık", "içerik", True, 180))
        db.finish_attempt(str(index), "sent")
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(write, range(40)))
    assert db.stats()["sent"] == 40


def test_future_schema_does_not_silently_downgrade(tmp_path):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=99")
    with pytest.raises(ConfigError):
        Database(path)
