"""Datastore-backed published practice store tests (SPEC-035)."""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from fablit.application.persistence import PersistenceError
from fablit.application.publishing import PublishedPractice
from fablit.application.store import Concept, DemoActivity, PracticeContentContract
from fablit.domain import (
    ActivityStimulusContext,
    ActivityType,
    AssessmentActivity,
    StimulusInstance,
)
from fablit.platform.datastore_published_store import (
    DatastorePublishedPracticeStore,
    deserialize_published_practice,
    serialize_published_practice,
)
from tests.persistence.datastore_fakes import (
    INDEXED_STRING_LIMIT_BYTES,
    FakeEntity,
    FakeKey,
    assert_within_index_limits,
)


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
            if entity.key is not None
            and entity.key.kind == self._kind
            and entity.key.namespace == self._namespace
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

    def entity(
        self, key: FakeKey | None = None, exclude_from_indexes: Sequence[str] = ()
    ) -> FakeEntity:
        return FakeEntity(key, exclude_from_indexes)

    def get(self, key: FakeKey) -> FakeEntity | None:
        return self._store.get(key._id())

    def put(self, entity: FakeEntity) -> None:
        if self.fail_next_put:
            self.fail_next_put = False
            raise RuntimeError("simulated datastore put outage")
        assert_within_index_limits(entity)
        if entity.key is None:
            raise ValueError("Entity must have a key")
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


def _authored_stimulus(activity_id: UUID) -> StimulusInstance:
    return StimulusInstance(
        activity_id=activity_id,
        provider="pexafy",
        asset_id="photo-1",
        image_url="https://cdn.example/large.jpg",
        source_url="https://example/photos/still-life",
        retrieved_at=datetime(2026, 10, 12, 9, tzinfo=UTC),
        creator="Saurabh_U",
        license="free",
        attribution="Photo by Saurabh_U on Pixabay",
        alt_text="A still life on a wooden table",
    )


def test_authored_stimulus_and_sketch_capability_roundtrip() -> None:
    activity_id = uuid4()
    record = _make_record(activity_id=activity_id)
    record = dataclasses.replace(
        record,
        activity=dataclasses.replace(
            record.activity,
            authored_stimulus=_authored_stimulus(activity_id),
            fallback_image="https://cdn.example/large.jpg",
            fallback_alt="A still life on a wooden table",
            supports_sketch_upload=True,
        ),
    )
    client = FakeDatastoreClient()
    store = DatastorePublishedPracticeStore(client)

    store.save(record)
    retrieved = store.get(activity_id)

    assert retrieved is not None
    stimulus = retrieved.activity.authored_stimulus
    assert stimulus is not None
    assert stimulus.image_url == "https://cdn.example/large.jpg"
    assert stimulus.alt_text == "A still life on a wooden table"
    assert stimulus.attribution == "Photo by Saurabh_U on Pixabay"
    assert retrieved.activity.supports_sketch_upload is True
    assert retrieved.activity.fallback_image == "https://cdn.example/large.jpg"


def test_older_records_without_stimulus_fields_still_load() -> None:
    client = FakeDatastoreClient()
    store = DatastorePublishedPracticeStore(client)
    record = _make_record()
    store.save(record)
    key = client.key("PublishedPractice", str(record.source_candidate_id), namespace="library")
    entity = client.get(key)
    assert entity is not None
    activity = entity["activity"]
    del activity["authored_stimulus"]
    del activity["supports_sketch_upload"]

    retrieved = deserialize_published_practice(entity)

    assert retrieved.activity.authored_stimulus is None
    assert retrieved.activity.supports_sketch_upload is False


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
    client = FakeDatastoreClient()
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
        serialize_published_practice(
            dataclasses.replace(record, activity=activity), client
        )
    assert "stimulus contexts are not supported" in str(excinfo.value)


# --- Indexed-value limits ------------------------------------------------------
#
# Datastore rejects an *indexed* string property longer than 1500 bytes, which
# would fail the whole publication write. The learner-facing activity payload is
# only ever read back by key, so it is stored unindexed.


def test_long_published_content_is_persisted_instead_of_failing_the_write() -> None:
    client = FakeDatastoreClient()
    store = DatastorePublishedPracticeStore(client)
    long_text = ("Observe closely before interpreting what you see. " * 80).strip()
    assert len(long_text.encode("utf-8")) > INDEXED_STRING_LIMIT_BYTES

    record = _make_record()
    original_contract = record.activity.content_contract
    assert original_contract is not None
    contract = dataclasses.replace(original_contract, expected_thinking=long_text)
    activity = dataclasses.replace(
        record.activity,
        description=long_text,
        content_contract=contract,
        concepts=(Concept(keyword="evidence", finding=long_text),),
    )
    record = dataclasses.replace(record, activity=activity)

    store.save(record)

    retrieved = DatastorePublishedPracticeStore(client).get(record.activity_id)
    assert retrieved is not None
    assert retrieved.activity.description == long_text
    content_contract = retrieved.activity.content_contract
    assert content_contract is not None
    assert content_contract.expected_thinking == long_text
    assert retrieved.activity.concepts[0].finding == long_text


def test_activity_payload_is_stored_unindexed() -> None:
    """The queried provenance properties stay indexed (SPEC-035)."""
    client = FakeDatastoreClient()
    store = DatastorePublishedPracticeStore(client)
    record = _make_record()

    store.save(record)

    entity = client._store[("PublishedPractice", str(record.source_candidate_id), "library")]
    assert entity.exclude_from_indexes == set()
    assert entity["published_at"] == record.published_at
    activity = entity["activity"]
    assert isinstance(activity, FakeEntity)
    # Every learner-facing payload property is a real embedded entity marked
    # non-indexed.
    assert activity.exclude_from_indexes == set(activity)
    contract = activity["content_contract"]
    assert isinstance(contract, FakeEntity)
    assert contract.exclude_from_indexes == set(contract)


def test_deserialization_tolerates_isoformatted_timestamps() -> None:
    entity = serialize_published_practice(_make_record(), FakeDatastoreClient())
    entity["published_at"] = "2026-10-12T09:00:00+00:00"
    entity["withdrawn_at"] = "2026-10-13T10:00:00+00:00"

    record = deserialize_published_practice(entity)

    assert record.published_at == datetime(2026, 10, 12, 9, tzinfo=UTC)
    assert record.withdrawn_at == datetime(2026, 10, 13, 10, tzinfo=UTC)
    assert record.is_withdrawn
