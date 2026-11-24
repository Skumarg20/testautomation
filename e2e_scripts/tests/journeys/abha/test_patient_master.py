"""J39 ABHA in the chemist patient master (AB-29 column, AB-30, AB-02): read only, no patient is saved."""

import pytest
from playwright.sync_api import Page

from pages.abha.patient_master import PatientMaster

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]


def test_patient_list_has_an_abha_status_column(abha_patient_master: PatientMaster) -> None:
    abha_patient_master.expect_abha_status_column()


def test_new_patient_shows_govt_abha_rows_and_save_and_check(abha_patient_master: PatientMaster) -> None:
    abha_patient_master.start_new_patient()

    abha_patient_master.expect_abha_rows_and_check_button()


def test_patient_list_has_no_abha_status_column_when_the_abha_id_is_blank(
    chemist_without_abha_page: Page,
) -> None:
    patients = PatientMaster(chemist_without_abha_page)

    patients.open()

    patients.expect_no_abha_status_column()


def test_new_patient_has_no_abha_rows_when_the_abha_id_is_blank(chemist_without_abha_page: Page) -> None:
    patients = PatientMaster(chemist_without_abha_page)
    patients.open()

    patients.start_new_patient()

    patients.expect_no_abha_rows_or_check_button()
