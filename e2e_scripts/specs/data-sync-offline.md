# Plan: J35 Data sync / offline (data-sync-offline)

Scenario pack: `scenarios/data-sync-offline.md`. Tests: `tests/journeys/data_sync/` (`test_connection_loss.py`, `test_internet_speed.py`, `test_data_sync_screen.py`, `test_forced_logout.py`, `test_offline_guards.py`, `test_lost_saves.py`, `test_request_states.py`, `test_throwaway_requests.py`, `test_offline_start.py`, `conftest.py`) and API tests `tests/api/data_sync/test_sync_request_api.py` (+ `conftest.py`). Page objects: `pages/data_sync/` (`connection.py`, `internet_speed.py`, `maintenance_page.py`, `data_sync_screen.py`, `data_sync_form.py`, `menu.py`, `offline_bill.py`, `request_log.py`, `offline_guards.py`, `help_links.py`, `sale_list_sends.py`, `saved_bill_print.py`, `gst_verification.py`, `lost_save.py`, `sync_status_stub.py`, `transaction_lock.py`, `throwaway_company.py`, `offline_login.py`, `sync_api.py`); test data `test_data/data_sync.py` (throwaway company name). Shared change: `pages/components/footer.py` now exposes `save_button` (behaviour of `save()` unchanged).

**Status: DRAFT — locators from Angular source, NOT yet verified live.** Written offline on 2026-10-13: no browser was opened and no test reached the app (no login available). Every locator, text and endpoint below comes from `newmarg-webangular20` (cited `file:line`) and the KB, and must be checked by the first live run (see "To verify live").

Priority marker: `pytest.mark.p3` (J35 is P3 in the matrix; `p3` is registered in `pyproject.toml`). Module mark: `pytest.mark.journey("data-sync-offline")`; API module also `pytest.mark.api`. 45 tests collect (39 browser, 6 API); 3 are `permanent` (DS-18, DS-19, DS-45), skipped unless `--allow-permanent`.

## Scope
Only the web app (isElectron 0) in a browser: connection-loss handling (DS-01..DS-07, DS-13, DS-26, DS-48) and the read-only Data Sync request screen (DS-14..DS-17, DS-23, DS-24). Second pass: the API rows (DS-31, DS-44..DS-46, DS-19 re-enable) are API tests on the DataSync host; the rows that need the Electron EXE stay in "Not automated" (desktop app only). The journey name says "(Electron app)"; see the pack's KB vs live item 11 (suggest splitting J35).

Connectivity is switched with `BrowserContext.set_offline(True/False)`: `ng-connection-service` 1.0.4 listens only to the window `online`/`offline` events (`node_modules/ng-connection-service/fesm2015/ng-connection-service.js:11-14`), which this fires. Service workers are blocked for every context by the root `conftest.py`, so `page.on("request")` sees every call (the J21 finding).

