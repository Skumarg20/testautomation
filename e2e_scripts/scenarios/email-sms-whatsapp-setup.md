# Scenario pack: Email / SMS / WhatsApp setup (J30, journey id `email-sms-whatsapp-setup`)

Status: DRAFT for QA/BA review (2026-10-09). Journey J30 "Email / SMS / WhatsApp setup", priority P2, layer e2e. Live findings are in `specs/email-sms-whatsapp-setup.md`.

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`.
- CODE = the code index in the same KB (`codekb:MargBooks:code|api|screen|schema`). `ask_codebase` fails (no API key); `get_file` does not hold the Angular files, so only component summaries are citable.
- UNVERIFIED = not citable; the question is stated, no value invented.

## Safety frame (applies to every case)
All three screens live in Control Room settings and are tenant-wide communication configuration. Tests never press a Send / Test / Verify / "Send via Personal Whatsapp" button, never add a sender email (adding one sends a verification mail, KB `onedrive_processed_data.csv#55605be2`), never save credentials, and never change an existing template, default flag, switch or WhatsApp config. Only records the test itself creates (a cloned template named `QA-<run_id>-...`, if the screen allows it) may be saved, and they are deleted in teardown.

## What the KB says
- Menu: Dashboard > Settings icon > "Dashboard Setting" > Control Room > Configure > "Control Room" window; Email Settings, SMS and Transaction SMS (WhatsApp) are entries there (KB `careportal_enriched_v5.csv#ef09e59c`, `#19a789a8`, `#c417f1af`; `onedrive_processed_data.csv#181e894d`).
- Email Settings: pick a nature of transaction (e.g. "Sale Bill"), click the Clone icon, an email template opens with "Set as default"; Save (KB `careportal_enriched_v5.csv#ef09e59c`). Component `ControlRoomSettingEmail` form fields `tempname`, `tempsubject`, `tempfrom`, `tempcc`, `tempbcc`, `template`, `isSelect`; lists `GET Template/List`, saves `POST Template/Save` (CODE `codekb:MargBooks:screen#ebdd3cc3`, `codekb:MargBooks:api#bd0d5309`). Email preference/sender: `POST Template/SaveEmailPreference` sends a verification mail (CODE `codekb:MargBooks:api#aae15f32`); "Add New Email Sender" dialog has Name, Email Address, Cancel, Save (KB `onedrive_processed_data.csv#55605be2`).
- SMS Settings: select transaction type (e.g. "Invoice"), Clone, tick "Set as default", Save; Preview icon shows the saved template (KB `careportal_enriched_v5.csv#68506e06`). Component `ControlRoomSmsSetting` form fields `tempname`, `template`, `smstype`, `chckedSwitch`, `isSelect`; an on/off switch calls `POST Template/UpdateStatus` (CODE `codekb:MargBooks:screen#8b71898a`, `codekb:MargBooks:api#c8f4933a`). DLT templates are configured via "SMS Notifications" Overview / SMS Templates tabs (KB `onedrive_processed_data.csv#51e9aee6`).
- WhatsApp (Transaction SMS): "Select SMS Type" (send via Marg Books or own account), Transaction Type with a "Transaction Type Message Preview"; transaction-wise contents are default and cannot be modified (KB `careportal_enriched_v5.csv#bc739708`). "Send via Personal Whatsapp" opens a QR-code popup (KB `onedrive_processed_data.csv#181e894d`). Component `TransactionsmsComponent` fields `phoneNo`, `selectedType`, `selectedTemplateId`, `selectedVariables[i]`, `template`; saves `POST Profiler/WhatsappConfigSave`, `POST Profiler/WhatsappTemplateSave` (CODE `codekb:MargBooks:screen#330b23ef`, `codekb:MargBooks:api#cae1322d`, `#956efaf5`).
- Jira: WhatsApp "sent successfully" toast shown while the customer gets nothing (KB `jira_vectordb.csv#abe058c0` MB-036085, `#7292a798` MB-034875, `#f08c607d` MB-033195). "Saving Template Must Save Changes." (KB `jira_vectordb.csv#feea40da`). "Remove the template name and add a Set as Default button" (KB `jira_vectordb.csv#93582712`). Email verification field max 200 characters (KB `jira_vectordb.csv#747eb7a7`).

## Email settings

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| EM-01 | positive | Open Control Room > Email Settings | Email Settings window with transaction types and templates | KB `#ef09e59c` |
| EM-02 | positive | Select a transaction type (Sale Bill) | Its template list shows | KB `#ef09e59c`; CODE `#ebdd3cc3` |
| EM-03 | positive | Clone a template, give a `QA-` name, save | Saved; listed under the type | KB `#ef09e59c`; safe only if the clone is not set as default (UNVERIFIED) |
| EM-04 | positive | Edit the cloned template subject | Change saved (Jira `#feea40da`) | UNVERIFIED |
| EM-05 | positive | Delete the cloned template | Removed from list | UNVERIFIED (no delete endpoint found in KB) |
| EM-06 | negative | Save a clone with an empty template name / subject | Refused | UNVERIFIED |
| EM-07 | negative | CC / BCC with an invalid email | Refused | UNVERIFIED |
| EM-08 | negative | Close a dirty clone without saving | Nothing saved | UNVERIFIED |
| EM-09 | safety | Add New Email Sender dialog: fill invalid / valid, Cancel | Nothing saved, no mail sent | KB `onedrive_processed_data.csv#55605be2` |

## SMS settings

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| SM-01 | positive | Open Control Room > SMS settings | Transaction types, templates, Clone / Preview icons | KB `#19a789a8`, `#68506e06` |
| SM-02 | positive | Preview a template | Template text shows | KB `#68506e06` |
| SM-03 | positive | Clone a template with a `QA-` name, save, delete | Saved then removed | KB `#68506e06`; delete UNVERIFIED |
| SM-04 | negative | Save a clone with empty name | Refused | UNVERIFIED |
| SM-05 | safety | On/off switch | Not toggled by tests (tenant-wide, `Template/UpdateStatus`) | CODE `#c8f4933a` |

## WhatsApp (Transaction SMS)

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| WA-01 | positive | Open Control Room > Transaction SMS | SMS type choices and transaction types show | KB `#bc739708`; `onedrive#181e894d` |
| WA-02 | positive | Pick a transaction type (Sale) | Message preview shows | KB `#bc739708` |
| WA-03 | negative | Test-number field with invalid mobile | Refused | CODE `#330b23ef` (`phoneNo`); rule UNVERIFIED; never pressed Send |
| WA-04 | safety | Close without saving | Config unchanged | derived |
| WA-05 | safety | "Send via Personal Whatsapp" QR popup | Not opened by tests (links a device) | `onedrive#181e894d` |
