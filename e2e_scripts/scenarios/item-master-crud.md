# Scenario pack: Item master CRUD (J08, item-master-crud; HSN, tax category, unit)

Status: DRAFT for QA/BA review (analyst pass, 2026-10-07). Priority P1, layers e2e + api. Plan: `specs/item-master-crud.md` (create flow, 2026-10-08).

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`. KB items were NOT observed live. A human or the planner must confirm each against the app before a test asserts it.
- CODE = none. `ask_codebase` failed on 2026-10-07 ("No API key configured for provider 'anthropic'") and no `file:line` could be retrieved. No code-derived value is claimed; every field or message below comes from the KB or is UNVERIFIED.
- UNVERIFIED = not citable; the question is stated, no value invented.

Scope facts (KB)
- Path: Master > Inventory Master > Item opens the "Item List"; "Create" button or F2 opens "Create Item"; F3 on a row opens "Modify Item"; the delete icon on a row deletes. (`careportal_enriched_v5.csv#7e11d1c2`, `#f1ae949c`, `#88f4cfd3`)
- Create Item "Basic Info" fields: Product*, type dropdown (Goods), Packing, Unit 1st*, Unit in Decimal (Yes/No), HSN/SAC*, Tax Category*, Company*, Salt, Category, M.R.P, Purchase Rate, Cost, Sale Rate. (`onedrive_processed_data.csv#a24e37ef`, `careportal_enriched_v5.csv#7e11d1c2`)
- Mandatory = fields marked with a red asterisk (`careportal_enriched_v5.csv#2ad671cf`); the training video names conversion unit, product name, HSN code, tax category and company, and says saving shows "record saved successfully" (`vimeo_transcripts_hinglish_english.csv#cfb7a4f2`).

