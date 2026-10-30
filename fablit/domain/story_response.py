"""Story-linked learner response domain model (SPEC-044 §6.1).

A Story Response is a lightweight, private learner artifact: the learner's
answer to the "What to try" prompt attached to a Fashion & Design Pulse story.
It is deliberately distinct from a Submission or a completed practice. Saving
one captures the learner's words together with enough story and prompt
provenance to understand the context later; it does not evaluate, grade, or
advance the formal practice journey.

The model references the story by its stable identity and keeps the displayed
headline, source name, canonical URL, and prompt as provenance. It never
duplicates the story's editorial content beyond what is needed to revisit the
response.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from .types import InvalidStoryResponseError

#: The longest learner response the composer accepts. A story prompt invites a
#: short observation or idea, not an essay, so the bound stays deliberately
#: small and is enforced before persistence.
MAX_STORY_RESPONSE_CHARS = 2000

#: Provenance bounds mirror the published story contract (SPEC-041).
MAX_STORY_HEADLINE_CHARS = 200
MAX_STORY_SOURCE_CHARS = 200
MAX_STORY_PROMPT_CHARS = 400
MAX_STORY_URL_CHARS = 2048


@dataclass(frozen=True)
class StoryResponse:
    """A learner's private response to one story's "What to try" prompt.

    The response is immutable. Saving another response to the same story
    creates a separate record, and an identical save retried with the same
    ``request_id`` resolves to the same stable identity.

    Attributes:
        learner_id: The opaque identity of the learner who wrote the response.
        story_id: The stable identity of the originating story.
        story_headline: The headline shown when the response was written.
        story_source_name: The publisher attribution shown with the story.
        canonical_url: The story's canonical URL, for returning later.
        prompt: The "What to try" prompt the learner responded to.
        response_text: The learner's own words.
        created_at: The timezone-aware time the response was saved.
        id: The stable identity of this response.
        request_id: The composer's idempotency token for this save attempt.

    Raises:
        InvalidStoryResponseError: When identity, provenance, response text,
            URL, or timestamp is missing or invalid.
    """

    learner_id: UUID
    story_id: UUID
    story_headline: str
    story_source_name: str
    canonical_url: str
    prompt: str
    response_text: str
    created_at: datetime
    id: UUID = field(default_factory=uuid4)
    request_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        for name in ("id", "learner_id", "story_id", "request_id"):
            value = getattr(self, name)
            if not isinstance(value, UUID):
                raise InvalidStoryResponseError(
                    f"story response {name!r} must be a valid identity (got {value!r})"
                )

        _require_text(
            "story_headline",
            self.story_headline,
            MAX_STORY_HEADLINE_CHARS,
        )
        _require_text(
            "story_source_name",
            self.story_source_name,
            MAX_STORY_SOURCE_CHARS,
        )
        _require_text("prompt", self.prompt, MAX_STORY_PROMPT_CHARS)
        _require_text(
            "response_text",
            self.response_text,
            MAX_STORY_RESPONSE_CHARS,
        )

        if not isinstance(self.canonical_url, str) or not self.canonical_url.strip():
            raise InvalidStoryResponseError(
                "story response 'canonical_url' must be non-blank text "
                f"(got {self.canonical_url!r})"
            )
        if len(self.canonical_url) > MAX_STORY_URL_CHARS:
            raise InvalidStoryResponseError(
                "story response 'canonical_url' must be at most "
                f"{MAX_STORY_URL_CHARS} characters"
            )
        parts = urlsplit(self.canonical_url.strip())
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise InvalidStoryResponseError(
                "story response 'canonical_url' must be an absolute http(s) URL "
                f"(got {self.canonical_url!r})"
            )

        if not isinstance(self.created_at, datetime):
            raise InvalidStoryResponseError(
                "story response must record when it was saved"
            )
        if self.created_at.tzinfo is None:
            raise InvalidStoryResponseError(
                "story response timestamp must be timezone-aware"
            )


def _require_text(name: str, value: object, max_length: int) -> None:
    """Reject missing, non-text, blank, or over-long provenance fields."""
    if not isinstance(value, str) or not value.strip():
        raise InvalidStoryResponseError(
            f"story response {name!r} must be non-blank text (got {value!r})"
        )
    if len(value.strip()) > max_length:
        raise InvalidStoryResponseError(
            f"story response {name!r} must be at most {max_length} characters"
        )
