# Scenario pack: J21 Notifications, reminders, export/print (notifications-export)

Journey: `notifications-export` (J21, P2, layers visual + api, stretch, target day 14). Plan: not written yet. Tests: none yet.
Analyst pass 2026-10-12. Written from the KB and the code only: no browser was opened and no login was used (a live suite holds the shared login).

Source keys
- KB = a chunk in the Tech Debt Radar KB, cited as `file#chunk_id(first 8)`. The MCP server dropped at the start of the session, so the KB was queried through the same server module in-process (`codeheatmap/mcp_server.search_kb`, read-only, same index). `ask_codebase` fails ("No API key configured"), so no answer from it is used.
- CODE = a code-index chunk in the same KB (`codekb:MargBooks:screen|api|schema|code#...`).
- CODE-L = a line in the read-only source. `web:` = `/home/jmd/margProject/newmarg-webangular20/src/app/`, `api:` = `/home/jmd/margProject/margbookscoreapi/`, `i18n:` = `newmarg-webangular20/src/assets/i18n/en.json`.
- UNVERIFIED = not citable; the question is stated and no value is invented.

## Safety frame (applies to every case)
- Never press a control that delivers to a real person: Send SMS, WhatsApp Share (F10) after a number is typed, Email Send, Schedule Save, Prescription Reminder "Send SMS". These rows are marked **needs sandbox** and stay out of the shared-tenant run.
- Safe to automate: opening the bell, tabs and lists; Excel and PDF downloads (they only return a file to the browser); the print/PDF tab (blob URL); opening a share or schedule dialog and closing it, and client-side validation that stops before any API call.
- Network guard for every test in this journey: abort `**/Template/SendEmailPdfExcel`, `**/SendBulkSMSTemplate*`, `**/BulkReminderInsert*`, `**/WorkFlow/SchedulerSave`, `**/Notification/InsertNotification`, `**/Common/GetMediaLink`, `**/Common/GetReporExceltLink`. The same pattern as the OTP guard in `password-reset-registration.md`.
- Never open `/admin/support/notification`. It asks for a shared admin password (see Q4), and the tests must not use or store it.

## What the KB and code say

### Notification bell (header)
- Care portal: click the "Notification" icon on the dashboard, a "Notification" window opens, "Click Here" opens New Updates (KB `careportal_enriched_v5.csv#4b884a0d`).
- The spec `MB_Notification.docx` (KB `onedrive_processed_data.csv#c7745bb1`):
  - Desktop notification only when the browser is minimised or another tab is active, and it is switched on in Control Room for all users.
  - The count stays until the user clicks the message. Clicking the bell does **not** clear it.
  - At most 4 visible at a time, the rest by scrolling. Text is cut at 150 characters with "….". A click opens a popup or the Care portal.
  - Unread messages have a coloured background or a dot. Read messages have a white background.
  - Modules: Minor Bug Fixes, Software Improvements, Prescription Reminder, Support Ticket conversations. Announcements arrive 24 h before an update or maintenance.
