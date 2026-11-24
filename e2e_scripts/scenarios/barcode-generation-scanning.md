# Scenario pack: Barcode generation / scanning (J27, barcode-generation-scanning)

Status: DRAFT for QA/BA review (analyst pass, 2026-10-09). Priority P2, layer e2e. Plan: `specs/barcode-generation-scanning.md`.

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`. KB items were NOT observed live unless the spec says so.
- CODE = code-index chunks found through `search_kb` (`codekb:MargBooks:*`). `ask_codebase` failed on 2026-10-09 ("No API key configured for provider 'anthropic'"), so no code body was read.
- UNVERIFIED = not citable; the question is stated, no value invented.

Scope facts (KB)
- Barcode behaviour is driven by Control Room > Barcode Management: Name Of Barcode, Barcode Required (Master wise / Batch wise / Multiple / Parameter wise / Serial wise / No), Barcode Numbering Style (Automatic / Manual), Pattern Start From, Default Value Pick (`onedrive_processed_data.csv#f621122a`, `careportal_enriched_v5.csv#23a4c042`, `#0b1d00a3`).
- Automatic numbering: the item's Barcode field is pre-filled from the configured pattern, increments item by item, and is disabled; Manual: the user types it. Item Create also has "Print Label" Yes/No (`onedrive_processed_data.csv#c9b99382`).
- "Barcode Duplicate allowed?" in Control Room: Yes lets two items share a barcode (care portal example updates a second item with an existing barcode); No forbids it (`careportal_enriched_v5.csv#4427f5a5`, `#a66633af`).
- Create Item checks duplicates through `GET billpurchase/barcodeduplicatecheck` (ItemMaster + BatchMaster) (`codekb:MargBooks:api#c901896a`).
- Print: Report > Accounts Report > Misc. Report > Print Barcode; Print Criteria "Item Wise"; select item, Ok, Print; a "Select Format" window asks for the template, then Print sends to a printer (`careportal_enriched_v5.csv#9639900d`, `#0b1d00a3`). Format window = `BarcodeFormat` screen calling `POST printtemplate/printbarcodetemplate` (`codekb:MargBooks:screen#e6e98105`, `codekb:MargBooks:api#1683ea7d`).
- Sale bill: scanning an unknown barcode shows "Barcode Not Available" style errors (tickets) or, with generation enabled, "Barcode not found, do you want to create a new barcode ?" (`onedrive_processed_data.csv#d3f205c6`).

Jira / ticket history (regression ideas)
- MB-031744: editing an item shows "Duplicate barcode" wrongly (`jira_vectordb.csv#082139c2`).
- MB-031147: "Duplicate barcode is found" pop-up after every item save (`jira_vectordb.csv#492caaea`).
- MB-035359: barcode of a DELETED item still blocks reuse, "Duplicate Barcode Not Allowed" (`jira_vectordb.csv#dc86e645`, `#0dfd4187`).
- MB-038597: requirement that the duplicate message names the existing item, e.g. "Barcode already exists for item: ABC" (`jira_vectordb.csv#ae69d094`).
- "we are able to create item with duplicate barcode" (`jira_vectordb.csv#b65e4a7b`).
- MB-035193: sale bill scan says "BARCODE NOT AVILBLE" for an existing item (`jira_vectordb.csv#60d68c1c`); "stock not available" on scan although stock exists (`support_tickets_vectordb.csv#6b9aa689`).
- MB-036916, MB-038619: Print Barcode purchase-bill wise misses qty / packing (`jira_vectordb.csv#2d3677a2`, `#1e5be8a6`).

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| BC-01 | positive | Type a barcode in Create Item > Barcode and save the item | Saved; the barcode is shown again when the item is opened with Edit/F3 | KB `onedrive_processed_data.csv#c9b99382` |
| BC-02 | positive | Numbering Style = Automatic: open Create Item | Barcode pre-filled from the pattern and disabled; the next item gets the next number | KB `onedrive_processed_data.csv#c9b99382`, `careportal_enriched_v5.csv#23a4c042` |
| BC-03 | boundary | Barcode field length and case | UNVERIFIED in KB (planner: read `maxlength` and text transform live) | n/a |
| BC-04 | negative | Duplicate allowed = No: save a second item with an existing barcode | Save refused with a duplicate message; message text UNVERIFIED ("Duplicate Barcode Not Allowed" per MB-035359; MB-038597 wants the item name) | KB `careportal_enriched_v5.csv#a66633af`, `jira_vectordb.csv#dc86e645`, `#ae69d094` |
| BC-05 | positive | Duplicate allowed = Yes: second item with the same barcode | Saved | KB `careportal_enriched_v5.csv#4427f5a5` |
| BC-06 | regression | Delete an item, then reuse its barcode on a new item (duplicates not allowed) | Allowed (MB-035359 says it is wrongly refused) | KB `jira_vectordb.csv#dc86e645` |
| BC-07 | regression | Edit an item and keep its own barcode | No "Duplicate barcode" error (MB-031744) | KB `jira_vectordb.csv#082139c2` |
| BC-08 | positive | Scan (type + Enter) the item's barcode in a sale bill | The item is loaded on the line | KB `careportal_enriched_v5.csv#23a4c042` (Default Value Pick), tickets |
| BC-09 | negative | Scan an unknown barcode in a sale bill | Alert "Barcode Not Available" (already covered by sale-bill-creation `test_unknown_barcode_raises_an_alert`) or the create-new-barcode question | KB `onedrive_processed_data.csv#d3f205c6`, `support_tickets_vectordb.csv#3a696d8f` |
| BC-10 | negative | Scan the barcode of an item with no stock | UNVERIFIED: "stock not available" or loaded with negative stock, depends on settings | KB `support_tickets_vectordb.csv#6b9aa689` |
| BC-11 | positive | Print Barcode, Item Wise, select item, Ok, Print | Grid lists the item, barcode and qty; Print opens a "Select Format" window. Never confirm a printer | KB `careportal_enriched_v5.csv#9639900d` |
| BC-12 | negative | Print with no item chosen | Refused (message UNVERIFIED in KB) | n/a |
| BC-13 | positive | Barcode icon in the Item List row | Opens Barcode Printing for that item (UNVERIFIED in KB) | n/a |
| BC-14 | state | Control Room barcode settings are tenant-wide | Any test that changes one restores it; `xdist_group("chemist-tenant")` | e2e/CLAUDE.md rule 0 |
| BC-15 | output | Batch-wise barcodes generated on purchase/opening stock, picked by scan | Out of scope here (needs stock, items become undeletable) | KB `careportal_enriched_v5.csv#0b1d00a3` |
