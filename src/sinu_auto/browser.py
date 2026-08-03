"""SINU Auto-Enrollment — browser session management via Playwright CDP."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

# Resolve the shared browser helper if present (human_browser.py in job-search lib)
_HB_PATHS = [
    Path(__file__).resolve().parents[3] / "lib" / "human_browser.py",
    Path.home() / ".hermes" / "job-search" / "lib" / "human_browser.py",
]


def _import_human_browser():
    """Import the shared human_browser helper when available (stealth CDP)."""
    for p in _HB_PATHS:
        if p.exists():
            sys.path.insert(0, str(p.parent))
            import human_browser  # type: ignore

            return human_browser
    return None


class BrowserSession:
    """Wraps a Playwright browser connection (CDP if available, else local)."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._pw = None
        self._browser = None
        self._context = None
        self._hb = _import_human_browser()

    def connect(self) -> BrowserContext:
        """Connect to a browser. Uses CDP (human_browser) when present, else launches local."""
        if self._hb is not None:
            self._pw = sync_playwright().start()
            browser, context = self._hb.connect(self._pw)
            self._browser = browser
            self._context = context
            return context

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context()
        return self._context

    def new_page(self) -> Page:
        if self._context is None:
            self.connect()
        return self._context.new_page()  # type: ignore

    def close(self):
        try:
            if self._context is not None:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser is not None and self._hb is None:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass


def wait(seconds: float):
    """Sleep helper (keeps code greppable for timeouts)."""
    time.sleep(seconds)
