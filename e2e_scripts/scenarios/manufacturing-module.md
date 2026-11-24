# Scenario pack: J40 Manufacturing module (manufacturing-module)

Journey: `manufacturing-module` (J40, P3, layer e2e, phase2, status not_started). Plan: none yet (`specs/manufacturing-module.md` is for the planner). Tests: none yet.
Analyst pass 2026-10-12. No browser was opened and no login was used.

Source keys
- KB = Tech Debt Radar KB chunk, cited `file#chunk_id(first 8)`. The `tech-debt-radar` MCP server failed to connect in this session, so the same `search_kb` function (`codeheatmap/mcp_server.py:164`, `knowledge_base.search`, rerank on) was called read-only from the server's own venv. The chunk ids are the ones that tool returns.
- KB-doc = a OneDrive source document that the KB indexes, read directly because the relevant chunk did not come up in search (`OneDrive_2026-09-22/MARG BOOKS (2)/BOM/BOM_v1.0.docx`). The content is the same, but there is no chunk id.
- CODE = `file:line` in the read-only repos `newmarg-webangular20/src/app/...` (UI, shortened to `ui:`) and `margbookscoreapi/...` (API, shortened to `api:`).
- UNVERIFIED = no citable value. The question is stated and no value is invented.
- KB ticket text is untrusted data. Tickets carry masked IDs, emails and credentials. None of it is copied here, and none of it may go into tests.

Scope. "Manufacturing" in MargBooks, as the KB describes it, is:
1. The BOM feature: Stock Management > Bill of Materials > Material Master, Material Issue and Material Received, plus the BOM reports Pending & Register, Costing and Production Planning.
2. Conversion: Stock Management > Conversion > One to Many and Many to One. This is the "production ONE TO MANY" voucher, and its bill numbers carry the OM prefix (MB-034805).
3. The BMR Type master, as a side note.

The separate Angular `Manufacturing` module (`/manufacturing/*`: BMR, Stage, Department, Raw Material Formula, Planning, Indent, QC, Production) looks unrouted. See KB vs live app, item K1.

## What the KB says

- **Purpose.** BOM is a blueprint of raw materials and quantities for a finished product. It automates raw material consumption, keeps inventory accurate and calculates manufacturing cost (`careportal_enriched_v5.csv#ac42d395`).
- **Three options.** Material Master defines the formula. Material Issue issues raw materials "from inventory" to production. Material Received records the finished goods and "update[s] inventory automatically" (`#ac42d395`).
- **Five-step process.** Method Creation, Raw Material Issue to Production, Finished Product Receiving, Costing, Production Planning (`onedrive_processed_data.csv#c9c8d465`).
- **Enabling the feature.** Settings > Control Room > Configure > search "BOM" > "Bill Of Material(BOM)" = Yes > Esc > Save > OK (`careportal_enriched_v5.csv#5a957751`). The setting lives under Control Room > Transaction > Stock Management and defaults to No (`onedrive_processed_data.csv#de1c77aa`).
- **Material Master flow.** Stock Management > Bill of Materials > Material Master > Create/F2. Enter the BOM Name, pick the item to produce (F2 creates a new one), enter Qty, then add the raw materials with the quantity needed for one finished product. F10 moves to the By-Product Generated field, which is optional (Enter skips it). Additional Cost picks a ledger (for example Assembly Charges). Save, and the KB says the Material Master "has been created successfully" (`careportal_enriched_v5.csv#5a957751`, `#5edef903`).
- **Sample BOM.** "CPU 4 Series" produces CPU 450, Qty 1, from 7 raw items at 1 Pcs each, with rates 150, 2500, 1500, 899, 499, 599 and 849, a total of 7.00 Pcs (`onedrive_processed_data.csv#a5a8b6b5`).
- **Material Issue.** Create/F2, choose the "Production Department" ledger, then add each raw material and its quantity, for example the raw materials for 20 Labeling Machines. Save, and it is "saved successfully" (`careportal_enriched_v5.csv#5edef903`, `#67531890`). The user picks raw materials by hand. Rows show Qty, Rate (from the item master) and Amount = Qty x Rate (KB-doc BOM_v1.0 "Material Issue").
- **Material Received.** Create/F2, choose Production Department, set the date, pick the finished product and enter the quantity. A "Raw Material Consumed" window lists the raw materials and quantities "as defined in the Material Master". Click OK, enter the finished-product rate and Save (`careportal_enriched_v5.csv#67531890`). The popup columns are Item Name, Qty and Cost, with totals (KB-doc BOM_v1.0 "Material Receive").
- **Reports.** They are under Report > Inventory Report > Bill of Materials (KB-doc BOM_v1.0 "Report").
  - Pending & Register takes the Production Department ledger. Example: 10 sets issued and 7 received leaves 3 pending (`onedrive_processed_data.csv#50cbfc45`).
  - Costing gives the cost per unit as the sum of the component values (KB-doc BOM_v1.0 "Costing").
  - Production Planning "From Current Stock" multiplies each BOM component quantity by the planned quantity. A "From Vendor Stock" variant also exists (KB-doc BOM_v1.0; `onedrive_processed_data.csv#ae0c72c7`).
