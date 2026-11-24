"""Sale > Return: a return of a single bill, or a manual return."""

from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import Locator, expect

from pages.sale.documents.document import SaleDocument, expect_amount_equals
from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.screen import is_shown_within, tick_every_row

ReturnKind = Literal["Single", "Manual"]
SAVE_TOAST_TIMEOUT_MS = 50_000
DETAILS_WAIT_MS = 5_000
DETAILS_TIMEOUT_MS = 20_000
ITEMS_WINDOW_TIMEOUT_MS = 40_000
SAVE_WINDOW_WAIT_MS = 10_000


@dataclass(frozen=True)
class ReturnSource:
    kind: ReturnKind
    bill_number: str = ""


MANUAL_RETURN = ReturnSource("Manual")


class SaleReturn(SaleDocument):
    menu = ("Sale", "Return")
    number_label = "Cr. Note"

    def choose_party_for_return(self, name: str, source: ReturnSource) -> None:
        self._dismiss_bill_details()
        self.header.choose_party(name)
        self.screen.wait_for_loader()
        self._answer_bill_details(source)
        self._dismiss_unsaved_prompt()

    def expect_product_loaded(self, row: int) -> None:
        self.grid.expect_product_shown(row)

    def expect_saved(self) -> None:
        self.screen.wait_for_loader()
        if is_shown_within(self.save_window, SAVE_WINDOW_WAIT_MS):
            self.screen.press_button("save")
        self.screen.expect_toast("success", SAVE_TOAST_TIMEOUT_MS)
        self.screen.wait_for_loader()
        self._close_windows_left_open()

    def expect_rejected(self) -> None:
        self.screen.expect_toast("warning")
        self.screen.close_print_window_if_shown()
        self._dismiss_bill_details()

    def _verify_row_total(self, row: int, line: ProductLine) -> None:
        expect_amount_equals(self.grid.amount(row), line.amount)

    def _close_windows_left_open(self) -> None:
        self.screen.close_print_window_if_shown()
        if self.selection.is_shown():
            self.page.keyboard.press("Escape")
        self._dismiss_bill_details()

    def _answer_bill_details(self, source: ReturnSource) -> None:
        """A single-bill return needs the bill-details window; without it the return would quietly become
        the default kind, so a late window fails. A manual return only answers the window if it opens."""
        details = self._bill_details
        if source.kind == "Single":
            expect(details).to_be_visible(timeout=DETAILS_TIMEOUT_MS)
        elif not is_shown_within(details, DETAILS_WAIT_MS):
            return
        # The return-kind drop-down only has an id.
        self.page.locator("#returnOfBill").select_option(source.kind)
        if source.kind == "Single":
            self._return_single_bill(source.bill_number)
        else:
            expect(self.header.field("Bill No.")).to_be_hidden()
            self.screen.press_button("ok")

    def _return_single_bill(self, bill_number: str) -> None:
        bill_field = self.header.field("Bill No.")
        bill_field.fill(bill_number)
        bill_field.press("Enter")
        self.screen.press_button("ok")
        self.screen.wait_for_loader()
        self._select_every_bill_item()

    def _select_every_bill_item(self) -> None:
        items = self.page.locator(".modal-content").filter(has=self.page.locator("app-modal"))
        expect(items).to_be_visible(timeout=ITEMS_WINDOW_TIMEOUT_MS)
        tick_every_row(items)
        self.screen.press_button("ok")
        self.screen.confirm_if_asked()
        expect(self.page.locator("challanorder-item")).to_be_hidden()

    def _dismiss_bill_details(self) -> None:
        details = self._bill_details
        if is_shown_within(details, DETAILS_WAIT_MS):
            details.locator(".modal-header button").click()
            expect(details).to_be_hidden()

    @property
    def _bill_details(self) -> Locator:
        return self.page.locator(".modal-content").filter(has=self.page.locator("out-billdetails"))
