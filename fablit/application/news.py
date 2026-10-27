"""Curated Fashion & Design Pulse application workflow (SPEC-041).

This module owns the part of the news feature that must be deterministic and
testable without a network or an AI call:

- the persisted :class:`NewsStory` contract (SPEC-041 §7);
- the news-specific :class:`NewsRepository` port and its in-memory
  implementation;
- the bounded curation workflow that fetches approved sources, normalizes and
  deduplicates links, applies deterministic safety/freshness checks, asks the
  provider-neutral :class:`~fablit.application.news_curation.NewsCurationProvider`
  for curation, validates the result against the source evidence, and only
  then persists and publishes the story;
- an accurate batch report (fetched, deduplicated, published, rejected,
  failed) that never carries raw provider payloads or secrets.

A failed or empty refresh never clears the existing feed: stories are only
ever written, never deleted by the workflow (SPEC-041 §5.3).
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from threading import Lock
from uuid import NAMESPACE_URL, UUID, uuid5

from .errors import (
    NewsCurationInProgressError,
    NewsCurationProviderError,
    UnsafeNewsUrlError,
)
from .news_curation import (
    NewsCurationProvider,
    NewsCurationRequest,
    NewsCurationResult,
    coerce_news_curation_result,
)
from .news_sources import (
    NewsSource,
    NewsSourceFetcher,
    NewsSourceItem,
    link_belongs_to_source,
    normalize_http_url,
    normalize_terms,
    term_is_grounded,
)

logger = logging.getLogger("fablit.application.news")

#: Bounded source/field limits used by the deterministic checks.
MAX_HEADLINE_CHARS = 200
MAX_STORY_SUMMARY_CHARS = 2000
MAX_RELEVANCE_CHARS = 600
MAX_REFLECTION_CHARS = 400
MAX_GROUNDING_TERMS = 8
MAX_GROUNDING_TERM_CHARS = 80
MAX_SOURCE_ITEMS = 50

DEFAULT_MAX_ITEMS_PER_SOURCE = 6
DEFAULT_FRESHNESS_DAYS = 14
DEFAULT_MAX_SUMMARY_CHARS = 600
DEFAULT_RELEVANCE_THRESHOLD = 0.5

#: One day of tolerance for a publisher date ahead of the server clock.
_FUTURE_DATE_TOLERANCE = timedelta(days=1)

#: Learner-facing copy must stay qualitative (project-wide convention).
_FORBIDDEN_LEARNER_TERMS = (
    "score",
    "scored",
    "grade",
    "graded",
    "mastery",
    "mastered",
    "streak",
    "rank",
    "ranking",
    "urgent",
    "hurry",
    "don't miss",
)


class NewsCategory(StrEnum):
    """Controlled categories for curated fashion and design stories."""

    FASHION = "fashion"
    TEXTILES = "textiles"
    SUSTAINABILITY = "sustainability"
    INDIAN_CRAFT = "indian-craft"
    DESIGN = "design"
    VISUAL_CULTURE = "visual-culture"


NEWS_CATEGORY_LABELS: dict[NewsCategory, str] = {
    NewsCategory.FASHION: "Fashion",
    NewsCategory.TEXTILES: "Textiles & materials",
    NewsCategory.SUSTAINABILITY: "Sustainability",
    NewsCategory.INDIAN_CRAFT: "Indian craft",
    NewsCategory.DESIGN: "Design",
    NewsCategory.VISUAL_CULTURE: "Visual culture",
}


@dataclass(frozen=True)
class NewsStory:
    """One curated, published story (SPEC-041 §7).

    Only validated stories reach this type: the curation workflow constructs a
    story after every deterministic and provider-result check has passed, and
    the repository persists exactly this contract. Source excerpts are not
    stored — attribution and a canonical link are.
    """

    story_id: UUID
    headline: str
    canonical_url: str
    source_name: str
    summary: str
    categories: tuple[NewsCategory, ...]
    educational_relevance: str
    retrieved_at: datetime
    curated_at: datetime
    published_at: datetime | None = None
    reflection_prompt: str | None = None
    provider: str = ""
    model: str = ""
    validation_status: str = "published"

    def __post_init__(self) -> None:
        """Enforce the persisted story invariants."""
        if not isinstance(self.story_id, UUID):
            raise ValueError(f"news story id must be a UUID, got {self.story_id!r}")
        for name in ("headline", "canonical_url", "source_name", "summary"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"news story {name} must be non-blank text")
        if len(self.headline.strip()) > MAX_HEADLINE_CHARS:
            raise ValueError(
                f"news story headline must be at most {MAX_HEADLINE_CHARS} characters"
            )
        if len(self.summary.strip()) > MAX_STORY_SUMMARY_CHARS:
            raise ValueError(
                "news story summary must be at most "
                f"{MAX_STORY_SUMMARY_CHARS} characters"
            )
        try:
            normalize_http_url(self.canonical_url)
        except UnsafeNewsUrlError as exc:
            raise ValueError(f"news story canonical_url is unsafe: {exc}") from exc
        if not isinstance(self.categories, tuple) or not self.categories:
            raise ValueError("news story categories must be a non-empty tuple")
        if not all(isinstance(category, NewsCategory) for category in self.categories):
            raise ValueError(
                "news story categories must be controlled NewsCategory values"
            )
        if not isinstance(self.educational_relevance, str) or not (
            self.educational_relevance.strip()
        ):
            raise ValueError("news story educational_relevance must be non-blank text")
        if len(self.educational_relevance.strip()) > MAX_RELEVANCE_CHARS:
            raise ValueError(
                "news story educational_relevance must be at most "
                f"{MAX_RELEVANCE_CHARS} characters"
            )
        for name in ("retrieved_at", "curated_at", "published_at"):
            value = getattr(self, name)
            if value is None and name == "published_at":
                continue
            if (
                not isinstance(value, datetime)
                or value.tzinfo is None
                or value.utcoffset() != timedelta(0)
            ):
                raise ValueError(f"news story {name} must be timezone-aware UTC")
        if self.reflection_prompt is not None:
            if not isinstance(self.reflection_prompt, str) or not (
                self.reflection_prompt.strip()
            ):
                raise ValueError(
                    "news story reflection_prompt must be non-blank text when provided"
                )
            if len(self.reflection_prompt.strip()) > MAX_REFLECTION_CHARS:
                raise ValueError(
                    "news story reflection_prompt must be at most "
                    f"{MAX_REFLECTION_CHARS} characters"
                )
        for name in ("provider", "model", "validation_status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"news story {name} must be non-blank text")

    @property
    def display_at(self) -> datetime:
        """The date the feed orders and shows: publication date when reliable."""
        return self.published_at or self.curated_at


class NewsRepository(ABC):
    """Persistence port for curated news stories (SPEC-041 §6.3).

    This boundary is deliberately independent of learner practice history and
    published practices. Implementations may raise
    :class:`~fablit.application.persistence.PersistenceError` so a storage
    failure is explicit and is never reported as a published story.
    """

    @abstractmethod
    def save(self, story: NewsStory) -> NewsStory:
        """Persist one validated story under its stable identity."""

    @abstractmethod
    def get(self, story_id: UUID) -> NewsStory | None:
        """Return one story by identity, or ``None`` when it is absent."""

    @abstractmethod
    def find_by_url(self, canonical_url: str) -> NewsStory | None:
        """Return the story already stored for a canonical URL, if any."""

    @abstractmethod
    def list_stories(self) -> tuple[NewsStory, ...]:
        """Return every published story, newest first with a stable tie-break."""


class InMemoryNewsRepository(NewsRepository):
    """Deterministic in-memory news store for tests and local development."""

    def __init__(self) -> None:
        self._stories: dict[UUID, NewsStory] = {}
        self._lock = Lock()

    def save(self, story: NewsStory) -> NewsStory:
        if not isinstance(story, NewsStory):
            raise ValueError("news repository only accepts NewsStory records")
        with self._lock:
            self._stories[story.story_id] = story
        return story

    def get(self, story_id: UUID) -> NewsStory | None:
        if not isinstance(story_id, UUID):
            return None
        with self._lock:
            return self._stories.get(story_id)

    def find_by_url(self, canonical_url: str) -> NewsStory | None:
        with self._lock:
            for story in self._stories.values():
                if story.canonical_url == canonical_url:
                    return story
        return None

    def list_stories(self) -> tuple[NewsStory, ...]:
        with self._lock:
            stories = tuple(self._stories.values())
        return tuple(
            sorted(
                stories,
                key=lambda story: (story.display_at, str(story.story_id)),
                reverse=True,
            )
        )


@dataclass(frozen=True)
class NewsItemOutcome:
    """A safe, actionable report of one rejected or failed candidate.

    It carries only the publisher name, a bounded headline, the normalized
    link (empty when the link itself was unsafe), and a stable reason. The raw
    source excerpt and provider payload are never included.
    """

    source_name: str
    title: str
    url: str
    reason: str


@dataclass(frozen=True)
class NewsSourceFailure:
    """A source that could not be read during a batch."""

    source_name: str
    reason: str


class NewsBatchStage(StrEnum):
    """Observable phases a running batch reports to a progress observer.

    SPEC-042 §8: only stages that reflect real work are reported, so the
    durable job never claims a phase the workflow has not reached.
    """

    FETCHING_SOURCES = "fetching_sources"
    CURATING_ITEMS = "curating_items"
    FINALIZING_REPORT = "finalizing_report"


@dataclass(frozen=True)
class NewsBatchProgress:
    """One observed step of a running batch (SPEC-042 §6).

    Counts describe the current invocation only: a batch that is split into
    bounded task-sized units restarts its counters for each unit, and the
    durable job adds them to the totals it has already persisted.
    """

    stage: NewsBatchStage
    sources_configured: int
    sources_processed: int
    fetched: int
    deduplicated: int
    published: int
    rejected: int
    failed: int

    def __post_init__(self) -> None:
        """Require a controlled stage and non-negative counters."""
        if not isinstance(self.stage, NewsBatchStage):
            raise ValueError(f"news batch stage must be controlled, got {self.stage!r}")
        for name in (
            "sources_configured",
            "sources_processed",
            "fetched",
            "deduplicated",
            "published",
            "rejected",
            "failed",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"news batch progress {name} must be >= 0")
        if self.sources_processed > self.sources_configured:
            raise ValueError(
                "news batch progress sources_processed cannot be greater than "
                "sources_configured"
            )


@dataclass(frozen=True)
class NewsBatchResult:
    """Accurate outcome counts and safe detail for one refresh (SPEC-041 §5.1)."""

    started_at: datetime
    finished_at: datetime
    sources_configured: int = 0
    sources_processed: int = 0
    fetched: int = 0
    deduplicated: int = 0
    published: int = 0
    rejected: int = 0
    failed: int = 0
    rejections: tuple[NewsItemOutcome, ...] = ()
    failures: tuple[NewsItemOutcome, ...] = ()
    source_failures: tuple[NewsSourceFailure, ...] = ()

    @property
    def summary_line(self) -> str:
        """A one-line, human-readable batch summary for the operator."""
        return (
            f"{self.fetched} fetched, {self.deduplicated} duplicate"
            f"{'' if self.deduplicated == 1 else 's'}, {self.published} published, "
            f"{self.rejected} rejected, {self.failed} failed"
        )


class NewsCurator:
    """Bounded, on-demand curation workflow for the news feed (SPEC-041 §5.2).

    One call fetches every configured source, curates each eligible candidate,
    validates the provider's structured result against the fetched source, and
    persists only stories that pass every check. Failures are contained per
    source and per candidate; nothing already published is removed.
    """

    def __init__(
        self,
        *,
        repository: NewsRepository,
        fetcher: NewsSourceFetcher,
        provider: NewsCurationProvider,
        sources: Iterable[NewsSource],
        max_items_per_source: int = DEFAULT_MAX_ITEMS_PER_SOURCE,
        freshness_days: int = DEFAULT_FRESHNESS_DAYS,
        max_summary_chars: int = DEFAULT_MAX_SUMMARY_CHARS,
        relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(repository, NewsRepository):
            raise ValueError("news curator requires a NewsRepository")
        if max_items_per_source < 1:
            raise ValueError("max_items_per_source must be at least 1")
        if freshness_days < 1:
            raise ValueError("freshness_days must be at least 1")
        if not 1 <= max_summary_chars <= MAX_STORY_SUMMARY_CHARS:
            raise ValueError(
                f"max_summary_chars must be between 1 and {MAX_STORY_SUMMARY_CHARS}"
            )
        if not 0 <= relevance_threshold <= 1:
            raise ValueError("relevance_threshold must be between 0 and 1")
        self._repository = repository
        self._fetcher = fetcher
        self._provider = provider
        self._sources = tuple(sources)
        self._max_items_per_source = min(max_items_per_source, MAX_SOURCE_ITEMS)
        self._freshness_days = freshness_days
        self._max_summary_chars = max_summary_chars
        self._relevance_threshold = relevance_threshold
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = Lock()

    @property
    def sources(self) -> tuple[NewsSource, ...]:
        """The approved sources this workflow may fetch, in configured order."""
        return self._sources

    def curate_batch(
        self,
        *,
        sources: Iterable[NewsSource] | None = None,
        on_progress: Callable[[NewsBatchProgress], None] | None = None,
    ) -> NewsBatchResult:
        """Run one bounded refresh and report exactly what happened.

        ``sources`` narrows the run to a bounded slice of the configured
        allowlist so a large batch can be split across task-sized units; the
        slice is still subject to every source and URL check. ``on_progress``
        observes the phases the batch actually reaches (SPEC-042 §8); an
        observer that raises aborts the run rather than letting a job report
        progress that was never persisted.

        Raises:
            NewsCurationInProgressError: When another refresh is already
                running in this process. Repeated runs are otherwise
                idempotent: a story already stored for a canonical URL is
                counted as a duplicate and is not written again.
        """
        if not self._lock.acquire(blocking=False):
            raise NewsCurationInProgressError("a news refresh is already running")
        try:
            selected = self._sources if sources is None else tuple(sources)
            return self._run(selected, on_progress=on_progress)
        finally:
            self._lock.release()

    def _run(
        self,
        selected: tuple[NewsSource, ...],
        *,
        on_progress: Callable[[NewsBatchProgress], None] | None,
    ) -> NewsBatchResult:
        started_at = self._clock()
        fetched = deduplicated = published = rejected = failed = 0
        rejections: list[NewsItemOutcome] = []
        failures: list[NewsItemOutcome] = []
        source_failures: list[NewsSourceFailure] = []
        seen_urls: set[str] = set()
        processed = 0

        def report(stage: NewsBatchStage, sources_processed: int) -> None:
            if on_progress is None:
                return
            on_progress(
                NewsBatchProgress(
                    stage=stage,
                    sources_configured=len(selected),
                    sources_processed=sources_processed,
                    fetched=fetched,
                    deduplicated=deduplicated,
                    published=published,
                    rejected=rejected,
                    failed=failed,
                )
            )

        for index, source in enumerate(selected):
            report(NewsBatchStage.FETCHING_SOURCES, index)
            try:
                items = tuple(self._fetcher.fetch(source))
            except Exception as error:
                logger.warning(
                    "news source could not be retrieved",
                    extra={
                        "source": source.name,
                        "error_type": type(error).__name__,
                    },
                )
                source_failures.append(
                    NewsSourceFailure(
                        source_name=source.name,
                        reason="source could not be retrieved",
                    )
                )
                processed += 1
                continue

            for item in items[: self._max_items_per_source]:
                fetched += 1
                outcome, story = self._process_item(
                    item,
                    source,
                    now=started_at,
                    seen_urls=seen_urls,
                )
                if outcome is not None:
                    if outcome.reason == "duplicate":
                        deduplicated += 1
                    elif outcome.reason in _FAILURE_REASONS:
                        failed += 1
                        failures.append(outcome)
                    else:
                        rejected += 1
                        rejections.append(outcome)
                elif story is not None:
                    published += 1
                report(NewsBatchStage.CURATING_ITEMS, index)
            processed += 1

        report(NewsBatchStage.FINALIZING_REPORT, processed)
        finished_at = self._clock()
        return NewsBatchResult(
            started_at=started_at,
            finished_at=finished_at,
            sources_configured=len(selected),
            sources_processed=processed,
            fetched=fetched,
            deduplicated=deduplicated,
            published=published,
            rejected=rejected,
            failed=failed,
            rejections=tuple(rejections),
            failures=tuple(failures),
            source_failures=tuple(source_failures),
        )

    def _process_item(
        self,
        item: NewsSourceItem,
        source: NewsSource,
        *,
        now: datetime,
        seen_urls: set[str],
    ) -> tuple[NewsItemOutcome | None, NewsStory | None]:
        title = " ".join(item.title.split())[:MAX_HEADLINE_CHARS]
        try:
            canonical_url = normalize_http_url(item.url)
        except UnsafeNewsUrlError:
            return (
                _outcome(
                    source.name, title, "", "link is not a safe public HTTP(S) URL"
                ),
                None,
            )

        if not link_belongs_to_source(canonical_url, source):
            return (
                _outcome(
                    source.name,
                    title,
                    canonical_url,
                    "link is outside the approved source",
                ),
                None,
            )

        if canonical_url in seen_urls:
            return _outcome(source.name, title, canonical_url, "duplicate"), None
        seen_urls.add(canonical_url)

        try:
            existing = self._repository.find_by_url(canonical_url)
        except Exception as error:
            logger.warning(
                "news repository could not be read",
                extra={"error_type": type(error).__name__},
            )
            return (
                _outcome(source.name, title, canonical_url, "news storage unavailable"),
                None,
            )
        if existing is not None:
            return _outcome(source.name, title, canonical_url, "duplicate"), None

        rejection = self._deterministic_rejection(item, now=now)
        if rejection is not None:
            return _outcome(source.name, title, canonical_url, rejection), None

        request = NewsCurationRequest(
            source_name=source.name,
            headline=title,
            url=canonical_url,
            excerpt=item.excerpt,
            allowed_categories=tuple(category.value for category in NewsCategory),
        )
        try:
            raw_result = self._provider.curate(request)
        except Exception as error:
            # A provider failure (unavailable, timed out, unreadable response)
            # is a failed candidate, never a rejected one and never published.
            logger.warning(
                "news curation provider failed",
                extra={"error_type": type(error).__name__},
            )
            return (
                _outcome(source.name, title, canonical_url, "curation provider failed"),
                None,
            )
        try:
            result = coerce_news_curation_result(raw_result)
        except NewsCurationProviderError:
            return (
                _outcome(
                    source.name,
                    title,
                    canonical_url,
                    "curation result could not be used",
                ),
                None,
            )

        rejection = self._result_rejection(result, item, title)
        if rejection is not None:
            return _outcome(source.name, title, canonical_url, rejection), None

        categories = _categories(result.categories)
        reflection = _optional_text(result.reflection_prompt)
        story = NewsStory(
            story_id=uuid5(NAMESPACE_URL, canonical_url),
            headline=title,
            canonical_url=canonical_url,
            source_name=source.name,
            summary=" ".join(result.summary.split()),
            categories=categories,
            educational_relevance=" ".join(result.educational_relevance.split()),
            retrieved_at=now,
            curated_at=now,
            published_at=(
                _utc(item.published_at) if item.published_at is not None else None
            ),
            reflection_prompt=reflection,
            provider=_provider_identity(self._provider, "provider_id"),
            model=_provider_identity(self._provider, "model_id"),
        )
        try:
            self._repository.save(story)
        except Exception as error:
            logger.warning(
                "news story could not be stored",
                extra={"error_type": type(error).__name__},
            )
            return (
                _outcome(
                    source.name, title, canonical_url, "story could not be stored"
                ),
                None,
            )
        return None, story

    def _deterministic_rejection(
        self, item: NewsSourceItem, *, now: datetime
    ) -> str | None:
        """Apply source, field, and freshness checks before any AI call."""
        if not item.title.strip():
            return "headline is missing"
        if len(item.title.strip()) > MAX_HEADLINE_CHARS:
            return "headline is too long"
        if len(item.excerpt) > MAX_HEADLINE_CHARS * 100:
            return "source excerpt is too long"
        published_at = item.published_at
        if published_at is None:
            return "publication date is missing"
        published_at = _utc(published_at)
        if published_at > now + _FUTURE_DATE_TOLERANCE:
            return "publication date is in the future"
        if published_at < now - timedelta(days=self._freshness_days):
            return "story is older than the freshness window"
        return None

    def _result_rejection(
        self,
        result: NewsCurationResult,
        item: NewsSourceItem,
        title: str,
    ) -> str | None:
        """Validate the provider result's shape, relevance, and grounding."""
        if len(" ".join(result.summary.split())) > self._max_summary_chars:
            return "summary is too long"
        if len(result.educational_relevance.strip()) > MAX_RELEVANCE_CHARS:
            return "educational relevance is too long"
        if (
            result.reflection_prompt is not None
            and len(result.reflection_prompt.strip()) > MAX_REFLECTION_CHARS
        ):
            return "reflection prompt is too long"
        if len(result.grounding_terms) > MAX_GROUNDING_TERMS:
            return "too many grounding terms"
        if any(
            len(term.strip()) > MAX_GROUNDING_TERM_CHARS
            for term in result.grounding_terms
        ):
            return "grounding term is too long"
        if result.relevance_score < self._relevance_threshold:
            return "story is not relevant enough"
        categories = _categories(result.categories)
        if not categories:
            return "unknown category"
        learner_text = " ".join(
            (
                result.summary,
                result.educational_relevance,
                result.reflection_prompt or "",
            )
        )
        if _uses_forbidden_language(learner_text):
            return "result uses learner-measurement language"
        evidence = normalize_terms(f"{item.title} {item.excerpt}")
        if not all(term_is_grounded(term, evidence) for term in result.grounding_terms):
            return "summary is not grounded in the source"
        return None


_FAILURE_REASONS = frozenset(
    {
        "news storage unavailable",
        "curation provider failed",
        "story could not be stored",
    }
)


def _outcome(source_name: str, title: str, url: str, reason: str) -> NewsItemOutcome:
    return NewsItemOutcome(
        source_name=source_name,
        title=title,
        url=url,
        reason=reason,
    )


def _categories(values: Iterable[str]) -> tuple[NewsCategory, ...]:
    categories: list[NewsCategory] = []
    for value in values:
        try:
            category = NewsCategory(str(value).strip().lower())
        except ValueError:
            return ()
        if category not in categories:
            categories.append(category)
    return tuple(categories)


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = " ".join(value.split())
    return stripped or None


def _provider_identity(provider: object, attribute: str) -> str:
    value = getattr(provider, attribute, "")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _uses_forbidden_language(text: str) -> bool:
    normalized = text.casefold()
    return any(
        re.search(rf"\b{re.escape(term)}\b", normalized)
        for term in _FORBIDDEN_LEARNER_TERMS
    )