- **One to Many / Many to One.**
  - Enabled by Control Room "One To Many & Many To One" = Yes. The big-unit item carries Conversion 1, and the small-unit items are separate items (`careportal_enriched_v5.csv#a0aa8adf`, `#aa46966a`).
  - Entry path: Stock Management > Conversion > One to many > Create/F2. Set the date, choose the predefined ledger "Production Department", pick the big item, add the small items and Save. A "Stock Update" popup appears, then OK, and the entry is saved. The result is checked in the Item Ledger (`careportal_enriched_v5.csv#25e8dd21`).
  - Example: 5 x Sugar 1KG plus 5 x Sugar 5KG deducts 30 kg from the Sugar bag. A "Less Stock" dialog shows Stock 80 and BAG -30 (`onedrive_processed_data.csv#58e13213`, `#c036bd72`).
  - With Multi Unit on, an item that has a conversion loses decimal quantities (`onedrive_processed_data.csv#4b3addfc`). Changing an item's Conversion needs its transactions deleted first (`careportal_enriched_v5.csv#d890578b`).
- **BMR Type.** Master > Inventory Master > BMR Type, with sample types Powder and Tablets. BMR (Batch Manufacturing Record) is described as a chemical or process manufacturing document (`onedrive_processed_data.csv#a835ce0d`).
- **Which company type.** No KB page ties BOM or Conversion to a trade. Both are Control Room switches. Conversion is described as "mostly used in departmental stores" (`onedrive_processed_data.csv#9ba8ad4d`), and BOM "across industries" (`#ac42d395`). The code ties the BOM and Conversion party to the account group Sundry Creditor (Manufacturer), id 42 (`ui:Model/TransactionFactory/billofmaterialissue.factory.ts:29`, `ui:Globals/global.ts:20224`). `TradeEnum.pharmamanufacturing = 14` exists (`ui:Globals/global.ts:18863`), but no BOM gating on it was found. The QA login is a garments company (`docs/environment.md:14`). Whether the BOM and Conversion menus show there once the Control Room switches are on is UNVERIFIED.

## Code facts used below

- **Routes:**
  - BOM list: `/transaction/billofmaterial` (`ui:Modules/transaction.module.ts:211`).
  - BOM editor: `billofmaterialmater` and `billofmaterialmater/:action/:id`, registered in `other.masters.module.ts:175-176`, which is mounted at `/mstr` (`ui:app-routing.module.ts:82`). The list navigates to `/transaction/billofmaterialmater` (`ui:Component/Transaction/InverntoryTransaction/billofmaterialmasterlist.ts:192,214`). See K2.
  - Material Issue list: `/sale/matissue` (`ui:Modules/sales.module.ts:38`). Material Receive list: `/purchase/matrecieve` (`ui:Modules/purchase.module.ts:33`).
  - One to Many: `/purchase/onetomany`. Many to One: `/purchase/manytoone` (`ui:Modules/purchase.module.ts:30-31`).
  - BOM reports: `/report/bomreport/:type` and `/report/bomreport` for production planning (`ui:Modules/report.module.ts:260-261`).
