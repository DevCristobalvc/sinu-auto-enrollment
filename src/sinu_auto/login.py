"""SINU Auto-Enrollment — authentication."""
from __future__ import annotations

import time

from playwright.sync_api import Page

from .logging_setup import get_logger

log = get_logger()


class LoginError(RuntimeError):
    """Raised when SINU login fails."""


def login(page: Page, url: str, username: str, password: str) -> None:
    """Log into SINU. Assumes the classic SmartClient login form."""
    log.debug("Navigating to %s", url)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(5)

    # SmartClient login fields (fixed IDs in the classic form)
    log.debug("Filling username field")
    set_input(page, "#isc_3Z", username)
    log.debug("Filling password field")
    set_input(page, "#isc_42", password)
    time.sleep(1)

    # Click "Entrar" (login button) — coordinates from UI map
    log.debug("Clicking Entrar (1059, 960)")
    page.mouse.click(1059, 960)
    time.sleep(4)

    # Dismiss "duplicate session" dialog if it appears
    try:
        log.debug("Dismissing possible duplicate-session dialog (675, 917)")
        page.mouse.click(675, 917)
        time.sleep(5)
    except Exception:
        pass

    # Verify login succeeded: the student menu should be present
    body = page.evaluate("() => document.body ? document.body.innerText : ''")
    if "Salir" not in body and "CERON" not in body and "Estudiante" not in body:
        raise LoginError("Login may have failed — expected menu text not found")
    log.info("Login verified: student menu present")


def set_input(page: Page, selector: str, value: str) -> None:
    """Set an input value with native setter + input event (SmartClient-friendly)."""
    page.eval_on_selector(
        selector,
        f"el => {{ el.value='{value}'; el.dispatchEvent(new Event('input', {{bubbles:true}})); }}",
    )
