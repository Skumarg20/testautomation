# Plan: J39 ABHA / health flows (abha-health-flows)

Scenario pack: `scenarios/abha-health-flows.md`. Tests: `tests/journeys/abha/` (`conftest.py`, `test_registration.py`, `test_consent.py`, `test_registration_otp_stubbed.py`, `test_enrolment_stubbed.py`, `test_card_download.py`, `test_card_download_stubbed.py`, `test_sale_bill_abha.py`, `test_sale_bill_abha_link.py`, `test_patient_master.py`, `test_patient_abha_status.py`, `test_digital_menu.py`, `test_direct_url.py`) and `tests/api/abha/` (`conftest.py`, `test_patient_abha_details_api.py`). Page objects: `pages/abha/` (`abdm_endpoints.py`, `abha_setup.py`, `captcha.py`, `consent_dialog.py`, `registration_page.py`, `address_popup.py`, `card_download_page.py`, `sale_bill_abha.py`, `billing_details.py`, `bill_abha_link.py`, `cash_bill_draft.py`, `consent_connector.py`, `patient_master.py`, `patient_abha_status.py`, `digital_menu.py`, `app_api.py`, `messages.py`). Test data: `test_data/abha.py`. Offline checks: `tests/framework/test_abha_safety.py`.

**Status: DRAFT — locators from Angular source, NOT yet verified live.** Written offline on 2026-10-13 with no login: no browser was opened and no test reached the app. Every locator and text comes from `newmarg-webangular20/src/app/` (cited `file:line`, paths relative to that folder) and must be checked by the healer on the first live run (see "To verify live").

Priority marker: `pytest.mark.p3` (J39 is P3 in the matrix; `p3` is registered in `pyproject.toml`). Every module also has `pytest.mark.journey("abha-health-flows")`.

## Safety
- **Guard.** Every test's page is armed, before its first navigation, with the shared `SendGuard` (`pages/components/send_guard.py`, from the J41 work) set to `ABDM_OR_ABHA_WRITE` (`pages/abha/abdm_endpoints.py`): anything to `//abdm.` (the `abdmAbhaBaseUrl` host, `environments/environment.prod.ts:57`), `//localhost:5020/` (dev build), `/api/AbhaGateway/`, `/api/Enrollment/`, `/api/AbhaInvoice/`, `abhaconnector` (the consent site the selection popup opens) and `MedicalPrescription/SaveAbhadetails`. The call is aborted and the test fails in teardown. Contexts block the service worker (root `conftest.py`), so routes see every call.
- **Stubs.** `StubbedEndpoint` (`pages/components/stubbed_endpoint.py`) is a page route and wins over the guard's context route. Replies are the smallest bodies the code reads, with fake values (`abdm_endpoints.py`, each with `file:line`):
  - `AbhaGateway/GetSessionToken`: answered for every test before the first navigation. The two screen fixtures open the screen through `capture_one`, which proves the stub answered (not the server, not a service worker) before the test types anything.
  - `Enrollment/m1/request/otp` (registration), `.../login/request/abhanumberLoginviaabhaotp` and `.../AbhaAddressLoginViaAbhaOtp` (card download): answered only in the class-b tests, each proven with `capture_one` on the action that calls it. In the validation tests these endpoints are not stubbed, and `expect_none_during` proves the refused action made no call at all.
  - Enrolment (`byAadhaarVerfication`), suggestion, abha-address and `account/abhacard`: answered only in `test_enrolment_stubbed.py`, each proven with `capture_one` (the refused-address tests prove no call with `expect_none_during`).
  - Consent connector: answered only in the AB-35 tests by a context stub registered after the guard (`pages/abha/consent_connector.py`); its URL (it carries a token) is never returned, logged or asserted on in text.
  - MargBooks reads/writes, not ABDM: `GetPatientAbhaDetails` stubbed (AB-33/34), `GetPatientList` and `BillSales/Get` passed through and patched (AB-29, AB-34 reopen), `BillSales/Save` of an ABHA-linked bill answered by a refusing stub (AB-34).
  - Never stubbed, so always aborted in the browser: OTP verify, card download by mobile/number/address, AbhaInvoice, `SaveAbhadetails`.
  - API tests (`tests/api/abha/`) call only `MedicalPrescription/GetPatientAbhaDetails` and, in `permanent` tests, `SaveAbhadetails`, with fake values; never the ABDM proxy.