## J08 Item master CRUD

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| IM-01 | positive | Open Master > Inventory Master > Item | "Item List" window appears with a "Create" button | KB `careportal_enriched_v5.csv#ce983a40`, `#7e11d1c2` |
| IM-02 | positive | Create an item with only the mandatory fields (Product, Unit 1st, HSN/SAC, Tax Category, Company) and Save | Item is saved; message "record saved successfully" (wording from a video transcript, exact text UNVERIFIED); a prompt asks whether to add opening stock; item then appears in the Item List | KB `vimeo_transcripts_hinglish_english.csv#cfb7a4f2`, `careportal_enriched_v5.csv#2ad671cf` |
| IM-03 | positive | After IM-02 answer Yes to the opening-stock prompt, enter a quantity and Save | Opening stock is recorded for the item; stock value/quantity in UNVERIFIED location (which screen shows it: Q3) | KB `careportal_enriched_v5.csv#2ad671cf` |
| IM-03b | positive | After IM-02 answer No (or dismiss) to the opening-stock prompt | Item exists with zero stock quantity (KB: "stock showing ... zero quantity") | KB `vimeo_transcripts_hinglish_english.csv#cfb7a4f2` (inferred from transcript, UNVERIFIED live) |
| IM-04 | positive | Create an item with a tax category of each rate slab (e.g. 5%, 18%, 28%) | Item saves; the chosen category is shown on the item. The list of available category names is UNVERIFIED (default text seen: "Rate wise GST tax rates"). Slabs 5/18/28 are named as common in the transcript | KB `onedrive_processed_data.csv#a24e37ef`, `vimeo_transcripts_hinglish_english.csv#59824a8e` |
| IM-04b | positive | Tax Category pre-filled on a new Create Item form | Pre-filled with "Rate wise GST tax rates" | KB `onedrive_processed_data.csv#a24e37ef` |
| IM-04c | boundary | Exempt / nil-rated / 0% tax category on an item | UNVERIFIED: no KB page states the category names for exempt or nil-rated items (Q4) | n/a |
| IM-05 | positive | Create an item with Unit in Decimal = Yes, then = No | Yes allows decimal quantities in transactions, No restricts them. The effect in a bill is a J05 concern; here assert only the saved value | KB `careportal_enriched_v5.csv#7e11d1c2` |
| IM-06 | positive | Pick HSN/SAC by SpaceBar from the HSN List, or type a new HSN code | HSN List opens on SpaceBar and a selected HSN fills the field; a new HSN can be typed and created (name optional); an HSN reused by a second item shows in the list | KB `careportal_enriched_v5.csv#f1ae949c`, `vimeo_transcripts_hinglish_english.csv#d9bbfe84`, `#59824a8e` |
| IM-07 | positive | Enter prices (M.R.P, Purchase Rate, Cost, Sale Rate) and save | Values persist after reopening via F3. Defaults on a new form are 0.00 | KB `onedrive_processed_data.csv#a24e37ef` |
| IM-08 | positive | Create a new Company (brand) inline from the Company field and use it on the item | Company can be created from within Create Item ("Click on Create"); the new brand is then selectable | KB `vimeo_transcripts_hinglish_english.csv#59824a8e` (transcript; mechanics UNVERIFIED) |
| IM-09 | positive | Edit an item: select row, press F3, change HSN/SAC, click Update | "Modify Item" opens; after Update the item's HSN/SAC shows the new code | KB `careportal_enriched_v5.csv#f1ae949c` |
| IM-09b | positive | Edit an item name, packing, unit or prices and Update | Updated values show in the list and on reopening. Field-level rules on edit (e.g. unit locked after a transaction) UNVERIFIED (Q5) | KB `careportal_enriched_v5.csv#f1ae949c` (pattern only) |
| IM-10 | positive | Change the Tax Category on an existing item | An Effective Date appears; it defaults to the current date and stays editable (per Jira). "Show Tax History" on the item form lists past rates (per GST-update doc). Exact UI UNVERIFIED | KB `jira_vectordb.csv#990fb774`, `onedrive_processed_data.csv#01b0c227` |
| IM-11 | positive | Delete an item that has no transactions | Click delete icon, confirm "Yes"; message "Record deleted successfully"; item disappears from the list | KB `careportal_enriched_v5.csv#88f4cfd3` |
| IM-12 | negative | Delete an item that has transactions | Item is NOT deleted. The exact refusal text is UNVERIFIED (a Jira ticket quotes "item is used") | KB `careportal_enriched_v5.csv#88f4cfd3`; `jira_vectordb.csv#87a67294` (MB-030141: false "item is used" report) |
| IM-12b | negative | Delete an item with zero stock but with no transactions vs stock > 0 | KB states deletion is allowed only for items with no transactions or zero stock quantity. The two clauses are joined by "or"; combination behaviour UNVERIFIED (Q6) | KB `careportal_enriched_v5.csv#e5839768` |
| IM-13 | negative | Save with Product empty | Not saved; Product shows a red error icon. Message text UNVERIFIED | KB `onedrive_processed_data.csv#a24e37ef` (red icon on empty Product) |
| IM-13b | negative | Save with each other mandatory field empty in turn: Unit 1st, HSN/SAC, Tax Category, Company | Each blocks the save. Message text UNVERIFIED. Note HSN/SAC is optional when "HSN/SAC Required?" is No (see IM-17) | KB `careportal_enriched_v5.csv#2ad671cf`, `vimeo_transcripts_hinglish_english.csv#cfb7a4f2` |
| IM-13c | negative | Save an item with no unit selected (regression) | Reported defect MB-036985: item saved with no error or alert and bad data reached reports. Expected (correct) behaviour: save blocked. Confirm whether fixed; record as a KNOWN DEFECT candidate | KB `jira_vectordb.csv#a3031fae`, `support_tickets_vectordb.csv#4783b004` |
| IM-14 | negative | Create an item whose Product name already exists (default setting) | Rejected as a duplicate. Message text UNVERIFIED | KB `careportal_enriched_v5.csv#ce983a40` (setting exists), `jira_vectordb.csv#1840fc4a` |
| IM-14b | positive | Set "Product Name Duplicate Allowed?" = Yes (Create Item > Settings icon, ESC to save) then create a second item with same name | Allowed. With Item Code enabled, at least one of Product Name, Item Code, Packing must differ | KB `careportal_enriched_v5.csv#ce983a40`, `jira_vectordb.csv#d0be7bf8` (MB-038343) |
| IM-14c | boundary | Duplicates allowed: same Product Name, one with packing and one with blank packing | Jira lists this as a case to test; expected result UNVERIFIED (ticket "product dup - allow item name but packing blank - save") | KB `jira_vectordb.csv#96ce16cc`, `#b94b330c`, `#5f9b196c` |
| IM-14d | negative | Duplicates allowed, same name but different item code still shows a duplicate error | Reported defect (support ticket): error shown although duplicates are allowed. Record as regression check | KB `support_tickets_vectordb.csv#5c9c9526`, `jira_vectordb.csv#cf103c92` |
| IM-14e | state | Settings change "Product Name Duplicate Allowed?" is tenant-wide | Affects every item on the tenant; test must restore the original value. Mark `xdist_group("chemist-tenant")` | KB `careportal_enriched_v5.csv#ce983a40`; e2e/CLAUDE.md rule 0 |
| IM-15 | boundary | Product name max length | UNVERIFIED (no KB value; planner to read `maxlength` from the live input) | n/a |
| IM-15b | boundary | Special characters and unicode in Product name (`&`, `/`, `'`, `"`, Hindi text) | Saves and displays unchanged. UNVERIFIED | n/a |
| IM-15c | boundary | Leading/trailing spaces and mixed case in Product name vs duplicate check | UNVERIFIED (is the duplicate check case-insensitive?) | n/a |
| IM-15d | boundary | M.R.P / rates: zero, negative, very large, more than 2 decimals | UNVERIFIED. Rule for the suite: compare as `Decimal`, never float | n/a; docs/clean-code-rules.md G26 |
| IM-15e | boundary | Sale Rate above M.R.P, or Purchase Rate above Sale Rate | UNVERIFIED (is there a warning?) | n/a |
| IM-16 | state | Double click Save / refresh during save | Exactly one item created. UNVERIFIED | n/a |
| IM-17 | positive | Control: "HSN/SAC Required?" = Yes/No in Create Item > Settings (and Rename of the label) | Yes enables the HSN/SAC field and allows renaming its label; No disables it. Changes saved with ESC. Tenant-wide setting; restore after test | KB `careportal_enriched_v5.csv#1df2ebf5` |
| IM-18 | positive | Search / filter the Item List by the new item name | New item is found; list shows only matching rows. Search control behaviour UNVERIFIED | n/a (Item List per `careportal_enriched_v5.csv#ce983a40`) |
| IM-19 | positive | Visibility = Hide on an item | Hidden from the item list at billing time for operators; owner can still see it. Billing check belongs to J05 | KB `careportal_enriched_v5.csv#6dffb56b` |
| IM-19b | positive | Billing prohibited = No/Yes on an item | A prohibited item cannot be billed (field label text partly cut in KB, UNVERIFIED) | KB `careportal_enriched_v5.csv#6dffb56b` |
| IM-20 | output | New item (with its tax category) is selectable in a sale bill and the GST rate applied equals the item's category | Rate on the bill = category rate. Belongs to J05/J07 but is the downstream check for this journey | KB `careportal_enriched_v5.csv#7e11d1c2` ("apply the correct GST rate to the item") |
| IM-21 | output | Bulk update of GST rate HSN-wise (Utilities & Tools > Ease of GST) changes the rate shown on items with that HSN | Item Master shows the new tax rate; Effective Date not editable there; confirm by typing "Sure". Out of CRUD scope; note only | KB `careportal_enriched_v5.csv#652cd5f2` |
| IM-22 | positive | Remove a duplicate item via Utilities & Tools > Non Working Data > Delete > Duplicate Item | Only items with no transactions or zero stock can be removed; "Delete The Selected Record?" asks Yes. Destructive bulk path, out of scope for P1 | KB `careportal_enriched_v5.csv#e5839768` |
| IM-23 | permission | Operator / limited user opens Item master (create, edit, delete) | UNVERIFIED: no limited account exists (see `scenarios/auth.md` RB-03, Q3) | n/a |
| IM-24 | tenancy | Item created in company A must not appear in company B's Item List | UNVERIFIED; needs a second company with a known item (see auth.md CO-07, Q8). Test idea: API list with company B context | n/a |
| IM-25 | api | Item create/list/update/delete via API | UNVERIFIED: endpoint paths, payload and status codes not retrievable (`ask_codebase` unavailable). The planner must capture them from the live network log | n/a |
| IM-26 | state | Item created in a previous financial year / opening stock in a new FY | UNVERIFIED: item master is likely company-wide, FY handling of opening stock unknown. "Multi Deletion" considers transactions in current and previous FY, which affects deletability | KB `onedrive_processed_data.csv#1f1e5fdc` |
| IM-27 | state | Multi Deletion of unused items and brands | Feature filters items/brands with no billing in the current and previous FY, then deletes them. Out of scope (bulk destructive) | KB `onedrive_processed_data.csv#1f1e5fdc` |