- Code: the bell is `.notificationDrop > a#dropdownMenuLink2[title="Notifications"]` with `img[src*="bell-icon.svg"]`, a badge `span.badge` showing `notificationCount` and the label "Notification" (CODE-L `web:Layout/homeLayout.component.html:893-904`, `i18n:406`, `i18n:525`). Note: an Electron-only sync link reuses `id="dropdownMenuLink2"` (`homeLayout.component.html:721-723`). Select by `.notificationDrop` and not by the id.
- Tabs come from `GET StaticData/NotificationTypeData` with type 3 removed. Tab anchors are `#tbNType1` (Notifications, red badge `notificationCount`) and `#tbNType2` (Announcements, blue badge `announcementCount`) (CODE-L `web:Layout/homelayout.component.ts:2280-2284`, `homeLayout.component.html:920-932`).
- List: `GET notification/NotificationList?isForDashboard=true`. Type 0/1 are notifications, type 2 announcements, type 3 dashboard notifications. The dropdown shows the first 4 (`slice(0, 4)`). Unread = `isRead == 0`. A read item gets class `read` (CODE-L `homelayout.component.ts:2293-2335`, `homeLayout.component.html:990-994`; CODE `codekb:MargBooks:api#bdf361a7`, `codekb:MargBooks:code#d1fe84df`).
- The item is `<a (click)="readNotification(linkid)" href=descURL target=_blank when isLink==1>`. Its date is `dd-MM-yyyy`. The description is rendered as HTML through `safeHtml` (CODE-L `homeLayout.component.html:990-1032`).
- Empty state: "No notifications yet" / "You're all caught up! ..." (CODE-L `homeLayout.component.html:1088-1096`). Empty announcements: "No announcement! " (`:1251`). "View All Announcements" link only when more than 4 (`:1183-1184`).
- SignalR push notifications are kept in `localStorage.myNotifications` and `notificationCount`. Buttons "Mark all as read" (only when something is unread) and "Clear all". Toasts "Notification deleted successfully" and "Notifications deleted successfully" (CODE-L `homeLayout.component.html:1074-1082`, `homelayout.component.ts:3758-3772`, `:487-511`; Jira `jira_vectordb.csv#066c47fa` "signal R notification delete functionality").
- Desktop notification toggle: `svg#btnEnableNotification` / `svg#btnDisableNotification`. Confirm texts "Are you sure you want to enable notification?" / "...disable notification?". Labels "Desktop Notification Enable/Disable" (CODE-L `homeLayout.component.html:941-970`, `homelayout.component.ts:1056-1072`, `web:Globals/global.ts:19617-19618`, `i18n:528-529`). The toggle writes the profiler setting `WebNotification` (`homelayout.component.ts:1107-1114`).
- Server: `GET Notification/readNotification` returns `Data = null` at once (the body is commented out) (CODE-L `api:margerpapi/Controllers/NotificationController.cs:85-105`; CODE `codekb:MargBooks:api#264c1a5d`). The UI then reads `res.Data.status` (CODE-L `homelayout.component.ts:2349-2360`). See "KB vs live app" K1.
- `NotificationList` and `GetNotification` are `[AllowAnonymous]`. List returns 417 "Dbinfolinkid is zero" when there is no tenant header (CODE-L `NotificationController.cs:38-55`, `:60-76`).
- Admin screens `/admin/support/notification` (AdminGuard: a `prompt()` password compared with a constant in the web bundle) and `/admin/support/create-notification` (**no guard**) (CODE-L `web:Modules/admin.module.ts:25-27`, `web:Authantication/admin-guard.component.ts:14-25`, `web:app-routing.module.ts:147`). Create posts `Notification/InsertNotification`, which writes to the main DB (CODE `codekb:MargBooks:api#5b4cfb14`).

### SMS Notification report (sent-message log)
- Path: Reports > Combined Report > Management Report > SMS Notification. Columns Date, Sent to, Notification Type (Payment Received, Payment Pending, ...), Content. Excel icon exports, PDF icon downloads, print (KB `careportal_enriched_v5.csv#80743db4`).
- Code: `SmsNotificationComponent`, route `/support/sms-notification` (CODE-L `web:Modules/support.module.ts:72`; CODE `codekb:MargBooks:screen#430511f0`). Heading `h1.mhead` from `SMSNotification.sMSNotification`. The date range is a read-only label showing the books year (`fromDate` To `toDate`). Grid `#userActivityLogs` with columns "Show Use Date", "Mobile No", "Module Name", "Message", "No of SMS". Back button `a[title="Back"]` goes to `/report/combine-report/<Management>` (CODE-L `web:UI/Report/Sms-Notification/sms-notification.html:1-50`, `web:Component/Report/Sms-Notification/sms-notification.component.ts:31-37`, `:123-133`).
- Data: `GET RegisterUser/GetSmsHistoryByuserID` (CODE-L `web:Globals/global.ts:286`). It is per user, not per company (see T-rows).
- Export: PDF and Excel build the rows on the client (Date, SendTo, NotificationType, Content, Unit) with title "SMS Notification". PDF goes to `Common/GetReportData`, Excel to `Common/GetReporExceltData` (CODE-L `sms-notification.component.ts:139-237`). Header date bug in K3.

### Shared export toolbar (all report and list screens that use `<sharedexportimport>`)
- Buttons `a[title="Excel"]` (emits `exportexcel`), `a[title="CSV"]` (only with `ShowCSVButton`), `a[title="PDF"]` (`exportpdf`, or the print configuration when `isReport`), and a print anchor (no title) shown when `showPdfButton` (CODE-L `web:Component/Shared/sharedexportimport.html:4-5`, `:54-58`, `:90`; `web:Component/Shared/sharedexportimport.ts:22-26`, `:132-150`).
- Generic export with no rows gives the warning "Exporting data not found !" (CODE-L `sharedexportimport.ts:96-101`).
- PDF: `POST Common/GetReportData` returns `application/octet-stream`. The UI opens the blob in a **new tab** with `window.open(blobUrl)`, not as a download (CODE-L `web:Services/MrgHttpService.service.ts:706-741`; CODE `codekb:MargBooks:api#fced3e38`). Server failure returns HTTP 418 (CODE-L `api:MargBooks.SalePurchaseMastersAPI/Controllers/CommonController.cs:216-235`).
- Excel: `POST Common/GetReporExceltData`. The UI downloads `<Title>.xls` (CODE-L `MrgHttpService.service.ts:744-786`, `CommonController.cs:330-353`). The live GSTR-1 export is an HTML table named `.xls` (see `scenarios/gst-report.md`, LIVE). Parse exports as HTML.
- Rate limits: `GetReportData` and `GetReporExceltData` allow 2 requests per second (`[RequestLimit(..., NoOfRequest = 2, Seconds = 1)]`, `CommonController.cs:217`, `:331`).
- Report screens: Excel, PDF, Print and Share icons. Share offers WhatsApp, Email, Send SMS (or Drive) (KB `careportal_enriched_v5.csv#3735db3d`, `#a97722d2`, `#2a2eba81`, `#c664140d`, `#e05bd70c`). Creditor outstanding has a Menu with Export, Print and Refresh List (KB `#e05bd70c`). Ledger report formats are Excel, PDF, Word, CSV, and PDF has Configure > Current View (KB `careportal_enriched_v5.csv#b541ba40`, `#306f9a59`, also cited in `scenarios/ledger-report.md`).

