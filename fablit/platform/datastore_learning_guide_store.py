"""Google Cloud Datastore learning guide store (SPEC-045).

Persists authored and published Learning Guides across Google App Engine
instances and restarts, in a namespace of its own so guide content stays
separate from authoring candidates, the learner library, and practice
history.

Guide content is read back by key and never queried on its free-text fields,
so the whole payload is stored unindexed: a long section body must not fail
the write on Datastore's 1500-byte limit for indexed string values. Storage
failures are translated into
:class:`~fablit.application.persistence.PersistenceError` so a guide that
could not be written is never reported as saved.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fablit.application.image_search import (
    ImageCandidate,
    image_candidate_from_mapping,
    image_candidate_to_mapping,
)
from fablit.application.learning_guides import (
    GuideImage,
    GuideSection,
    GuideStage,
    GuideStatus,
    LearningGuide,
    LearningGuideRepository,
    resolve_layout,
)
from fablit.application.persistence import PersistenceError
from fablit.platform.datastore_entities import unindexed_value

logger = logging.getLogger(__name__)

#: Datastore kind holding learning guides, in its own namespace.
LEARNING_GUIDE_KIND = "LearningGuide"
DEFAULT_NAMESPACE = "guides"


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _aware(value: object) -> datetime | None:
    """Read a Datastore datetime as a timezone-aware UTC value."""
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def serialize_learning_guide(guide: LearningGuide, client: Any) -> dict[str, Any]:
    """Convert a guide into a Datastore entity dictionary.

    Only short, queried workflow properties stay indexed; the full content
    payload — sections, imagery, provenance, and authoring search state — is
    embedded unindexed.
    """
    return {
        "status": guide.status.value,
        "updated_at": guide.updated_at,
        "payload": unindexed_value(
            client,
            {
                "id": str(guide.id),
                "title": guide.title,
                "summary": guide.summary,
                "practice_area": guide.practice_area,
                "intended_learner_context": guide.intended_learner_context,
                "status": guide.status.value,
                "version": guide.version,
                "created_at": guide.created_at,
                "updated_at": guide.updated_at,
                "published_at": guide.published_at,
                "associated_practice_ids": [
                    str(practice_id) for practice_id in guide.associated_practice_ids
                ],
                "sections": [_section_payload(section) for section in guide.sections],
            },
        ),
    }


def _section_payload(section: GuideSection) -> dict[str, Any]:
    return {
        "id": str(section.id),
        "stage": section.stage.value,
        "heading": section.heading,
        "body": section.body,
        "questions": list(section.questions),
        "examples": list(section.examples),
        "reflection_prompt": section.reflection_prompt,
        "layout": section.layout,
        "images": [_image_payload(image) for image in section.images],
        "search_query": section.search_query,
        "search_candidates": [
            image_candidate_to_mapping(candidate)
            for candidate in section.search_candidates
        ],
    }


def _image_payload(image: GuideImage) -> dict[str, Any]:
    return {
        "provider": image.provider,
        "asset_id": image.asset_id,
        "image_url": image.image_url,
        "source_url": image.source_url,
        "creator": image.creator,
        "creator_url": image.creator_url,
        "source": image.source,
        "attribution": image.attribution,
        "license_type": image.license_type,
        "thumbnail_url": image.thumbnail_url,
        "alt_text": image.alt_text,
        "caption": image.caption,
        "query": image.query,
    }


def deserialize_learning_guide(entity: Mapping[str, Any]) -> LearningGuide:
    """Rebuild a guide from a Datastore entity, refusing malformed payloads.

    Raises:
        PersistenceError: The stored payload is missing or cannot form a
            valid guide. Corruption is never silently reported as an empty
            guide, because that would look like unpublished content.
    """
    payload = entity.get("payload")
    if not isinstance(payload, Mapping):
        raise PersistenceError("stored learning guide payload is missing or malformed")
    try:
        return _guide_from_payload(payload)
    except PersistenceError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise PersistenceError(
            f"stored learning guide payload is invalid: {exc}"
        ) from exc


def _guide_from_payload(payload: Mapping[str, Any]) -> LearningGuide:
    sections_data = payload.get("sections")
    if not isinstance(sections_data, list | tuple):
        raise ValueError("guide sections must be a sequence")
    created_at = _aware(payload.get("created_at"))
    updated_at = _aware(payload.get("updated_at"))
    if created_at is None or updated_at is None:
        raise ValueError("guide timestamps must be datetimes")
    practice_ids = payload.get("associated_practice_ids") or []
    if not isinstance(practice_ids, list | tuple):
        raise ValueError("associated practice ids must be a sequence")
    return LearningGuide(
        id=UUID(_text(payload.get("id"))),
        title=_text(payload.get("title")),
        summary=_text(payload.get("summary")),
        practice_area=_text(payload.get("practice_area")),
        intended_learner_context=_text(payload.get("intended_learner_context")),
        status=GuideStatus(_text(payload.get("status"))),
        version=int(payload.get("version", 1)),
        created_at=created_at,
        updated_at=updated_at,
        published_at=_aware(payload.get("published_at")),
        associated_practice_ids=tuple(UUID(str(item)) for item in practice_ids),
        sections=tuple(_section_from_payload(item) for item in sections_data),
    )


def _section_from_payload(data: object) -> GuideSection:
    if not isinstance(data, Mapping):
        raise ValueError("guide section payload must be a mapping")
    questions = data.get("questions") or []
    examples = data.get("examples") or []
    images = data.get("images") or []
    candidates = data.get("search_candidates") or []
    if not isinstance(questions, list | tuple):
        raise ValueError("guide section questions must be a sequence")
    if not isinstance(examples, list | tuple):
        raise ValueError("guide section examples must be a sequence")
    if not isinstance(images, list | tuple):
        raise ValueError("guide section images must be a sequence")
    if not isinstance(candidates, list | tuple):
        raise ValueError("guide section search candidates must be a sequence")
    layout = _text(data.get("layout")) or resolve_layout(None).value
    return GuideSection(
        id=UUID(_text(data.get("id"))),
        stage=GuideStage(_text(data.get("stage"))),
        heading=_text(data.get("heading")),
        body=_text(data.get("body")),
        questions=tuple(_text(item) for item in questions),
        examples=tuple(_text(item) for item in examples),
        reflection_prompt=_text(data.get("reflection_prompt")),
        layout=layout,
        images=tuple(_image_from_payload(item) for item in images),
        search_query=_text(data.get("search_query")),
        search_candidates=tuple(_candidate_from_stored(item) for item in candidates),
    )


def _image_from_payload(data: object) -> GuideImage:
    if not isinstance(data, Mapping):
        raise ValueError("guide image payload must be a mapping")
    return GuideImage(
        provider=_text(data.get("provider")),
        asset_id=_text(data.get("asset_id")),
        image_url=_text(data.get("image_url")),
        source_url=_text(data.get("source_url")),
        creator=_text(data.get("creator")),
        creator_url=_text(data.get("creator_url")),
        source=_text(data.get("source")),
        attribution=_text(data.get("attribution")),
        license_type=_text(data.get("license_type")),
        thumbnail_url=_text(data.get("thumbnail_url")),
        alt_text=_text(data.get("alt_text")),
        caption=_text(data.get("caption")),
        query=_text(data.get("query")),
    )


def _candidate_from_stored(data: object) -> ImageCandidate:
    candidate = image_candidate_from_mapping(data)
    if candidate is None:
        raise ValueError("stored image candidate is unusable")
    return candidate


class DatastoreLearningGuideStore(LearningGuideRepository):
    """Learning guide repository backed by Google Cloud Datastore (SPEC-045)."""

    def __init__(self, client: Any, *, namespace: str = DEFAULT_NAMESPACE) -> None:
        self._client = client
        self._namespace = namespace

    def save(self, guide: LearningGuide) -> LearningGuide:
        try:
            key = self._client.key(
                LEARNING_GUIDE_KIND, str(guide.id), namespace=self._namespace
            )
            entity = self._client.entity(key)
            entity.update(serialize_learning_guide(guide, self._client))
            self._client.put(entity)
        except Exception as exc:
            logger.exception(
                "failed to persist learning guide to Datastore",
                extra={"guide_id": str(guide.id)},
            )
            raise PersistenceError(
                f"failed to persist learning guide {guide.id}: {exc}"
            ) from exc
        return guide

    def get(self, guide_id: UUID) -> LearningGuide | None:
        try:
            key = self._client.key(
                LEARNING_GUIDE_KIND, str(guide_id), namespace=self._namespace
            )
            entity = self._client.get(key)
            if entity is None:
                return None
            return deserialize_learning_guide(entity)
        except PersistenceError:
            raise
        except Exception as exc:
            logger.exception(
                "failed to retrieve learning guide from Datastore",
                extra={"guide_id": str(guide_id)},
            )
            raise PersistenceError(
                f"failed to retrieve learning guide {guide_id}: {exc}"
            ) from exc

    def list_guides(self) -> tuple[LearningGuide, ...]:
        try:
            query = self._client.query(
                kind=LEARNING_GUIDE_KIND, namespace=self._namespace
            )
            entities = list(query.fetch())
        except Exception as exc:
            logger.exception("failed to query learning guides from Datastore")
            raise PersistenceError(f"failed to list learning guides: {exc}") from exc

        guides: list[LearningGuide] = []
        for entity in entities:
            with suppress(PersistenceError):
                guides.append(deserialize_learning_guide(entity))
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
