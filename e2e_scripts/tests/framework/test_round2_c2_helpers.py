"""Offline checks of the round-2 part C2 helpers: mail post parsing, amounts, option matching, endpoints."""

import json
from decimal import Decimal

import pytest

from pages.components.stubbed_endpoint import AnsweredRequest
from pages.masters.round2_c2.owned_parties import email_of
from pages.sale.manual.option_settings import OptionNotOfferedError, index_of_option
from pages.sale.round2_c2.email_sms import SEND_GUARD, SEND_SMS, TRIGGER_MAIL, amount_in, sent_mail
from test_data.masters import PartyLedgerSpec

pytestmark = pytest.mark.framework


def test_sent_mail_reads_keys_whatever_their_case() -> None:
    post = {
        "EmailId": "x",
        "emailid": "a@example.com",
        "userName": "Ann",
        "body": "Rs. 225.00",
        "InvoiceExportReport": {"BillLinkID": 77},
    }
    request = AnsweredRequest("POST", "https://x/Template/TriggerMail", json.dumps(post))

    mail = sent_mail(request)

    assert (mail.email, mail.party, mail.bill_link_id) == ("a@example.com", "Ann", "77")
    assert amount_in(mail.body, Decimal(225))
    assert not amount_in(mail.body, Decimal(150))


def test_send_endpoints_are_matched_and_guarded() -> None:
    assert TRIGGER_MAIL.search("api/Template/multiEmailTrigger")
    assert SEND_SMS.search("api/RegisterUser/SendSMSTemplate")
    assert SEND_GUARD.search("api/RegisterUser/SendSMSTemplate")
    assert not SEND_GUARD.search("api/PrintTemplate/PrintTemplatePath")


def test_email_is_derived_from_the_unique_party_name() -> None:
    party = PartyLedgerSpec("QA-ab12-Cust-1", "Sundry Debtors", "Others", "9000000000")
    assert email_of(party) == "qa-ab12-cust-1@example.com"


def test_discontinue_is_not_confused_with_continue() -> None:
    assert index_of_option("Status", "discontinue", ["Continue", "Discontinue"]) == 1
    with pytest.raises(OptionNotOfferedError):
        index_of_option("Visibility", "hide", ["Show"])


def test_store_refusal_and_right_columns_are_stable() -> None:
    from pages.admin.round2_c2.role_rights import RightColumn
    from pages.sale.round2_c2.store_billing import STOCK_REFUSED

    assert [column.name for column in sorted(RightColumn, key=lambda each: each.value)] == [
        "FULL",
        "CREATE",
        "EDIT",
        "DELETE",
        "EXPORT",
    ]
    assert STOCK_REFUSED.search("Salable stock 4.")
    assert STOCK_REFUSED.search("Stock going in negative!")
