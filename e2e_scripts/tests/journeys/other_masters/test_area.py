"""J25: areas in Master > Other Master > Area (specs/route-station-area-masters.md, AR-01 to AR-06)."""

import re
from dataclasses import replace

import pytest

from pages.other_masters.master_forms import AreaForm
from pages.other_masters.master_lists import AreaList
from pages.other_masters.other_master_records import OtherMasterRecords

pytestmark = [pytest.mark.p2, pytest.mark.journey("route-station-area-masters")]

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
ALREADY_EXISTS = re.compile(r"Area Already Exists!", re.IGNORECASE)
ROUTE_REQUIRED = re.compile(r"Route Name required", re.IGNORECASE)


def test_area_list_opens_from_the_master_menu(area_list: AreaList) -> None:
    area_list.open_from_menu()


def test_new_area_is_listed_with_its_route(records: OtherMasterRecords, area_list: AreaList) -> None:
    area = records.saved_area()
    area_list.open()
    area_list.expect_route_beside(area.name, area.route)


def test_area_without_route_is_not_saved(
    records: OtherMasterRecords, area_form: AreaForm, area_list: AreaList
) -> None:
    area = records.new_area(records.saved_route())
    area_form.open_new()
    area_form.enter_name(area.name)
    area_form.save()
    area_form.expect_still_open_saying(ROUTE_REQUIRED)
    area_form.close_discarding()
    area_list.open()
    area_list.expect_not_listed(area.name)


def test_duplicate_area_name_is_refused(records: OtherMasterRecords, area_form: AreaForm) -> None:
    area = records.saved_area()
    area_form.open_new()
    area_form.enter(area)
    area_form.save()
    area_form.expect_refused_with(ALREADY_EXISTS)


def test_same_area_name_is_allowed_on_another_route(
    records: OtherMasterRecords, area_form: AreaForm, area_list: AreaList
) -> None:
    area = records.saved_area()
    twin_on_other_route = replace(area, route=records.saved_route())
    area_form.open_new()
    area_form.enter(twin_on_other_route)
    area_form.save()
    area_form.expect_saved()
    area_list.open()
    area_list.expect_route_beside(area.name, twin_on_other_route.route)


def test_renamed_area_is_listed_under_new_name(
    records: OtherMasterRecords, area_form: AreaForm, area_list: AreaList
) -> None:
    area = records.saved_area()
    new_name = records.own_area_name(f"{area.name}R")
    area_form.open_existing(area.name)
    area_form.type_new_name(new_name)
    area_form.update()
    area_form.expect_updated()
    area_list.expect_listed(new_name)


def test_area_is_deleted(records: OtherMasterRecords, area_list: AreaList) -> None:
    area = records.saved_area()
    area_list.open()
    area_list.delete(area.name)
    area_list.expect_not_listed(area.name)
