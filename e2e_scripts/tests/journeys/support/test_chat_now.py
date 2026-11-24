"""J41 Help drawer "Chat Now" (SH-39). Chat Now opens Zoho SalesIQ, a third-party chat with real agents, so
Zoho is never reached: the widget script is answered by a recording stand-in (`pages/support/zoho_widget.py`)
or aborted, and each test proves which before it clicks."""

import pytest
from playwright.sync_api import Page

from pages.support.help_drawer import HelpDrawer
from pages.support.zoho_widget import ZohoWidget

pytestmark = [pytest.mark.p3, pytest.mark.journey("support-helpdesk")]

FLOAT_WINDOW_SHOWN = "show"
WIDGET_MISSING_WARNING = "Zoho SalesIQ not loaded yet"
WARNING_TIMEOUT_MS = 5_000


# SH-39
def test_chat_now_shows_the_zoho_float_window(
    chat_drawer_with_stand_in: HelpDrawer, zoho_stand_in: ZohoWidget
) -> None:
    chat_drawer_with_stand_in.chat_now()

    assert zoho_stand_in.float_window_state() == FLOAT_WINDOW_SHOWN


# SH-39
def test_chat_now_closes_the_drawer(chat_drawer_with_stand_in: HelpDrawer) -> None:
    chat_drawer_with_stand_in.chat_now()

    chat_drawer_with_stand_in.expect_closed()


# SH-39 (D13: index.html always defines `$zoho.salesiq`, so without the widget `floatwindow` is undefined and
# the click throws instead of warning; this test keeps the pack's expectation)
def test_chat_now_without_the_widget_only_warns(
    guarded_page: Page, chat_drawer_without_widget: HelpDrawer
) -> None:
    with guarded_page.expect_console_message(
        lambda message: message.type == "warning" and WIDGET_MISSING_WARNING in message.text,
        timeout=WARNING_TIMEOUT_MS,
    ):
        chat_drawer_without_widget.chat_now()


# SH-39
def test_chat_now_without_the_widget_keeps_the_drawer_open(chat_drawer_without_widget: HelpDrawer) -> None:
    chat_drawer_without_widget.chat_now()

    chat_drawer_without_widget.expect_open()
