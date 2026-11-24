"""Master > Inventory Master > Item: the Item List grid, its Tax Info panel and the row delete."""

import re
from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.inventory.item_alert import ItemAlert
from pages.purchase.documents.navigation import ModuleMenu
from test_data.money import parse_amount

# Case-blind: the DOM text is lower case and CSS capitalises it on screen.
DELETED_MESSAGE = re.compile("Record Deleted Successfully", re.IGNORECASE)
DELETE_QUESTION = "Are you sure you want to delete the selected Record?"
LIST_TIMEOUT_MS = 30_000
FILTER_SETTLE_MS = 5_000
SEARCH_KEY_DELAY_MS = 50
PRODUCT = "Product"
COMPANY = "cus_ItemCompanyName"
STOCK = "Opening"
UNIT = "cus_unitname2"
SALE_RATE = "ratea"


class ItemListPage(BasePage):
    def open(self) -> None:
        ModuleMenu(self.page).open_item_master()
        expect(self._search).to_be_visible(timeout=LIST_TIMEOUT_MS)
        expect(self._product_cells.first).to_be_visible(timeout=LIST_TIMEOUT_MS)

    def has_item(self, product: str) -> bool:
        self._filter(product)
        return appears_within(self._row(product), FILTER_SETTLE_MS)

    def cell_text(self, product: str, column: str) -> str:
        """A cell of a row already shown by expect_listed or select."""
        return self._row(product).locator(f'[col-id="{column}"]').inner_text().strip()

    def cell_amount(self, product: str, column: str) -> Decimal:
        return parse_amount(self.cell_text(product, column))

    def select(self, product: str) -> None:
        self.expect_listed(product)
        row = self._row(product)
        row.locator(f'[col-id="{PRODUCT}"]').click()
        # Why a class: Edit/F3 and Delete act on the selected row, and ag-Grid shows selection only by class.
        expect(row).to_have_class(re.compile(r"\bag-row-selected\b"))

    def tax_info(self, label: str) -> str:
        """A value of the Tax Info panel of the selected item, e.g. "HSN/SAC" or "IGST %"."""
        line = self._tax_info_panel.get_by_role("listitem").filter(has_text=label)
        return line.locator("span").inner_text().strip()

    def tax_rate(self, label: str) -> Decimal:
        return parse_amount(self.tax_info(label))

    def edit(self, product: str) -> None:
        self.select(product)
        self._row(product).get_by_role("button", name="Edit/F3").click()

    def delete(self, product: str) -> None:
        self.select(product)
        self._row(product).get_by_role("button", name="Delete").click()
        alert = ItemAlert(self.page)
        alert.expect_asking(DELETE_QUESTION)
        alert.answer_yes()
        Toasts(self.page).expect_success_saying(DELETED_MESSAGE)

    def expect_listed(self, product: str) -> None:
        """Exactly one row with this name, and it is the only row the filter shows."""
        self._filter(product)
        expect(self._row(product)).to_have_count(1, timeout=LIST_TIMEOUT_MS)
        # Filtered-out rows stay in the DOM with empty cells, so only cells with text are counted.
        expect(self._product_cells.filter(has_text=re.compile(r"\S"))).to_have_count(1)

    def expect_not_listed(self, product: str) -> None:
        self._filter(product)
        expect(self._row(product)).to_have_count(0, timeout=LIST_TIMEOUT_MS)

    def _row(self, product: str) -> Locator:
        # Why col-id: the grid is an ag-Grid; its cells are told apart only by col-id.
        name_cell = self._product_cells.get_by_text(product, exact=True)
        return self.page.get_by_role("row").filter(has=name_cell)

    def _filter(self, product: str) -> None:
        """Types the name into the search box. ag-Grid renders only the rows on screen and reuses row
        elements while it scrolls, so on a long list an unfiltered row may be absent or a click on its
        button may land on another item."""
        # Not fill(): it filters nothing, and clearing the box with it made the box vanish.
        self._search.click()
        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(product, delay=SEARCH_KEY_DELAY_MS)

    @property
    def _search(self) -> Locator:
        return self.page.get_by_role("searchbox", name="Search", exact=True)

    @property
    def _product_cells(self) -> Locator:
        """Body cells only; the header cell has a col-id too but sits in a columnheader, not a gridcell."""
        return self.page.get_by_role("gridcell").and_(self.page.locator(f'[col-id="{PRODUCT}"]'))

    @property
    def _tax_info_panel(self) -> Locator:
        # Why a class: the panel is a plain div whose only label is a span, not a heading or legend.
        return self.page.locator("div.taxInfo")
