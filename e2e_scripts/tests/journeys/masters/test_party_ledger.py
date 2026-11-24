"""J07: customer and supplier ledgers in Master > Accounts Master > Ledger (specs/masters.md)."""

import re

import pytest
from playwright.sync_api import expect

from pages.masters.ledger_form import LedgerForm
from pages.masters.master_list import LedgerList
from pages.masters.master_records import MasterRecords
from pages.masters.master_toasts import MasterToasts
from test_data.masters import SUNDRY_CREDITORS

pytestmark = [pytest.mark.p1, pytest.mark.journey("masters")]

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
INVALID_NAME = re.compile(r"Invalid LedgerName", re.IGNORECASE)
INVALID_STATION = re.compile(r"Invalid StationLinkID", re.IGNORECASE)
INVALID_MOBILE = re.compile(r"Invalid Mobile1", re.IGNORECASE)
ALREADY_EXISTS = re.compile(r"Ledger Already Exists!", re.IGNORECASE)
NEW_CITY = "Pune"


def test_customer_ledger_is_listed_with_its_station(records: MasterRecords, ledger_list: LedgerList) -> None:
    customer = records.saved_customer()
    ledger_list.open()
    expect(ledger_list.station_of(customer.name)).to_have_text(customer.station)


def test_supplier_ledger_keeps_sundry_creditors_group(
    records: MasterRecords, ledger_form: LedgerForm
) -> None:
    supplier = records.saved_supplier()
    ledger_form.open_existing(supplier.name)
    ledger_form.expect_group(SUNDRY_CREDITORS)


def test_ledger_without_name_is_refused(ledger_form: LedgerForm) -> None:
    ledger_form.open_new()
    ledger_form.save()
    MasterToasts(ledger_form.page).expect_warning_saying(INVALID_NAME)


def test_party_ledger_without_station_is_refused(
    records: MasterRecords, ledger_form: LedgerForm, ledger_list: LedgerList
) -> None:
    customer = records.new_customer()
    ledger_form.open_new()
    ledger_form.enter_party_without_station(customer)
    ledger_form.save()
    MasterToasts(ledger_form.page).expect_warning_saying(INVALID_STATION)
    ledger_list.open()
    ledger_list.expect_not_listed(customer.name)


def test_party_ledger_without_mobile_is_refused(
    records: MasterRecords, ledger_form: LedgerForm, ledger_list: LedgerList
) -> None:
    customer = records.new_customer()
    ledger_form.open_new()
    ledger_form.enter_party(customer)
    ledger_form.clear_mobile()
    ledger_form.save()
    MasterToasts(ledger_form.page).expect_warning_saying(INVALID_MOBILE)
    ledger_list.open()
    ledger_list.expect_not_listed(customer.name)


def test_duplicate_ledger_name_is_refused(records: MasterRecords, ledger_form: LedgerForm) -> None:
    customer = records.saved_customer()
    ledger_form.open_new()
    ledger_form.enter_party(customer)
    ledger_form.save()
    MasterToasts(ledger_form.page).expect_error_saying(ALREADY_EXISTS)


def test_duplicate_ledger_check_ignores_letter_case(records: MasterRecords, ledger_form: LedgerForm) -> None:
    customer = records.saved_customer()
    upper_case_twin = customer.renamed(customer.name.upper())
    records.own_ledger_name(upper_case_twin.name)
    ledger_form.open_new()
    ledger_form.enter_party(upper_case_twin)
    ledger_form.save()
    MasterToasts(ledger_form.page).expect_error_saying(ALREADY_EXISTS)


def test_modified_city_shows_on_reopen(records: MasterRecords, ledger_form: LedgerForm) -> None:
    customer = records.saved_customer()
    ledger_form.open_existing(customer.name)
    ledger_form.enter_city(NEW_CITY)
    ledger_form.update()
    ledger_form.expect_updated()
    ledger_form.open_existing(customer.name)
    ledger_form.expect_city(NEW_CITY)


def test_customer_moved_to_sundry_creditors_keeps_new_group(
    records: MasterRecords, ledger_form: LedgerForm
) -> None:
    customer = records.saved_customer()
    ledger_form.open_existing(customer.name)
    ledger_form.choose_group(SUNDRY_CREDITORS)
    ledger_form.update()
    ledger_form.expect_updated()
    ledger_form.open_existing(customer.name)
    ledger_form.expect_group(SUNDRY_CREDITORS)


def test_ledger_without_transactions_is_deleted(records: MasterRecords, ledger_list: LedgerList) -> None:
    customer = records.saved_customer()
    ledger_list.open()
    ledger_list.delete(customer.name)
    ledger_list.expect_not_listed(customer.name)
