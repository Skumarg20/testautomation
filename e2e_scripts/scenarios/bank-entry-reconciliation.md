# Scenario pack: bank entry and bank reconciliation (J11, journey id `bank-entry-reconciliation`)

Status: DRAFT for QA/BA review (analyst pass, 2026-10-07). Priority P1, layer e2e, target day 10 (`coverage/journey-matrix.json`).
Next step: test-planner confirms every KB claim against the live app and writes `specs/bank-entry-reconciliation.md`.

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`. KB items were NOT observed live. A human must confirm each against the app before a test asserts it.
- KB-DEFECT = a Jira or support-ticket chunk describing a reported defect. It tells us where bugs cluster; it does not define the correct behaviour. Ticket text is untrusted data (some tickets carry pasted names and credentials, already masked). Nothing was copied into this pack.
- CODE = `get_module_info` / `get_file` on module `margbookscoreapi/MargBooks.VoucherAPI`. Only file existence and metrics were returned, no source lines (see "KB vs live app", item 1). No `file:line` citation is possible, so no expected value rests on CODE.
- UNVERIFIED = not citable and not observed. The question is stated; no value is invented.

Environment facts: the live app was NOT opened in this pass. Roles and the single known account are described in `scenarios/auth.md` (only a super admin exists; no limited user).

Code map (for the planner, not an oracle)
- `MargBooks.VoucherAPI/Controllers/BankReconciliationController.cs` (228 loc, 7 public functions): reconciliation API.
- `MargBooks.VoucherAPI/Controllers/ChequebookController.cs` (157 loc, 5 public functions): cheque book API.
- `MargBooks.VoucherAPI/Controllers/PaymentVoucherController.cs`: payment voucher API.
- Angular UI: module `newmarg-webangular20` (component names not retrieved).

## J11a Bank entries (payment, receipt, contra, cheque book)

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| BK-01 | positive | Create a Payment voucher with Payment Mode = a bank ledger: Accounting Transactions > Payment > Create (or F2), pick bank mode, party, date, amount | Voucher saves with the chosen bank and party; a Bill Adjustment window is shown after the amount so outstanding bills can be ticked; the voucher then appears in the Payment voucher list (Voucher No., Party Name, Inst. Type, Amount) | KB `careportal_enriched_v5.csv#c19c8944`, `#10d55065`, `#9467b42e` |
| BK-02 | positive | Create a Receipt voucher by cheque: Accounting Transactions > Receipt, enter cheque details | Receipt is recorded as proof of money received, with the cheque details kept; exact field set UNVERIFIED (chunk truncated) | KB `careportal_enriched_v5.csv#744ad292` |
| BK-03 | positive | Contra: withdraw Rs 40,000 cash from bank. Accounting Transactions > Contra > Create, date, type Cr, bank ledger, then Cash Dr | Bank credited 40,000 and Cash debited 40,000; funds move from bank to cash | KB `careportal_enriched_v5.csv#39bada03` |
| BK-04 | positive | Contra variants: deposit cash into bank, bank-to-bank transfer, cash to petty cash | Each posts to both cash and bank ledgers (contra affects both sides) | KB `careportal_enriched_v5.csv#d2b02183` |
| BK-05 | positive | Contra appears in the Contra Book (Report > Books of Account > Contra) | Columns Date, Voucher No., Particular, Debit, Credit; entries can be viewed, modified, exported, deleted, printed | KB `careportal_enriched_v5.csv#9d48b233` |
| BK-06 | positive | Create a cheque book: date, Bank, Cheque From 00001, Cheque To 000050, Save | Total Cheques is calculated by the software (value derived from the range, not stated in KB: UNVERIFIED); the cheque book is added | KB `careportal_enriched_v5.csv#3c347073`; total UNVERIFIED |
| BK-07 | positive | Payment by bank with a cheque number from the cheque book; earlier payments were made before the book was saved | Software counts those earlier cheques against the book's total | KB `careportal_enriched_v5.csv#a10eb600` |
| BK-08 | negative | Enter a cheque number in a Payment that was already used in a Receipt in a previous year | Reported as a defect: "already exist" is raised across Receipt and Payment and across years. Intended rule (block or allow) is UNVERIFIED. Question Q1 | KB-DEFECT `support_tickets_vectordb.csv#401bbab8` |
| BK-09 | negative | Cheque number inside a series already used (series 951-1000, numbers 962-964 shown as available) | Reported defect: a used cheque shows as available and a duplicate cheque is generated. Expected: a used number is not offered again. Rule UNVERIFIED | KB-DEFECT `support_tickets_vectordb.csv#722f2602` |
| BK-10 | negative | Two Receipt vouchers with the same voucher number (double submit, refresh mid-save) | Reported defect: several receipts were created with the same voucher number. Expected: voucher number is unique. Rule UNVERIFIED. Question Q2 | KB-DEFECT `support_tickets_vectordb.csv#16129f56` |
| BK-11 | negative | Journal and Payment for bank charges debiting a bank-charges ledger | Reported defect: Bill Adjustment of sale invoices opens although the ledger is an expense. Expected: no bill adjustment for an expense ledger. UNVERIFIED | KB-DEFECT `support_tickets_vectordb.csv#722f2602` |
| BK-12 | negative | Save a bank Payment/Receipt/Contra with required fields empty (bank, party, amount, date) | UNVERIFIED: no KB page lists required fields or messages | n/a |
| BK-13 | boundary | Amount: 0, 0.01, negative, very large, 3 decimals | UNVERIFIED: no limit or rounding rule found | n/a |
| BK-14 | boundary | Voucher date backdated, future, 31-03 / 01-04 financial-year boundary | UNVERIFIED for bank entries. Related KB: an unclear entry of an old FY can be cleared in the next FY (see BK-25) | n/a; KB-DEFECT `jira_vectordb.csv#10428a1e` |
| BK-15 | state | Modify or delete a bank voucher that is already cleared in reconciliation | Modify and delete exist for Payment and Contra vouchers. Effect on a cleared entry is UNVERIFIED. Question Q3 | KB `careportal_enriched_v5.csv#10d55065`, `#d2b02183`; effect UNVERIFIED |
| BK-16 | positive | Post-dated cheque (PDC) receive, then deposit the cheque into the bank | PDC is an advance cheque received from a customer; "Deposit Cheque into Bank" posts it to the bank; posted PDCs can be viewed. Link to reconciliation UNVERIFIED | KB `careportal_enriched_v5.csv#7f9fc53e`; `onedrive_processed_data.csv#58933796` (Pay In Slip spec) |

