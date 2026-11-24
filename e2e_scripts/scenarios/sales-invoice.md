# Scenario pack: J04 sales invoice, GST, totals (incl. invalid GSTIN)

Journey J04 (matrix slug `sale-bill-creation`). Source tags: LIVE = live observation 2026-10-05 on
https://premargbooks.com, company "Garments New 29-08 (GANE29)", V. 4.3.597.b, read-only (no bill saved);
CODE = code path named in `docs/prd/02-prd-api-and-calculation.md` (not read by me); PRD = repo PRD.
Anything not seen is `UNVERIFIED` with its question. No scenario here may be asserted from the app's own output
(expected values come from the calculation table below).

## Live facts used by this pack
- Sale list route `/sale/salebook/bill` ("GST Invoice List": Bill No., Date, Patient Name, Party, Status, Amount, Action). Create button `Create/F2`. Entry screen route `/transaction` (title "Sale Bill 1"). LIVE
- Header fields: `#txtbillDate88` (default today `05-10-2026`), `#txtLedgerName88` (formcontrolname `ledgerName`), `#txtentryNo88` (`entryNo`, auto "0000014"), `#txtptmobile88`, `#txtptname88`, `#txtpatientaddress88`. Ids end in a number that is per window type (88 = sale, 80 = purchase). LIVE
- Grid col-ids: `tmp_barcode`, `itemLinkID` (Product), `tmp_packing`, `quantity`, `free`, `salePurchaseRate`, `discount1`, `DisplayAmount`, `Action`. Qty editor input `#txt-qty-0`. Footer table col-ids `ledgerLinkID`, `percentage`, `amount` (rows "CGST Output"/"SGST Output" or "IGST Output"). LIVE
- Buttons: `#btnSave88` (F10/End Save), Save & New (F9, also `#btnSave88`), `#btnDraft88`, `#btnEsc88`, `#lastDeal`, `#startScan`. LIVE
- Garments flow differs from chemist: after party Enter the cursor is in the barcode cell; Enter on an empty barcode opens "Select Item" (`#searchItems`), Enter opens the variant list (Barcode/Design/Color/Size/Quantity/MRP/Sale Rate), Enter opens a qty window (Design/Color/Size/Qty/MRP/Sale Rate/Disc %/Barcode/Amount), F10 there commits to the bill. A wrong barcode typed gives alert "Barcode Not Available". LIVE
- Settings: `#calculationTypeForSale` default value 2 (labels in the panel: Inclusive / Exclusive / Tax on MRP(inc.)); bills seen were EXCLUSIVE (tax added on top). UNVERIFIED which option value 2 is. LIVE
- Parties (9 ledgers): Ajay (Others, intra-state), Arun Sharma (Rohini, INTER-state: bill showed IGST), Cash Account, General Ledger, Marg Mart, Online Store, Sample Ledger, Santosh, Santosh Sir (Trjhfjdhf). All except Arun Sharma gave CGST+SGST. Balances exist; the tenant already holds one B2B bill of 444.00 + IGST 124.32 in Sept 2026 (568.00 invoice). LIVE
- Items (5): Barcdoe (HSN 54545454, IGST 28 / CGST 14 / SGST 14, one variant d3/reef/33, rate 200, stock 50), Sample Item (HSN 12345678, 5%, rate 100, variants d1 red 32 /d2 blue 34 /fdf, stock 1976), Test 1 2, Test 2, Test 3 (all 28%, sale rate 0, stock 1596/347/64). Only the 5% and 28% slabs exist. LIVE
- Observed totals (exclusive): Ajay + Sample Item 3 x 100 = CGST 7.500 + SGST 7.500, invoice 315.000. Arun Sharma + Sample Item 3 x 100 = IGST 15.000, invoice 315.000. Ajay + Barcdoe 3 x 200 = CGST 84.000 + SGST 84.000, invoice 768.000. Arun + Barcdoe = IGST 168.000, 768.000. All match the table below. LIVE
- Display precision is 3 decimals: rate edited to 33.33, qty 1, 5%: CGST 0.833, SGST 0.833, invoice value 34.996 (no 2-decimal rounding shown before save). Rounding at save UNVERIFIED (D5). LIVE
- Qty 0 or -2 entered in the qty window and committed: no row appeared in the bill, no alert text captured. LIVE (D7 still open: was it silent rejection or a message I missed)
- Existing GSTR-1 for 01-09-2026..30-09-2026 shows invoice amount 568.00 for taxable 444.00 + tax 124.32 = 568.32: a bill-level round-off to the rupee exists. LIVE (export file, B2B row 568.00 vs HSN row 568.32)

