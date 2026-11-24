"""J41 writes to the support desk, every one answered by a stub (SH-20, SH-26 to SH-29, SH-31, SH-33, SH-34).

Never unstubbed: a real save creates a ticket on Marg's live desk and sends a WhatsApp and an email. Each
test first proves its stub answered (`capture_one` checks the response came from the stub, and the test
asserts the captured payload fields from the code) and only then looks at the screen. The send guard
aborts anything the stub did not answer and fails the test in teardown.
"""

import base64
import re

import pytest
from playwright.sync_api import FilePayload, Page

from pages.accounting.toasts import Toasts
from pages.components.app_texts import RECORD_SAVED, RECORD_UPDATED
from pages.components.confirm_dialog import ConfirmDialog
from pages.components.stubbed_endpoint import StubbedEndpoint, StubReply
from pages.support.desk_feed import DeskFeed, write_refused
from pages.support.support_chat import SupportChat
from pages.support.ticket_list import SupportTicketList
from pages.support.ticket_modal import UPDATE_TITLE, TicketModal
from test_data.support import (
    BILL_NOT_SAVING,
    BILLING,
    CLOSED_TICKET,
    PENDING_TICKET,
    REFUSAL_MESSAGE,
    REOPEN_MESSAGE,
    SALE_BILL,
    UNICODE_DESCRIPTION,
)

pytestmark = [pytest.mark.p3, pytest.mark.journey("support-helpdesk")]

RECORD_DELETED = re.compile("Record deleted successfully", re.IGNORECASE)
DELETE_QUESTION = "Are you sure you want to delete the selected Record?"
REOPENED_STATUS = "5"
# Filled from the session and the build (`create-ticket.component.ts:349-397`, `:424-432`).
CONTEXT_FIELDS = {
    "Mobile",
    "FirmName",
    "LicNo",
    "PartnerCode",
    "ProductLinkId",
    "ProductName",
    "Userid",
    "MBVersion",
    "MBDomain",
    "BuildOn",
    "UserEmail",
    "BranchName",
    "BranchCode",
}
SCREENSHOT: FilePayload = {"name": "qa-screen.png", "mimeType": "image/png", "buffer": b"\x89PNG\r\n\x1a\nQA"}


