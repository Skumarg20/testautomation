"""The header of a sale document: party, date, patient, doctor and address."""

import re
from datetime import date

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.sale.documents.document_requests import Person
from pages.sale.documents.selection_window import SelectionWindow

DATE_FORMAT = "%d-%m-%Y"
FIELD_TIMEOUT_MS = 10_000
PARTY_LABEL = "Party Name"
ASK_ON_SPACEBAR = "Ask on Spacebar"


class DocumentHeader(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self._selection = SelectionWindow(self.page)

    def number(self, label: str) -> str:
        return self.field(label).input_value()

    def field(self, label: str, index: int = 0) -> Locator:
        """The app's labels are not tied to their inputs, so the input is found beside its label."""
        return self.page.locator("label", has_text=label).locator("..").locator("input").nth(index)

    def choose_party(self, name: str) -> None:
        """Side effect: when the party has to be asked for, the tenant-wide Control Room option "ask party
        in retail billing" is set to "Ask on Spacebar" and left so (see `_ask_for_party_on_spacebar`)."""
        party = self.field(PARTY_LABEL)
        if self._selection.is_shown():
            self._selection.choose_cell_value(name)
        elif party.input_value().lower() == name.lower():
            party.press("Enter")
        else:
            self._choose_party_with_spacebar(name)

    def enter_date(self, day: date) -> None:
        # The first "Date" label is the document's; later ones belong to pop-up windows.
        field = (
            self.page.locator("label", has_text=re.compile(r"^\s*Date")).locator("..").locator("input").first
        )
        field.press("Control+A")
        field.press_sequentially(day.strftime(DATE_FORMAT))
        field.press("Enter")

    def choose_patient(self, patient: Person) -> None:
        self._choose_person(self.field("Patient Mob./ID"), self.field("Patient Name", 1), patient)

    def choose_doctor(self, doctor: Person) -> None:
        self._choose_person(self.field("Doctor Mob./ID"), self.field("Doctor Name", 1), doctor)

    def fill_address(self, address: str) -> None:
        self.field("Address").fill(address)

    def _choose_party_with_spacebar(self, name: str) -> None:
        self._ask_for_party_on_spacebar()
        self.field(PARTY_LABEL).press("Space")
        self._selection.choose_cell_value(name)

    def _ask_for_party_on_spacebar(self) -> None:
        """Tenant-wide Control Room setting; it is why the sales tests share the tenant xdist group."""
        self.page.locator("#aControlRoomSetting").click()
        self.page.locator("#txtaskpartyinretailbilling").select_option(label=ASK_ON_SPACEBAR)
        self.page.locator(".dashboardSetting h2.headingItem button").click()

    def _choose_person(self, by_mobile: Locator, by_name: Locator, person: Person) -> None:
        if self._selection.is_shown():
            self._selection.choose_cell_value(person.mobile)
        elif person.mobile:
            self._pick_through(by_mobile, person.mobile)
        elif person.name:
            self._pick_through(by_name, person.name)

    def _pick_through(self, field: Locator, value: str) -> None:
        """The case names this person, so a field that never shows fails instead of being skipped."""
        expect(field).to_be_visible(timeout=FIELD_TIMEOUT_MS)
        field.click()
        field.press("Control+A")
        field.press("Space")
        self._selection.choose_cell_value(value)
