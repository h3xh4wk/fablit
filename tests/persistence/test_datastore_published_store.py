"""Datastore-backed published practice store tests (SPEC-035)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from fablit.application.persistence import PersistenceError
from fablit.application.publishing import PublishedPractice
from fablit.application.store import DemoActivity, PracticeContentContract
from fablit.domain import ActivityStimulusContext, ActivityType, AssessmentActivity
from fablit.platform.datastore_published_store import (
    DatastorePublishedPracticeStore,
    deserialize_published_practice,
    serialize_published_practice,
)


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

    def fetch(self) -> list[FakeEntity]:
        if self._client.fail_query:
            raise RuntimeError("simulated datastore query outage")
        return [
            entity
            for entity in self._client._store.values()
            if entity.key.kind == self._kind and entity.key.namespace == self._namespace
        ]


class FakeDatastoreClient:
    """In-memory stand-in for google.cloud.datastore.Client."""

    def __init__(self, project: str = "test-project") -> None:
        self.project = project
        self._store: dict[tuple[str, str, str | None], FakeEntity] = {}
        self.fail_next_put = False
        self.fail_query = False

    def key(self, kind: str, name: str, namespace: str | None = None) -> FakeKey:
        return FakeKey(kind, name, namespace)

    def entity(self, key: FakeKey) -> FakeEntity:
        return FakeEntity(key)

    def get(self, key: FakeKey) -> FakeEntity | None:
        return self._store.get(key._id())

    def put(self, entity: FakeEntity) -> None:
        if self.fail_next_put:
            self.fail_next_put = False
            raise RuntimeError("simulated datastore put outage")
        self._store[entity.key._id()] = entity

    def query(self, kind: str, namespace: str | None = None, **_: Any) -> FakeQuery:
        return FakeQuery(self, kind, namespace or "")


def _contract() -> PracticeContentContract:
    return PracticeContentContract(
        purpose="Distinguish visible evidence from interpretation.",
        task="Identify three visible details in the provided stimulus.",
        expected_thinking="The learner names details before interpreting them.",
        response_contract="A short written observation.",
        evaluation_intent="Look for specific observable details.",
        feedback_intent="Name one concrete strength and one useful next move.",
        reflection_intent="Notice which observation strategy was useful.",
        continuation_intent="Apply the same observation to a different scene.",
    )


def _make_record(
    *,
    activity_id: UUID | None = None,
    position: int = 12,
    source_candidate_id: UUID | None = None,
    source_revision: int = 1,
    withdrawn_at: datetime | None = None,
) -> PublishedPractice:
    return PublishedPractice(
        activity=DemoActivity(
            activity=AssessmentActivity(
                activity_type=ActivityType.WRITTEN_RESPONSE,
                instructions=_contract().task,
                position=position,
                id=activity_id or uuid4(),
            ),
            title="Visual analysis — Observe Practice",
            description="A learner practising close observation.",
            strength="You worked through this practice's own task.",
            improvement="Check your response against what the task asks for.",
            next_step="Take another pass with the purpose in mind.",
            content_contract=_contract(),
            primary_capability="Observe",
        ),
        source_candidate_id=source_candidate_id or uuid4(),
        source_revision=source_revision,
        published_at=datetime(2026, 10, 12, 9, tzinfo=UTC),
        withdrawn_at=withdrawn_at,
    )


def test_roundtrip_serialization_and_deserialization() -> None:
    client = FakeDatastoreClient()
    store = DatastorePublishedPracticeStore(client)
    record = _make_record(source_revision=2)

    store.save(record)
    retrieved = store.get(record.activity_id)

    assert retrieved is not None
    assert retrieved.activity_id == record.activity_id
    assert retrieved.activity.title == record.activity.title
    assert retrieved.activity.activity.instructions == _contract().task
    assert retrieved.activity.content_contract == _contract()
    assert retrieved.activity.primary_capability == "Observe"
    assert retrieved.source_candidate_id == record.source_candidate_id
    assert retrieved.source_revision == 2
    assert retrieved.published_at == record.published_at
    assert retrieved.withdrawn_at is None
    assert retrieved.is_visible


def test_cross_instance_visibility_and_candidate_lookup() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastorePublishedPracticeStore(client)
    instance_b = DatastorePublishedPracticeStore(client)
    record = _make_record(position=13)

    instance_a.save(record)

    assert instance_b.get(record.activity_id) is not None
    assert [item.activity_id for item in instance_b.list_records()] == [
        record.activity_id
    ]
    assert [item.activity_id for item in instance_b.visible()] == [record.activity_id]
    assert instance_b.find_by_candidate(record.source_candidate_id) == record
    assert instance_b.find_by_candidate(uuid4()) is None
    assert instance_b.get(uuid4()) is None


def test_saving_under_an_existing_identity_replaces_in_place() -> None:
    client = FakeDatastoreClient()
    store = DatastorePublishedPracticeStore(client)
    record = _make_record()

    store.save(record)
    store.save(dataclasses.replace(record, source_revision=2))

    assert len(client._store) == 1
    listed = store.list_records()
    assert len(listed) == 1
    assert listed[0].source_revision == 2


def test_records_are_ordered_by_learner_facing_position() -> None:
    client = FakeDatastoreClient()
    store = DatastorePublishedPracticeStore(client)
    later = _make_record(position=14)
    earlier = _make_record(position=13)

    store.save(later)
    store.save(earlier)

    assert [item.activity.activity.position for item in store.list_records()] == [
        13,
        14,
    ]


def test_withdrawal_roundtrips_and_leaves_the_library() -> None:
    client = FakeDatastoreClient()
    store = DatastorePublishedPracticeStore(client)
    record = _make_record()
    withdrawn_at = datetime(2026, 10, 13, 10, tzinfo=UTC)
    store.save(record)
    store.save(dataclasses.replace(record, withdrawn_at=withdrawn_at))

    retrieved = store.get(record.activity_id)
    assert retrieved is not None
    assert retrieved.withdrawn_at == withdrawn_at
    assert retrieved.is_withdrawn
    assert store.visible() == ()
    assert store.list_records() == (retrieved,)


def test_put_failure_is_reported_as_a_persistence_error() -> None:
    client = FakeDatastoreClient()
    client.fail_next_put = True
    store = DatastorePublishedPracticeStore(client)

    with pytest.raises(PersistenceError):
        store.save(_make_record())


def test_query_failure_is_reported_as_a_persistence_error() -> None:
    client = FakeDatastoreClient()
    client.fail_query = True
    store = DatastorePublishedPracticeStore(client)

    with pytest.raises(PersistenceError):
        store.list_records()


def test_serializing_an_unsupported_stimulus_context_fails_loudly() -> None:
    record = _make_record()
    activity = dataclasses.replace(
        record.activity,
        activity=dataclasses.replace(
            record.activity.activity,
            stimulus_context=ActivityStimulusContext(
                learning_focus="Composition",
                stimulus_context="Street photography",
                retrieval_query="street photography composition",
            ),
        ),
    )

    with pytest.raises(PersistenceError) as excinfo:
        serialize_published_practice(dataclasses.replace(record, activity=activity))
    assert "stimulus contexts are not supported" in str(excinfo.value)


def test_deserialization_tolerates_isoformatted_timestamps() -> None:
    entity = serialize_published_practice(_make_record())
    entity["published_at"] = "2026-10-12T09:00:00+00:00"
    entity["withdrawn_at"] = "2026-10-13T10:00:00+00:00"

    record = deserialize_published_practice(entity)

    assert record.published_at == datetime(2026, 10, 12, 9, tzinfo=UTC)
    assert record.withdrawn_at == datetime(2026, 10, 13, 10, tzinfo=UTC)
    assert record.is_withdrawn
