# Spec: cash-transfer-day-closure (J29, P2) - DRAFT for QA/BA review

Scenario pack: `scenarios/cash-transfer-day-closure.md`. Tests: `tests/journeys/cash_transfer/`.
Account: `garments` (super-admin), company "Garments New 29-08". Explored live 2026-10-09 (app V. 4.3.598.b).

## 1. What was seen live

### Contra (Accounting Trans. > Contra)
- List "Contra Voucher List" at `/transaction/voucher/contra/55`, button `Create/F2`; empty state
  "No Contra Voucher List Created Yet" when there are no vouchers in the default (today) range.
- New voucher: header `Date` (dd-mm-yyyy, defaults to today) and `Voucher No.` (next tenant-wide number,
  e.g. `0000001`). Grid columns: S.No., Cr./Dr., Account, Station, Inst. Type, Inst. No, Debit, Credit.
  Row 1 starts as `Cr`. Footer shows Dr/Cr totals and "Current Balance". Narration box, `F10 / End Save`.
- Own ledgers work: a new ledger in group **Cash-in-Hand** and a new ledger in group **Bank Accounts**
  (station Others, account no.) can both be picked in the contra account popup.
- Picking a **bank** ledger sets Inst. Type to `Cheque`. Saving with an empty Inst. No is refused with the
  warning toast **"Please Fill Cheque No."** and focus moves to Inst. No (CT-07). Inst. No accepts at
  most 6 characters. After a cheque number is entered (Enter) the app asks "Do you want to create cheque
  book ?" (Yes/No); the tests answer **No** so no cheque book is created.
- Save (End) with both legs and a cheque number shows a success toast; the voucher appears in today's
  list with columns Date, Voucher No, Party Name (the Cr ledger, i.e. the cash ledger), Station,
  Inst. Type. (`Cheque`), Inst. No., ₹ Amount (`500.00`), Action.
- Double-clicking the row opens the voucher read-only with buttons `F3 Modify`, `Del Delete`, `P Print`,
  `Esc Close`. Delete key + Confirmation "Yes" deletes it.
- Day Book (`/report/daybook/db-default`, today): one row per leg, e.g. Ledger = cash ledger,
  VoucherNo `0000001`, VoucherType **`Contra`**, Debit empty, Credit `500`.
- Right after saving, the sidebar link can be "not stable"; the page objects open the dashboard first.
  The expanded sidebar also covers the list's Date column, so rows are opened by their Party Name cell.
- Modify (F3) lets both amounts be retyped; Save confirms with a success toast.
- Unequal Dr (750) and Cr (500) amounts: Save is refused with a warning toast (CT-08).
- Balances are read from each ledger's own report (Ledger : name, "₹ Balance" running balance). A ledger
  without vouchers shows only the column headers and no "Total" row; that is read as zero.
  (Reading the balance from Master > Ledger list with "Single Ledger Refresh", as the accounting suite
  does, did not find the row of a new Cash-in-Hand ledger within 30 s; not investigated further.)

### Daily Cashbook / day closure
- `/openclosecashbook`, `/stopbilling`, `/cashTransfer`, `/dayclosureapproval`: all show
  **"Oops! You are not authorized."** for the super-admin. The sidebar has no "Daily Cashbook" group.
  Interpretation: Control Room "Daily Cashbook" is off on this tenant (DC-01 says the module appears only
  when it is Yes).
- `/closingDayReport` opens: heading **"Close Billing/Day"**, "Total Users : 0", "Prev. Closing Day & Net
  Cash : ₹ 0.00 as on", "Closing Date : <today>", Selected Date Range From/To both today, a
  S.No./User Name/(₹) Net Cash table (empty), Opening Cash / Total Cash Sale / Total Cash Expenses /
  Net Cash all ₹ 0.00, and a button "Go to manage Approvals" (leads to the unauthorized approval screen).
  There is **no close-day button** on this screen in the current state.
- `/dailycashbookphysicalcount` ("Daily Cashbook Physical Stock") opens with Outlet, User List, Closing Date
  and Submit. Not used (Submit would write a physical-stock day record).

## 2. What the tests cover

| Test | Scenario | Notes |
|---|---|---|
| deposit saves and moves both balances | CT-01, CT-02 | own cash + bank ledgers, Cr cash / Dr bank, cheque no. given |
| contra lines in Day Book | CT-03 | both lines, same voucher no., type as shown |
| contra in own ledger report | CT-02 | cash ledger report shows the credit |
| modify amount moves balances to the new amount | CT-05 | |
| delete restores both balances | CT-06 | |
| missing cheque no. refused | CT-07 | warning toast text |
| unequal amounts refused | CT-08 | |
| Close Billing/Day screen read-only | DC-06 | heading, closing date and range = today; no write |
| Daily Cashbook screens not authorized while setting is off (4 routes) | DC-01 | guards the NEEDS DECISION 1 state; fails if someone turns the module on |

Every test owns its ledgers (`QA-<run_id>-Cash-n`, `QA-<run_id>-Bank-n`); vouchers are deleted, then the
ledgers. The voucher number is tenant-wide, so the module is in `xdist_group("chemist-tenant")` like the
other contra tests.

## 3. NEEDS DECISION

1. **Day closure (DC-01..DC-05) is not automated.** It needs Control Room "Daily Cashbook" = Yes, a
   tenant-wide switch that makes Start Billing mandatory for every sale bill (DC-02) and would break the
   other suites running on the same login. No reopen/undo of an approved day was found in the KB or the UI.
   Options: (a) a dedicated tenant/company with Daily Cashbook on, (b) accept toggling it in a
   serial-only run with restore in teardown. Until then only the read-only Close Billing/Day screen is tested.
2. **"Closing restrictions" (editing a voucher dated in a closed day)** cannot be tested without (1).
   Transaction Locking (`dbo.TransactionLock`) is the general lock feature; it is tenant-wide too and was
   not touched.
3. Is the Contra cheque-number rule intended for cash deposits into a bank (Inst. Type defaults to Cheque
   for every bank leg)? The test passes a cheque number; QA/BA to confirm whether "Cash"/no instrument
   should be allowed.
