# Scenario pack: J39 ABHA / health flows (abha-health-flows)

Journey: `abha-health-flows` (J39, P3, layer e2e, phase2, status not_started; `coverage/journey-matrix.json:623`). No plan or tests yet.
Analyst pass 2026-10-12.

**Source note.** The Tech Debt Radar MCP server (`search_kb`, `ask_codebase`) failed to connect when this pack was first written, so it was drafted from local KB source files. **KB chunk citations were backfilled on 2026-10-12 via `search_kb`**: each `file#slide/row` citation now has the matching chunk next to it as `<file>#<chunk id prefix>` (the L&D decks are indexed as `onedrive_processed_data.csv`). Original sourcing:
- KB content was read from the local copies the KB is built from, under `~/Downloads/TechRadarData/`. These are cited as `file#row-key`, where the row key is a Jira key, a support id or a slide number.
- Code is cited as `file:line`:
  - UI paths are relative to `newmarg-webangular20/src/app/` and are shortened to `ui:`.
  - API paths are relative to `margbookscoreapi/` and are shortened to `api:`.
- The 2026-10-12 re-run also checked the care-portal and code-kb cards. The care portal still has **no** ABHA article; the nearest is "How to Add Government ID of Patient" (`careportal_enriched_v5.csv#c917710e`), see "KB vs live app" item 9.

Safety classes used below:
- **a**: UI-only safe. The test makes no ABDM/gateway call with identity data. The test stops before any "Send OTP", consent-OK or enrol call.
- **b**: Needs an ABDM sandbox or a mocked `abdm.*` proxy, for example Playwright `route()` on `abdmAbhaBaseUrl`. Never use real Aadhaar or ABHA identities.
- **c**: Manual only. This covers real-person OTPs, government portals (HFR/NHPR, DHIS, e-sign) and the patient's PHR app.

Test data rule: use only obviously fake values. Examples are ABHA no. `00-0000-0000-0000`, Aadhaar `0000 0000 0000`, address `qa_test01`, mobile `0000000000`. Never paste the facility or pharmacy ID shown on the L&D slides, and never paste the connector URL token from the source.

## Account context
- The ABHA UI is shown only when **both** of these hold:
  - The selected company has `bustype == 5`. This is `chemist` (`ui:Globals/global.ts:18854`).
  - Control Room field 4426, "Abha Id for pharmacy store", is non-empty (`ui:Services/Helper.services.ts:3043`, `ui:Component/Transaction/InverntoryTransaction/processout.transaction.component.ts:19926-19933`, `ui:Component/Chemist/Patient/patientmaster.component.ts:339-350`).
- Pharma distributor (13) and pharma manufacturing (14) (`ui:Globals/global.ts:18862-18863`) do **not** get the ABHA button, column or fields. **A chemist account is needed.** The suite has none today: `QA_CHEMIST_USER` is "not provided; tests skip" (`e2e/docs/environment.md:21`).
- The Digital > ABHA menu child (menu value 92385071029) is also gated on profile field 4426 (`ui:Services/Common.service.ts:1212-1216`). The Digital parent (92385071021) is hidden when it has no children (`ui:Layout/menu.component.ts:1896-1903`). This is Jira MBC-806, "Hide Digital Menu When ... ABHA Settings Are Off" (`Jira (1).csv#MBC-806`, `jira_vectordb.csv#4f67fc1f`, Live).

