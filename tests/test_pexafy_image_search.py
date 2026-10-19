"""Pexafy image-search adapter tests (SPEC-036)."""

from __future__ import annotations

import json
import urllib.error
from collections.abc import Mapping

import pytest

from fablit.application.image_search import ImageSearchError
from fablit.platform.pexafy_image_search import PexafyImageSearch

RESULT = {
    "success": True,
    "data": [
        {
            "photo_id": "photo-1",
            "image_url": "https://cdn.example/large.jpg",
            "urls": {
                "thumb": "https://cdn.example/thumb.jpg",
                "small": "https://cdn.example/small.jpg",
            },
            "alt_description": "A still life on a wooden table",
            "description": "A pear and a silver box on a wooden table.",
            "photographer_full_name": "",
            "photographer_username": "Saurabh_U",
            "photographer_url": "https://example/users/saurabh",
            "source": "Pixabay",
            "source_image_url": "https://example/photos/still-life",
            "attribution": {"plain": "Photo by Saurabh_U on Pixabay"},
            "width": 6000,
            "height": 4000,
            "orientation": "landscape",
            "license_type": "free",
        }
    ],
}


def _provider(payload: str) -> PexafyImageSearch:
    calls: list[tuple[str, dict[str, str]]] = []

    def fetch(url: str, headers: Mapping[str, str]) -> str:
        calls.append((url, dict(headers)))
        return payload

    provider = PexafyImageSearch(api_key="secret-key", fetch=fetch)
    provider.calls = calls  # type: ignore[attr-defined]
    return provider


def test_search_maps_urls_alt_text_and_attribution() -> None:
    provider = _provider(json.dumps(RESULT))

    images = provider.search("still life composition")

    assert len(images) == 1
    image = images[0]
    assert image.photo_id == "photo-1"
    assert image.image_url == "https://cdn.example/large.jpg"
    assert image.thumbnail_url == "https://cdn.example/thumb.jpg"
    assert image.alt_text == "A still life on a wooden table"
    assert image.photographer == "Saurabh_U"
    assert image.source == "Pixabay"
    assert image.source_url == "https://example/photos/still-life"
    assert image.attribution == "Photo by Saurabh_U on Pixabay"
    assert image.orientation == "landscape"


def test_search_sends_key_in_header_and_a_bounded_page() -> None:
    provider = _provider(json.dumps(RESULT))

    provider.search("still life", limit=3)

    url, headers = provider.calls[0]  # type: ignore[attr-defined]
    assert "q=still+life" in url
    assert "per_page=3" in url
    assert headers["x-api-key"] == "secret-key"
    assert "secret-key" not in url


def test_blank_query_skips_the_provider() -> None:
    provider = _provider(json.dumps(RESULT))

    assert provider.search("   ") == ()
    assert provider.calls == []  # type: ignore[attr-defined]


def test_malformed_result_is_skipped() -> None:
    payload = {
        "success": True,
        "data": [{"image_url": "https://cdn.example/large.jpg"}],
    }
    provider = _provider(json.dumps(payload))

    assert provider.search("still life") == ()


def test_http_error_is_reported_without_provider_payload() -> None:
    def fetch(url: str, headers: Mapping[str, str]) -> str:
        raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)  # type: ignore[arg-type]

    provider = PexafyImageSearch(api_key="secret-key", fetch=fetch)

    with pytest.raises(ImageSearchError, match="status 429"):
        provider.search("still life")


def test_unreadable_response_raises_image_search_error() -> None:
    provider = _provider("not-json")

    with pytest.raises(ImageSearchError, match="unreadable"):
        provider.search("still life")


def test_provider_error_response_is_not_surfaced_verbatim() -> None:
    payload = {
        "success": False,
        "error": {"message": "quota exceeded for secret-key"},
    }
    provider = _provider(json.dumps(payload))

    with pytest.raises(ImageSearchError) as error:
        provider.search("still life")

    assert "secret-key" not in str(error.value)
