"""Master > Inventory Master > Unit List and HSN/SAC List: search, edit, delete and the values in a row."""

from playwright.sync_api import expect

from pages.inventory.item_alert import ItemAlert
from pages.masters.master_list import ROW_TIMEOUT_MS, MasterList
from pages.unit_hsn.inventory_masters_menu import InventoryMastersMenu

UNIT_DELETE_QUESTION = "Are you sure you want to delete?"
SEARCH_BY_HSN_CODE = "HSN Code"
# The sidebar entry "HSN / SAC" could not be matched by its link name, so the list is opened by its route.
HSN_LIST_PATH = "/mstr/hsn"


class InventoryMasterList(MasterList):
    def _expect_row_value(self, key: str, value: str) -> None:
        self.search(key)
        cell = self._row(key).get_by_role("gridcell", name=value, exact=True)
        expect(cell).to_have_count(1, timeout=ROW_TIMEOUT_MS)


class UnitList(InventoryMasterList):
    """Rows are found by unit name; the row also shows the UQC, e.g. "BOX-BOX"."""

    def open(self) -> None:
        InventoryMastersMenu(self.page).open_unit_list()
        self._wait_until_loaded()

    def confirm_delete(self) -> None:
        alert = ItemAlert(self.page)
        alert.expect_asking(UNIT_DELETE_QUESTION)
        alert.answer_yes()

    def expect_uqc(self, name: str, uqc: str) -> None:
        self._expect_row_value(name, uqc)


class HsnList(InventoryMasterList):
    """Rows are found by HSN code (the list is set to search by code); the row also shows the name."""

    def open(self) -> None:
        self.goto(HSN_LIST_PATH)
        self._wait_until_loaded()
        self.page.get_by_role("combobox").select_option(SEARCH_BY_HSN_CODE)

    def expect_name(self, code: str, name: str) -> None:
        self._expect_row_value(code, name)
