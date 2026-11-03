"""Learning Guides: curated guided-thinking experiences (SPEC-045).

A Learning Guide is an optional, editorially presented sequence of sections
that helps a learner approach a practice through observation, interpretation,
exploration, and their own creation. Guides are authored and published by
authorised Fablit authors; learners may open one from an associated practice,
and opening or leaving it never touches their practice progress.

This module owns the smallest representation the workflow needs:

- :class:`LearningGuide` — versioned guide content with ordered sections and
  stable associations to existing practices.
- :class:`GuideSection` / :class:`GuideImage` — one editorial section and the
  author-selected, provenance-bearing imagery it may carry.
- :func:`validate_guide` — the publication gate. Drafts may be incomplete;
  only complete, safely attributed content becomes learner-visible.
- :class:`LearningGuideRepository` — the persistence port, with an in-memory
  implementation for local development and tests.
- Publish/archive transitions and section editing helpers.

Guide content is structured data, never template code: presentation is a
controlled layout hint that falls back to a safe default, and learner
rendering uses persisted content only — no image search and no LLM call.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from .errors import (
    InvalidLearningGuideError,
    LearningGuideNotPublishableError,
)
from .image_search import ImageCandidate

logger = logging.getLogger("fablit.application")

#: A section may carry several images where the layout benefits from it, but
#: authoring stays bounded so one section never becomes a gallery dump.
MAX_SECTION_IMAGES = 3

#: Search results retained on a section for preview/selection are bounded.
MAX_SECTION_IMAGE_CANDIDATES = 8

#: A search query is an authoring convenience, not learner content.
MAX_SEARCH_QUERY_LENGTH = 200


class GuideStatus(StrEnum):
    """Authoring/publication state of a learning guide (SPEC-045 §7, §9.3).

    ``DRAFT`` and ``ARCHIVED`` guides are never learner-visible; only
    ``PUBLISHED`` content appears beside its associated practices.
    """

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class GuideStage(StrEnum):
    """The shared guided-thinking structure (SPEC-045 §5.2).

    The stages define a learning sequence, not a rigid visual template.
    """

    OBSERVE = "observe"
    THINK = "think"
    EXPLORE = "explore"
    CREATE = "create"
    REFLECT = "reflect"


#: Learner-facing stage labels. Presentation copy, not a stored value.
STAGE_LABELS: dict[GuideStage, str] = {
    GuideStage.OBSERVE: "Observe",
    GuideStage.THINK: "Think",
    GuideStage.EXPLORE: "Explore",
    GuideStage.CREATE: "Create",
    GuideStage.REFLECT: "Reflect",
}


class GuideLayout(StrEnum):
    """Controlled editorial layout variants (SPEC-045 §6.2).

    A section stores a layout *hint*; unknown hints resolve to
    :attr:`DEFAULT` rather than rendering arbitrary markup.
    """

    DEFAULT = "default"
    HERO = "hero"
    PHOTO = "photo"
    SPLIT = "split"
    COMPARISON = "comparison"
    QUOTE = "quote"


LAYOUT_LABELS: dict[GuideLayout, str] = {
    GuideLayout.DEFAULT: "Text-led",
    GuideLayout.HERO: "Large hero image",
    GuideLayout.PHOTO: "Photography-led",
    GuideLayout.SPLIT: "Image and text side by side",
    GuideLayout.COMPARISON: "Side-by-side comparison",
    GuideLayout.QUOTE: "Highlighted prompt",
}


def resolve_layout(value: str | None) -> GuideLayout:
    """Resolve a stored layout hint, falling back to the safe default."""
    if isinstance(value, str):
        try:
            return GuideLayout(value.strip().lower())
        except ValueError:
            return GuideLayout.DEFAULT
    return GuideLayout.DEFAULT


def is_safe_image_url(value: str) -> bool:
    """Whether a provider-supplied URL is an absolute http(s) reference.

    Provider fields are untrusted: only ordinary web URLs may be persisted or
    rendered, so a value can never select a local file, another scheme, or a
    server-side fetch.
    """
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def split_guide_items(value: str) -> tuple[str, ...]:
    """Parse a multi-line authoring field into non-blank items."""
    return tuple(line.strip() for line in value.splitlines() if line.strip())


@dataclass(frozen=True)
class GuideImage:
    """An author-selected section image and the provenance it carries (§7).

    The record keeps provider identity, display URL, source page, creator,
    attribution, and usage details together, so the learner page renders the
    exact metadata the author approved and the guide version stays
    reproducible after publication. Stock imagery is illustrative: it never
    claims to document a specific person, collection, or event.
    """

    provider: str
    asset_id: str
    image_url: str
    source_url: str
    creator: str = ""
    creator_url: str = ""
    source: str = ""
    attribution: str = ""
    license_type: str = ""
    thumbnail_url: str = ""
    alt_text: str = ""
    caption: str = ""
    query: str = ""

    def __post_init__(self) -> None:
        for name in (
            "provider",
            "asset_id",
            "image_url",
            "source_url",
            "creator",
            "creator_url",
            "source",
            "attribution",
            "license_type",
            "thumbnail_url",
            "alt_text",
            "caption",
            "query",
        ):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise InvalidLearningGuideError(
                    f"guide image {name!r} must be text (got {value!r})"
                )
        for name in ("provider", "asset_id", "image_url", "source_url"):
            if not getattr(self, name).strip():
                raise InvalidLearningGuideError(
                    f"guide image {name!r} must be non-blank text"
                )
        for name in ("image_url", "source_url"):
            value = getattr(self, name)
            if not is_safe_image_url(value):
                raise InvalidLearningGuideError(
                    f"guide image {name!r} must be an absolute http(s) URL "
                    f"(got {value!r})"
                )
        for name in ("thumbnail_url", "creator_url"):
            value = getattr(self, name)
            if value.strip() and not is_safe_image_url(value):
                raise InvalidLearningGuideError(
                    f"guide image {name!r} must be an absolute http(s) URL "
                    f"(got {value!r})"
                )

    @property
    def display_url(self) -> str:
        """The URL the section renders, with a safe thumbnail fallback."""
        return self.thumbnail_url.strip() or self.image_url

    @property
    def has_provenance(self) -> bool:
        """Whether the provider source, creator/credit, and licence are known.

        SPEC-045 §8.3: a candidate whose usage requirements cannot be
        established must not be published.
        """
        return bool(
            self.source.strip()
            and is_safe_image_url(self.source_url)
            and (self.attribution.strip() or self.creator.strip())
        )

    @classmethod
    def from_candidate(
        cls,
        candidate: ImageCandidate,
        *,
        alt_text: str = "",
        caption: str = "",
        provider: str = "pexafy",
        query: str = "",
    ) -> GuideImage:
        """Retain one author-approved search result as section imagery.

        Only the provider-neutral candidate contract is read, so Learning
        Guides reuse the existing image-search boundary rather than a second
        provider integration.
        """
        return cls(
            provider=provider,
            asset_id=candidate.photo_id,
            image_url=candidate.image_url,
            source_url=candidate.source_url,
            creator=candidate.photographer,
            creator_url=candidate.photographer_url,
            source=candidate.source,
            attribution=candidate.attribution,
            license_type=candidate.license_type,
            thumbnail_url=candidate.thumbnail_url,
            alt_text=(alt_text.strip() or candidate.alt_text),
            caption=caption.strip(),
            query=query.strip()[:MAX_SEARCH_QUERY_LENGTH],
        )


@dataclass(frozen=True)
class GuideSection:
    """One ordered guide section: a stage, its content, and optional imagery.

    Text-only sections are first-class: ``images`` may be empty and the
    section still stands on its own (SPEC-045 §8.2, §8.3).
    """

    heading: str
    body: str
    stage: GuideStage = GuideStage.OBSERVE
    id: UUID = field(default_factory=uuid4)
    questions: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    reflection_prompt: str = ""
    layout: str = GuideLayout.DEFAULT.value
    images: tuple[GuideImage, ...] = ()
    #: Authoring-only search state, persisted so preview/selection survives a
    #: page reload. Never rendered as learner content.
    search_query: str = ""
    search_candidates: tuple[ImageCandidate, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidLearningGuideError(
                f"guide section must have a valid identity (got {self.id!r})"
            )
        for name in ("heading", "body", "reflection_prompt", "search_query"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise InvalidLearningGuideError(
                    f"guide section {name!r} must be text (got {value!r})"
                )
        if not self.heading.strip():
            raise InvalidLearningGuideError("guide section heading must be non-blank")
        if not self.body.strip():
            raise InvalidLearningGuideError(
                f"guide section {self.heading!r} body must be non-blank"
            )
        if not isinstance(self.stage, GuideStage):
            raise InvalidLearningGuideError(
                f"guide section must declare a supported stage (got {self.stage!r})"
            )
        if not isinstance(self.layout, str):
            raise InvalidLearningGuideError(
                f"guide section layout must be text (got {self.layout!r})"
            )
        for name in ("questions", "examples"):
            values = getattr(self, name)
            if not isinstance(values, tuple):
                raise InvalidLearningGuideError(
                    f"guide section {name!r} must be a tuple (got {values!r})"
                )
            for item in values:
                if not isinstance(item, str) or not item.strip():
                    raise InvalidLearningGuideError(
                        f"guide section {name!r} entries must be non-blank text "
                        f"(got {values!r})"
                    )
        if not isinstance(self.images, tuple):
            raise InvalidLearningGuideError(
                f"guide section images must be a tuple (got {self.images!r})"
            )
        for image in self.images:
            if not isinstance(image, GuideImage):
                raise InvalidLearningGuideError(
                    "guide section images must be guide images "
                    f"(got {type(image).__name__})"
                )
        if not isinstance(self.search_candidates, tuple):
            raise InvalidLearningGuideError(
                "guide section search candidates must be a tuple "
                f"(got {self.search_candidates!r})"
            )

    @property
    def resolved_layout(self) -> GuideLayout:
        """The layout this section renders, never an unsupported variant."""
        return resolve_layout(self.layout)

    @property
    def stage_label(self) -> str:
        """The learner-facing stage label for this section."""
        return STAGE_LABELS[self.stage]


@dataclass(frozen=True)
class LearningGuide:
    """Versioned, structured guide content (SPEC-045 §7).

    Guides are associated with existing practices by stable identity, so
    creating a guide never requires creating a practice and a later rename
    never breaks the association.
    """

    title: str
    summary: str
    practice_area: str
    sections: tuple[GuideSection, ...] = ()
    associated_practice_ids: tuple[UUID, ...] = ()
    intended_learner_context: str = ""
    id: UUID = field(default_factory=uuid4)
    status: GuideStatus = GuideStatus.DRAFT
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidLearningGuideError(
                f"learning guide must have a valid identity (got {self.id!r})"
            )
        for name in (
            "title",
            "summary",
            "practice_area",
            "intended_learner_context",
        ):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise InvalidLearningGuideError(
                    f"learning guide {name!r} must be text (got {value!r})"
                )
        if not self.title.strip():
            raise InvalidLearningGuideError("learning guide title must be non-blank")
        if not isinstance(self.status, GuideStatus):
            raise InvalidLearningGuideError(
                f"learning guide must declare a valid status (got {self.status!r})"
            )
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version < 1
        ):
            raise InvalidLearningGuideError(
                f"learning guide version must be at least 1 (got {self.version!r})"
            )
        for name in ("created_at", "updated_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise InvalidLearningGuideError(
                    f"learning guide {name} must be a timezone-aware datetime "
                    f"(got {value!r})"
                )
        if self.published_at is not None and (
            not isinstance(self.published_at, datetime)
            or self.published_at.tzinfo is None
        ):
            raise InvalidLearningGuideError(
                "learning guide published_at must be a timezone-aware "
                f"datetime (got {self.published_at!r})"
            )
        if not isinstance(self.sections, tuple):
            raise InvalidLearningGuideError(
                f"learning guide sections must be a tuple (got {self.sections!r})"
            )
        for section in self.sections:
            if not isinstance(section, GuideSection):
                raise InvalidLearningGuideError(
                    "learning guide sections must be guide sections "
                    f"(got {type(section).__name__})"
                )
        if not isinstance(self.associated_practice_ids, tuple):
            raise InvalidLearningGuideError(
                "learning guide associated practice ids must be a tuple "
                f"(got {self.associated_practice_ids!r})"
            )
        for practice_id in self.associated_practice_ids:
            if not isinstance(practice_id, UUID):
                raise InvalidLearningGuideError(
                    "learning guide associated practice ids must be valid "
                    f"identities (got {practice_id!r})"
                )

    @property
    def is_published(self) -> bool:
        """Whether learners may open this guide (SPEC-045 §9.3)."""
        return self.status is GuideStatus.PUBLISHED

    @property
    def is_archived(self) -> bool:
        """Whether this guide has been withdrawn from authoring and learners."""
        return self.status is GuideStatus.ARCHIVED

    def section(self, section_id: UUID) -> GuideSection:
        """Return one section by identity, or raise when it does not exist."""
        for section in self.sections:
            if section.id == section_id:
                return section
        raise InvalidLearningGuideError(
            f"learning guide {self.id} has no section {section_id}"
        )


@dataclass(frozen=True)
class GuideValidation:
    """The result of validating a guide for publication (SPEC-045 §9.3).

    ``errors`` block publication; ``warnings`` inform the author without
    blocking an intentional publication decision.
    """

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_publishable(self) -> bool:
        """Whether this guide may be shown to learners."""
        return not self.errors


def validate_guide(
    guide: LearningGuide,
    *,
    known_practice_ids: Iterable[UUID] | None = None,
) -> GuideValidation:
    """Validate a guide against the publication requirements.

    Args:
        guide: The guide to validate.
        known_practice_ids: The practices that exist right now. When supplied,
            an association with any other identity is a publication error —
            associations use stable practice identities, never titles.

    Returns:
        The blocking errors and non-blocking warnings for this guide.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not guide.summary.strip():
        errors.append("a learner-facing summary is required before publication")
    if not guide.practice_area.strip():
        errors.append("a practice area is required before publication")
    if not guide.sections:
        errors.append("a guide needs at least one section before publication")

    seen_sections: set[UUID] = set()
    for section in guide.sections:
        if section.id in seen_sections:
            errors.append(
                f"section identity {section.id} appears more than once; sections "
                "need stable, distinct identities"
            )
        seen_sections.add(section.id)
        if section.resolved_layout is GuideLayout.DEFAULT and section.layout.strip():
            warnings.append(
                f"section {section.heading!r} uses an unsupported layout "
                f"{section.layout!r}; it will render as the default layout"
            )
        for image in section.images:
            if not image.alt_text.strip():
                errors.append(
                    f"section {section.heading!r} image {image.asset_id!r} needs "
                    "alternative text before publication"
                )
            if not image.has_provenance:
                errors.append(
                    f"section {section.heading!r} image {image.asset_id!r} lacks "
                    "creator, source, or attribution details required for "
                    "publication"
                )

    if not guide.associated_practice_ids:
        warnings.append(
            "no practice is associated yet, so learners cannot reach this guide "
            "from a practice"
        )
    if known_practice_ids is not None:
        known = set(known_practice_ids)
        for practice_id in guide.associated_practice_ids:
            if practice_id not in known:
                errors.append(
                    f"associated practice {practice_id} is not an available "
                    "practice; remove or replace the association"
                )

    return GuideValidation(errors=tuple(errors), warnings=tuple(warnings))


