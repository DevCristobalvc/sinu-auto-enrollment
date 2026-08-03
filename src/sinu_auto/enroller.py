"""SINU Auto-Enrollment — enrollment action."""
from __future__ import annotations

import time
from typing import Optional

from playwright.sync_api import Page

from .parser import Group


class Enroller:
    """Selects a group and closes enrollment (SmartClient UI)."""

    # Positions of the action buttons in the 'Grupos ofertados' toolbar
    BTN_CERRAR_MATRICULA = (526, 648)  # center of "Cerrar matrícula"
    DIALOG_OK = (673, 586)  # "OK" button of the confirmation dialog
    DIALOG_CANCEL = (799, 586)  # "Cancelar" button

    def __init__(self, page: Page):
        self.page = page

    def select_group(self, group: Group) -> bool:
        """Click the select icon (true_select.png) of a group row.

        Returns True if the icon is present. NOTE: SmartClient selection may
        require a real mouse event on the containing cell — see docs/sinu-ui-map.md.
        """
        row = self.page.locator(f"tr:has-text('{group.grupo}')").first
        if row.count() == 0:
            return False
        sel_icon = row.locator("img[src*='select']").first
        if sel_icon.count() == 0:
            return False
        sel_icon.scroll_into_view_if_needed()
        # Full mouse event sequence — SmartClient listens to mousedown/up
        box = sel_icon.bounding_box()
        if box is None:
            return False
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        self.page.mouse.move(x, y)
        time.sleep(0.4)
        self.page.mouse.down()
        time.sleep(0.2)
        self.page.mouse.up()
        time.sleep(1)
        return True

    def close_enrollment(self) -> bool:
        """Click 'Cerrar matrícula' and confirm the dialog.

        Returns True if the confirmation dialog appeared and was accepted.
        WARNING: closing enrollment is IRREVERSIBLE — only call when sure.
        """
        x, y = self.BTN_CERRAR_MATRICULA
        self.page.mouse.click(x, y)
        time.sleep(5)

        # Check for the confirmation dialog
        body = self.page.evaluate("() => document.body ? document.body.innerText : ''")
        if "cerrar su matr" in body.lower() or "seguro" in body.lower():
            ok_x, ok_y = self.DIALOG_OK
            self.page.mouse.click(ok_x, ok_y)
            time.sleep(6)
            return True
        return False

    def is_selected(self, group: Group) -> Optional[bool]:
        """Heuristic: check if the group row looks selected (icon changed)."""
        row = self.page.locator(f"tr:has-text('{group.grupo}')").first
        if row.count() == 0:
            return None
        imgs = row.locator("img").all()
        srcs = []
        for i in imgs:
            src = i.get_attribute("src")
            if src:
                srcs.append(src.split("/")[-1])
        return any("checked" in s or "true_select" in s for s in srcs)
