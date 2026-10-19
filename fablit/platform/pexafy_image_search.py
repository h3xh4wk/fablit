"""Pexafy semantic image-search adapter (SPEC-036).

Pexafy searches several free stock-photo libraries by meaning and returns
display URLs together with source, photographer, and attribution metadata.
This adapter owns the provider-specific request/response details so the
authoring workflow depends only on the application's image-search port.

The API key is sent as ``x-api-key`` and never appears in a URL, log line, or
client response. The transport is injectable so tests run deterministically
without network access.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, Final

from fablit.application.image_search import (
    ImageCandidate,
    ImageSearchError,
    ImageSearchProvider,
)

logger = logging.getLogger("fablit.authoring.pexafy")

#: Provider identity recorded on published stimuli.
PEXAFY_PROVIDER_ID: Final[str] = "pexafy"

#: Default Pexafy search endpoint (SPEC-036).
DEFAULT_PEXAFY_ENDPOINT: Final[str] = "https://api.pexafy.com/api/v1/search/photos"

#: Transport signature: ``(url, headers) -> response_text``.
PexafyTransport = Callable[[str, Mapping[str, str]], str]

#: Pexafy caps a single page at 80 results; authoring only needs a small set.
MAX_RESULTS: Final[int] = 20

#: A single generic message so provider details never reach the authoring UI.
_UNAVAILABLE_MESSAGE: Final[str] = "image search is unavailable"


class PexafyImageSearch(ImageSearchProvider):
    """Pexafy-backed adapter for optional candidate image search (SPEC-036)."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = DEFAULT_PEXAFY_ENDPOINT,
        timeout: float = 10.0,
        limit: int = 6,
        fetch: PexafyTransport | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("the Pexafy image search requires a non-blank API key")
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError("the Pexafy image search requires an endpoint")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("the Pexafy image search limit must be positive")
        self._api_key = api_key.strip()
        self._endpoint = endpoint.strip()
        self._timeout = timeout
        self._limit = min(limit, MAX_RESULTS)
        self._fetch: PexafyTransport = fetch or self._default_fetch

    def search(
        self, query: str, *, limit: int | None = None
    ) -> tuple[ImageCandidate, ...]:
        """Search Pexafy for free-to-use images matching ``query``."""
        cleaned = " ".join(query.split())
        if not cleaned:
            return ()
        requested = self._limit if limit is None else limit
        per_page = max(1, min(requested, self._limit, MAX_RESULTS))
        params = urllib.parse.urlencode({"q": cleaned, "per_page": per_page})
        url = f"{self._endpoint}?{params}"
        try:
            payload = self._fetch(
                url,
                {"x-api-key": self._api_key, "Accept": "application/json"},
            )
        except ImageSearchError:
            raise
        except urllib.error.HTTPError as exc:
            # Never surface the status text: it can echo request details.
            raise ImageSearchError(
                f"{_UNAVAILABLE_MESSAGE} (status {exc.code})"
            ) from exc
        except Exception as exc:  # network errors, timeouts, unexpected failures
            raise ImageSearchError(_UNAVAILABLE_MESSAGE) from exc
        return self._parse(payload, query=cleaned, limit=per_page)

    def _default_fetch(self, url: str, headers: Mapping[str, str]) -> str:
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            payload: bytes = response.read()
        return payload.decode("utf-8")

    def _parse(
        self, payload: str, *, query: str, limit: int
    ) -> tuple[ImageCandidate, ...]:
        try:
            data: Any = json.loads(payload)
        except (ValueError, TypeError) as exc:
            raise ImageSearchError(
                f"{_UNAVAILABLE_MESSAGE} (unreadable response)"
            ) from exc
        if not isinstance(data, Mapping):
            raise ImageSearchError(
                f"{_UNAVAILABLE_MESSAGE} (unexpected response shape)"
            )
        if data.get("success") is False:
            # Provider messages can echo request details or credentials, so
            # the author sees only the stable, safe explanation.
            raise ImageSearchError(
                f"{_UNAVAILABLE_MESSAGE} (provider refused the search)"
            )
        results = data.get("data")
        if not isinstance(results, list):
            raise ImageSearchError(f"{_UNAVAILABLE_MESSAGE} (no image results)")
        candidates: list[ImageCandidate] = []
        for item in results[:limit]:
            candidate = _candidate_from_item(item, fallback_alt=query)
            if candidate is not None:
                candidates.append(candidate)
        return tuple(candidates)


def _candidate_from_item(item: object, *, fallback_alt: str) -> ImageCandidate | None:
    """Map one Pexafy result, skipping entries without usable provenance."""
    if not isinstance(item, Mapping):
        return None
    image_url = _text(item.get("image_url"))
    source_url = _text(item.get("source_image_url"))
    if not image_url or not source_url:
        return None
    urls = item.get("urls")
    thumbnail = ""
    if isinstance(urls, Mapping):
        thumbnail = _text(urls.get("thumb")) or _text(urls.get("small"))
    description = _text(item.get("description"))
    alt_text = _text(item.get("alt_description")) or description or fallback_alt
    attribution = ""
    attribution_data = item.get("attribution")
    if isinstance(attribution_data, Mapping):
        attribution = _text(attribution_data.get("plain"))
    photographer = _text(item.get("photographer_full_name")) or _text(
        item.get("photographer_username")
    )
    source = _text(item.get("source"))
    width = _positive_int(item.get("width"))
    height = _positive_int(item.get("height"))
    orientation = _text(item.get("orientation"))
    if not source:
        return None
    try:
        return ImageCandidate(
            photo_id=_text(item.get("photo_id")) or source_url,
            image_url=image_url,
            thumbnail_url=thumbnail or image_url,
            alt_text=alt_text or fallback_alt,
            description=description or alt_text or fallback_alt,
            photographer=photographer,
            photographer_url=_text(item.get("photographer_url")),
            source=source,
            source_url=source_url,
            attribution=attribution,
            width=width,
            height=height,
            orientation=orientation,
            license_type=_text(item.get("license_type")),
        )
    except ValueError:
        return None


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _positive_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return 0
    return value
