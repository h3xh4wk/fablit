"""Stimulus provider abstraction and implementations (SPEC-015 §8–14, §40–44).

External image retrieval is isolated behind an application-level abstraction
so the domain never depends on a specific image provider, provider-specific
fields are translated into Fablit's internal stimulus representation (§49),
and the provider can be replaced without changing the learner activity model
(§9). The automated test suite never depends on the live external provider:
tests inject deterministic providers, and the built-in fallback keeps the
default experience offline and reproducible (§42–43, §67).
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from fablit.domain import AssessmentActivity, StimulusInstance

from .errors import StimulusRetrievalError
from .store import DemoActivity

logger = logging.getLogger("fablit.stimulus")

SUPPORTED_PROVIDERS = {"builtin", "wikimedia"}

#: The source page for Fablit's own bundled demo stimuli.
FABLIT_SOURCE_URL = "https://github.com/h3xh4wk/fablit"


class StimulusProvider(Protocol):
    """Application-level abstraction over an external visual stimulus source (§9)."""

    def resolve(
        self,
        activity: AssessmentActivity,
        *,
        resolved_at: datetime | None = None,
    ) -> StimulusInstance:
        """Resolve the visual stimulus for the activity's stimulus context.

        Raises:
            StimulusRetrievalError: When the provider cannot supply a usable
                stimulus (SPEC-015 §21, §50).
        """
        ...


@dataclass(frozen=True)
class FallbackDefinition:
    """A known, deterministic stimulus used when external retrieval fails (§22)."""

    asset_id: str
    image_url: str
    source_url: str
    creator: str | None = None
    license: str | None = None
    attribution: str | None = None
    alt_text: str | None = None


class FallbackStimulusProvider:
    """Deterministic built-in stimulus provider (SPEC-015 §22).

    Returns a known stimulus that still satisfies the activity's learning
    purpose — never leaving the learner with a blank activity when a valid
    fallback is available. Used directly when external retrieval is disabled
    and as the fallback of a resilient provider when it fails.
    """

    def __init__(self, fallbacks: Mapping[UUID, FallbackDefinition]) -> None:
        self._fallbacks = dict(fallbacks)

    def resolve(
        self,
        activity: AssessmentActivity,
        *,
        resolved_at: datetime | None = None,
    ) -> StimulusInstance:
        definition = self._fallbacks.get(activity.id)
        if definition is None:
            raise StimulusRetrievalError(
                "no fallback stimulus is defined for this activity"
            )
        return StimulusInstance(
            activity_id=activity.id,
            provider="fablit",
            asset_id=definition.asset_id,
            image_url=definition.image_url,
            source_url=definition.source_url,
            creator=definition.creator,
            license=definition.license,
            attribution=definition.attribution,
            alt_text=definition.alt_text,
            retrieved_at=resolved_at if resolved_at is not None else datetime.now(UTC),
        )


class WikimediaCommonsProvider:
    """Stimulus provider backed by the Wikimedia Commons API (SPEC-015 §8, §10).

    The first implementation uses one approved source (Wikimedia Commons)
    because it supports stable image identification, image URLs, source
    pages, creator/author, license, and attribution metadata (§8). The
    retrieval query is derived from the activity's stimulus context (§11–12)
    and a small set of candidates is searched, keeping retrieval bounded by
    the activity's learning context rather than unrestricted (§12–13).

    The provider is deliberately defensive: network failures, timeouts,
    invalid responses, and missing metadata all raise
    :class:`StimulusRetrievalError` so the application can fall back safely
    (§21, §50). ``fetch`` is injectable for deterministic tests (§42–43).
    """

    def __init__(
        self,
        *,
        fetch: Callable[[str], str] | None = None,
        timeout: float = 10.0,
        width: int = 1200,
        limit: int = 5,
    ) -> None:
        self._fetch = fetch or self._default_fetch
        self._timeout = timeout
        self._width = width
        self._limit = limit

    def _default_fetch(self, url: str) -> str:
        with urllib.request.urlopen(url, timeout=self._timeout) as response:
            payload: bytes = response.read()
            return payload.decode("utf-8")

    def resolve(
        self,
        activity: AssessmentActivity,
        *,
        resolved_at: datetime | None = None,
    ) -> StimulusInstance:
        context = activity.stimulus_context
        if context is None:
            raise StimulusRetrievalError("activity does not define a stimulus context")
        query = urllib.parse.quote(context.retrieval_query)
        url = (
            "https://commons.wikimedia.org/w/api.php?action=query&format=json"
            "&formatversion=2&generator=search"
            f"&gsrsearch={query}&gsrnamespace=6&gsrlimit={self._limit}"
            "&prop=imageinfo&iiprop=url%7Cextmetadata"
            f"&iiurlwidth={self._width}"
        )
        try:
            payload = self._fetch(url)
        except Exception as exc:  # network errors, timeouts, malformed responses
            raise StimulusRetrievalError("the image provider is unavailable") from exc
        stimulus = self._select(payload, activity, resolved_at)
        if stimulus is None:
            raise StimulusRetrievalError(
                "the image provider returned no usable stimulus"
            )
        return stimulus

    def _select(
        self,
        payload: str,
        activity: AssessmentActivity,
        resolved_at: datetime | None,
    ) -> StimulusInstance | None:
        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            return None
        pages = (data.get("query") or {}).get("pages") or []
        for page in pages:
            image_info = (page.get("imageinfo") or [None])[0]
            if image_info is None:
                continue
            image_url = image_info.get("thumburl") or image_info.get("url")
            source_url = image_info.get("descriptionurl")
            if not image_url or not source_url:
                continue
            metadata = image_info.get("extmetadata") or {}
            creator = _extract_text((metadata.get("Artist") or {}).get("value"))
            license_name = _extract_text(
                (metadata.get("LicenseShortName") or {}).get("value")
            )
            attribution_required = (
                (metadata.get("AttributionRequired") or {}).get("value") or ""
            ).lower() == "true"
            attribution = None
            if attribution_required and (creator or license_name):
                attribution = " / ".join(
                    part for part in (creator, license_name) if part
                )
            title = page.get("title") or ""
            return StimulusInstance(
                activity_id=activity.id,
                provider="wikimedia_commons",
                asset_id=title or None,
                image_url=image_url,
                source_url=source_url,
                creator=creator,
                license=license_name,
                attribution=attribution,
                alt_text=_plain_title(title) or None,
                retrieved_at=resolved_at
                if resolved_at is not None
                else datetime.now(UTC),
            )
        return None


class ResilientStimulusProvider:
    """Compose a primary provider with a deterministic fallback (§21–23, §45, §50).

    If external retrieval fails for any reason, the known fallback stimulus
    is used so the learner never sees a blank activity. A stimulus failure
    therefore never corrupts the learner's activity state.
    """

    def __init__(self, primary: StimulusProvider, fallback: StimulusProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    def resolve(
        self,
        activity: AssessmentActivity,
        *,
        resolved_at: datetime | None = None,
    ) -> StimulusInstance:
        try:
            return self._primary.resolve(activity, resolved_at=resolved_at)
        except StimulusRetrievalError:
            logger.info(
                "stimulus provider failed; using fallback",
                extra={"activity_id": str(activity.id)},
            )
            return self._fallback.resolve(activity, resolved_at=resolved_at)


def build_fallback_stimuli(
    activities: tuple[DemoActivity, ...],
) -> dict[UUID, FallbackDefinition]:
    """Build a deterministic fallback stimulus per stimulus-dependent activity.

    Each fallback points at a bundled Fablit image (served from
    ``/static/images/``) so it is always available, satisfies the activity's
    learning purpose, and carries stable source/attribution metadata (§22).
    """
    fallbacks: dict[UUID, FallbackDefinition] = {}
    for item in activities:
        if item.stimulus_context is None or item.fallback_image is None:
            continue
        fallbacks[item.activity.id] = FallbackDefinition(
            asset_id=f"fablit-{item.activity.id}",
            image_url=item.fallback_image,
            source_url=FABLIT_SOURCE_URL,
            creator="Fablit",
            license="MIT",
            attribution=f"Fablit demo stimulus — {item.title}",
            alt_text=item.fallback_alt,
        )
    return fallbacks


def build_stimulus_provider(
    activities: tuple[DemoActivity, ...],
    *,
    provider_name: str = "builtin",
) -> StimulusProvider:
    """Assemble the application's stimulus provider for the given provider name.

    ``builtin`` (the default) serves deterministic bundled stimuli, keeping
    the pilot experience and the automated tests offline and reproducible.
    ``wikimedia`` enables the approved external source, composed with the
    built-in deterministic fallback for safe failure handling (§21–22).
    """
    fallback = FallbackStimulusProvider(build_fallback_stimuli(activities))
    if provider_name == "wikimedia":
        return ResilientStimulusProvider(WikimediaCommonsProvider(), fallback)
    return fallback


def _extract_text(value: str | None) -> str | None:
    """Strip HTML tags and collapse whitespace from a provider metadata value."""
    if not value:
        return None
    text = re.sub(r"<[^>]+>", "", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _plain_title(title: str) -> str:
    """Turn a Wikimedia file title into a short, plain descriptive label."""
    name = title.split(":", 1)[-1]
    name = name.rsplit(".", 1)[0]
    return name.replace("_", " ")
