"""Sale Bill Setting window (the Control Room button on an open sale bill): read and change one drop-down.

The window is `salebill.setting.html`; every setting below is a `<select>` with the id given here and sits on
the "Basic Setting" or "Advance Setting" tab. A setting is chosen by the option `value` the template binds
(`value="{{item.value}}"`), because the labels come from the API and are not in the source. Closing the
window keeps the choice, the way `GstConfiguration` already relies on. Locators are unverified live.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage

WINDOW_TIMEOUT_MS = 15_000
BASIC = "Basic Setting"
ADVANCE = "Advance Setting"


@dataclass(frozen=True)
class SelectSetting:
    element_id: str
    tab: str
    title: str


ASK_PARTY = SelectSetting("txtaskpartyinretailbilling", BASIC, "Ask Party in Retail Billing")
CURSOR_WAIT = SelectSetting("txtCursorshouldwait", BASIC, "Cursor wait on")
LAST_DEAL = SelectSetting("lastDealInSale", BASIC, "Last deal in Sale")
MODE_OF_PAYMENT = SelectSetting("txtisModeofPayment", BASIC, "Mode of Payment Required")
AMOUNT_CALCULATION = SelectSetting("amountCalculationOnBilling", ADVANCE, "Amount Calculation On Billing")
ASK_BILL_NO = SelectSetting("askBillNo", ADVANCE, "Ask Bill No.")
ASK_SALE_TYPE = SelectSetting("txtisSaleTypeForBilling", ADVANCE, "Ask Sale Type at the time of Billing")
ASK_NET_RATE = SelectSetting("askNetRate", ADVANCE, "Ask Net Rate")
ASK_ORDER_NO = SelectSetting("askOrderNoOrderDeliveryDate", ADVANCE, "Ask Order No., Order Date")
MR_REQUIRED = SelectSetting("txtisMR", ADVANCE, "MR required?")
PICK_MR_FROM = SelectSetting("mrFrom", ADVANCE, "Pick MR From")
ITEM_REPEATED = SelectSetting("IndicateIfItemRepeatedInBill", ADVANCE, "Indicate if Item Repeated in Bill")
BILLING_RATE_ZERO = SelectSetting("IndicateIfBillingRateIsZero", ADVANCE, "Indicate if Billing Rate is Zero")
BATCH_WINDOW_INDEX = SelectSetting("openBatchWindowIndexOn", ADVANCE, "Batch window index on")
FREE_QUANTITY = SelectSetting("freeQtyConditionOnSale", ADVANCE, "Free Quantity Required in Sale")
FREE_QUANTITY_DECIMAL = SelectSetting("freeQuantityRequiredinDecimal", ADVANCE, "Free Quantity in Decimal")
FREE_DEAL_FROM = SelectSetting("dealFrom", ADVANCE, "Free Deal From")
UPDATE_CHANGED_RATE = SelectSetting("updateChangedRate", ADVANCE, "Update Changed Rate")
UPDATE_CHANGED_DISCOUNT = SelectSetting("updateChangedDiscount", ADVANCE, "Update Changed Discount")
LOSS_ON_BILL = SelectSetting("lossOnBillAskFor", ADVANCE, "Loss on Bill ask for")
LOT_RATE_CALCULATION = SelectSetting("lotRateCalculation", ADVANCE, "Lot Rate Calculation")


class OptionMissingError(LookupError):
    def __init__(self, setting: SelectSetting, value: str, offered: list[str]) -> None:
        super().__init__(f'"{setting.title}" has no option with value "{value}"; it offers {offered}')


class SettingNotRestoredError(AssertionError):
    def __init__(self, setting: SelectSetting, original: str, now: str) -> None:
        super().__init__(f'Sale setting "{setting.title}" is "{now}" after the restore, it was "{original}"')


class SaleSettings(BasePage):
    def offered_values(self, setting: SelectSetting) -> list[str]:
        select = self._open(setting)
        offered = [option.get_attribute("value") or "" for option in select.locator("option").all()]
        self._close()
        return offered

    def read(self, setting: SelectSetting) -> str:
        select = self._open(setting)
        value = select.input_value()
        self._close()
        return value

    def write(self, setting: SelectSetting, wanted: str) -> None:
        """`wanted` is an option value, or failing that an option label (case and spacing ignored)."""
        select = self._open(setting)
        options = [
            (option.get_attribute("value") or "", option.inner_text())
            for option in select.locator("option").all()
        ]
        value = _resolve(wanted, options)
        if value is None:
            self._close()
            raise OptionMissingError(setting, wanted, [f"{v} ({label.strip()})" for v, label in options])
        select.select_option(value=value)
        self._close()

    def _open(self, setting: SelectSetting) -> Locator:
        self.page.locator("#aControlRoomSetting").click()
        select = self.page.locator(f"#{setting.element_id}")
        if not select.is_visible():
            self._window.get_by_text(setting.tab, exact=True).click()
        expect(select).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        return select

    def _close(self) -> None:
        self._window.locator("h2.headingItem button").click()
        expect(self._window).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)

    @property
    def _window(self) -> Locator:
        # Why CSS: the settings window is a plain div with this class (also used by DocumentHeader).
        return self.page.locator(".dashboardSetting").last


def _resolve(wanted: str, options: list[tuple[str, str]]) -> str | None:
    for value, _ in options:
        if value == wanted:
            return value
    plain = " ".join(wanted.split()).casefold()
    for value, label in options:
        if " ".join(label.split()).casefold() == plain:
            return value
    return None


class _ScreenWithSettings(Protocol):
    page: Page

    def reopen(self) -> None: ...


@contextmanager
def setting_held(screen: _ScreenWithSettings, setting: SelectSetting, value: str) -> Iterator[str]:
    """Sets `setting` to the option `value` for the block, yields the original value, then puts it back.

    The screen must have a bill open on entry. The original is read before anything is written, the restore
    runs when the test fails, and a value left wrong is an error because the tenant is shared.
    """
    settings = SaleSettings(screen.page)
    original = settings.read(setting)
    if original != value:
        settings.write(setting, value)
    try:
        yield original
    finally:
        if original != value:
            screen.reopen()
            settings.write(setting, original)
            now = settings.read(setting)
            if now != original:
                raise SettingNotRestoredError(setting, original, now)
