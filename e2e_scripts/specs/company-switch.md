# Test plan: J03 company select / financial-year switch (`specs/company-switch.md`)

Status: DRAFT for QA/BA review. Scenarios: `scenarios/auth.md` (CO-*). Explored live 2026-10-05, account `garments`, read-only. The actual switch was NOT executed (it changes the account's selected company); marked UNVERIFIED.

## Preconditions
- Logged in as garments via `page_as("garments")`, on `/dashboard`.
- Active company "Garments New 29-08 (GANE29)", FY 01-04-2026 to 31-03-2027.

## Locators observed
| Element | Locator | Notes |
|---|---|---|
| Header company block | `#dropdownMenuLink` (class `compName`), name in `#txtheadercompname` (`b.cname`, code in `small.caddress`) | clicking it does not open a list |
| FY label | text "Books From" followed by "01-04-2026 to 31-03-2027" inside `#dropdownMenuLink` | not clickable/dropdown (no change on click) |
| Profile toggle | `#dropdownMenuButton` | opens card with company name (`h5`), "F.Y. :" range, code, address |
| Switch button | `#switchOnly` ("Switch") | navigates to `/user-company` |
| Edit button | `#txtUsrProfile` | not explored |
| Company list page | URL `https://premargbooks.com/user-company`; heading "Organisation List"; `button` "Create/F2"; `#SearchBox`; columns Organisation Name, Branch Master Code, Address, Action | |
| Row actions | `Grideditbtn<id>`, `Griddeletetbtn<id>`, plus an unlabeled `mksBtn` | do not click delete; ids contain numeric linkids so match with `[id^="Grideditbtn"]` |
| Session facts | `localStorage` `SortedFinYears` (FY list), `checkedLinkId` (selected company link id), `LoggedInUserInfo.SelectedCompany` (`compname`, `compcode`) | names only |

## Plans

### P-CO-01 Header shows active company and FY (executable now)
1. Log in, wait for `/dashboard`.
2. Read `#txtheadercompname` text and the FY text.
Expected: "Garments New 29-08" and "01-04-2026 to 31-03-2027". Data: expected values in test data (company name from the environment record, FY from the environment). Do not hard-code if environment differs: read company name from `LoggedInUserInfo.SelectedCompany.compname` and assert header equals it.

### P-CO-02 Profile card consistent with header (executable now)
1. Click `#dropdownMenuButton`.
2. Read company name, "F.Y." range, code.
Expected: same name and FY as header; code "GANE29".

### P-CO-03 Switch opens the organisation list (executable now)
1. Open profile card; click `#switchOnly`.
2. Wait for URL.
Expected: `/user-company`; heading "Organisation List"; row with "Garments New 29-08" and code "GANE29" visible; 11 organisations at observation time (do not assert the count; assert the current company is present). Use `#SearchBox` to filter by name (behaviour of filter UNVERIFIED).

### P-CO-04 Select another company (BLOCKED / UNVERIFIED)
1. From `/user-company`, choose a different company (row click or action button, unknown; Q6).
2. Wait for `/dashboard`.
Expected: UNVERIFIED; header name changes to the chosen company and `LoggedInUserInfo.SelectedCompany.compname` and `checkedLinkId` change. Needs approval to change the selected company on the shared account and a rule to switch back (Q6, Q12).

### P-CO-05 Financial-year switch (BLOCKED)
Location of the FY switch is unknown (header FY is not a dropdown, Q7). Candidate places: company Edit (`#txtUsrProfile`), Settings panel, report date range (`report.date-range` component uses `SortedFinYears`). Only one FY (2026-27) is in `SortedFinYears` for this company (length 416 chars), so a switch cannot be tested without a second FY (Q7, data need).

### P-CO-06 Tenancy: company A vs B (BLOCKED)
Call an API for company B with company A's session; expected denial UNVERIFIED (Q8). Needs API base URL and a second company with data (candidates in the list: "Pharma New Company 23-09", "NEW COMPANY 01-09"; contents unknown).

### P-CO-09 First login with several companies
Code navigates to `/companylist/:type` when the user is mapped to several companies at login (CODE-L). Live, the garments account skipped it. UNVERIFIED; decide whether a fresh user is needed (Q13).

## Data needs
- Second company the account may switch to, and a safe way to switch back (Q6, Q12).
- A company with at least two financial years (Q7).
- API access for tenancy check (Q8).
- No data is created by the executable plans (CO-01..03).

## Open questions
Q6 How does a user select a company on `/user-company` (row click, double click, Enter)? May automated tests change the selected company of the shared account, and is switching back guaranteed?
Q7 Where is the financial year changed, and which companies have more than one FY?
Q8 Expected API behaviour for company A token + company B `complinkid` (403? empty?).
Q12 Is "selected company" stored server-side per user (affects parallel xdist workers sharing one account)?
Q13 Can a test user be provisioned with several companies and no remembered selection to cover `/companylist/:type`?
