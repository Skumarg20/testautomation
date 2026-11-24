# Plan: J11 bank entry and bank reconciliation (bank-entry-reconciliation)

Scenario pack: `scenarios/bank-entry-reconciliation.md`. Tests: `tests/journeys/banking/test_bank_reconciliation.py`.
Status: DRAFT for QA/BA review. Everything below was observed live on 2026-10-08 (QA tenant, `garments` login, company "Garments New 29-08 (GANE29)", books 01-04-2026..31-03-2027). No screen in this journey has test ids; locators fall back to roles, element ids and ag-Grid `col-id`s.

## Preconditions and test data
- The tenant has NO bank ledger: the Bank Reconciliation "Select Bank" list was empty and the Payment Mode typeahead offered only "Cash Account". Every test therefore creates its own ledgers (fixture `bank_book`, `fixtures/bank_book.py`):
  - bank ledger `QA-<run_id>-Bank-1`: group "Bank Accounts", station "Others", Account No "1234567890" (Station and Account No are mandatory for this group; without a station the save fails with toast "Invalid StationLinkID").
  - expense ledger `QA-<run_id>-Exp-2`: group "Indirect Expenses" (form shows only GST Applicable and opening balance).
- Vouchers: payment 1000.50 by cheque 100001 and/or receipt 400.25 by cheque 200002, bank = own bank ledger, account = own expense ledger, date today.
- Teardown, in this order (the app refuses otherwise): remove clearing dates the test set, delete the vouchers, delete the expense ledger, delete the bank ledger. A ledger with vouchers is refused with toast "Transaction Available"; a reconciled voucher is refused (BK-15).
- No tenant-wide setting is changed. Not in an xdist group: all balances asserted belong to the test's own ledgers.

## Locators (verified live)
| Thing | Locator |
|---|---|
| Menu | sidebar Accounting Trans. > Bank Reconciliation (route `/banking/reconciliation`); `AccountingMenu.open_bank_reconciliation` |
| Ledger create | Master > Accounts Master > Ledger, F2; `#txtlegername`, `#drpAccountGroup`, `#ddlstation` (typeaheads, `listbox` > `option`), `#txtAccountNo`, `#btn-Save`; toast "Record Saved Successfully." (reuses `pages/masters/ledger_form.py`) |
| Payment/Receipt mode | combobox "Search here.." (`drpPaymentModeAutocomplete<n>`), default "Cash Account" |
| Voucher grid (bank mode) | col-ids `voucherNo` (filled only in bank mode, provisional until saved), `ledgerLinkID`, `entryDate`, `drAmount`, `station`, `instype` (default "Cheque"), `insno` (popup editor `#txt-insno-0`, max 6 chars, opened by double click), `crAmount` |
| Cheque prompt | after a payment cheque number: alert "Do you want to create cheque book ?" Yes/No (`#btnYes`/`#btnNo`, both aria-label "Close"). Tests answer No. Receipts do not ask. |
| Save without cheque | toast "Please Fill Cheque No." |
| Saved | toast "Payment Voucher Saved Successfully !" / "Receipt Voucher Saved Successfully !" |
| BRS bank | `select#searchItems` (formcontrolname `bank`), options = bank ledgers |
| BRS range | two textboxes (From/To), default = current month (01-10-2026..31-10-2026). The list loads only after Enter in the To date. |
| BRS grid | col-ids `BillDate`, `DataType` (Trans.Type), `LedgerName`, `InstrumentType`, `InstrumentNumber`, `Debit`, `Credit`, `ClearingDateSelectedDate` |
| BRS summary rows | label in `InstrumentType`: "₹ Total", "₹ Difference", "Computer Balance", "Bank Balance" |
| Views | links "E Cleared Entry", "U Un-Cleared Entry"; also "D Date", "B Opening BR", "C Clear All", "N Entry" (not used) |
| Clearing date | input `#txt-ClearingDateSelectedDate-<row>` in the cell; Enter on an empty input fills today and saves: toast "Record Updated Successfully." |
| Voucher delete | open the voucher from the account's ledger report (double click the voucher number), button "Del Delete", alert "Are you sure you want to delete the selected Record?", toast "Voucher Record Deleted Successfully." |

