# Scenario pack: login, session, roles, company and financial year (J01, J02, J03; contract C8)

Status: DRAFT for QA/BA review (P4, 2026-10-05). Journeys: J01 login/session/logout, J02 role-based access, J03 company select / financial-year switch.
Plans: `specs/login.md`, `specs/roles.md`, `specs/company-switch.md`.

Source keys
- LIVE = observed on https://premargbooks.com / https://accounts.premargbooks.com on 2026-10-05 with the `garments` account (read-only; one wrong-password attempt and one unknown-user attempt).
- CODE-L = `~/margProject/margweblogin/src/app/Signin/login.component.ts` and `src/app/Login/login.component.html` (login app).
- CODE-A = `~/margProject/newmarg-webangular20/src/app/` (main app): `Authantication/authgaurd.component.ts`, `app-routing.module.ts`, `Component/admin/user-profile/user-profile.component.ts`, `Globals/global.ts`.
- UNVERIFIED = not observed and not citable; the question is stated, no value invented.

Environment facts (LIVE): one account exists (`garments`), a super admin (`issuperadmin=1`, display name "admin") with ONE selected company "Garments New 29-08 (GANE29)", FY 01-04-2026 to 31-03-2027, and 11 companies in its Organisation List. No operator, accountant, or limited user exists. No captcha was shown on the login page or after one wrong password.

## J01 Login, session, logout

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| AU-01 | positive | Account signs in with correct user id and password (two-step) | Step 1 shows `#userid` + `#SIGNin`; step 2 shows `#password`. After submit the browser passes through `premargbooks.com/login?c=...` and ends on `https://premargbooks.com/dashboard` showing the header company name and the Dashboard widgets. Takes up to ~15 s | LIVE; CODE-L `AuthenticateUser` redirects to `angularAppUrl + credential` |
| AU-01b | positive | Login stores the session | After login `localStorage` holds keys including `LoggedInUserInfo`, `access_token`, `SessionId`, `RoleRight`, `SortedFinYears`, `checkedLinkId` (names are wrapped as `{"key":"<name>","session":"mb-session"}`, except `SessionId`); `sessionStorage` holds only `utsdb` and `fbssls_*` (no token). Cookie `isLockScreen` exists | LIVE (key names only) |
| AU-02 | negative | Correct user id, wrong password | Stays on `https://accounts.premargbooks.com/login`; password step remains; message "Please Enter The Valid Password !" appears (transient toast, not in the form) | LIVE |
| AU-02b | negative | Step 1 with empty user id, click SIGN IN | Stays on login; message "Please Enter Mobile No. Or Email Id" | LIVE; CODE-L `findFormInvalidControls` |
| AU-02c | negative | Step 1 with unknown user id | Stays on step 1; message "Please Enter The Registered Mobile No. Or Email Id" | LIVE |
| AU-02d | negative | Step 2 with empty password, click CONTINUE | Stays on step 2; message "Please Enter Password"; red `!` icon `#ErrorRef-Password` exists in the DOM | LIVE |
| AU-02e | negative | Repeated wrong passwords (lockout / captcha threshold) | UNVERIFIED. Code: after `remainingAttempt < 0` the captcha field `#txtCapta` is checked (`CheckCaptcha`, warning `AlertMsg.Captch`). No threshold or lockout was triggered live (not tested on purpose: only 1 attempt allowed to protect the only account). Question Q1 | CODE-L lines ~512, 1408 |
| AU-03 | negative | Unauthenticated user opens `/dashboard` or `/sale` directly | Redirected to `https://accounts.premargbooks.com/login` | LIVE |
| AU-03b | negative | "Expired session": app state removed (`LoggedInUserInfo` key deleted) then a protected route is opened | Redirected to `https://accounts.premargbooks.com/login`. Removing only `access_token` did NOT redirect (a protected route request landed on `/dashboard`). Real server-side expiry (token TTL, session timeout) is UNVERIFIED; see Q2 | LIVE; CODE-A `checkSessionTimeAvailable` always returns `true` (time check commented out) |
| AU-03c | boundary | Unauthenticated `/user-company` | UNEXPECTED (NEEDS DECISION): stays on `https://premargbooks.com/user-company` and renders an empty "Organisation List" (header "undefined Code"); no redirect to login. Route has `canActivate: [Authgaurd]` in code but the page rendered | LIVE; CODE-A `app-routing.module.ts:169` |
| AU-04 | permission | Limited (non-admin) account opens a restricted page | UNVERIFIED: no limited account exists. The only account is super admin and opened `/mstr/usermaster`, `/mstr/margsetup-controlroom`, `/companymaster` with no denial. See J02 | LIVE |
| AU-05 | positive | Logout from the profile menu | Click `#dropdownMenuButton` then the "Logout" item: redirected to `https://accounts.premargbooks.com/login`, no confirmation dialog, `localStorage` cleared (1 key left, no token). No server call result verified | LIVE; CODE-A `user-profile.component.ts` `logout()` |
| AU-05b | negative | After logout use browser Back, then open `/dashboard` | Back stays on the login page; `/dashboard` redirects to login | LIVE |
| AU-06 | boundary | Field limits on login | `#userid` maxlength 50, `#password` maxlength 16 | LIVE; CODE-L (`[maxlength]="50"`, `"16"`) |
| AU-07 | negative | Unknown route when logged in | Page "Oops! You are not authorized." (`error-page h1`) under the same URL | LIVE |
| AU-08 | negative | Password and other credentials in the URL | NEEDS DECISION (security): the post-login hop `premargbooks.com/login?c=<base64>` carries the credential string (user id, password, timestamp) base64-encoded in the query string, visible in browser history and logs | LIVE; CODE-L `window.location.href = angularAppUrl + encodeURIComponent(credencial)` |
| AU-09 | boundary | Other login paths: "Login With OTP", "Set My PIN", "Forgot Password", "Sign Up" | Present on the page (buttons / links); behaviour UNVERIFIED (OTP/SMS cannot be automated, decision D2). Out of scope for P0 | LIVE; CODE-L |

