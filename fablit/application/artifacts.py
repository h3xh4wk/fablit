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

#: Signature → effective content type. The bytes are the source of truth for
#: what an upload actually is, so nothing supported can be stored or served
#: under a media type that disagrees with its payload.
_IMAGE_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)

#: Filename extension → content type (both JPEG spellings map to image/jpeg).
_EXTENSION_CONTENT_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def detect_image_type(data: bytes) -> str | None:
    """Return the content type of supported sketch bytes, or ``None``.

    Detection is based on the file signature rather than the declared MIME
    type or filename, so a mislabelled or disguised upload cannot claim a
    media type its bytes do not match.
    """
    for signature, content_type in _IMAGE_SIGNATURES:
        if data.startswith(signature):
            return content_type
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    return None


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
        """Validate uploaded bytes and construct a private sketch artifact.

        The image format detected from the bytes is authoritative, and the
        stored ``content_type`` is always that detected type. Any declared
        media type or filename extension that disagrees with the detected
        format is rejected deterministically, so the media metadata can never
        silently disagree with the payload that is stored and served
        (issue #113).
        """
        if not data:
            raise ValueError("Please choose an image to upload.")
        if len(data) > MAX_SKETCHBOOK_ARTIFACT_BYTES:
            raise ValueError(
                "Sketch uploads must be 5MB or smaller. Please choose a smaller image."
            )

        # An unsupported declaration is rejected before byte inspection so the
        # learner gets the actionable "supported formats" message.
        declared_type = _normalise_content_type(content_type)
        if (
            declared_type is not None
            and declared_type not in SUPPORTED_SKETCHBOOK_ARTIFACT_TYPES
        ):
            raise ValueError("Please upload a PNG, JPG, or WebP image.")

        safe_name = (filename or "sketch.png").strip() or "sketch.png"
        extension = PurePosixPath(safe_name).suffix.lower()
        extension_type = _EXTENSION_CONTENT_TYPES.get(extension)
        if extension_type is None:
            raise ValueError("Please upload a PNG, JPG, or WebP image.")

        detected_type = detect_image_type(data)
        if detected_type is None:
            raise ValueError(
                "The uploaded image could not be read. Please try another file."
            )

        # The detected format is authoritative: a declared media type or
        # filename extension naming a different supported format cannot be
        # trusted, so it is rejected rather than silently stored.
        if declared_type is not None and declared_type != detected_type:
            raise ValueError("Please upload a PNG, JPG, or WebP image.")
        if extension_type != detected_type:
            raise ValueError("Please upload a PNG, JPG, or WebP image.")

        return cls(
            learner_id=learner_id,
            activity_id=activity_id,
            filename=safe_name,
            content_type=detected_type,
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


def _normalise_content_type(content_type: str | None) -> str | None:
    """Normalise a declared media type, dropping any parameters."""
    if not content_type:
        return None
    normalised = content_type.split(";", 1)[0].strip().lower()
    return normalised or None
