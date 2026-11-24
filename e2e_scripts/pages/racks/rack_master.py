"""The Rack List (route /rack) and its Create / Modify Rack dialog."""

from playwright.sync_api import Locator, expect

from pages.accounting.loader import Loader
from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.components.app_texts import RECORD_SAVED, RECORD_UPDATED
from pages.masters.typeahead import Typeahead
from pages.racks.master_grid import ROW_TIMEOUT_MS, MasterGrid
from test_data.racks import RackSpec

# The sidebar has no Rack entry on the QA company (specs/rack-warehouse-management.md, D1).
RACK_LIST_PATH = "/rack"
FORM_TIMEOUT_MS = 30_000
LIST_TIMEOUT_MS = 60_000


class RackList(MasterGrid):
    delete_question = "Are you sure you want to delete the selected Record?"

    def open(self) -> None:
        self.goto(RACK_LIST_PATH)
        expect(self.page.get_by_role("button", name="Create/F2")).to_be_visible(timeout=LIST_TIMEOUT_MS)
        Loader(self.page).wait_until_idle()
        self._wait_until_loaded()

    def expect_rack_in_store(self, rack: RackSpec) -> None:
        self.search(rack.name)
        store_cell = self.page.get_by_role("gridcell", name=rack.store, exact=True)
        expect(self._row(rack.name).filter(has=store_cell)).to_have_count(1, timeout=ROW_TIMEOUT_MS)


class RackForm(BasePage):
    def open_new(self) -> None:
        RackList(self.page).open()
        self.page.get_by_role("button", name="Create/F2").click()
        expect(self._name).to_be_visible(timeout=FORM_TIMEOUT_MS)

    def open_existing(self, name: str) -> None:
        racks = RackList(self.page)
        racks.open()
        racks.open_edit(name)
        expect(self._name).to_have_value(name, timeout=FORM_TIMEOUT_MS)

    def enter(self, rack: RackSpec) -> None:
        self.choose_store(rack.store)
        self.enter_name(rack.name)

    def choose_store(self, store: str) -> None:
        Typeahead(self.page).choose(self._store, store)

    def enter_name(self, name: str) -> None:
        self._name.fill(name)

    def save(self) -> None:
        self._dialog.locator("#btn-Save").click()

    def update(self) -> None:
        self._dialog.locator("#btn-Update").click()

    def expect_saved(self) -> None:
        Toasts(self.page).expect_success_saying(RECORD_SAVED)

    def expect_updated(self) -> None:
        Toasts(self.page).expect_success_saying(RECORD_UPDATED)

    def expect_still_open(self) -> None:
        expect(self._name).to_be_visible()

    @property
    def _dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(has=self.page.locator("#name"))

    @property
    def _store(self) -> Locator:
        # Why ids: the dialog has no test ids; the store box is named only by its "Search here.." placeholder.
        return self.page.locator("#storeNameDrp")

    @property
    def _name(self) -> Locator:
        return self.page.locator("#name")
