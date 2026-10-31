"""Google Cloud Datastore adapter for private learner-requested practices.

Generated practices live in their own kind and namespace, separate from the
shared curated library, authoring candidates, curated news, and practice
history. Each record stores the validated practice exactly as the learner was
offered it — title, description, complete SPEC-029 contract, request
preferences, and safe provider/model provenance. Raw provider payloads and
secrets are never stored.

Storage failures are translated into
:class:`~fablit.application.persistence.PersistenceError`, so a practice that
could not be written is never reported as generated.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fablit.application.authoring import _CONTRACT_FIELDS
from fablit.application.learner_practice import (
    ChallengePreference,
    GeneratedPracticeRecord,
    GeneratedPracticeRepository,
    PracticeArea,
)
from fablit.application.persistence import PersistenceError
from fablit.application.store import PracticeContentContract
from fablit.platform.datastore_entities import unindexed_value

logger = logging.getLogger(__name__)

#: Datastore kind holding learner-requested private practices.
GENERATED_PRACTICE_KIND = "GeneratedPractice"

#: Private requested practices live in their own namespace.
DEFAULT_GENERATED_PRACTICE_NAMESPACE = "learner-practices"

#: Properties only read back with the record, never queried.
_UNINDEXED_FIELDS = (
    "request_token",
    "title",
    "description",
    "contract",
    "area",
    "challenge",
    "response_form",
    "primary_capability",
    "used_history",
    "provider",
    "model",
    "generated_at",
    "examination_context",
)


def serialize_generated_practice(
    record: GeneratedPracticeRecord, client: Any
) -> dict[str, Any]:
    """Convert a validated private practice into Datastore-storable properties.

    The practice payload is only ever read back by key, so the contract fields
    are stored as an embedded entity whose values are not indexed: a long
    generated contract field must not fail the write on Datastore's 1500-byte
    limit for indexed string values.
    """
    contract = record.contract
    return {
        "practice_id": str(record.practice_id),
        "learner_id": str(record.learner_id),
        "request_token": str(record.request_token),
        "title": record.title,
        "description": record.description,
        "contract": unindexed_value(
            client, {name: getattr(contract, name) for name in _CONTRACT_FIELDS}
        ),
        "area": record.area.value,
        "challenge": record.challenge.value,
        "response_form": record.response_form,
        "primary_capability": record.primary_capability,
        "used_history": record.used_history,
        "provider": record.provider,
        "model": record.model,
        "generated_at": record.generated_at,
        "created_at": record.created_at,
        "examination_context": record.examination_context,
    }


def deserialize_generated_practice(
    entity: Mapping[str, Any],
) -> GeneratedPracticeRecord:
    """Reconstruct a private practice from a Datastore entity."""
    contract_data = entity.get("contract")
    if not isinstance(contract_data, Mapping):
        raise ValueError("generated practice contract is missing")
    contract_values: dict[str, str] = {}
    for name in _CONTRACT_FIELDS:
        value = contract_data.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"generated practice contract field {name!r} is invalid")
        contract_values[name] = value
    return GeneratedPracticeRecord(
        practice_id=UUID(str(entity["practice_id"])),
        learner_id=UUID(str(entity["learner_id"])),
        request_token=UUID(str(entity["request_token"])),
        title=str(entity["title"]),
        description=str(entity["description"]),
        contract=PracticeContentContract(**contract_values),
        area=PracticeArea(str(entity["area"])),
        challenge=ChallengePreference(str(entity["challenge"])),
        response_form=str(entity["response_form"]),
        primary_capability=str(entity["primary_capability"]),
        used_history=bool(entity.get("used_history", False)),
        provider=str(entity["provider"]),
        model=str(entity["model"]),
        generated_at=_as_utc(entity["generated_at"]),
        created_at=_as_utc(entity["created_at"]),
        examination_context=(
            str(entity["examination_context"])
            if entity.get("examination_context") is not None
            else None
        ),
    )


def _as_utc(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    if not isinstance(value, datetime):
        raise ValueError(f"expected a datetime, got {value!r}")
    return value.astimezone(UTC)


class DatastoreGeneratedPracticeRepository(GeneratedPracticeRepository):
    """Private generated practice repository backed by Google Cloud Datastore."""

    def __init__(
        self,
        client: Any,
        *,
        namespace: str = DEFAULT_GENERATED_PRACTICE_NAMESPACE,
    ) -> None:
        self._client = client
        self._namespace = namespace

    def save(self, record: GeneratedPracticeRecord) -> GeneratedPracticeRecord:
        try:
            key = self._key(record.practice_id)
            existing = self._client.get(key)
            if existing is not None:
                return deserialize_generated_practice(existing)
            entity = self._client.entity(key, exclude_from_indexes=_UNINDEXED_FIELDS)
            entity.update(serialize_generated_practice(record, self._client))
            self._client.put(entity)
            return record
        except Exception as exc:
            logger.exception(
                "Failed to persist generated practice",
                extra={"practice_id": str(record.practice_id)},
            )
            raise PersistenceError(
                f"Failed to persist generated practice {record.practice_id}: {exc}"
            ) from exc

    def get(
        self, learner_id: UUID, practice_id: UUID
    ) -> GeneratedPracticeRecord | None:
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            return None
        try:
            entity = self._client.get(self._key(practice_id))
        except Exception as exc:
            logger.exception(
                "Failed to retrieve generated practice",
                extra={"practice_id": str(practice_id)},
            )
            raise PersistenceError(
                f"Failed to retrieve generated practice {practice_id}: {exc}"
            ) from exc
        if entity is None:
            return None
        try:
            record = deserialize_generated_practice(entity)
        except Exception as exc:
            logger.exception(
                "Failed to reconstruct generated practice",
                extra={"practice_id": str(practice_id)},
            )
            raise PersistenceError(
                f"Failed to reconstruct generated practice {practice_id}: {exc}"
            ) from exc
        if record.learner_id != learner_id:
            return None
        return record

    def list_for_learner(self, learner_id: UUID) -> tuple[GeneratedPracticeRecord, ...]:
        if not isinstance(learner_id, UUID):
            return ()
        try:
            query = self._client.query(
                kind=GENERATED_PRACTICE_KIND,
                namespace=self._namespace,
            )
            query.add_filter("learner_id", "=", str(learner_id))
            entities = list(query.fetch())
            records = [
                deserialize_generated_practice(entity)
                for entity in entities
                if str(entity.get("learner_id")) == str(learner_id)
            ]
        except Exception as exc:
            logger.exception(
                "Failed to query generated practices",
                extra={"learner_id": str(learner_id)},
            )
            raise PersistenceError(
                f"Failed to query generated practices for learner {learner_id}: {exc}"
            ) from exc
        return tuple(
            sorted(
                records,
                key=lambda record: (record.created_at, str(record.practice_id)),
                reverse=True,
            )
        )

    def _key(self, practice_id: UUID) -> Any:
        return self._client.key(
            GENERATED_PRACTICE_KIND,
            str(practice_id),
            namespace=self._namespace,
        )