## Calculation table (independent oracle; Decimal; tax computed per line; total = base + tax)
Rounding rule is UNVERIFIED (decision D5). Columns show the tax to 2 dp under half-up and under banker's (half-even); rows
where they differ are flagged DIFF and must be skipped or parametrised until D5 is answered. Intra-state: CGST = SGST =
half the total tax (a half-split rounding question: HALF-DIFF flags where the two modes differ per half). Inter-state: IGST = total tax.
Slab 40 is excluded until D4 answers whether it is valid (and from which date).

| Slab | Base | Exact tax | Tax half-up | Tax half-even | Each of CGST/SGST exact | Flag |
|---|---|---|---|---|---|---|
| 0 | any | 0 | 0.00 | 0.00 | 0 | |
| 5 | 100.00 | 5 | 5.00 | 5.00 | 2.5 | observed live (base 300 -> 15.00) |
| 5 | 333.33 | 16.6665 | 16.67 | 16.67 | 8.33325 | per-half 8.33 |
| 5 | 999.99 | 49.9995 | 50.00 | 50.00 | 24.99975 | per-half 25.00 |
| 5 | 33.33 | 1.6665 | 1.67 | 1.67 | 0.83325 | live UI shows 1.666 total (0.833 each): 3-dp, not 2-dp |
| 5 | 0.50 | 0.025 | 0.03 | 0.02 | 0.0125 | DIFF |
| 5 | 1234.56 | 61.728 | 61.73 | 61.73 | 30.864 | |
| 5 | 250.10 | 12.505 | 12.51 | 12.50 | 6.2525 | DIFF |
| 12 | 100.00 | 12 | 12.00 | 12.00 | 6 | no 12% item exists |
| 12 | 333.33 | 39.9996 | 40.00 | 40.00 | 19.9998 | |
| 12 | 999.99 | 119.9988 | 120.00 | 120.00 | 59.9994 | |
| 12 | 0.50 | 0.06 | 0.06 | 0.06 | 0.03 | |
| 12 | 1234.56 | 148.1472 | 148.15 | 148.15 | 74.0736 | |
| 18 | 100.00 | 18 | 18.00 | 18.00 | 9 | no 18% item exists |
| 18 | 333.33 | 59.9994 | 60.00 | 60.00 | 29.9997 | |
| 18 | 33.33 | 5.9994 | 6.00 | 6.00 | 2.9997 | |
| 18 | 0.50 | 0.09 | 0.09 | 0.09 | 0.045 | HALF-DIFF (0.05 vs 0.04 per half) |
| 18 | 1234.56 | 222.2208 | 222.22 | 222.22 | 111.1104 | |
| 18 | 250.10 | 45.018 | 45.02 | 45.02 | 22.509 | |
| 28 | 100.00 | 28 | 28.00 | 28.00 | 14 | |
| 28 | 600.00 | 168 | 168.00 | 168.00 | 84 | observed live (Barcdoe 3 x 200) |
| 28 | 333.33 | 93.3324 | 93.33 | 93.33 | 46.6662 | per-half 46.67 |
| 28 | 33.33 | 9.3324 | 9.33 | 9.33 | 4.6662 | |
| 28 | 0.50 | 0.14 | 0.14 | 0.14 | 0.07 | |
| 28 | 1234.56 | 345.6768 | 345.68 | 345.68 | 172.8384 | |
| 28 | 250.10 | 70.028 | 70.03 | 70.03 | 35.014 | |

Totals: invoice = base + tax. Bill-level round-off to whole rupee is observed in the existing Sept bill (568.32 -> 568.00);
whether the round-off is on the sale ledger side, shown on screen before save, or applied only at save is UNVERIFIED (D5).
Safe independent cases today (no DIFF, no rounding doubt): 5% on 100 x qty (live-confirmed), 28% on 200 x qty (live-confirmed).