def _revise(
    guide: LearningGuide,
    *,
    now: datetime | None = None,
    **changes: Any,
) -> LearningGuide:
    """Apply an author edit, returning published content to draft first.

    SPEC-045 §9.3: saving an edit to a published guide must never silently
    change what learners see. Any content change makes the guide a draft
    again and requires an explicit republish (which bumps its version).
    """
    updated_at = now or datetime.now(UTC)
    status = guide.status if guide.status is GuideStatus.DRAFT else GuideStatus.DRAFT
    return replace(guide, status=status, updated_at=updated_at, **changes)


def save_guide_details(
    guide: LearningGuide,
    *,
    title: str,
    summary: str,
    practice_area: str,
    intended_learner_context: str = "",
    associated_practice_ids: tuple[UUID, ...] = (),
    now: datetime | None = None,
) -> LearningGuide:
    """Update the guide's own metadata and its practice associations."""
    if not title.strip():
        raise InvalidLearningGuideError("learning guide title must be non-blank")
    deduplicated = tuple(dict.fromkeys(associated_practice_ids))
    return _revise(
        guide,
        now=now,
        title=title.strip(),
        summary=summary.strip(),
        practice_area=practice_area.strip(),
        intended_learner_context=intended_learner_context.strip(),
        associated_practice_ids=deduplicated,
    )


