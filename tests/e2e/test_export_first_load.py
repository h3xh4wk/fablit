"""Browser-level end-to-end tests for export on first page load (issue #97).

Reported bug: the "Export this practice" and "Export history as JSON"
buttons did nothing until a full page refresh. Cause: ``base.html`` enables
htmx body boosting (``hx-boost="true"``), so boosted navigation swaps page
content without re-running the ``<head>`` scripts — ``export.js`` bound its
click listeners once at initial load, before any export button existed.

These tests reproduce that exact journey: a full page load of Explore (where
``export.js`` runs with no export buttons present), completing a practice,
then reaching the export controls through boosted navigation and exporting
both artifacts. Companions to ``test_browser_journey.py``: same opt-in
browser contract (``RUN_BROWSER_TESTS=1``, same launch/server helpers) and
the same real-application server.

Covered behaviour:

- After boosted navigation to ``/history``, "Export history as JSON"
  downloads the SPEC-027 JSON payload with the completed record.
- After boosted navigation to a review page, "Export this practice"
  downloads the Markdown practice log.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Download, Page, expect, sync_playwright

from tests.e2e.test_browser_journey import (
    _free_port,
    _launch_options,
    _wait_until_ready,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_TESTS") != "1",
    reason="browser tests are opt-in (set RUN_BROWSER_TESTS=1)",
)

_RESPONSE = "The contrast between the figure and the dark background is striking."


@contextmanager
def _running_history_server() -> Iterator[str]:
    """Start Fablit with the in-memory history repository enabled.

    The shared ``_running_server`` helper keeps the application defaults,
    where practice history is disabled (``practice_history_repository``
    defaults to off), so completed practices would never appear on
    ``/history``. Exporting history requires SPEC-021 records, so these
    tests run the server with the same memory repository the web tests use.
    """
    port = _free_port()
    env = {**os.environ, "FABLIT_PRACTICE_HISTORY_REPOSITORY": "memory"}
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_ready(base_url, process)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def _complete_practice_and_reach_history(page: Page, base_url: str) -> None:
    """Full-load Explore, complete a practice, then boosted-navigate to history.

    Every navigation after the initial ``goto`` is htmx-boosted, so the
    export buttons arrive after ``export.js`` has already run — the reported
    scenario.
    """
    page.goto(base_url)
    expect(
        page.get_by_role("heading", name="What would you like to explore?", exact=True)
    ).to_be_visible()

    # Complete one practice through the boosted learner journey.
    page.get_by_role("link", name="Explore").first.click()
    expect(
        page.get_by_role("heading", name="Set an intention", exact=True)
    ).to_be_visible()
    page.get_by_role("button", name="Skip — go straight to practice").click()
    page.get_by_label("What's your reading of it?").fill(_RESPONSE)
    page.get_by_role("button", name="I'm ready").click()
    expect(
        page.get_by_role("heading", name="Something you noticed", exact=False)
    ).to_be_visible()
    page.get_by_role("link", name="Save reflection").click()
    page.get_by_label("Your reflection").fill(
        "I will explain how two elements interact next time."
    )
    page.get_by_role("button", name="Continue").click()
    expect(
        page.get_by_role("heading", name="✨ That's one done.", exact=True)
    ).to_be_visible()

    # Boosted navigation to the history page: the export section is swapped
    # into a document whose export.js listeners (pre-fix) were bound on the
    # Explore page, where no export button exists.
    page.get_by_role("link", name="Your practice", exact=True).click()
    expect(
        page.get_by_role("heading", name="Your practice", exact=True)
    ).to_be_visible()
    expect(page.get_by_role("button", name="Export history as JSON")).to_be_visible()


def test_history_export_works_after_boosted_navigation() -> None:
    with _running_history_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = browser.new_page(accept_downloads=True)
            _complete_practice_and_reach_history(page, base_url)

            with page.expect_download() as download_info:
                page.get_by_role("button", name="Export history as JSON").click()
            download: Download = download_info.value

            assert download.suggested_filename.startswith(
                "fablit-history-export-private-learner-"
            )
            assert download.suggested_filename.endswith(".json")

            path = download.path()
            assert path is not None
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            assert payload["specVersion"] == "027"
            assert len(payload["records"]) == 1
            assert payload["records"][0]["learner_response"] == _RESPONSE
        finally:
            browser.close()


def test_session_export_works_after_boosted_navigation() -> None:
    with _running_history_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = browser.new_page(accept_downloads=True)
            _complete_practice_and_reach_history(page, base_url)

            # Boosted navigation from history into the review page, then
            # export the single practice as Markdown.
            page.get_by_role("link", name="Review this practice").first.click()
            expect(
                page.get_by_role("button", name="Export this practice")
            ).to_be_visible()

            with page.expect_download() as download_info:
                page.get_by_role("button", name="Export this practice").click()
            download: Download = download_info.value

            assert download.suggested_filename.startswith("fablit-session-")
            assert download.suggested_filename.endswith(".md")

            path = download.path()
            assert path is not None
            markdown = Path(path).read_text(encoding="utf-8")
            assert markdown.startswith("# Practice Log: ")
            assert _RESPONSE in markdown
            assert "## 4. Learner Reflection" in markdown
            assert "I will explain how two elements interact next time." in markdown
        finally:
            browser.close()
