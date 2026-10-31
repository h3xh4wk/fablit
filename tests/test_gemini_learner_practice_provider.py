"""Gemini adapter behaviour for learner-requested practice (SPEC-044 §8.1).

The adapter sits behind the provider-neutral generation port and is exercised
with an injected transport, so no real API call is made: request construction,
structured parsing, provenance, and clean failure translation.
"""

from __future__ import annotations

import json
import urllib.error
from collections.abc import Mapping
from datetime import UTC, datetime
from email.message import Message
from typing import Any
from uuid import uuid4

import pytest

from app.main import _build_learner_practice_generator
from fablit.application import (
    ChallengePreference,
    HistoryContext,
    LearnerPracticeGenerationError,
    LearnerPracticeGenerationRequest,
    LearnerPracticeGenerator,
    PracticeArea,
    PracticeRequest,
)
from fablit.application.errors import AuthoringProviderConfigurationError
from fablit.config import AppConfig
from fablit.platform.gemini_learner_practice_provider import (
    DEFAULT_GEMINI_ENDPOINT,
    DEFAULT_GEMINI_MODEL,
    GEMINI_LEARNER_PROVIDER_ID,
    GeminiLearnerPracticeProvider,
    GeminiTransport,
)

API_KEY = "gemini-learner-key-secret-456"
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _request(**overrides: Any) -> PracticeRequest:
    values: dict[str, Any] = {
        "learner_id": uuid4(),
        "text": "Practise noticing how colour and texture work together.",
        "area": PracticeArea.VISUAL_ANALYSIS,
        "response_form": "A short written response",
        "challenge": ChallengePreference.FAMILIAR,
        "include_history": False,
        "created_at": NOW,
        "token": uuid4(),
    }
    values.update(overrides)
    return PracticeRequest(**values)


def _generation_request(
    *,
    history: HistoryContext | None = None,
    **overrides: Any,
) -> LearnerPracticeGenerationRequest:
    return LearnerPracticeGenerationRequest(
        request=_request(**overrides),
        history=history or HistoryContext(),
    )


def _candidate_json() -> str:
    return json.dumps(
        {
            "title": "A focused practice: visual analysis",
            "description": "A short practice made for your request.",
            "contract": {
                "purpose": "Practise noticing how colour and texture work together.",
                "task": "Describe one outfit detail and what it shows you.",
                "expected_thinking": "Move from observation to a specific claim.",
                "response_contract": "A short written response.",
                "evaluation_intent": "Look for a specific, relevant observation.",
                "feedback_intent": "Name one strength and one useful next move.",
                "reflection_intent": "Notice what you would try differently.",
                "continuation_intent": "Carry the same move into another example.",
            },
        }
    )


def _gemini_response(text: str) -> str:
    return json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]})


def _http_error(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://example.invalid", status, "error", hdrs=Message(), fp=None
    )


def _provider(
    fetch: GeminiTransport | None = None, **overrides: Any
) -> GeminiLearnerPracticeProvider:
    return GeminiLearnerPracticeProvider(
        api_key=API_KEY,
        fetch=fetch,
        retry_backoff_seconds=0.0,
        **overrides,
    )


def test_adapter_satisfies_the_generation_port() -> None:
    provider = _provider()

    assert isinstance(provider, LearnerPracticeGenerator)
    assert provider.provider_id == GEMINI_LEARNER_PROVIDER_ID
    assert provider.model_id == DEFAULT_GEMINI_MODEL


def test_generate_returns_structured_output_with_safe_provenance() -> None:
    provider = _provider(
        lambda _url, _body, _headers: _gemini_response(_candidate_json())
    )

    result = provider.generate(_generation_request())

    assert result.candidate_data["title"] == "A focused practice: visual analysis"
    assert result.provider == GEMINI_LEARNER_PROVIDER_ID
    assert result.model == DEFAULT_GEMINI_MODEL
    assert result.generated_at.tzinfo is not None


