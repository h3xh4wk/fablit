"""Concrete Google Gemini adapter for the authoring LLM port (ARCH-001).

This is the initial concrete implementation of the provider-neutral
:class:`~fablit.application.authoring_llm.AuthoringLlmProvider` port used by
SPEC-032. It owns everything provider-specific:

- credential handling (the API key never leaves this module and is never
  written to logs or error messages);
- API request construction (the structured authoring brief becomes a
  Gemini ``generateContent`` request that asks for JSON output);
- response parsing (the model's JSON text becomes the structured generation
  result SPEC-032 validates);
- provider/model identity for authoring provenance; and
- failure translation (network, HTTP, and unusable-response failures become
  :class:`~fablit.application.errors.AuthoringProviderError`).

The adapter targets the Gemini REST API using the standard library, so it
introduces no SDK dependency and injects its transport (``fetch``) for
deterministic tests. Swapping in an SDK-backed adapter later needs no change
to the authoring workflow, which depends only on the port.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, Final

from fablit.application.authoring_llm import (
    AuthoringGenerationRequest,
    LlmGenerationResult,
)
from fablit.application.errors import (
    AuthoringProviderConfigurationError,
    AuthoringProviderError,
)

logger = logging.getLogger("fablit.authoring.gemini")

#: Stable provider identifier retained for SPEC-032 §10 provenance.
GEMINI_PROVIDER_ID: Final[str] = "google-gemini"

#: Default Gemini model used when configuration does not choose one.
DEFAULT_GEMINI_MODEL: Final[str] = "gemini-2.5-flash"

#: Default Gemini REST API base endpoint.
DEFAULT_GEMINI_ENDPOINT: Final[str] = "https://generativelanguage.googleapis.com/v1beta"

#: Transport signature: ``(url, body_bytes, headers) -> response_text``.
#: Injectable so tests can exercise the adapter without network access.
GeminiTransport = Callable[[str, bytes, Mapping[str, str]], str]

#: The SPEC-029 contract fields the adapter asks the model to populate.
_CONTRACT_FIELDS: Final[tuple[str, ...]] = (
    "purpose",
    "task",
    "expected_thinking",
    "response_contract",
    "evaluation_intent",
    "feedback_intent",
    "reflection_intent",
    "continuation_intent",
)

#: A single generic message so no provider detail can leak to clients.
_UNAVAILABLE_MESSAGE = "the AI provider is unavailable"


class GeminiAuthoringProvider:
    """Gemini-backed adapter for the authoring LLM port (ARCH-001).

    Constructed with the server-side API key only; the key is held privately
    and sent as an ``x-goog-api-key`` header so it never appears in a URL,
    log line, or client response (SPEC-032 §16, SEC-001).
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        endpoint: str = DEFAULT_GEMINI_ENDPOINT,
        timeout: float = 30.0,
        fetch: GeminiTransport | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise AuthoringProviderConfigurationError(
                "the Gemini authoring provider requires a non-blank API key"
            )
        if not isinstance(model, str) or not model.strip():
            raise AuthoringProviderConfigurationError(
                "the Gemini authoring provider requires a non-blank model name"
            )
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._endpoint = endpoint.rstrip("/")
        self._timeout = timeout
        self._fetch: GeminiTransport = fetch or self._default_fetch

    @property
    def provider_id(self) -> str:
        return GEMINI_PROVIDER_ID

    @property
    def model_id(self) -> str:
        return self._model

    def generate_candidate(
        self, request: AuthoringGenerationRequest
    ) -> LlmGenerationResult:
        """Ask Gemini for a structured candidate and parse its JSON response."""
        url = f"{self._endpoint}/models/{self._model}:generateContent"
        body = json.dumps(self._build_payload(request)).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }
        try:
            payload = self._fetch(url, body, headers)
        except AuthoringProviderError:
            raise
        except urllib.error.HTTPError as exc:
            # A non-2xx status is a provider failure; never surface the body
            # (it can echo request details) or the status text to clients.
            raise AuthoringProviderError(
                f"{_UNAVAILABLE_MESSAGE} (status {exc.code})"
            ) from exc
        except Exception as exc:  # network errors, timeouts, unexpected failures
            raise AuthoringProviderError(_UNAVAILABLE_MESSAGE) from exc

        output = self._parse_response(payload)
        return LlmGenerationResult(
            output=output,
            provider=self.provider_id,
            model=self.model_id,
        )

    def _default_fetch(self, url: str, body: bytes, headers: Mapping[str, str]) -> str:
        request = urllib.request.Request(
            url,
            data=body,
            headers=dict(headers),
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            payload: bytes = response.read()
        return payload.decode("utf-8")

    def _build_payload(self, request: AuthoringGenerationRequest) -> dict[str, Any]:
        """Build the Gemini ``generateContent`` request body (SPEC-032 §5, §6)."""
        return {
            "contents": [{"parts": [{"text": self._build_prompt(request)}]}],
            "generationConfig": {
                # Ask for machine-readable output so the result can be
                # validated against the Practice Content Contract (§7).
                "responseMimeType": "application/json",
                "temperature": 0.4,
            },
        }

    def _build_prompt(self, request: AuthoringGenerationRequest) -> str:
        """Turn the structured authoring brief into a contract-led prompt.

        Generation is guided by the Practice Content Contract rather than
        free-form prompting alone (AA-002), and the prompt states the SPEC-030
        feedback boundary so generated guidance stays grounded (AA-003).
        """
        brief = request.as_payload()
        contract_fields = ", ".join(_CONTRACT_FIELDS)
        lines = [
            "You are drafting one candidate practice for Fablit's curated "
            "library. A human author reviews and approves every candidate, so "
            "return a complete draft, not commentary.",
            "",
            "Authoring brief:",
            f"- practice area: {brief['practice_area']}",
            f"- practice purpose: {brief['practice_purpose']}",
            f"- learner task: {brief['task']}",
            f"- response form: {brief['response_form']}",
            f"- primary thinking lens: {brief['primary_capability']}",
            f"- practice mode: {brief['practice_mode']}",
        ]
        optional = (
            ("learner context", brief["learner_context"]),
            ("expected thinking", brief["expected_thinking"]),
            ("evaluation intent", brief["evaluation_intent"]),
            ("feedback intent", brief["feedback_intent"]),
            ("reflection intent", brief["reflection_intent"]),
            ("continuation intent", brief["continuation_intent"]),
            ("examination context", brief["examination_context"]),
            ("secondary thinking lens", brief["secondary_capability"]),
            ("stimulus requirements", brief["stimulus_requirements"]),
        )
        for label, value in optional:
            if isinstance(value, str) and value.strip():
                lines.append(f"- {label}: {value}")
        constraints = brief["constraints"]
        if constraints:
            lines.append(f"- constraints: {'; '.join(constraints)}")
        lines += [
            "",
            "Return a single JSON object with exactly these keys:",
            '- "title": a short learner-facing title;',
            '- "description": a learner-facing description of the practice;',
            '- "contract": an object with the keys '
            f"{contract_fields}, each a non-blank string grounded in the "
            "brief above.",
            "",
            "The evaluation and feedback guidance must stay evidence-based and "
            "must not grade, score, rank, or label the learner, infer ability, "
            "motivation, or effort, or claim mastery. Where examination "
            "context is given, explain the thinking it demands rather than "
            "relying on the exam name alone. Return JSON only.",
        ]
        return "\n".join(lines)

    def _parse_response(self, payload: str) -> Mapping[str, Any]:
        """Extract the structured candidate object from a Gemini response.

        A response that cannot be read as the requested JSON object is treated
        as a provider failure, so the workflow produces no candidate. Output
        that is valid JSON but incomplete is returned as-is; SPEC-032
        validation then keeps it out of the approval path (§7, §17).
        """
        try:
            data = json.loads(payload)
        except (ValueError, TypeError) as exc:
            raise AuthoringProviderError(
                f"{_UNAVAILABLE_MESSAGE} (unreadable response)"
            ) from exc
        if not isinstance(data, Mapping):
            raise AuthoringProviderError(
                f"{_UNAVAILABLE_MESSAGE} (unexpected response shape)"
            )

        text = _candidate_text(data)
        if not text:
            raise AuthoringProviderError(
                f"{_UNAVAILABLE_MESSAGE} (no candidate content)"
            )

        try:
            output = json.loads(_strip_code_fence(text))
        except (ValueError, TypeError) as exc:
            raise AuthoringProviderError(
                f"{_UNAVAILABLE_MESSAGE} (unreadable candidate)"
            ) from exc
        if not isinstance(output, Mapping):
            raise AuthoringProviderError(
                f"{_UNAVAILABLE_MESSAGE} (unexpected candidate shape)"
            )
        return output


def _candidate_text(data: Mapping[str, Any]) -> str:
    """Join the text parts of the first candidate, if any."""
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    first = candidates[0]
    if not isinstance(first, Mapping):
        return ""
    content = first.get("content")
    if not isinstance(content, Mapping):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    chunks = [
        part["text"]
        for part in parts
        if isinstance(part, Mapping) and isinstance(part.get("text"), str)
    ]
    return "".join(chunks).strip()


def _strip_code_fence(text: str) -> str:
    """Drop a Markdown code fence if the model wrapped its JSON despite the
    ``application/json`` request."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[-1].strip().startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return stripped
