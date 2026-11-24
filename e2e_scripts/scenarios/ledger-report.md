# Scenario pack: ledger report matches transactions (J12, journey id `ledger-report`)

Status: DRAFT for QA/BA review (2026-10-07). Priority P1, layers e2e + api. Plan: none yet (`specs/ledger-report.md` to be written by the planner from the live app).

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`. Not observed live; a human confirms each against the app before a test asserts it.
- CODE = would cite `file:line`. `ask_codebase` failed (no Anthropic API key configured in the radar admin settings; one attempt, not retried), so NO code citations exist in this pack.
- UNVERIFIED = not citable; the question is stated, no value invented.
- Not observed live in this pack. Menu paths, selectors and numbers come from KB text only.

Facts from the KB (all KB, none live)
- Ledger report path A: Report > "Combined Report" window > "Ledger" under the "Accounts Report" tab > "Ledger Master" window: search and select a ledger, press Enter to see the detailed report. Date via the Date field or Alt+D ("Date Filter" window, OK). Filter via button or Alt+F ("Advanced Filter"). `careportal_enriched_v5.csv#19614629`
- Ledger report path B: Master > Account Master > Ledger > "Ledger Master" window lists all ledgers with balances; Enter on a ledger opens its transaction report; Excel, PDF, Print and Share (WhatsApp, Email, Drive) icons. `careportal_enriched_v5.csv#d596ad1b`, `#306f9a59`
- Ledger display options (General Setup): Show Voucher Number, Show Debit/Credit Entries (Dr only, Cr only, All), Set Multicurrency, Load Challan, Show Ledger Name. `careportal_enriched_v5.csv#ae5bd4cb`
- F10 Filter on the all-ledger transaction report: Account Group, Ledger Category, Country, Station (and more, truncated). `careportal_enriched_v5.csv#a746b97e`
- Export formats named: Excel, PDF, Word, CSV; Print; Share via WhatsApp, Email, Drive. `careportal_enriched_v5.csv#b541ba40`
- PDF export has a "Configure" button with a "Current View" option. `careportal_enriched_v5.csv#306f9a59`
- Trial Balance (to reconcile with ledger): date filter, Opening Balance on/off in "Trial Balance Configuration", Expand All, Enter on a group drills to ledgers. `careportal_enriched_v5.csv#fba17458`, `#7973b72d`
- Ledger opening balance is set in Master > Opening Balance > Ledger; removing it requires switching to the Previous Financial Year. `careportal_enriched_v5.csv#41450cdc`
- Mobile app Ledger Book: More > Reports > Ledger, calendar period (e.g. Current Year), pick ledger, Edit icon modifies the entry. Mobile only, out of web scope. `careportal_enriched_v5.csv#ab22e1bc`