- **Data.** Only obviously fake values (`test_data/abha.py`): Aadhaar `0000 0000 0000`, mobile `0000000000`, OTP `000000`, ABHA address `qa_test01`, consent name `QATest`. Wrong captcha `zzzz` (no "z" in the captcha alphabet). Nothing is saved: no patient, no bill.
- The hard-coded connector URL/token in `abha-selection-component.ts:73` and `Layout/menu.component.ts:1303` is not reproduced anywhere; no test clicks "Patient History".
- Control Room is never changed. Field 4426's value (the pharmacy's facility id) is never read into the test: `abha_setup.py` returns only "filled / blank".

## Account, company and precondition
- Login: the `chemist` account (`page_as("chemist")`), the one the chemist and manufacturing journeys use.
- Company pinned with `CompanySwitchPage.ensure_company`: **"Pharma New Company 23-09" (`PHARMA_COMPANY`)** for the ABHA tests and AB-02; **"Garments New 29-08" (`GARMENTS_COMPANY`)** for AB-03.
- Needed for the ABHA tests: that company is a **chemist company (business type 5)** with **Control Room field 4426 "Abha Id for pharmacy store" filled**. Read from the app's own local storage after the company switch (`LoggedInUserInfo.SelectedCompany.bustype`, `controlRoomData.profilerModel.FieldsData[4426].ActionData[6].action`; the same values `processout.transaction.component.ts:19926-19933` and `Component/Shared/common.function.ts:726-731` use). If not, the test **skips** with "ABHA precondition: ... it has business type N and field 4426 filled/blank. The suite does not change Control Room." Whether PNC2 is type 5 (chemist) or 13 (pharma distributor) is unknown offline: if it is 13, every ABHA test skips and a chemist company with 4426 filled is needed (see N1).
- AB-02 needs the opposite (chemist, 4426 blank) and AB-03 a non-chemist company; they skip with their own precondition text. One company cannot satisfy both AB-01..AB-32 and AB-02, so at least one group always skips (N1).

