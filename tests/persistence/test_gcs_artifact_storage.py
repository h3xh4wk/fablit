"""Unit tests for the Google Cloud Storage artifact adapter (SPEC-034).

Covers GCS artifact storage adapter contract, save/get/delete behaviour,
content metadata preservation, storage error mapping, missing object handling,
and retry-safe lifecycle integration (SPEC-034 §15).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from fablit.application import (
    DEMO_LEARNER_ID,
    ArtifactRef,
    ArtifactStorage,
    ArtifactStorageError,
    DemoEvaluator,
    LearnerJourneyStore,
    PracticeApplication,
    SketchbookArtifact,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
    build_stimulus_provider,
)
from fablit.application.repositories import InMemoryPracticeHistoryRepository
from fablit.domain import ActivityType
from fablit.platform.gcs_artifact_storage import GCSArtifactStorage

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class FakeNotFound(Exception):
    """Fake 404 exception mirroring google.cloud.exceptions.NotFound."""

    pass


class FakeBlob:
    """Fake GCS Blob emulating google.cloud.storage.blob.Blob."""

    def __init__(self, name: str, bucket: FakeBucket) -> None:
        self.name = name
        self.bucket = bucket
        self.data: bytes | None = None
        self.content_type: str | None = None
        self.metadata: dict[str, str] = {}
        self._exists = False

    def upload_from_string(
        self,
        data: bytes,
        content_type: str | None = None,
    ) -> None:
        if self.bucket._fail_upload:
            raise RuntimeError("GCS upload simulated network failure")
        self.data = data
        self.content_type = content_type
        self._exists = True
        self.bucket._blobs[self.name] = self

    def download_as_bytes(self) -> bytes:
        if self.bucket._fail_download:
            raise RuntimeError("GCS download simulated network failure")
        if not self._exists or self.data is None:
            raise FakeNotFound(f"Blob {self.name} not found")
        return self.data

    def exists(self) -> bool:
        if self.bucket._fail_exists:
            raise RuntimeError("GCS exists check simulated network failure")
        return self._exists

    def delete(self) -> None:
        if self.bucket._fail_delete:
            raise RuntimeError("GCS delete simulated network failure")
        if not self._exists:
            raise FakeNotFound(f"Blob {self.name} not found")
        self._exists = False
        self.bucket._blobs.pop(self.name, None)


class FakeBucket:
    """Fake GCS Bucket emulating google.cloud.storage.bucket.Bucket."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._blobs: dict[str, FakeBlob] = {}
        self._fail_upload = False
        self._fail_download = False
        self._fail_exists = False
        self._fail_delete = False

    def blob(self, blob_name: str) -> FakeBlob:
        if blob_name in self._blobs:
            return self._blobs[blob_name]
        return FakeBlob(blob_name, self)


class FakeStorageClient:
    """Fake GCS Client emulating google.cloud.storage.Client."""

    def __init__(self) -> None:
        self._buckets: dict[str, FakeBucket] = {}
        self.project = "test-fablit-project"

    def bucket(self, bucket_name: str) -> FakeBucket:
        if bucket_name not in self._buckets:
            self._buckets[bucket_name] = FakeBucket(bucket_name)
        return self._buckets[bucket_name]


def make_ref(
    *,
    artifact_id: UUID | None = None,
    filename: str = "sketch.png",
    content_type: str = "image/png",
    size_bytes: int = 4,
) -> ArtifactRef:
    """Build an artifact reference with test defaults."""
    return ArtifactRef(
        artifact_id=artifact_id or uuid4(),
        learner_id=uuid4(),
        activity_id=uuid4(),
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


# --- GCS Adapter Direct Contract Tests ---------------------------------------


def test_init_validates_bucket_name() -> None:
    client = FakeStorageClient()

    with pytest.raises(ValueError, match="non-empty GCS bucket name"):
        GCSArtifactStorage("", client=client)

    with pytest.raises(ValueError, match="non-empty GCS bucket name"):
        GCSArtifactStorage("   ", client=client)


def test_implements_artifact_storage_boundary() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("my-bucket", client=client)

    assert isinstance(storage, ArtifactStorage)
    assert storage.bucket_name == "my-bucket"
    assert storage.prefix == ""
    assert storage.client is client


def test_save_then_get_round_trip() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)
    ref = make_ref()

    storage.save(ref, b"binary-data")

    assert storage.get(ref.artifact_id) == b"binary-data"


def test_save_preserves_content_type_and_metadata() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)
    ref = make_ref(filename="artwork.webp", content_type="image/webp", size_bytes=10)

    storage.save(ref, b"0123456789")

    bucket = client.bucket("test-bucket")
    blob = bucket.blob(str(ref.artifact_id))
    assert blob.content_type == "image/webp"
    assert blob.metadata == {
        "artifact_id": str(ref.artifact_id),
        "filename": "artwork.webp",
    }


def test_get_missing_artifact_returns_none() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)

    assert storage.get(uuid4()) is None


def test_get_handles_not_found_exception() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)

    bucket = client.bucket("test-bucket")
    missing_id = uuid4()
    blob = bucket.blob(str(missing_id))
    # exists() returns True (simulating race condition where object was
    # removed before download)
    blob.exists = lambda: True  # type: ignore[method-assign]

    assert storage.get(missing_id) is None


def test_delete_removes_artifact_bytes() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)
    ref = make_ref()
    storage.save(ref, b"to-delete")

    storage.delete(ref.artifact_id)

    assert storage.get(ref.artifact_id) is None


def test_delete_missing_artifact_is_ignored() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)

    # Deleting an absent artifact must be a clean no-op
    storage.delete(uuid4())


