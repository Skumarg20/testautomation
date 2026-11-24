"""J25: stations in Master > Other Master > Station (specs/route-station-area-masters.md, ST-01 to ST-08)."""

import re

import pytest
from playwright.sync_api import expect

from pages.masters.master_list import LedgerList
from pages.masters.master_toasts import MasterToasts
from pages.other_masters.master_forms import StationForm
from pages.other_masters.master_lists import StationList
from pages.other_masters.other_master_records import OtherMasterRecords
from test_data.masters import PartyLedgerSpec

pytestmark = [pytest.mark.p2, pytest.mark.journey("route-station-area-masters")]

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
ALREADY_EXISTS = re.compile(r"Station Already Exists!", re.IGNORECASE)
LEDGER_ON_STATION = re.compile(r"Ledger Are Available For This Station", re.IGNORECASE)
# Longer than the 15 characters of the update procedure, inside the form's 25 (spec NEEDS DECISION N2).
LONG_NAME_SUFFIX = "-Long-Nm"


def test_station_list_opens_from_the_master_menu(station_list: StationList) -> None:
    station_list.open_from_menu()


def test_new_station_is_listed(records: OtherMasterRecords, station_list: StationList) -> None:
    station = records.saved_station()
    station_list.open()
    station_list.expect_listed(station)


def test_station_without_name_is_not_saved(station_form: StationForm) -> None:
    station_form.open_new()
    station_form.save()
    station_form.expect_still_open()


def test_duplicate_station_name_is_refused(records: OtherMasterRecords, station_form: StationForm) -> None:
    station = records.saved_station()
    station_form.open_new()
    station_form.enter_name(station)
    station_form.save()
    station_form.expect_refused_with(ALREADY_EXISTS)


def test_duplicate_station_check_ignores_letter_case(
    records: OtherMasterRecords, station_form: StationForm
) -> None:
    station = records.saved_station()
    lower_case_twin = records.own_station_name(station.lower())
    station_form.open_new()
    station_form.enter_name(lower_case_twin)
    station_form.save()
    station_form.expect_refused_with(ALREADY_EXISTS)


def test_station_name_longer_than_fifteen_characters_is_kept_whole(
    records: OtherMasterRecords, station_form: StationForm, station_list: StationList
) -> None:
    long_name = records.own_station_name(f"{records.new_station()}{LONG_NAME_SUFFIX}")
    station_form.open_new()
    station_form.enter_name(long_name)
    station_form.save()
    station_form.expect_saved()
    station_list.open()
    station_list.expect_listed(long_name)


def test_renamed_station_is_listed_under_new_name(
    records: OtherMasterRecords, station_form: StationForm, station_list: StationList
) -> None:
    station = records.saved_station()
    new_name = records.own_station_name(f"{station}R")
    station_form.open_existing(station)
    station_form.enter_name(new_name)
    station_form.update()
    station_form.expect_updated()
    station_list.expect_listed(new_name)
    station_list.expect_not_listed(station)


def test_new_station_is_shown_on_a_customer_ledger(
    customer_at_new_station: PartyLedgerSpec, ledger_list: LedgerList
) -> None:
    customer = customer_at_new_station
    ledger_list.open()
    expect(ledger_list.station_of(customer.name)).to_have_text(customer.station)


def test_renamed_station_is_shown_on_its_ledger(
    records: OtherMasterRecords, customer_at_new_station: PartyLedgerSpec, ledger_list: LedgerList
) -> None:
    customer = customer_at_new_station
    new_name = records.own_station_name(f"{customer.station}R")
    form = StationForm(ledger_list.page)
    form.open_existing(customer.station)
    form.enter_name(new_name)
    form.update()
    form.expect_updated()
    ledger_list.open()
    expect(ledger_list.station_of(customer.name)).to_have_text(new_name)


def test_station_on_a_ledger_cannot_be_deleted(
    customer_at_new_station: PartyLedgerSpec, station_list: StationList
) -> None:
    customer = customer_at_new_station
    station_list.open()
    station_list.ask_to_delete(customer.station)
    station_list.confirm_delete()
    MasterToasts(station_list.page).expect_error_saying(LEDGER_ON_STATION)
    station_list.expect_listed(customer.station)


def test_unused_station_is_deleted(records: OtherMasterRecords, station_list: StationList) -> None:
    station = records.saved_station()
    station_list.open()
    station_list.delete(station)
    station_list.expect_not_listed(station)
