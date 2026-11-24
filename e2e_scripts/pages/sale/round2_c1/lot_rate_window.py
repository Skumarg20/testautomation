"""The Lot Rate window opened with F7 in the rate cell (netrateask.component.ts:339-342).

lotRate.component.ts: `#LOTRateinput` Scheme Type select (1 Percentage, 2 Rate, 3 Scheme), `#LOTRateper` the
percentage, `#LOTRateinput1` quantity and `#LOTRateinput2` free of a deal such as 10 + 1; Enter on the
percentage or the free field calculates and closes (:176-181, :206-232). The result goes to the rate cell.
"""

from decimal import Decimal

from playwright.sync_api import expect

from pages.base_page import BasePage
from pages.sale.documents.item_grid import PRICE, DocumentItemGrid

WINDOW_TIMEOUT_MS = 15_000


class LotRateWindow(BasePage):
    def open_from_rate_cell(self, row: int) -> None:
        cell = DocumentItemGrid(self.page).cell(row, PRICE)
        cell.click()
        cell.locator("input").press("F7")
        expect(self.page.locator("#LOTRateinput")).to_be_visible(timeout=WINDOW_TIMEOUT_MS)

    def by_percentage(self, percentage: Decimal) -> None:
        self.page.locator("#LOTRateinput").select_option(value="1")
        field = self.page.locator("#LOTRateper")
        field.fill(f"{percentage:f}")
        field.press("Enter")
        expect(self.page.locator("#LOTRateinput")).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)

    def by_deal(self, quantity: int, free: int) -> None:
        self.page.locator("#LOTRateinput").select_option(value="2")
        self.page.locator("#LOTRateinput1").fill(str(quantity))
        field = self.page.locator("#LOTRateinput2")
        field.fill(str(free))
        field.press("Enter")
        expect(self.page.locator("#LOTRateinput")).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)
