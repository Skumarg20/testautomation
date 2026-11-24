# Plan: J18 opening balance entry (opening-balance-entry)

Scenario pack: `scenarios/opening-balance-entry.md`. Tests: `tests/journeys/accounting/test_opening_balance.py`.
Status: DRAFT for QA/BA review. Locators and messages observed live on 2026-10-08 (QA tenant, `garments` login, books 01-04-2026..31-03-2027). No test ids on these screens; the fallbacks are element ids (the form labels are not linked to their inputs) and roles.

## Preconditions
- Session `page_as("garments")` via the accounting `accounting_page` fixture, dashboard open.
- Each test creates its own party ledger `QA-<run_id>-OB-...` (`DataFactory.party_name`) in Sundry Debtors, station "Others", mobile 9876543210. The `owned_ledgers` fixture (accounting `conftest.py`) deletes every ledger the test created. No existing ledger is opened or changed.

## Locators (verified live)
| Thing | Locator |
|---|---|
| Page | `/partymaster/opening-ledger` (Master > Opening Balance > Ledger), heading "Opening Balance" |
| List | searchbox "Search" (`#SearchBox`); grid columns "Ledger Name", "Station", "₹ Balance", "Action"; row buttons "Edit/F3", "Delete" |
| Create / modify form | "Create/F2" opens "Create Party"; "Edit/F3" opens "Modify Party" |
| Fields | `#txtlegername`, `#drpAccountGroup` and `#ddlstation` (typeahead, `listbox` > `option`), `#txtMobile`, `#ddlBalancingMethod` (Bill By Bill / On Account), `#txtOpeningBalance`, `#ddlIsDebitCredit` (Dr / Cr) |
| Save | button "F10 Save"; toast "Record saved successfully." |
| Delete | row "Delete", dialog "Confirmation" ("Are you sure you want to delete the selected Record?"), Yes/No buttons both named "Close" (told apart by text) |

## OB-A Debit opening balance (OB-01)
1. Create/F2, name, station, mobile, On Account, Opening Balance 1234.50, Dr, F10 Save.
2. Expect toast "Record saved successfully."; the list row shows "1,234.500 Dr" (amount compared as Decimal 1234.50, side Dr).

## OB-B Credit opening balance (OB-02)
As OB-A with 750.25 Cr. Expect 750.25 Cr in the list.

## OB-C Change the opening balance (OB-03)
1. Create with 1000 Dr. 2. Edit/F3 from the Opening Balance list, set 400, Cr, save.
3. Expect the list to show 400 Cr and the reopened form to show 400.000 / Cr.

## OB-D Bill By Bill party (OB-04)
Create with Balancing Method "Bill By Bill", 1500 Dr. Expect save and 1500 Dr in the list.

## NEEDS DECISION
- OB-04: the KB (`careportal_enriched_v5.csv#37c5efe8`, `#ae4f03c8`) says a bill-wise "Opening Balance" window opens for a Bill By Bill ledger. Live, no window opened on Enter or on save; the ledger saved with only the amount. Is bill-wise opening entry gone from the web form, behind a setting ("Ledger Setting" panel), or a defect? Not asserted until decided.
- OB-06: the KB (`#e970a2d0`) says changing an opening balance needs a switch to the previous financial year. Live, the change saved in the current year without any prompt. Which is correct?
- The list shows amounts with 3 decimals ("1,234.500"); Indian vs western digit grouping above 99,999 not checked; amounts in tests stay below that.
- OB-07..OB-12 (zero, non-numeric, >3 decimals, tenancy, permission): not verified live; not automated.
- Observation (security, not J18): after a forced re-login the app's login URL carried a base64 `c=` parameter that appeared to encode the account identity and password. Flag for the security reviewer; value not copied here.
