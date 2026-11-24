# Plan: J40 Manufacturing module (manufacturing-module)

Scenario pack: `scenarios/manufacturing-module.md`. Tests: `tests/journeys/manufacturing/` (`test_bom_master.py`, `test_bom_stock.py`, `test_conversion.py`, `conftest.py`). Page objects: `pages/manufacturing/` (`menu.py`, `bom_master.py`, `stock_vouchers.py`, `items.py`). Test data: `test_data/manufacturing.py`.
Status: DRAFT for QA/BA review. Observed live on 2026-10-12 (QA tenant premargbooks, `chemist` login, app V. 4.3.598.b) on "Garments New 29-08 (GANE29)" and "Pharma New Company 23-09 (PNC2)", books 01-04-2026..31-03-2027. No test ids on these screens.

Priority marker: `pytest.mark.p3` (J40 is P3 in the matrix and `p3` is registered in `pyproject.toml`).

## Result of the live look: the module is not enabled on any company the suite uses
- On both GANE29 and PNC2 the Stock Management menu lists only **Stock Transfer** and **Physical Stock**. There is no "Bill of Materials" and no "Conversion" sub-menu.
- Control Room > Configure (read only, nothing saved): **"Bill Of Material(BOM)"** (S.No 367) = **No** and **"One To Many & Many To One required?"** (S.No 21) = **No** on both companies. The pack's K10 is answered: the switches gate the menus; the trade was not the reason.
- Direct URLs: `/sale/matissue`, `/purchase/matrecieve`, `/purchase/onetomany`, `/purchase/manytoone` redirect to `/dashboard`. `/transaction/billofmaterial` (Material Master list) and `/report/bomreport` (Production Planning filter) open even with the switch off (see N3).
- The other organisations on the login (Outstanding Santosh Ji, Pharma New Company Without Cx, Santosh Sir Outstatdning Check, TEENA SHARMA25-26, tEST-1) were not opened: switching the shared login to them would disturb the suite run that was going at the time, and the switches default to No.

During that look nothing on the tenant was changed. Since decision N1 (2026-10-12) each test turns the switch it needs on itself and puts the original value back (see Preconditions).

## Preconditions and test data (when the switches are on)
- Company pinned to GANE29 (`CompanySwitchPage.ensure_company`), as in the other journeys.
- Control Room switch per test (N1 decided): the `bom_page` fixture holds "Bill Of Material(BOM)" at Yes, the `conversion_page` fixture holds "One To Many & Many To One required?" at Yes (`pages/settings/control_room_switch.py::switch_held` over `ControlRoomState`). The fixture reads the original value first (never assumes No), writes only if it differs, reloads the dashboard and then requires the sub-menu ("Bill of Materials" / "Conversion"): if it is still missing, the test **fails** with `ScreenNotOfferedError`. Teardown goes back to the dashboard, writes the original value even if the test or that step failed, and reads it again (`SwitchNotRestoredError` if it did not go back). All three test modules are in xdist group `chemist-tenant` (CLAUDE.md rule 0). A test skips only when the `chemist` account has no credentials.
- Own items per test, named `QA-<run_id>-...`, so no other session can change the figures:
  - RM-A opening 100, RM-B opening 50, FG opening 0 (pack data line); FG-2 (opening 0) for MF-07.
  - BIG Conversion 1 opening 80; S1 Conversion 1 and S5 Conversion 5, each opening 5 (the opening of the small items is not in the pack; it lets Many to One take them off).
- BOM `BOM-<run_id>`: FG 1 = RM-A 2 + RM-B 1, party for vouchers "Production Department".
- Stock read with `pages/stock/item_stock_balance.py` (main store, Single Item Refresh first) after each step.
- Teardown in reverse dependency order: receive -> issue -> BOM -> finished item (fixture teardown order, `start_receive` depends on `material_issue`). Items with opening stock stay behind under the run id: the app refuses to delete them ("Opening Available In Main Store", `specs/inventory.md` D4).

