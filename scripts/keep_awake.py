"""Visit the deployed app so Streamlit's hibernation timer never expires.

Why a real browser and not curl
-------------------------------
Streamlit Community Cloud hibernates any app with no traffic for 12 hours. What
counts as traffic is the websocket session the front end opens, not the initial
HTTP GET, so a plain `curl https://<app>/` fetches a page without ever
establishing a session and is not reliable at resetting the timer. Worse, if the
app is already asleep, that GET returns the hibernation page rather than waking
anything.

Driving a headless browser does both jobs: it opens a genuine session, and if it
lands on the hibernation page it clicks the wake button and waits for the app to
come back.

Why every check walks the frames
--------------------------------
On *.streamlit.app the app is served inside a cross-origin iframe, and the
top-level document body is empty. Checking `document.body.innerText` therefore
reports nothing regardless of whether the app is healthy, asleep or broken, so
every text check here iterates page.frames instead. Playwright drives the
browser itself, so it can read across the origin boundary that a page script
could not.

It doubles as an uptime check. The script exits non-zero if the app never
renders, so a failed scheduled run is a real alert rather than a silent no-op.
"""
from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import Page, sync_playwright

APP_URL = os.environ.get("APP_URL", "https://gee-lulc-pakistan.streamlit.app/")

# Text that only appears once the Streamlit front end has connected and the
# script has run. Matching the page <title> would not do: the hibernation page
# carries a title too.
READY_TEXT = "Pakistan land cover and carbon"

# The hibernation page's wake control. Streamlit has reworded this before, so
# match loosely on the distinctive part rather than the whole sentence.
WAKE_PATTERN = "get this app back up"

READY_TIMEOUT_S = 180
WAKE_LOOK_S = 20


def _all_text(page: Page) -> str:
    """Visible text across every frame, including the cross-origin app iframe."""
    chunks = []
    for frame in page.frames:
        try:
            chunks.append(frame.locator("body").inner_text(timeout=2_000))
        except Exception:  # noqa: BLE001
            continue  # a frame can detach mid-poll; it is not an error
    return "\n".join(chunks)


def _wait_for_text(page: Page, needle: str, seconds: int) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if needle.lower() in _all_text(page).lower():
            return True
        page.wait_for_timeout(2_000)
    return False


def _click_wake(page: Page) -> bool:
    for frame in page.frames:
        try:
            button = frame.get_by_text(WAKE_PATTERN, exact=False).first
            button.wait_for(state="visible", timeout=2_000)
            button.click()
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        print(f"visiting {APP_URL}", flush=True)
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=120_000)

        if _wait_for_text(page, WAKE_PATTERN, WAKE_LOOK_S):
            print("app was asleep, clicking the wake button", flush=True)
            if not _click_wake(page):
                print("could not click the wake button", flush=True)
        else:
            print("no hibernation page, app was already up", flush=True)

        if not _wait_for_text(page, READY_TEXT, READY_TIMEOUT_S):
            print(f"FAILED: app did not render within {READY_TIMEOUT_S}s",
                  flush=True)
            print(f"frames seen: {[f.url[:80] for f in page.frames]}", flush=True)
            print(f"text across frames:\n{_all_text(page)[:800]}", flush=True)
            browser.close()
            return 1

        # A session that closes the instant it renders may not register as
        # traffic, so hold it open briefly.
        page.wait_for_timeout(5_000)
        print("app is awake and rendered", flush=True)
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
