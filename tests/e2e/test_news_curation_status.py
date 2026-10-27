"""Browser tests for the author-facing durable curation status UI (SPEC-042 / #166).

These opt-in tests exercise real browser polling and navigation against
controlled responses. They never call Gemini, Cloud Tasks, or Datastore.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Route, expect, sync_playwright

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_TESTS") != "1",
    reason="browser tests are opt-in (set RUN_BROWSER_TESTS=1)",
)

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "static"
    / "js"
    / "news-curation-status.js"
)


def test_status_recovers_from_temporary_failure_and_reloads_final_report() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    page_requests = 0
    status_requests = 0

    def page_html(*, terminal: bool) -> str:
        status = "succeeded" if terminal else "queued"
        label = "Completed" if terminal else "Queued"
        report = (
            '<section id="curation-batch-report">Final report is available.</section>'
            if terminal
            else ""
        )
        return (
            '<!doctype html><html lang="en"><body>'
            '<main id="main">'
            '<section id="curation-job-status"'
            ' data-job-id="job-1"'
            f' data-job-status="{status}"'
            f' data-job-terminal="{"true" if terminal else "false"}">'
            f'<p><strong id="curation-status-label">{label}</strong> — '
            '<span id="curation-status-message">Waiting to start.</span></p>'
            '<p id="curation-poll-message" hidden></p>'
            '<p id="curation-error-message" hidden></p>'
            '<strong id="curation-sources-processed">0</strong>'
            '<strong id="curation-sources-total">1</strong>'
            '<strong id="curation-items-fetched">0</strong>'
            '<strong id="curation-items-deduplicated">0</strong>'
            '<strong id="curation-items-published">0</strong>'
            '<strong id="curation-items-rejected">0</strong>'
            '<strong id="curation-items-failed">0</strong>'
            "</section>"
            f"{report}"
            "</main>"
            f"<script>{script}</script>"
            "</body></html>"
        )

    def handle_page(route: Route) -> None:
        nonlocal page_requests
        page_requests += 1
        route.fulfill(
            status=200,
            content_type="text/html",
            body=page_html(terminal=page_requests > 1),
        )

    def handle_status(route: Route) -> None:
        nonlocal status_requests
        status_requests += 1
        if status_requests == 1:
            route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"temporarily unavailable"}',
            )
            return

        if status_requests == 2:
            payload = {
                "job_id": "job-1",
                "status": "running",
                "status_label": "Running",
                "stage": "curating_items",
                "message": "Checking and curating eligible stories.",
                "is_terminal": False,
                "counters": {
                    "sources_configured": 1,
                    "sources_processed": 1,
                    "sources_failed": 0,
                    "items_fetched": 3,
                    "items_deduplicated": 1,
                    "items_published": 1,
                    "items_rejected": 1,
                    "items_failed": 0,
                },
                "error": None,
            }
        else:
            payload = {
                "job_id": "job-1",
                "status": "succeeded",
                "status_label": "Completed",
                "stage": "done",
                "message": "Curation completed.",
                "is_terminal": True,
                "counters": {
                    "sources_configured": 1,
                    "sources_processed": 1,
                    "sources_failed": 0,
                    "items_fetched": 3,
                    "items_deduplicated": 1,
                    "items_published": 1,
                    "items_rejected": 1,
                    "items_failed": 0,
                },
                "error": None,
            }
        route.fulfill(status=200, content_type="application/json", json=payload)

    with sync_playwright() as playwright:
        launch_options: dict[str, Any] = {"headless": True}
        if os.environ.get("PLAYWRIGHT_NO_SANDBOX") == "1":
            launch_options["args"] = ["--no-sandbox"]
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page()
        # Speed up only this test's polling clock; application logic is unchanged.
        page.add_init_script(
            "const originalSetTimeout = window.setTimeout.bind(window);"
            "window.setTimeout = (callback, delay, ...args) => "
            "originalSetTimeout(callback, Math.min(delay, 250), ...args);"
        )
        page.route("https://fablit.test/authoring/pulse", handle_page)
        page.route("https://fablit.test/authoring/pulse/jobs/job-1", handle_status)
        try:
            page.goto("https://fablit.test/authoring/pulse")

            expect(page.locator("#curation-poll-message")).to_contain_text(
                "temporarily unavailable"
            )
            expect(page.locator("#curation-status-label")).to_have_text("Running")
            expect(page.locator("#curation-items-fetched")).to_have_text("3")
            expect(page.locator("#curation-items-published")).to_have_text("1")
            expect(page.locator("#curation-batch-report")).to_contain_text(
                "Final report is available."
            )
            assert page_requests == 2
            assert status_requests == 3
        finally:
            browser.close()
