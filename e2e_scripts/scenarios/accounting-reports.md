# Scenario pack: trial balance / P&L / day book (J19, journey id `accounting-reports`)

Status: DRAFT for QA/BA review (2026-10-08). Priority P1, layers e2e + api. Plan: `specs/accounting-reports.md`.

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`.
- CODE = a code-index chunk from the same KB (`codekb:MargBooks:*`). `ask_codebase` was not used.
- LIVE = seen on the QA tenant (garments account) by the planner's probes on 2026-10-08.
- UNVERIFIED = not citable; the question is stated, no value invented.

Rule for this journey: the tenant is shared and other tests post vouchers in parallel, so no scenario asserts an absolute tenant total. Each scenario checks lines of the test's own ledgers and vouchers, or an invariant that holds whatever the tenant holds.

Facts
- Report > "Combined Report" > "Accounts Report" tab lists Ledger, Day Book, Trial Balance, Cash/Bank Books, Group Summary, Outstanding, Books of Account, Final Account (Profit & Loss, Balance Sheet). `careportal_enriched_v5.csv#7973b72d`, `#e920ef82` (transcript); LIVE
- Trial Balance: account groups, "Expand All" shows ledger-wise details, Enter on a group drills down, Date filter (Alt+D), "Trial Balance Configuration" turns the opening balance on or off. `careportal_enriched_v5.csv#7973b72d`, `#fba17458`, `#95b3de8a`
- Trial Balance differences come from mismatched vouchers or opening balances; "Show Opening Balance" = Yes shows them. `careportal_enriched_v5.csv#665e010c`
- Profit & Loss: Date filter, "Configuration" (opening balance on/off), Excel/PDF export. `careportal_enriched_v5.csv#ba1945b8`
- Day Book: all day-wise entries (Sale, Purchase, Payment, ...), modify/delete/export/print/share; voucher number column can be enabled in settings. `careportal_enriched_v5.csv#0b03a9b1`, `#6b961b40`, `#ed3ac9a7`
- API: `POST /Reports/TrialBalanceReport`, `POST /Reports/GetTBReportData`, `POST /Reports/GetDayBookReportData` (procs `USP_TRIALBALANCENew`, `RPT_ProfitLoss`). CODE `codekb:MargBooks:api#3a5308c6`, `#de9271e1`, `#d32a3c1f`
- LIVE: pages `/report/trialbalance/tb-group`, `/report/daybook/db-default` (opens on today), `/report/profitloss` (first asks "Stock Valuation: Update Balance Sheet Stock?" No / Current Date / All Days). Trial Balance shows opening balances by default and a "Difference in Trial Balance" line that balances the grand totals.

## J19 Accounting reports

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| AR-01 | positive | Own party with opening balance 1500 Dr; Trial Balance, Expand All | Party row: Debit 1500.00, Credit empty | KB `#7973b72d`; LIVE |
| AR-02 | invariant | Trial Balance grand totals | Debit total = Credit total | KB `#665e010c` (difference concept); LIVE |
| AR-03 | positive | Own journal today: Dr own Indirect Expenses ledger 250, Cr own Indirect Incomes ledger 250; Day Book | Two lines, same voucher number, type "Journal", 250 Dr / 250 Cr | KB `#0b03a9b1`; LIVE |
| AR-04 | positive | Same journal; Profit & Loss, Expand All | Own expense ledger 250.00 on the expense side, own income ledger 250.00 on the income side | KB `#ba1945b8`; LIVE |
| AR-05 | state | Delete the journal; Day Book again | Lines gone. UNVERIFIED (not asserted; cleanup only) | UNVERIFIED |
| AR-06 | positive | Trial Balance with opening balance off (Configuration) | Own party opening not shown. Not automated: tenant-wide setting, other tests read the report in parallel | KB `#95b3de8a` |
| AR-07 | boundary | Date filter From = To = voucher date / day after | Included / excluded. UNVERIFIED | UNVERIFIED |
| AR-08 | positive | Export Excel/PDF of each report | File downloads, figures match screen. UNVERIFIED | KB `#ba1945b8`, `#6b961b40` |
| AR-09 | invariant | P&L net result equals Balance Sheet profit/loss line | UNVERIFIED | UNVERIFIED |
| AR-10 | tenancy (api) | Report API with company A token and company B id | Rejected or empty. UNVERIFIED | CODE (endpoints only) |
| AR-11 | permission | User without "Day Book" right | Denied. Rights are assigned per role (KB) | KB `#44a76d11` |
