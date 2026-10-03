"""Private sketchbook artifact handling for the sketchbook reflection practice.

The artifact is intentionally scoped to the learner's private practice journey and
is never treated as a public gallery or a general media library. The application
layer validates the uploaded bytes before storing them in the learner-scoped
history record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import UUID, uuid4

MAX_SKETCHBOOK_ARTIFACT_BYTES = 5 * 1024 * 1024
SUPPORTED_SKETCHBOOK_ARTIFACT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}


@dataclass(frozen=True)
class ArtifactRef:
    """Metadata-only reference to a private sketchbook artifact (SPEC-033).

    This is the *only* artifact handle that durable practice-history records
    may carry: the binary payload lives behind the artifact-storage boundary
    (``artifact_storage.py``). The reference is learner-scoped by construction
    and its fields are fixed at save time, so history records stay small and
    the private bytes never enter learner-journey history storage.
    """

    artifact_id: UUID
    learner_id: UUID
    activity_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


@dataclass(frozen=True)
class SketchbookArtifact:
    """Private sketch image stored by a learner for one reflection practice."""

    learner_id: UUID
    activity_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    data: bytes
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    artifact_id: UUID = field(default_factory=uuid4)

    @classmethod
    def from_upload(
        cls,
        *,
        learner_id: UUID,
        activity_id: UUID,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> SketchbookArtifact:
        """Validate uploaded bytes and construct a private sketch artifact."""
        if not data:
            raise ValueError("Please choose an image to upload.")
        if len(data) > MAX_SKETCHBOOK_ARTIFACT_BYTES:
            raise ValueError(
                "Sketch uploads must be 5MB or smaller. Please choose a smaller image."
            )

        resolved_type = (content_type or "").lower()
        if resolved_type and resolved_type not in SUPPORTED_SKETCHBOOK_ARTIFACT_TYPES:
            raise ValueError("Please upload a PNG, JPG, or WebP image.")

        safe_name = (filename or "sketch.png").strip() or "sketch.png"
        extension = PurePosixPath(safe_name).suffix.lower()
        if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("Please upload a PNG, JPG, or WebP image.")

        if not _looks_like_supported_image(data):
            raise ValueError(
                "The uploaded image could not be read. Please try another file."
            )

        return cls(
            learner_id=learner_id,
            activity_id=activity_id,
            filename=safe_name,
            content_type=resolved_type or _infer_content_type(extension),
            size_bytes=len(data),
            data=data,
        )

    def as_ref(self) -> ArtifactRef:
        """Return the metadata-only reference persisted with history (SPEC-033).

        The reference deliberately excludes ``data``: only the artifact-storage
        boundary ever holds the private bytes.
        """
        return ArtifactRef(
            artifact_id=self.artifact_id,
            learner_id=self.learner_id,
            activity_id=self.activity_id,
            filename=self.filename,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            created_at=self.created_at,
        )


def _looks_like_supported_image(data: bytes) -> bool:
    """Validate the first bytes so the upload is not a disguised file."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if data.startswith(b"\xff\xd8\xff"):
        return True
    if data.startswith((b"GIF87a", b"GIF89a")):
        return True
    return data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP"


def _infer_content_type(extension: str) -> str:
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    return mapping.get(extension, "image/png")
