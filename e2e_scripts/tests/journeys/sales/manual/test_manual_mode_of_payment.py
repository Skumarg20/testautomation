"""Manual cases 40, 117, 119, 121: what is taken in the Mode Of Payment window when a bill is saved.

A garments customer of the test's own gets one bill of 100 for the 0% GST item (so the bill is exactly its
line rate); the bill and the customer are deleted afterwards. The check is the party's outstanding on the
ledger's F8 report (`OutstandingReport`), as the ported OA-041..OA-060 cases do: the bill amount less what was
taken at the save. Splitting needs a second payment ledger in the window; a company that lists only Cash
Account skips with that reason (the window's own Add setting is not driven, see the scenario file).
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.accounting.outstanding.outstanding_report import OutstandingReport
from pages.components.bill_totals import BillTotals
from pages.sale.manual.split_payment import SecondPaymentLedgerMissingError, SplitPaymentDesk

pytestmark = [pytest.mark.p1, pytest.mark.journey("payments-ledger")]

BILL_AMOUNT = Decimal(100)
NOTHING = Decimal(0)


@dataclass
class CustomerBills:
    """The test's customer and the numbers of the bills saved for it."""

    party: str
    numbers: list[str] = field(default_factory=list)


@pytest.fixture
def desk(garments_dashboard: Page, exempt_item_name: str) -> SplitPaymentDesk:
    return SplitPaymentDesk(garments_dashboard, exempt_item_name)


@pytest.fixture
def bills(desk: SplitPaymentDesk, owned_customer: str) -> Iterator[CustomerBills]:
    """Bills are deleted before the customer."""
    saved = CustomerBills(owned_customer)
    yield saved
    for number in saved.numbers:
        desk.delete(number)


def save_split_or_skip(desk: SplitPaymentDesk, party: str, split: tuple[Decimal, Decimal]) -> str:
    try:
        return desk.create_paid_across_two_ledgers(party, BILL_AMOUNT, split)
    except SecondPaymentLedgerMissingError:
        BillTotals(desk.page).leave_without_saving()
        pytest.skip("the Mode Of Payment window lists only one payment ledger")


@pytest.mark.parametrize(
    "split",
    [
        pytest.param((Decimal(40), Decimal(60)), id="cash-40-and-second-ledger-60"),
        pytest.param((NOTHING, BILL_AMOUNT), id="whole-amount-in-the-second-ledger"),
    ],
)
def test_payment_across_two_ledgers_settles_the_bill(
    desk: SplitPaymentDesk, bills: CustomerBills, split: tuple[Decimal, Decimal]
) -> None:
    """Rows 40 (payment into another ledger saves), 117 and 121 (amounts split between two ledgers)."""
    bills.numbers.append(save_split_or_skip(desk, bills.party, split))

    assert OutstandingReport(desk.page).read(bills.party).outstanding == NOTHING


def test_zero_payment_leaves_the_whole_bill_outstanding(desk: SplitPaymentDesk, bills: CustomerBills) -> None:
    """Row 119: nothing entered in the window saves a credit bill."""
    bills.numbers.append(desk.create(bills.party, BILL_AMOUNT, NOTHING))

    assert OutstandingReport(desk.page).read(bills.party).outstanding == BILL_AMOUNT
