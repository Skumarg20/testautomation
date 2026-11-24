# Plan: J19 trial balance / P&L / day book (accounting-reports)

Scenario pack: `scenarios/accounting-reports.md`. Tests: `tests/journeys/accounting/test_accounting_reports.py`.
Status: DRAFT for QA/BA review. Observed live on 2026-10-08 (QA tenant, `garments` login, books 01-04-2026..31-03-2027).

## Preconditions
- Session `page_as("garments")`, dashboard open (`accounting_page`).
- Own data only: ledgers `QA-<run_id>-...` created through Master > Opening Balance > Ledger (`OpeningBalancePage`), deleted by `owned_ledgers` at teardown. The journal voucher of AR-03/AR-04 is deleted from the Journal list before its ledgers.
- The module runs in `xdist_group("chemist-tenant")` like the other journal tests (tenant-wide voucher numbering).
- No report configuration is changed (the configuration is tenant-wide).

## Locators (verified live)
| Thing | Locator |
|---|---|
| Trial Balance | `/report/trialbalance/tb-group`, h1 "Trial Balance"; button "+ Expand All" / "- Collapse All" (state is remembered between visits); grid columns "Account Group", "₹ Debit", "₹ Credit"; second grid row "Grand Total" |
| Day Book | `/report/daybook/db-default`, h1 "Day Book", opens on today's date; ag-Grid `col-id`s `Date`, `Ledger`, `VoucherNo`, `VoucherType`, `Debit`, `Credit`, `User`; one row per voucher line |
| Profit & Loss | `/report/profitloss`, first a dialog "Stock Valuation" ("Update Balance Sheet Stock?" No / Current Date / All Days): the test answers No; h1 "Trading, Profit and Loss Account"; expenses in `col-id` `First`/`FirstTotalAmount`, incomes in `Second`/`SecondTotalAmount` |
| Journal | `JournalPage` (existing) to post; Journal Voucher List shows today's vouchers, row double-click opens it, Delete key + "Confirmation" Yes |

All three grids render only visible rows, so the page object scrolls the grid until the wanted row shows.

## AR-A Own opening balance in the Trial Balance (AR-01)
Create a party with 1500 Dr, open Trial Balance, Expand All. Expect the party row: Debit 1500, Credit 0 (empty).

## AR-B Grand totals agree (AR-02)
Open Trial Balance. Expect Grand Total Debit = Grand Total Credit (read-only, no data needed).

## AR-C Day Book lists own journal (AR-03)
Create `Exp` (Indirect Expenses) and `Inc` (Indirect Incomes), post today's journal Dr Exp 250 / Cr Inc 250. Day Book: Exp line Debit 250, type "Journal"; Inc line Credit 250; both with the same voucher number.

## AR-D P&L shows own expense and income (AR-04)
Same journal. Profit & Loss, Expand All: Exp 250.00 on the expense side, Inc 250.00 on the income side.

## NEEDS DECISION
- Trial Balance balances its grand totals with a "Difference in Trial Balance" line (seen live: 1500.00 Cr while an unmatched 1500 Dr opening existed). AR-02 therefore checks the displayed totals, which are equal by construction. Should the suite instead assert that the difference line is zero? On a shared tenant with other tests creating one-sided openings it is not stable.
- Seen live: "Cash Account" with a credit balance (267390.00 Cr) and "Current Assets" net credit. Tenant data, not asserted; worth a look by QA.
- AR-05..AR-11 not automated (see the scenario pack for why).
