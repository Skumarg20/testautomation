# Scenario pack: J05 purchase entry and input tax credit (ITC)

Journey J05 (matrix slug `purchase-itc`). Source tags: LIVE = live observation 2026-10-05 (read-only, nothing saved) by me, or
confirmed by the coordinator's other agent (marked LIVE-C); CODE = code path from `docs/prd/02-prd-api-and-calculation.md`
(`PurchaseChallanBill.cs`: `SavePurchaseGSTReturnData`, `GetAllRoundValue`; not read by me); PRD = repo PRD.
Calculation values come from the table in `scenarios/sales-invoice.md` (same per-line formula, rate x qty x slab).

## Live facts
- Purchase menu: Bill(+), Challan(+), Quotation(+), Stock Receive(+), Order(+), Return(+), purchase draft. List route `/purchase/purchasebook/bill`; list cols `partyBillNo` (Invoice No.), `billDate`, `tmp_LedgerName` (Party), `tmp_stationname`, `Status`, `totaliteminvoice` (Amount), `Action`. LIVE
- Entry window route `/transaction` (opened by Create/F2 or Alt+P LIVE-C). Header: `#txtbillDate80` (entry date, default today), `#txtLedgerName80` (formcontrolname `ledgerName`), `#txtentryNo80` (formcontrolname `entryNo`, placeholder "F11 - Import", this is the supplier Invoice No.), `#txtisInvoiceDate80` (invoice date), `#txtbillDiscountPercentage80`, `#txtbillDiscountAmount80`, `#txtbillValue80` (formcontrolname `BillValueAmount`, bill value typed in for cross-check). Buttons `#btnSave80` (F10/End, id number changes: use `[id^=btnSave]`), `#btnDraft80`, `#btnEsc80`, `#lastDeal`, `#startScan`. LIVE
- On opening a window a choice appears: "Upload & Auto Read Invoice" or "Start Manual Entry". After choosing a supplier a dialog asks "How would you like to create your purchase bill?" LIVE / LIVE-C
- Grid col-ids as in sale: `tmp_barcode`, `itemLinkID`, `tmp_packing`, `quantity`, `free`, `salePurchaseRate`, `discount1`, `DisplayAmount` (header "Amount"). Footer: Goods Value, Discount Info (Item Disc. 1/2, Scheme Disc. %), Tax Info, Bill Discount, Additional Details (`ledgerLinkID`, `percentage`, `amount`). LIVE
- Settings `#calculationTypeForPurchase` default value 2 (same as sale: UNVERIFIED which option), `#freeQtyConditionOnPurchase`, `#indicateIfStockMinimumLevel`. LIVE
- Supplier choose-list shows "Total No of Ledgers" (4 additional-ledger rows were counted in the footer of this window); supplier names were NOT enumerated by me. Supplier "Mayur Sharma" raises the toast "Supplier In Un-Registered" (LIVE-C). Dashboard "Current Payable 404132.000" means at least one supplier balance exists. UNVERIFIED which suppliers are registered/intra/inter-state.
- Items are shared with sale: Barcdoe (28%), Sample Item (5%), Test 1 2 / Test 2 / Test 3 (28%); purchase rate on Barcdoe: Pur.Rate 50.000, Cost 39.000, Cost+Tax 49.920 (picker panel). LIVE
- ITC reporting surfaces: GSTR-3B (`/report/gst/gstr3b`, only a JSON button and Excel/PDF seen, body empty in my run), GSTR-2 and GSTR-2B/2A reconciliation. Dashboard Business tile shows CGST/SGST/IGST Payable. LIVE

## Scenarios
| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| PU-01 | Positive | Intra-state registered supplier, Sample Item (5%) qty 10 x purchase rate 100, exclusive | Taxable 1000.00, CGST 25.00 + SGST 25.00 (table 5% on 1000 = 50 total), bill value 1050.00 (round-off per D5) | table (independent); screen UNVERIFIED for purchase |
| PU-02 | Positive | Inter-state registered supplier, Barcdoe (28%) qty 3 x 50 | Taxable 150.00, IGST 42.00, bill 192.00 | table; supplier data gap |
| PU-03 | Positive | Save purchase, then GSTR-2 / 3B ITC for the month rises by the CGST+SGST (or IGST) | Delta equals the PU-01 tax | UNVERIFIED (needs saved bill; GSTR-3B grid not seen) |
| PU-04 | Positive | Saved bill appears in `/purchase/purchasebook/bill` with Invoice No., supplier, amount; supplier balance (Payable) rises by bill value | Amount equals bill value | UNVERIFIED |
| PU-05 | Positive | Invoice No. (`entryNo`) and Invoice Date saved as entered | Round trip | UNVERIFIED |
| PU-06 | Boundary | Odd paise base (333.33 x 5%, 250.10 x 5%, 0.50 x 5%) | Table rows incl. DIFF flags; D5 | table; D5 UNVERIFIED, skip DIFF rows |
| PU-07 | Boundary | `BillValueAmount` typed differs from computed total | Warning or block on save; wording UNVERIFIED | question |
| PU-08 | Boundary | Qty 0 / negative / fractional / 13-digit maxlength | UNVERIFIED (sale analog saw no row added; D7) | D7 |
| PU-09 | Boundary | Invoice date earlier than entry date, in a previous FY, or future | UNVERIFIED (D6) | D6 |
| PU-10 | Boundary | Bill discount % and amount fields together with item discount | UNVERIFIED formula | question |
| PU-11 | Negative | Unregistered supplier (Mayur Sharma) | Toast "Supplier In Un-Registered"; ITC NOT claimable (no GST credit, or reverse-charge flow) | LIVE-C for toast; ITC behaviour UNVERIFIED (RCM, `GetAllRoundValue` CODE) |
| PU-12 | Negative | Composition supplier or supplier with invalid GSTIN | ITC not allowed / blocked; UNVERIFIED | no such party; see invalid-GSTIN form questions in `sales-invoice.md` SI-17/18 |
| PU-13 | Negative | Save with no supplier / no item / no Invoice No. | Validation text UNVERIFIED | question |
| PU-14 | Duplicate | Same supplier + same Invoice No. twice | UNVERIFIED; rule probably blocks (CODE: duplicate-bill checks exist for sale `CheckBillNoExistance`) | question |
| PU-15 | State | Edit or delete a saved purchase, ITC and payable follow | UNVERIFIED | question |
| PU-16 | State | Save As Draft (`#btnDraft80`) then purchase draft menu | Draft not in GSTR-2 | UNVERIFIED |
| PU-17 | Mode | Inclusive purchase: base = amount x 100/(100+slab) | UNVERIFIED | question |
| PU-18 | Permission | Operator/accountant create purchase | UNVERIFIED, no role accounts (D10) | skip with reason |
| PU-19 | Tenancy | Purchases from another company absent | UNVERIFIED, no second company | skip with reason |
| PU-20 | Reconcile | Purchase tax in ledger "GST input" = GSTR-2/3B ITC = invoice tax | Totals reconcile | UNVERIFIED; ledger names not enumerated |

## KB vs live app
- The purchase window offers "Upload & Auto Read Invoice" (AI/OCR) before manual entry: not in any PRD; manual entry path only is in scope.
- Supplier "Mayur Sharma" is un-registered although the demo name suggests an ordinary supplier: data seed contains at least one non-GST supplier.
- GSTR-3B page showed an empty grid in a quiet run (only a JSON button): needs a longer wait or the report is only produced after a generation action. UNVERIFIED.
- Round-off: sale showed rupee round-off; behaviour on purchase unknown.
