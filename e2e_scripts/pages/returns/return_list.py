"""Purchase > Return: the "Purchase Return debit Note List" and the values of one of its rows."""

from decimal import Decimal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.components.app_texts import LIST_SEARCH_BOX, NO_BREAK_SPACE
from pages.dashboard_page import DashboardPage
from pages.purchase.documents.document_list import DocumentList
from pages.purchase.documents.navigation import ModuleMenu, PurchaseScreen
from test_data.money import parse_amount

ROW_TIMEOUT_MS = 20_000
EMPTY_STATE = "No Purchase Return debit Note Created Yet"
LIST_HEADING = "Purchase Return debit Note List"
NUMBER = "partyBillNo"
PARTY = "tmp_LedgerName"
AMOUNT = "totaliteminvoice"


class PurchaseReturnList(BasePage):
    def open(self) -> None:
        """From a fresh dashboard: after a save or delete here the sidebar is left half-collapsed and the
        "Return" entry cannot be clicked; the list's own address redirects to the dashboard."""
        DashboardPage(self.page).open()
        ModuleMenu(self.page).open_purchase(PurchaseScreen.RETURN)
        expect(self.page.get_by_text(LIST_HEADING)).to_be_visible(timeout=ROW_TIMEOUT_MS)

    def find(self, number: str) -> None:
        """Searches the number; a list with no return today shows only an empty-state text, no search box."""
        self.open()
        empty = self.page.get_by_text(EMPTY_STATE)
        # Why ids: the same search-box union the shared DocumentList uses.
        search = self.page.locator(LIST_SEARCH_BOX).first
        expect(empty.or_(search).first).to_be_visible(timeout=ROW_TIMEOUT_MS)
        if empty.is_visible():
            return
        DocumentList(self.page).find(number)

    def is_listed(self, number: str) -> bool:
        return self._row(number).count() > 0

    def expect_listed(self, number: str) -> None:
        expect(self._row(number)).to_have_count(1, timeout=ROW_TIMEOUT_MS)

    def expect_not_listed(self, number: str) -> None:
        expect(self._row(number)).to_have_count(0, timeout=ROW_TIMEOUT_MS)

    def party(self, number: str) -> str:
        shown = self._row(number).locator(f'[col-id="{PARTY}"]').inner_text()
        return shown.replace(NO_BREAK_SPACE, " ").strip()

    def amount(self, number: str) -> Decimal:
        return parse_amount(self._row(number).locator(f'[col-id="{AMOUNT}"]').inner_text())

    def open_row_menu(self, number: str) -> None:
        # The row's menu button is a Bootstrap dropdown toggle without a name.
        self._row(number).locator('button[data-toggle="dropdown"]').click()

    def _row(self, number: str) -> Locator:
        # Why col-id: the list is an ag-Grid; the number cell is told apart only by its col-id.
        number_cell = self.page.locator(f'[col-id="{NUMBER}"]').get_by_text(number, exact=True)
        return self.page.get_by_role("row").filter(has=number_cell)
