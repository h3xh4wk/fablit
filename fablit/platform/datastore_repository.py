"""Google Cloud Datastore adapter for practice history persistence (SPEC-021).

This module isolates Datastore-specific concerns behind the persistence
boundary. The adapter is responsible for converting application/domain records
to Datastore-compatible representations, handling Datastore-specific errors,
and reconstructing domain records for review.

SPEC-021 §11: the adapter is responsible for:
- converting application/domain records to Datastore-compatible representations
- assigning and retrieving stable identifiers
- writing learner-journey records
- querying completed practice history
- reconstructing application/domain records for review
- handling Datastore-specific errors without leaking them into domain objects

The domain layer remains independent of Datastore APIs.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fablit.application.artifacts import ArtifactRef
from fablit.application.persistence import (
    PersistenceError,
    PracticeHistoryRepository,
    PracticeHistorySummary,
    StoredPracticeCompletion,
)
from fablit.domain import Evaluation, Feedback, Reflection, StimulusInstance, Submission
from fablit.platform.datastore_entities import embedded_entity

logger = logging.getLogger("fablit.application.datastore_repository")


class DatastorePracticeHistoryRepository(PracticeHistoryRepository):
    """Google Cloud Datastore adapter for practice history (SPEC-021).

    This adapter handles all Datastore-specific concerns:
    - entity serialization/deserialization
    - Datastore key management
    - query construction
    - error handling and mapping

    The domain model and application layer never depend on Datastore APIs.

    SPEC-021 §12: configuration keeps Google Cloud project/environment
    configuration outside source-code business logic, uses the normal Google
    Cloud authentication/application-default mechanism available to App Engine,
    and avoids hard-coded credentials or service-account secrets.
    """

    def __init__(self, client: Any) -> None:
        """Initialize the Datastore adapter.

        Args:
            client: A google.cloud.datastore.Client instance. This is typically
                created by the application's initialization logic, not by this
                adapter, so GCP authentication is handled at the application level.
        """
        self._client = client

    def _embedded_entity(self, properties: Mapping[str, Any]) -> dict[str, Any]:
        """Build a Datastore embedded entity whose properties are not indexed.

        The practice-completion payload (response, feedback, reflection,
        stimulus and artifact metadata) is only ever read back by key, never
        queried, so none of it needs an index. Excluding it matters beyond
        write cost: Datastore rejects an *indexed* string property longer than
        1500 bytes, which previously failed the whole completion write for a
        long enough reflection (or learner response, or generated feedback).

        See :mod:`fablit.platform.datastore_entities` for why the exclusions
        have to live on nested embedded entities rather than on the parent.
        """
        return embedded_entity(self._client, properties)

    def save_completion(
        self,
        learner_id: UUID,
        activity_id: UUID,
        activity_title: str,
        submission: Submission,
        evaluation: Evaluation,
        feedback: Feedback,
        reflection: Reflection | None,
        stimulus: StimulusInstance | None,
        artifact: ArtifactRef | None = None,
        completion_id: UUID | None = None,
    ) -> StoredPracticeCompletion:
        """Persist a completed practice journey to Datastore.

        SPEC-021 §14: completion writes are idempotent via stable completion
        identity. A retry does not unintentionally create duplicate history
        for the same completion.

        SPEC-159: reflection may be absent or attached later to the same
        completion.
        """
        if completion_id is None:
            if reflection is not None:
                completion_id = reflection.id
            else:
                from uuid import uuid4

                completion_id = uuid4()

        try:
            key = self._client.key(
                "PracticeCompletion",
                str(completion_id),
                namespace=f"learner_{learner_id}",
            )

            # Check if exists for update (attach reflection later)
            existing_entity = self._client.get(key)
            if existing_entity is not None:
                completed_at = existing_entity.get("completed_at")
                if reflection is not None:
                    reflection_to_store = reflection
                    completed_at = (
                        reflection.created_at
                    )  # update timestamp if reflection added
                else:
                    reflection_to_store = None
                    if existing_entity.get("reflection"):
                        reflection_to_store = self._deserialize_reflection(
                            existing_entity["reflection"]
                        )
                activity_title_to_store = activity_title or existing_entity.get(
                    "activity_title", ""
                )
            else:
                if reflection is not None:
                    completed_at = reflection.created_at
                else:
                    completed_at = feedback.created_at
                reflection_to_store = reflection
                activity_title_to_store = activity_title

            entity = self._client.entity(key)
            entity.update(
                {
                    "learner_id": str(learner_id),
                    "activity_id": str(activity_id),
                    "activity_title": activity_title_to_store,
                    "completed_at": completed_at,
                    # Serialize journey records
                    "submission": self._serialize_submission(submission),
                    "evaluation": self._serialize_evaluation(evaluation),
                    "feedback": self._serialize_feedback(feedback),
                    "reflection": (
                        self._serialize_reflection(reflection_to_store)
                        if reflection_to_store is not None
                        else None
                    ),
                    "stimulus": (
                        self._serialize_stimulus(stimulus) if stimulus else None
                    ),
                    "artifact": (
                        self._serialize_artifact(artifact) if artifact else None
                    ),
                }
            )

            self._client.put(entity)
            logger.info(
                "completion persisted",
                extra={
                    "learner_id": str(learner_id),
                    "activity_id": str(activity_id),
                    "completion_id": str(completion_id),
                },
            )

            return StoredPracticeCompletion(
                completion_id=completion_id,
                learner_id=learner_id,
                activity_id=activity_id,
                activity_title=activity_title_to_store,
                completed_at=completed_at,
                submission=submission,
                evaluation=evaluation,
                feedback=feedback,
                reflection=reflection_to_store,
                stimulus=stimulus,
                artifact=artifact,
            )

        except Exception as e:
            logger.exception(
                "completion persistence failed",
                extra={
                    "learner_id": str(learner_id),
                    "activity_id": str(activity_id),
                    "completion_id": str(completion_id),
                },
            )
            raise PersistenceError(
                "Failed to save completed practice. Please try again."
            ) from e

    def get_completion(
        self, learner_id: UUID, completion_id: UUID
    ) -> StoredPracticeCompletion | None:
        """Retrieve a specific completed practice from Datastore.

        Args:
            learner_id: The learner whose practice is being retrieved.
            completion_id: The stable identity of the completion record.

        Returns:
            StoredPracticeCompletion: The complete record, or None if not found.

        Raises:
            PersistenceError: If the Datastore query fails.
        """
        try:
            key = self._client.key(
                "PracticeCompletion",
                str(completion_id),
                namespace=f"learner_{learner_id}",
            )
            entity = self._client.get(key)

            if entity is None:
                return None

            # Verify ownership: ensure this completion belongs to the requested learner
            if UUID(entity["learner_id"]) != learner_id:
                return None

            reflection = None
            if entity.get("reflection"):
                try:
                    reflection = self._deserialize_reflection(entity["reflection"])
                except Exception:
                    reflection = None

            return StoredPracticeCompletion(
                completion_id=completion_id,
                learner_id=learner_id,
                activity_id=UUID(entity["activity_id"]),
                activity_title=entity["activity_title"],
                completed_at=entity["completed_at"],
                submission=self._deserialize_submission(entity["submission"]),
                evaluation=self._deserialize_evaluation(entity["evaluation"]),
                feedback=self._deserialize_feedback(entity["feedback"]),
                reflection=reflection,
                stimulus=(
                    self._deserialize_stimulus(entity["stimulus"])
                    if entity.get("stimulus")
                    else None
                ),
                artifact=(
                    self._deserialize_artifact(entity["artifact"])
                    if entity.get("artifact")
                    else None
                ),
            )

        except Exception as e:
            logger.exception(
                "completion retrieval failed",
                extra={
                    "learner_id": str(learner_id),
                    "completion_id": str(completion_id),
                },
            )
            raise PersistenceError(
                "Failed to retrieve completed practice. Please try again."
            ) from e

    def list_completions(self, learner_id: UUID) -> tuple[PracticeHistorySummary, ...]:
        """List all completed practice for a learner from Datastore.

        SPEC-021 §8: ordered newest first (descending by completed_at).

        Args:
            learner_id: The learner whose history is being listed.

        Returns:
            tuple[PracticeHistorySummary, ...]: Summaries ordered newest first.

        Raises:
            PersistenceError: If the Datastore query fails.
        """
        try:
            query = self._client.query(
                kind="PracticeCompletion",
                namespace=f"learner_{learner_id}",
            )
            query.add_filter("learner_id", "=", str(learner_id))
            query.order_by = [("-completed_at",)]

            entities = list(query.fetch())

            summaries = tuple(
                PracticeHistorySummary(
                    completion_id=UUID(entity.key.name),
                    activity_id=UUID(entity["activity_id"]),
                    activity_title=entity["activity_title"],
                    completed_at=entity["completed_at"],
                    submission_preview=self._preview_text(
                        self._deserialize_submission(entity["submission"]).response
                    ),
                )
                for entity in entities
            )

            return summaries

        except Exception as e:
            logger.exception(
                "history list query failed",
                extra={"learner_id": str(learner_id)},
            )
            raise PersistenceError(
                "Failed to load practice history. Please try again."
            ) from e

    def has_completed_activity(self, learner_id: UUID, activity_id: UUID) -> bool:
        """Check if learner has completed an activity.

        Args:
            learner_id: The learner.
            activity_id: The activity.

        Returns:
            bool: True if at least one completion exists for this pair.

        Raises:
            PersistenceError: If the Datastore query fails.
        """
        try:
            query = self._client.query(
                kind="PracticeCompletion",
                namespace=f"learner_{learner_id}",
            )
            query.add_filter("learner_id", "=", str(learner_id))
            query.add_filter("activity_id", "=", str(activity_id))
            # Limit to 1 for efficiency: we only need to know if at least one exists
            query.limit = 1

            return len(list(query.fetch())) > 0

        except Exception:
            logger.exception(
                "activity completion check failed",
                extra={
                    "learner_id": str(learner_id),
                    "activity_id": str(activity_id),
                },
            )
            # In case of query failure, default to False (conservative approach)
            # so the dashboard doesn't show incorrect completion indicators
            return False

    def _serialize_submission(self, submission: Submission) -> dict[str, Any]:
        """Convert a Submission domain object to Datastore representation."""
        return self._embedded_entity(
            {
                "id": str(submission.id),
                "learner_id": str(submission.learner_id),
                "activity_id": str(submission.activity_id),
                "response": submission.response,
                "submitted_at": submission.submitted_at,
                "status": submission.status.value,
                # SPEC-026 §2.3: the session's optional pre-practice intention
                # is persisted with the response so review can render it.
                "pre_practice_intention": submission.pre_practice_intention,
            }
        )

    @staticmethod
    def _deserialize_submission(data: dict[str, Any]) -> Submission:
        """Reconstruct a Submission from Datastore representation."""
        from fablit.domain import SubmissionStatus

        return Submission(
            learner_id=UUID(data["learner_id"]),
            activity_id=UUID(data["activity_id"]),
            response=data["response"],
            id=UUID(data["id"]),
            submitted_at=data["submitted_at"],
            status=SubmissionStatus(data["status"]),
            # Records stored before SPEC-026 carry no intention key.
            pre_practice_intention=data.get("pre_practice_intention"),
        )

    def _serialize_evaluation(self, evaluation: Evaluation) -> dict[str, Any]:
        """Convert an Evaluation domain object to Datastore representation."""
        return self._embedded_entity(
            {
                "id": str(evaluation.id),
                "submission_id": str(evaluation.submission_id),
                # Nested findings, like every other payload mapping, are
                # stored as non-indexed embedded entities by the helper.
                "findings": [
                    {
                        "id": str(f.id),
                        "observation": f.observation,
                        "evidence": f.evidence,
                    }
                    for f in evaluation.findings
                ],
                "evaluated_at": evaluation.evaluated_at,
            }
        )

    @staticmethod
    def _deserialize_evaluation(data: dict[str, Any]) -> Evaluation:
        """Reconstruct an Evaluation from Datastore representation."""
        from fablit.domain import EvaluationFinding

        findings = tuple(
            EvaluationFinding(
                observation=f["observation"],
                evidence=f.get("evidence"),
                id=UUID(f["id"]),
            )
            for f in data["findings"]
        )
        return Evaluation(
            submission_id=UUID(data["submission_id"]),
            findings=findings,
            id=UUID(data["id"]),
            evaluated_at=data["evaluated_at"],
        )

    def _serialize_feedback(self, feedback: Feedback) -> dict[str, Any]:
        """Convert a Feedback domain object to Datastore representation."""
        return self._embedded_entity(
            {
                "id": str(feedback.id),
                "evaluation_id": str(feedback.evaluation_id),
                "content": feedback.content,
                "created_at": feedback.created_at,
            }
        )

    @staticmethod
    def _deserialize_feedback(data: dict[str, Any]) -> Feedback:
        """Reconstruct a Feedback from Datastore representation."""
        return Feedback(
            evaluation_id=UUID(data["evaluation_id"]),
            content=data["content"],
            id=UUID(data["id"]),
            created_at=data["created_at"],
        )

    def _serialize_reflection(self, reflection: Reflection) -> dict[str, Any]:
        """Convert a Reflection domain object to Datastore representation."""
        return self._embedded_entity(
            {
                "id": str(reflection.id),
                "feedback_id": str(reflection.feedback_id),
                "content": reflection.content,
                "created_at": reflection.created_at,
            }
        )

    @staticmethod
    def _deserialize_reflection(data: dict[str, Any]) -> Reflection:
        """Reconstruct a Reflection from Datastore representation."""
        return Reflection(
            feedback_id=UUID(data["feedback_id"]),
            content=data["content"],
            id=UUID(data["id"]),
            created_at=data["created_at"],
        )

    def _serialize_stimulus(self, stimulus: StimulusInstance) -> dict[str, Any]:
        """Convert a StimulusInstance to Datastore representation."""
        return self._embedded_entity(
            {
                "id": str(stimulus.id),
                "activity_id": str(stimulus.activity_id),
                "provider": stimulus.provider,
                "image_url": stimulus.image_url,
                "source_url": stimulus.source_url,
                "retrieved_at": stimulus.retrieved_at,
                "asset_id": stimulus.asset_id,
                "creator": stimulus.creator,
                "license": stimulus.license,
                "attribution": stimulus.attribution,
                "alt_text": stimulus.alt_text,
            }
        )

    @staticmethod
    def _deserialize_stimulus(data: dict[str, Any]) -> StimulusInstance:
        """Reconstruct a StimulusInstance from Datastore representation."""
        return StimulusInstance(
            activity_id=UUID(data["activity_id"]),
            provider=data["provider"],
            image_url=data["image_url"],
            source_url=data["source_url"],
            retrieved_at=data["retrieved_at"],
            id=UUID(data["id"]),
            asset_id=data.get("asset_id"),
            creator=data.get("creator"),
            license=data.get("license"),
            attribution=data.get("attribution"),
            alt_text=data.get("alt_text"),
        )

    def _serialize_artifact(self, artifact: ArtifactRef) -> dict[str, Any]:
        """Convert a private sketchbook reference to a Datastore-safe payload.

        SPEC-033: only artifact metadata is persisted; the private bytes live
        behind the artifact-storage boundary, never inside the history entity.
        """
        return self._embedded_entity(
            {
                "artifact_id": str(artifact.artifact_id),
                "learner_id": str(artifact.learner_id),
                "activity_id": str(artifact.activity_id),
                "filename": artifact.filename,
                "content_type": artifact.content_type,
                "size_bytes": artifact.size_bytes,
                "created_at": artifact.created_at,
            }
        )

    @staticmethod
    def _deserialize_artifact(data: dict[str, Any]) -> ArtifactRef:
        """Reconstruct a private sketchbook reference from Datastore representation."""
        return ArtifactRef(
            artifact_id=UUID(data["artifact_id"]),
            learner_id=UUID(data["learner_id"]),
            activity_id=UUID(data["activity_id"]),
            filename=data["filename"],
            content_type=data["content_type"],
            size_bytes=data["size_bytes"],
            created_at=data["created_at"],
        )

    @staticmethod
    def _preview_text(response: str, max_length: int = 60) -> str:
        """Create a brief preview of the learner's response."""
        if len(response) <= max_length:
            return response
        return response[:max_length].rstrip() + "…"
