"""The item search window that opens from a grid row (search by item code or by description)."""

from playwright.sync_api import Locator, Page

CODE_COLUMN = "itemcode"
DESCRIPTION_COLUMN = "Product"


class ItemPicker:
    def __init__(self, page: Page) -> None:
        self._page = page

    def choose_by_item_code(self, item_code: int) -> None:
        self._page.locator("#mrgSearchBox").select_option("itemcode")
        self._search(str(item_code))
        self._result_row(CODE_COLUMN, str(item_code)).click()

    def choose_by_description(self, description: str) -> None:
        self._search(description)
        self._result_row(DESCRIPTION_COLUMN, description).click()

    def _search(self, text: str) -> None:
        # The app also gives the <marg-search> wrapper the id "searchItems"; only the input takes text.
        search_box = self._page.locator("input#searchItems").first
        search_box.click()
        search_box.press_sequentially(text)

    def _result_row(self, column: str, exact_text: str) -> Locator:
        results = self._page.locator(".ag-body-container").filter(
            has=self._page.locator(f'[col-id="{CODE_COLUMN}"], [col-id="{DESCRIPTION_COLUMN}"]')
        )
        cell = self._page.locator(f'[col-id="{column}"]').get_by_text(exact_text, exact=True)
        return results.get_by_role("row").filter(has=cell)
