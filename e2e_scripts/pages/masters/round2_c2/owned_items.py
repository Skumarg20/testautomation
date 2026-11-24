"""Items a round-2 test creates in Master > Inventory Master > Item and deletes afterwards.

`saved` makes an item with no stock (deletable); `saved_with_opening` gives it an opening quantity in the main
store, after which the app refuses to delete it ("Opening Available In Main Store", see
tests/journeys/stock/conftest.py), so a test using it is marked `permanent`. The Status box of the item
form is
`#status1` (UI/Master/Item/createitem.component.html:1050) with the options Continue / Discontinue
(createitem.component.ts:3702). The Barcode box is `#txtBarcode` (:67). Part C2 owns this helper.
"""

import re
from dataclasses import replace
from decimal import Decimal

from playwright.sync_api import Page

from pages.dashboard_page import DashboardPage
from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import ItemListPage
from pages.sale.manual.option_settings import index_of_option
from pages.stock.opening_stock import create_item_with_opening
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

DUPLICATE_BARCODE = re.compile(r"Duplicate Bar ?Code", re.IGNORECASE)


class OwnedItems:
    def __init__(self, page: Page, data: DataFactory) -> None:
        self._page = page
        self._data = data
        self._products: list[str] = []
        self._serial = 0

    def spec(self, tax_category: str | None = None) -> ItemMasterSpec:
        """A new item named for this run; with `tax_category` it uses that category at 0%."""
        self._serial += 1
        base = replace(self._data.item_master(), product=f"QA-{self._data.run_id}-Item{self._serial}")
        if tax_category is None:
            return base
        return replace(base, tax_category=tax_category, gst_rate=Decimal(0))

    def saved(self, item: ItemMasterSpec) -> ItemMasterSpec:
        self._products.append(item.product)
        form = self._filled(item)
        form.save()
        form.expect_saved()
        form.decline_opening_stock()
        return item

    def saved_discontinued(self, item: ItemMasterSpec) -> ItemMasterSpec:
        self._products.append(item.product)
        form = self._filled(item)
        self.choose_status(form, "discontinue")
        form.save()
        form.expect_saved()
        form.decline_opening_stock()
        return item

    def saved_with_barcode(self, item: ItemMasterSpec, barcode: str) -> None:
        self._products.append(item.product)
        form = self._filled(item)
        self._page.locator("#txtBarcode").fill(barcode)
        form.save()
        form.expect_saved()
        form.decline_opening_stock()

    def refused_with_barcode(self, item: ItemMasterSpec, barcode: str) -> CreateItemPage:
        """Fills a second item with a barcode that is already taken and presses Save; nothing is saved."""
        form = self._filled(item)
        self._page.locator("#txtBarcode").fill(barcode)
        form.save()
        return form

    def saved_with_opening(self, item: ItemMasterSpec, quantity: Decimal) -> ItemMasterSpec:
        self._products.append(item.product)
        create_item_with_opening(self._page, item, quantity)
        return item

    def delete_unused(self) -> None:
        """Deletes the items without stock; an item that cannot be deleted is left (see the class note)."""
        DashboardPage(self._page).open()
        items = ItemListPage(self._page)
        items.open()
        for product in self._products:
            if items.has_item(product) and not self._has_stock(items, product):
                items.delete(product)
        self._products.clear()

    @staticmethod
    def choose_status(form: CreateItemPage, wanted: str) -> None:
        select = form.page.locator("#status1").locator("visible=true").first
        offered = [text.strip() for text in select.locator("option").all_inner_texts()]
        select.select_option(index=index_of_option("Status", wanted, offered))

    def _filled(self, item: ItemMasterSpec) -> CreateItemPage:
        form = CreateItemPage(self._page)
        form.open()
        form.fill(item)
        return form

    @staticmethod
    def _has_stock(items: ItemListPage, product: str) -> bool:
        return items.cell_amount(product, "Opening") > 0
