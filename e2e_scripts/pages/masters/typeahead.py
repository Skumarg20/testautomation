"""The "Search here.." typeahead fields of the master forms (Account Group, Under Group, Station)."""

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage

SUGGESTIONS_TIMEOUT_MS = 5_000
TYPE_ATTEMPTS = 3
KEY_DELAY_MS = 100


class TypeaheadError(AssertionError):
    def __init__(self, text: str) -> None:
        super().__init__(f'No suggestion "{text}" appeared after {TYPE_ATTEMPTS} tries')


class Typeahead(BasePage):
    def choose(self, field: Locator, text: str) -> None:
        """Retypes when needed: keys typed before the master list has loaded are lost."""
        suggestion = self.page.get_by_role("listbox").get_by_role("option", name=text, exact=True)
        for _ in range(TYPE_ATTEMPTS):
            self._type(field, text)
            if appears_within(suggestion, SUGGESTIONS_TIMEOUT_MS):
                suggestion.click()
                expect(field).to_have_value(text)
                return
        raise TypeaheadError(text)

    @staticmethod
    def _type(field: Locator, text: str) -> None:
        field.click()
        field.fill("")
        field.press_sequentially(text, delay=KEY_DELAY_MS)
