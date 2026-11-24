"""Sale > Order: create, convert to a bill, close and delete."""

from decimal import Decimal

from playwright.sync_api import expect

from pages.sale.documents.bill_conversion import BillConversion
from pages.sale.documents.document import SaleDocument, expect_amount_equals, expect_amount_to_round_to
from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.item_grid import PRODUCT
from pages.sale.documents.screen import is_shown_within

SAVE_TOAST_TIMEOUT_MS = 50_000
MINIMUM_PRICE = Decimal(1)
LINES_LOADED_TIMEOUT_MS = 20_000
CLOSED_STATUS_TIMEOUT_MS = 7_000
CONVERSION_PROMPT_WAIT_MS = 5_000


class SaleOrder(SaleDocument):
    menu = ("Sale", "Order")
    number_label = "Order No."

    def choose_batch(self, row: int, line: ProductLine) -> None:
        """Orders reserve nothing, so no batch is chosen."""

    def expect_saved(self) -> None:
        self.screen.expect_toast("success", SAVE_TOAST_TIMEOUT_MS)
        self.screen.wait_for_loader()
        self.leave_to_list()

    def convert_to_bill(self, number: str) -> None:
        self._open_row_action(number, "Convert")
        self.screen.wait_for_loader()
        if is_shown_within(self.screen.active_dialog, CONVERSION_PROMPT_WAIT_MS):
            self.screen.confirm_yes()
        expect(self.grid.cell(0, PRODUCT).locator("input")).to_be_hidden(timeout=LINES_LOADED_TIMEOUT_MS)
        BillConversion(self.page).finish()
        self.delete_converted(number)

    def delete_converted(self, number: str) -> None:
        self.screen.open_menu(self.menu)
        self.screen.delete_after_conversion(number)

    def close(self, number: str) -> None:
        self._open_row_action(number, "Close")
        expect(self.screen.active_dialog).to_be_visible()
        self.screen.confirm_yes()
        self.screen.search_list(number)
        expect(self.screen.list_row(number).get_by_text("Closed")).to_be_visible(
            timeout=CLOSED_STATUS_TIMEOUT_MS
        )
        self.screen.row_action(number, "Delete")
        self.screen.expect_toast("warning")

    def _price_floor(self, row: int) -> Decimal:
        return MINIMUM_PRICE

    def _verify_price_entry(self, row: int, line: ProductLine) -> None:
        expect_amount_to_round_to(self.grid.amount(row), line.amount)

    def _verify_row_total(self, row: int, line: ProductLine) -> None:
        expect_amount_equals(self.grid.amount(row), line.amount)

    def _open_row_action(self, number: str, action: str) -> None:
        self.screen.open_menu(self.menu)
        self.screen.search_list(number)
        self.screen.row_action(number, action)
