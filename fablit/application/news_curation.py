"""Provider-neutral AI curation port for the Fashion & Design Pulse (SPEC-041).

News curation is deliberately separate from practice authoring: it has its own
request/result shapes and its own port, so ``AuthoringLlmProvider``,
``BriefDraftingRequest``, and practice-authoring semantics stay unchanged
(SPEC-041 §6.2, AC-3/AC-4).

The workflow asks a provider to classify, summarize, assess educational
relevance, and optionally propose a reflection or practice prompt for one
fetched story. Provider SDKs, credentials, request construction, and response
parsing stay in the platform adapter; this module owns only the neutral
contract and a deterministic fake for tests and local development.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .errors import NewsCurationProviderError

#: Maximum characters of source evidence sent to a provider for one story.
MAX_CURATION_EXCERPT_CHARS = 4000


@dataclass(frozen=True)
class NewsCurationRequest:
    """One bounded, untrusted source story offered for curation."""

    source_name: str
    headline: str
    url: str
    excerpt: str
    allowed_categories: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Require the identifying fields and bound the source excerpt."""
        for name in ("source_name", "headline", "url"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"news curation request {name} must be non-blank text")
        if not isinstance(self.excerpt, str):
            raise ValueError("news curation request excerpt must be text")
        object.__setattr__(self, "excerpt", self.excerpt[:MAX_CURATION_EXCERPT_CHARS])

    def as_payload(self) -> dict[str, Any]:
        """Return a JSON-safe view for an adapter's request construction."""
        return {
            "source_name": self.source_name,
            "headline": self.headline,
            "url": self.url,
            "excerpt": self.excerpt,
            "allowed_categories": list(self.allowed_categories),
        }


@dataclass(frozen=True)
class NewsCurationResult:
    """The untrusted structured result the workflow validates before publication."""

    summary: str
    categories: tuple[str, ...]
    educational_relevance: str
    relevance_score: float
    grounding_terms: tuple[str, ...]
    reflection_prompt: str | None = None

    def __post_init__(self) -> None:
        """Enforce the shape every provider result must satisfy."""
        for name in ("summary", "educational_relevance"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"news curation result {name} must be non-blank text")
        if not isinstance(self.categories, tuple) or not self.categories:
            raise ValueError(
                "news curation result categories must be a non-empty tuple"
            )
        if not all(isinstance(category, str) for category in self.categories):
            raise ValueError("news curation result categories must be text")
        if not isinstance(self.grounding_terms, tuple) or not self.grounding_terms:
            raise ValueError(
                "news curation result grounding_terms must be a non-empty tuple"
            )
        if not all(isinstance(term, str) for term in self.grounding_terms):
            raise ValueError("news curation result grounding_terms must be text")
        if self.reflection_prompt is not None and not isinstance(
            self.reflection_prompt, str
        ):
            raise ValueError(
                "news curation result reflection_prompt must be text when provided"
            )
        score = self.relevance_score
        if isinstance(score, bool) or not isinstance(score, int | float):
            raise ValueError("news curation result relevance_score must be a number")
        if score < 0 or score > 1:
            raise ValueError(
                "news curation result relevance_score must be between 0 and 1"
            )
        object.__setattr__(self, "relevance_score", float(score))


def coerce_news_curation_result(value: object) -> NewsCurationResult:
    """Turn an adapter result or mapping into the neutral result, or refuse it."""
    if isinstance(value, NewsCurationResult):
        return value
    if not isinstance(value, Mapping):
        raise NewsCurationProviderError("the news provider returned an unusable result")

    summary = value.get("summary")
    categories = value.get("categories")
    relevance = value.get("educational_relevance", value.get("relevance"))
    reflection = value.get("reflection_prompt")
    score = value.get("relevance_score")
    grounding = value.get("grounding_terms")

    try:
        return NewsCurationResult(
            summary=_text(summary),
            categories=_text_tuple(categories, "categories"),
            educational_relevance=_text(relevance),
            relevance_score=_score(score),
            grounding_terms=_text_tuple(grounding, "grounding_terms"),
            reflection_prompt=(
                _text(reflection)
                if reflection is not None and _text(reflection)
                else None
            ),
        )
    except (ValueError, TypeError) as exc:
        raise NewsCurationProviderError(
            "the news provider returned an unusable result"
        ) from exc


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("expected text")
    return value.strip()


def _text_tuple(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, str):
        items = (value,)
    elif isinstance(value, list | tuple):
        items = tuple(value)
    else:
        raise ValueError(f"{name} must be text or a list of text")
    return tuple(
        str(item).strip() for item in items if isinstance(item, str) and item.strip()
    )


def _score(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise ValueError("relevance_score must be a number")
    return float(value)


@runtime_checkable
class NewsCurationProvider(Protocol):
    """Provider-neutral port for AI news curation (SPEC-041 §6.2)."""

    @property
    def provider_id(self) -> str:
        """Stable provider identifier retained for curation provenance."""
        ...

    @property
    def model_id(self) -> str:
        """Provider model identifier retained for curation provenance."""
        ...

    def curate(self, request: NewsCurationRequest) -> NewsCurationResult:
        """Curate one bounded source story.

        Raises:
            NewsCurationProviderError: When the provider is unavailable, the
                response is unusable, or the provider cannot be reached. The
                affected candidate is never published.
        """
        ...


class FakeNewsCurationProvider:
    """Deterministic in-process provider for tests and local development.

    Returns a supplied result, a per-URL result, or a safe default derived
    from the source headline. No network I/O is ever performed, so the
    automated suite never needs a live Gemini API call or credentials.
    """

    def __init__(
        self,
        result: NewsCurationResult | Mapping[str, Any] | None = None,
        *,
        results: Mapping[str, NewsCurationResult] | None = None,
        error: Exception | None = None,
        provider: str = "fake-news-curation",
        model: str = "fake-model",
    ) -> None:
        self._result = result
        self._results = dict(results or {})
        self._error = error
        self.provider = provider
        self.model = model
        self.requests: list[NewsCurationRequest] = []

    @property
    def provider_id(self) -> str:
        return self.provider

    @property
    def model_id(self) -> str:
        return self.model

    def curate(self, request: NewsCurationRequest) -> NewsCurationResult:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        per_url = self._results.get(request.url)
        if per_url is not None:
            return per_url
        if self._result is not None:
            return coerce_news_curation_result(self._result)
        return _default_result(request)


def _default_result(request: NewsCurationRequest) -> NewsCurationResult:
    """Build a grounded default result from the source's own headline."""
    words = [word.strip(".,:;!?()[]\"'“”‘’") for word in request.headline.split()]
    terms = tuple(word for word in words if len(word) >= 4)[:3]
    if not terms:
        terms = (request.headline.strip(),)
    return NewsCurationResult(
        summary=(
            f"{request.headline.strip()} — a current story worth noticing for "
            "fashion and design learners."
        ),
        categories=("design",),
        educational_relevance=(
            "Use this story to notice how design choices respond to materials, "
            "culture, and the world around them."
        ),
        relevance_score=0.8,
        grounding_terms=terms,
        reflection_prompt=(
            "What detail in this story changes how you would look at an object, "
            "garment, or space?"
        ),
    )
