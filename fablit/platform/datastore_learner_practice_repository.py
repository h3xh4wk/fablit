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
import math
import time
from collections.abc import Mapping
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from uuid import UUID, uuid4

from fablit.application.authoring import _CONTRACT_FIELDS
from fablit.application.errors import LearnerPracticeGenerationError
from fablit.application.learner_practice import (
    DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    DEFAULT_GENERATION_WAIT_TIMEOUT_SECONDS,
    DEFAULT_LEARNER_PRACTICE_RATE_LIMIT,
    DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS,
    GENERATION_UNAVAILABLE_MESSAGE,
    ChallengePreference,
    GeneratedPracticeRecord,
    GeneratedPracticeRepository,
    GenerationClaimOutcome,
    PracticeArea,
    _InMemoryGenerationClaim,
    _normalize_rate_limit_params,
)
from fablit.application.persistence import PersistenceError, StaleGenerationClaimError
from fablit.application.store import PracticeContentContract
from fablit.platform.datastore_entities import unindexed_value

logger = logging.getLogger(__name__)

#: Datastore kind holding learner-requested private practices.
GENERATED_PRACTICE_KIND = "GeneratedPractice"

#: Datastore kind holding in-flight generation claims per practice identity.
GENERATED_PRACTICE_CLAIM_KIND = "GeneratedPracticeClaim"

#: Datastore kind holding per-learner generation rate-limit state across instances.
GENERATED_PRACTICE_RATE_LIMIT_KIND = "GeneratedPracticeRateLimit"

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

_CLAIM_UNINDEXED_FIELDS = (
    "practice_id",
    "learner_id",
    "claim_token",
    "claimed_at",
    "expires_at",
)

_RATE_LIMIT_UNINDEXED_FIELDS = (
    "requested_at",
    "updated_at",
)

