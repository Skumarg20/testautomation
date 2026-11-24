"""Item Register: one item's documents in date order with a running balance ("Stock Summary" detail).

Opened from Master > Inventory Master > Item with F4 on the row, then "Item Register" (KB
`careportal_enriched_v5.csv`: "How to view Item Register in Marg Books?"; itemmaster.component.ts:2535-2548).
The detail route is `/report/stocksummary/sm-detail/...` (itemmaster.component.ts:2881-2916). The route and
the Enter-to-open step are the ones `pages.manufacturing.item_ledger.ItemLedger` already uses, so this class
reuses it. The columns come from the API, so a line is read as whole-row text and the balance is the cell
whose col-id holds "balance" (unverified live; the first live run settles the col-id).
"""

import re
from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.manufacturing.item_ledger import ItemLedger

ROW_TIMEOUT_MS = 30_000
FIGURE = re.compile(r"-?\d[\d,]*\.?\d*")


class RegisterBalanceUnreadableError(AssertionError):
    def __init__(self, product: str) -> None:
        super().__init__(f'The Item Register of "{product}" shows no running balance cell (col-id *balance*)')


class ItemRegister(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._ledger = ItemLedger(page)

    def closing_balance(self, product: str) -> Decimal:
        """The running balance on the register's last line."""
        self._ledger.open_for(product)
        expect(self._lines.first).to_be_visible(timeout=ROW_TIMEOUT_MS)
        figures = [FIGURE.findall(text) for text in self._balances.all_inner_texts()]
        balances = [found[0] for found in figures if found]
        if not balances:
            raise RegisterBalanceUnreadableError(product)
        return Decimal(balances[-1].replace(",", ""))

    def lists_document(self, product: str, number: str) -> bool:
        """True when a register line names the document number."""
        self._ledger.open_for(product)
        expect(self._lines.first).to_be_visible(timeout=ROW_TIMEOUT_MS)
        return self._lines.filter(has_text=number).count() > 0

    @property
    def _lines(self) -> Locator:
        # Why CSS: the register is an ag-Grid; its body rows are the ones inside the centre container.
        return self.page.locator(".ag-center-cols-container .ag-row")

    @property
    def _balances(self) -> Locator:
        return self._lines.locator('[col-id*="balance" i]')
