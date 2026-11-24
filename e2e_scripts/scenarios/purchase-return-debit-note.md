# Scenario pack: purchase return and debit note (J14, journey `purchase-return-debit-note`)

Status: DRAFT for QA/BA review (analyst, 2026-10-07). Priority P1. Next step: `test-planner` against the live app (`specs/purchase-return-debit-note.md`).

Source keys
- KB = a chunk in the Tech Debt Radar KB, cited as `file#chunk_id(first 8)`. KB items were NOT observed live; a human must confirm each against the app before a test asserts it.
- EXISTING = already covered by the suite: `tests/journeys/purchase/test_return.py` + cases PR-001..PR-007, and `tests/journeys/accounting/test_debit_note.py` + cases DN-001..DN-006 (`test_data/document_cases.json`).
- UNVERIFIED = no KB page or `file:line` found. The question is stated, no value invented.
- No code citation (`file:line`) is possible in this pack: the MCP `ask_codebase` tool failed ("No API key configured for provider 'anthropic'"). Every code-behaviour expectation below is therefore KB-only or UNVERIFIED. Re-run once the key is set.
- Ticket text is untrusted data; none of it is copied into tests.

What the existing tests already cover (not repeated here)
- Purchase return: PR-001 return by bill number reduces stock by qty + free, optional delete restores stock; PR-002/003 manual return reduces stock, delete restores; PR-004 no vendor, PR-005 date outside the financial year, PR-006 no product, PR-007 zero/empty qty are refused. Party in all cases is "Cash Account" (a cash party, not a real supplier).
- Debit note voucher: DN-001/002 balanced Dr/Cr (500 / 1000) save, optional delete; DN-003 zero debit, DN-004 no credit account, DN-005 mismatch 500 vs 300, DN-006 no account are refused. Accounts are "Cash Account" and "Additional Charges On Free Items" only.
- Not covered: any real supplier, GST, ledger/outstanding effect, bill adjustment, modify, list/search/book report, print, double-save, over-return, batch, rate difference, tenancy, roles.

