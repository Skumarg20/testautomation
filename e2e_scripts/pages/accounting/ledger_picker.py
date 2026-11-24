"""The "select a ledger" popup that opens from the Account column of a voucher grid."""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.loader import Loader
from pages.accounting.voucher_grid import CellRef, VoucherGrid
from pages.accounting.waiting import appears_within, disappears_within
from pages.base_page import BasePage

OPEN_LOOKUP_MS = 1_500
CLICK_OPEN_LOOKUP_MS = 2_000
PICK_ATTEMPTS = 3
CLOSE_AFTER_PICK_MS = 10_000
FINAL_CLOSE_MS = 50_000
STACKED_MODAL_CLOSE_MS = 5_000


class LedgerPicker(BasePage):
    def choose(self, row: int, account: str) -> None:
        """An empty account name closes the popup without choosing, which the negative cases rely on."""
        self._open_for(CellRef(row, "ledgerLinkID"))
        if account:
            self._pick(account)
        else:
            self._close_button().first.click()

    @property
    def window(self) -> Locator:
        # Why CSS: the popup is an ngb modal with no role or test id.
        return self.page.locator("div.modal-dialog.modal-lg")

    def close_window(self) -> None:
        self._close_button().first.click()

    def _open_for(self, ref: CellRef) -> None:
        grid = VoucherGrid(self.page)
        if appears_within(self.window, OPEN_LOOKUP_MS):
            return
        if not grid.cell_input(ref).is_visible():
            grid.cell(ref).click()
            if appears_within(self.window, CLICK_OPEN_LOOKUP_MS):
                return
        grid.cell_input(ref).press("Space")

    def _pick(self, account: str) -> None:
        self._close_stacked_modals()
        search = self.window.get_by_role("searchbox")
        search.press("Control+A")
        search.press_sequentially(account)
        self._click_result_until_closed(account)
        Loader(self.page).wait_until_idle()
        expect(self.window).to_be_hidden(timeout=FINAL_CLOSE_MS)

    def _click_result_until_closed(self, account: str) -> None:
        exact_name = re.compile(rf"^\s*{re.escape(account)}\s*$", re.IGNORECASE)
        result = self.window.get_by_role("gridcell", name=exact_name).first
        for _ in range(PICK_ATTEMPTS):
            result.click()
            Loader(self.page).wait_until_idle()
            if disappears_within(self.window, CLOSE_AFTER_PICK_MS):
                return

    def _close_button(self) -> Locator:
        # Why CSS: the close cross is a bare span in the modal header (two header variants exist).
        header_cross = self.page.locator("#header-modal").get_by_text("×")
        modal_cross = self.page.locator("ngb-modal-window:not([aria-hidden='true'])").get_by_role(
            "button", name="×"
        )
        return header_cross.or_(modal_cross)

    def _close_stacked_modals(self) -> None:
        """Older modals stay in the DOM under the newest one and block clicks, so close all but the last."""
        modals = self.page.locator("ngb-modal-window[aria-modal='true']")
        while modals.count() > 1:
            remaining = modals.count() - 1
            self._close_newest(modals)
            expect(modals).to_have_count(remaining, timeout=STACKED_MODAL_CLOSE_MS)

    def _close_newest(self, modals: Locator) -> None:
        close = modals.last.locator("button[aria-label='Close'], .close").first
        if close.is_visible():
            close.click()
        else:
            self.page.keyboard.press("Escape")