## Screens (from source, not seen live)
| Thing | Locator and source |
|---|---|
| Registration route | `/abha/patient/registration` (`Modules/abha.module.ts:24-25`); h1 "Ayushman Bharat Health Account", h3 "ABHA Registration" (`abha-patient-registration.component.html:5-13`) |
| Aadhaar boxes | `input[formcontrolname=adharNo1..3]`, `type=password` by default, `maxlength=4`, integer mask (`.html:21-43`); labels have no `for`, hence CSS |
| Eye icon | first `svg.iconPosi` (`.html:50-59`), toggles `type` password/text (`.ts:513-519`) |
| Download link | link "Download ABHA Card" (`.html:128-131`) |
| Buttons | marg-button "Submit", "Close" (`.html:141-145`; Close renders "Esc Close", `UtililityComponent/Buttons/buttons.component.ts:298-299`) |
| OTP stage | `input[formcontrolname=CpdMno]` (maxlength 10), `input[formcontrolname=otp]` (maxlength 6), "Resend OTP ..., Upto 2 times", note "Note: This mobile number will be used for all the communications related to ABHA" (`.html:62-88,134-139`; `resendOtpCount = 2`, `.ts:51`) |
| Captcha | placeholder "Captcha" (`#txtCapta`), four spans in `.captcha-box` (`.html:92-112`; download `.html:141-160`) |
| Consent popup | role dialog with "I hereby declare that", 7 checkboxes all ticked (`abha-patient-consent.component.ts:44-50`), the only textbox is the name (`#nameInput`), buttons "I Agree", "Close" (`.html` footer) |
| Card download route | `/abha/patient/card/download`; h3 "Download ABHA Card"; radios `input[name=downloadtype][value=mobileNo|aadhaar|abhaNo|abhaAddress]` with no label (`abha-patient-card-download.html:14-48`); fields by formcontrolname `mobileNo`, `aadhaarNo1..3`, `abhaNo1..4`, `abhaAddress` (`.html:50-136`); "Send OTP" only for Mobile/Aadhaar (`.html:171-175`), "Send Otp on Aadhaar linked Mobile" / "Send Otp on ABHA linked Mobile" for ABHA No./Address (`.html:188-195`); "Submit OTP" once the OTP is sent (`.html` pageButton) |
| Sale bill button | role button "Abha" (marg-button type 'Abha', no shortcut, `buttons.component.ts:846-850`), id `btnAbha<tabId>`, class `red-btn` while `abhaStatus == 0` (`UI/Transaction/InverntoryTransaction/processout.transaction.component.html:1188-1191`); sale bill opened with `SaleBillDocument.open_new()` (Sale > Bill > Create/F2) |
| ABHA Selection | role dialog with h2 "ABHA Selection"; options "Select ABHA Address", "Patient History", "Patient Registration", "Download Abha Card"; button "Close" (`#No`) (`abha-selection-component.html:5-59`, `.ts:64`) |
| Patient master | `/chemist/patient`; grid column "Abha Status" hidden unless chemist + 4426 (`patientmaster.component.ts:329,339-344`); add-patient window on F2 (`.ts:619-622`; the New button is hidden outside `/transaction` routes, `buttons.component.ts` `setButton`) with "Govt Abha Id", "Govt Abha Address", button "Save & Check Abha Id" (`UI/Chemist/Patient/add.patient.component.html:106-121,600-603`, `assets/i18n/en.json:951-952`) |
| Warnings | notifier toasts, warning style (`Globals/alertbox.ts:31-49`); texts in `pages/abha/messages.py` with `file:line` |

## Tests
Registration, UI only (`test_registration.py`)
| Test | Scenario | Asserts |
|---|---|---|
| `test_registration_screen_shows_its_headings` | AB-06 | h1 "Ayushman Bharat Health Account", h3 "ABHA Registration" |
| `test_registration_asks_for_aadhaar_in_three_boxes` | AB-06 | three Aadhaar boxes |
| `test_registration_links_to_card_download` | AB-06 | link "Download ABHA Card" |
| `test_submit_without_aadhaar_is_refused` | AB-07 | "Please Enter Valid Aadhaar Number" |
| `test_aadhaar_box_refuses_letters` | AB-08 | "ab" typed -> value "" |
| `test_aadhaar_box_takes_at_most_four_digits` | AB-08 | `maxlength=4` |
| `test_fourth_digit_moves_to_the_next_aadhaar_box` | AB-08 | box 2 focused |
| `test_aadhaar_is_masked_by_default` | AB-09 | `type=password` |
| `test_eye_icon_shows_the_aadhaar` | AB-09 | `type=text` |
| `test_close_returns_to_the_dashboard` | AB-28 | URL `/dashboard` |

Consent popup (`test_consent.py`; OTP endpoint never answered, `expect_none_during`)
| Test | Scenario | Asserts |
|---|---|---|
| `test_twelve_digits_open_the_consent_with_every_declaration_ticked` | AB-10 | 7 checkboxes, all checked |
| `test_consent_asks_for_the_patients_name` | AB-10 | name box shown |
| `test_consent_with_a_declaration_unticked_is_refused` | AB-11 | no OTP call; "Please read and tick all the terms and conditions"; popup stays |
| `test_consent_without_a_name_is_refused` | AB-12 | no OTP call; "Please enter your full name as per Aadhar card"; popup stays |
| `test_consent_without_a_name_puts_the_cursor_in_the_name` | AB-12 | name box focused |
| `test_closing_the_consent_requests_no_otp` | AB-13 | no OTP call; popup closed |

