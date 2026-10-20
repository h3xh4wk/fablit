"""Publication boundary tests (SPEC-035): approved → published → learner library.

The tests cover both sides of the boundary — the publication rules that keep
unapproved content out of the learner library, and the learner-facing
reconciliation that makes an explicit publication discoverable and
completable through the ordinary practice journey.
"""

from __future__ import annotations

import dataclasses
import threading
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from fablit.application.authoring import (
    AuthoringCandidateStore,
    PracticeAuthoringBrief,
    candidate_from_provider_output,
    draft_candidate_from_brief,
)
from fablit.application.demo_data import (
    PRACTICE_CAPABILITY_OBSERVE,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
)
from fablit.application.demo_evaluator import DemoEvaluator
from fablit.application.errors import (
    CandidateContentNotPublishableError,
    CandidateNotPublishableError,
    InvalidPublishedPracticeError,
    PublishedPracticeNotFoundError,
)
from fablit.application.persistence import PersistenceError
from fablit.application.practice_modes import PracticeMode
from fablit.application.publishing import (
    InMemoryPublishedPracticeStore,
    PublishableCandidate,
    PublishedPractice,
    PublishedPracticeStore,
    load_publications,
    publish_candidate,
    withdraw_publication,
)
from fablit.application.repositories import InMemoryPracticeHistoryRepository
from fablit.application.stimulus import build_stimulus_provider
from fablit.application.store import LearnerJourneyStore, PracticeContentContract
from fablit.application.use_cases import PracticeApplication

BANNED_LEARNER_LANGUAGE = ("score", "grade", "mastery", "streak", "ranking")


def _brief(**overrides: Any) -> PracticeAuthoringBrief:
    values: dict[str, Any] = {
        "practice_area": "Visual analysis",
        "practice_purpose": "Distinguish visible evidence from interpretation.",
        "task": "Identify three visible details in the provided stimulus.",
        "response_form": "A short written observation.",
        "primary_capability": PRACTICE_CAPABILITY_OBSERVE,
        "practice_mode": PracticeMode.SHORT_DRILL,
        "learner_context": "A learner practising close observation.",
    }
    values.update(overrides)
    return PracticeAuthoringBrief(**values)


def _authoring_store() -> AuthoringCandidateStore:
    return AuthoringCandidateStore()


def _add(
    store: AuthoringCandidateStore,
    *,
    overrides: dict[str, Any] | None = None,
) -> UUID:
    brief = _brief(**(overrides or {}))
    candidate = draft_candidate_from_brief(brief)
    store.add(candidate)
    return candidate.id


def _approved(store: AuthoringCandidateStore, **overrides: Any) -> UUID:
    candidate_id = _add(store, overrides=overrides)
    store.approve(candidate_id, reviewer="reviewer")
    return candidate_id


def _publish(
    candidate_id: UUID,
    store: AuthoringCandidateStore,
    published: PublishedPracticeStore,
    *,
    position: int = 12,
    now: datetime | None = None,
) -> PublishedPractice:
    return publish_candidate(
        store.get(candidate_id),
        store=published,
        position=position,
        now=now,
    )


def _application(
    publications: tuple[PublishedPractice, ...] = (),
) -> tuple[PracticeApplication, LearnerJourneyStore]:
    """Build a learner application over the seeded library (SPEC-012 pattern)."""
    activities = build_demo_activities()
    store = LearnerJourneyStore(
        learner_id=uuid4(),
        activities=activities,
        skills=build_demo_skills(),
    )
    application = PracticeApplication(
        store=store,
        evaluator=DemoEvaluator(build_demo_activity_map(activities)),
        stimulus_provider=build_stimulus_provider(activities, provider_name="builtin"),
        history_repository=InMemoryPracticeHistoryRepository(),
        publications=publications,
    )
    return application, store


def _dashboard_titles(application: PracticeApplication) -> list[str]:
    return [item.title for item in application.get_dashboard().activities]


# --- Publication rules (SPEC-035 §5) -----------------------------------------


