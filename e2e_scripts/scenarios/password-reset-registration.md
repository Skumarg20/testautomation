# Scenario pack: forgot password / reset / registration (J33, `password-reset-registration`)

Status: DRAFT for QA/BA review (2026-10-09). Priority P2, layer e2e. Plan: `specs/password-reset-registration.md`.
Builds on `scenarios/auth.md` (AU-09, AU-13, AU-14) and the existing page object `pages/signup_page.py`.

Source keys
- KB = Tech Debt Radar KB chunk (`file#chunk_id(first 8)`).
- CODE-L = margweblogin source (`~/margProject/margweblogin/src/app/`): `forgetpassword/forgetPasswordNew.component.{ts,html}`, `Signup/registration.component.{ts,html}`, `Signin/login.component.ts`, `Globals/global.ts`.
- CODE-B = margbookscoreapi (`MargBooks.RegistrationLogin/Controllers/LoginUserController.cs` `ValidLoginNew`, `margerpdal/LoginDal.cs`).
- LIVE = observed on the QA tenant (filled in by the planner, see the spec).
- UNVERIFIED = not observed and not citable.

Safety frame (task rule, overrides everything below): the `.env` accounts are the shared super admin. No reset, OTP or registration is ever requested for them or for any real person. Tests run in a fresh logged-out context, use only clearly fake identifiers (`@example.com`, numbers starting with `1`, which no Indian mobile uses), and stop before any request that dispatches an OTP, SMS or mail. The OTP/mail endpoints (`RegisterUser/SendSMSInQue`, `PharmaNxt/SendOTP`, `RegisterUser/CheckOTP`, `RegisterUser/ForgotPasswordMail`) are blocked by a route guard in every test as a safety net (CODE-L `global.ts:296-298`, `environment*.ts sendOTP`).

## Forgot password (FP)

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| FP-01 | positive | Step 2 of login shows "Forgot Password?" | Link present on the password step; it navigates to `/forgetpasswordNew/<encrypted user id>` (no server call, nothing sent) | CODE-L `login.component.html:126`, `login.component.ts:865-869`; `specs/login.md` step-2 links |
| FP-02 | positive | Forgot-password page loads | Heading "Get back into your account", text "To recover your account,begin by entering your email or mobile", field "Mobile /Email ID" (`#txtEmailId`), "Captcha" (`#txtCapta`, maxlength 4), a 4-character captcha image made of 4 spans, a refresh icon, "Go Back" link, "Next" button | CODE-L `forgetPasswordnew.component.html` |
| FP-03 | positive | Opened from step 2 of login | The user id typed on step 1 is pre-filled in Mobile /Email ID (decrypted from the route param) | CODE-L `forgetPasswordNew.component.ts:111-130` |
| FP-04 | negative | Wrong captcha, click Next | Warning "Wrong captcha number."; no request to the server; page stays | CODE-L `btnSendClick`, `CheckCaptcha`, `global.ts:18516` |
| FP-05 | negative | Empty Mobile /Email ID, click Next | Field validation message for "EmailId / Mobile" (text UNVERIFIED, read live) | CODE-L `validation-message labelName="EmailId / Mobile "` |
| FP-06 | negative | Unregistered dummy id (`...@example.com`) + correct captcha, click Next | `Loginuser/ValidLoginNew` is a lookup only (no OTP/mail for an unknown user); app shows an error message (text read live) and does not move on | CODE-L `AuthenticateUser`; CODE-B `ValidLoginNew` / `LoginDal.cs:3660-3700` |
| FP-07 | boundary | Captcha refresh | Clicking the refresh icon draws a new 4-character captcha (may repeat by chance) | CODE-L `generatenumber()` |
| FP-08 | positive | "Go Back" | Returns to `/login` | CODE-L `GoBack()` |
| FP-09 | positive | Registered e-mail + captcha + "Get Mail", reset link, new password, "Submit", success, log in | Reset link sent to the registered mail; after reset "password has been reset successfully"; user can log in | KB `careportal_enriched_v5.csv#783c986f`, `#7efea5a8`; API `codekb:MargBooks:api#2f231c3c` (`/RegisterUser/ForgotPasswordMail`), `#aa63d3a2` (`/v1/Auth/resetpwd`). NOT AUTOMATABLE SAFELY: needs a disposable test user plus a readable mailbox or OTP bypass (NEEDS DECISION) |
| FP-10 | negative | Reset form: confirm password differs from new password | "Confirm password does not match with password !" | CODE-L `validatePassword`, `global.ts:18517`. Reachable only after OTP/mail (NEEDS DECISION) |
| FP-11 | boundary | New password length | `maxLength="16"` on `#txtpass`; min length 8 in a commented-out validator (policy UNVERIFIED) | CODE-L `forgetPasswordnew.component.html` |
| FP-12 | negative | Jira/support: reset mail not received | Known complaint class | KB `jira_vectordb.csv#cfeb02d4`, `#a9f9ec2a`; `support_tickets_vectordb.csv#d53bc153` |

