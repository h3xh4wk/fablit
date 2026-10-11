"""Provider-neutral LLM boundary for AI-assisted practice authoring (ARCH-001).

SPEC-032's authoring workflow must be able to ask an AI provider for a
structured practice candidate without becoming coupled to a specific vendor.
This module owns that boundary — the smallest representation the workflow
needs:

- :class:`AuthoringBrief` — type alias for the structured brief.
- :class:`AuthoringGenerationRequest` — what the workflow asks the provider
  for (the structured authoring brief).
- :class:`LlmGenerationResult` — the structured generation result plus the
  provider/model/timestamp metadata SPEC-032 retains for provenance.
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
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .errors import AuthoringProviderError

if TYPE_CHECKING:
    from .authoring import PracticeAuthoringBrief

    AuthoringBrief = PracticeAuthoringBrief
else:
    AuthoringBrief = Any


@dataclass(frozen=True)
class AuthoringGenerationRequest:
    """The workflow's provider-neutral request for a practice candidate.

    Carries the structured authoring brief (SPEC-032 §4): the adapter turns
    it into whatever prompt/request shape its provider needs.
    """

    brief: Any

    def as_payload(self) -> dict[str, Any]:
        """Return a JSON-safe view of the brief for adapter request building."""
        if hasattr(self.brief, "as_dict"):
            result = self.brief.as_dict()
            if isinstance(result, Mapping):
                return dict(result)
        if hasattr(self.brief, "as_payload"):
            result = self.brief.as_payload()
            if isinstance(result, Mapping):
                return dict(result)
        if is_dataclass(self.brief) and not isinstance(self.brief, type):
            return asdict(self.brief)
        if isinstance(self.brief, Mapping):
            return dict(self.brief)
        raise ValueError(f"cannot convert brief {self.brief!r} to payload")


@dataclass(frozen=True)
class LlmGenerationResult:
    """A structured generation result with its provider/model/time identity.

    ``candidate_data`` (also accessible via the legacy alias ``output``) is the
    untrusted candidate data from the provider. ``provider``, ``model``, and
    ``generated_at`` are retained for SPEC-032 §10 provenance.
    """

    candidate_data: Mapping[str, Any] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __init__(
        self,
        candidate_data: Mapping[str, Any] | None = None,
        provider: str = "",
        model: str = "",
        generated_at: datetime | None = None,
        *,
        output: Mapping[str, Any] | None = None,
    ) -> None:
        data = candidate_data if candidate_data is not None else output
        if data is None:
            data = {}
        ts = generated_at if generated_at is not None else datetime.now(UTC)
        object.__setattr__(self, "candidate_data", data)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "generated_at", ts)

        if not isinstance(data, Mapping):
            raise AuthoringProviderError(
                "generation result 'candidate_data' must be a mapping, "
                f"got {type(data).__name__}"
            )
        for name in ("provider", "model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise AuthoringProviderError(
                    f"generation result {name!r} must be non-blank text, got {value!r}"
                )
        if not isinstance(ts, datetime) or ts.tzinfo is None:
            raise AuthoringProviderError(
                "generation result 'generated_at' must be a timezone-aware datetime, "
                f"got {ts!r}"
            )

    @property
    def output(self) -> Mapping[str, Any]:
        """Backward compatibility alias for candidate_data."""
        return self.candidate_data


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

    def generate(self, brief: AuthoringBrief) -> LlmGenerationResult:
        """Generate a candidate for the given brief.

        Raises:
            AuthoringProviderError: When the provider is unavailable, the
                response is unusable, or the provider cannot be reached. The
                workflow treats this as a safe failure and creates no
                learner-facing content.
        """
        ...

    def generate_candidate(
        self, request: AuthoringGenerationRequest
    ) -> LlmGenerationResult:
        """Compatibility method accepting an AuthoringGenerationRequest wrapper."""
        ...


class FakeAuthoringProvider:
    """Deterministic in-process provider for tests (ARCH-001).

    Never performs network I/O and returns the supplied structured
    ``candidate_data`` for every request, so the automated suite exercises
    the authoring workflow end to end without real external API calls.
    An ``error`` may be injected to exercise provider-failure handling.
    """

    def __init__(
        self,
        output: Mapping[str, Any] | None = None,
        *,
        candidate_data: Mapping[str, Any] | None = None,
        provider: str = "fake-authoring",
        model: str = "fake-model",
        error: Exception | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        raw_data = candidate_data if candidate_data is not None else output
        self._candidate_data: dict[str, Any] = dict(raw_data or {})
        self._provider = provider
        self._model = model
        self._error = error
        self._generated_at = generated_at or datetime.now(UTC)
        self.calls: list[Any] = []

    @property
    def provider_id(self) -> str:
        return self._provider

    @property
    def model_id(self) -> str:
        return self._model

    def generate(self, brief: Any) -> LlmGenerationResult:
        self.calls.append(brief)
        if self._error is not None:
            raise self._error
        return LlmGenerationResult(
            candidate_data=dict(self._candidate_data),
            provider=self._provider,
            model=self._model,
            generated_at=self._generated_at,
        )

    def generate_candidate(
        self, request: AuthoringGenerationRequest
    ) -> LlmGenerationResult:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        return LlmGenerationResult(
            candidate_data=dict(self._candidate_data),
            provider=self._provider,
            model=self._model,
            generated_at=self._generated_at,
        )
