"""Reads Control Room options, so a test that changes one can put the tenant's original value back."""

from typing import cast, get_args

from pages.settings.control_room import BarcodeRequired, ControlRoom, DateBilling, YesNo

BARCODE_REQUIRED = "Barcode Required"


class UnexpectedOptionError(AssertionError):
    def __init__(self, name: str, text: str, choices: tuple[str, ...]) -> None:
        super().__init__(f'"{name}" shows "{text}", expected one of {choices}')


class ControlRoomState(ControlRoom):
    def current_barcode_required(self) -> BarcodeRequired:
        return cast(BarcodeRequired, self._current(BARCODE_REQUIRED, get_args(BarcodeRequired)))

    def current_date_billing(self, setting: DateBilling) -> YesNo:
        return cast(YesNo, self._current(setting, get_args(YesNo)))

    def current_switch(self, name: str) -> YesNo:
        """Any Yes/No option, by its full Particulars text."""
        return cast(YesNo, self._current(name, get_args(YesNo)))

    def _current(self, name: str, choices: tuple[str, ...]) -> str:
        """Reads the option and leaves the Control Room with Escape, which closes it unchanged."""
        self.page.wait_for_load_state("load")
        self.open_button.click()
        self.configure_button.click()
        self.search.click()
        self.search.press_sequentially(name)
        # Why CSS: a select exposes its chosen option only through the :checked state.
        text = self._dropdown_for(name).locator("option:checked").inner_text().strip()
        self.page.keyboard.press("Escape")
        if text not in choices:
            raise UnexpectedOptionError(name, text, choices)
        return text
