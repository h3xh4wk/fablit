"""Tests for the stimulus provider abstraction (SPEC-015 §8–14, §21–22, §40–44).

The automated suite never depends on the live external provider (§67): the
Wikimedia Commons provider is exercised with an injected fetch function, and
the built-in fallback keeps everything deterministic (§42–43).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID, uuid4

import pytest

from fablit.application import (
    FallbackStimulusProvider,
    ResilientStimulusProvider,
    StimulusRetrievalError,
    WikimediaCommonsProvider,
    build_demo_activities,
    build_fallback_stimuli,
    build_stimulus_provider,
)
from fablit.application.stimulus import StimulusProvider
from fablit.domain import AssessmentActivity, StimulusInstance
from tests.domain.helpers import make_activity, make_stimulus_context

VALID_PAYLOAD = json.dumps(
    {
        "batchcomplete": "",
        "query": {
            "pages": [
                {
                    "pageid": 123,
                    "ns": 6,
                    "title": "File:Example fashion editorial.jpg",
                    "index": 1,
                    "imageinfo": [
                        {
                            "thumburl": (
                                "https://upload.wikimedia.org/wikipedia/commons/thumb/"
                                "Example.jpg/1200px-Example.jpg"
                            ),
                            "url": "https://upload.wikimedia.org/wikipedia/commons/Example.jpg",
                            "descriptionurl": (
                                "https://commons.wikimedia.org/wiki/"
                                "File:Example_fashion_editorial.jpg"
                            ),
                            "mime": "image/jpeg",
                            "extmetadata": {
                                "Artist": {
                                    "value": (
                                        '<a href="https://example.com/jane">'
                                        "Jane Doe</a>"
                                    ),
                                },
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                "AttributionRequired": {"value": "true"},
                            },
                        }
                    ],
                }
            ]
        },
    }
)


def make_stimulus_activity() -> AssessmentActivity:
    """Build an activity that defines a stimulus context."""
    return make_activity(stimulus_context=make_stimulus_context())


class FakeStimulusProvider:
    """A deterministic provider for tests (SPEC-015 §42–43)."""

    def __init__(self, stimulus: StimulusInstance | None = None) -> None:
        self._stimulus = stimulus
        self.calls = 0

    def resolve(
        self,
        activity: AssessmentActivity,
        *,
        resolved_at: datetime | None = None,
    ) -> StimulusInstance:
        self.calls += 1
        if self._stimulus is None:
            raise StimulusRetrievalError("provider unavailable")
        return self._stimulus


def stimulus_for(activity_id: UUID) -> StimulusInstance:
    """Build a deterministic stimulus for an activity identity."""
    return StimulusInstance(
        activity_id=activity_id,
        provider="fablit",
        image_url="/static/images/test.svg",
        source_url="https://example.com/source",
        retrieved_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# Provider abstraction (SPEC-015 §9, §40–44)
# ---------------------------------------------------------------------------


def test_builtin_provider_serves_deterministic_fallback_stimuli() -> None:
    activities = build_demo_activities()
    provider = build_stimulus_provider(activities, provider_name="builtin")
    stimulus_activities = [
        item for item in activities if item.stimulus_context is not None
    ]

    assert stimulus_activities
    for item in stimulus_activities:
        stimulus = provider.resolve(item.activity)
        assert isinstance(stimulus, StimulusInstance)
        assert stimulus.activity_id == item.activity.id
        assert stimulus.provider == "fablit"
        assert stimulus.image_url.startswith("/static/images/")
        assert stimulus.source_url
        assert stimulus.alt_text
        assert stimulus.retrieved_at.tzinfo is not None


def test_wikimedia_provider_is_composed_with_fallback() -> None:
    activities = build_demo_activities()

    provider = build_stimulus_provider(activities, provider_name="wikimedia")

    assert isinstance(provider, ResilientStimulusProvider)


def test_fallback_image_overrides_replace_bundled_images_by_title() -> None:
    activities = build_demo_activities()
    overrides = {
        "Visual Analysis — Composition": "/static/images/custom-composition.svg"
    }

    provider = build_stimulus_provider(
        activities,
        provider_name="builtin",
        fallback_image_overrides=overrides,
    )

    composition = next(
        item for item in activities if item.title == "Visual Analysis — Composition"
    )
    stimulus = provider.resolve(composition.activity)
    assert stimulus.image_url == "/static/images/custom-composition.svg"

    # Unlisted activities keep their bundled image.
    other = next(
        item for item in activities if item.title == "Observation — Detail Spotting"
    )
    assert provider.resolve(other.activity).image_url == other.fallback_image


def test_wikimedia_knobs_reach_the_provider() -> None:
    seen: list[str] = []

    def capture(url: str) -> str:
        seen.append(url)
        return VALID_PAYLOAD

    activities = build_demo_activities()
    provider = build_stimulus_provider(
        activities,
        provider_name="wikimedia",
        wikimedia_endpoint="https://example.test/api.php",
        wikimedia_width=640,
        wikimedia_limit=3,
        wikimedia_fetch=capture,
    )
    activity = next(
        item for item in activities if item.stimulus_context is not None
    ).activity

    stimulus = provider.resolve(activity)

    assert stimulus.provider == "wikimedia_commons"
    assert seen
    assert seen[0].startswith("https://example.test/api.php?")
    assert "iiurlwidth=640" in seen[0]
    assert "gsrlimit=3" in seen[0]


def test_wikimedia_endpoint_is_configurable_directly() -> None:
    seen: list[str] = []

    def capture(url: str) -> str:
        seen.append(url)
        return VALID_PAYLOAD

    provider = WikimediaCommonsProvider(
        fetch=capture, endpoint="https://example.test/custom.php"
    )

    provider.resolve(make_stimulus_activity())

    assert seen
    assert seen[0].startswith("https://example.test/custom.php?")


# ---------------------------------------------------------------------------
# Fallback provider (SPEC-015 §22)
# ---------------------------------------------------------------------------


def test_fallback_stimuli_cover_every_stimulus_activity() -> None:
    activities = build_demo_activities()
    fallbacks = build_fallback_stimuli(activities)

    stimulus_activity_ids = {
        item.activity.id for item in activities if item.stimulus_context is not None
    }
    assert set(fallbacks) == stimulus_activity_ids
    assert len(fallbacks) >= 1


def test_fallback_provider_returns_known_stimulus() -> None:
    activities = build_demo_activities()
    provider = FallbackStimulusProvider(build_fallback_stimuli(activities))
    item = next(item for item in activities if item.stimulus_context is not None)

    stimulus = provider.resolve(item.activity)

    assert stimulus.activity_id == item.activity.id
    assert stimulus.image_url == item.fallback_image
    assert stimulus.creator == "Fablit"
    assert stimulus.license == "MIT"


def test_fallback_provider_rejects_activity_without_fallback() -> None:
    activities = build_demo_activities()
    provider = FallbackStimulusProvider(build_fallback_stimuli(activities))
    activity = next(
        item for item in activities if item.stimulus_context is None
    ).activity

    with pytest.raises(StimulusRetrievalError, match="no fallback stimulus"):
        provider.resolve(activity)


# ---------------------------------------------------------------------------
# Wikimedia Commons provider (SPEC-015 §8, §10, §50)
# ---------------------------------------------------------------------------


def test_wikimedia_provider_parses_valid_response() -> None:
    provider = WikimediaCommonsProvider(fetch=lambda url: VALID_PAYLOAD)
    activity = make_stimulus_activity()

    stimulus = provider.resolve(activity)

    assert isinstance(stimulus, StimulusInstance)
    assert stimulus.provider == "wikimedia_commons"
    assert stimulus.image_url == (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/"
        "Example.jpg/1200px-Example.jpg"
    )
    assert stimulus.source_url == (
        "https://commons.wikimedia.org/wiki/File:Example_fashion_editorial.jpg"
    )
    assert stimulus.asset_id == "File:Example fashion editorial.jpg"
    assert stimulus.creator == "Jane Doe"
    assert stimulus.license == "CC BY-SA 4.0"
    assert stimulus.attribution == "Jane Doe / CC BY-SA 4.0"
    assert stimulus.alt_text == "Example fashion editorial"
    assert stimulus.activity_id == activity.id


def test_wikimedia_provider_uses_contextual_query() -> None:
    seen: list[str] = []

    def capture(url: str) -> str:
        seen.append(url)
        return VALID_PAYLOAD

    provider = WikimediaCommonsProvider(fetch=capture)
    activity = make_stimulus_activity()

    provider.resolve(activity)

    assert seen
    # The retrieval query is derived from the activity's stimulus context and
    # restricted to bitmap images (SPEC-015 §11–13).
    parsed = urlparse(seen[0])
    assert parsed.hostname == "commons.wikimedia.org"
    assert "fashion%20editorial%20composition" in seen[0]
    assert "filetype%3Abitmap" in seen[0]
    assert "mime" in seen[0]


def test_wikimedia_provider_default_fetch_sends_a_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wikimedia policy requires a descriptive User-Agent; it must be sent."""
    import urllib.request

    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return VALID_PAYLOAD.encode("utf-8")

    def fake_urlopen(request: object, timeout: float = 0.0) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = WikimediaCommonsProvider()
    activity = make_stimulus_activity()

    provider.resolve(activity)

    request = captured["request"]
    assert isinstance(request, urllib.request.Request)
    # urllib normalises header names, so match case-insensitively.
    user_agent = next(
        (
            value
            for key, value in request.headers.items()
            if key.lower() == "user-agent"
        ),
        "",
    )
    assert "FablitPilot" in user_agent
    assert captured["timeout"] == 10.0


