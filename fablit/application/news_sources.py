"""Approved news sources, fetched source items, and URL safety (SPEC-041).

The news feature only ever reads from an explicit allowlist of sources. This
module owns the provider-neutral representation of those sources, the bounded
items a source returns, and the deterministic URL rules the curation workflow
applies before anything is sent to an AI provider or persisted:

- only absolute HTTP(S) links are accepted;
- credentials in a URL, unsupported ports, loopback/private/link-local hosts,
  and local-only hostnames are rejected;
- a story link must belong to the publisher host of the source that supplied
  it.

Fetching itself lives in a platform adapter behind
:class:`NewsSourceFetcher`, so the workflow and its tests never depend on the
network.
"""

from __future__ import annotations

import ipaddress
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit, urlunsplit

from .errors import InvalidNewsSourceError, UnsafeNewsUrlError


@dataclass(frozen=True)
class NewsSource:
    """One approved publisher source and the host its story links may use."""

    name: str
    feed_url: str
    site_url: str | None = None

    def __post_init__(self) -> None:
        """Normalize and validate the source identity and URLs."""
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidNewsSourceError("news source name must be non-blank text")
        object.__setattr__(self, "name", " ".join(self.name.split()))
        object.__setattr__(self, "feed_url", normalize_http_url(self.feed_url))
        if self.site_url is not None:
            object.__setattr__(self, "site_url", normalize_http_url(self.site_url))

    @property
    def publisher_url(self) -> str:
        """The publisher site, defaulting to the feed's own host."""
        return self.site_url or self.feed_url

    @property
    def publisher_host(self) -> str:
        """The host a story link must belong to (or be a subdomain of)."""
        host = urlsplit(self.publisher_url).hostname
        if not host:  # pragma: no cover - normalize_http_url guarantees a host
            raise InvalidNewsSourceError(
                f"news source {self.name!r} has no publisher host"
            )
        return host.lower()