## Preconditions and test data
- Second pass (2026-10-13, offline): every remaining scenario was re-checked against the Angular and .NET source. Guards behind the overlay are reached with the pack's test-only DOM tweak (`offline_guards.lift_overlay` hides `div.locked-screen` after it was shown; the browser stays offline). A context-wide `SendGuard` (`OUTSIDE_CALLS`: care portal, WhatsApp host, bill upload, e-mail, GST lookup) aborts any send or third-party call and fails the test. Tests that may end on `/error` (logout) use `own_login_page`.
- Request states (DS-19 confirm, DS-20, DS-21) are stubbed in the browser with `SyncStatusStub` (page route on `SyncRequeststatus`, keyed by complinkid), so no QA company gets a real request.
- Throwaway company **"QA Data Sync Throwaway"** on the chemist login (`test_data/data_sync.py`) for DS-18, DS-19, DS-45 and the DS-19 re-enable API check; looked up at run time, skip with the DS id when missing or in the wrong state. Must be created by hand.
- DS-22 uses the `operator` role account (skips without credentials). DS-25 uses `service_worker_page`, a form login in its own context with `service_workers="allow"` (skips if no worker registers).
- API tests call the DataSync host `https://onlineofflinesyncservices.premargbooks.com/v1.1/` (`environment.preprod.ts:50`, `global.ts:18270`), checked with `is_allowed_target` before use; the actions have no `[Authorize]`, so no login.
- Account `chemist` (as J22 and the sales journey).
- `layout_page`: the worker's shared session, company pinned to **Garments New 29-08** with `CompanySwitchPage.ensure_company` (as `tests/journeys/dashboard/conftest.py`). Going offline affects only the test's own browser context; the fixture goes online again in teardown.
- `sale_bill_page`: the same shared session pinned to **Pharma New Company 23-09**, because the bill used is the sales journey's stored case TC_SM_009 (item 3, batch BATCH001; `pages/sale/documents/flows.py`). The bill is filled, never saved (DS-04 sends nothing; DS-05..07 lose the save offline).
- `own_login_page`: **forced-logout isolation.** `/error` sends the app to `/login`, and the login screen's `ngOnInit` calls `commonService.logoutdata(SessionId)` (server `Logout`) and `clearLocalStorage(true)` (`login.component.ts:336-343`, `Common.service.ts:1455-1479`). Doing that in the shared `page_as` session would end the server session every later test of the worker restores. So DS-05, DS-06, DS-07 and DS-24 sign in through the login form in a fresh plain context (pytest-playwright `page`, as `tests/journeys/auth/test_login.py` does), with the worker's own user (`settings.credentials(account, worker_index(worker_id))`), and only that form session is logged out. Missing credentials skip locally and fail in CI (`report_missing_credentials`).
- `test_internet_speed.py` holds Control Room **"Show Internet Speed"** (`ControlRoomDesignData.cs:417`, care portal `careportal_enriched_v5.csv#ec34efb4`) at the value each test needs with `switch_held` (reads the original first, writes only if different, restores and re-reads even on failure; restore starts online from the dashboard). Tenant-wide, so the module is in xdist group `chemist-tenant` (CLAUDE.md rule 0).
- DS-13 does not throttle the network: whether CDP emulation changes `navigator.connection.downlink` is unverified (pack DS-13), and the real value depends on the machine. `ReportedDownlink` replaces only `navigator.connection` (init script) with a fixed `downlink` (1 Mb/s slow, 50 Mb/s fast); the layout's own speed logic is what is tested.
- Nothing is created or saved on the tenant. Enable Data Sync and Cancel are never pressed online.

## Screens (from source, none seen live)
| Thing | What and locator | Source |
|---|---|---|
| Offline overlay | root component, all routes incl. login: text "No internet connection found." + "Check your connection or try again.", fixed, z-index 500000000; shown when isElectron 0 and isAzure 1 (preprod isAzure 1) | `app.component.ts:29-35`, `:108`, `:141-158`; `environment.preprod.ts:2,36` |
| No-wifi header icon | `div.icn` svg viewBox `0 0 365.892 365.892`, no name (CSS, see comment) | `homeLayout.component.html:487-498` |
| Speed widget | "<n> Mb/s" text + wifi bars (path fill `lightgreen`/`yellow`/`red`), only when `!noInternetConnection && isWifiShow`; `d-none d-lg-block` (needs ≥ 992 px wide) | `homeLayout.component.html:509-529`; `homelayout.component.ts:771-786`, `:1096` |
| Slow banner | "Slow internet connection. Please check your internet setting" when class `red` (0 < downlink < 2) | `homeLayout.component.html:1-10` |
| Maintenance page | `/error` (public): heading "Website Under Maintenance", "We're Sorry! Web site is down for maintenance"; on load calls a user-detail API and on success goes to `/login` | `errorpage.component.ts:17-20`, `:53-65`; `app-routing.module.ts:183` |
| Status-0 handler | "0 Unknown Error" on the web (`isOnlineOffline` 0) → `navigateByUrl('/error')` | `MrgHttpService.service.ts:467-479`; `environment.preprod.ts:38` |
| Data Sync screen | `/other/datasyncreport`: h1 "Data Sync", "Currently logged in with the following Email:" + company e-mail, "Report Date: dd-MM-yyyy", strip with status text and buttons "Enable Data Sync" / "Cancel"; grid, Add, Refresh, Upload only in Electron; host element `app-data-syncreport` | `data-sync.Reportcomponent.html:8-149`; `data-syncreport.component.ts:49-58`, `:200-226` |
| Strip calls | `OfflineOnline/SetGetdatasyncsetting` then, only if it answers 0, `OfflineOnline/SyncRequeststatus`; request `OfflineOnline/SyncRequestsave` (DataSync host `onlineofflinesyncservices.premargbooks.com`, preprod) | `data-syncreport.component.ts:200-232`, `:237-253`; `global.ts:18264-18280`; `environment.preprod.ts:50` |
| `/datasync` | public; `form#dataSyncForm` inside a `[hidden]="!isElectron"` block; title "Online Data Sync From Server" | `data-sync.component.html:2-12`, `:84`; `app-routing.module.ts:191` |
| Menu | Utilities & Tools > Other Tools; "DataSync Details" row `isactive 0`; "Multi Editing" in the same sub-menu | `menumaster.json:5905-5917`, `:6392-6400`; KB `onedrive_processed_data.csv#61d9a9e6` |
| Sale bill save | footer span "Save" (pointer); End (keyboard) → save window `.frameModal` button "save"; API `BillSales/Save` (or `TempBillHold/Save` for a held bill) | `pages/sale/documents/bill.py`, `document.py:135-142`; `global.ts:755`, `:774`; `processout.transaction.component.ts:11578-11586` |

