"""J25: routes at /route (specs/route-station-area-masters.md, RT-01 to RT-07)."""

import re

import pytest

from pages.masters.master_toasts import MasterToasts
from pages.other_masters.master_forms import RouteForm
from pages.other_masters.master_lists import AreaList, RouteList
from pages.other_masters.other_master_records import OtherMasterRecords

pytestmark = [pytest.mark.p2, pytest.mark.journey("route-station-area-masters")]

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
ALREADY_EXISTS = re.compile(r"Route Already Exists!", re.IGNORECASE)
# Seen live as "AreaArea Available For This Route." (spec D2); the doubled word is not part of the rule.
AREA_STILL_ON_ROUTE = re.compile(r"Area Available For This Route", re.IGNORECASE)
# Seen live both as the inline note "Route name required !" and as the tooltip "Route is required!".
NAME_REQUIRED = re.compile(r"Route (name|is) required", re.IGNORECASE)


def test_new_route_is_listed(records: OtherMasterRecords, route_list: RouteList) -> None:
    route = records.saved_route()
    route_list.open()
    route_list.expect_listed(route)


def test_route_without_name_is_not_saved(route_form: RouteForm) -> None:
    route_form.open_new()
    route_form.save()
    route_form.expect_still_open_saying(NAME_REQUIRED)


def test_duplicate_route_name_is_refused(records: OtherMasterRecords, route_form: RouteForm) -> None:
    route = records.saved_route()
    route_form.open_new()
    route_form.enter_name(route)
    route_form.save()
    route_form.expect_refused_with(ALREADY_EXISTS)


def test_duplicate_route_check_ignores_letter_case(
    records: OtherMasterRecords, route_form: RouteForm
) -> None:
    route = records.saved_route()
    lower_case_twin = records.own_route_name(route.lower())
    route_form.open_new()
    route_form.enter_name(lower_case_twin)
    route_form.save()
    route_form.expect_refused_with(ALREADY_EXISTS)


def test_renamed_route_is_listed_under_new_name(
    records: OtherMasterRecords, route_form: RouteForm, route_list: RouteList
) -> None:
    route = records.saved_route()
    new_name = records.own_route_name(f"{route}R")
    route_form.open_existing(route)
    route_form.enter_name(new_name)
    route_form.update()
    route_form.expect_updated()
    route_list.expect_listed(new_name)
    route_list.expect_not_listed(route)


def test_route_with_an_area_cannot_be_deleted(records: OtherMasterRecords, route_list: RouteList) -> None:
    area = records.saved_area()
    route_list.open()
    route_list.ask_to_delete(area.route)
    route_list.confirm_delete()
    MasterToasts(route_list.page).expect_error_saying(AREA_STILL_ON_ROUTE)
    route_list.expect_listed(area.route)


def test_unused_route_is_deleted(records: OtherMasterRecords, route_list: RouteList) -> None:
    route = records.saved_route()
    route_list.open()
    route_list.delete(route)
    route_list.expect_not_listed(route)


def test_renamed_route_shows_on_its_area(
    records: OtherMasterRecords, route_form: RouteForm, area_list: AreaList
) -> None:
    area = records.saved_area()
    new_route_name = records.own_route_name(f"{area.route}R")
    route_form.open_existing(area.route)
    route_form.enter_name(new_route_name)
    route_form.update()
    route_form.expect_updated()
    area_list.open()
    area_list.expect_route_beside(area.name, new_route_name)