## What the KB says ABHA is
- **ABHA number and address.** The ABHA number is a 14-digit random identifier (sample format `0000-1111-2222-33`). The ABHA address is a user-created alias in the format `name@abdm`. Each ABHA has at least one address; if there are several, one is preferred (`1 Introduction to ABDM.pptx#slide5`, `#slide6`; `onedrive_processed_data.csv#67c19ed4` sample card; an L&D billing screenshot shows a live address ending `@abdm`, `onedrive_processed_data.csv#0794d68f`).
- **Facility setup.** The chemist first registers the facility on HFR/NHPR (government portal, Aadhaar plus OTP, e-sign) (`ABHA_Presentation.pptx#slide2-21`; `onedrive_processed_data.csv#72837ae8`, `#8e9cfb3d`, `#c5a3c0bd`). Software linkage uses bridge `MEL_001`, then "Register HIP" (`3 Software Linkage.pptx#slide4-5`; `onedrive_processed_data.csv#469a5d9d`). The HFR ID is then entered at Control Room > search "ABHA" and verified with an OTP sent to the Marg-registered number (`4 Configuration & Invoicing.pptx#slide4`; `onedrive_processed_data.csv#4c8bbbb9`). An HFR wallet with a balance of 2000 is required ("Insufficient Balance" otherwise) (`4 Configuration & Invoicing.pptx#slide3`, `#slide5`; `onedrive_processed_data.csv#4c8bbbb9`).
- **Patient registration.** The flow is:
  1. Enter the Aadhaar number.
  2. Name plus "I Agree" (consent).
  3. OTP on the Aadhaar-linked mobile.
  4. Correspondence mobile.
  5. Choose or type an ABHA address.
  6. Card download, or send on WhatsApp.

  Sources: `5 Billing.pptx#slide6-9`, `ABHA.pptx#slide3` (`onedrive_processed_data.csv#d0b24616`, `#b06490fb`, `#3d38377b`, `#fe284fea`). The workflow is Registration > Operator Approval > Customer OTP Verification > ABHA Search and Download (`ABHA IN MARGBOOKS/screen.docx`; `onedrive_processed_data.csv#5c8b2b1a`).
- **ABHA button in the sale bill.**
  - The button is red when the patient is unregistered and green when an ABHA is linked (`5 Billing.pptx#slide5`, `#slide23`, `#slide33`; `ABHA_Presentation.pptx#slide25`, `#slide35`; `onedrive_processed_data.csv#a1579188` "ABHA Green", `#c4686fe5`).
  - It opens 4 options: Select ABHA ID/Address, Patient History, Patient Registration and Download ABHA Card (`5 Billing.pptx#slide31`; `ABHA_Presentation.pptx#slide26`; `onedrive_processed_data.csv#88b246ec`, `#0794d68f`).
  - A patient mobile number with several ABHAs opens a selection window (`ABHA.pptx#slide9`; `onedrive_processed_data.csv#478acdd9`).
- **Card download.** The card can be downloaded by mobile, ABHA number or ABHA address (`ABHA.pptx#slide5`; `onedrive_processed_data.csv#59198d48`).
- **Patient history.** Search the ABHA address, then "New Consent Request" > Next > "Request Consent"; the patient approves in the PHR app (`6 Patient History.pptx#slide3-4`; `ABHA.pptx#slide7`; `onedrive_processed_data.csv#80bec3bc`, `#06ace516`, `#d3727bde`).
- **Printing and upload.** The bill print shows the ABHA number and address. The Chemist Shop (BB) format has the command built in (`4 Configuration & Invoicing.pptx#slide3`; `5 Billing.pptx#slide14`; `onedrive_processed_data.csv#4c8bbbb9`, `#a1579188`). ABHA bills are uploaded from Digital > ABHA > Upload ABHA Bills > Pending/Bulk, and an Incentive Claim is available (`5 Billing.pptx#slide35-36`; `ABHA_Presentation.pptx#slide45`, `#slide49`; `onedrive_processed_data.csv#17339c14`).
- **Desktop vs web.** The L&D decks describe **Marg ERP (desktop)** screens ("digital entry", "Control Room", "Press F"). How far they apply to the MargBooks web app is unverified; see "KB vs live app".

