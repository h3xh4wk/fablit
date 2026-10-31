"""Google Cloud Datastore adapter for private story responses (SPEC-044 §9).

Story responses live in their own kind and namespace, separate from curated
news, authoring candidates, published practices, and practice history. The
learner identity is stored as an indexed property so a learner's own responses
can be listed; the response text and story provenance are stored unindexed
because they are only ever read back with the record, never queried.

Storage failures are translated into
:class:`~fablit.application.persistence.PersistenceError`, so a response that
could not be written is never reported as saved.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fablit.application.persistence import PersistenceError
from fablit.application.story_responses import StoryResponseRepository
from fablit.domain import StoryResponse

logger = logging.getLogger(__name__)

#: Datastore kind holding story-linked responses.
STORY_RESPONSE_KIND = "StoryResponse"

#: Responses live in their own namespace so learner-authored text is never
#: mixed with the curated news feed or internal authoring records.
DEFAULT_STORY_RESPONSE_NAMESPACE = "story-responses"

#: Response properties that are only read back with the record.
_UNINDEXED_FIELDS = (
    "request_id",
    "story_id",
    "story_headline",
    "story_source_name",
    "canonical_url",
    "prompt",
    "response_text",
)


def serialize_story_response(response: StoryResponse) -> dict[str, Any]:
    """Convert a validated response into Datastore-storable properties."""
    return {
        "response_id": str(response.id),
        "request_id": str(response.request_id),
        "learner_id": str(response.learner_id),
        "story_id": str(response.story_id),
        "story_headline": response.story_headline,
        "story_source_name": response.story_source_name,
        "canonical_url": response.canonical_url,
        "prompt": response.prompt,
        "response_text": response.response_text,
        "created_at": response.created_at,
    }


def deserialize_story_response(entity: Mapping[str, Any]) -> StoryResponse:
    """Reconstruct a validated response from a Datastore entity."""
    return StoryResponse(
        id=UUID(str(entity["response_id"])),
        learner_id=UUID(str(entity["learner_id"])),
        story_id=UUID(str(entity["story_id"])),
        story_headline=str(entity["story_headline"]),
        story_source_name=str(entity["story_source_name"]),
        canonical_url=str(entity["canonical_url"]),
        prompt=str(entity["prompt"]),
        response_text=str(entity["response_text"]),
        created_at=_as_utc(entity["created_at"]),
        request_id=UUID(str(entity["request_id"])),
    )


def _as_utc(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    if not isinstance(value, datetime):
        raise ValueError(f"expected a datetime, got {value!r}")
    return value.astimezone(UTC)


class DatastoreStoryResponseRepository(StoryResponseRepository):
    """Story response repository backed by Google Cloud Datastore."""

    def __init__(
        self,
        client: Any,
        *,
        namespace: str = DEFAULT_STORY_RESPONSE_NAMESPACE,
    ) -> None:
        self._client = client
        self._namespace = namespace

    def save(self, response: StoryResponse) -> StoryResponse:
        if not isinstance(response, StoryResponse):
            raise ValueError("story response repository only accepts StoryResponse")
        try:
            with self._transaction() as transaction:
                key = self._key(response.id)
                existing = self._read(transaction, key)
                if existing is not None:
                    # Retrying the same composer token is the same save.
                    persisted = deserialize_story_response(existing)
                    if persisted.learner_id != response.learner_id:
                        raise ValueError(
                            f"story response {response.id} belongs to another learner"
                        )
                    return persisted
                entity = self._client.entity(
                    key, exclude_from_indexes=_UNINDEXED_FIELDS
                )
                entity.update(serialize_story_response(response))
                self._write(entity, transaction)
                return response
        except Exception as exc:
            logger.exception(
                "Failed to persist story response",
                extra={"response_id": str(response.id)},
            )
            raise PersistenceError(
                f"Failed to persist story response {response.id}: {exc}"
            ) from exc

    def get(self, learner_id: UUID, response_id: UUID) -> StoryResponse | None:
        if not isinstance(learner_id, UUID) or not isinstance(response_id, UUID):
            return None
        try:
            entity = self._client.get(self._key(response_id))
        except Exception as exc:
            logger.exception(
                "Failed to retrieve story response",
                extra={"response_id": str(response_id)},
            )
            raise PersistenceError(
                f"Failed to retrieve story response {response_id}: {exc}"
            ) from exc
        if entity is None:
            return None
        try:
            response = deserialize_story_response(entity)
        except Exception as exc:
            logger.exception(
                "Failed to reconstruct story response",
                extra={"response_id": str(response_id)},
            )
            raise PersistenceError(
                f"Failed to reconstruct story response {response_id}: {exc}"
            ) from exc
        if response.learner_id != learner_id:
            return None
        return response

    def list_for_learner(self, learner_id: UUID) -> tuple[StoryResponse, ...]:
        if not isinstance(learner_id, UUID):
            return ()
        try:
            query = self._client.query(
                kind=STORY_RESPONSE_KIND,
                namespace=self._namespace,
            )
            query.add_filter("learner_id", "=", str(learner_id))
            entities = list(query.fetch())
            responses = [
                deserialize_story_response(entity)
                for entity in entities
                if str(entity.get("learner_id")) == str(learner_id)
            ]
        except Exception as exc:
            logger.exception(
                "Failed to query story responses",
                extra={"learner_id": str(learner_id)},
            )
            raise PersistenceError(
                f"Failed to query story responses for learner {learner_id}: {exc}"
            ) from exc
        return tuple(
            sorted(
                responses,
                key=lambda response: (response.created_at, str(response.id)),
                reverse=True,
            )
        )

    def _transaction(self) -> Any:
        transaction = getattr(self._client, "transaction", None)
        return transaction() if callable(transaction) else nullcontext(None)

    def _read(self, transaction: Any, key: Any) -> Any:
        getter = getattr(transaction, "get", None)
        if callable(getter):
            return getter(key)
        return self._client.get(key)

    def _write(self, entity: Any, transaction: Any) -> None:
        putter = getattr(transaction, "put", None)
        if callable(putter):
            putter(entity)
            return
        self._client.put(entity)

    def _key(self, response_id: UUID) -> Any:
        return self._client.key(
            STORY_RESPONSE_KIND,
            str(response_id),
            namespace=self._namespace,
        )