## Tests
| Test | Scenario | Asserts |
|---|---|---|
| `test_connection_loss.py::test_going_offline_covers_the_screen_with_the_no_internet_overlay` | DS-01 | overlay title and hint visible |
| `::test_going_online_again_removes_the_overlay_without_a_reload` | DS-02 | overlay hidden after online; a `window` mark set before survives (no reload) |
| `::test_offline_header_shows_the_no_wifi_icon` | DS-03 | no-wifi icon visible |
| `::test_offline_click_on_save_reaches_the_overlay_and_sends_no_bill` | DS-04 | real pointer click on Save while offline; after reconnecting the bill is still open and no `BillSales/Save` request was started |
| `::test_overlay_covers_the_login_screen_too` | DS-26 (part) | overlay on the login screen (plain context, no session) |
| `test_internet_speed.py::test_speed_widget_shows_a_reading_when_the_setting_is_on` | DS-48 (on) | "<n> Mb/s" visible |
| `::test_speed_widget_and_banner_are_absent_when_the_setting_is_off` | DS-48 (off) | header drawn (version label), no reading, no banner |
| `::test_offline_header_hides_the_speed_widget` | DS-03 | setting on: reading shown, then gone offline |
| `::test_link_below_two_megabits_shows_the_slow_internet_banner` | DS-13 | downlink 1 → red banner within one 5 s cycle |
| `::test_fast_link_shows_no_slow_internet_banner` | DS-13, DS-48 | downlink 50 → light-green bars, no banner (false-positive tickets MB-36053, MB-14241) |
| `test_data_sync_screen.py::test_screen_shows_company_email_and_todays_report_date` | DS-14 | caption followed by an e-mail; "Report Date:" today dd-MM-yyyy |
| `::test_screen_offers_no_electron_grid_or_upload` | DS-14 | no `ag-grid-angular`, no "Particulars Name", no Add/Refresh/Upload button |
| `::test_request_strip_shows_exactly_one_request_state` | DS-16 | exactly one of pending / approved / cancelled / no request (+ Enable) |
| `::test_other_tools_menu_does_not_list_data_sync_details` | DS-15 | Multi Editing visible, DataSync Details absent |
| `::test_offline_enable_data_sync_asks_for_internet_and_sends_nothing` | DS-17 | offline, Enter on Enable → "Internet Required for this option!", no `SyncRequestsave` request. Skips (with the DS id) when the company already has a request, because Enable is then not offered and Cancel is never pressed |
| `::test_public_data_sync_route_keeps_its_electron_form_hidden` | DS-23 | `form#dataSyncForm` attached but hidden; title hidden |
| `test_forced_logout.py::test_offline_keyboard_save_shows_the_maintenance_page` | DS-05 | own login; offline End-save → `/error` with "Website Under Maintenance" (see D1) |
| `::test_reconnecting_on_the_maintenance_page_logs_the_user_out` | DS-06 | online + reload → `/login`; `/dashboard` then lands on login (session ended) |
| `::test_lost_bill_save_is_not_retried_after_reconnecting` | DS-07 (part) | no `BillSales/Save` request from reconnect to `/login` |
| `::test_opening_the_error_route_while_signed_in_logs_the_user_out` | DS-24 | own login; `/error` shows maintenance, goes to `/login`, session ended |
| `test_offline_guards.py::test_offline_care_portal_link_asks_for_internet` | DS-09 | Help window opened online; offline, overlay lifted, "Visit portal" → "Internet Required for this option!", no new tab |
| `::test_offline_drug_helpline_asks_for_internet_and_stays` | DS-09 | pharma; skips without the Drug Helpline link; warning, not on `/pharmanxt` |
| `::test_offline_upload_bills_asks_for_internet` | DS-10 | own login, pharma list, one bill ticked; Upload → warning; guard: nothing sent |
| `::test_offline_email_of_a_listed_bill_asks_for_internet` | DS-10 | Alt+E → warning (source may reach `/error` first, see corrections) |
| `::test_offline_whatsapp_of_a_listed_bill_asks_for_internet` | DS-10 | Alt+W → warning |
| `::test_offline_whatsapp_from_a_saved_bill_asks_for_internet` | DS-11 | stored bill saved online, print window "Whatsapp" offline → warning; bill deleted after |
| `::test_offline_gstin_fetch_leaves_the_ledger_form_for_manual_entry` | DS-12 | own login; GST Verification, F10 offline → ledger name still editable, not on `/error` (D3) |
| `test_lost_saves.py::test_lost_offline_save_does_not_use_up_the_bill_number` | DS-07 (number) | number before offline save == next bill's number after re-login (N3) |
| `::test_save_with_a_dropped_answer_leaves_at_most_one_bill` | DS-08 | save reaches server (`route.fetch`), answer aborted; after re-login ≤ 1 bill with that number; cleaned up |
| `::test_saving_again_after_a_dropped_answer_does_not_duplicate_the_number` | DS-08 | re-save after re-login; still ≤ 1 bill with the first number; both cleaned up |
| `test_request_states.py::test_approved_request_locks_new_sale_bills` | DS-20 | stub "approved" for pharma; Create/F2 on sale list → "Transaction locked after datasync", no bill form |
| `::test_cancel_asks_for_confirmation_before_sending` | DS-19 (confirm) | stub "pending"; Cancel → confirmation text, No → still pending; `SyncRequestsave` guarded |
| `::test_other_company_shows_its_own_request_state` | DS-21 | pharma "approved"; switch to garments → strip shows no request + Enable |
| `::test_lock_of_one_company_does_not_reach_another` | DS-21 | garments "approved"; switch to pharma → Create/F2 opens the bill form |
| `::test_limited_user_reaches_the_data_sync_screen_by_url` | DS-22 | operator role; screen opens (source: no rights check, UNVERIFIED) |
| `test_throwaway_requests.py::test_enable_data_sync_sends_a_pending_request` | DS-18 | **permanent**; throwaway, no request → "Request has been accepted!", pending + Cancel |
| `::test_cancelling_a_pending_request_marks_it_cancelled` | DS-19 | **permanent**; confirm text, Yes → cancelled text, no Enable |
| `test_offline_start.py::test_reload_while_offline_draws_the_app_shell_with_the_overlay` | DS-25 | SW allowed; offline reload → overlay shown |
| `::test_login_submitted_offline_ends_on_the_maintenance_page` | DS-26 (submit) | overlay; Enter submit with dummy credentials → `/error` (N4) |
| `tests/api/data_sync/test_sync_request_api.py::test_o2dm_user_check_refuses_a_blank_branch_code` | DS-31 | StatusCode 0, "Invalid branchcode" |
| `::test_request_save_refuses_a_zero_company_id` | DS-44 | statuscode 0, "branchlinkid" (D4) |
| `::test_request_save_refuses_a_zero_dbinfo_id` | DS-44 | statuscode 0, "Invalid DBInfolinkid" |
| `::test_request_status_of_a_company_without_request_is_201_with_no_data` | DS-46 | ids 0/0 → 201, data null |
| `::test_enabling_again_after_a_cancelled_request_is_refused` | DS-19 (re-enable) | throwaway cancelled → 401 "Invalid request" (no write) |
| `::test_sending_the_same_request_twice_is_answered_already_requested` | DS-45 | **permanent**; second save → 200 "Already requested", status pending |

