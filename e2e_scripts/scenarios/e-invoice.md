# Scenario pack: J20 e-invoice generation and error list

Journey J20 (matrix slug `e-invoice`, P1). Source tags: KB = Tech Debt Radar KB chunk (id prefix given), CODE = code index
chunk, LIVE = live observation on the QA tenant (garments account, company "Garments New 29-08", 2026-10-08, read-only).

## Safety first
Generating an IRN submits the bill to the government IRP through a GSP (KB 706a3dc6, ef77ef1d: Marg works with GSP
"Pinnacle Finserve Advisors"). Cancelling an IRN is irreversible and only allowed within 24 hours (KB c54d0b86).
- CODE d02a6ebe/cf1524dd: `POST /EInvoiceGSP/GenerateIRN`, `GET /EInvoiceGSP/authenticate`, `GET /EInvoiceGSP/GetIRNDetails`
  live in `MargApp.DataIntegrationSvc.Api`; the GSP/IRP base URL is not in the indexed chunks and the KB names no
  sandbox. Nothing proves the QA tenant talks to a sandbox IRP.
- LIVE: Control Room > "E-Invoice" = Yes and "Alert to generate E-Invoice" = Yes on the garments company, but its
  E-Invoice Configuration has an empty "GSP User ID" and "Password". So no IRN can be generated from this tenant today.
- Decision taken for the suite: no test generates, fetches ("Get IRN") or cancels an IRN. Generation is NEEDS DECISION.

## Facts from the KB and code
- Menu: Report > Statutory Report > E-Invoice opens the "E-Invoice Summary" window. Period (Today, This Year...), status
  filter All / Uploaded / Pending / Cancelled, check boxes B2B and CDNR, Submit; the list then lets the user tick bills
  and "Generate", "Get IRN" or "Cancel Invoice". KB 6089afd3, 2b380963, 820de7e5, 9f0e694d, d611afd8.
- E-invoice while billing: Control Room "E-Invoice" = Yes, Configure (GSP user id, password, QR data HSN/Item wise,
  alert). After saving a sale bill the app asks "Want to generate E-invoice ?" Yes/No. KB 11554bc0, 86f3f58f, f6d9f63b.
- Sale bill list has an E-Invoice / Cancel E-Invoice action (FRD). KB 0b968bb3, 00923129.
- The list comes from `POST /EInvoice/GetEInvoiceReport` (`usp_EinvoiceReport`); the response is stored with
  `POST /EInvoice/InsertEInvoiceResponse` (`dbo.EInvoiceResponse`). CODE 605e885d, ffd51ee5.
- Error messages users meet (all returned by the IRP, i.e. only after submitting): "Duplicate IRN" (KB 17ffb742,
  Jira MB-037796), "GSTIN is Invalid / Unregistered" (KB 84303936), "The Address Field is Required" (KB f0c95f1d),
  "SGST and CGST amount passed does not match with taxable value and tax rate" (ticket 233b40a4).
- Known field complaints: pending list blank although bills are not e-invoiced (Jira MB-038353, ticket ae19aef3),
  bills missing from the list (ticket c4a45bc9), the same invoice listed 2-3 times (ticket 1780cd6d).

## Live facts (LIVE)
- Direct route `/report/e-invoice`; heading "E-Invoice Summary" (h1). Buttons Export (`#btn-Export`), Back, Submit
  (`#submit`), "Esc Cancel" (`#btn-Ledger`). Period select `#txtdateType`: Today, This Month, Yesterday, Last 7 Days,
  This Week, Previous Month, This Year, Custom; From/To (`#txtfromDate`, `#txttoDate`) are disabled unless Custom. "This
  Year" fills 01-04-2026 / 31-03-2027. Status select `#txtDatadropdown`: All, Uploaded, Pending, Cancelled.
  Check boxes `#b2b`, `#cdnr` (a hidden `#export` too), both unticked on open.
- Grid columns: (selection), Name of the Customer, GSTIN, Tax Type, Invoice Date, Invoice No, Bill Amount, Taxable Value,
  Tax Amount. Counter paragraph "Uploaded- 0Pending- 0Cancelled- 0".
- Submit with neither B2B nor CDNR ticked sends no request and the list stays empty.
- This Year + All + B2B + CDNR: one row "Arun Sharma | 33AAACT0763E1ZS | Central | 03-09-2026 | 0000013 | 568.00 |
  444.00 | 124.32"; counter Pending- 1. Same row under Pending. Under Uploaded and Cancelled: no row, counter all 0.
  API filter values: All 0, Pending 2; dataType "2,4,6".
- Navigation: side menu "Report" -> tab "Statutory Report" (role tab) -> link "E-Invoice". A full page load of
  `/report/e-invoice` also works but restarts the app session (a `LoginUser/Logout` call was seen around it), so tests
  use the menu.
- No action buttons until a row is ticked; ticking the pending bill shows Generate, Bill To Ship, Get IRN and Manual
  (ticking sends no request). No "Cancel Invoice" button seen for a pending bill.
- E-Invoice Configuration dialog: GSP User ID (`#txt4118`), Password (`#txt4119`, an `input type=text`, not a password
  field), Upload Data For QRC Code (HSN Wise), Alert to generate E-Invoice (Yes).

## Scenarios
| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| EI-01 | Positive | Open E-Invoice Summary | Heading, period, status, B2B/CDNR, Submit, grid headers as listed | LIVE |
| EI-02 | Positive | This Year + All + B2B + CDNR | B2B bill to registered party Arun Sharma listed with GSTIN, date, number, amounts | LIVE |
| EI-03 | Positive | Status Pending | The not-yet-uploaded bill is listed; counter Pending- 1 | LIVE, KB 6089afd3 |
| EI-04 | Positive | Status Uploaded / Cancelled | Not-uploaded bill is not listed | LIVE |
| EI-05 | Negative | Submit with B2B and CDNR unticked | No bill listed | LIVE (question Q-EI-3: no message shown) |
| EI-06 | Positive | Period filter: This Year fills 01-04-2026..31-03-2027 and Custom enables dates | LIVE |
| EI-07 | Reconcile | Listed amounts equal the GSTR-1 B2B row for Sept 2026 (444.00 / 124.32 / 568.00) | J06 spec, LIVE |
| EI-08 | Negative | Bill to an unregistered party (no GSTIN) is not listed under B2B | UNVERIFIED: needs a saved B2C bill (Q-EI-4) |
| EI-09 | Security | E-Invoice configuration password field masks the value | EXPECTED by rule 5 of the programme; LIVE: input type=text (defect candidate) |
| EI-10 | Positive | Generate IRN for a pending bill; IRN, Ack No, Ack Date shown; status Uploaded | NEEDS DECISION (sandbox) |
| EI-11 | Negative | Generate for an invalid bill shows the IRP error list (invalid GSTIN, address required, tax mismatch) | NEEDS DECISION (submits to IRP) |
| EI-12 | Negative | Generate again for an uploaded bill: "Duplicate IRN"; Get IRN recovers details | NEEDS DECISION |
| EI-13 | Positive | Cancel an IRN within 24 h with a reason | NEEDS DECISION; never cancel an IRN the test did not create |
| EI-14 | Positive | Save a sale bill: "Want to generate E-invoice ?" prompt; No keeps the bill pending | NEEDS DECISION (saves a bill; "Yes" would submit) |
| EI-15 | Positive | Export button downloads the list | UNVERIFIED |
| EI-16 | Positive | Ticking a pending bill reveals Generate and Get IRN; nothing ticked, no actions | LIVE (buttons not pressed) |
