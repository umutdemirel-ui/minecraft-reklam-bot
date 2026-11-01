"""Small WAL-mode SQLite repository. Each operation owns its connection, including on workers."""
from __future__ import annotations

import json
import sqlite3
import time
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from core.config import ConfigError, Settings
from database.models import Attempt, Message, validate_message


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise ConfigError("Veritabanı daha yeni bir uygulama sürümüne ait.")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                    interval_seconds INTEGER NOT NULL CHECK(interval_seconds BETWEEN 30 AND 86400)
                );
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK(id = 1), value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY,
                    message_id INTEGER REFERENCES messages(id) ON DELETE SET NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN
                        ('pending','sending','sent','failed','aborted','unknown')),
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    error TEXT NOT NULL DEFAULT '',
                    session_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS attempts_created ON attempts(created_at DESC);
                CREATE INDEX IF NOT EXISTS attempts_status ON attempts(status);
                PRAGMA user_version = 1;
            """)

    def recover_interrupted(self) -> int:
        """An ambiguous Enter outcome is NEVER retried automatically."""
        with self.connection() as conn:
            cursor = conn.execute(
                "UPDATE attempts SET status='unknown', completed_at=?, error=? "
                "WHERE status IN ('pending','sending')",
                (utc_now(), "Önceki oturum kesildi; sunucuya ulaşıp ulaşmadığı bilinmiyor. "
                 "Otomatik yeniden deneme yapılmaz."),
            )
            return cursor.rowcount

    def get_settings(self, defaults: Settings) -> Settings:
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE id=1").fetchone()
            if row is None:
                conn.execute("INSERT INTO settings(id,value) VALUES(1,?)",
                             (json.dumps(defaults.to_dict()),))
                return defaults
        try:
            return Settings.from_dict(json.loads(row["value"]))
        except (TypeError, json.JSONDecodeError) as exc:
            raise ConfigError("Kayıtlı ayarlar bozuk. Otomasyon başlatılmadı.") from exc

    def save_settings(self, settings: Settings) -> None:
        settings.validate()
        with self.connection() as conn:
            conn.execute("INSERT INTO settings(id,value) VALUES(1,?) ON CONFLICT(id) "
                         "DO UPDATE SET value=excluded.value", (json.dumps(settings.to_dict()),))

    def messages(self, active_only: bool = False) -> list[Message]:
        sql = "SELECT * FROM messages" + (" WHERE active=1" if active_only else "") + " ORDER BY id"
        with self.connection() as conn:
            return [Message.from_row(row) for row in conn.execute(sql)]

    def add_message(self, title: str, content: str, active: bool, interval: int,
                    max_length: int = 256) -> int:
        title, content, interval = validate_message(title, content, interval, max_length)
        with self.connection() as conn:
            cursor = conn.execute("INSERT INTO messages(title,content,active,interval_seconds) "
                                  "VALUES(?,?,?,?)", (title, content, int(active), interval))
            conn.execute("INSERT INTO metadata(key,value) VALUES('messages_revision','1') "
                         "ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1")
            return int(cursor.lastrowid)

    def update_message(self, message_id: int, title: str, content: str, active: bool,
                       interval: int, max_length: int = 256) -> None:
        title, content, interval = validate_message(title, content, interval, max_length)
        with self.connection() as conn:
            cursor = conn.execute("UPDATE messages SET title=?,content=?,active=?,interval_seconds=? "
                                  "WHERE id=?", (title, content, int(active), interval, message_id))
            if not cursor.rowcount:
                raise ConfigError("Mesaj bulunamadı.")
            conn.execute("INSERT INTO metadata(key,value) VALUES('messages_revision','1') "
                         "ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1")

    def delete_message(self, message_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM messages WHERE id=?", (message_id,))
            conn.execute("INSERT INTO metadata(key,value) VALUES('messages_revision','1') "
                         "ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1")

    def revision(self) -> str:
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key='messages_revision'").fetchone()
            return row["value"] if row else "0"

    def begin_attempt(self, attempt_id: str, session_id: str, message: Message,
                      cooldown: int = 180) -> None:
        """Commit the journal and cooldown together BEFORE the first synthetic keystroke."""
        with self.connection() as conn:
            conn.execute("INSERT INTO attempts(id,message_id,title,content,status,created_at,session_id) "
                         "VALUES(?,?,?,?, 'pending', ?,?)",
                         (attempt_id, message.id, message.title, message.content, utc_now(), session_id))
            conn.execute("INSERT INTO metadata(key,value) VALUES('last_attempt_epoch',?) "
                         "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(time.time()),))
            conn.execute("INSERT INTO metadata(key,value) VALUES('last_interval',?) "
                         "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(cooldown),))

    def mark_sending(self, attempt_id: str) -> None:
        with self.connection() as conn:
            conn.execute("UPDATE attempts SET status='sending' WHERE id=? AND status='pending'",
                         (attempt_id,))

    def finish_attempt(self, attempt_id: str, status: str, error: str = "") -> None:
        if status not in ("sent", "failed", "aborted", "unknown"):
            raise ValueError("Geçersiz işlem sonucu")
        with self.connection() as conn:
            conn.execute("UPDATE attempts SET status=?,completed_at=?,error=? WHERE id=?",
                         (status, utc_now(), error[:1000], attempt_id))

    def set_cooldown(self, seconds: int) -> None:
        with self.connection() as conn:
            conn.execute("INSERT INTO metadata(key,value) VALUES('last_interval',?) "
                         "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(seconds),))

    def cooldown_remaining(self, now_epoch: float) -> float:
        with self.connection() as conn:
            rows = dict(conn.execute("SELECT key,value FROM metadata "
                                     "WHERE key IN ('last_attempt_epoch','last_interval')"))
        try:
            return max(0.0, float(rows["last_attempt_epoch"]) + float(rows["last_interval"]) - now_epoch)
        except (KeyError, ValueError):
            return 0.0

    def history(self, limit: int = 100, offset: int = 0) -> list[Attempt]:
        with self.connection() as conn:
            return [Attempt.from_row(row) for row in conn.execute(
                "SELECT * FROM attempts ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
                (limit, offset))]

    def stats(self) -> dict[str, int]:
        with self.connection() as conn:
            return {
                "messages": conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                "active": conn.execute("SELECT COUNT(*) FROM messages WHERE active=1").fetchone()[0],
                "sent": conn.execute("SELECT COUNT(*) FROM attempts WHERE status='sent'").fetchone()[0],
                "unknown": conn.execute("SELECT COUNT(*) FROM attempts WHERE status='unknown'").fetchone()[0],
            }

    def last_sent(self) -> Attempt | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM attempts WHERE status='sent' "
                               "ORDER BY created_at DESC, rowid DESC LIMIT 1").fetchone()
            return Attempt.from_row(row) if row else None

    def clear_history(self) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM attempts")
            # Cooldown metadata deliberately survives history cleanup.

    def backup(self, destination: Path) -> None:
        destination = Path(destination)
        if destination.resolve() == self.path.resolve():
            raise ConfigError("Yedek, çalışan veritabanıyla aynı dosya olamaz.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Verify a temporary snapshot before replacing an existing user-selected backup.
        fd, temporary = tempfile.mkstemp(prefix=".advertiser-backup-", suffix=".db", dir=destination.parent)
        os.close(fd)
        try:
            with self.connection() as source:
                target = sqlite3.connect(temporary)
                try:
                    source.backup(target)
                    result = target.execute("PRAGMA integrity_check").fetchone()[0]
                    if result != "ok":
                        raise ConfigError("Yedek bütünlük doğrulaması başarısız.")
                finally:
                    target.close()
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
