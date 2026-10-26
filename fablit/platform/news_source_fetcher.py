"""Bounded HTTP retrieval of approved news sources (SPEC-041 §8).

The curation workflow never talks to the network itself. This adapter owns the
untrusted part: fetching one configured publisher feed with a bounded timeout
and response size, refusing private/loopback destinations, validating redirect
targets, and parsing RSS/Atom into the neutral
:class:`~fablit.application.news_sources.NewsSourceItem` records.

It deliberately uses the standard library and an injectable transport and
resolver, so the tests exercise redirect refusal, size limits, malformed
payloads, and date handling without any live request.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any, Final
from urllib.parse import urlsplit

from fablit.application.errors import NewsSourceFetchError
from fablit.application.news import MAX_SOURCE_ITEMS
from fablit.application.news_sources import (
    NewsSource,
    NewsSourceItem,
    normalize_http_url,
)

#: Transport signature: ``(url, headers) -> response_bytes``.
FeedTransport = Callable[[str, Mapping[str, str]], bytes]

#: Resolver signature: ``(host) -> resolved addresses``.
FeedResolver = Callable[[str], Sequence[str]]

#: Default browser-ish identity; publishers may refuse a bare Python client.
USER_AGENT: Final[str] = "FablitNewsCuration/1.0 (+https://fablit.app)"

#: A feed item excerpt is only curation input, never republished.
MAX_EXCERPT_CHARS: Final[int] = 4000
MAX_FEED_TITLE_CHARS: Final[int] = 300


class _TextExtractor(HTMLParser):
    """Collect visible text from a snippet without keeping markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    @property
    def text(self) -> str:
        return " ".join("".join(self._parts).split())