## Screens
| Thing | What and locator | Seen live? |
|---|---|---|
| Menu | Stock Management > Bill of Materials > Material Master / Material Issue / Material Received; Stock Management > Conversion > One to many / Many to one (KB `#5edef903`, `#67531890`, `#25e8dd21`) | No: sub-menus absent |
| BOM list | `/transaction/billofmaterial`, heading "Material Master", button "Create/F2", columns S.No, Date, BOM Name, Product, Qty, By Product Qty., Action (col-ids `bomName`, `product`, `quantity`, `byproductQuantity`) | Yes (empty list on GANE29) |
| BOM editor | `#txtbomname` (min 4, max 50), `#txtitemname` (focus opens "Select Item"), `#txtqty` (Enter moves to the grid); raw grid `#rmcproduct`, cell editor `#txt-itemLinkID-<row>`; button "Save" (`billofmaterialmaster.html:26-50`, `bom.itemselection.ts:21`) | No |
| Material Issue / Received, One to many / Many to one | common transaction screen: list "Create/F2", party picker (Production Department), item grid (`EntryGrid`), number field "Invoice No." (`onetomany.facory.ts`), "Save" | No |
| Raw Materials Consumed | overlay with heading "Raw Materials Consumed", grid col `quantity`, button "Ok" (`billofmaterialdetails.ts:16-50`) | No |
| Conversion item | row 0 asks for the big item first (`transactionin.component.ts:6835`); "Stock Update" window, OK | No |
| Item Conversion field | `#txtconversion` on Create Item (`createitem.component.html:2105`) | No |

Every "No" row is from the Angular source and must be checked by the healer the first time the tests run with the switches on.

## Tests
Each test runs with its switch on (N1); see "Last live run" in `.claude/tmp-journeys/manufacturing-module/notes.md` for the current result.

