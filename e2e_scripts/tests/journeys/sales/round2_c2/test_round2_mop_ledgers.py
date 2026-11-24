"""Ajay rows 41 and 122: adding and removing a ledger in the Mode Of Payment window, and an inactive ledger.

A bank ledger of the test's own (group "Bank Accounts") is added with the window's gear > Add and removed with
Delete (modeofpayment.component.ts:491-520, 970-982); the window is closed without saving the bill, so the
stored
payment list is untouched. For row 122 the ledger is first set to Status Discontinue (Other Info); the Add
list is
expected not to offer it, following the rule that transactions list only Continue ledgers
(Helper.services.ts:11728-11745). Decision needed: that rule is read from the transaction lists, the Add
list is a
Ledger Master window.
"""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.components.bill_totals import BillTotals
from pages.masters.ledger_form import LedgerForm
from pages.masters.master_records import MasterRecords
from pages.masters.round2_c2.ledger_windows import LedgerExtras
from pages.masters.round2_c2.owned_parties import OwnedParties
from pages.sale.round2_c2.mop_ledgers import PaymentDesk
from test_data.masters import MasterDataFactory

pytestmark = [pytest.mark.p2, pytest.mark.journey("sale-bill-creation")]

BANK_GROUP = "Bank Accounts"
BILL_AMOUNT = Decimal(150)


@pytest.fixture
def records(guarded_page: Page, run_id: str) -> Iterator[MasterRecords]:
    owned = MasterRecords(guarded_page, MasterDataFactory(run_id))
    yield owned
    owned.delete_all()


@pytest.fixture
def paying(
    guarded_page: Page, parties: OwnedParties, zero_rated_item_name: str
) -> Iterator[tuple[PaymentDesk, str]]:
    party = parties.saved_with_email().name
    PartyAvailability(guarded_page).wait_until_selectable(party)
    yield PaymentDesk(guarded_page, zero_rated_item_name), party
    if guarded_page.locator("[id^=btnEsc]").first.is_visible():
        guarded_page.keyboard.press("Escape")
        BillTotals(guarded_page).leave_without_saving()


def test_ledger_can_be_added_to_and_removed_from_the_payment_list(
    records: MasterRecords, paying: tuple[PaymentDesk, str]
) -> None:
    bank = records.saved_general_ledger(BANK_GROUP).name
    desk, party = paying
    window = desk.open_payment_window(party, BILL_AMOUNT)

    window.show_settings()
    window.add_ledger(bank)
    window.expect_listed(bank)
    window.delete_ledger(bank)

    window.expect_not_listed(bank)
    window.close_without_saving()


def test_inactive_ledger_is_not_offered_for_the_payment_list(
    guarded_page: Page, records: MasterRecords, paying: tuple[PaymentDesk, str]
) -> None:
    ledger = records.new_general_ledger(BANK_GROUP)
    form = LedgerForm(guarded_page)
    form.open_new()
    form.enter_general(ledger)
    LedgerExtras(guarded_page).discontinue()
    form.save()
    form.expect_saved()
    desk, party = paying
    window = desk.open_payment_window(party, BILL_AMOUNT)

    window.show_settings()

    window.expect_picker_without(ledger.name)
    window.close_without_saving()
