"""The left-hand menu entries for stock: Stock Management screens and the item list."""

from enum import Enum

from pages.purchase.documents.navigation import ModuleMenu

STOCK_GROUP = "Stock Management"


class StockScreen(Enum):
    TRANSFER = "Stock Transfer"
    PHYSICAL = "Physical Stock"


class StockMenu(ModuleMenu):
    def open_stock_screen(self, screen: StockScreen) -> None:
        self._expand_menu(STOCK_GROUP)
        self._expand(self._group(STOCK_GROUP))
        self._parent_link(screen.value).click()
        self._settle()