_POLL_INTERVAL_SECONDS = 0.01


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
        self._lock = Lock()
        self._in_flight: dict[UUID, _InMemoryGenerationClaim] = {}

    def claim_generation(
        self,
        learner_id: UUID,
        practice_id: UUID,
        *,
        now: datetime | None = None,
        ttl_seconds: int = DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    ) -> GenerationClaimOutcome:
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            raise ValueError(
                "claim_generation requires UUID learner_id and practice_id"
            )
        current, _, ttl = _normalize_rate_limit_params(
            now or datetime.now(UTC),
            limit=1,
            window_seconds=ttl_seconds,
        )
        expires_at = current + timedelta(seconds=ttl)
        claim_token = uuid4()
        try:
            with self._transaction() as transaction:
                key = self._key(practice_id)
                existing = self._read(transaction, key)
                if existing is not None:
                    persisted = deserialize_generated_practice(existing)
                    if persisted.learner_id != learner_id:
                        raise ValueError(
                            f"generated practice {practice_id} "
                            "belongs to another learner"
                        )
                    return GenerationClaimOutcome(claimed=False, existing=persisted)

                claim_key = self._claim_key(practice_id)
                claim_entity = self._read(transaction, claim_key)
                if claim_entity is not None:
                    claim_owner = UUID(str(claim_entity["learner_id"]))
                    if claim_owner != learner_id:
                        raise ValueError(
                            f"generated practice claim {practice_id} "
                            "belongs to another learner"
                        )
                    if _as_utc(claim_entity["expires_at"]) > current:
                        return GenerationClaimOutcome(claimed=False, existing=None)

                entity = self._client.entity(
                    claim_key, exclude_from_indexes=_CLAIM_UNINDEXED_FIELDS
                )
                entity.update(
                    {
                        "practice_id": str(practice_id),
                        "learner_id": str(learner_id),
                        "claim_token": str(claim_token),
                        "claimed_at": current,
                        "expires_at": expires_at,
                    }
                )
                self._write(entity, transaction)
        except Exception as exc:
            logger.exception(
                "Failed to claim generated practice key",
                extra={"practice_id": str(practice_id), "learner_id": str(learner_id)},
            )
            raise PersistenceError(
                f"Failed to claim generated practice {practice_id}: {exc}"
            ) from exc

        with self._lock:
            prior = self._in_flight.get(practice_id)
            if prior is not None:
                prior.event.set()
            self._in_flight[practice_id] = _InMemoryGenerationClaim(
                learner_id=learner_id,
                expires_at=expires_at,
                claim_token=claim_token,
            )
        return GenerationClaimOutcome(
            claimed=True,
            existing=None,
            claim_token=claim_token,
        )

    def renew_generation_claim(
        self,
        learner_id: UUID,
        practice_id: UUID,
        claim_token: UUID | None = None,
        *,
        now: datetime | None = None,
        ttl_seconds: int = DEFAULT_GENERATION_CLAIM_TTL_SECONDS,
    ) -> bool:
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            raise ValueError(
                "renew_generation_claim requires UUID learner_id and practice_id"
            )
        current, _, ttl = _normalize_rate_limit_params(
            now or datetime.now(UTC),
            limit=1,
            window_seconds=ttl_seconds,
        )
        if not isinstance(claim_token, UUID):
            return False
        expires_at = current + timedelta(seconds=ttl)
        try:
            with self._transaction() as transaction:
                key = self._key(practice_id)
                existing = self._read(transaction, key)
                if existing is not None:
                    persisted = deserialize_generated_practice(existing)
                    if persisted.learner_id != learner_id:
                        raise ValueError(
                            f"generated practice {practice_id} "
                            "belongs to another learner"
                        )
                    return False

                claim_key = self._claim_key(practice_id)
                claim_entity = self._read(transaction, claim_key)
                if claim_entity is None:
                    return False
                claim_owner = UUID(str(claim_entity["learner_id"]))
                if claim_owner != learner_id:
                    raise ValueError(
                        f"generated practice claim {practice_id} "
                        "belongs to another learner"
                    )
                if (
                    str(claim_entity.get("claim_token")) != str(claim_token)
                    or _as_utc(claim_entity["expires_at"]) <= current
                ):
                    return False

                entity = self._client.entity(
                    claim_key, exclude_from_indexes=_CLAIM_UNINDEXED_FIELDS
                )
                entity.update(
                    {
                        "practice_id": str(practice_id),
                        "learner_id": str(learner_id),
                        "claim_token": str(claim_token),
                        "claimed_at": _as_utc(claim_entity["claimed_at"]),
                        "expires_at": expires_at,
                    }
                )
                self._write(entity, transaction)
        except Exception as exc:
            logger.exception(
                "Failed to renew generated practice claim",
                extra={"practice_id": str(practice_id), "learner_id": str(learner_id)},
            )
            raise PersistenceError(
                f"Failed to renew generated practice claim {practice_id}: {exc}"
            ) from exc

        with self._lock:
            in_flight = self._in_flight.get(practice_id)
            if (
                in_flight is not None
                and in_flight.learner_id == learner_id
                and in_flight.claim_token == claim_token
            ):
                in_flight.expires_at = expires_at
        return True

    def complete_generation_claim(
        self,
        record: GeneratedPracticeRecord,
        claim_token: UUID | None = None,
    ) -> GeneratedPracticeRecord:
        if "save" in self.__dict__:
            return self.save(record)
        return self.save(record, claim_token=claim_token)

    def await_generation(
        self,
        learner_id: UUID,
        practice_id: UUID,
        *,
        timeout_seconds: float = DEFAULT_GENERATION_WAIT_TIMEOUT_SECONDS,
    ) -> GeneratedPracticeRecord:
        if not isinstance(learner_id, UUID) or not isinstance(practice_id, UUID):
            raise ValueError(
                "await_generation requires UUID learner_id and practice_id"
            )
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while True:
            with self._lock:
                in_flight = self._in_flight.get(practice_id)
            if in_flight is not None:
                if in_flight.learner_id != learner_id:
                    raise PersistenceError(
                        f"Generated practice claim {practice_id} "
                        "belongs to another learner"
                    )
                if in_flight.record is not None:
                    return in_flight.record
                if in_flight.error is not None:
                    raise in_flight.error

            persisted = self._get_requiring_owner(learner_id, practice_id)
            if persisted is not None:
                return persisted

            if not self._is_claim_present(learner_id, practice_id):
                with self._lock:
                    settled = self._in_flight.get(practice_id)
                if settled is not None:
                    if settled.record is not None:
                        return settled.record
                    if settled.error is not None:
                        raise settled.error
                persisted = self._get_requiring_owner(learner_id, practice_id)
                if persisted is not None:
                    return persisted
                raise LearnerPracticeGenerationError(GENERATION_UNAVAILABLE_MESSAGE)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            wait_step = min(_POLL_INTERVAL_SECONDS, remaining)
            if in_flight is not None:
                in_flight.event.wait(timeout=wait_step)
                if in_flight.record is not None:
                    return in_flight.record
                if in_flight.error is not None:
                    with self._lock:
                        current = self._in_flight.get(practice_id)
                    if (
                        current is None or current.claim_token == in_flight.claim_token
                    ) and not self._is_claim_present(learner_id, practice_id):
                        raise in_flight.error
            else:
                time.sleep(wait_step)

        persisted = self._get_requiring_owner(learner_id, practice_id)
        if persisted is not None:
            return persisted
        raise LearnerPracticeGenerationError(GENERATION_UNAVAILABLE_MESSAGE)

    def release_generation_claim(
        self,
        learner_id: UUID,
        practice_id: UUID,
        claim_token: UUID | None = None,
        *,
        error: Exception | None = None,
    ) -> bool:
        if (
            not isinstance(learner_id, UUID)
            or not isinstance(practice_id, UUID)
            or not isinstance(claim_token, UUID)
        ):
            return False
        released = False
        release_failed = False
        try:
            with self._transaction() as transaction:
                claim_key = self._claim_key(practice_id)
                claim_entity = self._read(transaction, claim_key)
                if (
                    claim_entity is not None
                    and str(claim_entity.get("learner_id")) == str(learner_id)
                    and str(claim_entity.get("claim_token")) == str(claim_token)
                ):
                    self._delete(claim_key, transaction)
                    released = True
        except Exception:
            release_failed = True
            logger.warning(
                "Failed to release generated practice claim",
                extra={"practice_id": str(practice_id), "learner_id": str(learner_id)},
                exc_info=True,
            )
        finally:
            with self._lock:
                in_flight = self._in_flight.get(practice_id)
                if (
                    in_flight is not None
                    and in_flight.learner_id == learner_id
                    and in_flight.claim_token == claim_token
                ):
                    if released or release_failed:
                        in_flight.error = error
                    in_flight.event.set()
                    self._in_flight.pop(practice_id, None)
        return released

    def save(
        self,
        record: GeneratedPracticeRecord,
        *,
        claim_token: UUID | None = None,
    ) -> GeneratedPracticeRecord:
        if not isinstance(record, GeneratedPracticeRecord):
            raise ValueError(
                "generated practice repository only accepts GeneratedPracticeRecord"
            )
        if claim_token is not None and not isinstance(claim_token, UUID):
            raise ValueError("save claim_token must be a UUID when provided")
        try:
            with self._transaction() as transaction:
                key = self._key(record.practice_id)
                existing = self._read(transaction, key)
                claim_key = self._claim_key(record.practice_id)
                claim_entity = self._read(transaction, claim_key)
                if existing is not None:
                    persisted = deserialize_generated_practice(existing)
                    if persisted.learner_id != record.learner_id:
                        raise ValueError(
                            f"generated practice {record.practice_id} "
                            "belongs to another learner"
                        )
                    if (
                        claim_entity is not None
                        and claim_token is not None
                        and str(claim_entity.get("learner_id"))
                        == str(record.learner_id)
                        and str(claim_entity.get("claim_token")) == str(claim_token)
                    ):
                        self._delete(claim_key, transaction)
                else:
                    if claim_entity is not None:
                        if str(claim_entity.get("learner_id")) != str(
                            record.learner_id
                        ):
                            raise ValueError(
                                f"generated practice claim {record.practice_id} "
                                "belongs to another learner"
                            )
                        if claim_token is None or str(
                            claim_entity.get("claim_token")
                        ) != str(claim_token):
                            raise StaleGenerationClaimError(
                                f"Generated practice claim {record.practice_id} "
                                "is owned by another generation attempt"
                            )
                    elif claim_token is not None:
                        raise StaleGenerationClaimError(
                            f"Generated practice claim {record.practice_id} "
                            "is no longer active"
                        )
                    entity = self._client.entity(
                        key, exclude_from_indexes=_UNINDEXED_FIELDS
                    )
                    entity.update(serialize_generated_practice(record, self._client))
                    self._write(entity, transaction)
                    if claim_entity is not None:
                        self._delete(claim_key, transaction)
                    persisted = record
        except StaleGenerationClaimError:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to persist generated practice",
                extra={"practice_id": str(record.practice_id)},
            )
            raise PersistenceError(
                f"Failed to persist generated practice {record.practice_id}: {exc}"
            ) from exc

        with self._lock:
            in_flight = self._in_flight.get(record.practice_id)
            if in_flight is not None and (
                claim_token is None or in_flight.claim_token == claim_token
            ):
                self._in_flight.pop(record.practice_id, None)
                in_flight.record = persisted
                in_flight.event.set()
        return persisted

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

    def reserve_generation_slot(
        self,
        learner_id: UUID,
        *,
        now: datetime,
        limit: int = DEFAULT_LEARNER_PRACTICE_RATE_LIMIT,
        window_seconds: int = DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS,
    ) -> int | None:
        if not isinstance(learner_id, UUID):
            raise ValueError("rate limit learner_id must be a UUID")
        current, max_requests, window = _normalize_rate_limit_params(
            now, limit=limit, window_seconds=window_seconds
        )
        window_start = current - timedelta(seconds=window)
        try:
            with self._transaction() as transaction:
                key = self._rate_limit_key(learner_id)
                entity = self._read(transaction, key)
                raw_timestamps = (
                    entity.get("requested_at", ()) if entity is not None else ()
                )
                active = sorted(
                    ts
                    for item in raw_timestamps
                    if (ts := _as_utc(item)) > window_start
                )
                if len(active) >= max_requests:
                    unlock_at = active[-max_requests] + timedelta(seconds=window)
                    return max(1, math.ceil((unlock_at - current).total_seconds()))
                active.append(current)
                rate_entity = self._client.entity(
                    key, exclude_from_indexes=_RATE_LIMIT_UNINDEXED_FIELDS
                )
                rate_entity.update(
                    {
                        "learner_id": str(learner_id),
                        "requested_at": active,
                        "updated_at": current,
                    }
                )
                self._write(rate_entity, transaction)
                return None
        except Exception as exc:
            logger.exception(
                "Failed to reserve generation slot",
                extra={"learner_id": str(learner_id)},
            )
            raise PersistenceError(
                f"Failed to check generation rate limit for learner {learner_id}: {exc}"
            ) from exc

    def _get_requiring_owner(
        self, learner_id: UUID, practice_id: UUID
    ) -> GeneratedPracticeRecord | None:
        try:
            entity = self._client.get(self._key(practice_id))
            if entity is None:
                return None
            record = deserialize_generated_practice(entity)
            if record.learner_id != learner_id:
                raise ValueError(
                    f"generated practice {practice_id} belongs to another learner"
                )
            return record
        except Exception as exc:
            logger.exception(
                "Failed to inspect generated practice during claim wait",
                extra={"practice_id": str(practice_id)},
            )
            raise PersistenceError(
                f"Failed to retrieve generated practice {practice_id}: {exc}"
            ) from exc

    def _is_claim_present(self, learner_id: UUID, practice_id: UUID) -> bool:
        try:
            claim_entity = self._client.get(self._claim_key(practice_id))
            if claim_entity is None:
                return False
            if str(claim_entity.get("learner_id")) != str(learner_id):
                raise ValueError(
                    f"generated practice claim {practice_id} belongs to another learner"
                )
            return True
        except Exception as exc:
            logger.exception(
                "Failed to inspect generated practice claim",
                extra={"practice_id": str(practice_id)},
            )
            raise PersistenceError(
                f"Failed to inspect generated practice claim {practice_id}: {exc}"
            ) from exc

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

    def _delete(self, key: Any, transaction: Any) -> None:
        deleter = getattr(transaction, "delete", None)
        if callable(deleter):
            deleter(key)
            return
        client_deleter = getattr(self._client, "delete", None)
        if callable(client_deleter):
            client_deleter(key)

    def _key(self, practice_id: UUID) -> Any:
        return self._client.key(
            GENERATED_PRACTICE_KIND,
            str(practice_id),
            namespace=self._namespace,
        )

    def _claim_key(self, practice_id: UUID) -> Any:
        return self._client.key(
            GENERATED_PRACTICE_CLAIM_KIND,
            str(practice_id),
            namespace=self._namespace,
        )

    def _rate_limit_key(self, learner_id: UUID) -> Any:
        return self._client.key(
            GENERATED_PRACTICE_RATE_LIMIT_KIND,
            str(learner_id),
            namespace=self._namespace,
        )
