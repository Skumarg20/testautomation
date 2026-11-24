# Test plan: J02 role-based access (`specs/roles.md`)

Status: DRAFT for QA/BA review. Scenarios: `scenarios/auth.md` (RB-*, AU-04). Explored live 2026-10-05 with the only account (`garments`, super admin). Only the allowed side of access control could be observed; the denied side is UNVERIFIED.

## What exists today
- One account: super admin (`LoggedInUserInfo.UserLoginData.issuperadmin = 1`, display name "admin"). Source: LIVE.
- No admin / operator / accountant / limited account. Roles in docs disagree (Q5).
- Code: `Authgaurd` (CODE-A `Authantication/authgaurd.component.ts`) matches the URL against `menuData[].pageurl` and applies plan/trial limits; no role check was found in the guard. Role rights are stored client-side in `localStorage` keys `RoleRight` and `Commonrigths`. User management page: `/mstr/usermaster`; "User Access & Privileges" is under the Settings panel (`#aControlRoomSetting`).

## Preconditions
- Logged in via `page_as("garments")` (or a role fixture once roles exist; `Settings.credentials` resolves `QA_<ACCOUNT>_USER/PASS`).

## Locators observed
| Element | Locator |
|---|---|
| Top menu | texts Dashboard, Master, Sale, Purchase, Accounting Trans., Stock Management, Banking, Staff Register, Report, Other Products, CRM, Utilities & Tools, Online Store (no ids; use `get_by_text`) |
| Settings panel | `#aControlRoomSetting`; panel shows "User Access & Privileges" (Configure) and "Control Room" (Configure) |
| Header icons | `#aShortCutSetting`, `#openRecentHistory`, `#dropdownMenuLink2` (Notifications) |
| Not-authorized page | `error-page h1` "Oops! You are not authorized." |
| Menu data (session) | `localStorage['{"key":"LoggedInUserInfo","session":"mb-session"}']` -> `UserLoginData.menuData[].pageurl` (447 entries for super admin) |

## Plans

### P-RB-01 Super admin menu (executable now)
1. Log in as garments, wait for dashboard.
2. Assert the 13 top-level menu texts are visible.
Expected: all visible. Data: none.

### P-RB-02 Super admin opens admin pages directly (executable now)
1. Logged in, `goto` each of `/mstr/usermaster`, `/mstr/margsetup-controlroom`, `/companymaster`.
2. After 6 s read the URL and check the menu bar is rendered.
Expected: URL unchanged and no "not authorized" heading. Observed: all three allowed. This is the positive half of AU-04.

### P-AU-04 / RB-03 Limited account is denied restricted pages (BLOCKED, test stays skipped)
1. Log in as the operator (or accountant) account.
2. `goto("/mstr/usermaster")`, `/mstr/margsetup-controlroom`, `/companymaster`.
3. Expected: UNVERIFIED (denied page, redirect to dashboard, or error). Must be defined by the product owner (Q3).
Needed to unblock: see below.

### P-RB-05 Menu parity per role (BLOCKED)
Compare `menuData[].pageurl` set per role to the expected role matrix (Q4). The tech PRD wants `coverage/menu-snapshot-<trade>-<role>.json`; only the super admin snapshot can be produced now.

### P-RB-06 Direct URL of an item not in the user's menu (partly executable)
Unknown route returns "Oops! You are not authorized." for super admin. For limited roles UNVERIFIED.

## Data needs (exactly what is required to unblock AU-04 / J02)
1. An operator account (login id + password) in the same Garments company, with the documented restricted set.
2. An accountant account likewise (if "accountant" is a real role, Q5).
3. Optionally an admin (non-super) account.
4. Env vars: `QA_OPERATOR_USER/PASS`, `QA_ACCOUNTANT_USER/PASS`, `QA_ADMIN_USER/PASS` (tech PRD T2: role accounts).
5. A table "role -> allowed pages, denied pages, expected denial behaviour" (Q3, Q4).
6. Creating those users through `/mstr/usermaster` was NOT done (read-only exploration). Product owner to confirm whether tests may create users via UI/API (Q11).

## Mapping to skipped test
`test_limited_account_is_denied_restricted_pages` (AU-04) stays skipped until items 1-5 exist; add the restricted URLs above as the first candidates.

## Open questions
Q3 What exactly happens when a limited user opens a restricted URL (message, redirect target)? Which URLs are restricted for operator and accountant?
Q4 Role matrix: which menus are visible per role?
Q5 Which roles exist in MargBooks: Super Admin/Admin/Operator/Manager (PRD 01) or admin/operator/accountant (W1-03)?
Q11 May tests create users (User Master) through the UI or API on this environment, and who owns cleanup?
