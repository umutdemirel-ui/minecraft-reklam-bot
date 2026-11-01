"""Validated configuration and user-data paths (never write beside a frozen EXE by default)."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

APP_NAME = "MinecraftAutoAdvertiser"
MIN_INTERVAL = 30
MAX_INTERVAL = 86400


class ConfigError(ValueError):
    pass


def integer(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ConfigError(f"{name} tam sayı olmalı.")
    try:
        result = int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} tam sayı olmalı.") from exc
    if not low <= result <= high:
        raise ConfigError(f"{name}, {low}–{high} aralığında olmalı.")
    return result


@dataclass(frozen=True)
class Settings:
    schema_version: int = 1
    window_title: str = ""
    interval_seconds: int = 180
    message_gap_seconds: int = 0
    server_min_interval_seconds: int = 180
    start_delay_seconds: int = 10
    session_limit_seconds: int = 0
    loop: bool = True
    automation_allowed: bool = False
    default_chat_confirmed: bool = False
    max_message_length: int = 256
    theme: str = "Koyu"
    launch_on_startup: bool = False
    hotkey: str = "f8"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        if not isinstance(data, dict):
            raise ConfigError("Ayar kaydı nesne olmalı.")
        known = {field.name for field in fields(cls)}
        values = {key: value for key, value in data.items() if key in known}
        try:
            obj = cls(**values)
        except TypeError as exc:
            raise ConfigError("Ayar alanlarının türü geçersiz.") from exc
        for name in ("interval_seconds", "server_min_interval_seconds", "message_gap_seconds",
                     "start_delay_seconds", "session_limit_seconds", "max_message_length"):
            object.__setattr__(obj, name, integer(getattr(obj, name), name, 0, 604800))
        obj.validate()
        return obj

    def validate(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ConfigError("Desteklenmeyen ayar sürümü.")
        for name in ("window_title", "theme", "hotkey"):
            if not isinstance(getattr(self, name), str):
                raise ConfigError(f"{name} metin olmalı.")
        if len(self.window_title.strip()) > 200:
            raise ConfigError("Pencere başlığı en fazla 200 karakter olabilir.")
        for name in ("loop", "automation_allowed", "default_chat_confirmed", "launch_on_startup"):
            if type(getattr(self, name)) is not bool:
                raise ConfigError(f"{name} açık/kapalı değeri olmalı.")
        integer(self.interval_seconds, "Gönderim aralığı", MIN_INTERVAL, MAX_INTERVAL)
        integer(self.server_min_interval_seconds, "Sunucu alt sınırı", MIN_INTERVAL, MAX_INTERVAL)
        integer(self.message_gap_seconds, "Ek bekleme", 0, 3600)
        integer(self.start_delay_seconds, "Başlangıç gecikmesi", 3, 300)
        if self.session_limit_seconds != 0:
            integer(self.session_limit_seconds, "Çalışma sınırı", 60, 604800)
        integer(self.max_message_length, "Mesaj uzunluğu", 1, 256)
        if self.theme not in ("Koyu", "Açık", "Sistem"):
            raise ConfigError("Tema Koyu, Açık veya Sistem olmalı.")
        if self.hotkey.lower() != "f8":
            raise ConfigError("Güvenlik standardı olarak acil durdurma kısayolu F8'dir.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AppPaths:
    data: Path
    resources: Path
    portable: bool

    @property
    def database(self) -> Path:
        return self.data / "advertiser.db"

    @property
    def logs(self) -> Path:
        return self.data / "logs"

    @classmethod
    def discover(cls, data_dir: Path | None = None) -> "AppPaths":
        resources = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        executable_dir = Path(sys.executable).resolve().parent
        portable = getattr(sys, "frozen", False) and (executable_dir / "portable.txt").exists()
        if data_dir is not None:
            data = data_dir.expanduser().resolve()
        elif portable:
            data = executable_dir / "data"
        elif os.name == "nt":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            data = root / APP_NAME
        else:
            root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            data = root / APP_NAME
        return cls(data, resources, portable)

    def ensure(self) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)


def default_settings(paths: AppPaths) -> Settings:
    path = paths.resources / "config" / "settings.json"
    try:
        return Settings.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Varsayılan ayar dosyası okunamadı: {path}") from exc
