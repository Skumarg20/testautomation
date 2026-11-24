"""Creates and deletes the ledgers a test owns, with the ledger master page objects of J07/J17."""

from playwright.sync_api import Locator

from pages.dashboard_page import DashboardPage
from pages.masters.ledger_form import LedgerForm
from pages.masters.master_list import LedgerList
from pages.masters.typeahead import Typeahead
from test_data.banking import LedgerSpec


class LedgerSetup(LedgerForm):
    def create(self, ledger: LedgerSpec) -> None:
        DashboardPage(self.page).open()
        self.open_new()
        self._name.fill(ledger.name)
        self.choose_group(ledger.group)
        if ledger.station:
            Typeahead(self.page).choose(self._station, ledger.station)
        if ledger.account_number:
            self._account_number.fill(ledger.account_number)
        self.save()
        self.expect_saved()

    def ensure(self, ledger: LedgerSpec) -> None:
        """Creates a standing ledger only when the tenant does not have it yet; it is never deleted."""
        DashboardPage(self.page).open()
        ledgers = LedgerList(self.page)
        ledgers.open()
        if not ledgers.is_listed(ledger.name):
            self.create(ledger)

    def delete(self, name: str) -> None:
        # A fresh dashboard first: a report or a half-filled form can cover the sidebar.
        DashboardPage(self.page).open()
        ledgers = LedgerList(self.page)
        ledgers.open()
        ledgers.delete(name)

    @property
    def _account_number(self) -> Locator:
        # Why an id: the bank block of the form ("Account No *") has no test id or linked label.
        return self.page.locator("#txtAccountNo")