| Test | Scenario | Asserts |
|---|---|---|
| `test_bom_master.py::test_saved_bom_returns_to_the_list` | MF-02 | toast "Record saved successfully.", URL `/transaction/billofmaterial` |
| `test_bom_master.py::test_bom_list_shows_the_saved_bom` | MF-03 | row with BOM name and FG, Qty 1, By Product Qty 0 |
| `test_bom_master.py::test_bom_name_differing_only_by_case_and_spaces_is_refused` | MF-07 | "... already exist" (API text, visible text unverified), editor stays |
| `test_bom_master.py::test_second_bom_for_the_same_finished_item_is_refused` | MF-08 | "Bom Of this <FG> Already Exists!" |
| `test_bom_master.py::test_bom_without_raw_materials_is_not_saved` | MF-09 | "Raw Material Required!", editor stays |
| `test_bom_master.py::test_unused_bom_can_be_deleted` | MF-23 | toast "Record updated successfully." (K3), row gone |
| `test_bom_stock.py::test_material_issue_takes_raw_materials_out_of_the_main_store` | MF-14 | RM-A 80, RM-B 40 |
| `test_bom_stock.py::test_raw_materials_consumed_window_lists_bom_quantities_for_the_sets_received` | MF-18 | window lists RM-A 20, RM-B 10 for FG 10 |
| `test_bom_stock.py::test_material_receive_adds_the_finished_items` | MF-18 | FG 10 |
| `test_bom_stock.py::test_material_receive_does_not_take_raw_materials_out_again` | MF-18 | RM-A stays 80, RM-B stays 40 |
| `test_bom_stock.py::test_partial_receive_adds_only_the_sets_received` | MF-19 | FG 7 |
| `test_bom_stock.py::test_receive_of_more_sets_than_issued_is_refused` | MF-20 | "<RM-A> Quantity Not Available", window stays |
| `test_bom_stock.py::test_bom_with_a_receive_cannot_be_deleted` | MF-24 | "Bill of Material Already Used", row stays |
| `test_conversion.py::test_one_to_many_takes_the_converted_quantity_off_the_big_item` | MF-30 | BIG 80 -> 50 |
| `test_conversion.py::test_one_to_many_adds_the_small_items` | MF-30 | S1 5 -> 10, S5 5 -> 10 |
| `test_conversion.py::test_many_to_one_adds_the_converted_quantity_to_the_big_item` | MF-31 | BIG 80 -> 90 (posted once, MB-038393) |
| `test_conversion.py::test_many_to_one_takes_the_small_items_off` | MF-31 | S1 5 -> 0, S5 5 -> 4 |
| `test_bom_master.py::test_bom_name_differing_only_by_case_and_spaces_is_refused` (changed 2026-10-13) | MF-07 | now reads the field's validation text "BOM Name already exists !" instead of a toast (validation.component.html:39-40) |
| `test_switches.py::test_bom_switch_lists_material_master_issue_and_received` | MF-01 | Bill of Materials lists Material Master, Material Issue, Material Received |
| `test_switches.py::test_conversion_switch_lists_one_to_many_and_many_to_one` | MF-29 | Conversion lists One to many, Many to one |
| `test_bom_validation.py::test_blank_header_field_is_marked_required[name/item/quantity]` | MF-05 | "BOM Name required !" / "Item Name required !" / "Quantity required !" |
| `test_bom_validation.py::test_bom_name_input_stops_at_fifty_characters` | MF-06 | 51 typed, 50 kept |
| `test_bom_validation.py::test_bom_name_of_three_characters_is_marked_too_short` | MF-06 | "Minimum n characters required !" |
| `test_bom_validation.py::test_bom_name_of_four_characters_is_not_marked_too_short` | MF-06 | no minimum-length text |
| `test_bom_validation.py::test_bom_name_keeps_unicode_and_special_characters` | MF-06 | typed text kept as is (N5) |
| `test_bom_validation.py::test_quantity_on_a_raw_row_without_an_item_is_refused` | MF-10 | "Please select item first" |
| `test_bom_validation.py::test_raw_material_quantity_of_zero_is_refused` | MF-10 | "Quantity should be greater than 0!" |
| `test_bom_validation.py::test_service_item_is_refused_as_raw_material` | MF-11 | "Can't Select Service Item!" |
| `test_bom_validation.py::test_finished_item_is_refused_as_its_own_raw_material` | MF-11 | "Can't Select Finised Good!" |
| `test_bom_validation.py::test_raw_material_is_refused_as_a_by_product` | MF-11 | "Can't Select Raw Material Items!" |
| `test_bom_validation.py::test_raw_material_chosen_twice_stays_one_row` | MF-11 | raw footer stays "Total: 1 Product" |
| `test_bom_validation.py::test_addition_cost_of_zero_is_refused` | MF-12 | "Please enter amount" |
| `test_bom_validation.py::test_tab_on_quantity_warns_about_the_conversion` | MF-13 | "Quantity Should By multiple of conversion" on Tab (K6) |
| `test_bom_validation.py::test_bom_quantity_is_saved_times_the_conversion` | MF-13 | FG Conversion 10, Qty 1: list Qty 10 |
| `test_bom_more.py::test_by_product_and_addition_cost_are_counted_in_their_grid_totals` | MF-04 | "Total: 1 Product" (by-product), "Total: 1 Ledger" |
| `test_bom_more.py::test_bom_with_by_product_and_addition_cost_is_saved_with_its_by_product_quantity` | MF-04 | saved, list By Product Qty 1 |
| `test_bom_more.py::test_saved_bom_opens_for_change_with_its_raw_materials` | MF-25 | grid shows RM-A, RM-B (MBC-16368) |
| `test_bom_more.py::test_unused_bom_raw_quantity_change_is_updated` | MF-25 | "Record updated successfully." |
| `test_bom_more.py::test_raw_row_of_a_used_bom_cannot_be_deleted` | MF-25 | "Bill of Material Already Used" |
| `test_bom_more.py::test_bom_of_one_company_is_not_listed_in_another` | MF-35 | BOM of GANE29 absent from the PNC2 list (opened by URL, N3) |
| `test_bom_vouchers.py::test_issue_line_rate_is_the_item_master_rate` | MF-15 | Rate = item's Rate A |
| `test_bom_vouchers.py::test_issue_line_amount_is_quantity_times_rate` | MF-15 | Amount = 20 x Rate |
| `test_bom_vouchers.py::test_issue_party_window_offers_production_department` | MF-16 | Production Department listed |
| `test_bom_vouchers.py::test_issue_party_window_leaves_out_ledgers_of_other_groups` | MF-16 | "Cash" not listed |
| `test_bom_vouchers.py::test_issue_beyond_stock_is_warned_when_negative_stock_is_not_allowed` | MF-17 | Stock Negative allowed = No: "Stock going in negative!" |
| `test_bom_vouchers.py::test_issue_beyond_stock_takes_the_raw_material_negative_when_allowed` | MF-17 | = Yes: RM-A -20 |
| `test_bom_vouchers.py::test_receive_below_the_bom_quantity_is_refused` | MF-21 | "Minimum Quantity Should be :2" |
| `test_bom_vouchers.py::test_receive_of_a_non_multiple_scales_the_raw_materials` | MF-21 | receive 3 of a BOM for 2: RM-A 6, RM-B 3 |
| `test_bom_vouchers.py::test_receive_without_an_issue_is_refused` | MF-22 | "<RM-A> Quantity Not Available" |
| `test_bom_vouchers.py::test_deleted_issue_puts_the_raw_materials_back` | MF-26 | RM-A 100, RM-B 50 |
| `test_bom_vouchers.py::test_changed_issue_takes_out_the_new_quantity` | MF-26 | "Sale Bill updated successfully!", RM-A 70 |
| `test_bom_vouchers.py::test_deleted_receive_takes_the_finished_items_off_again` | MF-26 | FG 0 |
| `test_bom_vouchers.py::test_receive_batch_change_is_saved` | MF-26 / MB-038971 | " Updated successfully!"; skips if the receive grid has no Batch column |
| `test_bom_vouchers.py::test_issue_dated_before_the_books_year_is_refused` | MF-36 | "Invalid entry date ! Date should be between financial year." |
| `test_bom_vouchers.py::test_receive_dated_after_the_books_year_is_refused` | MF-36 | same text on the receive |
| `test_bom_reports.py::test_pending_register_shows_the_sets_not_yet_received` | MF-19 | 3 sets pending: RM-A 6, RM-B 3 |
| `test_bom_reports.py::test_pending_register_refuses_a_ledger_that_is_not_a_manufacturer` | MF-27 | "Please Select Only 'Sundry Creditor (Manufacturer)' A/C Ledgers" |
| `test_bom_reports.py::test_costing_lists_each_component_with_its_bom_quantity` | MF-27 | Qty RM-A 2, RM-B 1 |
| `test_bom_reports.py::test_costing_component_value_is_quantity_times_cost` | MF-27 | Value = Qty x Cost |
| `test_bom_reports.py::test_costing_total_is_the_sum_of_the_component_values` | MF-27 | total Value = sum (N6) |
| `test_bom_reports.py::test_production_planning_multiplies_the_bom_by_the_planned_quantity` | MF-28 | Required Qty RM-A 20, RM-B 10 |
| `test_bom_reports.py::test_production_planning_recalculates_when_the_planned_quantity_changes` | MF-28 | RM-A 30, RM-B 15 (MBC-17129) |
| `test_conversion_more.py::test_item_ledger_lists_the_earlier_purchase_before_the_one_to_many` | MF-32 | purchase line before the OM line (MB-034805) |
| `test_conversion_more.py::test_item_ledger_running_balance_never_goes_negative` | MF-32 | no negative running balance |
| `test_conversion_more.py::test_conversion_of_an_item_with_a_conversion_entry_cannot_be_changed` | MF-33 | Conversion field read-only |
| `test_access.py::test_material_issue_is_not_in_the_menu_of_a_role_without_its_right` | MF-34 | no Material Issue entry for `operator` |
| `test_access.py::test_material_issue_url_is_refused_to_a_role_without_its_right` | MF-34 | `/sale/matissue` redirected or denied |
| `test_access.py::test_bmr_type_master_is_listed_under_inventory_master` | MF-37 | Master > Inventory Master > BMR Type (N7) |