def test_wikimedia_provider_skips_non_image_documents() -> None:
    """Documents (e.g. PDFs) must never become a learner's visual stimulus."""
    payload = json.dumps(
        {
            "query": {
                "pages": [
                    {
                        "title": "File:Document.pdf",
                        "imageinfo": [
                            {
                                "thumburl": "https://example.com/doc.pdf",
                                "descriptionurl": "https://example.com/doc",
                                "mime": "application/pdf",
                            }
                        ],
                    },
                    {
                        "title": "File:Photo.jpg",
                        "imageinfo": [
                            {
                                "thumburl": "https://example.com/photo.jpg",
                                "descriptionurl": "https://example.com/photo",
                                "mime": "image/jpeg",
                            }
                        ],
                    },
                ]
            }
        }
    )
    provider = WikimediaCommonsProvider(fetch=lambda url: payload)
    activity = make_stimulus_activity()

    stimulus = provider.resolve(activity)

    assert stimulus.asset_id == "File:Photo.jpg"
    assert stimulus.image_url == "https://example.com/photo.jpg"


def test_wikimedia_provider_handles_network_failure() -> None:
    def broken_fetch(url: str) -> str:
        raise TimeoutError("timed out")

    provider = WikimediaCommonsProvider(fetch=broken_fetch)
    activity = make_stimulus_activity()

    with pytest.raises(StimulusRetrievalError, match="unavailable"):
        provider.resolve(activity)