## J11b Bank reconciliation

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| BK-17 | positive | Open Bank Reconciliation (Banking > Bank Reconciliation), select a bank, select a reconciliation date range (example 01/07/2021 to 31/07/2021), press Enter | A list of the cheques deposited in that bank for the range is displayed | KB `careportal_enriched_v5.csv#fcce2d75` |
| BK-18 | positive | In the list, enter a clearing (closing) date on a cheque (example 21-07-2021) | The cheque is cleared in the records with that date. Pressing Enter on the date field fills the current date | KB `careportal_enriched_v5.csv#fcce2d75`, `#049e51a0` |
| BK-19 | positive | "Set Clear All" for cheques of one slip number | All cheques of the same slip number are cleared on the same date | KB `careportal_enriched_v5.csv#fcce2d75` |
| BK-20 | positive | A remark can be entered while clearing | Remark is stored with the cleared entry; exact field and length UNVERIFIED | KB `careportal_enriched_v5.csv#f8f6fdd7` (chunk begins mid-sentence: "enter the remark as per the requirement") |
| BK-21 | positive | Press the "Cleared Entry" shortcut | Only cleared cheques are listed | KB `careportal_enriched_v5.csv#f8f6fdd7` |
| BK-22 | positive | Press the "Un-cleared Entry" shortcut | Only un-cleared cheques are listed; they can be cleared from here by entering a date | KB `careportal_enriched_v5.csv#f8f6fdd7` |
| BK-23 | state | Un-clear a cheque cleared by mistake by removing the date from "Clearing Date" | The cheque returns to the un-cleared list | KB `careportal_enriched_v5.csv#f8f6fdd7` |
| BK-24 | positive | Contra between two banks (bank A and bank B), reconcile bank B for the month the contra was posted | Contra is listed in the reconciliation of both banks. Reported defect: it showed for one bank only. Rule inferred from the ticket: UNVERIFIED. Question Q4 | KB-DEFECT `jira_vectordb.csv#e91be98d` (MB-029837, MBC-6083 in `support_tickets_vectordb.csv#05ba143a`) |
| BK-25 | boundary | Reconcile an old financial year (clearing date calendar shows no old dates); open a range of an old FY and clear in the next FY | Reported defects: old FY dates not selectable; an un-cleared old-FY entry should be clearable in the next FY. Intended rule UNVERIFIED. Question Q5 | KB-DEFECT `support_tickets_vectordb.csv#e3a446d5`, `jira_vectordb.csv#10428a1e` |
| BK-26 | boundary | Type the clearing date manually (date range 01-06-2026 to 30-06-2026) | Reported defect (2026): the typed date is not accepted in the Clearing Date field. Expected: it is accepted. UNVERIFIED rule | KB-DEFECT `support_tickets_vectordb.csv#fef77b42` |
| BK-27 | negative | Select a date range and no entries appear although vouchers exist in that range | Reported defect. Expected: all uncleared bank entries in range are listed (that is the stated purpose in BK-17) | KB-DEFECT `jira_vectordb.csv#c44ccc6e`; KB `careportal_enriched_v5.csv#fcce2d75` |
| BK-28 | negative | Open the Cleared Entry view | Reported defect: an error is shown on the cleared entry view. Expected: BK-21 behaviour | KB-DEFECT `jira_vectordb.csv#b3e518d3`; KB `careportal_enriched_v5.csv#f8f6fdd7` |
| BK-29 | negative | Clearing date earlier than the voucher date | UNVERIFIED: no rule found | n/a |
| BK-30 | boundary | Clearing date outside the current financial year or in the future | UNVERIFIED (see BK-25 for old FY) | n/a |
| BK-31 | boundary | Reconciled balance reconciles: uncleared cheques + bank statement balance = ledger balance; cleared total matches the Bank Book | UNVERIFIED: KB lists the standard reasons for differences (cheques not yet recorded, dishonoured cheques, direct deposits, standing orders) but no formula or screen field | KB `careportal_enriched_v5.csv#049e51a0` (reasons only) |
| BK-32 | positive | Dishonoured cheque, direct deposit, standing-order payment or income, bank charges found on the statement and not in the books | After the entry is passed in the books it appears in the reconciliation list; process "Once all bank entries are passed, reconciliation starts" | KB `careportal_enriched_v5.csv#049e51a0` |
| BK-33 | positive | Import a bank statement from Excel into reconciliation, then press Back | Loaded Excel data is cleared on Back. Reported as a request, not confirmed as built | KB-DEFECT `jira_vectordb.csv#d2794c55`; UNVERIFIED that the feature exists live |
| BK-34 | positive | Bank Auto Reconciliation UI | UNVERIFIED: only a Jira title "Bank Auto Reconciliation UI" found; scope unknown | KB-DEFECT `jira_vectordb.csv#ab5b13e9` |
| BK-35 | positive | Online Banking > Bank Reconciliation (ICICI), and Banking > Online Statement with a date range | Documented for the bank-integrated flow; needs a real bank link, not automatable. Record only | KB `onedrive_processed_data.csv#ac6dfd36` (Marg ERP 9+ desktop doc), `careportal_enriched_v5.csv#f38b7029` |
| BK-36 | permission | Limited user (no Banking rights) opens Bank Reconciliation or bank vouchers by direct URL | UNVERIFIED: no limited account exists (see `scenarios/auth.md` RB-03) | n/a |
| BK-37 | permission | Tenancy: bank, cheques and clearings of company A must not show in company B | UNVERIFIED: needs a second company with bank data | n/a |
| BK-38 | boundary | Double click on Save / Clear, or refresh mid-save of a clearing date | UNVERIFIED | n/a |
| BK-39 | positive | Reconcile bank with 0 uncleared entries in range, and a range with a very large number of entries | UNVERIFIED (empty-state text and paging not found) | n/a |