def test_request_targets_the_model_and_json_response_mode() -> None:
    captured: list[tuple[str, dict[str, Any]]] = []

    def fetch(url: str, body: bytes, _headers: Mapping[str, str]) -> str:
        captured.append((url, json.loads(body)))
        return _gemini_response(_candidate_json())

    _provider(fetch).generate(_generation_request())

    url, payload = captured[0]
    assert (
        url
        == f"{DEFAULT_GEMINI_ENDPOINT}/models/{DEFAULT_GEMINI_MODEL}:generateContent"
    )
    assert payload["generationConfig"]["responseMimeType"] == "application/json"


def test_api_key_is_a_header_and_never_part_of_the_url() -> None:
    captured: list[tuple[str, Mapping[str, str]]] = []

    def fetch(url: str, _body: bytes, headers: Mapping[str, str]) -> str:
        captured.append((url, headers))
        return _gemini_response(_candidate_json())

    _provider(fetch).generate(_generation_request())

    url, headers = captured[0]
    assert headers["x-goog-api-key"] == API_KEY
    assert API_KEY not in url


def test_the_prompt_carries_the_request_and_preferences() -> None:
    captured: list[str] = []

    def fetch(_url: str, body: bytes, _headers: Mapping[str, str]) -> str:
        captured.append(json.loads(body)["contents"][0]["parts"][0]["text"])
        return _gemini_response(_candidate_json())

    _provider(fetch).generate(
        _generation_request(
            text="I want to describe a sari's texture.",
            examination_context="A portfolio interview next month",
            challenge=ChallengePreference.MORE_CHALLENGING,
        )
    )

    prompt = captured[0]
    assert "I want to describe a sari's texture." in prompt
    assert "Visual analysis" in prompt
    assert "A short written response" in prompt
    assert "more-challenging" in prompt
    assert "A portfolio interview next month" in prompt
    assert "Do not grade" in prompt
    assert "<<<" in prompt


def test_the_prompt_includes_only_the_supplied_history_context() -> None:
    captured: list[str] = []

    def fetch(_url: str, body: bytes, _headers: Mapping[str, str]) -> str:
        captured.append(json.loads(body)["contents"][0]["parts"][0]["text"])
        return _gemini_response(_candidate_json())

    history = HistoryContext(
        recent_titles=("Reading Composition",),
        recent_areas=("Observe",),
    )
    provider = _provider(fetch)
    provider.generate(
        _generation_request(
            include_history=True,
            history=history,
        )
    )
    provider.generate(_generation_request(history=history))

    with_history, without_history = captured
    assert "Reading Composition" in with_history
    assert "recent titles" in with_history
    assert "Reading Composition" not in without_history
    assert "recent titles" not in without_history


def test_no_learner_identity_is_sent_to_the_provider() -> None:
    captured: list[bytes] = []

    def fetch(_url: str, body: bytes, _headers: Mapping[str, str]) -> str:
        captured.append(body)
        return _gemini_response(_candidate_json())

    request = _generation_request()
    _provider(fetch).generate(request)

    assert str(request.request.learner_id) not in captured[0].decode("utf-8")


def test_fenced_and_loose_json_are_both_accepted() -> None:
    fenced = "```json\n" + _candidate_json() + "\n```"
    loose = "Here you go:\n" + _candidate_json() + "\nEnjoy."

    def transport(text: str) -> GeminiTransport:
        def fetch(_url: str, _body: bytes, _headers: Mapping[str, str]) -> str:
            return _gemini_response(text)

        return fetch

    for text in (fenced, loose):
        result = _provider(transport(text)).generate(_generation_request())
        assert result.candidate_data["contract"]["task"]


@pytest.mark.parametrize("api_key", ["", "   "])
def test_a_blank_api_key_is_a_configuration_error(api_key: str) -> None:
    with pytest.raises(AuthoringProviderConfigurationError):
        GeminiLearnerPracticeProvider(api_key=api_key)


def test_a_blank_model_is_a_configuration_error() -> None:
    with pytest.raises(AuthoringProviderConfigurationError):
        GeminiLearnerPracticeProvider(api_key=API_KEY, model=" ")


def test_invalid_retry_settings_are_configuration_errors() -> None:
    with pytest.raises(AuthoringProviderConfigurationError):
        GeminiLearnerPracticeProvider(api_key=API_KEY, max_attempts=0)

    with pytest.raises(AuthoringProviderConfigurationError):
        GeminiLearnerPracticeProvider(api_key=API_KEY, retry_backoff_seconds=-1)


