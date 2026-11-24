"""Changing a saved sale challan or bill: open it from its list, change line 1, save it again.

The list opens a document with Enter on the highlighted row, as the purchase and chemist lists do
(`DocumentList.open`, `SaleBillPage.reopen_for_modification`). Saving a modified document goes through the
same End key and save confirmation as a new one (unverified live for the modify case).
"""

from decimal import Decimal

from playwright.sync_api import Page

from pages.sale.documents.document import SaleDocument


class SavedDocument:
    def __init__(self, document: SaleDocument, number: str) -> None:
        self._document = document
        self._number = number

    @property
    def page(self) -> Page:
        return self._document.page

    def reopen(self) -> None:
        screen = self._document.screen
        screen.open_menu(self._document.menu)
        screen.filter_list_this_week()
        screen.search_list(self._number)
        screen.list_row(self._number).click()
        self.page.keyboard.press("Enter")
        screen.wait_for_loader()

    def change_quantity(self, quantity: Decimal) -> None:
        self._document.grid.enter_quantity(0, quantity)

    def change_batch(self, batch: str) -> None:
        self._document.grid.choose_batch(0, batch)

    def save_again(self) -> None:
        self._document.save()
        self._document.expect_saved()
