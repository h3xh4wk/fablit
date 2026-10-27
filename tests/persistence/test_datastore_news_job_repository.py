"""Contract tests for the SPEC-042 Datastore curation job repository.

The fake client models Datastore's indexed-string limit and the transactional
surface the adapter relies on. No test needs GCP credentials.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fablit.application.errors import NewsCurationJobTransitionError
from fablit.application.news import (
    NewsBatchResult,
    NewsCurationDiagnostics,
    NewsItemOutcome,
    NewsProviderOutcome,
    NewsSourceFailure,
)
from fablit.application.news_jobs import (
    NewsCurationCounters,
    NewsCurationErrorCategory,
    NewsCurationJob,
    NewsCurationJobStatus,
    NewsCurationStage,
    counters_for,
)
from fablit.application.persistence import PersistenceError
from fablit.platform.datastore_news_job_repository import (
    ACTIVE_POINTER_NAME,
    DEFAULT_NEWS_JOB_NAMESPACE,
    NEWS_JOB_ACTIVE_KIND,
    NEWS_JOB_KIND,
    DatastoreNewsCurationJobRepository,
    deserialize_news_job,
    serialize_news_job,
)
from tests.persistence.test_datastore_authoring_store import FakeDatastoreClient

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
LEASE = timedelta(minutes=5)


def make_report(**overrides: object) -> NewsBatchResult:
    values: dict[str, object] = {
        "started_at": NOW,
        "finished_at": NOW + timedelta(minutes=1),
        "sources_configured": 1,
        "sources_processed": 1,
        "fetched": 2,
        "published": 1,
        "rejected": 1,
    }
    values.update(overrides)
    return NewsBatchResult(**values)  # type: ignore[arg-type]


def make_job(**overrides: object) -> NewsCurationJob:
    values: dict[str, object] = {"job_id": uuid4(), "created_at": NOW}
    values.update(overrides)
    return NewsCurationJob(**values)  # type: ignore[arg-type]


def running(job: NewsCurationJob) -> NewsCurationJob:
    return job.claim(owner="worker-1", at=NOW, lease_until=NOW + LEASE)


def test_queued_job_round_trips_in_the_news_namespace() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsCurationJobRepository(client)
    job = make_job()

    assert repository.start(job) is job

    loaded = repository.get(job.job_id)
    assert loaded == job
    entity = client.get(
        client.key(NEWS_JOB_KIND, str(job.job_id), namespace=DEFAULT_NEWS_JOB_NAMESPACE)
    )
    assert entity is not None
    assert entity.key is not None
    assert entity.key.namespace == "news"
    assert entity["status"] == "queued"


def test_job_state_is_visible_across_repository_instances() -> None:
    client = FakeDatastoreClient()
    accepting_repository = DatastoreNewsCurationJobRepository(client)
    executing_repository = DatastoreNewsCurationJobRepository(client)
    job = make_job()

    assert accepting_repository.start(job) == job
    assert executing_repository.get(job.job_id) == job

    claimed = executing_repository.claim(
        job.job_id,
        owner="worker-1",
        now=NOW,
        lease_until=NOW + LEASE,
    )
    assert claimed is not None
    finished = claimed.complete(
        report=make_report(),
        counters=NewsCurationCounters(sources_configured=1, sources_processed=1),
        at=NOW + timedelta(minutes=1),
    )
    executing_repository.save(finished)

    assert accepting_repository.get(job.job_id) == finished
    assert accepting_repository.latest() == finished
    assert accepting_repository.find_active() is None


def test_running_job_round_trips_with_its_lease() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsCurationJobRepository(client)
    repository.start(make_job())
    claimed = repository.claim(
        repository.latest().job_id,  # type: ignore[union-attr]
        owner="worker-1",
        now=NOW,
        lease_until=NOW + LEASE,
    )
    assert claimed is not None

    loaded = repository.get(claimed.job_id)

    assert loaded == claimed
    assert loaded is not None
    assert loaded.lease_owner == "worker-1"
    assert loaded.attempt == 1


def test_only_one_active_job_can_be_started() -> None:
    repository = DatastoreNewsCurationJobRepository(FakeDatastoreClient())
    first = make_job()

    assert repository.start(first) is first
    assert repository.start(make_job()) is None
    assert repository.find_active() == first


def test_a_terminal_job_releases_the_active_pointer() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsCurationJobRepository(client)
    job = make_job()
    repository.start(job)
    claimed = repository.claim(
        job.job_id, owner="worker-1", now=NOW, lease_until=NOW + LEASE
    )
    assert claimed is not None
    finished = claimed.complete(
        report=make_report(),
        counters=NewsCurationCounters(sources_configured=1, sources_processed=1),
        at=NOW,
    )

    repository.save(finished)

    assert repository.find_active() is None
    assert (
        client.get(
            client.key(
                NEWS_JOB_ACTIVE_KIND,
                ACTIVE_POINTER_NAME,
                namespace=DEFAULT_NEWS_JOB_NAMESPACE,
            )
        )
        is None
    )
    assert repository.start(make_job()) is not None


def test_claim_is_refused_for_terminal_and_leased_jobs() -> None:
    repository = DatastoreNewsCurationJobRepository(FakeDatastoreClient())
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


def test_a_stale_lease_can_be_taken_over() -> None:
    repository = DatastoreNewsCurationJobRepository(FakeDatastoreClient())
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


def test_an_overtaken_worker_cannot_overwrite_a_newer_attempt() -> None:
    repository = DatastoreNewsCurationJobRepository(FakeDatastoreClient())
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


def test_a_terminal_job_cannot_be_rewritten() -> None:
    repository = DatastoreNewsCurationJobRepository(FakeDatastoreClient())
    job = make_job()
    repository.start(job)
    claimed = repository.claim(
        job.job_id, owner="worker-1", now=NOW, lease_until=NOW + LEASE
    )
    assert claimed is not None
    finished = claimed.complete(
        report=make_report(), counters=NewsCurationCounters(), at=NOW
    )
    repository.save(finished)

    with pytest.raises(NewsCurationJobTransitionError):
        repository.save(job)


def test_the_full_report_and_operator_copy_are_stored_unindexed() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsCurationJobRepository(client)
    report = make_report(
        rejections=(
            NewsItemOutcome(
                source_name="The Daily Weave",
                title="A" * 200,
                url="https://news.example.com/story/1",
                reason="story is older than the freshness window",
            ),
        ),
        failures=(
            NewsItemOutcome(
                source_name="The Daily Weave",
                title="B" * 200,
                url="https://news.example.com/story/2",
                reason="curation provider failed",
            ),
        ),
        source_failures=(
            NewsSourceFailure(
                source_name="The Daily Weave",
                reason="source could not be retrieved",
            ),
        ),
    )
    job = make_job(
        message="M" * 500,
        counters=counters_for(report, sources_configured=1),
    )
    repository.start(job)
    claimed = repository.claim(
        job.job_id, owner="worker-1", now=NOW, lease_until=NOW + LEASE
    )
    assert claimed is not None
    finished = claimed.complete(
        report=report,
        counters=counters_for(report, sources_configured=1),
        at=NOW,
    )

    repository.save(finished)
    loaded = repository.get(job.job_id)

    assert loaded is not None
    assert loaded.status is NewsCurationJobStatus.PARTIALLY_SUCCEEDED
    assert loaded.stage is NewsCurationStage.DONE
    assert loaded.report is not None
    assert loaded.report.rejections[0].reason.startswith("story is older")
    assert loaded.report.failures[0].reason == "curation provider failed"
    assert loaded.report.source_failures[0].source_name == "The Daily Weave"
    assert loaded.counters.items_rejected == 1


def test_a_failed_job_persists_only_its_safe_diagnostic() -> None:
    repository = DatastoreNewsCurationJobRepository(FakeDatastoreClient())
    job = make_job()
    repository.start(job)
    claimed = repository.claim(
        job.job_id, owner="worker-1", now=NOW, lease_until=NOW + LEASE
    )
    assert claimed is not None
    failed = claimed.fail(
        category=NewsCurationErrorCategory.EXECUTION_FAILED,
        message=(
            "The curation run could not be completed. Existing stories are unchanged."
        ),
        at=NOW,
    )

    repository.save(failed)
    loaded = repository.get(job.job_id)

    assert loaded is not None
    assert loaded.status is NewsCurationJobStatus.FAILED
    assert loaded.error_category is NewsCurationErrorCategory.EXECUTION_FAILED
    assert "Existing stories are unchanged" in (loaded.error_message or "")


def test_storage_failures_are_reported_as_persistence_errors() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsCurationJobRepository(client)
    job = make_job()

    client.fail_next_put = True
    with pytest.raises(PersistenceError):
        repository.start(job)

    repository.start(job)
    client.fail_next_get = True
    with pytest.raises(PersistenceError):
        repository.get(job.job_id)

    client.fail_query = True
    with pytest.raises(PersistenceError):
        repository.latest()
    with pytest.raises(PersistenceError):
        repository.find_active()


def test_unknown_and_malformed_identities_are_safe() -> None:
    repository = DatastoreNewsCurationJobRepository(FakeDatastoreClient())

    assert repository.get(uuid4()) is None
    assert repository.get("not-a-uuid") is None  # type: ignore[arg-type]
    assert repository.latest() is None
    assert repository.find_active() is None


def test_serialization_round_trip_matches_the_model() -> None:
    job = running(make_job())

    restored = deserialize_news_job(serialize_news_job(job))

    assert restored == job


def test_completed_job_round_trips_with_retries_and_diagnostics() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsCurationJobRepository(client)
    diag = NewsCurationDiagnostics(
        provider_id="google-gemini",
        model_id="gemini-2.5-flash",
        provider_retries=3,
        transient_retries_recovered=2,
        exhausted_retries=1,
        provider_outcome=NewsProviderOutcome.RETRIES_EXHAUSTED,
        last_status_code=429,
    )
    report = make_report(
        provider_retries=3,
        diagnostics=diag,
        failed=1,
        failures=(
            NewsItemOutcome(
                "A", "Title", "https://a.com/1", "curation provider retries exhausted"
            ),
        ),
    )
    counters = NewsCurationCounters(
        sources_configured=1,
        sources_processed=1,
        items_fetched=2,
        items_published=1,
        items_failed=1,
        provider_retries=3,
    )
    job = running(make_job()).complete(
        report=report, counters=counters, at=NOW + timedelta(minutes=2)
    )

    repository.start(make_job(job_id=job.job_id))
    repository.save(job)

    loaded = repository.get(job.job_id)
    assert loaded is not None
    assert loaded == job
    assert loaded.counters.provider_retries == 3
    assert loaded.diagnostics == diag
