"""J39 the patient master's ABHA state (AB-29 value, AB-31).

AB-29: the list reply is patched in the browser (one patient with an ABHA link, one without) because a real
link needs `SaveAbhadetails` (decision N3); the fixture proves the grid's list call went through the patch.
AB-31 saves a new fake patient with "Save & Check Abha Id": patients have no delete path the suite owns, so
those tests are `permanent` and run only with `--allow-permanent`. They stop at the card-download popup,
before any OTP is requested.
"""

import pytest
from playwright.sync_api import Page

from pages.abha.patient_abha_status import PatchedPatients
from pages.abha.patient_master import PatientMaster
from test_data.abha import fake_patient_mobile, fake_patient_name

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]

LEAVES_A_PATIENT = 'a fake patient "Qa Abha <number>" with an "0000..." mobile in the ABHA company'


def test_patient_with_an_abha_link_shows_active(
    abha_page: Page, patients_with_known_abha_states: PatchedPatients
) -> None:
    PatientMaster(abha_page).expect_abha_active(patients_with_known_abha_states.active_name)


def test_patient_without_an_abha_link_shows_no_status(
    abha_page: Page, patients_with_known_abha_states: PatchedPatients
) -> None:
    PatientMaster(abha_page).expect_abha_not_active(patients_with_known_abha_states.inactive_name)


@pytest.mark.permanent(LEAVES_A_PATIENT)
def test_save_and_check_opens_the_card_download_with_the_patients_mobile(
    patient_checked_for_abha: PatientMaster, run_id: str
) -> None:
    patient_checked_for_abha.expect_card_download_prefilled_with(fake_patient_mobile(run_id))


@pytest.mark.permanent(LEAVES_A_PATIENT)
def test_closing_the_card_download_keeps_the_patient_without_an_active_abha(
    patient_checked_for_abha: PatientMaster, run_id: str
) -> None:
    patient_checked_for_abha.close_card_download()

    patient_checked_for_abha.open()
    patient_checked_for_abha.expect_abha_not_active(fake_patient_name(run_id))
