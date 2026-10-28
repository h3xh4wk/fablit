"""Google Cloud Datastore news repository adapter (SPEC-041 §6.3).

Curated stories live in their own kind and namespace, separate from learner
practice history and published practices. The adapter keeps the small queried
properties indexed and stores the free-text story fields unindexed, so a long
summary can never fail a write on Datastore's 1500-byte indexed-string limit.

Storage failures are translated into
:class:`~fablit.application.persistence.PersistenceError`, so a story that
could not be written is never reported as published and an unreadable feed is
never presented as an empty one.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fablit.application.news import NewsCategory, NewsRepository, NewsStory
from fablit.application.news_images import (
    story_image_from_mapping,
    story_image_to_mapping,
)
from fablit.application.persistence import PersistenceError

from .datastore_entities import embedded_entity

logger = logging.getLogger(__name__)

#: Datastore kind holding curated news stories, in its own namespace so the
#: feed stays separate from authoring candidates, publications, and history.
NEWS_STORY_KIND = "NewsStory"
DEFAULT_NEWS_NAMESPACE = "news"

#: Story text that is only read back with the entity, never queried.
_UNINDEXED_FIELDS = (
    "headline",
    "summary",
    "educational_relevance",
    "reflection_prompt",
    "image",
)


def serialize_news_story(story: NewsStory) -> dict[str, Any]:
    """Convert a validated story into Datastore-storable properties."""
    return {
        "story_id": str(story.story_id),
        "headline": story.headline,
        "canonical_url": story.canonical_url,
        "source_name": story.source_name,
        "summary": story.summary,
        "categories": [category.value for category in story.categories],
        "educational_relevance": story.educational_relevance,
        "retrieved_at": story.retrieved_at,
        "curated_at": story.curated_at,
        "published_at": story.published_at,
        "reflection_prompt": story.reflection_prompt,
        "provider": story.provider,
        "model": story.model,
        "validation_status": story.validation_status,
        "image": (
            story_image_to_mapping(story.image) if story.image is not None else None
        ),
    }


def deserialize_news_story(entity: Mapping[str, Any]) -> NewsStory:
    """Reconstruct a validated story from a Datastore entity."""
    raw_categories = entity.get("categories") or ()
    categories = tuple(NewsCategory(str(value)) for value in raw_categories)
    published_raw = entity.get("published_at")
    return NewsStory(
        story_id=UUID(str(entity["story_id"])),
        headline=str(entity["headline"]),
        canonical_url=str(entity["canonical_url"]),
        source_name=str(entity["source_name"]),
        summary=str(entity["summary"]),
        categories=categories,
        educational_relevance=str(entity["educational_relevance"]),
        retrieved_at=_as_datetime(entity["retrieved_at"]),
        curated_at=_as_datetime(entity["curated_at"]),
        published_at=(
            _as_datetime(published_raw) if published_raw is not None else None
        ),
        reflection_prompt=(
            str(entity["reflection_prompt"])
            if entity.get("reflection_prompt") is not None
            else None
        ),
        provider=str(entity.get("provider", "")),
        model=str(entity.get("model", "")),
        validation_status=str(entity.get("validation_status", "published")),
        image=story_image_from_mapping(entity.get("image")),
    )


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    if not isinstance(value, datetime):
        raise ValueError(f"expected a datetime, got {value!r}")
    return value.astimezone(UTC)


class DatastoreNewsRepository(NewsRepository):
    """News repository backed by Google Cloud Datastore (SPEC-041 §6.3)."""

    def __init__(
        self,
        client: Any,
        *,
        namespace: str = DEFAULT_NEWS_NAMESPACE,
    ) -> None:
        self._client = client
        self._namespace = namespace

    def save(self, story: NewsStory) -> NewsStory:
        try:
            key = self._client.key(
                NEWS_STORY_KIND,
                str(story.story_id),
                namespace=self._namespace,
            )
            properties = serialize_news_story(story)
            image = properties.pop("image", None)
            entity = self._client.entity(key, exclude_from_indexes=_UNINDEXED_FIELDS)
            entity.update(properties)
            if image is not None:
                # An exclusion on a bare dict does not propagate into it, so
                # the image provenance is stored as a non-indexed embedded
                # entity (googleapis/google-cloud-python#5111).
                entity["image"] = embedded_entity(self._client, image)
            self._client.put(entity)
            return story
        except Exception as exc:
            logger.exception(
                "Failed to persist news story",
                extra={"story_id": str(story.story_id)},
            )
            raise PersistenceError(
                f"Failed to persist news story {story.story_id}: {exc}"
            ) from exc

    def get(self, story_id: UUID) -> NewsStory | None:
        if not isinstance(story_id, UUID):
            return None
        try:
            key = self._client.key(
                NEWS_STORY_KIND,
                str(story_id),
                namespace=self._namespace,
            )
            entity = self._client.get(key)
            if entity is None:
                return None
            return deserialize_news_story(entity)
        except Exception as exc:
            logger.exception(
                "Failed to retrieve news story",
                extra={"story_id": str(story_id)},
            )
            raise PersistenceError(
                f"Failed to retrieve news story {story_id}: {exc}"
            ) from exc

    def find_by_url(self, canonical_url: str) -> NewsStory | None:
        try:
            for story in self.list_stories():
                if story.canonical_url == canonical_url:
                    return story
            return None
        except PersistenceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive translation
            logger.exception("Failed to find news story by URL")
            raise PersistenceError(f"Failed to find news story by URL: {exc}") from exc

    def list_stories(self) -> tuple[NewsStory, ...]:
        try:
            query = self._client.query(kind=NEWS_STORY_KIND, namespace=self._namespace)
            entities = list(query.fetch())
            stories = [deserialize_news_story(entity) for entity in entities]
        except Exception as exc:
            logger.exception("Failed to query news stories")
            raise PersistenceError(f"Failed to query news stories: {exc}") from exc
        return tuple(
            sorted(
                stories,
                key=lambda story: (story.display_at, str(story.story_id)),
                reverse=True,
            )
        )
