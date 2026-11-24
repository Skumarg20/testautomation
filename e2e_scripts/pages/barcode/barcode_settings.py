"""Control Room > "Barcode Duplicate allowed?". Tenant-wide: whoever changes it restores it."""

from typing import cast

from pages.settings.control_room import ControlRoom, YesNo

DUPLICATE_ALLOWED = "Barcode Duplicate allowed?"
CHOICES = ("Yes", "No")


class UnexpectedChoiceError(AssertionError):
    def __init__(self, text: str) -> None:
        super().__init__(f'"{DUPLICATE_ALLOWED}" shows "{text}", expected one of {CHOICES}')


class BarcodeDuplicateSetting(ControlRoom):
    def current(self) -> YesNo:
        """Reads the choice and leaves the Control Room with Escape, which closes it unchanged."""
        self.page.wait_for_load_state("load")
        self.open_button.click()
        self.configure_button.click()
        self.search.click()
        self.search.press_sequentially(DUPLICATE_ALLOWED)
        # Why CSS: a select exposes its chosen option only through the :checked state.
        text = self._dropdown_for(DUPLICATE_ALLOWED).locator("option:checked").inner_text().strip()
        self.page.keyboard.press("Escape")
        if text not in CHOICES:
            raise UnexpectedChoiceError(text)
        return cast(YesNo, text)

    def change_to(self, choice: YesNo) -> None:
        self._set_option(DUPLICATE_ALLOWED, choice)