def add_section(
    guide: LearningGuide,
    section: GuideSection,
    *,
    now: datetime | None = None,
) -> LearningGuide:
    """Append an ordered section to the guide."""
    if not isinstance(section, GuideSection):
        raise InvalidLearningGuideError(
            f"only guide sections can be added (got {type(section).__name__})"
        )
    return _revise(guide, now=now, sections=guide.sections + (section,))


def update_section(
    guide: LearningGuide,
    section: GuideSection,
    *,
    now: datetime | None = None,
) -> LearningGuide:
    """Replace one section's authored content, keeping its configured order."""
    if not any(existing.id == section.id for existing in guide.sections):
        raise InvalidLearningGuideError(
            f"learning guide {guide.id} has no section {section.id}"
        )
    sections = tuple(
        section if existing.id == section.id else existing
        for existing in guide.sections
    )
    return _revise(guide, now=now, sections=sections)


def move_section(
    guide: LearningGuide,
    section_id: UUID,
    direction: int,
    *,
    now: datetime | None = None,
) -> LearningGuide:
    """Move a section one place up or down without losing its content."""
    sections = list(guide.sections)
    index = next(
        (position for position, item in enumerate(sections) if item.id == section_id),
        None,
    )
    if index is None:
        raise InvalidLearningGuideError(
            f"learning guide {guide.id} has no section {section_id}"
        )
    target = index + (-1 if direction < 0 else 1)
    if target < 0 or target >= len(sections):
        return guide
    sections[index], sections[target] = sections[target], sections[index]
    return _revise(guide, now=now, sections=tuple(sections))