## J12 Ledger report

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| LR-01 | positive | Open Report > Combined Report > Accounts Report > Ledger | "Ledger Master" window appears; selecting a ledger and pressing Enter shows its detailed report | KB `careportal_enriched_v5.csv#19614629` |
| LR-02 | positive | Open Master > Account Master > Ledger | "Ledger Master" window lists all ledgers with their balances | KB `careportal_enriched_v5.csv#d596ad1b` |
| LR-03 | positive | Create a sales invoice for a new party (own data), open that party's ledger report for the invoice date | Ledger shows one entry for the invoice on the debit side with the invoice total. Exact column names, Dr/Cr placement and amount: UNVERIFIED (no KB value; confirm live) | UNVERIFIED |
| LR-04 | positive | Ledger closing balance after one sale and one receipt for a new party | Closing balance = opening + debits - credits. Formula is accounting convention, not cited; displayed sign and Dr/Cr label UNVERIFIED | UNVERIFIED |
| LR-05 | positive | Ledger total debit and credit equal the sum of the visible rows | Totals equal sums of listed rows (edge checklist "totals reconcile"). Footer layout UNVERIFIED | UNVERIFIED |
| LR-06 | positive | Party created with an opening balance in Master > Opening Balance > Ledger, report for the full FY | Opening balance appears as the first line / opening figure. Presentation UNVERIFIED | KB `careportal_enriched_v5.csv#41450cdc` (where it is set only) |
| LR-07 | positive | Date filter: set From/To via Date field or Alt+D, click OK | Report shows only entries in the range; "Date Filter" window appears | KB `careportal_enriched_v5.csv#19614629` |
| LR-08 | boundary | Date range starts the day after an entry | Entry excluded; opening figure for the range includes it. Whether the report carries a brought-forward line: UNVERIFIED | UNVERIFIED |
| LR-09 | boundary | Range equals one day equal to the entry date (From = To) | Entry included. Inclusive-boundary rule UNVERIFIED | UNVERIFIED |
| LR-10 | boundary | FY boundary: entries on 31-03 and 01-04 across two FYs | Each FY report shows only its own entries; opening of the new FY carries the closing of the old. Carry-forward rule UNVERIFIED | UNVERIFIED |
| LR-11 | positive | Advanced Filter (Alt+F) opens | "Advanced Filter" window appears with selectable criteria; criteria list truncated in KB | KB `careportal_enriched_v5.csv#19614629` |
| LR-12 | positive | All-ledger report filtered by Account Group (for example Sundry Debtors) | Only ledgers of the chosen group are listed | KB `careportal_enriched_v5.csv#a746b97e` |
| LR-13 | positive | All-ledger report filtered by Ledger Category, Country, Station | Only matching ledgers listed | KB `careportal_enriched_v5.csv#a746b97e` |
| LR-14 | positive | Setting "Show Debit/Credit Entries" = Dr only / Cr only / All | Report lists only debit rows / only credit rows / all rows respectively | KB `careportal_enriched_v5.csv#ae5bd4cb` |
| LR-15 | positive | Setting "Show Voucher Number" on vs off | Voucher number column present vs absent. Exact option labels UNVERIFIED | KB `careportal_enriched_v5.csv#ae5bd4cb` |
| LR-16 | positive | Setting "Show Ledger Name" on vs off, "Load Challan" on vs off | Ledger name / challan details displayed or hidden per option | KB `careportal_enriched_v5.csv#ae5bd4cb` |
| LR-17 | positive | Export ledger report as Excel | File generated for the selected party; its rows and closing balance match the screen | KB `careportal_enriched_v5.csv#b541ba40`; match rule from edge checklist |
| LR-18 | positive | Export as PDF with Configure > Current View | PDF reflects the current on-screen view (filters, range) | KB `careportal_enriched_v5.csv#306f9a59` |
| LR-19 | positive | Export as CSV and Word | Formats offered in the Export window | KB `careportal_enriched_v5.csv#b541ba40` |
| LR-20 | positive | Print icon | Print preview/dialog opens. Behaviour in headless browser UNVERIFIED | KB `careportal_enriched_v5.csv#b541ba40` |
| LR-21 | positive | Share via WhatsApp / Email / Drive icons are present | Three share options shown. Delivery not automatable (external services); presence check only | KB `careportal_enriched_v5.csv#d596ad1b` |
| LR-22 | positive | Reconcile with Trial Balance: ledger closing balance equals its Trial Balance figure for the same date range with Opening Balance on | Same amount and Dr/Cr side | KB `careportal_enriched_v5.csv#fba17458`, `#7973b72d` (drill-down exists); equality rule from edge checklist |
| LR-23 | positive | Reconcile with the sale invoice: invoice grand total equals the ledger debit for that party | Equal to the paisa (use Decimal). Invoice screen total is covered by J05 | edge checklist "totals reconcile"; value UNVERIFIED |
| LR-24 | positive | Reconcile with GST: tax ledgers (output CGST/SGST/IGST) show the invoice tax split | CGST+SGST for intra-state, IGST for inter-state. Ledger names UNVERIFIED | UNVERIFIED |
| LR-25 | state | Edit a posted invoice amount, reopen ledger | Ledger reflects the new amount, no duplicate row | UNVERIFIED |
| LR-26 | state | Cancel/delete the invoice, reopen ledger | Entry removed or reversed. Which of the two: UNVERIFIED | UNVERIFIED |
| LR-27 | state | Ledger with no transactions in range | Empty state or only opening figure; no error. Wording UNVERIFIED | UNVERIFIED |
| LR-28 | boundary | Odd paise: invoice with total ending in .5 paise rounding | Ledger shows the rounded invoice total and a round-off line if the app posts one. Round-off ledger behaviour UNVERIFIED | UNVERIFIED |
| LR-29 | boundary | Very large amount (for example 9,99,99,999.99) | Displayed without truncation, Indian digit grouping assumed. UNVERIFIED | UNVERIFIED |
| LR-30 | boundary | Ledger name with unicode / special characters / long name | Name searchable in "Ledger Master" and printed intact. Max length UNVERIFIED | UNVERIFIED |
| LR-31 | negative | Search for a ledger that does not exist in "Ledger Master" | No result; no report opens | UNVERIFIED (behaviour implied by KB search step, `#19614629`) |
| LR-32 | permission | Limited user (no report right) opens the ledger report by menu and by direct URL | Denied or redirect. Rule UNVERIFIED; no limited account known to exist (see auth pack Q3) | UNVERIFIED |
| LR-33 | tenancy | Company A ledger entries never appear in company B's ledger report (same party name in both) | Company B report shows only company B entries | edge checklist; value UNVERIFIED |
| LR-34 | tenancy (api) | API: request ledger data with company A token and company B company id | Rejected or empty. Endpoint name UNVERIFIED (`ask_codebase` unavailable) | UNVERIFIED |
| LR-35 | duplicate | Refresh the report mid-load / open the same ledger twice quickly | Same figures, no doubled rows | UNVERIFIED |
| LR-36 | api | Ledger API figures equal the UI figures for the same party and range | Equal totals and row count. Endpoint and payload UNVERIFIED | UNVERIFIED |
| LR-37 | positive | Mobile app Ledger Book (More > Reports > Ledger) | Out of scope for the web suite; recorded only | KB `careportal_enriched_v5.csv#ab22e1bc` |

