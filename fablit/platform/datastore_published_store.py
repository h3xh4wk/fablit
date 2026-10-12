"""Google Cloud Datastore published practice store (SPEC-035).

Persists the explicit publication of approved authoring candidates to the
learner library across Google App Engine instances and restarts, alongside
the existing authoring candidate store. Each record keeps the published
learner-facing activity together with its source provenance (candidate,
approved revision, publication and withdrawal times); internal authoring
provenance never reaches learner-facing routes.

Storage failures are translated into
:class:`~fablit.application.persistence.PersistenceError` so a publication
that could not be written is never reported as a success.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fablit.application.authoring import _CONTRACT_FIELDS
from fablit.application.persistence import PersistenceError
from fablit.application.publishing import (
    PublishedPractice,
    PublishedPracticeStore,
)
from fablit.application.store import Concept, DemoActivity, PracticeContentContract
from fablit.domain import (
    ActivityStatus,
    ActivityStimulusContext,
    ActivityType,
    AssessmentActivity,
)

logger = logging.getLogger(__name__)

#: Datastore kind holding publication records, in its own namespace so the
#: learner-library catalogue stays separate from authoring candidates and
#: learner practice history.
PUBLISHED_PRACTICE_KIND = "PublishedPractice"
DEFAULT_NAMESPACE = "library"


def serialize_published_practice(record: PublishedPractice) -> dict[str, Any]:
    """Convert a publication record into a Datastore entity dictionary."""
    activity = record.activity
    contract = activity.content_contract
    stimulus = activity.activity.stimulus_context
    if stimulus is not None:
        # Publication builds activities without a visual stimulus
        # requirement; failing loudly beats silently dropping one.
        raise PersistenceError(
            "published practice stimulus contexts are not supported by the "
            f"published practice store (activity {activity.activity.id})"
        )
    return {
        "activity": {
            "id": str(activity.activity.id),
            "activity_type": activity.activity.activity_type.value,
            "instructions": activity.activity.instructions,
            "position": activity.activity.position,
            "status": activity.activity.status.value,
            "skill_ids": [str(skill_id) for skill_id in activity.activity.skill_ids],
            "stimulus_context": None,
            "title": activity.title,
            "description": activity.description,
            "strength": activity.strength,
            "improvement": activity.improvement,
            "next_step": activity.next_step,
            "content_contract": (
                {name: getattr(contract, name) for name in _CONTRACT_FIELDS}
                if contract is not None
                else None
            ),
            "primary_capability": activity.primary_capability,
            "secondary_capabilities": list(activity.secondary_capabilities),
            "concepts": [
                {"keyword": concept.keyword, "finding": concept.finding}
                for concept in activity.concepts
            ],
            "fallback_image": activity.fallback_image,
            "fallback_alt": activity.fallback_alt,
        },
        "source_candidate_id": str(record.source_candidate_id),
        "source_revision": record.source_revision,
        "published_at": record.published_at,
        "withdrawn_at": record.withdrawn_at,
    }


def deserialize_published_practice(
    entity: Mapping[str, Any],
) -> PublishedPractice:
    """Reconstruct a publication record from a Datastore entity dictionary."""
    data = dict(entity.get("activity") or {})
    contract_data = data.get("content_contract")
    contract: PracticeContentContract | None = None
    if contract_data is not None:
        values = {
            name: str(contract_data[name]).strip()
            for name in _CONTRACT_FIELDS
            if name in contract_data
            and isinstance(contract_data[name], str)
            and contract_data[name].strip()
        }
        if len(values) == len(_CONTRACT_FIELDS):
            contract = PracticeContentContract(**values)

    stimulus_data = data.get("stimulus_context")
    stimulus_context = (
        ActivityStimulusContext(
            learning_focus=str(stimulus_data["learning_focus"]),
            stimulus_context=str(stimulus_data["stimulus_context"]),
            retrieval_query=str(stimulus_data["retrieval_query"]),
        )
        if isinstance(stimulus_data, Mapping)
        else None
    )

    activity = DemoActivity(
        activity=AssessmentActivity(
            id=UUID(str(data["id"])),
            activity_type=ActivityType(str(data["activity_type"])),
            instructions=str(data["instructions"]),
            position=int(data["position"]),
            status=ActivityStatus(str(data.get("status", ActivityStatus.ACTIVE.value))),
            skill_ids=tuple(UUID(str(item)) for item in data.get("skill_ids", ())),
            stimulus_context=stimulus_context,
        ),
        title=str(data["title"]),
        description=str(data["description"]),
        strength=str(data["strength"]),
        improvement=str(data["improvement"]),
        next_step=str(data["next_step"]),
        content_contract=contract,
        primary_capability=str(data.get("primary_capability", "")),
        concepts=tuple(
            Concept(keyword=str(item["keyword"]), finding=str(item["finding"]))
            for item in data.get("concepts", ())
        ),
        fallback_image=data.get("fallback_image"),
        fallback_alt=data.get("fallback_alt"),
        secondary_capabilities=tuple(
            str(item) for item in data.get("secondary_capabilities", ())
        ),
    )
    return PublishedPractice(
        activity=activity,
        source_candidate_id=UUID(str(entity["source_candidate_id"])),
        source_revision=int(entity["source_revision"]),
        published_at=_as_datetime(entity["published_at"]),
        withdrawn_at=(
            _as_datetime(entity["withdrawn_at"])
            if entity.get("withdrawn_at") is not None
            else None
        ),
    )


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    if not isinstance(value, datetime):
        raise ValueError(f"expected a datetime, got {value!r}")
    return value


class DatastorePublishedPracticeStore(PublishedPracticeStore):
    """Published practice store backed by Google Cloud Datastore (SPEC-035).

    Publication survives instance restarts and is shared between App Engine
    instances, so approved content an author publishes once is durable. The
    entity key is the stable learner-facing activity identity: saving the
    same publication again replaces it in place, which keeps republishing
    idempotent and duplicate-free.
    """

    def __init__(
        self,
        client: Any,
        *,
        namespace: str = DEFAULT_NAMESPACE,
    ) -> None:
        self._client = client
        self._namespace = namespace

    def save(self, record: PublishedPractice) -> PublishedPractice:
        try:
            data = serialize_published_practice(record)
            key = self._client.key(
                PUBLISHED_PRACTICE_KIND,
                str(record.activity_id),
                namespace=self._namespace,
            )
            entity = self._client.entity(key)
            entity.update(data)
            self._client.put(entity)
            return record
        except PersistenceError:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to persist published practice",
                extra={"activity_id": str(record.activity_id)},
            )
            raise PersistenceError(
                f"Failed to persist published practice {record.activity_id}: {exc}"
            ) from exc

    def get(self, activity_id: UUID) -> PublishedPractice | None:
        try:
            key = self._client.key(
                PUBLISHED_PRACTICE_KIND,
                str(activity_id),
                namespace=self._namespace,
            )
            entity = self._client.get(key)
            if entity is None:
                return None
            return deserialize_published_practice(entity)
        except Exception as exc:
            logger.exception(
                "Failed to retrieve published practice",
                extra={"activity_id": str(activity_id)},
            )
            raise PersistenceError(
                f"Failed to retrieve published practice {activity_id}: {exc}"
            ) from exc

    def find_by_candidate(self, candidate_id: UUID) -> PublishedPractice | None:
        matches = [
            record
            for record in self.list_records()
            if record.source_candidate_id == candidate_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda record: record.published_at)

    def list_records(self) -> tuple[PublishedPractice, ...]:
        try:
            query = self._client.query(
                kind=PUBLISHED_PRACTICE_KIND, namespace=self._namespace
            )
            with suppress(AttributeError, TypeError):
                query.order = ["-published_at"]
            entities = list(query.fetch())
            records = [deserialize_published_practice(entity) for entity in entities]
        except Exception as exc:
            logger.exception("Failed to query published practices")
            raise PersistenceError(
                f"Failed to query published practices: {exc}"
            ) from exc
        return tuple(
            sorted(records, key=lambda record: record.activity.activity.position)
        )