def remove_section(
    guide: LearningGuide,
    section_id: UUID,
    *,
    now: datetime | None = None,
) -> LearningGuide:
    """Remove a section from the guide; reapplying removal is harmless."""
    if not any(section.id == section_id for section in guide.sections):
        return guide
    return _revise(
        guide,
        now=now,
        sections=tuple(
            section for section in guide.sections if section.id != section_id
        ),
    )


def set_search_candidates(
    guide: LearningGuide,
    section_id: UUID,
    candidates: Iterable[ImageCandidate],
    *,
    query: str = "",
    now: datetime | None = None,
) -> LearningGuide:
    """Record bounded search results for author preview and selection.

    This is authoring state, not learner content, so it never changes the
    guide's publication status. A provider failure is represented by an empty
    candidate list: the section stays usable and can remain text-only.
    """
    section = guide.section(section_id)
    retained = tuple(candidates)[:MAX_SECTION_IMAGE_CANDIDATES]
    updated = replace(
        section,
        search_query=query.strip()[:MAX_SEARCH_QUERY_LENGTH],
        search_candidates=retained,
    )
    sections = tuple(
        updated if item.id == section_id else item for item in guide.sections
    )
    return replace(guide, sections=sections, updated_at=now or datetime.now(UTC))


def select_image(
    guide: LearningGuide,
    section_id: UUID,
    *,
    photo_id: str,
    alt_text: str = "",
    caption: str = "",
    now: datetime | None = None,
) -> LearningGuide:
    """Select one stored candidate as section imagery (SPEC-045 §8.2).

    Selection is only possible among the candidates the authoring UI actually
    displayed, so an author cannot inject an arbitrary image reference.
    """
    section = guide.section(section_id)
    candidate = next(
        (item for item in section.search_candidates if item.photo_id == photo_id),
        None,
    )
    if candidate is None:
        raise InvalidLearningGuideError(
            f"image {photo_id!r} is not one of this section's search results"
        )
    image = GuideImage.from_candidate(
        candidate,
        alt_text=alt_text,
        caption=caption,
        query=section.search_query,
    )
    images = tuple(
        existing
        for existing in section.images
        if existing.asset_id != image.asset_id and existing.image_url != image.image_url
    )
    if len(images) >= MAX_SECTION_IMAGES:
        raise InvalidLearningGuideError(
            f"a guide section can carry at most {MAX_SECTION_IMAGES} images"
        )
    updated = replace(section, images=images + (image,))
    sections = tuple(
        updated if item.id == section_id else item for item in guide.sections
    )
    return _revise(guide, now=now, sections=sections)


