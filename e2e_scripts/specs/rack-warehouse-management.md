# Plan: J28 rack / warehouse management (rack-warehouse-management)

Scenario pack: `scenarios/rack-warehouse-management.md`. Tests: `tests/journeys/racks/test_store_master.py`, `test_rack_master.py`, `test_rack_on_item.py`; page objects `pages/racks/`; data `test_data/racks.py`.
Status: DRAFT for QA/BA review, 2026-10-09. Final run: 15 passed (`-n 2`). Observed on the QA tenant, `chemist` login, company "Garments New 29-08 (GANE29)". No test ids on these screens; fallbacks are element ids, roles and ag-Grid cells.

## Seen live so far
- Store list: Master > Inventory Master > Store (sidebar). Create/F2 opens the store form with `#txtStoreCode`, `#txtStoreName`; Save `#btn-Save`, Close `#btn-Close`.
- Rack list: route `/rack` ("Rack List"; grid columns Rack / Store / Action; row buttons Edit (pencil) and "Delete"). The search box filters the grid to matching rows.
- Create Rack: `#storeNameDrp` store typeahead (listbox > option), `#name` rack name, `#btn-Save`.
- The same rack name can exist in two stores (seen 11:20: "QA-1171c611-R1" under Main Store and under a QA store).
- A rack created without picking a store was saved under "Main Store" (same screenshot; the store field defaults to Main Store, to confirm).
- Create Item showed a "Rack" field (placeholder "Rack") in Basic Info at 11:33.
- Sidebar Inventory Master shows Item, Store, Agency, Multi Group, HSN/SAC, Unit, Manufacturer: no "Rack" link (KB says Master > Inventory Master > Rack). See D1.

## Seen live 2026-10-09 13:5x (probe 3)
- Store list URL `/mstr/store`, grid "Store Name | Action"; predefined rows Main Store, Scrap Store.
- Store form: Store Code is mandatory. Save with code but no name, or name but no code: no toast, form stays open (no message text).
- Store saved: success toast "Record Saved Successfully !". Duplicate store name: toast "Store Name Is Already Exists!", form stays open.
- Store delete asks "Are you sure you want to delete?"; Yes -> "Record Deleted Successfully".
- Delete Main Store: toast "Predefined Store Cannot Be Deleted!" before any confirmation.
- Create Rack is a dialog "Create Rack": combobox "Search here.." (`#storeNameDrp`, default "Main Store"), textbox "Rack *" (`#name`), buttons "F10 Save" / "F9 Clear" / "Esc Close". Store options list the company's stores.
- Rack saved: toast "Record Saved Successfully."; list row "rack | store".
- Rack without name: no toast, dialog stays open.
- Duplicate rack name in the same store: toast "Rack No. Already Exists!", dialog stays open.
- Modify Rack has `#btn-Update`.
- Rack delete asks "Are you sure you want to delete the selected Record?"; Yes -> "Record Deleted Successfully".
- Closing a form with Esc Close asks "Are you sure you want to close?" (Yes/No).
- Probe 4 (14:2x): Store Code is NOT unique: a second store with an existing code saved ("Record Saved Successfully !"). See D2.
- Modify Store: `#btn-Update`, toast "Record Updated Successfully !". Store List search moves matches to the top (does not hide others); Rack List search filters.
- Same rack name in a second store: saved; list shows both rows (rack | store).
- Modify Rack (heading "Modify Rack"): rename + move to another store, `#btn-Update`, toast "Record Updated Successfully."; list shows the new name with the new store.
- Delete a store that has a rack: confirmation "Are you sure you want to delete?", Yes, then toast "Rack Are Available For This Store."; store and its racks stay.
- In probe 3 and 4 the Create Item form had no Rack field. Probe 6 (read only): Control Room > Configure (`#btnGStHeading-2`), setting "Rack Master" (row 40) = No. So the item Rack field follows Control Room "Rack Master", and someone set it to No between 11:33 and 13:50 (not this suite).
- The item form has no settings icon of its own on this build (KB describes a "Rack Required?" option behind a Settings icon on Create Item).

## Tests
Session: `page_as("chemist")`, company pinned to "Garments New 29-08" (`CompanySwitchPage.ensure_company`). Each test makes its own stores (`QA-<run_id>-St<n>`, code `Q<run_id[:4]><n>`) and racks (`QA-<run_id>-R<n>`); the `records` fixture deletes what is still listed (racks, then stores).

| Test | Scenario | Asserts (seen live) |
|---|---|---|
| test_new_store_is_listed | RW-S02 | saved toast; row in Store List |
| test_store_without_name_is_not_saved | RW-S03 | form stays open; not listed |
| test_duplicate_store_name_is_refused | RW-S04 | toast "Store Name Is Already Exists"; form stays open |
| test_renamed_store_is_listed_under_new_name | RW-S07 | "Record Updated Successfully"; new name listed |
| test_unused_store_is_deleted | RW-S08 | confirmation "Are you sure you want to delete?"; deleted toast; not listed |
| test_main_store_cannot_be_deleted | RW-S09 | toast "Predefined Store Cannot Be Deleted" |
| test_store_with_a_rack_cannot_be_deleted | RW-S11 | toast "Rack Are Available For This Store"; store still listed |
| test_new_rack_is_listed_with_its_store | RW-R02 | row with rack name and store |
| test_rack_without_name_is_not_saved | RW-R03 | dialog stays open |
| test_duplicate_rack_in_same_store_is_refused | RW-R05 | toast "Rack No. Already Exists"; dialog stays open |
| test_same_rack_name_is_allowed_in_another_store | RW-R06 | second row with the other store |
| test_edited_rack_shows_new_name_and_store | RW-R08 | "Record Updated Successfully"; row with new name and new store |
| test_unused_rack_is_deleted | RW-R09 | confirmation, deleted toast, not listed |
| test_rack_picked_on_item_is_kept_on_the_item | RW-U01 | Modify Item shows the rack in the Rack field |
| test_rack_used_by_an_item_cannot_be_deleted | RW-R10 | rack still listed after a delete attempt (KB `careportal_enriched_v5.csv#eb4e77fe`) |

The two item tests set Control Room "Rack Master" = Yes when it is not, and restore the old value in teardown (fixture `rack_field_page`, module marked `xdist_group("chemist-tenant")`). The item (`QA-<run_id>-Item`, no stock) is deleted before its rack.

Not automated: RW-S05 (predefined name), RW-S06 (D2), RW-S10 (store with stock; needs stock that cannot be cleaned, see `specs/inventory.md` D4), RW-R04 (store defaults to Main Store, so "no store" cannot be entered), RW-R07 (length), RW-U02 (no rack column known in Item List).

## NEEDS DECISION
- D1: Rack has no sidebar entry under Master > Inventory Master on this company; it is reached by URL `/rack`. Is the menu entry missing by design (setting) or a defect?
- D2: RW-S06 Store Code is mandatory but not unique (two stores saved with the same code). Intended? Not asserted by a test until decided.
- D3: The Create Item "Rack" field was present at 11:33 and absent from 13:5x (Basic Info aria snapshot lists no Rack field). It depends on the Control Room "Rack Master" setting (KB calls it "Rack Required?", `careportal_enriched_v5.csv#f1e382b2`), which this suite did not change. Who turns it off? The suite now turns it on for two tests and restores it; is that acceptable, or should the tenant keep it on?

## Cleanup
Each test names its records `QA-<run_id>-...` and deletes them in teardown (items first, then racks, then stores).