## KB vs live app (for a human to decide)
1. Two entry points exist in the KB (Report > Combined Report > Ledger, and Master > Account Master > Ledger). Both must be checked live; they may open different screens (LR-01, LR-02).
2. KB mentions both the Ledger Master window and an "All Ledger Transaction Report" with F10 Filter; the F10 criteria list is truncated and the live shortcut (F10 vs Alt+F) may differ.
3. Several KB articles describe the desktop-style flow (Enter, Alt+D, Alt+F); the Angular web app may not honour keyboard shortcuts the same way. Confirm live.
4. The "Ledger Book" article describes the mobile app, not web. Not used for expected values.
5. KB gives no figures, column names, Dr/Cr rules or reconciliation rules for the ledger. Every numeric expectation here is UNVERIFIED and must be set from the live app by the planner.
6. KB confirms ledger opening balance is a master-level input that must be edited in the previous FY to remove; this may block the FY-boundary tests (LR-10) from cleaning up.
7. No code was read: `ask_codebase` failed. `get_module_info`/`get_file` were not used because the module and file ids are unknown.

## Open questions
- Q1 Which ledger screen is the canonical one for the journey: Combined Report > Ledger or Master > Account Master > Ledger?
- Q2 Column set, Dr/Cr sign convention and closing-balance display?
- Q3 Is the date range inclusive on both ends, and does the report show a brought-forward line?
- Q4 Does cancel/delete of an invoice remove or reverse the ledger entry?
- Q5 Which API endpoint backs the ledger report (needed for the api layer)? Needs the radar API key or a developer.
- Q6 What do limited roles see (needs a non-admin account, as in auth Q3)?
- Q7 Is export content comparable in an automated test (Excel/CSV parse) and is download enabled in the QA tenant?
- Q8 Does the app post a round-off ledger line for odd paise?