def remove_image(
    guide: LearningGuide,
    section_id: UUID,
    *,
    asset_id: str,
    now: datetime | None = None,
) -> LearningGuide:
    """Remove a selected image before publication; unknown images are a no-op."""
    section = guide.section(section_id)
    images = tuple(image for image in section.images if image.asset_id != asset_id)
    if len(images) == len(section.images):
        return guide
    updated = replace(section, images=images)
    sections = tuple(
        updated if item.id == section_id else item for item in guide.sections
    )
    return _revise(guide, now=now, sections=sections)


class LearningGuideRepository(ABC):
    """Persistence port for learning guides (SPEC-045 §7, §10).

    The application layer depends on this port only. Concrete adapters live
    behind it: in-memory for local development and tests, Datastore for the
    deployed App Engine environment. Every operation may raise
    :class:`~fablit.application.persistence.PersistenceError` so a storage
    failure is explicit and never reported as a successful publication.
    """

    @abstractmethod
    def save(self, guide: LearningGuide) -> LearningGuide:
        """Persist a guide under its stable identity, replacing any previous state."""

    @abstractmethod
    def get(self, guide_id: UUID) -> LearningGuide | None:
        """Return one guide by identity, or ``None`` when it does not exist."""

    @abstractmethod
    def list_guides(self) -> tuple[LearningGuide, ...]:
        """Return every guide in deterministic authoring order (newest first)."""

    def published(self) -> tuple[LearningGuide, ...]:
        """Return the guides learners may open (published only)."""
        return tuple(guide for guide in self.list_guides() if guide.is_published)

    def published_for_practice(self, practice_id: UUID) -> tuple[LearningGuide, ...]:
        """Return published guides associated with one existing practice.

        Ordered by publication time then title so the practice's entry point
        is stable across instances. A guide never blocks practice access:
        callers treat "no guide" as the ordinary case.
        """
        guides = [
            guide
            for guide in self.published()
            if practice_id in guide.associated_practice_ids
        ]
        return tuple(
            sorted(
                guides,
                key=lambda guide: (
                    guide.published_at or guide.updated_at,
                    guide.title.lower(),
                ),
            )
        )