All 37 scenarios are now scripted (2026-10-13, offline). None is marked `permanent` and none needs a stub: nothing sends anything, and every test deletes what it saves except items with opening stock (D4, as before). Tenant-wide settings changed and restored: the two manufacturing switches and, for MF-17, Control Room "Stock Negative allowed" (`pages/settings/stock_negative_setting.py`, a `SwitchAccess` for `switch_held`). Runtime skips: MF-34 if the `operator` login cannot reach GANE29, MF-26 batch part if the receive grid has no Batch column.

Also changed for these tests (locator fixes from the source, not seen live): the item Conversion field is `#txtunitConversion` (the old `#txtconversion` is inside a commented-out block, createitem.component.html:2094-2109), and the Material Issue number label is "Bill No." (billofmaterialissue.factory.ts:37), not "Invoice No.".

## Defects seen
None: no manufacturing screen could be exercised.

## NEEDS DECISION
- N1 (MF-01, MF-29): **DECIDED 2026-10-12 (orchestrator): option (b), per test.** The fixture turns the switch on and restores the original value in teardown; tests are in xdist group "chemist-tenant". While a test runs, the Stock Management menu of GANE29 also shows the sub-menu to any other session on the tenant.
- N2 (K4): "used" is computed per component item, not per BOM. Once the switch is on, MF-24 may also lock BOMs of other sessions that share no item with ours; our items are run-unique, so our tests are safe, but the rule itself needs a decision.
- N3: `/transaction/billofmaterial` and `/report/bomreport` open by URL with the BOM switch off while the vouchers redirect. Should the list and the report also be refused when the feature is off? Not asserted.
- N4: `SMALL_OPENING = 5` for S1 and S5 is test data of this plan, not of the pack. Confirm or replace.
- N5 (MF-06): the pack has no expected value for unicode and special characters in BOM Name; the test asserts they are kept as typed (no input mask). Confirm.
- N6 (MF-27): whether Costing includes Additional Cost is UNVERIFIED; the test only asserts total = sum of the listed component values.
- N7 (MF-37, K1): `manufacturing.module.ts:8-9` imports BMR Type components whose files are not in the UI repo, and no route loads the module. The test asserts the KB's menu entry; if it fails, decide whether BMR Type exists in the web app at all.
- N8 (MF-34): the test assumes the `operator` role has no "MaterialIssue" right. If it has, the test fails; give it a role without the right or name another login.

