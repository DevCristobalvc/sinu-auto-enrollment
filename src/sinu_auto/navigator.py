"""SINU Auto-Enrollment — UI navigation (SmartClient clicks)."""
from __future__ import annotations

import time
from typing import Optional

from playwright.sync_api import Page

from .logging_setup import get_logger

log = get_logger()


class Navigator:
    """Navigates the SINU SmartClient UI to the enrollment screen."""

    # Menu item text -> expected location in the left menu
    MENU_MATRICULA_INDIVIDUAL = "Matrícula individual"

    def __init__(self, page: Page, program_row_y: int = 211):
        self.page = page
        self.program_row_y = program_row_y  # Y of the program row (P217) in the student table

    def open_matricula_individual(self) -> None:
        """Click 'Matrícula individual' in the left menu."""
        pos = self._find_text_element(self.MENU_MATRICULA_INDIVIDUAL)
        if pos is None:
            raise RuntimeError("Menu item 'Matrícula individual' not found")
        log.debug("Clicking 'Matrícula individual' at (%s, %s)", pos["left"], pos["top"])
        self.page.mouse.click(pos["left"], pos["top"])
        time.sleep(10)
        # Close any dialog that may have opened (preferences, etc.)
        self.page.keyboard.press("Escape")
        time.sleep(2)

    def select_program(self) -> None:
        """Click the student's program row (e.g. P217 INGENIERÍA DE SISTEMAS)."""
        log.debug("Clicking program row at (700, %s)", self.program_row_y)
        self.page.mouse.click(700, self.program_row_y)
        time.sleep(6)

    def expand_course(self, course_code: str) -> bool:
        """Expand a course row (click its row_collapsed icon). Returns True if expanded."""
        row = self.page.locator(f"tr:has-text('{course_code}')").first
        if row.count() == 0:
            log.warning("Course row %s not found", course_code)
            return False
        collapse = row.locator("img[src*='row_collapsed']").first
        if collapse.count() == 0:
            # Already expanded or no expander
            log.debug("No row_collapsed icon for %s (already expanded?)", course_code)
            return False
        collapse.scroll_into_view_if_needed()
        collapse.click(force=True)
        time.sleep(6)
        log.debug("Expanded course %s", course_code)
        return True

    def _find_text_element(self, text: str) -> Optional[dict]:
        """Find the center of the first element whose innerText equals `text`."""
        return self.page.evaluate(
            """(text) => {
                var els = document.querySelectorAll('td, div, span');
                for (var i = 0; i < els.length; i++) {
                    var t = (els[i].innerText || '').trim();
                    if (t === text) {
                        var r = els[i].getBoundingClientRect();
                        if (r.width > 10 && r.height > 8) {
                            return {top: Math.round(r.top + r.height/2),
                                    left: Math.round(r.left + r.width/2)};
                        }
                    }
                }
                return null;
            }""",
            text,
        )
