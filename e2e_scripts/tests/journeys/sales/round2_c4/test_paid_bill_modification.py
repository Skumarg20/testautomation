"""Sale bill rows 115 and 183: a bill with a payment taken at save (Mode Of Payment window).

Row 115 (delete a paid bill) is OA-047 in `tests/journeys/accounting/outstanding/test_bill_time_payment.py`
(bill of 1000, 300 paid, deleted: outstanding 0, advance 0). Row 183 (modify a paid bill) is here: the payment
stays with the bill whatever the new amount, so the outstanding is the new amount less the 300 paid; the
amount can be changed up or down (OA-002/003 do it for an unpaid bill, OA-044..046 change the payment).
Same fixtures as the outstanding journey: a new garments customer per test and the 0% GST item.
"""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.outstanding.credit_desks import ReceiptDesk, SaleReturnDesk
from pages.accounting.outstanding.exempt_item import ExemptItem
from pages.accounting.outstanding.outstanding_report import OutstandingReport
from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.accounting.outstanding.scenario import CaseDesks, CreditDocuments, OutstandingScenario
from pages.company_switch_page import GARMENTS_COMPANY
from pages.dashboard_page import DashboardPage
from pages.masters.master_records import MasterRecords
from test_data.masters import MasterDataFactory
from test_data.outstanding_cases import PAID_300, case, modify_bill, party
from test_data.outstanding_steps import CreditKind, OutstandingCase

pytestmark = [pytest.mark.p1, pytest.mark.journey("payments-ledger")]

GARMENTS: Account = "garments"
CASES = [
    case((901, "Paid bill modified up"), [PAID_300, modify_bill("A", 1500)], party(1200, 0)),
    case(
        (902, "Paid bill modified down, still above the payment"),
        [PAID_300, modify_bill("A", 600)],
        party(300, 0),
    ),
]


@pytest.fixture
def garments_page(company_page: Callable[[Account, str], Page]) -> Page:
    page = company_page(GARMENTS, GARMENTS_COMPANY)
    DashboardPage(page).expect_loaded()
    return page


@pytest.fixture
def scenario(garments_page: Page, run_id: str) -> OutstandingScenario:
    customer = MasterRecords(garments_page, MasterDataFactory(run_id)).saved_customer().name
    PartyAvailability(garments_page).wait_until_selectable(customer)
    item = ExemptItem(garments_page).ensure_exists()
    credits: dict[CreditKind, CreditDocuments] = {
        CreditKind.RECEIPT: ReceiptDesk(garments_page),
        CreditKind.SALE_RETURN: SaleReturnDesk(garments_page, item),
    }
    desks = CaseDesks(SaleBillDesk(garments_page, item), credits, OutstandingReport(garments_page))
    return OutstandingScenario(customer, desks)


@pytest.mark.parametrize("modified", CASES, ids=lambda c: c.id)
def test_modified_paid_bill_keeps_its_payment(
    scenario: OutstandingScenario, modified: OutstandingCase
) -> None:
    scenario.play(modified)

    scenario.expect_balances(modified.expected)