Registration after the OTP, class b (`test_registration_otp_stubbed.py`; `request/otp` stubbed and proven)
| Test | Scenario | Asserts |
|---|---|---|
| `test_unknown_aadhaar_is_reported` | AB-14 | stub `loginId: "Invalid LoginId"` -> "Invaild Aadhaar No." (sic) |
| `test_submit_after_the_otp_without_a_mobile_is_refused` | AB-15 | "Please Enter Valid Corresponding Mobile Number" |
| `test_wrong_captcha_is_refused` | AB-16 | mobile, OTP, captcha `zzzz` -> "Invalid CAPTCHA" |
| `test_otp_box_keeps_six_digits` | AB-17 | "1234567" typed -> "123456" |
| `test_resend_is_offered_up_to_two_times` | AB-17 | text "Upto 2 times" |
| `test_mobile_note_is_shown_with_the_otp` | AB-17 | the mobile note |

Card download, UI only (`test_card_download.py`; no OTP stub, so a call would be aborted and fail the test)
| Test | Scenario | Asserts |
|---|---|---|
| `test_download_screen_shows_its_heading` | AB-21 | h3 "Download ABHA Card" |
| `test_download_offers_mobile_aadhaar_abha_number_and_address` | AB-21 | four radios |
| `test_download_starts_with_mobile` | AB-21 | Mobile radio checked |
| `test_send_otp_without_a_mobile_is_refused` | AB-22 | "Please  Enter Mobile No." (two spaces in source) |
| `test_send_otp_with_part_of_the_abha_number_is_refused` | AB-23 | part 1 "00" only -> "Please Enter Full ABHA Number" |
| `test_incomplete_abha_number_puts_the_cursor_in_the_first_empty_part` | AB-23 | part 2 focused |
| `test_send_otp_without_an_abha_address_is_refused` | AB-24 | "Please Enter ABHA Address", address focused |
| `test_send_otp_without_an_aadhaar_is_refused` | AB-24 | "Please Enter Aadhaar No.", Aadhaar box 1 focused |
| `test_send_otp_without_the_captcha_is_refused` | AB-25 | "Please Enter CAPTCHA", captcha focused |
| `test_send_otp_with_a_wrong_captcha_is_refused` | AB-25 | "Invalid CAPTCHA", captcha focused |
| `test_close_returns_to_the_dashboard` | AB-28 | URL `/dashboard` |

Card download past the captcha, class b (`test_card_download_stubbed.py`; the shown captcha is typed, the one OTP call is stubbed and proven)
| Test | Scenario | Asserts |
|---|---|---|
| `test_submit_otp_without_the_otp_is_refused` | AB-26 | OTP box shown; "Submit OTP" -> "Please Enter Received OTP" |
| `test_unregistered_abha_address_is_reported` | AB-27 | stub `code: ABDM-1211` -> "Invalid ABHA Address Or ABHA Address Not Register" |
| `test_unregistered_aadhaar_is_reported` | AB-27 | stub `loginId` -> "Invalid Aadhaar Number Or Aadhaar Number Not Register" |

Sale bill (`test_sale_bill_abha.py`; nothing saved)
| Test | Scenario | Asserts |
|---|---|---|
| `test_sale_bill_offers_a_red_abha_button_before_a_patient_is_linked` | AB-01 | button "Abha" visible, class `red-btn` |
| `test_abha_button_opens_the_selection_with_its_four_options` | AB-32 | "Select ABHA Address", "Patient History", "Patient Registration", "Download Abha Card" |
| `test_abha_selection_closes_without_choosing` | AB-32 | Close -> popup hidden |
| `test_sale_bill_has_no_abha_button_when_the_abha_id_is_blank` | AB-02 | no "Abha" button |
| `test_sale_bill_of_another_trade_has_no_abha_button` | AB-03 | no "Abha" button (garments) |