def test_approved_candidate_publishes_as_existing_learner_activity() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()

    record = _publish(candidate_id, authoring, published, position=12)

    assert record.activity_id == record.activity.activity.id
    assert record.source_candidate_id == candidate_id
    assert record.source_revision == 1
    assert record.published_at.tzinfo is not None
    assert record.is_visible and not record.is_withdrawn
    assert published.list_records() == (record,)

    candidate = authoring.get(candidate_id)
    activity = record.activity
    assert activity.title == candidate.title
    assert activity.description == candidate.description
    assert activity.content_contract is candidate.contract
    assert activity.activity.instructions == candidate.contract.task  # type: ignore[union-attr]
    assert activity.primary_capability == PRACTICE_CAPABILITY_OBSERVE
    assert activity.stimulus_context is None
    assert activity.activity.position == 12


def test_published_learner_guidance_is_qualitative_only() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    record = _publish(candidate_id, authoring, InMemoryPublishedPracticeStore())

    guidance = " ".join(
        (
            record.activity.strength,
            record.activity.improvement,
            record.activity.next_step,
        )
    ).lower()
    for banned in BANNED_LEARNER_LANGUAGE:
        assert banned not in guidance


def test_approved_but_unpublished_candidate_stays_out_of_the_library() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()

    assert published.list_records() == ()
    assert published.find_by_candidate(candidate_id) is None
    assert published.visible() == ()


def test_generated_candidate_cannot_be_published() -> None:
    authoring = _authoring_store()
    candidate_id = _add(authoring)
    published = InMemoryPublishedPracticeStore()

    with pytest.raises(CandidateNotPublishableError) as excinfo:
        _publish(candidate_id, authoring, published)

    assert "not approved" in str(excinfo.value)
    assert published.list_records() == ()


def test_candidate_with_validation_errors_cannot_be_published() -> None:
    brief = _brief()
    invalid = candidate_from_provider_output({}, brief, provider="p", model="m")
    assert not invalid.validation.is_approvable
    published = InMemoryPublishedPracticeStore()

    with pytest.raises(CandidateContentNotPublishableError) as excinfo:
        publish_candidate(invalid, store=published, position=12)

    assert "validation errors" in str(excinfo.value)
    assert published.list_records() == ()


def test_rejected_candidate_cannot_be_published() -> None:
    authoring = _authoring_store()
    candidate_id = _add(authoring)
    authoring.reject(candidate_id, reviewer="reviewer")
    published = InMemoryPublishedPracticeStore()

    with pytest.raises(CandidateNotPublishableError) as excinfo:
        _publish(candidate_id, authoring, published)

    assert "status: rejected" in str(excinfo.value)
    assert published.list_records() == ()


def test_edited_candidate_cannot_publish_and_published_content_stays_intact() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()
    original = _publish(candidate_id, authoring, published)
    original_title = original.activity.title

    authoring.edit(candidate_id, title="Edited after approval", editor="a")

    with pytest.raises(CandidateNotPublishableError) as excinfo:
        _publish(candidate_id, authoring, published)
    assert "approve this revision first" in str(excinfo.value)

    stored = published.find_by_candidate(candidate_id)
    assert stored is not None
    assert stored.activity_id == original.activity_id
    assert stored.source_revision == 1
    assert stored.activity.title == original_title
    assert published.list_records() == (original,)


def test_repeated_publish_is_idempotent_and_creates_no_duplicates() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()

    first = _publish(candidate_id, authoring, published)
    second = _publish(candidate_id, authoring, published)

    assert second == first
    assert second.activity_id == first.activity_id
    assert published.list_records() == (first,)


def test_republishing_a_reapproved_revision_replaces_content_in_place() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()
    first = _publish(candidate_id, authoring, published)

    authoring.edit(candidate_id, title="Revised title", editor="a")
    authoring.approve(candidate_id, reviewer="reviewer")
    replacement = _publish(
        candidate_id, authoring, published, now=datetime(2026, 10, 12, tzinfo=UTC)
    )

    assert replacement.activity_id == first.activity_id
    assert replacement.source_revision == 2
    assert replacement.activity.title == "Revised title"
    assert published.list_records() == (replacement,)


def test_withdrawal_removes_discovery_but_keeps_the_publication_record() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()
    record = _publish(candidate_id, authoring, published)

    withdrawn = withdraw_publication(candidate_id, store=published)

    assert withdrawn.is_withdrawn and not withdrawn.is_visible
    assert withdrawn.activity_id == record.activity_id
    assert withdrawn.source_revision == record.source_revision
    assert published.visible() == ()
    assert published.list_records() == (withdrawn,)