# SH-26
def test_save_sends_a_new_ticket_with_the_chosen_ids(
    filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    body = save_stub.capture_one(filled_modal.save).json_body()

    assert (body["ID"], body["ProblemType_id"]) == (0, "1")
    assert (body["SubDispostionID"], body["ProblemTypeMargBookID"], body["SubProblemTypeMargBookID"]) == (
        BILLING.choice_id,
        SALE_BILL.choice_id,
        BILL_NOT_SAVING.choice_id,
    )


# SH-26
def test_save_sends_the_names_of_the_chosen_options(
    filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    body = save_stub.capture_one(filled_modal.save).json_body()

    names = (body["SubDispostionID_D"], body["ProblemTypeMargBookID_D"], body["SubProblemTypeMargBookID_D"])
    assert names == (BILLING.name, SALE_BILL.name, BILL_NOT_SAVING.name)


# SH-26
def test_save_sends_the_session_and_build_fields(
    filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    body = save_stub.capture_one(filled_modal.save).json_body()

    assert body.keys() >= CONTEXT_FIELDS


# SH-26
def test_save_sends_the_attachment_in_base64(filled_modal: TicketModal, save_stub: StubbedEndpoint) -> None:
    filled_modal.attach(SCREENSHOT)
    filled_modal.expect_attached(SCREENSHOT["name"])

    body = save_stub.capture_one(filled_modal.save).json_body()

    assert body["ImageName"] == SCREENSHOT["name"]
    assert base64.b64decode(body["FileContent"]) == SCREENSHOT["buffer"]


# SH-26
def test_accepted_save_confirms_and_closes_the_modal(
    guarded_page: Page, filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    body = save_stub.capture_one(filled_modal.save).json_body()
    assert body["ID"] == 0

    Toasts(guarded_page).expect_success_saying(RECORD_SAVED)
    filled_modal.expect_closed()


# SH-26
def test_accepted_save_reloads_the_list(
    desk_feed: DeskFeed, filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    desk_feed.ticket_list.capture_one(lambda: save_stub.capture_one(filled_modal.save))


# SH-20
def test_hindi_and_emoji_description_is_sent_as_typed(
    filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    filled_modal.write_description(UNICODE_DESCRIPTION)

    body = save_stub.capture_one(filled_modal.save).json_body()

    assert body["Description"] == UNICODE_DESCRIPTION


# SH-27
def test_refused_save_shows_the_refusal(
    guarded_page: Page, filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    save_stub.answer_with(write_refused(REFUSAL_MESSAGE))

    save_stub.capture_one(filled_modal.save)

    Toasts(guarded_page).expect_any_saying(re.compile(REFUSAL_MESSAGE))


# SH-27
def test_refused_save_keeps_the_ticket_open(filled_modal: TicketModal, save_stub: StubbedEndpoint) -> None:
    save_stub.answer_with(write_refused(REFUSAL_MESSAGE))
    typed = filled_modal.description()

    save_stub.capture_one(filled_modal.save)

    filled_modal.expect_open()
    filled_modal.expect_description(typed)


# SH-27
def test_save_without_tenant_header_keeps_the_ticket_open(
    filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    save_stub.answer_with(StubReply({"Message": "Dbinfolinkid is zero"}, status=417))
    typed = filled_modal.description()

    save_stub.capture_one(filled_modal.save)

    filled_modal.expect_open()
    filled_modal.expect_description(typed)


# SH-28 (no in-flight guard in the code: more than one request is a defect)
def test_double_click_on_save_sends_one_ticket(filled_modal: TicketModal, save_stub: StubbedEndpoint) -> None:
    save_stub.capture_one(filled_modal.double_click_save)

    assert save_stub.answered_once_things_settle() == 1


# SH-29 (code risk D1: F10 reads `editdata.TicketNo` of a new ticket and throws)
def test_f10_saves_a_new_ticket_like_the_save_button(
    filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    body = save_stub.capture_one(filled_modal.press_f10).json_body()

    assert body["ID"] == 0


# SH-31
def test_edit_of_a_pending_ticket_opens_it_filled_in(
    guarded_page: Page, ticket_list: SupportTicketList
) -> None:
    ticket_list.ask_to_edit(PENDING_TICKET.ticket_no)

    modal = TicketModal(guarded_page, UPDATE_TITLE)
    modal.expect_chosen(
        PENDING_TICKET.main_disposition.name,
        PENDING_TICKET.sub_disposition.name,
        PENDING_TICKET.problem_type.name,
    )
    modal.expect_description(PENDING_TICKET.description)


# SH-31
def test_update_sends_the_ticket_with_its_id(
    guarded_page: Page, ticket_list: SupportTicketList, save_stub: StubbedEndpoint
) -> None:
    ticket_list.ask_to_edit(PENDING_TICKET.ticket_no)
    modal = TicketModal(guarded_page, UPDATE_TITLE)
    modal.expect_description(PENDING_TICKET.description)

    body = save_stub.capture_one(modal.update).json_body()

    assert str(body["ID"]) == str(PENDING_TICKET.ticket_id)


# SH-31
def test_accepted_update_confirms(
    guarded_page: Page, ticket_list: SupportTicketList, save_stub: StubbedEndpoint
) -> None:
    ticket_list.ask_to_edit(PENDING_TICKET.ticket_no)
    modal = TicketModal(guarded_page, UPDATE_TITLE)
    modal.expect_description(PENDING_TICKET.description)
    body = save_stub.capture_one(modal.update).json_body()
    assert str(body["ID"]) == str(PENDING_TICKET.ticket_id)

    Toasts(guarded_page).expect_success_saying(RECORD_UPDATED)


# SH-33
def test_delete_of_a_pending_ticket_asks_first(guarded_page: Page, ticket_list: SupportTicketList) -> None:
    ticket_list.ask_to_delete(PENDING_TICKET.ticket_no)

    ConfirmDialog(guarded_page).expect_asking(DELETE_QUESTION)


# SH-33
def test_confirmed_delete_sends_the_ticket_id(
    guarded_page: Page, ticket_list: SupportTicketList, delete_stub: StubbedEndpoint
) -> None:
    ticket_list.ask_to_delete(PENDING_TICKET.ticket_no)

    body = delete_stub.capture_one(ConfirmDialog(guarded_page).answer_yes).json_body()

    assert (body["Usertypeid"], str(body["Id"])) == ("0", str(PENDING_TICKET.ticket_id))
    assert "Userid" in body


# SH-33
def test_confirmed_delete_reports_success(
    guarded_page: Page, ticket_list: SupportTicketList, delete_stub: StubbedEndpoint
) -> None:
    ticket_list.ask_to_delete(PENDING_TICKET.ticket_no)
    body = delete_stub.capture_one(ConfirmDialog(guarded_page).answer_yes).json_body()
    assert str(body["Id"]) == str(PENDING_TICKET.ticket_id)

    Toasts(guarded_page).expect_success_saying(RECORD_DELETED)


# SH-33
def test_cancelled_delete_sends_nothing(
    guarded_page: Page, ticket_list: SupportTicketList, delete_stub: StubbedEndpoint
) -> None:
    ticket_list.ask_to_delete(PENDING_TICKET.ticket_no)

    delete_stub.expect_none_during(ConfirmDialog(guarded_page).answer_no)


# SH-34
def test_reopened_chat_lets_the_user_type(guarded_page: Page, ticket_list: SupportTicketList) -> None:
    ticket_list.reopen(CLOSED_TICKET.ticket_no)

    SupportChat(guarded_page).expect_typing_enabled()


# SH-34
def test_reopen_message_is_sent_with_status_5(
    guarded_page: Page, ticket_list: SupportTicketList, reopen_stub: StubbedEndpoint
) -> None:
    ticket_list.reopen(CLOSED_TICKET.ticket_no)
    chat = SupportChat(guarded_page)
    chat.expect_typing_enabled()

    body = reopen_stub.capture_one(lambda: chat.send(REOPEN_MESSAGE)).json_body()

    assert (str(body["Id"]), body["Status"], body["Remarks"]) == (
        str(CLOSED_TICKET.ticket_id),
        REOPENED_STATUS,
        REOPEN_MESSAGE,
    )


# SH-34
def test_sent_reopen_message_locks_typing_again(
    guarded_page: Page, ticket_list: SupportTicketList, reopen_stub: StubbedEndpoint
) -> None:
    ticket_list.reopen(CLOSED_TICKET.ticket_no)
    chat = SupportChat(guarded_page)
    chat.expect_typing_enabled()
    body = reopen_stub.capture_one(lambda: chat.send(REOPEN_MESSAGE)).json_body()
    assert body["Remarks"] == REOPEN_MESSAGE

    chat.expect_typing_disabled()
