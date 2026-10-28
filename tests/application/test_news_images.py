"""Deterministic tests for SPEC-043 story imagery selection.

No test here calls a live image provider: the port is faked in-process, so
query derivation, conservative candidate selection, metadata validation, and
persistence round trips are all exercised deterministically.
"""

from __future__ import annotations

import pytest

from fablit.application.image_search import ImageCandidate, ImageSearchError
from fablit.application.news_images import (
    MAX_VISUAL_QUERY_CHARS,
    NewsImageSelector,
    StoryImage,
    derive_visual_query,
    select_story_image,
    story_image_from_mapping,
    story_image_to_mapping,
)

QUERY = derive_visual_query(
    "Handloom revival connects weavers with new markets",
    "A collective is helping weavers reach contemporary fashion buyers.",
    ("textiles", "indian-craft"),
)


def make_candidate(**overrides: object) -> ImageCandidate:
    values: dict[str, object] = {
        "photo_id": "photo-1",
        "image_url": "https://images.example.com/handloom.jpg",
        "thumbnail_url": "https://images.example.com/handloom-thumb.jpg",
        "alt_text": "Handloom weaver at a wooden loom",
        "description": "Weaver working with handloom textiles",
        "photographer": "Asha Rao",
        "photographer_url": "https://images.example.com/@asha",
        "source": "unsplash",
        "source_url": "https://images.example.com/photos/handloom",
        "attribution": "Photo by Asha Rao on Unsplash",
        "width": 1600,
        "height": 900,
        "orientation": "landscape",
        "license_type": "unsplash",
    }
    values.update(overrides)
    return ImageCandidate(**values)  # type: ignore[arg-type]


class FakeImageSearch:
    """In-process image-search port that records the query it received."""

    def __init__(
        self,
        candidates: tuple[ImageCandidate, ...] = (),
        *,
        error: Exception | None = None,
        provider_id: str = "fake-images",
    ) -> None:
        self._candidates = candidates
        self._error = error
        self.provider_id = provider_id
        self.queries: list[tuple[str, int | None]] = []

    def search(
        self, query: str, *, limit: int | None = None
    ) -> tuple[ImageCandidate, ...]:
        self.queries.append((query, limit))
        if self._error is not None:
            raise self._error
        return self._candidates


# --- Visual query derivation -------------------------------------------------


def test_visual_query_keeps_distinctive_words_and_the_category_subject() -> None:
    assert "handloom" in QUERY
    assert "textile" in QUERY
    assert len(QUERY.split()) <= 5


def test_visual_query_drops_stop_words_and_is_not_the_headline() -> None:
    headline = "Handloom revival connects weavers with new markets"

    assert headline != QUERY
    assert " with " not in f" {QUERY} "
    assert " new " not in f" {QUERY} "


def test_visual_query_is_bounded_for_a_long_sensational_headline() -> None:
    headline = (
        "You will not believe what this incredible handloom collective did "
        "and why everyone is talking about it right now"
    )

    query = derive_visual_query(headline, "", ("textiles",))

    assert len(query) <= MAX_VISUAL_QUERY_CHARS
    assert query
    assert query.split()[-1] in {"handloom", "collective", "textile", "fabric"}


def test_visual_query_falls_back_to_the_category_subject() -> None:
    assert derive_visual_query("", "", ("fashion",)) == "fashion design"
    assert derive_visual_query("", "", ()) == ""


# --- Conservative candidate selection ---------------------------------------


def test_selector_returns_a_credited_illustrative_story_image() -> None:
    provider = FakeImageSearch((make_candidate(),))
    selector = NewsImageSelector(provider, limit=3)

    selection = selector.select(
        headline="Handloom revival connects weavers with new markets",
        summary="A collective is helping weavers reach buyers.",
        categories=("textiles",),
    )

    assert selection.reason == "selected"
    assert selection.candidates_considered == 1
    image = selection.image
    assert isinstance(image, StoryImage)
    assert image.image_url == "https://images.example.com/handloom.jpg"
    assert image.thumbnail_url == "https://images.example.com/handloom-thumb.jpg"
    assert image.alt_text.startswith("Illustrative stock image: ")
    assert image.credit == "Photo by Asha Rao on Unsplash"
    assert image.source_name == "unsplash"
    assert image.source_url == "https://images.example.com/photos/handloom"
    assert image.provider == "fake-images"
    assert image.is_illustrative is True
    assert provider.queries == [(selection.query, 3)]
    assert selection.query == derive_visual_query(
        "Handloom revival connects weavers with new markets",
        "A collective is helping weavers reach buyers.",
        ("textiles",),
    )


def test_most_relevant_candidate_wins_over_a_merely_larger_one() -> None:
    relevant = make_candidate(
        photo_id="photo-relevant",
        description="Handloom textile fabric weavers at a craft market",
        width=1200,
        height=800,
    )
    larger = make_candidate(
        photo_id="photo-large",
        description="Textile fabric detail",
        alt_text="Textile fabric detail",
        width=4000,
        height=2400,
    )

    image = select_story_image((larger, relevant), query=QUERY)

    assert image is not None
    assert image.asset_id == "photo-relevant"


