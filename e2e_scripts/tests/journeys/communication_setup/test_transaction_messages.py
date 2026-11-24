"""J30: Control Room > Transaction SMS, WhatsApp messages (specs/email-sms-whatsapp-setup.md, WA-01, WA-02).

The sending-channel buttons are never pressed; the guard in conftest.py fails the test on any save or send.
"""

import pytest

from pages.communication_setup.transaction_messages import TransactionMessages

pytestmark = [pytest.mark.p2, pytest.mark.journey("email-sms-whatsapp-setup")]

TRANSACTION_TYPES = (
    "Sale",
    "Sale Return",
    "Purchase",
    "Purchase Return",
    "Cancelled Invoice",
    "Loyality",
    "Purchase Order",
    "Sale Order",
)


def test_transaction_sms_offers_the_sending_channels(transaction_messages: TransactionMessages) -> None:
    transaction_messages.open()
    transaction_messages.expect_sending_channels()


def test_transaction_sms_lists_every_transaction_type(transaction_messages: TransactionMessages) -> None:
    transaction_messages.open()
    transaction_messages.expect_transaction_types(TRANSACTION_TYPES)


@pytest.mark.parametrize(
    ("transaction_type", "message"),
    [
        ("Purchase", "Recently, we have made a purchase with you."),
        ("Sale Return", "We have created a credit note to you as below:"),
        ("Purchase Return", "We have created a debit note to you as below:"),
        ("Cancelled Invoice", "has been cancelled."),
    ],
)
def test_choosing_a_transaction_type_previews_its_message(
    transaction_messages: TransactionMessages, transaction_type: str, message: str
) -> None:
    transaction_messages.open()
    transaction_messages.choose(transaction_type)
    transaction_messages.expect_preview_containing(message)


def test_sale_previews_a_message(transaction_messages: TransactionMessages) -> None:
    """D1: KB (careportal_enriched_v5.csv#bc739708) says choosing Sale shows its message preview."""
    transaction_messages.open()
    transaction_messages.choose("Purchase")
    transaction_messages.choose("Sale")
    transaction_messages.expect_preview_shows_a_message()
