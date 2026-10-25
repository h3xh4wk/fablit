"""Gemini authoring adapter behaviour (ARCH-001).

The adapter owns provider-specific concerns behind the provider-neutral port.
These tests exercise it with an injected transport, so no real API call is
made: request construction, structured parsing, provider/model provenance,
and clean translation of configuration and provider failures.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from email.message import Message
from typing import Any

import pytest

from app.main import _build_authoring_provider
from fablit.application import (
    AuthoringGenerationRequest,
    AuthoringLlmProvider,
    AuthoringProviderConfigurationError,
    AuthoringProviderError,
    BriefDraftingRequest,
    LlmGenerationResult,
    PracticeAuthoringBrief,
    PracticeMode,
    candidate_from_provider_output,
)
from fablit.config import AppConfig
from fablit.platform.gemini_authoring_provider import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_PROVIDER_ID,
    GeminiAuthoringProvider,
    GeminiTransport,
)

API_KEY = "gemini-api-key-secret-123"


def _brief(**overrides: Any) -> PracticeAuthoringBrief:
    base: dict[str, Any] = {
        "practice_area": "Visual Analysis",
        "practice_purpose": "Practise reading structure in a composition.",
        "task": "Describe the dominant structure you notice.",
        "response_form": "A short evidence-based paragraph.",
        "primary_capability": "Observe",
        "practice_mode": PracticeMode.FULL_PRACTICE,
        "feedback_intent": "Name one strength, why it matters, and one next move.",
    }
    base.update(overrides)
    return PracticeAuthoringBrief(**base)


def _candidate_json() -> str:
    return json.dumps(
        {
            "title": "Reading Composition — Observe Practice",
            "description": "A generated practice on reading composition.",
            "contract": {
                "purpose": "Practise reading structure in a composition.",
                "task": "Describe the dominant structure you notice.",
                "expected_thinking": "Move from observation to a reasoned claim.",
                "response_contract": "A short evidence-based paragraph.",
                "evaluation_intent": "Look for evidence tied to the composition.",
                "feedback_intent": "Name one strength, why it matters, next move.",
                "reflection_intent": "Notice how you approached the reading.",
                "continuation_intent": "Try a related practice on the same move.",
            },
        }
    )


def _gemini_response(text: str) -> str:
    return json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]})


def _brief_draft_json() -> str:
    return json.dumps(
        {
            "fields": {
                "practice_area": {"value": "Visual analysis", "source": "notes"},
                "intended_mode": {
                    "value": "short-drill",
                    "source": "suggested",
                },
            },
            "assumptions": ["The learner group is Year 10."],
        }
    )


class _Transport:
    """A recording, scripted transport stand-in for the Gemini HTTP call."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, bytes, Mapping[str, str]]] = []

    def __call__(self, url: str, body: bytes, headers: Mapping[str, str]) -> str:
        self.calls.append((url, body, headers))
        return self.response


def _provider(
    transport: GeminiTransport, *, model: str = DEFAULT_GEMINI_MODEL
) -> GeminiAuthoringProvider:
    return GeminiAuthoringProvider(api_key=API_KEY, model=model, fetch=transport)


# --- Port conformance & provenance (ARCH-001) --------------------------------


def test_adapter_satisfies_the_authoring_provider_port() -> None:
    provider = _provider(_Transport(_gemini_response(_candidate_json())))
    assert isinstance(provider, AuthoringLlmProvider)
    assert provider.provider_id == GEMINI_PROVIDER_ID
    assert provider.model_id == DEFAULT_GEMINI_MODEL


def test_generate_returns_structured_result_with_provenance_and_timestamp() -> None:
    provider = _provider(_Transport(_gemini_response(_candidate_json())))

    result = provider.generate(_brief())

    assert isinstance(result, LlmGenerationResult)
    assert result.provider == GEMINI_PROVIDER_ID
    assert result.model == DEFAULT_GEMINI_MODEL
    assert result.candidate_data["title"] == "Reading Composition — Observe Practice"
    assert result.output["title"] == "Reading Composition — Observe Practice"
    assert isinstance(result.generated_at, datetime)
    assert result.generated_at.tzinfo is not None


