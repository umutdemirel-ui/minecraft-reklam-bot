from dataclasses import replace

import pytest

from core.config import AppPaths, ConfigError, Settings, default_settings


def test_defaults_are_safe_and_json_matches():
    settings = default_settings(AppPaths.discover())
    assert settings == Settings()
    assert not settings.automation_allowed
    assert not settings.default_chat_confirmed
    assert settings.interval_seconds == 180


@pytest.mark.parametrize("change", [
    {"interval_seconds": 1}, {"server_min_interval_seconds": 0},
    {"start_delay_seconds": -1}, {"hotkey": "f5"},
    {"loop": "false"}, {"max_message_length": 500},
    {"schema_version": 2}, {"session_limit_seconds": 10},
])
def test_invalid_settings_rejected(change):
    with pytest.raises(ConfigError):
        replace(Settings(), **change).validate()


def test_data_dir_is_outside_resources(tmp_path):
    paths = AppPaths.discover(tmp_path / "user-data")
    paths.ensure()
    assert paths.database.parent == paths.data
    assert paths.logs.is_dir()
    assert paths.database != paths.resources / "advertiser.db"
