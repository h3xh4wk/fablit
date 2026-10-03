"""Tests for the private sketchbook artifact-storage boundary (SPEC-033).

The boundary is what keeps the private binary payload out of durable
practice-history records: callers hold only an ``ArtifactRef`` and read the
bytes back through the opaque artifact identity.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from fablit.application import ArtifactRef, FileArtifactStorage
from fablit.application.artifact_storage import (
    ARTIFACT_STORAGE_DIR_ENV,
    ArtifactStorage,
    default_artifact_storage_dir,
)


def make_ref(
    *,
    artifact_id: UUID | None = None,
    filename: str = "sketch.png",
    content_type: str = "image/png",
) -> ArtifactRef:
    """Build an artifact reference with sensible defaults."""
    return ArtifactRef(
        artifact_id=artifact_id or uuid4(),
        learner_id=uuid4(),
        activity_id=uuid4(),
        filename=filename,
        content_type=content_type,
        size_bytes=4,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def make_storage(tmp_path: Path) -> ArtifactStorage:
    """Build a file-backed storage rooted inside the test's temp directory."""
    return FileArtifactStorage(str(tmp_path / "artifacts"))


def test_save_then_get_round_trips_the_bytes(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)
    ref = make_ref()

    storage.save(ref, b"PNGD")

    assert storage.get(ref.artifact_id) == b"PNGD"


def test_get_missing_artifact_returns_none(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)

    assert storage.get(uuid4()) is None


def test_delete_removes_bytes(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)
    ref = make_ref()
    storage.save(ref, b"data")

    storage.delete(ref.artifact_id)

    assert storage.get(ref.artifact_id) is None


def test_delete_missing_artifact_is_ignored(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)

    # Deleting an already-absent artifact must not raise.
    storage.delete(uuid4())


def test_storage_is_keyed_by_the_opaque_artifact_id(tmp_path: Path) -> None:
    """The artifact identity alone addresses the stored bytes."""
    storage = make_storage(tmp_path)
    artifact_id = uuid4()
    first = make_ref(artifact_id=artifact_id, filename="first.png")
    second = make_ref(artifact_id=artifact_id, filename="second.png")

    storage.save(first, b"first-bytes")
    storage.save(second, b"second-bytes")

    # Same identity → same stored object; the newer write is what remains.
    assert storage.get(artifact_id) == b"second-bytes"


def test_directory_is_created_lazily_on_save(tmp_path: Path) -> None:
    base_dir = tmp_path / "not-yet-created"
    storage = FileArtifactStorage(str(base_dir))

    assert not base_dir.exists()
    storage.save(make_ref(), b"x")
    assert base_dir.exists()


def test_default_dir_uses_the_environment_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configured = str(tmp_path / "private")
    monkeypatch.setenv(ARTIFACT_STORAGE_DIR_ENV, configured)

    assert default_artifact_storage_dir() == configured
    assert FileArtifactStorage().base_dir == configured


def test_default_dir_falls_back_to_a_temp_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ARTIFACT_STORAGE_DIR_ENV, raising=False)

    assert default_artifact_storage_dir().endswith("fablit-artifacts")


def test_blank_environment_override_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ARTIFACT_STORAGE_DIR_ENV, "   ")

    assert default_artifact_storage_dir().endswith("fablit-artifacts")


def test_file_storage_implements_the_boundary(tmp_path: Path) -> None:
    assert isinstance(make_storage(tmp_path), ArtifactStorage)


def test_artifact_storage_error_is_raised_from_the_boundary_module() -> None:
    """The boundary owns its error type for future storage backends."""
    from fablit.application import ArtifactStorageError

    assert issubclass(ArtifactStorageError, Exception)


def test_get_is_repeatable(tmp_path: Path) -> None:
    """Reading the same artifact twice returns identical bytes."""
    storage = make_storage(tmp_path)
    ref = make_ref()
    storage.save(ref, b"stable")

    assert storage.get(ref.artifact_id) == storage.get(ref.artifact_id)
