"""Browser-level end-to-end test for the learner journey (SPEC-012).

This suite drives the real application in Chromium via Playwright and is
opt-in: it is skipped unless ``RUN_BROWSER_TESTS=1`` is set. The CI workflow
sets that variable in a dedicated browser job; normal test runs are
unaffected.

Requirements:

- Playwright browsers installed: ``uv run playwright install chromium``
- For local runs against an existing Chromium instead of a downloaded one,
  set ``PLAYWRIGHT_EXECUTABLE_PATH`` to the browser binary. Root containers
  may also need ``PLAYWRIGHT_NO_SANDBOX=1``.
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
    """Walk the SPEC-012 §33 learner journey in the browser (SPEC-013 presentation)."""
    page.goto(base_url)
    expect(
        page.get_by_role("heading", name="What would you like to explore?", exact=True)
    ).to_be_visible()
    expect(page.get_by_role("link", name="Try it").first).to_be_visible()

    page.get_by_role("link", name="Try it").first.click()
    expect(page.get_by_label("Your response")).to_be_visible()
    # The practice page is visually quieter than the dashboard (SPEC-013 §14).
    expect(page.get_by_role("link", name="Try it")).to_have_count(0)

    page.get_by_label("Your response").fill(
        "The composition uses strong diagonal lines to guide the eye."
    )
    page.get_by_role("button", name="Submit response").click()
    expect(
        page.get_by_role("heading", name="A little feedback", exact=True)
    ).to_be_visible()
    expect(page.get_by_text("What you noticed")).to_be_visible()
    expect(page.get_by_text("Try this next")).to_be_visible()

    page.get_by_role("link", name="Reflect").click()
    expect(
        page.get_by_text(
            "What will you try differently the next time you practise this skill?"
        )
    ).to_be_visible()

    page.get_by_label("Your reflection").fill(
        "I will explain how two elements interact next time."
    )
    page.get_by_role("button", name="Save reflection").click()
    expect(
        page.get_by_role("heading", name="That's one done.", exact=True)
    ).to_be_visible()

    page.get_by_role("link", name="Back to practice").click()
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
    """Tab order reaches the core actions with visible focus (SPEC-013 §27)."""
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = browser.new_page()
            page.goto(base_url)

            page.keyboard.press("Tab")
            expect(page.get_by_role("link", name="Skip to content")).to_be_focused()

            page.keyboard.press("Tab")
            expect(page.get_by_role("link", name="Fablit")).to_be_focused()

            page.keyboard.press("Tab")
            expect(page.get_by_role("link", name="Try it").first).to_be_focused()
        finally:
            browser.close()