## Defect candidates (expected value kept from the source; to confirm live)
- **D1 (DS-05/06/24, pack KB vs live 4, MB-7335):** a request lost to the network shows "Website Under Maintenance / Web site is down for maintenance" and, after reconnecting, the user is logged out with the unsaved bill lost. The tests assert this source behaviour; a human decides whether it is intended. If the decision is "defect", the expected values change (needs review, CLAUDE.md rule 8).
- **D2 candidate (DS-13 boundary, new, source only):** the speed class is set only for `0 < n < 2`, `2 < n < 6` and `n > 6` (`homelayout.component.ts:779-785`): a downlink of exactly 2 or 6 Mb/s (and 0) keeps the previous colour, so the widget can stay red at 2 Mb/s. Not asserted (expected value at the boundary unknown, see N2).

- **D3 candidate (DS-12, new, source):** GST Verification has no offline guard (`createledger.component.ts:4870-4905`); offline the encrypt call fails with status 0 and the source sends the app to `/error` (logout), while the pack expects a graceful error with manual entry. The test asserts the pack.
- **D4 candidate (DS-44, source):** `SyncRequestsave` with complinkid 0 answers the message "branchlinkid" (`OfflineOnlineController.cs:284-287`); asserted as the source has it.
- **DS-35 note:** `pushpull` answers "process" for every type, so the type-3 branch defect is not observable through the API.

