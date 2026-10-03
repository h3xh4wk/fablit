"""Regression tests for issue #113 — retry-safe artifact persistence and
MIME/signature consistency at the application integration layer.

These exercises sit at the application-integration layer because that is where
the sketchbook-artifact boundary is orchestrated: validation, staging,
durable persistence, rollback, and retrieval all meet here. They complement
the existing SPEC-033 history tests, which already cover the happy path and
the legacy “no sketch” path.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from fablit.application import (
    DEMO_LEARNER_ID,
    ArtifactRef,
    DemoActivity,
    FileArtifactStorage,
    LearnerJourneyStore,
    PracticeApplication,
    SketchbookArtifact,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
    build_stimulus_provider,
)
from fablit.application.demo_evaluator import DemoEvaluator
from fablit.application.persistence import (
    PersistenceError,
    StoredPracticeCompletion,
)
from fablit.application.repositories import InMemoryPracticeHistoryRepository
from fablit.application.store import DemoActivity as _DemoActivity
from fablit.domain import (
    ActivityStatus,
    ActivityType,
    AssessmentActivity,
)

LEARNER = DEMO_LEARNER_ID

#: Minimal payloads that pass signature detection for each supported format.
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-body"
JPEG_BYTES = b"\xff\xd8\xff\xdb" + b"fake-jpeg-body"
WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"fake-webp-body"


def _sketch(
    *,
    learner_id: UUID = LEARNER,
    activity_id: UUID,
    filename: str = "sketch.png",
    content_type: str | None = None,
    data: bytes = PNG_BYTES,
) -> SketchbookArtifact:
    return SketchbookArtifact.from_upload(
        learner_id=learner_id,
        activity_id=activity_id,
        filename=filename,
        content_type=content_type,
        data=data,
    )


def _application(
    tmp_path: Path,
    *,
    repository: InMemoryPracticeHistoryRepository | None = None,
    activities: tuple[DemoActivity, ...] | None = None,
) -> PracticeApplication:
    repository = repository or InMemoryPracticeHistoryRepository()
    storage = FileArtifactStorage(str(tmp_path / "artifacts"))
    activities = activities or build_demo_activities()
    return PracticeApplication(
        store=LearnerJourneyStore(
            learner_id=LEARNER,
            activities=activities,
            skills=build_demo_skills(),
        ),
        evaluator=DemoEvaluator(build_demo_activity_map(activities)),
        stimulus_provider=build_stimulus_provider(activities, provider_name="builtin"),
        history_repository=repository,
        artifact_storage=storage,
    )


def _reflection_activity_id(activities: tuple[DemoActivity, ...]) -> UUID:
    for item in activities:
        if item.activity.activity_type is ActivityType.REFLECTION:
            return item.activity.id
    raise AssertionError("demo content has no reflection activity")


def _reflection_activity_id_from_store(application: PracticeApplication) -> UUID:
    """Return the reflection activity identity from the application's store."""
    return _reflection_activity_id(application._store.list_activities())


# ---------------------------------------------------------------------------
# MIME / signature consistency — the detected type is authoritative
# ---------------------------------------------------------------------------


def test_detected_type_is_stored_content_type() -> None:
    """The content_type stored on the artifact is the detected image format."""
    artifact = _sketch(activity_id=uuid4(), filename="sketch.png")
    assert artifact.content_type == "image/png"


def test_png_signature_is_detected_as_image_png() -> None:
    artifact = _sketch(activity_id=uuid4(), data=PNG_BYTES)
    assert artifact.content_type == "image/png"


def test_jpeg_signature_is_detected_as_image_jpeg() -> None:
    artifact = _sketch(activity_id=uuid4(), filename="sketch.jpg", data=JPEG_BYTES)
    assert artifact.content_type == "image/jpeg"


def test_webp_signature_is_detected_as_image_webp() -> None:
    artifact = _sketch(
        activity_id=uuid4(),
        filename="sketch.webp",
        content_type="image/webp",
        data=WEBP_BYTES,
    )
    assert artifact.content_type == "image/webp"