def _clean_text(value: str, *, limit: int) -> str:
    """Strip markup and bound an untrusted source text field."""
    extractor = _TextExtractor()
    try:
        extractor.feed(value)
        extractor.close()
        text = extractor.text
    except Exception:
        text = " ".join(value.split())
    return text[:limit]


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect whose destination is not a safe public URL."""

    def __init__(self, validate_destination: Callable[[str], None]) -> None:
        self._validate_destination = validate_destination

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        self._validate_destination(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpNewsSourceFetcher:
    """Fetch approved publisher feeds over HTTP(S) with safety bounds."""

    def __init__(
        self,
        *,
        timeout: float = 10.0,
        max_response_bytes: int = 512_000,
        transport: FeedTransport | None = None,
        resolver: FeedResolver | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("news fetch timeout must be positive")
        if max_response_bytes < 1024:
            raise ValueError("news fetch max_response_bytes must be at least 1024")
        self._timeout = timeout
        self._max_response_bytes = max_response_bytes
        self._transport = transport or self._default_transport
        self._resolver = resolver or _default_resolver

    def fetch(self, source: NewsSource) -> tuple[NewsSourceItem, ...]:
        """Retrieve and parse one approved source, or raise a safe error."""
        self._validate_destination(source.feed_url)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml, application/atom+xml, application/xml, text/xml"
            ),
        }
        try:
            payload = self._transport(source.feed_url, headers)
        except NewsSourceFetchError:
            raise
        except urllib.error.HTTPError as exc:
            raise NewsSourceFetchError(
                f"source could not be retrieved (status {exc.code})"
            ) from exc
        except Exception as exc:
            raise NewsSourceFetchError("source could not be retrieved") from exc

        if not isinstance(payload, bytes):
            raise NewsSourceFetchError("source returned an unreadable response")
        if len(payload) > self._max_response_bytes:
            raise NewsSourceFetchError("source response is too large")
        if b"<!doctype" in payload.lower() or b"<!entity" in payload.lower():
            raise NewsSourceFetchError("source response uses unsupported XML features")
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as exc:
            raise NewsSourceFetchError("source response could not be read") from exc

        items = _feed_items(root)
        if items is None:
            raise NewsSourceFetchError("source response is not a recognized feed")
        return tuple(
            item
            for item in (
                _parse_item(entry, source, root_tag=root.tag) for entry in items
            )
            if item is not None
        )[:MAX_SOURCE_ITEMS]

    def _validate_destination(self, url: str) -> None:
        """Validate a URL and every address its host currently resolves to."""
        try:
            normalized = normalize_http_url(url)
        except Exception as exc:
            raise NewsSourceFetchError("source link is not a safe public URL") from exc
        host = urlsplit(normalized).hostname
        if not host:  # pragma: no cover - normalize_http_url guarantees it
            raise NewsSourceFetchError("source link is not a safe public URL")
        try:
            addresses = self._resolver(host)
        except Exception as exc:
            raise NewsSourceFetchError("source host could not be resolved") from exc
        if not addresses:
            raise NewsSourceFetchError("source host could not be resolved")
        for address in addresses:
            try:
                parsed = ipaddress.ip_address(address.split("%", 1)[0])
            except ValueError as exc:
                raise NewsSourceFetchError("source host is not public") from exc
            if not parsed.is_global:
                raise NewsSourceFetchError("source host is not public")

    def _default_transport(self, url: str, headers: Mapping[str, str]) -> bytes:
        opener = urllib.request.build_opener(
            _SafeRedirectHandler(self._validate_destination)
        )
        request = urllib.request.Request(
            url,
            headers=dict(headers),
            method="GET",
        )
        with opener.open(request, timeout=self._timeout) as response:
            payload: bytes = response.read(self._max_response_bytes + 1)
        return payload


def _default_resolver(host: str) -> tuple[str, ...]:
    infos = socket.getaddrinfo(host, None)
    return tuple(str(info[4][0]) for info in infos if info[4])


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _feed_items(root: ElementTree.Element) -> list[ElementTree.Element] | None:
    root_name = _local_name(root.tag)
    if root_name == "rss":
        channel = next(
            (child for child in root if _local_name(child.tag) == "channel"), None
        )
        if channel is None:
            return None
        return [child for child in channel if _local_name(child.tag) == "item"]
    if root_name == "feed":
        return [child for child in root if _local_name(child.tag) == "entry"]
    if root_name == "rdf":
        return [child for child in root if _local_name(child.tag) == "item"]
    return None


def _child_text(entry: ElementTree.Element, *names: str) -> str:
    for child in entry:
        if _local_name(child.tag) in names:
            text = child.text or ""
            if text.strip():
                return text.strip()
    return ""


def _entry_link(entry: ElementTree.Element) -> str:
    for child in entry:
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        rel = child.attrib.get("rel", "alternate")
        if href and rel in {"alternate", ""}:
            return href.strip()
        if child.text and child.text.strip():
            return child.text.strip()
    return ""


def _parse_item(
    entry: ElementTree.Element,
    source: NewsSource,
    *,
    root_tag: str,
) -> NewsSourceItem | None:
    title = _clean_text(_child_text(entry, "title"), limit=MAX_FEED_TITLE_CHARS)
    url = _entry_link(entry).strip()
    if not title or not url:
        return None
    excerpt = _clean_text(
        _child_text(entry, "description", "summary", "content", "encoded"),
        limit=MAX_EXCERPT_CHARS,
    )
    published_at = _entry_date(entry, root_tag=root_tag)
    return NewsSourceItem(
        source_name=source.name,
        title=title,
        url=url,
        published_at=published_at,
        excerpt=excerpt,
    )


def _entry_date(entry: ElementTree.Element, *, root_tag: str) -> datetime | None:
    if _local_name(root_tag) in {"rss", "rdf"}:
        raw = _child_text(entry, "pubdate", "date")
        return _parse_rss_date(raw)
    raw = _child_text(entry, "published", "updated")
    return _parse_iso_date(raw)


def _parse_rss_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    return _as_utc(parsed)


def _parse_iso_date(value: str) -> datetime | None:
    if not value:
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return _as_utc(datetime.fromisoformat(candidate))
    except ValueError:
        return None


def _as_utc(value: datetime) -> datetime | None:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