- **Transaction data types:** OneToMany 223, ManyToOne 224, BillOfMaterialIssue 230, BillOfMaterialRecieve 231, BillOfMaterialDirectRecieve 233 (`api:margerputil/TransactionDataType.cs:45-49`).
- **Material Issue** is a sale-type document: page heading "Bill Of Material Issue", saved through `billSales.Save`, success text "Bill of Material saved successfully!" (`ui:Model/TransactionFactory/billofmaterialissue.factory.ts:24-33`). Role right "MaterialIssue" under "Stock Management" (`ui:Component/Transaction/InverntoryTransaction/processout.list.component.ts:435`).
- **Material Receive** is a purchase-type document: heading "Bill of Material Recieve" (sic), saved through `billPurchases.Save`, success text " Saved successfully!" (`ui:Model/TransactionFactory/billofmaterialrecieve.factory.ts:24-31`, `ui:Globals/global.ts:19045`). On save, stock is updated only for rows that are not raw material, so raw materials are not deducted a second time ("raw material is excluded from update stock", `api:margerpdal/SalePurchaseCommon.cs:431-446`).
- **Raw Material Consumed popup** (`ui:.../billofmaterialdetails.ts:210-247`):
  - Factor = received qty / BOM qty.
  - Raw qty = BOM raw qty x factor x conversion.
  - Raw rows are marked "Less" and by-products "Add".
  - Amount = qty x rate.
  - A raw row passes only if raw qty <= `balanceqty`, the balance pending with the chosen ledger. `GetBomItem` takes the ledger and store (`api:margerpbll/BomMaterBll.cs:106`).
  - Receiving less than the BOM qty raises "Minimum Quantity Should be :<BOM qty>".
- **Conversion stock:**
  - One to Many: the big item gets a sale (out) of `convertionQuantity`.
  - Many to One: the big item gets a purchase (in) of `convertionQuantity`.
  - Source: `api:margerpdal/SalePurchaseCommon.cs:601-623`.
- **BOM "used" flag.** A BOM counts as used when any of its component items appears in any live Material Receive line (dataType 231). The check is by component item, not by BOM (`api:margerpdal/Contracts/BomMaterDAL.cs:38`). See K4.
- **BOM duplicate checks:**
  - Name: case- and space-insensitive per company, API text "<name> already exist!" (`api:margerpdal/Contracts/BomMaterDAL.cs:259-263`).
  - Finished item: one BOM per item, API text " already exist!" (`api:.../BomMaterDAL.cs:292-296`).
- **BOM delete** is a soft delete, `isdelete=1` (`api:.../BomMaterDAL.cs:325`).

## Known defects and complaints (bugs cluster here, T6)

- MB-034805: the Item Register lists a production ONE TO MANY bill (OM00002, saved at 05 PM) before a purchase bill (1166, saved at 04:26 PM) on the same day, so production shows a negative running stock (`jira_vectordb.csv#54fd6003`, `#fb212bf9`, `support_tickets_vectordb.csv#ea4f0163`).
- MB-038393: Many to One entries sometimes post twice and sometimes not at all to the stock ledgers, which leaves stock reports wrong (`jira_vectordb.csv#1169a2f5`). MBC-17124 is a "stock in one to many and many to one" check (`jira_vectordb.csv#c230fd4c`). MBC-3745 checks stock after conversion, parameter company and partial conversion (`jira_vectordb.csv#6289d455`).
- MB-038971: after a BOM receive, changing the batch and saving gives "Bad Request" (`jira_vectordb.csv#6ff999a0`).
- MB-037251: the expiry of the finished product cannot be entered at Material Receive, and the Control Room expiry option keeps switching itself off (`jira_vectordb.csv#8a7fedd1`, `#5231ec1d`).
- MBC-17129: Production Planning against current stock shows the wrong required quantity when the planning quantity changes (`jira_vectordb.csv#415b00b0`).
- MB-036277 (fixed list) (`jira_vectordb.csv#afdde74a`, `support_tickets_vectordb.csv#aa83344a`):
  - BOM edit/delete validation.
  - Main item not selectable.
  - Qty and Rate enterable without an item.
  - By-product serial numbers and quantity.
  - Additional ledger F2.
  - Production Planning export to Excel/PDF.
  - Vendor-wise planning showing a negative quantity.
  - Missing totals in Pending Register and Costing.
