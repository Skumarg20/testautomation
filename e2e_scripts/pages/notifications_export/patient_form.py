"""A new patient in the chemist patient master (`/chemist/patient`, add.patient.component.html, not seen
live): F2 on the list opens the add-patient window (as `pages/abha/patient_master.py` does), with Mobile
No. and Name boxes known only by their form control names, and Save."""

from playwright.sync_api import Locator, expect

from pages.abha.patient_master import PatientMaster
from pages.accounting.toasts import Toasts
from pages.components.app_texts import RECORD_SAVED

SAVE_TIMEOUT_MS = 60_000
QA_MOBILE = "9000000001"


class PatientForm(PatientMaster):
    def add(self, name: str) -> None:
        """Saves a patient called `name` with a fictitious mobile number."""
        self.open()
        self.start_new_patient()
        self._box("MobileNo").fill(QA_MOBILE)
        self._box("Name").fill(name)
        self._window.get_by_role("button", name="Save", exact=True).click()
        Toasts(self.page).expect_any_saying(RECORD_SAVED, SAVE_TIMEOUT_MS)
        expect(self._window).to_be_hidden(timeout=SAVE_TIMEOUT_MS)

    def _box(self, form_control_name: str) -> Locator:
        # Why CSS: the window's labels have no `for`; the boxes are known only by form control name.
        return self._window.locator(f'input[formcontrolname="{form_control_name}"]')

    @property
    def _window(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has=self.page.get_by_role("button", name="Save"))
