# Plan: J20 e-invoice generation and error list

Scenario pack: `scenarios/e-invoice.md`. Status: DRAFT for QA/BA review. Observed live on 2026-10-08 (garments
account, company "Garments New 29-08", app V. 4.3.598.b). Read-only: no test saves a bill or touches the IRP.

## Safety decision
- No test presses Generate, Get IRN, Manual, Bill To Ship or any Cancel action on an e-invoice. These call
  `/EInvoiceGSP/*` (DataIntegrationSvc), which forwards to a GSP and the government IRP.
- Sandbox not proven: the KB and code index name no sandbox GSP/IRP URL, and the garments company's E-Invoice
  Configuration has an empty GSP User ID and Password. IRN generation stays NEEDS DECISION (Q-EI-1).
- The page object `pages/reports/e_invoice_summary_page.py` has no method for those buttons, by design.

## Preconditions
- `page_as("garments")`, company "Garments New 29-08", Control Room "E-Invoice" = Yes (observed, not changed).
- Known data: B2B bill 0000013 of 03-09-2026 to Arun Sharma (GSTIN 33AAACT0763E1ZS, Central), bill 568.00, taxable
  444.00, tax 124.32, no IRN (Pending). Same bill as the J06 GSTR-1 baseline. If it is ever e-invoiced or deleted, the
  EI-02/03/04/16 tests need a new pending bill.

## Locators
| Thing | Locator |
|---|---|
| Open | side menu link "Report" (`DocumentScreen.open_menu(("Report",))`) -> role tab "Statutory Report" -> role link "E-Invoice" |
| Heading | role heading "E-Invoice Summary" |
| Period | `select#txtdateType` (no label); From/To `input#txtfromDate`, `input#txttoDate` (disabled unless Custom) |
| Status | `select#txtDatadropdown`: All, Uploaded, Pending, Cancelled |
| Document types | `input#b2b`, `input#cdnr` (no labels; text "B2B", "CDNR" sits beside them) |
| Submit | role button "Submit" in main |
| Grid | role row containing gridcell "<invoice no>"; selection box `.ag-selection-checkbox` (first cell; ag-Grid has no role for it) |
| Counter | paragraph "Uploaded- n Pending- n Cancelled- n" |
| Actions after ticking | role buttons Generate, Bill To Ship, Get IRN, Manual (NOT pressed) |

## Tests (`tests/journeys/gst/test_e_invoice.py`, fixture `e_invoice_summary` in `tests/journeys/gst/conftest.py`)
| Test | Scenario | Steps / expected |
|---|---|---|
| test_ei01_summary_offers_status_filter_document_types_and_bill_columns | EI-01 | Status options All/Uploaded/Pending/Cancelled; B2B and CDNR unticked; 8 named columns |
| test_ei06_this_year_period_spans_the_financial_year | EI-06 | This Year -> From 01-04-2026, To 31-03-2027 (books period in the header) |
| test_ei02_bill_to_registered_party_is_listed_with_gstin_and_amounts | EI-02 | This Year, All, B2B+CDNR, Submit -> row 0000013 with all 8 values above |
| test_ei03_pending_filter_lists_bill_without_irn_and_counts_it | EI-03 | Pending -> row listed, Pending counter >= 1 (other bills may join) |
| test_ei04_bill_without_irn_is_not_listed_as_uploaded_or_cancelled[Uploaded/Cancelled] | EI-04 | Listed under All, then Uploaded / Cancelled + Submit -> row gone |
| test_ei16_irn_actions_appear_only_once_a_pending_bill_is_ticked | EI-16 | No Generate/Get IRN before ticking; tick 0000013 -> both shown; nothing pressed |

## Not automated
- EI-05 Submit with B2B and CDNR unticked: no request is sent and no message shown; on a fresh screen the test could not
  tell "filtered out" from "never loaded", so it is left out. Q-EI-3.
- EI-07 reconciliation with GSTR-1: values equal the J06 baseline (444.00 / 124.32 / 568.00) by observation; a combined
  test is left to J06.
- EI-08 unregistered (B2C) bill not listed: needs a saved B2C bill this year; none observed. Q-EI-4.
- EI-09..EI-14 generation, IRP error list, Duplicate IRN, Get IRN, cancel, and the "Want to generate E-invoice ?" prompt
  after saving a bill: NEEDS DECISION Q-EI-1 (they submit to the IRP or save bills).
- EI-15 Export: UNVERIFIED.

## NEEDS DECISION / open questions
- Q-EI-1 Is there a sandbox GSP/IRP for the QA tenant (URL and test GSTIN credentials)? Until then, IRN generation,
  the IRP error list and cancel are not tested. The "error list" of J20 only exists after a submission (KB: errors such
  as "GSTIN is Invalid / Unregistered", "The Address Field is Required" come back from the IRP).
- Q-EI-2 KB shows "Cancel Invoice" on the summary; live, only Generate, Bill To Ship, Get IRN, Manual appear for a
  pending bill. Where is cancel for uploaded bills (summary or sale list)?
- Q-EI-3 Should Submit without B2B or CDNR show a validation message? Today it silently does nothing.
- Q-EI-4 Which seeded bill can serve as a B2C/unregistered negative case?
- Q-EI-5 Security (defect candidate): in Control Room > E-Invoice > Configure, the GSP "Password" input is
  `type=text`, so a stored password would show in clear text. Expected masked. Not asserted in a test because the
  expected behaviour is not written in a MargBooks spec; confirm and log.
- Q-EI-6 Control Room "Alert to generate E-Invoice" = Yes on garments: any test that saves a sale bill will be asked
  "Want to generate E-invoice ?". Tests must answer No. Confirm this setting is intended on the QA company.