### Share via WhatsApp / Email from a report
- WhatsApp share of a report: the UI first uploads the file (`POST Common/GetMediaLink` or `Common/GetReporExceltLink`) and gets a short link (CODE-L `MrgHttpService.service.ts:707-720`, `:745-757`).
  - With no contact, a "Share on Whatsapp" dialog opens: label "WhatsApp Number", `input#mobileno` (integer mask), Close `#btnEsc`, `button[title="Share"]` (F10) (CODE-L `web:Services/Common.service.ts:4397-4423`, `web:transactionsms-qr/transactionsms-qr.component.html:419-436`).
  - Close gives "Party Whatsapp Number not available." (CODE-L `transactionsms-qr.component.ts:74-81`, `global.ts:19349`).
  - Offline gives "Internet Required for this option!" (`global.ts:19031`). An exception gives "Whastapp not Sent !" (`global.ts:19694`, typo as in source).
  - Missing file gives "Attachment file not found!" (`MrgHttpService.service.ts:717`).
- Email share: `POST Template/SendEmailPdfExcel` (CODE `codekb:MargBooks:api#d3c41646`). Care portal: Share > Email > Excel/PDF, "To" pre-filled from the party, "Subject", Send (KB `careportal_enriched_v5.csv#d1385283`). A party without email gives "Please enter a valid Email Id!" (CODE-L `web:Component/Shared/share.component.ts:288-297`, `global.ts:18967`). Success gives "Email sent successfully." (`i18n:783`, `share.component.ts:429`).

### Sale bill print window (print / preview / share after save)
- After a sale bill is saved, a "Print" window opens with Preview (F), Print, Email and Whatsapp (KB `careportal_enriched_v5.csv#3471a505`, `#b78e2aeb`, `#bf10b6fb`; transcript `vimeo_transcripts_hinglish_english.csv#47662e3b`). Live: "Select Format; Preview, Close, Print, Whatsapp", and Close leaves the bill saved (`scenarios/outstanding-advance.md`, live 2026-10-09). Owned by J04/J-sale. Here only the preview-and-close path is reused.

### Reminders
- Prescription reminder (chemist trade): due prescriptions show on the dashboard at login until a sale bill is made. CRM > Prescription Reminder lists prescriptions with due dates. Tick a row, "Send SMS", and the KB says "SMS Sent Successfully". Share via Email, WhatsApp or Drive, export, print (KB `careportal_enriched_v5.csv#d71970a8`).
- Code: `PrescriptionReminderComponent`, route `/report/crm/prescription/:type` (also under `/menu/...`) (CODE-L `web:Modules/report.module.ts:182`; CODE `codekb:MargBooks:screen#3ccf611a`). It reuses the trial-balance template. `a[title="Send SMS"]` appears only on `/report/crm/prescription/cm-default` or in the dashboard popup, and only when rows exist **and** at least one row is ticked (CODE-L `web:UI/Report/Accounting/trial.balance.component.html:13-16`, `:343-346`; `web:Component/Report/CRM/PrescriptionReminder/prescription.reminder.component.ts:230-240`).
- Send path: `SendBulkSMSTemplate`, then `BulkReminderInsert`, then the toast "SMS send successfully" (CODE-L `prescription.reminder.component.ts:281-336`). The table `dbo.PrescriptionReminder` stores senttype, duedate and remindersenddate (CODE `codekb:MargBooks:schema#cb8ac0d9`). `POST Reports/InsertBulkReminderData` (CODE `codekb:MargBooks:api#25be798e`).
- Role right: Role Configurations > CRM > "Prescription Reminder" Full, then Update, then "Role Saved Successfully"; re-login shows the menu (KB `careportal_enriched_v5.csv#4c1ef562`).
- Report scheduler (recurring report delivery by email or WhatsApp): Schedule Master list (KB `onedrive_processed_data.csv#e4db84dd`) and Scheduler Report (KB `onedrive_processed_data.csv#bd21eb41`).
  - Screens `/other/Schedular`, `/other/Schedular-process` (CODE-L `web:Modules/other.home.module.ts:68-69`; CODE `codekb:MargBooks:screen#ac2fd383`, `#c6c2fa9a`).
  - Form fields `SchedulerName, reportType, sendTo, frequency, date, day, month, time, email, toEmail, bccEmail, subject, emailmessage, whatsapp, MobileNo, whatsappmessage, attachFormat` (CODE `codekb:MargBooks:screen#c6c2fa9a`). Save is `POST WorkFlow/SchedulerSave` (CODE `codekb:MargBooks:api#41ed4e06`).
  - Validation order and messages (CODE-L `web:Component/Schedular-System/Schedular-Process/Schedular-Process.Component.ts:778-809`, texts `global.ts:19779-19786`):
    1. "Please Enter Schedular Name"
    2. "Please select report type"
    3. "Please Select Report"
    4. "Please select Schedule Plateform"
    5. "Please select frequency"
    6. "Please enter valid Email Id" (no email, bad email, or bad BCC)
