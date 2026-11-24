# Plan: J05 purchase entry and input tax credit

Scenario pack: `scenarios/purchase.md`; calculation table in `scenarios/sales-invoice.md`. Status: DRAFT for human review.
Purchase screen was only opened (not filled) by me: steps beyond the header are inferred from the identical sale grid and are UNVERIFIED. Nothing was saved.

## Preconditions
- `page_as("garments")`. Items: `Sample Item` (5%), `Barcdoe` (28%). Suppliers: only `Mayur Sharma` is known by name (un-registered). DATA GAP: no known registered intra-state or inter-state supplier; list names with the supplier picker (F4 / Select Party) before generating tests.
- Do not save bills until approved (Q1).

## Locators
| Thing | Locator |
|---|---|
| Menu | `a:visible` "Purchase" then `span:visible` "Bill" (route `/purchase/purchasebook/bill`); or Alt+P (route `/transaction`) |
| List cols | `[col-id="partyBillNo"]`, `billDate`, `tmp_LedgerName`, `tmp_stationname`, `Status`, `totaliteminvoice` |
| Start choice | buttons "Start Manual Entry" and "Upload & Auto Read Invoice" |
| Header | `#txtLedgerName80` (`ledgerName`), `#txtentryNo80` (`entryNo`, Invoice No.), `#txtbillDate80`, `#txtisInvoiceDate80`, `#txtbillValue80` (`BillValueAmount`), `#txtbillDiscountPercentage80`, `#txtbillDiscountAmount80` |
| Grid | same col-ids as sale: `itemLinkID`, `quantity`, `free`, `salePurchaseRate`, `discount1`, `DisplayAmount` |
| Save etc. | `[id^=btnSave]` (number varies), `[id^=btnDraft]`, `[id^=btnEsc]` |
| Toast | text "Supplier In Un-Registered" |
| Method dialog | text "How would you like to create your purchase bill?" |

## Plan PU-A: unregistered supplier warning (PU-11) (safe, read-only)
1. Purchase > Bill > Create/F2; choose "Start Manual Entry" if shown.
2. Pick supplier `Mayur Sharma`. Expect toast "Supplier In Un-Registered" and the method dialog.
3. Enter Invoice No. `QA-<run_id>` in `#txtentryNo80`, add `Sample Item` qty 10, rate 100. Expect Tax Info per UNVERIFIED rule (RCM / no ITC); record what the footer shows. NEEDS DECISION: expected ITC for un-registered supplier.

## Plan PU-B: intra-state ITC (PU-01, PU-03, PU-04) (needs a registered intra-state supplier)
1. Choose supplier S1 (registered, home state). Expect Tax Info CGST + SGST.
2. Invoice No. `QA-<run_id>-1`, invoice date today; item `Sample Item`, qty 10, purchase rate 100.
3. Expect Goods Value 1000.00, CGST 25.00 + SGST 25.00, bill value 1050.00. Cross-check by typing 1050.000 into `#txtbillValue80`; expect no warning.
4. (After approval) Save; expect bill in `/purchase/purchasebook/bill` with Invoice No. and amount 1050.00 and the supplier payable up by 1050.00; GSTR-2/3B ITC for the month up by 50.00 (CGST 25 + SGST 25).

## Plan PU-C: inter-state ITC (PU-02)
Supplier S2 (other state): `Barcdoe` qty 3 rate 50 -> Taxable 150.00, IGST 42.00, bill 192.00.

## Plan PU-D: boundaries and negatives (PU-06..PU-17)
- Odd paise rows from the table (333.33 x 5% -> 16.67; DIFF rows 0.50 and 250.10 skipped until D5).
- Typed bill value mismatch; qty 0/negative; missing Invoice No.; duplicate Invoice No. for the same supplier; invoice date future/other FY: each recorded as `skip` with the scenario id and question (D5, D6, D7) until answered.
- Draft: `[id^=btnDraft]`, then Purchase > purchase draft lists it; GSTR-2 unchanged.

## Open questions
- Q1 may tests save purchases; how to delete/reverse them.
- Q5 list of suppliers with GSTIN type and state; need one registered intra-state, one registered inter-state, one composition.
- Q6 expected ITC behaviour for unregistered supplier and invalid-GSTIN supplier.
- Q7 does purchase round off the bill to the rupee like the observed sale?
- Q8 which ledger names carry input tax (for ledger reconcile PU-20) and where GSTR-3B shows ITC (its grid was empty in my run).
- D4/D5/D6/D7 as in `sale-invoice-gst.md`; D9 `data-testid` for purchase header and grid.