@dataclass(frozen=True)
class NewsSourceItem:
    """One untrusted item fetched from an approved source (SPEC-041 §5.2)."""

    source_name: str
    title: str
    url: str
    published_at: datetime | None = None
    excerpt: str = ""

    def __post_init__(self) -> None:
        """Require the fields every candidate must carry to be considered."""
        for name in ("source_name", "title", "url"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise ValueError(f"news source item {name} must be text")
        if self.published_at is not None and not isinstance(
            self.published_at, datetime
        ):
            raise ValueError("news source item published_at must be a datetime")
        if not isinstance(self.excerpt, str):
            raise ValueError("news source item excerpt must be text")


@runtime_checkable
class NewsSourceFetcher(Protocol):
    """Provider-neutral port for retrieving an approved source (SPEC-041 §6.1)."""

    def fetch(self, source: NewsSource) -> tuple[NewsSourceItem, ...]:
        """Return bounded items from the source.

        Raises:
            NewsSourceFetchError: When the source cannot be retrieved or its
                payload cannot be read. The workflow records the source as
                failed and continues with the remaining sources.
        """
        ...


class FakeNewsSourceFetcher:
    """Deterministic in-process fetcher for tests and local development.

    Items are keyed by feed URL; an injected error simulates an unavailable
    source without any network access.
    """

    def __init__(
        self,
        items: Mapping[str, Iterable[NewsSourceItem]] | None = None,
        *,
        default: Iterable[NewsSourceItem] = (),
        errors: Mapping[str, Exception] | None = None,
    ) -> None:
        self._items = {key: tuple(value) for key, value in (items or {}).items()}
        self._default = tuple(default)
        self._errors = dict(errors or {})

    def fetch(self, source: NewsSource) -> tuple[NewsSourceItem, ...]:
        error = self._errors.get(source.feed_url)
        if error is not None:
            raise error
        return self._items.get(source.feed_url, self._default)


def normalize_http_url(value: object) -> str:
    """Normalize an absolute HTTP(S) URL or raise :class:`UnsafeNewsUrlError`."""
    if not isinstance(value, str):
        raise UnsafeNewsUrlError("news links must be text")
    candidate = value.strip()
    if not candidate or any(character in candidate for character in "\r\n\t"):
        raise UnsafeNewsUrlError("news links must be a single absolute URL")
    try:
        parts = urlsplit(candidate)
    except ValueError as exc:
        raise UnsafeNewsUrlError("news link could not be parsed") from exc

    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise UnsafeNewsUrlError(
            f"unsupported news link scheme: {parts.scheme or '(none)'}"
        )
    if not parts.hostname:
        raise UnsafeNewsUrlError("news link must include a host")
    if parts.username is not None or parts.password is not None:
        raise UnsafeNewsUrlError("news links must not contain credentials")

    host = parts.hostname.lower().rstrip(".")
    if host_is_blocked(host):
        raise UnsafeNewsUrlError(f"news link host is not public: {host}")

    try:
        port = parts.port
    except ValueError as exc:
        raise UnsafeNewsUrlError("news link has an invalid port") from exc
    default_port = 80 if scheme == "http" else 443
    if port is not None and port != default_port:
        raise UnsafeNewsUrlError(f"unsupported news link port: {port}")

    path = parts.path or "/"
    if "\\" in path:
        raise UnsafeNewsUrlError("news link path is not supported")
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def is_safe_news_url(value: object) -> bool:
    """Whether a value is an absolute, public HTTP(S) URL we may fetch."""
    try:
        normalize_http_url(value)
    except UnsafeNewsUrlError:
        return False
    return True


def host_is_blocked(host: str) -> bool:
    """Whether a host is loopback, private, link-local, reserved, or local-only."""
    normalized = host.strip().strip("[]").lower().rstrip(".")
    if not normalized:
        return True
    if normalized in {"localhost", "localhost.localdomain"}:
        return True
    if normalized.endswith((".localhost", ".local", ".internal", ".localdomain")):
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return not address.is_global


def link_belongs_to_source(url: str, source: NewsSource) -> bool:
    """Whether a story link belongs to the source's publisher host."""
    host = urlsplit(url).hostname
    if not host:
        return False
    normalized = host.lower().rstrip(".")
    publisher = source.publisher_host
    return normalized == publisher or normalized.endswith(f".{publisher}")


def parse_news_sources(value: object) -> tuple[NewsSource, ...]:
    """Parse configured sources from a JSON string or a list of objects.

    Each entry needs a ``name`` and a ``feed_url``; ``site_url`` is optional
    and names the publisher host used to validate story links. Unknown keys,
    duplicates, and unsafe URLs are refused rather than ignored, so a
    misconfiguration is visible at startup instead of silently shrinking the
    allowlist.
    """
    if value is None:
        return ()
    parsed: object = value
    if isinstance(value, str):
        if not value.strip():
            return ()
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise InvalidNewsSourceError(
                f"news sources must be valid JSON: {exc}"
            ) from exc
    if isinstance(parsed, (list, tuple)):
        entries = parsed
    elif isinstance(parsed, Mapping) and "sources" in parsed:
        entries = parsed["sources"]
    else:
        raise InvalidNewsSourceError(
            "news sources must be a JSON list of {name, feed_url, site_url} objects"
        )
    if not isinstance(entries, (list, tuple)):
        raise InvalidNewsSourceError("news sources must be a list")

    sources: list[NewsSource] = []
    seen: set[str] = set()
    for entry in entries:
        source = _parse_source(entry)
        if source.feed_url in seen:
            raise InvalidNewsSourceError(
                f"duplicate news source feed: {source.feed_url}"
            )
        seen.add(source.feed_url)
        sources.append(source)
    return tuple(sources)


def _parse_source(entry: object) -> NewsSource:
    if isinstance(entry, NewsSource):
        return entry
    if not isinstance(entry, Mapping):
        raise InvalidNewsSourceError("each news source must be an object")
    unsupported = set(entry) - {"name", "feed_url", "site_url"}
    if unsupported:
        raise InvalidNewsSourceError(
            "unsupported news source fields: " + ", ".join(sorted(unsupported))
        )
    name = entry.get("name")
    feed_url = entry.get("feed_url")
    site_url = entry.get("site_url")
    if not isinstance(name, str) or not isinstance(feed_url, str):
        raise InvalidNewsSourceError("each news source needs a text name and feed_url")
    if site_url is not None and not isinstance(site_url, str):
        raise InvalidNewsSourceError("news source site_url must be text when provided")
    try:
        return NewsSource(name=name, feed_url=feed_url, site_url=site_url)
    except UnsafeNewsUrlError as exc:
        raise InvalidNewsSourceError(str(exc)) from exc


#: Characters trimmed from source text before use in matching.
_TRIM_PATTERN = re.compile(r"^[\s\W_]+|[\s\W_]+$")


def normalize_terms(text: str) -> str:
    """Lowercase and collapse whitespace so grounding checks are stable."""
    return " ".join(text.split()).casefold()


def term_is_grounded(term: str, evidence: str) -> bool:
    """Whether a provider-supplied grounding term occurs in source evidence."""
    needle = normalize_terms(_TRIM_PATTERN.sub("", term))
    if not needle:
        return False
    return needle in evidence


#: A conservative starting allowlist: two public publisher feeds whose reuse
#: terms (headline, short summary, attribution, and a link back) are
#: understood. Operators may override the list through configuration.
DEFAULT_NEWS_SOURCES: tuple[NewsSource, ...] = (
    NewsSource(
        name="The Guardian — Fashion",
        feed_url="https://www.theguardian.com/fashion/rss",
        site_url="https://www.theguardian.com",
    ),
    NewsSource(
        name="The Guardian — Art & Design",
        feed_url="https://www.theguardian.com/artanddesign/rss",
        site_url="https://www.theguardian.com",
    ),
)
