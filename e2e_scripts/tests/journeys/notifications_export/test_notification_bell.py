"""J21 header bell (specs/notifications-export.md, NE-01..NE-13).

The global Marg feed cannot be seeded (it was empty on the QA tenant), so every test except NE-01 feeds
the bell its own list through `bell_showing` (a route stub of NotificationList, scenario pack Q2).
"""

import re
from collections.abc import Callable
from dataclasses import replace

import pytest
from playwright.sync_api import Page, expect

from pages.notifications_export.notification_bell import NotificationBell
from pages.notifications_export.notification_feed import LINK_TARGET, FeedItem, FeedType, feed_items

pytestmark = [pytest.mark.p2, pytest.mark.journey("notifications-export")]

BellShowing = Callable[[list[FeedItem]], NotificationBell]
NOTICE = "QA-feed notice"
ANNOUNCEMENT = "QA-feed announcement"
DROPDOWN_LIMIT = 4
SPEC_TEXT_LIMIT = 150
SPEC_ELLIPSIS = "…."
FEED_MONTH_PARAMETER = "?M=202610&t=#MBM"
TOGGLE_QUESTION = re.compile(r"Are you sure you want to (enable|disable) notification\?")
SCRIPT_IN_MARKUP = '<img src="qa-missing.png" onerror="window.qaInjected = true">'


def _notices(count: int) -> list[FeedItem]:
    return feed_items(NOTICE, FeedType.NOTIFICATION, count)


def _announcements(count: int) -> list[FeedItem]:
    return feed_items(ANNOUNCEMENT, FeedType.ANNOUNCEMENT, count)


def _read(item: FeedItem) -> FeedItem:
    return replace(item, isRead=1)


def test_header_shows_the_notification_bell(journey_page: Page) -> None:
    """NE-01: the bell link titled "Notifications" with the label "Notification" (live feed)."""
    NotificationBell(journey_page).expect_shown()


def test_bell_opens_notification_and_announcement_tabs(bell_showing: BellShowing) -> None:
    """NE-02: two tabs from NotificationTypeData (type 3 left out), each with its unread badge."""
    bell = bell_showing(_notices(2) + _announcements(1))

    bell.open()

    bell.expect_tab_badges(notifications=2, announcements=1)


def test_badge_counts_the_unread_notifications(bell_showing: BellShowing) -> None:
    """NE-03: badge = unread items of type 0/1; read items and announcements do not count."""
    first, second, third, fourth = _notices(4)
    bell = bell_showing([first, second, third, _read(fourth), *_announcements(2)])

    bell.expect_badge(3)


def test_dropdown_lists_four_notifications_when_there_are_more(bell_showing: BellShowing) -> None:
    """NE-04: six notifications, four listed (code slices to 4; the KB's scrolling rest is K2)."""
    bell = bell_showing(_notices(6))

    bell.open()

    expect(bell.listed_items(NOTICE)).to_have_count(DROPDOWN_LIMIT)


def test_read_notification_is_marked_read(bell_showing: BellShowing) -> None:
    """NE-05: a read item carries the class "read" (white background), an unread one does not."""
    unread, read = _notices(2)
    bell = bell_showing([unread, _read(read)])

    bell.open()

    expect(bell.item(read.name)).to_have_class(re.compile(r"\bread\b"))
    expect(bell.item(unread.name)).not_to_have_class(re.compile(r"\bread\b"))


def test_long_notification_text_is_cut_at_150_characters(bell_showing: BellShowing) -> None:
    """NE-06: the spec (KB MB_Notification.docx) cuts the text at 150 characters and adds "….".
    The code renders the whole description, so this is expected to fail (D3)."""
    long_text = "Q" * (SPEC_TEXT_LIMIT + 50)
    (notice,) = _notices(1)
    bell = bell_showing([replace(notice, description=long_text)])

    bell.open()

    expect(bell.item(notice.name)).to_contain_text(long_text[:SPEC_TEXT_LIMIT] + SPEC_ELLIPSIS)


def test_opening_the_bell_keeps_the_count(bell_showing: BellShowing) -> None:
    """NE-07: opening and closing the bell does not clear the badge."""
    bell = bell_showing(_notices(3))

    bell.open()
    bell.close()

    bell.expect_badge(3)


def test_clicking_an_unread_notification_lowers_the_count(bell_showing: BellShowing) -> None:
    """NE-08: the spec says the count drops by one when a message is clicked. The server's
    readNotification is a no-op returning Data=null (K1), so this is expected to fail (D1)."""
    first, *others = _notices(3)
    bell = bell_showing([first, *others])
    bell.open()

    bell.item(first.name).click()

    bell.expect_badge(2)


def test_link_notification_opens_its_page_for_the_month(bell_showing: BellShowing) -> None:
    """NE-09: an item with isLink 1 opens descURL?M=<yyyymm>&t=#MBM in a new tab."""
    (notice,) = _notices(1)
    bell = bell_showing([replace(notice, isLink=1, descURL=LINK_TARGET)])
    bell.open()

    new_tab = bell.open_link_item(notice.name)

    expect(new_tab).to_have_url(LINK_TARGET + FEED_MONTH_PARAMETER)


def test_empty_feed_shows_no_badge_and_all_caught_up(bell_showing: BellShowing) -> None:
    """NE-10: no items, no badge; the dropdown says "No notifications yet" / "You're all caught up!"."""
    bell = bell_showing([])
    bell.expect_no_badge()

    bell.open()

    bell.expect_empty_state()


def test_announcements_tab_lists_the_announcements(bell_showing: BellShowing) -> None:
    """NE-11: type 2 items are listed under Announcement, not under Notification."""
    bell = bell_showing(_notices(1) + _announcements(2))
    bell.open()

    bell.show_announcements()

    expect(bell.listed_items(ANNOUNCEMENT)).to_have_count(2)


def test_view_all_announcements_is_offered_above_four(bell_showing: BellShowing) -> None:
    """NE-11: "View All Announcements" appears when there are more than four announcements."""
    bell = bell_showing(_notices(1) + _announcements(DROPDOWN_LIMIT + 1))
    bell.open()

    bell.show_announcements()

    expect(bell.view_all_announcements()).to_be_visible()


def test_announcements_tab_without_announcements_says_so(bell_showing: BellShowing) -> None:
    """NE-11: no type 2 items gives "No announcement!"."""
    bell = bell_showing(_notices(1))
    bell.open()

    bell.show_announcements()

    bell.expect_no_announcement_message()


def test_declining_the_desktop_notification_question_keeps_the_setting(bell_showing: BellShowing) -> None:
    """NE-12: the toggle asks first; No leaves the label as it was and saves nothing (the guard
    fails the test if Profiler/Save is called)."""
    bell = bell_showing(_notices(1))
    bell.open()
    label_before = bell.desktop_notification_label()

    bell.toggle_desktop_notification()
    bell.expect_toggle_question(TOGGLE_QUESTION)
    bell.decline_toggle()

    assert bell.desktop_notification_label() == label_before


def test_markup_in_a_notification_does_not_run_script(bell_showing: BellShowing) -> None:
    """NE-13: the description is rendered as HTML; an onerror handler in it must not run."""
    (notice,) = _notices(1)
    bell = bell_showing([replace(notice, description=SCRIPT_IN_MARKUP)])

    bell.open()

    assert not bell.injected_script_ran()
