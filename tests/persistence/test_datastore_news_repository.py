"""Contract tests for the SPEC-041 Datastore news repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fablit.application.news import NewsCategory, NewsStory
from fablit.application.persistence import PersistenceError
from fablit.platform.datastore_news_repository import (
    DEFAULT_NEWS_NAMESPACE,
    NEWS_STORY_KIND,
    DatastoreNewsRepository,
    deserialize_news_story,
)
from tests.persistence.test_datastore_authoring_store import FakeDatastoreClient

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def make_story(**overrides: object) -> NewsStory:
    story_id = uuid4()
    values: dict[str, object] = {
        "story_id": story_id,
        "headline": "Handloom revival connects weavers with new markets",
        "canonical_url": f"https://news.example.com/story/{story_id}",
        "source_name": "The Daily Weave",
        "summary": "A collective is helping weavers reach contemporary buyers.",
        "categories": (NewsCategory.TEXTILES, NewsCategory.INDIAN_CRAFT),
        "educational_relevance": "Notice how local craft meets contemporary design.",
        "retrieved_at": NOW,
        "curated_at": NOW,
        "published_at": NOW - timedelta(days=1),
        "reflection_prompt": "Where do you see a material tradition nearby?",
        "provider": "google-gemini",
        "model": "gemini-2.5-flash",
    }
    values.update(overrides)
    return NewsStory(**values)  # type: ignore[arg-type]


def test_save_and_get_round_trip_in_the_news_namespace() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsRepository(client)
    story = make_story()

    assert repository.save(story) is story

    assert repository.get(story.story_id) == story
    key = client.key(
        NEWS_STORY_KIND,
        str(story.story_id),
        namespace=DEFAULT_NEWS_NAMESPACE,
    )
    entity = client.get(key)
    assert entity is not None
    assert entity.key is not None
    assert entity.key.namespace == "news"
    assert entity["canonical_url"] == story.canonical_url


def test_long_free_text_is_stored_without_indexing() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsRepository(client)
    story = make_story(summary="A" * 1600)

    repository.save(story)

    loaded = repository.get(story.story_id)
    assert loaded is not None
    assert loaded.summary == story.summary
    entity = client.get(
        client.key(
            NEWS_STORY_KIND,
            str(story.story_id),
            namespace=DEFAULT_NEWS_NAMESPACE,
        )
    )
    assert entity is not None
    assert "summary" in entity.exclude_from_indexes


def test_find_by_url_returns_the_stored_story() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsRepository(client)
    story = make_story()
    repository.save(story)

    assert repository.find_by_url(story.canonical_url) == story
    assert repository.find_by_url("https://news.example.com/story/other") is None


def test_list_stories_is_newest_first_with_a_stable_tie_break() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsRepository(client)
    older = make_story(published_at=NOW - timedelta(days=5))
    newer = make_story(published_at=NOW - timedelta(days=1))
    same_time_a = make_story(published_at=NOW)
    same_time_b = make_story(published_at=NOW)
    for story in (older, newer, same_time_a, same_time_b):
        repository.save(story)

    listed = repository.list_stories()

    assert listed[0] in {same_time_a, same_time_b}
    assert listed[1] in {same_time_a, same_time_b}
    assert listed[2] == newer
    assert listed[3] == older
    assert [str(story.story_id) for story in listed[:2]] == [
        str(story.story_id)
        for story in sorted(
            (same_time_a, same_time_b),
            key=lambda item: str(item.story_id),
            reverse=True,
        )
    ]


def test_get_unknown_story_returns_none() -> None:
    repository = DatastoreNewsRepository(FakeDatastoreClient())

    assert repository.get(uuid4()) is None
    assert repository.list_stories() == ()


def test_save_failure_is_reported_as_a_persistence_error() -> None:
    client = FakeDatastoreClient()
    client.fail_next_put = True
    repository = DatastoreNewsRepository(client)

    with pytest.raises(PersistenceError, match="Failed to persist news story"):
        repository.save(make_story())


def test_read_and_query_failures_are_reported_as_persistence_errors() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsRepository(client)
    story = make_story()
    repository.save(story)

    client.fail_next_get = True
    with pytest.raises(PersistenceError, match="Failed to retrieve news story"):
        repository.get(story.story_id)

    client.fail_query = True
    with pytest.raises(PersistenceError, match="Failed to query news stories"):
        repository.list_stories()

    with pytest.raises(PersistenceError, match="Failed to query news stories"):
        repository.find_by_url(story.canonical_url)


def test_an_unreadable_entity_fails_explicitly_rather_than_emptying_the_feed() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsRepository(client)
    key = client.key(
        NEWS_STORY_KIND,
        str(uuid4()),
        namespace=DEFAULT_NEWS_NAMESPACE,
    )
    entity = client.entity(key)
    entity.update({"story_id": key.name})
    client.put(entity)

    with pytest.raises(PersistenceError):
        repository.list_stories()


def test_published_at_may_be_absent() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsRepository(client)
    story = make_story(published_at=None)

    repository.save(story)

    assert repository.get(story.story_id) == story
    assert story.display_at == story.curated_at


def test_deserialization_accepts_iso_strings_and_naive_datetimes() -> None:
    story = make_story()
    entity = {
        "story_id": str(story.story_id),
        "headline": story.headline,
        "canonical_url": story.canonical_url,
        "source_name": story.source_name,
        "summary": story.summary,
        "categories": ["textiles"],
        "educational_relevance": story.educational_relevance,
        "retrieved_at": "2026-10-20T12:00:00+00:00",
        "curated_at": datetime(2026, 10, 20, 12, 0),
        "published_at": None,
        "reflection_prompt": None,
        "provider": "google-gemini",
        "model": "gemini-2.5-flash",
        "validation_status": "published",
    }

    loaded = deserialize_news_story(entity)

    assert loaded.categories == (NewsCategory.TEXTILES,)
    assert loaded.retrieved_at == NOW
    assert loaded.curated_at == NOW
    assert loaded.published_at is None


def test_saving_the_same_story_again_replaces_it_in_place() -> None:
    client = FakeDatastoreClient()
    repository = DatastoreNewsRepository(client)
    story = make_story()
    repository.save(story)
    edited = make_story(
        story_id=story.story_id, canonical_url=story.canonical_url, summary="Updated."
    )
    repository.save(edited)

    assert repository.get(story.story_id) == edited
    assert len(repository.list_stories()) == 1