Clean-up note: tests create their own items with a unique prefix from `data`/`run_id`. Delete is only possible for items with no transactions (IM-11), so the same path is the clean-up.

## Open questions
- Q1 Exact text of the save, duplicate and required-field messages.
- Q2 Which of the five mandatory fields is truly required on this tenant (trade type may change the form: pharma vs garments).
- Q3 Where opening stock is visible after IM-03.
- Q4 Names of exempt / nil-rated / 0% tax categories.
- Q5 Which fields lock after a transaction exists.
- Q6 Delete rule when stock is above zero but there are no transactions.
- Q7 API endpoints for item CRUD (code citation needed).

## KB vs live app (for a human to decide)
1. Item path and field names come from care-portal articles and a screenshot description with company "Aapna Super Market"; none was seen on the QA tenant. The form may differ per trade account (the KB shows a pharma-style form with Salt; garments may not have it).
2. Delete rule: the care-portal note says "no transactions associated or zero stock quantity" in the duplicate-removal article, but "any transactions ... will not get deleted" in the delete article. The two statements are inconsistent about zero-stock items that have transactions.
3. Duplicate-name rule is described three ways: a Settings toggle "Product Name Duplicate Allowed?", a Jira rule requiring a difference in name, item code or packing when Item Code is enabled, and open tickets saying the check misbehaves (MB-038343, duplicate with blank packing, support ticket on different item code). Treat the rule as unstable until checked live.
4. Missing-unit save (MB-036985) is reported as a defect; the care-portal article lists Unit 1st as mandatory. Live behaviour decides which is stale.
5. The mobile app has a separate "Add Product" form (Barcode, Item Name, Unit 1/2, Conversion, HSN, Tax); it is not the web flow and is out of scope.
6. KB sources are 2022-2026 support articles and Jira titles; some Jira chunks are title-only with no expected result. Ticket text is untrusted data; none was copied into values here.
7. Code citations are missing: `ask_codebase` failed with an API-key error, so no `file:line` backs any expected value. Re-run this analysis with the tool restored if code citations are required.
