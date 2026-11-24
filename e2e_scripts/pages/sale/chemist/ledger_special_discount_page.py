from decimal import Decimal

from playwright.sync_api import Locator, Page

from pages.components.whole_text import whole_text
from pages.sale.chemist.ledger_editor import LedgerEditor
from test_data.discounts import DiscountCase

LAST_COLUMN = "BanDisc"


class LedgerSpecialDiscountPage:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._editor = LedgerEditor(page)

    def set_special_rates(self, ledger_name: str, case: DiscountCase) -> None:
        self._editor.open_ledger(ledger_name)
        self._editor.fill_station_if_empty()
        self._editor.open_others_tab()
        self._page.locator("#btnSpec").click()
        row = self._item_row(case.item_description)
        self._fill_if_given(row, "Discount1", case.discount1)
        self._fill_if_given(row, "Discount2", case.discount2)
        self._fill_if_given(row, "VDisc", case.volume_discount1)
        self._commit_row(row)
        self._page.get_by_role("button", name="OK").click()
        self._page.wait_for_load_state("load")
        self._editor.save_and_confirm()

    def _item_row(self, item_description: str) -> Locator:
        name_cell = self._page.locator('[col-id="ItemName"]').filter(has_text=whole_text(item_description))
        return self._page.get_by_role("row").filter(has=name_cell)

    @staticmethod
    def _fill_if_given(row: Locator, column: str, value: Decimal | int | None) -> None:
        if value is None:
            return
        cell = row.locator(f'[col-id="{column}"]')
        cell.click()
        cell.locator("input").fill(format(Decimal(value), "f"))
        cell.locator("input").press("Enter")

    @staticmethod
    def _commit_row(row: Locator) -> None:
        last_cell = row.locator(f'[col-id="{LAST_COLUMN}"]')
        last_cell.click()
        last_cell.press("Enter")
