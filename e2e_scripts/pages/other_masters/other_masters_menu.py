"""The sidebar entries of Master > Other Master. Route has no entry on the garments company (spec N1)."""

from pages.accounting.accounting_menu import MASTER_GROUP, AccountingMenu

AREA_PATH = ("Other Master", "Area")
STATION_PATH = ("Other Master", "Station")


class OtherMastersMenu(AccountingMenu):
    def open_area_list(self) -> None:
        self._open(MASTER_GROUP, AREA_PATH)

    def open_station_list(self) -> None:
        self._open(MASTER_GROUP, STATION_PATH)
