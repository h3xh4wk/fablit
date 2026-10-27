"""Google Cloud Datastore news-curation job repository (SPEC-042 §6).

Jobs live in their own kind and in the existing ``news`` namespace, separate
from curated stories, learner practice history, authoring candidates, and
published practices. The adapter persists the queryable lifecycle fields and
keeps operator copy and the serialized batch report unindexed, so a long safe
message can never fail a write on Datastore's 1500-byte indexed-string limit.

``start`` and ``claim`` run inside a transaction: the small "active job"
pointer guarantees that at most one job is queued or running, and a lease
check guarantees that only one worker executes a job. Storage failures are
translated into
:class:`~fablit.application.persistence.PersistenceError`, so a job that could
not be written is never reported as accepted.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fablit.application.errors import NewsCurationJobTransitionError
from fablit.application.news import (
    NewsBatchResult,
    NewsCurationDiagnostics,
    NewsItemOutcome,
    NewsProviderOutcome,
    NewsSourceFailure,
)
from fablit.application.news_jobs import (
    NewsCurationCounters,
    NewsCurationErrorCategory,
    NewsCurationJob,
    NewsCurationJobRepository,
    NewsCurationJobStatus,
    NewsCurationStage,
)
from fablit.application.persistence import PersistenceError

logger = logging.getLogger(__name__)

#: Datastore kind holding curation jobs, in the existing news namespace.
NEWS_JOB_KIND = "NewsCurationJob"

#: Datastore kind holding the single active-job pointer used by ``start``.
NEWS_JOB_ACTIVE_KIND = "NewsCurationJobActive"
DEFAULT_NEWS_JOB_NAMESPACE = "news"
ACTIVE_POINTER_NAME = "active"

#: Operator copy and the serialized report are read back with the entity only.
_UNINDEXED_FIELDS = (
    "message",
    "error_message",
    "report_json",
    "lease_owner",
)


def serialize_news_job(job: NewsCurationJob) -> dict[str, Any]:
    """Convert a validated job into Datastore-storable properties."""
    properties: dict[str, Any] = {
        "job_id": str(job.job_id),
        "status": job.status.value,
        "stage": job.stage.value,
        "message": job.message,
        "created_at": job.created_at,
        "next_source_index": job.next_source_index,
        "attempt": job.attempt,
        "sources_configured": job.counters.sources_configured,
        "sources_processed": job.counters.sources_processed,
        "sources_failed": job.counters.sources_failed,
        "items_fetched": job.counters.items_fetched,
        "items_deduplicated": job.counters.items_deduplicated,
        "items_published": job.counters.items_published,
        "items_rejected": job.counters.items_rejected,
        "items_failed": job.counters.items_failed,
        "provider_retries": job.counters.provider_retries,
    }
    optional: dict[str, Any] = {
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "lease_owner": job.lease_owner,
        "lease_expires_at": job.lease_expires_at,
        "error_category": (
            job.error_category.value if job.error_category is not None else None
        ),
        "error_message": job.error_message,
        "report_json": (
            json.dumps(_report_payload(job.report)) if job.report is not None else None
        ),
    }
    properties.update(
        {name: value for name, value in optional.items() if value is not None}
    )
    return properties


def deserialize_news_job(entity: Mapping[str, Any]) -> NewsCurationJob:
    """Reconstruct a validated job from a Datastore entity."""
    raw_category = entity.get("error_category")
    raw_report = entity.get("report_json")
    return NewsCurationJob(
        job_id=UUID(str(entity["job_id"])),
        created_at=_as_datetime(entity["created_at"]),
        status=NewsCurationJobStatus(str(entity.get("status", "queued"))),
        stage=NewsCurationStage(str(entity.get("stage", "queued"))),
        message=str(entity.get("message", "Waiting to start.")),
        started_at=_optional_datetime(entity.get("started_at")),
        finished_at=_optional_datetime(entity.get("finished_at")),
        counters=NewsCurationCounters(
            sources_configured=int(entity.get("sources_configured", 0)),
            sources_processed=int(entity.get("sources_processed", 0)),
            sources_failed=int(entity.get("sources_failed", 0)),
            items_fetched=int(entity.get("items_fetched", 0)),
            items_deduplicated=int(entity.get("items_deduplicated", 0)),
            items_published=int(entity.get("items_published", 0)),
            items_rejected=int(entity.get("items_rejected", 0)),
            items_failed=int(entity.get("items_failed", 0)),
            provider_retries=int(entity.get("provider_retries", 0)),
        ),
        report=(
            _report_from_payload(json.loads(str(raw_report)))
            if raw_report is not None
            else None
        ),
        next_source_index=int(entity.get("next_source_index", 0)),
        attempt=int(entity.get("attempt", 0)),
        lease_owner=(str(entity["lease_owner"]) if entity.get("lease_owner") else None),
        lease_expires_at=_optional_datetime(entity.get("lease_expires_at")),
        error_category=(
            NewsCurationErrorCategory(str(raw_category))
            if raw_category is not None
            else None
        ),
        error_message=(
            str(entity["error_message"]) if entity.get("error_message") else None
        ),
    )


def _report_payload(report: NewsBatchResult) -> dict[str, Any]:
    return {
        "started_at": report.started_at.isoformat(),
        "finished_at": report.finished_at.isoformat(),
        "sources_configured": report.sources_configured,
        "sources_processed": report.sources_processed,
        "fetched": report.fetched,
        "deduplicated": report.deduplicated,
        "published": report.published,
        "rejected": report.rejected,
        "failed": report.failed,
        "provider_retries": report.provider_retries,
        "diagnostics": (
            _diagnostics_payload(report.diagnostics)
            if report.diagnostics is not None
            else None
        ),
        "rejections": [_outcome_payload(item) for item in report.rejections],
        "failures": [_outcome_payload(item) for item in report.failures],
        "source_failures": [
            {"source_name": failure.source_name, "reason": failure.reason}
            for failure in report.source_failures
        ],
    }


def _diagnostics_payload(diagnostics: NewsCurationDiagnostics) -> dict[str, Any]:
    return {
        "provider_id": diagnostics.provider_id,
        "model_id": diagnostics.model_id,
        "provider_retries": diagnostics.provider_retries,
        "transient_retries_recovered": diagnostics.transient_retries_recovered,
        "exhausted_retries": diagnostics.exhausted_retries,
        "provider_outcome": diagnostics.provider_outcome.value,
        "last_status_code": diagnostics.last_status_code,
    }


def _diagnostics_from_payload(payload: Mapping[str, Any]) -> NewsCurationDiagnostics:
    return NewsCurationDiagnostics(
        provider_id=str(payload.get("provider_id", "")),
        model_id=str(payload.get("model_id", "")),
        provider_retries=int(payload.get("provider_retries", 0)),
        transient_retries_recovered=int(payload.get("transient_retries_recovered", 0)),
        exhausted_retries=int(payload.get("exhausted_retries", 0)),
        provider_outcome=NewsProviderOutcome(
            str(payload.get("provider_outcome", "ok"))
        ),
        last_status_code=(
            int(payload["last_status_code"])
            if payload.get("last_status_code") is not None
            else None
        ),
    )


def _outcome_payload(outcome: NewsItemOutcome) -> dict[str, str]:
    return {
        "source_name": outcome.source_name,
        "title": outcome.title,
        "url": outcome.url,
        "reason": outcome.reason,
    }


def _report_from_payload(payload: Mapping[str, Any]) -> NewsBatchResult:
    return NewsBatchResult(
        started_at=_as_datetime(payload["started_at"]),
        finished_at=_as_datetime(payload["finished_at"]),
        sources_configured=int(payload.get("sources_configured", 0)),
        sources_processed=int(payload.get("sources_processed", 0)),
        fetched=int(payload.get("fetched", 0)),
        deduplicated=int(payload.get("deduplicated", 0)),
        published=int(payload.get("published", 0)),
        rejected=int(payload.get("rejected", 0)),
        failed=int(payload.get("failed", 0)),
        provider_retries=int(payload.get("provider_retries", 0)),
        diagnostics=(
            _diagnostics_from_payload(payload["diagnostics"])
            if payload.get("diagnostics") is not None
            else None
        ),
        rejections=tuple(
            _outcome_from_payload(item) for item in payload.get("rejections", ())
        ),
        failures=tuple(
            _outcome_from_payload(item) for item in payload.get("failures", ())
        ),
        source_failures=tuple(
            NewsSourceFailure(
                source_name=str(item["source_name"]), reason=str(item["reason"])
            )
            for item in payload.get("source_failures", ())
        ),
    )


def _outcome_from_payload(payload: Mapping[str, Any]) -> NewsItemOutcome:
    return NewsItemOutcome(
        source_name=str(payload.get("source_name", "")),
        title=str(payload.get("title", "")),
        url=str(payload.get("url", "")),
        reason=str(payload.get("reason", "")),
    )


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    if not isinstance(value, datetime):
        raise ValueError(f"expected a datetime, got {value!r}")
    return value.astimezone(UTC)


def _optional_datetime(value: Any) -> datetime | None:
    return None if value is None else _as_datetime(value)


class DatastoreNewsCurationJobRepository(NewsCurationJobRepository):
    """Durable curation job repository backed by Google Cloud Datastore."""

    def __init__(
        self,
        client: Any,
        *,
        namespace: str = DEFAULT_NEWS_JOB_NAMESPACE,
    ) -> None:
        self._client = client
        self._namespace = namespace

    def start(self, job: NewsCurationJob) -> NewsCurationJob | None:
        if not isinstance(job, NewsCurationJob):
            raise ValueError("news job repository only accepts NewsCurationJob records")
        if job.status is not NewsCurationJobStatus.QUEUED:
            raise ValueError("a new news curation job must be queued")
        try:
            with self._transaction() as transaction:
                active = self._read_active(transaction)
                if active is not None and active.is_active:
                    return None
                entity = self._client.entity(
                    self._job_key(job.job_id),
                    exclude_from_indexes=_UNINDEXED_FIELDS,
                )
                entity.update(serialize_news_job(job))
                self._write(entity, transaction)
                pointer = self._client.entity(self._pointer_key())
                pointer["job_id"] = str(job.job_id)
                self._write(pointer, transaction)
        except Exception as exc:
            logger.exception(
                "Failed to persist news curation job",
                extra={"job_id": str(job.job_id)},
            )
            raise PersistenceError(
                f"Failed to persist news curation job {job.job_id}: {exc}"
            ) from exc
        return job

    def claim(
        self,
        job_id: UUID,
        *,
        owner: str,
        now: datetime,
        lease_until: datetime,
    ) -> NewsCurationJob | None:
        try:
            with self._transaction() as transaction:
                entity = self._read(transaction, self._job_key(job_id))
                if entity is None:
                    return None
                job = deserialize_news_job(entity)
                if job.is_terminal:
                    return None
                if job.status is NewsCurationJobStatus.RUNNING and not job.is_stale(
                    now
                ):
                    return None
                claimed = job.claim(owner=owner, at=now, lease_until=lease_until)
                self._put(claimed, transaction)
        except NewsCurationJobTransitionError:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to claim news curation job",
                extra={"job_id": str(job_id)},
            )
            raise PersistenceError(
                f"Failed to claim news curation job {job_id}: {exc}"
            ) from exc
        return claimed

    def save(self, job: NewsCurationJob) -> NewsCurationJob:
        if not isinstance(job, NewsCurationJob):
            raise ValueError("news job repository only accepts NewsCurationJob records")
        try:
            existing_entity = self._client.get(self._job_key(job.job_id))
            if existing_entity is not None:
                existing = deserialize_news_job(existing_entity)
                if existing != job:
                    if existing.is_terminal:
                        raise NewsCurationJobTransitionError(
                            f"news curation job {job.job_id} is already terminal"
                        )
                    if existing.attempt > job.attempt:
                        raise NewsCurationJobTransitionError(
                            f"news curation job {job.job_id} was taken over by a "
                            "newer attempt"
                        )
            self._put(job)
            if job.is_terminal:
                self._clear_pointer(job.job_id)
        except NewsCurationJobTransitionError:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to save news curation job",
                extra={"job_id": str(job.job_id)},
            )
            raise PersistenceError(
                f"Failed to save news curation job {job.job_id}: {exc}"
            ) from exc
        return job

    def get(self, job_id: UUID) -> NewsCurationJob | None:
        if not isinstance(job_id, UUID):
            return None
        try:
            entity = self._client.get(self._job_key(job_id))
        except Exception as exc:
            logger.exception(
                "Failed to retrieve news curation job",
                extra={"job_id": str(job_id)},
            )
            raise PersistenceError(
                f"Failed to retrieve news curation job {job_id}: {exc}"
            ) from exc
        return None if entity is None else deserialize_news_job(entity)

    def latest(self) -> NewsCurationJob | None:
        jobs = self._all_jobs()
        if not jobs:
            return None
        return max(jobs, key=lambda job: (job.created_at, str(job.job_id)))

    def find_active(self) -> NewsCurationJob | None:
        active = [job for job in self._all_jobs() if job.is_active]
        if not active:
            return None
        return max(active, key=lambda job: (job.created_at, str(job.job_id)))

    def _all_jobs(self) -> tuple[NewsCurationJob, ...]:
        try:
            query = self._client.query(kind=NEWS_JOB_KIND, namespace=self._namespace)
            entities = [entity for entity in query.fetch()]
            return tuple(deserialize_news_job(entity) for entity in entities)
        except Exception as exc:
            logger.exception("Failed to query news curation jobs")
            raise PersistenceError(
                f"Failed to query news curation jobs: {exc}"
            ) from exc

    def _read_active(self, transaction: Any) -> NewsCurationJob | None:
        pointer = self._read(transaction, self._pointer_key())
        if pointer is None:
            return None
        raw_id = pointer.get("job_id")
        if not raw_id:
            return None
        try:
            job_id = UUID(str(raw_id))
        except ValueError:
            return None
        entity = self._read(transaction, self._job_key(job_id))
        return None if entity is None else deserialize_news_job(entity)

    def _clear_pointer(self, job_id: UUID) -> None:
        pointer_key = self._pointer_key()
        pointer = self._client.get(pointer_key)
        if pointer is not None and str(pointer.get("job_id")) == str(job_id):
            delete = getattr(self._client, "delete", None)
            if callable(delete):
                delete(pointer_key)

    def _put(self, job: NewsCurationJob, transaction: Any = None) -> None:
        entity = self._client.entity(
            self._job_key(job.job_id),
            exclude_from_indexes=_UNINDEXED_FIELDS,
        )
        entity.update(serialize_news_job(job))
        self._write(entity, transaction)

    def _write(self, entity: Any, transaction: Any) -> None:
        """Write through the open transaction so the guard is atomic."""
        putter = getattr(transaction, "put", None)
        if callable(putter):
            putter(entity)
            return
        self._client.put(entity)

    def _transaction(self) -> Any:
        transaction = getattr(self._client, "transaction", None)
        return transaction() if callable(transaction) else nullcontext(None)

    def _read(self, transaction: Any, key: Any) -> Any:
        getter = getattr(transaction, "get", None)
        if callable(getter):
            return getter(key)
        return self._client.get(key)

    def _job_key(self, job_id: UUID) -> Any:
        return self._client.key(
            NEWS_JOB_KIND,
            str(job_id),
            namespace=self._namespace,
        )

    def _pointer_key(self) -> Any:
        return self._client.key(
            NEWS_JOB_ACTIVE_KIND,
            ACTIVE_POINTER_NAME,
            namespace=self._namespace,
        )
