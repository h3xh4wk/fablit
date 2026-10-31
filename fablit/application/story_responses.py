"""Private story-linked learner responses (SPEC-044 §6.1, §9).

This module owns the application behaviour for responding to a Pulse story's
"What to try" prompt:

- the learner's text is validated and bounded before it is accepted;
- the story's identity, headline, source, canonical URL, and prompt are kept
  as provenance so the response can be understood when revisited;
- the response is saved under the current opaque learner identity only;
- a retried save with the same composer token resolves to the same record, so
  a double submit or an explicit retry cannot create duplicates.

Saving a response never evaluates it, never creates a practice completion, and
never calls an AI provider. It is private capture, deliberately distinct from
the formal practice journey.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from threading import Lock
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fablit.domain import StoryResponse
from fablit.domain.story_response import MAX_STORY_RESPONSE_CHARS

from .errors import InvalidStoryResponseInputError
from .news import NewsStory

#: Learner-facing explanation when a response is empty or whitespace only.
EMPTY_RESPONSE_MESSAGE = "Write a short response before saving it."

#: Learner-facing explanation when a response exceeds the composer bound.
TOO_LONG_RESPONSE_MESSAGE = (
    f"Keep your response to {MAX_STORY_RESPONSE_CHARS} characters or fewer."
)

#: The message shown when a story does not offer a prompt to respond to.
NO_PROMPT_MESSAGE = "This story does not have a prompt to respond to."


class StoryResponseRepository(ABC):
    """Persistence port for private story-linked learner responses.

    Implementations must scope every read by learner identity. ``save`` is
    idempotent by response identity, so retrying the same composer submission
    returns the already-saved record instead of creating a duplicate.
    """

    @abstractmethod
    def save(self, response: StoryResponse) -> StoryResponse:
        """Persist one response and return the stored record.

        Raises:
            PersistenceError: When the private write cannot be completed. The
                caller must not claim the response was saved.
        """

    @abstractmethod
    def get(self, learner_id: UUID, response_id: UUID) -> StoryResponse | None:
        """Return the learner's own response by identity, or ``None``."""

    @abstractmethod
    def list_for_learner(self, learner_id: UUID) -> tuple[StoryResponse, ...]:
        """Return the learner's responses, newest first."""


class InMemoryStoryResponseRepository(StoryResponseRepository):
    """Deterministic in-memory store for tests and local development."""

    def __init__(self) -> None:
        self._responses: dict[UUID, StoryResponse] = {}
        self._learner_responses: dict[UUID, list[UUID]] = {}
        self._lock = Lock()

    def save(self, response: StoryResponse) -> StoryResponse:
        if not isinstance(response, StoryResponse):
            raise ValueError("story response repository only accepts StoryResponse")
        with self._lock:
            existing = self._responses.get(response.id)
            if existing is not None:
                # A retry of the same composer submission is the same save,
                # even if the browser resent it after a slow response.
                return existing
            self._responses[response.id] = response
            self._learner_responses.setdefault(response.learner_id, []).append(
                response.id
            )
            return response

    def get(self, learner_id: UUID, response_id: UUID) -> StoryResponse | None:
        if not isinstance(learner_id, UUID) or not isinstance(response_id, UUID):
            return None
        with self._lock:
            response = self._responses.get(response_id)
        if response is None or response.learner_id != learner_id:
            return None
        return response

    def list_for_learner(self, learner_id: UUID) -> tuple[StoryResponse, ...]:
        if not isinstance(learner_id, UUID):
            return ()
        with self._lock:
            response_ids = tuple(self._learner_responses.get(learner_id, ()))
            responses = [
                self._responses[response_id]
                for response_id in response_ids
                if response_id in self._responses
            ]
        return tuple(
            sorted(
                responses,
                key=lambda response: (response.created_at, str(response.id)),
                reverse=True,
            )
        )


def new_story_response_request_id() -> UUID:
    """Return a fresh idempotency token for one composer render."""
    return uuid4()


def story_response_id(learner_id: UUID, request_id: UUID) -> UUID:
    """Derive the stable response identity from its learner and save token.

    A retried submission keeps the same token, so it resolves to the same
    identity and the repository returns the existing record rather than
    creating a second one.
    """
    return uuid5(
        NAMESPACE_URL,
        f"fablit:story-response:{learner_id}:{request_id}",
    )


def normalize_story_response_text(text: str) -> str:
    """Validate and normalize learner-authored response text.

    Raises:
        InvalidStoryResponseInputError: With actionable, non-technical copy
            when the response is missing or exceeds the composer bound.
    """
    if not isinstance(text, str) or not text.strip():
        raise InvalidStoryResponseInputError(EMPTY_RESPONSE_MESSAGE)
    normalized = text.strip()
    if len(normalized) > MAX_STORY_RESPONSE_CHARS:
        raise InvalidStoryResponseInputError(TOO_LONG_RESPONSE_MESSAGE)
    return normalized


def save_story_response(
    repository: StoryResponseRepository,
    *,
    learner_id: UUID,
    story: NewsStory,
    response_text: str,
    request_id: UUID,
    saved_at: datetime | None = None,
) -> StoryResponse:
    """Save one private response to the story's "What to try" prompt.

    The story's prompt is required; a story without one never shows the
    composer, and a direct request for it is refused with actionable copy.
    """
    prompt = story.reflection_prompt
    if not isinstance(prompt, str) or not prompt.strip():
        raise InvalidStoryResponseInputError(NO_PROMPT_MESSAGE)

    text = normalize_story_response_text(response_text)
    response = StoryResponse(
        learner_id=learner_id,
        story_id=story.story_id,
        story_headline=story.headline,
        story_source_name=story.source_name,
        canonical_url=story.canonical_url,
        prompt=prompt,
        response_text=text,
        created_at=saved_at if saved_at is not None else datetime.now(UTC),
        id=story_response_id(learner_id, request_id),
        request_id=request_id,
    )
    return repository.save(response)


def get_story_response(
    repository: StoryResponseRepository,
    *,
    learner_id: UUID,
    response_id: UUID,
) -> StoryResponse | None:
    """Return the current learner's response, never another learner's."""
    return repository.get(learner_id, response_id)


def list_story_responses(
    repository: StoryResponseRepository,
    *,
    learner_id: UUID,
) -> tuple[StoryResponse, ...]:
    """Return the current learner's story responses, newest first."""
    return repository.list_for_learner(learner_id)
