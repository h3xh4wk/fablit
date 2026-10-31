"""Contract tests for the SPEC-044 Datastore generated-practice repository.

Generated practices are private: they live in their own kind and namespace,
never in the shared published catalogue, and every read is scoped to the
learner who requested the practice.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from typing import Any
from uuid import UUID, uuid4

import pytest

from fablit.application.errors import LearnerPracticeGenerationError
from fablit.application.learner_practice import (
    ChallengePreference,
    FakeLearnerPracticeGenerator,
    GeneratedPracticeRecord,
    HistoryContext,
    LearnerPracticeGenerationRequest,
    LearnerPracticeGenerationResult,
    PracticeArea,
    PracticeRequest,
    generate_private_practice,
    practice_id_for,
)
from fablit.application.persistence import PersistenceError, StaleGenerationClaimError
from fablit.application.store import PracticeContentContract
from fablit.platform.datastore_learner_practice_repository import (
    DEFAULT_GENERATED_PRACTICE_NAMESPACE,
    GENERATED_PRACTICE_CLAIM_KIND,
    GENERATED_PRACTICE_KIND,
    GENERATED_PRACTICE_RATE_LIMIT_KIND,
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


def test_rate_limit_state_is_shared_across_repository_instances() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreGeneratedPracticeRepository(client)
    instance_b = DatastoreGeneratedPracticeRepository(client)

    assert (
        instance_a.reserve_generation_slot(
            LEARNER, now=NOW, limit=2, window_seconds=3600
        )
        is None
    )
    assert (
        instance_b.reserve_generation_slot(
            LEARNER,
            now=NOW + timedelta(minutes=10),
            limit=2,
            window_seconds=3600,
        )
        is None
    )

    # Third request within the window on either instance is blocked.
    retry_after = instance_a.reserve_generation_slot(
        LEARNER,
        now=NOW + timedelta(minutes=15),
        limit=2,
        window_seconds=3600,
    )
    assert retry_after == 2700

    # Another learner is unaffected.
    assert (
        instance_b.reserve_generation_slot(
            uuid4(),
            now=NOW + timedelta(minutes=15),
            limit=2,
            window_seconds=3600,
        )
        is None
    )

    # Once the first slot expires, a new request is allowed and prunes old entries.
    assert (
        instance_b.reserve_generation_slot(
            LEARNER,
            now=NOW + timedelta(seconds=3600),
            limit=2,
            window_seconds=3600,
        )
        is None
    )
    entity = client.get(
        client.key(
            GENERATED_PRACTICE_RATE_LIMIT_KIND,
            str(LEARNER),
            namespace=DEFAULT_GENERATED_PRACTICE_NAMESPACE,
        )
    )
    assert entity is not None
    assert entity["requested_at"] == [
        NOW + timedelta(minutes=10),
        NOW + timedelta(seconds=3600),
    ]
    assert set(entity.exclude_from_indexes) == {"requested_at", "updated_at"}


def test_rate_limit_works_without_client_transaction_method() -> None:
    class NonTransactionalClient(FakeDatastoreClient):
        transaction = None  # type: ignore[assignment]

    repository = DatastoreGeneratedPracticeRepository(NonTransactionalClient())

    assert (
        repository.reserve_generation_slot(LEARNER, now=NOW, limit=1, window_seconds=60)
        is None
    )
    assert (
        repository.reserve_generation_slot(
            LEARNER,
            now=NOW + timedelta(seconds=20),
            limit=1,
            window_seconds=60,
        )
        == 40
    )


def test_rate_limit_datastore_failure_raises_persistence_error() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreGeneratedPracticeRepository(client)
    client.fail_next_put = True

    with pytest.raises(PersistenceError):
        repository.reserve_generation_slot(LEARNER, now=NOW)

    with pytest.raises(ValueError, match="learner_id"):
        repository.reserve_generation_slot("not-a-uuid", now=NOW)  # type: ignore[arg-type]


def _make_request(*, learner_id: UUID = LEARNER, token: UUID) -> PracticeRequest:
    return PracticeRequest(
        learner_id=learner_id,
        text="I want to practise noticing how colour and texture work together.",
        area=PracticeArea.VISUAL_ANALYSIS,
        response_form="A short written response",
        challenge=ChallengePreference.FAMILIAR,
        created_at=NOW,
        token=token,
    )


def test_concurrent_duplicate_datastore_requests_call_provider_once() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreGeneratedPracticeRepository(client)
    instance_b = DatastoreGeneratedPracticeRepository(client)
    entered_provider = Event()
    release_provider = Event()

    class CoordinatedGenerator(FakeLearnerPracticeGenerator):
        def generate(self, request: LearnerPracticeGenerationRequest) -> Any:
            entered_provider.set()
            release_provider.wait(timeout=2.0)
            return super().generate(request)

    generator = CoordinatedGenerator()
    token = uuid4()
    request_a = _make_request(token=token)
    request_b = _make_request(token=token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(
            generate_private_practice,
            instance_a,
            generator,
            request=request_a,
            history=HistoryContext(),
            now=NOW,
            rate_limit=1,
            rate_window_seconds=3600,
        )
        assert entered_provider.wait(timeout=2.0)
        second_future = pool.submit(
            generate_private_practice,
            instance_b,
            generator,
            request=request_b,
            history=HistoryContext(),
            now=NOW + timedelta(seconds=1),
            rate_limit=1,
            rate_window_seconds=3600,
        )
        release_provider.wait(timeout=0.03)
        release_provider.set()
        first_record = first_future.result(timeout=2.0)
        second_record = second_future.result(timeout=2.0)

    assert first_record == second_record
    assert len(generator.calls) == 1
    assert instance_a.list_for_learner(LEARNER) == (first_record,)
    assert instance_b.get(LEARNER, first_record.practice_id) == first_record
    # The claim entity is cleaned up once the practice is persisted.
    claim_key = client.key(
        GENERATED_PRACTICE_CLAIM_KIND,
        str(first_record.practice_id),
        namespace=DEFAULT_GENERATED_PRACTICE_NAMESPACE,
    )
    assert client.get(claim_key) is None


def test_concurrent_duplicate_datastore_failure_releases_claim() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreGeneratedPracticeRepository(client)
    instance_b = DatastoreGeneratedPracticeRepository(client)
    entered_provider = Event()
    release_provider = Event()

    class FailingGenerator(FakeLearnerPracticeGenerator):
        def generate(self, request: LearnerPracticeGenerationRequest) -> Any:
            self.calls.append(request)
            entered_provider.set()
            release_provider.wait(timeout=2.0)
            raise RuntimeError("provider outage")

    generator = FailingGenerator()
    token = uuid4()
    request = _make_request(token=token)
    practice_id = practice_id_for(LEARNER, token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(
            generate_private_practice,
            instance_a,
            generator,
            request=request,
            history=HistoryContext(),
            now=NOW,
        )
        assert entered_provider.wait(timeout=2.0)
        second_future = pool.submit(
            generate_private_practice,
            instance_b,
            generator,
            request=request,
            history=HistoryContext(),
            now=NOW,
        )
        release_provider.wait(timeout=0.03)
        release_provider.set()

        with pytest.raises(LearnerPracticeGenerationError):
            first_future.result(timeout=2.0)
        with pytest.raises(LearnerPracticeGenerationError):
            second_future.result(timeout=2.0)

    assert len(generator.calls) == 1
    assert (
        client.get(
            client.key(
                GENERATED_PRACTICE_CLAIM_KIND,
                str(practice_id),
                namespace=DEFAULT_GENERATED_PRACTICE_NAMESPACE,
            )
        )
        is None
    )

    # Subsequent retry succeeds now that the claim was released.
    working_generator = FakeLearnerPracticeGenerator()
    recovered = generate_private_practice(
        instance_b,
        working_generator,
        request=request,
        history=HistoryContext(),
        now=NOW + timedelta(seconds=5),
    )
    assert len(working_generator.calls) == 1
    assert instance_a.get(LEARNER, practice_id) == recovered


def test_datastore_claim_expiry_and_learner_ownership_checks() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreGeneratedPracticeRepository(client)
    other_learner = uuid4()
    record = make_record(learner_id=LEARNER)

    with pytest.raises(ValueError, match="GeneratedPracticeRecord"):
        repository.save("not-a-record")  # type: ignore[arg-type]

    # Claim the practice key.
    outcome = repository.claim_generation(
        LEARNER, record.practice_id, now=NOW, ttl_seconds=30
    )
    assert outcome.claimed is True
    assert outcome.existing is None

    # Active claim blocks duplicate claim for same learner.
    duplicate = repository.claim_generation(
        LEARNER,
        record.practice_id,
        now=NOW + timedelta(seconds=10),
        ttl_seconds=30,
    )
    assert duplicate.claimed is False
    assert duplicate.existing is None

    # Another learner cannot claim, save, or await a practice_id owned by LEARNER.
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.claim_generation(
            other_learner,
            record.practice_id,
            now=NOW + timedelta(seconds=10),
            ttl_seconds=30,
        )
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.save(
            make_record(learner_id=other_learner, practice_id=record.practice_id)
        )
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.await_generation(
            other_learner, record.practice_id, timeout_seconds=0.01
        )

    # After TTL expiry, the claim can be re-acquired.
    reclaimed = repository.claim_generation(
        LEARNER,
        record.practice_id,
        now=NOW + timedelta(seconds=31),
        ttl_seconds=30,
    )
    assert reclaimed.claimed is True
    assert isinstance(reclaimed.claim_token, UUID)
    assert reclaimed.claim_token != outcome.claim_token

    # The expired claim owner cannot release, renew, or overwrite the replacement.
    assert (
        repository.release_generation_claim(
            LEARNER,
            record.practice_id,
            outcome.claim_token,
        )
        is False
    )
    assert (
        repository.renew_generation_claim(
            LEARNER,
            record.practice_id,
            outcome.claim_token,
            now=NOW + timedelta(seconds=32),
            ttl_seconds=30,
        )
        is False
    )
    with pytest.raises(StaleGenerationClaimError):
        repository.save(record, claim_token=outcome.claim_token)
    with pytest.raises(StaleGenerationClaimError):
        repository.save(record)

    # Saving with the replacement token persists the record and clears the claim.
    repository.save(record, claim_token=reclaimed.claim_token)
    already_saved = repository.claim_generation(
        LEARNER,
        record.practice_id,
        now=NOW + timedelta(seconds=32),
        ttl_seconds=30,
    )
    assert already_saved.claimed is False
    assert already_saved.existing == record

    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.claim_generation(other_learner, record.practice_id, now=NOW)
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.save(
            make_record(learner_id=other_learner, practice_id=record.practice_id)
        )


def test_datastore_claim_and_save_work_without_client_transaction_method() -> None:
    class NonTransactionalClient(FakeDatastoreClient):
        transaction = None  # type: ignore[assignment]

    repository = DatastoreGeneratedPracticeRepository(NonTransactionalClient())
    record = make_record(learner_id=LEARNER)

    outcome = repository.claim_generation(LEARNER, record.practice_id, now=NOW)
    assert outcome.claimed is True
    assert (
        repository.release_generation_claim(
            LEARNER,
            record.practice_id,
            outcome.claim_token,
        )
        is True
    )
    assert repository.save(record) == record
    assert repository.save(record) == record


def test_datastore_expired_claim_owner_cannot_release_or_overwrite_replacement() -> (
    None
):
    client = FakeDatastoreClient()
    instance_a = DatastoreGeneratedPracticeRepository(client)
    instance_b = DatastoreGeneratedPracticeRepository(client)
    record_a = make_record(learner_id=LEARNER, title="Stale worker practice")
    record_b = make_record(
        learner_id=LEARNER,
        practice_id=record_a.practice_id,
        request_token=record_a.request_token,
        title="Replacement worker practice",
    )

    claim_a = instance_a.claim_generation(
        LEARNER,
        record_a.practice_id,
        now=NOW,
        ttl_seconds=30,
    )
    assert claim_a.claimed is True
    assert isinstance(claim_a.claim_token, UUID)

    # Lease expires; instance_b acquires a replacement claim.
    claim_b = instance_b.claim_generation(
        LEARNER,
        record_a.practice_id,
        now=NOW + timedelta(seconds=31),
        ttl_seconds=30,
    )
    assert claim_b.claimed is True
    assert isinstance(claim_b.claim_token, UUID)
    assert claim_b.claim_token != claim_a.claim_token

    # instance_a cannot release, renew, or save using its stale claim_token.
    assert (
        instance_a.release_generation_claim(
            LEARNER,
            record_a.practice_id,
            claim_a.claim_token,
            error=LearnerPracticeGenerationError("stale failure"),
        )
        is False
    )
    assert (
        instance_a.renew_generation_claim(
            LEARNER,
            record_a.practice_id,
            claim_a.claim_token,
            now=NOW + timedelta(seconds=32),
            ttl_seconds=30,
        )
        is False
    )
    with pytest.raises(StaleGenerationClaimError):
        instance_a.save(record_a, claim_token=claim_a.claim_token)

    # Replacement claim in Datastore is still intact with claim_b's token.
    claim_entity = client.get(
        client.key(
            GENERATED_PRACTICE_CLAIM_KIND,
            str(record_a.practice_id),
            namespace=DEFAULT_GENERATED_PRACTICE_NAMESPACE,
        )
    )
    assert claim_entity is not None
    assert claim_entity["claim_token"] == str(claim_b.claim_token)

    # instance_b can renew and complete its replacement claim.
    assert (
        instance_b.renew_generation_claim(
            LEARNER,
            record_b.practice_id,
            claim_b.claim_token,
            now=NOW + timedelta(seconds=45),
            ttl_seconds=30,
        )
        is True
    )
    saved = instance_b.save(record_b, claim_token=claim_b.claim_token)
    assert saved == record_b

    # If instance_a arrives late to save after B already persisted, B's record wins.
    assert instance_a.save(record_a, claim_token=claim_a.claim_token) == record_b
    assert instance_a.get(LEARNER, record_b.practice_id) == record_b


def test_datastore_stale_failed_worker_does_not_delete_replacement_claim() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreGeneratedPracticeRepository(client)
    instance_b = DatastoreGeneratedPracticeRepository(client)
    instance_c = DatastoreGeneratedPracticeRepository(client)
    token = uuid4()
    request = PracticeRequest(
        learner_id=LEARNER,
        text="I want to practise describing colour and texture in an outfit.",
        area=PracticeArea.CREATIVE_ABILITY,
        response_form="A short written response",
        challenge=ChallengePreference.FAMILIAR,
        include_history=False,
        created_at=NOW,
        token=token,
    )
    first_entered = Event()
    release_first = Event()
    second_entered = Event()
    release_second = Event()

    class StaleThenValidGenerator(FakeLearnerPracticeGenerator):
        def generate(
            self, generation_request: LearnerPracticeGenerationRequest
        ) -> LearnerPracticeGenerationResult:
            call_number = len(self.calls) + 1
            result = super().generate(generation_request)
            if call_number == 1:
                first_entered.set()
                release_first.wait(timeout=2.0)
                raise RuntimeError("stale worker failed after lease expiry")
            second_entered.set()
            release_second.wait(timeout=2.0)
            return result

    generator = StaleThenValidGenerator()

    with ThreadPoolExecutor(max_workers=3) as pool:
        future_a = pool.submit(
            generate_private_practice,
            instance_a,
            generator,
            request=request,
            history=HistoryContext(),
            now=NOW,
            claim_ttl_seconds=30,
            claim_renewal_interval_seconds=0.0,
        )
        assert first_entered.wait(timeout=2.0)

        future_b = pool.submit(
            generate_private_practice,
            instance_b,
            generator,
            request=request,
            history=HistoryContext(),
            now=NOW + timedelta(seconds=31),
            claim_ttl_seconds=30,
            claim_renewal_interval_seconds=0.0,
        )
        assert second_entered.wait(timeout=2.0)

        # Request A fails now and runs release_generation_claim with its stale token.
        release_first.set()
        with pytest.raises(LearnerPracticeGenerationError):
            future_a.result(timeout=2.0)

        # Request C arrives on a third instance; B's Datastore claim is still active.
        future_c = pool.submit(
            generate_private_practice,
            instance_c,
            generator,
            request=request,
            history=HistoryContext(),
            now=NOW + timedelta(seconds=35),
            claim_ttl_seconds=30,
            claim_renewal_interval_seconds=0.0,
        )
        release_second.wait(timeout=0.03)
        release_second.set()

        record_b = future_b.result(timeout=2.0)
        record_c = future_c.result(timeout=2.0)

    assert len(generator.calls) == 2
    assert record_b == record_c
    assert instance_a.get(LEARNER, record_b.practice_id) == record_b


def test_datastore_stale_completing_worker_resolves_to_replacement_record() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreGeneratedPracticeRepository(client)
    instance_b = DatastoreGeneratedPracticeRepository(client)
    token = uuid4()
    request = PracticeRequest(
        learner_id=LEARNER,
        text="I want to practise describing colour and texture in an outfit.",
        area=PracticeArea.CREATIVE_ABILITY,
        response_form="A short written response",
        challenge=ChallengePreference.FAMILIAR,
        include_history=False,
        created_at=NOW,
        token=token,
    )
    first_entered = Event()
    release_first = Event()
    second_entered = Event()
    release_second = Event()

    class TwoWorkerGenerator(FakeLearnerPracticeGenerator):
        def generate(
            self, generation_request: LearnerPracticeGenerationRequest
        ) -> LearnerPracticeGenerationResult:
            call_number = len(self.calls) + 1
            result = super().generate(generation_request)
            if call_number == 1:
                first_entered.set()
                release_first.wait(timeout=2.0)
                return LearnerPracticeGenerationResult(
                    candidate_data={
                        **result.candidate_data,
                        "title": "Stale worker title",
                    },
                    provider=result.provider,
                    model=result.model,
                    generated_at=result.generated_at,
                )
            second_entered.set()
            release_second.wait(timeout=2.0)
            return LearnerPracticeGenerationResult(
                candidate_data={
                    **result.candidate_data,
                    "title": "Replacement worker title",
                },
                provider=result.provider,
                model=result.model,
                generated_at=result.generated_at,
            )

    generator = TwoWorkerGenerator()

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(
            generate_private_practice,
            instance_a,
            generator,
            request=request,
            history=HistoryContext(),
            now=NOW,
            claim_ttl_seconds=30,
            claim_renewal_interval_seconds=0.0,
        )
        assert first_entered.wait(timeout=2.0)

        future_b = pool.submit(
            generate_private_practice,
            instance_b,
            generator,
            request=request,
            history=HistoryContext(),
            now=NOW + timedelta(seconds=31),
            claim_ttl_seconds=30,
            claim_renewal_interval_seconds=0.0,
        )
        assert second_entered.wait(timeout=2.0)

        # Worker A finishes first while Worker B owns the replacement claim.
        release_first.set()
        release_second.wait(timeout=0.03)
        release_second.set()

        record_a = future_a.result(timeout=2.0)
        record_b = future_b.result(timeout=2.0)

    assert record_a == record_b
    assert record_b.title == "Replacement worker title"
    assert instance_a.get(LEARNER, record_b.practice_id) == record_b


def test_datastore_active_generation_renews_lease_across_instances() -> None:
    client = FakeDatastoreClient()
    instance_a = DatastoreGeneratedPracticeRepository(client)
    instance_b = DatastoreGeneratedPracticeRepository(client)
    token = uuid4()
    request = PracticeRequest(
        learner_id=LEARNER,
        text="I want to practise describing colour and texture in an outfit.",
        area=PracticeArea.CREATIVE_ABILITY,
        response_form="A short written response",
        challenge=ChallengePreference.FAMILIAR,
        include_history=False,
        created_at=NOW,
        token=token,
    )
    entered_provider = Event()
    release_provider = Event()

    class SlowGenerator(FakeLearnerPracticeGenerator):
        def generate(
            self, generation_request: LearnerPracticeGenerationRequest
        ) -> LearnerPracticeGenerationResult:
            entered_provider.set()
            release_provider.wait(timeout=2.0)
            return super().generate(generation_request)

    generator = SlowGenerator()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(
            generate_private_practice,
            instance_a,
            generator,
            request=request,
            history=HistoryContext(),
            now=NOW,
            claim_ttl_seconds=1,
            claim_renewal_interval_seconds=0.02,
        )
        assert entered_provider.wait(timeout=2.0)
        release_provider.wait(timeout=0.06)

        second_future = pool.submit(
            generate_private_practice,
            instance_b,
            generator,
            request=request,
            history=HistoryContext(),
            now=NOW + timedelta(seconds=1),
            claim_ttl_seconds=1,
        )
        release_provider.wait(timeout=0.03)
        release_provider.set()

        first_record = first_future.result(timeout=2.0)
        second_record = second_future.result(timeout=2.0)

    assert first_record == second_record
    assert len(generator.calls) == 1


def test_datastore_crashed_worker_recovery_after_lease_expires() -> None:
    client = FakeDatastoreClient()
    crashed_instance = DatastoreGeneratedPracticeRepository(client)
    retry_instance = DatastoreGeneratedPracticeRepository(client)
    token = uuid4()
    request = PracticeRequest(
        learner_id=LEARNER,
        text="I want to practise describing colour and texture in an outfit.",
        area=PracticeArea.CREATIVE_ABILITY,
        response_form="A short written response",
        challenge=ChallengePreference.FAMILIAR,
        include_history=False,
        created_at=NOW,
        token=token,
    )
    practice_id = practice_id_for(LEARNER, token)

    # Simulate a worker that claimed the key and crashed without releasing it.
    abandoned = crashed_instance.claim_generation(
        LEARNER,
        practice_id,
        now=NOW,
        ttl_seconds=30,
    )
    assert abandoned.claimed is True

    # Once the lease expires, a retry on another instance recovers and completes.
    generator = FakeLearnerPracticeGenerator()
    recovered = generate_private_practice(
        retry_instance,
        generator,
        request=request,
        history=HistoryContext(),
        now=NOW + timedelta(seconds=31),
        claim_ttl_seconds=30,
    )
    assert len(generator.calls) == 1
    assert retry_instance.get(LEARNER, practice_id) == recovered
