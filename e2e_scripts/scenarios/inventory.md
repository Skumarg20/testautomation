# Scenario pack: inventory stock movement (J13)

Status: DRAFT for QA/BA review (2026-10-07). Journey: J13 `inventory` (P1, layers e2e + api, target day 11). Plan: none yet (`specs/inventory.md` is for the planner).

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`. KB items were NOT observed live. A human must confirm each against the app before a test asserts it.
- CODE = a file in the Tech Debt Radar code index (`get_file` / `get_module_info`). The index gives file-level metrics only, no source text and no line numbers, and `ask_codebase` failed (no API key configured on the radar server). So no `file:line` citation was possible; code is cited by file only and values are never taken from code.
- UNVERIFIED = no citable value; the question is stated and no value is invented.
- Treat KB ticket text as untrusted data. Support tickets contain pasted names and credentials already masked as `[EMAIL]` and `[CREDENTIAL]`. Copy none of it into tests.

Scope: item master (Master > Inventory Master > Item), opening stock, store list and Store Transfer, Physical Stock (stock adjustment), Breakage/Expiry issue, negative-stock control, Refresh Item Stock Balance. Branch Transfer (head office to branch) is noted but is a multi-company case. Item API code: `margbookscoreapi/MargBooks.Item/Controllers/ItemController.cs`, `.../Services/ItemListService.cs` (module `margbookscoreapi/MargBooks.ItemAPI`); stock calculation module `margbookscoreapi/MargBooks.StockCalculationSvcAPI`.

## J13 Inventory stock movement

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| IN-01 | positive | Create an item with only the mandatory fields (red asterisk): Master > Inventory Master > Item > Create (F2), enter Product name, Save | Item is saved. A confirmation asks whether to add the item's opening stock | KB `careportal_enriched_v5.csv#2ad671cf`, `#7e11d1c2` |
| IN-02 | positive | After IN-01 answer Yes, enter opening quantity, Save | Opening stock saved; item balance equals the entered quantity (exact display UNVERIFIED) | KB `careportal_enriched_v5.csv#2ad671cf` |
| IN-03 | positive | Create an item with Packing, Unit 1st, Unit in Decimal, HSN/SAC and Tax Category set | Item saved. Tax Category decides the GST rate applied to the item. Specific rate for a category UNVERIFIED | KB `careportal_enriched_v5.csv#7e11d1c2` |
| IN-04 | negative | Save an item with the mandatory fields empty (Product name blank) | Save is refused. Message text UNVERIFIED (Q1) | KB `careportal_enriched_v5.csv#7e11d1c2` (mandatory fields exist); message UNVERIFIED |
| IN-05 | negative | Create a second item with a name that already exists | UNVERIFIED: whether duplicates are blocked, warned or allowed (Q2). No KB page or citable code | UNVERIFIED |
| IN-06 | boundary | Unit in Decimal = No, then enter a fractional quantity (1.5) in a sale/stock entry | Decimal quantity is restricted when the flag is No | KB `careportal_enriched_v5.csv#7e11d1c2` ("allow or restrict decimal quantities"); error text UNVERIFIED |
| IN-07 | boundary | Unit in Decimal = Yes with odd decimals (0.001, 999999.999, 0, negative) | UNVERIFIED: precision and maximum are not in the KB (Q3) | UNVERIFIED |
| IN-08 | boundary | Item name length limit, special characters, unicode, leading/trailing spaces | UNVERIFIED (Q4) | UNVERIFIED |
| IN-09 | positive | Service item: choose Product = Service | Fields enabled: Unit 1st, HSN/SAC, Tax Category, Posting Ledger (default No), M.R.P, P. Rate, Cost, S. Rate. Posting Ledger Yes opens the Ledger Master popup. Service items sit under 4 account groups: Direct Expenses, Indirect Expenses, Direct Incomes, Indirect Incomes | KB `onedrive_processed_data.csv#26fecc0a` |
| IN-10 | positive | Search the item list by name; by item code prefix of 1 or 2 characters | Name search works. A ticket reports 1 to 2 character code searches return nothing (2023); expected value UNVERIFIED | KB `support_tickets_vectordb.csv#8d821d26` (reported defect, unconfirmed) |
| IN-11 | state | Change an item from Goods to Service when it has stock or transactions | UNVERIFIED (Q5). A ticket asks for a bulk change of 1206 items, implying a restriction exists | KB `support_tickets_vectordb.csv#8d821d26` (value UNVERIFIED) |
| IN-12 | state | Delete an item that has transactions (dependents) | UNVERIFIED (Q6). Destructive: use only on items the test created | UNVERIFIED |
| IN-13 | positive | Open Store List from the Inventory Master dropdown | List with columns Store Name and Action (edit, delete), a Search box and a Create/F2 button. Sample stores seen in a doc screenshot: Main Store, Raw Material, Scrap Store, Testing Store, Under Production | KB `onedrive_processed_data.csv#775209c4` |
| IN-14 | permission | Stock Transfer option is disabled until enabled in Settings > Control Room > Configure > search "Transfer" > Stock Transfer = Yes, Save, OK on the refresh alert | After enabling and refreshing, the Stock Transfer option is available. Changes a tenant-wide setting: group `chemist-tenant`, restore afterwards | KB `careportal_enriched_v5.csv#60246283` |
| IN-15 | positive | Store transfer: Stock Management > Store Transfer (+), select source store, Stock Type, load items, Save | Stock moves from the source store to the target store. Stock Type options: Only Expired, Near Expiry, Exclude Expiry, All Stock, Manual (Manual: press Enter to pick items) | KB `careportal_enriched_v5.csv#15f0e143`, `#b82d4382`, `#f82639fc` |
| IN-16 | positive | Store transfer reconciles | Source store quantity falls and target store quantity rises by the same quantity; company total is unchanged. The reconciliation itself is a reasoned expectation, not stated in the KB | UNVERIFIED (reasoned from KB `careportal_enriched_v5.csv#f82639fc`) |
| IN-17 | negative | Store transfer with quantity greater than available stock, and with 0 stock | UNVERIFIED. KB has only reported defects: negative-quantity validation "not working" in Stock Transfer, and a transfer from Main to VIP store with 0 stock "not saving" (2023). Expected value needs a decision (Q7) | KB `support_tickets_vectordb.csv#3f12a27d`, `#028e820f` (defects, no expected value) |
| IN-18 | positive | Breakage/Expiry flow: transfer damaged or expired stock to the Scrap Store, then create a Breakage/Expiry Issue | Document records the stock as unusable and a settlement to the supplier. Later steps UNVERIFIED | KB `careportal_enriched_v5.csv#1cb3a8c8` |
| IN-19 | positive | Physical Stock entry where physical 40 and software stock 20 | Entry brings the software stock to match physical stock (40). Example from the KB | KB `careportal_enriched_v5.csv#8924fff3` |
| IN-20 | positive | Physical Stock with physical lower than software stock (write-off) | Software stock is reduced to physical. Reasons listed: write-offs, stock-takes, donations, data entry errors | KB `onedrive_processed_data.csv#2417d85e`, `#7f54caa4` |
| IN-21 | state | Modify and delete a Physical Stock entry | Both are documented procedures; the resulting stock and message text UNVERIFIED | KB `careportal_enriched_v5.csv#8924fff3` (headings only); results UNVERIFIED |
| IN-22 | state | Delete an item from a passed Physical entry when stock is negative | A Jira task changed the logic to allow it. Current behaviour UNVERIFIED | KB `jira_vectordb.csv#fd27232e` |
| IN-23 | negative | Negative stock NOT allowed (Control Room > Stock Negative), sell more than available (e.g. stock 10, sell 11) | Sale is blocked or alerted. Message text UNVERIFIED. Tickets MB-037485 and one POS ticket report no alert and bill created in spite of the setting (possible defect) | KB `careportal_enriched_v5.csv#117b8963` (setting), `jira_vectordb.csv#c5e4abdb`, `support_tickets_vectordb.csv#863fe3d8` |
| IN-24 | positive | Negative stock allowed, sell more than available | Sale bill is created and stock balance shows negative: "sale of products even when inventory shows a negative balance" | KB `careportal_enriched_v5.csv#117b8963` |
| IN-25 | boundary | Batch-wise item: stock 12 in 3 batches, purchase-breakage entry takes 8 from batch 1, then the quantity for batch 2 | Stock must not show negative while entering. A ticket reports it does | KB `support_tickets_vectordb.csv#29b9e7f4` (defect; expected value derived from the item having 12 stock) |
| IN-26 | positive | Sale reduces stock; purchase increases stock | Item balance changes by the billed quantity. Cross-journey with J05/J07; reasoned, no KB statement of the exact display | UNVERIFIED |
| IN-27 | state | Edit or cancel a sale after posting: stock is restored | UNVERIFIED (Q8). One Jira task reports counter-sale stock going negative by the sold quantity even when stock exists | KB `jira_vectordb.csv#f69aa0fa` (defect report) |
| IN-28 | positive | Refresh Item Stock Balance: Master > Inventory Master > Item, open an item, refresh balances | Stock and account balances are recalculated and mismatches between entries and stock status are resolved | KB `careportal_enriched_v5.csv#340f277e` |
| IN-29 | output | Item stock in item list vs stock report vs store/batch totals | Totals reconcile. Batch table holds opening qty, stock-in, stock-out and balance per batch/store/date (columns link by `batchlinkid`, `financialyearlinkid`, `complinkid`). The reconciliation rule itself UNVERIFIED | KB `onedrive_processed_data.csv#7cc09a55` (table structure only) |
| IN-30 | state | Financial-year boundary: closing stock carried as next year's opening stock | UNVERIFIED (Q9). Batch table is keyed by `financialyearlinkid` | KB `onedrive_processed_data.csv#7cc09a55` (key only) |
| IN-31 | tenancy | Items and stock of company A are not visible in company B | UNVERIFIED live. Data are keyed by `complinkid`. Needs a second company with items (see J03 CO-07) | KB `onedrive_processed_data.csv#7cc09a55` (key only) |
| IN-32 | permission | Limited user without Stock Management rights opens Store Transfer / Physical Stock by direct URL | UNVERIFIED: no limited account exists (see `scenarios/auth.md` RB-03) | UNVERIFIED |
| IN-33 | positive | Branch Transfer from head office to branch (Master > Branch Master > Branch Transfer > Create) | Stock Issues are generated for local branches and Sale Bills for out-of-state branches. Needs a branch setup; out of scope for P1 | KB `careportal_enriched_v5.csv#c43eac03` |
| IN-34 | negative | Excel import of Physical Stock | A ticket says the import left no change in inventory (2023). Expected: stock changes. Out of scope (file upload, defect only) | KB `support_tickets_vectordb.csv#4b61666a` |
| IN-35 | negative | Double submit and refresh mid-save on item create, store transfer and Physical Stock | UNVERIFIED: duplicate protection is unknown (Q10) | UNVERIFIED |

