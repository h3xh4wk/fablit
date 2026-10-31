"""Unit tests for the StoryResponse domain model (SPEC-044 §6.1)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import fablit.domain.story_response
from fablit.domain import InvalidStoryResponseError, StoryResponse
from fablit.domain.story_response import (
    MAX_STORY_HEADLINE_CHARS,
    MAX_STORY_PROMPT_CHARS,
    MAX_STORY_RESPONSE_CHARS,
    MAX_STORY_SOURCE_CHARS,
    MAX_STORY_URL_CHARS,
)

from .helpers import make_story_response

STORY_RESPONSE_SOURCE = Path(fablit.domain.story_response.__file__).read_text(
    encoding="utf-8"
)


# --- Creation and identity ---------------------------------------------------


def test_create_story_response_with_valid_data() -> None:
    learner_id = uuid4()
    story_id = uuid4()

    response = make_story_response(learner_id=learner_id, story_id=story_id)

    assert response.learner_id == learner_id
    assert response.story_id == story_id
    assert response.story_headline
    assert response.story_source_name
    assert response.canonical_url.startswith("https://")
    assert response.prompt
    assert response.response_text
    assert isinstance(response.id, UUID)
    assert isinstance(response.request_id, UUID)
    assert response.created_at.tzinfo is not None


def test_identity_and_request_token_are_generated_uniquely() -> None:
    first = make_story_response()
    second = make_story_response()

    assert first.id != second.id
    assert first.request_id != second.request_id


@pytest.mark.parametrize("field", ["id", "learner_id", "story_id", "request_id"])
def test_reject_invalid_identity_fields(field: str) -> None:
    with pytest.raises(InvalidStoryResponseError, match=field):
        make_story_response(**{field: "not-a-uuid"})

    with pytest.raises(InvalidStoryResponseError, match=field):
        make_story_response(**{field: None})


# --- Provenance --------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    ["story_headline", "story_source_name", "prompt", "response_text"],
)
def test_reject_missing_or_blank_provenance_text(field: str) -> None:
    for value in (None, "", "   \n\t "):
        with pytest.raises(InvalidStoryResponseError, match=field):
            make_story_response(**{field: value})


@pytest.mark.parametrize(
    ("field", "limit"),
    [
        ("story_headline", MAX_STORY_HEADLINE_CHARS),
        ("story_source_name", MAX_STORY_SOURCE_CHARS),
        ("prompt", MAX_STORY_PROMPT_CHARS),
        ("response_text", MAX_STORY_RESPONSE_CHARS),
    ],
)
def test_reject_overlong_provenance_text(field: str, limit: int) -> None:
    make_story_response(**{field: "a" * limit})

    with pytest.raises(InvalidStoryResponseError, match=f"at most {limit}"):
        make_story_response(**{field: "a" * (limit + 1)})


def test_response_text_must_be_text() -> None:
    with pytest.raises(InvalidStoryResponseError, match="response_text"):
        make_story_response(response_text=42)


# --- Canonical URL -----------------------------------------------------------


def test_canonical_url_accepts_http_and_https() -> None:
    assert make_story_response(canonical_url="http://example.com/a").canonical_url
    assert make_story_response(canonical_url="https://example.com/a").canonical_url


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "   ",
        42,
        "javascript:alert(1)",
        "ftp://example.com/story",
        "https://",
        "not a url",
    ],
)
def test_reject_unsafe_or_missing_canonical_url(url: object) -> None:
    with pytest.raises(InvalidStoryResponseError, match="canonical_url"):
        make_story_response(canonical_url=url)


def test_reject_overlong_canonical_url() -> None:
    url = "https://example.com/" + "a" * MAX_STORY_URL_CHARS

    with pytest.raises(InvalidStoryResponseError, match="canonical_url"):
        make_story_response(canonical_url=url)


# --- Timestamp ---------------------------------------------------------------


def test_response_records_when_it_was_saved() -> None:
    created_at = datetime.now(UTC) - timedelta(minutes=5)

    response = make_story_response(created_at=created_at)

    assert response.created_at == created_at


def test_reject_missing_timestamp() -> None:
    with pytest.raises(InvalidStoryResponseError, match="when it was saved"):
        make_story_response(created_at=None)


def test_reject_naive_timestamp() -> None:
    with pytest.raises(InvalidStoryResponseError, match="timezone-aware"):
        make_story_response(created_at=datetime(2026, 10, 30, 12, 0, 0))


# --- Immutability ------------------------------------------------------------


def test_story_response_cannot_be_silently_modified() -> None:
    response = make_story_response()

    with pytest.raises(FrozenInstanceError):
        response.response_text = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        response.story_id = uuid4()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        response.created_at = datetime.now(UTC)  # type: ignore[misc]


def test_replace_cannot_create_invalid_response() -> None:
    response = make_story_response()

    with pytest.raises(InvalidStoryResponseError, match="response_text"):
        replace(response, response_text="")


# --- Domain boundaries -------------------------------------------------------


def test_response_has_no_assessment_or_generation_concerns() -> None:
    response = make_story_response()

    for forbidden in (
        "score",
        "grade",
        "mastery",
        "rank",
        "provider",
        "model",
        "completion_id",
        "feedback_id",
    ):
        assert not hasattr(response, forbidden)


def test_story_response_source_has_no_infrastructure_dependencies() -> None:
    for module in (
        "sqlalchemy",
        "psycopg",
        "redis",
        "sqlite3",
        "motor",
        "fastapi",
        "pydantic",
        "uvicorn",
    ):
        assert f"import {module}" not in STORY_RESPONSE_SOURCE
        assert f"from {module}" not in STORY_RESPONSE_SOURCE


@pytest.mark.parametrize("forbidden", ["NIFT", "NID", "CEED"])
def test_story_response_source_has_no_examination_terminology(
    forbidden: str,
) -> None:
    assert forbidden.lower() not in STORY_RESPONSE_SOURCE.lower()


def test_story_response_is_usable_in_memory_without_infrastructure() -> None:
    response = make_story_response()

    assert isinstance(response, StoryResponse)
