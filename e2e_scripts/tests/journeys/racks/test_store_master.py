"""J28: stores (warehouses) in Master > Inventory Master > Store (specs/rack-warehouse-management.md)."""

import re

import pytest

from pages.accounting.toasts import Toasts
from pages.racks.rack_records import RackRecords
from pages.racks.store_master import StoreForm, StoreList
from test_data.racks import MAIN_STORE

pytestmark = [pytest.mark.p2, pytest.mark.journey("rack-warehouse-management")]

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS. Seen live 2026-10-09.
ALREADY_EXISTS = re.compile(r"Store Name Is Already Exists", re.IGNORECASE)
PREDEFINED_NOT_DELETABLE = re.compile(r"Predefined Store Cannot Be Deleted", re.IGNORECASE)
RACKS_IN_STORE = re.compile(r"Rack Are Available For This Store", re.IGNORECASE)


def test_new_store_is_listed(records: RackRecords, store_list: StoreList) -> None:
    store = records.saved_store()
    store_list.open()
    store_list.expect_listed(store.name)


def test_store_without_name_is_not_saved(
    records: RackRecords, store_form: StoreForm, store_list: StoreList
) -> None:
    store = records.new_store()
    store_form.open_new()
    store_form.enter_code_only(store)
    store_form.save()
    store_form.expect_still_open()
    store_list.open()
    store_list.expect_not_listed(store.name)


def test_duplicate_store_name_is_refused(records: RackRecords, store_form: StoreForm) -> None:
    store = records.saved_store()
    twin = records.new_store().renamed(store.name)
    store_form.open_new()
    store_form.enter(twin)
    store_form.save()
    Toasts(store_form.page).expect_any_saying(ALREADY_EXISTS)
    store_form.expect_still_open()


def test_renamed_store_is_listed_under_new_name(
    records: RackRecords, store_form: StoreForm, store_list: StoreList
) -> None:
    store = records.saved_store()
    new_name = f"{store.name}-Renamed"
    records.own_store_name(new_name)
    store_form.open_existing(store.name)
    store_form.enter_name(new_name)
    store_form.update()
    store_form.expect_updated()
    store_list.open()
    store_list.expect_listed(new_name)


def test_unused_store_is_deleted(records: RackRecords, store_list: StoreList) -> None:
    store = records.saved_store()
    store_list.open()
    store_list.delete(store.name)
    store_list.expect_not_listed(store.name)


def test_main_store_cannot_be_deleted(store_list: StoreList) -> None:
    store_list.open()
    store_list.ask_to_delete(MAIN_STORE)
    Toasts(store_list.page).expect_any_saying(PREDEFINED_NOT_DELETABLE)


def test_store_with_a_rack_cannot_be_deleted(records: RackRecords, store_list: StoreList) -> None:
    store = records.saved_store()
    records.saved_rack(store.name)
    store_list.open()
    store_list.try_to_delete(store.name)
    Toasts(store_list.page).expect_any_saying(RACKS_IN_STORE)
    store_list.open()
    store_list.expect_listed(store.name)
