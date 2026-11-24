"""Offline checks of the pure logic in the round-2 C3 page objects (no browser, no app)."""

from datetime import date, timedelta
from decimal import Decimal

from pages.purchase.documents.dates import EXCEL_EPOCH
from pages.sale.round2_c3.owned_stock import BatchSpec, OwnedItem, StockSpec, serial_in


def test_serial_in_counts_days_from_today_on_the_excel_calendar() -> None:
    expected = (date.today() + timedelta(days=30) - EXCEL_EPOCH).days

    assert serial_in(30) == expected


def test_owned_item_lists_its_batch_names_in_purchase_order() -> None:
    spec = StockSpec(
        batches=(
            BatchSpec(Decimal(1), Decimal(1), name="B1"),
            BatchSpec(Decimal(1), Decimal(1), name="B2"),
        )
    )

    assert OwnedItem("9", "QA", spec).batch_names == ["B1", "B2"]
