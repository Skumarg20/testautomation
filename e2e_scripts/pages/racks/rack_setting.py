"""Control Room > Configure > "Rack Master": shows the Rack field on the item form. Tenant-wide."""

from typing import Literal

from playwright.sync_api import expect

from pages.settings.control_room import ControlRoom

RackMasterValue = Literal["Yes", "No"]
RACK_MASTER = "Rack Master"
SETTING_TIMEOUT_MS = 30_000


class RackMasterSetting(ControlRoom):
    def current(self) -> RackMasterValue:
        """Reads the value and leaves the Control Room with Escape, which saves nothing."""
        self.page.wait_for_load_state("load")
        self.open_button.click()
        self.configure_button.click()
        self.search.click()
        self.search.press_sequentially(RACK_MASTER)
        dropdown = self._dropdown_for(RACK_MASTER)
        expect(dropdown).to_be_visible(timeout=SETTING_TIMEOUT_MS)
        value: RackMasterValue = (
            "Yes" if dropdown.evaluate("s => s.selectedOptions[0].text") == "Yes" else "No"
        )
        self.page.keyboard.press("Escape")
        return value

    def change_to(self, value: RackMasterValue) -> None:
        self._set_option(RACK_MASTER, value)
        # The item form reads the setting when the app loads.
        self.page.reload()