def test_save_is_idempotent_and_overwrites() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)
    artifact_id = uuid4()
    first = make_ref(artifact_id=artifact_id, filename="draft.png")
    second = make_ref(artifact_id=artifact_id, filename="final.png")

    storage.save(first, b"draft-bytes")
    storage.save(second, b"final-bytes")

    assert storage.get(artifact_id) == b"final-bytes"


def test_prefix_configuration_prepends_to_blob_name() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage(
        "test-bucket", client=client, prefix="fablit-artifacts/"
    )
    ref = make_ref()

    storage.save(ref, b"prefixed-data")

    bucket = client.bucket("test-bucket")
    expected_blob_name = f"fablit-artifacts/{ref.artifact_id}"
    assert expected_blob_name in bucket._blobs
    assert storage.get(ref.artifact_id) == b"prefixed-data"


def test_save_failure_raises_artifact_storage_error() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)
    client.bucket("test-bucket")._fail_upload = True
    ref = make_ref()

    with pytest.raises(ArtifactStorageError, match="Failed to save artifact"):
        storage.save(ref, b"data")


def test_get_unexpected_failure_raises_artifact_storage_error() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)
    ref = make_ref()
    storage.save(ref, b"data")

    client.bucket("test-bucket")._fail_download = True

    with pytest.raises(ArtifactStorageError, match="Failed to retrieve artifact"):
        storage.get(ref.artifact_id)


def test_delete_unexpected_failure_is_handled_gracefully() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)
    ref = make_ref()
    storage.save(ref, b"data")

    client.bucket("test-bucket")._fail_delete = True

    # Delete logs a warning and suppresses the error to avoid breaking cleanup
    storage.delete(ref.artifact_id)


# --- Application Integration & Retry-Safety Tests -----------------------------


def _make_application(
    storage: ArtifactStorage,
    history_repository: InMemoryPracticeHistoryRepository | None = None,
) -> tuple[PracticeApplication, UUID]:
    activities = build_demo_activities()
    skills = build_demo_skills()
    store = LearnerJourneyStore(
        learner_id=DEMO_LEARNER_ID,
        activities=activities,
        skills=skills,
    )
    history = history_repository or InMemoryPracticeHistoryRepository()

    app = PracticeApplication(
        store=store,
        evaluator=DemoEvaluator(build_demo_activity_map(activities)),
        stimulus_provider=build_stimulus_provider(activities, provider_name="builtin"),
        history_repository=history,
        artifact_storage=storage,
    )

    reflection_act_id = next(
        a.activity.id
        for a in activities
        if a.activity.activity_type is ActivityType.REFLECTION
    )
    return app, reflection_act_id


def _make_sketch(activity_id: UUID, filename: str = "sketch.png") -> SketchbookArtifact:
    return SketchbookArtifact.from_upload(
        learner_id=DEMO_LEARNER_ID,
        activity_id=activity_id,
        filename=filename,
        content_type="image/png",
        data=PNG_BYTES,
    )


def test_application_persists_artifact_to_gcs_and_retrieves_bytes() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)
    history = InMemoryPracticeHistoryRepository()
    app, activity_id = _make_application(storage, history)

    sketch = _make_sketch(activity_id, filename="my-sketch.png")
    app.submit_response(activity_id, "Response with sketch", artifact=sketch)
    app.submit_reflection("My reflection on the drawing.")

    completions = history.list_completions(DEMO_LEARNER_ID)
    assert len(completions) == 1
    completion_id = completions[0].completion_id

    review = app.get_practice_review(completion_id)
    assert review.artifact is not None
    assert review.artifact.artifact_id == sketch.artifact_id

    # Raw bytes are read back from GCS
    bytes_back = app.get_artifact_bytes(sketch.artifact_id)
    assert bytes_back == PNG_BYTES


def test_application_rolls_back_gcs_artifact_on_history_save_failure() -> None:
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)

    class FailingHistoryRepository(InMemoryPracticeHistoryRepository):
        def save_completion(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("Simulated Datastore failure")

    app, activity_id = _make_application(storage, FailingHistoryRepository())

    sketch = _make_sketch(activity_id, filename="rollback-sketch.png")
    app.submit_response(activity_id, "Response with sketch", artifact=sketch)

    with pytest.raises(RuntimeError, match="Simulated Datastore failure"):
        app.submit_reflection("Reflection that fails to save.")

    # FIX-3: staged bytes in GCS are deleted on durable write failure
    assert storage.get(sketch.artifact_id) is None


def test_missing_gcs_artifact_degrades_gracefully_during_review() -> None:
    """AC-034-10: Review renders normally when artifact bytes are unavailable."""
    client = FakeStorageClient()
    storage = GCSArtifactStorage("test-bucket", client=client)
    history = InMemoryPracticeHistoryRepository()
    app, activity_id = _make_application(storage, history)

    sketch = _make_sketch(activity_id, filename="lost-sketch.png")
    app.submit_response(activity_id, "Response with sketch", artifact=sketch)
    app.submit_reflection("Reflection on lost sketch.")

    # Simulate missing artifact in GCS (e.g. deleted or unmigrated legacy artifact)
    storage.delete(sketch.artifact_id)
    assert storage.get(sketch.artifact_id) is None

    completions = history.list_completions(DEMO_LEARNER_ID)
    completion_id = completions[0].completion_id

    # The review still reconstructs the entire written history
    review = app.get_practice_review(completion_id)
    assert review.learner_response == "Response with sketch"
    assert review.reflection == "Reflection on lost sketch."
    # The reference is present in the review view model so the UI can attempt to render
    assert review.artifact is not None
    # But getting the raw bytes returns None
    assert app.get_artifact_bytes(sketch.artifact_id) is None
