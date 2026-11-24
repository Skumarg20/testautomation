"""An item with a barcode made for a test, picked on a purchase bill by that barcode.

The Create Item form has a "Barcode" input (`#txtBarcode`, createitem.component.html:66) shown when the
Control Room
"Barcode Required" is not "No"/"Batch wise" (`isBarcodedRequired` 3 or 4 hide it); the item window can
search by
barcode. Which search mode the window offers is read from its options (one containing "barcode"), an
unverified-live guess that fails with the offered list when wrong.
"""

from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Page, expect

from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from pages.purchase.documents.entry_grid import EntryGrid
from pages.stock.search_typing import type_search
from test_data.models import ItemMasterSpec

LIST_MS = 60_000


class NoBarcodeSearchError(LookupError):
    def __init__(self, offered: list[str]) -> None:
        super().__init__(f"The item window offers no barcode search; it offers {offered}")


@dataclass(frozen=True)
class BarcodedSpec:
    master: ItemMasterSpec
    barcode: str
    purchase_rate: Decimal


class BarcodedItem:
    def __init__(self, page: Page, spec: BarcodedSpec) -> None:
        self._page = page
        self.spec = spec
        self.barcode = spec.barcode

    def create(self) -> None:
        form = CreateItemPage(self._page)
        form.open()
        form.fill(self.spec.master)
        self._page.locator("#txtBarcode").fill(self.barcode)
        self._page.locator("#txtprate").fill(format(self.spec.purchase_rate, "f"))
        form.save()
        form.expect_saved()
        form.decline_opening_stock()

    def delete(self) -> None:
        DashboardPage(self._page).open()
        items = ItemListPage(self._page)
        items.open()
        items.delete(self.spec.master.product)

    def pick_on_purchase_line(self, grid: EntryGrid, row: int) -> None:
        """Opens the product window of `row`, searches by barcode and clicks the item."""
        body = self._page.locator(".ag-body-container").first
        cell = body.locator(f'[row-id="{row}"] [col-id="itemLinkID"]')
        cell.click()
        cell.press("Enter")
        window = self._page.locator("div.modal-dialog.modal-lg")
        expect(window).to_be_visible(timeout=LIST_MS)
        mode = window.get_by_role("combobox").first
        offered = [text.strip() for text in mode.locator("option").all_inner_texts()]
        match = [text for text in offered if "barcode" in text.lower()]
        if not match:
            raise NoBarcodeSearchError(offered)
        mode.select_option(label=match[0])
        type_search(window.get_by_role("searchbox"), self.barcode)
        listed = window.locator(".ag-cell-value").filter(has_text=self.barcode)
        expect(listed.first).to_be_visible(timeout=LIST_MS)
        listed.first.click()
        grid.expect_product_shown(row)
