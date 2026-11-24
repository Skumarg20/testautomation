"""The list screen of a purchase document type: create, find a row, and its action menu."""

from decimal import Decimal
from enum import Enum

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.purchase.documents.feedback import AppFeedback, ToastKind, appears_within
from test_data.money import parse_amount

ROW_TIMEOUT_MS = 20_000
DELETE_PROMPT_TIMEOUT_MS = 90_000
SUCCESS_TIMEOUT_MS = 90_000
WEEK_FILTER = "This Week"
CLOSED_STATUS_TIMEOUT_MS = 7_000
MENU_OPEN_TIMEOUT_MS = 5_000
AMOUNT_COLUMN = "totaliteminvoice"
PARTY_COLUMN = "tmp_LedgerName"


class RowAction(Enum):
    CONVERT = "Convert"
    CLOSE = "Close"
    DELETE = "Delete"


class DocumentList(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._feedback = AppFeedback(page)

    def create(self) -> None:
        self.page.get_by_role("button", name="Create/F2").click()
        self._feedback.wait_for_loader()

    def filter_this_week(self) -> None:
        # The date range is a dropdown button with only styling classes to find it by.
        toggle = self.page.locator("button.default-btn.dropdown-toggle")
        week = self.page.locator("#txtthisweek")
        toggle.click()
        if not appears_within(week, MENU_OPEN_TIMEOUT_MS):
            # Why: a click that lands while the list is still loading is swallowed; open the menu again.
            toggle.click()
        week.click()
        self._feedback.wait_for_loader()

    def find(self, number: str) -> None:
        search = self._search_box
        search.press("Control+A")
        search.press("Backspace")
        search.press_sequentially(number)
        self._feedback.wait_for_loader()

    def row(self, number: str) -> Locator:
        return self.page.get_by_role("row").filter(has=self.page.get_by_text(number, exact=True)).first

    def expect_row_visible(self, number: str) -> None:
        expect(self.row(number)).to_be_visible(timeout=ROW_TIMEOUT_MS)

    def amount_of(self, number: str) -> Decimal:
        return parse_amount(self.row(number).locator(f'[col-id="{AMOUNT_COLUMN}"]').inner_text())

    def party_of(self, number: str) -> str:
        return " ".join(self.row(number).locator(f'[col-id="{PARTY_COLUMN}"]').inner_text().split())

    def open(self, number: str) -> None:
        """Opens the document of a row; Enter opens the highlighted row."""
        self.expect_row_visible(number)
        self.row(number).click()
        self.page.keyboard.press("Enter")
        self._feedback.wait_for_loader()

    def expect_row_status(self, number: str, status: str) -> None:
        expect(self.row(number).get_by_text(status)).to_be_visible(timeout=CLOSED_STATUS_TIMEOUT_MS)

    def choose_action(self, number: str, action: RowAction) -> None:
        self.expect_row_visible(number)
        # The row's menu button is a Bootstrap dropdown toggle without a name.
        self.row(number).locator('button[data-toggle="dropdown"]').click()
        # The menu opens over the list, not inside the row; the open menu is the last such text on screen.
        self.page.get_by_text(action.value, exact=True).locator("visible=true").last.click()

    def delete(self, number: str) -> None:
        """Deletes a document and waits for the success toast (stock moves back with it)."""
        self.filter_this_week()
        self.find(number)
        self.choose_action(number, RowAction.DELETE)
        self._feedback.wait_for_loader()
        self._expect_delete_prompt(number)
        self._feedback.confirm_if_asked()
        self._feedback.expect_toast(ToastKind.SUCCESS, SUCCESS_TIMEOUT_MS)
        self._feedback.wait_for_loader()

    def delete_after_conversion(self, number: str) -> None:
        """Removes the source document of a conversion; the app answers with a warning toast."""
        self.filter_this_week()
        self.find(number)
        self.choose_action(number, RowAction.DELETE)
        self._feedback.wait_for_loader()
        self._feedback.expect_toast(ToastKind.WARNING)

    def _expect_delete_prompt(self, number: str) -> None:
        # The prompt names the document in an italic tag, which has no role or label.
        named = self.page.locator("i").filter(has_text=number)
        expect(named.first).to_be_visible(timeout=DELETE_PROMPT_TIMEOUT_MS)

    @property
    def _search_box(self) -> Locator:
        # The list search box has a different id on each list screen; take whichever is on screen.
        union = "#SearchBox, #searchItems, .searchFilterBox input[name='SearchBox']"
        return self.page.locator(union).first