## Scenarios
| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| SI-01 | Positive | Intra-state bill, party Ajay, Sample Item (5%) qty 3 x 100, exclusive | Grid row qty 3.000, rate 100.000, amount 300.000; CGST 7.500, SGST 7.500; footer rows CGST Output / SGST Output 7.500 each; Invoice Value 315.000 | LIVE 2026-10-05 (and table) |
| SI-02 | Positive | Inter-state bill, party Arun Sharma, Sample Item qty 3 | IGST 15.000 only (no CGST/SGST rows), Invoice Value 315.000 | LIVE |
| SI-03 | Positive | Intra-state, Barcdoe (28%) qty 3 x 200 | CGST 84.000 + SGST 84.000, Invoice Value 768.000 | LIVE |
| SI-04 | Positive | Inter-state, Barcdoe qty 3 | IGST 168.000, Invoice Value 768.000 | LIVE |
| SI-05 | Positive | Save the bill (F10) then open it in the list `/sale/salebook/bill` | Bill appears with party, amount equal to the invoice value (rounded per D5); print preview shows (as ported chemist assumption) | UNVERIFIED (never saved by me); PRD W1-04, `PORTING-NOTES.md` |
| SI-06 | Positive | Saved bill shows in GSTR-1 for its month: Taxable Sales voucher count +1, taxable and tax columns +bill values | Delta equals the table value | UNVERIFIED (needs a saved bill, cross-ref J06) |
| SI-07 | Boundary | Rate 33.33 qty 1 at 5% | Tax 1.6665 exact; app shows 0.833+0.833 (3 dp) before save; saved value per D5 | LIVE (display), D5 UNVERIFIED |
| SI-08 | Boundary | Odd paise DIFF cases (5% on 0.50 and 250.10) | half-up 0.03 / 12.51 vs half-even 0.02 / 12.50 | table; D5 UNVERIFIED, skip with question |
| SI-09 | Boundary | Qty 0 | No row accepted (seen), message UNVERIFIED | LIVE partial; D7 |
| SI-10 | Boundary | Qty negative (-2) | No row accepted (seen), message UNVERIFIED | LIVE partial; D7. PRD API message "Quantity should be greater than 0" is for the API save, CODE |
| SI-11 | Boundary | Qty above stock (Barcdoe stock 50, qty 51) | Negative stock setting `#negativeAllowed` is value 1 ("Yes"?) so likely allowed | UNVERIFIED; question: label of option 1 |
| SI-12 | Boundary | Qty fractional (2.5) and very large (9999999999999, field maxlength 13) | UNVERIFIED | question to product owner |
| SI-13 | Boundary | Zero-rated line: no 0% item exists in the demo data | Tax 0.00, invoice = base | UNVERIFIED, data gap |
| SI-14 | Boundary | Bill date today, back date, future date (e.g. 05-10-2027 is outside books 01-04-2026..31-03-2027), date before FY start | UNVERIFIED (my date-typing script did not reach the field; D6) | D6 open |
| SI-15 | Negative | Wrong barcode typed in the barcode cell | Alert dialog "Barcode Not Available" | LIVE |
| SI-16 | Negative | Save with no party / no item | UNVERIFIED validation text | question |
| SI-17 | Negative | Party ledger form: GSTIN with bad format (e.g. 15 chars, wrong pattern) | Inline or save-time error; wording UNVERIFIED | UNVERIFIED (ledger form not yet opened by me), CODE `GSTINValidation.cs`; use `DataFactory` invalid-format value |
| SI-18 | Negative | Party ledger form: well-formed GSTIN with wrong check digit | Rejected; wording UNVERIFIED | UNVERIFIED, CODE `IsValidGSTIN` (check digit); `DataFactory.valid_gstin()` then alter the last char |
| SI-19 | Negative | Sale to a party whose GSTIN is invalid (existing data) | Bill creation/GST classification behaviour UNVERIFIED (B2B vs B2C) | question |
| SI-20 | Duplicate | Same bill number, double click on Save, Save twice | UNVERIFIED; CODE `CheckBillNoExistance` | question |
| SI-21 | Duplicate | Refresh the browser mid-bill | Unsaved bill lost vs draft; UNVERIFIED | question |
| SI-22 | State | Edit a saved bill, change quantity, totals recalc and GSTR-1 follows | UNVERIFIED | question |
| SI-23 | State | Save As Draft (`#btnDraft88`) then Sale > Draft | Draft listed, not in GSTR-1 | UNVERIFIED |
| SI-24 | Discount | Item discount 1 / discount 2 / bill discount reduce the taxable base before tax | UNVERIFIED formula; `calculatedDiscountGST` CODE | question, covers GS-02 |
| SI-25 | Mode | Calculation type Inclusive and Tax-on-MRP (Ctrl+R "change calculation") | Price includes tax: base = rate x 100/(100+slab) | UNVERIFIED; needs the settings change (not done, read-only) |
| SI-26 | Permission | Operator/admin/accountant can or cannot open Sale > Bill and save | UNVERIFIED, no role accounts (D10) | skip with reason |
| SI-27 | Tenancy | Bill created in another company never appears here | UNVERIFIED, no second company | skip with reason |
| SI-28 | Output | Invoice value in list, ledger balance of party, and GSTR-1 reconcile | Party balance moves by invoice value; Arun Sharma already shows 568.000 Dr from the 568.00 bill | LIVE (568 Dr matches the 568.00 bill) |

## KB vs live app
- Garments screen has the variant window (Design/Color/Size) and a "Patient Name" column header in the list; the ported chemist grid assumptions (batch window, `ChemistSaleGrid`) do not apply directly.
- Chemist pack asked for banker's vs half-up; the live UI shows 3-decimal tax, so a third behaviour (truncation or 3-dp storage) is possible.
- Party list search typed "Ajay" selected "Additional Charges On Free Items": a hidden/system ledger appears in search but not in the list of 9. Needs a human look.
- Item name "Barcdoe" is spelled so in the data (typo in the demo).
- Home state code UNVERIFIED (Ajay is intra-state, Arun Sharma inter-state by behaviour only; their GSTIN/state values were not read).
