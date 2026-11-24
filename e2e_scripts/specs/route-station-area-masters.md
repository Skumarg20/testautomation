# Spec: route / station / area masters (J25, `route-station-area-masters`)

Status: DRAFT for QA/BA review (2026-10-09). Scenarios: `scenarios/route-station-area-masters.md`. Seen live on the garments QA company ("Garments New 29-08 (GANE29)", app V. 4.3.598.b) with throwaway probes, 2026-10-09.

## Screens (seen live)

| Master | How it opens | List | Form | Field ids |
|---|---|---|---|---|
| Route | URL `/route` only: the sidebar Master > Other Master shows Customer, Area, Station but no Route on this company | "Route List" (h1); grid columns Route, Action; searchbox "Search" | "Create Route" / "Modify Route" dialog: Route * | `#txtRouteName` |
| Area | Master > Other Master > Area (`/mstr/area`) | "Area List"; grid columns Area, Route, Action. With no areas the page shows "No Area Created Yet" and no search box | "Create Area" / "Modify Area": Route Name * (typeahead "Search here..", max 40), Area * (max 30) | `#autoCompleteRoute`, `#txtAreaName` |
| Station | Master > Other Master > Station (`/mstr/station`) | "Station" (h1, WATCH VIDEO); grid columns Station, (actions); search input `#SearchBox` | "Create Station" / "Modify Station": Station * (max 25) | `#txtStaionName` (sic) |

All three: Create/F2 opens the form; F10 Save / F10 Update; F9 Clear; Esc Close asks "Are you sure you want to close?" when the form is dirty. Row buttons Edit/F3 and Delete; Delete asks "Are you sure you want to delete the selected Record?" (Yes = `#btnYes`).

## Behaviour seen live

| Ref | Action | Seen |
|---|---|---|
| RT-01 | Save new route | success toast "Record Saved Successfully."; form closes; row listed |
| RT-02 | Rename route | success toast "Record Updated Successfully."; list shows the new name |
| RT-04 | Save empty route | no toast; form stays open; seen once as inline "Route name required !", once as a "!" link with tooltip "Route is required!" |
| RT-05 | Duplicate route, same case and lower case | error toast "Route Already Exists!"; form stays open |
| RT-06 | Delete a route used by an area | confirmation, then error toast "AreaArea Available For This Route." (sic, doubled word); route stays listed |
| RT-07 | Delete unused route | success toast "Record Deleted Successfully" |
| AR-01 | Save area with a route | "Record Saved Successfully."; list row shows area and route |
| AR-02 | Save area without route | no toast; inline "Route Name required !"; form stays open |
| AR-04 | Duplicate area name (same route) | value set without typing: error toast "Area Already Exists!" on Save. Typed key by key: the field shows "!" with tooltip "Area name already exists !" before Save and no toast comes |
| AR-02b | Type into Area while Route is empty | after the first key the focus jumps to the Route field ("Select valid Route!"); the rest of the text lands in Route |
| AR-05 | Rename area to a new unique name | Typed key by key: "Record Updated Successfully."; list shows the new name. Set with Playwright `fill` (no key events): refused with inline "Area name already exists !" (seen twice). Tests type the name; see NEEDS DECISION N4 |
| AR-04b | Same area name under a different route | Saved; both rows listed (duplicate check is per route) |
| AR-06 | Delete area | "Record Deleted Successfully" |
| ST-01 | Save station | "Record Saved Successfully."; listed |
| ST-03 | Rename station | "Record Updated Successfully."; list shows new name |
| ST-05 | Duplicate station, same and lower case | error toast "Station Already Exists!" |
| ST-06 | 24-character station name | saved and listed in full |
| RT-03 | Rename a route an area uses | Area List shows the area with the new route name |
| ST-02 | Customer ledger with the new station | Ledger Master's Station column shows it; after a station rename it shows the new name |
| ST-07 | Delete a station a ledger uses | confirmation, then error toast "Ledger Are Available For This Station."; station stays |
| ST-04 | Save empty station | no toast; form stays open (inline text not captured) |

## Defects (suspected)
- D1 withdrawn: the area rename refusal only happens when the value is set without key events (Playwright `fill`, also paste-like input). See N4.
- D2 (cosmetic, RT-06): the refusal text reads "AreaArea Available For This Route.".

## NEEDS DECISION
- N1: Route has no sidebar entry on the garments company (KB says Route Master can be disabled, `careportal_enriched_v5.csv#e2b09670`) but `/route` still opens and saves. Is direct URL access to a disabled master intended? Tests open `/route` by URL.
- N2: Station name: UI allows 25 characters, the update procedure declares `nvarchar(15)` (KB `codekb:MargBooks:schema#d9b151d3`). Long names saved on create; is 15 or 25 the rule?
- N3: Station delete is refused when a ledger uses it (seen live, although `StationMasterService.Delete` shows no check, KB `#1979b04e`: the check lives elsewhere). Area delete when a customer uses it was not tried (the Customer master needs its module; the area procedure has no usage check, KB `#b591800f`). What is expected for an area in use?
- N4: The area duplicate-name check runs on key events: a value put into the Area field without typing (paste via script, autofill) is refused on Update with "Area name already exists !" even when the name is new. Is a paste by a user affected too? Worth a manual check.
- N5: An area name may repeat under different routes (AR-04b). Intended? The Jira "Area unable to delete (MB - 028699)" mentions duplicate area names in an area-wise report (KB `jira_vectordb.csv#1516965a`).

## Tests (`tests/journeys/other_masters/`)
Each test creates `QA-<run_id>-...` records and deletes them in teardown (ledgers, then areas, routes, stations). Garments account, company pinned to "Garments New 29-08".
- `test_route.py`: RT-01, RT-04, RT-05 (same case, other case), RT-02, RT-06, RT-07, RT-03.
- Lists open by URL (`/route`, `/mstr/area`, `/mstr/station`): the Route page has no sidebar, so a menu walk cannot start there. `test_area_list_opens_from_the_master_menu` and `test_station_list_opens_from_the_master_menu` cover the menu path.
- `test_area.py`: AR-01, AR-02, AR-04, AR-04b, AR-05, AR-06.
- `test_station.py`: ST-01, ST-04, ST-05 (same case, other case), ST-06, ST-03, ST-02 (new and renamed station on a ledger), ST-07, ST-08.
Not automated: RT-08 (tenant-wide setting), AR-07 (UI caps at 30, API limit 50 not reachable from the UI), AR-08 (Customer module).
