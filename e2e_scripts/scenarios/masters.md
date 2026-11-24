# Scenario pack: customer / vendor master CRUD (J07, journey id `masters`)

Status: DRAFT for QA/BA review (2026-10-07). Journey J07 "Customer/vendor master CRUD", priority P1, layers e2e + api. Next step: `test-planner` captures the live app into `specs/masters.md`.

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`. KB items were NOT observed live; a human must confirm each against the app before a test asserts it.
- CODE = Tech Debt Radar code index (`get_module_info`). Module level only: `margbookscoreapi/MargBooks.LedgerAPI` (`MargBooks.Ledger/Controllers/LedgerController.cs`, `Services/LedgeListService.cs`), `MargBooks.MastersAPI`, `MargBooks.ItemAPI`. `ask_codebase` failed (no API key configured on the server), so no `file:line` citations or validation rules could be read from code.
- UNVERIFIED = not citable; the question is stated, no value invented.

Scope note: "customer/vendor master" is the Ledger Master (Master > Accounts Master > Ledger; account group Sundry Debtors = customer, Sundry Creditors = supplier). A separate "Customer" master (Master > Other Master > Customer, loyalty-style record with mobile/ID/name) also exists and is covered at the end. Item Master is included only where it is the other half of a bill's master data; its full CRUD belongs in a later journey.

## Ledger master (customer / vendor)

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| MS-01 | positive | Open Master > Accounts Master > Ledger | A "Ledger Master" window lists all ledgers; a Create button (or F2) is available | KB `careportal_enriched_v5.csv#5fe16050`, `#f6bd22bb` |
| MS-02 | positive | Create a customer ledger with only mandatory fields (name, account group Sundry Debtors, station if enabled) and Save | Ledger is created; it appears in the ledger list and in the sale bill party picker. Mandatory fields are marked with a red asterisk (*); exact set UNVERIFIED | KB `careportal_enriched_v5.csv#5fe16050`, `#085d1e1b` |
| MS-03 | positive | Create a supplier ledger with account group Sundry Creditors | Ledger saved under Sundry Creditors and selectable in a purchase bill | KB `vimeo_transcripts_hinglish_english.csv#45d0f78f`, `careportal_enriched_v5.csv#085d1e1b` |
| MS-04 | positive | Create a ledger with full details: address, country, state, city, pincode, GSTIN, opening balance with Dr/Cr, credit days, mobile, WhatsApp | All values persist and show again on Modify. Opening balance side for a customer is Debit, for a supplier Credit | KB `careportal_enriched_v5.csv#82cf84c4`, `#9eac622d` |
| MS-05 | positive | Create a ledger from the sale bill: Sale > Bill > Party Name > Select Party > Create | "Create Ledger" window opens; after save the new ledger is selected on the bill | KB `careportal_enriched_v5.csv#f680f130` |
| MS-06 | positive | Modify a ledger: Edit icon, change a field, Update | Message "Record Updated Successfully"; the list and the next reopen show the new value | KB `careportal_enriched_v5.csv#f6bd22bb` |
| MS-07 | positive | Search the ledger list for a just-created ledger name | Ledger found. Search behaviour (prefix or contains, case) UNVERIFIED | KB `vimeo_transcripts_hinglish_english.csv#f2666820` (search then Enter shows the ledger); rule UNVERIFIED |
| MS-08 | positive | GST verification while creating a ledger: enter GSTIN, use the verify action | Party details (name, address, state) are fetched from the GST number. Needs the GST portal; likely not automatable on QA | KB `careportal_enriched_v5.csv#4162a53d` |
| MS-09 | negative | Save a ledger with the required name empty | Save refused, nothing created. Error wording UNVERIFIED | KB `careportal_enriched_v5.csv#5fe16050` (mandatory *); wording UNVERIFIED |
| MS-10 | negative | Save a ledger without an account group | Save refused. Wording UNVERIFIED | KB `careportal_enriched_v5.csv#5fe16050` (group is part of the mandatory path); wording UNVERIFIED |
| MS-11 | negative | Station enabled: save a customer or supplier ledger without a station | Save refused; Station is a required field while the Station option is on, and can be turned off in settings | KB `careportal_enriched_v5.csv#44127743` |
| MS-12 | negative | Save a ledger with an invalid GSTIN (14 chars, bad structure, wrong check character) | UNVERIFIED. Field id/label and error text not yet seen live (see `specs/sale-invoice-gst.md` line 49). Do not click Save during exploration | UNVERIFIED |
| MS-13 | negative | GSTIN state code differs from the selected State | UNVERIFIED (no KB or code evidence) | UNVERIFIED |
| MS-14 | negative | Create a second ledger with the same name as an existing one | UNVERIFIED: duplicate allowed or blocked unknown. A Jira item mentions removing spaces in the ledger master table for a second customer, hinting at trimming/duplicate handling | KB `jira_vectordb.csv#b024d6a9` (hint only) |
| MS-15 | negative | Delete a ledger that has transactions | Deletion refused: a ledger with transactions cannot be deleted; the transactions must be deleted first | KB `careportal_enriched_v5.csv#f6bd22bb` |
| MS-16 | positive | Delete a ledger that has no transactions | Ledger removed from the list. Confirmation dialog text UNVERIFIED | KB `careportal_enriched_v5.csv#f6bd22bb` (process exists; steps truncated in the chunk) |
| MS-17 | negative | Delete a ledger that has a journal voucher in an older financial year | KB reports the app deleted it anyway while the entry stayed, leaving blank ledger names in the old entry. Treat as a possible defect: expected is the MS-15 refusal | KB `support_tickets_vectordb.csv#33c01bed`; Jira "Ledger not able to delete" `jira_vectordb.csv#fb844b2f` |
| MS-18 | boundary | Ledger name: very long, special characters (`& ' / -`), unicode, leading/trailing spaces | UNVERIFIED: max length and allowed set unknown. Questions Q3, Q4 | UNVERIFIED |
| MS-19 | boundary | Mobile / pincode / credit days / opening balance: zero, negative, non-numeric, very large, odd paise | UNVERIFIED limits. Opening balance must keep its Dr/Cr side (see MS-04) | UNVERIFIED |
| MS-20 | boundary | Double submit: press Save twice quickly, or refresh mid-save | UNVERIFIED: expect one ledger only. Check the list count afterwards | UNVERIFIED (checklist: duplicates) |
| MS-21 | state | Edit a ledger that is already used on a posted bill (change name/group/GSTIN) | UNVERIFIED: whether the existing bill changes. Group change on a ledger with transactions is a risk | UNVERIFIED (checklist: edit after posting) |
| MS-22 | state | Opening balance on the ledger shows in the ledger report / trial balance | Opening balance is reflected in the ledger balance. Report path and figure format UNVERIFIED | KB `careportal_enriched_v5.csv#82cf84c4` (field exists); reconciliation UNVERIFIED |
| MS-23 | permission | Limited user without Master rights opens Master > Ledger by menu and by URL | UNVERIFIED: no limited account exists (auth.md RB-03/RB-04, Q3). Guard only filters by menu items and plan | `scenarios/auth.md` RB-03; UNVERIFIED |
| MS-24 | permission | Each trade account (chemist, pharma, retail, grocery) can create a ledger | UNVERIFIED: labels and mandatory fields (e.g. Station, GSTIN, drug licence) may differ by trade | UNVERIFIED |
| MS-25 | tenancy | A ledger created in company A does not appear in company B's ledger list or party picker | UNVERIFIED live; test idea: create in A, switch company, search by unique name. The API module serving this is `MargBooks.LedgerAPI` | CODE module `MargBooks.LedgerAPI`; rule UNVERIFIED (see auth.md CO-07, Q8) |
| MS-26 | tenancy | Same ledger name in two companies | Allowed, no clash. UNVERIFIED | UNVERIFIED |
| MS-27 | api | Create / read / update / delete a ledger through the ledger API with a company A token | CRUD works for the owner; a company B id returns denial. Endpoint paths, payload and status codes UNVERIFIED (not read from code) | CODE module `MargBooks.LedgerAPI`, `LedgerController.cs`; contract UNVERIFIED |
| MS-28 | output | Ledger created via UI is returned by the API, and an API-created ledger shows in the UI list | Both views agree on name, group, GSTIN, opening balance | UNVERIFIED (reconciliation idea from checklist) |

