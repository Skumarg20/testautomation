"""A stand-in for `GET notification/NotificationList`, the global Marg feed behind the header bell.

The real feed is Marg-wide content that a test cannot seed (it was empty on the QA tenant on 2026-10-12),
so the bell tests serve their own list. The item shape and the envelope are the ones the live API
returned for `StaticData/NotificationTypeData` and `NotificationList` (probe of 2026-10-12) and the
fields `homelayout.component.ts` reads (`type`, `isRead`, `isLink`, `descURL`, `month`, `lastupdatedon`).
"""

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import IntEnum

from playwright.sync_api import Page, Route

from pages.notifications_export.json_route import fulfil_with_data

NOTIFICATION_LIST = re.compile(r"notification/NotificationList", re.IGNORECASE)
LIST_TIMEOUT_MS = 60_000
FEED_MONTH = 10
FEED_DATE = "10-10-2026"
FIRST_LINK_ID = 900_000
LINK_TARGET = "https://qa-feed.invalid/updates"
LINK_TARGET_PAGE = "<html><body>QA link target</body></html>"


class FeedType(IntEnum):
    NOTIFICATION = 1
    ANNOUNCEMENT = 2


@dataclass(frozen=True)
class FeedItem:
    linkid: int
    name: str
    description: str
    type: int
    isRead: int  # noqa: N815 - the API's field name
    isLink: int = 0  # noqa: N815 - the API's field name
    descURL: str = ""  # noqa: N815 - the API's field name
    month: int = FEED_MONTH
    lastupdatedon: str = FEED_DATE


def feed_items(prefix: str, feed_type: FeedType, count: int) -> list[FeedItem]:
    """`count` unread items of one type, named "<prefix> 1", "<prefix> 2", ..."""
    return [
        FeedItem(FIRST_LINK_ID + number, f"{prefix} {number}", f"Text of {prefix} {number}", feed_type, 0)
        for number in range(1, count + 1)
    ]


class NotificationFeed:
    def __init__(self, page: Page) -> None:
        self._page = page

    def serve(self, items: list[FeedItem]) -> None:
        """Answers every NotificationList call with `items`.
        Relies on the suite-wide service-worker block (root conftest)."""
        data = [asdict(item) for item in items]
        self._page.route(NOTIFICATION_LIST, lambda route: fulfil_with_data(route, data))

    def live_items_while(self, load: Callable[[], None]) -> list[object]:
        """The items the real feed answered while `load` ran (it must load the dashboard header)."""
        with self._page.expect_response(NOTIFICATION_LIST, timeout=LIST_TIMEOUT_MS) as response:
            load()
        data: list[object] = response.value.json().get("Data") or []
        return data

    def serve_link_target(self) -> None:
        """Answers LINK_TARGET (a reserved, unreachable host) in any tab, so a link item opens offline."""
        self._page.context.route(f"{LINK_TARGET}**", _fulfil_link_target)


def _fulfil_link_target(route: Route) -> None:
    route.fulfill(status=200, content_type="text/html", body=LINK_TARGET_PAGE)
