"""J41 Create Ticket modal up to, but not including, a save (SH-10 to SH-19, SH-25, SH-36). A Save press
here is one the app must block before sending; a stub stands ready and must stay unanswered."""

import re

import pytest
from playwright.sync_api import ConsoleMessage, Page

from pages.accounting.toasts import Toasts
from pages.components.stubbed_endpoint import StubbedEndpoint
from pages.support.desk_feed import DeskFeed
from pages.support.help_drawer import HelpDrawer
from pages.support.ticket_list import SupportTicketList
from pages.support.ticket_modal import TicketModal
from test_data.support import (
    BILL_NOT_SAVING,
    BILLING,
    GST,
    PRINT_ISSUE,
    PURCHASE_BILL,
    REGEX_DESCRIPTION,
    SALE_BILL,
    SUGGESTION,
)

pytestmark = [pytest.mark.p3, pytest.mark.journey("support-helpdesk")]

DESCRIPTION_LIMIT = 1000
SUGGESTION_KEYWORD = "gstr"
TOO_SHORT_FOR_SUGGESTIONS = "gst"
INTERNET_REQUIRED = re.compile(re.escape("Internet Required for this option!"))


# SH-10
def test_create_button_opens_the_create_ticket_modal(live_ticket_list: SupportTicketList) -> None:
    modal = live_ticket_list.start_ticket()

    modal.expect_open()
    modal.expect_fields()


# SH-10
def test_f2_opens_the_create_ticket_modal(ticket_list: SupportTicketList) -> None:
    modal = ticket_list.start_ticket_with_f2()

    modal.expect_open()


# SH-11
def test_main_disposition_narrows_the_sub_dispositions(create_modal: TicketModal) -> None:
    create_modal.choose_main_disposition(BILLING.name)

    assert create_modal.sub_dispositions() == ["Select", SALE_BILL.name, PURCHASE_BILL.name]


# SH-11
def test_main_disposition_moves_focus_to_sub_disposition(create_modal: TicketModal) -> None:
    create_modal.choose_main_disposition(BILLING.name)

    create_modal.expect_sub_disposition_focused()


# SH-12
def test_sub_disposition_narrows_the_problem_types(create_modal: TicketModal) -> None:
    create_modal.choose_main_disposition(BILLING.name)
    create_modal.choose_sub_disposition(SALE_BILL.name)

    assert create_modal.problem_types() == ["Select", BILL_NOT_SAVING.name, PRINT_ISSUE.name]


# SH-12
def test_problem_type_moves_focus_to_description(create_modal: TicketModal) -> None:
    create_modal.choose_main_disposition(BILLING.name)
    create_modal.choose_sub_disposition(SALE_BILL.name)

    create_modal.choose_problem_type(BILL_NOT_SAVING.name)

    create_modal.expect_description_focused()


# SH-13
def test_hidden_main_dispositions_are_not_offered(create_modal: TicketModal) -> None:
    assert create_modal.main_dispositions() == ["Select", BILLING.name, GST.name]


# SH-14
def test_save_of_an_empty_form_sends_nothing(create_modal: TicketModal, save_stub: StubbedEndpoint) -> None:
    save_stub.expect_none_during(create_modal.save)


# SH-14 (D5: the message names "Problem Type 1", not "Main Disposition")
def test_save_of_an_empty_form_flags_main_disposition(create_modal: TicketModal) -> None:
    create_modal.save()

    create_modal.expect_required_message("Problem Type 1 required !")


# SH-14: no marker on Description, see D3
def test_save_of_an_empty_form_puts_no_marker_on_description(create_modal: TicketModal) -> None:
    create_modal.save()

    create_modal.expect_no_required_marker_on_description()


# SH-15
def test_save_without_description_sends_nothing(
    filled_modal: TicketModal, save_stub: StubbedEndpoint
) -> None:
    filled_modal.write_description("")

    save_stub.expect_none_during(filled_modal.save)


