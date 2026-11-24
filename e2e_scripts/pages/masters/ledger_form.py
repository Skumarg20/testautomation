"""Master > Accounts Master > Ledger > Create/F2 and Edit/F3: the Create / Modify Party (ledger) form."""

import re
from enum import Enum

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.masters.master_list import LedgerList
from pages.masters.typeahead import Typeahead
from test_data.masters import GeneralLedgerSpec, PartyLedgerSpec

SAVED_MESSAGE = re.compile("Record Saved Successfully", re.IGNORECASE)
UPDATED_MESSAGE = re.compile("Record Updated Successfully", re.IGNORECASE)
GST_APPLICABLE_LABEL = "GST Applicable"
FORM_TIMEOUT_MS = 30_000


class TaxRegistration(Enum):
    """The "Ledger Type" of a party: the option values of the GST/Tax Details tab."""

    REGISTERED = "1"
    COMPOSITION = "2"
    UNREGISTERED = "3"


class LedgerForm(BasePage):
    def open_new(self) -> None:
        LedgerList(self.page).open()
        self.page.keyboard.press("F2")
        expect(self._name).to_be_visible(timeout=FORM_TIMEOUT_MS)

    def open_existing(self, name: str) -> None:
        ledgers = LedgerList(self.page)
        ledgers.open()
        ledgers.open_edit(name)
        expect(self._name).to_have_value(name, timeout=FORM_TIMEOUT_MS)

    def enter_general(self, ledger: GeneralLedgerSpec) -> None:
        self._name.fill(ledger.name)
        self.choose_group(ledger.group)

    def enter_party(self, party: PartyLedgerSpec) -> None:
        self._name.fill(party.name)
        self.choose_group(party.group)
        Typeahead(self.page).choose(self._station, party.station)
        self._mobile.fill(party.mobile)

    def enter_party_without_station(self, party: PartyLedgerSpec) -> None:
        self._name.fill(party.name)
        self.choose_group(party.group)
        self._mobile.fill(party.mobile)

    def register_for_gst(self, registration: TaxRegistration, gstin: str) -> None:
        """Sets the party's GST registration; every type except unregistered needs a GSTIN."""
        self._ledger_type.select_option(registration.value)
        self._gstin.fill(gstin)
        self._gstin.press("Tab")

    def choose_group(self, group: str) -> None:
        Typeahead(self.page).choose(self._group, group)

    def clear_name(self) -> None:
        self._name.fill("")

    def clear_mobile(self) -> None:
        self._mobile.fill("")

    def enter_city(self, city: str) -> None:
        self._city.fill(city)

    def save(self) -> None:
        self.page.locator("#btn-Save").click()

    def update(self) -> None:
        self.page.locator("#btn-Update").click()

    def expect_saved(self) -> None:
        Toasts(self.page).expect_success_saying(SAVED_MESSAGE)

    def expect_updated(self) -> None:
        Toasts(self.page).expect_success_saying(UPDATED_MESSAGE)

    def expect_group(self, group: str) -> None:
        expect(self._group).to_have_value(group, timeout=FORM_TIMEOUT_MS)

    def expect_city(self, city: str) -> None:
        expect(self._city).to_have_value(city, timeout=FORM_TIMEOUT_MS)

    def expect_general_fields_only(self) -> None:
        """A non-party group swaps the party block (station, mobile) for GST Applicable."""
        expect(self.page.get_by_text(GST_APPLICABLE_LABEL, exact=True)).to_be_visible()
        expect(self._station).to_be_hidden()
        expect(self._mobile).to_be_hidden()

    @property
    def _name(self) -> Locator:
        # Why ids: the form has no test ids and its labels are not tied to the inputs.
        return self.page.locator("#txtlegername")

    @property
    def _ledger_type(self) -> Locator:
        return self.page.locator("#ddlLedgerType")

    @property
    def _gstin(self) -> Locator:
        return self.page.locator("#txtGSTNo").first

    @property
    def _group(self) -> Locator:
        return self.page.locator("#drpAccountGroup")

    @property
    def _station(self) -> Locator:
        return self.page.locator("#ddlstation")

    @property
    def _mobile(self) -> Locator:
        return self.page.locator("#txtMobile")

    @property
    def _city(self) -> Locator:
        return self.page.locator("#ddlCity")
