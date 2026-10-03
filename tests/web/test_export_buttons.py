"""Web tests for the export surfaces (issue #97 — export on first page load).

The export controls are client-driven (`app/static/js/export.js`), so these
tests only guard the server-rendered wiring the client depends on:

- the export button and its `<script type="application/json">` data node
  render on the history page and on the review page once a practice exists;
- `export.js` is loaded from `base.html` on every page. This matters for the
  reported bug: with `hx-boost="true"`, navigating swaps page content without
  re-running head scripts, so the module must be present from the first full
  page load and must not be moved into the pages that use it.

The click behaviour itself is covered by the opt-in browser test in
`tests/e2e/test_export_first_load.py`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from fablit.config import load_config


def _history_client() -> TestClient:
    """A TestClient running the app with the in-memory history repository."""
    test_config = load_config(overrides={"practice_history_repository": "memory"})
    test_app = create_app(test_config)
    return TestClient(test_app)


def _first_activity_href(dashboard_html: str) -> str:
    """Extract the first activity href from the dashboard page."""
    href = "/activities/" + dashboard_html.split('href="/activities/')[1].split('"')[0]
    # Card actions lead through the SPEC-026 intention prompt; the journeys
    # here drive the practice activity itself, so drop the intention suffix.
    return href.removesuffix("/intention")


def _complete_first_practice(client: TestClient, response: str) -> str:
    """Complete one practice journey through the web layer; return its review href."""
    dashboard = client.get("/")
    href = _first_activity_href(dashboard.text)
    client.post(href + "/submit", data={"response": response})
    client.post("/reflect", data={"content": "I will look for balance next time."})
    history = client.get("/history")
    for line in history.text.splitlines():
        if 'href="/history/' in line:
            return line.split('href="')[1].split('"')[0]
    raise AssertionError("no history entry link found after completion")


def test_export_module_is_loaded_on_every_page() -> None:
    """export.js ships from base.html, before any boosted navigation happens."""
    with _history_client() as client:
        dashboard = client.get("/")
        history = client.get("/history")

    for page in (dashboard, history):
        assert page.status_code == 200
        assert '<script src="/static/js/export.js" defer></script>' in page.text


def test_history_page_renders_export_button_and_data() -> None:
    with _history_client() as client:
        _complete_first_practice(client, "The contrast is striking.")
        history = client.get("/history")

    assert history.status_code == 200
    assert 'class="button button--secondary js-export-history"' in history.text
    assert '<script type="application/json" id="fablit-history-export-data">' in (
        history.text
    )


def test_empty_history_renders_no_export_section() -> None:
    """Without completed practices there is nothing to export."""
    with _history_client() as client:
        history = client.get("/history")

    assert history.status_code == 200
    assert "js-export-history" not in history.text
    assert "fablit-history-export-data" not in history.text


def test_review_page_renders_export_button_and_data() -> None:
    with _history_client() as client:
        review_href = _complete_first_practice(client, "A considered response.")
        review = client.get(review_href)

    assert review.status_code == 200
    assert 'class="button button--secondary js-export-session"' in review.text
    assert '<script type="application/json" id="fablit-session-export-data">' in (
        review.text
    )
