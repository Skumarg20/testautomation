# Plan: J07 customer / vendor ledger master CRUD (masters)

Scenario pack: `scenarios/masters.md`. Tests: `tests/journeys/masters/test_party_ledger.py`.
Status: DRAFT for QA/BA review. Observed live on 2026-10-08 (QA tenant, `garments` login, the account the accounting tests use). No test ids exist on these screens; fallbacks are element ids, ag-Grid `col-id`s and roles.

## Preconditions
- `page_as("garments")`, dashboard open.
- Picked, never created: account groups `Sundry Debtors`, `Sundry Creditors`; station `Others` (stations seen: Others, Rohini, Trjhfjdhf).
- Ledger settings on the QA company (Create Party > Settings panel, not changed by tests): Mobile Number Mandatory in Ledger = Yes, Station Required? = Yes, Ledger Name Duplicate allowed ? = No.
- Each test makes its own ledgers `QA-<run_id>-Cust-<n>` / `-Supp-<n>` with mobile `9` + 9 digits from the run id (`test_data/masters.py`). The `records` fixture (`pages/masters/master_records.py`) remembers every name before saving and deletes what is still listed in teardown.

## Locators (verified live)
| Thing | Locator |
|---|---|
| Menu | Master > Accounts Master > Ledger (`AccountingMenu.open_ledger_list`) |
| Ledger Master list | heading "Ledger Master"; button "Create/F2"; searchbox "Search"; grid columns `LedgerName`, `cus_Station`, `0` (Balance), `1` (Action); row buttons "Edit/F3", "Delete" (accessible names from the svg titles) |
| Search | fills the box; matching rows move to the top, other rows stay (it does not filter) |
| Create form | heading "Create Party" (Modify: "Modify Party"); `#txtlegername`, `#drpAccountGroup` (typeahead, default Sundry Debtors), `#ddlstation` (typeahead), `#ddlCountryLinkID`, `#ddlStateLinkID` (default India / Delhi), `#ddlCity`, `#txtPostalCode`, `#txtOpeningBalance`, `#ddlIsDebitCredit`, `#txtCreditDays`, `#txtMobile`; buttons `#btn-Save` (F10), `#btn-Update`, `#btn-Clear` (F9), `#btn-Close` (Esc) |
| Delete confirmation | dialog "Confirmation", "Are you sure you want to delete the selected Record?", `#btnYes` / `#btnNo` (both aria-label "Close") |
| Toasts | `notifier-notification.notifier__notification--{success,warning,error}` |

Quirks: typeahead keys typed before its list loads are lost (typing "Indirect Expenses" left only "I"); `Typeahead.choose` clears and retypes up to 3 times. After Save the form stays on "Create Party" with empty fields.

## Plans (one test each)
| Plan | Scenario | Steps | Expected (seen live) | Test |
|---|---|---|---|---|
| ML-1 | MS-02, MS-07 | Create customer (name, Sundry Debtors, station Others, mobile), Save; open list, search | Toast "Record Saved Successfully."; row found, Station cell "Others" | `test_customer_ledger_is_listed_with_its_station` |
| ML-2 | MS-03 | Create supplier under Sundry Creditors; reopen with Edit/F3 | Account Group shows "Sundry Creditors" | `test_supplier_ledger_keeps_sundry_creditors_group` |
| ML-3 | MS-09 | F2, Save with nothing filled | Warning toast "Invalid LedgerName"; form stays | `test_ledger_without_name_is_refused` |
| ML-4 | MS-11 | Name + mobile, no station, Save | Warning "Invalid StationLinkID"; not listed | `test_party_ledger_without_station_is_refused` |
| ML-5 | Q1 (mobile mandatory) | Name + station, mobile empty, Save | Warning "Invalid Mobile1"; not listed | `test_party_ledger_without_mobile_is_refused` |
| ML-6 | MS-14 | Save a second ledger with the same name | Error toast "Ledger Already Exists!" | `test_duplicate_ledger_name_is_refused` |
| ML-7 | MS-14, MS-18 | Same name in upper case | Error toast "Ledger Already Exists!" (check is case-blind) | `test_duplicate_ledger_check_ignores_letter_case` |
| ML-8 | MS-04, MS-06 | Edit/F3, City = Pune, Update; reopen | Toast "Record Updated Successfully."; City "Pune" | `test_modified_city_shows_on_reopen` |
| ML-9 | MS-21 (no transactions) | Edit/F3, Account Group = Sundry Creditors, Update; reopen | Group "Sundry Creditors" | `test_customer_moved_to_sundry_creditors_keeps_new_group` |
| ML-10 | MS-16 | Delete, confirm Yes | Toast "Record Deleted Successfully."; not listed | `test_ledger_without_transactions_is_deleted` |

## NEEDS DECISION
1. Validation wording: the warnings are raw field names ("Invalid LedgerName", "Invalid StationLinkID", "Invalid Mobile1"), not user language. Tests assert the current text; a BA should say whether this is the intended UX (if it changes, the expected texts need a reviewed update).
2. Duplicate message: KB `#3b37ea40` says "Ledger Name Already Exist"; live it is the error toast "Ledger Already Exists!". Tests follow live.
3. MS-15 delete with transactions: a ledger with only an opening balance (no vouchers) was refused with warning "Transaction Available". Is an opening balance a "transaction" for the delete rule? Not tested here (opening balances are J18); a voucher-based test needs a decision on using shared voucher numbering.
4. MS-04 opening balance Dr/Cr, MS-12/13 GSTIN validation, MS-08 GST verification, MS-17 cross-year delete, MS-23 permissions, MS-25/26 tenancy, MS-27/28 API: not covered (opening balance is J18; no second company, limited user or API contract confirmed).
5. MS-05 create from the sale bill and the Customer master (CU-*) are not covered in this pass.
