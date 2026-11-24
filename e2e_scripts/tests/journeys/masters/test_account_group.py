"""J17: account groups in Master > Accounts Master > Group (specs/ledger-master-crud.md)."""

import re

import pytest

from pages.masters.account_group_form import AccountGroupForm
from pages.masters.master_list import AccountGroupList
from pages.masters.master_records import MasterRecords
from pages.masters.master_toasts import MasterToasts
from test_data.masters import INDIRECT_EXPENSES, AccountGroupSpec

pytestmark = [pytest.mark.p1, pytest.mark.journey("ledger-master-crud")]

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
ALREADY_EXISTS = re.compile(r"Account Group Name Already Exists", re.IGNORECASE)
PREDEFINED_NOT_DELETABLE = re.compile(r"Pre-Defined Account Group Can't Be Deleted", re.IGNORECASE)
PREDEFINED_GROUP = "Sundry Debtors"
# A predefined group with no ledgers on the QA company; the app refuses before it asks to confirm.
PREDEFINED_GROUP_TO_DELETE = "Suspense Accounts"
# The chain above Indirect Expenses in the group tree, seen live 2026-10-08.
INDIRECT_EXPENSES_CHAIN = ["Revenue Account", "Expenditure Account", INDIRECT_EXPENSES]


def test_new_group_is_listed_under_its_parent(records: MasterRecords, group_list: AccountGroupList) -> None:
    group = records.saved_group()
    group_list.open()
    assert group_list.names_in_view(group.name) == [*INDIRECT_EXPENSES_CHAIN, group.name]


def test_group_without_parent_is_not_saved(
    records: MasterRecords, group_form: AccountGroupForm, group_list: AccountGroupList
) -> None:
    group = records.new_group()
    group_form.open_new()
    group_form.enter_name(group.name)
    group_form.save()
    group_form.expect_still_creating()
    group_list.open()
    group_list.expect_not_listed(group.name)


def test_duplicate_group_name_is_refused(records: MasterRecords, group_form: AccountGroupForm) -> None:
    group = records.saved_group()
    group_form.open_new()
    group_form.enter(group)
    group_form.save()
    MasterToasts(group_form.page).expect_warning_saying(ALREADY_EXISTS)


def test_duplicate_group_check_ignores_letter_case(
    records: MasterRecords, group_form: AccountGroupForm
) -> None:
    group = records.saved_group()
    lower_case_twin = AccountGroupSpec(group.name.lower(), group.parent)
    records.own_group_name(lower_case_twin.name)
    group_form.open_new()
    group_form.enter(lower_case_twin)
    group_form.save()
    MasterToasts(group_form.page).expect_warning_saying(ALREADY_EXISTS)


def test_predefined_group_name_cannot_be_reused(group_form: AccountGroupForm) -> None:
    group_form.open_new()
    group_form.enter(AccountGroupSpec(PREDEFINED_GROUP, INDIRECT_EXPENSES))
    group_form.save()
    MasterToasts(group_form.page).expect_warning_saying(ALREADY_EXISTS)


def test_renamed_group_is_listed_under_new_name(
    records: MasterRecords, group_form: AccountGroupForm, group_list: AccountGroupList
) -> None:
    group = records.saved_group()
    new_name = f"{group.name}-Renamed"
    records.own_group_name(new_name)
    group_form.open_existing(group.name)
    group_form.enter_name(new_name)
    group_form.update()
    group_form.expect_updated()
    group_list.expect_listed(new_name)


def test_predefined_group_cannot_be_deleted(group_list: AccountGroupList) -> None:
    group_list.open()
    group_list.ask_to_delete(PREDEFINED_GROUP_TO_DELETE)
    MasterToasts(group_list.page).expect_warning_saying(PREDEFINED_NOT_DELETABLE)


def test_empty_group_is_deleted(records: MasterRecords, group_list: AccountGroupList) -> None:
    group = records.saved_group()
    group_list.open()
    group_list.delete(group.name)
    group_list.expect_not_listed(group.name)
