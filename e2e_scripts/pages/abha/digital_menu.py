"""The sidebar's Digital menu and its ABHA child, found by the app's menu ids.

Why CSS: the menu labels come from the server and the Control Room (`controlRoomMenuName`), so they are not
stable names; the element ids carry the fixed menu values (`Layout/menu.component.html:5,30,54,81,92,104`):
Digital is 92385071021 and its ABHA child 92385071029 (`Services/Common.service.ts:1212`). A parent with
children renders as `#menu<value>`, a leaf as `#menu-<index>-<value>`.

The Digital parent is hidden when it has no children (`Layout/menu.component.ts:1896-1903`, MBC-806); the
ABHA child is dropped when Control Room field 4426 is blank (`Common.service.ts:1212-1216`) or the company is
not a chemist (`Layout/menu.component.ts:1833`).
"""

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage

DIGITAL_MENU = "92385071021"
ABHA_MENU = "92385071029"
MENU_READY_ITEM = ("Master",)
SUBMENU_TIMEOUT_MS = 10_000


class DigitalMenu(BasePage):
    def wait_until_shown(self) -> None:
        DashboardPage(self.page).expect_menu_items(MENU_READY_ITEM)

    def digital_has_children(self) -> bool:
        return self._parent(DIGITAL_MENU).count() > 0

    def expect_digital_hidden(self) -> None:
        expect(self._any_entry(DIGITAL_MENU)).to_have_count(0)

    def expect_abha_entry_present(self) -> None:
        expect(self._any_entry(ABHA_MENU).first).to_be_attached()

    def expect_abha_entry_absent(self) -> None:
        expect(self._any_entry(ABHA_MENU)).to_have_count(0)

    def open_abha(self) -> None:
        self._parent(DIGITAL_MENU).click()
        abha_toggle = self.page.locator(f'a[href$="-{ABHA_MENU}"]')
        expect(abha_toggle).to_be_visible(timeout=SUBMENU_TIMEOUT_MS)
        abha_toggle.click()

    def expect_abha_offers(self, entry: str) -> None:
        submenu = self.page.locator(f'menu[id$="-{ABHA_MENU}"]')
        expect(submenu.get_by_text(entry, exact=True)).to_be_visible(timeout=SUBMENU_TIMEOUT_MS)

    def _parent(self, menu_value: str) -> Locator:
        return self.page.locator(f"#menu{menu_value}")

    def _any_entry(self, menu_value: str) -> Locator:
        return self.page.locator(f'#menu{menu_value}, a[id^="menu-"][id$="-{menu_value}"]')