Patient master (`test_patient_master.py`; nothing saved)
| Test | Scenario | Asserts |
|---|---|---|
| `test_patient_list_has_an_abha_status_column` | AB-29 (column) | column header "Abha Status" |
| `test_new_patient_shows_govt_abha_rows_and_save_and_check` | AB-30 | "Govt Abha Id", "Govt Abha Address", "Save & Check Abha Id" |
| `test_patient_list_has_no_abha_status_column_when_the_abha_id_is_blank` | AB-02 | no "Abha Status" column |
| `test_new_patient_has_no_abha_rows_when_the_abha_id_is_blank` | AB-02 | no Govt Abha rows, no "Save & Check Abha Id" |

Absence checks (AB-02, AB-03, AB-04) pass trivially if a locator is wrong: check them against the present-state tests on the first live run.

Enrolment after the OTP, class b (`test_enrolment_stubbed.py`; enrolment and suggestion stubbed and proven in the `address_step` fixture, address and card stubbed per test)
| Test | Scenario | Asserts |
|---|---|---|
| `test_address_popup_offers_the_suggested_addresses` | AB-19 | suggestions "qa_test01", "qa.test02" from the stub |
| `test_address_box_drops_characters_other_than_letters_digits_dot_and_underscore` | AB-19 | "qa_te$st 01" typed -> "qa_test01" |
| `test_too_short_address_is_refused_without_a_call` | AB-19 | "qa_t01": no address call; "ABHA Address Not Valid" |
| `test_address_without_a_dot_or_underscore_is_refused_without_a_call` | AB-19 | "qatest001": no address call; "ABHA Address Not Valid" |
| `test_valid_address_is_sent_as_the_preferred_address` | AB-19 | address call body `abhaAddress = qa_test01`, `preferred = 1` |
| `test_taken_address_is_reported` | AB-20 | stub error -> "This ABHA Address already exists. Please create with unique ABHA address" |
| `test_created_address_is_confirmed` | AB-18 | success "ABHA Address Successfully Created" |
| `test_created_address_opens_the_abha_card` | AB-18 | card call proven; "Download" popup with img "ABHA Card" |

ABHA linked to a sale bill (`test_sale_bill_abha_link.py`; `GetPatientAbhaDetails` stubbed with one fake row, decision N3 taken as "stub, do not seed")
| Test | Scenario | Asserts |
|---|---|---|
| `test_select_abha_address_lists_the_patients_abha_rows` | AB-33 | "Select Billing for Abha Number" row: ABHA no., address, "Active" |
| `test_choosing_an_abha_row_turns_the_button_green` | AB-33 | button class `blue-btn` |
| `test_linked_bill_offers_to_change_the_abha_address` | AB-32 (linked) | "Change ABHA Address" |
| `test_bill_save_sends_the_chosen_abha` | AB-34 | save request answered by a refusing stub; body `PatientAbhaDetails` = fake linkid, ABHA no., address |
| `test_reopened_bill_with_an_abha_link_shows_the_green_button` | AB-34 | a plain cash bill is saved (like the chemist suite), its `BillSales/Get` reply patched with the fake link on reopen (proven) -> `blue-btn` |
| `test_patient_history_opens_the_consent_site_in_a_new_tab` | AB-35 | new tab, answered by the connector stub, is `abhaconnector.../consents?type=hip` (URL never printed) |
| `test_patient_history_leaves_the_bill_without_an_abha` | AB-35 | button still `red-btn` (sale-bill handler is empty) |

Patient ABHA state (`test_patient_abha_status.py`)
| Test | Scenario | Asserts |
|---|---|---|
| `test_patient_with_an_abha_link_shows_active` | AB-29 | real `GetPatientList` reply patched (proven): first own patient `IsAbhaStatus` true -> "Active" |
| `test_patient_without_an_abha_link_shows_no_status` | AB-29 | second own patient false -> empty cell |
| `test_save_and_check_opens_the_card_download_with_the_patients_mobile` | AB-31 | **permanent**; fake patient saved, popup's token call proven, mobile box prefilled |
| `test_closing_the_card_download_keeps_the_patient_without_an_active_abha` | AB-31 | **permanent**; patient listed, Abha Status empty |