def test_wrong_extension_is_rejected_even_when_bytes_are_valid() -> None:
    """A valid PNG uploaded with a non-image extension is rejected."""
    with pytest.raises(ValueError, match="Please upload a PNG, JPG, or WebP image."):
        _sketch(activity_id=uuid4(), filename="sketch.txt", data=PNG_BYTES)


def test_mismatched_extension_is_rejected_even_when_bytes_are_valid() -> None:
    """A valid JPEG uploaded under a PNG extension is rejected."""
    with pytest.raises(ValueError, match="Please upload a PNG, JPG, or WebP image."):
        _sketch(activity_id=uuid4(), filename="sketch.png", data=JPEG_BYTES)


def test_mismatched_declared_content_type_is_rejected() -> None:
    """A valid PNG uploaded with a JPEG content_type is rejected."""
    with pytest.raises(ValueError, match="Please upload a PNG, JPG, or WebP image."):
        _sketch(
            activity_id=uuid4(),
            filename="sketch.png",
            content_type="image/jpeg",
            data=PNG_BYTES,
        )


def test_unsupported_declared_content_type_is_rejected_before_byte_inspection() -> None:
    """An unsupported declared MIME is rejected with the formats message."""
    with pytest.raises(ValueError, match="Please upload a PNG, JPG, or WebP image."):
        _sketch(
            activity_id=uuid4(),
            filename="sketch.gif",
            content_type="image/gif",
            data=PNG_BYTES,
        )


def test_empty_upload_is_rejected() -> None:
    with pytest.raises(ValueError, match="Please choose an image to upload."):
        _sketch(activity_id=uuid4(), data=b"")


def test_oversized_upload_is_rejected() -> None:
    big = b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="5MB or smaller"):
        _sketch(activity_id=uuid4(), data=big)


def test_unrecognised_image_is_rejected() -> None:
    with pytest.raises(ValueError, match="could not be read"):
        _sketch(activity_id=uuid4(), data=b"not an image")


# ---------------------------------------------------------------------------
# Retry-safe staging — the pending artifact survives until durable persistence
# ---------------------------------------------------------------------------


def test_pending_artifact_survives_a_failed_durable_write_and_is_retryable(
    tmp_path: Path,
) -> None:
    """A failed durable write leaves the pending sketch intact for a retry."""
    repository = InMemoryPracticeHistoryRepository()
    application = _application(tmp_path, repository=repository)
    activity_id = _reflection_activity_id_from_store(application)

    sketch = _sketch(activity_id=activity_id)
    application.submit_response(activity_id, "A response.", artifact=sketch)

    original_save = repository.save_completion

    def failing_save(
        *,
        learner_id: UUID,
        activity_id: UUID,
        activity_title: str,
        submission: object,
        evaluation: object,
        feedback: object,
        reflection: object,
        stimulus: object | None,
        artifact: ArtifactRef | None = None,
    ) -> StoredPracticeCompletion:
        raise PersistenceError("durable write failed")

    repository.save_completion = failing_save  # type: ignore[assignment]

    with pytest.raises(PersistenceError):
        application.submit_reflection("I noticed the line weight.")

    # The pending artifact must still be available for a retry.
    pending = application._store.pending_artifact(activity_id)
    assert pending is not None
    assert pending.artifact_id == sketch.artifact_id

    # Retry succeeds once the durable write is healthy again.
    repository.save_completion = original_save  # type: ignore[method-assign]
    view = application.submit_reflection("I noticed the line weight.")

    assert "completed this practice" in view.message
    stored = repository.get_completion(
        LEARNER, repository.list_completions(LEARNER)[0].completion_id
    )
    assert stored is not None
    assert stored.artifact is not None
    assert stored.artifact.artifact_id == sketch.artifact_id
    assert application.get_artifact_bytes(stored.artifact.artifact_id) == sketch.data


