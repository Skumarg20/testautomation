"""J19 trial balance, day book and profit & loss (specs/accounting-reports.md).

Tenant totals move while other tests run, so each test checks the report lines of its own ledgers and
voucher, plus the one invariant that holds whatever the tenant holds: Trial Balance Dr total = Cr total.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.accounting.journal_page import JournalPage
from pages.accounting.journal_voucher_list import JournalVoucherList
from pages.accounting.opening_balance_page import LedgerSpec, OpeningBalance
from pages.accounting.owned_ledgers import OwnedLedgers
from pages.accounting.voucher_cases import Leg
from pages.reports.accounting_reports import DayBookPage, DebitCredit, ProfitLossPage, TrialBalancePage
from test_data.factory import DataFactory

# The journal voucher takes the next tenant-wide voucher number, like the other journal tests.
pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("accounting-reports"),
    pytest.mark.xdist_group("chemist-tenant"),
]

NO_OPENING = OpeningBalance(Decimal(0), "Dr")
JOURNAL_AMOUNT = "250"
NOTHING = Decimal(0)


@dataclass(frozen=True)
class OwnJournal:
    expense_ledger: str
    income_ledger: str
    amount: Decimal


@pytest.fixture
def own_journal(data: DataFactory, owned_ledgers: OwnedLedgers, journal: JournalPage) -> Iterator[OwnJournal]:
    """Today's journal voucher: Dr an own Indirect Expenses ledger, Cr an own Indirect Incomes ledger."""
    expense = LedgerSpec(data.party_name("Exp"), NO_OPENING, group="Indirect Expenses")
    income = LedgerSpec(data.party_name("Inc"), NO_OPENING, group="Indirect Incomes")
    owned_ledgers.create(expense)
    owned_ledgers.create(income)
    _post_journal(
        journal, Leg("debit", expense.name, JOURNAL_AMOUNT), Leg("credit", income.name, JOURNAL_AMOUNT)
    )
    yield OwnJournal(expense.name, income.name, Decimal(JOURNAL_AMOUNT))
    JournalVoucherList(journal.page).delete_voucher_of(expense.name)


def _post_journal(journal: JournalPage, debit: Leg, credit: Leg) -> None:
    journal.open_new_voucher()
    journal.enter_date(date.today())
    for row, leg in enumerate((debit, credit)):
        journal.choose_side(row, leg.side)
        journal.select_account(row, leg.account)
        journal.enter_leg_amount(row, leg)
    journal.enter_narration(f"QA journal for {debit.account}")
    journal.save()
    journal.expect_saved()


def test_trial_balance_shows_own_opening_balance_on_the_debit_side(
    data: DataFactory, owned_ledgers: OwnedLedgers, accounting_page: Page
) -> None:
    ledger = LedgerSpec(data.party_name("TB"), OpeningBalance(Decimal("1500"), "Dr"))
    owned_ledgers.create(ledger)
    report = TrialBalancePage(accounting_page)

    report.open()
    report.expand_all()

    assert report.balance_of(ledger.name) == DebitCredit(Decimal("1500"), NOTHING)


def test_trial_balance_debit_total_equals_credit_total(accounting_page: Page) -> None:
    report = TrialBalancePage(accounting_page)

    report.open()
    totals = report.grand_totals()

    assert totals.debit == totals.credit, f"Trial Balance grand totals differ: {totals}"


def test_day_book_lists_both_lines_of_own_journal(own_journal: OwnJournal, accounting_page: Page) -> None:
    report = DayBookPage(accounting_page)

    report.open()
    debit_line = report.entry_of(own_journal.expense_ledger)
    credit_line = report.entry_of(own_journal.income_ledger)

    assert debit_line.voucher_type == "Journal"
    assert debit_line.amounts == DebitCredit(own_journal.amount, NOTHING)
    assert credit_line.amounts == DebitCredit(NOTHING, own_journal.amount)
    assert credit_line.voucher_no == debit_line.voucher_no


def test_profit_and_loss_shows_own_expense_and_income(own_journal: OwnJournal, accounting_page: Page) -> None:
    report = ProfitLossPage(accounting_page)

    report.open()
    report.expand_all()

    assert report.expense_amount(own_journal.expense_ledger) == own_journal.amount
    assert report.income_amount(own_journal.income_ledger) == own_journal.amount
