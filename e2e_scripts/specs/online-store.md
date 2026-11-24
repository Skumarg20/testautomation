# Plan: J37 Online store setting & orders (online-store)

Scenario pack: `scenarios/online-store.md`. Tests: `tests/journeys/online_store/` (`test_store_entry.py`, `test_store_setting.py`, `test_order_dashboard.py`, `test_order_conversion.py`, `test_store_creation.py`, `test_conversion_rules.py`, `test_order_figures.py`, `test_store_tenancy.py`, `test_store_catalogue.py`, `test_store_access.py`, `conftest.py`). Page objects: `pages/online_store/` (`entry.py`, `create_store.py`, `order_dashboard.py`, `order_api.py`, `store_setting.py`, `store_items.py`, `store_endpoints.py`, `marg_mart_portal.py`, `marg_mart_items.py`, `converted_bill.py`, `status_updates.py`). Test data: `test_data/online_store.py`.
Status: **DRAFT — locators from Angular source, NOT yet verified live.** Written offline on 2026-10-12/13 with no browser and no login. Every locator, route and message comes from `newmarg-webangular20/src/app/` (paths below are relative to it) or `margbookscoreapi/`. The pack warns that the UI is changing (MBC-17208 "Online Store New UI Update" is in live testing), so expect the healer to move selectors.

Priority marker: `pytest.mark.p3` (J37 is P3 in the matrix; `p3` is registered in `pyproject.toml`). Journey marker: `pytest.mark.journey("online-store")`.

## Decisions taken (orchestrator, 2026-10-12)
- Only the **own (in-house) Online Store** mode is automated (`OnlinestoreNotMart`, fixed ledger 83, `OnlineStore/*` API). Marg Mart orders come from margmart.com and are manual only.
- Orders are seeded with `POST v4.2/OnlineStore/SubmitOrder` as the logged-in user and named `QA-<run_id>-Order-n` / `QA-<run_id>-Customer-n`.
- Tenant-wide settings are set and **restored** by fixtures; those tests are in xdist group `chemist-tenant`.
- 2026-10-13 (script-all brief, offline): every remaining scenario is scripted. Irreversible ones (create a store, upload an item into the store) are marked `pytest.mark.permanent(...)` and skip unless the run passes `--allow-permanent`. Store creation, Marg Mart registration, catalogue writes and margmart.com are answered by `StubbedEndpoint` stubs on a page armed with a `SendGuard` (`store_endpoints.py`), and each stubbed test proves its stub was hit (`capture_one` / `expect_none_during`). Marg Mart flows (OS-07, OS-33) are therefore scripted with stubs, not left manual.

## Preconditions and test data
- Account `chemist`, company pinned to Garments New 29-08 (GANE29) with `CompanySwitchPage.ensure_company`, as in the other journeys. The pack names no trade-specific need, so the default company is used. Its store state is unknown (see N1).
- Store state decides which tests can run (both skip with the scenario id and the question when GANE29 is in the other state):
  - `create_store_page`: `/other/onlinestore` must land on `/other/createStore` (company has no store): OS-01, OS-03.
  - `store_api` / `dashboard`: the company must have an own Online Store; a company that also has Marg Mart opens in Marg Mart mode and is switched with "Switch to Online Store".
  - No fixture creates a store: `SaveOnlineStore` has no delete, so OS-04 would change the company for good (N1).