def test_unrelated_candidates_fall_back_to_no_image() -> None:
    unrelated = make_candidate(
        description="A red sports car on a coastal road",
        alt_text="Sports car on a coast",
    )

    assert select_story_image((unrelated,), query=QUERY) is None


def test_small_or_extreme_aspect_candidates_are_rejected() -> None:
    tiny = make_candidate(photo_id="tiny", width=300, height=200)
    banner = make_candidate(photo_id="banner", width=3000, height=400)
    missing_size = make_candidate(photo_id="unknown", width=0, height=0)

    assert select_story_image((tiny,), query=QUERY) is None
    assert select_story_image((banner,), query=QUERY) is None
    assert select_story_image((missing_size,), query=QUERY) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"image_url": "javascript:alert(1)"},
        {"image_url": "http://127.0.0.1/private.jpg"},
        {"thumbnail_url": "file:///etc/passwd"},
        {"source_url": "javascript:alert(1)"},
        {"thumbnail_url": "https://user:secret@images.example.com/a.jpg"},
    ],
)
def test_unsafe_or_incomplete_metadata_is_rejected(overrides: dict[str, str]) -> None:
    candidate = make_candidate(**overrides)

    assert select_story_image((candidate,), query=QUERY) is None


def test_missing_alt_text_is_described_from_the_candidate_description() -> None:
    candidate = make_candidate()
    object.__setattr__(candidate, "alt_text", "")

    image = select_story_image((candidate,), query=QUERY)

    assert image is not None
    assert image.alt_text == (f"Illustrative stock image: {candidate.description}")


@pytest.mark.parametrize(
    "error",
    [ImageSearchError("provider unavailable"), RuntimeError("unexpected")],
)
def test_provider_failures_report_a_safe_reason(error: Exception) -> None:
    selector = NewsImageSelector(FakeImageSearch(error=error))

    selection = selector.select(headline="Handloom revival", summary="")

    assert selection.image is None
    assert selection.reason == "image search failed"
    assert "unexpected" not in selection.reason
    assert "provider unavailable" not in selection.reason


def test_empty_results_report_a_reason_without_an_image() -> None:
    selector = NewsImageSelector(FakeImageSearch(()))

    selection = selector.select(headline="Handloom revival", summary="")

    assert selection.image is None
    assert selection.reason == "image search returned no results"


def test_unsuitable_results_report_a_reason_without_an_image() -> None:
    selector = NewsImageSelector(
        FakeImageSearch((make_candidate(width=200, height=100),))
    )

    selection = selector.select(
        headline="Handloom revival connects weavers",
        summary="A collective helps weavers.",
        categories=("textiles",),
    )

    assert selection.image is None
    assert selection.reason == "no returned image was suitable"
    assert selection.candidates_considered == 1


def test_selector_validates_its_dependencies() -> None:
    with pytest.raises(ValueError, match="image-search provider"):
        NewsImageSelector(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="limit must be positive"):
        NewsImageSelector(FakeImageSearch(), limit=0)


# --- Provenance persistence --------------------------------------------------


def test_story_image_mapping_round_trips() -> None:
    image = select_story_image((make_candidate(),), query=QUERY)
    assert image is not None

    stored = story_image_to_mapping(image)
    restored = story_image_from_mapping(stored)

    assert restored == image
    assert restored is not None
    assert restored.credit_line == image.credit


@pytest.mark.parametrize(
    "stored",
    [
        None,
        {},
        "not-a-mapping",
        {
            "asset_id": "photo-1",
            "image_url": "javascript:alert(1)",
            "thumbnail_url": "https://images.example.com/a.jpg",
            "alt_text": "Image",
            "source_name": "unsplash",
            "source_url": "https://images.example.com/photos/a",
        },
    ],
)
def test_unusable_stored_images_are_ignored(stored: object) -> None:
    assert story_image_from_mapping(stored) is None


def test_story_image_rejects_unsafe_urls_and_blank_fields() -> None:
    mapping = story_image_to_mapping(
        StoryImage(
            asset_id="photo-1",
            image_url="https://images.example.com/a.jpg",
            thumbnail_url="https://images.example.com/a-thumb.jpg",
            alt_text="Illustrative image",
            source_name="unsplash",
            source_url="https://images.example.com/photos/a",
            provider="pexafy",
        )
    )

    for field, value in (
        ("image_url", "javascript:alert(1)"),
        ("source_url", "file:///etc/passwd"),
        ("alt_text", ""),
    ):
        broken = dict(mapping)
        broken[field] = value
        with pytest.raises(ValueError, match=field):
            StoryImage(**broken)  # type: ignore[arg-type]