## Corrections to the pack (code read for this plan)
- DS-06/DS-24: `errorpage.component.ts:63` calls `clearLocalStorage()` with no arguments, which clears nothing (`Helper.services.ts:450-506`: both flags default false). The session is actually ended by the login screen it navigates to (`login.component.ts:336-343`: server `Logout` + `clearLocalStorage(true)`). The visible outcome (on `/login`, signed out) is the same; the cause matters for the isolation above.
- DS-17: `SaveUpdateRequest` reads `navigator.onLine` (`data-syncreport.component.ts:238`), and Cancel asks for confirmation before that guard (`:187-193`), so only Enable reaches the guard directly.
- DS-10/11: Email and WhatsApp on the sale list first await `findManageInvoiceLayoutLinkId` / `getPrintTemplates` (`processout.list.component.ts:1305-1340`), which may call the API; offline that takes the status-0 path to `/error` before the guard. Upload Bills checks the guard first (`:1322-1327`).

## NEEDS DECISION
- N1 (D1): is "maintenance page + logout" the intended web reaction to a lost request?
- N2 (D2): what should the widget show at exactly 2 and 6 Mb/s?
- N3 (DS-07): the bill number "not consumed" part needs the number read before the offline save and compared after re-login; other sessions save on the same company, so a number check is unreliable (`premargbooks` quirk). Accept the "no retry" part only, or run it in a quiet window?
- N4 (DS-26): should the login form submit offline go to `/error` (pack, unverified)? Only the overlay is asserted.

## Not automated
| Scenario | Reason |
|---|---|
| DS-27 dashboard "Last Sync" | Covered by J22 (`tests/journeys/dashboard/test_dashboard_period.py`, DB-06) |
| DS-30 EXE `/datasync` sync with OTP | Desktop app only (the web build keeps the form hidden, DS-23 covers the web side) |
| DS-32 Data Sync Details grid | Desktop app only (grid and `getSyncDataFromLocal` are Electron-only, `data-sync.Reportcomponent.html`) |
| DS-33, DS-34 Upload online / offline | Desktop app only (Upload exists only in Electron) |
| DS-35 `pushpull?type=3` | Desktop app only: the endpoint is the EXE's local sync service (`Global.DataMigration`); on the cloud host it would run sync jobs for every tenant, and its answer ("process") does not show which jobs ran |
| DS-36..DS-39, DS-43, DS-47 | Desktop app only (bills saved / deleted / restored in the EXE and uploaded; licence and HO/branch sync run from the EXE) |
| DS-40 15 vs 16 offline days | Desktop app only (`PostLicense`, Electron licence file) |
| DS-41 local API stopped | Desktop app only (`openAlertforElectron`, `isElectron == 1`) |
| DS-42, DS-49 sign-up / login without internet | Desktop app only (the guards in `registration.component.ts:206-215`, `:268-273` run only when `isElectron == 1`) |

