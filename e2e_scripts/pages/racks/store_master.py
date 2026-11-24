"""Master > Inventory Master > Store: the Store List and the Create / Modify Store form."""

from playwright.sync_api import Locator, expect

from pages.accounting.loader import Loader
from pages.accounting.toasts import Toasts
from pages.base_page import BasePage
from pages.components.app_texts import RECORD_SAVED, RECORD_UPDATED
from pages.racks.master_grid import MasterGrid
from test_data.racks import StoreSpec

# The page behind Master > Inventory Master > Store, seen live 2026-10-09.
STORE_LIST_PATH = "/mstr/store"
FORM_TIMEOUT_MS = 30_000


class StoreList(MasterGrid):
    delete_question = "Are you sure you want to delete?"

    def open(self) -> None:
        """By URL, like the Rack List: after a page opened by URL the sidebar does not always expand."""
        self.goto(STORE_LIST_PATH)
        Loader(self.page).wait_until_idle()
        self._wait_until_loaded()


class StoreForm(BasePage):
    def open_new(self) -> None:
        StoreList(self.page).open()
        self.page.get_by_role("button", name="Create/F2").click()
        expect(self._name).to_be_visible(timeout=FORM_TIMEOUT_MS)

    def open_existing(self, name: str) -> None:
        stores = StoreList(self.page)
        stores.open()
        stores.open_edit(name)
        expect(self._name).to_have_value(name, timeout=FORM_TIMEOUT_MS)

    def enter(self, store: StoreSpec) -> None:
        self._code.fill(store.code)
        self.enter_name(store.name)

    def enter_code_only(self, store: StoreSpec) -> None:
        self._code.fill(store.code)

    def enter_name(self, name: str) -> None:
        self._name.fill(name)

    def save(self) -> None:
        self.page.locator("#btn-Save").click()

    def update(self) -> None:
        self.page.locator("#btn-Update").click()

    def expect_saved(self) -> None:
        Toasts(self.page).expect_success_saying(RECORD_SAVED)

    def expect_updated(self) -> None:
        Toasts(self.page).expect_success_saying(RECORD_UPDATED)

    def expect_still_open(self) -> None:
        expect(self._name).to_be_visible()

    @property
    def _code(self) -> Locator:
        # Why ids: the form has no test ids and its labels are not tied to the inputs.
        return self.page.locator("#txtStoreCode")

    @property
    def _name(self) -> Locator:
        return self.page.locator("#txtStoreName")
