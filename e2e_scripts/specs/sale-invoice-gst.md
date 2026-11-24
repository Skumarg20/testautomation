# Plan: J04 sale invoice, GST, totals (garments tenant)

Scenario pack: `scenarios/sales-invoice.md` (calculation table lives there; tests copy it as Decimal data, never read expected values from the screen).
Status: DRAFT for human review. Locators are from live observation 2026-10-05; no test-id exists, fallbacks are ids / formcontrolname / ag-Grid col-id (T6). Nothing was saved.

## Preconditions
- Session `page_as("garments")`; tenant company GANE29, books 01-04-2026..31-03-2027; today 05-10-2026 is inside the books.
- Parties: `Ajay` (intra-state), `Arun Sharma` (inter-state). Items: `Sample Item` (5%, rate 100, variants d1/red/32 barcode 11110001), `Barcdoe` (28%, rate 200, variant d3/reef/33 barcode 11110005). Data gap: no 0/12/18% items, no party with an invalid GSTIN, home state code UNVERIFIED.
- Never edit the pre-existing Sept bill (568.00); created bills are for test-owned parties/runs and cannot be deleted by the test unless the delete flow is confirmed (open question Q1).
- Do not wait on networkidle; wait on elements. The app is slow (page loads 8-15 s).

## Locators (verified live)
| Thing | Locator |
|---|---|
| Menu | `a:visible` text "Sale" then `span:visible` text "Bill" (ids like `menu-2-<random>` change: never use) |
| New bill | button text "Create/F2" (route `/sale/salebook/bill` then `/transaction`) |
| Party picker | dialog "Select Party", rows ag-Grid; `#SearchBox`; Enter selects the highlighted row |
| Header | `#txtLedgerName88`, `#txtbillDate88`, `#txtentryNo88`, `#txtptmobile88`, `#txtptname88` |
| Barcode cell | `#txt-tmp_barcode-0` (row n: `#txt-tmp_barcode-n`) |
| Item picker | `#searchItems`; variant list `#SearchBox`; qty window input `#txt-qty-0`; qty window Save F10 |
| Grid cells | `.ag-row` filtered by text, cell `[col-id="quantity"]`, `[col-id="salePurchaseRate"]`, `[col-id="DisplayAmount"]`, `[col-id="itemLinkID"]` |
| Tax info | footer table rows "CGST Output" / "SGST Output" / "IGST Output" (`[col-id="amount"]`); "Invoice Value :" label |
| Buttons | `#btnSave88` (F10/End), `#btnDraft88`, `#btnEsc88` |
| Alert | dialog titled "Alert!" with OK button |

Keyboard flow that worked: Create/F2 (party dialog opens) -> Enter on highlighted party (or ArrowDown n then Enter) -> Enter in empty barcode cell opens item picker -> type search text -> Enter (variant list) -> Enter (qty window) -> Ctrl+A, type qty, Tab -> F10. Waits of 3-4 s between steps were needed.

## Plan SI-A: intra-state bill (SI-01, SI-03)
1. Open Sale > Bill, click Create/F2. Expect "Select Party" dialog with 9 ledgers.
2. Choose `Ajay`. Expect Tax Info labels CGST and SGST (no IGST), cursor in barcode cell.
3. Add `Sample Item` variant 11110001, qty 3. Expect row qty 3.000, rate 100.000, amount 300.000.
4. Expect CGST Output 7.500, SGST Output 7.500, Invoice Value 315.000 (oracle: 5% on 300 = 15.00).
5. Add `Barcdoe` qty 3. Expect added CGST 84.000, SGST 84.000; Invoice Value 315 + 768 = 1083.000 (UNVERIFIED rupee round-off of mixed bills: 1083.000 is already whole).
6. Do NOT save during exploration; the generated test saves only after the human approves test data creation (Q1). On save expect print preview (assumed, SI-05) and the bill in the list with amount 1083.00.
Data: oracle `gst_calc.line_tax(Decimal("300"), 5, intra_state=True)` etc.

## Plan SI-B: inter-state bill (SI-02, SI-04)
1. Same as SI-A with `Arun Sharma`. Expect Tax Info label IGST only.
2. Sample Item qty 3: IGST Output 15.000, Invoice Value 315.000. Barcdoe qty 3: IGST 168.000.
Expected: no CGST/SGST rows with non-zero amounts.

## Plan SI-C: boundaries (SI-07..SI-14)
1. Rate edit: double-click `[col-id="salePurchaseRate"]` on the Sample Item row, Ctrl+A, type 33.33, Enter. Expect screen CGST 0.833, SGST 0.833, Invoice Value 34.996 for qty 1 (observed); the oracle value 1.67 (half-up) applies only after D5 and only to the saved bill. Test asserts the 3-dp display only as an "observed" value or is skipped with reason "D5: rounding rule".
2. Qty 0 and -2: after F10 in the qty window expect no row added (observed) and record any alert text. Marked skip with question until D7 is answered; do not assert absence silently.
3. Date: set `#txtbillDate88` to 05-10-2027, 01-03-2026 (outside books) and 06-10-2026; expected behaviour UNVERIFIED -> skip with D6 reason.
4. Wrong barcode: type 99999999 in `#txt-tmp_barcode-0`, Enter; expect Alert! "Barcode Not Available", OK closes it. Safe (not saved).

## Plan SI-D: invalid GSTIN negative (SI-17, SI-18)
UNVERIFIED path: Master > Ledger (or party picker's Create/F2, or the pencil icon in "Select Party") opens a ledger form; GSTIN field label/id not yet seen. Steps once found: type bad-format value (`DataFactory.invalid_gstin_format()`), e.g. 14 characters; Tab; observe inline error; then a 15-character value with valid structure but wrong last character (`DataFactory.valid_gstin()` with the check character altered). Expect: error text visible, form not saved. Do not click Save. NEEDS DECISION: need the field locators and error wording; plan to capture with Playwright MCP before generation.

## Plan SI-E: reconcile (SI-05, SI-06, SI-28) after human approval to create data
1. Save SI-B bill (Arun Sharma, Sample Item qty 3): list `/sale/salebook/bill` shows it, amount 315.00.
2. GSTR-1 for the month: B2B vouchers +1, taxable +300.00, IGST +15.00 (see `gst-report-export.md`). Party balance of Arun Sharma changes by 315.000 Dr.

## Open questions / NEEDS DECISION
- D4 slab by date and whether 40% exists; D5 rounding (banker's vs half-up, per line vs per bill, 3-dp display vs 2-dp save; flagged table rows DIFF/HALF-DIFF); D6 future/out-of-books dates; D7 zero/negative qty message.
- Q1 may tests save bills in this pre-prod tenant, and how do they delete or cancel them?
- Q2 what are the Calculation Type option labels and is value 2 Exclusive? (Observed behaviour is exclusive.)
- Q3 home state code and Ajay / Arun Sharma states and GSTINs (to document intra/inter).
- Q4 does `Additional Charges On Free Items` (matched by typing "Ajay") belong in the party list?
- D9 `data-testid` list requested: party dialog, `#txt-tmp_barcode-n`, qty window, tax info rows, Invoice Value, Save buttons (stable ids without the window number).
