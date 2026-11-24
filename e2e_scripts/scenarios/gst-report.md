# Scenario pack: J06 GST report generation and export (GSTR)

Journey J06 (matrix slug `gst-reports`). Source tags: LIVE = live observation 2026-10-05 (read-only); CODE = from
`docs/prd/02-prd-api-and-calculation.md` (GSTR1 7 endpoints, GSTR2 1, GSTR3 4, `MargExcelDataExportController`; not read by me).

## Live facts
- Menu: Report > Statutory Report tab (route `/report/combine-report/<number>`; the tab list is Accounts, Inventory, Statutory, Management, Report Designer). Statutory lists: E-Way Bill, E-Invoice, GST Report: GSTR-1, GSTR-2, GSTR-3B, GSTR-2B Reconciliation, GSTR-2A Reconciliation, GSTR-9 (Annual), and Misc. GST Reports: Internal Audit, GST Tax Register. LIVE
- Direct routes: `/report/gst/gstr1`, `/report/gst/gstr3b` (coordinator: also GSTR-1, GSTR-2, GSTR-3B spellings). LIVE
- GSTR-1 screen: title "GSTR-1 01-09-2026 to 30-09-2026"; the default period was the previous month while the date dialog pre-fills 01-10-2026..31-10-2026 (current month): a mismatch to ask about. Period selector: Alt+D, or click the date strip, opens "Date Filter" with `#fromDateFilter`, `#toDateFilter` (dd-mm-yyyy mat-datepicker inputs), buttons `#btn-Ok`, `#btn-Close` (Esc). No monthly/quarterly picker on the main grid (only on IFF). LIVE
- GSTR-1 grid col-ids: `Particulars`, `Vouchers`, `TaxableValue`, `IntegratedTax`, `CentralTax`, `StateTax` (screen also has Cess/Tax Amount/Invoice Amount to the right, as in the export). Rows: B2B Invoices - 4A,4B,4C,6B,6C (Taxable Sales, Reverse charge supplies), B2C(Large) - 5A,5B, B2C(Small) - 7, Credit/Debit Notes (Registered/Unregistered) - 9B, Exports - 6A, Tax Liability (Advances) 11A, Adjustment of Advances 11B, Nil Rated Invoices 8A-8D (Nil Rated, Exempted, Non-GST), Total, HSN/SAC Summary, Document Summary. LIVE
- Export controls on GSTR-1: top-right `a[title="Excel"]`, `a[title="PDF"]`, a menu icon (`a.addEffset`, contains "Refresh List"), bottom buttons `#btn-GST Summary`, `#btn-GSTR1 Returns`, `#btn-IFF`, `#btn-Detail Excel`, `#btn-Reconcile GSTR1` (looked disabled). IFF opens "GSTR 1: IFF Facility" dialog: Return Type Monthly/Quarterly, Month (Apr..Mar), buttons Excel | JSON | Cancel. GSTR-3B has Excel, PDF and `#btn-JSON`. LIVE
- Excel download: filename "GSTR-1 01-09-2026 to 30-09-2026.xls"; the file is HTML (not a binary xls): parse with an HTML table reader. Header row: Particulars, No. of vouchers, Taxable Value, Integrated Tax, Central Tax, State Tax, Cess, Tax Amount, Invoice Amount. B2B Taxable Sales row: 1, 444.00, 124.32, 0.00, 0.00, 0.00, 124.32, 568.00. HSN/SAC row: 1, 444.00, 124.32, 0.00, 0.00, 0.00, 124.32, 568.32. Document Summary: 1. LIVE
- Known dataset: Sept 2026 holds exactly one B2B bill (party balance Arun Sharma 568 Dr suggests him), taxable 444.00, IGST 124.32 (= 28%), invoice 568.00 after round-off. This is the baseline for reconciliation tests. LIVE
- The bottom-button clicks (GST Summary, GSTR1 Returns, Detail Excel) were not completed because a "Bad Network" banner and an open menu overlay blocked my script; their output is UNVERIFIED. Heavy concurrent browsing caused "Bad Network".

