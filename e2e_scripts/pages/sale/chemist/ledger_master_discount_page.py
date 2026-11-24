from decimal import Decimal

from playwright.sync_api import Page

from pages.sale.chemist.ledger_editor import LedgerEditor
from test_data.discounts import DiscountCase


class LedgerMasterDiscountPage:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._editor = LedgerEditor(page)

    def set_discounts(self, ledger_name: str, case: DiscountCase) -> None:
        self._editor.open_ledger(ledger_name)
        self._editor.fill_station_if_empty()
        self._editor.open_others_tab()
        self._page.locator("#btnDiscounts").click()
        self._fill("ItemDiscount", case.discount1)
        self._fill("ItemDiscount2", case.discount2)
        self._page.get_by_role("button", name="Save").click()
        self._page.wait_for_load_state("load")
        self._editor.save_and_confirm()

    def _fill(self, form_control_name: str, value: Decimal | int | None) -> None:
        if value is None:
            return
        field = self._page.locator(f'[formcontrolname="{form_control_name}"]')
        field.click()
        field.fill(format(Decimal(value), "f"))
        field.press("Enter")