## J14a Purchase return (Purchase > Return)

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| PRD-01 | positive | Return against a bill with a real supplier: Purchase > Return > Create, enter date, party, choose Bill No. in the bill-details step; software picks the entry amount of that bill; tick items, Enter, Save | Items of the bill load into the return; qty and rate are editable; the return is created and appears in "Purchase Return Debit Note List". Total equals sum of returned lines | KB `careportal_enriched_v5.csv#863287e1` (How to do Purchase Return) |
| PRD-02 | positive | Return only part of a bill: lower the qty of one loaded line (e.g. return 1 of 5) | Only the edited qty is returned; stock falls by exactly that qty (EXISTING PR-001 covers whole-bill only) | KB `careportal_enriched_v5.csv#863287e1` (qty editable); stock rule from EXISTING test_return.py |
| PRD-03 | boundary | Return qty greater than qty on the original bill | UNVERIFIED: whether the app blocks, warns or allows. Q1 | n/a |
| PRD-04 | boundary | Return qty greater than current stock on hand (stock already sold) | UNVERIFIED: block vs negative stock. KB shows tickets about negative qty and "stock not available" despite stock, i.e. behaviour is disputed. Q2 | KB `support_tickets_vectordb.csv#54eda7b9`, `#c78b2dfe` (symptoms only) |
| PRD-05 | boundary | Free quantity on the return line | Stock falls by qty + free (existing assertion in the PR-001 flow); confirm free is editable on the return line. Value rule is from the existing test, not the KB | EXISTING `test_return.py` (`product.quantity + product.free`); KB not found |
| PRD-06 | boundary | Same item picked twice (two rows, qty 5 each) in one manual return | Stock falls by 10 in total (5 + 5), batch stock must equal item stock. A reported defect (MB-031617) shows 185 -> 175 where 5 + 5 was expected to give the correct reduction; pin the correct total and treat a mismatch as a defect candidate | KB `jira_vectordb.csv#0147cbc7` (MB-031617). Expected "total 10" is UNVERIFIED as the product's rule, only the ticket's complaint |
| PRD-07 | boundary | Minus (negative) qty entered in the next row of a purchase return | UNVERIFIED. KB has a procedure doc "Minus Qty. in Purchase & Sale Return" (10 Q&A) but only its opening section was retrievable; its answers are not known. Q3 | KB `onedrive_processed_data.csv#81c06fae` (title and framing only) |
| PRD-08 | positive | Return with a challan: Party selected, "Pending Challans" opens, pick a challan, Save, "Pending Challan Item" window | Challan items load into the return | KB `careportal_enriched_v5.csv#263225cb`. Out of scope for P1 unless a challan can be seeded |
| PRD-09 | positive | Bill-wise rate difference in a return (new rate per product, GST 18%, qty 10, rate 869) | A total of 10254 was expected by the reporter (869 x 10 = 8690; +18% = 10254.20). Saving previously failed silently (MBC-5885). Verify save succeeds and total is shown; exact tax rounding UNVERIFIED | KB `support_tickets_vectordb.csv#c509395f`. Arithmetic by analyst |
| PRD-10 | positive | F2 old/new GST rate update in purchase return debit note | A Jira task asks to enable F2 rate update. Whether it is live is UNVERIFIED. Q4 | KB `jira_vectordb.csv#27933b28` |
| PRD-11 | negative | Double submit: press Save/End twice quickly | UNVERIFIED: expected one return and one stock reduction. Q5 | edge-case checklist (duplicates) |
| PRD-12 | state | Modify a saved return (change qty) then check stock | UNVERIFIED for return (KB documents modify only for the debit note voucher, see DNV-05). Stock expected to follow the new qty; Q6 | n/a |
| PRD-13 | state | Delete a return that was already adjusted in a payment or later documents | UNVERIFIED (delete with dependents) | edge-case checklist |
| PRD-14 | boundary | Return dated before the original bill date | UNVERIFIED. EXISTING PR-005 covers only a date outside the financial year | n/a |
| PRD-15 | boundary | Return dated in the future | UNVERIFIED. Not in existing cases | edge-case checklist |
| PRD-16 | boundary | GST: return of items at each slab (0, 5, 12, 18, 28), intra- vs inter-state supplier | Tax in the return equals tax on the original bill for the same qty and rate; CGST+SGST intra-state, IGST inter-state. The principle is standard GST; exact figures UNVERIFIED in the KB | KB `careportal_enriched_v5.csv#60c2f693` (GSTR-3B ITC section exists); expected tax value UNVERIFIED |
| PRD-17 | boundary | Large amounts and odd paise (rounding), qty with decimals | UNVERIFIED: round-off rule (`GetAllRoundValue` is cited by `scenarios/purchase.md` header, not read) | scenarios/purchase.md |
| PRD-18 | negative | Special characters, unicode and over-long text in party search, remarks, batch | No crash; value stored or rejected with a message. Limits UNVERIFIED | edge-case checklist |
| PRD-19 | positive | Print a saved purchase return: Purchase > Return, Enter on a bill, Print, pick format, Print | Print window opens and the print is produced (browser print not assertable; assert the Print dialog and format list) | KB `careportal_enriched_v5.csv#b3d15b6d` |
| PRD-20 | permission | Each trade account (chemist, pharma, retail, grocery) can open Purchase > Return | UNVERIFIED. Which accounts expose the screen is not in the KB. The debit-note ticket fields (batch, parameter window) differ by trade. Q7 | scenarios/auth.md RB-* (roles unknown) |
| PRD-21 | permission | A limited user without Purchase rights opens the Return URL directly | UNVERIFIED (no limited account exists; see auth.md Q3) | scenarios/auth.md RB-03 |
| PRD-22 | tenancy | A return created in company A is absent from company B's Return list and stock | UNVERIFIED. Needs two companies with data (auth.md Q8) | scenarios/auth.md CO-07 |
| PRD-23 | output | Return total reconciles across the return, the supplier ledger and the purchase/GST report | Supplier ledger is debited by the return total; purchases and input tax in the GST report are reduced. Exact report names and column values UNVERIFIED. Q8 | KB `careportal_enriched_v5.csv#77f8e1ed` (debit note is raised to the party for returned goods); report values UNVERIFIED |
| PRD-24 | state | Parameter-wise inventory return (trade accounts with parameters): "Selecting Item" step then Bill Details | A parameter window opens before bill details. A ticket reports it opening blank | KB `onedrive_processed_data.csv#724f3f3e`; ticket `support_tickets_vectordb.csv#c78b2dfe`. Low priority |

