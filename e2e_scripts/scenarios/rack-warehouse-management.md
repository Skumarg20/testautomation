# Scenario pack: Rack / warehouse management (J28, rack-warehouse-management)

Status: DRAFT for QA/BA review (analyst pass, 2026-10-09). Priority P2, layer e2e. Plan: `specs/rack-warehouse-management.md`.

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`. KB items were NOT observed live; the planner confirms them before a test asserts them.
- CODE = a code-index chunk in the same KB (`codekb:MargBooks:*`). `ask_codebase` failed on 2026-10-09 ("No API key configured for provider 'anthropic'") and `get_file` does not know the source paths, so only the indexed chunks are cited; no `file:line` beyond what the chunk states.
- UNVERIFIED = not citable; the question is stated, no value invented.

Scope facts (KB)
- Store (warehouse/godown) master: Master >> Inventory Master >> Store opens "Store List" with predefined stores (Main Store for fresh stock, Brk/Exp Store, ...); Create opens "Create Store" with Store Name and Address; Edit (F3) opens "Modify Store"; delete icon asks "Are you sure ...". (`careportal_enriched_v5.csv#d31a6331`, `#ce432d17`, `#846d048f`)
- The store form fields in code: `storecode`, `storename`, `address1..3` (CODE `codekb:MargBooks:screen#8f9ca90d`, AddStore `add.store.component.ts:26-473`); table `dbo.StoreMaster` has `storecode`, `isPredefine`, soft delete `isdelete` (CODE `codekb:MargBooks:schema#1b1c30e7`).
- A predefined store, or a store with sales/purchases, cannot be deleted; stock must first be moved with a store transfer. (`careportal_enriched_v5.csv#846d048f`)
- Rack master: Master > Inventory Master > Rack opens "Rack List"; Create opens "Create Rack" with Store Name and Rack Name; Edit opens "Modify Rack"; delete asks for confirmation. A rack selected in any item cannot be deleted. (`careportal_enriched_v5.csv#2f2ecf2f`, `#eb4e77fe`)
- Rack form fields in code: `name`, `storelinkid` (AddRack `add.rack.component.ts:26-478`, saves with `POST rack/save`) (CODE `codekb:MargBooks:screen#1252e47c`, `codekb:MargBooks:api#a5ca1a90`). The list `RackMasterComponent` is routed at `/rack` and deletes through the same `rack/save` call (CODE `codekb:MargBooks:screen#6a9060e6`). Rack list is filtered per store: `GET Rack/List(complinkid, storelinkid)` (CODE `codekb:MargBooks:api#7f412684`).
- Rack name column is `nvarchar(30)` in `usp_RackMasterUpdate` (CODE `codekb:MargBooks:schema#aa4af1f9`). The newer `usp_RackMasterDelete` only sets `isdelete = 1`, with no in-use check (CODE `codekb:MargBooks:schema#f38c1998`); whether the UI path checks item usage is UNVERIFIED in code.
- Rack on the item: Create Item > Settings "Rack Required?" Yes shows a Rack field on the item, renamable per trade. (`careportal_enriched_v5.csv#f1e382b2`, `#f59f4e07`)

Jira / tickets (regression ideas)
- MB-038596: adding a rack to an item and updating made the app unresponsive (`jira_vectordb.csv#1fbe6514`).
- MB-031380: rack column showed blank duplicates in item creation (`jira_vectordb.csv#6d6c1dd0`, `support_tickets_vectordb.csv#1e4b107b`).
- Item rack not shown on the item list after update with smart search on (`jira_vectordb.csv#46a639b9`).
- MB-035757: a store with zero stock could not be deleted (`jira_vectordb.csv#6ac97a9b`).
- MB-036207: request for branch-wise rack management (`jira_vectordb.csv#791175c8`); feature request, not tested.

## Store (warehouse) master

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| RW-S01 | positive | Open Master > Inventory Master > Store | "Store List" with predefined stores (Main Store at least) | KB `careportal_enriched_v5.csv#d31a6331` |
| RW-S02 | positive | Create a store with a name (and code) and Save | Saved; listed in Store List | KB `#ce432d17` |
| RW-S03 | negative | Save with Store Name empty | Not saved. Message UNVERIFIED | UNVERIFIED |
| RW-S04 | negative | Duplicate store name (same case / other case) | Refused. Message and case rule UNVERIFIED | UNVERIFIED |
| RW-S05 | negative | Store name equal to a predefined store ("Main Store") | Refused as duplicate. UNVERIFIED | UNVERIFIED |
| RW-S06 | negative | Duplicate store code | UNVERIFIED (is the code unique?) | CODE `#8f9ca90d` (field exists) |
| RW-S07 | positive | Edit a store name | "Modify Store"; new name listed | KB `#ce432d17` |
| RW-S08 | positive | Delete an unused store | Confirmation; store gone from the list | KB `#846d048f` |
| RW-S09 | negative | Delete a predefined store (Main Store) | Refused | KB `#846d048f` |
| RW-S10 | negative | Delete a store that has stock / transactions | Refused until stock is transferred out | KB `#846d048f`; Jira MB-035757 |
| RW-S11 | state | Delete a store that still has a rack | UNVERIFIED (refused, or racks orphaned?) | UNVERIFIED |

## Rack master

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| RW-R01 | positive | Open Rack List | Grid Rack / Store / Action | KB `#2f2ecf2f` |
| RW-R02 | positive | Create a rack under a store | Saved; listed with its store | KB `#2f2ecf2f` |
| RW-R03 | negative | Save with Rack Name empty | Not saved. Message UNVERIFIED | UNVERIFIED |
| RW-R04 | negative | Save with no store | UNVERIFIED (required, or defaults to Main Store?) | CODE `#1252e47c` (`storelinkid`) |
| RW-R05 | negative | Duplicate rack name in the same store (and other case) | UNVERIFIED | UNVERIFIED |
| RW-R06 | positive | Same rack name in a different store | UNVERIFIED; racks belong to a store (`Rack/List` by store) | CODE `#7f412684` |
| RW-R07 | boundary | Rack name longer than 30 characters | Cut or refused; DB column is 30 | CODE `#aa4af1f9` |
| RW-R08 | positive | Edit a rack: rename and move to another store | "Modify Rack"; list shows new name and store | KB `#eb4e77fe` |
| RW-R09 | positive | Delete an unused rack | Confirmation Yes; rack gone | KB `#eb4e77fe` |
| RW-R10 | negative | Delete a rack set on an item | Refused | KB `#eb4e77fe` |

## Usage: rack on the item

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| RW-U01 | positive | Create Item, pick the new rack in the Rack field, save | Item saved; reopening shows the rack | KB `#f1e382b2` |
| RW-U02 | positive | Item List shows the rack of the item | UNVERIFIED (is there a rack column?) | Jira `#46a639b9` |
| RW-U03 | state | "Rack Required?" No hides the Rack field | Tenant-wide setting; not changed by the suite | KB `#f59f4e07` |
| RW-U04 | regression | Update an item's rack | Saves without hanging (MB-038596) | Jira `#1fbe6514` |

## Stock transfer between stores
Covered by J27 `tests/journeys/stock/test_stock_movement.py` (`StockTransferPage`), which moves stock from Main Store to another store. Here only RW-S10 depends on it; not repeated.

## Out of scope
Permissions for a limited user (no such account), API layer, rack-wise reports (UNVERIFIED which report), branch-wise racks (feature request).
