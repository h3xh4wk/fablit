"""Application tests for private story-linked responses (SPEC-044 §6.1)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fablit.application.errors import InvalidStoryResponseInputError
from fablit.application.news import NewsCategory, NewsStory
from fablit.application.persistence import PersistenceError
from fablit.application.story_responses import (
    EMPTY_RESPONSE_MESSAGE,
    NO_PROMPT_MESSAGE,
    TOO_LONG_RESPONSE_MESSAGE,
    InMemoryStoryResponseRepository,
    get_story_response,
    list_story_responses,
    new_story_response_request_id,
    normalize_story_response_text,
    save_story_response,
    story_response_id,
)
from fablit.domain import StoryResponse
from fablit.domain.story_response import MAX_STORY_RESPONSE_CHARS

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
PROMPT = "Where do you see a material tradition nearby?"


def make_story(**overrides: object) -> NewsStory:
    """Build a valid published story with a "What to try" prompt."""
    story_id = uuid4()
    values: dict[str, object] = {
        "story_id": story_id,
        "headline": "Handloom revival connects weavers with new markets",
        "canonical_url": f"https://news.example.com/story/{story_id}",
        "source_name": "The Daily Weave",
        "summary": "A collective is helping weavers reach contemporary buyers.",
        "categories": (NewsCategory.TEXTILES,),
        "educational_relevance": "Notice how local craft meets contemporary design.",
        "retrieved_at": NOW,
        "curated_at": NOW,
        "published_at": NOW,
        "reflection_prompt": PROMPT,
        "provider": "fake-news-curation",
        "model": "fake-model",
    }
    values.update(overrides)
    return NewsStory(**values)  # type: ignore[arg-type]


def test_save_captures_story_and_prompt_provenance() -> None:
    repository = InMemoryStoryResponseRepository()
    learner_id = uuid4()
    story = make_story()

    response = save_story_response(
        repository,
        learner_id=learner_id,
        story=story,
        response_text="  A tailor near me repairs clothes instead of replacing them.  ",
        request_id=uuid4(),
        saved_at=NOW,
    )

    assert response.learner_id == learner_id
    assert response.story_id == story.story_id
    assert response.story_headline == story.headline
    assert response.story_source_name == story.source_name
    assert response.canonical_url == story.canonical_url
    assert response.prompt == PROMPT
    assert response.response_text == (
        "A tailor near me repairs clothes instead of replacing them."
    )
    assert response.created_at == NOW
    assert repository.get(learner_id, response.id) == response


def test_response_save_is_idempotent_for_one_composer_token() -> None:
    repository = InMemoryStoryResponseRepository()
    learner_id = uuid4()
    story = make_story()
    request_id = uuid4()

    first = save_story_response(
        repository,
        learner_id=learner_id,
        story=story,
        response_text="First version.",
        request_id=request_id,
        saved_at=NOW,
    )
    retried = save_story_response(
        repository,
        learner_id=learner_id,
        story=story,
        response_text="First version.",
        request_id=request_id,
        saved_at=NOW + timedelta(minutes=1),
    )

    assert retried == first
    assert len(repository.list_for_learner(learner_id)) == 1


def test_each_composer_render_creates_a_separate_response() -> None:
    repository = InMemoryStoryResponseRepository()
    learner_id = uuid4()
    story = make_story()

    first = save_story_response(
        repository,
        learner_id=learner_id,
        story=story,
        response_text="One observation.",
        request_id=uuid4(),
        saved_at=NOW,
    )
    second = save_story_response(
        repository,
        learner_id=learner_id,
        story=story,
        response_text="Another observation.",
        request_id=uuid4(),
        saved_at=NOW + timedelta(minutes=1),
    )

    assert first.id != second.id
    assert first.response_text != second.response_text
    assert len(repository.list_for_learner(learner_id)) == 2


def test_response_identity_is_stable_for_learner_and_token() -> None:
    learner_id = uuid4()
    request_id = uuid4()

    assert story_response_id(learner_id, request_id) == story_response_id(
        learner_id, request_id
    )
    assert story_response_id(learner_id, request_id) != story_response_id(
        learner_id, uuid4()
    )
    assert story_response_id(learner_id, request_id) != story_response_id(
        uuid4(), request_id
    )


def test_new_request_tokens_are_unique() -> None:
    assert new_story_response_request_id() != new_story_response_request_id()


@pytest.mark.parametrize("text", ["", "   \n\t"])
def test_empty_response_is_refused_with_actionable_copy(text: str) -> None:
    with pytest.raises(InvalidStoryResponseInputError) as excinfo:
        normalize_story_response_text(text)

    assert str(excinfo.value) == EMPTY_RESPONSE_MESSAGE


def test_overlong_response_is_refused_with_actionable_copy() -> None:
    with pytest.raises(InvalidStoryResponseInputError) as excinfo:
        normalize_story_response_text("a" * (MAX_STORY_RESPONSE_CHARS + 1))

    assert str(excinfo.value) == TOO_LONG_RESPONSE_MESSAGE


def test_response_at_the_bound_is_accepted() -> None:
    text = "a" * MAX_STORY_RESPONSE_CHARS

    assert normalize_story_response_text(text) == text


def test_story_without_a_prompt_cannot_be_responded_to() -> None:
    repository = InMemoryStoryResponseRepository()

    with pytest.raises(InvalidStoryResponseInputError) as excinfo:
        save_story_response(
            repository,
            learner_id=uuid4(),
            story=make_story(reflection_prompt=None),
            response_text="A response.",
            request_id=uuid4(),
        )

    assert str(excinfo.value) == NO_PROMPT_MESSAGE


def test_response_lookup_and_listing_are_learner_scoped() -> None:
    repository = InMemoryStoryResponseRepository()
    learner_a = uuid4()
    learner_b = uuid4()
    story = make_story()
    a_response = save_story_response(
        repository,
        learner_id=learner_a,
        story=story,
        response_text="Learner A's private note.",
        request_id=uuid4(),
        saved_at=NOW,
    )
    save_story_response(
        repository,
        learner_id=learner_b,
        story=story,
        response_text="Learner B's private note.",
        request_id=uuid4(),
        saved_at=NOW,
    )

    assert (
        get_story_response(repository, learner_id=learner_a, response_id=a_response.id)
        == a_response
    )
    assert (
        get_story_response(repository, learner_id=learner_b, response_id=a_response.id)
        is None
    )
    assert list_story_responses(repository, learner_id=learner_a) == (a_response,)
    assert len(list_story_responses(repository, learner_id=learner_b)) == 1
    assert list_story_responses(repository, learner_id=uuid4()) == ()


def test_listing_is_newest_first_with_a_stable_tie_break() -> None:
    repository = InMemoryStoryResponseRepository()
    learner_id = uuid4()
    story = make_story()
    older = save_story_response(
        repository,
        learner_id=learner_id,
        story=story,
        response_text="Older.",
        request_id=uuid4(),
        saved_at=NOW - timedelta(days=1),
    )
    newer = save_story_response(
        repository,
        learner_id=learner_id,
        story=story,
        response_text="Newer.",
        request_id=uuid4(),
        saved_at=NOW,
    )

    assert list_story_responses(repository, learner_id=learner_id) == (
        newer,
        older,
    )


def test_repository_rejects_non_response_records() -> None:
    repository = InMemoryStoryResponseRepository()

    with pytest.raises(ValueError, match="StoryResponse"):
        repository.save("not a response")  # type: ignore[arg-type]


def test_repository_returns_none_for_invalid_identities() -> None:
    repository = InMemoryStoryResponseRepository()

    assert repository.get("learner", uuid4()) is None  # type: ignore[arg-type]
    assert repository.get(uuid4(), "response") is None  # type: ignore[arg-type]
    assert repository.list_for_learner("learner") == ()  # type: ignore[arg-type]


def test_concurrent_duplicate_story_response_saves_resolve_to_one_record() -> None:
    repository = InMemoryStoryResponseRepository()
    learner_id = uuid4()
    story = make_story()
    request_id = uuid4()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(
                save_story_response,
                repository,
                learner_id=learner_id,
                story=story,
                response_text=f"Submission attempt {index}",
                request_id=request_id,
                saved_at=NOW + timedelta(seconds=index),
            )
            for index in range(4)
        ]
        results = [future.result(timeout=2.0) for future in futures]

    assert all(result == results[0] for result in results)
    assert list_story_responses(repository, learner_id=learner_id) == (results[0],)


def test_repository_rejects_colliding_id_owned_by_another_learner() -> None:
    repository = InMemoryStoryResponseRepository()
    learner_a = uuid4()
    learner_b = uuid4()
    story = make_story()
    saved = save_story_response(
        repository,
        learner_id=learner_a,
        story=story,
        response_text="Learner A's note.",
        request_id=uuid4(),
        saved_at=NOW,
    )
    colliding = StoryResponse(
        learner_id=learner_b,
        story_id=story.story_id,
        story_headline=story.headline,
        story_source_name=story.source_name,
        canonical_url=story.canonical_url,
        prompt=PROMPT,
        response_text="Learner B trying to overwrite.",
        created_at=NOW,
        id=saved.id,
        request_id=uuid4(),
    )

    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.save(colliding)
