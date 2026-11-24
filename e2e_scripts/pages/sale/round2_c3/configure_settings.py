"""The Sale Bill Setting window's "Configure" sub-windows, and the other settings round 2 reads.

Some settings sit behind a Configure button of the Setting window, not in the window itself: Expiry & MFG
(`openConfigureWindow('expiry')`, `UtililityComponent/ControlRoom/salebill.setting.ts:182`), Loss on bill
(`'loss'`) and Minimum/Maximum level (`'maxormin'`). Each opens a modal with its own controls and a Save
button that closes it (`txn-expiry-setting.html:112-116`). `ConfigureSettings` has the same `current` /
`choose` surface as `SaleBillSettings`, so `HeldOptions` can hold a field of either. A control may be a
drop-down (chosen by its text) or a text box (filled). Unverified live.
"""

from dataclasses import dataclass

from playwright.sync_api import Locator, expect

from pages.sale.manual.option_settings import (
    ADVANCE_TAB,
    SETTING_TIMEOUT_MS,
    SaleBillSettings,
    SettingField,
    index_of_option,
)

MODAL = "ngb-modal-window:not([aria-hidden='true'])"
INPUT_TAG = "input"


@dataclass(frozen=True)
class ConfigureField(SettingField):
    """A control inside a Configure window: `button_id` opens the window, `select_id` is the control."""

    button_id: str = ""


EXPIRY_BUTTON = "ExpiryMFG"
LOSS_BUTTON = "loss"
MIN_MAX_BUTTON = "btnMaxorMin"
CESS_BUTTON = "btnSurcharge1"
NEAR_EXPIRED = ConfigureField(
    "nearExpiredItemsonBilling", "Near expired items on billing", True, EXPIRY_BUTTON
)
NEAR_EXPIRY_DAYS = ConfigureField(
    "txtcalculateNearExpiryDays", "Calculate Near Expiry Days", True, EXPIRY_BUTTON
)
EXPIRED_ITEMS = ConfigureField(
    "allowRateZERORateorBanIndicateforExpiredItems",
    "Allow Rate/ZERO Rate or Ban/Indicate for Expired Items",
    True,
    EXPIRY_BUTTON,
)
LOSS_INDICATION = ConfigureField(
    "NetLossAndMarginLossIndication", "Net Loss and Margin Loss Indication", True, LOSS_BUTTON
)
MINIMUM_LEVEL_INDICATION = ConfigureField(
    "indicateifstockgoingminimum", "Indicate if Stock going Minimum/Maximum", True, MIN_MAX_BUTTON
)


class ConfigureSettings(SaleBillSettings):
    """Works on the sale bill that is open on the page, like `SaleBillSettings`."""

    def current(self, field: SettingField) -> str:
        control = self._open(field)
        text = control.input_value() if self._is_text_box(control) else self._selected_text(control)
        self._close()
        return text

    def choose(self, field: SettingField, wanted: str) -> None:
        control = self._open(field)
        if self._is_text_box(control):
            control.fill(wanted)
        else:
            offered = [text.strip() for text in control.locator("option").all_inner_texts()]
            control.select_option(index=index_of_option(field.label, wanted, offered))
        self._close()

    def _open(self, field: SettingField) -> Locator:
        if not isinstance(field, ConfigureField):
            return super()._open(field)
        self.page.locator("#aControlRoomSetting").locator("visible=true").first.click()
        self.page.get_by_text(ADVANCE_TAB, exact=True).click()
        self.page.locator(f"#{field.button_id}").click()
        control = self._modal.locator(f"#{field.select_id}")
        expect(control).to_be_visible(timeout=SETTING_TIMEOUT_MS)
        return control

    def _close(self) -> None:
        if self._modal.count():
            self._modal.get_by_role("button", name="Save").click()
            expect(self._modal).to_have_count(0, timeout=SETTING_TIMEOUT_MS)
        super()._close()

    @property
    def _modal(self) -> Locator:
        # Why CSS: ng-bootstrap draws the Configure window as a bare modal element with no role.
        return self.page.locator(MODAL).last

    @staticmethod
    def _is_text_box(control: Locator) -> bool:
        return str(control.evaluate("el => el.tagName.toLowerCase()")) == INPUT_TAG

    @staticmethod
    def _selected_text(control: Locator) -> str:
        # Why CSS: a select exposes its chosen option only through the :checked state.
        return control.locator("option:checked").inner_text().strip()


CESS_PERCENT = ConfigureField("isCessVisible", "Cess in %", True, CESS_BUTTON)
CESS_AMOUNT = ConfigureField("isAdditionalCessVisible", "Additional Cess Amount", True, CESS_BUTTON)