- **Seeding** (`pages/online_store/order_api.py`): the API takes the company from encrypted headers that the app's interceptor builds (`Services/LoaderInterceptor.service.ts:47-73`). The fixture captures the headers of the dashboard's own `OnlineStore/GetSavedOrders` call and replays them with `page.request`. The headers carry the session's credentials and are never logged or put in an error message. The gateway URL comes from the same request. `ApiClient` (`fixtures/api_client.py`) is not used because it has no session auth.
- Order bodies follow `margerpmodel/OnlineStoreNew.cs:141-190`. `quantity` is an `int`, so seeded quantities are whole (qty 2, price 125.50). `orderstatus` is free text, so Converted and Order Rejected orders are seeded directly for OS-17.
- For conversion (OS-18/19) the order line must point at a real item: the test creates `QA-<run_id>-Item` (Master > Item, no opening stock) and looks up its linkid with `OnlineStore/GetItemListForMapping` (paged, `type: "all"`). The saved bill is deleted in teardown, then the item.
- Store Setting: the Control Room row "Store Setting" (bindCode 4409) is a Yes/No row whose "Configure" button shows only while it is Yes (`UtililityComponent/DynamicForm/form.component.html` fieldtype 4). The `store_setting` fixture holds it at Yes with `switch_held` and restores it. `rate_restored` reads the saved Rate Selection first and writes it back if the test changed it.

## Screens (from source, not seen live)
| Thing | What and locator | Source |
|---|---|---|
| Router | `/other/onlinestore` → `/report/crm/E-Commerce/dashboard` (store) or `/other/createStore` (none) | `Component/Online-Store/dashboard/onlineStoreDashboard.ts:69-87` |
| Create store banner | heading "CREATING ONLINE STORE", button "Create Store" | `Component/Online-Store/app-onlinestore.component.html:647-649` |
| Create store form | heading "Store Details"; tabs (role tab) "Marg Mart", "Online Store"; fields by `formcontrolname` (labels have no `for`); radio `#wholeday`; day checkboxes `formcontrolname=Monday..Sunday` | `app-onlinestore.component.html:26,29,45,62-163,180-187,326-358` |
| Menus | top-level "Online Store" (menumaster id 5467); Sale > "Online Order" | pack; `AlterMainDBData.xml:484` |
| Order dashboard | h1 "Online Store Dashboard"; buttons "Switch to MargMart"/"Switch to Online Store", "Create QR code", "Copy Store Link"; link tile "Manage Item" | `Component/Master/E-Commerce/order-dashboard.component.html:6,528,555,598,662` |
| Filters | selects in the form groups labelled "Order Status" (All/Pending/Converted/Order Rejected) and "Vendor Type" (All/Shopify/Amazon/Flipkart, default Shopify) | `.html:704-731`; `.ts:1461-1466` |
| Grid | ag-Grid 19 `#topGrid`, col-ids `orderDate`, `customerName`, `orderNo`, `statusCaption`, `totalOrderQty`, `orderAmount`; row button "Convert" | `.ts:440-458`; `Component/Shared/action.component.ts:221,533-545` |
| QR overlay | `.qr-popup`, heading "Scan QR Code", img "QR Code" (src `api.qrserver.com/...&data=<url>`), button "Close" | `.html:536-547`; `.ts:1724-1734` |
| Item list | heading "Item List", button "Upload Item" (disabled with nothing ticked) | `Component/Online-Store/ProductList/OnlineStoreProductList.component.html:6-42` |
| Store Setting window | Control Room > Configure > search "Store Setting" > row button "Configure"; dialog with h4 "Store Setting", columns S.No./Particulars/Action/Help, one row "Rate Selection" with a select; × button; no footer | `form.component.ts:3431-3432`; `Component/Master/OlineStoreSetting/online-store-setting.component.html:1-16,180-218` |
| Store Configuration panel | header Control Room `#aControlRoomSetting` on the dashboard; h2 "Store Configuration"; `.itemTitle` "Rate Selection" with options M.R.P, Rate A..H | `Layout/homelayout.component.ts:1631-1632`; `UtililityComponent/ControlRoom/onlineStore.ControlRoom.Config.html:119-147` |
| Messages | toast "Link Successfully copy to clipboard" (notifier) | `order-dashboard.component.ts:1394` |