- SMS template catalogue (payment received/pending and so on) (KB `onedrive_processed_data.csv#bfee0aac`, `#e34bf471`). Template setup belongs to J30 (`scenarios/email-sms-whatsapp-setup.md`).

## Known defects and complaints (bugs cluster here)
Export fidelity
- MBC-13152: Ledger export to Excel/PDF exports only the rows visible in the grid, not the whole dataset (KB `jira_vectordb.csv#42823243`).
- MB-037757: the receivable outstanding export contains Cash, CGST, SGST and other ledgers that are not in the report (KB `jira_vectordb.csv#f13d21fc`, `support_tickets_vectordb.csv#d60bcad5`). MB-037728: an extra party in the receivable export (KB `support_tickets_vectordb.csv#50acaa4b`).
- Stock and quantity mismatches between screen and Excel: batch-wise valuation (MB-037195, KB `support_tickets_vectordb.csv#a1b1c1b8`), current stock, near expiry, item register (Jira MBC-16708/16680/17568, cluster KB `support_tickets_vectordb.csv#e631bf52`). "Item category not showing while export report in excel" (KB `jira_vectordb.csv#b7459587`).
- GSTR-1 Excel/JSON export gives a 0 KB file (MB-036155, KB `support_tickets_vectordb.csv#2ec73d7f`).

PDF generation
- MBC-2046: "Value cannot be null. (Parameter 'fileContents') at Common/GetReportData While export pdf" (KB `jira_vectordb.csv#b56fd7c7`). This matches the code: on error `GetPDFReportDataByte` returns null, which then fails into 418 (CODE-L `CommonController.cs:237-257`).
- MBC-13147: a PDF with non-English text shows black dots (KB `jira_vectordb.csv#5e5e518b`, also print templates `#b15a539d`).
- MB-031813: ledger register PDF page 2 has no header or margin (KB `jira_vectordb.csv#25c24e59`).
- MB-038042: error exporting sale bills to PDF from the sale bill list (KB `jira_vectordb.csv#70d66274`). A PDF shared by mail is 0 KB (KB `support_tickets_vectordb.csv#1788f718`).
- MB-038519: after the plan expires, sale bills cannot be printed, exported to PDF or mailed for an old FY (KB `jira_vectordb.csv#efc6d2d7`).

Print and share
- MB-037864: the bill date is dd/mm/yyyy in preview but mm/dd/yyyy when opened from the WhatsApp link (KB `jira_vectordb.csv#6b2f6e49`). Previous balance is 0 in the WhatsApp copy but correct in preview (KB `support_tickets_vectordb.csv#58ee1046`).
- MB-037192: no print option from the purchase return voucher (KB `jira_vectordb.csv#1123986f`). Print preview shows no product for a bill (Jira MBC-17804, KB not chunk-cited: UNVERIFIED chunk id).
- WhatsApp "sent successfully" while nothing arrives (MB-036085 and others, cited in `scenarios/email-sms-whatsapp-setup.md`, KB `jira_vectordb.csv#abe058c0`).

Reminders
- Prescription reminder: "object reference error" (KB `jira_vectordb.csv#45d38f3b`). Prescription not in the reminder list, MB-035643 (KB `jira_vectordb.csv#64c02a52`, `support_tickets_vectordb.csv#e231f51d`). The option shows no details, MB-028958 (KB `jira_vectordb.csv#ebaf1ac6`).

