"""Deterministic tests for durable curation jobs (SPEC-042 §6, §7).

Every dependency is injected: a fake source fetcher, a fake curation provider,
an in-memory job repository, a recording task dispatcher, and a fixed clock.
No test fetches a live feed, calls Gemini, or needs cloud credentials.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from fablit.application.errors import (
    NewsCurationDispatchError,
    NewsCurationInProgressError,
    NewsCurationJobTransitionError,
)
from fablit.application.news import (
    InMemoryNewsRepository,
    NewsBatchProgress,
    NewsBatchResult,
    NewsCurator,
    NewsItemOutcome,
    NewsSourceFailure,
)
from fablit.application.news_curation import FakeNewsCurationProvider
from fablit.application.news_jobs import (
    QUEUED_JOB_STALE_AFTER,
    InMemoryNewsCurationJobRepository,
    NewsCurationCounters,
    NewsCurationErrorCategory,
    NewsCurationJob,
    NewsCurationJobService,
    NewsCurationJobStatus,
    NewsCurationStage,
    counters_for,
    merge_reports,
)
from fablit.application.news_sources import (
    FakeNewsSourceFetcher,
    NewsSource,
    NewsSourceItem,
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
LEASE = timedelta(minutes=5)

SOURCE_A = NewsSource(
    name="The Daily Weave",
    feed_url="https://news.example.com/feed.xml",
    site_url="https://news.example.com",
)
SOURCE_B = NewsSource(
    name="Atelier Notes",
    feed_url="https://atelier.example.com/feed.xml",
    site_url="https://atelier.example.com",
)


def make_item(**overrides: object) -> NewsSourceItem:
    values: dict[str, object] = {
        "source_name": SOURCE_A.name,
        "title": "Handloom revival connects weavers with new markets",
        "url": "https://news.example.com/story/1",
        "published_at": NOW - timedelta(days=1),
        "excerpt": "A collective is helping handloom weavers reach new buyers.",
    }
    values.update(overrides)
    return NewsSourceItem(**values)  # type: ignore[arg-type]


def make_job(**overrides: object) -> NewsCurationJob:
    values: dict[str, object] = {
        "job_id": uuid4(),
        "created_at": NOW,
    }
    values.update(overrides)
    return NewsCurationJob(**values)  # type: ignore[arg-type]


def running_job(*, at: datetime = NOW) -> NewsCurationJob:
    return make_job().claim(
        owner="worker-1",
        at=at,
        lease_until=at + LEASE,
    )


def make_report(**overrides: object) -> NewsBatchResult:
    values: dict[str, object] = {
        "started_at": NOW,
        "finished_at": NOW + timedelta(minutes=1),
        "sources_configured": 1,
        "sources_processed": 1,
    }
    values.update(overrides)
    return NewsBatchResult(**values)  # type: ignore[arg-type]


class ExplodingCurator(NewsCurator):
    """A curator whose batch fails at the workflow level, not per candidate."""

    def curate_batch(
        self,
        *,
        sources: Iterable[NewsSource] | None = None,
        on_progress: Callable[[NewsBatchProgress], None] | None = None,
    ) -> NewsBatchResult:
        raise RuntimeError("secret upstream payload")


class RecordingDispatcher:
    """A task dispatcher that records identities instead of delivering them."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.dispatched: list[UUID] = []
        self._error = error

    def dispatch(self, job_id: UUID) -> None:
        self.dispatched.append(job_id)
        if self._error is not None:
            raise self._error


def make_curator(
    *,
    sources: tuple[NewsSource, ...] = (SOURCE_A,),
    items: tuple[NewsSourceItem, ...] | None = None,
    provider: FakeNewsCurationProvider | None = None,
    repository: InMemoryNewsRepository | None = None,
    errors: dict[str, Exception] | None = None,
) -> tuple[NewsCurator, InMemoryNewsRepository, FakeNewsCurationProvider]:
    story_repository = repository or InMemoryNewsRepository()
    curation_provider = provider or FakeNewsCurationProvider()
    fetcher = FakeNewsSourceFetcher(
        default=items if items is not None else (make_item(),),
        errors=errors,
    )
    curator = NewsCurator(
        repository=story_repository,
        fetcher=fetcher,
        provider=curation_provider,
        sources=sources,
        clock=lambda: NOW,
    )
    return curator, story_repository, curation_provider


