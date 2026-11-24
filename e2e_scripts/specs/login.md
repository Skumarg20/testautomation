# Test plan: J01 login, session, logout (`specs/login.md`)

Status: DRAFT for QA/BA review. Scenarios: `scenarios/auth.md` (AU-*). Explored live 2026-10-05, account `garments`, read-only. Maps to tests in `tests/journeys/auth/test_login.py`.

## Preconditions
- App `https://premargbooks.com`, login `https://accounts.premargbooks.com/login`, two-step style (`LOGIN_STYLE=two_step`).
- Fresh browser context, no stored state (for login tests use `browser.new_context()`, not the `page_as` fixture).
- Valid credentials from settings (`settings.credentials("garments")`; env `QA_GARMENTS_USER/PASS`). Never log or print them.
- Wrong-password data: a constant that is not the real password, e.g. `"Wrong#Pass123"`. Max 1 wrong attempt per test run until Q1 (lockout) is answered.

## Locators observed (login app)
| Element | Locator | Notes |
|---|---|---|
| User id | `#userid` (placeholder "Email address or mobile number", `formcontrolname=userid`, maxlength 50) | step 1 |
| Step-1 button | `#SIGNin` (text SIGN IN) | step 1 |
| Password | `input#password` (`formcontrolname=password`, maxlength 16, type password) | visible only on step 2 |
| Step-2 button | `button[type=submit]` visible, text CONTINUE | a hidden second submit exists in the DOM |
| Step-2 links | links "Back", "Forgot Password" | |
| Password error icon | `#ErrorRef-Password` (text "!") | hidden until error |
| Other | buttons "Set My PIN", "Login With OTP"; link "Sign Up" | out of scope |
| Captcha input | `#txtCapta` | NOT visible at start / after 1 wrong attempt |
| Messages | transient toast text; role/selector UNVERIFIED (use `get_by_text` of the message) | Q9 |

Locators in the main app after login
| Element | Locator |
|---|---|
| Company name / FY (header) | `#dropdownMenuLink`, `#txtheadercompname` |
| Profile menu toggle | `#dropdownMenuButton` |
| Logout item | `a.dropdown-item` with text "Logout" (`get_by_text("Logout", exact=True)`) |
| Not-authorized page | `error-page h1` text "Oops! You are not authorized." |

## Plans

### P-AU-01 Login success (test exists: `test_every_account_reaches_dashboard_with_stored_session`)
1. Open login URL. Expect `#userid` visible.
2. Fill `#userid`; click `#SIGNin`. Expect `input#password` visible.
3. Fill `input#password`; click the visible CONTINUE button.
4. Wait up to 150 s (observed ~15 s) for URL `https://premargbooks.com/dashboard`.
Expected: dashboard URL; header `#dropdownMenuLink` contains the company name. Data: garments credentials.
Optional (AU-01b): assert `localStorage` has keys `SessionId` and one ending with `"access_token"...` (wrapped JSON name) and `sessionStorage` has no token. Do not assert values.

### P-AU-02 Wrong password (skipped test AU-02: `test_wrong_password_stays_on_login`)
1. Open login, step 1 with valid user id, reach step 2.
2. Fill `input#password` with the wrong constant; click CONTINUE.
3. Wait 3 s for the toast.
Expected: URL still `accounts.premargbooks.com/login`; `input#password` still visible; text "Please Enter The Valid Password !" visible; no `access_token` in localStorage. Unblocks: yes, expected result observed. Remaining risk: lockout threshold Q1 (use at most one attempt per run).
Variants: AU-02b (empty user id: "Please Enter Mobile No. Or Email Id"), AU-02c (unknown user: "Please Enter The Registered Mobile No. Or Email Id"; use a clearly fake id such as `nosuchuser999@example.com`), AU-02d (empty password: "Please Enter Password"). These do not hit the password check for the real account, so safe to run in the same suite.

### P-AU-03 Session lost -> login (skipped test AU-03: `test_expired_session_redirects_to_login`)
Two executable forms:
A. No session: new context, `goto("/dashboard")` -> expect URL `accounts.premargbooks.com/login` (observed). Also `/sale`.
B. Session state cleared: log in, then `localStorage.removeItem('{"key":"LoggedInUserInfo","session":"mb-session"}')`, `goto("/mstr/usermaster")` -> expect login URL (observed). Removing only `access_token` does not redirect (observed), so do not use it as the "expiry" simulation.
Real server-side expiry (token TTL): UNVERIFIED, Q2. Test AU-03 can be un-skipped for form A/B once the product owner accepts these as the definition.

