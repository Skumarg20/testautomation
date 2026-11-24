"""The ABHA parts of the chemist patient master, `/chemist/patient`, and its add-patient window.

With ABHA set up the grid has an "Abha Status" column (`patientmaster.component.ts:329,339-344`) and the
add-patient window shows read-only "Govt Abha Id" / "Govt Abha Address" rows and a "Save & Check Abha Id"
(F2) button (`add.patient.component.html:106-121,600-603`, `assets/i18n/en.json:951-952`). Nothing is saved.
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

SCREEN_TIMEOUT_MS = 30_000
ABHA_ROWS = ("Govt Abha Id", "Govt Abha Address")
SAVE_AND_CHECK = "Save & Check Abha Id"
ACTIVE = "Active"
CARD_DOWNLOAD_TITLE = "Download ABHA Card"


class PatientMaster(BasePage):
    PATH = "/chemist/patient"

    def open(self) -> None:
        self.goto(self.PATH)
        expect(self._column("Name")).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def expect_abha_active(self, patient_name: str) -> None:
        expect(self._abha_status_of(patient_name)).to_have_text(ACTIVE)

    def expect_abha_not_active(self, patient_name: str) -> None:
        expect(self._abha_status_of(patient_name)).to_have_text("")

    def fill_new_patient(self, mobile: str, name: str) -> None:
        """Mobile and name only; the form defaults its cash account (`add.patient.component.ts:192-198`)."""
        self._new_patient_field("MobileNo").fill(mobile)
        self._new_patient_field("Name").fill(name)

    def save_and_check_abha(self) -> None:
        """Saves the patient (ActionType A) and opens the card-download popup (`add.patient...ts:648-701`)."""
        self._save_and_check.click()
        expect(self._card_download_popup).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def expect_card_download_prefilled_with(self, mobile: str) -> None:
        # Why CSS: the popup's inputs have no accessible names (`abha-patient-card-download.html:52-60`).
        mobile_box = self._card_download_popup.locator('input[formcontrolname="mobileNo"]')
        expect(mobile_box).to_have_value(mobile)

    def close_card_download(self) -> None:
        self._card_download_popup.get_by_role("button", name="Close").click()
        expect(self._card_download_popup).to_be_hidden(timeout=SCREEN_TIMEOUT_MS)

    def expect_abha_status_column(self) -> None:
        expect(self._column("Abha Status")).to_be_visible()

    def expect_no_abha_status_column(self) -> None:
        expect(self._column("Abha Status")).to_have_count(0)

    def start_new_patient(self) -> None:
        # The New button is hidden outside /transaction routes (buttons.component.ts setButton); the list
        # opens the add-patient window on F2 (`patientmaster.component.ts:619-622`).
        self._column("Name").click()
        self.page.keyboard.press("F2")
        expect(self._new_patient_window).to_be_visible(timeout=SCREEN_TIMEOUT_MS)

    def expect_abha_rows_and_check_button(self) -> None:
        for label in ABHA_ROWS:
            expect(self._new_patient_window.get_by_text(label, exact=True)).to_be_visible()
        expect(self._save_and_check).to_be_visible()

    def expect_no_abha_rows_or_check_button(self) -> None:
        for label in ABHA_ROWS:
            expect(self._new_patient_window.get_by_text(label, exact=True)).to_have_count(0)
        expect(self._save_and_check).to_have_count(0)

    def _abha_status_of(self, patient_name: str) -> Locator:
        row = self.page.get_by_role("row").filter(
            has=self.page.get_by_role("gridcell", name=patient_name, exact=True)
        )
        # Why CSS: ag-Grid cells are told apart only by their col-id (`patientmaster.component.ts:329`).
        return row.first.locator('[col-id="abhastatus"]')

    def _new_patient_field(self, control_name: str) -> Locator:
        # Why CSS: the labels are not linked to the inputs (`add.patient.component.html:31-60`).
        return self._new_patient_window.locator(f'input[formcontrolname="{control_name}"]')

    @property
    def _card_download_popup(self) -> Locator:
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name=CARD_DOWNLOAD_TITLE)
        )

    def _column(self, name: str) -> Locator:
        return self.page.get_by_role("columnheader", name=name, exact=True)

    @property
    def _new_patient_window(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has=self.page.get_by_role("button", name="Save"))

    @property
    def _save_and_check(self) -> Locator:
        return self._new_patient_window.get_by_role("button", name=SAVE_AND_CHECK)
