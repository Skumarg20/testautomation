"""Test-owned routes, areas and stations: made through the UI, remembered, and deleted in teardown."""

from functools import partial

from playwright.sync_api import Page

from pages.components.undo import UndoStep, undo_all
from pages.other_masters.master_forms import AreaForm, RouteForm, StationForm
from pages.other_masters.master_lists import AreaList, OtherMasterList, RouteList, StationList
from test_data.other_masters import AreaSpec, OtherMasterDataFactory

# An area name may be saved once per route; a test makes at most two routes with the same area name.
MAX_ROWS_PER_NAME = 2


class OtherMasterRecords:
    """Every name is remembered before the UI is asked to save it, so a half-done save is cleaned too."""

    def __init__(self, page: Page, data: OtherMasterDataFactory) -> None:
        self._page = page
        self._data = data
        self._routes: list[str] = []
        self._areas: list[str] = []
        self._stations: list[str] = []

    def new_route(self) -> str:
        return self.own_route_name(self._data.route())

    def new_station(self) -> str:
        return self.own_station_name(self._data.station())

    def new_area(self, route: str) -> AreaSpec:
        area = self._data.area(route)
        self.own_area_name(area.name)
        return area

    def own_route_name(self, name: str) -> str:
        self._routes.append(name)
        return name

    def own_station_name(self, name: str) -> str:
        self._stations.append(name)
        return name

    def own_area_name(self, name: str) -> str:
        self._areas.append(name)
        return name

    def saved_route(self) -> str:
        route = self.new_route()
        form = RouteForm(self._page)
        form.open_new()
        form.enter_name(route)
        form.save()
        form.expect_saved()
        return route

    def saved_station(self) -> str:
        station = self.new_station()
        form = StationForm(self._page)
        form.open_new()
        form.enter_name(station)
        form.save()
        form.expect_saved()
        return station

    def saved_area(self) -> AreaSpec:
        area = self.new_area(self.saved_route())
        form = AreaForm(self._page)
        form.open_new()
        form.enter(area)
        form.save()
        form.expect_saved()
        return area

    def delete_all(self) -> None:
        """Areas go first: the app refuses to delete a route that still has an area."""
        undo_all(
            [
                *_undo_steps(AreaList(self._page), self._areas),
                *_undo_steps(RouteList(self._page), self._routes),
                *_undo_steps(StationList(self._page), self._stations),
            ]
        )


def _undo_steps(screen: OtherMasterList, names: list[str]) -> list[UndoStep]:
    if not names:
        return []
    deletes: list[UndoStep] = [(name, partial(_delete_rows_named, screen, name)) for name in names]
    return [(f"opening {type(screen).__name__}", screen.open), *deletes]


def _delete_rows_named(screen: OtherMasterList, name: str) -> None:
    for _ in range(MAX_ROWS_PER_NAME):
        if not screen.is_listed(name):
            return
        screen.delete(name)
