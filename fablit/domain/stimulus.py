"""Stimulus domain models (SPEC-015).

SPEC-015 establishes that the visual stimulus is part of the learner's
activity instance, not merely an attachment to an activity. This module
introduces the two domain concepts required to reason about that:

- ``ActivityStimulusContext``: the contextual requirements an Assessment
  Activity defines so an appropriate visual stimulus can be identified
  (learning focus, stimulus context, retrieval query; SPEC-015 §6).
- ``StimulusInstance``: a resolved visual stimulus that was actually shown
  to a learner as part of an activity instance, together with the
  provider and attribution metadata needed to identify it later
  (SPEC-015 §15–17).

Both models are intentionally independent of HTTP, FastAPI, any specific
image provider, browser rendering, and external network calls (SPEC-015
§39): they carry only identity references and plain metadata values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .types import InvalidStimulusContextError, InvalidStimulusError


@dataclass(frozen=True)
class ActivityStimulusContext:
    """The contextual visual stimulus requirements defined by an activity (SPEC-015 §6).

    An activity may define enough contextual information to identify an
    appropriate visual stimulus: the skill is already represented by the
    activity's ``skill_ids``, while the learning focus, the stimulus context,
    and the retrieval query are captured here. Retrieval is deliberately
    derived from this context so the system produces relevant variation
    rather than unrestricted randomness (§11–12).

    Attributes:
        learning_focus: The specific aspect of the skill being practised
            (for example ``Composition``).
        stimulus_context: A description of the kind of visual material the
            activity needs (for example ``Fashion editorial photography``).
        retrieval_query: The query used to retrieve candidates from an
            approved external source (for example ``fashion editorial
            composition``).

    Raises:
        InvalidStimulusContextError: When a required field is missing,
            empty, or whitespace-only.
    """

    learning_focus: str
    stimulus_context: str
    retrieval_query: str

    def __post_init__(self) -> None:
        for label, value in (
            ("learning focus", self.learning_focus),
            ("stimulus context", self.stimulus_context),
            ("retrieval query", self.retrieval_query),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidStimulusContextError(
                    "an activity stimulus context must define a meaningful "
                    f"{label} (got {value!r})"
                )


@dataclass(frozen=True)
class StimulusInstance:
    """A resolved visual stimulus shown to a learner (SPEC-015 §15–16).

    A Stimulus Instance is the specific stimulus selected for a learner's
    activity instance. It is represented separately from the reusable
    activity definition so one activity can use different stimuli over time
    without losing the identity of the specific stimulus shown to a learner
    (§15). It retains enough information to determine what the learner saw:
    the provider, the provider asset identifier where available, the direct
    image URL, the source page URL, creator/author, license, attribution,
    and the retrieval timestamp (§16).

    The direct image URL answers ``What was displayed?`` while the source
    page URL answers ``Where did it come from?``; both are preserved because
    they serve different purposes (§17).

    Attributes:
        activity_id: The stable identity of the Assessment Activity whose
            instance this stimulus is part of (SPEC-005; reference by
            identity only).
        provider: The approved source that supplied the stimulus.
        image_url: The direct image URL that was displayed to the learner.
        source_url: The source page URL identifying where the image came
            from.
        retrieved_at: The timezone-aware time the stimulus was resolved.
        id: The stable, unique domain identity. Generated when omitted.
        asset_id: The provider asset identifier, where available.
        creator: The creator/author information, where available.
        license: The license information, where available.
        attribution: The attribution information, where available.
        alt_text: Meaningful alternative text for the image, where
            appropriate (SPEC-015 §26).

    Raises:
        InvalidStimulusError: When required domain information is missing or
            invalid (missing/invalid identity or activity reference, blank
            provider, image URL, or source URL, a missing/naive retrieval
            timestamp, or an empty/whitespace-only optional metadata value).
    """

    activity_id: UUID
    provider: str
    image_url: str
    source_url: str
    retrieved_at: datetime
    id: UUID = field(default_factory=uuid4)
    asset_id: str | None = None
    creator: str | None = None
    license: str | None = None
    attribution: str | None = None
    alt_text: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidStimulusError(
                f"stimulus instance must have a valid identity (got {self.id!r})"
            )
        if not isinstance(self.activity_id, UUID):
            raise InvalidStimulusError(
                "stimulus instance must reference a valid activity identity"
                f" (got {self.activity_id!r})"
            )
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise InvalidStimulusError(
                f"stimulus instance must record a provider (got {self.provider!r})"
            )
        if not isinstance(self.image_url, str) or not self.image_url.strip():
            raise InvalidStimulusError(
                "stimulus instance must preserve a direct image url"
                f" (got {self.image_url!r})"
            )
        if not isinstance(self.source_url, str) or not self.source_url.strip():
            raise InvalidStimulusError(
                "stimulus instance must preserve a source page url"
                f" (got {self.source_url!r})"
            )
        if not isinstance(self.retrieved_at, datetime):
            raise InvalidStimulusError(
                "stimulus instance must record when it was retrieved"
            )
        if self.retrieved_at.tzinfo is None:
            raise InvalidStimulusError(
                "stimulus retrieval timestamp must be timezone-aware"
            )
        for label, value in (
            ("asset", self.asset_id),
            ("creator", self.creator),
            ("license", self.license),
            ("attribution", self.attribution),
            ("alternative text", self.alt_text),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise InvalidStimulusError(
                    "stimulus "
                    f"{label} information must be a non-blank string when present"
                    f" (got {value!r})"
                )