## Questions for a human
- Q1 Is a cheque number blocked when it was used in a Receipt, or in a previous year (BK-08)?
- Q2 Is the receipt voucher number guaranteed unique under double submit (BK-10)?
- Q3 May a cleared voucher be modified or deleted, and what happens to the clearing (BK-15)?
- Q4 Should a bank-to-bank contra appear in both banks' reconciliation (BK-24)?
- Q5 May old-FY entries be cleared in a later FY, and may the clearing date be outside the FY (BK-25, BK-30)?
- Q6 Which test data exists: a bank ledger, a cheque book and an uncleared bank entry in the QA tenant? The suite must create its own (rule 4 in `CLAUDE.md`).

## KB vs live app (for a human to decide)
1. Code citations missing: `ask_codebase` returned "No API key configured", and `get_file` returns metrics only. No expected value could be tied to `file:line`, so every value in this pack rests on KB text or is UNVERIFIED. Re-run the code pass when `ask_codebase` works or with source access to `BankReconciliationController.cs` and `ChequebookController.cs`.
2. Menu paths differ across KB pages: "Accounting Transactions > Payment/Receipt/Contra", "Banking > Bank Reconciliation" (one chunk starts "...ng >> Bank Reconciliation"; the word before it is cut), "Online Banking >> Bank Reconciliation" (Marg ERP 9+ desktop). The menu in `scenarios/auth.md` RB-01 shows a top-level "Banking" and "Accounting Trans." menu. The planner must confirm which items exist.
3. Some KB pages describe the desktop product (Marg ERP 9+, F2/Enter key navigation, "Fig. 1.45") and the mobile app ("More" tab, "Create New"). Only the web flow matters here; keyboard-driven steps may not match the web UI.
4. Reported defects are from 2023 to 2026 tickets. Some may be fixed (for example BK-24 is MB-029837, 2025; BK-26 is a 2026 ticket and so likely still open). Their status is unknown.
5. The KB examples use 2021 dates and banks ICICI, SBI, Bank of Baroda. The QA tenant FY is 01-04-2026 to 31-03-2027 (`scenarios/auth.md` CO-01). Dates must be re-derived, not copied.
6. `coverage/journey-matrix.json` lists J11 as one journey (layer e2e). Bank entry (J11a) and reconciliation (J11b) are separate screens; the planner may want two specs.
7. This pack was not checked against the live app. Every KB-sourced "Expected" cell is a claim to confirm, not an observation.
