"""Provider-neutral LLM boundary for AI-assisted practice authoring (ARCH-001).

SPEC-032's authoring workflow must be able to ask an AI provider for a
structured practice candidate without becoming coupled to a specific vendor.
This module owns that boundary — the smallest representation the workflow
needs:

- :class:`AuthoringGenerationRequest` — what the workflow asks the provider
  for (today, the structured authoring brief).
- :class:`LlmGenerationResult` — the structured generation result plus the
  provider/model metadata SPEC-032 retains for provenance and traceability.
- :class:`AuthoringLlmProvider` — the port. The workflow depends on this
  protocol, never on a concrete provider SDK.
- :class:`FakeAuthoringProvider` — a deterministic in-process test double so
  the automated suite exercises the workflow without any external API call.

Dependency direction (ARCH-001):

    Authoring workflow -> AuthoringLlmProvider (port) -> concrete adapter

Provider-specific concerns (credentials, request construction, response
parsing, provider errors, provider/model identity) live entirely in the
concrete adapter. This module imports no provider SDK and no credential
storage, so the boundary stays server-side and compatible with SEC-001.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .authoring import PracticeAuthoringBrief
from .errors import AuthoringProviderError


@dataclass(frozen=True)
class AuthoringGenerationRequest:
    """The workflow's provider-neutral request for a practice candidate.

    Carries the structured authoring brief (SPEC-032 §4): the adapter turns
    it into whatever prompt/request shape its provider needs.
    """

    brief: PracticeAuthoringBrief

    def as_payload(self) -> dict[str, Any]:
        """Return a JSON-safe view of the brief for adapter request building."""
        return self.brief.as_dict()


@dataclass(frozen=True)
class LlmGenerationResult:
    """A structured generation result with its provider/model identity.

    ``output`` is the provider's structured candidate content in the shape
    :func:`fablit.application.authoring.candidate_from_provider_output`
    understands, so SPEC-032 can validate it against the Practice Content
    Contract. ``provider`` and ``model`` are retained for SPEC-032 §10
    provenance.
    """

    output: Mapping[str, Any]
    provider: str
    model: str

    def __post_init__(self) -> None:
        for name in ("provider", "model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise AuthoringProviderError(
                    f"generation result {name!r} must be non-blank text, got {value!r}"
                )


@runtime_checkable
class AuthoringLlmProvider(Protocol):
    """Provider-neutral LLM port for the SPEC-032 authoring workflow.

    Implementations own provider-specific concerns: credentials, API request
    construction, response parsing, and provider error translation. They must
    translate any provider failure into :class:`AuthoringProviderError` so the
    workflow never depends on a vendor SDK's exception types.
    """

    @property
    def provider_id(self) -> str:
        """Stable provider identifier retained for authoring provenance."""
        ...

    @property
    def model_id(self) -> str:
        """Provider model identifier retained for authoring provenance."""
        ...

    def generate_candidate(
        self, request: AuthoringGenerationRequest
    ) -> LlmGenerationResult:
        """Generate a structured candidate for the given brief.

        Raises:
            AuthoringProviderError: When the provider is unavailable, the
                response is unusable, or the provider cannot be reached. The
                workflow treats this as a safe failure and creates no
                learner-facing content.
        """
        ...


class FakeAuthoringProvider:
    """Deterministic in-process provider for tests (ARCH-001).

    Never performs network I/O and returns the supplied structured ``output``
    for every request, so the automated suite exercises the authoring
    workflow end to end without real external API calls. An ``error`` may be
    injected to exercise provider-failure handling.
    """

    def __init__(
        self,
        output: Mapping[str, Any] | None = None,
        *,
        provider: str = "fake-authoring",
        model: str = "fake-model",
        error: Exception | None = None,
    ) -> None:
        self._output: dict[str, Any] = dict(output or {})
        self._provider = provider
        self._model = model
        self._error = error
        self.calls: list[AuthoringGenerationRequest] = []

    @property
    def provider_id(self) -> str:
        return self._provider

    @property
    def model_id(self) -> str:
        return self._model

    def generate_candidate(
        self, request: AuthoringGenerationRequest
    ) -> LlmGenerationResult:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        return LlmGenerationResult(
            output=dict(self._output),
            provider=self._provider,
            model=self._model,
        )