Notifications
- "Notification Redesign" (KB `jira_vectordb.csv#1ca5eec3`). SignalR notification delete (KB `jira_vectordb.csv#066c47fa`). No defect ticket found for the bell count. K1 is a code finding.

## Scenarios
P1 = candidate for the first automation pass (safe on the shared tenant, cheap, deterministic).

### A. Notification bell

| ID | P1 | Type | Scenario | Expected result | Source |
|---|---|---|---|---|---|
| NE-01 | P1 | positive | Dashboard header shows the bell | `.notificationDrop` visible with bell image and label "Notification" | CODE-L `homeLayout.component.html:893-904`, `i18n:406`; KB `careportal_enriched_v5.csv#4b884a0d` |
| NE-02 | P1 | positive | Click the bell | Dropdown opens with tabs from NotificationTypeData (`#tbNType1` Notifications, `#tbNType2` Announcements), each with a badge | CODE-L `homeLayout.component.html:918-932`, `homelayout.component.ts:2280-2284` |
| NE-03 | P1 | consistency (api + visual) | Badge count equals the unread type 0/1 items from `GET notification/NotificationList?isForDashboard=true` captured on the same load | `badge == count(type in (0,1) and isRead == 0)` (plus unread SignalR items in localStorage) | CODE-L `homelayout.component.ts:2315-2319`, `:498-511` |
| NE-04 | P1 | boundary | API returns more than 4 notifications | Dropdown lists exactly 4 (first 4 by month, newest first). KB says the rest scroll; the code has no scroll for type 1 (see K2) | KB `onedrive_processed_data.csv#c7745bb1` §3a; CODE-L `homelayout.component.ts:2302`, `:2320` |
| NE-05 | | positive | Unread vs read styling | Read items have class `read` (white background per spec), unread do not | KB `#c7745bb1` §3c-d; CODE-L `homeLayout.component.html:992` |
| NE-06 | | boundary | A notification text longer than 150 characters | Cut at 150 characters with "….". Code renders the full `description` HTML, no cut found | KB `#c7745bb1` §3b; UNVERIFIED in code |
| NE-07 | P1 | negative | Opening the bell does not clear the count | Badge unchanged after open and close | KB `#c7745bb1` §2 note |
| NE-08 | | positive | Click one unread notification | Spec: count drops by 1 and the item turns white. Code: `readNotification` API is a no-op returning `Data=null` and the UI reads `res.Data.status`, so expect a console TypeError and no change. Assert the spec value, mark xfail with K1 | KB `#c7745bb1` §2b; CODE-L `NotificationController.cs:85-105`, `homelayout.component.ts:2349-2360` |
| NE-09 | | positive | Item with `isLink == 1` | Opens `descURL?M=<yyyymm>&t=#MBM` in a new tab (Care portal) | KB `#c7745bb1` §3b, `#4b884a0d`; CODE-L `homelayout.component.ts:2309`, `homeLayout.component.html:993-994` |
| NE-10 | P1 | boundary | API returns an empty list (route-mock the response) | "No notifications yet" and "You're all caught up!..." shown, no badge | CODE-L `homeLayout.component.html:1088-1096`, `:898-899` |
| NE-11 | | positive | Announcements tab | Lists type 2 items; "View All Announcements" only when there are more than 4; empty shows "No announcement!" | CODE-L `homeLayout.component.html:1102-1108`, `:1183-1187`, `:1251`; KB `#c7745bb1` §5 |
| NE-12 | | negative | Desktop notification toggle, then Cancel on the confirmation | Confirmation "Are you sure you want to enable notification?" (or disable). Cancel keeps `WebNotification` unchanged. Never confirm: it changes a profile setting for the shared user | CODE-L `homelayout.component.ts:1056-1072`, `global.ts:19617-19618` |
| NE-13 | | security (XSS) | Description containing HTML (route-mock with `<img onerror>`) | Rendered through `safeHtml` after `sanitize`: no script runs. The pipe name suggests a bypass, so check | CODE-L `homelayout.component.ts:2308`, `homeLayout.component.html:1030`; UNVERIFIED outcome |

### B. Exports and print from report and list screens

