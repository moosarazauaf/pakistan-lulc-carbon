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

It doubles as an uptime check. The script exits non-zero if the app never
renders, so a failed scheduled run is a real alert rather than a silent no-op.
"""
from __future__ import annotations

import os
import sys

from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "https://gee-lulc-pakistan.streamlit.app/")

# Text that only appears once the Streamlit front end has connected and the
# script has run. Matching the page <title> would not do: the hibernation page
# carries a title too.
READY_TEXT = "Pakistan land cover and carbon"

# The hibernation page's wake control. Streamlit has reworded this before, so
# match loosely on the distinctive part rather than the whole sentence.
WAKE_PATTERN = "get this app back up"

TIMEOUT_MS = 120_000


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        print(f"visiting {APP_URL}")
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

        # If it hibernated, wake it. Give this a short window: on a healthy app
        # the button is simply absent and we should not wait out the timeout.
        try:
            wake = page.get_by_text(WAKE_PATTERN, exact=False).first
            wake.wait_for(state="visible", timeout=15_000)
            print("app was asleep, clicking the wake button")
            wake.click()
        except Exception:
            print("no hibernation page, app was already up")

        try:
            page.wait_for_function(
                "text => document.body.innerText.includes(text)",
                arg=READY_TEXT,
                timeout=TIMEOUT_MS,
            )
        except Exception:
            body = ""
            try:
                body = page.inner_text("body")[:600]
            except Exception:  # noqa: BLE001
                pass
            print(f"FAILED: app did not render within {TIMEOUT_MS // 1000}s")
            print(f"page text was:\n{body}")
            browser.close()
            return 1

        # A session that closes immediately may not register as traffic, so hold
        # it open briefly.
        page.wait_for_timeout(5_000)
        print("app is awake and rendered")
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
