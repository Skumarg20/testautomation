"""Fixtures for the accounting voucher tests: a garments session on the garments company's dashboard."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.contra_page import ContraPage
from pages.accounting.credit_note_page import CreditNotePage
from pages.accounting.debit_note_page import DebitNotePage
from pages.accounting.journal_page import JournalPage
from pages.accounting.opening_balance_page import OpeningBalancePage
from pages.accounting.owned_ledgers import OwnedLedgers
from pages.accounting.payment_page import PaymentPage
from pages.accounting.receipt_page import ReceiptPage
from pages.banking.ledger_setup import LedgerSetup
from pages.company_switch_page import GARMENTS_COMPANY
from pages.dashboard_page import DashboardPage
from test_data.banking import LedgerSpec
from test_data.cash_transfer import CASH_GROUP

GARMENTS: Account = "garments"
# The ledger the ported contra cases name. A cash ledger, because a bank ledger makes the app demand a
# cheque number the cases do not have. It stays on the tenant: CON-002 keeps its voucher, and the app
# refuses to delete a ledger that has vouchers.
CONTRA_LEDGER = LedgerSpec("Contra 001", CASH_GROUP)


@pytest.fixture
def accounting_page(company_page: Callable[[Account, str], Page]) -> Page:
    page = company_page(GARMENTS, GARMENTS_COMPANY)
    DashboardPage(page).expect_loaded()
    return page


@pytest.fixture
def receipt(accounting_page: Page) -> ReceiptPage:
    return ReceiptPage(accounting_page)


@pytest.fixture
def payment(accounting_page: Page) -> PaymentPage:
    return PaymentPage(accounting_page)


@pytest.fixture
def debit_note(accounting_page: Page) -> DebitNotePage:
    return DebitNotePage(accounting_page)


@pytest.fixture
def credit_note(accounting_page: Page) -> CreditNotePage:
    return CreditNotePage(accounting_page)


@pytest.fixture
def contra(accounting_page: Page) -> ContraPage:
    LedgerSetup(accounting_page).ensure(CONTRA_LEDGER)
    return ContraPage(accounting_page)


@pytest.fixture
def journal(accounting_page: Page) -> JournalPage:
    return JournalPage(accounting_page)


@pytest.fixture
def opening_balances(accounting_page: Page) -> OpeningBalancePage:
    return OpeningBalancePage(accounting_page)


@pytest.fixture
def owned_ledgers(opening_balances: OpeningBalancePage) -> Iterator[OwnedLedgers]:
    """Ledgers the test creates; deleted at teardown so the tenant keeps no test ledgers."""
    ledgers = OwnedLedgers(opening_balances)
    yield ledgers
    ledgers.delete_all()