## Not automated (and why)
None. Every scenario MF-01..MF-37 has a test (see Tests). Nothing in this journey is desktop-only or needs a physical device.

## To verify live (locators and texts not seen; source file:line)
- Menu child entries under Bill of Materials / Conversion (`pages/manufacturing/menu.py`), Master > Inventory Master > "BMR Type" (KB `#a835ce0d`; no source).
- BOM editor: `#txtbomname`, `#txtitemname`, `#txtqty` and their validation texts (billofmaterialmaster.html:26-53, validation.component.html:17-53); "Update" button (billofmaterialmaster.html:128); list row "Edit" button (billofmaterialmasterlist.ts:211).
- BOM grids `#rmcproduct`, `#byproduct`, `#additional`, footers `#<id>Foot`, F10 order, cost column `salePurchaseRate`, row "Delete" (billofmaterialmaster.html:58-112, .ts:315-341, 369-411); the ledger window "Select Addition ledger" takes its first row (bom.itemselection.ts:132-160).
- Raw item editor `#txt-itemLinkID-<row>` and the picker refusals (bom.itemselection.ts:21, itemmaster.component.ts:4889-4903); whether Escape on the raw window leaves hotkeys working (MF-10 first test).
- Item form: `#txtunitConversion` (createitem.component.html:199), supply type `#typeofSupply` option "Service" (:112).
- Voucher date input `input[id^="txtbillDate"]` (processout.transaction.component.html:131, transactionin.component.html:127); line cells `salePurchaseRate`, `DisplayAmount`, `batchLinkID`; edit icon `button.mksBtn.edit` and "F3 Modify" on the voucher lists (as seen on the sale list, pages/accounting/outstanding/document_list.py:31-45).
- Issue line Rate: assumed Rate A (`DefaultBillingRate`, bom.itemselection.ts:118 uses it for BOM rows).
- Party window search for "Cash" on Material Issue and on the Pending & Register "Select Party" (fixedID 42 may hide other groups entirely, billofmaterial.report.ts:394-417).
- Stock Setting window: "Stock Negative" row's "Configure" button, `#negativeAllowed`, options "Yes"/"No", F10 to close (stock-negative-setting.html).
- Reports: `/report/bomreport/bomdefault`, `/costing`, `/report/bomreport` + `#txtplanningtype`, `#txtitem`, OK; grids `#reportGrid`, `#reportGrid1`, `#trialBalFoot`; col-ids "Qty", "Cost", "Value", "Required Qty" and a Pending column (sp_Bomreport is not in the API repo).
- Item Ledger `/item-master/report/itemledger`, Enter to the detail, body rows `.ag-center-cols-container .ag-row`, a balance col-id containing "balance" (item.module.ts:38, itemmaster.component.ts:2881-2916).
- MF-32 purchase: garments purchase window save toast, and deleting the bill from Purchase > Bill by its invoice number (pages/manufacturing/purchase_in.py).
- `operator` login reaching GANE29 (MF-34).

## KB vs live app
- K10 answered: the menus are gated by the two Control Room switches, both No on the garments and the pharma company. The pack is unchanged.
- K2 partly answered: the BOM list lives at `/transaction/billofmaterial`. The editor URL is still unseen.
