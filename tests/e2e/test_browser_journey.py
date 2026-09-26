"""Browser-level end-to-end test for the learner journey (SPEC-012, SPEC-015).

This suite drives the real application in Chromium via Playwright and is
**skipped by default in the local environment**. It only runs when
``RUN_BROWSER_TESTS=1`` is set, and the CI workflow sets that variable in a
dedicated browser job that installs Playwright browsers. Normal local test
runs (``make check`` / ``pytest``) are unaffected and remain green without
any browser installed.

Local constraints:

- Many local environments do not have a Playwright browser downloaded, a
  display, or the sandbox permissions a browser needs (root containers in
  particular). Running these tests there is not supported: keep them skipped
  and rely on the CI browser job instead.
- If a compatible browser is available and an opt-in run is genuinely
  wanted: ``uv run playwright install chromium`` (or point
  ``PLAYWRIGHT_EXECUTABLE_PATH`` at an existing Chromium/Chrome binary).
  Root containers may also need ``PLAYWRIGHT_NO_SANDBOX=1``.

SPEC-026 (#92): the journey now walks the wired metacognitive flow —
activity selection leads through the optional intention prompt, and the
HTMX feedback panel carries the structured reflection prompts with Save
and Skip controls, matching the full feedback page.
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
from playwright.sync_api import Browser, Page, expect, sync_playwright

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_TESTS") != "1",
    reason="browser tests are opt-in (set RUN_BROWSER_TESTS=1)",
)


@contextmanager
def _running_server() -> Iterator[str]:
    """Start the Fablit application on a free port and yield its base URL."""
    port = _free_port()
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
    """Playwright launch options, honouring local overrides via environment."""
    options: dict[str, Any] = {}
    executable = os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH")
    if executable:
        options["executable_path"] = executable
    if os.environ.get("PLAYWRIGHT_NO_SANDBOX") == "1":
        options["args"] = ["--no-sandbox"]
    return options


def _run_journey(page: Page, base_url: str) -> None:
    """Walk the learner journey in the browser (SPEC-013 + SPEC-015 stimulus).

    SPEC-015 §71: the journey includes seeing the image before entering a
    response, and the feedback is response-aware (grounded in the response).
    """
    page.goto(base_url)
    expect(
        page.get_by_role("heading", name="What would you like to explore?", exact=True)
    ).to_be_visible()
    expect(page.get_by_role("link", name="Explore").first).to_be_visible()

    # SPEC-026 §2.1: selecting an activity leads through the optional
    # intention prompt before the active workspace (issue #92 wiring).
    page.get_by_role("link", name="Explore").first.click()
    expect(
        page.get_by_role("heading", name="Set an intention", exact=True)
    ).to_be_visible()
    page.get_by_label("Your intention (optional)").fill(
        "Focus on how two elements interact."
    )
    page.get_by_role("button", name="Continue with intention").click()

    expect(page.get_by_label("What's your reading of it?")).to_be_visible()
    # The stated intention is echoed quietly in the active workspace.
    expect(page.get_by_text("Focus on how two elements interact.")).to_be_visible()
    # The practice page is visually quieter than the dashboard (SPEC-013 §14).
    expect(page.get_by_role("link", name="Explore")).to_have_count(0)
    # SPEC-015 §71: the learner sees the resolved image before responding.
    expect(page.get_by_role("img").first).to_be_visible()
    # SPEC-020: the practice screen presents an observe → task → response
    # hierarchy rather than a bare question-and-answer form.
    expect(page.get_by_role("heading", name="Observe", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Your task", exact=True)).to_be_visible()
    expect(
        page.get_by_role("heading", name="Your response", exact=True)
    ).to_be_visible()

    page.get_by_label("What's your reading of it?").fill(
        "The contrast between the figure and the dark background is striking."
    )
    page.get_by_role("button", name="I'm ready").click()
    expect(
        page.get_by_role("heading", name="Something you noticed", exact=False)
    ).to_be_visible()
    expect(page.get_by_text("What you noticed")).to_be_visible()
    expect(page.get_by_text("Try this next")).to_be_visible()
    # SPEC-015 §71: the feedback reflects the learner's actual response.
    expect(page.get_by_text("You noticed the contrast in the image")).to_be_visible()

    # SPEC-026 §2.2: the HTMX-swapped feedback carries the full structured
    # reflection panel — the same one the no-JS feedback page renders.
    expect(page.get_by_text("A moment to reflect")).to_be_visible()
    expect(
        page.get_by_text(
            "What strategy or mental model did you use to complete this activity?"
        )
    ).to_be_visible()
    expect(
        page.get_by_text(
            "What was the primary friction point or misconception you encountered?"
        )
    ).to_be_visible()
    # The intention echo travels into the reflection panel as quiet context.
    expect(
        page.get_by_text("Your intention for this practice: Focus on how two")
    ).to_be_visible()

    page.get_by_role("link", name="Save reflection").click()
    expect(
        page.get_by_text(
            "What will you try differently the next time you practise this skill?"
        )
    ).to_be_visible()

    page.get_by_label("Your reflection").fill(
        "I will explain how two elements interact next time."
    )
    page.get_by_role("button", name="Continue").click()
    expect(
        page.get_by_role("heading", name="✨ That's one done.", exact=True)
    ).to_be_visible()

    page.get_by_role("link", name="Back to explore").click()
    expect(
        page.get_by_role("heading", name="What would you like to explore?", exact=True)
    ).to_be_visible()


def test_learner_journey_in_browser() -> None:
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            _run_journey(browser.new_page(), base_url)
        finally:
            browser.close()


def test_intention_skip_path_in_browser() -> None:
    """Skipping the intention goes straight to practice, never a gate."""
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = browser.new_page()
            page.goto(base_url)
            page.get_by_role("link", name="Explore").first.click()
            expect(
                page.get_by_role("heading", name="Set an intention", exact=True)
            ).to_be_visible()
            page.get_by_role("button", name="Skip — go straight to practice").click()

            expect(page.get_by_label("What's your reading of it?")).to_be_visible()
            # No intention was stated, so no echo is rendered.
            expect(page.locator(".practice__intention")).to_have_count(0)
        finally:
            browser.close()


def test_learner_journey_on_mobile_viewport() -> None:
    """The full journey remains coherent on a mobile-sized viewport (SPEC-013 §25)."""
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            _run_journey(page, base_url)
        finally:
            browser.close()


def test_keyboard_navigation_reaches_core_actions() -> None:
    """Tab order reaches the core actions with visible focus (SPEC-013 §27).

    SPEC-021 added the persistent "Your practice" header link, so the tab
    order on every page is now: skip link → brand → Your practice → page
    content. The test asserts that order and that the new link is
    keyboard-reachable alongside the pre-existing core actions.

    SPEC-022 adds the dashboard's quiet practice-mode invitation as the
    first content link, before the activity cards.
    """
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = browser.new_page()
            page.goto(base_url)

            page.keyboard.press("Tab")
            expect(page.get_by_role("link", name="Skip to content")).to_be_focused()

            page.keyboard.press("Tab")
            expect(page.get_by_role("link", name="Fablit")).to_be_focused()

            # SPEC-021: the header navigation to practice history is part of
            # the core keyboard-reachable actions on every page.
            page.keyboard.press("Tab")
            expect(page.get_by_role("link", name="Your practice")).to_be_focused()

            # SPEC-022: the optional practice-mode invitation is the first
            # keyboard-reachable content link on the dashboard.
            page.keyboard.press("Tab")
            expect(
                page.get_by_role("link", name="Choose how you'd like to practise")
            ).to_be_focused()

            page.keyboard.press("Tab")
            expect(page.get_by_role("link", name="Explore").first).to_be_focused()
        finally:
            browser.close()


def test_dashboard_displays_activity_previews() -> None:
    """Explore cards with bundled fallback images show a preview (SPEC-019)."""
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = browser.new_page()
            page.goto(base_url)
            # The demo content includes seven activities with bundled fallback images
            # (the three SPEC-015 originals plus four SPEC-023 additions)
            expect(page.locator(".card__preview img")).to_have_count(7)
            # Check one known alt text from demo content for robustness
            expect(
                page.get_by_role(
                    "img",
                    name="A photograph-style composition for visual analysis.",
                )
            ).to_be_visible()
        finally:
            browser.close()