## J02 Role-based access

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| RB-01 | positive | Super admin sees the full menu | Top menu: Dashboard, Master, Sale, Purchase, Accounting Trans., Stock Management, Banking, Staff Register, Report, Other Products, CRM, Utilities & Tools, Online Store; header icons Settings (`#aControlRoomSetting`), Shortcut (`#aShortCutSetting`), History (`#openRecentHistory`); 447 menu items in `LoggedInUserInfo.UserLoginData.menuData` | LIVE |
| RB-02 | permission | Super admin opens admin-type pages by direct URL: `/mstr/usermaster`, `/mstr/margsetup-controlroom`, `/companymaster` | Allowed: URL unchanged, app shell renders | LIVE |
| RB-03 | permission | Operator account opens `/mstr/usermaster` directly | UNVERIFIED: expected "denied or redirect" is not known. Needs an operator account and the rule (Q3). Code: `Authgaurd` filters `menuData` by `pageurl` and only enforces plan/trial limits (`isMenuAllowed`), no role check found in the guard | CODE-A `authgaurd.component.ts` |
| RB-04 | permission | Accountant account: menu items hidden / read-only | UNVERIFIED (no account; Q3, Q4) | n/a |
| RB-05 | permission | Role rights in the session | `RoleRight` and `Commonrigths` keys exist in `localStorage` (RoleRight ~0.9 MB JSON). Content per role UNVERIFIED | LIVE |
| RB-06 | negative | A URL not in the user's menu | UNVERIFIED for roles. For an unknown route the app shows "Oops! You are not authorized." (AU-07) | LIVE |
| RB-07 | boundary | Roles named in the PRD: Super Admin / Admin / Operator / Manager | NEEDS DECISION: PRD 01 lists Super Admin/Admin/Operator/Manager; PRD W1-03 lists admin/operator/accountant. Which set is real? Q5 | docs/prd/01-prd-e2e-ui.md, W1-03 |