def test_pending_artifact_is_discarded_when_reflection_is_skipped(
    tmp_path: Path,
) -> None:
    """Skipping the reflection must not leave the sketch pending or stored."""
    repository = InMemoryPracticeHistoryRepository()
    application = _application(tmp_path, repository=repository)
    activity_id = _reflection_activity_id_from_store(application)

    sketch = _sketch(activity_id=activity_id)
    application.submit_response(activity_id, "A response.", artifact=sketch)
    application.submit_reflection(None)

    assert application._store.pending_artifact(activity_id) is None
    assert repository.list_completions(LEARNER) == ()


def _demo_activity(title: str, activity_id: UUID | None = None) -> _DemoActivity:
    """Build a minimal demo activity whose domain activity has a stable identity."""
    return _DemoActivity(
        activity=AssessmentActivity(
            activity_type=ActivityType.REFLECTION,
            instructions=title,
            position=0,
            id=activity_id or uuid4(),
            status=ActivityStatus.ACTIVE,
        ),
        title=title,
        description="d",
        strength="s",
        improvement="i",
        next_step="n",
    )


def test_pending_artifact_is_not_visible_to_a_different_learner_identity() -> None:
    """Pending sketches are learner-scoped and must not leak across identities."""
    activity_id = uuid4()
    store = LearnerJourneyStore(
        learner_id=LEARNER,
        activities=(_demo_activity("t", activity_id),),
        skills=(),
    )
    sketch = _sketch(learner_id=LEARNER, activity_id=activity_id)
    store.save_pending_artifact(activity_id, sketch)

    other_learner = uuid4()
    other_store = LearnerJourneyStore(
        learner_id=other_learner,
        activities=store.list_activities(),
        skills=(),
    )
    assert other_store.pending_artifact(activity_id) is None


def test_pending_artifact_is_consumed_only_by_the_pending_activity_key() -> None:
    """Pending sketches are keyed by activity, not globally consumed."""
    activity_a = uuid4()
    activity_b = uuid4()
    store = LearnerJourneyStore(
        learner_id=LEARNER,
        activities=(
            _demo_activity("a", activity_a),
            _demo_activity("b", activity_b),
        ),
        skills=(),
    )
    sketch_a = _sketch(learner_id=LEARNER, activity_id=activity_a)
    sketch_b = _sketch(learner_id=LEARNER, activity_id=activity_b)
    store.save_pending_artifact(activity_a, sketch_a)
    store.save_pending_artifact(activity_b, sketch_b)

    assert store.pending_artifact(activity_a) is not None
    assert store.pending_artifact(activity_b) is not None
    taken_a = store.take_pending_artifact(activity_a)
    assert taken_a is not None
    assert taken_a.artifact_id == sketch_a.artifact_id
    assert store.pending_artifact(activity_a) is None
    assert store.pending_artifact(activity_b) is not None


# ---------------------------------------------------------------------------
# Corruption / rollback isolation — failed writes do not strand media
# ---------------------------------------------------------------------------


def test_failed_durable_write_does_not_leave_staged_bytes_on_disk(
    tmp_path: Path,
) -> None:
    """A failed write must roll staged bytes back so no orphan media remains."""
    repository = InMemoryPracticeHistoryRepository()
    application = _application(tmp_path, repository=repository)
    activity_id = _reflection_activity_id_from_store(application)

    sketch = _sketch(activity_id=activity_id)
    application.submit_response(activity_id, "A response.", artifact=sketch)

    stored_ref = sketch.as_ref()
    application._artifact_storage.save(stored_ref, sketch.data)

    original_save = repository.save_completion

    def failing_save(
        *,
        learner_id: UUID,
        activity_id: UUID,
        activity_title: str,
        submission: object,
        evaluation: object,
        feedback: object,
        reflection: object,
        stimulus: object | None,
        artifact: ArtifactRef | None = None,
    ) -> StoredPracticeCompletion:
        raise PersistenceError("durable write failed")

    repository.save_completion = failing_save  # type: ignore[assignment]

    with pytest.raises(PersistenceError):
        application.submit_reflection("I noticed the line weight.")

    # Staged bytes must have been rolled back.
    assert application._artifact_storage.get(stored_ref.artifact_id) is None
    # The pending artifact remains so a retry can re-stage it.
    pending = application._store.pending_artifact(activity_id)
    assert pending is not None

    # Restore the healthy save path so later tests in this process are not broken.
    repository.save_completion = original_save  # type: ignore[method-assign]


