"""J17: ledgers outside the party groups, and their link to account groups (specs/ledger-master-crud.md)."""

import re

import pytest

from pages.masters.ledger_form import LedgerForm
from pages.masters.master_list import AccountGroupList
from pages.masters.master_records import MasterRecords
from pages.masters.master_toasts import MasterToasts
from test_data.masters import INDIRECT_EXPENSES

pytestmark = [pytest.mark.p1, pytest.mark.journey("ledger-master-crud")]

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
LEDGER_AVAILABLE = re.compile(r"Ledger Available", re.IGNORECASE)


def test_expense_ledger_form_asks_general_fields_only(ledger_form: LedgerForm) -> None:
    ledger_form.open_new()
    ledger_form.choose_group(INDIRECT_EXPENSES)
    ledger_form.expect_general_fields_only()


def test_ledger_in_user_group_keeps_its_group(records: MasterRecords, ledger_form: LedgerForm) -> None:
    group = records.saved_group()
    ledger = records.saved_general_ledger(group.name)
    ledger_form.open_existing(ledger.name)
    ledger_form.expect_group(group.name)


def test_ledger_moved_to_another_group_keeps_new_group(
    records: MasterRecords, ledger_form: LedgerForm
) -> None:
    first_group, second_group = records.saved_group(), records.saved_group()
    ledger = records.saved_general_ledger(first_group.name)
    ledger_form.open_existing(ledger.name)
    ledger_form.choose_group(second_group.name)
    ledger_form.update()
    ledger_form.expect_updated()
    ledger_form.open_existing(ledger.name)
    ledger_form.expect_group(second_group.name)


def test_group_with_a_ledger_cannot_be_deleted(records: MasterRecords, group_list: AccountGroupList) -> None:
    group = records.saved_group()
    records.saved_general_ledger(group.name)
    group_list.open()
    group_list.ask_to_delete(group.name)
    group_list.confirm_delete()
    MasterToasts(group_list.page).expect_error_saying(LEDGER_AVAILABLE)
    group_list.expect_listed(group.name)
