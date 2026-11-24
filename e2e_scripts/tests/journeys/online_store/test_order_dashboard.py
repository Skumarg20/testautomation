"""J37 own Online Store dashboard: seeded orders in the grid, filters, the store card and its settings panel.

Orders are seeded through `OnlineStore/SubmitOrder` as the logged-in user (QA-<run_id> names).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect

from pages.online_store.order_dashboard import OrderColumn, OrderDashboard, StatusFilter
from pages.online_store.store_items import StoreItemList
from pages.online_store.store_setting import StoreConfigurationPanel
from pages.stock.messages import StockMessages
from test_data.online_store import (
    CONVERTED,
    HIDDEN_SETTING_CAPTIONS,
    PENDING,
    RATE_CAPTIONS,
    REJECTED,
    SeededOrder,
)

pytestmark = [pytest.mark.p3, pytest.mark.journey("online-store")]

DEFAULT_VENDOR_TYPE = "Shopify"
LINK_COPIED = re.compile(r"Link Successfully copy to clipboard")
DEV_HOSTS = ("localhost", "127.0.0.1")


def test_seeded_order_is_listed_with_its_figures(
    dashboard: OrderDashboard, seeded_pending_order: SeededOrder
) -> None:
    """OS-15: Order Date dd-mm-yyyy, Customer Name, Status, Qty = sum of item qty, Amount = totalamount."""
    order = seeded_pending_order
    dashboard.show_every_vendor()
    shown = (
        dashboard.cell_text(order.order_no, OrderColumn.ORDER_DATE),
        dashboard.cell_text(order.order_no, OrderColumn.CUSTOMER),
        dashboard.cell_text(order.order_no, OrderColumn.STATUS),
        Decimal(dashboard.cell_text(order.order_no, OrderColumn.QUANTITY)),
        dashboard.amount_of(order.order_no),
    )
    expected = (
        order.grid_date,
        order.customer_name,
        PENDING,
        Decimal(order.total_quantity),
        order.total_amount,
    )
    assert shown == expected


def test_vendor_type_filter_starts_on_shopify(dashboard: OrderDashboard) -> None:
    """OS-16: the Vendor Type filter defaults to Shopify (order-dashboard.component.ts:1461)."""
    assert dashboard.chosen_vendor_type() == DEFAULT_VENDOR_TYPE


def test_seeded_order_is_hidden_by_the_default_vendor_filter(
    dashboard: OrderDashboard, seeded_pending_order: SeededOrder
) -> None:
    """OS-16: GetSavedOrders returns no vendortype, so the default Shopify filter drops the order."""
    expect(dashboard.order_row(seeded_pending_order.order_no)).to_have_count(0)


@dataclass(frozen=True)
class FilterCase:
    seeded_status: str
    status_filter: StatusFilter
    listed: bool


FILTER_CASES = [
    FilterCase(PENDING, StatusFilter.PENDING, listed=True),
    FilterCase(CONVERTED, StatusFilter.PENDING, listed=False),
    FilterCase(REJECTED, StatusFilter.PENDING, listed=False),
    FilterCase(CONVERTED, StatusFilter.CONVERTED, listed=True),
    FilterCase(PENDING, StatusFilter.CONVERTED, listed=False),
    FilterCase(REJECTED, StatusFilter.REJECTED, listed=True),
    FilterCase(REJECTED, StatusFilter.ALL, listed=True),
]


@pytest.mark.parametrize(
    "case", FILTER_CASES, ids=lambda case: f"{case.seeded_status}-in-{case.status_filter.name}"
)
def test_order_status_filter_lists_only_matching_orders(
    dashboard: OrderDashboard, seed_order_with_status: Callable[[str], SeededOrder], case: FilterCase
) -> None:
    """OS-17: Pending hides Converted and Order Rejected; Converted and Order Rejected show only theirs."""
    order = seed_order_with_status(case.seeded_status)
    dashboard.show_every_vendor()
    dashboard.show_status(case.status_filter)
    expect(dashboard.order_row(order.order_no)).to_have_count(1 if case.listed else 0)


def test_own_store_offers_the_switch_to_marg_mart(dashboard: OrderDashboard) -> None:
    """OS-36: in own Online Store mode the button reads "Switch to MargMart"."""
    expect(dashboard.switch_button).to_be_visible()


def test_copy_store_link_confirms_the_copy(dashboard: OrderDashboard) -> None:
    """OS-34: toast "Link Successfully copy to clipboard"."""
    dashboard.copy_store_link()
    StockMessages(dashboard.page).expect_shown(LINK_COPIED)


def test_qr_code_overlay_opens_and_closes(dashboard: OrderDashboard) -> None:
    """OS-35: "Scan QR Code" overlay with a Close button."""
    dashboard.open_qr_code()
    expect(dashboard.qr_heading).to_be_visible()
    dashboard.close_qr_code()
    expect(dashboard.qr_heading).to_be_hidden()


def test_qr_code_points_at_a_public_store_url(dashboard: OrderDashboard) -> None:
    """OS-35, KB vs live 4: the QR should encode the public store URL; the code uses localhost:4200 (D1)."""
    dashboard.open_qr_code()
    assert urlparse(dashboard.qr_target_url()).hostname not in DEV_HOSTS


def test_store_configuration_panel_offers_mrp_and_rates_a_to_h(dashboard: OrderDashboard) -> None:
    """OS-14: Control Room on the dashboard opens "Store Configuration" with Rate Selection."""
    panel = StoreConfigurationPanel(dashboard.page)
    panel.open()
    assert tuple(panel.rate_options()) == RATE_CAPTIONS


@pytest.mark.parametrize("caption", HIDDEN_SETTING_CAPTIONS)
def test_store_configuration_panel_hides_unsupported_options(dashboard: OrderDashboard, caption: str) -> None:
    """OS-13: the five options commented out "due to marg mart have no option yet" are not rendered."""
    panel = StoreConfigurationPanel(dashboard.page)
    panel.open()
    assert caption not in panel.text()


def test_upload_item_needs_a_ticked_item(dashboard: OrderDashboard) -> None:
    """OS-30: with nothing ticked the upload is refused; the source disables "Upload Item" (see spec K1)."""
    dashboard.open_manage_items()
    items = StoreItemList(dashboard.page)
    items.expect_open()
    expect(items.upload_button).to_be_disabled()
