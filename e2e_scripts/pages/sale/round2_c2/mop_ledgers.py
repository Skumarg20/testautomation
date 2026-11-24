"""The Mode Of Payment window's own ledger list: gear, Add, Delete.

Source: Component/Transaction/InverntoryTransaction/PaymentMode/modeofpayment.component.ts:491-520
(`openledgerlist`,
Add opens the "Select CashorBank" ledger window), :970-982 (`ondelete` removes the selected row when its
amount is
0 and it is not the cash ledger), :926-927 (the gear `#aControlRoomSetting` of this window shows Add and
Delete);
modeofpayment.component.html:6-14. The list is stored only when the bill is saved, so the tests close the
window
without saving. Part C2 owns this module.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.base_page import BasePage
from pages.sale.documents.mode_of_payment import TITLE, ModeOfPayment
from pages.sale.documents.selection_window import SelectionWindow

WINDOW_TIMEOUT_MS = 15_000
PICKER_TITLE = "Select CashorBank"


class MopLedgers(BasePage):
    def show_settings(self) -> None:
        self._window.locator("#aControlRoomSetting").click()
        expect(self._window.get_by_role("button", name=re.compile("Add"))).to_be_visible(
            timeout=WINDOW_TIMEOUT_MS
        )

    def add_ledger(self, name: str) -> None:
        self._window.get_by_role("button", name=re.compile("Add")).first.click()
        picker = self.page.locator("ngb-modal-window").filter(has_text=PICKER_TITLE)
        expect(picker).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        self.page.get_by_role("searchbox").last.fill(name)
        SelectionWindow(self.page).choose_cell_value(name)

    def expect_picker_without(self, name: str) -> None:
        """Opens Add and expects the ledger is not in the list; the picker is closed again."""
        self._window.get_by_role("button", name=re.compile("Add")).first.click()
        picker = self.page.locator("ngb-modal-window").filter(has_text=PICKER_TITLE)
        expect(picker).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        self.page.get_by_role("searchbox").last.fill(name)
        expect(picker.get_by_role("gridcell", name=name, exact=True)).to_have_count(0)
        self.page.keyboard.press("Escape")

    def delete_ledger(self, name: str) -> None:
        self.row(name).click()
        self._window.get_by_role("button", name=re.compile("Delete")).first.click()

    def row(self, name: str) -> Locator:
        return self._window.get_by_role("gridcell", name=name, exact=True)

    def expect_listed(self, name: str) -> None:
        expect(self.row(name)).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def expect_not_listed(self, name: str) -> None:
        expect(self.row(name)).to_have_count(0, timeout=WINDOW_TIMEOUT_MS)

    def close_without_saving(self) -> None:
        self.page.keyboard.press("Escape")

    @property
    def _window(self) -> Locator:
        return self.page.locator("ngb-modal-window").filter(has_text=TITLE)


class PaymentDesk(SaleBillDesk):
    """Opens a one-line bill up to its Mode Of Payment window and stops there."""

    def open_payment_window(self, party: str, amount: Decimal) -> MopLedgers:
        self._start(party, amount)
        self._open_payment_window()
        ModeOfPayment(self._page).expect_open()
        return MopLedgers(self._page)
