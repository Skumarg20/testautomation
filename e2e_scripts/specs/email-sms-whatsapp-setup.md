# Spec: Email / SMS / WhatsApp setup (J30, `email-sms-whatsapp-setup`)

Status: DRAFT for QA/BA review (2026-10-10). Tests: `tests/journeys/communication_setup/` (17; 15 pass, 2 fail on D1 and D2). Scenarios: `scenarios/email-sms-whatsapp-setup.md`. Seen live on the garments QA company ("Garments New 29-08 (GANE29)", app V. 4.3.598.b) with throwaway probes, 2026-10-09/10.

## Safety design
All three screens are tenant-wide communication configuration inside the Control Room. The tests:
- open screens, read what is shown, trigger client-side validations, and leave with Close / Cancel;
- run under a network guard (`pages/communication_setup/outbound_guard.py`) that aborts every non-GET request whose URL looks like a save or a dispatch (template save, email preference / sender, WhatsApp config or template, SMS switch, DLT, send) and fails the test in teardown if one was attempted;
- never press Send via MargBooks / Send Via Whatsapp Web / Integrate your own WhatsApp number (they change the SMS type or link a device), never touch the SMS "Configure" or "SMS Bazaar" panels, never add a sender email.
No test saves anything, so nothing is left on the tenant. Template create / edit / delete is not automated: see N1.

## Screens (seen live)

Entry: Dashboard > Settings (`#aControlRoomSetting`) > Control Room "Configure" (`#btnGStHeading-2`) opens the page `/mstr/margsetup-controlroom` (heading "Control Room"). Tests other than `test_control_room_lists_the_communication_sections` open the page by URL: right after a dashboard load on the QA host the Settings icon click was sometimes lost (see N6). Its left list holds, among others, "Email Settings", "SMS Settings" and "Transaction SMS" (list items without link role). Esc on the Control Room closes it and returns to the dashboard.

| Section | What it shows |
|---|---|
| Email Settings | Type links: Email Preference, Payment Reminder, Payment Received, Credit Note, User Invitation, Purchase Order, Party Statement, Sale-Bill, Sale Order, Purchase Import Email Setup, Sale Quotation. Per type: heading, "+ New" button, table NAME / SUBJECT. Sale-Bill holds one row: name "Sale-Bill", label "Default Template", subject "Sale-Bill Invoice", row links "Clone" and "Attach File". No edit or delete control on the row; clicking the name does nothing visible. |
| Email template form ("+ New" or "Clone") | Name (textbox), From / CC / BCC (tag comboboxes), Subject (textbox), "Insert Fields", checkbox "Set as default", rich-text body (TinyMCE), buttons "F10 Save" and "Esc Close" |
| Email Preference | "Default Domain": emails are sent through "Email address of Marg Books (noreply@margbooks.com)"; table NAME / EMAIL ADDRESS / STATUS / ACTION with one row "Marg Books Default", "noreply@margbooks.com", "System Verified", "Default". No add-sender button seen on this company. |
| SMS Settings | Banner "Update DLT registration details to continue sending SMS" with button "Configure DLT Registration"; panels "Marg Books" (Configure) and "External SMS Providers" > "SMS Bazaar" |
| DLT Registration Details (dropdown popup) | "DLT Registered Number", "Sender ID" (both empty on this company), Note text, buttons Cancel / Save |
| Transaction SMS (WhatsApp) | "Select SMS type": buttons Send Via MargBooks, Send Via Whatsapp Web, Integrate Your Own WhatsApp Businees Number (sic). "Transaction Message": combobox Transaction Type (Sale [selected], Sale Return, Purchase, Purchase Return, Cancelled Invoice, Loyality (sic), Purchase Order, Sale Order) and a "Message Preview" box with "Transaction Image Attached" |

## Behaviour seen live

