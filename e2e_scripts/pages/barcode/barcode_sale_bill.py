"""Scanning barcodes into the garments sale bill (Alt+N). The bill is never saved."""

from playwright.sync_api import expect

from pages.base_page import BasePage
from pages.components.bill_totals import BillTotals
from pages.sale.garments.garments_sale_page import GarmentsSalePage

STEP_TIMEOUT_MS = 15_000
FIRST_ROW = 0


class BarcodeSaleBill(BasePage):
    def open_new_bill(self) -> None:
        self._sale_bill.open_new_bill()

    def choose_party(self, name: str) -> None:
        self._sale_bill.choose_party(name)

    def scan(self, barcode: str) -> None:
        """Types the code and Enter into the first line's Barcode cell, as a scanner does."""
        self._sale_bill.enter_barcode(FIRST_ROW, barcode)

    def expect_line(self, barcode: str, product: str) -> None:
        line = self.page.get_by_role("row").filter(has=self.page.get_by_text(product, exact=True))
        expect(line).to_contain_text(barcode, timeout=STEP_TIMEOUT_MS)

    def leave_without_saving(self) -> None:
        BillTotals(self.page).leave_without_saving()

    @property
    def _sale_bill(self) -> GarmentsSalePage:
        return GarmentsSalePage(self.page)
