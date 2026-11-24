# Scenario pack: account group / ledger master CRUD (J17, journey id `ledger-master-crud`)

Status: DRAFT for QA/BA review (2026-10-08). Journey J17 "Account group / ledger master CRUD", priority P1, layers e2e + api. Next step: `test-planner` confirms on the live app into `specs/ledger-master-crud.md`.

Scope: account groups (Master > Accounts Master > Group) and non-party ledgers (expense, income, bank, tax and other ledgers whose group is not Sundry Debtors / Sundry Creditors). Party ledgers (customers and suppliers) are J07 `masters` (`scenarios/masters.md`); opening balances are J18; ledger reports are J12. None of those are repeated here.

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`. Not observed live; the planner confirms.
- CODE = Tech Debt Radar code index, cited as `repo:path:lines` as the index returned it.
- UNVERIFIED = not citable; the question is stated, no value invented.

## Account group

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| AG-01 | positive | Open Master > Accounts Master > Group | "Account Group List" window with a tree of groups, a Create button (F2) and a search box | KB `careportal_enriched_v5.csv#d96b054c`, `#478035fd` |
| AG-02 | positive | Create a group: Group Name, Under Group (a parent such as Bank Accounts or Indirect Expenses), Prohibited = No, Save | "Record Saved Successfully"; the new group is listed under its parent | KB `careportal_enriched_v5.csv#d96b054c` |
| AG-03 | positive | Modify a group: Edit icon, change it, Update | "Record Updated Successfully" | KB `careportal_enriched_v5.csv#478035fd` |
| AG-04 | negative | Save a group without a name | Save refused (name is mandatory). Wording UNVERIFIED | KB `#d96b054c` (field list); wording UNVERIFIED |
| AG-05 | negative | Save a group without an Under Group | Save refused. Wording UNVERIFIED | KB `#d96b054c`; CODE `usp_AccountGroupMasterUpdate` takes `@parentlinkid` (`codekb:MargBooks:schema#241b0cbc`) |
| AG-06 | negative | Create a group whose name already exists in the company | Refused. The data layer counts rows with the same name in the same company that are not deleted | CODE `margbookscoreapi:margerpdal/AccountGroup.cs:292-299` `IsAccountGroupNameExists` (`codekb:MargBooks:code#58e75544`) |
| AG-07 | boundary | Duplicate name differing only in letter case | UNVERIFIED in code: the SQL compares `name = @name`; whether it is case-blind depends on the database collation | CODE `#58e75544`; collation UNVERIFIED |
| AG-08 | negative | Create a group with the name of a predefined group (e.g. Sundry Debtors) | Refused as a duplicate (AG-06 applies to predefined groups too) | CODE `#58e75544` (no filter on predefined rows) |
| AG-09 | negative | Delete a predefined group | Refused: "Predefined Account Groups cannot be deleted" | KB `careportal_enriched_v5.csv#478035fd` |
| AG-10 | negative | Delete a group that a ledger uses | Refused: a group selected in a ledger cannot be deleted | KB `careportal_enriched_v5.csv#478035fd`; CODE `AccountGroupDal.Delete` reads `dbo.LedgerMaster` (`codekb:MargBooks:api#4dadb5bb`) |
| AG-11 | positive | Delete a user group with no ledgers | Group removed from the list. Confirmation text UNVERIFIED | KB `#478035fd`; CODE `DELETE AccountGroup/Delete` -> `usp_AccountGroupMasterDelete` (`codekb:MargBooks:api#004a478f`) |
| AG-12 | state | Prohibited = Yes on a group, then pick one of its ledgers in a bill | Alert "Ledger Prohibited From Account Group"; setting Prohibited = No resolves it | KB `careportal_enriched_v5.csv#205e3e22` |
| AG-13 | boundary | Group name: long, special characters (`& / ( ) .`), leading/trailing spaces | UNVERIFIED limits; predefined names already contain `& / ( ) . -` so these characters must be accepted | UNVERIFIED |
| AG-14 | state | Rename a group used by ledgers | Ledgers keep pointing to the group (link by id, not name). UNVERIFIED in UI | CODE `usp_AccountGroupMasterUpdate` updates by `@linkid` (`#241b0cbc`) |
| AG-15 | api | Create / read / update / delete a group by API (`POST AccountGroup/Save`, `GET AccountGroup/GetById`, `PUT AccountGroup/Update`, `DELETE AccountGroup/Delete`; open API `POST Account/createGroup`) | CRUD for the owner company; payload and auth contract UNVERIFIED | CODE `#4dadb5bb`, `#1ed47937`, `#004a478f`, `codekb:MargBooks:schema#bc143a20` |
| AG-16 | tenancy | A group created in company A is absent in company B | All group SQL filters by `complinkid`; UNVERIFIED live | CODE `#58e75544`, `#bc143a20` |
| AG-17 | known issue | Jira "Account Group Fixed ID duplicate issue" | Duplicate fixed ids on groups have occurred; a regression check after group create is advisable | KB `jira_vectordb.csv#5cf8b56c` |

## Non-party ledger (expense, income, bank, tax)

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| GL-01 | positive | Create a ledger under Indirect Expenses (or a user group under it): name + account group, Save | Saved; Indirect Expenses ledgers are admin expenses such as office expenses | KB `careportal_enriched_v5.csv#b8a0ae88`, `onedrive_processed_data.csv#f03d3903` |
| GL-02 | positive | The Create Ledger form for a non-party group shows General Info only: Ledger Name, Account Group, GST Applicable, Opening Balance; no party fields | The KB screenshot of a Forex Gain/Loss ledger shows Ledger Name, Account Group and GST Applicable (Not Applicable) | KB `onedrive_processed_data.csv#44f37361` |
| GL-03 | positive | Modify a non-party ledger (change GST Applicable or the account group), Update | "Record Updated Successfully"; the change shows on reopen | KB `careportal_enriched_v5.csv#980bd762` (change account group via Modify Ledger) |
| GL-04 | positive | Delete a non-party ledger with no transactions | Removed from the Ledger Master list | KB `careportal_enriched_v5.csv#f6bd22bb` (same rule as party ledgers) |
| GL-05 | negative | Delete a non-party ledger that has transactions | Refused | KB `careportal_enriched_v5.csv#f6bd22bb` |
| GL-06 | negative | Ledger name duplicate when "Ledger Name Duplicate allowed ?" = No | Alert "Ledger Name Already Exist" | KB `careportal_enriched_v5.csv#3b37ea40`, `#c4c32709` |
| GL-07 | state | Move a ledger to another account group | The ledger now belongs to the new group (Modify shows it) | KB `careportal_enriched_v5.csv#980bd762` |

## Open questions for a human
- Q1 AG-04/AG-05 wording: is a silent refusal (no message) acceptable, or should the form say which field is missing?
- Q2 AG-07: should duplicate checks be case-blind? (Depends on collation; needs a product decision.)
- Q3 AG-12 Prohibited: which screens honour it, and can the test tenant enable it without disturbing others?
- Q4 GL-05: what counts as a "transaction" for delete (vouchers only, or also an opening balance)?
- Q5 May tests create and delete groups freely on the shared QA tenant (unique run-id prefix, teardown clean-up)?

## KB vs live app
1. KB menu path "Master >> Account Master >> Group" vs the live sidebar (planner to confirm).
2. KB articles describe the Billing setup; trade accounts may label the form "Create Party" rather than "Create Ledger".
3. Journey matrix status for `ledger-master-crud` stays `not_started`; the analyst does not change it.
