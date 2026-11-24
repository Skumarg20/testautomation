"""J39 `MedicalPrescription` ABHA details at the API level (AB-36 tenancy read, AB-37 tenancy write, AB-38
validation). No ABDM call is made: these endpoints are MargBooks' own.

AB-37 and AB-38 send `SaveAbhadetails`, which writes a `PatientAbhaDetails` row when the server accepts it
(the missing-field checks may never fire, `margerpbll/MedicalPrescription.cs:520-529` and the note in
`MargBooks.UnitTests/Services/MedicalPrescriptionBalTests.cs:30`), and no delete is known. They are
`permanent` and run only with `--allow-permanent` (decision N3). Every value sent is fake.
"""

import pytest

from pages.abha.app_api import CompanySession, OwnCompany, SessionIds, was_accepted
from test_data.abha import FAKE_ABHA_NUMBER, FAKE_CONSENT_NAME

pytestmark = [pytest.mark.p3, pytest.mark.api, pytest.mark.journey("abha-health-flows")]

MAY_LEAVE_A_ROW = "a fake PatientAbhaDetails row (abhano 00-0000-0000-0000) if the server accepts it"
SAVE_ACTION = "A"


def _fake_abha_details(ids: SessionIds, patient_linkid: int, abha_address: str) -> dict[str, object]:
    """The body the app's address popup sends (`abha-address.component.ts:112-127`), with fake values."""
    return {
        "ActionType": SAVE_ACTION,
        "complinkid": ids.company_linkid,
        "userlinkid": ids.user_linkid,
        "username": ids.user_name,
        "abhano": FAKE_ABHA_NUMBER,
        "abhaaddress": abha_address,
        "abhastatus": 0,
        "patientlinkid": patient_linkid,
        "name": FAKE_CONSENT_NAME,
        "dob": "01-01-2000",
        "gender": "M",
    }


def _run_address(run_id: str) -> str:
    return f"qa_{run_id}@sbx"


def test_abha_rows_of_a_patient_are_not_returned_to_another_company(
    other_company: CompanySession, patient_with_abha_rows: int
) -> None:
    assert other_company.api.abha_rows_of(patient_with_abha_rows) == []


@pytest.mark.permanent(MAY_LEAVE_A_ROW)
def test_abha_details_sent_with_another_companys_id_do_not_land_in_that_company(
    own_company: OwnCompany, other_company: CompanySession, run_id: str
) -> None:
    patient = own_company.patient_linkids[0]
    body = _fake_abha_details(own_company.session.ids, patient, _run_address(run_id))
    body["complinkid"] = other_company.ids.company_linkid

    own_company.session.api.save_abha_details(body)

    addresses = [row.get("abhaaddress") for row in other_company.api.abha_rows_of(patient)]
    assert _run_address(run_id) not in addresses


@pytest.mark.permanent(MAY_LEAVE_A_ROW)
def test_abha_details_without_an_action_type_are_refused(own_company: OwnCompany, run_id: str) -> None:
    body = _fake_abha_details(own_company.session.ids, own_company.patient_linkids[0], _run_address(run_id))
    del body["ActionType"]

    assert not was_accepted(own_company.session.api.save_abha_details(body))


@pytest.mark.permanent(MAY_LEAVE_A_ROW)
def test_abha_details_without_a_user_name_are_refused(own_company: OwnCompany, run_id: str) -> None:
    body = _fake_abha_details(own_company.session.ids, own_company.patient_linkids[0], _run_address(run_id))
    del body["username"]

    assert not was_accepted(own_company.session.api.save_abha_details(body))
