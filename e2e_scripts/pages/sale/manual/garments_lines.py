"""Extra grid steps on the garments sale bill (Alt+N) for the manual cases.

`GarmentsSalePage` adds items that have variants (Design / Color / Size). An item without variants, such as
the 0% GST item of the outstanding cases, lands straight in the grid with its quantity editor open; the editor
id is `#txt-quantity-<row>` (live 2026-10-09, `pages/accounting/outstanding/item_line.py`).
"""

from decimal import Decimal

from playwright.sync_api import expect

from pages.sale.chemist.sale_bill_page import SaleBillPage
from pages.sale.garments.garments_sale_page import PRODUCT, STEP_TIMEOUT_MS, GarmentsSalePage

VOLUME_DISCOUNT = "volumediscount"


class ManualGarmentsSale(GarmentsSalePage):
    def add_plain_item(self, row: int, item_name: str, quantity: Decimal) -> None:
        """An item with no variants: pick it, type the quantity in the editor that opens, Enter."""
        self._open_item_picker(row)
        self._item_search.press_sequentially(item_name)
        expect(self._highlighted_item(item_name)).to_be_visible(timeout=STEP_TIMEOUT_MS)
        self._item_search.press("Enter")
        editor = self.page.locator(f"#txt-quantity-{row}")
        expect(editor).to_be_visible(timeout=STEP_TIMEOUT_MS)
        editor.press("Control+A")
        editor.press_sequentially(f"{quantity:f}")
        editor.press("Enter")

    def replace_item(self, row: int, item_name: str, quantity: Decimal) -> None:
        """Opens the item picker on a filled row and picks another item with variants."""
        cell = self._grid.cell(row, PRODUCT)
        cell.click()
        cell.press("Enter")
        expect(self._item_search).to_be_visible(timeout=STEP_TIMEOUT_MS)
        self._pick_highlighted_item(item_name)
        self._confirm_variant()
        self._commit_quantity(quantity)

    def expect_item_in_row(self, row: int, item_name: str) -> None:
        expect(self._grid.cell(row, PRODUCT)).to_contain_text(item_name, timeout=STEP_TIMEOUT_MS)

    def change_first_volume_discount(self, row: int, value: Decimal) -> None:
        self._grid.cell(row, VOLUME_DISCOUNT).click()
        self.page.keyboard.insert_text(f"{value:f}")
        self.page.keyboard.press("Enter")

    def delete_row(self, position: int) -> None:
        """Deletes the grid row at the 1-based `position` and answers Yes."""
        SaleBillPage(self.page).delete_grid_row(position)
