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


# --- Artifact storage backend (SPEC-034) --------------------------------------


def test_artifact_storage_backend_defaults_to_file() -> None:
    config = AppConfig.model_validate({})

    assert config.artifact_storage_backend == "file"
    assert config.artifact_storage_bucket is None
    assert config.artifact_storage_dir is None


def test_artifact_storage_backend_accepts_file() -> None:
    config = AppConfig.model_validate({"artifact_storage_backend": "file"})

    assert config.artifact_storage_backend == "file"


def test_artifact_storage_backend_accepts_gcs_with_bucket() -> None:
    config = AppConfig.model_validate(
        {
            "artifact_storage_backend": "gcs",
            "artifact_storage_bucket": "my-bucket",
        }
    )

    assert config.artifact_storage_backend == "gcs"
    assert config.artifact_storage_bucket == "my-bucket"


def test_artifact_storage_backend_is_normalised_to_lowercase() -> None:
    config = AppConfig.model_validate(
        {
            "artifact_storage_backend": "  GCS ",
            "artifact_storage_bucket": "my-bucket",
        }
    )

    assert config.artifact_storage_backend == "gcs"


def test_unsupported_artifact_storage_backend_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_ARTIFACT_STORAGE_BACKEND", "s3")

    with pytest.raises(ConfigValidationError, match="artifact storage backend"):
        load_config()


def test_gcs_backend_without_bucket_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="artifact_storage_bucket is required"):
        AppConfig.model_validate({"artifact_storage_backend": "gcs"})


def test_gcs_backend_with_empty_bucket_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="artifact_storage_bucket is required"):
        AppConfig.model_validate(
            {
                "artifact_storage_backend": "gcs",
                "artifact_storage_bucket": "   ",
            }
        )


def test_artifact_storage_backend_and_bucket_read_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_ARTIFACT_STORAGE_BACKEND", "gcs")
    monkeypatch.setenv("FABLIT_ARTIFACT_STORAGE_BUCKET", "prod-artifacts-bucket")

    config = load_config()

    assert config.artifact_storage_backend == "gcs"
    assert config.artifact_storage_bucket == "prod-artifacts-bucket"


def test_artifact_storage_dir_reads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_ARTIFACT_STORAGE_DIR", "/custom/storage/path")

    config = load_config()

    assert config.artifact_storage_dir == "/custom/storage/path"


def test_authoring_secret_and_ai_provider_defaults_to_none() -> None:
    config = AppConfig.model_validate({})
    assert config.authoring_secret is None
    assert config.ai_provider_api_key is None


def test_authoring_secret_and_ai_provider_read_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_AUTHORING_SECRET", "super-secret-key-123")
    monkeypatch.setenv("FABLIT_AI_PROVIDER_API_KEY", "ai-key-xyz")

    config = load_config()

    assert config.authoring_secret == "super-secret-key-123"
    assert config.ai_provider_api_key == "ai-key-xyz"


def test_authoring_secret_and_ai_provider_whitespace_normalized_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_AUTHORING_SECRET", "   ")
    monkeypatch.setenv("FABLIT_AI_PROVIDER_API_KEY", " \t\n ")

    config = load_config()

    assert config.authoring_secret is None
    assert config.ai_provider_api_key is None


def test_ai_provider_model_defaults_to_gemini() -> None:
    config = AppConfig.model_validate({})
    assert config.ai_provider_model == "gemini-2.5-flash"


def test_ai_provider_model_reads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_AI_PROVIDER_MODEL", "gemini-2.5-pro")

    config = load_config()

    assert config.ai_provider_model == "gemini-2.5-pro"


def test_ai_provider_model_blank_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_AI_PROVIDER_MODEL", "   ")

    config = load_config()

    assert config.ai_provider_model == "gemini-2.5-flash"


def test_authoring_candidate_store_defaults_to_memory() -> None:
    config = AppConfig.model_validate({})
    assert config.authoring_candidate_store == "memory"
    assert config.authoring_candidate_retention_days == 30


