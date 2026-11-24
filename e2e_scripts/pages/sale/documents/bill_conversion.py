"""The bill form that opens when an order or a challan is converted to a bill."""

from decimal import Decimal

from pages.sale.documents.document import TemplatedDocument
from pages.sale.documents.document_requests import ProductLine

CONVERSION_PRICE = Decimal(100)
CONVERSION_DISCOUNT = Decimal(10)
CONVERSION_LINE = ProductLine(product="", batch="", quantity=Decimal(0), price=CONVERSION_PRICE)
SAVE_TOAST_TIMEOUT_MS = 50_000


class BillConversion(TemplatedDocument):
    menu = ("Sale", "Bill")
    number_label = "Bill No."

    def finish(self) -> None:
        """Price the converted line, give the bill a discount, save and confirm."""
        self.enter_price(0, CONVERSION_LINE)
        self.enter_bill_discount(CONVERSION_DISCOUNT)
        self.save()
        self.screen.wait_for_loader()
        self.confirm_save_window()
        self.screen.expect_toast("success", SAVE_TOAST_TIMEOUT_MS)
        self.leave_to_list()

    def expect_saved(self) -> None:
        self.screen.wait_for_loader()
        self.confirm_save_window()
        self.screen.wait_for_loader()
        self.leave_to_list()
