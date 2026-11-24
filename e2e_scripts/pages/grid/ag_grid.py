"""Locators shared by the app's ag-Grid tables. Cells are found by their `col-id` attribute."""

from playwright.sync_api import Locator, Page


class AgGrid:
    def __init__(self, page: Page, identifying_column: str) -> None:
        self._page = page
        self._identifying_column = identifying_column

    @property
    def body(self) -> Locator:
        marker = self._page.locator(f'[col-id="{self._identifying_column}"]')
        return self._page.locator(".ag-body-container").filter(has=marker)

    def row(self, index: int) -> Locator:
        return self.body.locator(".ag-row").nth(index)

    def cell(self, index: int, column: str) -> Locator:
        return self.row(index).locator(f'[col-id="{column}"]')

    def cell_input(self, index: int, column: str) -> Locator:
        return self.cell(index, column).locator("input")
