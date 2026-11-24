# Plan: J21 Notifications, reminders, export/print (notifications-export)

Scenario pack: `scenarios/notifications-export.md`. Tests: `tests/journeys/notifications_export/` (+ `conftest.py`). Page objects: `pages/notifications_export/` (`delivery_endpoints.py` with the shared `pages/components/send_guard.py`, `notification_feed.py`, `notification_bell.py`, `sms_notification_page.py`, `report_share_export.py`, `schedule_setup_page.py`, `prescription_reminder_page.py`, `export_heading.py`, `downloads.py`, `json_route.py`, `anonymous_call.py`). Reused: `pages/reports/gst_export.py` (`read_export`, HTML-table `.xls`), `pages/reports/ledger_report_page.py`, `pages/banking/bank_book.py`, `pages/components/access_denied.py`, `pages/banking/yes_no_alert.py`, `pages/accounting/toasts.py`, `pages/company_switch_page.py`.
Status: DRAFT for QA/BA review. Observed live on 2026-10-12 (QA tenant premargbooks, `chemist` login pinned to company "Garments New 29-08", books 01-04-2026..31-03-2027; `garments` login for the ledger-report tests, as J12). Explored with probe tests (`page_as` + aria snapshots), no secrets read. No test ids on these screens.

## Preconditions and test data
- Every page is armed with `SendGuard(page, DELIVERY_OR_GLOBAL_WRITE)` (`pages/components/send_guard.py`, moved from `delivery_guard.py` on 2026-10-13 for J41) before its first navigation (service workers are blocked suite-wide by the root `conftest.py`, see N5). It aborts `Template/SendEmailPdfExcel`, `SendBulkSMSTemplate*`, `Reports/InsertBulkReminderData` (the old pattern `BulkReminderInsert*` was the constant's name in `global.ts:476`, not its URL, so it never matched; fixed 2026-10-13), `WorkFlow/SchedulerSave`, `Notification/InsertNotification`, `Notification/SendWhatsapp*`, `/api/SendMessage`, `Profiler/Save`; any attempt fails the test in teardown.
- Tests that drive a send (NE-30, NE-33, NE-37) answer the send endpoint with `pages/components/stubbed_endpoint.py::StubbedEndpoint` (a page route, which takes precedence over the guard) and prove with `capture_one` that the stub answered before they look at the screen. Recipients are `qa-sink@example.com` and `9000000001` (`test_data/notifications_export.py`); the real address the email draft prefills is removed first.
- PDFs are read with `pages/notifications_export/pdf_text.py` (no PDF library in the venv): page tree, Flate streams, ToUnicode maps, Tj/TJ. Checked offline on Chromium-made PDFs (multi-page, header on each page, Devanagari); not yet on a MargBooks PDF.
  - Why (1): live, every API response came `from_service_worker=True`, and Playwright cannot route requests a service worker makes. Without (1) a `page.route` stub or abort is silently bypassed. This also affects the existing guards in other journeys (`pages/auth/dispatch_guard.py`, `pages/communication_setup/outbound_guard.py`) on logged-in pages: see N5.
- The bell's feed (`notification/NotificationList`) is Marg-wide content; it was empty for the QA login (`{"Data":[]}`). Bell tests NE-02..NE-13 serve their own list by route stub (pack Q2 answered "yes" here, see N1). Items are named `QA-feed notice <n>` / `QA-feed announcement <n>`; nothing is written anywhere.
- Ledger-report tests own a new bank and expense ledger (`ledger_book`, a guarded copy of `fixtures/bank_book.py`) and post a cheque payment 1000.50 and receipt 400.25; ledgers and vouchers are deleted in teardown.
- The scheduler tests stop at client validation (name `QA-<run_id>-Schedule-<n>`, never saved).
- Never pressed: Send SMS, WhatsApp Share/F10, Email Send, Schedule (with valid data), Desktop-notification Yes, Save on Create Notification. No admin password is used or stored.

## Screens (verified live)
| Thing | What and locator |
|---|---|
| Bell | link "Notification" or "<n> Notification" (title "Notifications"); badge is part of the name. Dropdown tabs: role tab "Notification <n>" (`#tbNType1`), "Announcement <n>" (`#tbNType2`), labels singular (pack wrote plural). Items are links "<name> <description> <dd-mm-yyyy>", read ones have class `read`. Empty: h6 "No notifications yet" + "You're all caught up! ...". Desktop toggle `#btnEnableNotification`/`#btnDisableNotification` (bare svg) with label "Desktop Notification Enable/Disable", shown only when the list is not empty |
| Bell data | `GET StaticData/NotificationTypeData` (Notification 1, Announcement 2, Dashboard Notification 3), `GET notification/NotificationList?isForDashboard=true` -> `{"Data":[...],"status":{"status":"1"}}`; `GET notification/readNotification?linkid=` on item click |
| SMS Notification | `/support/sms-notification`, h1 "SMS Notification", toolbar links "Excel", "PDF", an unnamed print link, menu, "Back"; label "01-04-2026 -To-31-03-2027"; grid columns Show Use Date, Mobile No, Module Name, Message, No of SMS. Data `RegisterUser/GetSmsHistoryByuserID` (empty for the QA login). Back -> `/report/combine-report/<id>` |
| SMS exports | Excel downloads `SMS Notification.xls` (HTML): h1 company, h2 address, h3 "SMS Notification", p "<from> To <to>", columns Date, SendTo, NotificationType, Content, Unit. Empty log exported without any warning. PDF and print: `POST Common/GetReportData`, blob tab |
| Ledger report export | Excel/PDF open "Print Configuration": only a "Configure" checkbox; ticking it shows a view list ("Current View" selected, "Item Wise View") and the button "Print". Excel then downloads `<ledger>.xls` with columns Date, Particular, Vch/Bill No., Voucher Type, ₹ Debit, ₹ Credit, ₹ Balance |
| Ledger report share | "Share" menu: What's App (submenu PDF only), Email (Excel, PDF; anchors with `href=""`), SMS. What's App > PDF shows the toast "Module Is Under Development" and makes no upload call |
| Schedule | `/other/Schedular` "Schedule Master" (S.No., Schedule Name, Schedule For, Last Sent, Next Schedule Date, Status, Actions; empty). `/other/Schedular-process` "Schedule Setup": Schedule Name, Report Type preset "Inventory" (disabled), reports Minimum Stock / Maximum Stock, Send To radios, Email preset (disabled), Frequency Daily, To/Cc/Subject, attach Excel/PDF, buttons Reset, Schedule. Empty Schedule -> toast "Please Enter Schedular Name" |
| Prescription Reminder | `/report/crm/prescription/cm-default`, h1 "Prescription Reminder", columns (tick), Patient, Address, Contact No., Due On., Over Due, Prescribed By, Sms; empty on the garments company; no "Send SMS" |
| Create Notification | `/admin/support/create-notification` opens for the chemist login: h1 "Create Notification", Name, Type, Month, From/To Date, Enable As Link, Description editor |

## Tests
Bell (`test_notification_bell.py`, chemist, garments company; all but NE-01 on a stubbed feed)
| Test | Scenario | Asserts |
|---|---|---|
| `test_header_shows_the_notification_bell` | NE-01 | bell link visible, title "Notifications" (live feed) |
| `test_bell_opens_notification_and_announcement_tabs` | NE-02 | tabs "Notification 2", "Announcement 1" |
| `test_badge_counts_the_unread_notifications` | NE-03 | 3 unread + 1 read notification + 2 announcements -> "3 Notification" |
| `test_dropdown_lists_four_notifications_when_there_are_more` | NE-04 | 6 notifications -> 4 listed |
| `test_read_notification_is_marked_read` | NE-05 | read item has class `read`, unread not |
| `test_long_notification_text_is_cut_at_150_characters` | NE-06 | first 150 characters + "…." (KB spec). FAILS: D3 |
| `test_opening_the_bell_keeps_the_count` | NE-07 | open + close -> badge still 3 |
| `test_clicking_an_unread_notification_lowers_the_count` | NE-08 | 3 -> 2 after a click (KB spec). FAILS: D1 |
| `test_link_notification_opens_its_page_for_the_month` | NE-09 | new tab `<descURL>?M=202610&t=#MBM` (target host stubbed) |
| `test_empty_feed_shows_no_badge_and_all_caught_up` | NE-10 | link name "Notification", "No notifications yet", "You're all caught up!" |
| `test_announcements_tab_lists_the_announcements` | NE-11 | 2 announcements listed |
| `test_view_all_announcements_is_offered_above_four` | NE-11 | 5 announcements -> "View All Announcements" |
| `test_announcements_tab_without_announcements_says_so` | NE-11 | "No announcement!" |
| `test_declining_the_desktop_notification_question_keeps_the_setting` | NE-12 | question "Are you sure you want to enable/disable notification?", No, label unchanged, no `Profiler/Save` |
| `test_markup_in_a_notification_does_not_run_script` | NE-13 | an `onerror` handler in the description does not run. FAILS: D6 |

SMS Notification (`test_sms_notification_report.py`)
| Test | Scenario | Asserts |
|---|---|---|
| `test_report_shows_the_sms_log_columns` | NE-14 | the five grid columns |
| `test_report_period_is_the_books_year` | NE-14 | label "<books start> -To-<books end>" (from the header's books year) |
| `test_back_returns_to_the_combined_report` | NE-14, K5 | Back -> `/report/combine-report/` |
| `test_excel_export_is_named_after_the_report_with_its_columns` | NE-15 | `SMS Notification.xls`, columns Date, SendTo, NotificationType, Content, Unit |
| `test_excel_export_has_one_row_per_grid_row` | NE-15 | export rows = grid rows (0 = 0 for the QA login today) |
| `test_excel_export_period_is_the_books_year` | NE-17 | heading period = books start, books end. FAILS: D2 |
| `test_excel_export_names_the_current_company` | NE-43 (one company) | heading h1 = "Garments New 29-08" |
| `test_pdf_export_opens_a_new_tab_with_a_pdf` | NE-16 | a new tab opens and `Common/GetReportData` returns `%PDF-` (headless Chromium leaves the blob tab at about:blank) |
| `test_print_icon_opens_the_pdf_view` | NE-25 | same for the print icon |
| `test_excel_export_of_an_empty_report_warns_and_saves_no_file` | NE-18 | log stubbed empty -> "Exporting data not found !", no file. FAILS: D7 (expected) |

Ledger report of the test's own ledger (`test_report_export_share.py`, garments login)
| Test | Scenario | Asserts |
|---|---|---|
| `test_excel_export_lists_every_voucher_shown_on_screen` | NE-19 | Excel (Configure > Current View > Print) rows with a voucher number = report lines (number, type, debit, credit, order) |
| `test_whatsapp_pdf_share_asks_for_the_number_and_sends_nothing_on_close` | NE-27 | upload stubbed; dialog "Share on Whatsapp" with "WhatsApp Number"; Close -> "Party Whatsapp Number not available.". FAILS: D5 |

Reminders (`test_reminders.py`) and permissions (`test_permissions.py`)
| Test | Scenario | Asserts |
|---|---|---|
| `test_prescription_reminder_lists_due_prescriptions_without_send_sms` | NE-31 | columns, no "Send SMS" |
| `test_schedule_without_a_name_is_refused` | NE-35 | "Please Enter Schedular Name" |
| `test_schedule_without_a_report_is_refused` | NE-35 | name only -> "Please Select Report" (N3) |
| `test_schedule_with_an_invalid_email_is_refused` | NE-36 | name, Minimum Stock, To "qa-not-an-email" -> "Please enter valid Email Id" |
| `test_notification_list_without_login_is_refused` | NE-40 | anonymous GET: body status httpstatuscode "417", "Dbinfolinkid is zero", no Data (HTTP status is 200) |
| `test_create_notification_screen_is_refused_to_a_tenant_user` | NE-41 | redirect or denial wording (`AccessDenied`). FAILS: D4 |
| `test_valid_schedule_is_saved_and_returns_to_schedule_master` | NE-37 | SchedulerSave stubbed and proven answered; "Record saved successfully."; URL `/other/Schedular` (Schedular-Process.Component.ts:814-820). The schedule is not really saved, so it is not looked for in the list |
| `test_prescription_reminder_is_refused_without_the_crm_right[operator/accountant]` | NE-38 | `AccessDenied` on `/report/crm/prescription/cm-default`. Skips without credentials, or when the role's menu (`LoggedInUserInfo.UserLoginData.menuData`, `menu_rights.py`) shows the right |
| `test_report_offers_no_export_without_the_export_right[operator/accountant]` | NE-39 | Trial Balance shows no Excel/PDF link. Skips unless the role can view Trial Balance with `IsExport` 0 |

Export fidelity (`test_export_fidelity.py`; garments login, own customer/bill/ledgers deleted in teardown)
| Test | Scenario | Asserts |
|---|---|---|
| `test_receivable_export_lists_the_customers_bill` | NE-20 | own customer + one unpaid 150.00 bill (outstanding journey's `SaleBillDesk`); party outstanding (F8 from Ledger) > Excel holds the bill number |
| `test_receivable_export_holds_no_cash_or_tax_ledgers` | NE-20 | no cell starting Cash/CGST/SGST/IGST (MB-037757) |
| `test_export_of_an_empty_report_warns_and_saves_no_file` | NE-21 | Closing Stock Valuation served the real `Reports/GetOpeningClosingStock` answer with `ClosingStock`/`ReportData` emptied (`emptied_report.py`); Export > Save -> "Exporting data not found !", no file (importexport.component.ts:292-295) |
| `test_double_click_on_excel_saves_one_file` | NE-22 | SMS Notification, Excel double-clicked: exactly 1 download within 10 s |
| `test_pdf_shows_a_hindi_ledger_name_as_text` | NE-23 | expense ledger "<name> खाता" + one payment; ledger report PDF (Configure > Print) page 1 has every character of खाता and no unmapped glyph. A font without Devanagari that still maps glyphs to text would pass: the look stays a visual check |
| `test_second_pdf_page_repeats_the_report_header` | NE-24 | expanded Trial Balance PDF page 2 shows "Garments New 29-08" and "Trial Balance"; skips if the PDF has one page. Margins not checked |

Sale bill print (`test_sale_bill_print.py`; garments login, own customer and bill deleted in teardown)
| Test | Scenario | Asserts |
|---|---|---|
| `test_preview_shows_the_bill_number` | NE-26 | Print window after save > Preview (`PrintTemplate/PrintTemplateExport` or `Reports/InvoiceExport` PDF) shows the number read back from the list after Close (so Close left it saved) |
| `test_preview_shows_the_bill_date` | NE-26 | today as dd-mm-yyyy |
| `test_preview_shows_the_bill_total` | NE-26 | "150.00" |

Share delivery on Sale Register (`test_report_share_delivery.py`; chemist, garments company)
| Test | Scenario | Asserts |
|---|---|---|
| `test_share_without_an_uploaded_file_says_attachment_not_found` | NE-28 | `Common/GetMediaLink` stubbed with empty Data -> "Attachment file not found!" (MrgHttpService.service.ts:709-719). Sale Register's `mediaShare` is `isWoConfiguration`, so What's App > PDF reaches the upload (the ledger report does not, D5) |
| `test_whatsapp_share_sends_the_link_to_the_typed_number` | NE-30 | upload stubbed; number typed, Share (F10) -> `Notification/SendWhatsapp` stub answered, URL carries the number; "Whastapp Sent Succesfully !" |
| `test_email_without_a_recipient_is_refused_and_not_sent` | NE-29 | Share > Email > PDF opens "New Email"; To chips removed; Send -> "Please enter a valid Email Id!" and no `SendEmailPdfExcel` (email.setting.ts:308-313). The pack's "party without email" cannot occur on a report draft: To falls back to the user's own address (share.component.ts EmailFormat) |
| `test_email_share_sends_the_report_to_the_recipient` | NE-30 | To = qa-sink@example.com; Send -> stub answered with `toemailid` = that address; "Email sent successfully." |

Prescriptions on the pharma company (`test_prescription_sms.py`, xdist group chemist-tenant)
| Test | Scenario | Asserts |
|---|---|---|
| `test_ticking_a_due_prescription_offers_send_sms` | NE-32 | tick first row -> "Send SMS" shown (not clicked). Skips if no due prescription |
| `test_send_sms_sends_and_records_the_reminder` | NE-33 | `SendBulkSMSTemplate` + `InsertBulkReminderData` stubbed; SMS stub proven answered, record stub answered once; "SMS send successfully" (K6). Skips if no due prescription |
| `test_saved_prescription_is_listed_for_reminder` | NE-34 | `permanent`: new patient (F2 on `/chemist/patient`) + prescription (1 day, Dolo 650) -> listed in the reminder |
| `test_prescription_leaves_the_reminder_list_after_a_sale_bill` | NE-34 | `permanent`: then a cash sale bill for the patient -> no longer listed |

Tenancy (`test_tenancy.py`, xdist group chemist-tenant; skips without the pharma company; switched back in teardown)
| Test | Scenario | Asserts |
|---|---|---|
| `test_sms_log_is_the_same_in_both_companies` | NE-42 | SMS Notification rows in garments == rows in pharma (per-user log) |
| `test_bell_feed_is_the_same_in_both_companies` | NE-42 | live `NotificationList` Data in garments == in pharma (Marg-wide feed) |

## Defects seen (expected values kept from the source; the tests fail on them)
- D1 (NE-08, K1): clicking an unread notification does not lower the count (badge "3 Notification" stayed). The server's `readNotification` returns `Data=null` without writing and the UI reads `res.Data.status`. Spec (KB `onedrive_processed_data.csv#c7745bb1`): the count stays until the message is clicked.
- D2 (NE-17, K3): the SMS Notification export heading says "01-04-2026 To 01-04-2026"; the screen says 01-04-2026 -To-31-03-2027 (`sms-notification.component.ts:142,185` pass FinancialYearFrom as To).
- D3 (NE-06): a 200-character description is shown in full; the spec cuts at 150 characters with "….".
- D4 (NE-41, K10): `/admin/support/create-notification` opens for a tenant (chemist) user with the full form (Name, Type incl. "Dashboard Notification", Month, dates, Description). Its sibling list route has an AdminGuard; this one has none. Save (global `Notification/InsertNotification`) was not pressed.
- D5 (NE-27): Ledger report > Share > What's App > PDF shows "Module Is Under Development" and uploads nothing; What's App offers no Excel entry. The KB lists WhatsApp sharing on report screens (`careportal_enriched_v5.csv#3735db3d`). Cause in code: `share.component.ts` `whatsup()` falls to `underDevelopment` when the screen passes no `mediaShare` (the ledger report passes none).
- D6 (NE-13, security): a notification description containing `<img src=... onerror="...">` ran its script in the user's session. `loadNotifications` passes the description through `bypassSecurityTrustHtml` before `sanitize`, which returns trusted values unchanged, and the template binds it to `[innerHTML]` via `safeHtml`. Anyone who can create a notification (D4 makes that any logged-in user, if Save works) could run script in every tenant user's session. Not tried against the real feed.
- D7 (NE-18): with an empty SMS log, Excel saves a header-only `SMS Notification.xls` and shows no warning. The screen builds its own export (`sms-notification.component.ts:155-171`) and skips the shared toolbar's empty-data guard. Not yet confirmed by a run of the new test (pending the shared login).
- D8 (NE-37, seen live 2026-10-14): Schedule Setup refuses a valid typed To address. Name, report "Minimum Stock" and To = qa-sink@example.com, then Schedule: toast "Please Enter Valid Email Id" and no `WorkFlow/SchedulerSave` call. Cause in code: `Schedular-Process.Component.ts` `onSchedule()` counts only `autoEmail` + `allEmails` (addresses loaded from a Send To choice) in `EmailCount` and refuses when it is 0 (line ~798), although `finalEmail` includes the typed `toEmail`. `test_valid_schedule_is_saved_and_returns_to_schedule_master` keeps its expectation and fails on this defect.
- Note (NE-30, 2026-10-14): a report share's WhatsApp send goes to `whatsapp.margbooks.com/api/SendMessage` (number in body `contactUser`), not `Notification/SendWhatsapp`; the guard always covered it (`/api/SendMessage`), and the stub now matches it.

## NEEDS DECISION
- N1 (Q2) DECIDED 2026-10-12 by the test owner: stubbed NotificationList is accepted as the oracle for NE-02..NE-13 (they test bell behaviour, not feed content).
- N2 (NE-18, NE-21) DECIDED 2026-10-12: the intended behaviour is the app's own shared-export rule, warning "Exporting data not found !" and no file (`sharedexportimport.ts:99-102`). NE-18 is scripted (`test_excel_export_of_an_empty_report_warns_and_saves_no_file`, log stubbed empty) and fails on D7. NE-21 is scripted on Closing Stock Valuation, whose import/export button reaches the same rule (`importexport.component.ts:292-295`).
- N3 (NE-35): the pack's step "Please select report type" cannot occur on this screen: Report Type is preset and disabled. The test goes from the name check to "Please Select Report". Confirm that the preset is intended.
- N4 (NE-12): the desktop-notification icons react only when the click target is the `<svg>` itself (`e.target.id`); a real mouse click on the icon usually lands on its `<path>` and does nothing (live: a Playwright click did nothing). The test dispatches the click on the svg. Is the dead click a defect?
- N5 FIXED 2026-10-12: every browser context now blocks service workers (`browser_context_args` in the root `conftest.py`, checked by `tests/framework/test_page_review_fixes.py::test_every_context_blocks_the_service_worker`). The guard (now `SendGuard`) no longer removes the worker itself.

## Not automated (and why)
None. Every scenario NE-01..NE-43 is scripted (2026-10-13, offline; see "To verify live"). NE-43 stays single-company; NE-42 covers the two-company switch. No scenario of this journey is desktop-only or needs a physical device (the print icon and Preview open PDFs, nothing goes to a printer).

## To verify live (scripted offline 2026-10-13, locators from source only)
| Where | What to confirm | Source |
|---|---|---|
| `pdf_text.py` | reads a real MargBooks PDF (GetReportData, PrintTemplateExport): text, page order, fonts in object streams | `CommonController.cs:237-257` (`Pdfexport`) |
| `closing_stock_page.py` | route `/report/profitloss/closingstock`, heading "Closing Stock Valuation", toolbar link titled "Export", dialog with "File Name" and a Save button; emptied `ReportData` really empties the export check | `ClosingStock.html:6-12`, `ClosingStock.ts:84-104,259`, `save.as.component.html`, `importexport.component.ts:75,281-295` |
| `sale_register_page.py` | `/report/register/sale` opens straight to the report, h1 "Sale Register" | `report.module.ts:164`, `sale.purchase.register.html:11-12` |
| `report_share_export.py` `email_pdf`, `share_with_whatsapp_number` | Share > Email > PDF on Sale Register opens the draft; `#mobileno` and the Share button (title "Share") | `share.component.ts:96-120,269-271,513-534`, `transactionsms-qr.component.html:419-436` |
| `report_share_export.py` `export_pdf_current_view` | PDF on ledger report / Trial Balance goes through Print Configuration and posts `Common/GetReportData` | `sharedexportimport.ts:139-141` |
| `email_draft.py` | dialog text "New Email", To row found by label "To", chip remove "X", Enter adds a chip, Send button, From is prefilled (else Send refuses) | `email.setting.html:391-564`, `email.setting.ts:308-313,512-560,813-816` |
| WhatsApp send path | after Share the app reaches `Notification/SendWhatsapp` on this tenant (it depends on the WhatsApp setting; with none it may say "Whatsapp Via web is not available for reports!") | `Common.service.ts:4743-4840,4564-4580,5060` |
| `party_outstanding_page.py` + Excel | the party outstanding screen's Excel uses Print Configuration (trial-balance template); export cells hold the bill number as listed | `outstanding.report.ts:25,711-716` |
| `bill_preview.py` | Print window button named "Preview"; the preview's endpoint; bill number/date/total printed as asserted | `trxnprint.component.html:67`, `trxnprint.component.ts:192-199,322-386` |
| `prescription_reminder_page.py` | row tick box is a checkbox role inside the row; patient cell text | `prescription.reminder.component.ts:262-276` |
| `patient_form.py` | F2 window boxes `formcontrolname="MobileNo"` / `"Name"`, Save button; name mask accepts "QA-<run>-Patient-1" | `add.patient.component.html:22-58` |
| `prescription_master_page.py` | heading "Create Prescription Master", `#txtPresForDay`, "---Search Here---" opens a searchable patient window, item cell `#precription [col-id="itemLinkID"]` takes a typed description + Enter, Save | `prescription.master.component.html:6-120,365-382`, `.ts:474,1526-1543` |
| NE-34 oracle | which due window the reminder lists (1-day course from today), and that a cash bill naming the patient clears it | DB procedure not in the repo; KB `careportal_enriched_v5.csv#d71970a8` |
| `menu_rights.py` | `LoggedInUserInfo` in localStorage holds `UserLoginData.menuData` with `IsView`/`IsExport` | `importexport.component.ts:538-550`, `global.ts:13150-13180` |
| NE-22 | whether the second click is throttled, ignored or saves a second file | `CommonController.cs:331` |

## KB vs live app
- K1 confirmed live: clicking an unread item calls `readNotification?linkid=...`; the badge stays (4 before and after in the probe).
- K2 confirmed: six notifications, four listed, no scroll or "View All" for notifications.
- K3 confirmed: SMS Notification export heading "01-04-2026 To 01-04-2026".
- K4 confirmed: three header sets (KB, grid, export).
- K5: the route `/support/sms-notification` works and Back goes to `/report/combine-report/<id>`; the menu path was not walked.
- K10 confirmed: Create Notification opens for a tenant user.
- New: tab labels are singular ("Notification", "Announcement"); the pack wrote "Notifications"/"Announcements" (pack not edited, only the planner's table).
