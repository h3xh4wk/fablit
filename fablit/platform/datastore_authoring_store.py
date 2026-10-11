"""Google Cloud Datastore shared authoring candidate store (SPEC-032 / FIX-7).

This platform adapter provides shared authoring candidate persistence across
Google App Engine instances. Active candidate drafts, validation results,
revisions, and review decisions are stored in the authoring namespace, keeping
untrusted candidate data completely isolated from learner practice history.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.authoring import (
    AuthoringBrief,
    AuthoringCandidateStore,
    CandidateReviewOutcome,
    PracticeCandidate,
)
from fablit.application.authoring import (
    _CONTRACT_FIELDS,
    AuthoringRevision,
    CandidateValidation,
)
from fablit.application.persistence import PersistenceError
from fablit.application.store import PracticeContentContract

logger = logging.getLogger(__name__)


class DatastoreAuthoringCandidateStore(AuthoringCandidateStore):
    """Shared authoring candidate store backed by Google Cloud Datastore (FIX-7).

    Preserves candidate state across requests and instance restarts on Google
    App Engine, enforcing validation gates, conflict prevention, and candidate
    retention policies.
    """

    def __init__(
        self,
        client: Any,
        *,
        retention_days: int = 30,
        namespace: str = "authoring",
    ) -> None:
        super().__init__(retention_days=retention_days)
        self._client = client
        self._namespace = namespace

    def _get_entity(self, candidate_id: UUID) -> PracticeCandidate | None:
        """Fetch a candidate entity from Datastore by key."""
        try:
            key = self._client.key(
                "AuthoringCandidate", str(candidate_id), namespace=self._namespace
            )
            entity = self._client.get(key)
            if entity is None:
                return None
            return self._deserialize_candidate(entity)
        except Exception as exc:
            logger.exception(
                "Failed to retrieve authoring candidate from Datastore",
                extra={"candidate_id": str(candidate_id)},
            )
            raise PersistenceError(
                f"Failed to retrieve candidate {candidate_id}: {exc}"
            ) from exc

    def _put_entity(self, candidate: PracticeCandidate) -> None:
        """Persist a candidate entity to Datastore."""
        try:
            key = self._client.key(
                "AuthoringCandidate", str(candidate.id), namespace=self._namespace
            )
            entity = self._client.entity(key)
            entity.update(self._serialize_candidate(candidate))
            self._client.put(entity)
        except Exception as exc:
            logger.exception(
                "Failed to persist authoring candidate to Datastore",
                extra={"candidate_id": str(candidate.id)},
            )
            raise PersistenceError(
                f"Failed to persist candidate {candidate.id}: {exc}"
            ) from exc

    def _delete_entity(self, candidate_id: UUID) -> None:
        """Delete a candidate entity from Datastore."""
        try:
            key = self._client.key(
                "AuthoringCandidate", str(candidate_id), namespace=self._namespace
            )
            if hasattr(self._client, "delete"):
                self._client.delete(key)
            elif hasattr(self._client, "_store") and isinstance(
                self._client._store, dict
            ):
                self._client._store.pop(key._id(), None)
        except Exception as exc:
            logger.exception(
                "Failed to delete authoring candidate from Datastore",
                extra={"candidate_id": str(candidate_id)},
            )
            raise PersistenceError(
                f"Failed to delete candidate {candidate_id}: {exc}"
            ) from exc

    def _all_entities(self) -> list[PracticeCandidate]:
        """Fetch all candidates from Datastore ordered newest first."""
        try:
            query = self._client.query(
                kind="AuthoringCandidate", namespace=self._namespace
            )
            with suppress(AttributeError, TypeError):
                query.order = ["-generated_at"]
            with suppress(AttributeError, TypeError):
                query.order_by = [("-generated_at",)]

            entities = list(query.fetch())
            candidates = [self._deserialize_candidate(e) for e in entities]
            candidates.sort(key=lambda c: c.generated_at, reverse=True)
            return candidates
        except Exception as exc:
            logger.exception("Failed to query authoring candidates from Datastore")
            raise PersistenceError(f"Failed to query candidates: {exc}") from exc

    @staticmethod
    def _serialize_candidate(candidate: PracticeCandidate) -> dict[str, Any]:
        """Convert a PracticeCandidate to Datastore entity dictionary."""
        brief_dict = dataclasses.asdict(candidate.brief)
        if "intended_mode" in brief_dict and hasattr(
            candidate.brief.intended_mode, "value"
        ):
            brief_dict["intended_mode"] = candidate.brief.intended_mode.value

        return {
            "id": str(candidate.id),
            "provider": candidate.provider,
            "model": candidate.model,
            "generated_at": candidate.generated_at,
            "revision": candidate.revision,
            "reviewer": candidate.reviewer,
            "decided_at": candidate.decided_at,
            "review_outcome": (
                candidate.review_outcome.value
                if candidate.review_outcome is not None
                else None
            ),
            "brief": brief_dict,
            "candidate_data": dict(candidate.candidate_data),
            "validation": {
                "structural_errors": list(candidate.validation.structural_errors),
                "feedback_errors": list(candidate.validation.feedback_errors),
                "content_warnings": list(candidate.validation.content_warnings),
            },
            "history": [
                {
                    "version": rev.version,
                    "title": rev.title,
                    "description": rev.description,
                    "contract": (
                        {
                            field: getattr(rev.contract, field)
                            for field in _CONTRACT_FIELDS
                            if hasattr(rev.contract, field)
                        }
                        if rev.contract is not None
                        else None
                    ),
                    "edited_at": rev.edited_at,
                    "editor": rev.editor,
                }
                for rev in candidate.history
            ],
        }

    @staticmethod
    def _deserialize_candidate(entity: Mapping[str, Any]) -> PracticeCandidate:
        """Reconstruct a PracticeCandidate from a Datastore entity dictionary."""
        candidate_id = UUID(str(entity["id"]))
        provider = str(entity["provider"])
        model = str(entity["model"])

        generated_at = entity["generated_at"]
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=UTC)

        revision = int(entity.get("revision", 1))
        reviewer = entity.get("reviewer")

        decided_at = entity.get("decided_at")
        if decided_at is not None:
            if isinstance(decided_at, str):
                decided_at = datetime.fromisoformat(decided_at)
            if decided_at.tzinfo is None:
                decided_at = decided_at.replace(tzinfo=UTC)

        raw_outcome = entity.get("review_outcome")
        review_outcome = (
            CandidateReviewOutcome(raw_outcome) if raw_outcome is not None else None
        )

        brief_dict = dict(entity.get("brief", {}))
        if "intended_mode" in brief_dict and hasattr(
            brief_dict["intended_mode"], "value"
        ):
            brief_dict["intended_mode"] = brief_dict["intended_mode"].value
        brief = AuthoringBrief.from_mapping(brief_dict)

        candidate_data = dict(entity.get("candidate_data", {}))

        val_raw = entity.get("validation", {})
        validation = CandidateValidation(
            structural_errors=tuple(val_raw.get("structural_errors", ())),
            feedback_errors=tuple(val_raw.get("feedback_errors", ())),
            content_warnings=tuple(val_raw.get("content_warnings", ())),
        )

        history_raw = entity.get("history", [])
        history: list[AuthoringRevision] = []
        for h in history_raw:
            rev_contract = None
            if h.get("contract") is not None:
                c_data = h["contract"]
                vals = {
                    k: str(c_data[k]).strip()
                    for k in _CONTRACT_FIELDS
                    if k in c_data and str(c_data[k]).strip()
                }
                if len(vals) == len(_CONTRACT_FIELDS):
                    rev_contract = PracticeContentContract(**vals)

            rev_edited_at = h["edited_at"]
            if isinstance(rev_edited_at, str):
                rev_edited_at = datetime.fromisoformat(rev_edited_at)
            if rev_edited_at.tzinfo is None:
                rev_edited_at = rev_edited_at.replace(tzinfo=UTC)

            history.append(
                AuthoringRevision(
                    version=int(h["version"]),
                    title=str(h["title"]),
                    description=str(h["description"]),
                    contract=rev_contract,
                    edited_at=rev_edited_at,
                    editor=str(h.get("editor", "author")),
                )
            )

        return PracticeCandidate(
            id=candidate_id,
            brief=brief,
            candidate_data=candidate_data,
            provider=provider,
            model=model,
            generated_at=generated_at,
            review_outcome=review_outcome,
            validation=validation,
            revision=revision,
            reviewer=reviewer,
            decided_at=decided_at,
            history=tuple(history),
        )
