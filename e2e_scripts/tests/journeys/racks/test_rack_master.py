"""J28: racks in the Rack List (/rack), each under a store (specs/rack-warehouse-management.md)."""

import re

import pytest

from pages.accounting.toasts import Toasts
from pages.racks.rack_master import RackForm, RackList
from pages.racks.rack_records import RackRecords

pytestmark = [pytest.mark.p2, pytest.mark.journey("rack-warehouse-management")]

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS. Seen live 2026-10-09.
ALREADY_EXISTS = re.compile(r"Rack No\. Already Exists", re.IGNORECASE)


def test_new_rack_is_listed_with_its_store(records: RackRecords, rack_list: RackList) -> None:
    store = records.saved_store()
    rack = records.saved_rack(store.name)
    rack_list.open()
    rack_list.expect_rack_in_store(rack)


def test_rack_without_name_is_not_saved(records: RackRecords, rack_form: RackForm) -> None:
    store = records.saved_store()
    rack_form.open_new()
    rack_form.choose_store(store.name)
    rack_form.save()
    rack_form.expect_still_open()


def test_duplicate_rack_in_same_store_is_refused(records: RackRecords, rack_form: RackForm) -> None:
    store = records.saved_store()
    rack = records.saved_rack(store.name)
    rack_form.open_new()
    rack_form.enter(rack)
    rack_form.save()
    Toasts(rack_form.page).expect_any_saying(ALREADY_EXISTS)
    rack_form.expect_still_open()


def test_same_rack_name_is_allowed_in_another_store(records: RackRecords, rack_list: RackList) -> None:
    first_store, second_store = records.saved_store(), records.saved_store()
    rack = records.saved_rack(first_store.name)
    twin = rack.moved(rack.name, second_store.name)
    records.save_rack(twin)
    rack_list.open()
    rack_list.expect_rack_in_store(twin)


def test_edited_rack_shows_new_name_and_store(
    records: RackRecords, rack_form: RackForm, rack_list: RackList
) -> None:
    first_store, second_store = records.saved_store(), records.saved_store()
    rack = records.saved_rack(first_store.name)
    edited = rack.moved(f"{rack.name}-Moved", second_store.name)
    records.own_rack_name(edited.name)
    rack_form.open_existing(rack.name)
    rack_form.enter(edited)
    rack_form.update()
    rack_form.expect_updated()
    rack_list.open()
    rack_list.expect_rack_in_store(edited)


def test_unused_rack_is_deleted(records: RackRecords, rack_list: RackList) -> None:
    rack = records.saved_rack(records.saved_store().name)
    rack_list.open()
    rack_list.delete(rack.name)
    rack_list.expect_not_listed(rack.name)
