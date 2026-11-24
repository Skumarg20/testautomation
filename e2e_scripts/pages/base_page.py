"""Contract C5. Locator priority: data-testid > role > label > text. CSS or XPath only where the app offers
none of those (ag-Grid col-ids, bare class-only dialogs), each with a "Why CSS/XPath" comment."""

from playwright.sync_api import Locator, Page


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def by_test_id(self, test_id: str) -> Locator:
        return self.page.get_by_test_id(test_id)

    def goto(self, path: str, timeout_ms: float | None = None) -> None:
        self.page.goto(path, timeout=timeout_ms)