- MBC-16368: modifying a Material Master shows an empty item grid (`jira_vectordb.csv#621cf68f`). MBC-13026: the item list should open when typing in "Item Produce" (`jira_vectordb.csv#3d999bce`). MBC-12760 "Bom Production Issue" has no detail (`jira_vectordb.csv#db66baea`).
- Requests:
  - Direct Issue+Receive in one entry: MB-036408 and MB-038802 (`jira_vectordb.csv#2318b35c`, `#5a68f123`). MBC-14105 enabled it (`support_tickets_vectordb.csv#86c72de1`), and the code has `BillOfMaterialDirectRecieve = 233`.
  - Auto-load the BOM raw materials into Material Issue: MB-038690 (`jira_vectordb.csv#fa0552ef`).

## Scenarios

Data for every stock row: create run-unique items RM-A and RM-B (raw, goods) and FG (finished, goods) with opening stock RM-A 100, RM-B 50, FG 0. Create BOM "BOM-<run>": FG Qty 1 = RM-A 2 + RM-B 1. Use the Production Department ledger. Read stock with `pages/stock/item_stock_balance.py` (main store; refresh first, see IN-28 in `scenarios/inventory.md`). "Auto" marks P1 automation candidates.

| ID | Type | Scenario | Expected result | Source | Auto |
|---|---|---|---|---|---|
| MF-01 | positive / setting | Control Room > Configure > search "BOM" > "Bill Of Material(BOM)" = Yes > Esc > Save > OK | Stock Management shows "Bill of Materials" with Material Master, Material Issue and Material Receive. Default is No. This is a tenant-wide switch, so the test reads it first and restores it afterwards (`pages/settings/control_room.py` `ControlRoom` pattern) | KB `careportal_enriched_v5.csv#5a957751`, `onedrive_processed_data.csv#de1c77aa`; KB-doc BOM_v1.0 "BOM Menu" | P1 (precondition) |
| MF-02 | positive | Material Master > Create (F2): BOM Name, Item to Produce FG, Qty 1, raw RM-A 2 and RM-B 1, Save | Toast "Record saved successfully." and a return to the BOM list. The KB wording is "created successfully" | CODE `ui:.../billofmaterialmaster.ts:760-763`, `ui:Globals/global.ts:18945`; KB `careportal_enriched_v5.csv#5edef903` | P1 |
| MF-03 | positive | BOM list after MF-02 | A row with BOM Name, Produced Item FG, Qty/Unit 1 and By Product Qty 0, plus edit and delete actions. The list query also returns billdate (dd-MM-yyyy) | KB-doc BOM_v1.0 "Material Master List"; CODE `api:margerpdal/Contracts/BomMaterDAL.cs:38` | P1 |
| MF-04 | positive | Material Master with a by-product (qty 1) and an Additional Cost ledger (for example Assembly Charges, amount 100) | Saved. Grid totals read "Total: n Product" / "Total: n Ledger" | KB `careportal_enriched_v5.csv#5a957751`, `#5edef903`; CODE `ui:.../billofmaterialmaster.ts:820-829` | P2 |
| MF-05 | validation | Save with BOM Name blank, or Item to Produce blank, or Qty blank | Form invalid: bomname, itemname and qty are required. Message text UNVERIFIED | CODE `ui:.../billofmaterialmaster.ts:126-128` | P2 |
| MF-06 | boundary | BOM Name of 3 characters, 4 characters, 50 characters, 51 characters; unicode and special characters | Input has `minlength=4` and `maxlength=50`. 51 characters cannot be typed. Behaviour at 3 characters and with unicode is UNVERIFIED | CODE `ui:.../billofmaterialmaster.html:26`, `ui:.../billofmaterialmaster.ts:126` | P2 |
| MF-07 | duplicate | Second BOM whose name equals an existing one, differing only by case or spaces | Name field is marked duplicate (API returns status -2, "<name> already exist!"). Visible text UNVERIFIED | CODE `api:.../BomMaterDAL.cs:259-263`, `ui:.../billofmaterialmaster.ts:113-118` | P1 |
| MF-08 | duplicate | Second BOM for the same finished item FG | Warning "Bom Of this FG Already Exists!" and focus returns to the item | CODE `ui:.../billofmaterialmaster.ts:527-533`, `api:.../BomMaterDAL.cs:292-296` | P1 |
| MF-09 | validation | Save with no raw-material row | Warning "Raw Material Required!" and nothing is saved | CODE `ui:.../billofmaterialmaster.ts:705-723`, `ui:Globals/global.ts:19736` | P1 |
| MF-10 | validation | Enter a quantity on a raw row with no item, then a raw qty of 0 or negative | "Please select item first" / "Quantity should be greater than 0!". MB-036277 reported the first was missing (fixed) | CODE `ui:.../billofmaterialmaster.ts:889-901`, `ui:Globals/global.ts:18995,19354`; KB `jira_vectordb.csv#afdde74a` | P2 |
| MF-11 | validation | Raw-material picker: choose a Service item; choose FG itself; choose RM-A a second time | "Can't Select Service Item!" / "Can't Select Finised Good!" / "Can't Select Raw Material Items!" (texts as spelled in the code). Duplicate rows are not allowed per KB-doc | CODE `ui:Component/Master/Item/itemmaster.component.ts:4891-4903`, `ui:Globals/global.ts:19737-19739`; KB-doc BOM_v1.0 "Create Material" | P2 |
| MF-12 | validation | Additional Cost ledger row with amount 0 | "Please enter amount" | CODE `ui:.../billofmaterialmaster.ts:907-910`, `ui:Globals/global.ts:19335` | P3 |
| MF-13 | boundary | Finished item with conversion > 1 (for example 10), Qty not a multiple of it | "Quantity Should By multiple of conversion". The saved BOM qty is Qty x conversion. The exact trigger condition is odd (K6) | CODE `ui:.../billofmaterialmaster.ts:443-450, 698` | P3 |
| MF-14 | positive / stock | Material Issue (F2): party Production Department, RM-A 20 and RM-B 10, Save | "Bill of Material saved successfully!". Main-store stock RM-A 100 -> 80 and RM-B 50 -> 40; FG unchanged at 0. The decrease is reasoned: "issue raw materials from inventory", sale-type document | KB `careportal_enriched_v5.csv#ac42d395`, `#5edef903`; CODE `ui:Model/TransactionFactory/billofmaterialissue.factory.ts:26,31`. Exact figures UNVERIFIED until seen live | P1 |
| MF-15 | positive | Material Issue rows | Each row shows Qty, Rate (from the item master) and Amount = Qty x Rate. Example: RM-A 20 x rate 150 = 3000.00 | KB-doc BOM_v1.0 "Material Issue" | P2 |
| MF-16 | permission | Material Issue party picker | Only ledgers of the group Sundry Creditor (Manufacturer) are offered (Production Department is a predefined ledger). Behaviour on another ledger name typed in is UNVERIFIED | CODE `ui:Model/TransactionFactory/billofmaterialissue.factory.ts:29`, `ui:Globals/global.ts:20224`; KB `careportal_enriched_v5.csv#25e8dd21` ("predefine ledger master") | P2 |
| MF-17 | negative / stock | Material Issue of RM-A 120 when stock is 100, with Negative Stock = No, then with Yes | No: blocked or warned (the general text is "Stock going in negative!"). Yes: saved and RM-A shows -20. Whether BOM issue follows the sale rule is UNVERIFIED | CODE `ui:Globals/global.ts:19322`; KB `careportal_enriched_v5.csv#117b8963` (via IN-23/IN-24 in `scenarios/inventory.md`) | P2 |
| MF-18 | positive / stock | Material Receive (F2): party Production Department, today's date, FG qty 10 | Raw Material Consumed popup: RM-A 20 "Less", RM-B 10 "Less" (2x10, 1x10). OK, enter FG rate, Save, toast " Saved successfully!". Stock: FG 0 -> 10; RM-A stays 80 and RM-B stays 40 (not deducted twice) | KB `careportal_enriched_v5.csv#67531890`; CODE `ui:.../billofmaterialdetails.ts:215-223`, `api:margerpdal/SalePurchaseCommon.cs:431-446`, `ui:Globals/global.ts:19045` | P1 |
| MF-19 | boundary / stock | Partial receive: after MF-14, receive FG 7 | Saved. FG +7. Pending & Register for Production Department shows the remainder pending (KB example: 10 issued, 7 received, 3 pending). Here 3 sets = RM-A 6, RM-B 3 | KB `onedrive_processed_data.csv#50cbfc45` | P1 |
| MF-20 | negative | Receive more than was issued: after MF-14, receive FG 11 (needs RM-A 22 > 20 pending) | Warning "RM-A Quantity Not Available". The popup refuses OK, so the receive cannot proceed | CODE `ui:.../billofmaterialdetails.ts:224-246` | P1 |
| MF-21 | boundary | BOM Qty 2 (FG 2 = RM-A 4 + RM-B 2), receive FG 1 | "Minimum Quantity Should be :2". A non-multiple receive (for example 3) gives a factor of 1.5. Rounding is UNVERIFIED | CODE `ui:.../billofmaterialdetails.ts:211-215` | P2 |
| MF-22 | negative | Material Receive with no Material Issue at all | Raw rows have balance 0, so "<raw> Quantity Not Available" and no receive | CODE `ui:.../billofmaterialdetails.ts:224-232` (`balanceqty` per ledger, `api:margerpbll/BomMaterBll.cs:106`) | P2 |
| MF-23 | state | Delete a BOM that has no receives | Confirmation "Are you sure you want to delete the selected Record?". On Yes the row disappears. The toast reads "Record updated successfully.", not "Record deleted successfully." (K3) | CODE `ui:.../billofmaterialmasterlist.ts:217-250`, `ui:Globals/global.ts:18939,18942,18955` | P1 |
| MF-24 | state | Delete a BOM after MF-18 (it has a receive) | Warning "Bill of Material Already Used" and the row stays | CODE `ui:.../billofmaterialmasterlist.ts:216-218`, `ui:Globals/global.ts:19744`; KB `jira_vectordb.csv#afdde74a` ("Validation for DeleteEdit Case") | P1 |
| MF-25 | state | Edit a used BOM: delete a raw row; edit an unused BOM: change raw qty and Save | Used: "Bill of Material Already Used" on row delete. Unused: "Record updated successfully." and the item grid is populated on open (MBC-16368 regression) | CODE `ui:.../billofmaterialmaster.ts:836-839, 762`; KB `jira_vectordb.csv#621cf68f` | P2 |
| MF-26 | state / stock | Modify, then delete, a saved Material Issue and a saved Material Receive | Stock reverts by the same quantities (Issue delete: RM-A +20, RM-B +10; Receive delete: FG -10). After a receive, changing the batch must not give "Bad Request" (MB-038971). Revert values UNVERIFIED | KB `jira_vectordb.csv#6ff999a0`; reasoned | P2 |
| MF-27 | output | Costing report for FG | Cost per unit = sum of component Qty x unit cost, here RM-A 2 x rate + RM-B 1 x rate. Ledger must be Sundry Creditor (Manufacturer), else "Please Select Only 'Sundry Creditor (Manufacturer)' A/C Ledgers". Whether additional cost is included is UNVERIFIED | KB-doc BOM_v1.0 "Costing"; CODE `ui:Component/Report/Accounting/billofmaterial/billofmaterial.report.ts:413`, `ui:Globals/global.ts:19746` | P2 |
| MF-28 | output | Production Planning "From Current Stock", FG, planned qty 10, View; then change the planned qty to 15 | Required RM-A 20 and RM-B 10, then RM-A 30 and RM-B 15 (BOM qty x planned qty). MBC-17129 reports a wrong recalculation on change | KB-doc BOM_v1.0 "Production Planning – Current Stock"; KB `jira_vectordb.csv#415b00b0`; CODE `ui:.../productionplanning.report.ts:104` | P2 |
| MF-29 | positive / setting | Control Room "One To Many & Many To One" = Yes; item BIG with Conversion 1 and small items S1 (conv 1) and S5 (conv 5) | Stock Management > Conversion > One to many / Many to one are available (`/purchase/onetomany`, `/purchase/manytoone`). Tenant-wide switch: read first, restore afterwards | KB `careportal_enriched_v5.csv#a0aa8adf`, `#aa46966a`, `onedrive_processed_data.csv#4b3addfc`; CODE `ui:Modules/purchase.module.ts:30-31` | P1 (precondition) |
| MF-30 | positive / stock | One to Many: Production Department, BIG (opening 80), add S1 x 5 and S5 x 5, Save | "Stock Update"/"Less Stock" popup shows BIG -30. OK, toast " Saved successfully!", bill number with prefix OM (for example OM00002). Stock: BIG 80 -> 50, S1 +5, S5 +5 | KB `careportal_enriched_v5.csv#25e8dd21`, `onedrive_processed_data.csv#58e13213`, `#c036bd72`, `jira_vectordb.csv#54fd6003` (OM prefix); CODE `api:margerpdal/SalePurchaseCommon.cs:613-617` | P1 |
| MF-31 | positive / stock | Many to One: Production Department, BIG, add S1 x 5 and S5 x 1 | BIG +10 and S1 -5, S5 -1. Each entry posts exactly once to the Item Ledger (MB-038393 double or missing posting) | KB `careportal_enriched_v5.csv#25e8dd21`, `jira_vectordb.csv#1169a2f5`; CODE `api:margerpdal/SalePurchaseCommon.cs:619-623` | P1 |
| MF-32 | output / sequence | Same day: purchase BIG +10 at time T1, then One to Many at T2 > T1 | Item Register lists the purchase before the OM bill, and the running balance never goes negative (MB-034805) | KB `jira_vectordb.csv#54fd6003`, `#fb212bf9` | P2 |
| MF-33 | state | Change Conversion on an item that has conversion transactions | Refused until the transactions are deleted. On success: "Record Updated successfully". Refusal text UNVERIFIED | KB `careportal_enriched_v5.csv#d890578b` | P3 |
| MF-34 | permission | Role without the "MaterialIssue" (Stock Management) right; direct URL `/sale/matissue` | Menu entry hidden and direct URL denied. Not covered today: no limited user on the QA login | CODE `ui:.../processout.list.component.ts:435`; `docs/environment.md:28` | — |
| MF-35 | tenancy | BOM created in company A, then switch to company B | B's BOM list does not contain A's BOM (the list is filtered by complinkid) | CODE `api:.../BomMaterDAL.cs:38` (`where bm.complinkid =`) | P2 |
| MF-36 | date | Material Issue/Receive backdated before the FY start or future-dated | UNVERIFIED (KB silent). Expiry of FG at receive is a known gap (MB-037251) | KB `jira_vectordb.csv#8a7fedd1` | — |
| MF-37 | positive | BMR Type master: Master > Inventory Master > BMR Type, create "Powder" | Listed with existing types. Route, fields and messages UNVERIFIED (the `/manufacturing/bmr` route looks unrouted, K1) | KB `onedrive_processed_data.csv#a835ce0d`; CODE `ui:Manufacturing/manufacturing.module.ts:65` | — |

