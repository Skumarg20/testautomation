"""Sale > Challan: create, convert to a bill and delete."""

from playwright.sync_api import expect

from pages.sale.documents.bill_conversion import BillConversion
from pages.sale.documents.document import TemplatedDocument
from pages.sale.documents.document_requests import ProductLine

SAVE_TOAST_TIMEOUT_MS = 50_000


class SaleChallan(TemplatedDocument):
    menu = ("Sale", "Challan")
    number_label = "Challan No."

    def enter_price(self, row: int, line: ProductLine) -> None:
        """A challan keeps the rate the app proposes; the price cell is only visited."""
        self.grid.accept_default_price(row)

    def expect_saved(self) -> None:
        self.screen.expect_toast("success", SAVE_TOAST_TIMEOUT_MS)
        self.screen.wait_for_loader()
        self.leave_to_list()

    def convert_to_bill(self, number: str) -> None:
        self.screen.open_menu(self.menu)
        self.screen.search_list(number)
        self.screen.row_action(number, "Convert")
        expect(self.screen.active_dialog).to_be_visible()
        self.screen.confirm_yes()
        BillConversion(self.page).finish()