def test_wikimedia_provider_handles_invalid_json() -> None:
    provider = WikimediaCommonsProvider(fetch=lambda url: "not json")
    activity = make_stimulus_activity()

    with pytest.raises(StimulusRetrievalError, match="no usable stimulus"):
        provider.resolve(activity)


def test_wikimedia_provider_skips_pages_without_usable_image() -> None:
    payload = json.dumps(
        {
            "query": {
                "pages": [
                    {"title": "File:NoImage.jpg", "imageinfo": []},
                    {
                        "title": "File:MissingUrl.jpg",
                        "imageinfo": [{"url": "x", "mime": "image/jpeg"}],
                    },
                ]
            }
        }
    )
    provider = WikimediaCommonsProvider(fetch=lambda url: payload)
    activity = make_stimulus_activity()

    with pytest.raises(StimulusRetrievalError, match="no usable stimulus"):
        provider.resolve(activity)


def test_wikimedia_provider_rejects_activity_without_stimulus_context() -> None:
    provider = WikimediaCommonsProvider(fetch=lambda url: VALID_PAYLOAD)
    activity = make_activity()

    with pytest.raises(StimulusRetrievalError, match="stimulus context"):
        provider.resolve(activity)


def test_wikimedia_provider_omits_attribution_when_not_required() -> None:
    payload = json.dumps(
        {
            "query": {
                "pages": [
                    {
                        "title": "File:Plain image.jpg",
                        "imageinfo": [
                            {
                                "thumburl": "https://example.com/plain.jpg",
                                "descriptionurl": "https://example.com/plain",
                                "mime": "image/jpeg",
                                "extmetadata": {
                                    "Artist": {"value": "Jane Doe"},
                                    "AttributionRequired": {"value": "false"},
                                },
                            }
                        ],
                    }
                ]
            }
        }
    )
    provider = WikimediaCommonsProvider(fetch=lambda url: payload)
    activity = make_stimulus_activity()

    stimulus = provider.resolve(activity)

    assert stimulus.creator == "Jane Doe"
    assert stimulus.attribution is None


# ---------------------------------------------------------------------------
# Resilient composition (SPEC-015 §21–23, §45)
# ---------------------------------------------------------------------------


def test_resilient_provider_uses_primary_when_it_succeeds() -> None:
    stimulus = stimulus_for(uuid4())
    primary = FakeStimulusProvider(stimulus=stimulus)
    fallback = FakeStimulusProvider(stimulus=stimulus_for(uuid4()))
    provider: StimulusProvider = ResilientStimulusProvider(primary, fallback)

    result = provider.resolve(make_activity())

    assert result is stimulus
    assert primary.calls == 1
    assert fallback.calls == 0


def test_resilient_provider_falls_back_when_primary_fails() -> None:
    fallback_stimulus = stimulus_for(uuid4())
    primary = FakeStimulusProvider()
    fallback = FakeStimulusProvider(stimulus=fallback_stimulus)
    provider: StimulusProvider = ResilientStimulusProvider(primary, fallback)

    result = provider.resolve(make_activity())

    assert result is fallback_stimulus
    assert primary.calls == 1
    assert fallback.calls == 1


def test_resilient_provider_raises_when_fallback_also_fails() -> None:
    primary = FakeStimulusProvider()
    fallback = FakeStimulusProvider()
    provider: StimulusProvider = ResilientStimulusProvider(primary, fallback)

    with pytest.raises(StimulusRetrievalError):
        provider.resolve(make_activity())
