"""J41 Help drawer (SH-01 to SH-04, SH-38; Chat Now SH-39 is in `test_chat_now.py`). Nothing here writes:
Raise ticket only navigates, and the care portal tab is answered by a local stand-in, so no outside site
is browsed."""

import pytest
from playwright.sync_api import Page, Route

from pages.support.help_drawer import SUPPORT_EMAIL, HelpDrawer
from pages.support.ticket_list import SupportTicketList

pytestmark = [pytest.mark.p3, pytest.mark.journey("support-helpdesk")]

CONTACTS = ("011-30969630", "011-66969630", SUPPORT_EMAIL, "+91-8010971097")
CARE_PORTAL = "https://care.margcompusoft.com/marg-book"


def _stand_in_for_the_portal(route: Route) -> None:
    route.fulfill(status=200, content_type="text/html", body="<p>QA stand-in for the care portal</p>")


# SH-01
def test_help_button_slides_in_the_drawer_with_its_banner(help_drawer: HelpDrawer) -> None:
    help_drawer.expect_banner()


# SH-01
def test_help_drawer_shows_its_sections(help_drawer: HelpDrawer) -> None:
    help_drawer.expect_sections()


# SH-02
def test_help_drawer_lists_the_support_contacts(help_drawer: HelpDrawer) -> None:
    help_drawer.expect_contacts(CONTACTS)


# SH-03
def test_copy_button_puts_the_support_email_on_the_clipboard(
    guarded_page: Page, help_drawer: HelpDrawer
) -> None:
    guarded_page.context.grant_permissions(["clipboard-read", "clipboard-write"])

    copied = help_drawer.copy_support_email()

    assert copied == SUPPORT_EMAIL


# SH-03
def test_copy_button_shows_the_copied_tick(guarded_page: Page, help_drawer: HelpDrawer) -> None:
    guarded_page.context.grant_permissions(["clipboard-read", "clipboard-write"])

    help_drawer.copy_support_email()

    help_drawer.expect_copied_tick()


# SH-03
def test_copied_tick_turns_back_into_the_copy_icon(guarded_page: Page, help_drawer: HelpDrawer) -> None:
    guarded_page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    help_drawer.copy_support_email()
    help_drawer.expect_copied_tick()

    help_drawer.expect_copy_icon_back()


# SH-04
def test_raise_ticket_closes_the_drawer(help_drawer: HelpDrawer) -> None:
    help_drawer.raise_ticket()

    help_drawer.expect_closed()


# SH-04
def test_raise_ticket_opens_the_support_ticket_list(guarded_page: Page, help_drawer: HelpDrawer) -> None:
    help_drawer.raise_ticket()

    SupportTicketList(guarded_page).expect_loaded()


# SH-38
def test_visit_portal_opens_the_care_portal_in_a_new_tab(guarded_page: Page, help_drawer: HelpDrawer) -> None:
    guarded_page.context.route(f"{CARE_PORTAL}**", _stand_in_for_the_portal)

    portal = help_drawer.visit_portal()

    assert portal.url.startswith(CARE_PORTAL)
