"""J37 order figures at their boundaries, and orders no store setting stops (OS-26, OS-27).

Orders are seeded through `OnlineStore/SubmitOrder` on no real item: enough for the grid. Quantities are
whole: `OnlineStoreOrderItem.quantity` is an int (`margerpmodel/OnlineStoreNew.cs:181`), so the pack's
decimal quantity cannot be seeded and is not covered.
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.online_store.order_dashboard import OrderColumn, OrderDashboard, StatusFilter
from test_data.online_store import OrderLine, SeededOrder

pytestmark = [pytest.mark.p3, pytest.mark.journey("online-store")]

SeedLine = Callable[[OrderLine], SeededOrder]
TWO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class Figures:
    quantity: int
    price: Decimal
    name: str

    def line(self) -> OrderLine:
        return OrderLine(f"QA-SKU-{self.name}", f"QA-Product-{self.name}", self.quantity, self.price)


BOUNDARY_FIGURES = [
    Figures(1, Decimal("125.50"), "qty-1"),
    Figures(9999, Decimal("125.50"), "large-qty"),
    Figures(2, Decimal("0.01"), "one-paisa-price"),
    Figures(3, Decimal("33.33"), "odd-paise-price"),
]
# OS-27: below any "minimum order amount"; the setting is not rendered and nothing enforces it.
TINY_ORDER = Figures(1, Decimal("0.01"), "tiny-order")


@pytest.mark.parametrize("figures", BOUNDARY_FIGURES, ids=lambda figures: figures.name)
def test_order_amount_is_shown_with_two_decimals(
    dashboard: OrderDashboard, seed_priced_order: SeedLine, figures: Figures
) -> None:
    """OS-26: the grid's Amount is qty x price with two decimals (`order-dashboard.component.ts:428`)."""
    order = seed_priced_order(figures.line())
    dashboard.show_every_vendor()
    shown = dashboard.cell_text(order.order_no, OrderColumn.AMOUNT).replace(",", "")
    assert shown == str(order.total_amount.quantize(TWO_PLACES))


def test_order_below_any_minimum_amount_is_accepted(
    dashboard: OrderDashboard, seed_priced_order: SeedLine
) -> None:
    """OS-27: a 0.01 order is accepted and listed (no server or UI rule; recorded as a gap)."""
    order = seed_priced_order(TINY_ORDER.line())
    dashboard.show_every_vendor()
    dashboard.show_status(StatusFilter.ALL)
    expect(dashboard.order_row(order.order_no)).to_have_count(1)