| Ref | Action | Seen |
|---|---|---|
| EM-01 | Open Control Room > Email Settings | type links listed as above; Payment Reminder selected first |
| EM-02 | Select Sale-Bill | heading "Sale-Bill"; default template row as above |
| EM-06 | "+ New", F10 Save with all fields empty | no request sent; Name and Subject get a "!" marker; Name tooltip "Name required !"; form stays open |
| EM-06b | Name and Subject filled, body empty, F10 Save | no request sent (guard saw none); no toast; Name keeps a "!" marker without tooltip. Unclear what is still missing (N3) |
| EM-07 | Type "not-an-email" + Enter in CC | error toast "Please Enter A Valid Email Id!"; CC stays empty; focus moves to BCC |
| EM-08 | Esc Close on a dirty new template | no confirmation; back to the type list; nothing added |
| EM-03 | Clone on the Sale-Bill default | form opens with Name empty, Subject "Sale-Bill Invoice", "Set as default" unchecked |
| EM-03b | "+ New", type a name, Esc Close, then Clone | Clone opens with the discarded name in Name, also on a second Clone (D2; seen in 3 probes and the test run) |
| EM-09 | Email Preference | default sender row as above |
| SM-01 | Open SMS Settings | DLT banner, Marg Books and SMS Bazaar panels |
| SM-06 | Configure DLT Registration > Save with both fields empty, and again with "abc" / "12" | popup closes; no request sent (all non-GET requests were blocked and logged: none); no message; fields empty when reopened (N2) |
| SM-07 | Configure DLT Registration > Cancel | popup closes; fields unchanged |
| WA-01 | Open Transaction SMS | buttons and combobox as above |
| WA-02 | Choose a transaction type | no request sent. Preview text per type: Sale Return "We have created a credit note to you as below:", Purchase "Recently, we have made a purchase with you.", Purchase Return "We have created a debit note to you as below:", Cancelled Invoice "Your Invoice No.CH7889 has been cancelled.", Loyality "Your exclusive store points ...". Sale, Purchase Order and Sale Order: preview empty (D1) |

## Defects (suspected)
- D1: Transaction SMS > Transaction Type "Sale" (the default selection) shows an empty Message Preview, also after choosing another type and coming back; Purchase Order and Sale Order are empty too. KB says choosing Sale shows the "Transaction Type Message Preview" (`careportal_enriched_v5.csv#bc739708`). Expected: the Sale message preview; actual: empty box.
- D2: Email Settings > Sale-Bill > "+ New", type a Name, Esc Close, then Clone on the default template. Expected: Name empty (as on a fresh Clone). Actual: the discarded name is in Name (`test_clone_does_not_keep_the_name_of_a_discarded_template`). A user saving that clone would save it under the wrong name.

## NEEDS DECISION
- N1: Email template CRUD. "+ New" and Clone save into `TemplateDetails` (CODE `codekb:MargBooks:api#bd0d5309`), but the template rows show no edit or delete control and no screen calls `usp_TemplateDetailsDelete` (CODE `codekb:MargBooks:schema#5c459cc7`). A saved test template could not be removed and would show up in every company user's template list (and in share-by-email pickers, `ShareComponent`). Not automated until a delete path exists or QA allows a permanent `QA-` template.
- N2: DLT Save closes the popup without a request or message, with empty or junk values. Is a client check missing, or is DLT Save disabled for this company? Not automated beyond Cancel.
- N3: What makes the email template form refuse Save when Name and Subject are filled (body empty, From empty)? No message is shown.
- N4: SMS templates (Clone / Preview per transaction type, KB `careportal_enriched_v5.csv#68506e06`) are not reachable on this company: SMS Settings shows only the DLT banner and provider panels until DLT is configured. Configuring DLT is a tenant-wide change and is not done.
- N5: WhatsApp SMS type buttons, personal WhatsApp QR linking and the WhatsApp Business integration are not exercised (they change the tenant's sending channel or link a device).
- N6: The Control Room is opened by URL `/mstr/margsetup-controlroom` in all but one test, because the Settings > Configure clicks were lost under load. One test keeps the menu path covered. Acceptable?