Digital menu (`test_digital_menu.py`; menu ids, `pages/abha/digital_menu.py`)
| Test | Scenario | Asserts |
|---|---|---|
| `test_digital_menu_offers_abha_for_the_abha_company` | AB-04 (present state) | ABHA child (92385071029) in the menu |
| `test_digital_menu_has_no_abha_when_the_abha_id_is_blank` | AB-04 / MBC-806 | no ABHA child (skips unless 4426 blank) |
| `test_digital_menu_is_hidden_when_abha_was_its_only_child` | AB-04 | no Digital (92385071021) entry; skips if Digital has other children |
| `test_another_trade_has_no_abha_menu` | AB-03 | no ABHA child (garments) |
| `test_abha_menu_offers_upload_abha_bills` | AB-39 | Digital > ABHA lists "Upload ABHA Bills" (KB text; fails if the web has no such entry) |
| `test_abha_menu_offers_incentive_claim` | AB-39 | Digital > ABHA lists "Incentive Claim" |

Direct URL (`test_direct_url.py`; session token stubbed)
| Test | Scenario | Asserts |
|---|---|---|
| `test_registration_url_is_refused_for_another_trade` | AB-05 | registration screen does not render within 30 s (pack: refused or redirected) |
| `test_card_download_url_is_refused_for_another_trade` | AB-05 | same, card download |
| `test_registration_url_is_refused_when_the_abha_id_is_blank` | AB-05 | same, chemist with 4426 blank |
| `test_card_download_url_is_refused_when_the_abha_id_is_blank` | AB-05 | same |

These four are expected to fail today (no business-type guard on the routes) and report a defect, unless N2 withdraws the expectation.