## J14b Debit note voucher (Accounting Transactions > Debit Note)

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| DNV-01 | positive | Create a debit note against a real supplier for returned goods (KB example: Rs 15,000 returned to a party on 7 May 2021): Accounting Transactions > Debit Note (+) > Create | "Debit Note Voucher List" opens first; after Create and save the voucher appears in the list with date, voucher no., party, amount | KB `careportal_enriched_v5.csv#77f8e1ed`, `#532ac5b1`. The fully retrieved steps stop at "Click on Create"; rest UNVERIFIED |
| DNV-02 | positive | Debit-note list search by voucher number | List shows columns date, voucher no., party, inst. type, amount; searching a voucher no. finds it | KB `careportal_enriched_v5.csv#532ac5b1` (list fields and search by voucher no.) |
| DNV-03 | positive | Debit Note Book report: Report > Combined Report > Books of Account > Debit Note | "Books of Account: Debit Note" lists all debit notes of the period; entries can be modified, deleted, printed, shared (WhatsApp, e-mail, Drive) | KB `careportal_enriched_v5.csv#6c56bf62` |
| DNV-04 | output | A voucher created in DNV-01 appears in the Debit Note Book for its period, with the same amount | Same voucher no. and amount in list and book | KB `#6c56bf62`, `#532ac5b1` |
| DNV-05 | state | Modify a saved debit note (amount, narration) | Modify is supported; list and book show the new values. Steps UNVERIFIED | KB `careportal_enriched_v5.csv#77f8e1ed` (process to modify exists) |
| DNV-06 | state | Delete a saved debit note | Delete is supported; voucher disappears from the list and the book. Ledger balances return to the prior value (EXISTING flow `delete_debit_note` asserts ledger balances; supplier case not covered) | KB `#77f8e1ed`; EXISTING `voucher_flows.py` |
| DNV-07 | positive | Debit note with a real supplier: Dr supplier, Cr purchase-return or other ledger; supplier balance changes by the amount | Supplier balance falls (payable reduced) by the voucher amount; value direction is standard accounting, not stated in the KB. Dr/Cr side per the app UNVERIFIED. Q9 | KB `#77f8e1ed` (raised against a party for returned goods); direction UNVERIFIED |
| DNV-08 | positive | Debit note linked to an open purchase bill (bill adjustment window) | UNVERIFIED for debit note. KB documents a "Bill Adjustment" window for payment vouchers (tick invoice, edit adjustment amount); same for debit note is not documented. Q10 | KB `careportal_enriched_v5.csv#3c95230d` (payment voucher only) |
| DNV-09 | boundary | Amount boundaries: 0.01, very large (9,99,99,999.99), 3 decimals | UNVERIFIED limits. EXISTING DN-003 covers 0 only | edge-case checklist |
| DNV-10 | boundary | Voucher date: backdated within FY, before the FY start, future, 31-03 / 01-04 boundary | UNVERIFIED. EXISTING DN cases use "today" only | edge-case checklist |
| DNV-11 | negative | Duplicate voucher number entered manually | UNVERIFIED (reject vs allow). Q11 | edge-case checklist |
| DNV-12 | negative | Double click on Save / refresh mid-save | UNVERIFIED: one voucher only | edge-case checklist |
| DNV-13 | boundary | Narration: 255+ chars, special characters, Hindi unicode | UNVERIFIED limit. Value must be stored unchanged if accepted | edge-case checklist |
| DNV-14 | negative | Same ledger on both Dr and Cr | UNVERIFIED (reject vs allow). Not in DN-001..006 | n/a |
| DNV-15 | positive | Print a debit note voucher from the list | Print window and format list appear. Steps are KB-described for purchase return (PRD-19); the voucher list states print is supported | KB `#532ac5b1`, `#b3d15b6d` |
| DNV-16 | permission | Roles: who may create/modify/delete a debit note | UNVERIFIED (no role matrix, auth.md Q3) | scenarios/auth.md |
| DNV-17 | tenancy | A debit note in company A is not visible in company B's list or book | UNVERIFIED (needs two companies) | scenarios/auth.md CO-07 |