def test_withdrawal_is_idempotent() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()
    _publish(candidate_id, authoring, published)

    first = withdraw_publication(candidate_id, store=published)
    second = withdraw_publication(candidate_id, store=published)

    assert second == first


def test_withdrawing_a_never_published_candidate_fails() -> None:
    published = InMemoryPublishedPracticeStore()

    with pytest.raises(PublishedPracticeNotFoundError):
        withdraw_publication(uuid4(), store=published)


def test_republish_after_withdrawal_restores_the_same_identity() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()
    record = _publish(candidate_id, authoring, published)
    withdraw_publication(candidate_id, store=published)

    restored = _publish(candidate_id, authoring, published)

    assert restored.activity_id == record.activity_id
    assert restored.is_visible
    assert restored.published_at == record.published_at
    assert published.list_records() == (restored,)
    assert published.visible() == (restored,)


def test_publishing_an_invalid_position_is_rejected() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()

    with pytest.raises(InvalidPublishedPracticeError):
        publish_candidate(
            authoring.get(candidate_id),
            store=published,
            position=-1,
        )

    assert published.list_records() == ()


def test_storage_failure_is_propagated_and_leaves_no_partial_state() -> None:
    class FailingStore(PublishedPracticeStore):
        def save(self, record: PublishedPractice) -> PublishedPractice:
            raise PersistenceError("simulated outage")

        def get(self, activity_id: UUID) -> PublishedPractice | None:
            raise PersistenceError("simulated outage")

        def find_by_candidate(self, candidate_id: UUID) -> PublishedPractice | None:
            return None

        def list_records(self) -> tuple[PublishedPractice, ...]:
            raise PersistenceError("simulated outage")

    authoring = _authoring_store()
    candidate_id = _approved(authoring)

    with pytest.raises(PersistenceError):
        _publish(candidate_id, authoring, FailingStore())


def test_load_publications_degrades_to_empty_when_store_unavailable() -> None:
    class UnavailableStore(PublishedPracticeStore):
        def save(self, record: PublishedPractice) -> PublishedPractice:
            raise PersistenceError("unavailable")

        def get(self, activity_id: UUID) -> PublishedPractice | None:
            raise PersistenceError("unavailable")

        def find_by_candidate(self, candidate_id: UUID) -> PublishedPractice | None:
            raise PersistenceError("unavailable")

        def list_records(self) -> tuple[PublishedPractice, ...]:
            raise PersistenceError("unavailable")

    assert load_publications(UnavailableStore()) == ()


# --- Publication record invariants (SPEC-035 §8) -----------------------------


def _record() -> PublishedPractice:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    return _publish(candidate_id, authoring, InMemoryPublishedPracticeStore())


def test_publication_record_requires_a_timezone_aware_publish_time() -> None:
    with pytest.raises(InvalidPublishedPracticeError) as excinfo:
        dataclasses.replace(
            _record(), published_at=datetime(2026, 10, 12, 9, tzinfo=None)
        )
    assert "timezone-aware" in str(excinfo.value)


def test_publication_record_rejects_withdrawal_before_publication() -> None:
    record = _record()
    with pytest.raises(InvalidPublishedPracticeError) as excinfo:
        dataclasses.replace(
            record,
            withdrawn_at=record.published_at.replace(year=2000),
        )
    assert "withdrawn before it was published" in str(excinfo.value)


def test_publication_record_requires_a_valid_source_revision() -> None:
    with pytest.raises(InvalidPublishedPracticeError) as excinfo:
        dataclasses.replace(_record(), source_revision=0)
    assert "source revision" in str(excinfo.value)


def test_publication_record_requires_a_valid_source_identity() -> None:
    with pytest.raises(InvalidPublishedPracticeError) as excinfo:
        dataclasses.replace(_record(), source_candidate_id="not-a-uuid")  # type: ignore[arg-type]
    assert "source candidate identity" in str(excinfo.value)


# --- Published practice store behaviour (SPEC-035 §5) ------------------------


