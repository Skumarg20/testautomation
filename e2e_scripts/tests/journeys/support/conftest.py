"""Fixtures for J41 support-helpdesk (specs/support-helpdesk.md).

Saving a ticket writes to Marg's live support desk and queues a real WhatsApp and email
(`MargSupportController.cs:229-288`). So every page is armed with the send guard before its first
navigation: it aborts the desk writes and every OTP or message dispatch (`pages/support/desk_endpoints.py`),
and a test fails in teardown if the screen tried one that no stub answered. Tests that press Save, Update,
Delete or send a reply get a stub for that one write and must prove it answered (`capture_one`).

The chemist login's company is shared state, so it is pinned to the garments company.
"""

from collections.abc import Callable, Iterator
from re import Pattern

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.components.send_guard import SendGuard
from pages.components.stubbed_endpoint import StubbedEndpoint
from pages.dashboard_page import DashboardPage
from pages.support.desk_endpoints import DELETE_TICKET, REOPEN_MESSAGE, SAVE_TICKET, SUPPORT_WRITES
from pages.support.desk_feed import DeskFeed, write_accepted
from pages.support.help_drawer import HelpDrawer
from pages.support.ticket_list import SupportTicketList
from pages.support.ticket_modal import TicketModal
from pages.support.zoho_widget import ZohoWidget
from test_data.support import (
    BILL_NOT_SAVING,
    BILLING,
    DESK_TICKETS,
    DESK_TREE,
    PARTNER_REPLY,
    RAISED_TICKET,
    SALE_BILL,
)

SUPPORT_ACCOUNT: Account = "chemist"


@pytest.fixture
def guarded_page(page_as: Callable[[Account], Page]) -> Iterator[Page]:
    """A chemist page, guarded, not yet navigated."""
    page = page_as(SUPPORT_ACCOUNT)
    guard = SendGuard(page, SUPPORT_WRITES)
    guard.arm()
    yield page
    guard.expect_nothing_sent()


@pytest.fixture
def guarded_plain_page(page: Page) -> Iterator[Page]:
    """A page with no session (the plain-browser context), guarded all the same."""
    guard = SendGuard(page, SUPPORT_WRITES)
    guard.arm()
    yield page
    guard.expect_nothing_sent()


@pytest.fixture
def desk_feed(guarded_page: Page) -> DeskFeed:
    """The served desk: invented tickets, dispositions and chat (test_data/support.py)."""
    feed = DeskFeed(guarded_page)
    feed.serve_tickets(DESK_TICKETS)
    feed.serve_dispositions(DESK_TREE)
    feed.serve_chat((PARTNER_REPLY,))
    return feed


@pytest.fixture
def save_stub(guarded_page: Page) -> StubbedEndpoint:
    return _accepting_stub(guarded_page, SAVE_TICKET)


@pytest.fixture
def delete_stub(guarded_page: Page) -> StubbedEndpoint:
    return _accepting_stub(guarded_page, DELETE_TICKET)


@pytest.fixture
def reopen_stub(guarded_page: Page) -> StubbedEndpoint:
    return _accepting_stub(guarded_page, REOPEN_MESSAGE)


@pytest.fixture
def help_drawer(guarded_page: Page) -> HelpDrawer:
    """The dashboard of the garments company with the Help drawer open."""
    _open_dashboard_of_garments(guarded_page)
    drawer = HelpDrawer(guarded_page)
    drawer.open()
    return drawer


@pytest.fixture
def zoho_stand_in(guarded_page: Page) -> ZohoWidget:
    """The Zoho chat widget answered by a recording stand-in; Zoho itself is never reached."""
    widget = ZohoWidget(guarded_page)
    widget.stand_in()
    return widget


@pytest.fixture
def zoho_blocked(guarded_page: Page) -> ZohoWidget:
    """The Zoho chat widget aborted, as when Zoho is unreachable."""
    widget = ZohoWidget(guarded_page)
    widget.block()
    return widget


@pytest.fixture
def chat_drawer_with_stand_in(guarded_page: Page, zoho_stand_in: ZohoWidget) -> HelpDrawer:
    _open_dashboard_of_garments(guarded_page)
    zoho_stand_in.expect_stand_in_loaded()
    drawer = HelpDrawer(guarded_page)
    drawer.open()
    return drawer


@pytest.fixture
def chat_drawer_without_widget(guarded_page: Page, zoho_blocked: ZohoWidget) -> HelpDrawer:
    _open_dashboard_of_garments(guarded_page)
    drawer = HelpDrawer(guarded_page)
    drawer.open()
    return drawer


@pytest.fixture
def second_company(guarded_page: Page) -> Iterator[str]:
    """The chemist login's other company, switched back to the garments company afterwards (the login's
    company is shared state). Skips when the login has no second company."""
    _open_dashboard_of_garments(guarded_page)
    switch = CompanySwitchPage(guarded_page)
    switch.open()
    try:
        switch.expect_organisation_listed(PHARMA_COMPANY)
    except AssertionError:
        pytest.skip(f"SH-37: needs a second company ({PHARMA_COMPANY}) on the chemist login")
    yield PHARMA_COMPANY
    switch.ensure_company(GARMENTS_COMPANY)


@pytest.fixture
def live_ticket_list(guarded_page: Page) -> SupportTicketList:
    """The list on the desk's real reads (the login's own tickets, the real dispositions)."""
    _open_dashboard_of_garments(guarded_page)
    ticket_list = SupportTicketList(guarded_page)
    ticket_list.open()
    return ticket_list


@pytest.fixture
def ticket_list(guarded_page: Page, desk_feed: DeskFeed) -> SupportTicketList:
    """The list on the served desk."""
    _open_dashboard_of_garments(guarded_page)
    served_list = SupportTicketList(guarded_page)
    served_list.open()
    return served_list


@pytest.fixture
def list_awaiting_raised_ticket(desk_feed: DeskFeed, ticket_list: SupportTicketList) -> SupportTicketList:
    """The served list without SH-40's new ticket; the desk serves it from the next reload on."""
    ticket_list.expect_not_listed(RAISED_TICKET.ticket_no)
    desk_feed.serve_tickets((RAISED_TICKET, *DESK_TICKETS))
    return ticket_list


@pytest.fixture
def create_modal(ticket_list: SupportTicketList) -> TicketModal:
    modal = ticket_list.start_ticket()
    modal.expect_open()
    return modal


@pytest.fixture
def filled_modal(create_modal: TicketModal, run_id: str) -> TicketModal:
    """A complete new ticket, not saved: the three served choices and a description named after the run."""
    create_modal.choose_main_disposition(BILLING.name)
    create_modal.choose_sub_disposition(SALE_BILL.name)
    create_modal.choose_problem_type(BILL_NOT_SAVING.name)
    create_modal.write_description(f"QA-{run_id} sale bill does not save")
    return create_modal


def _accepting_stub(page: Page, endpoint: Pattern[str]) -> StubbedEndpoint:
    stub = StubbedEndpoint(page, endpoint)
    stub.answer_with(write_accepted())
    return stub


def _open_dashboard_of_garments(page: Page) -> None:
    dashboard = DashboardPage(page)
    dashboard.open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)
    dashboard.expect_loaded()
