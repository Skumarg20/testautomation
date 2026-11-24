"""Manual cases 53, 56, 156, 157, 160, 161: sharing sale bills from the sale bill list, nothing really sent.

A garments customer of the test's own gets two unpaid bills (`SaleBillDesk`, the outstanding journey's path);
everything is deleted afterwards. Every send is stubbed (`StubbedEndpoint`) or aborted by the send guard, and
a WhatsApp web window is blocked, so nothing reaches a person. Rules cited are in `bill_list_share.py`:
Email needs a stored e-mail id, Whatsapp takes one bill and asks for a number when the party has none
(Common.service.ts:4405-4412, the same "Share on Whatsapp" window the report share uses).
The ledger form helper has no e-mail field, so no test party has an e-mail id: sending an e-mail (row 54, 159)
is not scripted; see the scenario file.
"""

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.outstanding.exempt_item import ExemptItem
from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.accounting.toasts import Toasts
from pages.accounting.waiting import appears_within
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.components.send_guard import SendGuard
from pages.components.stubbed_endpoint import StubbedEndpoint, StubReply
from pages.dashboard_page import DashboardPage
from pages.masters.master_records import MasterRecords
from pages.notifications_export.delivery_endpoints import DELIVERY_OR_GLOBAL_WRITE, WHATSAPP_SEND
from pages.notifications_export.json_route import success_envelope
from pages.notifications_export.report_share_export import ReportShareExport
from pages.sale.manual import messages
from pages.sale.manual.bill_list_share import EMAIL_NOT_VERIFIED, SaleBillListShare
from pages.sale.manual.bill_messages import BillMessages
from test_data.masters import MasterDataFactory
from test_data.notifications_export import QA_WHATSAPP_NUMBER

pytestmark = [pytest.mark.p2, pytest.mark.journey("notifications-export")]

GARMENTS: Account = "garments"
WEB_WHATSAPP = re.compile(r"web\.whatsapp\.com", re.IGNORECASE)
WHATSAPP_SENT = re.compile(re.escape("Whastapp Sent Succesfully !"), re.IGNORECASE)
BILL_AMOUNT = Decimal(150)
NUMBER_PROMPT_MS = 30_000


@dataclass(frozen=True)
class OwnedBills:
    party: str
    numbers: tuple[str, str]


@pytest.fixture
def guarded_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    """The garments login on its dashboard, with every send aborted and the WhatsApp web window blocked."""
    page = page_as(GARMENTS)
    guards = [SendGuard(page, DELIVERY_OR_GLOBAL_WRITE), SendGuard(page, WEB_WHATSAPP)]
    for guard in guards:
        guard.arm()
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    yield page
    for guard in guards:
        guard.expect_nothing_sent()


@pytest.fixture
def two_bills(guarded_page: Page, run_id: str) -> Iterator[OwnedBills]:
    """A new customer with two unpaid bills; the bills go first, then the customer."""
    records = MasterRecords(guarded_page, MasterDataFactory(run_id))
    desk: SaleBillDesk | None = None
    numbers: list[str] = []
    try:
        party = records.saved_customer().name
        PartyAvailability(guarded_page).wait_until_selectable(party)
        desk = SaleBillDesk(guarded_page, ExemptItem(guarded_page).ensure_exists())
        numbers = [desk.create(party, BILL_AMOUNT, Decimal(0)) for _ in range(2)]
        yield OwnedBills(party, (numbers[0], numbers[1]))
    finally:
        if desk is not None:
            for number in numbers:
                desk.delete(number)
        records.delete_all()


@pytest.fixture
def listed(guarded_page: Page, two_bills: OwnedBills) -> SaleBillListShare:
    share = SaleBillListShare(guarded_page)
    share.open_for(two_bills.party)
    return share


@pytest.fixture
def whatsapp(guarded_page: Page) -> StubbedEndpoint:
    stub = StubbedEndpoint(guarded_page, WHATSAPP_SEND)
    stub.answer_with(StubReply(success_envelope(True)))
    return stub


def number_asked_or_skip(page: Page) -> ReportShareExport:
    """The "Share on Whatsapp" window; a party that has a number goes straight to the (stubbed) send."""
    window = ReportShareExport(page)
    asked = page.get_by_role("dialog").filter(has_text="Share on Whatsapp")
    if not appears_within(asked, NUMBER_PROMPT_MS):
        pytest.skip("the test party has a WhatsApp number, so no number is asked for")
    return window


def test_email_without_a_stored_email_id_is_refused(listed: SaleBillListShare, guarded_page: Page) -> None:
    """Row 157: with one bill selected the app warns that the e-mail id is not verified; nothing is sent."""
    listed.select_first_bill()

    listed.press_email()

    BillMessages(guarded_page).expect_warning_like(EMAIL_NOT_VERIFIED)


def test_email_for_every_bill_without_email_ids_is_refused(
    listed: SaleBillListShare, guarded_page: Page
) -> None:
    """Rows 160 and 161 (selected bills, all bills): the same warning, once; nothing is sent."""
    listed.select_every_bill()

    listed.press_email()

    BillMessages(guarded_page).expect_warning_like(EMAIL_NOT_VERIFIED)


def test_whatsapp_is_offered_for_one_bill_only(listed: SaleBillListShare) -> None:
    """Rows 56 and 161: with two bills selected there is no Whatsapp button, but Email stays."""
    listed.select_every_bill()

    assert listed.whatsapp_button.count() == 0
    assert listed.email_button.count() == 1


def test_whatsapp_for_a_party_without_a_number_asks_for_one(
    listed: SaleBillListShare, guarded_page: Page
) -> None:
    """Row 156: the number is asked for; closing the window warns and sends nothing."""
    listed.select_first_bill()
    listed.press_whatsapp()

    number_asked_or_skip(guarded_page).close_whatsapp_dialog()

    BillMessages(guarded_page).expect_warning(messages.WHATSAPP_NUMBER_MISSING)


def test_whatsapp_sends_the_bill_to_the_typed_number(
    listed: SaleBillListShare, guarded_page: Page, whatsapp: StubbedEndpoint
) -> None:
    """Row 53 (stubbed send): the call carries the typed number and the app says it was sent."""
    listed.select_first_bill()
    listed.press_whatsapp()
    window = number_asked_or_skip(guarded_page)

    sent = whatsapp.capture_one(lambda: window.share_with_whatsapp_number(QA_WHATSAPP_NUMBER))

    assert QA_WHATSAPP_NUMBER in f"{sent.url} {sent.post_data}"
    Toasts(guarded_page).expect_any_saying(WHATSAPP_SENT)
