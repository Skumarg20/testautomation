"""The batch pop-up that appears when an item has several batches, and the Yes confirmation popup."""

import re

from playwright.sync_api import Locator, Page, expect

from pages.components.popup import Popup

ANY_TEXT = re.compile(r"\S")
FIRST_BATCH_AFTER_HEADER = 1
NEAR_EXPIRY_STATUS_ROW = 1
EXPIRED_STATUS_ROW = 2
BATCH_NAME_TIMEOUT_MS = 10_000
NEXT_STEP_TIMEOUT_MS = 10_000


class BatchWindow:
    def __init__(self, page: Page) -> None:
        self._page = page

    @property
    def yes_button(self) -> Locator:
        return self._page.locator("#btnYes")

    @property
    def window(self) -> Locator:
        marker = self._page.locator('[col-id="batchName"]')
        return self._page.locator(".ag-body-container").filter(has=marker)

    def wait_for_next_step(self, quantity_cell: Locator) -> None:
        """Waits until the grid shows the quantity cell, a Yes popup, or the batch window."""
        quantity_cell.or_(self.yes_button).or_(self.window).first.wait_for(
            state="visible", timeout=NEXT_STEP_TIMEOUT_MS
        )

    def is_yes_popup_shown(self) -> bool:
        return self.yes_button.is_visible()

    def is_batch_window_shown(self) -> bool:
        return self.window.is_visible()

    def confirm_yes(self) -> None:
        self.yes_button.click()

    def choose_batch(self, expiry_type: str | None) -> None:
        if expiry_type == "NE":
            self._status_cell(NEAR_EXPIRY_STATUS_ROW).click()
        elif expiry_type == "EXP":
            self._status_cell(EXPIRED_STATUS_ROW).click()
            Popup(self._page).expect_shown_then_dismissed("Expired")
        else:
            self._choose_first_batch()

    def _choose_first_batch(self) -> None:
        names = self._page.locator('[col-id="batchName"]')
        expect(names.first).to_be_visible()
        filled = names.filter(has_text=ANY_TEXT)
        expect(filled.nth(FIRST_BATCH_AFTER_HEADER)).to_have_text(ANY_TEXT, timeout=BATCH_NAME_TIMEOUT_MS)
        filled.nth(FIRST_BATCH_AFTER_HEADER).click()

    def _status_cell(self, position: int) -> Locator:
        return self._page.locator('[col-id="deal"]').filter(has_text=ANY_TEXT).nth(position)
