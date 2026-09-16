"""Unit tests for the Google Cloud Datastore adapter (SPEC-021).

Covers entity serialization/deserialization, create/read of completion
history, repeated practice records, history query ordering, review
reconstruction, duplicate/idempotency protection, and Datastore failure
mapping (SPEC-021 §19 "Datastore Tests").

The tests use a lightweight fake Datastore client so they run without GCP
credentials (AC-021-11). The adapter only uses the small client surface:
``key()``, ``entity()``, ``get()``, ``put()``, ``query()``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from fablit.application.persistence import PersistenceError
from fablit.domain import (
    Evaluation,
    EvaluationFinding,
    Feedback,
    Reflection,
    StimulusInstance,
    Submission,
)
from fablit.platform.datastore_repository import DatastorePracticeHistoryRepository

LEARNER = uuid4()
ACTIVITY = uuid4()


class FakeKey:
    def __init__(self, kind: str, name: str, namespace: str | None = None) -> None:
        self.kind = kind
        self.name = name
        self.namespace = namespace

    def _id(self) -> tuple[str, str, str | None]:
        return (self.kind, self.name, self.namespace)


class FakeQuery:
    def __init__(self, client: FakeDatastoreClient, kind: str, namespace: str) -> None:
        self._client = client
        self._kind = kind
        self._namespace = namespace
        self._filters: list[tuple[str, str, Any]] = []
        self._order: list[tuple[str]] = []
        self._limit: int | None = None

    def add_filter(self, prop: str, operator: str, value: Any) -> None:
        self._filters.append((prop, operator, value))

    @property
    def order_by(self) -> list[tuple[str]]:
        return self._order

    @order_by.setter
    def order_by(self, value: list[tuple[str]]) -> None:
        self._order = value

    @property
    def limit(self) -> int | None:
        return self._limit

    @limit.setter
    def limit(self, value: int) -> None:
        self._limit = value

    def fetch(self) -> list[dict[str, Any]]:
        assert self._kind == "PracticeCompletion"
        results: list[FakeEntity] = []
        for entity in self._client._store.values():
            if entity.key.namespace != self._namespace:
                continue
            if all(entity.get(prop) == value for prop, _, value in self._filters):
                results.append(entity)
        # The adapter relies on Datastore-side ordering; emulate it here.
        if self._order:
            (prop,) = self._order[0]
            descending = prop.startswith("-")
            prop_name = prop.lstrip("-")
            results.sort(key=lambda e: e[prop_name], reverse=descending)
        if self._limit is not None:
            results = results[: self._limit]
        return results  # type: ignore[return-value]


class FakeEntity(dict[str, Any]):
    def __init__(self, key: FakeKey) -> None:
        super().__init__()
        self.key = key


class FakeDatastoreClient:
    """A minimal in-memory stand-in for google.cloud.datastore.Client."""

    def __init__(self, project: str = "test-project") -> None:
        self.project = project
        self._store: dict[tuple[str, str, str | None], FakeEntity] = {}
        self.fail_next_put = False

    def key(self, kind: str, name: str, namespace: str | None = None) -> FakeKey:
        return FakeKey(kind, name, namespace)

    def entity(self, key: FakeKey) -> FakeEntity:
        return FakeEntity(key)

    def get(self, key: FakeKey) -> FakeEntity | None:
        return self._store.get(key._id())

    def put(self, entity: FakeEntity) -> None:
        if self.fail_next_put:
            self.fail_next_put = False
            raise RuntimeError("simulated datastore outage")
        self._store[entity.key._id()] = entity

    def query(self, kind: str, namespace: str | None = None, **_: Any) -> FakeQuery:
        return FakeQuery(self, kind, namespace or "")


def make_stored_fixtures(
    *,
    response: str = "The contrast is striking.",
    reflection_content: str = "I will look for balance next time.",
    created_at: datetime | None = None,
    with_stimulus: bool = True,
) -> dict[str, Any]:
    """Build the domain records for one completed practice."""
    created_at = created_at or datetime.now(UTC)
    submission = Submission(
        learner_id=LEARNER,
        activity_id=ACTIVITY,
        response=response,
    ).submit(submitted_at=created_at)
    evaluation = Evaluation(
        submission_id=submission.id,
        findings=(
            EvaluationFinding(observation="You noticed the contrast."),
            EvaluationFinding(observation="Consider the negative space."),
        ),
        evaluated_at=created_at,
    )
    feedback = Feedback(
        evaluation_id=evaluation.id,
        content="Strengths: You noticed the contrast.",
        created_at=created_at,
    )
    reflection = Reflection(
        feedback_id=feedback.id,
        content=reflection_content,
        created_at=created_at,
    )
    stimulus = (
        StimulusInstance(
            activity_id=ACTIVITY,
            provider="fablit",
            image_url="/static/images/stimulus-composition.svg",
            source_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
            retrieved_at=created_at,
            attribution="Example Author",
            alt_text="A composition example.",
        )
        if with_stimulus
        else None
    )
    return {
        "submission": submission,
        "evaluation": evaluation,
        "feedback": feedback,
        "reflection": reflection,
        "stimulus": stimulus,
    }


def make_repository() -> tuple[DatastorePracticeHistoryRepository, FakeDatastoreClient]:
    client = FakeDatastoreClient()
    return DatastorePracticeHistoryRepository(client), client


def save_fixture(
    repository: DatastorePracticeHistoryRepository,
    fixtures: dict[str, Any],
    *,
    activity_title: str = "CAT Practice — 2D & 3D Composition Analysis",
) -> UUID:
    stored = repository.save_completion(
        learner_id=LEARNER,
        activity_id=ACTIVITY,
        activity_title=activity_title,
        submission=fixtures["submission"],
        evaluation=fixtures["evaluation"],
        feedback=fixtures["feedback"],
        reflection=fixtures["reflection"],
        stimulus=fixtures["stimulus"],
    )
    return stored.completion_id


# --- Serialization round trips -------------------------------------------------


def test_save_completion_persists_and_returns_stored_record() -> None:
    repository, _client = make_repository()
    fixtures = make_stored_fixtures()

    stored = repository.save_completion(
        learner_id=LEARNER,
        activity_id=ACTIVITY,
        activity_title="CAT Practice",
        submission=fixtures["submission"],
        evaluation=fixtures["evaluation"],
        feedback=fixtures["feedback"],
        reflection=fixtures["reflection"],
        stimulus=fixtures["stimulus"],
    )

    assert stored.completion_id == fixtures["reflection"].id
    assert stored.activity_title == "CAT Practice"
    assert stored.completed_at == fixtures["reflection"].created_at


def test_get_completion_reconstructs_the_full_journey() -> None:
    repository, _client = make_repository()
    fixtures = make_stored_fixtures()
    completion_id = save_fixture(repository, fixtures)

    retrieved = repository.get_completion(LEARNER, completion_id)

    assert retrieved is not None
    assert retrieved.completion_id == completion_id
    assert retrieved.learner_id == LEARNER
    assert retrieved.activity_id == ACTIVITY
    assert retrieved.submission.response == "The contrast is striking."
    assert retrieved.submission.status == fixtures["submission"].status
    assert retrieved.submission.submitted_at == fixtures["submission"].submitted_at
    assert retrieved.evaluation.id == fixtures["evaluation"].id
    assert len(retrieved.evaluation.findings) == 2
    assert [f.id for f in retrieved.evaluation.findings] == [
        f.id for f in fixtures["evaluation"].findings
    ]
    assert retrieved.evaluation.findings[1].evidence is None
    assert retrieved.feedback.content == fixtures["feedback"].content
    assert retrieved.reflection.content == "I will look for balance next time."
    assert retrieved.completed_at == fixtures["reflection"].created_at


def test_get_completion_reconstructs_the_stimulus() -> None:
    """AC-021-07: the review stimulus is the one originally shown."""
    repository, _client = make_repository()
    fixtures = make_stored_fixtures()
    completion_id = save_fixture(repository, fixtures)

    retrieved = repository.get_completion(LEARNER, completion_id)

    assert retrieved is not None
    stimulus = retrieved.stimulus
    assert stimulus is not None
    assert stimulus.id == fixtures["stimulus"].id
    assert stimulus.activity_id == ACTIVITY
    assert stimulus.provider == "fablit"
    assert stimulus.image_url == "/static/images/stimulus-composition.svg"
    assert stimulus.source_url == fixtures["stimulus"].source_url
    assert stimulus.attribution == "Example Author"
    assert stimulus.alt_text == "A composition example."
    assert stimulus.retrieved_at == fixtures["stimulus"].retrieved_at


def test_get_completion_without_stimulus_returns_none_stimulus() -> None:
    repository, _client = make_repository()
    fixtures = make_stored_fixtures(with_stimulus=False)
    completion_id = save_fixture(repository, fixtures)

    retrieved = repository.get_completion(LEARNER, completion_id)

    assert retrieved is not None
    assert retrieved.stimulus is None


def test_get_unknown_completion_returns_none() -> None:
    repository, _client = make_repository()

    assert repository.get_completion(LEARNER, uuid4()) is None


def test_get_completion_for_another_learner_returns_none() -> None:
    repository, _client = make_repository()
    fixtures = make_stored_fixtures()
    completion_id = save_fixture(repository, fixtures)

    assert repository.get_completion(uuid4(), completion_id) is None


# --- Idempotency and repeated practice -----------------------------------------


def test_retrying_the_same_completion_does_not_duplicate_history() -> None:
    """AC-021-10: the reflection ID is the stable completion identity."""
    repository, client = make_repository()
    fixtures = make_stored_fixtures()
    completion_id = save_fixture(repository, fixtures)

    # A retry with identical data must overwrite, not duplicate.
    save_fixture(repository, fixtures)

    assert len(client._store) == 1
    assert repository.get_completion(LEARNER, completion_id) is not None


def test_repeated_practice_creates_distinguishable_records() -> None:
    """AC-021-06: repeated attempts are separate history records."""
    repository, client = make_repository()
    first = make_stored_fixtures(
        response="First attempt.", reflection_content="First reflection."
    )
    second = make_stored_fixtures(
        response="Second attempt.",
        reflection_content="Second reflection.",
        created_at=datetime.now(UTC) + timedelta(minutes=5),
    )

    first_id = save_fixture(repository, first)
    second_id = save_fixture(repository, second)

    assert first_id != second_id
    assert len(client._store) == 2


# --- History listing -------------------------------------------------------------


def test_list_completions_orders_newest_first() -> None:
    repository, _client = make_repository()
    old = make_stored_fixtures(
        response="Old response.", created_at=datetime.now(UTC) - timedelta(hours=2)
    )
    new = make_stored_fixtures(
        response="New response.", created_at=datetime.now(UTC) - timedelta(hours=1)
    )
    save_fixture(repository, old, activity_title="Older practice")
    save_fixture(repository, new, activity_title="Newer practice")

    summaries = repository.list_completions(LEARNER)

    assert [s.activity_title for s in summaries] == ["Newer practice", "Older practice"]
    assert summaries[0].submission_preview == "New response."
    assert summaries[0].completed_at == new["reflection"].created_at


def test_list_completions_returns_empty_tuple_for_unknown_learner() -> None:
    repository, _client = make_repository()

    assert repository.list_completions(uuid4()) == ()


def test_has_completed_activity_reflects_durable_history() -> None:
    repository, _client = make_repository()
    fixtures = make_stored_fixtures()

    assert not repository.has_completed_activity(LEARNER, ACTIVITY)
    save_fixture(repository, fixtures)

    assert repository.has_completed_activity(LEARNER, ACTIVITY)
    assert not repository.has_completed_activity(LEARNER, uuid4())


# --- Failure mapping (SPEC-021 §14) ----------------------------------------------


def test_save_failure_raises_persistence_error() -> None:
    repository, client = make_repository()
    fixtures = make_stored_fixtures()
    client.fail_next_put = True

    with pytest.raises(PersistenceError):
        repository.save_completion(
            learner_id=LEARNER,
            activity_id=ACTIVITY,
            activity_title="Failing write",
            submission=fixtures["submission"],
            evaluation=fixtures["evaluation"],
            feedback=fixtures["feedback"],
            reflection=fixtures["reflection"],
            stimulus=fixtures["stimulus"],
        )


def test_query_failure_raises_persistence_error() -> None:
    class ExplodingQueryClient(FakeDatastoreClient):
        def query(self, kind: str, namespace: str | None = None, **_: Any) -> Any:
            raise RuntimeError("simulated query failure")

    repository = DatastorePracticeHistoryRepository(ExplodingQueryClient())

    with pytest.raises(PersistenceError):
        repository.list_completions(LEARNER)

    # The has_completed_activity helper degrades conservatively instead of
    # surfacing dashboard errors for a transient query failure.
    assert repository.has_completed_activity(LEARNER, ACTIVITY) is False


# --- Adapter identity semantics ---------------------------------------------------


def test_entities_are_namespaced_per_learner() -> None:
    """Learner context stays explicit for future ownership work (SPEC-021 §15)."""
    repository, client = make_repository()
    fixtures = make_stored_fixtures()
    completion_id = save_fixture(repository, fixtures)

    key = next(iter(client._store.values())).key
    assert key.kind == "PracticeCompletion"
    assert key.name == str(completion_id)
    assert key.namespace == f"learner_{LEARNER}"
