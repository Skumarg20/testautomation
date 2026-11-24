"""Where the keyboard focus is on a bill screen, and a wait for it to reach one of several places.

The checklist rows about the cursor ("focus should be on ...") are asserted with this probe after each key
press. The app moves focus with jQuery `.focus()` on ids that end in a per-tab number (`txtbillDate48`), so a
place is named by an id prefix, by an ag-Grid `col-id`, or by "inside a pop-up window".
"""

from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage

FOCUS_TIMEOUT_MS = 10_000
Kind = Literal["id", "column", "window"]

DESCRIBE_FOCUS = """() => {
    const el = document.activeElement;
    if (!el || el === document.body) return {id: '', column: '', row: '', inWindow: false, tag: 'nothing'};
    const withId = el.closest('[id]');
    const cell = el.closest('[col-id]');
    return {
        id: el.id || (withId ? withId.id : ''),
        column: cell ? cell.getAttribute('col-id') : '',
        row: el.closest('[row-id]') ? el.closest('[row-id]').getAttribute('row-id') : '',
        inWindow: el.closest('ngb-modal-window') !== null,
        tag: el.tagName.toLowerCase(),
    };
}"""

IS_FOCUS_AT_ANY = """targets => {
    const el = document.activeElement;
    if (!el) return false;
    return targets.some(([kind, name]) => {
        if (kind === 'id') return el.closest('[id^="' + name + '"]') !== null;
        if (kind === 'column') {
            const cell = el.closest('[col-id]');
            return cell !== null && cell.getAttribute('col-id') === name;
        }
        return el.closest('ngb-modal-window') !== null;
    });
}"""


@dataclass(frozen=True)
class Place:
    kind: Kind
    name: str = ""


def field(id_prefix: str) -> Place:
    return Place("id", id_prefix)


def grid_column(column: str) -> Place:
    return Place("column", column)


IN_A_WINDOW = Place("window")

BILL_DATE = field("txtbillDate")
PARTY = field("txtLedgerName")
BILL_NUMBER = field("txtentryNo")
STORE = field("txtStore")
SALE_TYPE = field("txtSaleType")
PATIENT_MOBILE = field("txtptmobile")


@dataclass(frozen=True)
class Focus:
    id: str
    column: str
    row: str
    in_window: bool
    tag: str

    def __str__(self) -> str:
        where = f"grid row='{self.row}' column='{self.column}' window={self.in_window}"
        return f"<{self.tag}> id='{self.id}' {where}"


class FocusNotReachedError(AssertionError):
    def __init__(self, wanted: tuple[Place, ...], actual: Focus) -> None:
        names = ", ".join(f"{place.kind} {place.name}".strip() for place in wanted)
        super().__init__(f"Focus never reached any of [{names}]; it is on {actual}")


class FocusProbe(BasePage):
    def now(self) -> Focus:
        shown = self.page.evaluate(DESCRIBE_FOCUS)
        return Focus(shown["id"], shown["column"], shown["row"], shown["inWindow"], shown["tag"])

    def expect_at(self, *wanted: Place) -> Focus:
        """Waits (no sleeping) until the focus is on one of `wanted`; fails naming where it really is."""
        pairs = [[place.kind, place.name] for place in wanted]
        try:
            self.page.wait_for_function(IS_FOCUS_AT_ANY, arg=pairs, timeout=FOCUS_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            raise FocusNotReachedError(wanted, self.now()) from None
        return self.now()

    def expect_in_grid_row(self, row: int) -> None:
        """Waits until the focus is on a cell of the grid line `row` (ag-Grid `row-id`, counted from 0)."""
        check = "wanted => document.activeElement?.closest('[row-id]')?.getAttribute('row-id') === wanted"
        try:
            self.page.wait_for_function(check, arg=str(row), timeout=FOCUS_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            raise AssertionError(f"Focus never reached grid line {row}; it is on {self.now()}") from None

    def is_at(self, place: Place) -> bool:
        return bool(self.page.evaluate(IS_FOCUS_AT_ANY, [[place.kind, place.name]]))


FOCUS_MOVE_TIMEOUT_MS = 3_000
FOCUS_MOVED = "previous => document.activeElement !== previous"


class FocusProbeWalk(FocusProbe):
    """Walks the focus with a key, one press at a time, until it reaches a place."""

    def press_until(self, key: str, wanted: tuple[Place, ...], limit: int) -> Focus:
        for _ in range(limit):
            if any(self.is_at(place) for place in wanted):
                return self.now()
            previous = self.page.evaluate_handle("document.activeElement")
            self.page.keyboard.press(key)
            try:
                self.page.wait_for_function(FOCUS_MOVED, arg=previous, timeout=FOCUS_MOVE_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                break
        return self.expect_at(*wanted)
