"""The ABHA calls J39 must never let out of the browser, and the stub replies tests answer them with.

`ABDM_OR_ABHA_WRITE` is what the shared `SendGuard` aborts (pack "Network to mock" list and code map,
`scenarios/abha-health-flows.md`): everything under `abdmAbhaBaseUrl` (AbhaGateway, Enrollment, AbhaInvoice;
`abdm.<domain>/` on the hosted builds, `localhost:5020/` in the dev build), the external consent connector the
selection popup opens, and `MedicalPrescription/SaveAbhadetails`.

Each reply is the smallest body the Angular code reads (file:line per constant), with obviously fake values.
A `StubbedEndpoint` answering one of these calls is a page route, so it wins over the guard's context route.
"""

import re

from pages.components.stubbed_endpoint import StubReply
from test_data.abha import (
    FAKE_ABHA_ADDRESS,
    FAKE_ABHA_NUMBER,
    FAKE_ABHA_ROW,
    FAKE_CONSENT_NAME,
    FAKE_MOBILE,
    SUGGESTED_ABHA_ADDRESSES,
)

ABDM_OR_ABHA_WRITE = re.compile(
    r"(//abdm\.|//localhost:5020/|abhaconnector|/api/(AbhaGateway|Enrollment|AbhaInvoice)/|"
    r"MedicalPrescription/SaveAbhadetails)",
    re.IGNORECASE,
)

# Called by both standalone screens on load; abha-patient-registration.component.ts:468-474 and
# abha-patient-card-download.ts:145-150 read `data.accessToken`, the download screen also `status == "1"`.
SESSION_TOKEN = re.compile(r"/api/AbhaGateway/GetSessionToken", re.IGNORECASE)
SESSION_TOKEN_REPLY = StubReply({"status": "1", "data": {"accessToken": "qa-stub-session-token"}})

# Registration OTP, abha-patient-registration.component.ts:164-187.
REGISTRATION_OTP = re.compile(r"/api/Enrollment/m1/request/otp", re.IGNORECASE)
# Card-download OTP by mobile, Aadhaar or ABHA number, abha-patient-card-download.ts:458-486.
LOGIN_OTP = re.compile(r"/api/Enrollment/m1/profile/login/request/abhanumberLoginviaabhaotp", re.IGNORECASE)
# Card-download OTP by ABHA address, abha-patient-card-download.ts:369-402.
ADDRESS_LOGIN_OTP = re.compile(
    r"/api/Enrollment/m1/profile/login/request/AbhaAddressLoginViaAbhaOtp", re.IGNORECASE
)

# `!data.error` and no `data.loginId`: the OTP panel opens (registration .ts:173-180, download .ts:469-483).
OTP_SENT_REPLY = StubReply({"status": 1, "data": {"txnId": "qa-stub-txn", "message": "QA stub: no OTP sent"}})
# `data.loginId == "Invalid LoginId"` (registration .ts:170-172; download .ts:467-468, then
# handleErrorMsgAtOtpSend).
UNKNOWN_LOGIN_REPLY = StubReply({"status": 1, "data": {"loginId": "Invalid LoginId"}})
# `data.code == "ABDM-1211"` (download .ts:378-379).
ADDRESS_NOT_REGISTERED_REPLY = StubReply({"status": 1, "data": {"code": "ABDM-1211"}})

# Enrolment chain after the OTP, abha-patient-registration.component.ts:255-282 (enrol), :323-366
# (suggestion), abha-address.component.ts:83-100 (address) and :139-157 (card). The guard aborts each until
# a test answers it.
ENROL_BY_AADHAAR = re.compile(r"/api/Enrollment/m1/enrol/byAadhaarVerfication", re.IGNORECASE)
ADDRESS_SUGGESTION = re.compile(r"/api/Enrollment/m1/enrollment/enrol/suggestion", re.IGNORECASE)
CREATE_ABHA_ADDRESS = re.compile(r"/api/Enrollment/m1/enrol/abha-address", re.IGNORECASE)
ABHA_CARD = re.compile(r"/api/Enrollment/m1/account/abhacard", re.IGNORECASE)

# `isNew` and a profile mobile equal to the typed correspondence mobile open the address step
# (registration .ts:261-277); `tokens.token` is read by the card call (abha-address.component.ts:143).
ENROLLED_REPLY = StubReply(
    {
        "status": 1,
        "data": {
            "isNew": True,
            "message": "QA stub: enrolled",
            "txnId": "qa-stub-txn",
            "tokens": {"token": "qa-stub-x-token"},
            "ABHAProfile": {
                "mobile": FAKE_MOBILE,
                "ABHANumber": FAKE_ABHA_NUMBER,
                "firstName": FAKE_CONSENT_NAME,
                "abhaStatus": "ACTIVE",
            },
        },
    }
)
# `data.abhaAddressList` fills the suggestions (abha-address.component.ts:43).
SUGGESTIONS_REPLY = StubReply(
    {"status": 1, "data": {"txnId": "qa-stub-txn", "abhaAddressList": list(SUGGESTED_ABHA_ADDRESSES)}}
)
# Anything but the two refusals counts as created (abha-address.component.ts:86-94).
ADDRESS_CREATED_REPLY = StubReply({"status": 1, "data": {"abhaAddress": f"{FAKE_ABHA_ADDRESS}@sbx"}})
# AbhaEnum.AbhaAddresAlreadyExist, Globals/global.ts:21278, compared at abha-address.component.ts:89.
ADDRESS_TAKEN_REPLY = StubReply(
    {
        "status": 1,
        "data": {
            "error": {"message": "This ABHA Address already exists. Please create with unique ABHA address"}
        },
    }
)
# `data.imageAbhacard` becomes a PNG data URL (abha-address.component.ts:149); a 1x1 transparent PNG.
ONE_PIXEL_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CARD_REPLY = StubReply({"status": 1, "data": {"imageAbhacard": ONE_PIXEL_PNG}})

# Not an ABDM call: the tenant read the "Select Billing for Abha Number" popup lists
# (abha-selection-details.component.ts:23-31, Globals/global.ts:985). Stubbed so no PatientAbhaDetails row
# has to be seeded (decision N3, option "stub in the browser").
PATIENT_ABHA_DETAILS = re.compile(r"MedicalPrescription/GetPatientAbhaDetails", re.IGNORECASE)
PATIENT_ABHA_DETAILS_REPLY = StubReply({"status": {"status": "1"}, "Data": [FAKE_ABHA_ROW]})
