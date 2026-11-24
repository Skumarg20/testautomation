# Test plan: forgot password / reset / registration (J33, `password-reset-registration`)

Status: DRAFT for QA/BA review (2026-10-09). Scenarios: `scenarios/password-reset-registration.md`.
Tests: `tests/journeys/password_reset_registration/` (`test_forgot_password.py`, `test_registration_form.py`, `conftest.py`).
Page objects: `pages/auth/forgot_password_page.py`, `pages/auth/registration_page.py`, `pages/auth/dispatch_guard.py`.
Observed LIVE on the QA login host (`settings.login_url`) on 2026-10-09 with throwaway probes (deleted), logged out.

## Safety design (applies to every test)
- Fresh logged-out context (`page` fixture), never `page_as`.
- `guarded_page` fixture: `DispatchGuard` aborts every request to `RegisterUser/SendSMSInQue`, `PharmaNxt/SendOTP`, `RegisterUser/CheckOTP`, `RegisterUser/ForgotPasswordMail` and fails the test in teardown if one was attempted. No probe or test run hit the guard.
- Identifiers: `nosuchuser999@example.com` (reserved domain), mobile `1000000001` (no Indian mobile starts with 1). The full-length fake mobile is only submitted together with a referral code the app refuses first (the app sends the OTP straight away when there is no referral code, CODE-L `sendOtp()`), so "Send OTP" with a plain valid mobile is never pressed. Enter is never pressed in the mobile field (it also sends the OTP).
- The shared account's user id is typed only on login step 1 (as the auth suite already does) to reach "Forgot Password" on step 2; the recovery form is never submitted for it.

## Screens as seen
Forgot password (`/forgetpasswordNew`, `/forgetpasswordNew/<encrypted id>` from step 2):
heading h3 "Get back into your account"; paragraph "To recover your account,begin by entering your email or mobile"; text "Mobile /Email ID" + unlabeled textbox `#txtEmailId`; textbox "Captcha" (`#txtCapta`, maxlength 4); captcha drawn as 4 spans in `.captcha-box` (plain text in the DOM, e.g. "1 a h 1"), icon link to refresh; link "Go Back"; button "Next" (text renders as "NEXT").
Registration (`/registration`, from login link "Sign Up" `/registration`): marketing panel plus h3 "Create your free account", "Takes 60 seconds. We'll send an OTP to verify your number.", country "+91" (India default), textbox "Enter your mobile number" (`#mobileno`, maxlength 10), icon link "+" with "Have a referral code? (optional)" which reveals textbox placeholder "e.g. JH245G", button "Send OTP & start free", link "Sign in here" (`/login`). The old layout in `pages/signup_page.py` (h1 "Sign Up", "SEND OTP", label "Mobile") is no longer shown.