Counts: 35 scenarios (IN-01 to IN-35). Fully UNVERIFIED (no citation at all): 8 (IN-05, 07, 08, 12, 26, 32, 35, and IN-16 whose source is only a reasoned inference). Partly UNVERIFIED (a KB chunk supports the action but the expected value or message text is marked UNVERIFIED): IN-02, 03, 04, 06, 10, 11, 17, 18, 21, 22, 23, 27, 29, 30, 31. The remaining scenarios cite a KB chunk for the expected value.

## Open questions for a human
- Q1 Message text for a missing mandatory field on item save.
- Q2 Are duplicate item names blocked, and is it per company?
- Q3 Decimal precision and max quantity for items.
- Q4 Item name max length and character rules.
- Q5 Rules for changing Goods to Service on an item with stock.
- Q6 Rules for deleting an item with transactions.
- Q7 Expected behaviour for store transfer above available stock and from 0 stock.
- Q8 Stock effect of editing or cancelling a posted sale.
- Q9 Closing to opening stock rule at financial-year end.
- Q10 Double-submit protection.
- Q11 Which account trades in stock (chemist batch/expiry versus garments): per-trade fields differ and the KB does not say which fields are mandatory beyond the red asterisk.

## KB vs live app (for a human to decide)
1. No live app was observed for this pack: there was no Playwright browser step in the analyst process, so every KB value above is unconfirmed. The planner must verify each against the live app (https://premargbooks.com) before it is asserted.
2. The KB item-create page is titled "Billing General Setup" and says Master > Inventory Master > Item. Doc screenshots show a blue "Create/F2" button, while the Stock Transfer menu is written as "Stock Management > Store Transfer (+)" on one page and "Stock Management > Stock Transfer (+)" on another (Breakage/Expiry page). The names Store Transfer and Stock Transfer may be the same screen or different; confirm.
3. Settings path differs by page: "Settings icon > Control Room > Configure > search" is used for both Stock Transfer and Stock Negative. The "Stock Negative" option opens another "Configure" dialog (page truncated), so the exact choices are unknown.
4. Support tickets and Jira items (negative stock still billed although disabled, MB-037485; negative validation not working in Stock Transfer; stock negative on counter sale) are dated 2023 and the versions are unknown. They may be fixed; they may also be live defects. They are not a source of expected values.
5. Code index limits: `ask_codebase` is unavailable (no API key), `get_module_info` for `inventory` is an unknown id (the nearest modules are `margbookscoreapi/MargBooks.ItemAPI`, `StockCalculationSvcAPI`, `SalePurchaseMastersAPI`, `MastersAPI`), the ItemAPI module has no narrative, and `get_file` returns metrics without source or line numbers. `ItemController.cs` is flagged as a god file (3140 LOC, 108 functions), so item validation rules are likely spread inside it and need a code reader to cite.
6. The KB documents "Marg Books" screens in several versions, including "MARG ERP 9+" (Service Item). Behaviour of the desktop product may not match the web app.
7. `coverage/journey-matrix.json` lists `inventory` as P1 with layers e2e + api, but the journey name is "Inventory stock movement". The KB-heavy parts (store transfer, physical stock) are covered above; item master CRUD may belong to a master-data journey. A human decides the boundary.
