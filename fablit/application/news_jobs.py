"""Durable news-curation jobs (SPEC-042 §6, §7).

SPEC-041 ran a curation batch inside the author's HTTP request, with an
in-process lock and process-local last-batch state. That is not durability:
another App Engine instance, or the same instance after a restart, cannot see
the run. This module owns the durable part of the workflow and nothing else:

- :class:`NewsCurationJob` — a validated record with a stable identity,
  UTC timestamps, an explicit lifecycle, progress counters, a bounded and
  safe failure diagnostic, and the final batch report;
- :class:`NewsCurationJobRepository` — the news-specific persistence port,
  with an atomic ``start``/``claim`` pair so concurrent starts and duplicate
  task delivery are safe rather than merely unlikely;
- :class:`NewsCurationJobService` — start (persist before accepting), execute
  (lease, bounded unit of work, checkpoint, finalize), and recover (stale
  lease, interrupted job).

Durability never depends on a thread, an in-process background task, or the
browser request: the production adapter stores the job in Datastore and the
work is dispatched as a managed task. In-memory implementations exist only for
tests and local development.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from threading import Lock
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from .errors import (
    NewsCurationDispatchError,
    NewsCurationInProgressError,
    NewsCurationJobTransitionError,
)
from .news import (
    NewsBatchProgress,
    NewsBatchResult,
    NewsBatchStage,
    NewsCurationDiagnostics,
    NewsCurator,
    NewsProviderOutcome,
)

logger = logging.getLogger("fablit.application.news_jobs")

#: A job message is operator-facing copy, never provider or source content.
MAX_JOB_MESSAGE_CHARS = 500

#: A failure diagnostic stays short, single-purpose, and safe to persist.
MAX_JOB_ERROR_MESSAGE_CHARS = 300

#: How long one worker owns a job before another worker may recover it.
DEFAULT_LEASE_DURATION = timedelta(minutes=5)

#: How many approved sources one task-sized unit may process.
DEFAULT_MAX_SOURCES_PER_TASK = 2

#: How long a job may sit queued before a new start may recover it.
QUEUED_JOB_STALE_AFTER = timedelta(minutes=30)


class NewsCurationJobStatus(StrEnum):
    """The durable lifecycle of one curation job (SPEC-042 §6)."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """Whether this status closes the job for good."""
        return self in {
            NewsCurationJobStatus.SUCCEEDED,
            NewsCurationJobStatus.PARTIALLY_SUCCEEDED,
            NewsCurationJobStatus.FAILED,
        }


class NewsCurationStage(StrEnum):
    """Reported progress stages for a job (SPEC-042 §8).

    A stage is only reported once the workflow has actually reached it; there
    is no invented percentage and no promised completion time.
    """

    QUEUED = "queued"
    FETCHING_SOURCES = "fetching_sources"
    CURATING_ITEMS = "curating_items"
    FINALIZING_REPORT = "finalizing_report"
    DONE = "done"
    FAILED = "failed"


class NewsCurationErrorCategory(StrEnum):
    """Bounded, safe failure categories persisted with a job."""

    DISPATCH_FAILED = "dispatch_failed"
    INTERRUPTED = "interrupted"
    EXECUTION_FAILED = "execution_failed"


@dataclass(frozen=True)
class NewsCurationCounters:
    """Durable counters for one job (SPEC-042 §6).

    Counts are cumulative for the whole job: a job split into several
    task-sized units adds each unit's report to what it already persisted.
    """

    sources_configured: int = 0
    sources_processed: int = 0
    sources_failed: int = 0
    items_fetched: int = 0
    items_deduplicated: int = 0
    items_published: int = 0
    items_rejected: int = 0
    items_failed: int = 0
    provider_retries: int = 0

    def __post_init__(self) -> None:
        """Reject negative or non-integer counters."""
        for name in (
            "sources_configured",
            "sources_processed",
            "sources_failed",
            "items_fetched",
            "items_deduplicated",
            "items_published",
            "items_rejected",
            "items_failed",
            "provider_retries",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"news curation job counter {name} must be >= 0")
        if self.sources_processed > self.sources_configured:
            raise ValueError(
                "news curation job sources_processed cannot be greater than "
                "sources_configured"
            )


@dataclass(frozen=True)
class NewsCurationJob:
    """One durable curation job (SPEC-042 §6).

    The record is immutable: every lifecycle step returns a validated copy, so
    an illegal transition — finalizing twice, reviving a terminal job, or
    starting a run without a lease — fails loudly instead of corrupting state.
    """

    job_id: UUID
    created_at: datetime
    status: NewsCurationJobStatus = NewsCurationJobStatus.QUEUED
    stage: NewsCurationStage = NewsCurationStage.QUEUED
    message: str = "Waiting to start."
    started_at: datetime | None = None
    finished_at: datetime | None = None
    counters: NewsCurationCounters = field(default_factory=NewsCurationCounters)
    report: NewsBatchResult | None = None
    next_source_index: int = 0
    attempt: int = 0
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    error_category: NewsCurationErrorCategory | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Enforce identity, timestamps, counters, and lifecycle invariants."""
        if not isinstance(self.job_id, UUID):
            raise ValueError(
                f"news curation job id must be a UUID, got {self.job_id!r}"
            )
        _require_utc(self.created_at, "created_at")
        for name in ("started_at", "finished_at", "lease_expires_at"):
            value = getattr(self, name)
            if value is not None:
                _require_utc(value, name)
        if not isinstance(self.status, NewsCurationJobStatus):
            raise ValueError(
                f"news curation job status must be controlled, got {self.status!r}"
            )
        if not isinstance(self.stage, NewsCurationStage):
            raise ValueError(
                f"news curation job stage must be controlled, got {self.stage!r}"
            )
        if not isinstance(self.counters, NewsCurationCounters):
            raise ValueError("news curation job counters must be NewsCurationCounters")
        if self.report is not None and not isinstance(self.report, NewsBatchResult):
            raise ValueError("news curation job report must be a NewsBatchResult")
        _require_text(self.message, "message", limit=MAX_JOB_MESSAGE_CHARS)
        for name, value in (
            ("next_source_index", self.next_source_index),
            ("attempt", self.attempt),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"news curation job {name} must be >= 0")
        if self.next_source_index > self.counters.sources_configured:
            raise ValueError(
                "news curation job next_source_index cannot be greater than "
                "sources_configured"
            )
        if self.lease_owner is not None:
            _require_text(self.lease_owner, "lease_owner", limit=200)

        if self.status.is_terminal:
            if self.finished_at is None:
                raise ValueError(
                    "news curation job finished_at is required for a terminal status"
                )
            if self.lease_owner is not None or self.lease_expires_at is not None:
                raise ValueError(
                    "news curation job must not hold a lease after it is terminal"
                )
        elif self.finished_at is not None:
            raise ValueError(
                "news curation job finished_at is only set for a terminal status"
            )

        if self.status is NewsCurationJobStatus.QUEUED:
            if self.lease_owner is not None or self.lease_expires_at is not None:
                raise ValueError("queued news curation job must not hold a lease")
            if self.stage is not NewsCurationStage.QUEUED:
                raise ValueError(
                    "queued news curation job must report the queued stage"
                )
            if self.started_at is not None and self.attempt == 0:
                raise ValueError(
                    "queued news curation job cannot have started without an attempt"
                )
        if self.status is NewsCurationJobStatus.RUNNING:
            if self.started_at is None:
                raise ValueError("running news curation job requires started_at")
            if self.lease_owner is None or self.lease_expires_at is None:
                raise ValueError("running news curation job requires a lease")
            if self.stage not in {
                NewsCurationStage.FETCHING_SOURCES,
                NewsCurationStage.CURATING_ITEMS,
                NewsCurationStage.FINALIZING_REPORT,
            }:
                raise ValueError(
                    "running news curation job must report a working stage"
                )
        if self.status is NewsCurationJobStatus.FAILED:
            if self.stage is not NewsCurationStage.FAILED:
                raise ValueError(
                    "failed news curation job must report the failed stage"
                )
            if self.error_category is None or self.error_message is None:
                raise ValueError(
                    "failed news curation job requires a safe error category "
                    "and message"
                )
        elif self.error_category is not None or self.error_message is not None:
            raise ValueError(
                "only a failed news curation job carries an error diagnostic"
            )
        if self.status in {
            NewsCurationJobStatus.SUCCEEDED,
            NewsCurationJobStatus.PARTIALLY_SUCCEEDED,
        }:
            if self.stage is not NewsCurationStage.DONE:
                raise ValueError(
                    "finished news curation job must report the done stage"
                )
            if self.report is None:
                raise ValueError("finished news curation job requires a batch report")

    @property
    def is_terminal(self) -> bool:
        """Whether this job reached a terminal outcome."""
        return self.status.is_terminal

    @property
    def diagnostics(self) -> NewsCurationDiagnostics | None:
        """Safe structured diagnostics from the batch report, if present."""
        return self.report.diagnostics if self.report is not None else None

    @property
    def is_active(self) -> bool:
        """Whether this job is queued or running."""
        return not self.status.is_terminal

    def is_stale(self, now: datetime) -> bool:
        """Whether this job may be recovered rather than considered active.

        SPEC-042 §10: a running job is stale once its worker lease expires,
        and a queued job that has waited far longer than a task-sized unit can
        take is treated as never delivered. A stale job blocks no new start
        and can still be retried through its task.
        """
        if self.status is NewsCurationJobStatus.RUNNING:
            return self.lease_expires_at is not None and self.lease_expires_at <= now
        if self.status is NewsCurationJobStatus.QUEUED:
            queued_since = self.started_at or self.created_at
            return now - queued_since >= QUEUED_JOB_STALE_AFTER
        return False

    def claim(
        self,
        *,
        owner: str,
        at: datetime,
        lease_until: datetime,
    ) -> NewsCurationJob:
        """Lease this job for one worker (SPEC-042 §7).

        A queued job may always be claimed; a running job only once its lease
        expired, which is how a duplicate delivery becomes a recovery rather
        than a second run.
        """
        _require_text(owner, "lease owner", limit=200)
        _require_utc(at, "claim time")
        _require_utc(lease_until, "lease expiry")
        if lease_until <= at:
            raise NewsCurationJobTransitionError(
                "news curation job lease must extend past the claim time"
            )
        if self.status is NewsCurationJobStatus.RUNNING and not self.is_stale(at):
            raise NewsCurationJobTransitionError(
                f"news curation job {self.job_id} is still leased"
            )
        if self.status is not NewsCurationJobStatus.QUEUED and not self.is_stale(at):
            raise NewsCurationJobTransitionError(
                f"news curation job {self.job_id} cannot be claimed from "
                f"{self.status.value}"
            )
        return _replace(
            self,
            status=NewsCurationJobStatus.RUNNING,
            stage=NewsCurationStage.FETCHING_SOURCES,
            message="Curation is running.",
            started_at=self.started_at or at,
            attempt=self.attempt + 1,
            lease_owner=owner,
            lease_expires_at=lease_until,
        )

    def record_progress(
        self,
        *,
        stage: NewsCurationStage,
        message: str,
        counters: NewsCurationCounters,
    ) -> NewsCurationJob:
        """Record a progress step while this job is leased to its worker."""
        if self.status is not NewsCurationJobStatus.RUNNING:
            raise NewsCurationJobTransitionError(
                f"news curation job {self.job_id} is not running"
            )
        return _replace(self, stage=stage, message=message, counters=counters)

    def checkpoint(
        self,
        *,
        report: NewsBatchResult,
        counters: NewsCurationCounters,
        next_source_index: int,
        at: datetime,
        message: str,
    ) -> NewsCurationJob:
        """Persist finished work and queue the bounded remainder (SPEC-042 §7).

        The job returns to ``queued`` for the next task-sized unit; it keeps
        what it already completed and releases the lease so a fresh delivery
        can pick it up.
        """
        if self.status is not NewsCurationJobStatus.RUNNING:
            raise NewsCurationJobTransitionError(
                f"news curation job {self.job_id} is not running"
            )
        _require_utc(at, "checkpoint time")
        return _replace(
            self,
            status=NewsCurationJobStatus.QUEUED,
            stage=NewsCurationStage.QUEUED,
            message=message,
            counters=counters,
            report=report,
            next_source_index=next_source_index,
            lease_owner=None,
            lease_expires_at=None,
        )

    def complete(
        self,
        *,
        report: NewsBatchResult,
        counters: NewsCurationCounters,
        at: datetime,
    ) -> NewsCurationJob:
        """Close the job with its final report (SPEC-042 §6)."""
        if self.status is not NewsCurationJobStatus.RUNNING:
            raise NewsCurationJobTransitionError(
                f"news curation job {self.job_id} is not running"
            )
        _require_utc(at, "completion time")
        partial = (
            report.failed > 0 or bool(report.failures) or bool(report.source_failures)
        )
        return _replace(
            self,
            status=(
                NewsCurationJobStatus.PARTIALLY_SUCCEEDED
                if partial
                else NewsCurationJobStatus.SUCCEEDED
            ),
            stage=NewsCurationStage.DONE,
            message=(
                "Curation finished with item or source failures."
                if partial
                else "Curation finished."
            ),
            counters=counters,
            report=report,
            finished_at=at,
            lease_owner=None,
            lease_expires_at=None,
        )

    def fail(
        self,
        *,
        category: NewsCurationErrorCategory,
        message: str,
        at: datetime,
    ) -> NewsCurationJob:
        """Close the job with a bounded, safe failure diagnostic."""
        if self.status.is_terminal:
            raise NewsCurationJobTransitionError(
                f"news curation job {self.job_id} is already terminal"
            )
        if not isinstance(category, NewsCurationErrorCategory):
            raise ValueError(
                f"news curation job error category must be controlled, got {category!r}"
            )
        _require_utc(at, "failure time")
        _require_text(message, "error message", limit=MAX_JOB_ERROR_MESSAGE_CHARS)
        return _replace(
            self,
            status=NewsCurationJobStatus.FAILED,
            stage=NewsCurationStage.FAILED,
            message=message,
            finished_at=at,
            lease_owner=None,
            lease_expires_at=None,
            error_category=category,
            error_message=message,
        )


