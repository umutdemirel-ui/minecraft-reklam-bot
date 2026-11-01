"""Domain objects. History is an append-only attempt journal except for explicit cleanup."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import MAX_INTERVAL, MIN_INTERVAL, ConfigError, integer


@dataclass(frozen=True)
class Message:
    id: int
    title: str
    content: str
    active: bool
    interval_seconds: int

    @classmethod
    def from_row(cls, row: Any) -> "Message":
        return cls(row["id"], row["title"], row["content"], bool(row["active"]),
                   row["interval_seconds"])


def validate_message(title: str, content: str, interval: int, max_length: int = 256) -> tuple[str, str, int]:
    if not isinstance(title, str) or not isinstance(content, str):
        raise ConfigError("Başlık ve içerik metin olmalı.")
    title, content = title.strip(), content.strip()
    if not title or len(title) > 80:
        raise ConfigError("Başlık 1–80 karakter olmalı.")
    if not content:
        raise ConfigError("Mesaj içeriği boş olamaz.")
    if len(content) > max_length:
        raise ConfigError(f"Mesaj en fazla {max_length} karakter olabilir.")
    if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in content):
        raise ConfigError("Mesaj tek satır olmalı; kontrol karakterleri içeremez.")
    if content.startswith("/"):
        raise ConfigError("Güvenlik için komut gönderimi desteklenmez. Mesaj / ile başlayamaz.")
    return title, content, integer(interval, "Mesaj aralığı", MIN_INTERVAL, MAX_INTERVAL)


@dataclass(frozen=True)
class Attempt:
    id: str
    message_id: int | None
    title: str
    content: str
    status: str
    created_at: str
    completed_at: str | None
    error: str
    session_id: str

    @classmethod
    def from_row(cls, row: Any) -> "Attempt":
        return cls(*(row[key] for key in ("id", "message_id", "title", "content", "status",
                                         "created_at", "completed_at", "error", "session_id")))
