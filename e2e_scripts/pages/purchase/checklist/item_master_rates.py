"""An item's rates as the Item List and the item form show them (sheet rows 26 and 48).

The Item List is an ag-Grid: `itemcode`, `Product` and the sale rate `ratea` are its col-ids
(pages/inventory/item_list_page.py); the form's purchase rate input is `#txtprate`
(UI/Master/Item/createitem.component.html:834-835). The product name is needed to open the form.
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, Page

from pages.base_page import BasePage
from pages.inventory.item_list_page import PRODUCT, SALE_RATE, ItemListPage
from pages.purchase.documents.navigation import ModuleMenu
from pages.stock.search_typing import type_search
from test_data.money import parse_amount


class ItemMasterRates(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._menu = ModuleMenu(page)

    def product_name_of(self, code: str) -> str:
        return self._cell(code, PRODUCT).inner_text().strip()

    def sale_rate_a_of(self, code: str) -> Decimal:
        return parse_amount(self._cell(code, SALE_RATE).inner_text())

    def purchase_rate_of(self, code: str) -> Decimal:
        """Read from the item form; the form is left again without saving."""
        name = self.product_name_of(code)
        ItemListPage(self.page).edit(name)
        rate = parse_amount(self.page.locator("#txtprate").input_value())
        self.page.keyboard.press("Escape")
        return rate

    def _cell(self, code: str, column: str) -> Locator:
        self._menu.open_item_master()
        type_search(self.page.get_by_role("searchbox", name="Search", exact=True), code)
        pattern = re.compile(rf"^\s*{re.escape(code)}\s*$", re.IGNORECASE)
        # Why CSS: the Item List cells are told apart by col-id only.
        row = self.page.get_by_role("row").filter(
            has=self.page.locator('[col-id="itemcode"]').filter(has_text=pattern)
        )
        return row.locator(f'[col-id="{column}"]').first
