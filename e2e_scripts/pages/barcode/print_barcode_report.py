"""Report > Accounts Report > Misc. Report > Print Barcode (screen title "Barcode Printing") and its
"Select Item" window. Never confirms a printer."""

import re
from enum import Enum

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.stock.search_typing import type_search

SCREEN_TIMEOUT_MS = 30_000
SEARCH_KEY_DELAY_MS = 60
MENU_SEARCH_TEXT = "print barcode"
MENU_ENTRY = "Print Barcode"
SCREEN_TITLE = "Barcode Printing"
PICKER_TITLE = "Select Item"
SEARCH_BY_BARCODE = "Barcode"
PICKER_PRODUCT = "Product"
NO_ITEM_LISTED = re.compile("Please Select Item First", re.IGNORECASE)
NO_ITEM_TICKED = re.compile("You Have To Select Atleast One Item", re.IGNORECASE)


class PrintCriteria(Enum):
    ITEM_WISE = "Item Wise"


class PrintBarcodeReport(BasePage):
    def open(self) -> None:
        """Through the top search box; the report sits three menu levels deep."""
        search = self.page.get_by_role("searchbox", name="Type to search")
        search.click()
        search.press_sequentially(MENU_SEARCH_TEXT, delay=SEARCH_KEY_DELAY_MS)
        self.page.get_by_role("heading", name=MENU_ENTRY, exact=True).click()
        expect(self._title).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def choose_criteria(self, criteria: PrintCriteria) -> None:
        # Why an id: the Print Criteria label is a plain text node, not tied to the select.
        self.page.locator("#Type").select_option(label=criteria.value)
        expect(self._picker).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def search_items_by_barcode(self, barcode: str) -> None:
        # The item list arriving late re-renders the picker and empties a half-typed search.
        expect(self._picker_products.filter(has_text=re.compile(r"\S")).first).to_be_visible(
            timeout=SCREEN_TIMEOUT_MS
        )
        self._picker.get_by_role("combobox").select_option(SEARCH_BY_BARCODE)
        type_search(self._picker.get_by_role("searchbox", name="Search"), barcode)

    def expect_only_item(self, product: str) -> None:
        expect(self._picker.get_by_role("gridcell", name=product, exact=True)).to_be_visible(
            timeout=SCREEN_TIMEOUT_MS
        )
        # Filtered-out ag-Grid rows stay in the DOM with empty cells, so only cells with text count.
        expect(self._picker_products.filter(has_text=re.compile(r"\S"))).to_have_count(1)

    def confirm_selection(self) -> None:
        self._picker.get_by_role("button", name="Ok", exact=True).click()

    def print_labels(self) -> None:
        self.page.get_by_role("button", name="P Print").click()

    def expect_no_item_listed_refusal(self) -> None:
        Toasts(self.page).expect_any_saying(NO_ITEM_LISTED)

    def expect_no_item_ticked_refusal(self) -> None:
        Toasts(self.page).expect_any_saying(NO_ITEM_TICKED)

    @property
    def _title(self) -> Locator:
        return self.page.get_by_role("heading", name=SCREEN_TITLE, level=1)

    @property
    def _picker(self) -> Locator:
        heading = self.page.get_by_role("heading", name=PICKER_TITLE, exact=True)
        return self.page.get_by_role("dialog").filter(has=heading)

    @property
    def _picker_products(self) -> Locator:
        # Why col-id: the picker is an ag-Grid; its cells are told apart only by col-id.
        return self._picker.get_by_role("gridcell").and_(self.page.locator(f'[col-id="{PICKER_PRODUCT}"]'))