def test_generate_candidate_returns_structured_result_with_provenance() -> None:
    provider = _provider(_Transport(_gemini_response(_candidate_json())))

    result = provider.generate_candidate(AuthoringGenerationRequest(brief=_brief()))

    assert isinstance(result, LlmGenerationResult)
    assert result.provider == GEMINI_PROVIDER_ID
    assert result.model == DEFAULT_GEMINI_MODEL
    assert result.output["title"] == "Reading Composition — Observe Practice"


def test_provider_output_flows_into_spec_032_validation() -> None:
    provider = _provider(_Transport(_gemini_response(_candidate_json())))
    result = provider.generate(_brief())

    candidate = candidate_from_provider_output(
        result.candidate_data, _brief(), provider=result.provider, model=result.model
    )

    assert candidate.validation.is_approvable is True
    assert candidate.provenance.provider == GEMINI_PROVIDER_ID
    assert candidate.provenance.model == DEFAULT_GEMINI_MODEL


def test_incomplete_provider_output_is_surfaced_to_validation() -> None:
    """Valid JSON that omits contract fields must not be silently accepted."""
    provider = _provider(
        _Transport(_gemini_response(json.dumps({"title": "Only a title"})))
    )
    result = provider.generate(_brief())

    candidate = candidate_from_provider_output(
        result.candidate_data, _brief(), provider=result.provider, model=result.model
    )

    assert candidate.validation.is_approvable is False
    assert candidate.contract is None


# --- Request construction -----------------------------------------------------


def test_request_targets_the_selected_model_and_json_response_mode() -> None:
    transport = _Transport(_gemini_response(_candidate_json()))
    provider = _provider(transport, model="gemini-2.5-pro")

    provider.generate(_brief())

    url, body, headers = transport.calls[0]
    assert url.endswith("/models/gemini-2.5-pro:generateContent")
    assert headers["Content-Type"] == "application/json"
    payload: dict[str, Any] = json.loads(body)
    assert payload["generationConfig"]["responseMimeType"] == "application/json"


def test_prompt_grounds_generation_in_the_brief_and_feedback_contract() -> None:
    transport = _Transport(_gemini_response(_candidate_json()))
    provider = _provider(transport)

    provider.generate(_brief(continuation_intent="Try an iterative follow-up move."))

    _, body, _ = transport.calls[0]
    prompt = json.loads(body)["contents"][0]["parts"][0]["text"]
    assert "Visual Analysis" in prompt
    assert "Describe the dominant structure you notice." in prompt
    assert "reflection_intent" in prompt
    assert "continuation_intent" in prompt
    assert "must not grade" in prompt


def test_prompt_marks_continuation_intent_optional_when_brief_omits_it() -> None:
    transport = _Transport(_gemini_response(_candidate_json()))
    provider = _provider(transport)

    provider.generate(_brief(continuation_intent=""))

    _, body, _ = transport.calls[0]
    prompt = json.loads(body)["contents"][0]["parts"][0]["text"]
    assert "continuation_intent" in prompt
    assert "optional" in prompt.lower()


@dataclass(frozen=True)
class _Issue129Brief:
    practice_area: str = "Visual analysis"
    learner_context: str = "A learner practising close observation."
    purpose: str = "Distinguish visible evidence from interpretation."
    intended_mode: str = "short-drill"
    response_form: str = "A short written observation."
    evaluation_intent: str = "Look for specific observable details."
    feedback_intent: str = "Identify useful evidence and one next step."
    reflection_intent: str = "Notice which observation strategy was useful."
    primary_creative_thinking_lens: str = "Observe"
    constraints: str = "Keep it concise."


