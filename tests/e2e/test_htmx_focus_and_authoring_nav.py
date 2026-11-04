"""Browser tests for HTMX focus, status roles, and authoring nav (SPEC-046 Slice 1).

Exercises real HTMX boosted navigation, targeted ``#main`` swaps, error-page swaps,
and authoring navigation ``aria-current="page"`` across desktop and mobile viewports
in Chromium. Skipped unless ``RUN_BROWSER_TESTS=1`` is set.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from playwright.sync_api import Browser, Page, Route, expect, sync_playwright

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_TESTS") != "1",
    reason="browser tests are opt-in (set RUN_BROWSER_TESTS=1)",
)

AUTHORING_SECRET = "e2e-spec-046-authoring-secret"


@contextmanager
def _running_server() -> Iterator[str]:
    """Start the Fablit application on a free port with authoring enabled."""
    port = _free_port()
    env = {
        **os.environ,
        "FABLIT_AUTHORING_SECRET": AUTHORING_SECRET,
    }
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


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_ready(base_url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"application server exited early (code {process.returncode})"
            )
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.2)
    raise RuntimeError("application server did not become ready in time")


def _launch_options() -> dict[str, Any]:
    options: dict[str, Any] = {}
    executable = os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH")
    if executable:
        options["executable_path"] = executable
    if os.environ.get("PLAYWRIGHT_NO_SANDBOX") == "1":
        options["args"] = ["--no-sandbox"]
    return options


def _verify_boosted_navigation_focus(page: Page, base_url: str) -> None:
    """Verify boosted navigation moves focus to main h1 without scroll jumps."""
    page.goto(base_url)
    expect(
        page.get_by_role("heading", name="What would you like to explore?", exact=True)
    ).to_be_visible()

    # Navigate via boosted header link to Stories (/news)
    page.get_by_role("link", name="Stories", exact=True).click()
    stories_h1 = page.get_by_role(
        "heading", name="Fashion & Design Pulse", exact=True, level=1
    )
    expect(stories_h1).to_be_visible()
    expect(stories_h1).to_be_focused()
    assert page.evaluate("() => window.scrollY") == 0

    # Navigate via boosted header link to Your practice (/history)
    page.get_by_role("link", name="Your practice", exact=True).click()
    history_h1 = page.get_by_role("heading", level=1)
    expect(history_h1).to_be_visible()
    expect(history_h1).to_be_focused()

    # Navigate back to Practice (/) via boosted header link
    page.get_by_role("link", name="Practice", exact=True).click()
    home_h1 = page.get_by_role(
        "heading", name="What would you like to explore?", exact=True
    )
    expect(home_h1).to_be_visible()
    expect(home_h1).to_be_focused()

    # Pressing Tab from the focused h1 moves directly into main content links
    # rather than restarting at the top of <body>.
    page.keyboard.press("Tab")
    expect(
        page.get_by_role("link", name="Choose how you'd like to practise")
    ).to_be_focused()

    # Browser back/forward navigation stays intact
    page.go_back()
    expect(page).to_have_url(f"{base_url}/history")
    page.go_forward()
    expect(page).to_have_url(f"{base_url}/")


def test_boosted_navigation_focus_desktop_and_mobile() -> None:
    """SPEC-046 §6.1 / F-20: boosted nav focuses main h1 on desktop and mobile."""
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            desktop_page = browser.new_page(viewport={"width": 1280, "height": 800})
            _verify_boosted_navigation_focus(desktop_page, base_url)

            mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
            _verify_boosted_navigation_focus(mobile_page, base_url)
        finally:
            browser.close()


def test_authoring_navigation_aria_current_and_brief_draft_focus() -> None:
    """SPEC-046 §6.2, §6.4, §6.5: authoring nav aria-current and #main swap focus."""
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"{base_url}/authoring/login")
            page.get_by_label("Authoring Secret").fill(AUTHORING_SECRET)
            page.get_by_role("button", name="Access Authoring Workspace").click()

            expect(
                page.get_by_role(
                    "heading", name="Internal Authoring Workspace", exact=True
                )
            ).to_be_visible()

            # Check aria-current="page" on Candidate workspace
            nav = page.get_by_role("navigation", name="Authoring navigation")
            expect(
                nav.get_by_role("link", name="Candidate workspace")
            ).to_have_attribute("aria-current", "page")
            expect(
                nav.get_by_role("link", name="Learning Guides")
            ).not_to_have_attribute("aria-current", "page")
            expect(
                nav.get_by_role("link", name="Fashion & Design Pulse")
            ).not_to_have_attribute("aria-current", "page")

            # Navigate to Learning Guides via boosted authoring nav
            nav.get_by_role("link", name="Learning Guides").click()
            guides_h1 = page.get_by_role(
                "heading", name="Learning Guides", exact=True, level=1
            )
            expect(guides_h1).to_be_focused()
            expect(nav.get_by_role("link", name="Learning Guides")).to_have_attribute(
                "aria-current", "page"
            )
            expect(
                nav.get_by_role("link", name="Candidate workspace")
            ).not_to_have_attribute("aria-current", "page")

            # Navigate to Fashion & Design Pulse via boosted authoring nav
            nav.get_by_role("link", name="Fashion & Design Pulse").click()
            pulse_h1 = page.get_by_role(
                "heading", name="Fashion & Design Pulse", exact=True, level=1
            )
            expect(pulse_h1).to_be_focused()
            expect(
                nav.get_by_role("link", name="Fashion & Design Pulse")
            ).to_have_attribute("aria-current", "page")
            expect(
                nav.get_by_role("link", name="Candidate workspace")
            ).not_to_have_attribute("aria-current", "page")

            # Return to Candidate workspace
            nav.get_by_role("link", name="Candidate workspace").click()
            workspace_h1 = page.get_by_role(
                "heading", name="Internal Authoring Workspace", exact=True, level=1
            )
            expect(workspace_h1).to_be_focused()

            # Targeted #main swap: submitting empty notes to /authoring/brief/draft
            # returns 422 and moves focus to the [data-focus-target] alert banner.
            page.get_by_role("button", name="Draft the brief").click()
            error_banner = page.locator(
                ".validation-panel--error[data-focus-target][role='alert']"
            )
            expect(error_banner).to_be_visible()
            expect(error_banner).to_be_focused()

            # Intercept /authoring/brief/draft to return a successful HTML swap with
            # both outcome status and assumptions/warnings caution panel (F-17).
            def fulfill_draft(route: Route) -> None:
                body = (
                    '<!doctype html><html lang="en"><body>'
                    '<main id="main">'
                    '<article class="intention">'
                    '<h1 class="display">Internal Authoring Workspace</h1>'
                    '<div class="authoring-outcome" data-focus-target role="status">'
                    "<p>Drafted the brief from your notes.</p>"
                    "</div>"
                    '<div class="validation-panel validation-panel--caution" '
                    'role="status">'
                    "<p>Confirm these assumptions before you generate a candidate:</p>"
                    "<ul><li>The two posters are comparable in style.</li></ul>"
                    "</div>"
                    "</article></main></body></html>"
                )
                route.fulfill(status=200, content_type="text/html", body=body)

            page.route(f"{base_url}/authoring/brief/draft", fulfill_draft)
            page.get_by_label("Your notes, source text, or topic").fill(
                "Compare two posters."
            )
            page.get_by_role("button", name="Draft the brief").click()

            outcome_banner = page.locator(
                ".authoring-outcome[data-focus-target][role='status']"
            )
            expect(outcome_banner).to_be_visible()
            expect(outcome_banner).to_be_focused()
            caution_panel = page.locator(".validation-panel--caution[role='status']")
            expect(caution_panel).to_be_visible()
        finally:
            browser.close()
