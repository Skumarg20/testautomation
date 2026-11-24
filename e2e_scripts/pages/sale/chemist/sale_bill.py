"""A chemist sale bill as a user works with it: start it, fill the grid, save it, reopen it, read it back."""

from decimal import Decimal

from playwright.sync_api import Page

from pages.components.footer import Footer
from pages.components.sale_bill_header import SaleBillHeader
from pages.grid.chemist_sale_grid import ChemistSaleGrid
from pages.sale.chemist.sale_bill_page import SaleBillPage
from test_data.headers import HEADERS
from test_data.models import HeaderTag, ItemEntry


class SaleBill:
    def __init__(self, page: Page) -> None:
        self._header = SaleBillHeader(page)
        self._grid = ChemistSaleGrid(page)
        self._footer = Footer(page)
        self._saved_bill = SaleBillPage(page)

    def start(self, header_tag: HeaderTag = HeaderTag.BASE) -> None:
        self._header.open_document("sale bill")
        self._header.fill(HEADERS[header_tag])

    def add_item(self, row: int, entry: ItemEntry) -> None:
        self._grid.add_item(row, entry)

    def add_items(self, entries: list[ItemEntry]) -> None:
        self._grid.add_items(entries)

    def replace_item(self, row: int, entry: ItemEntry) -> None:
        self._grid.replace_item(row, entry)

    def change_quantity(self, row: int, quantity: int) -> None:
        self._grid.change_quantity(row, quantity)

    def change_sale_rate(self, row: int, rate: Decimal | int) -> None:
        self._grid.change_sale_rate(row, rate)

    def change_discounts(self, row: int, discounts: ItemEntry) -> None:
        self._grid.change_discounts(row, discounts)

    def change_batch(self, row: int, batch_name: str) -> None:
        self._grid.change_batch(row, batch_name)

    def save(self) -> None:
        self._footer.save()

    def expect_saved(self) -> None:
        self._saved_bill.expect_print_preview_shown()

    def save_and_expect_saved(self) -> None:
        self.save()
        self.expect_saved()

    def save_and_reopen_for_modification(self) -> None:
        entry_number = self._header.entry_number()
        self.save()
        self._saved_bill.reopen_for_modification(entry_number)

    def quantity_of(self, row: int) -> Decimal:
        return self._grid.quantity_of(row)

    def sale_rate_of(self, row: int) -> Decimal:
        return self._grid.sale_rate_of(row)

    def discount1_of(self, row: int) -> Decimal:
        return self._grid.discount1_of(row)

    def discount2_of(self, row: int) -> Decimal:
        return self._grid.discount2_of(row)

    def volume_discount1_of(self, row: int) -> Decimal:
        return self._grid.volume_discount1_of(row)

    def volume_discount2_of(self, row: int) -> Decimal:
        return self._grid.volume_discount2_of(row)

    def product_of(self, row: int) -> str:
        return self._grid.product_of(row)
