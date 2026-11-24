"""J37 converting a seeded own-store order into a sale bill, and the order's status afterwards.

The order's line is this test's own item (its linkid as productid), so the bill can be saved and deleted.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import Page, expect

from pages.online_store.order_dashboard import OrderColumn, OrderDashboard, StatusFilter
from pages.sale.documents.item_grid import DocumentItemGrid
from test_data.online_store import CONVERTED, SeededOrder

pytestmark = [pytest.mark.p3, pytest.mark.journey("online-store")]

TRANSACTION_URL = "**/transaction"
BILL_TIMEOUT_MS = 60_000


def test_convert_opens_a_sale_bill_with_the_order_quantity(
    store_page: Page, dashboard: OrderDashboard, convertible_order: SeededOrder
) -> None:
    """OS-18: Convert opens /transaction with the order's item and quantity (bill left unsaved)."""
    dashboard.show_every_vendor()
    dashboard.convert(convertible_order.order_no)
    store_page.wait_for_url(TRANSACTION_URL, timeout=BILL_TIMEOUT_MS)
    assert DocumentItemGrid(store_page).quantity_in_grid(0) == Decimal(convertible_order.total_quantity)


def test_saved_conversion_marks_the_order_converted(
    dashboard: OrderDashboard, converted_order: SeededOrder
) -> None:
    """OS-19: after the bill is saved the order's status is "Converted" (regression for MB-037180)."""
    dashboard.show_every_vendor()
    dashboard.show_status(StatusFilter.ALL)
    assert dashboard.cell_text(converted_order.order_no, OrderColumn.STATUS) == CONVERTED


def test_saved_conversion_leaves_the_pending_view(
    dashboard: OrderDashboard, converted_order: SeededOrder
) -> None:
    """OS-19: the converted order is no longer under Pending."""
    dashboard.show_every_vendor()
    dashboard.show_status(StatusFilter.PENDING)
    expect(dashboard.order_row(converted_order.order_no)).to_have_count(0)