### P-AU-05 Logout
1. Log in (P-AU-01).
2. Click `#dropdownMenuButton`, then "Logout".
3. Wait for URL.
Expected: `https://accounts.premargbooks.com/login`, no dialog, `localStorage` has no token key. Then `goto("/dashboard")` -> login URL; browser Back stays on login.

### P-AU-07 Not-authorized page
Logged in, `goto("/nosuchpage-xyz")` -> `error-page h1` has text "Oops! You are not authorized.". (Check with product owner whether this is intended for 404; Q10.)

### NEEDS DECISION / do not automate yet
- AU-03c `/user-company` without login renders an empty list (guard gap?).
- AU-08 credentials base64 in the `?c=` query string after login (security).
- AU-09 OTP / PIN / forgot password (SMS/email cannot be read).

## Data needs
- `garments` credentials only. No data created, nothing modified.

## Mapping to skipped tests
| Test | Scenario | Plan | Status |
|---|---|---|---|
| `test_wrong_password_stays_on_login` (AU-02) | AU-02 | P-AU-02 | answerable now |
| `test_expired_session_redirects_to_login` (AU-03) | AU-03/AU-03b | P-AU-03 | answerable for "no session"; true expiry open (Q2) |
| `test_limited_account_is_denied_restricted_pages` (AU-04) | AU-04 | see `roles.md` | blocked on a limited account (Q3) |

## Open questions
Q1 Account lockout / captcha threshold: after how many wrong passwords does the account lock or the captcha appear? Is the lock time-based? (Needed before any repeated wrong-password test.)
Q2 What is the real session lifetime and what should the user see when it expires (redirect, popup)? CODE-A has the time check commented out.
Q9 What is the DOM role/selector of the error toast, so the test can avoid text-only matching?
Q10 Is "Oops! You are not authorized." the intended page for unknown URLs?

## Added 2026-10-07: plans for AU-10 and AU-14 (from KB scenarios; NOT yet explored live)

Status: DRAFT. Steps come from the KB (`scenarios/auth.md` AU-10, AU-14) and existing page objects, not from a live walk-through. Run the planner against the live app before generating tests. Decisions used: D2 (any OTP works in preprod), D9 (role/label/text locators, no `data-testid`), user answers of 2026-10-07 (sign-up allowed with agreed test numbers; garments account logs in with both a mobile number and an e-mail).

### P-AU-10 Login with mobile number or e-mail (same account)
Preconditions: as P-AU-01, plus a second identifier for the same account. Add `QA_GARMENTS_ALT_USER` to `.env.example` (blank); the value goes in `e2e/.env` only. Never log either identifier.
1. New context, open login URL, fill `#userid` with the primary identifier, `#SIGNin`, fill `input#password`, CONTINUE.
2. Expect `https://premargbooks.com/dashboard` and the header company name (same as P-AU-01). Log out (P-AU-05) or use a fresh context.
3. Repeat with the alternate identifier.
Expected: both reach the dashboard with the same company in the header `#dropdownMenuLink`.
Parametrise as one test with two ids ("mobile", "email"); skip the id whose env var is unset, with a reason.
Risk: two real logins per run (login takes ~15 s each). No lockout risk (no wrong attempts).

### P-AU-14 Sign up with mobile and OTP (creates a tenant)
Existing code: `pages/signup_page.py` (`open_form`, `request_otp`, `expect_otp_step_for`, `otp_digit`) and `tests/journeys/auth/test_registration_cases.py` (skipped, upstream flag off).
Preconditions (OPEN, user must supply): agreed test mobile numbers (a reserved range), referral code, whether a used number can be reused, and how the created tenant is removed (D3: `DemoDataRemove` covers demo data, not necessarily a registered account).
1. New context, open the login page, click "Sign Up" (`SignupPage.open_form`). Expect heading "Sign Up".
2. Fill Mobile and Referral Code, click "SEND OTP". Expect the OTP step with the mobile shown in a level-3 heading.
3. Enter any OTP in inputs `otp_0..otp_n` (preprod accepts any, D2), submit. Expect the "Create Company" window (KB).
4. Create the company with a `QA-<run_id>` name; expect landing on the dashboard with that company in the header.
Negative variants (already in `register` cases): short mobile gives a field error; a full-length rejected mobile gives an error toast.
Expected values for steps 3 and 4 are UNVERIFIED (KB only). Do not un-skip until the numbers, the referral code and tenant clean-up are agreed.
Do not run in the PR smoke job: it creates a tenant per run.

### Open questions added
Q11 Which mobile number range and referral code are reserved for QA sign-up? (needed for P-AU-14)
Q12 How is a tenant created by sign-up removed or reused between runs?
Q13 The alternate identifier for the garments account: which env var, and is it a mobile number or an e-mail? (needed for P-AU-10)