def test_in_memory_store_orders_by_position_and_indexes_by_candidate() -> None:
    authoring = _authoring_store()
    first_id = _approved(authoring, practice_area="Observation")
    second_id = _approved(authoring, practice_area="Interpretation")
    published = InMemoryPublishedPracticeStore()

    first = _publish(first_id, authoring, published, position=13)
    second = _publish(second_id, authoring, published, position=12)

    assert published.list_records() == (second, first)
    assert published.find_by_candidate(first_id) == first
    assert published.find_by_candidate(second_id) == second
    assert published.get(first.activity_id) == first
    assert published.get(uuid4()) is None


def test_saving_under_an_existing_identity_replaces_the_record() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()
    first = _publish(candidate_id, authoring, published)
    updated = dataclasses.replace(first, source_revision=2)

    assert published.save(updated) == updated
    assert published.list_records() == (updated,)
    assert published.get(first.activity_id) == updated


# --- Concurrency safety (issue #144) ----------------------------------------

#: Short enough that a stuck race fails fast rather than stalling the suite.
RACE_TIMEOUT_SECONDS = 10.0


def test_concurrent_publish_of_the_same_candidate_shares_one_identity() -> None:
    """Two racing publishers receive the same canonical activity identity.

    The store gate forces both callers past the existence check before
    either saves — the exact issue #144 race window — so the test exercises
    the interleaving deterministically instead of relying on the scheduler.
    """

    class _RaceGateStore(InMemoryPublishedPracticeStore):
        def __init__(self) -> None:
            super().__init__()
            self._gate = threading.Barrier(2, timeout=RACE_TIMEOUT_SECONDS)
            self._gating = True

        def stop_gating(self) -> None:
            """Let later reads through once the two-publisher race is over."""
            self._gating = False

        def find_by_candidate(self, candidate_id: UUID) -> PublishedPractice | None:
            record = super().find_by_candidate(candidate_id)
            if not self._gating:
                return record
            # Both racers observe "not yet published" before either writes;
            # the barrier re-opens for the canonical reload after each save.
            self._gate.wait()
            return record

    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = _RaceGateStore()
    results: list[PublishedPractice] = []
    failures: list[Exception] = []

    def racer() -> None:
        try:
            results.append(
                publish_candidate(
                    authoring.get(candidate_id), store=published, position=12
                )
            )
        except Exception as exc:
            failures.append(exc)

    threads = [threading.Thread(target=racer) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=RACE_TIMEOUT_SECONDS)

    assert not any(thread.is_alive() for thread in threads), "publisher deadlocked"
    published.stop_gating()
    assert not failures, failures
    assert len(results) == 2
    # Both callers get the same canonical activity identity, and the
    # catalogue holds exactly one entry for the candidate.
    assert results[0].activity_id == results[1].activity_id
    listed = published.list_records()
    assert len(listed) == 1
    assert listed[0].activity_id == results[0].activity_id
    assert published.find_by_candidate(candidate_id) == listed[0]


def test_publications_sharing_a_position_order_deterministically() -> None:
    """Concurrent publications that share a position keep a stable order.

    Positions are advisory hints allocated per instance (issue #144); equal
    positions resolve through the deterministic tie-break documented on
    ``PublishedPracticeStore.list_records``.
    """
    authoring = _authoring_store()
    first_id = _approved(authoring, practice_area="Observation")
    second_id = _approved(authoring, practice_area="Interpretation")
    published = InMemoryPublishedPracticeStore()

    # Both publications receive the same position, as concurrent publish
    # requests handled by different instances can allocate.
    first = _publish(first_id, authoring, published, position=12)
    second = _publish(second_id, authoring, published, position=12)

    listed = published.list_records()

    assert len(listed) == 2
    assert {item.activity_id for item in listed} == {
        first.activity_id,
        second.activity_id,
    }
    expected = tuple(
        sorted(
            (first, second),
            key=lambda record: (
                record.activity.activity.position,
                record.published_at,
                str(record.activity_id),
            ),
        )
    )
    assert listed == expected
    assert published.list_records() == listed


# --- Learner discovery and journey (SPEC-035 §7) -----------------------------


