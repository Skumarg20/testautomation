# Plan: J13 inventory stock movement (inventory)

Scenario pack: `scenarios/inventory.md`. Tests: `tests/journeys/stock/test_stock_movement.py`.
Status: DRAFT for QA/BA review. Observed live on 2026-10-08 with throwaway probes (QA tenant, `chemist` login, company "Garments New 29-08 (GANE29)", books 01-04-2026..31-03-2027). The `garments` login opens the same company. No screen here has test ids; fallbacks are element ids, `formcontrolname`s and ag-Grid `col-id`s.

Item master CRUD is J08 (`tests/journeys/inventory/`, owned by another session); this journey only imports its page objects.

## Preconditions
- `page_as("chemist")`, dashboard open, then company "Garments New 29-08" ensured (`CompanySwitchPage.ensure_company`): the login's current company is shared state that other suites switch (during this work it changed to "Pharma New Company 23-09 (PNC2)", 3037 items).
- Each test creates its own item `QA-<run_id>-Stock` (unit PCS, HSN 12345678, tax category "GST Sale - 12%", company Others) with opening stock 10 in Main Store.
- Stores on the company: "Main Store", "Scrap Store" (the store selects of Physical Stock and Stock Transfer).
- All tests share `xdist_group("chemist-stock")`: physical stock vouchers (P0000001...) and transfer challans (ST000001...) are numbered company-wide.

## Screens and locators (verified live)
| Thing | Locator / behaviour |
|---|---|
| Opening stock | After item Save the alert "Do you want to add item Opening" (Yes = `#btnYes`). Window "Opening": form `#itemOpening`, Item Name and Store Name (Main Store) disabled, Opening Qty. `#opening` (integer mask, max 10 digits), Save `#btnSave` (both buttons have aria-label "Close"). Toast "Stock Updated Successfully" |
| Toasts on stock screens | `notifier-notification` with style `material` (not success/warning): told apart by text |
| Item List stock | column `Opening` (header "Stock"), store filter shows only "Main Store". The value is cached: it shows the new stock only after "Single Item Refresh" (toast "<item> Refreshed Successfully") and a reload of the list |
| Physical Stock list | `/transaction/physicalstocklist` (direct address works), columns Voucher No, Date, Store Name, User Id, Status, Action, Download; button "F10 Process Data"; rows have a tick box |
| Physical Stock entry | Create/F2 -> `/transaction/physicalstock`. Voucher No `#txtVoucherNo`, Date `#txtPhysDate`, Store `#fromStore`, item load type `#Item` (Product, Company, Manual, Barcode). Manual opens dialog "Select Item" (searchbox "Search"; click the row then Enter). Grid cols `cus_ItemName`, `currentToEnteredValue` (As Per Book), `unitToEnteredValue` (As Per Actual, editor `#txt-unitToEnteredValue-0`), `differenceToEnteredValue`. Narration `#txtRemark` |
| Physical Stock save | F10 from the narration saves (toast "Record Saved Successfully.", app returns to the list, status "Pending"). F10 pressed with focus in the grid did not save. Back asks "Are you sure you want to clear?" (`#btnYes`) |
| Process | tick the row, "F10 Process Data" -> toast "Physical Stock Data Updated Successfully", status "Processed". Without a tick: "Please Select Any Row To Process" |
| Stock Transfer | Stock Management > Stock Transfer (the direct address `/transaction/stocktransferlist` redirects to the dashboard; use the menu). Create/F2 -> `/transaction/stock`. Selects `formcontrolname` fromStore, toStore, stockType (Manual, All Stock). Enter from Stock Type goes to Barcode, then opens "Select Item". Qty editor `#txt-quantity-0`. End saves: toast "Store Transferred Successfully!". List "Store Transfer List": Challan No. (ST000001), Date, Store From, Store To, User Id, Amount |
| Transfer settings window | "Stock Transfer Setting": Stock Negative allowed = Yes (current tenant value, not changed by tests), Rates from master/batch = Batchwise |

## Hazard seen live (affects every suite)
In "Select Item" and the Item List, a Delete key press while the search box has focus opens "Are you sure you want to delete the selected Record?" for the highlighted row (the first row, an item nobody in the test owns). Playwright's `fill("")` on a non-empty box sends such a key. Search boxes must be cleared with Control+A and overtyping (`pages/stock/search_typing.py`). Any code that answers "Yes" to whatever confirmation is open (for example `Confirmation.answer_yes_if_asked` after navigation) could then delete tenant data. `pages/inventory/create_item_page.py` uses `fill("")` on the create form's typeahead fields (not a list); worth a check by its owner.

## Plans
- SM-A (IN-01, IN-02, IN-28): create item, Yes to opening, 10, Save -> toast; Item List after refresh shows 10.
- SM-B (IN-19): new Physical Stock, Main Store, Manual, the item -> As Per Book 10; As Per Actual 15 -> Difference 5. Leave with Back + Yes.
- SM-C: save a count of 15 -> list status Pending, Item List still 10 (stock changes only when processed).
- SM-D (IN-19, IN-20): save a count (15, or 4 as a write-off), tick it, Process Data -> status Processed; Item List shows the counted quantity.
- SM-E (IN-15, IN-16): refresh the item balance (see D6), then Stock Transfer Main Store -> Scrap Store, Manual, the item, 4, End -> toast. Main Store stock (Item List) 6; Scrap Store stock 4 (As Per Book in a Physical Stock entry for Scrap Store, not saved); total still 10.

## NEEDS DECISION
- D1 (IN-17, Q7) Transfer above available stock: the transfer settings say "Stock Negative allowed = Yes" on this tenant, so an over-transfer would be accepted by configuration. Not tested; needs a decision on the expected rule and whether a test may flip the setting.
- D2 (IN-23/IN-24) Negative stock on sale: needs Control Room changes (tenant-wide); not tested.
- D3 Physical Stock needs a separate "Process Data" step; the KB page (#8924fff3) describes the entry only. Confirm the two-step behaviour is intended.
- D4 Cleanup: an item with opening stock cannot be deleted ("Opening Available In Main Store", seen live), so every run leaves `QA-<run_id>-Stock` items (and their entries) behind. Decide on a cleanup path (e.g. a dedicated stock company, or allowed deletion of opening first).
- D5 Item List and the item picker show cached stock until "Single Item Refresh"; confirm this is intended (KB #340f277e describes the refresh as a repair tool).
- D6 (possible defect) Opening stock entered when the item is created is not in the cached balance: the Stock Transfer "Select Item" shows the new item with stock 0.000, and clicking it closes the window without adding a row (no message). After "Single Item Refresh" the same item (10.000) is taken and the transfer saves. Steps: create item with opening 10 -> Stock Management > Stock Transfer > Create/F2, Main -> Scrap, Manual, pick the item. Expected (by the KB): the item is added with its opening stock available. Actual: nothing is added. Tests refresh first; decide whether this is a defect.
- Not covered (no live evidence yet): IN-18 breakage/expiry issue, IN-21/22 modify/delete physical entry, IN-25 batch-wise items, IN-27 sale cancel, IN-29/30 reports and year-end, IN-31 tenancy, IN-32 permissions, IN-35 double submit, IN-13 store master screen.
