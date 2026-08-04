from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fablit.config import AppConfig, ConfigValidationError, load_config


def test_load_config_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FABLIT_SERVICE_NAME", "fablit-test")
    monkeypatch.setenv("FABLIT_ENV", "production")
    monkeypatch.setenv("FABLIT_LOG_LEVEL", "DEBUG")

    config = load_config()

    assert config.service_name == "fablit-test"
    assert config.environment == "production"
    assert config.log_level == "DEBUG"
    assert config.config_file is None


def test_load_config_from_json_file_and_environment_precedence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "service_name": "file-service",
                "environment": "development",
                "log_level": "WARNING",
                "host": "127.0.0.1",
                "port": 8081,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("FABLIT_CONFIG", str(config_file))
    monkeypatch.setenv("FABLIT_LOG_LEVEL", "INFO")

    config = load_config()

    assert config.service_name == "file-service"
    assert config.environment == "development"
    assert config.log_level == "INFO"
    assert config.host == "127.0.0.1"
    assert config.port == 8081
    assert config.config_file == config_file


def test_invalid_configuration_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_PORT", "-1")

    with pytest.raises(ConfigValidationError):
        load_config()


def test_app_config_defaults_are_frozen() -> None:
    config = AppConfig()

    with pytest.raises(ValidationError):
        config.service_name = "changed"