class InMemoryLearningGuideRepository(LearningGuideRepository):
    """In-memory guide store for local development and tests.

    Deterministic and side-effect free: guide state lives only in this
    process, so a deployment that needs durable, shared guides uses the
    Datastore adapter instead.
    """

    def __init__(self) -> None:
        self._guides: dict[UUID, LearningGuide] = {}
        self._lock = Lock()

    def save(self, guide: LearningGuide) -> LearningGuide:
        with self._lock:
            self._guides[guide.id] = guide
            return guide

    def get(self, guide_id: UUID) -> LearningGuide | None:
        with self._lock:
            return self._guides.get(guide_id)

    def list_guides(self) -> tuple[LearningGuide, ...]:
        with self._lock:
            guides = tuple(self._guides.values())
        return tuple(
            sorted(
                guides,
                key=lambda guide: (
                    guide.updated_at,
                    guide.title.lower(),
                    str(guide.id),
                ),
                reverse=True,
            )
        )


def publish_guide(
    guide: LearningGuide,
    *,
    repository: LearningGuideRepository,
    known_practice_ids: Iterable[UUID] | None = None,
    now: datetime | None = None,
) -> LearningGuide:
    """Explicitly publish a guide to learners (SPEC-045 §9.3).

    Publication revalidates content: incomplete sections, misattributed
    imagery, and associations to unavailable practices are refused rather
    than silently published. Repeating the request for an already published,
    unchanged guide is idempotent; publishing again after an edit bumps the
    content version so the version used for learners stays identifiable.

    Raises:
        LearningGuideNotPublishableError: The guide fails the publication gate.
    """
    if guide.is_published:
        return guide
    if guide.is_archived:
        raise LearningGuideNotPublishableError(
            f"learning guide {guide.id} is archived and cannot be published; "
            "create a new guide instead"
        )

    validation = validate_guide(guide, known_practice_ids=known_practice_ids)
    if not validation.is_publishable:
        raise LearningGuideNotPublishableError(
            f"learning guide {guide.id} cannot be published: "
            + "; ".join(validation.errors)
        )

    published_at = now or datetime.now(UTC)
    version = 1 if guide.published_at is None else guide.version + 1
    published = replace(
        guide,
        status=GuideStatus.PUBLISHED,
        version=version,
        published_at=published_at,
        updated_at=published_at,
    )
    repository.save(published)
    logger.info(
        "learning guide published",
        extra={"guide_id": str(guide.id), "guide_version": version},
    )
    return published


def archive_guide(
    guide: LearningGuide,
    *,
    repository: LearningGuideRepository,
    now: datetime | None = None,
) -> LearningGuide:
    """Withdraw a guide from learners and authoring; idempotent (SPEC-045 §9.3).

    Archived guides stop appearing beside their practices and are no longer
    learner-reachable. Learner practice progress is untouched: guides never
    own practice state.
    """
    if guide.is_archived:
        return guide
    archived_at = now or datetime.now(UTC)
    archived = replace(
        guide,
        status=GuideStatus.ARCHIVED,
        updated_at=archived_at,
    )
    repository.save(archived)
    logger.info(
        "learning guide archived",
        extra={"guide_id": str(guide.id), "guide_version": guide.version},
    )
    return archived