def test_generate_supports_issue_129_brief_dataclass() -> None:
    transport = _Transport(_gemini_response(_candidate_json()))
    provider = _provider(transport)

    result = provider.generate(_Issue129Brief())

    assert isinstance(result, LlmGenerationResult)
    assert result.provider == GEMINI_PROVIDER_ID
    assert result.candidate_data["title"] == "Reading Composition — Observe Practice"
    _, body, _ = transport.calls[0]
    prompt = json.loads(body)["contents"][0]["parts"][0]["text"]
    assert "Distinguish visible evidence from interpretation." in prompt
    assert "Keep it concise." in prompt


def test_api_key_is_sent_as_a_header_and_never_in_the_url() -> None:
    transport = _Transport(_gemini_response(_candidate_json()))
    provider = _provider(transport)

    provider.generate(_brief())

    url, _, headers = transport.calls[0]
    assert headers["x-goog-api-key"] == API_KEY
    assert API_KEY not in url


def test_code_fenced_json_response_is_accepted() -> None:
    fenced = f"```json\n{_candidate_json()}\n```"
    provider = _provider(_Transport(_gemini_response(fenced)))

    result = provider.generate(_brief())

    assert result.output["title"] == "Reading Composition — Observe Practice"


def test_loose_json_with_surrounding_text_is_accepted() -> None:
    text_with_json = f"Here is the candidate:\n{_candidate_json()}\nHope that helps!"
    provider = _provider(_Transport(_gemini_response(text_with_json)))

    result = provider.generate(_brief())

    assert result.output["title"] == "Reading Composition — Observe Practice"


# --- Configuration failures (ARCH-001) ---------------------------------------


@pytest.mark.parametrize("api_key", ["", "   "])
def test_missing_api_key_is_a_configuration_error(api_key: str) -> None:
    with pytest.raises(AuthoringProviderConfigurationError, match="API key"):
        GeminiAuthoringProvider(api_key=api_key)


@pytest.mark.parametrize("model", ["", "   "])
def test_missing_model_is_a_configuration_error(model: str) -> None:
    with pytest.raises(AuthoringProviderConfigurationError, match="model"):
        GeminiAuthoringProvider(api_key=API_KEY, model=model)


# --- Provider failures (ARCH-001) --------------------------------------------


def _raising_fetch(exc: Exception) -> Callable[[str, bytes, Mapping[str, str]], str]:
    def call(url: str, body: bytes, headers: Mapping[str, str]) -> str:
        raise exc

    return call


def test_network_failure_becomes_a_provider_error() -> None:
    provider = _provider(_raising_fetch(OSError("connection refused")))

    with pytest.raises(AuthoringProviderError):
        provider.generate(_brief())


def test_http_error_status_becomes_a_provider_error() -> None:
    http_error = urllib.error.HTTPError(
        "https://example.invalid", 429, "Too Many Requests", Message(), None
    )
    provider = _provider(_raising_fetch(http_error))

    with pytest.raises(AuthoringProviderError, match="429"):
        provider.generate(_brief())


@pytest.mark.parametrize(
    "response",
    [
        "not json at all",
        json.dumps({"candidates": []}),
        json.dumps({"candidates": [{"content": {"parts": [{"text": ""}]}}]}),
        json.dumps([1, 2, 3]),
    ],
)
def test_unusable_provider_response_becomes_a_provider_error(
    response: str,
) -> None:
    provider = _provider(_Transport(response))

    with pytest.raises(AuthoringProviderError):
        provider.generate(_brief())


def test_provider_errors_never_leak_the_api_key() -> None:
    provider = _provider(_raising_fetch(OSError(f"failed with {API_KEY}")))

    with pytest.raises(AuthoringProviderError) as excinfo:
        provider.generate(_brief())

    assert API_KEY not in str(excinfo.value)


def test_http_error_body_is_not_surfaced() -> None:
    http_error = urllib.error.HTTPError(
        "https://example.invalid",
        500,
        "Sensitive internal connection detail",
        Message(),
        None,
    )
    provider = _provider(_raising_fetch(http_error))

    with pytest.raises(AuthoringProviderError) as excinfo:
        provider.generate(_brief())

    assert "Sensitive" not in str(
        excinfo.value
    )  # --- Brief drafting (SPEC-040) ------------------------------------------------


