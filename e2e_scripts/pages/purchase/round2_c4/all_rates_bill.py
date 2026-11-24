"""A purchase bill that types sale rates B and C as well as MRP and rate A into the Batch Details window."""

import re
from decimal import Decimal

from playwright.sync_api import Page, expect

from pages.purchase.checklist.batch_details_window import BatchDetailsWindow
from pages.purchase.checklist.item_master_rates import ItemMasterRates
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.entry_form import PurchaseEntryForm
from pages.purchase.documents.line_items import PurchaseLineItem
from test_data.money import parse_amount

RATE_PROMPT_MS = 10_000


class RatesNotOfferedError(LookupError):
    def __init__(self, letters: str) -> None:
        super().__init__(f"The Batch Details window has no field for sale rates {letters}")


class AllRatesPurchaseBill(PurchaseBillEntryPage):
    def __init__(self, page: Page, mrp: Decimal, rates: dict[str, Decimal]) -> None:
        super().__init__(page)
        self._mrp = mrp
        self._rates = rates

    def _enter_price_details(self, row: int, line: PurchaseLineItem) -> None:
        PurchaseEntryForm._enter_price_details(self, row, line)
        window = BatchDetailsWindow(self.page)
        window.expect_open()
        missing = "".join(letter for letter in self._rates if not window.has_rate(letter))
        if missing:
            raise RatesNotOfferedError(missing)
        window.type_mrp(self._mrp)
        for letter, amount in self._rates.items():
            window.type_rate(letter, amount)
        window.close()


class RatesReader(ItemMasterRates):
    """Item List rate of any column (`rateb`, `ratec`, ... follow the `ratea` col-id)."""

    def rate_of(self, code: str, column: str) -> Decimal:
        return parse_amount(self._cell(code, column).inner_text())


class StoringRateBill(AllRatesPurchaseBill):
    """Types the purchase rate of the line and answers the "Update Change Rate" question with Store, so the
    item master takes the purchase rate (EntryGrid.enter_rate answers Don't Store instead)."""

    def __init__(self, page: Page, mrp: Decimal, rates: dict[str, Decimal]) -> None:
        super().__init__(page, mrp, rates)

    def _enter_price_details(self, row: int, line: PurchaseLineItem) -> None:
        self.grid.enter_free(row, line.free)
        body = self.page.locator(".ag-body-container").first
        cell = body.locator(f'[row-id="{row}"] [col-id="salePurchaseRate"]')
        cell.click()
        editor = cell.locator("input")
        editor.press("Control+A")
        editor.press_sequentially(format(line.rate, "f"))
        editor.press("Enter")
        prompt = self.page.locator("ngb-modal-window").filter(has_text="Update Change Rate")
        expect(prompt).to_be_visible(timeout=RATE_PROMPT_MS)
        prompt.get_by_role("button", name=re.compile(r"^\s*Store\s*$")).click()
        expect(prompt).to_be_hidden()
        self.grid.enter_discounts(row, line)
        self._enter_batch_window()

    def _enter_batch_window(self) -> None:
        window = BatchDetailsWindow(self.page)
        window.expect_open()
        window.type_mrp(self._mrp)
        for letter, amount in self._rates.items():
            window.type_rate(letter, amount)
        window.close()