## Code map (web app)
| What | Where |
|---|---|
| Routes `/abha/patient/registration`, `/abha/patient/card/download` (consent route commented out) | `ui:Modules/abha.module.ts:24-28`, lazy under authed shell `ui:app-routing.module.ts:52-56,163`; `codekb:MargBooks:screen#4c107aad`, `#bfc404ed` |
| Patient master `/chemist/patient`, prescriptions `/chemist/prescription`, `/chemist/prescription-create` | `ui:Modules/chemist.module.ts:26-29` |
| Registration screen: title "Ayushman Bharat Health Account", sub-heading "ABHA Registration" | `ui:Component/abha/patient-registration/abha-patient-registration.component.html:5,13` |
| Download screen: heading "Download ABHA Card", radios `downloadtype` = `mobileNo`/`aadhaar`/`abhaNo`/`abhaAddress` | `ui:Component/abha/patient-abha-card-download/abha-patient-card-download.html:14,21-45` |
| Sale bill ABHA button `#btnAbha<tabId>`, red when `abhaStatus==0` | `ui:UI/Transaction/InverntoryTransaction/processout.transaction.component.html:1188-1191` |
| ABHA Selection popup (4 options, "Select ABHA Address" / "Change ABHA Address ") | `ui:Component/abha/abha-selection/abha-selection-component.html:5,19-55`, `.ts:64`; `codekb:MargBooks:screen#7b896b35` |
| "Select Billing for Abha Number" popup, data from `GET MedicalPrescription/GetPatientAbhaDetails` | `ui:Component/abha/abha-selection-details/abha-selection-details.component.html:2`, `.ts:23-31`, `ui:Globals/global.ts:985-986`; `codekb:MargBooks:screen#e693fa68`, `codekb:MargBooks:api#47d5b5ce` |
| Patient grid column "Abha Status" ("Active", green #169162) | `ui:Component/Chemist/Patient/patientmaster.component.ts:329`, `ui:Component/Shared/template-abha-text-color.ts:5-18` |
| Add patient: labels "Govt Abha Id" / "Govt Abha Address" (read-only), button "Save & Check Abha Id" (F2) | `ui:UI/Chemist/Patient/add.patient.component.html:106-121,600-603`, `ui:assets/i18n/en.json:951-952` |
| API: tenancy-scoped read of `PatientAbhaDetails` (`complinkid` + `patientlinkid` + `isdelete=0`) | `api:margerpdal/MedicalPrescripton.cs:1558-1573`; table `codekb:MargBooks:schema#6a77229e` |
| API: `SaveAbhadetails` (rate limit 15/s; requires ActionType, complinkid, userlinkid, username) | `api:MargBooks.SalePurchaseMastersAPI/Controllers/MedicalPrescriptionController.cs:626-635`, `api:margerpbll/MedicalPrescription.cs:518-530`; `codekb:MargBooks:api#130b75f4`, `codekb:MargBooks:code#f9c9c925`, `#21e4fc29` |
| ABDM proxy (`abdmAbhaBaseUrl`, pre-prod `https://abdm.premargbooks.com/`): Enrollment m1 OTP/enrol/suggestion/abha-address/abhacard; AbhaGateway GetSessionToken; AbhaInvoice InvoiceDataSave, PatientScanShare, getPatientdata | `ui:../environments/environment.prod.ts:57`; `api:MargBooks.Abdm.Api/Controllers/EnrollmentController.cs:38-116`, `AbhaGatewayController.cs:31-145`, `AbhaInvoiceController.cs:30-77`; `codekb:MargBooks:api#f875cf2c`, `#abaa31b3`, `#d144cf78`, `#b9b7041b`, `#c04a58be`, `#5c2657e7`, `#074c5635` |

## Known defects and findings (bugs cluster here)
- **MBC-2139** "Hide Abha button from sale bill", Live (`Jira (1).csv#MBC-2139`, `jira_vectordb.csv#1a6e4f5d`). The button now renders only under the chemist + 4426 condition.
- **MBC-806** Digital menu is hidden when there is no submenu or the ABHA setting is off, Live (`Jira (1).csv#MBC-806`, `jira_vectordb.csv#4f67fc1f`).
- **No ABHA support tickets in the KB.** Confirmed by the 2026-10-12 `search_kb` re-run ("ABHA issue ticket" returns only unrelated ticket clusters). The local `support_tickets_vectordb.csv` hits are "ABHA GUGGUL" (an item name), "Arogya Bharti" and "Prabha" (party names), so they are not ABHA defects.
- **Code findings, not filed. A human decides.**
  1. **Patient History does nothing in the sale bill.** The sale bill's `patientHistroy()` is empty (`processout.transaction.component.ts:19781-19783`). The selection popup itself opens an external `abhaconnector.margerp.com/consents?...&token=...` URL in a new tab (`abha-selection-component.ts:71-75`, also `Layout/menu.component.ts:1302-1305`). The institute and token are **hard-coded in client JS**, and this is a secret-exposure risk. The value is not reproduced here.
  2. **ABHA address suffix is `@sbx` (ABDM sandbox) in production code paths.** The download screen sends `loginId = address + "@sbx"` (`abha-patient-card-download.ts:359`), and the input groups show `@sbx` (`abha-address.component.html:27`, `abha-patient-card-download.html:141,380`). The KB says live addresses are `name@abdm` (`1 Introduction to ABDM.pptx#slide6`).
  3. **Client-side captcha.** The captcha is generated in the browser, and its characters are rendered as 4 `<span>` elements (`abha-patient-registration.component.html:98-110`; `generatenumber()` at `.ts:87-99`). `CheckCaptcha()` strips spaces, but `submitOtp()` compares the raw value (`.ts:101-106` vs `.ts:222`).
  4. **Mobile-mode OTP is sent without a mobile-number check.** The mobile is only checked for non-empty before the OTP request (`abha-patient-card-download.ts:516-527`, `251-262`); there is no 10-digit check.
  5. **The resend counter drops on a failed attempt.** `sendOtpNew()` decrements `resendOtpCount` before it validates, so a failed validation still uses up a resend (`abha-patient-card-download.ts:512-513`).
  6. **F2 is wired to "Save & Check Abha Id" without the ABHA-configured check.** On add patient, F2 calls `saveData("abha")` for any chemist with Add right (`add.patient.component.ts:913-916`). The button itself is also gated on 4426 (`add.patient.component.html:600`). So F2 may open the ABHA download popup when ABHA is not configured. UNVERIFIED live.
  7. **`SaveAbhadetails` may trust `complinkid` from the body.** It takes `complinkid` from the request body; only `DBInfolinkid` is set from the header (`MedicalPrescriptionController.cs:631-635`). This is a tenancy risk. UNVERIFIED whether `GetHeaderData`/`BaseEntity` binding overrides it.
  8. **`[Authorize]` is commented out on the ABDM API base controller** (handlers: `codekb:MargBooks:api#5c2657e7`, `#074c5635`). It is commented out at `AbhaMargBaseController.cs:12`, and the ABDM controllers carry no `[Authorize]` attribute. `getPatientdata(type, healthId)` and `GetSessionToken` may be callable unauthenticated. UNVERIFIED (gateway or infra auth may exist).

## Scenarios
Type key: P positive, N negative, B boundary, R role/permission, T tenancy, S state, O output.

| ID | Type | Scenario | Expected result | Source | Class |
|---|---|---|---|---|---|
| AB-01 | R | Chemist company with field 4426 set: open sale bill | ABHA button `#btnAbha<tabId>` is visible; red (`red-btn`) for a patient with no ABHA | `processout...html:1188-1191`; `5 Billing.pptx#slide5`; `onedrive_processed_data.csv#a1579188` | a |
| AB-02 | R | Chemist company with 4426 blank: open sale bill, patient master, add patient | No ABHA button, no "Abha Status" column, no "Govt Abha Id/Address" rows, no "Save & Check Abha Id" button | `processout...ts:19926-19933`; `patientmaster.component.ts:339-344`; `add.patient.component.html:106,115,600`; MBC-2139 (`jira_vectordb.csv#1a6e4f5d`) | a |
| AB-03 | R | Pharma distributor (bustype 13) or retail/grocery company | No ABHA UI anywhere; Digital > ABHA menu child absent | `global.ts:18854,18862`; `Common.service.ts:1212-1216` | a (needs that trade login) |
| AB-04 | R | Digital menu when ABHA setting is off and Digital has no other child | Digital parent menu hidden | `menu.component.ts:1896-1903`; `Jira (1).csv#MBC-806`; `jira_vectordb.csv#4f67fc1f` | a |
| AB-05 | R | Direct URL `/abha/patient/registration` as a non-chemist / 4426-off user | Expected: refused or redirected. Code shows only `Authgaurd` (login) on the shell, no business-type guard, so the screen probably opens. UNVERIFIED | `app-routing.module.ts:52-56,163`; `abha.module.ts:24-26` | a |
| AB-06 | P | Open `/abha/patient/registration` (chemist) | Header "Ayushman Bharat Health Account", sub-heading "ABHA Registration", Aadhaar Number* in 3 masked 4-digit boxes, link "Download ABHA Card if already registered" | `abha-patient-registration.component.html:5,13,17,21-43,128-131`; `codekb:MargBooks:screen#4c107aad` | a (note: init calls `AbhaGateway/GetSessionToken`, no PII; `.ts:80-82,468`) |
| AB-07 | N | Registration: press Submit with Aadhaar boxes empty | Warning "Please Enter Valid Aadhaar Number", focus on first invalid box | `abha-patient-registration.component.ts:72-74,204-206,227-231` | a |
| AB-08 | B | Registration: type letters / 5th digit in an Aadhaar box | Integer mask rejects letters; maxlength 4 per box; focus auto-advances after 4 digits | `abha-patient-registration.component.html:21,30,39`; `.ts:121-130` | a |
| AB-09 | P | Registration: show/hide toggle on Aadhaar | Eye icon switches input type between password and text (Aadhaar masked by default) | `abha-patient-registration.component.html:21,46-58` (`[type]="Ispassword"`) | a |
| AB-10 | P | Fill 12 fake digits: consent popup opens | Consent modal with 7 checkboxes (all pre-ticked) and "I, [name]" field | `abha-patient-registration.component.ts:131-148`; `abha-patient-consent.component.ts:44-50`, `.html:17-66`; `5 Billing.pptx#slide6`; `onedrive_processed_data.csv#fe284fea`; `codekb:MargBooks:screen#9799eb48` | a (close the modal; do NOT confirm) |
| AB-11 | N | Consent popup: untick any checkbox, confirm | Warning "Please read and tick all the terms and conditions"; modal stays open | `abha-patient-consent.component.ts:62-65,78`; `global.ts:21279` | a |
| AB-12 | N | Consent popup: all ticked, blank name, confirm | Warning "Please enter your full name as per Aadhar card"; focus on name | `abha-patient-consent.component.ts:66-69,78-80`; `global.ts:21280` | a |
| AB-13 | P | Consent popup: Close | Modal closes with status false; no OTP request sent (verify no request to `api/Enrollment/m1/request/otp`) | `abha-patient-consent.component.ts:57-59`; `abha-patient-registration.component.ts:144-148` | a |
| AB-14 | N | Consent confirmed with a fake Aadhaar | Gateway refuses; UI warns "Invaild Aadhaar No." (sic) or the gateway message | `abha-patient-registration.component.ts:149-171`; `codekb:MargBooks:api#f875cf2c` | b (mock `abdmAbhaBaseUrl`) |
| AB-15 | N | After OTP sent: Submit with empty Correspondence Mobile / OTP / Captcha | Warnings in order "Please Enter Valid Corresponding Mobile Number", "Please Enter Received OTP", "Please Enter CAPTCHA" | `abha-patient-registration.component.ts:207-217,440-447` | b |
| AB-16 | N | After OTP sent: wrong captcha | "Invalid CAPTCHA", focus on captcha; captcha refresh icon regenerates 4 chars | `abha-patient-registration.component.ts:222-225`; `.html:87-117` | b |
| AB-17 | B | OTP field and resend | OTP maxlength 6, integer; "Resend OTP" with countdown, "Upto N times"; note "This mobile number will be used for all the communications related to ABHA" | `abha-patient-registration.component.html:68,77,81-85,133-136`; `5 Billing.pptx#slide7-8`; `onedrive_processed_data.csv#d0b24616` | b |
| AB-18 | P | Full enrolment: Aadhaar > consent > OTP > mobile > choose ABHA address > card | ABHA created with chosen address; "ABHA Address Successfully Created"; card downloadable / WhatsApp | `abha-address.component.ts:81-100`; `5 Billing.pptx#slide6-9`; `onedrive_processed_data.csv#d0b24616`, `#b06490fb`; `codekb:MargBooks:api#abaa31b3`, `#d144cf78` | c (real identity) / b in sandbox |
| AB-19 | B | ABHA address rule (create-address popup) | Accepts 8-18 chars, letters/digits with exactly one `.` or `_` not at start/end (e.g. `qa_test01`); input strips other chars; else "ABHA Address Not Valid" | `abha-address.component.ts:53-67,108-110`; `codekb:MargBooks:screen#2a6043a4` | b (popup only reachable after enrolment) |
| AB-20 | N | ABHA address already taken | Warning "This ABHA Address already exists. Please create with unique ABHA address" | `abha-address.component.ts:89-91`; `global.ts:21278` | b |
| AB-21 | P | Open `/abha/patient/card/download` | Heading "Download ABHA Card"; radios Mobile / Aadhaar / ABHA No. / ABHA Address; Mobile selected by default; Captcha* | `abha-patient-card-download.html:14,21-45,149`; `.ts:84`; `codekb:MargBooks:screen#bfc404ed`; `onedrive_processed_data.csv#59198d48` | a |
| AB-22 | N | Download, Mobile mode: Send OTP with empty mobile | "Please  Enter Mobile No." (double space in source) | `abha-patient-card-download.ts:516-518` | a |
| AB-23 | N | Download, ABHA No. mode: Send OTP with a part empty | "Please Enter Full ABHA Number" (or "Please Enter ABHA Number" on resend path), focus on first empty part; parts 2/4/4/4 digits | `abha-patient-card-download.ts:305-321,537`; `.html:110-128` | a |
| AB-24 | N | Download, ABHA Address / Aadhaar mode empty | "Please Enter ABHA Address" / "Please Enter Aadhaar No." with focus | `abha-patient-card-download.ts:345-348,545-555` | a |
| AB-25 | N | Download: field filled, captcha empty then wrong | "Please Enter CAPTCHA" then "Invalid CAPTCHA", focus on captcha; no OTP request sent | `abha-patient-card-download.ts:323-327,519-523,575-580` | a (fake values; assert no network call) |
| AB-26 | N | Download: OTP submit with empty OTP | "Please Enter Received OTP" | `abha-patient-card-download.ts:584-596` | b (OTP panel shows only after send) |
| AB-27 | N | Download: unregistered ABHA address / Aadhaar | "Invalid ABHA Address Or ABHA Address Not Register" / "Invalid Aadhaar Number Or Aadhaar Number Not Register" | `abha-patient-card-download.ts:379,500-510`; `codekb:MargBooks:api#34082b68`, `#c04a58be` | b |
| AB-28 | P | Close/x on standalone screens | Navigates to `/dashboard` | `abha-patient-registration.component.ts:113-119`; `abha-patient-card-download.ts:127-133` | a |
| AB-29 | P | Patient master grid (chemist + 4426) | Column "Abha Status" shows "Active" (green) for patients with `IsAbhaStatus` true, blank otherwise | `patientmaster.component.ts:329`; `template-abha-text-color.ts:13-18`; `ABHA_Presentation.pptx#slide32,41` | a (reading existing rows) |
| AB-30 | P | Add patient (chemist + 4426) | Read-only rows "Govt Abha Id", "Govt Abha Address"; button "Save & Check Abha Id" (F2) | `add.patient.component.html:106-121,600-603`; `ABHA_Presentation.pptx#slide31`; `onedrive_processed_data.csv#c4686fe5` ("Save & Check ABHA Address") | a |
| AB-31 | S | "Save & Check Abha Id" with a fake patient | Patient saved (ActionType A) and Download ABHA Card popup opens prefilled with patient mobile; closing popup leaves patient saved, Abha Status not Active | `add.patient.component.ts:648-666,693-701`; `abha-patient-card-download.ts:82-85`; `onedrive_processed_data.csv#c4686fe5` | a (stop before Send OTP; creates test data) |
| AB-32 | P | Sale bill ABHA button > selection popup | "ABHA Selection" with 4 options; first reads "Select ABHA Address" (red) or "Change ABHA Address" (green) | `abha-selection-component.html:5,19-55`; `.ts:64`; `5 Billing.pptx#slide31`; `onedrive_processed_data.csv#0794d68f`; `codekb:MargBooks:screen#7b896b35` | a |
| AB-33 | P | Select ABHA Address for a patient with linked ABHA rows | "Select Billing for Abha Number" lists rows from `GetPatientAbhaDetails`; picking one turns button green (`abhaStatus=1`) | `abha-selection-details.component.ts:23-38`; `processout...ts:19767-19778`; `ABHA_Presentation.pptx#slide34-35`; `onedrive_processed_data.csv#0794d68f` ("SELECT BILLING FOR ABHA NUMBER"); `codekb:MargBooks:screen#e693fa68` | b (needs a patient with seeded `PatientAbhaDetails`, fake values via `SaveAbhadetails`) |
| AB-34 | O | Save and print a bill with ABHA selected | Bill stores patient ABHA link (`patientAbhalinkid`, `abhano`, `abhaaddress`); reopening shows green; print preview shows ABHA no. and address | `api:margerpmodel/Bill_SalePurchase.cs:1424-1427`; `processout...ts:4486-4488`; `5 Billing.pptx#slide14`; `4 Configuration & Invoicing.pptx#slide3`; `onedrive_processed_data.csv#a1579188`, `#4c8bbbb9` | b |
| AB-35 | N | Patient History option from sale bill | KB: consent request flow. Code: opens external connector tab; sale-bill handler empty. Expected behaviour UNVERIFIED | `abha-selection-component.ts:71-75`; `processout...ts:19781-19783`; `6 Patient History.pptx#slide3-4`; `onedrive_processed_data.csv#80bec3bc`, `#06ace516` | c |
| AB-36 | T | `GetPatientAbhaDetails` with a patient linkid of company B while logged into company A | Empty result (query filtered by header `complinkid`) | `api:margerpdal/MedicalPrescripton.cs:1568-1570`; `codekb:MargBooks:api#47d5b5ce` | a (API-level, no ABDM) |
| AB-37 | T | `SaveAbhadetails` with body `complinkid` of another company | Must be refused or overridden by session company. UNVERIFIED (see finding 7) | `api:...MedicalPrescriptionController.cs:631-635`; `api:margerpbll/MedicalPrescription.cs:524`; `codekb:MargBooks:api#130b75f4` | a (API-level; fake ABHA values) |
| AB-38 | N | `SaveAbhadetails` missing ActionType / username | Business-rule error (no-data / action-type / username required) | `api:margerpbll/MedicalPrescription.cs:520-529`; `codekb:MargBooks:code#f9c9c925` | a |
| AB-39 | P | Upload ABHA bills (Pending / Bulk with date range), Incentive Claim, HFR/DHIS registration, software linkage | Per L&D decks | `5 Billing.pptx#slide35-36`; `7 DHIS.pptx`; `2 HFR Registration.pptx`; `3 Software Linkage.pptx` (`onedrive_processed_data.csv#17339c14`, `#0aebb069`, `#72837ae8`, `#469a5d9d`). Web screen not found in UI source: UNVERIFIED | c |

Not covered: Dates, GST slabs and duplicates from the checklist do not apply to ABHA screens. Bill-level GST is owned by `chemist-sale-bill`. Prescription CRUD (`/chemist/prescription*`) has no ABHA-specific logic in the source read; leave it to a prescription journey.

## Navigation, selectors, messages (quick reference)
- **Menu:**
  - Digital > ABHA (Ayushman Bharat): menu ids 92385071021 (Digital) and 92385071029 (ABHA). Child labels are server-driven, so they are UNVERIFIED.
  - Patient master: Master > Patient, route `/chemist/patient`, chemist only (`Common.service.ts:749`).
- **Routes:** `/abha/patient/registration`, `/abha/patient/card/download`, `/chemist/patient`, `/chemist/prescription`, `/chemist/prescription-create`.
- **Selectors:**
  - Sale-bill button: `#btnAbha<tabId>`, class `red-btn` / `blue-btn`.
  - Captcha input: `#txtCapta` (registration).
  - Download-mode radios: `input[name=downloadtype][value=mobileNo|aadhaar|abhaNo|abhaAddress]`.
  - Selection popup close: `#No`.
  - Add-patient save: `#btn-Save` (the ABHA button reuses this id; `add.patient.component.html:601`).
- **Messages:**
  - `AbhaEnum` (`global.ts:21272-21281`): "Invalid OTP Value", "Invalid Mobile Number", "Invalid LoginId", "This account already exist", "Invalid Abha Address", "This ABHA Address already exists. Please create with unique ABHA address", "Please read and tick all the terms and conditions", "Please enter your full name as per Aadhar card".
  - Inline: "ABHA Address Not Valid", "ABHA Address Successfully Created", "Not save" (`abha-address.component.ts:94,109,133`).
- **Network to mock for class b:** everything under `abdmAbhaBaseUrl`:
  - `api/AbhaGateway/GetSessionToken`
  - `api/Enrollment/m1/request/otp`, `m1/enrol/byAadhaarVerfication`, `m1/enrollment/enrol/suggestion`, `m1/enrol/abha-address`
  - `m1/profile/login/request/{abhanumberLoginviaabhaotp|AbhaAddressLoginViaAbhaOtp}`, `m1/profile/login/{abhanumberLoginverify|AbhaAddressLoginVerifyOtp}`
  - `m1/account/{abhacard|AbhaCardViaAbhaAddress}`

## KB vs live app
1. **Desktop vs web.** The L&D decks are Marg ERP desktop: Control Room > search ABHA plus Ctrl+W, "Press F" for print preview, and "digital entry". The web app uses Control Room profile field 4426 and the routes above. Whether HFR ID entry with OTP verification exists in the web Control Room is UNVERIFIED.
2. **`@sbx` vs `@abdm`.** The KB says addresses are `name@abdm`. The web code hard-codes the sandbox suffix `@sbx`. Either production is pointed at the ABDM sandbox, or download-by-address cannot work for real users.
3. **Patient History.** The KB describes an in-app flow (search address > New Consent Request > Request Consent). The web app opens an external connector URL with a fixed token, and the sale-bill handler is empty. The `/abha/consent` route is commented out (`abha.module.ts:27`).
4. **Upload ABHA Bills, Incentive Claim, DHIS.** These are in the KB (Digital > ABHA > Upload ABHA Bills > Pending/Bulk) but no web component was found under `Component/abha/`. They may be server-driven menus pointing elsewhere: UNVERIFIED.
5. **ABHA selection by mobile.** The KB says entering the patient mobile auto-retrieves ABHA, and several ABHAs open a selection window (`ABHA.pptx#slide9`). The web app instead lists `PatientAbhaDetails` rows by patient linkid on demand.
6. **ABHA address rule.** The client requires exactly one `.` or `_`. The KB example `name@abdm` and ABDM's own rule allow addresses without a separator. The client may reject valid addresses.
7. **Care portal.** Re-checked with `search_kb` on 2026-10-12: still no ABHA article. The code-kb cards were checked and are cited in the code map.
8. **Operator Approval.** The workflow in `screen.docx` (`onedrive_processed_data.csv#5c8b2b1a`) has an "Operator Approval" step. Nothing in the web source maps to it: UNVERIFIED.
9. **Patient "Government ID" (KB-only).** The care portal documents Master > Other Master > Patient > F3 'Modify Patient' > 'Government ID' (`careportal_enriched_v5.csv#c917710e`). The code shows read-only "Govt Abha Id" / "Govt Abha Address" rows on add patient (AB-30). Whether the article's editable 'Government ID' field is the same field is UNVERIFIED; AB-30's expected value is unchanged.
10. **Consent route: code-kb vs source.** The code-kb card lists `AbhaPatientConsentComponent` with route `/consent` (`codekb:MargBooks:screen#9799eb48`), while the source read for this pack has that route commented out (`abha.module.ts:27`). The card may be built from an older revision; check the live URL before relying on either.
11. **`@abdm` confirmed in L&D screenshots.** A billing screenshot in the decks shows a patient ABHA address ending `@abdm` (`onedrive_processed_data.csv#0794d68f`), which supports item 2: the web code's `@sbx` suffix is the sandbox one.
