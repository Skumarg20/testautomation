"""Ajay rows 54, 55, 56, 158, 159, 160, 161: sharing sale bills by e-mail and SMS, nothing really sent.

A customer with an e-mail id and mobile number gets bills through the outstanding journey's desk (0% item,
so a
bill's amount is its line rate). Mail goes through Template/TriggerMail and SMS through
RegisterUser/SendSMSTemplate, both answered by stubs that record the post (pages/sale/round2_c2/email_sms.py).
Bills and the customer are deleted afterwards.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.accounting.outstanding.party_availability import PartyAvailability
from pages.accounting.outstanding.sale_bill_desk import SaleBillDesk
from pages.masters.round2_c2.owned_parties import OwnedParties, email_of
from pages.sale.manual.bill_list_share import SaleBillListShare
from pages.sale.manual.bill_messages import BillMessages
from pages.sale.round2_c2.email_sms import (
    MOBILE_NOT_FOUND,
    SAVE_AND_SMS,
    RecordingStub,
    ShareOnSaveDesk,
    amount_in,
    ledger_mobile_optional,
    sent_mail,
    stub_mail_and_sms,
    tick_first_bills,
)
from test_data.masters import PartyLedgerSpec

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("notifications-export"),
    pytest.mark.xdist_group("chemist-tenant"),
]

GARMENTS: Account = "garments"
FIRST_AMOUNT = Decimal(150)
CHANGED_AMOUNT = Decimal(225)


@dataclass(frozen=True)
class MailedParty:
    spec: PartyLedgerSpec
    email: str
    numbers: tuple[str, str, str]


@dataclass(frozen=True)
class Mailbox:
    """The page with its mail and SMS stubs."""

    page: Page
    mail: RecordingStub
    sms: RecordingStub


@pytest.fixture
def mailbox(guarded_page: Page) -> Mailbox:
    mail, sms = stub_mail_and_sms(guarded_page)
    return Mailbox(guarded_page, mail, sms)


@pytest.fixture
def mailed(mailbox: Mailbox, parties: OwnedParties, zero_rated_item_name: str) -> Iterator[MailedParty]:
    """A customer with an e-mail id and three bills of 150; bills are deleted first, then the customer."""
    spec = parties.saved_with_email()
    PartyAvailability(mailbox.page).wait_until_selectable(spec.name)
    desk = SaleBillDesk(mailbox.page, zero_rated_item_name)
    numbers: list[str] = []
    try:
        numbers = [desk.create(spec.name, FIRST_AMOUNT, Decimal(0)) for _ in range(3)]
        yield MailedParty(spec, email_of(spec), (numbers[0], numbers[1], numbers[2]))
    finally:
        for number in numbers:
            desk.delete(number)


def test_email_button_sends_the_selected_bill(mailbox: Mailbox, mailed: MailedParty) -> None:
    """Row 54: one bill ticked, Email: one mail to the party's e-mail id with its name."""
    mail = mailbox.mail
    listed = SaleBillListShare(mailbox.page)
    listed.open_for(mailed.spec.name)
    listed.select_first_bill()

    listed.press_email()

    assert mail.answered_once_things_settle() == 1
    sent = sent_mail(mail.answered[0])
    assert (sent.email, sent.party) == (mailed.email, mailed.spec.name)


def test_email_of_a_modified_bill_carries_the_new_amount(
    mailbox: Mailbox, mailed: MailedParty, zero_rated_item_name: str
) -> None:
    """Row 159: after the amount of a bill is changed the mailed text holds the new amount, not the old."""
    mail = mailbox.mail
    SaleBillDesk(mailbox.page, zero_rated_item_name).change_amount(mailed.numbers[0], CHANGED_AMOUNT)
    listed = SaleBillListShare(mailbox.page)
    listed.open_for(mailed.spec.name)
    listed.select_first_bill()

    listed.press_email()

    assert mail.answered_once_things_settle() == 1
    body = sent_mail(mail.answered[0]).body
    assert amount_in(body, CHANGED_AMOUNT)


def test_email_for_every_ticked_bill_sends_one_mail_each(mailbox: Mailbox, mailed: MailedParty) -> None:
    """Rows 56 and 161: all three bills ticked, Email: three mails, one per bill (distinct bill ids)."""
    mail = mailbox.mail
    listed = SaleBillListShare(mailbox.page)
    listed.open_for(mailed.spec.name)
    listed.select_every_bill()

    listed.press_email()

    assert mail.answered_once_things_settle() == len(mailed.numbers)
    bill_ids = {sent_mail(request).bill_link_id for request in mail.answered}
    assert len(bill_ids) == len(mailed.numbers)


def test_email_for_two_chosen_bills_sends_two_mails(mailbox: Mailbox, mailed: MailedParty) -> None:
    """Row 160: of three bills only the first two are ticked: two mails, not three."""
    mail = mailbox.mail
    listed = SaleBillListShare(mailbox.page)
    listed.open_for(mailed.spec.name)
    tick_first_bills(listed, 2)

    listed.press_email()

    assert mail.answered_once_things_settle() == 2


def test_save_and_sms_posts_the_party_mobile(
    mailbox: Mailbox, parties: OwnedParties, zero_rated_item_name: str
) -> None:
    """Row 55: the bill saved with "Save & SMS" posts one SMS to the customer's mobile number."""
    sms = mailbox.sms
    spec = parties.saved_with_email()
    PartyAvailability(mailbox.page).wait_until_selectable(spec.name)
    desk = ShareOnSaveDesk(mailbox.page, zero_rated_item_name)
    number = desk.create_with_save_action(spec.name, FIRST_AMOUNT, SAVE_AND_SMS)
    try:
        assert sms.answered_once_things_settle() == 1
        assert spec.mobile in (sms.answered[0].post_data or "")
    finally:
        desk.delete(number)


def test_save_and_sms_without_a_mobile_number_warns(
    mailbox: Mailbox, parties: OwnedParties, zero_rated_item_name: str
) -> None:
    """Row 158: a customer saved without a mobile (Control Room "Mobile Number Mandatory in Ledger" = No) gets
    the warning "Mobile no not found." after "Save & SMS", and no SMS is posted."""
    sms = mailbox.sms
    with ledger_mobile_optional(mailbox.page):
        spec = parties.saved_without_mobile()
    PartyAvailability(mailbox.page).wait_until_selectable(spec.name)
    desk = ShareOnSaveDesk(mailbox.page, zero_rated_item_name)
    number = desk.create_with_save_action(spec.name, FIRST_AMOUNT, SAVE_AND_SMS)
    try:
        BillMessages(mailbox.page).expect_warning_like(MOBILE_NOT_FOUND)
        assert sms.answered_once_things_settle() == 0
    finally:
        desk.delete(number)
