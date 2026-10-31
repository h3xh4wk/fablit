"""Web tests for SPEC-044 story-linked responses.

Covers the inline "Try this" action, private persistence and provenance,
learner isolation, retry idempotency, honest failure handling, and the return
path through the learner's private history.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application.news import InMemoryNewsRepository, NewsCategory, NewsStory
from fablit.application.persistence import PersistenceError
from fablit.application.story_responses import (
    StoryResponseRepository,
    list_story_responses,
)
from fablit.config import load_config
from fablit.domain import StoryResponse

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
SOURCE_NAME = "The Daily Weave"
PROMPT = "Where do you see a material tradition nearby?"


def _app() -> FastAPI:
    return create_app(
        load_config(
            overrides={
                "environment": "testing",
                "news_repository": "memory",
                "story_response_repository": "memory",
            }
        )
    )


def _client() -> tuple[TestClient, FastAPI]:
    """A client over an app whose in-memory stores stay as configured.

    The test client is not used as a context manager: the application's
    lifespan rebuilds the in-memory repositories on startup, which would
    discard stories seeded before the client is used. Existing news tests use
    the same pattern.
    """
    app = _app()
    return TestClient(app), app


def make_story(**overrides: object) -> NewsStory:
    story_id = uuid4()
    values: dict[str, object] = {
        "story_id": story_id,
        "headline": "Handloom revival connects weavers with new markets",
        "canonical_url": f"https://news.example.com/story/{story_id}",
        "source_name": SOURCE_NAME,
        "summary": "A collective is helping weavers reach contemporary buyers.",
        "categories": (NewsCategory.TEXTILES, NewsCategory.INDIAN_CRAFT),
        "educational_relevance": "Notice how local craft meets contemporary design.",
        "retrieved_at": NOW,
        "curated_at": NOW,
        "published_at": NOW - timedelta(days=1),
        "reflection_prompt": PROMPT,
        "provider": "fake-news-curation",
        "model": "fake-model",
    }
    values.update(overrides)
    return NewsStory(**values)  # type: ignore[arg-type]


def _save_story(app: FastAPI, story: NewsStory) -> None:
    repository = app.state.news_repository
    assert isinstance(repository, InMemoryNewsRepository)
    repository.save(story)


def _response_token(html: str) -> str:
    match = re.search(r'name="request_id"\s+value="([^"]+)"', html)
    assert match is not None, "story composer token not found"
    return match.group(1)


def _story_response_hrefs(html: str) -> list[str]:
    return re.findall(r'href="(/history/story-responses/[^"]+)"', html)


def _repository(app: FastAPI) -> StoryResponseRepository:
    repository = app.state.story_response_repository
    assert isinstance(repository, StoryResponseRepository)
    return repository


class FailingStoryResponseRepository(StoryResponseRepository):
    """A repository that refuses every write, for honest-failure tests."""

    def save(self, response: StoryResponse) -> StoryResponse:
        raise PersistenceError("simulated private-store outage")

    def get(self, learner_id: UUID, response_id: UUID) -> StoryResponse | None:
        return None

    def list_for_learner(self, learner_id: UUID) -> tuple[StoryResponse, ...]:
        return ()


# --- Composer reachability ---------------------------------------------------


def test_story_with_a_prompt_offers_a_try_this_action() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)

    page = client.get("/pulse")

    assert page.status_code == 200
    assert "Try this" in page.text
    assert f'action="/pulse/stories/{story.story_id}/responses"' in page.text
    assert PROMPT in page.text
    assert f'id="story-{story.story_id}"' in page.text


def test_story_without_a_prompt_offers_no_composer() -> None:
    client, app = _client()
    story = make_story(reflection_prompt=None)
    _save_story(app, story)

    page = client.get("/pulse")

    assert page.status_code == 200
    assert "Try this" not in page.text
    assert f'action="/pulse/stories/{story.story_id}/responses"' not in page.text


# --- Saving and history ------------------------------------------------------


def test_saving_a_story_response_is_private_history_and_not_a_completion() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)
    text = "A tailor near me repairs clothes instead of replacing them."

    feed = client.get("/pulse")
    learner_id = UUID(client.cookies["fablit_learner_id"])
    saved = client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={
            "response_text": text,
            "request_id": _response_token(feed.text),
        },
        follow_redirects=False,
    )
    history = client.get(saved.headers["location"])

    assert saved.status_code == 303
    assert history.status_code == 200
    assert "Saved." in history.text
    assert story.headline in history.text

    history_page = client.get("/history")

    assert history_page.status_code == 200
    assert story.headline in history_page.text
    assert text in history_page.text
    assert "No completed practice yet" in history_page.text
    assert "Review this practice" not in history_page.text

    stored = list_story_responses(
        _repository(app),
        learner_id=learner_id,
    )
    assert len(stored) == 1


def test_story_response_review_keeps_story_and_prompt_provenance() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)
    text = "A hand-printed textile stall in my local market."

    feed = client.get("/pulse")
    client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={
            "response_text": text,
            "request_id": _response_token(feed.text),
        },
    )
    history = client.get("/history")
    href = _story_response_hrefs(history.text)[0]
    review = client.get(href)

    assert review.status_code == 200
    assert story.headline in review.text
    assert SOURCE_NAME in review.text
    assert PROMPT in review.text
    assert text in review.text
    assert story.canonical_url in review.text
    assert "not a completed practice" in review.text


def test_retrying_the_same_composer_token_creates_one_response() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)
    text = "One observation, submitted twice by a slow browser."

    feed = client.get("/pulse")
    token = _response_token(feed.text)
    first = client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={"response_text": text, "request_id": token},
        follow_redirects=True,
    )
    second = client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={"response_text": text, "request_id": token},
        follow_redirects=True,
    )
    history = client.get("/history")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(_story_response_hrefs(history.text)) == 1


# --- Privacy ----------------------------------------------------------------


def test_two_learners_never_see_each_others_story_responses() -> None:
    app = _app()
    story = make_story()
    _save_story(app, story)
    learner_a = TestClient(app)
    learner_b = TestClient(app)

    feed = learner_a.get("/pulse")
    saved = learner_a.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={
            "response_text": "Learner A private observation.",
            "request_id": _response_token(feed.text),
        },
        follow_redirects=False,
    )
    response_id = saved.headers["location"].split("saved=")[1].split("#")[0]

    a_history = learner_a.get("/history")
    b_history = learner_b.get("/history")
    b_review = learner_b.get(f"/history/story-responses/{response_id}")

    assert "Learner A private observation." in a_history.text
    assert "Learner A private observation." not in b_history.text
    assert _story_response_hrefs(b_history.text) == []
    assert b_review.status_code == 404
    assert "Learner A private observation." not in b_review.text


def test_a_forged_saved_parameter_does_not_confirm_another_learners_response() -> None:
    app = _app()
    story = make_story()
    _save_story(app, story)
    learner_a = TestClient(app)
    learner_b = TestClient(app)

    feed = learner_a.get("/pulse")
    saved = learner_a.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={
            "response_text": "Learner A private observation.",
            "request_id": _response_token(feed.text),
        },
        follow_redirects=False,
    )
    response_id = saved.headers["location"].split("saved=")[1].split("#")[0]
    forged = learner_b.get(f"/pulse?saved={response_id}")

    assert forged.status_code == 200
    assert "Saved." not in forged.text


# --- Validation and failure --------------------------------------------------


def test_empty_story_response_is_refused_and_the_composer_stays_open() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)

    feed = client.get("/pulse")
    response = client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={
            "response_text": "   ",
            "request_id": _response_token(feed.text),
        },
        follow_redirects=False,
    )
    history = client.get("/history")

    assert response.status_code == 400
    assert "Write a short response before saving it." in response.text
    assert " open>" in response.text
    assert "Saved." not in response.text
    assert _story_response_hrefs(history.text) == []


def test_overlong_story_response_is_refused_with_actionable_copy() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)

    feed = client.get("/pulse")
    response = client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={
            "response_text": "a" * 2001,
            "request_id": _response_token(feed.text),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "2000 characters or fewer" in response.text
    assert "Saved." not in response.text


def test_persistence_failure_is_honest_and_keeps_the_learners_words() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)
    app.state.story_response_repository = FailingStoryResponseRepository()
    text = "The words the learner does not want to lose."

    feed = client.get("/pulse")
    response = client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={"response_text": text, "request_id": _response_token(feed.text)},
        follow_redirects=False,
    )
    history = client.get("/history")

    assert response.status_code == 503
    assert "We couldn&#39;t save your response." in response.text
    assert text in response.text
    assert "Saved." not in response.text
    assert _story_response_hrefs(history.text) == []


def test_unknown_story_is_not_found() -> None:
    client, _ = _client()

    response = client.post(
        f"/pulse/stories/{uuid4()}/responses",
        data={"response_text": "A response.", "request_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert "Story not found." in response.text


def test_story_without_a_prompt_rejects_a_direct_submission() -> None:
    client, app = _client()
    story = make_story(reflection_prompt=None)
    _save_story(app, story)

    response = client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={"response_text": "A response.", "request_id": str(uuid4())},
    )

    assert response.status_code == 400
    assert "does not have a prompt" in response.text


def test_learner_text_is_escaped_when_rendered() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)
    payload = "<script>alert('hello')</script>"

    feed = client.get("/pulse")
    client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={
            "response_text": payload,
            "request_id": _response_token(feed.text),
        },
    )
    history = client.get("/history")

    assert "&lt;script&gt;alert(&#39;hello&#39;)&lt;/script&gt;" in history.text
    assert payload not in history.text


# --- Non-AI boundary ---------------------------------------------------------


def test_saving_a_story_response_does_not_call_an_ai_provider() -> None:
    """The response path has no provider dependency at all (SPEC-044 §6.1)."""
    client, app = _client()
    story = make_story()
    _save_story(app, story)

    class ExplodingProvider:
        def __getattr__(self, name: str) -> Any:
            raise AssertionError(f"AI provider unexpectedly used: {name}")

    app.state.authoring_ai_provider = ExplodingProvider()

    feed = client.get("/pulse")
    saved = client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={
            "response_text": "A quiet observation.",
            "request_id": _response_token(feed.text),
        },
    )

    assert saved.status_code == 200


# --- Submission progress and duplicate prevention ----------------------------


def test_story_response_form_announces_progress_and_blocks_duplicate_requests() -> None:
    """Submitting a story response disables the button, swaps to an in-progress
    label, and exposes a polite status region without fabricated percentages."""
    client, app = _client()
    story = make_story()
    _save_story(app, story)

    feed = client.get("/pulse")

    assert feed.status_code == 200
    form_match = re.search(
        rf'<form[^>]*action="/pulse/stories/{re.escape(str(story.story_id))}/responses"[^>]*>(.*?)</form>',
        feed.text,
        re.DOTALL,
    )
    assert form_match is not None
    form_tag = form_match.group(0).split(">", 1)[0]
    form_body = form_match.group(1)

    assert 'hx-disabled-elt="find button"' in form_tag
    assert 'hx-sync="this:drop"' in form_tag
    assert "authoring-generate__idle" in form_body
    assert "Save response" in form_body
    assert "authoring-generate__progress" in form_body
    assert "Saving response…" in form_body

    indicator = re.search(
        r'<span[^>]*class="[^"]*htmx-indicator[^"]*loading-indicator[^"]*"[^>]*>'
        r"(.*?)</span>",
        form_body,
        re.DOTALL,
    )
    assert indicator is not None
    assert 'role="status"' in indicator.group(0)
    assert 'aria-live="polite"' in indicator.group(0)
    assert "%" not in indicator.group(1)


def test_failed_story_response_returns_submit_button_in_idle_enabled_state() -> None:
    """When saving a story response fails validation, the re-rendered form
    leaves the submit button enabled and out of the in-progress state."""
    client, app = _client()
    story = make_story()
    _save_story(app, story)

    feed = client.get("/pulse")
    failed = client.post(
        f"/pulse/stories/{story.story_id}/responses",
        data={
            "response_text": "   ",
            "request_id": _response_token(feed.text),
        },
        follow_redirects=False,
    )

    assert failed.status_code == 400
    assert "htmx-request" not in failed.text
    submit_button = re.search(
        r'<button[^>]*type="submit"[^>]*>.*?</button>',
        failed.text,
        re.DOTALL,
    )
    assert submit_button is not None
    button_open = submit_button.group(0).split(">", 1)[0]
    assert "disabled" not in button_open
    assert "Save response" in submit_button.group(0)