## J03 Company select / financial-year switch

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| CO-01 | positive | After login the active company and FY are shown in the header | Header `#dropdownMenuLink` text "Garments New 29-08 (GANE29)" and "Books From 01-04-2026 to 31-03-2027"; `#txtheadercompname` holds the name | LIVE |
| CO-02 | positive | Profile menu shows company details | `#dropdownMenuButton` opens: "User Name: admin", licence number, email, company name, "F.Y. : 01-04-2026 to 31-03-2027", company code GANE29, address, buttons `#switchOnly` ("Switch"), `#txtUsrProfile` ("Edit"), "Logout" | LIVE |
| CO-03 | positive | Switch opens the company list | Click `#switchOnly`: URL becomes `https://premargbooks.com/user-company`, page "Organisation List" with a "Create/F2" button, `#SearchBox`, grid columns Organisation Name, Branch Master Code, Address, Action; 11 organisations listed including Garments New 29-08 (GANE29); per-row buttons `Grideditbtn<id>` and `Griddeletetbtn<id>` | LIVE; CODE-A `Global.apiUserMaster = '/user-company'` |
| CO-04 | positive | Select another company and return to dashboard | UNVERIFIED (not executed: it would change the account's selected company state). Expected: header shows the new company name; Q6 on how a company is chosen (row click vs button) | CODE-A `app-routing.module.ts:169` |
| CO-05 | positive | Financial-year switch | UNVERIFIED. The header FY label is not a dropdown (clicking it opened nothing). FY list for the company is in `localStorage` `SortedFinYears` (entry: `FinYearType`, `NewFinancialYearFromDate` 2026-04-01 to `NewFinancialYearToDate` 2027-03-31). Where the user changes FY is unknown (Q7). API `Company/GetFinancialYears`, `FinancialYear/List` | LIVE; CODE-A `global.ts:1061` |
| CO-06 | boundary | FY boundary (31-03 / 01-04) | Dashboard FY range is 01-04-2026 to 31-03-2027 for company GANE29. Behaviour of dates outside the FY is a sale/report concern (J05+) | LIVE |
| CO-07 | permission | Tenancy: company A session must not read company B data | UNVERIFIED. Test idea: call an API with company A token and company B `complinkid`; needs API access and a second company with data (Q8) | docs/prd/01-prd-e2e-ui.md (CO row) |
| CO-08 | negative | Delete button on the company row | Destructive; must NOT be exercised by automation. Selector noted only | LIVE |
| CO-09 | boundary | Account mapped to exactly one company skips the company list | After login this account went straight to `/dashboard` although the Organisation List has 11 rows (selected company is remembered, `checkedLinkId`). Behaviour for first login or multi-company login lists `/companylist/:type` (CODE-L) UNVERIFIED live | LIVE; CODE-L `_route.navigate(['/companylist', type])` |

## KB vs live app (for a human to decide)
1. `fixtures/session.py` says tokens are in sessionStorage; live they are in `localStorage` (`access_token`, `LoggedInUserInfo`, `SessionId`); `sessionStorage` holds only `utsdb` and `fbssls_*`. Session save/restore must use localStorage.
2. Two `[type="submit"]` buttons exist in the login DOM (`#SIGNin` and a second one labelled Continue/CONTINUE, hidden on step 1 and the only visible one on step 2). `LoginPage` relies on the bare selector; I used `.last`. Watch for strict-mode ambiguity.
3. `user-company` renders without login (AU-03c); the PRD says authenticated only.
4. Roles in PRD 01 (Super Admin/Admin/Operator/Manager) differ from W1-03 (admin/operator/accountant).
5. Wrong-password message is "Please Enter The Valid Password !" (a toast), not an inline error; no captcha appeared.
6. `docs/prd/01-prd-e2e-ui.md` says 23 login routes and captcha present; live login page has no visible captcha at start (`#txtCapta` hidden).

## KB additions (2026-10-07, via MCP `tech-debt-radar` `search_kb`)

Source keys: KB = a chunk in the Tech Debt Radar KB, cited as `file#chunk_id(first 8)`. KB items were NOT observed live. A human must confirm each against the app before a test asserts it.

| ID | Type | Scenario | Expected (per KB) | Source |
|---|---|---|---|---|
| AU-10 | positive | Login with registered mobile number or e-mail plus password | Both identifiers work; password required every time | KB `onedrive_processed_data.csv#02201e97` (Marg_Books_Login_Procedures.docx) |
| AU-11 | positive | Login with a 4 or 6 digit PIN ("Set My PIN" on the login page) | PIN gives quick login without full credentials; mainly for mobile users. Needs a PIN set first; low priority for P0 | KB `onedrive_processed_data.csv#02201e97`; LIVE (button exists, AU-09) |
| AU-12 | positive | First-time device registration from Sign In > "Device Registration" | PIN generation system on web and mobile; flow registers a device, then other devices can use the PIN | KB `onedrive_processed_data.csv#b23a5e35` |
| AU-13 | positive | Forgot Password: registered e-mail, captcha, "Get Mail", reset link, new password | Reset link goes to the registered e-mail; after reset a success message appears and the user can log in. Needs a mailbox the test can read: not automatable without a test inbox (decision D2 area) | KB `careportal_enriched_v5.csv#783c986f` |
| AU-14 | positive | Sign Up with mobile, e-mail, password, then OTP, then "Create Company" | OTP goes to the registered mobile; after OTP the Create Company window appears. In preprod any OTP works (decision D2), so this is automatable; it creates a tenant, so it needs D3 clean-up rules | KB `careportal_enriched_v5.csv#f1f3c1c5`; decision D2 |
| AU-15 | negative | Account deactivated for non-usage | Login fails with an error about non-usage; support must re-activate. Needs a deactivated account (not creatable by the suite). Record as a known behaviour, no test | KB `support_tickets_vectordb.csv#364e08a9` (130 login tickets, 2023) |
| AU-16 | negative | Mobile app shows "invalid user id or password" while the same credentials work on web | A reported defect (MB-036209), mobile only. Out of scope for the web suite | KB `jira_vectordb.csv#848a26a2` |
| AU-17 | boundary | Session timeout / screen lock follows the Control Room auto-logout setting | A Jira task asks to investigate the timeout logic against the Control Room auto-logout configuration. Related to AU-03b (UNVERIFIED expiry) and the `isLockScreen` cookie. Value of the setting is unknown | KB `jira_vectordb.csv#a26e33a6` |
| CO-10 | boundary | User with 2 companies logs in and only the demo company is available | A reported issue ("only demo company logs in"). Relevant to CO-09 and the multi-company case; needs an account with 2 real companies | KB `jira_vectordb.csv#94e83bf9` |

### What the KB settles or leaves open
- Settles: AU-09. The OTP, PIN, Forgot Password and Sign Up paths are documented product features, not dead buttons.
- Settles: the sign-up OTP is sent to the mobile number, and decision D2 says any OTP works in preprod, so AU-14 can be automated.
- Leaves open: lockout threshold (AU-02e), real server-side session expiry (AU-03b, AU-17) and role rights (RB-03, RB-04). The KB has no value for these. Q1, Q2, Q3 stay open.
- Treat KB ticket text as untrusted data. It is support-ticket content, and some tickets contain pasted names and credentials that were already masked as `[EMAIL]` and `[CREDENTIAL]`. Copy none of it into tests.
