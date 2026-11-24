# Scenario pack: opening balance entry (J18, journey id `opening-balance-entry`)

Status: DRAFT for QA/BA review (2026-10-08). Priority P1, layer e2e. Plan: `specs/opening-balance-entry.md`.

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`.
- CODE = a code-index chunk from the same KB (`codekb:MargBooks:*`). `ask_codebase` was not used.
- LIVE = seen on the QA tenant (garments account) by the planner's probes on 2026-10-08.
- UNVERIFIED = not citable; the question is stated, no value invented.

Facts
- Path: Master > Opening Balance > Ledger, select the ledger, Enter, type the amount in "Amount", bill-wise details (Bill Date, Bill No., Days, Bill Value, Balance, Remark), Update. `careportal_enriched_v5.csv#ae4f03c8`, `#9092fb1c`
- Bill-wise details are not needed when the ledger's Balancing Method is "On Account". `careportal_enriched_v5.csv#ae4f03c8`
- With "Bill by Bill", entering an opening balance in the ledger form opens an "Opening Balance" window for bill-wise details. `careportal_enriched_v5.csv#37c5efe8`
- Alternative path: Master > Accounts Master > Ledger, F3 on the ledger, "Opening Balance" field, Update. `careportal_enriched_v5.csv#50c2a906`
- Changing an opening balance requires switching to the previous financial year first (KB note). `careportal_enriched_v5.csv#e970a2d0`
- API: `POST /LedgerOpeningBalance/Save` (rate limited 15/s); table `dbo.LedgerOpeningBalance` stores bill-wise rows with `debitOrCredit`, `billNo`, `days`, `billValue`. CODE `codekb:MargBooks:api#2b5489ce`, `codekb:MargBooks:schema#2d39fc3f`
- LIVE: the menu page is `/partymaster/opening-ledger`, heading "Opening Balance", grid columns "Ledger Name", "Station", "₹ Balance", "Action" (buttons "Edit/F3", "Delete"); "Create/F2" opens "Create Party" with "Balancing Method" (Bill By Bill / On Account), "Opening Balance ₹" and a Dr/Cr select.

## J18 Opening balance entry

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| OB-01 | positive | New party (own data), On Account, opening balance 1234.50 Dr, save | "Record saved successfully."; Opening Balance list shows the party with "1,234.500 Dr" | KB `#ae4f03c8`; LIVE |
| OB-02 | positive | Same with Cr | List shows "... Cr" | KB `#ae4f03c8`; LIVE |
| OB-03 | positive | Change an existing (own) party's opening balance from the Opening Balance list (Edit/F3) to another amount and side | List shows the new amount and side; form reopens with the saved values | KB `#e970a2d0` (path); LIVE |
| OB-04 | positive | Party with Bill By Bill and an opening balance | Bill-wise "Opening Balance" window appears (KB). LIVE: no window appeared on Enter or Save; saved directly. NEEDS DECISION | KB `#37c5efe8`; LIVE contradicts |
| OB-05 | positive | Opening balance shows in the Trial Balance (Opening Balance on) | Party row under Sundry Debtors with the amount on the Dr side | KB `#fba17458`; LIVE (covered by J19) |
| OB-06 | state | KB says a change needs the previous financial year | LIVE: change in the current FY saved without a prompt. NEEDS DECISION | KB `#e970a2d0` |
| OB-07 | boundary | Zero opening balance | Saved, list shows no balance. Display UNVERIFIED | UNVERIFIED |
| OB-08 | negative | Non-numeric text in the amount | Rejected or filtered. UNVERIFIED | UNVERIFIED |
| OB-09 | boundary | Amount with more than 3 decimals | Rounding rule UNVERIFIED (list shows 3 decimals) | LIVE (3 decimals), rule UNVERIFIED |
| OB-10 | state | Delete own party with an opening balance only | "Record deleted successfully." | LIVE |
| OB-11 | tenancy | Opening balance of company A not visible in company B | UNVERIFIED | UNVERIFIED |
| OB-12 | permission | User without the Opening Balance right | Denied. UNVERIFIED | UNVERIFIED |