API level (`tests/api/abha/test_patient_abha_details_api.py`, marks `p3`, `api`, journey; sessions taken from the app's own signed calls, `pages/abha/app_api.py`, because the `api` fixture has no login)
| Test | Scenario | Asserts |
|---|---|---|
| `test_abha_rows_of_a_patient_are_not_returned_to_another_company` | AB-36 | PNC2 patient with ABHA rows (found, never seeded; else skip) -> `[]` when asked as the garments company |
| `test_abha_details_sent_with_another_companys_id_do_not_land_in_that_company` | AB-37 | **permanent**; `SaveAbhadetails` from PNC2 with body `complinkid` = garments -> the run's fake address is not in the garments company's rows |
| `test_abha_details_without_an_action_type_are_refused` | AB-38 | **permanent**; reply `status.status != "1"` |
| `test_abha_details_without_a_user_name_are_refused` | AB-38 | **permanent**; same |

Total: 78 tests over 39 scenarios (45 earlier + 33 new). `permanent` (skipped unless `--allow-permanent`): 5 (AB-31 x2, AB-37, AB-38 x2).


## Not automated
Every scenario now has a script; two keep a part that is not scripted.
| Scenario | Part left | Reason |
|---|---|---|
| AB-34 | Print preview shows the ABHA no. and address | Needs a server-saved ABHA-linked bill. The server may forward such a bill to the ABHA connector (`margerpdal/SaleChallanBill.cs:3618-3668`, not called in the source read), a call no browser stub can stop; the brief forbids any real ABDM request. Needs decision N4. The link sent with the save and the green button on reopen are scripted. |
| AB-39 | HFR/NHPR and DHIS registration, software linkage | Government portals outside MargBooks with a real identity and e-sign; the L&D decks show them on the desktop app only. The web menu entries "Upload ABHA Bills" and "Incentive Claim" are scripted. |

## To verify live (first run, healer)
1. Precondition values: PNC2's `bustype` and whether 4426 is filled, and that `controlRoomData` is in local storage right after `ensure_company` (`pages/abha/abha_setup.py`; `Component/Shared/common.function.ts:726-731`, `Services/Helper.services.ts:411-436`). If the key is missing the tests skip as "field 4426 blank".
2. Session-token stub is hit on both screens through `capture_one` (`abha-patient-registration.component.ts:80-82,463-478`, `abha-patient-card-download.ts:98,139-153`), i.e. no service worker in between.
3. Headings are exposed as role heading with those names (`abha-patient-registration.component.html:5-13`, `abha-patient-card-download.html:5-16`).
4. Aadhaar boxes `input[formcontrolname=adharNo1..3]` and the letter mask (`abha-patient-registration.component.html:21-43`, `appInputMask="integer"`).
5. Eye icon is the first `svg.iconPosi` on the page (`.html:50-59`).
6. Buttons by name: "Submit", "Close" (Esc Close), "I Agree", "Send OTP", "Send Otp on ABHA linked Mobile", "Submit OTP", "Abha" (exact) (`buttons.component.ts:13-38,298,846`; `abha-patient-consent.component.html` footer; `abha-patient-card-download.html:173,190-193,222`).
7. Warnings are notifier toasts of the warning kind (`Globals/alertbox.ts:44-49`, `pages/masters/master_toasts.py`).
8. Consent dialog: role dialog containing "I hereby declare that"; 7 checkboxes; the name is its only textbox (`abha-patient-consent.component.html`).
9. Focus checks: consent name (`abha-patient-consent.component.ts:78-80`), ABHA No. part 2 (`abha-patient-card-download.ts:314-315`), address (`:348`), Aadhaar box 1 (`:555-556`), captcha (`:577-579`).
10. OTP stage after the stubbed reply: `formcontrolname=CpdMno` visible, "Upto 2 times" text and note (`abha-patient-registration.component.html:62-88,134-139`). `corespondenceNo.nativeElement.focus()` (`.ts:180`) may throw on a not-yet-rendered field; check it does not stop the stage from showing.
11. Card download OTP box after the stubbed reply (`abha-patient-card-download.ts:469-483`, `.html:177-187`).
12. Captcha characters read from `.captcha-box span` (`abha-patient-card-download.html:150-160`).
13. Sale bill on PNC2 opens with Sale > Bill > Create/F2 (`pages/sale/documents/bill.py`), the "Abha" button and its `red-btn` class (`processout.transaction.component.html:1188-1191`).
14. ABHA Selection is a role dialog with heading "ABHA Selection" (`abha-selection-component.html:5,59`), option texts, Close (`#No`).
15. Patient master: column header names (`patientmaster.component.ts:323-331`), F2 opens the add-patient window (`.ts:619-622`), that window is a role dialog with a "Save" button, "Govt Abha Id/Address" texts and "Save & Check Abha Id" (`add.patient.component.html:106-121,600-603`).

16. Enrolment chain (AB-18..20): the OTP stage reaches `byAadhaarVerfication` with the shown captcha (`abha-patient-registration.component.ts:219-255`); the address popup is a role dialog containing "Create Your Unique ABHA Address." with `input[formcontrolname=abhaEmail]` and buttons "Save"/"Close" (`abha-address.component.html:1-55`); the input strips characters as typed (`.ts:62-66`); the card popup has heading "Download" and img "ABHA Card" (`abha-download-popup.component.html:1-10`).
17. Billing-details popup: role dialog, heading "Select Billing for Abha Number", table cells as role cell (`abha-selection-details.component.html:1-36`); the button turns `blue-btn` after a row click (`processout.transaction.component.html:1191`).
18. AB-34: the save request path matches `/BillSales/Save` and its JSON carries `PatientAbhaDetails` with `patientAbhaLinkId` (`processout.transaction.component.ts:11869`, `abha-selection-details.component.ts:37`); the cash bill (`pages/abha/cash_bill_draft.py`) opens with Create/F2, header `HEADERS[BASE]`, item A To Z Ns by barcode; reopen via `SaleBillPage.reopen_for_modification` calls `BillSales/Get` (`Globals/global.ts:757`).
19. AB-35: the consent tab is matched by the context stub (registered after the guard) and the popup event fires (`abha-selection-component.ts:71-75`).
20. AB-29: the grid's list call is `MedicalPrescription/GetPatientList` and its reply has `Data[].Name/linkid/Ispredefine/IsAbhaStatus`; status cells are `[col-id=abhastatus]` (`patientmaster.component.ts:188-205,329`).
21. AB-31: add-patient inputs `formcontrolname=MobileNo/Name` (`add.patient.component.html:31,58`), name capitalised (`:60`), "Save & Check Abha Id" saves then opens the card-download popup (heading "Download ABHA Card") with the mobile prefilled (`add.patient.component.ts:648-701`, `abha-patient-card-download.ts:82-85`); the popup's token call is proven by `capture_one`.
22. Digital menu ids: Digital parent `#menu92385071021` or `a#menu-<i>-92385071021`, ABHA child `[id$=-92385071029]`, nested submenu `menu[id$=-92385071029]` (`Layout/menu.component.html:5,30,54,81,92,104`); whether the ABHA child has children at all on the web (AB-39).
23. API sessions (AB-36..38): a signed app call carries a `complinkid` header (`Services/LoaderInterceptor.service.ts:45-60`); replaying its headers through `page.request` is accepted; `GetPatientAbhaDetails` is a GET with `patientlinkid` (`Services/MrgHttpService.service.ts:37-52`); the `SaveAbhadetails` reply has `status.status`.
24. AB-05: a refused screen is assumed to be anything but its heading within 30 s (`pages/abha/registration_page.py::expect_screen_refused`).

## KB vs source (offline)
- K1: The selection popup's fourth option reads "Download Abha Card" in the code (`abha-selection-component.html:53`); the pack writes "Download ABHA Card". Tests use the code text.
- K2 (AB-07): the pack expects focus on the first invalid Aadhaar box. The code calls `registrationForm.get(control).nativeElement.focus()` inside `try/catch` (`abha-patient-registration.component.ts:452-461`); a FormControl has no `nativeElement`, so no focus moves. Only the warning is asserted. Defect candidate D1 if the focus is required.
- K3 (AB-23): ABHA No. mode has no "Send OTP" button; its sends are "Send Otp on Aadhaar linked Mobile" / "Send Otp on ABHA linked Mobile" (`abha-patient-card-download.html:188-195`), and the message on that path is "Please Enter Full ABHA Number" (`.ts:310`); "Please Enter ABHA Number" (`.ts:537`) is reachable only through Resend. Tests use the ABHA-linked button.
- K4 (AB-16): the captcha refresh icon is not asserted (an unlabelled link; regeneration is random).
- K5 (AB-30): the patient list's New button is hidden by the shared button rule outside `/transaction` routes; the window opens on F2.
- The pack's code findings 2-8 (`@sbx` suffix, client-side captcha, no 10-digit mobile check, resend counter, F2 without the ABHA check, `complinkid` from body, `[Authorize]` commented out) are unchanged and not exercised by these tests.

## NEEDS DECISION
- N1: Which company is the ABHA company? A chemist (type 5) company with 4426 filled is needed for 41 of the 45 tests, and a chemist company with 4426 blank for AB-02 (4 tests). The suite will not change 4426. Options: two companies on the chemist login, or accept that one group always skips.
- N2 (AB-05): should `/abha/patient/registration` and `/abha/patient/card/download` be refused for a non-chemist or 4426-off user? If yes, the test asserts the refusal and fails as a defect today (code has no business-type guard, `app-routing.module.ts:52-56,163`).
- N3 (AB-33, AB-34, AB-37, AB-38): may the suite write fake `PatientAbhaDetails` rows with `SaveAbhadetails` (tenant data, finding 7), or should `GetPatientAbhaDetails` be stubbed in the browser instead? Scripted offline as: browser tests stub (AB-29, AB-33, AB-34), API tests that send `SaveAbhadetails` (AB-37, AB-38) are `permanent`, AB-36 only reads and skips if no row exists.
- N4 (AB-34 print): may one ABHA-linked bill be saved on QA? Only if the server is confirmed not to forward it to the ABHA connector (`SaleChallanBill.cs:3618-3668`).

## Defects seen
None observed (nothing was run against the app). D1 above is a code-reading candidate.
