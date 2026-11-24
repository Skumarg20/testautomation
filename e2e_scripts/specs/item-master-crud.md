# Plan: J08 item master, create flow end to end (item-master-crud)

Scenario pack: `scenarios/item-master-crud.md`. Tests: `tests/journeys/inventory/test_item_create.py`, `tests/journeys/inventory/test_item_validation_and_edit.py`.
Status: DRAFT for human review. Locators and messages observed live on 2026-10-08 (QA tenant, `chemist` login, company "Garments New 29-08 (GANE29)", books 01-04-2026..31-03-2027). No test id exists on these screens, so the fallbacks are element ids, ag-Grid `col-id`s and roles (T6).

Code from the Tech Debt Radar KB (`search_kb`; `ask_codebase` still fails with "No API key configured"):
- Create Item saves with `POST item/Save` from `CreateItemComponent.saveItem`; handler `ItemController.InsertUpdate`, `MargBooks.Item/Controllers/ItemController.cs:60-89` (KB `codekb:MargBooks:api#fb935878`). Live: `POST https://gateway.premargbooks.com/v4.2/item/Save` 200, then `item/SavePriceList`.
- The Item List deletes from `ItemMasterComponent.deleteData` (same KB chunk).
- Before saving, the form calls `GET item/CheckItem?name=...&packing=...` (live), which is the duplicate-name check of IM-14.

## Preconditions
- Session `page_as("chemist")`, dashboard open.
- Masters that exist on the tenant and are picked, never created: unit `PCS`, HSN `12345678`, tax category `GST Sale - 12%`, company (agency) `Others`.
- Each test makes its own item `QA-<run_id>-Item` (`DataFactory.item_master()`). The `new_item` fixture deletes it after the test (IM-11 path; allowed because the item has no transactions).

## Locators (verified live)
| Thing | Locator |
|---|---|
| Menu | Master > Inventory Master > Item (`ModuleMenu.open_item_master`) |
| Item List | searchbox "Search" (`#searchItems`; filters on key events only, `fill` does nothing; filtered-out rows keep empty cells in the DOM); ag-Grid rows; cells `[col-id]` `Product`, `packing`, `cus_ItemCompanyName`, `Opening` (header "Stock"), `cus_unitname2`, `ratea` (header "Sale Rate") |
| Row actions | buttons "Edit/F3" (`#Grideditbtn<id>`), "Delete" (`#Griddeletetbtn<id>`) |
| Tax Info panel | `div.taxInfo`, list items "HSN/SAC", "IGST %", "CGST %", "SGST %" |
| Create Item | F2 on the Item List; route `/item-master/item-create` |
| Product | `#txtProduct` (formcontrolname `Product`) |
| Unit / HSN / Tax Category | typeahead comboboxes `#unit`, `#hsn`, `#taxxCategory`; suggestions are `listbox` > `option` |
| Company | `#txtcompName`; typing opens dialog "Select Agency" (searchbox + grid); clicking the row picks it |
| Prices | `#txtmrp`, `#txtprate`, `#txtcost`, `#txtratea` (default `0.000`) |
| Buttons | `#btnSave` (F10), `#btnClear` (F9), `#btnClose` (Esc) |
| Yes/No alert | `div.active.modal-new`, buttons `#btnYes`, `#btnNo` (both have aria-label "Close") |
| Toasts | `notifier-notification.notifier__notification--success` |

Quirks seen live:
- Esc closes the whole Create Item form, so it must never be used to close a suggestion list.
- A typeahead sometimes stays shut when typing beats the load of its master; the page object clears and retypes (3 tries).
- Clearing `#txtcompName` opens a Select Agency dialog and typing opens a second one; the page object types without clearing.
- Toast texts are lower case in the DOM ("Record saved successfully") and capitalised by CSS; checks ignore case.
- Names with spaces are shown with non-breaking spaces in the grid; test item names have no spaces.
- Edit/F3 and Delete act on the selected row, and ag-Grid reuses row elements while it scrolls. On a long list (20+ items on 2026-10-08, most from other sessions) a click on a row's button opened another item. The page object filters the list to the one product with the search box and checks the row is selected (`ag-row-selected`) before Edit or Delete.
- An empty mandatory lookup (Unit, HSN/SAC, Tax Category, Company) shows only a red "!" with no text; the test checks Angular's `ng-invalid` class on the input.

