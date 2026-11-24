# Plan: J06 GST report generation and export

Scenario pack: `scenarios/gst-report.md`. Status: DRAFT for human review. All steps below were observed live on 2026-10-05 unless marked UNVERIFIED. Read-only: reports and downloads change no data.

## Preconditions
- `page_as("garments")`. Known dataset: Sept 2026 holds one B2B bill: 1 voucher, taxable 444.00, IGST 124.32, invoice 568.00. Tests that compare against this baseline must tolerate other tests adding bills in the same period: baseline-then-delta, or use a period (e.g. Aug 2026) that stays empty.
- Never wait on networkidle (never settles). A "Bad Network" banner may appear under load: run report tests with few workers.

## Locators
| Thing | Locator |
|---|---|
| Route | `/report/gst/gstr1` (direct), `/report/gst/gstr3b`; or Report > Statutory Report tab > "GSTR-1" |
| Grid | ag-Grid col-ids `Particulars`, `Vouchers`, `TaxableValue`, `IntegratedTax`, `CentralTax`, `StateTax` |
| Row | grid row filtered by text "Taxable Sales", "HSN/SAC Summary", "Document Summary" |
| Period | press Alt+D -> dialog "Date Filter": `#fromDateFilter`, `#toDateFilter`, `#btn-Ok`, `#btn-Close` |
| Title | heading text "GSTR-1 dd-mm-yyyy to dd-mm-yyyy" |
| Exports | `a[title="Excel"]`, `a[title="PDF"]`; bottom `#btn-GSTR1 Returns`, `#btn-Detail Excel`, `#btn-GST Summary`, `#btn-IFF`; GSTR-3B `#btn-JSON` |
| IFF dialog | text "GSTR 1: IFF Facility", Monthly/Quarterly, month list, Excel, JSON, Cancel |

## Plan GR-A: screen values (GR-01)
1. Navigate to `/report/gst/gstr1`; wait for the grid row "Taxable Sales".
2. Expect title "GSTR-1 01-09-2026 to 30-09-2026" (default was previous month; UNVERIFIED that it stays previous month always: set the period explicitly instead via Alt+D).
3. Expect Taxable Sales: Vouchers 1, TaxableValue 444.00, IntegratedTax 124.32, CentralTax 0.00, StateTax 0.00. HSN/SAC Summary 1 / 444.00 / 124.32. Document Summary 1.

## Plan GR-B: export matches screen (GR-02, GR-03)
1. Run GR-A. Read the on-screen rows into Decimals via `parse_amount`.
2. Click `a[title="Excel"]` inside `page.expect_download` (allow 90 s). Expect filename `GSTR-1 01-09-2026 to 30-09-2026.xls`.
3. Read the file as HTML (it is an HTML table with .xls extension; do not open with openpyxl/xlrd). Expect header row: Particulars, No. of vouchers, Taxable Value, Integrated Tax, Central Tax, State Tax, Cess, Tax Amount, Invoice Amount.
4. Expect for the "Taxable Sales" row: vouchers equal screen, taxable, IGST, CGST, SGST equal screen, Tax Amount = IGST+CGST+SGST+Cess (124.32), Invoice Amount 568.00 (rupee round-off) and for HSN/SAC row 568.32 (= 444.00 + 124.32). Assert the 0.32 difference only as an observed value, flagged question G-Q2.
5. Totals reconcile: Taxable + Tax Amount == HSN Invoice Amount (independent arithmetic).

## Plan GR-C: period change and empty period (GR-04, GR-11, GR-12, GR-14)
1. Alt+D; `#fromDateFilter` = 01-08-2026, `#toDateFilter` = 31-08-2026; `#btn-Ok`. Expect title for August and all rows 0.00 (UNVERIFIED that August is empty: check once). Export still downloads with header (UNVERIFIED).
2. Boundary: from 30-09-2026 to 30-09-2026 includes the Sept bill if dated 30-09 (UNVERIFIED bill date); 01-10-2026 excluded.
3. From later than To: record the validation text; skip until known.

## Plan GR-D: other exports (GR-05..GR-08) UNVERIFIED
- `#btn-GSTR1 Returns`, `#btn-Detail Excel`, `#btn-GST Summary`, PDF icon: each in `expect_download`; assert only that a non-empty file arrives until formats are inspected (my click attempts were blocked by an overlay and network banner). JSON: parse and compare b2b totals to screen once format known.
- IFF: open dialog, choose Monthly + Sep + JSON; UNVERIFIED output.
- GSTR-3B: open `/report/gst/gstr3b`; the grid was empty in my run; find whether it needs a longer wait or a generate action, then assert ITC and outward tax lines against the oracle after a saved purchase/sale.

## Plan GR-E: reconcile with J04/J05 (GR-09, GR-20) needs approval to save bills
Record baseline for the month, save SI-B (IGST 15.00, taxable 300.00) and PU-B, reload report and export; expect deltas exactly equal to the oracle; export deltas equal screen deltas.

## Open questions
- G-Q1 which period does the report default to (previous month vs current)? Date dialog pre-fills the current month.
- G-Q2 why does B2B Invoice Amount (568.00) differ from HSN Invoice Amount (568.32)?
- G-Q3 format/location of JSON for GSTR-1/3B and what "GST Summary", "Detail Excel", "Reconcile GSTR1" (disabled?) produce.
- G-Q4 B2C Large/Small thresholds for party without GSTIN.
- G-Q5 role/permission for reports (D10) and second company for tenancy.
- Q1 permission to save bills for the reconcile plan; D4 slab-by-date; D5 rounding; D9 `data-testid` for report grid rows, export buttons and Date Filter fields.