def test_authoring_candidate_store_accepts_datastore() -> None:
    config = AppConfig.model_validate({"authoring_candidate_store": "datastore"})
    assert config.authoring_candidate_store == "datastore"


def test_authoring_candidate_store_normalised_to_lowercase() -> None:
    config = AppConfig.model_validate({"authoring_candidate_store": "  DATASTORE "})
    assert config.authoring_candidate_store == "datastore"


def test_authoring_candidate_store_unsupported_raises() -> None:
    with pytest.raises(ValidationError, match="Unsupported authoring candidate store"):
        AppConfig.model_validate({"authoring_candidate_store": "redis"})


def test_authoring_candidate_store_and_retention_read_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_AUTHORING_CANDIDATE_STORE", "datastore")
    monkeypatch.setenv("FABLIT_AUTHORING_CANDIDATE_RETENTION_DAYS", "45")

    config = load_config()

    assert config.authoring_candidate_store == "datastore"
    assert config.authoring_candidate_retention_days == 45


def test_published_practice_store_defaults_to_memory() -> None:
    config = AppConfig.model_validate({})
    assert config.published_practice_store == "memory"


def test_published_practice_store_accepts_datastore() -> None:
    config = AppConfig.model_validate({"published_practice_store": "datastore"})
    assert config.published_practice_store == "datastore"


def test_published_practice_store_normalised_to_lowercase() -> None:
    config = AppConfig.model_validate({"published_practice_store": "  DATASTORE "})
    assert config.published_practice_store == "datastore"


def test_published_practice_store_unsupported_raises() -> None:
    with pytest.raises(ValidationError, match="Unsupported published practice store"):
        AppConfig.model_validate({"published_practice_store": "redis"})


def test_published_practice_store_reads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_PUBLISHED_PRACTICE_STORE", "datastore")

    config = load_config()

    assert config.published_practice_store == "datastore"


# --- Curated news feed (SPEC-041) --------------------------------------------


def test_news_repository_defaults_to_memory() -> None:
    config = AppConfig.model_validate({})

    assert config.news_repository == "memory"
    assert [source.name for source in config.news_sources] == [
        "The Guardian — Fashion",
        "The Guardian — Art & Design",
    ]
    assert config.news_max_items_per_source == 6
    assert config.news_freshness_days == 14
    assert config.news_max_summary_chars == 600
    assert config.news_relevance_threshold == 0.5
    assert config.news_fetch_timeout == 10.0
    assert config.news_max_response_bytes == 512_000


def test_news_repository_accepts_datastore() -> None:
    config = AppConfig.model_validate({"news_repository": "  DATASTORE "})

    assert config.news_repository == "datastore"


def test_unsupported_news_repository_raises() -> None:
    with pytest.raises(ValidationError, match="Unsupported news repository"):
        AppConfig.model_validate({"news_repository": "sqlite"})


# --- Private story responses (SPEC-044) --------------------------------------


def test_story_response_repository_defaults_to_memory() -> None:
    config = AppConfig.model_validate({})

    assert config.story_response_repository == "memory"


def test_story_response_repository_accepts_datastore() -> None:
    config = AppConfig.model_validate({"story_response_repository": "  DATASTORE "})

    assert config.story_response_repository == "datastore"


def test_story_response_repository_reads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_STORY_RESPONSE_REPOSITORY", "datastore")

    config = load_config()

    assert config.story_response_repository == "datastore"


def test_unsupported_story_response_repository_raises() -> None:
    with pytest.raises(ValidationError, match="Unsupported story response"):
        AppConfig.model_validate({"story_response_repository": "sqlite"})


# --- Private requested practices (SPEC-044) ----------------------------------


def test_generated_practice_repository_defaults_to_memory() -> None:
    config = AppConfig.model_validate({})

    assert config.generated_practice_repository == "memory"


def test_generated_practice_repository_accepts_datastore() -> None:
    config = AppConfig.model_validate({"generated_practice_repository": "  DATASTORE "})

    assert config.generated_practice_repository == "datastore"


def test_generated_practice_repository_reads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_GENERATED_PRACTICE_REPOSITORY", "datastore")

    config = load_config()

    assert config.generated_practice_repository == "datastore"


