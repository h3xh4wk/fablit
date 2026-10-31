"""Contract tests for the SPEC-044 Datastore story response repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from fablit.application.persistence import PersistenceError
from fablit.domain import StoryResponse
from fablit.platform.datastore_story_response_repository import (
    DEFAULT_STORY_RESPONSE_NAMESPACE,
    STORY_RESPONSE_KIND,
    DatastoreStoryResponseRepository,
    deserialize_story_response,
)
from tests.persistence.test_datastore_authoring_store import FakeDatastoreClient

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def make_response(**overrides: object) -> StoryResponse:
    story_id = uuid4()
    values: dict[str, object] = {
        "learner_id": uuid4(),
        "story_id": story_id,
        "story_headline": "Handloom revival connects weavers with new markets",
        "story_source_name": "The Daily Weave",
        "canonical_url": f"https://news.example.com/story/{story_id}",
        "prompt": "Where do you see a material tradition nearby?",
        "response_text": "A tailor near me repairs clothes before replacing them.",
        "created_at": NOW,
        "id": uuid4(),
        "request_id": uuid4(),
    }
    values.update(overrides)
    return StoryResponse(**values)  # type: ignore[arg-type]


def test_save_and_get_round_trip_in_the_private_namespace() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreStoryResponseRepository(client)
    response = make_response()

    assert repository.save(response) == response

    assert repository.get(response.learner_id, response.id) == response
    key = client.key(
        STORY_RESPONSE_KIND,
        str(response.id),
        namespace=DEFAULT_STORY_RESPONSE_NAMESPACE,
    )
    entity = client.get(key)
    assert entity is not None
    assert entity.key is not None
    assert entity.key.namespace == "story-responses"
    assert entity["learner_id"] == str(response.learner_id)
    assert entity["response_text"] == response.response_text


def test_long_learner_text_is_stored_without_indexing() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreStoryResponseRepository(client)
    response = make_response(response_text="A" * 1600)

    repository.save(response)

    loaded = repository.get(response.learner_id, response.id)
    assert loaded is not None
    assert loaded.response_text == response.response_text
    entity = client.get(
        client.key(
            STORY_RESPONSE_KIND,
            str(response.id),
            namespace=DEFAULT_STORY_RESPONSE_NAMESPACE,
        )
    )
    assert entity is not None
    assert "response_text" in entity.exclude_from_indexes


def test_get_is_learner_scoped() -> None:
    repository = DatastoreStoryResponseRepository(FakeDatastoreClient())
    response = make_response()
    repository.save(response)

    assert repository.get(uuid4(), response.id) is None
    assert repository.get(response.learner_id, response.id) == response
    assert repository.get(response.learner_id, uuid4()) is None


def test_listing_is_learner_scoped_and_newest_first() -> None:
    repository = DatastoreStoryResponseRepository(FakeDatastoreClient())
    learner_a = uuid4()
    learner_b = uuid4()
    older = make_response(
        learner_id=learner_a,
        created_at=NOW - timedelta(days=1),
    )
    newer = make_response(learner_id=learner_a, created_at=NOW)
    other = make_response(learner_id=learner_b, created_at=NOW)
    for response in (older, newer, other):
        repository.save(response)

    assert repository.list_for_learner(learner_a) == (newer, older)
    assert repository.list_for_learner(learner_b) == (other,)
    assert repository.list_for_learner(uuid4()) == ()


def test_retrying_the_same_response_returns_the_existing_record() -> None:
    repository = DatastoreStoryResponseRepository(FakeDatastoreClient())
    response = make_response()
    repository.save(response)
    retried = make_response(
        id=response.id,
        learner_id=response.learner_id,
        request_id=response.request_id,
        response_text="A duplicate retry with different text.",
    )

    stored = repository.save(retried)

    assert stored.response_text == response.response_text
    assert len(repository.list_for_learner(response.learner_id)) == 1


def test_save_failure_is_reported_as_a_persistence_error() -> None:
    client = FakeDatastoreClient()
    client.fail_next_put = True
    repository = DatastoreStoryResponseRepository(client)

    with pytest.raises(PersistenceError, match="Failed to persist story response"):
        repository.save(make_response())


def test_read_and_query_failures_are_reported_as_persistence_errors() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreStoryResponseRepository(client)
    response = make_response()
    repository.save(response)

    client.fail_next_get = True
    with pytest.raises(PersistenceError, match="Failed to retrieve story response"):
        repository.get(response.learner_id, response.id)

    client.fail_query = True
    with pytest.raises(PersistenceError, match="Failed to query story responses"):
        repository.list_for_learner(response.learner_id)


def test_an_unreadable_entity_fails_explicitly() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreStoryResponseRepository(client)
    key = client.key(
        STORY_RESPONSE_KIND,
        str(uuid4()),
        namespace=DEFAULT_STORY_RESPONSE_NAMESPACE,
    )
    entity = client.entity(key)
    entity.update({"response_id": key.name})
    client.put(entity)

    with pytest.raises(PersistenceError, match="Failed to reconstruct"):
        repository.get(uuid4(), UUID(key.name))


def test_invalid_identities_are_safe_no_ops() -> None:
    repository = DatastoreStoryResponseRepository(FakeDatastoreClient())

    assert repository.get("learner", uuid4()) is None  # type: ignore[arg-type]
    assert repository.get(uuid4(), "response") is None  # type: ignore[arg-type]
    assert repository.list_for_learner("learner") == ()  # type: ignore[arg-type]


def test_deserialization_accepts_iso_strings_and_naive_datetimes() -> None:
    response = make_response()
    entity: dict[str, object] = {
        "response_id": str(response.id),
        "request_id": str(response.request_id),
        "learner_id": str(response.learner_id),
        "story_id": str(response.story_id),
        "story_headline": response.story_headline,
        "story_source_name": response.story_source_name,
        "canonical_url": response.canonical_url,
        "prompt": response.prompt,
        "response_text": response.response_text,
        "created_at": "2026-10-30T12:00:00+00:00",
    }

    loaded = deserialize_story_response(entity)

    assert loaded == response

    entity["created_at"] = datetime(2026, 10, 30, 12, 0)
    assert deserialize_story_response(entity).created_at == NOW