## Planned and automated
| Test | Scenario | Steps | Expected (seen live unless noted) |
|---|---|---|---|
| test_forgot_password_link_opens_recovery_with_the_user_id_filled_in | FP-01, FP-03 | Login step 1 with the garments user id, click "Forgot Password" on step 2 | URL `/forgetpasswordNew/<param>`, page loaded, Mobile /Email ID holds the typed id. Nothing submitted |
| test_recovery_page_asks_for_id_and_captcha | FP-02 | Open `/forgetpasswordNew` | id field, captcha maxlength 4, "Go Back", 4-character captcha `[0-9a-z]{4}` |
| test_wrong_captcha_is_refused_before_any_account_lookup | FP-04 | Fake id, captcha "zzzz", Next | Warning toast "Wrong captcha number."; stays; no `Loginuser/ValidLoginNew` request |
| test_empty_captcha_is_flagged_on_the_captcha_field | FP-05 | Fake id, empty captcha, Next | Red "!" `#ErrorRef-Captcha`; stays |
| test_unregistered_id_is_refused | FP-06 | Fake id, shown captcha, Next | Toast "Please Enter the Registered Mobile No. or Email Id"; stays |
| test_empty_id_with_right_captcha_shows_no_raw_server_error | FP-05 | Empty id, shown captcha, Next | Expected (derived): the answer toast is not a raw server exception. FAILS: see defect D1 |
| test_captcha_refresh_draws_a_four_character_code | FP-07 | Click refresh icon | Still 4 characters `[0-9a-z]` (a new code is random and may repeat, so sameness is not asserted) |
| test_go_back_returns_to_login | FP-08 | "Go Back" | Login host, user id field visible |
| test_sign_up_link_on_login_opens_registration | RG-01 | Login page, "Sign Up" | `/registration`, h3 heading, "Send OTP & start free", mobile maxlength 10 |
| test_send_otp_without_a_full_mobile_asks_for_a_valid_one[empty, eight-digits] | RG-02, RG-03 | "" or "90810910", Send OTP | "Please enter a valid mobile number"; stays on the mobile step |
| test_mobile_field_drops_letters | RG-04 | Type "abc12" | Value "12" |
| test_mobile_field_stops_at_ten_digits | RG-04 | Type 12 digits (not submitted) | Value is the first 10 |
| test_too_short_referral_code_is_refused | RG-06 | Fake mobile + "AB" | Toast "Kindly enter at least 3 characters."; stays |
| test_three_character_referral_code_passes_the_length_check | RG-06 | Fake mobile + "ABC" | Expected (from the app's own message and `registration.component.ts:1273` `minLength(3)`): code is looked up (`User/GetPartnerDetailsBss`). FAILS: see defect D2 |
| test_unknown_referral_code_is_refused_before_any_otp | RG-05 | Fake mobile + "JFDSJFHS" | `GetPartnerDetailsBss` answers "No data found"; toast "Invalid Referral Code"; stays; no OTP request |
| test_sign_in_link_returns_to_login | RG-01 | "Sign in here" | Login host |

## App defects found
- D1 (FP-05): Forgot password, empty Mobile /Email ID with the correct captcha, Next. Expected: a validation message asking for the id (the field has no required validator, CODE-L `forgetPasswordnew.component.html`). Actual: the client posts an empty user id to `Loginuser/ValidLoginNew` and shows the raw .NET error toast "Object cannot be cast from DBNull to other types."
- D2 (RG-06): Registration, referral code of exactly 3 characters ("ABC") with a valid-format mobile. Expected: passes the length check, as the error text "Kindly enter at least 3 characters." and the TS validator `minLength(3)` say. Actual: refused with that same message; the template's `minlength="4"` attribute (`registration.component.html:533`) wins.

## NEEDS DECISION
- N1 (FP-09, FP-10, FP-11): full reset (mail or OTP, reset link, new password, confirm mismatch, policy). Needs a disposable test user (not the shared super admin) plus a readable mailbox, or an OTP/mail bypass on QA. Until then the reset form is not reachable safely.
- N2 (RG-08, RG-11): full sign-up (OTP, VERIFY OTP, Create Company). Needs an agreed test mobile range or OTP bypass on QA, and a clean-up rule for the created tenant (open since `specs/login.md` P-AU-14 / decision D2/D3). Note: code accepts the last 6 digits of the mobile as OTP for "salesperson" sign-ups (`onOtpChange`), which may be the intended bypass; confirm with the team.
- N3 (RG-09): "mobile already registered" needs a registered number that belongs to no real person.
- N4 (RG-07): non-India country path (e-mail field, temp-mail refusal) not automated; changing the country picker was not probed.
- N5: the captcha is plain text in the DOM and checked only in the browser (CODE-L `CheckCaptcha`), so it does not stop scripted requests. Security review, not a test.
- N6: `pages/signup_page.py` and the skipped `tests/journeys/auth/test_registration_cases.py` target the old sign-up layout; left unchanged per instructions. Its TC_001 "positive" mobile looks like a real number and must not be used.
