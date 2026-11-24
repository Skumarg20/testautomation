"""CRM > Prescription Reminder (`/report/crm/prescription/cm-default`, live 2026-10-12): due prescriptions
with a tick box per row; "Send SMS" appears only once a row is ticked (prescription.reminder.component.ts:
230-240). Send SMS posts `RegisterUser/SendBulkSMSTemplate`, then `Reports/InsertBulkReminderData`, then says
"SMS send successfully" (:281-336); the tests answer both calls with stubs. Rows and tick boxes were not seen
live (the garments company had none)."""

import re

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

PATH = "/report/crm/prescription/cm-default"
TITLE = "Prescription Reminder"
LOAD_TIMEOUT_MS = 60_000
SEND_SMS = "Send SMS"
ANY_TEXT = re.compile(r"\S")


class PrescriptionReminderPage(BasePage):
    def open(self) -> None:
        self.goto(PATH, LOAD_TIMEOUT_MS)
        expect(self.page.get_by_role("heading", name=TITLE, level=1)).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def expect_columns(self, columns: tuple[str, ...]) -> None:
        headers = self._grid.get_by_role("columnheader")
        # The first column holds the row tick boxes and has no title.
        expect(headers).to_have_text(["", *columns])

    def has_due_prescriptions(self) -> bool:
        return self._rows.count() > 0

    def tick_first_prescription(self) -> None:
        self._rows.first.get_by_role("checkbox").check()

    def expect_send_sms_hidden(self) -> None:
        expect(self._send_sms).to_have_count(0)

    def expect_send_sms_offered(self) -> None:
        expect(self._send_sms).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def send_sms(self) -> None:
        self._send_sms.click()

    def expect_listed(self, patient: str) -> None:
        expect(self._patient_cell(patient)).to_be_visible(timeout=LOAD_TIMEOUT_MS)

    def expect_not_listed(self, patient: str) -> None:
        expect(self._patient_cell(patient)).to_have_count(0, timeout=LOAD_TIMEOUT_MS)

    def _patient_cell(self, patient: str) -> Locator:
        return self._grid.get_by_role("gridcell", name=patient, exact=True)

    @property
    def _rows(self) -> Locator:
        """Rows that hold a prescription; the grid pads itself with empty rows."""
        return self._grid.get_by_role("row").filter(
            has=self.page.get_by_role("gridcell").filter(has_text=ANY_TEXT)
        )

    @property
    def _send_sms(self) -> Locator:
        return self.page.get_by_title(SEND_SMS, exact=True)

    @property
    def _grid(self) -> Locator:
        return self.page.get_by_role("main").get_by_role("grid")
