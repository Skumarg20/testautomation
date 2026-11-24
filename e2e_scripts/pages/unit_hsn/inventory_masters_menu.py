"""The sidebar entry Master > Inventory Master > Unit."""

from pages.accounting.accounting_menu import MASTER_GROUP, AccountingMenu

UNIT_PATH = ("Inventory Master", "Unit")


class InventoryMastersMenu(AccountingMenu):
    def open_unit_list(self) -> None:
        self._open(MASTER_GROUP, UNIT_PATH)
