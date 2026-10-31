"""Web tests for SPEC-044 learner-requested private practice.

Covers the short request composer, the validated brief shown before practice
begins, private persistence and retrieval, learner isolation, retry
idempotency, and honest failure handling.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application import (
    FORBIDDEN_FEEDBACK_TERMS,
    ChallengePreference,
    FakeLearnerPracticeGenerator,
    InMemoryNewsRepository,
    LearnerPracticeGenerationError,
    NewsCategory,
    NewsStory,
    PracticeArea,
)
from fablit.application.persistence import PersistenceError
from fablit.config import load_config
from fablit.platform.datastore_learner_practice_repository import (
    DatastoreGeneratedPracticeRepository,
)
from tests.persistence.test_datastore_authoring_store import FakeDatastoreClient

REQUEST_TEXT = "I want to practise noticing how colour and texture work together."


def _app(**config_overrides: Any) -> FastAPI:
    overrides: dict[str, Any] = {
        "environment": "testing",
        "practice_history_repository": "memory",
        "generated_practice_repository": "memory",
        "story_response_repository": "memory",
    }
    overrides.update(config_overrides)
    return create_app(load_config(overrides=overrides))


def _client(
    *,
    generator: FakeLearnerPracticeGenerator | None = None,
    **config_overrides: Any,
) -> tuple[TestClient, FastAPI]:
    """A client over an app with a deterministic generator injected."""
    app = _app(**config_overrides)
    app.state.learner_practice_generator = generator or FakeLearnerPracticeGenerator()
    return TestClient(app), app


def _token(html: str) -> str:
    match = re.search(r'name="request_token"\s+value="([^"]+)"', html)
    assert match is not None, "request token not found"
    return match.group(1)


def _history_checkbox_is_checked(html: str) -> bool:
    match = re.search(r'<input[^>]*name="include_history"[^>]*>', html)
    assert match is not None, "include_history checkbox not found"
    return "checked" in match.group(0)


def _form(page: str, **overrides: str) -> dict[str, str]:
    data = {
        "request_text": REQUEST_TEXT,
        "practice_area": PracticeArea.VISUAL_ANALYSIS.value,
        "challenge": ChallengePreference.FAMILIAR.value,
        "response_form": "A short written response",
        "examination_context": "",
        "request_token": _token(page),
    }
    if _history_checkbox_is_checked(page):
        data["include_history"] = "1"
    data.update(overrides)
    return data


def _requested_hrefs(html: str) -> list[str]:
    return re.findall(r'href="(/practice/request/[0-9a-f-]{36})"', html)


def make_story(**overrides: Any) -> NewsStory:
    story_id = uuid4()
    values: dict[str, Any] = {
        "story_id": story_id,
        "headline": "Handloom revival connects weavers with new markets",
        "canonical_url": f"https://news.example.com/story/{story_id}",
        "source_name": "The Daily Weave",
        "summary": "A collective is helping weavers reach contemporary buyers.",
        "categories": (NewsCategory.TEXTILES, NewsCategory.INDIAN_CRAFT),
        "educational_relevance": "Notice how local craft meets contemporary design.",
        "retrieved_at": datetime(2026, 10, 30, 9, 0, tzinfo=UTC),
        "curated_at": datetime(2026, 10, 30, 9, 0, tzinfo=UTC),
        "published_at": datetime(2026, 10, 29, 9, 0, tzinfo=UTC),
        "reflection_prompt": "Where do you see a material tradition nearby?",
        "provider": "fake-news-curation",
        "model": "fake-model",
    }
    values.update(overrides)
    return NewsStory(**values)


def _save_story(app: FastAPI, story: NewsStory) -> None:
    repository = app.state.news_repository
    assert isinstance(repository, InMemoryNewsRepository)
    repository.save(story)


def _submit(client: TestClient, page: str, **overrides: str) -> Any:
    return client.post(
        "/practice/request",
        data=_form(page, **overrides),
        follow_redirects=False,
    )


# --- Composer ----------------------------------------------------------------


def test_the_composer_is_reachable_from_the_dashboard() -> None:
    client, _ = _client()

    dashboard = client.get("/")
    page = client.get("/practice/request")

    assert dashboard.status_code == 200
    assert 'href="/practice/request"' in dashboard.text
    assert page.status_code == 200
    assert "Request a practice" in page.text
    assert 'name="request_text"' in page.text
    assert 'name="practice_area"' in page.text
    assert 'name="include_history"' in page.text
    assert "Practices you request will appear here" in page.text


def test_without_a_generator_the_composer_explains_it_is_unavailable() -> None:
    app = _app()
    client = TestClient(app)

    page = client.get("/practice/request")

    assert page.status_code == 200
    assert "temporarily unavailable" in page.text
    assert "disabled" in page.text


def test_the_composer_offers_only_plain_language_choices() -> None:
    client, _ = _client()

    page = client.get("/practice/request")

    assert "Introductory" in page.text
    assert "More challenging" in page.text
    for forbidden in ("score", "grade", "mastery", "streak"):
        assert forbidden not in page.text.lower()


# --- Generation and the brief -----------------------------------------------


def test_requesting_a_practice_shows_the_brief_before_it_begins() -> None:
    client, _ = _client()
    page = client.get("/practice/request")

    submitted = _submit(client, page.text)
    brief = client.get(submitted.headers["location"])

    assert submitted.status_code == 303
    assert submitted.headers["location"].startswith("/practice/request/")
    assert brief.status_code == 200
    assert "A focused practice: visual analysis" in brief.text
    assert REQUEST_TEXT in brief.text
    assert "Begin this practice" in brief.text
    assert "not part" in brief.text
    assert "shared library" in brief.text
    assert (
        f"/activities/{submitted.headers['location'].rsplit('/', 1)[1]}" in brief.text
    )


def test_a_requested_practice_appears_only_in_this_learners_request_list() -> None:
    client, _ = _client()

    page = client.get("/practice/request")
    submitted = _submit(client, page.text)
    refreshed = client.get("/practice/request")
    dashboard = client.get("/")
    modes = client.get("/practice")

    assert submitted.status_code == 303
    assert _requested_hrefs(refreshed.text) == [submitted.headers["location"]]
    assert "A focused practice: visual analysis" in refreshed.text
    assert "A focused practice: visual analysis" not in dashboard.text
    assert "A focused practice: visual analysis" not in modes.text


def test_retrying_the_same_token_makes_one_practice() -> None:
    generator = FakeLearnerPracticeGenerator()
    client, _ = _client(generator=generator)
    page = client.get("/practice/request")
    form = _form(page.text)

    first = client.post("/practice/request", data=form, follow_redirects=False)
    second = client.post("/practice/request", data=form, follow_redirects=False)
    refreshed = client.get("/practice/request")

    assert first.status_code == 303
    assert second.status_code == 303
    assert first.headers["location"] == second.headers["location"]
    assert len(generator.calls) == 1
    assert len(_requested_hrefs(refreshed.text)) == 1


def _complete_first_curated_activity(client: TestClient) -> None:
    """Complete one curated activity so the learner has real practice history."""
    dashboard = client.get("/")
    match = re.search(r'href="/activities/([0-9a-f-]{36})/intention"', dashboard.text)
    assert match is not None, "curated activity link not found"
    activity_id = match.group(1)
    client.get(f"/activities/{activity_id}")
    submitted = client.post(
        f"/activities/{activity_id}/submit",
        data={
            "response": (
                "Private learner response detail that must never be sent to Gemini."
            )
        },
        follow_redirects=True,
    )
    assert submitted.status_code == 200
    reflected = client.post(
        "/reflect",
        data={"content": "Private learner reflection note."},
        follow_redirects=True,
    )
    assert reflected.status_code == 200


def test_history_context_is_unchecked_by_default_and_excluded_when_unchanged() -> None:
    generator = FakeLearnerPracticeGenerator()
    client, _ = _client(generator=generator)
    _complete_first_curated_activity(client)
    page = client.get("/practice/request")

    assert not _history_checkbox_is_checked(page.text)
    assert "titles and areas of up to five" in page.text
    assert "never your" in page.text
    assert "responses, reflections, or uploads" in page.text

    submitted = _submit(client, page.text)

    assert submitted.status_code == 303
    assert generator.calls[-1].request.include_history is False
    assert generator.calls[-1].history.is_empty
    assert generator.calls[-1].as_payload()["history"] == {
        "recent_titles": [],
        "recent_areas": [],
    }


def test_explicitly_opting_in_includes_only_bounded_history_context() -> None:
    generator = FakeLearnerPracticeGenerator()
    client, _ = _client(generator=generator)
    _complete_first_curated_activity(client)
    page = client.get("/practice/request")

    submitted = _submit(client, page.text, include_history="1")

    assert submitted.status_code == 303
    sent = generator.calls[-1]
    payload = sent.as_payload()
    assert sent.request.include_history is True
    assert not sent.history.is_empty
    assert len(payload["history"]["recent_titles"]) == 1
    assert len(payload["history"]["recent_areas"]) == 1
    assert "Private learner response detail" not in str(payload)
    assert "Private learner reflection note" not in str(payload)


def test_history_checkbox_state_is_preserved_when_request_is_refused() -> None:
    client, _ = _client()
    page = client.get("/practice/request")

    refused_default = _submit(client, page.text, request_text="   ")
    refused_opted_in = _submit(
        client, page.text, request_text="   ", include_history="1"
    )

    assert refused_default.status_code == 400
    assert not _history_checkbox_is_checked(refused_default.text)
    assert refused_opted_in.status_code == 400
    assert _history_checkbox_is_checked(refused_opted_in.text)


def test_the_examination_context_is_shown_only_when_the_learner_states_it() -> None:
    client, _ = _client()
    page = client.get("/practice/request")

    submitted = _submit(client, page.text, examination_context="A portfolio review")
    brief = client.get(submitted.headers["location"])

    assert "Context: A portfolio review" in brief.text


def test_a_requested_practice_joins_the_ordinary_practice_journey() -> None:
    client, _ = _client()
    page = client.get("/practice/request")
    submitted = _submit(client, page.text)
    practice_id = submitted.headers["location"].rsplit("/", 1)[1]

    intention = client.get(f"/activities/{practice_id}/intention")
    practice_page = client.get(f"/activities/{practice_id}")
    feedback = client.post(
        f"/activities/{practice_id}/submit",
        data={"response": "The texture of the weave shows the cloth was made by hand."},
        follow_redirects=True,
    )

    assert intention.status_code == 200
    assert "A focused practice: visual analysis" in intention.text
    assert practice_page.status_code == 200
    assert REQUEST_TEXT in practice_page.text
    assert feedback.status_code == 200
    assert "What you noticed" in feedback.text
    assert "A focused practice: visual analysis" in feedback.text


# --- Privacy ----------------------------------------------------------------


def test_two_learners_never_see_each_others_requested_practices() -> None:
    app = _app()
    app.state.learner_practice_generator = FakeLearnerPracticeGenerator()
    learner_a = TestClient(app)
    learner_b = TestClient(app)

    page = learner_a.get("/practice/request")
    submitted = _submit(learner_a, page.text)
    b_page = learner_b.get("/practice/request")
    b_brief = learner_b.get(submitted.headers["location"])

    assert _requested_hrefs(b_page.text) == []
    assert "A focused practice: visual analysis" not in b_page.text
    assert b_brief.status_code == 404
    assert "A focused practice: visual analysis" not in b_brief.text


def test_an_unknown_requested_practice_is_not_found() -> None:
    client, _ = _client()

    missing = client.get(f"/practice/request/{uuid4()}")
    malformed = client.get("/practice/request/not-a-uuid")

    assert missing.status_code == 404
    assert malformed.status_code == 404


# --- Validation and failure --------------------------------------------------


def test_an_empty_request_is_refused_and_the_learners_words_are_kept() -> None:
    generator = FakeLearnerPracticeGenerator()
    client, _ = _client(generator=generator)
    page = client.get("/practice/request")

    refused = _submit(client, page.text, request_text="   ")
    refreshed = client.get("/practice/request")

    assert refused.status_code == 400
    assert "Write what you would like to practise." in refused.text
    assert generator.calls == []
    assert _requested_hrefs(refreshed.text) == []


def test_an_overlong_request_is_refused_with_actionable_copy() -> None:
    client, _ = _client()
    page = client.get("/practice/request")

    refused = _submit(client, page.text, request_text="a" * 601)

    assert refused.status_code == 400
    assert "600 characters or fewer" in refused.text


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("practice_area", "not-an-area", "Choose a supported practice area."),
        ("challenge", "not-a-challenge", "Choose a supported challenge preference."),
        ("response_form", "   ", "Choose the kind of response you want to make."),
    ],
)
def test_unsupported_choices_are_refused_before_generation(
    field: str, value: str, message: str
) -> None:
    generator = FakeLearnerPracticeGenerator()
    client, _ = _client(generator=generator)
    page = client.get("/practice/request")

    refused = _submit(client, page.text, **{field: value})

    assert refused.status_code == 400
    assert message in refused.text
    assert generator.calls == []


def test_invalid_generated_content_is_refused_before_the_learner_sees_it() -> None:
    generator = FakeLearnerPracticeGenerator(
        {
            "title": "A practice from an incomplete candidate",
            "description": "A description.",
            "contract": {
                "purpose": "Practise describing a detail.",
                "task": "   ",
                "expected_thinking": "Move from observation to a claim.",
                "response_contract": "A short written response.",
                "evaluation_intent": "Look for a specific detail.",
                "feedback_intent": "Name one strength and one next move.",
                "reflection_intent": "Notice what you would try differently.",
                "continuation_intent": "Carry the move into another example.",
            },
        }
    )
    client, _ = _client(generator=generator)
    page = client.get("/practice/request")

    refused = _submit(client, page.text)
    refreshed = client.get("/practice/request")

    assert refused.status_code == 422
    assert "make a practice from that request" in refused.text
    assert "A practice from an incomplete candidate" not in refused.text
    assert _requested_hrefs(refreshed.text) == []


def test_generation_failure_is_reported_honestly() -> None:
    generator = FakeLearnerPracticeGenerator(
        error=LearnerPracticeGenerationError("the practice generator is unavailable")
    )
    client, _ = _client(generator=generator)
    page = client.get("/practice/request")

    failed = _submit(client, page.text)
    refreshed = client.get("/practice/request")

    assert failed.status_code == 503
    assert "the practice generator is unavailable" in failed.text
    assert REQUEST_TEXT in failed.text
    assert _requested_hrefs(refreshed.text) == []


def test_a_persistence_failure_is_not_reported_as_generated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, app = _client()
    repository = app.state.generated_practice_repository

    def failing_save(record: Any) -> Any:
        raise PersistenceError("simulated outage")

    monkeypatch.setattr(repository, "save", failing_save)
    page = client.get("/practice/request")

    failed = _submit(client, page.text)
    refreshed = client.get("/practice/request")

    assert failed.status_code == 503
    assert "couldn&#39;t save this practice" in failed.text
    assert REQUEST_TEXT in failed.text
    assert _requested_hrefs(refreshed.text) == []


def test_learner_text_is_escaped_in_the_brief() -> None:
    generator = FakeLearnerPracticeGenerator(
        {
            "title": "A practice: <script>alert('hi')</script>",
            "description": "A description with <b>markup</b>.",
            "contract": {
                "purpose": "Practise describing a detail.",
                "task": "Describe one detail and say what it shows.",
                "expected_thinking": "Move from observation to a claim.",
                "response_contract": "A short written response.",
                "evaluation_intent": "Look for a specific detail.",
                "feedback_intent": "Name one strength and one next move.",
                "reflection_intent": "Notice what you would try differently.",
                "continuation_intent": "Carry the move into another example.",
            },
        }
    )
    client, _ = _client(generator=generator)
    page = client.get("/practice/request")

    submitted = _submit(client, page.text)
    brief = client.get(submitted.headers["location"])

    assert "&lt;script&gt;alert" in brief.text
    assert "<script>alert('hi')</script>" not in brief.text


# --- Requesting practice from a story (SPEC-044 §6.1) ------------------------


def test_a_story_with_a_prompt_offers_a_make_this_a_practice_link() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)

    feed = client.get("/pulse")

    assert feed.status_code == 200
    assert "Make this a practice" in feed.text
    assert f'href="/practice/request?story={story.story_id}"' in feed.text


def test_a_story_without_a_prompt_offers_no_practice_link() -> None:
    client, app = _client()
    story = make_story(reflection_prompt=None)
    _save_story(app, story)

    feed = client.get("/pulse")

    assert feed.status_code == 200
    assert "Make this a practice" not in feed.text
    assert f"/practice/request?story={story.story_id}" not in feed.text


def test_opening_the_request_from_a_story_prefills_the_editable_prompt() -> None:
    client, app = _client()
    story = make_story()
    _save_story(app, story)

    prompt = story.reflection_prompt
    assert prompt is not None

    page = client.get(f"/practice/request?story={story.story_id}")

    assert page.status_code == 200
    assert prompt in page.text
    assert story.headline in page.text
    assert story.source_name in page.text
    assert f'href="/pulse#story-{story.story_id}"' in page.text
    assert 'name="request_text"' in page.text
    assert "required>" in page.text


def test_the_prefilled_text_is_what_the_learner_can_edit_and_submit() -> None:
    generator = FakeLearnerPracticeGenerator()
    client, app = _client(generator=generator)
    story = make_story()
    _save_story(app, story)
    edited = "I want to practise describing how a local weaver works with colour."

    page = client.get(f"/practice/request?story={story.story_id}")
    submitted = _submit(client, page.text, request_text=edited)
    brief = client.get(submitted.headers["location"])

    assert submitted.status_code == 303
    assert generator.calls[-1].request.text == edited
    assert edited in brief.text


def test_an_unknown_story_opens_the_plain_composer() -> None:
    client, _ = _client()

    page = client.get(f"/practice/request?story={uuid4()}")

    assert page.status_code == 200
    assert "is filled in" not in page.text
    assert 'name="request_text"' in page.text


def test_a_story_without_a_prompt_does_not_prefill_the_composer() -> None:
    client, app = _client()
    story = make_story(reflection_prompt=None)
    _save_story(app, story)

    page = client.get(f"/practice/request?story={story.story_id}")

    assert page.status_code == 200
    assert story.headline not in page.text
    assert 'name="request_text"' in page.text


def test_an_unavailable_feed_does_not_block_the_composer() -> None:
    class UnavailableNews(InMemoryNewsRepository):
        def get(self, story_id: Any) -> NewsStory | None:
            raise PersistenceError("simulated news outage")

    client, app = _client()
    app.state.news_repository = UnavailableNews()

    page = client.get(f"/practice/request?story={uuid4()}")

    assert page.status_code == 200
    assert 'name="request_text"' in page.text
    assert "Request a practice" in page.text


def test_a_malformed_story_parameter_is_ignored() -> None:
    client, _ = _client()

    page = client.get("/practice/request?story=not-a-uuid")

    assert page.status_code == 200
    assert 'name="request_text"' in page.text


# --- Per-learner rate limiting (SPEC-044 / Issue #177) -----------------------


def test_reaching_the_rate_limit_returns_429_preserves_inputs_and_skips_provider() -> (
    None
):
    generator = FakeLearnerPracticeGenerator()
    client, _ = _client(
        generator=generator,
        learner_practice_rate_limit=2,
        learner_practice_rate_window_seconds=3600,
    )

    first_page = client.get("/practice/request")
    first = _submit(client, first_page.text)
    second_page = client.get("/practice/request")
    second = _submit(client, second_page.text)

    third_page = client.get("/practice/request")
    custom_text = "I want to practise comparing two garment silhouettes."
    limited = _submit(
        client,
        third_page.text,
        request_text=custom_text,
        examination_context="Design studio review",
    )

    assert first.status_code == 303
    assert second.status_code == 303
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0
    assert "reached the limit of 2 practice requests per hour" in limited.text
    assert custom_text in limited.text
    assert "Design studio review" in limited.text
    assert len(generator.calls) == 2
    alert_match = re.search(
        r'role="alert">\s*<p>(.*?)</p>',
        limited.text,
        re.DOTALL,
    )
    assert alert_match is not None
    alert_text = alert_match.group(1).lower()
    for term in FORBIDDEN_FEEDBACK_TERMS:
        assert term not in alert_text
    for term in ("score", "grade", "mastery", "streak", "urgent", "hurry"):
        assert term not in limited.text.lower()


def test_idempotent_resubmission_still_redirects_when_learner_is_at_rate_limit() -> (
    None
):
    generator = FakeLearnerPracticeGenerator()
    client, _ = _client(
        generator=generator,
        learner_practice_rate_limit=1,
        learner_practice_rate_window_seconds=3600,
    )

    page = client.get("/practice/request")
    first = _submit(client, page.text)
    repeated = _submit(client, page.text)

    assert first.status_code == 303
    assert repeated.status_code == 303
    assert repeated.headers["location"] == first.headers["location"]
    assert len(generator.calls) == 1


def test_rate_limit_is_enforced_across_app_instances_sharing_datastore() -> None:
    datastore_client = FakeDatastoreClient()
    generator_a = FakeLearnerPracticeGenerator()
    generator_b = FakeLearnerPracticeGenerator()
    client_a, app_a = _client(
        generator=generator_a,
        learner_practice_rate_limit=2,
        learner_practice_rate_window_seconds=3600,
    )
    client_b, app_b = _client(
        generator=generator_b,
        learner_practice_rate_limit=2,
        learner_practice_rate_window_seconds=3600,
    )
    app_a.state.generated_practice_repository = DatastoreGeneratedPracticeRepository(
        datastore_client
    )
    app_b.state.generated_practice_repository = DatastoreGeneratedPracticeRepository(
        datastore_client
    )

    page_a = client_a.get("/practice/request")
    for name, value in client_a.cookies.items():
        client_b.cookies.set(name, value)
    first = _submit(client_a, page_a.text)

    page_b = client_b.get("/practice/request")
    second = _submit(client_b, page_b.text)

    page_a_again = client_a.get("/practice/request")
    third = _submit(client_a, page_a_again.text)

    assert first.status_code == 303
    assert second.status_code == 303
    assert third.status_code == 429
    assert len(generator_a.calls) == 1
    assert len(generator_b.calls) == 1
