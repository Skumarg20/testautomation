"""Report > Item Ledger (`/item-master/report/itemledger`, item.module.ts:38): one item's movements in order.

The item list opens on that route; Enter on the item opens its detail (`/report/stocksummary/sm-detail/...`,
itemmaster.component.ts:2881-2916), the register of its documents with a running balance (KB `#25e8dd21`
checks a conversion there; MB-034805 is about its order). Locators and col-ids are from the Angular source
and unverified live: the detail's columns come from the API, so rows are read as whole-row text and the
running balance is matched by "balance" in its col-id.
"""

import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.purchase.documents.feedback import AppFeedback
from pages.stock.search_typing import type_search

ITEM_LEDGER_PATH = "/item-master/report/itemledger"
ROW_TIMEOUT_MS = 30_000
NEGATIVE = re.compile(r"^\s*-\s*\d")


class ItemLedger(BasePage):
    def open_for(self, product: str) -> None:
        self.goto(ITEM_LEDGER_PATH)
        type_search(self.page.get_by_role("searchbox", name="Search", exact=True), product)
        row = self.page.get_by_role("row").filter(has=self.page.get_by_text(product, exact=True)).first
        row.click()
        self.page.keyboard.press("Enter")
        AppFeedback(self.page).wait_for_loader()

    def position_of(self, document_number: str) -> int:
        """The 0-based place of the first register line that names the document."""
        rows = self._lines
        expect(rows.filter(has_text=document_number).first).to_be_visible(timeout=ROW_TIMEOUT_MS)
        texts = rows.all_inner_texts()
        return next(index for index, text in enumerate(texts) if document_number in text)

    def negative_running_balances(self) -> list[str]:
        cells = self._lines.locator('[col-id*="balance" i]')
        return [text for text in cells.all_inner_texts() if NEGATIVE.match(text)]

    @property
    def _lines(self) -> Locator:
        # Why CSS: the register is an ag-Grid; its body rows are the ones inside the centre container.
        return self.page.locator(".ag-center-cols-container .ag-row")