def test_published_practice_appears_in_the_learner_dashboard() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    record = _publish(candidate_id, authoring, InMemoryPublishedPracticeStore())

    application, _ = _application(publications=(record,))

    titles = _dashboard_titles(application)
    assert record.activity.title in titles
    assert titles[-1] == record.activity.title  # published content sorts last


def test_application_built_before_publishing_reconciles_on_the_next_call() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    record = _publish(candidate_id, authoring, InMemoryPublishedPracticeStore())

    application, _ = _application()
    assert record.activity.title not in _dashboard_titles(application)

    application.apply_publications((record,))

    assert record.activity.title in _dashboard_titles(application)


def test_reconciliation_is_idempotent_while_the_published_set_is_unchanged() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    record = _publish(candidate_id, authoring, InMemoryPublishedPracticeStore())

    application, _ = _application(publications=(record,))
    application.apply_publications((record,))
    application.apply_publications((record,))

    titles = _dashboard_titles(application)
    assert titles.count(record.activity.title) == 1


def test_published_practice_is_offered_through_full_practice_mode() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    record = _publish(candidate_id, authoring, InMemoryPublishedPracticeStore())

    application, _ = _application(publications=(record,))

    full_practice = application.get_practice_mode_activities(PracticeMode.FULL_PRACTICE)
    short_drill = application.get_practice_mode_activities(PracticeMode.SHORT_DRILL)
    assert [item.title for item in full_practice.activities][
        -1
    ] == record.activity.title
    assert record.activity.title not in [item.title for item in short_drill.activities]


def test_withdrawn_practice_leaves_discovery_but_stays_startable() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    published = InMemoryPublishedPracticeStore()
    record = _publish(candidate_id, authoring, published)
    withdrawn = withdraw_publication(candidate_id, store=published)

    application, store = _application(publications=(record,))
    application.apply_publications((withdrawn,))

    assert record.activity.title not in _dashboard_titles(application)
    assert record.activity.title not in [
        item.title
        for item in application.get_practice_mode_activities(
            PracticeMode.FULL_PRACTICE
        ).activities
    ]
    # Discovery-only withdrawal: the activity still resolves, so in-flight
    # practice and completed history are never broken.
    assert store.get_activity(record.activity_id).title == record.activity.title
    assert application.start_practice(record.activity_id).title == record.activity.title


def test_learner_can_complete_a_published_practice() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    record = _publish(candidate_id, authoring, InMemoryPublishedPracticeStore())
    application, _ = _application(publications=(record,))

    view = application.start_practice(record.activity_id)
    feedback = application.submit_response(
        record.activity_id,
        "I can see three details: the window, the shadow, and the frame.",
    )
    completion = application.submit_reflection(
        "I will slow down and name details first."
    )

    assert view.prompt == record.activity.activity.instructions
    assert feedback.activity_title == record.activity.title
    assert completion.message
    assert application.get_completion().message
    assert application.get_practice_history().entries[0].activity_title == (
        record.activity.title
    )


def test_evaluator_knows_about_the_activity_after_publication() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    record = _publish(candidate_id, authoring, InMemoryPublishedPracticeStore())

    application, _ = _application()
    application.apply_publications((record,))

    feedback = application.submit_response(
        record.activity_id,
        "The window frame draws the eye first, then the shadow behind it.",
    )
    assert feedback.activity_title == record.activity.title


def test_publishing_does_not_expose_authoring_provenance_to_learners() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)
    record = _publish(candidate_id, authoring, InMemoryPublishedPracticeStore())
    application, _ = _application(publications=(record,))

    summary = application.get_dashboard().activities[-1]
    rendered = f"{summary.title} {summary.description} {summary.skills}"

    assert str(candidate_id) not in rendered
    assert "provenance" not in rendered.lower()
    assert "reviewer" not in rendered.lower()


# --- Static: both candidate models cross the same boundary -------------------


def _accept(candidate: PublishableCandidate) -> PublishableCandidate:
    """Static proof that the SPEC-032 candidate satisfies the boundary contract."""
    return candidate


def test_spec_032_candidate_satisfies_the_publishable_contract() -> None:
    authoring = _authoring_store()
    candidate_id = _approved(authoring)

    accepted = _accept(authoring.get(candidate_id))

    assert accepted.is_approved
    assert isinstance(accepted.contract, PracticeContentContract)
