"""The list screens of Route, Area and Station: open, search, edit, delete (J25)."""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.masters.master_list import LIST_TIMEOUT_MS, MasterList
from pages.other_masters.other_masters_menu import OtherMastersMenu

# Opened by URL: the Route page has no sidebar, so a menu walk cannot start from it.
ROUTE_PATH = "/route"
AREA_PATH = "/mstr/area"
STATION_PATH = "/mstr/station"
EMPTY_LIST_HEADING = re.compile(r"^No .+ Created Yet$")
EMPTY_LOOKUP_MS = 2_000
STALE_LIST_MS = 10_000


class OtherMasterList(MasterList):
    """A list with a level-1 heading; it shows "No ... Created Yet" and no search box when empty."""

    HEADING: str | re.Pattern[str] = ""

    def open(self) -> None:
        raise NotImplementedError

    def is_listed(self, name: str) -> bool:
        if appears_within(self._empty_state, EMPTY_LOOKUP_MS):
            return False
        return super().is_listed(name)

    def expect_not_listed(self, name: str) -> None:
        if appears_within(self._empty_state, EMPTY_LOOKUP_MS):
            return
        super().expect_not_listed(name)

    def ask_to_delete(self, name: str) -> None:
        """The first row only: an area name may repeat once per route."""
        self.search(name)
        self._row(name).first.get_by_role("button", name="Delete").click()

    def open_create(self) -> None:
        self.page.get_by_role("button", name="Create/F2").click()

    def _wait_until_loaded(self) -> None:
        expect(self.page.get_by_role("heading", name=self.HEADING, level=1)).to_be_visible(
            timeout=LIST_TIMEOUT_MS
        )
        rows_or_empty = self.page.get_by_role("gridcell").first.or_(self._empty_state)
        expect(rows_or_empty.first).to_be_visible(timeout=LIST_TIMEOUT_MS)

    @property
    def _empty_state(self) -> Locator:
        return self.page.get_by_role("heading", name=EMPTY_LIST_HEADING, level=2)


class RouteList(OtherMasterList):
    """Opened by URL: the garments company has no Route entry in the sidebar (spec NEEDS DECISION N1)."""

    HEADING = "Route List"

    def open(self) -> None:
        self.goto(ROUTE_PATH, LIST_TIMEOUT_MS)
        self._wait_until_loaded()


class AreaList(OtherMasterList):
    HEADING = "Area List"

    def open(self) -> None:
        self.goto(AREA_PATH, LIST_TIMEOUT_MS)
        self._wait_until_loaded()

    def open_from_menu(self) -> None:
        OtherMastersMenu(self.page).open_area_list()
        self._wait_until_loaded()

    def expect_route_beside(self, area: str, route: str) -> None:
        """Reopens the list once: right after a route rename the server can still send the old name."""
        self.search(area)
        route_cell = self._row(area).get_by_role("gridcell", name=route, exact=True)
        if not appears_within(route_cell, STALE_LIST_MS):
            self.open()
            self.search(area)
        expect(route_cell).to_be_visible(timeout=LIST_TIMEOUT_MS)


class StationList(OtherMasterList):
    HEADING = re.compile(r"^Station")

    def open(self) -> None:
        self.goto(STATION_PATH, LIST_TIMEOUT_MS)
        self._wait_until_loaded()

    def open_from_menu(self) -> None:
        OtherMastersMenu(self.page).open_station_list()
        self._wait_until_loaded()
