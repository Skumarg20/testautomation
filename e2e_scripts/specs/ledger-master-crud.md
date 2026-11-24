# Plan: J17 account group / non-party ledger CRUD (ledger-master-crud)

Scenario pack: `scenarios/ledger-master-crud.md`. Tests: `tests/journeys/masters/test_account_group.py`, `tests/journeys/masters/test_general_ledger.py`.
Status: DRAFT for QA/BA review. Observed live on 2026-10-08 (QA tenant, `garments` login).

## Preconditions
- `page_as("garments")`, dashboard open.
- Picked, never created or changed: predefined groups `Indirect Expenses` (parent of test groups), `Sundry Debtors` (name clash), `Suspense Accounts` (delete refusal; the app refuses before asking to confirm, so nothing is clicked further).
- Each test makes its own groups `QA-<run_id>-Grp-<n>` under Indirect Expenses and ledgers `QA-<run_id>-Exp-<n>`. The `records` fixture deletes ledgers first, then groups.

## Locators (verified live)
| Thing | Locator |
|---|---|
| Menu | Master > Accounts Master > Group (`MastersMenu.open_account_group_list`) |
| Account Group List | heading "Account Group List"; "Create/F2"; searchbox "Search"; "- Collapse All"; tree grid, name column `col-id="name"`; row buttons "Edit/F3", "Delete" |
| Search | shows the match with the chain of groups above it, e.g. Revenue Account > Expenditure Account > Indirect Expenses > the group |
| Create form | heading "Create Account Group" (Modify: "Modify Account Group"); `#txtGroupName`, `#drpAccountGroup` (Under Group typeahead, 44 groups), `#drpProhibited` (No/Yes); `#btn-Save`, `#btn-Update`, `#btn-Clear`, `#btn-Close` |
| Non-party ledger form | choosing a non-party group (e.g. Indirect Expenses) replaces the party block: only Party Name, Account Group, "GST Applicable" (Applicable / Not Applicable / Non GST, default Not Applicable) and Opening Balance remain; no station or mobile |

## Plans (one test each)
| Plan | Scenario | Steps | Expected (seen live) | Test |
|---|---|---|---|---|
| AG-A | AG-01, AG-02 | Create group under Indirect Expenses; search the list | Toast "Record Saved Successfully."; rows Revenue Account, Expenditure Account, Indirect Expenses, group | `test_new_group_is_listed_under_its_parent` |
| AG-B | AG-05 | Name only, Save | No message; form stays on "Create Account Group"; not listed | `test_group_without_parent_is_not_saved` |
| AG-C | AG-06 | Same name again | Warning "Account Group Name Already Exists !" | `test_duplicate_group_name_is_refused` |
| AG-D | AG-07 | Same name in lower case | Same warning (case-blind) | `test_duplicate_group_check_ignores_letter_case` |
| AG-E | AG-08 | Name "Sundry Debtors" | Same warning | `test_predefined_group_name_cannot_be_reused` |
| AG-F | AG-03 | Edit/F3, new name, Update | Toast "Record Updated Successfully."; listed under the new name | `test_renamed_group_is_listed_under_new_name` |
| AG-G | AG-09 | Delete on "Suspense Accounts" | Warning "Pre-Defined Account Group Can't Be Deleted!" with no confirmation | `test_predefined_group_cannot_be_deleted` |
| AG-H | AG-11 | Delete own empty group, Yes | Toast "Record Deleted Successfully."; not listed | `test_empty_group_is_deleted` |
| AG-I | AG-10 | Group with a ledger: Delete, Yes | Confirmation is asked first, then error toast "Ledger Available!"; group still listed | `test_group_with_a_ledger_cannot_be_deleted` |
| GL-A | GL-02 | Ledger F2, Account Group = Indirect Expenses | "GST Applicable" shown; station and mobile hidden | `test_expense_ledger_form_asks_general_fields_only` |
| GL-B | GL-01 | Ledger (name + own group), Save; reopen | Saved with name and group only; group kept | `test_ledger_in_user_group_keeps_its_group` |
| GL-C | GL-03, GL-07 | Move ledger to a second own group, Update; reopen | Toast "Record Updated Successfully."; new group shown | `test_ledger_moved_to_another_group_keeps_new_group` |

## NEEDS DECISION
1. AG-04/AG-05: Save with an empty name or no Under Group gives no message at all (only the field turns `ng-invalid`). Is a silent refusal acceptable? AG-B asserts only that nothing is saved.
2. AG-I: the app asks "Are you sure...?" before it checks for ledgers, then refuses. Should it refuse before asking (as it does for predefined groups)?
3. AG-D: duplicate checks ignore case; confirm this is the intended rule (code compares `name = @name`; collation decides).
4. AG-12 Prohibited, AG-13 name limits, AG-14 rename with ledgers, AG-15 API, AG-16 tenancy, GL-05 delete with transactions: not covered (tenant-wide side effects, no API contract, no second company).
