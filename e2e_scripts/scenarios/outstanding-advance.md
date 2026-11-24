# Scenario pack: party outstanding and advance (J10 `payments-ledger`)

Source of every case and expected value: `TestCase_Outstanding.xlsx` (Sheet1, "Outstanding / Advance — Base Case Test Scenarios (1–100)"), supplied by the test owner 2026-10-09. Expected values are copied, never recomputed. Rows the workbook itself contradicts are listed under "Needs decision" and are not resolved here.

Tests: `tests/journeys/accounting/outstanding/`. Case data: `test_data/outstanding_cases.py`.

## Definitions
- **Outstanding** = the party's unpaid bill balance (Dr). **Advance** = credit not adjusted against any bill (unadjusted receipt, excess sale return, advance receipt).
- Read from Report > Outstanding Report > Receivable > Ledger Wise (Enter on the filter, F7 "Show All Ledger"), then double-click the party: bill-wise view with columns Station, Bill No, Bill Date, Due Date, BillAmt, Adjustment, Outstanding, Narration and a "Grand Total" footer. Seen live 2026-10-09.
- KB: for Sundry Debtors, credit rows (unadjusted receipts, credit notes, advances) are negated, so they show as negative Outstanding; there is no separate advance column; zero-balance rows are dropped (`sp_OutstandingReportDetails`, code-kb `sql.jsonl` line 575, ~line 207). The tests therefore read outstanding as the sum of positive rows and advance as minus the sum of negative rows. **UNVERIFIED live** until a run shows an advance row.

## Business rules from the KB and code (cited)
| Rule | Source |
|---|---|
| Deleting a bill that has a receipt, adjustment or return linked is refused: "Can't Delete/Cancel Bill, Adjustment Available, Please Rollback the Adjusted Bill and Try Deleting" | `usp_ValidateSalePurchaseDelete` (`sql.jsonl` line 702), `Ledger.cs:4010-4040`, shown at `processout.transaction.component.ts:9898` |
| Bill-time payment above the bill amount: "Please Enter less then Bill amount" | `global.ts:19350` (`AlertMsg.BilAmountPayment`), `modeofpayment.component.ts:527,542,852` |
| Adjusting more than a bill's balance: "The entered amount cannot exceed the bill value N" | `bill.adjustment.new.component.ts:1424` |
| Saving the adjustment with an amount still pending asks "<n> Amount will be transfered into Advance. Want to proceed ?" and turns the rest into an advance | `bill.adjustment.new.component.ts:1687` |
| Bill Adjustment window: `#SearchBox`, Reference Type `#drpRefType` (receipt: "Agst Ref" = 1, "Advance" = 2), grid `#billAdjustmentGrid` (col-ids `cus_invoiceNo`, `billDate`, `dueDate`, `totalAmount`, `balanceAmount`, `adjustmentAmount`), footer "Adjusted Amount" / "Pending Amount"; Space select, F10 save, Esc close | live 2026-10-09; `bill.adjustment.new.component.html` |
| The window opens after the receipt amount is entered (Enter on the Short Amount cell) for a bill-by-bill party | live 2026-10-09 |
| Saving a sale bill opens "Mode Of Payment" (Bill Amount, grid Particulars / ₹ Amount / Remarks with Cash Account first, Balance Amount, Cash Tender, Cash Return, SAVE `#btn-Save`). The Cash Account amount (`#txt-amount-0`, focused on open) is the bill-time payment; 0 saves a credit bill. It shows because the Sale Bill Setting "Mode of Payment Required ?" is Yes on this company | live 2026-10-09; `modeofpayment.component.html` |
| After the payment window, a "Print" window (Select Format; Preview, Close, Print, Whatsapp) opens; Close leaves the bill saved | live 2026-10-09 |
| In the receipt's Bill Adjustment window, Space on a bill selects it, fills Adjusted Amt. with the smaller of balance and pending, and focuses `#txt-adjustmentAmount-<row>`; F10 closes the window; End saves ("Receipt Voucher Saved Successfully !") and leaves an empty receipt open | live 2026-10-09; `bill.adjustment.new.component.ts:1130-1200` |
| Bill-wise report after bill ₹105 and receipt ₹40 adjusted: BillAmt 105.00, Adjustment 40, Outstanding 65, Narration "Agst: <bill no>", footer Grand Total | live 2026-10-09 (party QA-6d113560-Cust-1) |
| Sale bill list (GST Invoice List) row actions: edit button (`button.mksBtn.edit`), print, and a ⋮ menu with Delete, Logs, Cash Receive (anchors without href, rendered outside the row) | live 2026-10-09 |
| New customer ledgers default to Balancing Method "Bill By Bill" | live 2026-10-09 |
| 0% item: "QA Outstanding Exempt Item" (Unit PCS, HSN 12345678, Tax Category "GST Sale-Exempt", Company Others, MRP 1,00,000, Sale Rate 1) created 2026-10-09; IGST/CGST/SGST 0.000; stock 0 | live 2026-10-09 |
| Party ledgers carry a Balancing Method (`#ddlBalancingMethod`); the adjustment window needs bill-by-bill (1 or 2) | `createledger.component.html:716-726`, `processout.transaction.component.ts:12052-12080` |

