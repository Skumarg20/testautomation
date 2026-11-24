"""The figures on the dashboard: the three summary cards, the tiles below them and the last sync time.

The first paint shows the figures saved at the last sync (the app asks the server with callType 0);
choosing a period or pressing Refresh Dashboard recalculates them (callType 1). Every method that
changes the figures waits until the screen shows what the server sent for that call.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from playwright.sync_api import Locator, Response, expect

from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from test_data.money import parse_amount

FIGURES_TIMEOUT_MS = 90_000
THREE_PLACES = Decimal("0.001")
HEADER_DATA = "DashBoard/MainDashboardHeaderData"
NEWLY_ADDED = "DashBoard/NEWLYADDEDASHBOARD"
GROSS_PROFIT = "DashBoard/GetGrossProfit"
RECALCULATED_CALL = 1
LAST_SYNC = re.compile(r"^Last Sync : (?P<day>\d{2}-\d{2}-\d{4}) \| \d{2}:\d{2} [AP]M$")
CARD_FIGURES = re.compile(r"^₹(?P<current>-?[\d.]+) from ₹(?P<previous>-?[\d.]+)$")
# Why a second pattern: expect() runs the regex in the browser, and JavaScript rejects (?P<name>...).
CARD_FIGURES_SHOWN = re.compile(r"^₹-?[\d.]+ from ₹-?[\d.]+$")
CHANGE_PERCENT = re.compile(r"^-?\d+\.\d+%$")


class SummaryCard(Enum):
    NET_SALE = "Net Sale"
    NET_PURCHASE = "Net Purchase"
    GROSS_PROFIT = "Gross Profit"

    @property
    def title(self) -> str:
        return self.value


# The keys of a card's current and previous figure in the header data (gross profit has its own call).
HEADER_KEYS: dict[SummaryCard, tuple[str, str]] = {
    SummaryCard.NET_SALE: ("Total Sale", "Previous Sale"),
    SummaryCard.NET_PURCHASE: ("Total Purchase", "Previous Purchase"),
}


@dataclass(frozen=True)
class CardFigures:
    """What a card shows: "₹current from ₹previous" and the change in percent."""

    current: Decimal
    previous: Decimal
    change_percent: Decimal


class DashboardFigures(BasePage):
    def open(self) -> None:
        """Opens the dashboard and recalculates, so the screen is checked against a fresh server answer.

        Why not wait for the cached call: once a session has loaded the dashboard the app keeps the
        figures in its saved storage and a later open sends no request at all (seen live 2026-10-09).
        """
        DashboardPage(self.page).open()
        self.refresh()

    def refresh(self) -> None:
        self._reload_after(self._refresh_button.click, RECALCULATED_CALL)

    def recalculate_after(self, action: Callable[[], None]) -> None:
        """Runs an action that makes the app recalculate (a period choice) and waits for the result."""
        self._reload_after(action, RECALCULATED_CALL)

    def card(self, card: SummaryCard) -> CardFigures:
        found = CARD_FIGURES.match(self._card_figures(card).inner_text().strip())
        if found is None:
            raise AssertionError(f'Card "{card.title}" does not show "₹current from ₹previous"')
        change = self._card(card).get_by_text(CHANGE_PERCENT).inner_text().strip().rstrip("%")
        return CardFigures(Decimal(found["current"]), Decimal(found["previous"]), Decimal(change))

    def tile_value(self, tile: str) -> Decimal:
        return parse_amount(self._tile(tile).inner_text().splitlines()[-1])

    def expect_tile_value(self, tile: str, value: Decimal) -> None:
        expect(self._tile(tile)).to_have_text(
            re.compile(rf"^{re.escape(tile)}\s*₹?\s*{re.escape(_three_places(value))}$"),
            timeout=FIGURES_TIMEOUT_MS,
        )

    def expect_tile_shown(self, tile: str) -> None:
        expect(self._tile(tile)).to_be_visible(timeout=FIGURES_TIMEOUT_MS)

    def expect_card_shown(self, card: SummaryCard) -> None:
        expect(self._card_figures(card)).to_have_text(CARD_FIGURES_SHOWN, timeout=FIGURES_TIMEOUT_MS)
        expect(self._card(card).get_by_text(CHANGE_PERCENT)).to_be_visible()

    def expect_section_shown(self, section: str) -> None:
        expect(self._main.get_by_text(section, exact=True).first).to_be_visible(timeout=FIGURES_TIMEOUT_MS)

    def last_sync_day(self) -> str:
        """The dd-mm-yyyy date of "Last Sync : 09-10-2026 | 10:26 AM" under the dashboard title."""
        found = LAST_SYNC.match(self._last_sync.inner_text().strip())
        if found is None:
            raise AssertionError(f'Unexpected last sync text "{self._last_sync.inner_text()}"')
        return found["day"]

    def open_card_report(self, card: SummaryCard) -> None:
        self._card_title(card).click()

    def _reload_after(self, action: Callable[[], None], call_type: int) -> None:
        wait_for = self.page.expect_response
        with (
            wait_for(_is_call(HEADER_DATA, call_type), timeout=FIGURES_TIMEOUT_MS) as header,
            wait_for(_is_call(NEWLY_ADDED, call_type), timeout=FIGURES_TIMEOUT_MS) as added,
            wait_for(_is_call(GROSS_PROFIT, call_type), timeout=FIGURES_TIMEOUT_MS) as profit,
        ):
            action()
        self._expect_header_shown(header.value.json())
        self._expect_gross_previous_shown(profit.value.json())
        self.expect_tile_value("Items", _items_added(added.value.json()))

    def _expect_header_shown(self, payload: dict[str, Any]) -> None:
        figures = {row["Keys"]: row["Value"] for row in payload["Data"]["DashBoardHeader"]}
        for card, (current_key, previous_key) in HEADER_KEYS.items():
            shown = f"₹{_three_places(figures[current_key])} from ₹{_three_places(figures[previous_key])}"
            expect(self._card_figures(card)).to_have_text(shown, timeout=FIGURES_TIMEOUT_MS)

    def _expect_gross_previous_shown(self, payload: dict[str, Any]) -> None:
        previous = _three_places(_gross_profit_previous(payload))
        expect(self._card_figures(SummaryCard.GROSS_PROFIT)).to_have_text(
            re.compile(rf" from ₹{re.escape(previous)}$"), timeout=FIGURES_TIMEOUT_MS
        )

    @property
    def _main(self) -> Locator:
        return self.page.get_by_role("main")

    @property
    def _refresh_button(self) -> Locator:
        return self._main.get_by_role("button", name="Refresh Dashboard")

    @property
    def _last_sync(self) -> Locator:
        return self._main.get_by_role("heading", name=re.compile(r"^Last Sync"), level=3)

    def _card_title(self, card: SummaryCard) -> Locator:
        return self._main.get_by_role("link", name=card.title, exact=True)

    def _card(self, card: SummaryCard) -> Locator:
        # Why CSS: a card is a plain div with no role; it is the innermost div holding its title link
        # and its figure heading (ancestors come first in document order, so it is the last match).
        return (
            self._main.locator("div")
            .filter(has=self.page.get_by_role("link", name=card.title, exact=True))
            .filter(has=self.page.get_by_role("heading", level=4))
            .last
        )

    def _card_figures(self, card: SummaryCard) -> Locator:
        return self._card(card).get_by_role("heading", level=4)

    def _tile(self, tile: str) -> Locator:
        """A tile is a link named by its title and figure, for example "Cash Balance ₹-252890.000"."""
        return self._main.get_by_role("link", name=re.compile(rf"^{re.escape(tile)} ₹?-?[\d.]+$"))


def _is_call(endpoint: str, call_type: int) -> Callable[[Response], bool]:
    """POST calls carry callType in the JSON body, the gross-profit GET in the query string."""

    def matches(response: Response) -> bool:
        request = response.request
        sent = (request.post_data or "") + request.url
        return endpoint in request.url and re.search(rf'callType"?[:=]{call_type}\b', sent) is not None

    return matches


def _three_places(value: float | Decimal) -> str:
    """The dashboard prints every figure with three decimals: 4704 is "4704.000"."""
    return str(Decimal(str(value)).quantize(THREE_PLACES))


def _items_added(payload: dict[str, Any]) -> Decimal:
    counts = {row["Keys"]: row["Value"] for row in payload["Data"]["NewDashboard"]}
    return Decimal(counts["Items"])


def _gross_profit_previous(payload: dict[str, Any]) -> Decimal:
    """The previous gross profit comes back in "GrossProfitPrevious" or, for a cached call, in "Table2"."""
    for table in payload["Data"].values():
        for row in table:
            if "GrossProfitPrevious" in row:
                return Decimal(str(row["GrossProfitPrevious"]))
    raise AssertionError("The gross profit response has no previous figure")
