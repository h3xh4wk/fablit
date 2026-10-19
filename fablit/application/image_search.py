"""Optional image search for authoring candidates (SPEC-036).

The authoring workflow can ask a provider for free-to-use photographs that
match a one-line scene description. The application layer owns this port and
its value type so the workflow never imports a provider SDK or HTTP detail;
concrete adapters (Pexafy) live under :mod:`fablit.platform`.

Images are optional. A failure to search must not fail candidate generation,
and the selected image is always a human choice among listed results.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from fablit.domain import StimulusInstance


class ImageSearchError(Exception):
    """Raised when an image search cannot be completed safely."""


def image_candidate_from_mapping(data: object) -> ImageCandidate | None:
    """Read one stored image selection, or ``None`` when it is unusable.

    Candidate data is persisted as plain mappings (and read back from
    Datastore payloads), so the boundary is defensive: a missing or malformed
    selection means "no image", never a failed publication.
    """
    if not isinstance(data, Mapping):
        return None
    try:
        return ImageCandidate(
            photo_id=_text(data.get("photo_id")),
            image_url=_text(data.get("image_url")),
            thumbnail_url=_text(data.get("thumbnail_url")),
            alt_text=_text(data.get("alt_text")),
            description=_text(data.get("description")),
            photographer=_text(data.get("photographer")),
            photographer_url=_text(data.get("photographer_url")),
            source=_text(data.get("source")),
            source_url=_text(data.get("source_url")),
            attribution=_text(data.get("attribution")),
            width=_positive_int(data.get("width")),
            height=_positive_int(data.get("height")),
            orientation=_text(data.get("orientation")),
            license_type=_text(data.get("license_type")),
        )
    except ValueError:
        return None


def image_candidate_to_mapping(image: ImageCandidate) -> dict[str, object]:
    """Serialize an image selection for candidate/publication storage."""
    return {
        "photo_id": image.photo_id,
        "image_url": image.image_url,
        "thumbnail_url": image.thumbnail_url,
        "alt_text": image.alt_text,
        "description": image.description,
        "photographer": image.photographer,
        "photographer_url": image.photographer_url,
        "source": image.source,
        "source_url": image.source_url,
        "attribution": image.attribution,
        "width": image.width,
        "height": image.height,
        "orientation": image.orientation,
        "license_type": image.license_type,
    }


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _positive_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return 0
    return value


@dataclass(frozen=True)
class ImageCandidate:
    """One free-to-use image returned by an image-search provider.

    The value keeps display and provenance fields together so a candidate can
    store the result without retaining a provider response, and so the learner
    page can show attribution from the same record the author approved.
    """

    photo_id: str
    image_url: str
    thumbnail_url: str
    alt_text: str
    description: str
    photographer: str
    photographer_url: str
    source: str
    source_url: str
    attribution: str
    width: int
    height: int
    orientation: str
    license_type: str = ""

    def __post_init__(self) -> None:
        for name in (
            "photo_id",
            "image_url",
            "thumbnail_url",
            "alt_text",
            "source",
            "source_url",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"image candidate {name} must be non-blank text")

    def to_stimulus(
        self, *, activity_id: UUID, retrieved_at: datetime
    ) -> StimulusInstance:
        """Represent the chosen image as the learner-facing stimulus."""
        return StimulusInstance(
            activity_id=activity_id,
            provider="pexafy",
            asset_id=self.photo_id,
            image_url=self.image_url,
            source_url=self.source_url,
            retrieved_at=retrieved_at,
            creator=self.photographer or None,
            license=self.license_type or self.source or None,
            attribution=self.attribution or None,
            alt_text=self.alt_text,
        )


class ImageSearchProvider(Protocol):
    """Application-level port for optional stimulus-image search (SPEC-036)."""

    def search(
        self, query: str, *, limit: int | None = None
    ) -> tuple[ImageCandidate, ...]:
        """Return free-to-use images relevant to the one-line query.

        Raises:
            ImageSearchError: When the provider is unavailable, unauthorized,
                over quota, times out, or returns an unusable response.
        """
        ...