def test_a_network_failure_becomes_a_generation_error() -> None:
    def fetch(_url: str, _body: bytes, _headers: Mapping[str, str]) -> str:
        raise urllib.error.URLError("connection refused")

    with pytest.raises(LearnerPracticeGenerationError) as caught:
        _provider(fetch).generate(_generation_request())

    assert "unavailable" in str(caught.value)


def test_an_http_error_becomes_a_generation_error_without_the_body() -> None:
    def fetch(_url: str, _body: bytes, _headers: Mapping[str, str]) -> str:
        raise _http_error(400)

    with pytest.raises(LearnerPracticeGenerationError) as caught:
        _provider(fetch).generate(_generation_request())

    assert "status 400" in str(caught.value)


def test_transient_capacity_errors_are_retried() -> None:
    attempts: list[int] = []

    def fetch(_url: str, _body: bytes, _headers: Mapping[str, str]) -> str:
        attempts.append(1)
        if len(attempts) < 3:
            raise _http_error(503)
        return _gemini_response(_candidate_json())

    result = _provider(fetch, max_attempts=3).generate(_generation_request())

    assert len(attempts) == 3
    assert result.candidate_data["title"]


def test_retries_are_bounded() -> None:
    attempts: list[int] = []

    def fetch(_url: str, _body: bytes, _headers: Mapping[str, str]) -> str:
        attempts.append(1)
        raise _http_error(429)

    with pytest.raises(LearnerPracticeGenerationError):
        _provider(fetch, max_attempts=2).generate(_generation_request())

    assert len(attempts) == 2


def test_a_non_retryable_error_is_not_retried() -> None:
    attempts: list[int] = []

    def fetch(_url: str, _body: bytes, _headers: Mapping[str, str]) -> str:
        attempts.append(1)
        raise _http_error(403)

    with pytest.raises(LearnerPracticeGenerationError):
        _provider(fetch, max_attempts=3).generate(_generation_request())

    assert len(attempts) == 1


@pytest.mark.parametrize(
    "payload",
    [
        "not json at all",
        json.dumps({"candidates": []}),
        json.dumps({"candidates": [{"content": {"parts": [{"text": "no json"}]}}]}),
        _gemini_response("[1, 2, 3]"),
        json.dumps([]),
    ],
)
def test_unusable_provider_output_is_a_generation_error(payload: str) -> None:
    def fetch(_url: str, _body: bytes, _headers: Mapping[str, str]) -> str:
        return payload

    with pytest.raises(LearnerPracticeGenerationError):
        _provider(fetch).generate(_generation_request())


def test_errors_never_leak_the_api_key() -> None:
    def fetch(_url: str, _body: bytes, _headers: Mapping[str, str]) -> str:
        raise RuntimeError(f"transport failed using {API_KEY}")

    with pytest.raises(LearnerPracticeGenerationError) as caught:
        _provider(fetch).generate(_generation_request())

    assert API_KEY not in str(caught.value)


def test_default_transport_posts_with_the_key_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[Any] = []

    class _Response:
        def read(self) -> bytes:
            return _gemini_response(_candidate_json()).encode("utf-8")

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    def fake_urlopen(request: Any, timeout: float | None = None) -> _Response:
        captured.append(request)
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = _provider().generate(_generation_request())

    assert result.candidate_data["title"]
    sent = captured[0]
    lowered = {key.lower(): value for key, value in sent.headers.items()}
    assert lowered["x-goog-api-key"] == API_KEY


# --- Composition root --------------------------------------------------------


def test_composition_root_builds_the_generator_when_a_key_is_configured() -> None:
    generator = _build_learner_practice_generator(
        AppConfig.model_validate(
            {
                "ai_provider_api_key": API_KEY,
                "ai_provider_model": "gemini-2.5-pro",
            }
        )
    )

    assert isinstance(generator, GeminiLearnerPracticeProvider)
    assert generator.model_id == "gemini-2.5-pro"


def test_composition_root_offers_no_generator_without_a_key() -> None:
    assert _build_learner_practice_generator(AppConfig.model_validate({})) is None