## Plan IC-A: create with mandatory fields (IM-01, IM-02)
1. Open the Item List, press F2. Expect Create Item with an empty Product.
2. Product `QA-<run_id>-Item`, Unit `PCS`, HSN/SAC `12345678`, Tax Category `GST Sale - 12%`, Company `Others`, M.R.P 200, Sale Rate 150.
3. Save. Expect success toast "Record saved successfully".
4. Expect the alert "Do you want to add item Opening" with Yes/No. Answer No. Expect the form cleared for the next item.

## Plan IC-B: item in the Item List (IM-01, IM-07, IM-03b)
1. After IC-A, open the Item List. Expect exactly one row with the product name.
2. Expect Unit `PCS`, Company `Others`, Sale Rate 150 (compared as Decimal).
3. Expect Stock 0 (no opening stock was added).

## Plan IC-C: tax info of the saved item (IM-04, IM-06)
1. Select the row. Expect Tax Info HSN/SAC `12345678`, IGST % = 12, CGST % = SGST % = 6.
Oracle: the tax category rate from the test data; CGST and SGST are each half of it. Never read from the screen.

## Plan IC-D: delete an item without transactions (IM-11)
1. Click the row's Delete. Expect alert "Are you sure you want to delete the selected Record?". Answer Yes.
2. Expect success toast "Record deleted successfully" and no row with the name.

## Plan IC-E: required fields (IM-13, IM-13b)
1. Open Create Item, Save with nothing filled. Expect the text "Product is required!".
2. Product only, Save. Expect Unit, HSN/SAC, Tax Category and Company each marked invalid (one test per field), and no item with that name in the Item List.

## Plan IC-F: duplicate name (IM-14, default "Product Name Duplicate Allowed?")
1. After IC-A, create a second item with the same name and no packing. Expect the toast "Packing Is Required For Duplicate Product Names" and still one row with that name.
Observed: the refusal is about the missing packing, so the duplicate rule seems to be "name + packing must differ" (KB `jira_vectordb.csv#d0be7bf8`). IM-14c (same name, different packing) is not automated yet.

## Plan IC-G: edit (IM-09)
1. After IC-A, filter the Item List to the item, select it, Edit/F3. Expect Modify mode: same Product, button "F10 Update", route `/item-master/item-create;id=...`.
2. HSN/SAC `54545454` (another existing HSN), Sale Rate 175, Update. Expect toast "Record updated successfully".
3. Item List: Tax Info HSN/SAC `54545454`, Sale Rate 175.

## NEEDS DECISION: opening stock Yes (IM-03) and delete with opening (IM-12b)
Observed 2026-10-08: answering Yes opens a small "Opening" window (Item Name, Store Name "Main Store", "Opening Qty. *" `#opening`, Save, Close). Saving 7 shows "Stock Updated Successfully", but the Item List and the Main Store opening list both show 0 for the item afterwards (not explained). Delete is then refused with an error toast "Opening Available In Main Store", even with the opening shown as 0. Editing the item does not offer the opening window again, and the opening window could not be reopened from Master > Opening Balance > Stock in this probe. Result: item `QA-a481ef76-Item` cannot be deleted from the UI and stays on the tenant.
- An automated IM-03 test would leave one undeletable item per run, so it is not written. Needs a decision: a cleanup path (API or DB) for opening stock, or a dedicated tenant.
- Possible defect: the opening of 7 is saved ("Stock Updated Successfully") but shows as 0, and an item with opening 0 cannot be deleted. Compare MB-030141 (false "item is used", KB `jira_vectordb.csv#87a67294`) and MB-034558 (opening quantity cannot be changed, KB `jira_vectordb.csv#78fa65be`).

## Not covered yet
IM-05 decimal unit, IM-08 inline company create, IM-10 tax history, IM-12 delete refused for an item with transactions, IM-13c save with no unit (defect MB-036985; the Unit suggestion list stayed open over the HSN field in the probe), IM-14b/c/d duplicates with the setting changed (tenant-wide, needs `xdist_group("chemist-tenant")`), IM-15 boundaries, IM-25 API layer (`POST item/Save` payload not captured yet).

## Open questions
- Q-IC1 The `chemist` login opens a garments company (GANE29). Is that the intended company for item master tests?
- Q-IC2 The Item List search box did not filter rows when filled; on a tenant with many items the virtualised grid may not render the new row. Confirm how search should be used.
