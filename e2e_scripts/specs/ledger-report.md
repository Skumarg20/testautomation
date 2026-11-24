# Plan: J12 ledger report matches transactions (ledger-report)

Scenario pack: `scenarios/ledger-report.md`. Tests: `tests/journeys/reports/test_ledger_report.py`.
Status: DRAFT for QA/BA review. Observed live on 2026-10-08 (QA tenant, `garments` login, company "Garments New 29-08 (GANE29)", books 01-04-2026..31-03-2027). No test ids on these screens.

## Preconditions and test data
- Same fixture as J11 (`bank_book`, see `specs/bank-entry-reconciliation.md`): a new bank ledger `QA-<run_id>-Bank-1` and a new expense ledger `QA-<run_id>-Exp-2`, so the report holds only the test's own vouchers (shared ledgers such as "Cash Account" are moved by other tests in parallel).
- Vouchers, both dated today, bank = own bank ledger, account = own expense ledger:
  1. Payment 1000.50, cheque 100001.
  2. Receipt 400.25, cheque 200002.
- Opening balance 0 on both ledgers. Teardown deletes the vouchers, then both ledgers.

## Screens and locators (verified live)
| Thing | Locator |
|---|---|
| Entry points | Report (sidebar) > Combined Report > Accounts Report tab > "Ledger" opens the Ledger Master list (`/partymaster/account-report`), the same list as Master > Accounts Master > Ledger (answers Q1: one screen). |
| Open a ledger's report | double click the ledger name cell in the list; route `/report/ledger/ld-standard/...`, heading "Ledger : <name>" |
| Default range | the whole financial year "01-04-2026-To- 31-03-2027", template "Standard" |
| Grid col-ids | `Date`, `VoucherNo` (Vch/Bill No.), `VoucherType`, `Debit` (₹ Debit), `Credit` (₹ Credit), `ClosingBalance` (₹ Balance, running, with Dr/Cr) |
| Total row | separate pinned grid, `Date` = "Total", debit and credit sums and the closing balance |
| Toolbar | links Excel, PDF, Back; shortcuts Alt+D Date, Alt+F Filter, Configuration, Alt+S Standard, Alt+A Daily, Alt+M Monthly, Alt+Q Quarterly |
| Drill down | double click a voucher number cell opens "Modify Payment Voucher" / "Modify Receipt Voucher" (used by teardown) |
Amounts in the report have 3 decimals ("1000.500", "600.250 Dr"); they are compared as `Decimal`.

## Observed and asserted (answers Q2 for vouchers)
Expense ledger report:
| Date | Vch/Bill No. | Voucher Type | Debit | Credit | Balance |
|---|---|---|---|---|---|
| today | payment number | Payment | 1000.500 | 0.00 | 1000.500 Dr |
| today | receipt number | Receipt | 0.00 | 400.250 | 600.250 Dr |
| Total | | | 1000.500 | 400.250 | 600.250 Dr |

Bank ledger report: Payment Debit 0.00 / Credit 1000.500, balance 1000.500 Cr; Receipt Debit 400.250, balance 600.250 Cr; Total 400.250 / 1000.500 / 600.250 Cr.

Tests: LR-03 (rows and amounts), LR-04 (running balance = previous + debit - credit), LR-05 (Total = sum of rows, closing = last running balance), bank mirror (opposite sides, closing 600.25 Cr).

## NEEDS DECISION
1. LR-03 as written uses a sales invoice. These tests use payment/receipt vouchers (the brief's choice) because a sale needs a party with mobile, items and stock. Add an invoice-based case when J05 data helpers are stable.
2. No opening-balance line is shown when the opening balance is 0. Presentation of a non-zero opening balance (LR-06) and of a brought-forward line for a later range (LR-08) is unverified.
3. Amount precision: the report prints 3 decimals while the voucher grid and BRS print 2. Confirm this is intended.

## Not covered (and why)
- LR-07..LR-10 date filter and FY boundary (Alt+D window not probed), LR-11..LR-16 filters and display settings (tenant-wide settings), LR-17..LR-21 export/print/share (downloads not probed), LR-22 trial balance (J19 owns it), LR-24 GST ledgers and LR-25..LR-28 invoice edits/round-off (need J05 sale data), LR-29..LR-31 boundaries, LR-32..LR-36 permissions, tenancy and API (no limited user, endpoint unknown).
