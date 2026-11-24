"""The Create / Modify dialogs of Route, Station and Area (specs/route-station-area-masters.md)."""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.confirmation import Confirmation
from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.masters.master_toasts import MasterToasts
from pages.masters.typeahead import Typeahead
from pages.other_masters.master_lists import AreaList, OtherMasterList, RouteList, StationList
from test_data.other_masters import AreaSpec

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
SAVED_MESSAGE = re.compile("Record Saved Successfully", re.IGNORECASE)
UPDATED_MESSAGE = re.compile("Record Updated Successfully", re.IGNORECASE)
FORM_TIMEOUT_MS = 30_000
KEY_DELAY_MS = 50


class NamedMasterForm(BasePage):
    """A dialog whose one required field is the master's name; subclasses say which list and field."""

    NAME_FIELD_ID = ""

    def open_new(self) -> None:
        records = self._list()
        records.open()
        records.open_create()
        expect(self._name).to_be_visible(timeout=FORM_TIMEOUT_MS)

    def open_existing(self, name: str) -> None:
        records = self._list()
        records.open()
        records.open_edit(name)
        expect(self._name).to_have_value(name, timeout=FORM_TIMEOUT_MS)

    def enter_name(self, name: str) -> None:
        self._name.fill(name)

    def save(self) -> None:
        self.page.get_by_role("button", name="F10 Save").click()

    def update(self) -> None:
        self.page.get_by_role("button", name="F10 Update").click()

    def expect_saved(self) -> None:
        Toasts(self.page).expect_success_saying(SAVED_MESSAGE)

    def expect_updated(self) -> None:
        Toasts(self.page).expect_success_saying(UPDATED_MESSAGE)

    def expect_refused_with(self, message: re.Pattern[str]) -> None:
        MasterToasts(self.page).expect_error_saying(message)
        expect(self._name).to_be_visible()

    def expect_still_open(self) -> None:
        expect(self._dialog).to_be_visible()
        expect(self._name).to_be_visible()

    def expect_still_open_saying(self, message: re.Pattern[str]) -> None:
        """An inline note or a "!" tooltip on a field; the dialog stays open."""
        expect(self._dialog).to_contain_text(message, timeout=FORM_TIMEOUT_MS)
        expect(self._name).to_be_visible()

    def close_discarding(self) -> None:
        self.page.get_by_role("button", name="Esc Close").click()
        Confirmation(self.page).answer_yes_if_asked()
        expect(self._name).to_be_hidden(timeout=FORM_TIMEOUT_MS)

    def _list(self) -> OtherMasterList:
        raise NotImplementedError

    @property
    def _dialog(self) -> Locator:
        return self.page.get_by_role("dialog")

    @property
    def _name(self) -> Locator:
        # Why ids: the dialogs have no test ids and their labels are not tied to the inputs.
        return self.page.locator(f"#{self.NAME_FIELD_ID}")


class RouteForm(NamedMasterForm):
    NAME_FIELD_ID = "txtRouteName"

    def _list(self) -> OtherMasterList:
        return RouteList(self.page)


class StationForm(NamedMasterForm):
    NAME_FIELD_ID = "txtStaionName"  # sic: the app's id

    def _list(self) -> OtherMasterList:
        return StationList(self.page)


class AreaForm(NamedMasterForm):
    NAME_FIELD_ID = "txtAreaName"

    def enter(self, area: AreaSpec) -> None:
        Typeahead(self.page).choose(self._route, area.route)
        self.enter_name(area.name)

    def type_new_name(self, name: str) -> None:
        """Key by key: after `fill` the duplicate-name check refuses even a new name (spec N4)."""
        self._name.press("Control+a")
        self._name.press_sequentially(name, delay=KEY_DELAY_MS)

    def _list(self) -> OtherMasterList:
        return AreaList(self.page)

    @property
    def _route(self) -> Locator:
        return self.page.locator("#autoCompleteRoute")