## Item master (supporting master data)

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| IM-01 | positive | Create an item: Master > Inventory Master > Item > Create/F2; Product name, Packing, Unit 1st, Unit in Decimal, HSN/SAC, Tax Category | Item saved and appears in the Item List (Description, Packing, Company, Stock, Unit, Sale Rate). Mandatory fields have an asterisk; exact set UNVERIFIED | KB `careportal_enriched_v5.csv#7e11d1c2`, `#89501edb` |
| IM-02 | negative | Save an item without HSN/SAC when "HSN / SAC Required?" is Yes in the Control Room | HSN is mandatory in Item Master when the setting is on; save refused. Wording UNVERIFIED | KB `careportal_enriched_v5.csv#6576a008` |
| IM-03 | positive | Create an HSN/SAC code: Master > Inventory Master > HSN / SAC > Create, code + name, Save | HSN is created and selectable on an item | KB `careportal_enriched_v5.csv#320937c5` |
| IM-04 | boundary | Unit in Decimal = No, then a decimal quantity on a bill | Decimal quantity refused. Exact message UNVERIFIED | KB `careportal_enriched_v5.csv#7e11d1c2` (option restricts decimals); behaviour UNVERIFIED |
| IM-05 | negative | Item with the same name as an existing item | UNVERIFIED | UNVERIFIED |
| IM-06 | tenancy | Item created in company A absent from company B | UNVERIFIED. Module `MargBooks.ItemAPI` | CODE module `MargBooks.ItemAPI`; rule UNVERIFIED |

