"""Stock Management > Bill of Materials and Conversion menu entries, and whether the company shows them.

Both sub-menus appear only when their Control Room switch is Yes ("Bill Of Material(BOM)", S.No 367, and
"One To Many & Many To One required?", S.No 21). Seen live 2026-10-12: both No on GANE29 and PNC2, so the
Stock Management menu lists only Stock Transfer and Physical Stock there.
"""

from enum import Enum

from playwright.sync_api import expect

from pages.purchase.documents.feedback import appears_within
from pages.purchase.documents.navigation import INVENTORY_MASTER, MASTER_GROUP, ModuleMenu
from pages.stock.stock_menu import STOCK_GROUP

SUBMENU_TIMEOUT_MS = 5_000


class ManufacturingScreen(Enum):
    """A screen and the Stock Management sub-menu (KB `#5edef903`, `#25e8dd21`) it sits under."""

    MATERIAL_MASTER = ("Bill of Materials", "Material Master")
    MATERIAL_ISSUE = ("Bill of Materials", "Material Issue")
    MATERIAL_RECEIVE = ("Bill of Materials", "Material Received")
    ONE_TO_MANY = ("Conversion", "One to many")
    MANY_TO_ONE = ("Conversion", "Many to one")

    @property
    def submenu(self) -> str:
        return self.value[0]

    @property
    def entry(self) -> str:
        return self.value[1]


BILL_OF_MATERIALS = ManufacturingScreen.MATERIAL_MASTER.submenu
CONVERSION = ManufacturingScreen.ONE_TO_MANY.submenu


class ManufacturingMenu(ModuleMenu):
    def offers(self, screen: ManufacturingScreen) -> bool:
        self._open_stock_group()
        return appears_within(self._parent_link(screen.submenu), SUBMENU_TIMEOUT_MS)

    def expect_entries_under(self, submenu: str) -> None:
        """MF-01 / MF-29: every screen of the sub-menu is listed once the switch is on."""
        self._open_stock_group()
        self._expand(self._parent_link(submenu))
        for screen in ManufacturingScreen:
            if screen.submenu == submenu:
                expect(self._child_link(screen.entry)).to_be_visible(timeout=SUBMENU_TIMEOUT_MS)

    def expect_screen_missing(self, screen: ManufacturingScreen) -> None:
        """MF-34: a role without the screen's right does not see its entry."""
        self._open_stock_group()
        expect(self._child_link(screen.entry)).to_have_count(0)

    def open_screen(self, screen: ManufacturingScreen) -> None:
        self._open_stock_group()
        self._expand(self._parent_link(screen.submenu))
        self._child_link(screen.entry).click()
        self._settle()

    def _open_stock_group(self) -> None:
        self._expand_menu(STOCK_GROUP)
        self._expand(self._group(STOCK_GROUP))


class InventoryMasterMenu(ModuleMenu):
    """Master > Inventory Master, where the KB puts "BMR Type" (KB `onedrive_processed_data.csv#a835ce0d`)."""

    def expect_entry(self, name: str) -> None:
        self._expand_menu(MASTER_GROUP)
        self._expand(self._group(MASTER_GROUP))
        parent = self._parent_link(INVENTORY_MASTER)
        expect(parent).to_be_visible(timeout=SUBMENU_TIMEOUT_MS)
        self._expand(parent)
        expect(self._child_link(name)).to_be_visible(timeout=SUBMENU_TIMEOUT_MS)
