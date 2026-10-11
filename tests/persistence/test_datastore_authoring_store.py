"""Datastore-backed shared candidate store tests (SPEC-032 / FIX-7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.authoring import (
    AuthoringBrief,
    CandidateReviewOutcome,
    PracticeCandidate,
)
from fablit.application.authoring import (
    CandidateStatus,
    CandidateValidation,
)
from fablit.application.errors import (
    CandidateNotApprovableError,
    CandidateNotFoundError,
)
from fablit.application.persistence import PersistenceError
from fablit.application.practice_modes import PracticeMode
from fablit.platform.datastore_authoring_store import DatastoreAuthoringCandidateStore


class FakeKey:
    def __init__(self, kind: str, name: str, namespace: str | None = None) -> None:
        self.kind = kind
        self.name = name
        self.namespace = namespace

    def _id(self) -> tuple[str, str, str | None]:
        return (self.kind, self.name, self.namespace)


class FakeEntity(dict[str, Any]):
    def __init__(self, key: FakeKey) -> None:
        super().__init__()
        self.key = key


class FakeQuery:
    def __init__(self, client: FakeDatastoreClient, kind: str, namespace: str) -> None:
        self._client = client
        self._kind = kind
        self._namespace = namespace
        self._filters: list[tuple[str, str, Any]] = []
        self._order: list[tuple[str]] = []

    @property
    def order_by(self) -> list[tuple[str]]:
        return self._order

    @order_by.setter
    def order_by(self, value: list[tuple[str]]) -> None:
        self._order = value

    def fetch(self) -> list[FakeEntity]:
        if self._client.fail_query:
            raise RuntimeError("simulated datastore query outage")
        results: list[FakeEntity] = []
        for entity in self._client._store.values():
            if entity.key.kind != self._kind:
                continue
            if entity.key.namespace != self._namespace:
                continue
            results.append(entity)
        return results


class FakeDatastoreClient:
    """In-memory stand-in for google.cloud.datastore.Client."""

    def __init__(self, project: str = "test-project") -> None:
        self.project = project
        self._store: dict[tuple[str, str, str | None], FakeEntity] = {}
        self.fail_next_put = False
        self.fail_next_get = False
        self.fail_query = False

    def key(self, kind: str, name: str, namespace: str | None = None) -> FakeKey:
        return FakeKey(kind, name, namespace)

    def entity(self, key: FakeKey) -> FakeEntity:
        return FakeEntity(key)

    def get(self, key: FakeKey) -> FakeEntity | None:
        if self.fail_next_get:
            self.fail_next_get = False
            raise RuntimeError("simulated datastore get outage")
        return self._store.get(key._id())

    def put(self, entity: FakeEntity) -> None:
        if self.fail_next_put:
            self.fail_next_put = False
            raise RuntimeError("simulated datastore put outage")
        self._store[entity.key._id()] = entity

    def delete(self, key: FakeKey) -> None:
        self._store.pop(key._id(), None)

    def query(self, kind: str, namespace: str | None = None, **_: Any) -> FakeQuery:
        return FakeQuery(self, kind, namespace or "")


def _make_candidate(
    *,
    candidate_id: UUID | None = None,
    title: str = "Color Harmony Exploration",
    description: str = "Practice exploring complementary color palettes.",
    generated_at: datetime | None = None,
    structural_errors: tuple[str, ...] = (),
    feedback_errors: tuple[str, ...] = (),
    content_warnings: tuple[str, ...] = (),
    review_outcome: CandidateReviewOutcome | None = None,
    revision: int = 1,
) -> PracticeCandidate:
    cid = candidate_id or uuid4()
    gen_at = generated_at or datetime.now(UTC)
    brief = AuthoringBrief(
        practice_area="visual-arts",
        learner_context="High school design student",
        purpose="Learn how contrasting color palettes evoke emotion.",
        intended_mode=PracticeMode.SHORT_DRILL,
        response_form="text-and-sketchbook",
        evaluation_intent="Assess understanding of color theory and harmony.",
        feedback_intent="Constructive guidance on contrast and saturation.",
        reflection_intent="Encourage personal insight on aesthetic decisions.",
    )
    candidate_data = {
        "title": title,
        "description": description,
        "contract": {
            "purpose": "Learn how contrasting color palettes evoke emotion.",
            "task": "Create a high-contrast palette and describe its emotional tone.",
            "expected_thinking": (
                "Identify complementary hues and analyze their emotional impact."
            ),
            "response_contract": (
                "Submit written explanation and color swatch references."
            ),
            "evaluation_intent": "Assess understanding of color theory and harmony.",
            "feedback_intent": "Constructive guidance on contrast and saturation.",
            "reflection_intent": "Encourage personal insight on aesthetic decisions.",
            "continuation_intent": "Explore analogous palettes in subsequent practice.",
        },
    }
    validation = CandidateValidation(
        structural_errors=structural_errors,
        feedback_errors=feedback_errors,
        content_warnings=content_warnings,
    )
    return PracticeCandidate(
        id=cid,
        brief=brief,
        candidate_data=candidate_data,
        provider="gemini",
        model="gemini-2.5-flash",
        generated_at=gen_at,
        review_outcome=review_outcome,
        validation=validation,
        revision=revision,
    )


def test_roundtrip_serialization_and_deserialization() -> None:
    client = FakeDatastoreClient()
    store = DatastoreAuthoringCandidateStore(client)

    candidate = _make_candidate(content_warnings=("check saturation terminology",))
    store.add(candidate)

    retrieved = store.get(candidate.id)
    assert retrieved.id == candidate.id
    assert retrieved.title == candidate.title
    assert retrieved.description == candidate.description
    assert retrieved.provider == "gemini"
    assert retrieved.model == "gemini-2.5-flash"
    assert retrieved.brief.practice_area == "visual-arts"
    assert retrieved.contract is not None
    assert (
        retrieved.contract.purpose
        == "Learn how contrasting color palettes evoke emotion."
    )
    assert retrieved.validation.content_warnings == ("check saturation terminology",)
    assert retrieved.status == CandidateStatus.GENERATED.value
    assert retrieved.is_approved is False


def test_cross_instance_create_and_retrieve() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreAuthoringCandidateStore(client)
    instance_b = DatastoreAuthoringCandidateStore(client)

    candidate = _make_candidate()
    instance_a.add(candidate)

    # Listed and retrieved through another application instance
    candidates_b = instance_b.list()
    assert len(candidates_b) == 1
    assert candidates_b[0].id == candidate.id

    detail_b = instance_b.get(candidate.id)
    assert detail_b.id == candidate.id
    assert detail_b.title == candidate.title


def test_cross_instance_edit() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreAuthoringCandidateStore(client)
    instance_b = DatastoreAuthoringCandidateStore(client)

    candidate = _make_candidate(title="Original Title")
    instance_a.add(candidate)

    # Edit from instance A
    updated = instance_a.edit(
        candidate.id,
        updates={"title": "Updated Title", "description": "New description"},
        editor="curator-1",
    )
    assert updated.revision == 2
    assert len(updated.history) == 1
    assert updated.history[0].title == "Original Title"
    assert updated.history[0].editor == "curator-1"

    # Visible immediately from instance B
    retrieved_b = instance_b.get(candidate.id)
    assert retrieved_b.revision == 2
    assert retrieved_b.title == "Updated Title"
    assert retrieved_b.description == "New description"
    assert len(retrieved_b.history) == 1
    assert retrieved_b.history[0].title == "Original Title"


def test_cross_instance_approval_and_conflict_handling() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreAuthoringCandidateStore(client)
    instance_b = DatastoreAuthoringCandidateStore(client)

    candidate = _make_candidate()
    instance_a.add(candidate)

    # Instance A approves
    approved_a = instance_a.approve(candidate.id, reviewer="reviewer-1")
    assert approved_a.status == CandidateStatus.APPROVED.value
    assert approved_a.is_approved is True

    # Instance B reads approved state
    retrieved_b = instance_b.get(candidate.id)
    assert retrieved_b.status == CandidateStatus.APPROVED.value
    assert retrieved_b.reviewer == "reviewer-1"
    assert retrieved_b.decided_at is not None

    # Instance B attempts conflicting approval
    with pytest.raises(CandidateNotApprovableError, match="already approved"):
        instance_b.approve(candidate.id, reviewer="reviewer-2")

    # Instance B attempts conflicting rejection
    with pytest.raises(CandidateNotApprovableError, match="cannot be rejected"):
        instance_b.reject(candidate.id, reviewer="reviewer-2")


def test_cross_instance_rejection_and_conflict_handling() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreAuthoringCandidateStore(client)
    instance_b = DatastoreAuthoringCandidateStore(client)

    candidate = _make_candidate()
    instance_a.add(candidate)

    # Instance A rejects
    rejected_a = instance_a.reject(candidate.id, reviewer="reviewer-1")
    assert rejected_a.status == CandidateStatus.REJECTED.value

    # Instance B reads rejection
    retrieved_b = instance_b.get(candidate.id)
    assert retrieved_b.status == CandidateStatus.REJECTED.value

    # Conflicting operations rejected
    with pytest.raises(CandidateNotApprovableError, match="already rejected"):
        instance_b.reject(candidate.id)

    with pytest.raises(CandidateNotApprovableError, match="cannot be approved"):
        instance_b.approve(candidate.id)


def test_unapprovable_candidate_cannot_be_approved() -> None:
    client = FakeDatastoreClient()
    store = DatastoreAuthoringCandidateStore(client)

    candidate = _make_candidate(structural_errors=("Missing required contract field",))
    store.add(candidate)

    with pytest.raises(CandidateNotApprovableError, match="validation errors"):
        store.approve(candidate.id)


def test_instance_restart_does_not_lose_candidate() -> None:
    client = FakeDatastoreClient()
    store_1 = DatastoreAuthoringCandidateStore(client)

    candidate = _make_candidate()
    store_1.add(candidate)

    # Store 1 is discarded; new store 2 is spun up simulating an instance restart
    store_2 = DatastoreAuthoringCandidateStore(client)
    retrieved = store_2.get(candidate.id)
    assert retrieved.id == candidate.id

    # Non-existent ID raises CandidateNotFoundError
    with pytest.raises(CandidateNotFoundError):
        store_2.get(uuid4())


def test_retention_window_expiration_and_cleanup() -> None:
    client = FakeDatastoreClient()
    # 30 day retention window
    store = DatastoreAuthoringCandidateStore(client, retention_days=30)
    now = datetime.now(UTC)

    recent_unapproved = _make_candidate(generated_at=now - timedelta(days=10))
    expired_unapproved = _make_candidate(generated_at=now - timedelta(days=40))
    expired_but_approved = _make_candidate(
        generated_at=now - timedelta(days=40),
        review_outcome=CandidateReviewOutcome.APPROVED,
    )

    store.add(recent_unapproved)
    store.add(expired_unapproved)
    store.add(expired_but_approved)

    # Recent unapproved is available
    assert store.get(recent_unapproved.id).id == recent_unapproved.id

    # Expired unapproved raises CandidateNotFoundError and is excluded from list
    with pytest.raises(CandidateNotFoundError):
        store.get(expired_unapproved.id)

    # Expired but approved is retained for curated library handoff
    assert store.get(expired_but_approved.id).id == expired_but_approved.id

    active_list = store.list()
    active_ids = {c.id for c in active_list}
    assert recent_unapproved.id in active_ids
    assert expired_but_approved.id in active_ids
    assert expired_unapproved.id not in active_ids

    # Cleanup removes the expired unapproved candidate from Datastore
    deleted_count = store.cleanup_expired(now=now)
    assert deleted_count == 1

    # Only 2 entities remain in client store
    assert len(client._store) == 2


def test_approved_practices_isolation() -> None:
    client = FakeDatastoreClient()
    store = DatastoreAuthoringCandidateStore(client)

    draft_c = _make_candidate(title="Draft")
    approved_c = _make_candidate(
        title="Approved", review_outcome=CandidateReviewOutcome.APPROVED
    )
    rejected_c = _make_candidate(
        title="Rejected", review_outcome=CandidateReviewOutcome.REJECTED
    )

    store.add(draft_c)
    store.add(approved_c)
    store.add(rejected_c)

    approved = store.approved_practices()
    assert len(approved) == 1
    assert approved[0].id == approved_c.id


def test_storage_failure_handling() -> None:
    client = FakeDatastoreClient()
    store = DatastoreAuthoringCandidateStore(client)
    candidate = _make_candidate()

    # Outage on put raises PersistenceError
    client.fail_next_put = True
    with pytest.raises(PersistenceError, match="Failed to persist candidate"):
        store.add(candidate)

    # Outage on get raises PersistenceError
    client.fail_next_get = True
    with pytest.raises(PersistenceError, match="Failed to retrieve candidate"):
        store.get(candidate.id)

    # Outage on query raises PersistenceError
    client.fail_query = True
    with pytest.raises(PersistenceError, match="Failed to query candidates"):
        store.list()


def test_duplicate_title_attaches_warning() -> None:
    client = FakeDatastoreClient()
    store = DatastoreAuthoringCandidateStore(client)

    c1 = _make_candidate(title="Unique Perspective")
    c2 = _make_candidate(title="unique perspective")

    store.add(c1)
    stored_c2 = store.add(c2)

    assert any("possible duplicate" in w for w in stored_c2.validation.content_warnings)