def test_stored_artifact_bytes_match_the_uploaded_bytes(tmp_path: Path) -> None:
    """A completed practice must store and retrieve the exact uploaded bytes."""
    repository = InMemoryPracticeHistoryRepository()
    application = _application(tmp_path, repository=repository)
    activity_id = _reflection_activity_id_from_store(application)

    sketch = _sketch(activity_id=activity_id, filename="field-sketch.png")
    application.submit_response(activity_id, "A response.", artifact=sketch)
    application.submit_reflection("I noticed where the line weight broke down.")

    stored = repository.get_completion(
        LEARNER, repository.list_completions(LEARNER)[0].completion_id
    )
    assert stored is not None
    assert stored.artifact is not None
    assert stored.artifact.filename == "field-sketch.png"
    assert stored.artifact.content_type == "image/png"
    assert stored.artifact.size_bytes == len(sketch.data)
    assert application.get_artifact_bytes(stored.artifact.artifact_id) == sketch.data


def test_two_different_artifacts_keep_separate_identities_and_bytes(
    tmp_path: Path,
) -> None:
    """Different sketches completed in separate practice instances must not
    overwrite each other in storage.

    Pending artifacts are keyed by the activity instance, so two sketches
    uploaded while working on the *same* activity instance collide in the
    pending store. To exercise truly separate stored artifacts we complete two
    separate reflection practice instances, each with its own sketch, against
    the same shared repository and artifact storage.
    """
    repository = InMemoryPracticeHistoryRepository()
    activities = build_demo_activities()
    reflection_id = _reflection_activity_id(activities)

    # Build two separate practice applications, each with its own store, so the
    # two completions cannot share a pending-artifact key.
    first_app = _application(tmp_path, repository=repository, activities=activities)
    second_app = _application(tmp_path, repository=repository, activities=activities)

    first_sketch = _sketch(activity_id=reflection_id, filename="first.png")
    second_sketch = _sketch(activity_id=reflection_id, filename="second.png")

    first_app.submit_response(reflection_id, "First response.", artifact=first_sketch)
    first_app.submit_reflection("First reflection.")

    second_app.submit_response(
        reflection_id, "Second response.", artifact=second_sketch
    )
    second_app.submit_reflection("Second reflection.")

    # Both completions are now in the shared repository. The repository lists
    # newest-first, so index 0 is the second (newer) completion and index 1 is
    # the first (older) completion.
    all_completions = repository.list_completions(LEARNER)
    assert len(all_completions) == 2, (
        f"expected 2 completions, got {len(all_completions)}"
    )
    second_completion_id = all_completions[0].completion_id
    first_completion_id = all_completions[1].completion_id
    assert second_completion_id != first_completion_id, (
        "the two completions must have distinct identities"
    )

    first_stored = repository.get_completion(LEARNER, first_completion_id)
    second_stored = repository.get_completion(LEARNER, second_completion_id)
    assert first_stored is not None
    assert second_stored is not None
    assert first_stored.artifact is not None
    assert second_stored.artifact is not None

    # The meaningful invariant is that each completed practice can retrieve the
    # bytes that were uploaded for it. If the two artifact identities happen to
    # collide, one of these assertions will fail, which is the correct outcome.
    assert (
        first_app.get_artifact_bytes(first_stored.artifact.artifact_id)
        == first_sketch.data
    ), "first completion must retrieve its own uploaded bytes"
    assert (
        second_app.get_artifact_bytes(second_stored.artifact.artifact_id)
        == second_sketch.data
    ), "second completion must retrieve its own uploaded bytes"

    # Two genuinely different sketches should not share the same stored artifact
    # identity. Reject the collision case explicitly so the test is
    # deterministic about the property it is protecting.
    assert first_stored.artifact.artifact_id != second_stored.artifact.artifact_id
