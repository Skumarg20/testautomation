"""Changing the party or the sale type of a garments sale bill that already has lines.

Party: typing a new name in the party box opens "Select Party" as it does for the first party
(pages/sale/garments/garments_sale_page.py); when the chosen ledger differs from the bill's, the bill
resets its
tax block and recalculates discounts (processout.transaction.component.ts:3379-3386 and
dataCalculation.ts `applyDiscountOnTotalAmount`). The tax then follows the new party's state (local: CGST +
SGST,
other state: IGST), as the SI-01..04 tests check.
Sale type: the "Type" box `#txtSaleType<tab>` exists only when "Ask Sale Type at the time of Billing?" is Yes
(processout.transaction.component.html:373-379). Choosing another type than the bill's current one clears the
grid and the tax block (processout.transaction.component.ts:4867-4876, `resetBillAndBottomGridAccToTaxType`).
Part C2 owns this module.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.base_page import BasePage
from pages.sale.garments.garments_sale_page import PARTY_KEY_DELAY_MS, PARTY_PICKER_TITLE

PICK_TIMEOUT_MS = 15_000
TYPE_WINDOW_TIMEOUT_MS = 10_000


class SaleTypeBox(BasePage):
    @property
    def field(self) -> Locator:
        # Why an id prefix: the id carries the window number (txtSaleType88).
        return self.page.locator("[id^=txtSaleType]").locator("visible=true").first

    def current(self) -> str:
        return self.field.input_value().strip()

    def offered(self) -> list[str]:
        """Opens the Sale Master list from the box and returns the names it shows (the window is left
        open)."""
        self.field.click()
        self.field.press("Enter")
        names = self._window.get_by_role("gridcell")
        expect(names.first).to_be_visible(timeout=TYPE_WINDOW_TIMEOUT_MS)
        return [text.strip() for text in names.all_inner_texts() if text.strip()]

    def choose(self, name: str) -> None:
        cell = self._window.get_by_role("gridcell", name=name, exact=True).first
        cell.click()
        self.page.keyboard.press("Enter")
        expect(self._window).to_be_hidden(timeout=TYPE_WINDOW_TIMEOUT_MS)

    @property
    def _window(self) -> Locator:
        return self.page.locator("ngb-modal-window").filter(has=self.page.get_by_role("gridcell"))


def change_party(page: Page, name: str) -> None:
    """Replaces the party of the open garments bill by another ledger."""
    party = page.locator("[id^=txtLedgerName]").last
    party.click()
    party.press("Control+A")
    party.press_sequentially(name, delay=PARTY_KEY_DELAY_MS)
    picker = page.get_by_role("dialog").filter(has_text=PARTY_PICKER_TITLE)
    picker.get_by_role("gridcell", name=name, exact=True).click()
    expect(party).to_have_value(re.compile(re.escape(name), re.IGNORECASE), timeout=PICK_TIMEOUT_MS)


class OpenBillDesk(SaleBillDesk):
    """Opens a one-line bill for a party and leaves it open, unsaved; the caller closes it."""

    def open_with_line(self, party: str, amount: Decimal) -> None:
        self._start(party, amount)

    def save_open_bill(self, party: str) -> str:
        """Saves the bill left open by `open_with_line` and returns its number."""
        self._open_payment_window()
        self._save_payment()
        return self._saved_number(party)