def test_unsupported_generated_practice_repository_raises() -> None:
    with pytest.raises(ValidationError, match="Unsupported generated practice"):
        AppConfig.model_validate({"generated_practice_repository": "sqlite"})


def test_learner_practice_rate_limit_defaults_and_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default_config = AppConfig.model_validate({})
    assert default_config.learner_practice_rate_limit == 5
    assert default_config.learner_practice_rate_window_seconds == 3600
    assert default_config.learner_practice_claim_ttl_seconds == 60
    assert default_config.learner_practice_max_output_tokens == 4096
    assert default_config.learner_practice_max_response_bytes == 65_536

    monkeypatch.setenv("FABLIT_LEARNER_PRACTICE_RATE_LIMIT", "3")
    monkeypatch.setenv("FABLIT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS", "1800")
    monkeypatch.setenv("FABLIT_LEARNER_PRACTICE_CLAIM_TTL_SECONDS", "120")
    monkeypatch.setenv("FABLIT_LEARNER_PRACTICE_MAX_OUTPUT_TOKENS", "1536")
    monkeypatch.setenv("FABLIT_LEARNER_PRACTICE_MAX_RESPONSE_BYTES", "32768")

    overridden = load_config()

    assert overridden.learner_practice_rate_limit == 3
    assert overridden.learner_practice_rate_window_seconds == 1800
    assert overridden.learner_practice_claim_ttl_seconds == 120
    assert overridden.learner_practice_max_output_tokens == 1536
    assert overridden.learner_practice_max_response_bytes == 32_768


@pytest.mark.parametrize(
    "overrides",
    [
        {"learner_practice_rate_limit": 0},
        {"learner_practice_rate_limit": 101},
        {"learner_practice_rate_window_seconds": 0},
        {"learner_practice_rate_window_seconds": 86_401},
        {"learner_practice_claim_ttl_seconds": 4},
        {"learner_practice_claim_ttl_seconds": 601},
        {"learner_practice_max_output_tokens": 127},
        {"learner_practice_max_output_tokens": 8193},
        {"learner_practice_max_response_bytes": 1023},
        {"learner_practice_max_response_bytes": 1_048_577},
    ],
)
def test_learner_practice_rate_limit_validates_bounds(
    overrides: dict[str, int],
) -> None:
    with pytest.raises(ValidationError):
        AppConfig.model_validate(overrides)


def test_news_sources_parse_from_json_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FABLIT_NEWS_SOURCES",
        json.dumps(
            [
                {
                    "name": "Daily Weave",
                    "feed_url": "https://news.example.com/rss",
                    "site_url": "https://news.example.com",
                }
            ]
        ),
    )

    config = load_config()

    assert len(config.news_sources) == 1
    assert config.news_sources[0].name == "Daily Weave"
    assert config.news_sources[0].feed_url == "https://news.example.com/rss"
    assert config.news_sources[0].publisher_host == "news.example.com"


def test_invalid_news_sources_raise_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_NEWS_SOURCES", '[{"name": "Bad"}]')

    with pytest.raises(ConfigValidationError, match="news source"):
        load_config()


def test_news_limits_read_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FABLIT_NEWS_MAX_ITEMS_PER_SOURCE", "3")
    monkeypatch.setenv("FABLIT_NEWS_FRESHNESS_DAYS", "7")
    monkeypatch.setenv("FABLIT_NEWS_MAX_SUMMARY_CHARS", "500")
    monkeypatch.setenv("FABLIT_NEWS_RELEVANCE_THRESHOLD", "0.7")
    monkeypatch.setenv("FABLIT_NEWS_FETCH_TIMEOUT", "4.5")
    monkeypatch.setenv("FABLIT_NEWS_MAX_RESPONSE_BYTES", "2048")

    config = load_config()

    assert config.news_max_items_per_source == 3
    assert config.news_freshness_days == 7
    assert config.news_max_summary_chars == 500
    assert config.news_relevance_threshold == 0.7
    assert config.news_fetch_timeout == 4.5
    assert config.news_max_response_bytes == 2048
