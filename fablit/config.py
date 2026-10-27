from __future__ import annotations

import json
import os
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings

from fablit.application.errors import InvalidNewsSourceError
from fablit.application.news_sources import (
    DEFAULT_NEWS_SOURCES,
    NewsSource,
    parse_news_sources,
)

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
SUPPORTED_PRACTICE_HISTORY_REPOSITORIES = {"memory", "datastore"}
SUPPORTED_ARTIFACT_STORAGE_BACKENDS = {"file", "gcs"}
SUPPORTED_AUTHORING_CANDIDATE_STORES = {"memory", "datastore"}
SUPPORTED_PUBLISHED_PRACTICE_STORES = {"memory", "datastore"}
SUPPORTED_NEWS_REPOSITORIES = {"memory", "datastore"}
SUPPORTED_NEWS_TASK_DISPATCH = {"inline", "cloud_tasks"}


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
    practice_history_repository: str | None = Field(
        None,
        description=(
            "Practice history persistence backend (SPEC-021): 'memory' "
            "(in-memory, for tests and local development) or 'datastore' "
            "(Google Cloud Datastore, for the deployed App Engine environment). "
            "Unset disables practice history persistence."
        ),
    )
    artifact_storage_backend: str = Field(
        "file",
        description=(
            "Artifact storage backend (SPEC-034): 'file' (file-backed, for tests "
            "and local development) or 'gcs' (Google Cloud Storage, for the "
            "deployed App Engine environment)."
        ),
    )
    artifact_storage_bucket: str | None = Field(
        None,
        description=(
            "Google Cloud Storage bucket name for private sketchbook artifact bytes "
            "(SPEC-034). Required when artifact_storage_backend is 'gcs'."
        ),
    )
    artifact_storage_dir: str | None = Field(
        None,
        description=(
            "Deployment-private directory holding sketchbook artifact bytes "
            "(SPEC-033). Practice-history records store only artifact "
            "references, so the binary payload lives here instead when using "
            "the file backend. Unset uses FABLIT_ARTIFACT_STORAGE_DIR, or a "
            "process-private directory under the system temp location when that "
            "is also unset."
        ),
    )
    authoring_secret: str | None = Field(
        None,
        description=(
            "Shared secret for internal authoring access (SEC-001). "
            "Unset disables internal authoring access."
        ),
    )
    ai_provider_api_key: str | None = Field(
        None,
        description=(
            "Server-side API key for the AI practice authoring provider "
            "(SPEC-032 / SEC-001). Kept strictly server-side and never exposed to "
            "learners."
        ),
    )
    ai_provider_model: str = Field(
        "gemini-2.5-flash",
        description=(
            "Model identifier for the AI practice authoring provider "
            "(SPEC-032 / ARCH-001), retained as authoring provenance. Only "
            "used when ai_provider_api_key is configured."
        ),
    )
    image_search_api_key: str | None = Field(
        None,
        description=(
            "Server-side Pexafy API key for optional stimulus-image search "
            "during practice authoring (SPEC-036). Unset disables image "
            "sourcing; candidate generation still works."
        ),
    )
    image_search_endpoint: str = Field(
        "https://api.pexafy.com/api/v1/search/photos",
        description="Pexafy semantic image-search endpoint (SPEC-036).",
    )
    image_search_timeout: float = Field(
        10.0,
        ge=0.1,
        description="Timeout in seconds for one Pexafy image search.",
    )
    image_search_limit: int = Field(
        6,
        ge=1,
        le=20,
        description="Maximum images returned for one candidate (SPEC-036).",
    )
    authoring_candidate_store: str = Field(
        "memory",
        description=(
            "Authoring candidate store backend (SPEC-032 / FIX-7): 'memory' "
            "(in-memory, for tests and local development) or 'datastore' "
            "(Google Cloud Datastore, for the deployed App Engine environment)."
        ),
    )
    authoring_candidate_retention_days: int = Field(
        30,
        ge=1,
        description=(
            "Retention window in days for authoring candidates (FIX-7). "
            "Unapproved candidates older than this window are considered expired."
        ),
    )
    published_practice_store: str = Field(
        "memory",
        description=(
            "Published practice store backend (SPEC-035): 'memory' (in-memory, "
            "for tests and local development) or 'datastore' (Google Cloud "
            "Datastore, for the deployed App Engine environment). Holds the "
            "explicitly published learner-library practices derived from "
            "approved authoring candidates."
        ),
    )
    news_repository: str = Field(
        "memory",
        description=(
            "Curated news repository backend (SPEC-041): 'memory' (in-memory, "
            "for tests and local development) or 'datastore' (Google Cloud "
            "Datastore, for the deployed App Engine environment). Holds only "
            "the curated Fashion & Design Pulse stories."
        ),
    )
    news_sources: tuple[NewsSource, ...] = Field(
        default_factory=lambda: DEFAULT_NEWS_SOURCES,
        description=(
            "Explicit allowlist of approved news sources (SPEC-041). A JSON "
            "list of {name, feed_url, site_url} objects; story links must "
            "belong to the source's publisher host. Empty disables curation "
            "but keeps the existing feed readable."
        ),
    )
    news_max_items_per_source: int = Field(
        6,
        ge=1,
        le=50,
        description="Maximum news items considered per source in one refresh.",
    )
    news_freshness_days: int = Field(
        14,
        ge=1,
        le=90,
        description=(
            "How many days old a story may be and still be eligible for "
            "publication (SPEC-041)."
        ),
    )
    news_max_summary_chars: int = Field(
        600,
        ge=100,
        le=2000,
        description="Maximum curated summary length accepted for publication.",
    )
    news_relevance_threshold: float = Field(
        0.5,
        ge=0,
        le=1,
        description=(
            "Minimum provider relevance score for a story to be published (SPEC-041)."
        ),
    )
    news_fetch_timeout: float = Field(
        10.0,
        ge=0.1,
        description="Timeout in seconds for one approved news source fetch.",
    )
    news_max_response_bytes: int = Field(
        512_000,
        ge=1024,
        description="Maximum response size read from one news source.",
    )
    news_max_sources_per_task: int = Field(
        2,
        ge=1,
        le=10,
        description=(
            "Maximum approved sources processed by one durable curation task "
            "(SPEC-042). A larger batch is checkpointed and continued in "
            "bounded, resumable task units."
        ),
    )
    news_task_dispatch: str = Field(
        "inline",
        description=(
            "Durable dispatch backend for curation jobs (SPEC-042): 'inline' "
            "for local development and tests (runs the task in the request) "
            "or 'cloud_tasks' for managed production dispatch."
        ),
    )
    news_task_queue: str = Field(
        "",
        description=(
            "Full Cloud Tasks queue resource name used for curation jobs, for "
            "example projects/<project>/locations/<region>/queues/news-curation."
        ),
    )
    news_task_handler_url: str = Field(
        "",
        description=(
            "Absolute HTTPS URL of the protected curation task handler in this "
            "application, for example https://<project>.appspot.com/tasks/news-curation."
        ),
    )
    news_task_service_account: str = Field(
        "",
        description=(
            "Service account email Cloud Tasks uses for the curation task OIDC "
            "token, and the only identity the task handler accepts."
        ),
    )
    news_task_audience: str = Field(
        "",
        description=(
            "Expected OIDC audience for curation task requests; defaults to the "
            "configured task handler URL."
        ),
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

    @field_validator("practice_history_repository", mode="before")
    def normalize_practice_history_repository(cls, value: object) -> object:
        """Normalize the repository choice; empty/unset means disabled."""
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized or normalized in {"none", "off", "disabled"}:
                return None
            if normalized not in SUPPORTED_PRACTICE_HISTORY_REPOSITORIES:
                allowed = ", ".join(sorted(SUPPORTED_PRACTICE_HISTORY_REPOSITORIES))
                raise ValueError(
                    f"Unsupported practice history repository '{value}'. "
                    f"Must be one of: {allowed}."
                )
            return normalized
        return value

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

    @field_validator("artifact_storage_backend", mode="before")
    def normalize_artifact_storage_backend(cls, value: object) -> str:
        """Normalize the artifact storage backend; defaults to 'file'."""
        if value is None:
            return "file"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return "file"
            if normalized not in SUPPORTED_ARTIFACT_STORAGE_BACKENDS:
                allowed = ", ".join(sorted(SUPPORTED_ARTIFACT_STORAGE_BACKENDS))
                raise ValueError(
                    f"Unsupported artifact storage backend '{value}'. "
                    f"Must be one of: {allowed}."
                )
            return normalized
        return str(value)

    @field_validator("authoring_candidate_store", mode="before")
    def normalize_authoring_candidate_store(cls, value: object) -> str:
        """Normalize the authoring candidate store; defaults to 'memory'."""
        if value is None:
            return "memory"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return "memory"
            if normalized not in SUPPORTED_AUTHORING_CANDIDATE_STORES:
                allowed = ", ".join(sorted(SUPPORTED_AUTHORING_CANDIDATE_STORES))
                raise ValueError(
                    f"Unsupported authoring candidate store '{value}'. "
                    f"Must be one of: {allowed}."
                )
            return normalized
        return str(value)

    @field_validator("published_practice_store", mode="before")
    def normalize_published_practice_store(cls, value: object) -> str:
        """Normalize the published practice store; defaults to 'memory'."""
        if value is None:
            return "memory"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return "memory"
            if normalized not in SUPPORTED_PUBLISHED_PRACTICE_STORES:
                allowed = ", ".join(sorted(SUPPORTED_PUBLISHED_PRACTICE_STORES))
                raise ValueError(
                    f"Unsupported published practice store '{value}'. "
                    f"Must be one of: {allowed}."
                )
            return normalized
        return str(value)

    @field_validator("news_repository", mode="before")
    def normalize_news_repository(cls, value: object) -> str:
        """Normalize the curated news repository; defaults to 'memory'."""
        if value is None:
            return "memory"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return "memory"
            if normalized not in SUPPORTED_NEWS_REPOSITORIES:
                allowed = ", ".join(sorted(SUPPORTED_NEWS_REPOSITORIES))
                raise ValueError(
                    f"Unsupported news repository '{value}'. Must be one of: {allowed}."
                )
            return normalized
        return str(value)

    @field_validator("news_task_dispatch", mode="before")
    def normalize_news_task_dispatch(cls, value: object) -> str:
        """Normalize the durable dispatch backend; defaults to 'inline'."""
        if value is None:
            return "inline"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return "inline"
            if normalized not in SUPPORTED_NEWS_TASK_DISPATCH:
                allowed = ", ".join(sorted(SUPPORTED_NEWS_TASK_DISPATCH))
                raise ValueError(
                    f"Unsupported news task dispatch '{value}'. Must be one of: "
                    f"{allowed}."
                )
            return normalized
        return str(value)

    @field_validator("news_sources", mode="before")
    def parse_news_sources_config(cls, value: object) -> object:
        """Accept the source allowlist as a JSON string or a list of objects."""
        try:
            return parse_news_sources(value)
        except InvalidNewsSourceError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("artifact_storage_bucket", mode="before")
    def normalize_artifact_storage_bucket(cls, value: object) -> str | None:
        """Strip whitespace from bucket name; empty string becomes None."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return str(value)

    @field_validator(
        "authoring_secret",
        "ai_provider_api_key",
        "image_search_api_key",
        mode="before",
    )
    def normalize_optional_secrets(cls, value: object) -> str | None:
        """Strip whitespace from optional secrets; empty string becomes None."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return str(value)

    @field_validator("ai_provider_model", mode="before")
    def normalize_ai_provider_model(cls, value: object) -> str:
        """Strip whitespace from the model name; blank falls back to default."""
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else "gemini-2.5-flash"
        return str(value)

    @model_validator(mode="after")
    def validate_gcs_bucket(self) -> AppConfig:
        """Ensure GCS backend is configured with a non-empty bucket name."""
        if self.artifact_storage_backend == "gcs" and not self.artifact_storage_bucket:
            raise ValueError(
                "artifact_storage_bucket is required when "
                "artifact_storage_backend is 'gcs'."
            )
        return self


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
        "practice_history_repository": "FABLIT_PRACTICE_HISTORY_REPOSITORY",
        "artifact_storage_backend": "FABLIT_ARTIFACT_STORAGE_BACKEND",
        "artifact_storage_bucket": "FABLIT_ARTIFACT_STORAGE_BUCKET",
        "artifact_storage_dir": "FABLIT_ARTIFACT_STORAGE_DIR",
        "authoring_secret": "FABLIT_AUTHORING_SECRET",
        "authoring_candidate_store": "FABLIT_AUTHORING_CANDIDATE_STORE",
        "published_practice_store": "FABLIT_PUBLISHED_PRACTICE_STORE",
        "news_repository": "FABLIT_NEWS_REPOSITORY",
        "news_sources": "FABLIT_NEWS_SOURCES",
        "news_max_items_per_source": "FABLIT_NEWS_MAX_ITEMS_PER_SOURCE",
        "news_freshness_days": "FABLIT_NEWS_FRESHNESS_DAYS",
        "news_max_summary_chars": "FABLIT_NEWS_MAX_SUMMARY_CHARS",
        "news_relevance_threshold": "FABLIT_NEWS_RELEVANCE_THRESHOLD",
        "news_fetch_timeout": "FABLIT_NEWS_FETCH_TIMEOUT",
        "news_max_response_bytes": "FABLIT_NEWS_MAX_RESPONSE_BYTES",
        "news_max_sources_per_task": "FABLIT_NEWS_MAX_SOURCES_PER_TASK",
        "news_task_dispatch": "FABLIT_NEWS_TASK_DISPATCH",
        "news_task_queue": "FABLIT_NEWS_TASK_QUEUE",
        "news_task_handler_url": "FABLIT_NEWS_TASK_HANDLER_URL",
        "news_task_service_account": "FABLIT_NEWS_TASK_SERVICE_ACCOUNT",
        "news_task_audience": "FABLIT_NEWS_TASK_AUDIENCE",
        "authoring_candidate_retention_days": (
            "FABLIT_AUTHORING_CANDIDATE_RETENTION_DAYS"
        ),
        "ai_provider_api_key": "FABLIT_AI_PROVIDER_API_KEY",
        "ai_provider_model": "FABLIT_AI_PROVIDER_MODEL",
        "image_search_api_key": "FABLIT_IMAGE_SEARCH_API_KEY",
        "image_search_endpoint": "FABLIT_IMAGE_SEARCH_ENDPOINT",
        "image_search_timeout": "FABLIT_IMAGE_SEARCH_TIMEOUT",
        "image_search_limit": "FABLIT_IMAGE_SEARCH_LIMIT",
        "version": "FABLIT_VERSION",
    }
    resolved: dict[str, Any] = {}

    for field_name, env_name in env_map.items():
        value = os.getenv(env_name)
        if value is not None:
            resolved[field_name] = value

    # SPEC-036: the Pexafy dashboard documents PEXAFY_API_KEY, so accept it
    # directly when the namespaced Fablit variable is not set.
    if "image_search_api_key" not in resolved:
        pexafy_key = os.getenv("PEXAFY_API_KEY")
        if pexafy_key is not None:
            resolved["image_search_api_key"] = pexafy_key

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