class NewsCurationJobRepository(ABC):
    """Persistence port for durable curation jobs (SPEC-042 §6).

    ``start`` and ``claim`` are atomic by contract: at most one job may be
    active at a time, and at most one worker may lease a job. Implementations
    may raise :class:`~fablit.application.persistence.PersistenceError` so a
    storage failure is never reported as accepted work.
    """

    @abstractmethod
    def start(self, job: NewsCurationJob) -> NewsCurationJob | None:
        """Create a queued job, or return ``None`` when one is already active."""

    @abstractmethod
    def claim(
        self,
        job_id: UUID,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> NewsCurationJob | None:
        """Lease a queued or stale-running job, or return ``None`` to no-op."""

    @abstractmethod
    def save(self, job: NewsCurationJob) -> NewsCurationJob:
        """Persist a job state, refusing to rewrite a terminal outcome."""

    @abstractmethod
    def get(self, job_id: UUID) -> NewsCurationJob | None:
        """Return one job by identity, or ``None`` when it is absent."""

    @abstractmethod
    def latest(self) -> NewsCurationJob | None:
        """Return the most recently created job, or ``None`` when none exists."""

    @abstractmethod
    def find_active(self) -> NewsCurationJob | None:
        """Return the queued or running job, or ``None`` when there is none."""


class InMemoryNewsCurationJobRepository(NewsCurationJobRepository):
    """Deterministic in-memory job store for tests and local development.

    A lock makes the atomic parts atomic for one process; durability across
    processes is exactly what this implementation does not provide, which is
    why production uses the Datastore adapter (SPEC-042 §6).
    """

    def __init__(self) -> None:
        self._jobs: dict[UUID, NewsCurationJob] = {}
        self._lock = Lock()

    def start(self, job: NewsCurationJob) -> NewsCurationJob | None:
        if not isinstance(job, NewsCurationJob):
            raise ValueError("news job repository only accepts NewsCurationJob records")
        if job.status is not NewsCurationJobStatus.QUEUED:
            raise ValueError("a new news curation job must be queued")
        with self._lock:
            if self._active_locked() is not None:
                return None
            self._jobs[job.job_id] = job
        return job

    def claim(
        self,
        job_id: UUID,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> NewsCurationJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.is_terminal:
                return None
            if job.status is NewsCurationJobStatus.RUNNING and not job.is_stale(now):
                return None
            claimed = job.claim(owner=owner, at=now, lease_until=lease_until)
            self._jobs[job_id] = claimed
            return claimed

    def save(self, job: NewsCurationJob) -> NewsCurationJob:
        if not isinstance(job, NewsCurationJob):
            raise ValueError("news job repository only accepts NewsCurationJob records")
        with self._lock:
            existing = self._jobs.get(job.job_id)
            if existing is not None and existing != job:
                if existing.is_terminal:
                    raise NewsCurationJobTransitionError(
                        f"news curation job {job.job_id} is already terminal"
                    )
                if existing.attempt > job.attempt:
                    raise NewsCurationJobTransitionError(
                        f"news curation job {job.job_id} was taken over by a "
                        "newer attempt"
                    )
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: UUID) -> NewsCurationJob | None:
        if not isinstance(job_id, UUID):
            return None
        with self._lock:
            return self._jobs.get(job_id)

    def latest(self) -> NewsCurationJob | None:
        with self._lock:
            jobs = tuple(self._jobs.values())
        if not jobs:
            return None
        return max(jobs, key=lambda job: (job.created_at, str(job.job_id)))

    def find_active(self) -> NewsCurationJob | None:
        with self._lock:
            return self._active_locked()

    def _active_locked(self) -> NewsCurationJob | None:
        active = [job for job in self._jobs.values() if job.is_active]
        if not active:
            return None
        return max(active, key=lambda job: (job.created_at, str(job.job_id)))


@runtime_checkable
class NewsCurationTaskDispatcher(Protocol):
    """Durable task dispatch port (SPEC-042 §7).

    The caller has already persisted the job, so a dispatcher only has to
    hand the identity to a managed task service. Anything it raises is
    reported to the author as a dispatch failure, never as queued work.
    """

    def dispatch(self, job_id: UUID) -> None:
        """Schedule one durable execution of ``job_id``."""
        ...


class InlineNewsCurationTaskDispatcher:
    """Local-development dispatcher that runs the task immediately.

    This is explicitly **not** the durability mechanism: it exists so local
    runs and tests can exercise the same start/execute path without a cloud
    queue. Production uses the managed Cloud Tasks dispatcher.
    """

    def __init__(self) -> None:
        self._runner: Callable[[UUID], object] | None = None

    def bind(self, runner: Callable[[UUID], object]) -> None:
        """Attach the execution handler this dispatcher should invoke."""
        self._runner = runner

    def dispatch(self, job_id: UUID) -> None:
        if self._runner is None:
            raise NewsCurationDispatchError(
                "no local curation worker is bound to the inline dispatcher"
            )
        self._runner(job_id)


def _merge_diagnostics(
    previous: NewsCurationDiagnostics | None,
    batch: NewsCurationDiagnostics | None,
) -> NewsCurationDiagnostics | None:
    if previous is None:
        return batch
    if batch is None:
        return previous

    total_retries = previous.provider_retries + batch.provider_retries
    total_recovered = (
        previous.transient_retries_recovered + batch.transient_retries_recovered
    )
    total_exhausted = previous.exhausted_retries + batch.exhausted_retries

    if (
        previous.provider_outcome == NewsProviderOutcome.FAILED
        or batch.provider_outcome == NewsProviderOutcome.FAILED
    ):
        outcome = NewsProviderOutcome.FAILED
    elif (
        previous.provider_outcome == NewsProviderOutcome.RETRIES_EXHAUSTED
        or batch.provider_outcome == NewsProviderOutcome.RETRIES_EXHAUSTED
        or total_exhausted > 0
    ):
        outcome = NewsProviderOutcome.RETRIES_EXHAUSTED
    elif (
        previous.provider_outcome == NewsProviderOutcome.RECOVERED
        or batch.provider_outcome == NewsProviderOutcome.RECOVERED
        or total_recovered > 0
    ):
        outcome = NewsProviderOutcome.RECOVERED
    else:
        outcome = NewsProviderOutcome.OK

    return NewsCurationDiagnostics(
        provider_id=batch.provider_id or previous.provider_id,
        model_id=batch.model_id or previous.model_id,
        provider_retries=total_retries,
        transient_retries_recovered=total_recovered,
        exhausted_retries=total_exhausted,
        provider_outcome=outcome,
        last_status_code=batch.last_status_code or previous.last_status_code,
    )


def merge_reports(
    previous: NewsBatchResult | None,
    batch: NewsBatchResult,
    *,
    sources_configured: int,
    started_at: datetime,
) -> NewsBatchResult:
    """Add one completed unit's report to the job's accumulated report."""
    prior_counts = (
        (0, 0, 0, 0, 0, 0, 0)
        if previous is None
        else (
            previous.sources_processed,
            previous.fetched,
            previous.deduplicated,
            previous.published,
            previous.rejected,
            previous.failed,
            previous.provider_retries,
        )
    )
    (
        prior_processed,
        prior_fetched,
        prior_deduplicated,
        prior_published,
        prior_rejected,
        prior_failed,
        prior_retries,
    ) = prior_counts
    return NewsBatchResult(
        started_at=started_at,
        finished_at=batch.finished_at,
        sources_configured=sources_configured,
        sources_processed=prior_processed + batch.sources_processed,
        fetched=prior_fetched + batch.fetched,
        deduplicated=prior_deduplicated + batch.deduplicated,
        published=prior_published + batch.published,
        rejected=prior_rejected + batch.rejected,
        failed=prior_failed + batch.failed,
        provider_retries=prior_retries + batch.provider_retries,
        diagnostics=_merge_diagnostics(
            previous.diagnostics if previous is not None else None,
            batch.diagnostics,
        ),
        rejections=(() if previous is None else previous.rejections) + batch.rejections,
        failures=(() if previous is None else previous.failures) + batch.failures,
        source_failures=(() if previous is None else previous.source_failures)
        + batch.source_failures,
    )


def counters_for(
    report: NewsBatchResult,
    *,
    sources_configured: int,
) -> NewsCurationCounters:
    """Derive the durable counters from an accumulated batch report."""
    return NewsCurationCounters(
        sources_configured=sources_configured,
        sources_processed=report.sources_processed,
        sources_failed=len(report.source_failures),
        items_fetched=report.fetched,
        items_deduplicated=report.deduplicated,
        items_published=report.published,
        items_rejected=report.rejected,
        items_failed=report.failed,
        provider_retries=report.provider_retries,
    )


class NewsCurationJobService:
    """Start, execute, and recover durable curation jobs (SPEC-042 §6, §7).

    The browser never owns a job here: ``start`` persists the job before it is
    acknowledged and hands only its identity to the dispatcher, and
    ``handle_task`` is idempotent under duplicate delivery because the
    repository grants a lease to exactly one worker.
    """

    def __init__(
        self,
        *,
        repository: NewsCurationJobRepository,
        curator: NewsCurator,
        dispatcher: NewsCurationTaskDispatcher,
        clock: Callable[[], datetime] | None = None,
        lease_duration: timedelta = DEFAULT_LEASE_DURATION,
        max_sources_per_task: int = DEFAULT_MAX_SOURCES_PER_TASK,
    ) -> None:
        if not isinstance(repository, NewsCurationJobRepository):
            raise ValueError("news job service requires a job repository")
        if not isinstance(curator, NewsCurator):
            raise ValueError("news job service requires a news curator")
        if not isinstance(dispatcher, NewsCurationTaskDispatcher):
            raise ValueError("news job service requires a task dispatcher")
        if lease_duration <= timedelta(0):
            raise ValueError("news job lease duration must be positive")
        if max_sources_per_task < 1:
            raise ValueError("max_sources_per_task must be at least 1")
        self._repository = repository
        self._curator = curator
        self._dispatcher = dispatcher
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lease_duration = lease_duration
        self._max_sources_per_task = max_sources_per_task

    def start(self) -> NewsCurationJob:
        """Persist and dispatch one job, or refuse an overlapping start.

        Raises:
            NewsCurationInProgressError: When another job is already queued or
                running and has not gone stale.
            NewsCurationDispatchError: When durable dispatch failed. The job
                is retained as ``failed``; it is never reported as queued.
        """
        now = self._clock()
        active = self._repository.find_active()
        if active is not None:
            if not active.is_stale(now):
                raise NewsCurationInProgressError(
                    f"news curation job {active.job_id} is {active.status.value}"
                )
            logger.warning(
                "recovering interrupted news curation job",
                extra={"job_id": str(active.job_id)},
            )
            self._repository.save(
                active.fail(
                    category=NewsCurationErrorCategory.INTERRUPTED,
                    message=(
                        "The previous curation run was interrupted by a restart "
                        "and was closed before this run started."
                    ),
                    at=now,
                )
            )

        job = NewsCurationJob(job_id=uuid4(), created_at=now)
        created = self._repository.start(job)
        if created is None:
            raise NewsCurationInProgressError("a news curation job is already active")

        try:
            self._dispatcher.dispatch(created.job_id)
        except Exception as error:
            logger.exception(
                "news curation job could not be dispatched",
                extra={"job_id": str(created.job_id)},
            )
            self._repository.save(
                created.fail(
                    category=NewsCurationErrorCategory.DISPATCH_FAILED,
                    message=(
                        "Curation could not be queued, so no work was accepted. "
                        "Try again."
                    ),
                    at=self._clock(),
                )
            )
            raise NewsCurationDispatchError(
                "the curation job could not be queued"
            ) from error

        return self._repository.get(created.job_id) or created

    def handle_task(self, job_id: UUID, *, owner: str) -> NewsCurationJob | None:
        """Execute one task-sized unit of a job, idempotently.

        Returns the current job (terminal when the batch finished, queued when
        another unit remains), or ``None`` when the job does not exist. A
        duplicate delivery, or a delivery while another worker's lease is
        live, is a no-op that returns the job as it stands.

        Raises:
            NewsCurationDispatchError: When the bounded remainder could not be
                queued. The finished unit is checkpointed first, so a task
                retry resumes rather than repeating the whole batch.
        """
        now = self._clock()
        job = self._repository.claim(
            job_id,
            owner=owner,
            now=now,
            lease_until=now + self._lease_duration,
        )
        if job is None:
            return self._repository.get(job_id)

        logger.info(
            "news curation job started",
            extra={"job_id": str(job.job_id), "attempt": job.attempt},
        )
        sources = self._curator.sources
        remaining = sources[job.next_source_index :]

        if not remaining:
            return self._finish(job, report=job.report, sources_configured=len(sources))

        resume_index = job.next_source_index
        base_counters = job.counters
        current = job
        stage_by_progress: dict[NewsBatchStage, NewsCurationStage] = {
            NewsBatchStage.FETCHING_SOURCES: NewsCurationStage.FETCHING_SOURCES,
            NewsBatchStage.CURATING_ITEMS: NewsCurationStage.CURATING_ITEMS,
            NewsBatchStage.FINALIZING_REPORT: NewsCurationStage.FINALIZING_REPORT,
        }

        def record(progress: NewsBatchProgress) -> None:
            nonlocal current
            counters = NewsCurationCounters(
                sources_configured=len(sources),
                sources_processed=resume_index + progress.sources_processed,
                sources_failed=base_counters.sources_failed,
                items_fetched=base_counters.items_fetched + progress.fetched,
                items_deduplicated=(
                    base_counters.items_deduplicated + progress.deduplicated
                ),
                items_published=base_counters.items_published + progress.published,
                items_rejected=base_counters.items_rejected + progress.rejected,
                items_failed=base_counters.items_failed + progress.failed,
                provider_retries=(
                    base_counters.provider_retries + progress.provider_retries
                ),
            )
            current = self._repository.save(
                current.record_progress(
                    stage=stage_by_progress[progress.stage],
                    message=_stage_message(progress.stage),
                    counters=counters,
                )
            )

        try:
            batch = self._curator.curate_batch(
                sources=remaining[: self._max_sources_per_task],
                on_progress=record,
            )
        except Exception as error:
            logger.exception(
                "news curation job failed",
                extra={
                    "job_id": str(job.job_id),
                    "error_type": type(error).__name__,
                },
            )
            return self._repository.save(
                job.fail(
                    category=NewsCurationErrorCategory.EXECUTION_FAILED,
                    message=(
                        "The curation run could not be completed. Existing stories "
                        "are unchanged."
                    ),
                    at=self._clock(),
                )
            )

        report = merge_reports(
            job.report,
            batch,
            sources_configured=len(sources),
            started_at=job.created_at,
        )
        counters = counters_for(report, sources_configured=len(sources))
        processed = job.next_source_index + batch.sources_processed

        if processed < len(sources):
            checkpointed = self._repository.save(
                job.checkpoint(
                    report=report,
                    counters=counters,
                    next_source_index=processed,
                    at=self._clock(),
                    message=(
                        "Curation is continuing with the remaining approved sources."
                    ),
                )
            )
            try:
                self._dispatcher.dispatch(checkpointed.job_id)
            except Exception as error:
                logger.exception(
                    "news curation job continuation could not be dispatched",
                    extra={"job_id": str(checkpointed.job_id)},
                )
                raise NewsCurationDispatchError(
                    "the remaining curation work could not be queued"
                ) from error
            return checkpointed

        return self._finish(
            job,
            report=report,
            sources_configured=len(sources),
            counters=counters,
        )

    def _finish(
        self,
        job: NewsCurationJob,
        *,
        report: NewsBatchResult | None,
        sources_configured: int,
        counters: NewsCurationCounters | None = None,
    ) -> NewsCurationJob:
        """Close a running job with the report it actually produced."""
        finished_at = self._clock()
        if report is None:
            report = NewsBatchResult(
                started_at=job.created_at,
                finished_at=finished_at,
                sources_configured=sources_configured,
            )
        if counters is None:
            counters = counters_for(report, sources_configured=sources_configured)
        return self._repository.save(
            job.complete(report=report, counters=counters, at=finished_at)
        )

    def run_locally(self, job_id: UUID) -> NewsCurationJob | None:
        """Execute a task in-process for the local-only dispatcher."""
        return self.handle_task(job_id, owner="inline")

    def get(self, job_id: UUID) -> NewsCurationJob | None:
        """Return one job by identity for the protected authoring surface."""
        return self._repository.get(job_id)

    def latest(self) -> NewsCurationJob | None:
        """Return the most recently created job for the authoring surface."""
        return self._repository.latest()


def _stage_message(stage: NewsBatchStage) -> str:
    if stage is NewsBatchStage.FETCHING_SOURCES:
        return "Fetching approved sources."
    if stage is NewsBatchStage.CURATING_ITEMS:
        return "Checking and curating eligible stories."
    return "Finalizing the batch report."


def _replace(job: NewsCurationJob, **changes: object) -> NewsCurationJob:
    """Build a validated copy without mutating the persisted record."""
    return replace(job, **changes)  # type: ignore[arg-type]


def _require_utc(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise ValueError(f"news curation job {name} must be timezone-aware UTC")


def _require_text(value: str, name: str, *, limit: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"news curation job {name} must be non-blank text")
    if len(value.strip()) > limit:
        raise ValueError(f"news curation job {name} must be at most {limit} characters")
