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
    config = AppConfig.model_validate({})

    with pytest.raises(ValidationError):
        config.service_name = "changed"


def test_stimulus_provider_defaults_to_builtin() -> None:
    config = AppConfig.model_validate({})

    assert config.stimulus_provider == "builtin"


def test_stimulus_provider_accepts_wikimedia() -> None:
    config = AppConfig.model_validate({"stimulus_provider": "wikimedia"})

    assert config.stimulus_provider == "wikimedia"


def test_stimulus_provider_is_normalised_to_lowercase() -> None:
    config = AppConfig.model_validate({"stimulus_provider": "WIKIMEDIA"})

    assert config.stimulus_provider == "wikimedia"


def test_unsupported_stimulus_provider_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_STIMULUS_PROVIDER", "unsplash")

    with pytest.raises(ConfigValidationError, match="stimulus provider"):
        load_config()


def test_stimulus_fallback_images_default_to_empty() -> None:
    config = AppConfig.model_validate({})

    assert config.stimulus_fallback_images == {}


def test_stimulus_fallback_images_parse_from_json_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FABLIT_STIMULUS_FALLBACK_IMAGES",
        json.dumps(
            {"CAT Practice — 2D & 3D Composition Analysis": "/static/images/custom.svg"}
        ),
    )

    config = load_config()

    assert config.stimulus_fallback_images == {
        "CAT Practice — 2D & 3D Composition Analysis": "/static/images/custom.svg"
    }


def test_stimulus_fallback_images_accept_direct_dict() -> None:
    config = AppConfig.model_validate(
        {
            "stimulus_fallback_images": {
                "CAT Practice — 2D & 3D Composition Analysis": "/x.svg"
            }
        }
    )

    assert config.stimulus_fallback_images == {
        "CAT Practice — 2D & 3D Composition Analysis": "/x.svg"
    }


def test_invalid_stimulus_fallback_images_raise_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_STIMULUS_FALLBACK_IMAGES", "not-json")

    with pytest.raises(ConfigValidationError, match="stimulus_fallback_images"):
        load_config()


def test_wikimedia_knobs_default_to_sane_values() -> None:
    config = AppConfig.model_validate({})

    assert config.wikimedia_endpoint == "https://commons.wikimedia.org/w/api.php"
    assert config.wikimedia_timeout == 10.0
    assert config.wikimedia_width == 1200
    assert config.wikimedia_limit == 5


def test_wikimedia_knobs_read_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_WIKIMEDIA_ENDPOINT", "https://example.test/api.php")
    monkeypatch.setenv("FABLIT_WIKIMEDIA_TIMEOUT", "2.5")
    monkeypatch.setenv("FABLIT_WIKIMEDIA_WIDTH", "640")
    monkeypatch.setenv("FABLIT_WIKIMEDIA_LIMIT", "3")

    config = load_config()

    assert config.wikimedia_endpoint == "https://example.test/api.php"
    assert config.wikimedia_timeout == 2.5
    assert config.wikimedia_width == 640
    assert config.wikimedia_limit == 3


def test_invalid_wikimedia_limit_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_WIKIMEDIA_LIMIT", "0")

    with pytest.raises(ConfigValidationError):
        load_config()


# --- Practice history repository (SPEC-021) -----------------------------------


def test_practice_history_repository_defaults_to_disabled() -> None:
    config = AppConfig.model_validate({})

    assert config.practice_history_repository is None


def test_practice_history_repository_accepts_memory() -> None:
    config = AppConfig.model_validate({"practice_history_repository": "memory"})

    assert config.practice_history_repository == "memory"


def test_practice_history_repository_accepts_datastore() -> None:
    config = AppConfig.model_validate({"practice_history_repository": "datastore"})

    assert config.practice_history_repository == "datastore"


def test_practice_history_repository_is_normalised_to_lowercase() -> None:
    config = AppConfig.model_validate({"practice_history_repository": "  DATASTORE "})

    assert config.practice_history_repository == "datastore"


def test_practice_history_repository_reads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_PRACTICE_HISTORY_REPOSITORY", "memory")

    config = load_config()

    assert config.practice_history_repository == "memory"


@pytest.mark.parametrize("disabled", ["", "none", "off", "disabled"])
def test_practice_history_repository_disabled_values_become_none(
    disabled: str,
) -> None:
    config = AppConfig.model_validate({"practice_history_repository": disabled})

    assert config.practice_history_repository is None


def test_unsupported_practice_history_repository_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_PRACTICE_HISTORY_REPOSITORY", "sqlite")

    with pytest.raises(ConfigValidationError, match="practice history repository"):
        load_config()
