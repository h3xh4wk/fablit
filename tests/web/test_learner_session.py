"""Regression tests for the learner application registry (SPEC-024 §6, SPEC-035 §9).

Resolving an anonymous learner identity builds a learner-scoped
``PracticeApplication``. Building it refreshes the published learner library
from the shared ``PublishedPracticeStore``, so the registry's own lock was
acquired twice on the same request. A non-re-entrant lock deadlocked the
request thread there: the learner dashboard never answered, the request loop
froze, and every browser journey timed out.

The tests below run the resolution under a timeout, so a deadlock fails the
test instead of hanging the whole suite.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.learner_session import DemoContent, LearnerApplicationRegistry
from app.main import create_app
from fablit.application import (
    PRACTICE_CAPABILITY_OBSERVE,
    AuthoringCandidateStore,
    InMemoryPublishedPracticeStore,
    PracticeAuthoringBrief,
    PracticeMode,
    PublishedPractice,
    PublishedPracticeStore,
    draft_candidate_from_brief,
    publish_candidate,
)
from fablit.application.persistence import PersistenceError
from fablit.config import load_config

#: Generous enough for a slow CI machine, short enough that a deadlock
#: fails the test instead of stalling the suite.
TIMEOUT_SECONDS = 10.0


def _completes_within[T](seconds: float, action: Callable[[], T]) -> T:
    """Run an action in a worker thread and fail when it does not return.

    A registry deadlock blocks the request thread forever, so the action runs
    with a timeout: the test fails fast rather than hanging.
    """
    outcome: list[T] = []
    failure: list[BaseException] = []

    def runner() -> None:
        try:
            outcome.append(action())
        except Exception as exc:
            failure.append(exc)

    worker = threading.Thread(target=runner, daemon=True)
    worker.start()
    worker.join(timeout=seconds)
    if worker.is_alive():
        raise AssertionError(
            f"the action did not complete within {seconds}s (deadlock)"
        )
    if failure:
        raise failure[0]
    return outcome[0]


def _registry(
    store: PublishedPracticeStore | None = None,
    refresh_interval_seconds: float = 0.0,
) -> LearnerApplicationRegistry:
    """A registry over the seeded library, with a publication store attached."""
    return LearnerApplicationRegistry(
        DemoContent.build(load_config()),
        None,
        None,
        store=store if store is not None else InMemoryPublishedPracticeStore(),
        refresh_interval_seconds=refresh_interval_seconds,
    )


def _published_record(store: PublishedPracticeStore) -> PublishedPractice:
    """Publish one approved candidate into the given store."""
    authoring = AuthoringCandidateStore()
    brief = PracticeAuthoringBrief(
        practice_area="Visual analysis",
        practice_purpose="Distinguish visible evidence from interpretation.",
        task="Identify three visible details in the provided stimulus.",
        response_form="A short written observation.",
        primary_capability=PRACTICE_CAPABILITY_OBSERVE,
        practice_mode=PracticeMode.SHORT_DRILL,
        learner_context="A learner practising close observation.",
    )
    candidate = draft_candidate_from_brief(brief)
    authoring.add(candidate)
    authoring.approve(candidate.id, reviewer="reviewer")
    return publish_candidate(
        authoring.get(candidate.id),
        store=store,
        position=12,
    )


class _UnavailableStore(PublishedPracticeStore):
    """A publication store that cannot be read."""

    def save(self, record: PublishedPractice) -> PublishedPractice:
        raise PersistenceError("simulated publication outage")

    def get(self, activity_id: object) -> PublishedPractice | None:
        raise PersistenceError("simulated publication outage")

    def find_by_candidate(self, candidate_id: object) -> PublishedPractice | None:
        return None

    def list_records(self) -> tuple[PublishedPractice, ...]:
        raise PersistenceError("simulated publication outage")


class _RecoveringStore(PublishedPracticeStore):
    """A store that fails every read until the simulated outage passes (issue #143)."""

    def __init__(self, inner: InMemoryPublishedPracticeStore) -> None:
        self._inner = inner
        self.available = False

    def save(self, record: PublishedPractice) -> PublishedPractice:
        return self._inner.save(record)

    def get(self, activity_id: UUID) -> PublishedPractice | None:
        if not self.available:
            raise PersistenceError("simulated transient publication outage")
        return self._inner.get(activity_id)

    def find_by_candidate(self, candidate_id: UUID) -> PublishedPractice | None:
        if not self.available:
            raise PersistenceError("simulated transient publication outage")
        return self._inner.find_by_candidate(candidate_id)

    def list_records(self) -> tuple[PublishedPractice, ...]:
        if not self.available:
            raise PersistenceError("simulated transient publication outage")
        return self._inner.list_records()


# --- Deadlock regression -----------------------------------------------------


def test_new_learner_application_is_built_without_deadlock() -> None:
    """Building a learner's application never blocks the requesting thread."""
    registry = _registry()
    learner_id = uuid4()

    application = _completes_within(
        TIMEOUT_SECONDS, lambda: registry.application_for(learner_id)
    )

    assert application.get_dashboard().activities


def test_dashboard_answers_a_new_learner_without_hanging() -> None:
    """The dashboard answers a fresh learner (the browser-job symptom)."""

    def fetch() -> str:
        test_app = create_app(load_config())
        with TestClient(test_app) as client:
            response = client.get("/")
            assert response.status_code == 200
            return response.text

    body = _completes_within(TIMEOUT_SECONDS, fetch)

    assert "What would you like to explore?" in body


def test_several_learners_resolve_concurrently_without_deadlock() -> None:
    """Concurrent learners never block each other on the registry lock."""
    registry = _registry()
    learner_ids = [uuid4() for _ in range(8)]

    def resolve() -> list[int]:
        return [
            len(registry.application_for(learner_id).get_dashboard().activities)
            for learner_id in learner_ids
        ]

    counts = _completes_within(TIMEOUT_SECONDS, resolve)

    assert all(count > 0 for count in counts)


# --- Publication refresh (SPEC-035 §9) ---------------------------------------


def test_new_learner_sees_publications_refreshed_from_the_store() -> None:
    """A fresh learner sees the latest published library."""
    published = InMemoryPublishedPracticeStore()
    record = _published_record(published)
    registry = _registry(store=published)

    application = _completes_within(
        TIMEOUT_SECONDS, lambda: registry.application_for(uuid4())
    )

    titles = [item.title for item in application.get_dashboard().activities]
    assert record.activity.title in titles


def test_unavailable_publication_store_does_not_block_learner_requests() -> None:
    """A store that cannot be read degrades to the seeded library."""
    registry = _registry(store=_UnavailableStore())

    application = _completes_within(
        TIMEOUT_SECONDS, lambda: registry.application_for(uuid4())
    )

    assert application.get_dashboard().activities


def test_existing_learner_sees_publications_from_another_instance() -> None:
    """An existing learner picks up publications made by another instance."""
    published = InMemoryPublishedPracticeStore()
    registry_a = _registry(store=published)
    registry_b = _registry(store=published)
    learner_id = uuid4()

    app_a = _completes_within(
        TIMEOUT_SECONDS,
        lambda: registry_a.application_for(learner_id),
    )
    titles_before = [item.title for item in app_a.get_dashboard().activities]

    record = _published_record(published)
    app_b = _completes_within(
        TIMEOUT_SECONDS,
        lambda: registry_b.application_for(uuid4()),
    )
    assert record.activity.title in [
        item.title for item in app_b.get_dashboard().activities
    ]

    app_a_after = _completes_within(
        TIMEOUT_SECONDS,
        lambda: registry_a.application_for(learner_id),
    )
    titles_after = [item.title for item in app_a_after.get_dashboard().activities]
    assert record.activity.title in titles_after
    assert len(titles_after) == len(titles_before) + 1


def test_existing_learner_sees_withdrawals_from_another_instance() -> None:
    """An existing learner sees withdrawals made by another instance."""
    from fablit.application.publishing import withdraw_publication

    published = InMemoryPublishedPracticeStore()
    record = _published_record(published)
    registry_a = _registry(store=published)
    registry_b = _registry(store=published)
    learner_id = uuid4()

    app_a = _completes_within(
        TIMEOUT_SECONDS,
        lambda: registry_a.application_for(learner_id),
    )
    assert record.activity.title in [
        item.title for item in app_a.get_dashboard().activities
    ]

    withdraw_publication(record.source_candidate_id, store=published)

    _completes_within(
        TIMEOUT_SECONDS,
        lambda: registry_b.application_for(uuid4()),
    )
    app_a_after = _completes_within(
        TIMEOUT_SECONDS,
        lambda: registry_a.application_for(learner_id),
    )
    titles_after = [item.title for item in app_a_after.get_dashboard().activities]
    assert record.activity.title not in titles_after


def test_instance_recovers_publications_after_a_transient_store_outage() -> None:
    """An instance that starts during an outage recovers without a restart.

    Issue #143: a store-read failure must not permanently pin an instance to
    an empty publication snapshot.
    """
    published = InMemoryPublishedPracticeStore()
    record = _published_record(published)
    store = _RecoveringStore(published)
    registry = _registry(store=store)
    learner_id = uuid4()

    during_outage = _completes_within(
        TIMEOUT_SECONDS, lambda: registry.application_for(learner_id)
    )
    assert record.activity.title not in [
        item.title for item in during_outage.get_dashboard().activities
    ]

    store.available = True

    after_recovery = _completes_within(
        TIMEOUT_SECONDS, lambda: registry.application_for(learner_id)
    )
    assert record.activity.title in [
        item.title for item in after_recovery.get_dashboard().activities
    ]


def test_registry_orders_position_ties_deterministically() -> None:
    """Equal positions still render one deterministic catalogue order.

    Positions are advisory hints allocated per instance (issue #144), so
    concurrent publications can share one; the registry breaks the tie the
    same way as ``PublishedPracticeStore.list_records``.
    """
    published = InMemoryPublishedPracticeStore()
    # Both publications receive the same catalogue position.
    first = _published_record(published)
    second = _published_record(published)
    earlier, later = sorted(
        (first, second),
        key=lambda record: (record.published_at, str(record.activity_id)),
    )
    registry = _registry(store=published)
    # Insert in reverse order: only the full tie-break key can render the
    # deterministic order (dict insertion order alone would not).
    registry.record_publication(later)
    registry.record_publication(earlier)

    assert [record.activity_id for record in registry.publications] == [
        earlier.activity_id,
        later.activity_id,
    ]
