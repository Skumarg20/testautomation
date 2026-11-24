# Plan: J41 Support / helpdesk (support-helpdesk)

Scenario pack: `scenarios/support-helpdesk.md`. Tests: `tests/journeys/support/` (`test_help_drawer.py`, `test_chat_now.py`, `test_ticket_list.py`, `test_ticket_tenancy.py`, `test_create_ticket.py`, `test_attachment.py`, `test_ticket_writes_stubbed.py`, `test_ticket_end_to_end_stubbed.py`, `conftest.py`). Page objects: `pages/support/` (`desk_endpoints.py`, `desk_feed.py`, `help_drawer.py`, `ticket_list.py`, `ticket_modal.py`, `support_chat.py`, `zoho_widget.py`). Shared: `pages/components/send_guard.py` (J21`s `delivery_guard.py`, moved and generalised; the old file is removed), `pages/components/stubbed_endpoint.py`, `pages/components/confirm_dialog.py` (`answer_no`, `expect_asking` added). Test data: `test_data/support.py`. Framework check: `tests/framework/test_support_send_guard.py`.

**Status: DRAFT — locators from Angular source, NOT yet verified live.** Written offline on 2026-10-13. No browser was opened and no test reached the app. Every locator, message and payload shape comes from `/home/jmd/margProject/newmarg-webangular20` (paths below are relative to `src/app/`) and must be checked on the first live run (see "To verify live").

Priority marker: `pytest.mark.p3` (J41 is P3; `p3` is registered in `pyproject.toml`). Journey marker: `journey("support-helpdesk")`.

## Safety
- Saving a ticket is a write to Marg's **live** support desk and queues a real WhatsApp and email (`margerpapi/Controllers/MargSupportController.cs:229-288`). Delete, reopen/reply and chat insert also write to it.
- Every test page (including the no-session page of SH-06) is armed with `SendGuard(page, SUPPORT_WRITES)` before its first navigation. It is a **context** route, so it covers every tab, and it **aborts** `MargSupport/Save`, `MBSupportDeleteRecord`, `MBSupportUpdateStatus`, `MBSupportInsertChatRecord`, `RegisterUser/CheckOTP`, `PharmaNxt/SendOTP`, `RegisterUser/SendSMSInQue*`, `RegisterUser/SendSMSTemplate`, `RegisterUser/SendBulkSMSTemplate`, `RegisterUser/ForgotPasswordMail`, `Template/SendEmailPdfExcel`, `Notification/SendWhatsapp*`, `Whatsapp/sendMessage` (`pages/support/desk_endpoints.py`, from `Globals/global.ts`). Any aborted call fails the test in teardown (`SendAttemptedError`).
- Class b tests add a **page** route stub (`StubbedEndpoint`) for exactly the write they press. Page routes take precedence over context routes, so the stub answers and nothing leaves the browser. `capture_one` proves the interception (the response came from the stub, not a server or service worker, and the stub answered exactly one more call), and the test asserts the captured payload fields **before** asserting the UI outcome.
- **Zoho SalesIQ** (SH-39) is a third-party chat with real agents. Its widget script (`https://salesiq.zoho.in/widget`, `src/index.html:17-34`) is answered by a recording stand-in or aborted by a page route (`pages/support/zoho_widget.py`); every other Zoho request is aborted. The stand-in test proves the stand-in answered before it clicks.
- Service workers are blocked suite-wide (root `conftest.py`, checked by `test_page_review_fixes.py::test_every_context_blocks_the_service_worker`).
- `tests/framework/test_support_send_guard.py` (19 checks, no app) proves the guard aborts each write URL, lets the four desk reads through, covers a new tab, and that a page stub answers the save before the guard sees it.

## Preconditions and test data
- SH-37 needs the login's second company (`Pharma New Company 23-09`); the `second_company` fixture checks the organisation list at runtime and skips with "SH-37: needs a second company" if it is missing, and switches back to the garments company in teardown. That module is `xdist_group("chemist-tenant")`.
- Account `chemist`, company pinned to "Garments New 29-08" (`CompanySwitchPage.ensure_company`), as in J21/J22. The support screens are not trade-specific (`Modules/support.module.ts:60`).
- **Served desk.** The ticket list and chat are the login's real tickets on Marg's desk (licence-scoped) and cannot be seeded, so most tests serve invented data (`test_data/support.py`, names "QA ..."): three tickets (Pending `QA-T3`, Closed `QA-T2`, Closed `QA-T1`, served out of order), a disposition tree with two visible main dispositions plus the hidden ids 60/61/62/71/72, one partner chat line and one suggestion. Shapes follow the fields the code reads (`pages/support/desk_feed.py`).
- **Real reads** are used only in SH-05 (`live_ticket_list`) and the first SH-10 test, so the live screen is smoke-checked too.
- New tickets are never saved for real; descriptions carry `QA-<run_id>`.

## Screens (from source, unverified)
| Thing | Locator | Source |
|---|---|---|
| Help icon | `get_by_title("Help", exact=True)` (header, `d-none d-lg-block`) | `Layout/homeLayout.component.html:841-842` |
| Help drawer | heading "Help ?" (`to_be_in_viewport`; drawer is always in DOM and slides by CSS `right`), container `.helpPanel .help-window` | `homeLayout.component.html:3085-3260`, `homelayout.component.ts:1379-1407` |
| Drawer links | links "011-30969630", "011-66969630", "support@margbooks.com", "+91-8010971097", "Raise ticket", "Visit portal"; button "Copy email address" (aria-label) | `homeLayout.component.html:3115-3194` |
| List | `/support/support-ticket`, heading "Support Ticket", link "Home", link "Remote Support", button "Create/F2" | `Layout/support-ticket.component.html:5-42` |
| Grid | `#supportTicket [ref=eBodyContainer] [row-index]`, cells `[col-id=TicketNo|Description|...]`, headers role columnheader | `support-ticket.component.ts:144-165` |
| Other Info | `.borderLable .form-group` row filtered by label | `support-ticket.component.html:193-238` |
| Action | row buttons name /Edit/ (svg title "Edit/F3") and "Delete"; ReOpen text "Reopen" | `Component/Shared/action.component.ts:26-57`, `ticket-template-button.ts:22-57` |
| Modal | dialog with heading "Create Ticket"/"Update Ticket"; `#Main_Disposition`, `#Sub_Disposition`, `#ticket-support`, `#Description`, `#fileName`; buttons "Save", "Update", "Close", "Attachment" (file chooser) | `Layout/create-ticket.component.html:1-163` |
| Validation | tooltip "Problem Type 1 required !"; marker `a.errowMsgNew` | `create-ticket.component.html:24-26`; `UtililityComponent/Validation/validation.component.html` |
| Suggestions | tooltip containing "May be this is useful for you!", links with `target=_blank`, `<mark>` | `create-ticket.component.html:92-103`, `assets/i18n/en.json:694` |
| Chat | dialog containing "Ticket ID : <ID>", textbox placeholder "Type your message" (Enter sends) | `Layout/support-chat.component.html:3-45` |
| Copy feedback | inside the copy button: `.copy-message` (tick, 2 s) vs `span.copied-icon` (copy icon) | `homeLayout.component.html:3130-3139`, `homelayout.component.ts:3994-4002` |
| Chat Now | link "Chat Now" in the drawer -> `$zoho.salesiq.floatwindow.visible('show')` | `homeLayout.component.html:3209`, `homelayout.component.ts:4004-4010` |
| Toasts | `pages/accounting/toasts.py` (warning/success/error are notifier toasts; Confirmation is a dialog) | `Globals/alertbox.ts:31-53` |

## Tests (88 collected)
| File | Tests | Scenarios |
|---|---|---|
| `test_help_drawer.py` | banner, sections, contacts, clipboard, copied tick shown and gone again, Raise ticket closes drawer, Raise ticket opens list, Visit portal tab URL (portal answered by a local stand-in) | SH-01, SH-02, SH-03, SH-04, SH-38 |
| `test_chat_now.py` | Chat Now with the Zoho stand-in shows the float window and closes the drawer; without the widget it only warns and the drawer stays open | SH-39 |
| `test_ticket_tenancy.py` | list request keeps the same UserId/UserTypeId/LicNo after switching to the second company (skips without one) | SH-37 |
| `test_ticket_end_to_end_stubbed.py` | stubbed save names a 10-digit Mobile (WhatsApp) and an Emailid (confirmation mail); after the save the reloaded list shows the desk's new ticket | SH-40 |
| `test_ticket_list.py` | direct URL (live), no session -> login host, columns, newest first, Other Info x4 + cross, double-click chat, chat read-only, Esc closes chat, edit/delete of Closed refused, Reopen only on Closed (2), search by ID, search by visible ProblemType, Remote Support href | SH-05..09, SH-30, SH-32, SH-34 (offer), SH-35, SH-41 |
| `test_create_ticket.py` | Create (live) and F2 open the modal, cascade x4, hidden mains, empty Save sends nothing / flags "Problem Type 1 required !" / no Description marker, no-description Save sends nothing, 1000-char limit (paste), suggestions request/link/mark, <=3 chars no request, regex characters, Close/Esc discard, Close no list reload, offline Save and offline list | SH-10..19, SH-25, SH-36 |
| `test_attachment.py` | >2 MB warns / not attached, exactly 2 MB attached, small png attached, `.mbk` warns / not attached, `.pdf` and `.zip` attached (code behaviour, D6) | SH-21, SH-22, SH-23, SH-24 |
| `test_ticket_writes_stubbed.py` | Save payload ids / names / session fields / base64 attachment, accepted save toast+close, list reload, Hindi+emoji, refused (status 0) toast and modal kept, HTTP 417 modal kept, double-click one request, F10 saves, Edit pre-fill, Update payload ID and toast, delete confirmation / payload / toast / cancel, reopen typing enabled / payload Status "5" / typing locked after | SH-20, SH-26..29, SH-31, SH-33, SH-34 |

Expected values come from the pack and the cited source; where the code contradicts the expected behaviour the test keeps the pack's expectation and is expected to fail as a defect candidate (marked in the test comment).

## Defect candidates (code reading only, none seen live)
- D1 (pack) F10 in a new ticket reads `this.data.editdata.TicketNo` with `editdata` undefined (`create-ticket.component.ts:687-692`): `test_f10_saves_a_new_ticket_like_the_save_button` should fail.
- D2 (pack) regex characters in `highlightMatch` (`:331-337`): `test_regex_characters_do_not_break_the_suggestions`.
- D3 (pack) no marker for empty Description (`create-ticket.component.html:110`): asserted as current behaviour (no marker) because the pack's SH-14 expects it.
- D5 (pack) label "Problem Type 1" for Main Disposition: asserted as the code text.
- D8 (pack) search filters on `Problemtype` (`support-ticket.component.ts:43`): `test_search_by_visible_problem_type_finds_the_ticket` may fail. (The served rows set `Problemtype` = the visible ProblemType text, so this only fails if the live field differs; see "To verify live".)
- **D11 (new)** double-click / Enter never opens the chat: `onRowDoubleClick` requires `!this.isFocusOnForm` (`support-ticket.component.ts:217-220`), `isFocusOnForm` starts `true` (`:38`) and only `checkFocus` (`:249-255`) clears it, whose only callers are in the commented-out form (`support-ticket.component.html:46-163`). SH-09 tests should fail. The Action column's "N Chat Messages" button (`action.component.ts:58-68`, shown when `chats > 0`) may be the only working path.
- **D12 (new)** `SupportChat` sets the root `NgbModalConfig` to `backdrop: "static", keyboard: false` (`support-chat.component.ts:31-33`), so after a chat has been opened once, Esc no longer closes other ng-bootstrap modals for the rest of the session (relevant to SH-25 Esc if a chat was opened earlier in the same page).
- **D13 (new)** `src/index.html:18-24` always defines `$zoho.salesiq` (widget code and `ready` only), so when the widget script has not loaded, `openChat` passes its `$zoho.salesiq` check and throws on the undefined `floatwindow` instead of logging "Zoho SalesIQ not loaded yet" (`homelayout.component.ts:4004-4010`). `test_chat_now_without_the_widget_only_warns` should fail.
- **D6 (pack)** `uploadImage` accepts any type but `.mbk` (`create-ticket.component.ts:706-731`, `accept=""` at `create-ticket.component.html:163`) while the message speaks of images only. `test_non_image_file_is_attached` asserts the code's behaviour, as the pack's SH-24 does; a human still decides the intended rule.
- **Pack correction (SH-10):** the modal does not focus Main Disposition on open; `getSupportStaticData` focuses `#ticket-support` = **Problem Type** (`create-ticket.component.ts:482`). No test asserts the initial focus; flagged for the pack owner.

## Not automated (and why)
None. Every scenario SH-01 to SH-41 now has a test. Open human decisions that the tests do not settle: the intended attachment rule (D6, SH-24) and whether tickets should be company-scoped (SH-37). SH-40's real round trip (the WhatsApp and email actually arriving) stays with Marg support on a test licence; the test covers it stubbed.

Not a scenario: the OTP create flow (`SupportTicketCreateComponent`) is unreachable in the UI (opener commented out, `support-ticket.component.ts:553-563`); the guard aborts `RegisterUser/CheckOTP` anyway.

## To verify live (first run)
1. Header Help icon is unique by title "Help" at 1280 px (`homeLayout.component.html:842`; a second `title="Help"` at `:813` is commented out).
2. Drawer open/closed by `to_be_in_viewport` on heading "Help ?" (`homelayout.component.ts:1398-1406`).
3. Copy button accessible name "Copy email address" (aria-label beats title, `homeLayout.component.html:3130`); clipboard permissions work in the suite's Chromium.
4. "Raise ticket" / "Visit portal" are role link (`href="javascript:void(0)"`, `:3180`, `:3194`); Visit portal opens a popup via `window.open` (`homelayout.component.ts:2686`).
5. List heading role/name "Support Ticket" (`support-ticket.component.html:5`); "Home" link name from title (`:7`); "Remote Support" link name (`:25-26`); "Create/F2" button name (`:30-39`).
6. ag-Grid 19 markup: `ref="eBodyContainer"`, `row-index`, `col-id` per field, header role columnheader (`support-ticket.component.ts:144-165`); header texts exactly "S.No.", "Ticket ID", "ProblemType", "Description", "Status", "ReOpen", "Action".
7. Edit/Delete button names in the Action cell (`action.component.ts:26-57`); `isEdit`/`isDelete` defaults true for this grid.
8. Served-data shapes accepted by the screen: list `Data.Data.Details` (`support-ticket.component.ts:429`), static data `Data.SubDispostion/ProblemTypeMargBook/SubProblemTypeMargBook` with string IDs and `Subdispositionid`/`ProblemTypeID` (`create-ticket.component.ts:476-482`, `:462`, `:828-830`), chat `Data.Data.Status/Details` (`support-chat.component.ts:141-154`), suggestions top-level `Status/Details` (`create-ticket.component.ts:313-325`). Compare against one live response of each (reads only).
9. Real `Problemtype` field of a live row vs the visible `SubProblemTypeMargDescriptin` (D8).
10. Modal heading role for `h5.modal-title` "Create Ticket" (`create-ticket.component.html:2`); footer "Close" vs header × "close" told apart by exact name (`:3`, `:144-146`).
11. ngb popovers render with role tooltip (validation and suggestions, ng-bootstrap 6).
12. Option labels match after whitespace trimming in `select_option(label=...)` (`create-ticket.component.html:19-22`).
13. `keyboard.insert_text` respects `maxlength` (SH-16).
14. Toast texts: "You cant edit this record" / "You cant delete this record" (`assets/i18n/en.json:564`, `:605`), "Maximum file size allowed is 2 MB.", "Invalid image format. Only jpg/jpeg/png format is supported.", "Internet Required for this option!", "Record saved/updated/deleted successfully." (`Globals/global.ts:18939-18966`, `:19031`).
15. Offline: `context.set_offline(True)` makes `navigator.onLine` false so `noInternetConnection` is true at construction (`create-ticket.component.ts:101-106`, `support-ticket.component.ts` constructor); the Home -> Help -> Raise ticket path works offline with the lazy module already loaded.
16. Confirmation dialog for delete is the shared "Confirmation" heading with Yes/No (`Globals/alertbox.ts:38-42`).
17. The save body is plain JSON (headers are encrypted, the body is not: `Services/MrgHttpService.service.ts:431-432`, `Services/LoaderInterceptor.service.ts:48-68`).
18. Chat dialog text "Ticket ID : <ID>" uses `rowData.ID`, not `TicketNo` (`support-chat.component.html:3`).
19. Copy feedback: `.copy-message` tick inside the copy button for 2 s, then `span.copied-icon` back (`homeLayout.component.html:3130-3139`, `homelayout.component.ts:3994-4002`).
20. "Chat Now" is role link (`href="javascript:void()"`, `homeLayout.component.html:3209`); a page route on `https://salesiq.zoho.in/` catches the widget script (`src/index.html:31`), and a stand-in served as JavaScript defines `window.$zoho.salesiq.floatwindow`.
21. The console warning "Zoho SalesIQ not loaded yet" (`homelayout.component.ts:4009`) is type `warning` in Playwright (D13 predicts it never appears).
22. List request body is JSON with `UserId`, `UserTypeId`, `LicNo` (`support-ticket.component.ts:419-424`, sent by `GetData` as POST, `Services/MrgHttpService.service.ts:86-90`).
23. Save body field `Emailid` (from `userData.emailid`, `create-ticket.component.ts:362`) is filled for the chemist login; the server mails it (`MargSupportController.cs:288`). `Mobile` from `userData.mobileno` (`:360`) is 10 digits.
24. Organisation row "Pharma New Company 23-09" exists on the chemist login (SH-37 skips otherwise).

## KB vs live app
Not re-run (offline). The pack's KB section stands; the SH-10 focus correction above is from source.
