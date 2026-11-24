"""The Rack field of the Create / Modify Item form (shown when Control Room "Rack Master" is Yes)."""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.masters.typeahead import Typeahead

FIELD_TIMEOUT_MS = 30_000


class ItemRackField(BasePage):
    def choose(self, rack: str) -> None:
        Typeahead(self.page).choose(self._field, rack)

    def expect_value(self, rack: str) -> None:
        expect(self._field).to_have_value(rack, timeout=FIELD_TIMEOUT_MS)

    @property
    def _field(self) -> Locator:
        return self.page.get_by_placeholder("Rack", exact=True)