## Observed behaviour (asserted)
- BK-01/BK-17: a bank payment is listed with BillDate = voucher date, Trans.Type "Payment", Ledger = account, Inst.Type "Cheque", Inst.No = cheque number, amount in the **Debit** column, Clearing Date empty.
- BK-02: a bank receipt is listed with its amount in the **Credit** column.
- Default view after loading = un-cleared entries only.
- BK-18/21/22: Enter in an empty Clearing Date sets today; the entry leaves the default (un-cleared) view and appears in "E Cleared Entry" with that date.
- BK-23: emptying the Clearing Date and leaving the cell (no Enter) saves `ClearingDateSelectedDate: null` (POST `BankReconciliation/Update`) and the entry returns to the un-cleared view.
- BK-15 (answers Q3): deleting a reconciled voucher is refused with toast "Voucher Already Reconcile Of Date <dd-mm-yyyy>". The toast came straight after Delete in some runs and only after the user confirmed "Are you sure you want to delete the selected Record?" with Yes in others.
  - DEFECT CANDIDATE (intermittent): in the run of 2026-10-08 around 23:50 IST, the app deleted a cleared payment after Yes was confirmed: no refusal toast, the voucher was gone from the ledger report and the BRS cleared view, and both ledgers then deleted without "Transaction Available". Steps: bank payment by cheque > clear it in Bank Reconciliation (toast "Record Updated Successfully.") > open the voucher > Delete > Yes. Expected: refusal "Voucher Already Reconcile Of Date …", voucher kept. Actual: voucher deleted. The run crossed midnight, so a date-boundary check is a suspect. The test stays as written and fails when this happens.
- BK-31 (books side): "Computer Balance" = bank ledger closing balance. After payment 1000.50 + receipt 400.25: Computer Balance Credit 600.25; bank ledger report closing "600.250 Cr".
- BK-29 (partly answered): the clearing-date picker has `min` = voucher date, so a date before the voucher date cannot be picked.

## NEEDS DECISION
1. Debit/Credit convention: the list shows a payment (money out of the bank) under Debit and a receipt under Credit (bank-statement view), while "Computer Balance" uses the books view (Credit 600.25 when the books say 600.25 Cr). After clearing the 1000.50 payment, "Bank Balance" showed **Debit** 1,000.50. Is the mixed convention intended? Tests assert only the list columns and Computer Balance, not Bank Balance.
2. BK-23 usability: pressing Enter after clearing the date re-fills today (same as BK-18), so the only way to un-clear is to empty the field and leave it. KB says "removing the date" un-clears; confirm this is the intended interaction.
3. Payment/Receipt list: on 2026-10-08 the Payment list (range "Today" and "This Week") showed no rows while bank payments of that day existed (visible in the ledger report and BRS). Not asserted; needs a manual check before it is filed as a defect.
4. Voucher numbers in bank mode are tenant-wide sequential (0000014..0000022 seen). The number the new-voucher grid shows before saving is provisional: in a run with two workers the grid showed 0000017 and the voucher was saved as 0000018, with no message to the user. Is that intended (BK-10 area)? Payments and receipts appear to be numbered in separate series (a payment and a receipt of one test were both saved as 0000020), and numbers of deleted vouchers are reused. Tests therefore read the saved number of the same voucher type from the account's ledger report, and teardown opens a voucher from its own ledger's report (account + number), never by number alone.
5. "Do you want to create cheque book ?" after every unknown cheque number: BK-06/BK-07 (cheque book) not automated; tests answer No.

## Not covered (and why)
- BK-03/BK-04/BK-05/BK-24 contra (cash/bank, bank-to-bank): not probed in the time box; BK-24 needs two own banks.
- BK-06..BK-09 cheque books and duplicate cheque rules (Q1): need a cheque-book flow and rules from BA.
- BK-12/BK-13/BK-14 negatives and boundaries for bank vouchers; BK-16 PDC; BK-19 Clear All by slip; BK-20 remark; BK-25/BK-26/BK-30 old-FY and typed dates; BK-32..BK-35 statement import / auto / online banking; BK-36/37 permissions and tenancy (no limited user, no second company with bank data).
