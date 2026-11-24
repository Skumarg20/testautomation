"""`/other/createStore` (`Component/Online-Store/app-onlinestore.component.html`) for a company with no store.

The page opens on a banner "CREATING ONLINE STORE" with a "Create Store" button (`:649`); the form with the
tabs "Marg Mart" and "Online Store" (`:26,29`) shows after it. The form's labels have no `for` and the inputs
no name or aria-label, so fields are found by their Angular `formcontrolname` (CSS, see `_control`).

`save` submits the active tab (`.html:519-566`): on "Online Store" it posts `SaveOnlineStore`, which creates a
store for good, and on "Marg Mart" it goes through Marg's BSS server, `MargMart/Save` and margmart.com. Only
the permanent OS-04 test lets that through; every other caller stubs it
(`pages/online_store/store_endpoints.py`).
"""

from enum import Enum

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage

PAGE_TIMEOUT_MS = 30_000
BANNER_HEADING = "CREATING ONLINE STORE"
CREATE_STORE_BUTTON = "Create Store"
FORM_HEADING = "Store Details"
OWN_STORE_TAB = "Online Store"
MARG_MART_TAB = "Marg Mart"


class StoreField(Enum):
    """The form control names of the store form (app-onlinestore.component.ts createForm)."""

    STORE_NAME = "storeName"
    EMAIL = "emailAddress"
    MOBILE = "mobileNo"
    GSTIN = "GSTIN"
    ADDRESS_LINE_1 = "storeAddress1"
    WHOLE_DAY_START = "WholeDayStartTime"
    WHOLE_DAY_END = "WholeDayEndtTime"


class CreateStorePage(BasePage):
    def expect_banner(self) -> None:
        expect(self.page.get_by_role("heading", name=BANNER_HEADING)).to_be_visible(timeout=PAGE_TIMEOUT_MS)
        expect(self._create_store_button).to_be_visible()

    def start(self) -> None:
        self._create_store_button.click()
        expect(self.page.get_by_role("heading", name=FORM_HEADING)).to_be_visible(timeout=PAGE_TIMEOUT_MS)

    def expect_tab(self, name: str) -> None:
        expect(self.page.get_by_role("tab", name=name)).to_be_visible()

    def choose_tab(self, name: str) -> None:
        self.page.get_by_role("tab", name=name).click()

    def fill(self, field: StoreField, value: str) -> None:
        self._control(field.value).fill(value)

    def save(self) -> None:
        """The footer's Save (`#btn-Save`); its caption span can be hidden, so it is found by its title."""
        self.page.get_by_title("Save", exact=True).click()

    def value_of(self, field: StoreField) -> str:
        return self._control(field.value).input_value()

    def whole_day_is_chosen(self) -> bool:
        # Why CSS: the radio's caption is a sibling span, not a label; its id is the only handle.
        return self.page.locator("#wholeday").is_checked()

    def day_is_ticked(self, day: str) -> bool:
        """`day` is the English weekday name, which is also the checkbox's form control name."""
        return self._control(day).is_checked()

    @property
    def _create_store_button(self) -> Locator:
        return self.page.get_by_role("button", name=CREATE_STORE_BUTTON, exact=True)

    def _control(self, control_name: str) -> Locator:
        # Why CSS: the labels are not tied to their inputs (no `for`, no aria-label); see the docstring.
        return self.page.locator(f"[formcontrolname='{control_name}']").first
