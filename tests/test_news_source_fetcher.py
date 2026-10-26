"""Deterministic tests for the SPEC-041 HTTP source fetcher."""

from __future__ import annotations

import urllib.error
from collections.abc import Mapping
from email.message import Message
from unittest.mock import Mock

import pytest

from fablit.application.errors import NewsSourceFetchError
from fablit.application.news_sources import NewsSource
from fablit.platform.news_source_fetcher import (
    HttpNewsSourceFetcher,
    _SafeRedirectHandler,
)

SOURCE = NewsSource(
    name="The Daily Weave",
    feed_url="https://news.example.com/feed.xml",
    site_url="https://news.example.com",
)

RSS_PAYLOAD = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>The Daily Weave</title>
    <item>
      <title>Handloom revival</title>
      <link>https://news.example.com/story/1</link>
      <pubDate>Mon, 19 Oct 2026 09:00:00 GMT</pubDate>
      <description>&lt;p&gt;A collective is helping
      &lt;b&gt;weavers&lt;/b&gt;.&lt;/p&gt;</description>
    </item>
    <item>
      <title>No link item</title>
      <pubDate>Mon, 19 Oct 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Material innovation</title>
      <link>https://news.example.com/story/2</link>
      <description>A new fibre.</description>
    </item>
  </channel>
</rss>
"""

ATOM_PAYLOAD = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Craft Journal</title>
  <entry>
    <title>Craft residency opens</title>
    <link rel="alternate" href="https://craft.example.org/story/1"/>
    <published>2026-10-18T08:30:00Z</published>
    <summary>A residency for makers.</summary>
  </entry>
</feed>
"""


def _fetcher(
    payload: bytes = RSS_PAYLOAD,
    *,
    addresses: tuple[str, ...] = ("93.184.216.34",),
    max_response_bytes: int = 512_000,
) -> tuple[HttpNewsSourceFetcher, Mock]:
    transport = Mock(return_value=payload)
    fetcher = HttpNewsSourceFetcher(
        transport=transport,
        resolver=lambda host: addresses,
        max_response_bytes=max_response_bytes,
    )
    return fetcher, transport


def test_rss_feed_is_parsed_into_bounded_items() -> None:
    fetcher, transport = _fetcher()

    items = fetcher.fetch(SOURCE)

    assert len(items) == 2
    assert items[0].source_name == SOURCE.name
    assert items[0].title == "Handloom revival"
    assert items[0].url == "https://news.example.com/story/1"
    assert items[0].published_at is not None
    assert items[0].published_at.isoformat() == "2026-10-19T09:00:00+00:00"
    assert items[0].excerpt == "A collective is helping weavers."
    assert items[1].published_at is None
    transport.assert_called_once()
    _, headers = transport.call_args.args
    assert "FablitNewsCuration" in headers["User-Agent"]


def test_atom_feed_is_parsed() -> None:
    fetcher, _ = _fetcher(ATOM_PAYLOAD)

    items = fetcher.fetch(SOURCE)

    assert len(items) == 1
    assert items[0].title == "Craft residency opens"
    assert items[0].url == "https://craft.example.org/story/1"
    assert items[0].published_at is not None
    assert items[0].published_at.isoformat() == "2026-10-18T08:30:00+00:00"


def test_malformed_xml_is_reported_safely() -> None:
    fetcher, _ = _fetcher(b"<rss><channel>")

    with pytest.raises(NewsSourceFetchError, match="could not be read"):
        fetcher.fetch(SOURCE)


def test_a_non_feed_document_is_refused() -> None:
    fetcher, _ = _fetcher(b"<html><body>Not a feed</body></html>")

    with pytest.raises(NewsSourceFetchError, match="not a recognized feed"):
        fetcher.fetch(SOURCE)


def test_doctype_and_entity_declarations_are_refused() -> None:
    fetcher, _ = _fetcher(b"<!DOCTYPE rss [<!ENTITY x 'x'>]><rss/>")

    with pytest.raises(NewsSourceFetchError, match="unsupported XML features"):
        fetcher.fetch(SOURCE)


def test_oversized_response_is_refused_before_parsing() -> None:
    fetcher, _ = _fetcher(b"x" * 2048, max_response_bytes=1024)

    with pytest.raises(NewsSourceFetchError, match="too large"):
        fetcher.fetch(SOURCE)


def test_private_or_loopback_resolution_is_refused_before_fetch() -> None:
    fetcher, transport = _fetcher(addresses=("127.0.0.1",))

    with pytest.raises(NewsSourceFetchError, match="not public"):
        fetcher.fetch(SOURCE)

    transport.assert_not_called()


def test_unsafe_source_url_is_refused_before_fetch() -> None:
    fetcher, transport = _fetcher()
    unsafe = NewsSource(
        name="Local",
        feed_url="https://public.example.com/rss",
        site_url="https://public.example.com",
    )
    object.__setattr__(unsafe, "feed_url", "http://localhost/rss")

    with pytest.raises(NewsSourceFetchError, match="safe public URL"):
        fetcher.fetch(unsafe)

    transport.assert_not_called()


def test_redirect_to_a_private_destination_is_refused() -> None:
    fetcher, _ = _fetcher()
    handler = _SafeRedirectHandler(fetcher._validate_destination)

    with pytest.raises(NewsSourceFetchError, match="safe public URL"):
        handler.redirect_request(
            Mock(),
            None,
            302,
            "Found",
            Message(),
            "http://private.example.local/rss",
        )


def test_http_error_is_translated_without_leaking_the_body() -> None:
    def failing_transport(url: str, headers: Mapping[str, str]) -> bytes:
        raise urllib.error.HTTPError(url, 500, "server error", Message(), None)

    fetcher = HttpNewsSourceFetcher(
        transport=failing_transport,
        resolver=lambda host: ("93.184.216.34",),
    )

    with pytest.raises(NewsSourceFetchError, match="status 500"):
        fetcher.fetch(SOURCE)


def test_empty_feed_returns_no_items() -> None:
    fetcher, _ = _fetcher(
        b'<rss version="2.0"><channel><title>Empty</title></channel></rss>'
    )

    assert fetcher.fetch(SOURCE) == ()


def test_fetcher_constructor_rejects_unsafe_bounds() -> None:
    with pytest.raises(ValueError, match="timeout"):
        HttpNewsSourceFetcher(timeout=0)
    with pytest.raises(ValueError, match="max_response_bytes"):
        HttpNewsSourceFetcher(max_response_bytes=10)
