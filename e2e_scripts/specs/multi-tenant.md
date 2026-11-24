# Plan: J16 multi-company switching and isolation (`multi-tenant`)

Status: DRAFT for QA/BA review. Scenario pack: `scenarios/multi-tenant.md`. Tests: `tests/journeys/company/test_multi_company.py`. Builds on J03 `specs/company-switch.md`.
Explored live 2026-10-08 with throwaway probes (login `garments`).

## Preconditions
- Every configured account is the same login; `garments_alt` is not set (and would be the same login). The second company comes from that login's Organisation List: company A "Garments New 29-08" (GANE29, where the suite works), company B "NEW COMPANY 01-09" (NECO01). No company is created or deleted.
- Switching changes the login's selected company (stored in `localStorage` `LoggedInUserInfo.SelectedCompany`, `checkedLinkId`; the next login opens the company used last). The `companies` fixture records the stored company, moves to A, and switches back to the recorded company in teardown. The module is in `xdist_group("chemist-tenant")` so it runs on one worker with the other tests that rely on the login's company state.
- Item tests create `QA-<run_id>-Item` in company A (`DataFactory.item_master`, J08 masters: unit PCS, HSN 12345678, tax "GST Sale - 12%", agency Others) and delete it from A in teardown.

## Locators (verified live)
| Thing | Locator |
|---|---|
| Switch | `CompanySwitchPage.switch_company` (J03): `/user-company`, double-click the organisation row (`[col-id="compname"]`) |
| Header | `#txtheadercompname .cname` |
| Item List search | searchbox "Search" (`#searchItems`). `fill` does NOT filter; typing key by key does. After reopening the list in the same page the box stops responding, so each search starts from the dashboard (`pages/company/item_search.py`) |
| Filter applied | wait until no named `[col-id="Product"]` cell lacks the searched text (ag-Grid also renders empty filler cells) |

## Plans
| ID | Test | Steps | Expected |
|---|---|---|---|
| MT-01 | `test_switch_shows_the_chosen_company_in_the_header` | From A switch to B | header "NEW COMPANY 01-09" |
| MT-02 | `test_switch_stores_the_chosen_company_in_the_session` | From A switch to B | stored company name is B |
| MT-04a | `test_item_is_found_by_search_in_its_own_company` | Create item in A; search it in A | found (positive control for MT-03) |
| MT-03 | `test_item_of_one_company_is_not_found_in_another` | Create item in A; switch to B; search it | not found |
| MT-04 | `test_item_is_found_again_after_switching_back` | Create item in A; switch to B and back to A; search | found |

## NEEDS DECISION
- MT-D1 The brief expected a `garments_alt` account with a second company. There is no such separate login; the tests use the second organisation of the one login. Confirm "NEW COMPANY 01-09" may be used as company B (it is opened read-only; nothing is written to it).
- MT-D2 (J03 Q12) Is the selected company per session or per login on the server? A switch in one worker could change the company a fresh login in another worker opens. Mitigated by teardown + xdist group, not proven.
- MT-05 Regression of MB-030329 (sale register / Net Sales after a switch shows the first company's data): needs known sales figures in both companies.
- MT-06 API call with A's token and B's `complinkid`: expected answer undefined (J03 Q8).
- MT-08 Isolation of ledgers, vouchers and Control Room settings: not covered; only items are checked.