def test_draft_brief_returns_the_structured_mapping_and_builds_the_request() -> None:
    transport = _Transport(_gemini_response(_brief_draft_json()))
    provider = _provider(transport)
    request = BriefDraftingRequest(
        notes="Year 10 compared two posters.",
        current_values={"purpose": "Notice evidence."},
    )

    output = provider.draft_brief(request)

    assert output["fields"]["practice_area"]["value"] == "Visual analysis"
    assert output["assumptions"] == ["The learner group is Year 10."]

    url, body, headers = transport.calls[0]
    assert url.endswith(":generateContent")
    assert API_KEY not in url
    assert headers["x-goog-api-key"] == API_KEY
    payload = json.loads(body)
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    prompt = payload["contents"][0]["parts"][0]["text"]
    # Notes are delimited as untrusted data, never as instructions.
    assert "Year 10 compared two posters." in prompt
    assert "untrusted data" in prompt
    # The prompt states the existing allowed values and the provenance shape.
    assert "short-drill" in prompt and "full-practice" in prompt
    assert "Observe" in prompt
    assert '"source"' in prompt
    # The current brief is offered as context for a coherent draft.
    assert "Notice evidence." in prompt


def test_draft_brief_asks_only_for_the_target_field_on_regeneration() -> None:
    transport = _Transport(_gemini_response(_brief_draft_json()))
    provider = _provider(transport)

    provider.draft_brief(
        BriefDraftingRequest(notes="notes", target_field="feedback_intent")
    )

    prompt = json.loads(transport.calls[0][1])["contents"][0]["parts"][0]["text"]
    assert "Only propose a new value for feedback_intent" in prompt


def test_draft_brief_translates_provider_failure_without_leaking_details() -> None:
    http_error = urllib.error.HTTPError(
        "https://example.invalid", 500, f"Sensitive {API_KEY}", Message(), None
    )
    provider = _provider(_raising_fetch(http_error))

    with pytest.raises(AuthoringProviderError) as excinfo:
        provider.draft_brief(BriefDraftingRequest(notes="notes"))

    assert API_KEY not in str(excinfo.value)
    assert "Sensitive" not in str(excinfo.value)


@pytest.mark.parametrize(
    "response",
    [
        "not json at all",
        json.dumps({"candidates": []}),
        json.dumps({"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}),
    ],
)
def test_draft_brief_refuses_an_unusable_provider_response(response: str) -> None:
    provider = _provider(_Transport(response))

    with pytest.raises(AuthoringProviderError):
        provider.draft_brief(BriefDraftingRequest(notes="notes"))


# --- Default transport --------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


# --- Composition root wiring (ARCH-001) --------------------------------------


def test_composition_root_builds_gemini_when_a_key_is_configured() -> None:
    provider = _build_authoring_provider(
        AppConfig.model_validate(
            {
                "ai_provider_api_key": API_KEY,
                "ai_provider_model": "gemini-2.5-pro",
            }
        )
    )

    assert isinstance(provider, GeminiAuthoringProvider)
    assert provider.model_id == "gemini-2.5-pro"


def test_composition_root_returns_no_provider_without_a_key() -> None:
    assert _build_authoring_provider(AppConfig.model_validate({})) is None


# --- Default transport --------------------------------------------------------


def test_default_transport_posts_with_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[urllib.request.Request] = []

    def fake_urlopen(
        request: urllib.request.Request, timeout: float | None = None
    ) -> _FakeResponse:
        captured.append(request)
        return _FakeResponse(_gemini_response(_candidate_json()))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = GeminiAuthoringProvider(api_key=API_KEY)

    result = provider.generate(_brief())

    assert result.output["title"] == "Reading Composition — Observe Practice"
    sent = captured[0]
    assert sent.get_method() == "POST"
    lowered = {key.lower(): value for key, value in sent.headers.items()}
    assert lowered["x-goog-api-key"] == API_KEY
