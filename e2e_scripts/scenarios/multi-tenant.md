# Scenario pack: multi-company switching and isolation (J16 `multi-tenant`)

Status: DRAFT for QA/BA review (2026-10-08). Plan: `specs/multi-tenant.md`. Related: J03 `scenarios/auth.md` (CO-*), `specs/company-switch.md`, `tests/journeys/company/test_company_switch.py`.

Source keys
- KB-SW = care portal "How to Switch Company in Marg Books ?" (`careportal_enriched_v5.csv`, chunk `87d2410c`): Profile icon > "Switch" > "Organisation List" > select the company; and the testing variant (chunk `f3662263`): select the company and press Enter.
- JIRA-30329 = `jira_vectordb.csv` chunk `2bae3472` and support ticket chunk `5d26e521`: "When user is switching the company, sale register report data of first company is showing in the switched [second] company" (MB-030329, 23-01-2026).
- LIVE = observed on the QA tenant 2026-10-08 with the `garments` login.
- UNVERIFIED = not observed and not citable.

Environment facts (LIVE): every account in `.env` is the same login (there is no separate `garments_alt` login configured). That login has 12 organisations in its Organisation List, among them "Garments New 29-08" (code GANE29, the suite's company A), "NEW COMPANY 01-09" (code NECO01, used as company B), "25-26 Fy" (another books year), and one marked "Do Not Use". The selected company is kept in `localStorage` (`LoggedInUserInfo.SelectedCompany`, `checkedLinkId`) and the next login opens the company used last.

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| MT-01 | positive | Switch from company A to company B (Profile > Switch, double-click the row) | Dashboard opens; header shows "NEW COMPANY 01-09" | KB-SW; LIVE |
| MT-02 | positive | Session after the switch | `LoggedInUserInfo.SelectedCompany.compname` is company B; `checkedLinkId` changes | LIVE |
| MT-03 | tenancy | An item created in company A, searched by name in company B's Item List | Not found | LIVE (isolation rule from the brief; no KB value) |
| MT-04 | positive | The same item searched in company A, before and after a round trip through B | Found | LIVE |
| MT-05 | tenancy | Sale register / dashboard Net Sales right after a switch | Shows company B's figures, not A's (regression of JIRA-30329). UNVERIFIED: needs known sales in both companies | JIRA-30329 |
| MT-06 | tenancy | API call with company A's session but company B's `complinkid` | UNVERIFIED (J03 Q8): expected denial not defined | `specs/company-switch.md` P-CO-06 |
| MT-07 | concurrency | Two sessions of one login in different companies at the same time | UNVERIFIED (J03 Q12): whether one session's switch changes the other's company | none |
| MT-08 | tenancy | Ledgers, vouchers and settings (Control Room) of A not visible in B | UNVERIFIED: only items were checked | none |

## KB vs live app
- KB-SW says select the company and press Enter; the suite double-clicks the row (`CompanySwitchPage.switch_company`), which works live.
- The task brief expected a `garments_alt` account with a second company; live `garments_alt` is not configured and, per `config/settings.py`, would be the same login anyway. The second company comes from the one login's Organisation List.