| ID | P1 | Type | Scenario | Expected result | Source |
|---|---|---|---|---|---|
| NE-14 | P1 | positive | SMS Notification report opens from Reports > Management Report > SMS Notification and by `/support/sms-notification` | Heading SMS Notification, date label = books year, grid columns Show Use Date, Mobile No, Module Name, Message, No of SMS | KB `careportal_enriched_v5.csv#80743db4`; CODE-L `sms-notification.html:5-12`, `sms-notification.component.ts:31-37`. KB column names differ (K4) |
| NE-15 | P1 | positive | SMS Notification > Excel | `POST Common/GetReporExceltData` 200, download `SMS Notification.xls`, HTML table rows equal the grid rows (Date, SendTo, NotificationType, Content, Unit) | CODE-L `sms-notification.component.ts:183-237`, `MrgHttpService.service.ts:744-786`; KB `#80743db4` |
| NE-16 | P1 | positive | SMS Notification > PDF | New tab (popup) with a blob URL, `Common/GetReportData` 200, non-empty `%PDF` body | CODE-L `sms-notification.component.ts:139-181`, `MrgHttpService.service.ts:721-741` |
| NE-17 | | boundary | SMS Notification export header dates (non-Nepali calendar) | Expected: From = books start, To = books end, as on screen. Code passes FinancialYearFrom as **To** (K3), so the export header shows the same date twice | CODE-L `sms-notification.component.ts:141-142`, `:184-185` |
| NE-18 | | boundary | SMS Notification with no rows (new user or route-mock empty) | Expected: a warning like "Exporting data not found !" as on generic screens. Code sends an empty table with no guard: UNVERIFIED result | CODE-L `sharedexportimport.ts:96-101` vs `sms-notification.component.ts:162-171` |
| NE-19 | P1 | consistency | Export matches screen on one report with rows owned by the test (e.g. Ledger report of the test's own ledger, Outstanding of its own party) | Excel row count = grid row count **for the whole dataset** (scroll past the first page) and the totals are equal | Edge checklist "export matches screen"; KB `jira_vectordb.csv#42823243` (MBC-13152), `#f13d21fc` (MB-037757) |
| NE-20 | | negative | Receivable outstanding export does not contain ledgers outside the report | No Cash, CGST or SGST rows in Excel/PDF | KB `jira_vectordb.csv#f13d21fc`, `support_tickets_vectordb.csv#d60bcad5` |
| NE-21 | P1 | negative | Generic report export with no rows (period with no data, e.g. a future month) | Warning toast "Exporting data not found !" and no download | CODE-L `sharedexportimport.ts:96-101` |
| NE-22 | | boundary | Double-click Excel or PDF within 1 s | One file. The second call may be throttled (2 requests per second); no error dialog. Throttle response shape UNVERIFIED | CODE-L `CommonController.cs:217`, `:331` |
| NE-23 | | boundary (unicode) | PDF of a report whose rows contain non-Latin text (test-created ledger named in Hindi) | Text readable, not black dots | KB `jira_vectordb.csv#5e5e518b` (MBC-13147) |
| NE-24 | | boundary | Multi-page PDF (ledger register over 1 page) | Page 2 has the header and margins | KB `jira_vectordb.csv#25c24e59` (MB-031813) |
| NE-25 | P1 | positive | Print icon on a report | Opens the PDF/print view (new tab or print configuration). The test asserts the popup and its PDF and never sends to a printer | KB `#a97722d2`, `#2964ffb7`; CODE-L `sharedexportimport.html:90`, `sharedexportimport.ts:144-150` |
| NE-26 | | positive | Sale bill (test-created) > Print window > Preview, then Close | Preview PDF shows the same bill no., date (dd-mm-yyyy) and total as the bill, and Close leaves the bill saved | KB `careportal_enriched_v5.csv#3471a505`, `vimeo_transcripts_hinglish_english.csv#47662e3b`; `scenarios/outstanding-advance.md` (live) |

### C. Share (stops before delivery)

| ID | P1 | Type | Scenario | Expected result | Source |
|---|---|---|---|---|---|
| NE-27 | P1 | negative | Report > Share > WhatsApp (GetMediaLink route-mocked to return a fake id), then Close the "Share on Whatsapp" dialog | Dialog shows "WhatsApp Number" `#mobileno`. Close gives the warning "Party Whatsapp Number not available." and nothing is sent | CODE-L `Common.service.ts:4403-4416`, `transactionsms-qr.component.html:419-436`, `global.ts:19349` |
| NE-28 | | negative | Same with GetMediaLink route-mocked to return empty Data | "Attachment file not found!" | CODE-L `MrgHttpService.service.ts:709-719` |
| NE-29 | | negative | Share via Email for a party without an email address | "Please enter a valid Email Id!" and no mail call | CODE-L `share.component.ts:288-297`, `global.ts:18967` |
| NE-30 | | positive | WhatsApp or Email share actually delivered (Email Send, WhatsApp F10) | "Email sent successfully." / WhatsApp opened, and the recipient sees the same date format as the preview (MB-037864) | **needs sandbox**. KB `careportal_enriched_v5.csv#d1385283`, `jira_vectordb.csv#6b2f6e49`; `i18n:783` |

### D. Reminders

| ID | P1 | Type | Scenario | Expected result | Source |
|---|---|---|---|---|---|
| NE-31 | P1 | positive | CRM > Prescription Reminder (`/report/crm/prescription/cm-default`, chemist company) opens | Grid of due prescriptions with due dates. Send SMS hidden while no row is ticked | KB `careportal_enriched_v5.csv#d71970a8`; CODE-L `prescription.reminder.component.ts:230-240`, `trial.balance.component.html:343-346` |
| NE-32 | | positive | Tick one row | `a[title="Send SMS"]` appears. Do **not** click it | CODE-L `prescription.reminder.component.ts:234-236` |
| NE-33 | | positive | Send SMS for a ticked test prescription (test patient with a test number) | Toast "SMS send successfully" (code) vs "SMS Sent Successfully" (KB), and a `PrescriptionReminder` row with senttype SMS | **needs sandbox**. KB `#d71970a8`; CODE-L `prescription.reminder.component.ts:281-336`; CODE `codekb:MargBooks:schema#cb8ac0d9` |
| NE-34 | | state | Prescription saved by the test appears in the reminder list until a sale bill is made for it | Listed, then gone after the bill | KB `#d71970a8`, defect `jira_vectordb.csv#64c02a52`. Needs a test prescription (J-chemist data) |
| NE-35 | P1 | negative | Report scheduler: open Create Schedule, Save with an empty name | "Please Enter Schedular Name" and no `WorkFlow/SchedulerSave` call. Then fill name only and expect "Please select report type", and so on through the validation order above | CODE-L `Schedular-Process.Component.ts:778-809`, `global.ts:19779-19786`; CODE `codekb:MargBooks:screen#c6c2fa9a` |
| NE-36 | | negative | Scheduler with an invalid To or BCC email | "Please enter valid Email Id" | CODE-L `Schedular-Process.Component.ts:798-809` |
| NE-37 | | positive | Save a schedule that emails a report | Saved ("saveRecord" alert) and listed in Schedule Master | **needs sandbox** (it sends real mail on schedule). KB `onedrive_processed_data.csv#e4db84dd`; CODE `codekb:MargBooks:api#41ed4e06` |

### E. Permission and tenancy

| ID | P1 | Type | Scenario | Expected result | Source |
|---|---|---|---|---|---|
| NE-38 | | permission | User without the CRM "Prescription Reminder" right opens `/report/crm/prescription/cm-default` directly | Denied or hidden. Exact behaviour UNVERIFIED. Needs a limited user (shared open question in `auth.md` / `masters.md`) | KB `careportal_enriched_v5.csv#4c1ef562` |
| NE-39 | | permission | User without the Export right on a report | Excel/PDF icons hidden or refused. UNVERIFIED: no rights check found in `sharedexportimport.ts`; `user-role-management.md` UR-03 shows an Export column per screen | `scenarios/user-role-management.md` (live); UNVERIFIED |
| NE-40 | | permission (api) | `GET notification/NotificationList` with no auth token or tenant header | Not 200 with data: 417 "Dbinfolinkid is zero" (the endpoint is AllowAnonymous) | CODE-L `NotificationController.cs:38-48` |
| NE-41 | | permission | Logged-in non-admin opens `/admin/support/create-notification` | Expected: refused like `/admin/support/notification`. Code: no guard on this route. Assert only that the page opens or not, and never Save (it writes global notifications) | CODE-L `admin.module.ts:25-27`; CODE `codekb:MargBooks:api#5b4cfb14` |
| NE-42 | | tenancy | Switch company A to B, open the SMS Notification report and the bell | Report and notification rows must belong to the session user. The SMS log is per user (`GetSmsHistoryByuserID`), so the same rows in A and B are expected. Flag if B shows A-only party messages | CODE-L `global.ts:286`, `NotificationController.cs:45-47` (`complinkid`, `userlinkid`). UNVERIFIED |
| NE-43 | | tenancy | Export from company B after viewing company A | File header CompanyName = B and rows = B's grid | CODE-L `sms-notification.component.ts:147-149`; edge checklist |

P1 set (15): NE-01, 02, 03, 04, 07, 10, 14, 15, 16, 19, 21, 25, 27, 31, 35. NE-03, 04 and 10 can run with a route-mocked list. The rest need only the shared tenant's own data, or test-created ledgers for NE-19.

## Navigation, routes and selectors for the planner
- Bell: `.notificationDrop a[title="Notifications"]`. Badge: `.notificationDrop a > span.badge`. Tabs: `#tbNType1`, `#tbNType2`. Items: `.notificationDrop li a.primary` (read: `.read`). Empty state: text "No notifications yet". Push-notification buttons: text "Mark all as read", "Clear all". Desktop toggle: `#btnEnableNotification` / `#btnDisableNotification`.
- APIs to wait on or mock: `notification/NotificationList`, `StaticData/NotificationTypeData`, `notification/readNotification`.
- SMS Notification: `/support/sms-notification`; form `#smsnotificationForm`; grid `#userActivityLogs`; toolbar `sharedexportimport a[title="Excel"]`, `a[title="PDF"]`; Back `a[title="Back"]`. Menu path Reports > Management Report > SMS Notification.
- Prescription Reminder: `/report/crm/prescription/cm-default` (chemist module also has `/chemist/prescription`, `/chemist/prescription-create`, `web:Modules/chemist.module.ts:28-29`); Send SMS `a[title="Send SMS"]`.
- Scheduler: `/other/Schedular` (list), `/other/Schedular-process` (create). Report-side scheduler `/report/schedular`, `/report/schedular-detail` (CODE `codekb:MargBooks:screen#c5a1b2b6`, `#af824252`).
- Schedule payment (voucher due-date scheduling, not a messaging reminder): `/transaction/voucher/schedulepayment` (CODE `codekb:MargBooks:screen#ebf95433`). Out of scope unless the owner says otherwise (Q6).
- Export calls: PDF = popup page with a `blob:` URL (use `context.expect_page`). Excel = download event (`page.expect_download`), file `<Title>.xls`, HTML content. Print = popup or print config.
- WhatsApp share dialog: `input#mobileno`, `#btnEsc`, `button[title="Share"]`.

## Open questions
- Q1 Is K1 (bell count never drops after a click) a known product decision, so that NE-08 should be xfail, or a defect to raise?
- Q2 May tests route-mock `NotificationList` (NE-03/04/10/13)? The real list is global Marg content and cannot be seeded.
- Q3 Is there a sandbox tenant or SMS/WhatsApp/email sink for NE-30, 33, 37? Without one they stay manual.
- Q4 `/admin/support/notification` is protected by a password constant in the web bundle (`global.ts`, `Global.adminPassword`), and `/admin/support/create-notification` has no guard at all. Security review rather than an e2e case? (Not copied here.)
- Q5 Which trade or company on the QA login is chemist, for the Prescription Reminder rows?
- Q6 Is "reminders" meant to include payment-due reminders? The KB shows only SMS templates (payment received/pending) and outstanding-report Share > Send SMS. No standalone payment-reminder screen was found in routes.
- Q7 Should a limited user (no Export / no CRM right) be created for NE-38/39 (shared with `auth.md` Q3)?

## KB vs live app (and KB vs code)
Not resolved here; a human decides.
- K1 Bell read state: the spec says the count stays until the message is clicked, then the item turns white (KB `onedrive_processed_data.csv#c7745bb1`). Code: `readNotification` on the server returns `Data=null` without writing (`NotificationController.cs:85-105`). The UI then dereferences `res.Data.status` (`homelayout.component.ts:2352`), so the count never drops and the click logs a TypeError. `isRead` always comes from the server and never flips.
- K2 "Max 4 visible, the rest by scrolling" (KB `#c7745bb1` §3a): the code slices to 4 and has no scroll or "view all" for notifications. The "View All Notifications" link is commented out (`homeLayout.component.html:1070-1072`); only announcements have "View All".
- K3 SMS Notification export: both PDF and Excel pass `FinancialYearFrom` as `toDate` for the Gregorian calendar (`sms-notification.component.ts:142`, `:185`). In the Nepali-calendar branch, From is formatted `yyyy-MM-dd` while To is `dd-MM-yyyy` (`:145-146`).
- K4 SMS Notification columns: the KB says Date, Sent to, Notification Type, Content (and screenshots show "SMS ID", "Name"). The grid says Show Use Date, Mobile No, Module Name, Message, No of SMS. The export uses Date, SendTo, NotificationType, Content, Unit. Three different header sets.
- K5 KB route: the care portal reaches SMS Notification by Reports > Management Report. The code mounts it under `/support/sms-notification` with Back to `/report/combine-report/<Management>`. Confirm the menu entry still exists live.
- K6 Prescription reminder success text: the KB says "SMS Sent Successfully" (`#d71970a8`); the code says "SMS send successfully" (`prescription.reminder.component.ts:329`).
- K7 Care portal: "import the SMS Notification List in Excel format" (`#80743db4`). It is an export; there is no import on that screen.
- K8 PDF from the toolbar opens a new tab (blob) rather than downloading. The KB says "download it in PDF format" (`#80743db4`). Tests must wait for a popup, not a download.
- K9 Excel exports are HTML tables named `.xls` (code writes `titlename + .xls` from an octet-stream; live GSTR-1 file is HTML, `gst-report.md`). The KB calls them Excel.
- K10 `/admin/support/create-notification` has no AdminGuard while its list sibling has one (`admin.module.ts:25-27`).