## Scenarios
| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| GR-01 | Positive | Open GSTR-1 for 01-09-2026..30-09-2026 | B2B Taxable Sales: vouchers 1, taxable 444.00, IGST 124.32, CGST 0.00, SGST 0.00; HSN row 1 / 444.00 / 124.32; Document Summary 1 | LIVE |
| GR-02 | Positive | Excel export for GR-01 downloads and parses | File name starts "GSTR-1 01-09-2026", header row exactly as listed, B2B row values equal the on-screen row, HSN row equal, vouchers equal | LIVE |
| GR-03 | Positive | Export totals equal screen: sum of tax columns = Tax Amount; Taxable + Tax vs Invoice Amount | HSN row 444.00 + 124.32 = 568.32 holds; B2B Invoice Amount 568.00 differs by round-off 0.32 | LIVE (computed). Question: is the 0.32 gap intended? |
| GR-04 | Positive | Change period with Alt+D to 01-10-2026..31-10-2026 | Header title and numbers refresh; Oct has no bill unless tests create one | LIVE (dialog); result UNVERIFIED |
| GR-05 | Positive | GSTR-3B opens and offers JSON | JSON button present; content UNVERIFIED | LIVE partial |
| GR-06 | Positive | IFF dialog Monthly/Quarterly, Excel and JSON options | Dialog fields as listed; downloads UNVERIFIED | LIVE partial |
| GR-07 | Positive | PDF export | A PDF downloads; content UNVERIFIED | UNVERIFIED |
| GR-08 | Positive | GSTR-1 JSON ("GSTR1 Returns") is valid JSON with b2b, hsn sections and totals equal to the screen | UNVERIFIED | CODE GSTR1 endpoints; question |
| GR-09 | Reconcile | Create a sale (SI-01) in the period, GSTR-1 B2B rows increase by 1 voucher, taxable +300, IGST/CGST/SGST per table; export follows | Delta equals the oracle | UNVERIFIED (needs saving; cross-ref J04). PRD 02: GSTR-1 totals equal sum of the period's bills |
| GR-10 | Reconcile | Party without GSTIN (B2C) lands in B2C Large/Small, not B2B | UNVERIFIED; threshold rules not read | question |
| GR-11 | Boundary | Empty period (no bills) | Rows show 0.00 and export still downloads with header | UNVERIFIED; PRD 02 lists empty period |
| GR-12 | Boundary | Period boundaries: 01-09-2026 and 30-09-2026 inclusive, bill on 30-09 included, 01-10 excluded | UNVERIFIED | PRD 02 |
| GR-13 | Boundary | Period spanning FY end (To after 31-03-2027), or before 01-04-2026 | UNVERIFIED validation | D6-like question |
| GR-14 | Negative | From later than To in Date Filter | Validation message UNVERIFIED | question |
| GR-15 | Negative | Invalid date text in `#fromDateFilter` | UNVERIFIED | question |
| GR-16 | Boundary | Credit/Debit note rows after a sale return | UNVERIFIED | question |
| GR-17 | State | Edit/delete a bill in the period then the report | Report follows; UNVERIFIED | question |
| GR-18 | Permission | Role without report rights opens the URL | UNVERIFIED, no role accounts (D10) | skip with reason |
| GR-19 | Tenancy | Another company data absent | UNVERIFIED, no second company | skip with reason |
| GR-20 | Output | GSTR-2 and GSTR-3B ITC reconcile with purchase bills (cross-ref J05) | UNVERIFIED; GSTR-3B grid empty in my run | question |

## KB vs live app
- PRD 02 says GSTR exports are `MargExcelDataExportController` Excel files; the live "Excel" file is an HTML table named .xls (opens in Excel with a warning). Tests must read it as HTML.
- Main grid default period (Sept) differs from the date dialog pre-fill (Oct).
- B2B Invoice Amount 568.00 versus HSN Invoice Amount 568.32 in the same export.
- The `Reconcile GSTR1` button looked disabled for this company (maybe needs GST portal credentials).
