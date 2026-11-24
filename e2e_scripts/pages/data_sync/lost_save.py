"""A bill save the server receives but whose answer never reaches the browser (J35 DS-08).

`DroppedSaveAnswer` lets the save request through to the server (`route.fetch`), then fails it in the browser
as a dropped connection: the server may have saved the bill, the app only sees status 0
(`MrgHttpService.service.ts:467-479`, then `/error`). `SaleBillCount` counts the list rows that carry one bill
number, to tell "one bill or none" from a duplicate. Both are on the pharma company of the stored bill case.
The expected server behaviour (idempotency) is UNVERIFIED in every source (pack DS-08).
"""

from playwright.sync_api import Page, Route

from pages.data_sync.offline_bill import SAVE_ENDPOINT
from pages.sale.documents.bill import SaleBillDocument


class DroppedSaveAnswer:
    def __init__(self, page: Page) -> None:
        self._page = page
        self._reached_server: list[int] = []

    def install(self) -> None:
        self._page.route(SAVE_ENDPOINT, self._forward_then_drop)

    def remove(self) -> None:
        self._page.unroute(SAVE_ENDPOINT, self._forward_then_drop)

    @property
    def server_statuses(self) -> tuple[int, ...]:
        """The HTTP status the server gave each save it received (the browser never saw them)."""
        return tuple(self._reached_server)

    def _forward_then_drop(self, route: Route) -> None:
        answer = route.fetch()
        self._reached_server.append(answer.status)
        route.abort("internetdisconnected")


class SaleBillCount:
    def __init__(self, page: Page) -> None:
        self._bill = SaleBillDocument(page)
        self._page = page

    def bills_numbered(self, number: str) -> int:
        screen = self._bill.screen
        screen.open_menu(self._bill.menu)
        screen.filter_list_this_week()
        screen.search_list(number)
        rows = self._page.get_by_role("row").filter(has=self._page.get_by_text(number, exact=True))
        return rows.count()
