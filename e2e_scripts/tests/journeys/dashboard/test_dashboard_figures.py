"""J22 dashboard figures (specs/dashboard.md).

Other tests post sales and purchases on the same company at the same time, so card figures are only
compared with other dashboard figures read moments apart; the one count the test moves itself is the
"New Added > Items" tile for today.
"""

from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal

import pytest

from pages.dashboard.figures import CardFigures, DashboardFigures, SummaryCard
from pages.dashboard.period_filter import Period, PeriodFilter
from test_data.models import ItemMasterSpec

pytestmark = [pytest.mark.p2, pytest.mark.journey("dashboard"), pytest.mark.xdist_group("dashboard-period")]

THREE_PLACES = Decimal("0.001")
ONE_ITEM = Decimal(1)
NEW_ITEMS_TILE = "Items"


def test_previous_figure_of_this_month_is_the_previous_month_figure(
    period_filter: PeriodFilter, figures: DashboardFigures
) -> None:
    """DB-10: "from ₹x" under This Month is what Previous Month shows as its own figure."""
    period_filter.choose(Period.THIS_MONTH)
    previous_of_this_month = {card: figures.card(card).previous for card in SummaryCard}

    period_filter.choose(Period.PREVIOUS_MONTH)
    previous_month = {card: figures.card(card).current for card in SummaryCard}

    assert previous_of_this_month == previous_month


def test_change_percent_follows_from_current_and_previous_figure(
    period_filter: PeriodFilter, figures: DashboardFigures
) -> None:
    """DB-11, DB-17: change = (current - previous) / previous x 100, three decimals."""
    period_filter.choose(Period.PREVIOUS_MONTH)
    shown = {card: figures.card(card) for card in SummaryCard}

    assert {card: shown[card].change_percent for card in SummaryCard} == {
        card: _expected_change(shown[card]) for card in SummaryCard
    }


def test_item_added_today_is_counted_in_new_added_items(
    period_filter: PeriodFilter,
    figures: DashboardFigures,
    add_own_item: Callable[[], ItemMasterSpec],
) -> None:
    """DB-09: the Items tile under New Added counts the item this test creates."""
    period_filter.choose(Period.TODAY)
    items_before = figures.tile_value(NEW_ITEMS_TILE)

    add_own_item()
    figures.open()
    figures.refresh()

    figures.expect_tile_value(NEW_ITEMS_TILE, items_before + ONE_ITEM)


def _expected_change(card: CardFigures) -> Decimal:
    """Seen live: with no previous figure the card shows 0.000% rather than an error."""
    if card.previous == 0:
        return Decimal(0).quantize(THREE_PLACES)
    change = (card.current - card.previous) / card.previous * 100
    return change.quantize(THREE_PLACES, rounding=ROUND_HALF_UP)
