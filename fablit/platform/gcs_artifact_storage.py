"""Google Cloud Storage adapter for private sketchbook artifact bytes (SPEC-034).

This module isolates Google Cloud Storage concerns behind the existing
ArtifactStorage application boundary (SPEC-033/034).

The binary payload of a learner's sketchbook image is stored in a private
GCS bucket keyed by the opaque artifact identity, keeping raw bytes out of
Practice History (Datastore) and off the App Engine instance filesystem.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fablit.application.artifact_storage import ArtifactStorage, ArtifactStorageError
from fablit.application.artifacts import ArtifactRef

logger = logging.getLogger("fablit.platform.gcs_artifact_storage")

try:
    from google.cloud.exceptions import NotFound
except ImportError:  # pragma: no cover - optional dependency guarded at runtime
    NotFound = None


class GCSArtifactStorage(ArtifactStorage):
    """Google Cloud Storage adapter for private sketchbook artifacts (SPEC-034).

    Stores binary image payloads in a private GCS bucket keyed by an opaque
    artifact identifier. Preserves validated content type and size metadata
    without exposing direct public URLs or bucket access.

    Learner-scoped retrieval remains mediated entirely by the existing
    application route (/history/{completion_id}/artifact).
    """

    def __init__(
        self,
        bucket_name: str,
        client: Any = None,
        prefix: str = "",
    ) -> None:
        """Initialize the GCS artifact storage adapter.

        Args:
            bucket_name: The name of the private GCS bucket. Must be non-empty.
            client: An optional google.cloud.storage.Client instance or duck-typed
                test double. If omitted, storage.Client() is initialized lazily.
            prefix: An optional object name prefix (e.g. 'artifacts/'). Defaults
                to an empty string so the blob key is the artifact UUID string.

        Raises:
            ValueError: If bucket_name is empty or whitespace.
        """
        if (
            not bucket_name
            or not isinstance(bucket_name, str)
            or not bucket_name.strip()
        ):
            raise ValueError("A non-empty GCS bucket name is required.")

        self._bucket_name = bucket_name.strip()
        self._prefix = prefix

        if client is None:
            from google.cloud import storage

            client = storage.Client()

        self._client = client

    @property
    def bucket_name(self) -> str:
        """Return the configured GCS bucket name."""
        return self._bucket_name

    @property
    def prefix(self) -> str:
        """Return the configured object name prefix."""
        return self._prefix

    @property
    def client(self) -> Any:
        """Return the storage client."""
        return self._client

    def _blob_name(self, artifact_id: UUID) -> str:
        """Construct the opaque object key for an artifact."""
        return f"{self._prefix}{artifact_id}"

    def _get_bucket(self) -> Any:
        """Get the bucket reference from the storage client."""
        return self._client.bucket(self._bucket_name)

    def save(self, ref: ArtifactRef, data: bytes) -> None:
        """Persist private sketchbook artifact bytes to GCS.

        Overwrites any previous content under the same artifact identity,
        ensuring idempotent and retry-safe behaviour (SPEC-033/034, FIX-3).

        Args:
            ref: The artifact metadata reference.
            data: The validated binary image payload.

        Raises:
            ArtifactStorageError: If the GCS upload fails.
        """
        blob_name = self._blob_name(ref.artifact_id)
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(blob_name)
            blob.metadata = {
                "artifact_id": str(ref.artifact_id),
                "filename": ref.filename,
            }
            blob.upload_from_string(data, content_type=ref.content_type)
            logger.info(
                "artifact saved to GCS",
                extra={
                    "artifact_id": str(ref.artifact_id),
                    "bucket": self._bucket_name,
                    "blob": blob_name,
                    "size_bytes": len(data),
                    "content_type": ref.content_type,
                },
            )
        except Exception as exc:
            logger.exception(
                "failed to save artifact to GCS",
                extra={
                    "artifact_id": str(ref.artifact_id),
                    "bucket": self._bucket_name,
                    "blob": blob_name,
                },
            )
            raise ArtifactStorageError(
                f"Failed to save artifact {ref.artifact_id} to GCS: {exc}"
            ) from exc

    def get(self, artifact_id: UUID) -> bytes | None:
        """Retrieve private sketchbook artifact bytes from GCS.

        Args:
            artifact_id: The opaque artifact identifier.

        Returns:
            bytes | None: The raw image bytes, or None if the artifact is missing.

        Raises:
            ArtifactStorageError: If an unexpected GCS error occurs during retrieval.
        """
        blob_name = self._blob_name(artifact_id)
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(blob_name)
            if hasattr(blob, "exists") and not blob.exists():
                return None
            return blob.download_as_bytes()  # type: ignore[no-any-return]
        except Exception as exc:
            if (
                NotFound is not None and isinstance(exc, NotFound)
            ) or exc.__class__.__name__ == "NotFound":
                return None
            logger.exception(
                "failed to retrieve artifact from GCS",
                extra={
                    "artifact_id": str(artifact_id),
                    "bucket": self._bucket_name,
                    "blob": blob_name,
                },
            )
            raise ArtifactStorageError(
                f"Failed to retrieve artifact {artifact_id} from GCS: {exc}"
            ) from exc

    def delete(self, artifact_id: UUID) -> None:
        """Remove artifact bytes from GCS. Missing artifacts are ignored.

        Args:
            artifact_id: The opaque artifact identifier.
        """
        blob_name = self._blob_name(artifact_id)
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(blob_name)
            blob.delete()
            logger.info(
                "artifact deleted from GCS",
                extra={
                    "artifact_id": str(artifact_id),
                    "bucket": self._bucket_name,
                    "blob": blob_name,
                },
            )
        except Exception as exc:
            if (
                NotFound is not None and isinstance(exc, NotFound)
            ) or exc.__class__.__name__ == "NotFound":
                return
            logger.warning(
                "failed to delete artifact from GCS",
                extra={
                    "artifact_id": str(artifact_id),
                    "bucket": self._bucket_name,
                    "blob": blob_name,
                    "error": str(exc),
                },
            )
