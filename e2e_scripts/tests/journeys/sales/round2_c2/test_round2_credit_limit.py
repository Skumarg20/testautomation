"""Ajay rows 72 and 86: a bill above the party's credit limit follows the party's "Credit Limit Action".

Rule (processout.transaction.component.ts:13621-13665): available = limit - party debit balance (a new
party has
none); when it is below the bill total the "Credit Limit Alert!" window opens, with "Difference" = total -
limit.
Only Indicate -> Yes / No; Follow Strictly -> OK. Stop Billing draws nothing on the web (:13650, empty
branch):
Decision needed, see scenarios.md. A 0% item makes the bill total equal the line rate.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.components.bill_totals import BillTotals
from pages.masters.round2_c2.ledger_windows import CreditLimitAction
from pages.masters.round2_c2.owned_parties import OwnedParties
from pages.sale.round2_c2.credit_alert import CreditLimitAlert
from pages.sale.round2_c2.party_and_type import OpenBillDesk

pytestmark = [pytest.mark.p2, pytest.mark.journey("sale-bill-creation")]

LIMIT = Decimal(100)
BILL_TOTAL = Decimal(150)
EXCEEDS_BY = BILL_TOTAL - LIMIT


@dataclass(frozen=True)
class Scene:
    page: Page
    parties: OwnedParties
    desk: OpenBillDesk


@pytest.fixture
def scene(guarded_page: Page, parties: OwnedParties, zero_rated_item_name: str) -> Iterator[Scene]:
    yield Scene(guarded_page, parties, OpenBillDesk(guarded_page, zero_rated_item_name))
    if guarded_page.locator("[id^=btnEsc]").first.is_visible():
        BillTotals(guarded_page).leave_without_saving()


@pytest.mark.parametrize(
    ("action", "buttons"),
    [
        pytest.param(CreditLimitAction.ONLY_INDICATE, ("Yes", "No"), id="row-72-only-indicate"),
        pytest.param(CreditLimitAction.FOLLOW_STRICTLY, ("OK",), id="row-86-follow-strictly"),
    ],
)
def test_bill_above_the_limit_opens_the_credit_limit_alert(
    scene: Scene, action: CreditLimitAction, buttons: tuple[str, ...]
) -> None:
    party = scene.parties.saved_with_credit_limit(LIMIT, action)
    PartyAvailability(scene.page).wait_until_selectable(party.name)

    scene.desk.open_with_line(party.name, BILL_TOTAL)

    alert = CreditLimitAlert(scene.page)
    alert.expect_shown()
    alert.expect_party_limit(LIMIT)
    alert.expect_difference(EXCEEDS_BY)
    alert.expect_choice(buttons)
