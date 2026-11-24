"""The rate a purchase line shows in its rate cell before anything is typed there (sheet row 26)."""

import re
from decimal import Decimal

from playwright.sync_api import expect

from pages.base_page import BasePage
from pages.purchase.documents.entry_grid import RATE
from test_data.money import parse_amount

SHOWN_TIMEOUT_MS = 15_000
DIGIT = re.compile(r"\d")


class RateCell(BasePage):
    def shown_rate(self, row: int) -> Decimal:
        # Why CSS: ag-Grid cells carry only row-id and col-id attributes (as in EntryGrid._cell).
        cell = self.page.locator(".ag-body-container").first.locator(f'[row-id="{row}"] [col-id="{RATE}"]')
        expect(cell).to_have_text(DIGIT, timeout=SHOWN_TIMEOUT_MS)
        return parse_amount(cell.inner_text())
