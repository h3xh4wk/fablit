"""Contract tests for the SPEC-044 Datastore generated-practice repository.

Generated practices are private: they live in their own kind and namespace,
never in the shared published catalogue, and every read is scoped to the
learner who requested the practice.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from fablit.application.learner_practice import (
    ChallengePreference,
    GeneratedPracticeRecord,
    PracticeArea,
)
from fablit.application.persistence import PersistenceError
from fablit.application.store import PracticeContentContract
from fablit.platform.datastore_learner_practice_repository import (
    DEFAULT_GENERATED_PRACTICE_NAMESPACE,
    GENERATED_PRACTICE_KIND,
    DatastoreGeneratedPracticeRepository,
    deserialize_generated_practice,
    serialize_generated_practice,
)
from tests.persistence.datastore_fakes import INDEXED_STRING_LIMIT_BYTES, FakeEntity
from tests.persistence.test_datastore_authoring_store import FakeDatastoreClient

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
LEARNER = UUID("2b6f7f60-0d8d-4f6e-9c37-6c1f0c1e5f6a")


def _contract(**overrides: str) -> PracticeContentContract:
    values = {
        "purpose": "Practise noticing how colour and texture work together.",
        "task": "Describe one outfit detail and what it shows you.",
        "expected_thinking": "Move from observation to a specific claim.",
        "response_contract": "A short written response.",
        "evaluation_intent": "Look for a specific, relevant observation.",
        "feedback_intent": "Name one strength and one useful next move.",
        "reflection_intent": "Notice what you would try differently.",
        "continuation_intent": "Carry the same move into another example.",
    }
    values.update(overrides)
    return PracticeContentContract(**values)


def make_record(
    *,
    learner_id: UUID = LEARNER,
    created_at: datetime = NOW,
    **overrides: object,
) -> GeneratedPracticeRecord:
    values: dict[str, object] = {
        "practice_id": uuid4(),
        "learner_id": learner_id,
        "request_token": uuid4(),
        "title": "A focused practice: visual analysis",
        "description": "A short practice made for your request.",
        "contract": _contract(),
        "area": PracticeArea.VISUAL_ANALYSIS,
        "challenge": ChallengePreference.FAMILIAR,
        "response_form": "A short written response",
        "primary_capability": "Observe",
        "used_history": False,
        "provider": "fake-learner-generator",
        "model": "fake-model",
        "generated_at": NOW,
        "created_at": created_at,
        "examination_context": None,
    }
    values.update(overrides)
    return GeneratedPracticeRecord(**values)  # type: ignore[arg-type]


def test_save_and_get_round_trip_in_the_private_namespace() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreGeneratedPracticeRepository(client)
    record = make_record(examination_context="A portfolio interview next month")

    assert repository.save(record) == record

    assert repository.get(LEARNER, record.practice_id) == record
    key = client.key(
        GENERATED_PRACTICE_KIND,
        str(record.practice_id),
        namespace=DEFAULT_GENERATED_PRACTICE_NAMESPACE,
    )
    entity = client.get(key)
    assert entity is not None
    assert entity["learner_id"] == str(LEARNER)
    assert entity["area"] == "visual-analysis"
    assert entity["challenge"] == "familiar"
    assert entity["examination_context"] == "A portfolio interview next month"
    # The full response form stays readable back but is never an index value.
    assert "response_form" in entity.exclude_from_indexes


def test_saving_the_same_practice_twice_keeps_the_first_record() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreGeneratedPracticeRepository(client)
    record = make_record()
    first = repository.save(record)

    second = repository.save(
        make_record(practice_id=record.practice_id, request_token=record.request_token)
    )

    assert second == first
    assert len(repository.list_for_learner(LEARNER)) == 1


def test_long_learner_facing_text_is_stored_without_indexing_it() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreGeneratedPracticeRepository(client)
    long_text = "Observe the fabric. " * (INDEXED_STRING_LIMIT_BYTES // 10)
    record = make_record(
        description=long_text,
        contract=_contract(continuation_intent=long_text),
    )

    repository.save(record)

    assert repository.get(LEARNER, record.practice_id) == record


def test_another_learner_cannot_read_a_generated_practice() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreGeneratedPracticeRepository(client)
    record = make_record()
    repository.save(record)

    assert repository.get(uuid4(), record.practice_id) is None


def test_listing_returns_only_the_learners_own_practices_newest_first() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreGeneratedPracticeRepository(client)
    older = repository.save(
        make_record(created_at=datetime(2026, 10, 29, 9, tzinfo=UTC))
    )
    newer = repository.save(
        make_record(created_at=datetime(2026, 10, 30, 9, tzinfo=UTC))
    )
    repository.save(make_record(learner_id=uuid4()))

    listed = repository.list_for_learner(LEARNER)

    assert listed == (newer, older)
    assert repository.list_for_learner(uuid4()) != listed


def test_non_uuid_identities_return_nothing() -> None:
    repository = DatastoreGeneratedPracticeRepository(FakeDatastoreClient())

    assert repository.get("learner", uuid4()) is None  # type: ignore[arg-type]
    assert repository.get(LEARNER, "practice") is None  # type: ignore[arg-type]
    assert repository.list_for_learner("learner") == ()  # type: ignore[arg-type]


def test_a_write_failure_is_a_persistence_error() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreGeneratedPracticeRepository(client)
    client.fail_next_put = True

    with pytest.raises(PersistenceError):
        repository.save(make_record())


def test_a_read_failure_is_a_persistence_error() -> None:
    class FailingClient(FakeDatastoreClient):
        def get(self, key: Any) -> FakeEntity | None:
            raise RuntimeError("simulated datastore outage")

    repository = DatastoreGeneratedPracticeRepository(FailingClient())

    with pytest.raises(PersistenceError):
        repository.get(LEARNER, uuid4())


def test_a_query_failure_is_a_persistence_error() -> None:
    client = FakeDatastoreClient()
    client.fail_query = True
    repository = DatastoreGeneratedPracticeRepository(client)

    with pytest.raises(PersistenceError):
        repository.list_for_learner(LEARNER)


def test_a_corrupt_entity_is_a_persistence_error_not_a_partial_practice() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreGeneratedPracticeRepository(client)
    record = make_record()
    repository.save(record)
    key = client.key(
        GENERATED_PRACTICE_KIND,
        str(record.practice_id),
        namespace=DEFAULT_GENERATED_PRACTICE_NAMESPACE,
    )
    entity = client.get(key)
    assert entity is not None
    entity["contract"] = {"purpose": "Only one field"}

    with pytest.raises(PersistenceError):
        repository.get(LEARNER, record.practice_id)


def test_serialized_practice_never_carries_raw_provider_payloads() -> None:
    record = make_record()

    serialized = serialize_generated_practice(record, FakeDatastoreClient())

    assert set(serialized) == {
        "practice_id",
        "learner_id",
        "request_token",
        "title",
        "description",
        "contract",
        "area",
        "challenge",
        "response_form",
        "primary_capability",
        "used_history",
        "provider",
        "model",
        "generated_at",
        "created_at",
        "examination_context",
    }
    assert serialized["contract"] == {
        "purpose": record.contract.purpose,
        "task": record.contract.task,
        "expected_thinking": record.contract.expected_thinking,
        "response_contract": record.contract.response_contract,
        "evaluation_intent": record.contract.evaluation_intent,
        "feedback_intent": record.contract.feedback_intent,
        "reflection_intent": record.contract.reflection_intent,
        "continuation_intent": record.contract.continuation_intent,
    }


def test_serialized_contract_fields_are_not_indexed() -> None:
    record = make_record()
    client = FakeDatastoreClient()

    contract = serialize_generated_practice(record, client)["contract"]

    assert set(contract.exclude_from_indexes) == {
        "purpose",
        "task",
        "expected_thinking",
        "response_contract",
        "evaluation_intent",
        "feedback_intent",
        "reflection_intent",
        "continuation_intent",
    }


def test_deserialization_requires_a_complete_contract() -> None:
    with pytest.raises(ValueError):
        deserialize_generated_practice({"practice_id": str(uuid4())})


def test_datetimes_are_normalised_to_utc() -> None:
    record = make_record()
    serialized = serialize_generated_practice(record, FakeDatastoreClient())
    serialized["created_at"] = datetime(2026, 10, 30, 12, 0)  # naive

    restored = deserialize_generated_practice(serialized)

    assert restored.created_at.tzinfo is UTC
