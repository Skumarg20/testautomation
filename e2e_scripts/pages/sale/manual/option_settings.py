"""The sale bill's Setting window (the cog `#aControlRoomSetting` on the bill), read and written by field.

Each option is a drop-down with a fixed id in `salebill.setting.html` (UtililityComponent/ControlRoom); the
Basic and Advance tabs split them. A change is stored when it is made and the window closes with its cross,
as `GstConfiguration` does for the calculation type (live). Choices are matched by their visible text, whole
text first, then a unique partial match. The window needs an open sale bill, so `HeldOptions` opens and closes
one around each change when the test has none open yet. Tenant-wide, so the tests run in xdist group
"chemist-tenant" (CLAUDE.md rule 0) and always put the original value back.
"""

from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.components.app_texts import CONTROL_ROOM_SETTING_TITLE

SETTING_TIMEOUT_MS = 15_000
ADVANCE_TAB = "Advance Setting"


class OptionNotOfferedError(AssertionError):
    def __init__(self, label: str, wanted: str, offered: list[str]) -> None:
        super().__init__(f'"{label}" does not offer "{wanted}"; it offers {offered}')


class OptionNotRestoredError(AssertionError):
    def __init__(self, label: str, original: str, now: str) -> None:
        super().__init__(f'Sale bill setting "{label}" is "{now}" after the restore, it was "{original}"')


@dataclass(frozen=True)
class SettingField:
    """A drop-down of the Sale Bill Setting window: its id, its tab and its name in the app."""

    select_id: str
    label: str
    advanced: bool = False


ZERO_RATE = SettingField("IndicateIfBillingRateIsZero", "Indicate if Billing Rate is Zero", True)
ITEM_REPEATED = SettingField("IndicateIfItemRepeatedInBill", "Indicate if Item Repeated in Bill", True)
AMOUNT_CALCULATION = SettingField("amountCalculationOnBilling", "Amount Calculation On Billing", True)
NEGATIVE_ALLOWED = SettingField("negativeAllowed", "Stock Negative allowed")
INDICATE_NEGATIVE = SettingField("isGoingtoNegativeStock", "Indicate if going in negative stock", True)
MODE_OF_PAYMENT = SettingField("txtisModeofPayment", "Mode of Payment Required ?")
ASK_PARTY = SettingField("txtaskpartyinretailbilling", "Ask Party in Retail Billing")
LAST_DEAL = SettingField("lastDealInSale", "Last deal in Sale")
PATIENT_DOCTOR_MUST = SettingField("txtMandatoryPatientandDoctor", "Patient & Doctor Name Must")
ASK_PATIENT_START_SAVE = SettingField("txtAskpatientstartandsave", "Ask patient start and save?")
NET_SCHEME = SettingField("txtnetScheme", "Net Scheme")
ASK_BILL_NO = SettingField("askBillNo", "Ask Bill No.", True)
ASK_SALE_TYPE = SettingField("txtisSaleTypeForBilling", "Ask Sale Type at the time of Billing?", True)


class SaleBillSettings(BasePage):
    """Works on the sale bill that is open on the page."""

    def current(self, field: SettingField) -> str:
        select = self._open(field)
        # Why CSS: a select exposes its chosen option only through the :checked state.
        text = select.locator("option:checked").inner_text().strip()
        self._close()
        return text

    def choose(self, field: SettingField, wanted: str) -> None:
        select = self._open(field)
        select.select_option(index=index_of_option(field.label, wanted, _offered(select)))
        self._close()

    def _open(self, field: SettingField) -> Locator:
        self.page.locator("#aControlRoomSetting").locator("visible=true").first.click()
        if field.advanced:
            self.page.get_by_text(ADVANCE_TAB, exact=True).click()
        # Why visible=true: the Patient & Doctor option exists twice with one id, one of them hidden.
        select = self.page.locator(f"#{field.select_id}").locator("visible=true").first
        expect(select).to_be_visible(timeout=SETTING_TIMEOUT_MS)
        return select

    def _close(self) -> None:
        title = self.page.locator("h2.headingItem", has_text=CONTROL_ROOM_SETTING_TITLE)
        title.locator("button.close").click()


def _offered(select: Locator) -> list[str]:
    return [text.strip() for text in select.locator("option").all_inner_texts()]


def index_of_option(label: str, wanted: str, offered: list[str]) -> int:
    lowered = [text.lower() for text in offered]
    target = wanted.strip().lower()
    if target in lowered:
        return lowered.index(target)
    partial = [index for index, text in enumerate(lowered) if target in text]
    if len(partial) != 1:
        raise OptionNotOfferedError(label, wanted, offered)
    return partial[0]


def same_text(first: str, second: str) -> bool:
    return first.strip().lower() == second.strip().lower()


@contextmanager
def setting_held(settings: SaleBillSettings, field: SettingField, wanted: str) -> Iterator[str]:
    """Yields the original text; the field is only written when it differs, and always put back."""
    original = settings.current(field)
    if same_text(original, wanted):
        yield original
        return
    try:
        # Inside the try: a change that fails half-way may still have changed the tenant.
        settings.choose(field, wanted)
        yield original
    finally:
        settings.choose(field, original)
        now = settings.current(field)
        if not same_text(now, original):
            raise OptionNotRestoredError(field.label, original, now)


class HeldOptions:
    """Several held fields for one test; `close` puts every one back, last changed first.

    `open_bill` and `close_bill` bring a sale bill up and put it away again; a test whose bill is already
    open passes no-ops."""

    def __init__(
        self, settings: SaleBillSettings, open_bill: Callable[[], None], close_bill: Callable[[], None]
    ) -> None:
        self._settings = settings
        self._open_bill = open_bill
        self._close_bill = close_bill
        self._stack = ExitStack()
        self._holding = False

    def hold(self, field: SettingField, wanted: str) -> None:
        self._open_bill()
        try:
            self._stack.enter_context(setting_held(self._settings, field, wanted))
            self._holding = True
        finally:
            self._close_bill()

    def close(self) -> None:
        if not self._holding:
            return
        self._open_bill()
        try:
            self._stack.close()
        finally:
            self._close_bill()
