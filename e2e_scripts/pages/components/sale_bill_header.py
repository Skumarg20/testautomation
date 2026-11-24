"""The header of a sale document: party, patient, doctor, store, MR, address and date."""

from datetime import date, timedelta
from typing import Literal

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage
from test_data.headers import CASH_ACCOUNT
from test_data.models import BillHeader

Document = Literal["sale bill", "sale challan"]
OPEN_SHORTCUTS: dict[Document, str] = {"sale bill": "Alt+N", "sale challan": "Alt+C"}
DATE_FORMAT = "%d/%m/%Y"
PRINT_PREVIEW_CLOSE_TIMEOUT_MS = 2_000
PARTY_WINDOW_TIMEOUT_MS = 2_000
FIELD_VALUE_TIMEOUT_MS = 10_000


class SaleBillHeader(BasePage):
    def open_document(self, document: Document) -> None:
        self.page.wait_for_load_state("load")
        self.page.keyboard.press(OPEN_SHORTCUTS[document])
        self.page.wait_for_load_state("load")
        self._close_print_preview_if_shown()

    def fill(self, header: BillHeader) -> None:
        if header.date_offset_days is not None:
            self._enter_date(header.date_offset_days)
        if header.party_name is not None:
            self._choose_party(header.party_name)
        self._fill_text(self._field("PatientName"), header.patient_name)
        self._fill_text(self.page.locator('input[formcontrolname="DoctorName"]'), header.doctor)
        self._choose_from_list(self._field("tmp_StoreName"), "tmp_StoreName", header.store)
        self._choose_from_list(self._field("mrName"), "LedgerName", header.mr)
        self._fill_text(self._field("txtpatientaddress"), header.address)

    def entry_number(self) -> str:
        return self.page.locator('input[formcontrolname="entryNo"]').input_value()

    def _field(self, form_control_name: str) -> Locator:
        return self.page.locator(f'[formcontrolname="{form_control_name}"]')

    def _enter_date(self, offset_days: int) -> None:
        typed_date = (date.today() + timedelta(days=offset_days)).strftime(DATE_FORMAT)
        date_input = self.page.locator('[id^="txtbillDate"]')
        date_input.click()
        date_input.press("Control+A")
        date_input.press("Backspace")
        date_input.press_sequentially(typed_date)
        date_input.press("Enter")

    def _choose_party(self, party_name: str) -> None:
        if not self._party_window.is_visible():
            self._focus_party_field()
        if self._party_window_is_shown():
            self._pick_from_party_window(party_name)
        elif party_name == CASH_ACCOUNT:
            self.page.keyboard.press("Enter")
        else:
            self._search_and_pick(self._field("ledgerName"), "LedgerName", party_name)

    def _focus_party_field(self) -> None:
        party = self._field("ledgerName")
        expect(party).to_be_visible()
        party.click()

    def _party_window_is_shown(self) -> bool:
        """With Control Room "Ask Party in Retail Billing" = Ask, the party list opens as soon as the
        party field takes focus, also when a previous step moved focus there."""
        try:
            self._party_window.wait_for(state="visible", timeout=PARTY_WINDOW_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            return False
        return True

    def _pick_from_party_window(self, party_name: str) -> None:
        window = self._party_window
        window.get_by_role("searchbox").press_sequentially(party_name)
        name_cell = self._field_cell("LedgerName").get_by_text(party_name, exact=True)
        window.get_by_role("row").filter(has=name_cell).click()
        expect(window).to_be_hidden()

    @property
    def _party_window(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has_text="Select Party")

    def _choose_from_list(self, field: Locator, column: str, value: str | None) -> None:
        if value is None or not field.is_visible():
            return
        field.click()
        self._search_and_pick(field, column, value)

    def _search_and_pick(self, field: Locator, column: str, value: str) -> None:
        field.press("Space")
        search = self.page.get_by_role("searchbox", name="Search", exact=True)
        search.click()
        search.press_sequentially(value)
        self._list_row(column, value).click()

    def _field_cell(self, column: str) -> Locator:
        return self.page.locator(f'[col-id="{column}"]')

    def _list_row(self, column: str, value: str) -> Locator:
        marker = self._field_cell(column)
        list_body = self.page.locator(".ag-body-container").filter(has=marker)
        return list_body.get_by_role("row").filter(has=marker.filter(has_text=value))

    @staticmethod
    def _fill_text(field: Locator, value: str | None) -> None:
        if value is None or not field.is_visible():
            return
        field.fill(value)
        expect(field).to_have_value(value, timeout=FIELD_VALUE_TIMEOUT_MS)

    def _close_print_preview_if_shown(self) -> None:
        close_button = self.page.locator("#btn-Close")
        try:
            close_button.wait_for(state="visible", timeout=PRINT_PREVIEW_CLOSE_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            return  # The preview only appears after a previous bill was saved.
        close_button.click()
        self.page.wait_for_load_state("load")