## To verify live (first run, healer)
- [ ] `pages/data_sync/offline_guards.py:18-22` the overlay is `margerpapp-root > div.locked-screen` and hiding it lets clicks through (`app.component.ts:29`).
- [ ] `pages/data_sync/help_links.py:28-40` Help link name "Help", "Visit portal" inside `div.help-window`, Drug Helpline title (`homeLayout.component.html:784-787`, `:841-842`, `:3088`, `:3180`); the Help window may need its slide-in to finish.
- [ ] `pages/data_sync/sale_list_sends.py:20-23` Upload button name "Upload", ag-Grid row check box class; Alt+E/Alt+W reach the list's keydown handler (`processout.list.component.ts:2080-2091`); whether Email/WhatsApp reach the guard or `/error` first.
- [ ] `pages/data_sync/saved_bill_print.py:19-23` print window host `trxn-print` opens after the save window; button "Whatsapp" (`trxnprint.component.html:81`); `GetSmsHistoryByuserID` offline may send the app to `/error` before the guard.
- [ ] `pages/data_sync/gst_verification.py:18-25` "GST Verification" button visible on a new ledger (`createledger.component.html:2605-2607`), window `form#gstForm` with heading, `input#gst`, F10 verifies.
- [ ] `pages/data_sync/lost_save.py:31-34` `route.fetch` then `route.abort("internetdisconnected")` leads to status 0 and `/error`; `SaleBillCount` finds the bill by number with the "This Week" filter.
- [ ] `pages/data_sync/sync_status_stub.py:59-73` the status call is a POST with JSON `{complinkid, dbinfolinkid}` and the app accepts the stubbed body (keys `statuscode`, `data.status`); the layout asks again after a company switch (if not, DS-21 lock test fails: possible leak defect).
- [ ] `pages/data_sync/transaction_lock.py:14-18` "Create/F2" on the sale list and the "Bill No." label of the new bill form.
- [ ] `pages/data_sync/throwaway_company.py:17` company list cell `[col-id="compname"]` (as `company_switch_page.py`).
- [ ] `pages/data_sync/offline_login.py:13-15` Enter in the password field submits the login form under the overlay.
- [ ] `pages/data_sync/sync_api.py:18-21` DataSync host and paths answer from outside the browser (CORS does not matter for httpx); key case of the answer body.
- [ ] `tests/journeys/data_sync/conftest.py` `service_worker_page`: the preprod build registers `ngsw-worker.js` and `navigator.serviceWorker.ready` resolves.
- [ ] `test_offline_guards.py` DS-12: the `/error` navigation may come after the ledger field check; review timing if it passes too early.
- [ ] `pages/data_sync/connection.py:13` overlay texts render and are "visible" to Playwright behind `position-fixed`.
- [ ] `pages/data_sync/connection.py:18` no-wifi icon CSS (`div.icn svg[viewBox=...]`) matches one element.
- [ ] `pages/data_sync/internet_speed.py:15` "Show Internet Speed" is a Yes/No option in Control Room > Configure (KB article text was cut before the value); `ControlRoomState.current_switch` can read it.
- [ ] `pages/data_sync/internet_speed.py:19-23` "<n> Mb/s" text, version label `V. x` and `path[fill="lightgreen"]`; the widget is `d-lg-block` only, so the viewport must be ≥ 992 px.
- [ ] `pages/data_sync/internet_speed.py:26` the `navigator.connection` override takes effect before `ngAfterViewInit` reads it, and `_binternetSpeed` is already "T" at that moment (`homelayout.component.ts:771`, `:1096`: the profiler arrives asynchronously; if it arrives later the widget never shows — that would be an app race, record it).
- [ ] `pages/data_sync/data_sync_screen.py:24-26` endpoint paths on the DataSync host; `open()` waits for `SetGetdatasyncsetting` (if the call is not made, `open()` times out).
- [ ] `pages/data_sync/data_sync_screen.py:30-36` e-mail line, `app-data-syncreport` host tag, button names "Enable Data Sync" / "Cancel" (text has line breaks in the template).
- [ ] `pages/data_sync/data_sync_screen.py:101` the 15 s status wait is enough and not too slow for the "no request" case.
- [ ] `pages/data_sync/data_sync_screen.py:86` focus + Enter on Enable while the overlay is shown triggers the click handler.
- [ ] `pages/data_sync/data_sync_form.py:17` `/datasync` builds when routed (it injects `NgbActiveModal`, `data-sync.component.ts:46`); if it does not build, DS-23 fails: record whether that is a defect.
- [ ] `pages/data_sync/menu.py:12-14` "Utilities & Tools" is a sidebar group and "Other Tools" a parent entry with "Multi Editing" as child.
- [ ] `pages/data_sync/offline_bill.py:20` the bill save endpoint (`componentFactoryType.apiUrl`) really is `BillSales/Save`.
- [ ] `pages/data_sync/offline_bill.py:35-41` the forced pointer click lands on the overlay (not on Save).
- [ ] `pages/data_sync/offline_bill.py:43-52` offline End opens the save window or goes straight to `/error`; Enter on its focused "save" button starts the request.
- [ ] `pages/data_sync/maintenance_page.py:16-20` heading role/name, and `/login` is the app route (not a separate login host) after `/error`.
- [ ] `tests/journeys/data_sync/conftest.py:62` a second form login of the worker's chemist user does not end the worker's `page_as` session (single-session rules); if it does, move these tests to a dedicated account.
- [ ] `test_forced_logout.py` DS-24: the maintenance heading may show only for the time the user-detail call takes; if `expect_shown` misses it, that is a timing question for a human to review (dropping the check would loosen the assertion, CLAUDE.md rule 8).
