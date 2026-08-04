from __future__ import annotations

import json
import os
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings

# Dynamically import PyYAML without needing a mypy type-ignore comment.
# Annotate `yaml` as Any so assigning `None` is type-safe across envs.
yaml: Any
try:
    yaml = import_module("yaml")
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

SUPPORTED_ENVIRONMENTS = {"development", "testing", "production"}
SUPPORTED_LOG_FORMATS = {"json", "text"}


class ConfigError(RuntimeError):
    """Base exception raised for configuration loading issues."""


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""


class AppConfig(BaseSettings):
    service_name: str = Field("fablit", description="Logical service name.")
    environment: str = Field("development", description="Runtime environment.")
    host: str = Field("0.0.0.0", description="Host address to bind to.")
    port: int = Field(8000, ge=1, le=65535, description="Port to bind to.")
    debug: bool = Field(False, description="Enable debug mode.")
    log_level: str = Field("INFO", description="Logging level.")
    log_format: str = Field("json", description="Structured log output format.")
    config_file: Path | None = Field(None, description="Path to optional config file.")
    version: str = Field("0.1.0", description="Application version.")

    model_config = {
        "env_prefix": "FABLIT_",
        "frozen": True,
        "extra": "forbid",
    }

    @field_validator("environment", mode="before")
    def normalize_environment(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in SUPPORTED_ENVIRONMENTS:
            allowed = ", ".join(sorted(SUPPORTED_ENVIRONMENTS))
            raise ValueError(
                f"Unsupported environment '{value}'. Must be one of: {allowed}."
            )
        return normalized

    @field_validator("log_format", mode="before")
    def normalize_log_format(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in SUPPORTED_LOG_FORMATS:
            allowed = ", ".join(sorted(SUPPORTED_LOG_FORMATS))
            raise ValueError(
                f"Unsupported log format '{value}'. Must be one of: {allowed}."
            )
        return normalized


def _load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    raw_text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise ConfigError(
                "YAML configuration support requires PyYAML. "
                "Install it or use JSON format."
            )
        loaded = cast(dict[str, Any], yaml.safe_load(raw_text))
        if not loaded:
            return {}
        return loaded

    if suffix == ".json" or not suffix:
        return cast(dict[str, Any], json.loads(raw_text))

    raise ConfigError(
        "Unsupported configuration file type. Use JSON (.json) or YAML (.yaml/.yml)."
    )


def _resolve_environment_overrides() -> dict[str, Any]:
    env_map = {
        "service_name": "FABLIT_SERVICE_NAME",
        "environment": "FABLIT_ENV",
        "host": "FABLIT_HOST",
        "port": "FABLIT_PORT",
        "debug": "FABLIT_DEBUG",
        "log_level": "FABLIT_LOG_LEVEL",
        "log_format": "FABLIT_LOG_FORMAT",
        "version": "FABLIT_VERSION",
    }
    resolved: dict[str, Any] = {}

    for field_name, env_name in env_map.items():
        value = os.getenv(env_name)
        if value is not None:
            resolved[field_name] = value

    return resolved


def load_config(*, overrides: dict[str, Any] | None = None) -> AppConfig:
    config_data: dict[str, Any] = {}
    config_path = os.getenv("FABLIT_CONFIG")

    if config_path:
        config_file_path = Path(config_path)
        config_data = _load_config_file(config_file_path)
        config_data["config_file"] = config_file_path

    config_data.update(_resolve_environment_overrides())

    if overrides:
        config_data.update(overrides)

    try:
        return AppConfig(**config_data)
    except ValidationError as exc:
        raise ConfigValidationError(exc) from exc
