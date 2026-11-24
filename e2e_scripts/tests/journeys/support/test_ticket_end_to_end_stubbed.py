"""J41 a ticket raised end to end (SH-40), with the desk stubbed.

A real save creates a ticket on Marg's live desk, then the server queues a WhatsApp to 91<Mobile> and mails
`Emailid` (`MargSupportController.cs:229-288`). Neither may happen from a test, so the save is answered by a
stub, the desk's list reload is served with the new ticket, and the test checks what the server would send
to (the payload) and what the user sees (the new ticket in the list). The real round trip, with the WhatsApp
and email arriving, is for Marg support on a test licence.
"""

import re

import pytest

from pages.components.stubbed_endpoint import StubbedEndpoint
from pages.support.ticket_list import SupportTicketList
from pages.support.ticket_modal import TicketModal
from test_data.support import RAISED_TICKET

pytestmark = [pytest.mark.p3, pytest.mark.journey("support-helpdesk")]

INDIAN_MOBILE = re.compile(r"^\d{10}$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+$")


# SH-40
def test_new_ticket_names_the_mobile_for_the_whatsapp(
    filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    body = save_stub.capture_one(filled_modal.save).json_body()

    assert INDIAN_MOBILE.match(str(body["Mobile"]))


# SH-40
def test_new_ticket_names_the_email_for_the_confirmation(
    filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    body = save_stub.capture_one(filled_modal.save).json_body()

    assert EMAIL.match(str(body["Emailid"]))


# SH-40
def test_saved_ticket_appears_in_the_reloaded_list(
    list_awaiting_raised_ticket: SupportTicketList, filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    body = save_stub.capture_one(filled_modal.save).json_body()
    assert body["ID"] == 0

    list_awaiting_raised_ticket.expect_listed(RAISED_TICKET.ticket_no)