def make_service(
    *,
    curator: NewsCurator,
    repository: InMemoryNewsCurationJobRepository | None = None,
    dispatcher: RecordingDispatcher | None = None,
    max_sources_per_task: int = 2,
    clock: Callable[[], datetime] | None = None,
) -> tuple[
    NewsCurationJobService, InMemoryNewsCurationJobRepository, RecordingDispatcher
]:
    job_repository = repository or InMemoryNewsCurationJobRepository()
    task_dispatcher = dispatcher or RecordingDispatcher()
    service = NewsCurationJobService(
        repository=job_repository,
        curator=curator,
        dispatcher=task_dispatcher,
        clock=clock or (lambda: NOW),
        max_sources_per_task=max_sources_per_task,
    )
    return service, job_repository, task_dispatcher


# --- Job model --------------------------------------------------------------


def test_new_job_is_queued_with_empty_counters() -> None:
    job = make_job()

    assert job.status is NewsCurationJobStatus.QUEUED
    assert job.stage is NewsCurationStage.QUEUED
    assert job.counters == NewsCurationCounters()
    assert job.is_active
    assert not job.is_terminal
    assert job.report is None
    assert job.attempt == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"job_id": "not-a-uuid"},
        {"created_at": datetime(2026, 10, 20, 12, 0)},
        {"next_source_index": 1},
        {"message": " "},
        {"attempt": -1},
    ],
)
def test_invalid_job_records_are_refused(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        make_job(**overrides)


def test_counters_refuse_negative_and_inconsistent_values() -> None:
    with pytest.raises(ValueError, match="must be >= 0"):
        NewsCurationCounters(items_fetched=-1)
    with pytest.raises(ValueError, match="cannot be greater than"):
        NewsCurationCounters(sources_configured=1, sources_processed=2)
    with pytest.raises(ValueError):
        NewsCurationCounters(items_published=True)


def test_queued_job_must_not_hold_a_lease() -> None:
    with pytest.raises(ValueError, match="must not hold a lease"):
        make_job(lease_owner="worker-1", lease_expires_at=NOW + LEASE)


def test_terminal_job_requires_a_finish_time_and_report() -> None:
    with pytest.raises(ValueError, match="finished_at is required"):
        make_job(status=NewsCurationJobStatus.SUCCEEDED, stage=NewsCurationStage.DONE)
    with pytest.raises(ValueError, match="requires a batch report"):
        make_job(
            status=NewsCurationJobStatus.SUCCEEDED,
            stage=NewsCurationStage.DONE,
            finished_at=NOW,
        )


def test_claiming_a_queued_job_starts_it_with_a_lease() -> None:
    job = make_job()

    claimed = job.claim(owner="worker-1", at=NOW, lease_until=NOW + LEASE)

    assert claimed.status is NewsCurationJobStatus.RUNNING
    assert claimed.stage is NewsCurationStage.FETCHING_SOURCES
    assert claimed.started_at == NOW
    assert claimed.attempt == 1
    assert claimed.lease_owner == "worker-1"
    assert claimed.lease_expires_at == NOW + LEASE


def test_claiming_a_job_with_a_live_lease_is_refused() -> None:
    claimed = running_job()

    with pytest.raises(NewsCurationJobTransitionError, match="still leased"):
        claimed.claim(
            owner="worker-2",
            at=NOW + timedelta(seconds=30),
            lease_until=NOW + LEASE,
        )


def test_a_stale_running_job_can_be_reclaimed() -> None:
    claimed = running_job()

    takeover = claimed.claim(
        owner="worker-2",
        at=NOW + LEASE,
        lease_until=NOW + LEASE * 2,
    )

    assert takeover.lease_owner == "worker-2"
    assert takeover.attempt == 2
    assert takeover.started_at == NOW


def test_a_terminal_job_cannot_be_claimed_or_failed_again() -> None:
    finished = running_job().complete(
        report=make_report(), counters=NewsCurationCounters(), at=NOW
    )

    with pytest.raises(NewsCurationJobTransitionError):
        finished.claim(owner="worker-2", at=NOW, lease_until=NOW + LEASE)
    with pytest.raises(NewsCurationJobTransitionError):
        finished.fail(
            category=NewsCurationErrorCategory.EXECUTION_FAILED,
            message="No.",
            at=NOW,
        )


def test_progress_is_recorded_only_while_running() -> None:
    job = make_job()
    with pytest.raises(NewsCurationJobTransitionError):
        job.record_progress(
            stage=NewsCurationStage.CURATING_ITEMS,
            message="Curating.",
            counters=NewsCurationCounters(),
        )

    progressed = running_job().record_progress(
        stage=NewsCurationStage.CURATING_ITEMS,
        message="Checking and curating eligible stories.",
        counters=NewsCurationCounters(sources_configured=1, items_fetched=2),
    )

    assert progressed.stage is NewsCurationStage.CURATING_ITEMS
    assert progressed.counters.items_fetched == 2


def test_checkpoint_keeps_finished_work_and_requeues_the_remainder() -> None:
    report = make_report()

    checkpointed = running_job().checkpoint(
        report=report,
        counters=counters_for(report, sources_configured=3),
        next_source_index=1,
        at=NOW,
        message="Continuing.",
    )

    assert checkpointed.status is NewsCurationJobStatus.QUEUED
    assert checkpointed.stage is NewsCurationStage.QUEUED
    assert checkpointed.next_source_index == 1
    assert checkpointed.report == report
    assert checkpointed.lease_owner is None
    assert checkpointed.started_at == NOW
    assert checkpointed.attempt == 1


def test_completion_reports_success_or_partial_failure() -> None:
    succeeded = running_job().complete(
        report=make_report(),
        counters=NewsCurationCounters(sources_configured=1, sources_processed=1),
        at=NOW,
    )
    partial = running_job().complete(
        report=make_report(failures=(NewsItemOutcome("A", "B", "", "failed"),)),
        counters=NewsCurationCounters(sources_configured=1, sources_processed=1),
        at=NOW,
    )

    assert succeeded.status is NewsCurationJobStatus.SUCCEEDED
    assert succeeded.stage is NewsCurationStage.DONE
    assert succeeded.finished_at == NOW
    assert partial.status is NewsCurationJobStatus.PARTIALLY_SUCCEEDED
    source_failure = running_job().complete(
        report=make_report(source_failures=(NewsSourceFailure("A", "unreadable"),)),
        counters=NewsCurationCounters(),
        at=NOW,
    )
    assert source_failure.status is NewsCurationJobStatus.PARTIALLY_SUCCEEDED


def test_failure_is_bounded_and_carries_a_controlled_category() -> None:
    failed = running_job().fail(
        category=NewsCurationErrorCategory.EXECUTION_FAILED,
        message="The curation run could not be completed.",
        at=NOW,
    )

    assert failed.status is NewsCurationJobStatus.FAILED
    assert failed.stage is NewsCurationStage.FAILED
    assert failed.error_category is NewsCurationErrorCategory.EXECUTION_FAILED
    assert failed.finished_at == NOW
    with pytest.raises(ValueError):
        running_job().fail(
            category=NewsCurationErrorCategory.EXECUTION_FAILED,
            message="x" * 400,
            at=NOW,
        )


def test_a_queued_job_becomes_stale_after_it_waits_too_long() -> None:
    job = make_job()

    assert not job.is_stale(NOW)
    assert job.is_stale(NOW + QUEUED_JOB_STALE_AFTER)


# --- Job repository ---------------------------------------------------------


def test_repository_start_allows_only_one_active_job() -> None:
    repository = InMemoryNewsCurationJobRepository()
    first = make_job()

    assert repository.start(first) is first
    assert repository.start(make_job()) is None
    assert repository.find_active() == first
    assert repository.latest() == first


def test_repository_refuses_to_rewrite_a_terminal_job() -> None:
    repository = InMemoryNewsCurationJobRepository()
    job = make_job()
    repository.start(job)
    finished = job.claim(owner="worker-1", at=NOW, lease_until=NOW + LEASE).complete(
        report=make_report(), counters=NewsCurationCounters(), at=NOW
    )
    repository.save(finished)

    with pytest.raises(NewsCurationJobTransitionError):
        repository.save(replace(job, message="A different queued job."))


def test_repository_claim_is_a_no_op_for_terminal_and_leased_jobs() -> None:
    repository = InMemoryNewsCurationJobRepository()
    job = make_job()
    repository.start(job)
    claimed = repository.claim(
        job.job_id, owner="worker-1", now=NOW, lease_until=NOW + LEASE
    )
    assert claimed is not None

    assert (
        repository.claim(job.job_id, owner="worker-2", now=NOW, lease_until=NOW + LEASE)
        is None
    )
    assert (
        repository.claim(uuid4(), owner="worker-1", now=NOW, lease_until=NOW + LEASE)
        is None
    )


def test_an_overtaken_worker_cannot_overwrite_a_newer_attempt() -> None:
    repository = InMemoryNewsCurationJobRepository()
    job = make_job()
    repository.start(job)
    first = repository.claim(
        job.job_id,
        owner="worker-1",
        now=NOW - LEASE,
        lease_until=NOW,
    )
    takeover = repository.claim(
        job.job_id,
        owner="worker-2",
        now=NOW,
        lease_until=NOW + LEASE,
    )
    assert first is not None and takeover is not None

    stale = first.record_progress(
        stage=NewsCurationStage.CURATING_ITEMS,
        message="Checking and curating eligible stories.",
        counters=NewsCurationCounters(),
    )

    with pytest.raises(NewsCurationJobTransitionError, match="newer attempt"):
        repository.save(stale)
    assert repository.get(job.job_id) == takeover


def test_repository_allows_a_stale_lease_takeover() -> None:
    repository = InMemoryNewsCurationJobRepository()
    job = make_job()
    repository.start(job)
    repository.claim(job.job_id, owner="worker-1", now=NOW, lease_until=NOW + LEASE)

    takeover = repository.claim(
        job.job_id,
        owner="worker-2",
        now=NOW + LEASE,
        lease_until=NOW + LEASE * 2,
    )

    assert takeover is not None
    assert takeover.lease_owner == "worker-2"
    assert takeover.attempt == 2


# --- Report merging ---------------------------------------------------------


def test_reports_merge_into_one_accumulated_report() -> None:
    first = make_report(fetched=2, published=1, deduplicated=1)
    second = make_report(
        sources_configured=1,
        sources_processed=1,
        fetched=1,
        rejected=1,
        rejections=(NewsItemOutcome("B", "C", "https://b.example.com/1", "too old"),),
    )

    merged = merge_reports(
        first, second, sources_configured=2, started_at=NOW - timedelta(minutes=5)
    )

    assert merged.sources_processed == 2
    assert merged.sources_configured == 2
    assert merged.fetched == 3
    assert merged.published == 1
    assert merged.rejected == 1
    assert merged.rejections[0].reason == "too old"
    assert merged.started_at == NOW - timedelta(minutes=5)


# --- Job service ------------------------------------------------------------


def test_start_persists_the_job_before_dispatch_and_returns_it() -> None:
    curator, _, _ = make_curator()
    repository = InMemoryNewsCurationJobRepository()
    captured: list[NewsCurationJob | None] = []

    class InspectingDispatcher(RecordingDispatcher):
        def dispatch(self, job_id: UUID) -> None:
            captured.append(repository.get(job_id))
            super().dispatch(job_id)

    dispatcher = InspectingDispatcher()
    service, _, _ = make_service(
        curator=curator, repository=repository, dispatcher=dispatcher
    )

    job = service.start()

    assert captured and captured[0] is not None
    assert captured[0].status is NewsCurationJobStatus.QUEUED
    assert repository.get(job.job_id) is job
    assert dispatcher.dispatched == [job.job_id]


def test_dispatch_failure_is_persisted_truthfully() -> None:
    curator, _, _ = make_curator()
    dispatcher = RecordingDispatcher(error=RuntimeError("queue unavailable"))
    service, repository, _ = make_service(curator=curator, dispatcher=dispatcher)

    with pytest.raises(NewsCurationDispatchError):
        service.start()

    assert repository.find_active() is None
    failed = repository.latest()
    assert failed is not None
    assert failed.status is NewsCurationJobStatus.FAILED
    assert failed.error_category is NewsCurationErrorCategory.DISPATCH_FAILED
    assert "queue unavailable" not in (failed.error_message or "")


def test_a_second_start_is_refused_while_a_job_is_active() -> None:
    curator, _, _ = make_curator()
    service, repository, dispatcher = make_service(curator=curator)
    first = service.start()

    with pytest.raises(NewsCurationInProgressError):
        service.start()

    assert len(dispatcher.dispatched) == 1
    assert repository.find_active() == first


def test_a_stale_active_job_is_recovered_before_a_new_start() -> None:
    curator, _, _ = make_curator()
    service, repository, _ = make_service(curator=curator)
    stale = make_job(created_at=NOW - QUEUED_JOB_STALE_AFTER, job_id=uuid4())
    repository.start(stale)

    started = service.start()

    recovered = repository.get(stale.job_id)
    assert recovered is not None
    assert recovered.status is NewsCurationJobStatus.FAILED
    assert recovered.error_category is NewsCurationErrorCategory.INTERRUPTED
    assert started.job_id != stale.job_id
    assert repository.find_active() == started


def test_task_execution_publishes_stories_and_finalizes_the_job() -> None:
    curator, stories, provider = make_curator()
    service, repository, _ = make_service(curator=curator)
    job = service.start()

    finished = service.handle_task(job.job_id, owner="worker-1")

    assert finished is not None
    assert finished.status is NewsCurationJobStatus.SUCCEEDED
    assert finished.report is not None
    assert finished.report.published == 1
    assert finished.counters.items_published == 1
    assert finished.counters.sources_processed == 1
    assert finished.counters.sources_configured == 1
    assert len(stories.list_stories()) == 1
    assert len(provider.requests) == 1
    assert repository.get(job.job_id) == finished


def test_duplicate_delivery_after_completion_does_nothing() -> None:
    curator, stories, provider = make_curator()
    service, _, _ = make_service(curator=curator)
    job = service.start()
    first = service.handle_task(job.job_id, owner="worker-1")
    assert first is not None and first.is_terminal

    duplicate = service.handle_task(job.job_id, owner="worker-2")

    assert duplicate == first
    assert len(provider.requests) == 1
    assert len(stories.list_stories()) == 1


def test_duplicate_delivery_while_leased_does_not_run_again() -> None:
    curator, _, provider = make_curator()
    repository = InMemoryNewsCurationJobRepository()
    dispatcher = RecordingDispatcher()
    queue_service, _, _ = make_service(
        curator=curator, repository=repository, dispatcher=dispatcher
    )
    job = queue_service.start()

    # A second worker acknowledged the same task while the first lease is live.
    claimed = repository.claim(
        job.job_id, owner="worker-1", now=NOW, lease_until=NOW + LEASE
    )
    assert claimed is not None

    duplicate = queue_service.handle_task(job.job_id, owner="worker-2")

    assert duplicate == claimed
    assert provider.requests == []


def test_a_stale_lease_is_taken_over_and_completes_the_job() -> None:
    curator, _, provider = make_curator()
    service, repository, _ = make_service(curator=curator)
    job = service.start()
    repository.claim(
        job.job_id,
        owner="dead-worker",
        now=NOW - LEASE,
        lease_until=NOW,
    )

    recovered = service.handle_task(job.job_id, owner="fresh-worker")

    assert recovered is not None
    assert recovered.status is NewsCurationJobStatus.SUCCEEDED
    assert recovered.attempt == 2
    assert len(provider.requests) == 1


def test_a_large_batch_is_split_into_bounded_resumable_units() -> None:
    second_item = make_item(
        source_name=SOURCE_B.name,
        title="Atelier notes on repair and reuse",
        url="https://atelier.example.com/story/1",
        excerpt="Studios are keeping garments in use for longer.",
    )
    curator, stories, _ = make_curator(
        sources=(SOURCE_A, SOURCE_B),
        items=(make_item(), second_item),
    )
    service, repository, dispatcher = make_service(
        curator=curator, max_sources_per_task=1
    )

    accepted = service.start()
    checkpoint = service.handle_task(accepted.job_id, owner="worker-1")

    assert checkpoint is not None
    assert checkpoint.status is NewsCurationJobStatus.QUEUED
    assert checkpoint.next_source_index == 1
    assert checkpoint.counters.sources_processed == 1
    assert checkpoint.report is not None
    assert checkpoint.report.sources_configured == 2
    assert dispatcher.dispatched == [accepted.job_id, accepted.job_id]

    finished = service.handle_task(accepted.job_id, owner="worker-2")

    assert finished is not None
    assert finished.status is NewsCurationJobStatus.SUCCEEDED
    assert finished.next_source_index == 1
    assert finished.counters.sources_processed == 2
    assert finished.report is not None
    assert finished.report.sources_processed == 2
    assert len(stories.list_stories()) == 2


def test_job_state_is_shared_across_separately_constructed_services() -> None:
    curator, _, _ = make_curator()
    repository = InMemoryNewsCurationJobRepository()
    accepting, _, _ = make_service(
        curator=curator, repository=repository, dispatcher=RecordingDispatcher()
    )
    accepted = accepting.start()

    executing, _, _ = make_service(
        curator=curator, repository=repository, dispatcher=RecordingDispatcher()
    )

    assert executing.get(accepted.job_id) == accepted
    finished = executing.handle_task(accepted.job_id, owner="worker-1")
    assert finished is not None
    assert finished.is_terminal


def test_execution_failure_is_safe_and_preserves_existing_stories() -> None:
    curator, stories, _ = make_curator()
    service, repository, _ = make_service(curator=curator)
    published = service.start()
    completed = service.handle_task(published.job_id, owner="worker-1")
    assert completed is not None
    assert completed.status is NewsCurationJobStatus.SUCCEEDED
    existing_stories = stories.list_stories()
    assert existing_stories

    provider = FakeNewsCurationProvider()
    failing_service, _, _ = make_service(
        repository=repository,
        curator=ExplodingCurator(
            repository=stories,
            fetcher=FakeNewsSourceFetcher(default=(make_item(),)),
            provider=provider,
            sources=(SOURCE_A,),
            clock=lambda: NOW,
        ),
    )
    failed_job = failing_service.start()

    failed = failing_service.handle_task(failed_job.job_id, owner="worker-1")

    assert failed is not None
    assert failed.status is NewsCurationJobStatus.FAILED
    assert failed.error_category is NewsCurationErrorCategory.EXECUTION_FAILED
    assert failed.error_message == (
        "The curation run could not be completed. Existing stories are unchanged."
    )
    assert "secret upstream payload" not in (failed.error_message or "")
    assert stories.list_stories() == existing_stories


def test_an_unknown_job_task_is_a_safe_no_op() -> None:
    curator, _, _ = make_curator()
    service, _, _ = make_service(curator=curator)

    assert service.handle_task(uuid4(), owner="worker-1") is None
