"""Test-owned stores and racks: made through the UI, remembered, and deleted in teardown."""

from playwright.sync_api import Page

from pages.components.owned_records import deletion_steps
from pages.components.undo import undo_all
from pages.racks.rack_master import RackForm, RackList
from pages.racks.store_master import StoreForm, StoreList
from test_data.racks import MAIN_STORE, RackDataFactory, RackSpec, StoreSpec


class RackRecords:
    """Every record is remembered before the UI is asked to save it, so a half-done save is cleaned too."""

    def __init__(self, page: Page, data: RackDataFactory) -> None:
        self._page = page
        self._data = data
        self._stores: list[str] = []
        self._racks: list[str] = []

    def new_store(self) -> StoreSpec:
        store = self._data.store()
        self.own_store_name(store.name)
        return store

    def new_rack(self, store: str = MAIN_STORE) -> RackSpec:
        rack = self._data.rack(store)
        self.own_rack_name(rack.name)
        return rack

    def own_store_name(self, name: str) -> None:
        self._stores.append(name)

    def own_rack_name(self, name: str) -> None:
        self._racks.append(name)

    def saved_store(self) -> StoreSpec:
        store = self.new_store()
        form = StoreForm(self._page)
        form.open_new()
        form.enter(store)
        form.save()
        form.expect_saved()
        return store

    def saved_rack(self, store: str = MAIN_STORE) -> RackSpec:
        return self.save_rack(self._data.rack(store))

    def save_rack(self, rack: RackSpec) -> RackSpec:
        self.own_rack_name(rack.name)
        form = RackForm(self._page)
        form.open_new()
        form.enter(rack)
        form.save()
        form.expect_saved()
        return rack

    def delete_all(self) -> None:
        """Racks go first: they belong to a store. Every delete runs; the failures are reported at the end."""
        undo_all(
            [
                *deletion_steps("rack", RackList(self._page), self._racks),
                *deletion_steps("store", StoreList(self._page), self._stores),
            ]
        )
