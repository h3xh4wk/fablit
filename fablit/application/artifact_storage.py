"""Private sketchbook artifact storage behind the application boundary (SPEC-033).

The binary payload of a learner's sketchbook image is never carried inside the
learner-journey history records. History stores only the metadata reference
(:class:`~fablit.application.artifacts.ArtifactRef`), and the bytes live behind
this private, file-backed boundary. Retrieval is learner-scoped and unlisted:
callers obtain a reference from their own completion, then ask storage for the
bytes keyed by the artifact identity.

The boundary is deliberately small and file-backed because the current
deployment has no object storage. If object storage is introduced later, only
the concrete implementation of :class:`ArtifactStorage` changes here; every
caller still talks to the interface.
"""

from __future__ import annotations

import os
import tempfile
from abc import ABC, abstractmethod
from contextlib import suppress
from uuid import UUID

from .artifacts import ArtifactRef

#: Environment variable selecting the private artifact directory for the
#: deployment. Unset falls back to a process-private directory under the
#: system temp location, which keeps local development and tests working
#: without requiring a writable ``/private`` mount.
ARTIFACT_STORAGE_DIR_ENV = "FABLIT_ARTIFACT_STORAGE_DIR"


def default_artifact_storage_dir() -> str:
    """Resolve the default private artifact directory for this process."""
    configured = os.environ.get(ARTIFACT_STORAGE_DIR_ENV)
    if configured and configured.strip():
        return configured
    return os.path.join(tempfile.gettempdir(), "fablit-artifacts")


class ArtifactStorageError(Exception):
    """Base exception for artifact-storage failures."""


class ArtifactStorage(ABC):
    """Persistence boundary for private sketchbook artifact bytes.

    Storage is keyed by the artifact identity alone, so the on-disk layout
    stays an implementation detail and callers never learn or guess a path.
    """

    @abstractmethod
    def save(self, ref: ArtifactRef, data: bytes) -> None:
        """Persist artifact bytes under the artifact's opaque key."""

    @abstractmethod
    def get(self, artifact_id: UUID) -> bytes | None:
        """Return artifact bytes, or None when the artifact is missing."""

    @abstractmethod
    def delete(self, artifact_id: UUID) -> None:
        """Remove artifact bytes. Missing artifacts are ignored."""


class FileArtifactStorage(ArtifactStorage):
    """Private, file-backed artifact storage for the current deployment.

    Files are named by the opaque artifact id inside a base directory that is
    private to the deployment. The directory is created lazily on the first
    write so constructing the storage never depends on mount permissions.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = base_dir or default_artifact_storage_dir()

    @property
    def base_dir(self) -> str:
        """The configured private base directory (never learner-facing)."""
        return self._base_dir

    def _path(self, artifact_id: UUID) -> str:
        return os.path.join(self._base_dir, str(artifact_id))

    def save(self, ref: ArtifactRef, data: bytes) -> None:
        os.makedirs(self._base_dir, exist_ok=True)
        with open(self._path(ref.artifact_id), "wb") as handle:
            handle.write(data)

    def get(self, artifact_id: UUID) -> bytes | None:
        try:
            with open(self._path(artifact_id), "rb") as handle:
                return handle.read()
        except FileNotFoundError:
            return None

    def delete(self, artifact_id: UUID) -> None:
        with suppress(FileNotFoundError):
            os.remove(self._path(artifact_id))