## Tests (73 collected; 2 `permanent`)
| Test | Scenario | Asserts |
|---|---|---|
| `test_store_entry.py::test_store_menu_without_a_store_offers_to_create_one` | OS-01 | banner "CREATING ONLINE STORE" + "Create Store" |
| `test_store_entry.py::test_create_store_offers_both_store_kinds[2 tabs]` | OS-01 | tab "Marg Mart" / "Online Store" |
| `test_store_entry.py::test_sale_online_order_opens_the_order_dashboard` | OS-02 | URL `/report/crm/E-Commerce/dashboard` |
| `test_store_entry.py::test_store_name_is_prefilled_with_the_company_name` | OS-03 | Store Name = `SelectedCompany.compname` |
| `test_store_entry.py::test_working_hours_default_to_whole_day_nine_to_seven` | OS-03 | Whole Day, 09:00, 19:00 |
| `test_store_entry.py::test_working_days_default_to_monday_to_saturday` | OS-03 | Mon-Sat ticked, Sunday not |
| `test_store_setting.py::test_store_setting_window_has_the_settings_columns` | OS-08 | S.No., Particulars, Action, Help |
| `test_store_setting.py::test_store_setting_window_offers_only_rate_selection` | OS-08, OS-13 | rows == ["Rate Selection"] |
| `test_store_setting.py::test_rate_selection_offers_mrp_and_rates_a_to_h` | OS-09 | M.R.P, Rate A..Rate H |
| `test_store_setting.py::test_chosen_rate_is_kept_after_saving_the_control_room` | OS-10 [S] | M.R.P after save + reload (MBC-2591 says it was not saved) |
| `test_store_setting.py::test_store_setting_window_has_no_save_button` | OS-12 | no Save button (records today's state, see N4) |
| `test_store_setting.py::test_store_setting_window_closes_with_escape` | OS-12 | window hidden |
| `test_store_setting.py::test_store_setting_window_closes_with_the_cross` | OS-12 | window hidden |
| `test_order_dashboard.py::test_seeded_order_is_listed_with_its_figures` | OS-15 | date dd-mm-yyyy, customer, Pending, qty 2, amount 251.00 |
| `test_order_dashboard.py::test_vendor_type_filter_starts_on_shopify` | OS-16 | default "Shopify" |
| `test_order_dashboard.py::test_seeded_order_is_hidden_by_the_default_vendor_filter` | OS-16 | 0 rows for our order |
| `test_order_dashboard.py::test_order_status_filter_lists_only_matching_orders[7 cases]` | OS-17 | listed / not listed per status filter |
| `test_order_dashboard.py::test_own_store_offers_the_switch_to_marg_mart` | OS-36 | "Switch to MargMart" visible |
| `test_order_dashboard.py::test_copy_store_link_confirms_the_copy` | OS-34 | toast text |
| `test_order_dashboard.py::test_qr_code_overlay_opens_and_closes` | OS-35 | "Scan QR Code" shown, hidden after Close |
| `test_order_dashboard.py::test_qr_code_points_at_a_public_store_url` | OS-35, KB vs live 4 | QR target host is not localhost (**expected to fail: D1**) |
| `test_order_dashboard.py::test_store_configuration_panel_offers_mrp_and_rates_a_to_h` | OS-14 | M.R.P, Rate A..H |
| `test_order_dashboard.py::test_store_configuration_panel_hides_unsupported_options[5]` | OS-13 | none of the five captions in the panel |
| `test_order_dashboard.py::test_upload_item_needs_a_ticked_item` | OS-30 | "Upload Item" disabled (see K1) |
| `test_order_conversion.py::test_convert_opens_a_sale_bill_with_the_order_quantity` | OS-18 | `/transaction`, row 0 qty = 2 |
| `test_order_conversion.py::test_saved_conversion_marks_the_order_converted` | OS-19 | status "Converted" |
| `test_order_conversion.py::test_saved_conversion_leaves_the_pending_view` | OS-19 | not under Pending (MB-037180) |
| `test_store_creation.py::test_saving_the_online_store_tab_creates_the_store` | OS-04 **permanent** | dialog "Store Created Successfully..." then the dashboard |
| `test_store_creation.py::test_store_form_with_a_missing_or_malformed_field_is_not_saved[4]` | OS-05 stubbed | no `SaveOnlineStore` call for blank name / mobile / email or GSTIN "12ABC" (**expected to fail**: no validators) |
| `test_store_creation.py::test_failed_store_save_says_the_store_was_not_created` | OS-06 stubbed | stub answers status 500; toast "Store not Created" (**expected to fail: D4**) |
| `test_store_creation.py::test_marg_mart_save_opens_the_margmart_registration` | OS-07 stubbed | BSS, `MargMart/Save` and margmart.com stubbed; new tab URL `https://margmart.com/vendor/#/registration?value=...&utm_source=MARGBOOKS` |
| `test_conversion_rules.py::test_converted_bill_total_equals_the_order_amount` | OS-20 | invoice value = 251.00 |
| `test_conversion_rules.py::test_converted_order_offers_no_second_conversion` | OS-21 | no "Convert" on a Converted order (**expected to fail: D3**; asserts the "refused" form) |
| `test_conversion_rules.py::test_unsaved_conversion_does_not_update_the_order_status` | OS-22 | 0 `StatusUpdationOfOnlineStore` calls while the bill is open (temp-saves) |
| `test_conversion_rules.py::test_saving_the_conversion_updates_the_order_status_once` | OS-22 | exactly 1 call on the first save |
| `test_conversion_rules.py::test_resaving_the_converted_bill_posts_no_second_status_update` | OS-22 | Modify + save works, 0 calls (MBC-5415) |
| `test_conversion_rules.py::test_conversion_without_the_online_store_ledger_says_so` | OS-23 stubbed | ledger lookup stubbed empty; toast "Transaction data not found !" (skips if the session already holds the ledger) |
| `test_conversion_rules.py::test_converted_bill_keeps_the_customer_mobile` | OS-24 | header "Mobile No." = order mobile |
| `test_conversion_rules.py::test_customer_with_a_known_mobile_is_billed_to_that_ledger` | OS-25 | party = the QA ledger with that mobile |
| `test_conversion_rules.py::test_conversion_with_a_deleted_line_still_marks_the_order_converted` | OS-38 | two-line order, line 2 deleted, saved: status "Converted" |
| `test_order_figures.py::test_order_amount_is_shown_with_two_decimals[4]` | OS-26 | qty 1, 9999; price 0.01, 33.33: Amount text = total with 2 decimals |
| `test_order_figures.py::test_order_below_any_minimum_amount_is_accepted` | OS-27 | a 0.01 order is listed |
| `test_store_tenancy.py::test_order_of_one_company_is_not_listed_for_another` | OS-28 | not on PHARMA_COMPANY's dashboard (skips without its own store) |
| `test_store_tenancy.py::test_other_company_cannot_change_the_status_of_an_order` | OS-29 | status update replayed with the other company's headers; order still Pending (**expected to fail**, `OnlineStore.cs:570`) |
| `test_store_catalogue.py::test_item_price_is_captioned_with_the_chosen_rate` | OS-11 [S] | Rate B chosen: Edit Product price caption "Rate B" |
| `test_store_catalogue.py::test_item_price_follows_the_chosen_rate` | OS-11 [S], KB vs live 11 | M.R.P chosen: price = item M.R.P |
| `test_store_catalogue.py::test_upload_asks_to_confirm_the_number_of_items` | OS-31 | "Do you really want to upload 1 item(s)?" (answered No) |
| `test_store_catalogue.py::test_confirmed_upload_sends_the_ticked_item` | OS-31 stubbed | body `itemlinkids` = [our item]; toast "Item(s) uploaded successfully" |
| `test_store_catalogue.py::test_uploaded_item_is_counted_as_mapped` | OS-31 **permanent** | "Mapped Item (n)" rises by 1 |
| `test_store_catalogue.py::test_unmap_needs_a_ticked_item` | OS-32 | "Un-Map Item" disabled (pack toast unreachable, as K1) |
| `test_store_catalogue.py::test_confirmed_unmap_reports_success` | OS-32 stubbed | unmap question; toast "Item(s) unmapped successfully" |
| `test_store_catalogue.py::test_confirmed_hide_reports_success` | OS-32 stubbed | hide question; toast "Item Hide Successfully" |
| `test_store_catalogue.py::test_marg_mart_upload_reports_the_uploaded_count` | OS-33 stubbed | margmart import + `Item/UploadMargMartItemdata` stubbed; toast "1 Products successfully uploaded" (skips without a Marg Mart store) |
| `test_store_catalogue.py::test_marg_mart_upload_over_the_plan_limit_says_limit_reached` | OS-33 stubbed | import refused; toast "Limit Reached" |
| `test_store_access.py::test_limited_user_is_denied_the_online_store[2]` | OS-37 | `operator` login denied `/other/createStore` and the dashboard (skips without operator credentials) |

## Defect candidates (from source, to confirm live)
- D1 (OS-34/35): copy-link and QR build `http://localhost:4200/?site=<base64{complinkid,dbinfolinkid}>` and send it to the third-party `api.qrserver.com` (`order-dashboard.component.ts:1383-1395, 1724-1734`). The QR test asserts the pack's expected value (a public store URL) and should fail.
- D2 (OS-16): `GetSavedOrders` returns no `vendortype`, but the Vendor Type filter starts on Shopify and filters on it (`.ts:1497-1500`): orders from the own store are hidden until the user picks All.
- D3 (OS-21, not scripted): the "Convert" button also shows on a Converted order: `+"Converted"` is NaN, so `action.component.ts:538-545` falls through to "show Convert". A second bill can be made from one order.
- D4 (OS-06, not scripted): `if (res.status = "200")` assigns, so a failed `SaveOnlineStore` still says "Store Created Successfully" (`app-onlinestore.component.ts:723-724`).
- D5: with no orders at all, `GetStoreDataForOnlineStore` reads `OnlineSaveRes.Data[0].linkid` and throws (`.ts:1489`). The first seeded order hides this.

## NEEDS DECISION
- N1: does GANE29 (or another suite company) have an own Online Store? OS-01/03 need a company with **no** store and the dashboard tests a company **with** one. Creating a store is permanent. Proposal: keep GANE29 without a store and have a human create an own Online Store once on PNC2 (Pharma New Company 23-09), then pin the dashboard fixtures to PNC2.
- N2: seeded orders cannot be deleted (no API). Each run leaves about 12 `QA-<run_id>` orders on the company's dashboard (Pending ones stay Pending). Accept, or ask for a cleanup endpoint or DB job?
- N3 (OS-09): the window's option list is built from `DefaultBillingRate` minus ids 1, 2, 4 (`online-store-setting.component.ts:67-70`). The captions may follow the company's own rate captions instead of "Rate A..H". The test asserts the pack's captions.
- N4 (OS-12): no Save button in the window and only Rate Selection offered (MB-34343, MBC-2591). Is this a defect or the intended state? The test records today's state.
- N5 (OS-17): the count tile ("<status> Order") is not asserted against the grid's row count. Seeded orders pile up (N2) and ag-Grid renders only visible rows, so the row count is not reliable.

## KB / pack vs source
- K1 (OS-30): the pack expects the toast "Please select at least one item to upload.". In the template the button is disabled while nothing is ticked, so the toast cannot be reached. The test asserts the disabled button.
- K2 (OS-01): the pack says the router opens the tabs directly. The source shows the "CREATING ONLINE STORE" banner first, then the tabs after "Create Store".
- K3 (OS-02): the Sale > Online Order menu move (MBC-17953) was To Do in the KB. If the entry is missing live, that is the reason.
- K4 (OS-02/OS-14): the dashboard `Platform` select and the Marg Mart card are unused in own-store mode.

## Not automated (and why)
None. Every pack scenario (OS-01..OS-38) is scripted; no scenario of this journey is desktop-only or needs a physical device.

Partly covered (noted, not separate scenarios): OS-26's decimal quantity cannot be seeded (`quantity` is an int); OS-33's item-image upload is not asserted; OS-29 lives in `tests/journeys/` instead of `tests/api/` because the `api` fixture cannot sign in to the Online Store API (encrypted per-session headers, see `order_api.py`).

New open points from scripting:
- N6: `known_customer` (OS-25) leaves a QA ledger behind; the suite has no ledger-delete page object.
- N7: OS-11 changes the tenant's Rate Selection (restored by `rate_restored`, xdist group `chemist-tenant`).
- N8: OS-23 relies on a fresh page having no ledger list in memory; if the session already holds fixedID 83 the test skips.
- N9: OS-37 assumes the `operator` role has no Online Store / Sale rights.

## To verify live (first run)
| Inferred | Source |
|---|---|
| `/other/onlinestore` redirects in under 60 s to createStore or the dashboard | `onlineStoreDashboard.ts:69-87` |
| banner heading "CREATING ONLINE STORE" and button "Create Store" | `app-onlinestore.component.html:647-649` |
| heading "Store Details" after Create Store; tabs have role tab | `app-onlinestore.component.html:26,29,45` |
| `[formcontrolname=storeName]`, `WholeDayStartTime`, `WholeDayEndtTime`, day checkboxes; values "09:00"/"19:00" (ngx-mat-timepicker may format differently) | `app-onlinestore.component.html:64,200-213,326-358`; `.ts:166-202` |
| `#wholeday` radio | `app-onlinestore.component.html:180` |
| Store Name prefill equals localStorage `SelectedCompany.compname` | `app-onlinestore.component.ts:166` |
| top-level "Online Store" is a `li.grandParent > a`; Sale > "Online Order" is a parent link | pack; `pages/purchase/documents/navigation.py` |
| h1 "Online Store Dashboard" | `order-dashboard.component.html:6` |
| buttons "Switch to MargMart"/"Switch to Online Store", "Create QR code", "Copy Store Link" | `.html:528,555,598` |
| filters found via `.form-group` + label text; option labels | `.html:704-731` |
| `#topGrid` rows have role row, cells col-id = field | `.html:747`; `.ts:440-458` |
| row button "Convert" | `Shared/action.component.ts:221` |
| `.qr-popup`, heading "Scan QR Code", img alt "QR Code", button "Close" | `.html:536-547` |
| link "Manage Item" opens Item List; button "Upload Item" disabled | `.html:651-664`; `OnlineStoreProductList.component.html:6-42` |
| Control Room: search "Store Setting" finds one `.row.m-0`; its select options are "Yes"/"No"; "Configure" shows when Yes | `form.component.html:150-170`; `ControlRoomDesignData.cs:1361` |
| dialog role with h4 "Store Setting"; × button name "×"; columnheaders; tbody rows | `online-store-setting.component.html:1-16` |
| Control Room Save `#btn-x` + two `#btnYes` persist the Rate Selection (MBC-2591 says no) | `pages/settings/control_room.py`; `online-store-setting.component.ts:90-104` |
| dashboard Control Room shows h2 "Store Configuration" in `.itemControl`, `.itemTitle` row | `controlroom.setting.component.html:5-15,144-145` |
| toast "Link Successfully copy to clipboard" is a notifier toast | `order-dashboard.component.ts:1394`; `Globals/alertbox.ts:38-50` |
| `GetSavedOrders` is called when the own-store dashboard opens; replaying its headers on `SubmitOrder` and `GetItemListForMapping` is accepted | `order-dashboard.component.ts:1480`; `LoaderInterceptor.service.ts:47-73` |
| `SubmitOrder` answers `{"status": "200"}`; `GetItemListForMapping` answers `{status: {status: "1"}, Data: [{linkid, Product}]}` | `margerpdal/OnlineStore.cs:291-292`; `OnlineStoreProductList.component.ts:118-128` |
| grid Amount is a plain number ("251" or "251.00"; ag-Grid ignores `cellFilter`) | `.ts:447` |
| conversion opens `/transaction`; item grid row 0 col-id `unitToEnteredValue` holds the qty; bill saves with `SaleBillDocument` | `.ts:891-914`; `pages/sale/documents/item_grid.py` |
| order status becomes "Converted" after the bill's first save | `processout.transaction.component.ts:11986-11988`; `OnlineStore.cs:570` |
| create-store Save found by title "Save" (`#btn-Save`, caption span may be hidden); tabs clickable by role tab | `app-onlinestore.component.html:519-566, 26-29` |
| "Store Created Successfully..." is a Confirmation dialog (AlertEnum.Confirmation); "Store not Created" a notifier toast | `app-onlinestore.component.ts:725-729`; `Globals/alertbox.ts:31-50` |
| Marg Mart Save calls `Util/Compress` (real), then BSS `GetMargmartData`, `MargMart/Save`, then `window.open` margmart.com | `app-onlinestore.component.ts:289-325` |
| BSS stub reply shape `Details.PageDetails{...}` is enough for the next step | `app-onlinestore.component.ts:296-318` |
| Confirmation dialogs (upload, unmap, hide, delete line) have heading "Confirmation" and Yes/No buttons as `ConfirmDialog` expects | `Globals/alertbox.ts:37-41`; `pages/components/confirm_dialog.py` |
| item list: placeholder "Search...", radio "Mapped Item (n)", tbody rows with a checkbox, link title "Edit Product", hide link = last link of the row | `OnlineStoreProductList.component.html:71, 85-87, 149, 209, 217` |
| Edit Product window is a dialog; `#price` in a `.form-group` whose `.label` is the rate caption | `ItemList/OnlineStoreImageEdit.html:41-48` |
| `InsertOnlineStoreItems` body `{itemlinkids: [...]}`; `HideItemFromOnlineStore` answers `{status: "200"}` | `OnlineStoreProductList.component.ts:221-270` |
| Marg Mart Manage Item: rows have a mat-checkbox (role checkbox) next to the product text; upload needs a "MargMartToken" in storage | `ItemList/OnlineStoreItemList.html:12-24,137`; `OnlineStoreItemList.ts:376-420` |
| Marg Mart import URL `importproduct.margmart.com/.../erp-product-import`; reply `{status:"1", data:{data:[...]}}` | `MrgHttpService.service.ts:880-886`; `OnlineStoreItemList.ts:745-777` |
| `Ledger/GetLedgerTranMultiList` is called on Convert when the session has no ledger list | `order-dashboard.component.ts:756-776` |
| converted bill: `.bill-value-text`, header "Party Name" and "Mobile No." (mobile row only for chemist / Customer Name on) | `UI/Transaction/InverntoryTransaction/processout.transaction.component.html:222-228` |
| deleting a bill line: click the line's amount cell, Delete, confirm "Do you want to delete this Item- ...?" | `processout.transaction.component.ts:9385-9400, 15234-15238` |
| Sale > Bill list row action "Modify" reopens a saved bill | `pages/sale/documents/screen.py` row_action |
| `GetSavedOrders` is a GET; its Data rows carry `linkid` and `storeorderid`; `StatusUpdationOfOnlineStore` takes `{linkid, convertedBillLinkid}` | `MrgHttpService.service.ts:37-52`; `order-dashboard.component.ts:1486-1515`; `processout.transaction.component.ts:22088-22094` |
| `operator` is denied `/other/createStore` and the order dashboard | none (checklist) |