## Customer master (Master > Other Master > Customer)

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| CU-01 | positive | Enable the customer module, then create a customer: mobile, ID, name, gender, age, ledger, address, pin, e-mail, WhatsApp | Customer saved and listed. Customer ID is auto-generated by the software. The customer module must be enabled first (setting path UNVERIFIED) | KB `careportal_enriched_v5.csv#b58668e6`, `#8659e05b` |
| CU-02 | positive | Create a customer from the sale bill without leaving the billing screen | Customer created inline and attached to the bill | KB `careportal_enriched_v5.csv#b58668e6` |
| CU-03 | negative | Create a second customer with an existing mobile number | UNVERIFIED. A Jira task asks to delete duplicate customers uniquely identified by mobile number, so duplicates have occurred | KB `jira_vectordb.csv#0529399b` |
| CU-04 | boundary | Mobile number: 9, 10, 11 digits, letters | UNVERIFIED | UNVERIFIED |
| CU-05 | positive | Customer linked to Cash Account for cash billing, or to a named ledger for credit billing | The ledger choice drives where the bill posts | KB `careportal_enriched_v5.csv#8659e05b` |

## Open questions for a human
- Q1 Mandatory field set of Create Ledger per trade account, with exact error texts.
- Q2 Duplicate ledger name and duplicate item name: allowed or blocked.
- Q3 Maximum lengths and allowed characters for ledger name, address, GSTIN, mobile, pincode.
- Q4 GSTIN validation rules (format, check character, state code match) and the field locators.
- Q5 Can tests create and delete ledgers freely on the QA tenant, and who owns clean-up (data convention: unique run-id name prefix)?
- Q6 Is a limited user available for the permission scenarios (shared with auth.md Q3)?
- Q7 Ledger delete rule across financial years (MS-17).
- Q8 Is there a second company with a known state for tenancy tests (shared with auth.md Q8)?

## KB vs live app (for a human to decide)
1. Nothing in this pack was observed live. The live app was not opened for this pack; every KB step must be confirmed by the planner. Menu names ("Accounts Master", "Inventory Master", "Other Master") come from KB articles that describe the Billing / Retail Pharmacy setups and may differ from the current menu (auth.md RB-01 lists the live top menu: Master, Sale, Purchase, Accounting Trans., ...).
2. KB says deleting a ledger with transactions is blocked (`#f6bd22bb`); a 2026 support ticket reports a delete succeeding with a journal voucher in an older financial year (`#33c01bed`). Inconsistent or a defect; a human decides before the test asserts either.
3. The KB ledger-create article says only mandatory fields marked * are needed; the vimeo training transcript says mobile (starred) and station are needed for a party, and e-mail is optional (`vimeo_transcripts_hinglish_english.csv#0670cbb5`). The two describe possibly different trade setups. The mandatory set is not settled.
4. KB says a customer module "must be enabled" first (`#8659e05b`); where, and whether it is on in the QA tenant, is unknown.
5. KB support-ticket text is untrusted data (names and credentials are masked as `[EMAIL]`/`[CREDENTIAL]`). Copy none of it into tests.
6. The code index returns only file-level metrics for `LedgerAPI` and no validation rules; `ask_codebase` was unavailable. Code-level confirmation of validation, duplicate checks and delete rules is still outstanding.
7. Journey matrix `status` for `masters` stays `not_started`; the analyst does not change it.