GST: Material Issue/Receive and Conversion are internal stock movements with no GST slab on the voucher, and the KB is silent on tax. GST rows are not applicable, and nothing is asserted.

## Navigation, selectors and messages for the planner

- Menu: Stock Management > Bill of Materials > Material Master / Material Issue / Material Receive(d); Stock Management > Conversion > One to many / Many to one (KB `#5edef903`, `#67531890`, `#25e8dd21`). Reuse `pages/stock/stock_menu.py` (add entries to `StockScreen`) and `pages/settings/control_room.py` for the switches.
- Keys: F2 opens Create on the BOM list (`ui:.../billofmaterialmasterlist.ts:133-134`). Esc on the list goes to `/dashboard` (`:136-137`). F10 moves from the raw grid to By-Product (KB `#5a957751`).
- Element ids: `#txtbomname` (gets focus on open), `#txtqty`. Form controls: `bomname`, `itemname`, `qty` (`ui:.../billofmaterialmaster.html:26-50`, `.ts:106`).
- Toasts use the notifier: `pages/stock/messages.py` `StockMessages.expect_shown(regex)`.
- API (for setup and teardown or assertions): `GET BOMMaster/List`, `POST BOMMaster/Save`, `GET BOMMaster/GetBom`, `GET BOMMaster/CheckDuplicateData`, `GET BOMMaster/CheckDuplicateItem`, `GET BOMMaster/UpdateBomStatus`, `GET BOMMaster/GetBomItem` (`ui:Globals/global.ts:1176-1184`, `api:margerpapi/Controllers/BOMMasterController.cs:19-130`). Rate limit 15 requests per second per endpoint (KB `codekb:MargBooks:api#6f2e84b0`).
- Message strings (`ui:Globals/global.ts`):
  - 19736 "Raw Material Required!"
  - 19737 "Can't Select Service Item!"
  - 19738 "Can't Select Raw Material Items!"
  - 19739 "Can't Select Finised Good!"
  - 19741 "Bill of Material saved successfully!"
  - 19743 "Some BOM item raw material missing!"
  - 19744 "Bill of Material Already Used"
  - 19745 " item raw material Qty Not Available!"
  - 19746 "Please Select Only 'Sundry Creditor (Manufacturer)' A/C Ledgers"
  - 18945 "Record saved successfully."
  - 18942 "Record updated successfully."
  - 18939 "Record deleted successfully."
  - 18955 "Are you sure you want to delete the selected Record?"
  - 19045 " Saved successfully!"
