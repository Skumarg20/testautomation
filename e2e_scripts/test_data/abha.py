"""Obviously fake identity values for J39 (pack "Test data rule"): never a real Aadhaar, ABHA or mobile."""

FAKE_AADHAAR_PARTS = ("0000", "0000", "0000")
FAKE_MOBILE = "0000000000"
FAKE_OTP = "000000"
FAKE_ABHA_ADDRESS = "qa_test01"
# The consent box strips all but letters, digits, "." and "_" (`abha-patient-consent.component.ts:84-88`).
FAKE_CONSENT_NAME = "QATest"
FAKE_ABHA_NUMBER = "00-0000-0000-0000"
# Shown as suggestions in the create-address popup; the second differs only by its separator.
SUGGESTED_ABHA_ADDRESSES = ("qa_test01", "qa.test02")
# The address rule: 8-18 characters with exactly one "." or "_" inside (abha-address.component.ts:53-60).
TOO_SHORT_ABHA_ADDRESS = "qa_t01"
NO_SEPARATOR_ABHA_ADDRESS = "qatest001"
# The input drops every character but letters, digits, "." and "_" (abha-address.component.ts:62-66).
ABHA_ADDRESS_WITH_STRAY_CHARACTERS = "qa_te$st 01"
ABHA_ADDRESS_STRIPPED = "qa_test01"

# One PatientAbhaDetails row as GetPatientAbhaDetails returns it (margerpdal/MedicalPrescripton.cs:1569),
# all values fake; its `linkid` is not a real row.
FAKE_ABHA_ROW_LINKID = 990000001
FAKE_ABHA_ROW: dict[str, object] = {
    "linkid": FAKE_ABHA_ROW_LINKID,
    "abhano": FAKE_ABHA_NUMBER,
    "abhaaddress": f"{FAKE_ABHA_ADDRESS}@sbx",
    "abhastatus": 1,
    "dob": "01-01-2000",
    "gender": "M",
    "name": FAKE_CONSENT_NAME,
}

# Already in the case the name box's `textTransform="capitalize"` gives it (add.patient.component.html:60).
FAKE_PATIENT_NAME_PREFIX = "Qa Abha"
# Patient mobiles must be unique per company, so each run makes its own fake "00..." number.
FAKE_PATIENT_MOBILE_DIGITS = 6


def fake_patient_name(run_id: str) -> str:
    return f"{FAKE_PATIENT_NAME_PREFIX} {int(run_id, 16)}"


def fake_patient_mobile(run_id: str) -> str:
    """Ten digits starting with "0000": no Indian mobile starts with 0, so it reaches nobody."""
    suffix = int(run_id, 16) % 10**FAKE_PATIENT_MOBILE_DIGITS
    return f"0000{suffix:0{FAKE_PATIENT_MOBILE_DIGITS}d}"