## Cases (copied from the workbook)
| ID | Title | Scenario | Flow | Expected outstanding (₹) | Expected advance (₹) | Workbook iteration 1 |
|---|---|---|---|---|---|---|
| OA-001 | Simple Credit Sale | Bill Amount = ₹1,000 | Create credit sale bill of ₹1,000 / Save bill | 1000 |  | Pass  |
| OA-002 | Sale Bill Modify (Increase Amount) | Original Bill = ₹1,000 / Modified Bill = ₹1,500 | Create sale bill ₹1,000 / Modify bill amount to ₹1,500 / Save bill | 1500 |  | Pass  |
| OA-003 | Sale Bill Modify (Decrease Amount) | Original Bill = ₹1,500 / Modified Bill = ₹1,000 | Create bill ₹1,500 / Modify bill to ₹1,000 | 1000 |  | Pass  |
| OA-004 | Bill Modify Below Already Adjusted Receipt | Bill Amount = ₹1,500 / Receipt Adjusted = ₹1,200 / Bill Modified To = ₹1,000 | Create bill ₹1,500 / Adjust receipt of ₹1,200 / Modify bill amount to ₹1,000 | 0 | 200 | Pass  |
| OA-005 | Multiple Bills – Same Party | Bill-1 = ₹1,000 / Bill-2 = ₹2,000 | Create first bill ₹1,000 / Create second bill ₹2,000 | 3000 | 0 | Pass  |
| OA-006 | Sale Bill Delete (No Adjustment) | Bill Amount = ₹1,000 | Create bill ₹1,000 / Delete bill | 0 | 0 | Pass  |
| OA-007 | Sale Bill with Partial Receipt | Bill Amount = ₹1,000 / Receipt = ₹400 | Create bill ₹1,000 / Adjust receipt of ₹400 | 600 | 0 | Pass  |
| OA-008 | Sale Bill with Full Receipt | Bill Amount = ₹1,000 / Receipt = ₹1,000 | Create bill ₹1,000 / Adjust receipt of ₹1,000 | 0 | 0 | Pass  |
| OA-009 | Sale Bill with Excess Receipt | Bill Amount = ₹1,000 / Receipt = ₹1,300 | Create bill ₹1,000 / Adjust receipt of ₹1,300 | 0 | 300 | Pass  |
| OA-010 | Receipt Modify (Increase) | Bill Amount = ₹1,000 / Receipt = ₹400 → modified to ₹700 | Create bill ₹1,000 / Adjust receipt ₹400 / Modify receipt to ₹700 | 300 | 0 | Pass  |
| OA-011 | Receipt Modify to Excess | Bill Amount = ₹1,000 / Receipt = ₹900 → modified to ₹1,200 | Create bill ₹1,000 / Adjust receipt ₹900 / Modify receipt to ₹1,200 | 0 | 200 | Pass  |
| OA-012 | Receipt Delete After Partial Adjust | Bill Amount = ₹1,000 / Receipt = ₹500 | Create bill ₹1,000 / Adjust receipt ₹500 / Delete receipt | 1000 | 0 | Pass  |
| OA-013 | Receipt Un-Adjust | Bill Amount = ₹1,000 / Receipt = ₹1,000 (adjusted) | Un-adjust receipt | 1000 | 1000 | Pass  |
| OA-014 | Receipt Without Bill (Advance) | Receipt Amount = ₹600 | Create receipt without selecting bill | 0 | 600 | Pass  |
| OA-015 | One Receipt Adjusted to Two Bills | Bill-1 = ₹600 / Bill-2 = ₹400 / Receipt = ₹1,000 | Adjust receipt to both bills | 0 | 0 | Pass  |
| OA-016 | Sale Return – Partial | Bill Amount = ₹1,000 / Sale Return = ₹300 |  | 700 | 0 | Pass  |
| OA-017 | Sale Return – Full | Bill Amount = ₹1,000 / Sale Return = ₹1,000 |  | 0 | 0 | Pass  |
| OA-018 | Sale Return Greater Than Bill | Bill Amount = ₹1,000 / Sale Return = ₹1,300 |  | 0 | 300 | Pass  |
| OA-019 | Sale Return After Full Receipt | Bill Amount = ₹1,000 / Receipt = ₹1,000 / Sale Return = ₹400 |  | 0 | 400 | Pass  |
| OA-020 | Sale Return + Partial Receipt | Bill Amount = ₹1,000 / Receipt = ₹400 / Sale Return = ₹300 |  | 300 | 0 | Pass  |
| OA-021 | Sale Return Modify (Increase Amount) | Bill Amount = ₹1,000 / Sale Return = ₹300 → modified to ₹500 | Create sale bill ₹1,000 / Create sale return ₹300 / Modify sale return amount to ₹500 | 500 | 0 | Pass  |
| OA-022 | Sale Return Modify (Decrease Amount) | Bill Amount = ₹1,000 / Sale Return = ₹500 → modified to ₹200 | Create sale bill ₹1,000 / Create sale return ₹500 / Modify sale return to ₹200 | 800 | 0 | Pass  |
| OA-023 | Sale Return Delete | Bill Amount = ₹1,000 / Sale Return = ₹400 | Create bill ₹1,000 / Create sale return ₹400 / Delete sale return | 1000 | 0 | Pass  |
| OA-024 | Sale Return Un-Adjust | Bill Amount = ₹1,000 / Sale Return = ₹400 (adjusted) | Un-adjust sale return from bill | 1000 | 400 | Pass  |
| OA-025 | Multiple Sale Returns on One Bill | Bill Amount = ₹1,000 / Sale Return-1 = ₹200 / Sale Return-2 = ₹300 | Create bill ₹1,000 / Create two sale returns | 500 | 0 | Pass  |
| OA-026 | Sale Return After Partial Receipt | Bill Amount = ₹1,000 / Receipt = ₹400 / Sale Return = ₹300 | Create bill ₹1,000 / Adjust receipt ₹400 / Create sale return ₹300 | 300 | 0 | Pass  |
| OA-027 | Sale Return After Partial Receipt (Excess Case) | Bill Amount = ₹1,000 / Receipt = ₹400 / Sale Return = ₹700 | Create bill ₹1,000 / Adjust receipt ₹400 / Create sale return ₹700 | 0 | 100 | Pass  |
| OA-028 | Sale Return Adjusted in Next Sale Bill | Old Bill Amount = ₹1,000 (closed) / Sale Return = ₹300 / New Bill Amount = ₹800 | Close first bill / Create sale return ₹300 / Create new sale bill ₹800 / Adjust sale return in new bill | 500 | 0 | Pass  |
| OA-029 | Sale Return Delete After Receipt | Bill Amount = ₹1,000 / Receipt = ₹600 / Sale Return = ₹300 | Create bill ₹1,000 / Adjust receipt ₹600 / Create sale return ₹300 / Delete sale return | 400 | 0 | Pass  |
| OA-030 | Sale Return Reference Change | Bill-A = ₹1,000 / Bill-B = ₹800 / Sale Return = ₹300 | Adjust sale return to Bill-A / Change reference to Bill-B |  | 0 | Pass  |
| OA-031 | Receipt After Full Sale Return | Bill Amount = ₹1,000 / Sale Return = ₹1,000 / Receipt = ₹200 | Create bill ₹1,000 / Create sale return ₹1,000 / Create receipt ₹200 | 0 | 200 | Pass  |
| OA-032 | Receipt Modify After Sale Return | Bill Amount = ₹1,000 / Sale Return = ₹400 / Receipt = ₹300 → modified to ₹500 | Create bill ₹1,000 / Create sale return ₹400 / Adjust receipt ₹300 / Modify receipt to ₹500 | 100 | 0 | Pass  |
| OA-033 | Receipt Delete After Sale Return | Bill Amount = ₹1,000 / Sale Return = ₹400 / Receipt = ₹300 | Delete receipt | 600 | 0 | Pass  |
| OA-034 | Receipt Un-Adjust After Sale Return | Bill Amount = ₹1,000 / Sale Return = ₹400 / Receipt = ₹300 (adjusted) | Un-adjust receipt | 600 | 300 | Pass  |
| OA-035 | Multiple Receipts + Sale Return | Bill Amount = ₹1,000 / Receipt-1 = ₹300 / Receipt-2 = ₹200 / Sale Return = ₹400 |  | 100 | 0 | Pass  |
| OA-036 | Sale Return Before Any Receipt | Bill Amount = ₹1,000 / Sale Return = ₹500 |  | 500 | 0 | Pass  |
| OA-037 | Receipt Before Sale Return | Bill Amount = ₹1,000 / Receipt = ₹400 / Sale Return = ₹500 |  | 100 | 0 | Pass  |
| OA-038 | Receipt + Sale Return Exactly Closing Bill | Bill Amount = ₹1,000 / Receipt = ₹600 / Sale Return = ₹400 |  | 0 | 0 | Pass  |
| OA-039 | Sale Return Over Multiple Adjustments | Bill Amount = ₹1,000 / Receipt = ₹700 / Sale Return = ₹400 |  | 0 | 100 | Pass  |
| OA-040 | Sale Return Fully Un-Adjusted Then Re-Adjusted | Bill Amount = ₹1,000 / Sale Return = ₹400 | Adjust sale return / Un-adjust sale return / Adjust again | 600 | 0 | Not Run  |
| OA-041 | Bill-Time Partial Payment | Bill Amount = ₹1,000 / Paid at save = ₹300 | Create sale bill ₹1,000 / At bill save time, enter payment ₹300 / Save bill | 700 | 0 | Pass  |
| OA-042 | Bill-Time Full Payment | Bill Amount = ₹1,000 / Paid at save = ₹1,000 | Create sale bill ₹1,000 / Enter payment ₹1,000 at save | 0 | 0 | Pass  |
| OA-043 | Bill-Time Excess Payment (Not Allowed) | Bill Amount = ₹1,000 / User enters Paid at save = ₹1,200 | Create sale bill ₹1,000 / Enter payment ₹1,200 / Try to save bill | 0 | 0 | Pass  |
| OA-044 | Modify Bill-Time Payment (Increase) | Bill Amount = ₹1,000 / Paid at save = ₹300 → modified to ₹500 | Save bill with payment ₹300 / Edit bill → change payment to ₹500 | 500 | 0 | Pass  |
| OA-045 | Modify Bill-Time Payment (Decrease) | Bill Amount = ₹1,000 / Paid at save = ₹500 → modified to ₹200 |  | 800 | 0 | Pass  |
| OA-046 | Remove Bill-Time Payment | Bill Amount = ₹1,000 / Paid at save = ₹300 | Edit bill / Remove payment / Save bill | 1000 | 0 | Pass  |
| OA-047 | Invoice Delete (Only Bill-Time Payment) | Bill Amount = ₹1,000 / Paid at save = ₹300 | Delete invoice | 0 | 0 | Pass  |
| OA-048 | Bill-Time Payment + Sale Return ⭐ | Bill Amount = ₹1,000 / Paid at save = ₹300 / Sale Return = ₹1,000 | Create bill ₹1,000 / Take payment ₹300 at save / Create sale return ₹1,000 | 0 | 300 | Pass  |
| OA-049 | Bill-Time Payment + Partial Sale Return | Bill Amount = ₹1,000 / Paid at save = ₹300 / Sale Return = ₹400 |  | 300 | 0 | Pass  |
| OA-050 | Bill-Time Payment + Receipt | Bill Amount = ₹1,000 / Paid at save = ₹300 / Receipt later = ₹500 |  | 200 | 0 | Pass  |
| OA-051 | Bill-Time Payment + Receipt (Excess) | Bill Amount = ₹1,000 / Paid at save = ₹300 / Receipt later = ₹800 |  | 0 | 100 | Pass  |
| OA-052 | Bill-Time Payment + Multiple Receipts | Bill Amount = ₹1,000 / Paid at save = ₹300 / Receipt-1 = ₹200 / Receipt-2 = ₹300 |  | 200 | 0 | Pass  |
| OA-053 | Bill-Time Payment + Receipt Modify | Bill Amount = ₹1,000 / Paid at save = ₹300 / Receipt = ₹200 → modified to ₹400 |  | 300 | 0 | Pass  |
| OA-054 | Bill-Time Payment + Receipt Delete | Bill Amount = ₹1,000 / Paid at save = ₹300 / Receipt = ₹400 (deleted) |  | 700 | 0 | Pass  |
| OA-055 | Bill-Time Payment + Receipt Un-Adjust | Bill Amount = ₹1,000 / Paid at save = ₹300 / Receipt = ₹400 (un-adjusted) |  | 700 | 400 | Pass  |
| OA-056 | Bill-Time Payment + Sale Return + Receipt | Bill Amount = ₹1,000 / Paid at save = ₹300 / Sale Return = ₹400 / Receipt = ₹200 |  | 100 | 0 | Pass  |
| OA-057 | Bill-Time Payment + Sale Return (Excess) + Receipt | Bill Amount = ₹1,000 / Paid at save = ₹300 / Sale Return = ₹800 / Receipt = ₹100 |  | 0 | 200 | Pass  |
| OA-058 | Bill-Time Payment Modify After Sale Return | Bill Amount = ₹1,000 / Paid at save = ₹300 / Sale Return = ₹400 / Payment modified to ₹500 |  | 100 | 0 | Pass  |
| OA-059 | Bill-Time Payment Removed After Sale Return | Bill Amount = ₹1,000 / Paid at save = ₹300 (removed later) / Sale Return = ₹400 |  | 600 | 0 | Pass  |
| OA-060 | Bill-Time Payment + Sale Return Delete | Bill Amount = ₹1,000 / Paid at save = ₹300 / Sale Return = ₹400 (deleted) |  | 700 | 0 | Pass  |
| OA-061 | Advance Receipt Creation | Advance Receipt = ₹1,000 | Create receipt of ₹1,000 / Do not select any bill | 0 | 1000 | Pass  |
| OA-062 | Advance Adjusted to Single Bill | Advance = ₹1,000 / Bill Amount = ₹600 | Create advance receipt ₹1,000 / Create sale bill ₹600 / Adjust advance to bill | 0 | 400 | Pass  |
| OA-063 | Advance Adjusted to Multiple Bills | Advance = ₹1,000 / Bill-1 = ₹400 / Bill-2 = ₹600 | Create advance ₹1,000 / Create two bills / Adjust advance to both bills | 0 | 0 | Pass  |
| OA-064 | Advance Partial Adjustment | Advance = ₹1,000 / Bill Amount = ₹800 / Only ₹300 adjusted | Create advance ₹1,000 / Create bill ₹800 / Adjust only ₹300 from advance | 500 | 700 | Pass  |
| OA-065 | Advance Modify (Decrease Amount) | Advance = ₹1,000 → modified to ₹700 | Create advance ₹1,000 / Modify receipt amount to ₹700 | 0 | 700 | Remark - System not allowd to decreased amount |
| OA-066 | Advance Modify (Increase Amount) | Advance = ₹700 → modified to ₹1,000 |  | 0 | 1000 | Pass  |
| OA-067 | Advance Delete (No Adjustment) | Advance = ₹1,000 | Delete advance receipt | 0 | 0 | Pass  |
| OA-068 | Advance Used Then Bill Deleted | Advance = ₹1,000 / Bill Amount = ₹600 | Adjust advance to bill / Un-adjust advance / Delete bill | 0 | 1000 | Pass  |
| OA-069 | Advance Adjusted Then Un-Adjusted | Advance = ₹1,000 / Bill Amount = ₹700 | Adjust advance ₹700 / Un-adjust advance | 700 | 1000 | Pass  |
| OA-070 | Advance Adjusted to Wrong Bill Then Corrected | Advance = ₹1,000 / Bill-A = ₹400 / Bill-B = ₹600 | Adjust advance to Bill-A / Un-adjust / Adjust advance to Bill-B | 0 | 400 | Pass  |
| OA-071 | Invoice Delete With Advance Adjusted | Advance = ₹500 / Bill Amount = ₹500 | Adjust advance to bill / Try to delete bill | 0 | 0 | Pass  |
| OA-072 | Advance Un-Adjust Then Invoice Delete | Advance = ₹500 / Bill Amount = ₹500 | Un-adjust advance / Delete bill | 0 | 500 | Pass  |
| OA-073 | Invoice Delete With Partial Advance Adjusted | Advance = ₹1,000 / Bill Amount = ₹600 / Advance adjusted = ₹300 | Try deleting bill | 300 | 700 | Pass  |
| OA-074 | Advance Un-Adjust Partial Then Invoice Delete | Advance = ₹1,000 / Bill Amount = ₹600 / Advance adjusted = ₹300 | Un-adjust advance / Delete bill | 0 | 1000 | Pass  |
| OA-075 | Advance + Receipt Combined | Advance = ₹400 / Receipt = ₹300 / Bill Amount = ₹1,000 | Adjust both to bill | 300 | 0 | Remark - Advance and reciept both are same |
| OA-076 | Advance + Sale Return Combined | Advance = ₹400 / Sale Return = ₹300 / Bill Amount = ₹1,000 |  | 300 | 0 | Pass  |
| OA-077 | Advance Over-Adjustment Attempt | Advance = ₹500 / Bill Amount = ₹400 | Try adjusting ₹600 | 0 | 100 | Pass  |
| OA-078 | Advance Adjust After Bill Modify | Advance = ₹500 / Bill Amount = ₹600 → modified to ₹400 |  | 0 | 100 | Pass  |
| OA-079 | Advance Adjust Then Receipt Modify | Advance = ₹500 / Bill Amount = ₹800 / Receipt = ₹200 → modified to ₹400 |  | 0 | 100 | Remark - Advance and Receipt Both are same |
| OA-080 | Advance Un-Adjust After Multiple Uses | Advance = ₹1,000 / Bill-1 = ₹400 / Bill-2 = ₹300 | Adjust advance to both bills / Un-adjust advance fully | 700 | 1000 | Pass  |
| OA-081 | Invoice Delete With Receipt Adjusted | Bill Amount = ₹1,000 / Receipt = ₹600 (adjusted) | Create bill ₹1,000 / Adjust receipt ₹600 / Try to delete invoice | 400 | 0 | Pass  |
| OA-082 | Receipt Un-Adjust Then Invoice Delete | Bill Amount = ₹1,000 / Receipt = ₹600 (adjusted) | Un-adjust receipt / Delete invoice | 0 | 600 | Pass  |
| OA-083 | Invoice Delete With Sale Return Adjusted | Bill Amount = ₹1,000 / Sale Return = ₹400 (adjusted) | Try deleting invoice | 600 | 0 | Pass  |
| OA-084 | Sale Return Un-Adjust Then Invoice Delete | Bill Amount = ₹1,000 / Sale Return = ₹400 (adjusted) | Un-adjust sale return / Delete invoice | 0 | 400 | Pass  |
| OA-085 | Invoice Delete With Advance Adjusted | Advance = ₹500 / Bill Amount = ₹500 | Adjust advance to bill / Try deleting invoice | 0 | 0 | Pass  |
| OA-086 | Advance Un-Adjust Then Invoice Delete | Advance = ₹500 / Bill Amount = ₹500 | Un-adjust advance / Delete invoice | 0 | 500 | Pass  |
| OA-087 | Delete Receipt After Partial Adjustment | Bill Amount = ₹1,000 / Receipt = ₹400 | Adjust receipt ₹400 / Delete receipt | 1000 | 0 | Pass  |
| OA-088 | Delete Sale Return After Partial Adjustment | Bill Amount = ₹1,000 / Sale Return = ₹300 | Adjust sale return ₹300 / Delete sale return | 1000 | 0 | Pass  |
| OA-089 | Receipt + Sale Return Both Adjusted Then Receipt Deleted | Bill Amount = ₹1,000 / Receipt = ₹400 / Sale Return = ₹300 | Adjust both / Delete receipt | 1000 | 0 | Pass  |
| OA-090 | Receipt + Sale Return Both Adjusted Then Sale Return Deleted | Bill Amount = ₹1,000 / Receipt = ₹400 / Sale Return = ₹300 | Adjust both / Delete sale return | 1000 | 0 | Pass  |
| OA-091 | Receipt Un-Adjust After Partial Adjustment | Bill Amount = ₹1,000 / Receipt = ₹400 | Un-adjust receipt | 1000 | 400 | Pass  |
| OA-092 | Sale Return Un-Adjust After Partial Adjustment | Bill Amount = ₹1,000 / Sale Return = ₹300 | Un-adjust sale return | 1000 | 300 | Pass  |
| OA-093 | Receipt Un-Adjust Then Adjust to Another Bill | Bill-A = ₹1,000 / Bill-B = ₹600 / Receipt = ₹500 | Adjust receipt to Bill-A / Un-adjust receipt / Adjust receipt to Bill-B | 100 | 0 |   |
| OA-094 | Sale Return Un-Adjust Then Adjust to Another Bill | Bill-A = ₹1,000 / Bill-B = ₹700 / Sale Return = ₹400 | Adjust return to Bill-A / Un-adjust / Adjust to Bill-B | 300 | 0 |   |
| OA-095 | Advance + Receipt + Sale Return Mixed | Bill Amount = ₹1,000 / Advance = ₹300 / Receipt = ₹200 / Sale Return = ₹400 |  | 100 | 0 |   |
| OA-096 | Receipt Created After Invoice Deleted | Bill Amount = ₹1,000 / Invoice deleted / Receipt = ₹500 | Delete invoice / Create receipt | 0 | 500 |   |
| OA-097 | Sale Return Created After Invoice Deleted | Bill Amount = ₹1,000 / Invoice deleted / Sale Return = ₹400 |  | 0 | 400 |   |
| OA-098 | Multiple Un-Adjust Order Stress Case | Bill Amount = ₹1,000 / Receipt = ₹300 / Sale Return = ₹200 / Advance = ₹100 | Adjust all / Un-adjust in random order | 1000 | 600 |   |
| OA-099 | Full Rollback Scenario | Bill Amount = ₹1,000 / Receipt = ₹400 / Sale Return = ₹300 | Adjust receipt / Adjust sale return / Un-adjust both / Delete both | 1000 | 0 |   |
| OA-100 | MASTER END-TO-END CASE | Bill Amount = ₹1,000 / Paid at save = ₹300 / Receipt = ₹200 / Sale Return = ₹600 | Create bill ₹1,000 / Take payment ₹300 at save / Adjust receipt ₹200 / Create sale return ₹600 | 0 | 100 |   |