- Inline strings: "Bom Of this <Product> Already Exists!" (`billofmaterialmaster.ts:532`), "Quantity Should By multiple of conversion" (`:448`), "<raw> Quantity Not Available" and "Minimum Quantity Should be :<n>" (`billofmaterialdetails.ts:212,232`).
- Test data must be run-unique and created by the test. Never delete or modify shared BOMs. A BOM with a receive cannot be deleted, so teardown order is: delete Receive, delete Issue, delete BOM. Both Control Room switches are tenant-wide and must run in one serial xdist group with restore.

## KB vs live app (for a human to decide; not resolved here)

- **K1.** The Angular `ManufacturingModule` (`ui:Manufacturing/manufacturing.module.ts:63-110`: `/manufacturing/bmr`, `planning`, `materialissue`, `billofmaterial` "Raw Material Formula", `production`, QC...) is not referenced by any `loadChildren`. Only its own declaration was found (`:204`). The static `defaultMenu` lists these pages (`ui:Globals/global.ts:6082-6841, 9649-9712, 15213`). The KB places BMR Type under Master > Inventory Master (`#a835ce0d`). Is this module live for any trade (for example pharmamanufacturing = 14), or dead code?
- **K2.** The BOM list navigates to `/transaction/billofmaterialmater` for Create and Edit (`ui:.../billofmaterialmasterlist.ts:192,214`), but that route is registered only in the `/mstr` module (`ui:Modules/other.masters.module.ts:175-176`). Save then returns to `/transaction/billofmaterial` (`billofmaterialmaster.ts:763`). Check which URL the live app actually shows. The planner should not hard-code either URL.
- **K3.** Deleting a BOM sends `isactive: 2` and then shows "Record updated successfully." because the delete text is only used for status 0 (`ui:.../billofmaterialmasterlist.ts:250`). This is probably a wrong toast. Confirm before asserting.
- **K4.** "Used" is computed from receives of any component item, not of this BOM (`api:.../BomMaterDAL.cs:38`, join on `pcb.itemlinkid=bim.itemlinkid and pcb.dataType in (231)`). Any receive of a finished product that consumes RM-A could therefore lock every BOM that contains RM-A. It may also mean a receive's finished-item line marks a BOM as used. Needs a decision.
- **K5.** Save success wording differs: the KB says "Material Master ... created successfully" and "Material Issue ... saved successfully", while the code shows "Record saved successfully." and "Bill of Material saved successfully!". The receive page heading is spelled "Recieve" and the route `matrecieve`. Assert on code strings only after a live check.
- **K6.** The multiple-of-conversion check in `billofmaterialmaster.ts:447` (`qty / conv == qty % conv && ...`) only fires in narrow cases, and fires on any Tab. Its behaviour may not match its message.
- **K7.** Some KB text is now stale against the code. KB-doc BOM_v1.0 says the user picks raw materials by hand in Material Issue, and MB-038690 asks for auto-load. MB-036408/MB-038802 ask for a single Issue+Receive entry, and MBC-14105 plus `BillOfMaterialDirectRecieve = 233` show it now exists. Is "Direct Receive" a separate menu item, and which setting turns it on? UNVERIFIED.
- **K8.** The KB says Additional Cost is "unchecked by default; when unchecked the section is disabled" (KB-doc BOM_v1.0). The care portal describes adding a ledger by pressing Enter (`#5edef903`). The checkbox was not found in the code read. Check live.
- **K9.** In the KB's One to Many example (5 x 1 kg + 5 x 5 kg) the dialog shows "Stock 80" and "BAG -30", which mixes kg with BAG units (`#c036bd72`). Confirm the unit actually deducted from the big item.
- **K10.** Trade availability is unconfirmed. Neither the KB nor the code read ties BOM or Conversion to a trade; only Control Room switches gate them. Whether the garments QA company shows these menus once the switches are Yes needs a live look before planning.
