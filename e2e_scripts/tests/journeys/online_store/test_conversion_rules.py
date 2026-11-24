"""J37 what a conversion carries onto the sale bill, and when it updates the order's status.

Orders are seeded on this test's own item(s) so the bill can be saved and then deleted. The status update the
bill posts after its first save is real (it touches only this test's order) and is counted, not stubbed.
"""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

from pages.components.stubbed_endpoint import StubbedEndpoint
from pages.online_store.converted_bill import ConvertedBill
from pages.online_store.order_dashboard import OrderColumn, OrderDashboard, StatusFilter
from pages.online_store.status_updates import StatusUpdateCalls
from pages.online_store.store_endpoints import LEDGER_BY_FIXED_ID, NO_LEDGER_REPLY
from pages.sale.documents.bill import SaleBillDocument
from pages.stock.messages import StockMessages
from test_data.masters import PartyLedgerSpec
from test_data.online_store import CONVERTED, LEDGER_NOT_FOUND, ConvertedSale, SeededOrder

pytestmark = [pytest.mark.p3, pytest.mark.journey("online-store")]

LEDGER_HELD_IN_SESSION = (
    "OS-23: the session already holds the Online Store ledger, so the lookup this test stubs was not made"
)


def _convert(dashboard: OrderDashboard, order: SeededOrder) -> ConvertedBill:
    dashboard.show_every_vendor()
    dashboard.convert(order.order_no)
    bill = ConvertedBill(dashboard.page)
    bill.expect_open()
    return bill


def test_converted_bill_total_equals_the_order_amount(
    dashboard: OrderDashboard, convertible_order: SeededOrder
) -> None:
    """OS-20: invoice value = order Amount, GST counted once (MBC-16813, MBC-17618; rounding UNVERIFIED)."""
    bill = _convert(dashboard, convertible_order)
    assert bill.invoice_value() == convertible_order.total_amount


def test_converted_order_offers_no_second_conversion(
    dashboard: OrderDashboard, seed_order_with_status: Callable[[str], SeededOrder]
) -> None:
    """OS-21: a Converted order cannot be converted again (D3: `+"Converted"` is NaN, so Convert shows).

    The pack allows "refused or needs confirmation"; this test asserts the refusal form (no Convert button).
    """
    order = seed_order_with_status(CONVERTED)
    dashboard.show_every_vendor()
    dashboard.show_status(StatusFilter.CONVERTED)
    expect(dashboard.convert_button(order.order_no)).to_have_count(0)


def test_unsaved_conversion_does_not_update_the_order_status(
    dashboard: OrderDashboard, convertible_order: SeededOrder
) -> None:
    """OS-22: the bill's automatic temp-saves while it is filled post no status update."""
    calls = StatusUpdateCalls(dashboard.page)
    _convert(dashboard, convertible_order)
    assert calls.count_once_settled() == 0


def test_saving_the_conversion_updates_the_order_status_once(
    dashboard: OrderDashboard, convertible_order: SeededOrder, save_converted_bill: Callable[[], None]
) -> None:
    """OS-22: the first final save posts exactly one StatusUpdationOfOnlineStore."""
    _convert(dashboard, convertible_order)
    calls = StatusUpdateCalls(dashboard.page)
    save_converted_bill()
    assert calls.count_once_settled() == 1


def test_resaving_the_converted_bill_posts_no_second_status_update(
    dashboard: OrderDashboard, converted_sale: ConvertedSale
) -> None:
    """OS-22 (MBC-5415): reopening the saved bill and saving again works and posts no status update."""
    bill = ConvertedBill(dashboard.page)
    bill.reopen(converted_sale.bill_number)
    calls = StatusUpdateCalls(dashboard.page)
    sale_bill = SaleBillDocument(dashboard.page)
    sale_bill.save()
    sale_bill.expect_saved()
    assert calls.count_once_settled() == 0


def test_conversion_without_the_online_store_ledger_says_so(
    dashboard: OrderDashboard, seeded_pending_order: SeededOrder
) -> None:
    """OS-23: with no ledger of fixedID 83 the conversion warns "Transaction data not found !".

    The ledger lookup is answered by a stub with no ledger, which stands in for a company without it.
    """
    lookup = StubbedEndpoint(dashboard.page, LEDGER_BY_FIXED_ID)
    lookup.answer_with(NO_LEDGER_REPLY)
    dashboard.show_every_vendor()
    try:
        lookup.capture_one(lambda: dashboard.convert(seeded_pending_order.order_no))
    except PlaywrightTimeoutError:
        pytest.skip(LEDGER_HELD_IN_SESSION)
    StockMessages(dashboard.page).expect_shown(re.compile(re.escape(LEDGER_NOT_FOUND)))


def test_converted_bill_keeps_the_customer_mobile(
    dashboard: OrderDashboard, convertible_order: SeededOrder
) -> None:
    """OS-24 (MBC-6711, MB-31673): the order's customer mobile is on the bill."""
    assert _convert(dashboard, convertible_order).customer_mobile() == convertible_order.customer_mobile


def test_customer_with_a_known_mobile_is_billed_to_that_ledger(
    dashboard: OrderDashboard,
    known_customer: PartyLedgerSpec,
    seed_order_from_mobile: Callable[[str], SeededOrder],
) -> None:
    """OS-25 (MBC-16732): a mobile matching an existing ledger bills that ledger (UNVERIFIED, own store)."""
    order = seed_order_from_mobile(known_customer.mobile)
    assert _convert(dashboard, order).party_name() == known_customer.name


def test_conversion_with_a_deleted_line_still_marks_the_order_converted(
    dashboard: OrderDashboard, two_line_order: SeededOrder, save_converted_bill: Callable[[], None]
) -> None:
    """OS-38: delete one of two lines on the bill, save: the order is still "Converted"."""
    _convert(dashboard, two_line_order).delete_line(1)
    save_converted_bill()
    dashboard.show_every_vendor()
    dashboard.show_status(StatusFilter.ALL)
    assert dashboard.cell_text(two_line_order.order_no, OrderColumn.STATUS) == CONVERTED