## How multi-bill rows are read
Where the workbook's "Calculation" column names one bill (OA-030, OA-070, OA-093, OA-094), its expected outstanding is that bill's balance, not the party total. The case data says so explicitly (`bill=` on the expectation).

## Needs decision (workbook vs its own calculation; not resolved here)
| ID | What the workbook says | Why it looks inconsistent |
|---|---|---|
| OA-030 | Expected outstanding blank, advance 0 | Calculation says Bill-A goes back to 1,000 and Bill-B drops by 300 (to 500). Tests check those two bill balances. |
| OA-065 | Expected advance 700; Actual 1,000; Remark "System not allowd to decreased amount" | The app refuses the decrease. The test keeps the expected value 700 and is marked `xfail` with the remark as the reason. |
| OA-075, OA-079 | Remark "Advance and receipt both are same" | The app has no separate advance voucher; an advance is a receipt saved with Reference Type "Advance". Tests do that. |
| OA-089 | Expected outstanding 1,000 | Calculation says "Only sale return remains" (₹300 adjusted), which gives 700. |
| OA-090 | Expected outstanding 1,000 | Calculation says "Only receipt remains" (₹400 adjusted), which gives 600. |
| OA-040 | Iteration 1 "Not Run" | Implemented like the others. |
| OA-093 - OA-100 | No iteration 1 result | Implemented like the others. |

## KB vs live app
- KB route `/partymaster/outstanding-receivable-report` lists ledgers with a ₹ Balance column (seen live as "Ledger Master : Outstanding Receivable Report"); the bill-wise view opens by double-clicking a ledger. The ledger list balance (e.g. "4,062.000 Cr") is the ledger balance, not outstanding.
- Alt+N (new sale bill) did not open the bill on app V. 4.3.598.b; Sale > Bill > Create/F2 works.
- No item in the garments company has 0% GST (5%, 12% and 28% seen). Decision 2026-10-09 (test owner): use a 0% GST test item created once, so bill amounts equal the workbook's ₹ values.
