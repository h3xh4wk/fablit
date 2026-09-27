"""Browser-level end-to-end tests for local draft recovery (SPEC-028).

Companions to ``test_browser_journey.py``: same opt-in browser contract
(``RUN_BROWSER_TESTS=1``, same launch/server helpers) and the same
real-application server. SPEC-028 exists entirely on the client, so these
tests drive the real DOM and real IndexedDB/localStorage rather than mocking
storage.

Covered acceptance criteria:

- Typing into the response field auto-saves locally within 3 seconds (§2.1)
  and reloading mid-session preserves the draft (§4).
- Returning to an active activity with a draft shows the recovery banner
  with ``Resume Draft`` / ``Discard Draft`` (§2.2).
- ``Resume Draft`` restores the exact pre-reload response (§4).
- ``Discard Draft`` purges the local draft entry (§2.2).
- A successful submission removes the local draft key (§2.3).
"""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Browser, Page, expect, sync_playwright

from tests.e2e.test_browser_journey import _launch_options, _running_server

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_TESTS") != "1",
    reason="browser tests are opt-in (set RUN_BROWSER_TESTS=1)",
)

_DRAFT_SENTINEL = (
    "A draft response written before the reload, long enough to be meaningful."
)

# The auto-save debounce is 3s (SPEC-028 §2.1); polls budget generously
# beyond it so slow CI browsers never flake on timing.
_POLL_ATTEMPTS = 60
_POLL_INTERVAL_MS = 250


def _new_page(browser: Browser) -> Page:
    return browser.new_page()


def _start_practice(page: Page, base_url: str) -> None:
    """Navigate from Explore into the first activity's workspace."""
    page.goto(base_url)
    page.get_by_role("link", name="Explore").first.click()
    expect(
        page.get_by_role("heading", name="Set an intention", exact=True)
    ).to_be_visible()
    # Skip the optional intention prompt; recovery must not depend on it.
    page.get_by_role("button", name="Skip — go straight to practice").click()
    expect(page.get_by_label("What's your reading of it?")).to_be_visible()


def _indexeddb_draft_count(page: Page) -> int:
    """Number of draft records in the IndexedDB store (-1 when unavailable)."""
    count: int = page.evaluate(
        """() => new Promise((resolve) => {
          const open = indexedDB.open('fablit-session-recovery', 1);
          open.onsuccess = () => {
            const db = open.result;
            try {
              const req = db.transaction('drafts', 'readonly')
                .objectStore('drafts').count();
              req.onsuccess = () => resolve(req.result);
              req.onerror = () => resolve(-1);
            } catch (err) {
              resolve(-1);
            } finally {
              db.close();
            }
          };
          open.onerror = () => resolve(-1);
        })""",
    )
    return count


def _draft_exists(page: Page) -> bool:
    """A draft is present in either storage backend (IndexedDB or fallback)."""

    def _exists() -> bool:
        keys = page.evaluate(
            "() => Object.keys(localStorage).filter((k) =>"
            " k.startsWith('fablit_draft_'))"
        )
        return bool(keys) or _indexeddb_draft_count(page) > 0

    return _exists()


def _expect_draft_saved(page: Page) -> None:
    """The auto-save engine has persisted a draft within the debounce budget."""
    for _ in range(_POLL_ATTEMPTS):
        if _draft_exists(page):
            return
        page.wait_for_timeout(_POLL_INTERVAL_MS)
    raise AssertionError("expected a locally saved draft within 15s of typing")


def _expect_no_draft(page: Page) -> None:
    """The local draft entry has been purged from both storage backends."""
    for _ in range(_POLL_ATTEMPTS):
        if not _draft_exists(page):
            return
        page.wait_for_timeout(_POLL_INTERVAL_MS)
    raise AssertionError("expected the local draft to be purged")


def test_reload_preserves_draft_and_offers_resume() -> None:
    """Typing auto-saves within 3s; reload keeps the text and offers resume."""
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = _new_page(browser)
            _start_practice(page, base_url)

            response_field = page.get_by_label("What's your reading of it?")
            response_field.fill(_DRAFT_SENTINEL)
            _expect_draft_saved(page)

            # Reload mid-session: the workspace comes back with the draft.
            page.reload()
            expect(page.get_by_label("What's your reading of it?")).to_be_visible()

            # The draft is uncommitted, so the recovery banner appears with
            # both SPEC-028 §2.2 controls.
            banner = page.locator(".practice__recovery")
            expect(banner).to_be_visible()
            expect(banner.get_by_role("button", name="Resume Draft")).to_be_visible()
            expect(banner.get_by_role("button", name="Discard Draft")).to_be_visible()

            # The textarea is restored only when the learner accepts.
            expect(page.get_by_label("What's your reading of it?")).to_have_value("")

            banner.get_by_role("button", name="Resume Draft").click()
            expect(page.get_by_label("What's your reading of it?")).to_have_value(
                _DRAFT_SENTINEL
            )
            expect(banner).to_have_count(0)
        finally:
            browser.close()


def test_discard_draft_purges_local_entry() -> None:
    """Discard removes the stored draft and leaves a clean workspace (§2.2)."""
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = _new_page(browser)
            _start_practice(page, base_url)
            page.get_by_label("What's your reading of it?").fill(_DRAFT_SENTINEL)
            _expect_draft_saved(page)

            page.reload()
            banner = page.locator(".practice__recovery")
            expect(banner).to_be_visible()

            banner.get_by_role("button", name="Discard Draft").click()
            expect(banner).to_have_count(0)
            _expect_no_draft(page)

            # A further reload offers nothing: the draft is gone.
            page.reload()
            expect(page.locator(".practice__recovery")).to_have_count(0)
            expect(page.get_by_label("What's your reading of it?")).to_have_value("")
        finally:
            browser.close()


def test_successful_submission_clears_draft() -> None:
    """The stored draft key is removed once submission succeeds (§2.3)."""
    with _running_server() as base_url, sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(**_launch_options())
        try:
            page = _new_page(browser)
            _start_practice(page, base_url)
            page.get_by_label("What's your reading of it?").fill(_DRAFT_SENTINEL)
            _expect_draft_saved(page)

            page.get_by_role("button", name="I'm ready").click()
            expect(
                page.get_by_role("heading", name="Something you noticed", exact=False)
            ).to_be_visible()
            _expect_no_draft(page)
        finally:
            browser.close()