## Registration / sign up (RG)

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| RG-01 | positive | "Sign Up" link on the login page opens `/registration` | Heading "Sign Up" (h1) or the new layout "Create your free account" (h3); field Mobile with a country-code picker (India default), "Referral Code?" link, "SEND OTP" button | CODE-L `login.component.html:158`, `registration.component.html:17-183, 399-543` |
| RG-02 | negative | Empty mobile, SEND OTP | "Please enter a valid mobile number"; no OTP request | CODE-L `sendOtp()` `invalidMobile`, `registration.component.html:450-455` |
| RG-03 | negative | Short mobile (8 digits), SEND OTP | Same message; no OTP request | CODE-L validators `minLength(10)`; register case TC_003 |
| RG-04 | boundary | Mobile field for India: maxlength 10, digits only (`appInputMask`, `REGEX.number`) | Typing 12 digits keeps 10; letters are dropped (UNVERIFIED, read live) | CODE-L `maxChar = 10`, `registration.component.ts:244` |
| RG-05 | negative | Valid-format fake mobile + invalid referral code (e.g. "jfdsjfhs") | "Invalid Referral Code" alert; OTP not sent (code checks the referral before sending) | CODE-L `sendOtp()`, `global.ts:18072 InvalidPartnerCode`; register case TC_002 |
| RG-06 | negative | Referral code shorter than 3/4 characters | "kindly enter at least 3 characters." | CODE-L `sendOtp()` |
| RG-07 | negative | Non-India country: e-mail field shown; invalid e-mail | "Please enter a valid email address"; max 50 chars, temp-mail domains refused | CODE-L `registration.component.ts:302-310`; KB `jira_vectordb.csv#747eb7a7` (200-char limit request) |
| RG-08 | positive | Valid new mobile, SEND OTP, OTP, VERIFY OTP, "Create Company" | OTP sent to the mobile; after OTP the Create Company window | KB `careportal_enriched_v5.csv#f1f3c1c5`, `onedrive_processed_data.csv#a9591d87`, `#89a4f6f7`. NOT RUN: dispatches an SMS and creates a tenant (NEEDS DECISION: test number range or OTP bypass, clean-up rule) |
| RG-09 | negative | Mobile already registered | "This Mobile No. is already registered!" / login suggested. NOT RUN: needs a known registered number that is not a real person's (NEEDS DECISION) | CODE-L `checkDublicateUser`; KB `jira_vectordb.csv#f4ef39c1`, `#f6e0f89e` |
| RG-10 | negative | Jira: OTP window opens with no mobile entered | Must not happen (RG-02 covers it) | KB `jira_vectordb.csv#19c49080`, `#ae450e7f` |
| RG-11 | negative | Jira: new sign-up with an unknown number shows "Invalid username / Password" | Must not happen; reachable only after OTP (NEEDS DECISION) | KB `jira_vectordb.csv#fbbd2e61` |

## Planner results (LIVE, 2026-10-09)
- FP-02, FP-04, FP-06, FP-08, RG-01..RG-05 confirmed live; texts in `specs/password-reset-registration.md`.
- FP-05: the id field has no client validation; empty id + right captcha shows the raw server error "Object cannot be cast from DBNull to other types." (defect D1).
- RG-06: a 3-character referral code is refused with "Kindly enter at least 3 characters." (defect D2; template `minlength="4"`).
- FP-09/10/11, RG-07/08/09/11 stay NEEDS DECISION (they dispatch an OTP/mail or need a known registered number).
