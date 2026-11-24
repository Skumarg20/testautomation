"""J41 Support Ticket list (SH-05 to SH-09, SH-30, SH-32, SH-35, SH-41). The list, the dispositions and the
chat are served (test_data/support.py), except in SH-05, which reads the login's real tickets."""

import re

import pytest
from playwright.sync_api import Page

from config.settings import settings
from pages.accounting.toasts import Toasts
from pages.login_page import LoginPage
from pages.support.support_chat import SupportChat
from pages.support.ticket_list import PATH, SupportTicketList
from test_data.support import CLOSED_TICKET, NEWEST_FIRST, PARTNER_REPLY, PENDING_TICKET

pytestmark = [pytest.mark.p3, pytest.mark.journey("support-helpdesk")]

COLUMNS = ["S.No.", "Ticket ID", "ProblemType", "Description", "Status", "ReOpen", "Action"]
ANYDESK = "https://anydesk.com/en/downloads/thank-you?dv=win_exe"
CANNOT_EDIT = re.compile("You cant edit this record")
CANNOT_DELETE = re.compile("You cant delete this record")


# SH-05
def test_logged_in_user_reaches_the_list_directly(live_ticket_list: SupportTicketList) -> None:
    live_ticket_list.expect_header_actions()


# SH-06
def test_list_without_a_session_redirects_to_login(guarded_plain_page: Page) -> None:
    guarded_plain_page.goto(f"{settings.margbooks_qa_url}{PATH}")

    LoginPage(guarded_plain_page).expect_on_login_host()


# SH-07
def test_list_shows_the_ticket_columns(ticket_list: SupportTicketList) -> None:
    assert ticket_list.column_headers() == COLUMNS


# SH-07
def test_tickets_are_listed_newest_first(ticket_list: SupportTicketList) -> None:
    assert ticket_list.ticket_numbers_top_down() == list(NEWEST_FIRST)


# SH-08
@pytest.mark.parametrize(
    ("label", "value"),
    [
        ("Ticket Date", PENDING_TICKET.ticket_date[:10]),
        ("Main Disposition", PENDING_TICKET.main_disposition.name),
        ("Sub Disposition", PENDING_TICKET.sub_disposition.name),
        ("Attachment", "✅"),
    ],
)
def test_focused_ticket_fills_other_info(ticket_list: SupportTicketList, label: str, value: str) -> None:
    ticket_list.focus_ticket(PENDING_TICKET.ticket_no)

    ticket_list.expect_other_info(label, value)


# SH-08
def test_ticket_without_attachment_shows_a_cross(ticket_list: SupportTicketList) -> None:
    ticket_list.focus_ticket(CLOSED_TICKET.ticket_no)

    ticket_list.expect_other_info("Attachment", "❌")


# SH-09 (code risk D11: the double click is ignored while `isFocusOnForm` stays true)
def test_double_click_opens_the_chat_of_the_ticket(
    guarded_page: Page, ticket_list: SupportTicketList
) -> None:
    ticket_list.open_chat_by_double_click(PENDING_TICKET.ticket_no)

    chat = SupportChat(guarded_page)
    chat.expect_open_for(PENDING_TICKET.ticket_id)
    chat.expect_message(PARTNER_REPLY.text)


# SH-09
def test_chat_opened_from_the_list_is_read_only(guarded_page: Page, ticket_list: SupportTicketList) -> None:
    ticket_list.open_chat_by_double_click(PENDING_TICKET.ticket_no)

    SupportChat(guarded_page).expect_typing_disabled()


# SH-09
def test_escape_closes_the_chat(guarded_page: Page, ticket_list: SupportTicketList) -> None:
    ticket_list.open_chat_by_double_click(PENDING_TICKET.ticket_no)
    chat = SupportChat(guarded_page)
    chat.expect_open_for(PENDING_TICKET.ticket_id)

    chat.close_with_escape()

    chat.expect_closed()


# SH-30
def test_edit_of_a_closed_ticket_is_refused(guarded_page: Page, ticket_list: SupportTicketList) -> None:
    ticket_list.ask_to_edit(CLOSED_TICKET.ticket_no)

    Toasts(guarded_page).expect_any_saying(CANNOT_EDIT)


# SH-32
def test_delete_of_a_closed_ticket_is_refused(guarded_page: Page, ticket_list: SupportTicketList) -> None:
    ticket_list.ask_to_delete(CLOSED_TICKET.ticket_no)

    Toasts(guarded_page).expect_any_saying(CANNOT_DELETE)


# SH-34
def test_reopen_is_offered_for_a_closed_ticket(ticket_list: SupportTicketList) -> None:
    ticket_list.expect_reopen_offered(CLOSED_TICKET.ticket_no)


# SH-34
def test_reopen_is_not_offered_for_a_pending_ticket(ticket_list: SupportTicketList) -> None:
    ticket_list.expect_reopen_not_offered(PENDING_TICKET.ticket_no)


# SH-35 (code risk D8: the search filters on `Problemtype`, not on the visible column)
def test_search_by_ticket_id_keeps_only_that_ticket(ticket_list: SupportTicketList) -> None:
    ticket_list.search(PENDING_TICKET.ticket_no)

    ticket_list.expect_listed(PENDING_TICKET.ticket_no)
    ticket_list.expect_not_listed(CLOSED_TICKET.ticket_no)


# SH-35
def test_search_by_visible_problem_type_finds_the_ticket(ticket_list: SupportTicketList) -> None:
    ticket_list.search(CLOSED_TICKET.problem_type.name)

    ticket_list.expect_listed(CLOSED_TICKET.ticket_no)
    ticket_list.expect_not_listed(PENDING_TICKET.ticket_no)


# SH-41
def test_remote_support_links_to_the_anydesk_download(ticket_list: SupportTicketList) -> None:
    ticket_list.expect_remote_support_link(ANYDESK)
