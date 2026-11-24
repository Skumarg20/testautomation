"""The "Barcode Printing" window opened by the barcode icon of an Item List row, and its "Print Barcode"
format window. Nothing here presses the format window's Print: no label is ever sent to a printer."""

from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.inventory.item_list_page import ItemListPage

WINDOW_TIMEOUT_MS = 30_000
PRINTING_TITLE = "Barcode Printing"
FORMAT_TITLE = "Print Barcode"


class BarcodePrinting(BasePage):
    def open_for(self, product: str) -> None:
        item_list = ItemListPage(self.page)
        item_list.open()
        item_list.select(product)
        self._print_icon(product).click()
        expect(self._window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def expect_line(self, product: str, barcode: str, quantity: Decimal) -> None:
        line = self._window.get_by_role("row").filter(has=self._cell(product))
        expect(line.get_by_role("gridcell", name=barcode, exact=True)).to_be_visible(
            timeout=WINDOW_TIMEOUT_MS
        )
        expect(line.get_by_role("gridcell", name=f"{quantity:f}", exact=True)).to_be_visible()

    def open_format_window(self) -> None:
        self._window.get_by_role("button", name="P Print").click()
        expect(self._format_window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def expect_format_choice_with_preview(self) -> None:
        expect(self._format_window.get_by_role("combobox")).to_be_visible()
        expect(self._format_window.get_by_role("button", name="F Preview")).to_be_enabled()

    def close_format_window(self) -> None:
        self._format_window.get_by_role("button", name="Esc Close").click()
        expect(self._format_window).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)

    def _print_icon(self, product: str) -> Locator:
        row = self.page.get_by_role("row").filter(has=self._cell(product))
        # Why CSS: the icon button has no text, title or aria-label; its "print" class is its only name.
        return row.locator("button.print")

    def _cell(self, product: str) -> Locator:
        return self.page.get_by_role("gridcell", name=product, exact=True)

    @property
    def _window(self) -> Locator:
        return self._dialog_titled(PRINTING_TITLE)

    @property
    def _format_window(self) -> Locator:
        return self._dialog_titled(FORMAT_TITLE)

    def _dialog_titled(self, title: str) -> Locator:
        heading = self.page.get_by_role("heading", name=title, exact=True)
        return self.page.get_by_role("dialog").filter(has=heading)
