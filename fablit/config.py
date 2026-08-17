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
SUPPORTED_STIMULUS_PROVIDERS = {"builtin", "wikimedia"}


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
    stimulus_provider: str = Field(
        "builtin",
        description=(
            "Visual stimulus provider: 'builtin' (deterministic bundled stimuli) "
            "or 'wikimedia' (approved external source with safe fallback)."
        ),
    )
    stimulus_fallback_images: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Optional JSON object mapping activity title to a custom fallback image "
            "URL, overriding the bundled images without code changes."
        ),
    )
    wikimedia_endpoint: str = Field(
        "https://commons.wikimedia.org/w/api.php",
        description="Wikimedia Commons API endpoint used by the wikimedia provider.",
    )
    wikimedia_timeout: float = Field(
        10.0,
        ge=0.1,
        description="Timeout in seconds for Wikimedia Commons retrieval.",
    )
    wikimedia_width: int = Field(
        1200,
        ge=1,
        description="Thumbnail width requested from Wikimedia Commons.",
    )
    wikimedia_limit: int = Field(
        5,
        ge=1,
        le=50,
        description="Number of candidate images searched on Wikimedia Commons.",
    )
    config_file: Path | None = Field(None, description="Path to optional config file.")
    version: str = Field("0.1.0", description="Application version.")

    model_config = {
        "env_prefix": "FABLIT_",
        "frozen": True,
        "extra": "forbid",
        # Complex fields (e.g. the fallback-image map) are parsed by dedicated
        # field validators, not auto-decoded from env by pydantic-settings.
        "enable_decoding": False,
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

    @field_validator("stimulus_provider", mode="before")
    def normalize_stimulus_provider(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in SUPPORTED_STIMULUS_PROVIDERS:
            allowed = ", ".join(sorted(SUPPORTED_STIMULUS_PROVIDERS))
            raise ValueError(
                f"Unsupported stimulus provider '{value}'. Must be one of: {allowed}."
            )
        return normalized

    @field_validator("stimulus_fallback_images", mode="before")
    def parse_stimulus_fallback_images(cls, value: object) -> dict[str, str]:
        """Accept the fallback-image map as a JSON string (env var) or a dict."""
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "stimulus_fallback_images must be a valid JSON object "
                    f"mapping activity title to image URL: {exc}"
                ) from exc
            if not isinstance(parsed, dict):
                raise ValueError(
                    "stimulus_fallback_images must be a JSON object mapping "
                    "activity title to image URL"
                )
            return {
                str(key): str(item)
                for key, item in parsed.items()
                if isinstance(key, str) and isinstance(item, str)
            }
        return value  # type: ignore[return-value]


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
        "stimulus_provider": "FABLIT_STIMULUS_PROVIDER",
        "stimulus_fallback_images": "FABLIT_STIMULUS_FALLBACK_IMAGES",
        "wikimedia_endpoint": "FABLIT_WIKIMEDIA_ENDPOINT",
        "wikimedia_timeout": "FABLIT_WIKIMEDIA_TIMEOUT",
        "wikimedia_width": "FABLIT_WIKIMEDIA_WIDTH",
        "wikimedia_limit": "FABLIT_WIKIMEDIA_LIMIT",
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
