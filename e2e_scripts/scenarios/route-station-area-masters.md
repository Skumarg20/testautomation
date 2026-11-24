# Scenario pack: route / station / area masters (J25, journey id `route-station-area-masters`)

Status: DRAFT for QA/BA review (2026-10-09). Journey J25 "Route / station / area masters", priority P2, layer e2e. Live findings are in `specs/route-station-area-masters.md`.

Source keys
- KB = a chunk in the Tech Debt Radar KB (MCP `search_kb`), cited as `file#chunk_id(first 8)`.
- CODE = the code index in the same KB (`codekb:MargBooks:code|api|screen|schema`), cited the same way. `ask_codebase` failed (no API key on the server), and `get_file` does not hold the BLL files, so method bodies are only the first lines.
- UNVERIFIED = not citable; the question is stated, no value invented.

## What the KB says about the three masters
- Menu: Master >> Other Master >> Route / Area / Station; F2 creates, Edit icon modifies (KB `careportal_enriched_v5.csv#67cd74fd`, `#78e25a3c`, `#8b0bc945`).
- Route groups areas for salesmen ("South Delhi" holds "Lajpat Nagar", "Greater Kailash") (KB `careportal_enriched_v5.csv#67cd74fd`). Route Master can be enabled or disabled (KB `careportal_enriched_v5.csv#e2b09670`).
- Area belongs to a route: form fields `areaname`, `autoCompleteRoute` (CODE `codekb:MargBooks:screen#e588117a` AddArea); table `AreaMaster.routelinkid` (CODE `codekb:MargBooks:schema#565d33ec`). Area name longer than 50 is refused (`ErrAreaNameLength`, CODE `codekb:MargBooks:code#618a44da`).
- Station is a required field of a customer or supplier ledger (KB `careportal_enriched_v5.csv#8b0bc945`, `#b443f252`); form field `stationname` only (CODE `codekb:MargBooks:screen#a8e428b3`). The update procedure declares `@stationname nvarchar(15)` (CODE `codekb:MargBooks:schema#d9b151d3`) while the UI allows 25 characters (seen live).
- Area delete is a soft delete with no usage check in the procedure (`usp_AreaMasterDelete` sets `isdelete = 1`, CODE `codekb:MargBooks:schema#b591800f`). Station delete (`StationMasterService.Delete`) calls the repository straight through (CODE `codekb:MargBooks:code#1979b04e`): no usage check is visible.
- Jira: "Area unable to delete (MB - 028699)": duplicate area names shown in an area-wise ledger report, and an area could not be deleted (KB `jira_vectordb.csv#1516965a`). Jira: "Master>Ledger>Station create window is not closing after station creation while doing ledger creation" (KB `jira_vectordb.csv#03cf7d6e`).

## Route

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| RT-01 | positive | Create a route with a unique name | "Record Saved Successfully"; route listed in Route List | KB `careportal_enriched_v5.csv#67cd74fd` |
| RT-02 | positive | Rename a route via Edit | "Record Updated Successfully"; list shows the new name only | KB `careportal_enriched_v5.csv#67cd74fd` (modify process) |
| RT-03 | usage | Rename a route that an area uses | The Area List shows the new route name for that area | UNVERIFIED (derived: area stores `routelinkid`, CODE `#565d33ec`) |
| RT-04 | negative | Save a route with an empty name | Refused, nothing created | UNVERIFIED (KB marks the field mandatory only by *) |
| RT-05 | negative | Create a route whose name already exists (same case and other case) | Refused with a duplicate message | UNVERIFIED wording |
| RT-06 | negative | Delete a route that an area uses | Refused, route stays | UNVERIFIED |
| RT-07 | positive | Delete an unused route | Confirmation asked; route removed from list | KB `careportal_enriched_v5.csv#67cd74fd` |
| RT-08 | config | Route master disabled in settings: menu hides Route | KB `careportal_enriched_v5.csv#e2b09670`; not automated (tenant-wide setting) |

## Area

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| AR-01 | positive | Create an area under a route | Saved; Area List shows area with its route | KB `careportal_enriched_v5.csv#78e25a3c`; CODE `#e588117a` |
| AR-02 | negative | Save an area without a route | Refused | CODE `#e588117a` (route field on the form); rule UNVERIFIED |
| AR-03 | negative | Save an area with an empty name | Refused | UNVERIFIED |
| AR-04 | negative | Duplicate area name | Refused | UNVERIFIED (Jira MB-028699 shows duplicates once existed) |
| AR-05 | positive | Rename an area | "Record Updated Successfully"; list shows new name | KB `careportal_enriched_v5.csv#78e25a3c` (modify process) |
| AR-06 | positive | Delete an area | Removed from list | KB `careportal_enriched_v5.csv#78e25a3c`; CODE `#b591800f` |
| AR-07 | boundary | Area name of 50+ characters | Refused by the API (`ErrAreaNameLength`); UI max length is 30 (live) | CODE `#618a44da` |
| AR-08 | usage | Area used on a customer / party then deleted | UNVERIFIED: the procedure has no usage check (CODE `#b591800f`); not automated, Customer master needs its module enabled | UNVERIFIED |

## Station

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| ST-01 | positive | Create a station | Saved; listed in Station list | KB `careportal_enriched_v5.csv#8b0bc945` |
| ST-02 | usage | Pick the new station on a customer ledger | Ledger saved; Ledger Master shows the station | KB `careportal_enriched_v5.csv#8b0bc945`, `#b443f252` |
| ST-03 | positive | Rename a station | "Record Updated Successfully"; list shows new name | KB `careportal_enriched_v5.csv#8b0bc945` |
| ST-04 | negative | Empty station name | Refused | UNVERIFIED |
| ST-05 | negative | Duplicate station name (same and other case) | Refused | UNVERIFIED |
| ST-06 | boundary | Station name longer than 15 characters (UI allows 25) | Saved and listed in full | CODE `#d9b151d3` (15 in the update procedure) vs live UI 25: NEEDS DECISION |
| ST-07 | negative | Delete a station a ledger uses | UNVERIFIED: no usage check visible in code (CODE `#1979b04e`) | UNVERIFIED |
| ST-08 | positive | Delete an unused station | Removed from list | KB `careportal_enriched_v5.csv#8b0bc945` |