# SH-16
def test_description_keeps_at_most_1000_characters(create_modal: TicketModal) -> None:
    create_modal.paste_description("x" * (DESCRIPTION_LIMIT + 1))

    assert len(create_modal.description()) == DESCRIPTION_LIMIT


# SH-17
def test_four_characters_ask_for_suggestions_with_the_typed_text(
    desk_feed: DeskFeed, create_modal: TicketModal
) -> None:
    desk_feed.serve_suggestions((SUGGESTION,))

    asked = desk_feed.suggestions.capture_one(lambda: create_modal.type_description(SUGGESTION_KEYWORD))

    assert asked.query_value("keyword") == SUGGESTION_KEYWORD


# SH-17
def test_suggestions_open_their_answer_in_a_new_tab(desk_feed: DeskFeed, create_modal: TicketModal) -> None:
    desk_feed.serve_suggestions((SUGGESTION,))

    create_modal.type_description(SUGGESTION_KEYWORD)

    create_modal.expect_suggestion(SUGGESTION.question, SUGGESTION.url)


# SH-17
def test_suggestions_mark_the_typed_word(desk_feed: DeskFeed, create_modal: TicketModal) -> None:
    desk_feed.serve_suggestions((SUGGESTION,))

    create_modal.type_description(SUGGESTION_KEYWORD)

    create_modal.expect_marked_word(SUGGESTION_KEYWORD)


# SH-18
def test_three_characters_ask_for_no_suggestions(desk_feed: DeskFeed, create_modal: TicketModal) -> None:
    desk_feed.serve_suggestions((SUGGESTION,))

    desk_feed.suggestions.expect_none_during(lambda: create_modal.type_description(TOO_SHORT_FOR_SUGGESTIONS))
    create_modal.expect_no_suggestions()


# SH-19 (code risk D2: the highlight builds a RegExp from the raw text)
def test_regex_characters_do_not_break_the_suggestions(
    guarded_page: Page, desk_feed: DeskFeed, create_modal: TicketModal
) -> None:
    desk_feed.serve_suggestions((SUGGESTION,))
    errors: list[str] = []
    guarded_page.on("console", lambda message: _keep_errors(message, errors))

    desk_feed.suggestions.capture_one(lambda: create_modal.type_description(REGEX_DESCRIPTION))

    create_modal.expect_suggestion(SUGGESTION.question, SUGGESTION.url)
    assert not [error for error in errors if "regular expression" in error.lower()]


# SH-25
def test_close_discards_the_new_ticket(filled_modal: TicketModal) -> None:
    filled_modal.close()

    filled_modal.expect_closed()


# SH-25
def test_close_does_not_reload_the_list(desk_feed: DeskFeed, filled_modal: TicketModal) -> None:
    desk_feed.ticket_list.expect_none_during(filled_modal.close)


# SH-25
def test_escape_discards_the_new_ticket(filled_modal: TicketModal) -> None:
    filled_modal.close_with_escape()

    filled_modal.expect_closed()


# SH-36
def test_save_while_offline_warns_and_sends_nothing(
    guarded_page: Page, ticket_list: SupportTicketList, save_stub: StubbedEndpoint
) -> None:
    guarded_page.context.set_offline(True)
    modal = ticket_list.start_ticket()
    modal.expect_open()

    save_stub.expect_none_during(modal.save)

    Toasts(guarded_page).expect_any_saying(INTERNET_REQUIRED)


# SH-36
def test_list_opened_while_offline_warns(guarded_page: Page, ticket_list: SupportTicketList) -> None:
    ticket_list.go_home()
    guarded_page.context.set_offline(True)
    drawer = HelpDrawer(guarded_page)
    drawer.open()

    drawer.raise_ticket()

    Toasts(guarded_page).expect_any_saying(INTERNET_REQUIRED)


def _keep_errors(message: ConsoleMessage, errors: list[str]) -> None:
    if message.type == "error":
        errors.append(message.text)
