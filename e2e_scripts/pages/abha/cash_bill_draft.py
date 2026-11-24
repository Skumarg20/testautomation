"""A plain cash sale bill on the ABHA company with one stocked item, for the tests that need a bill that can
be saved (AB-34). Built from the chemist sale-bill parts; opened with Sale > Bill > Create/F2 because the
Alt+N shortcut is unreliable on the QA host.
"""

from pages.base_page import BasePage
from pages.components.footer import Footer
from pages.components.sale_bill_header import SaleBillHeader
from pages.grid.chemist_sale_grid import ChemistSaleGrid
from pages.sale.chemist.sale_bill_page import SaleBillPage
from pages.sale.documents.bill import SaleBillDocument
from test_data.headers import HEADERS
from test_data.models import HeaderTag
from test_data.sale_items import A_TO_Z_NS


class CashBillDraft(BasePage):
    def start(self) -> None:
        SaleBillDocument(self.page).open_new()
        SaleBillHeader(self.page).fill(HEADERS[HeaderTag.BASE])
        ChemistSaleGrid(self.page).add_item(0, A_TO_Z_NS.by_barcode())

    def press_save(self) -> None:
        Footer(self.page).save()

    def save(self) -> str:
        """Saves the bill and returns its entry number."""
        entry_number = SaleBillHeader(self.page).entry_number()
        self.press_save()
        SaleBillPage(self.page).expect_print_preview_shown()
        return entry_number

    def reopen(self, entry_number: str) -> None:
        SaleBillPage(self.page).reopen_for_modification(entry_number)