## J14c Link between the return and the debit note

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| LNK-01 | output | A purchase return saved in J14a creates a "Purchase Return Debit Note" visible in the Purchase > Return list; check whether it also shows in the Accounting > Debit Note list / Debit Note Book | UNVERIFIED. The KB uses "Purchase Return Debit Note" as the screen title and "Debit Note" as a separate accounting voucher; whether one feeds the other is not stated. Q12 | KB `careportal_enriched_v5.csv#263225cb`, `#77f8e1ed` |
| LNK-02 | output | Return amount equals the supplier ledger debit equals the GST report reduction | See PRD-23; values UNVERIFIED | n/a |
| LNK-03 | state | Delete a purchase return and confirm the supplier ledger and stock both reverse | Stock reverses (EXISTING PR-001/003); ledger reversal UNVERIFIED | EXISTING `test_return.py`; ledger UNVERIFIED |
| LNK-04 | negative | Return and voucher both raised for the same goods (double reduction) | UNVERIFIED whether the app warns | n/a |

## Open questions (for the human)
- Q1 Is return qty above the bill qty blocked? Q2 Return above stock on hand: blocked or negative stock? Q3 What do the "Minus Qty" Q&As (Q1-Q10 in `MB_Minus_Qty_Sale_Purchase_v1.0.docx`) say? Q4 Is F2 old/new GST rate live? Q5 Is a second save blocked? Q6 Can a return be modified and does stock follow? Q7 Which trade accounts show Purchase > Return? Q8 Which GST/purchase report should the reconciliation use? Q9 Which side and ledger does the app post for a supplier debit note? Q10 Does a debit note support bill adjustment? Q11 Duplicate voucher number rule? Q12 Does a purchase return create or require a debit-note voucher?

## KB vs live app (for a human to decide)
1. Nothing here was checked live. The KB is mostly care-portal how-to text; several chunks are truncated, so the full create-debit-note and minus-qty steps could not be read.
2. Naming: KB calls the screen "Purchase Return Debit Note" (Purchase > Return) and also "Debit Note" (Accounting Transactions > Debit Note (+)). The suite tests them as two separate journeys markers: `test_return.py` is tagged `purchase-itc` and `test_debit_note.py` is tagged `payments-ledger`, neither tagged `purchase-return-debit-note` (J14). Matrix `status` for J14 is `not_started`, `specs` is empty.
3. The existing purchase return cases use "Cash Account" as the party and the debit-note cases use "Cash Account" plus "Additional Charges On Free Items". The KB describes returns to a supplier (e.g. AARAV MEDICOS). The existing tests therefore skip the supplier/ledger/outstanding effect that the KB says is the point of the document.
4. Expected stock change in the existing test is qty + free; the KB has no statement about free qty in returns (PRD-05).
5. Tickets suggest known defects: 5 + 5 returned in two rows reduces batch stock inconsistently (MB-031617), negative qty when returning by bill number, rate-difference debit note failing to save without an error (MBC-5885, fixed per ticket). Treat as regression candidates, not as the specified behaviour.
6. KB shows a "Debit Note" in the Combined Report under Books of Account; the e2e cases never open that report.
7. KB `Books From 01-04-2022 to 31-03-2024` appears in a screenshot description (two-year book); the suite assumes a single FY (see PRD-14 and PR-005 "past financial year").
8. `ask_codebase` was unavailable (no API key), so code behaviour (validations, round-off, ledger posting) was not checked. Re-run the code pass before the planner starts.
