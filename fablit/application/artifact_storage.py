"""Private sketchbook artifact storage behind the application boundary (SPEC-033).

The binary payload of a learner's sketchbook image is never carried inside the
learner-journey history records. History stores only artifact metadata/ref, and
the bytes live behind this private file-backed boundary. Retrieval is
learner-scoped and unlisted: callers obtain a :class:`ArtifactRef`, then call
``storage.get(ref.artifact_id)``.

The boundary is deliberately small and file-backed because the current
deployment has no object storage. If object storage is introduced later, only
the concrete implementation of :class:`ArtifactStorage` changes here; every
caller still talks to the interface.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class ArtifactStorageError(Exception):
    """Base exception for artifact-storage failures."""


@dataclass(frozen=True)
class ArtifactRef:
    """Opaque metadata reference to a private sketchbook artifact.

    The ref is learner-scoped by construction: every field is fixed at save
    time and never changes. It is the only handle a caller may keep, which is
    what allows storage internals to move (here: file paths, later object
    storage) without redesigning the application layer.
    """

    artifact_id: UUID
    learner_id: UUID
    activity_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    created_at: datetime

    @property
    def image_url(self) -> str:
        """Learner-scoped URL for the artifact in the review view."""
        return f"/history/{self.artifact_id}/artifact"


class ArtifactStorage(ABC):
    """Persistence boundary for private sketchbook artifact bytes."""

    @abstractmethod
    def save(self, ref: ArtifactRef, data: bytes) -> None:
        """Persist artifact bytes under an opaque key."""

    @abstractmethod
    def get(self, artifact_id: UUID) -> bytes | None:
        """Return artifact bytes, or None when the artifact is missing."""

    @abstractmethod
    def delete(self, artifact_id: UUID) -> None:
        """Remove artifact bytes."""


class FileArtifactStorage(ArtifactStorage):
    """Private, file-backed artifact storage for the current deployment.

    Keys are opaque artifact ids so callers never learn the on-disk layout.
    The base directory is private to the deployment and is created on demand.
    """

    def __init__(self, base_dir: str = "/private/artifacts") -> None:
        self._base_dir = base_dir
        os.makedirs(self._base_dir, exist_ok=True)

    def save(self, ref: ArtifactRef, data: bytes) -> None:
        path = os.path.join(self._base_dir, str(ref.artifact_id))
        with open(path, "wb") as handle:
            handle.write(data)

    def get(self, artifact_id: UUID) -> bytes | None:
        path = os.path.join(self._base_dir, str(artifact_id))
        try:
            with open(path, "rb") as handle:
                return handle.read()
        except FileNotFoundError:
            return None

    def delete(self, artifact_id: UUID) -> None:
        path = os.path.join(self._base_dir, str(artifact_id))
        from contextlib import suppress

        with suppress(FileNotFoundError):
            os.remove(path)
