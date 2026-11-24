"""Stock rows 18, 19, 25 and 28: dated bills, a bill turned back into its challan, a challan that was billed.

Rules cited: a challan holds the stock and a bill made from it takes nothing more out (comment in
`tests/journeys/sales/test_bill.py::_sold_lines`, the purchase twin in tests/journeys/purchase/test_bill.py);
a converted challan cannot be deleted and the app answers with a warning
(`DocumentScreen.delete_after_conversion`); a back-dated or future-dated bill needs the Control Room switches
"Sale BackDate Billing" / "Sale Future Date Billing" (pages/settings/control_room.py), restored afterwards.
"""

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest

from pages.dashboard_page import DashboardPage
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.challan import SaleChallan
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held
from pages.stock.sale_impact.documents import PRODUCT, dated, sale_request
from pages.stock.sale_impact.item_register import ItemRegister
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

SOLD = Decimal(2)
ONE_DAY = timedelta(days=1)


@pytest.fixture
def back_date_billing(shop: Shop) -> Iterator[None]:
    switch = SwitchValue("Sale BackDate Billing", "Yes")
    with switch_held(ControlRoomState(shop.page), switch, DashboardPage(shop.page).open):
        yield


@pytest.fixture
def future_date_billing(shop: Shop) -> Iterator[None]:
    switch = SwitchValue("Sale Future Date Billing", "Yes")
    with switch_held(ControlRoomState(shop.page), switch, DashboardPage(shop.page).open):
        yield


def test_bill_dated_yesterday_reduces_stock_and_is_listed_in_the_item_register(
    shop: Shop, batch: str, back_date_billing: None
) -> None:
    views = shop.views(batch)
    before = views.read()

    number = shop.bill(dated(sale_request(batch, SOLD), date.today() - ONE_DAY))

    views.expect_moved_by(before, -SOLD)
    assert ItemRegister(shop.page).lists_document(PRODUCT, number)


def test_bill_dated_tomorrow_is_listed_in_the_item_register(
    shop: Shop, batch: str, future_date_billing: None
) -> None:
    """Whether today's stock figure includes a bill dated tomorrow is not documented; the register line is."""
    number = shop.bill(dated(sale_request(batch, SOLD), date.today() + ONE_DAY))

    assert ItemRegister(shop.page).lists_document(PRODUCT, number)


def test_bill_turned_back_into_its_challan_leaves_the_challans_deduction_in_place(
    shop: Shop, batch: str
) -> None:
    views = shop.views(batch)
    before = views.read()
    request = sale_request(batch, SOLD)
    challan = shop.challan(request)
    bill = shop.bill_from_challan(challan, request)

    SaleBillDocument(shop.page).convert_back_to_challan(bill, challan)

    views.expect_moved_by(before, -SOLD)


def test_challan_that_was_billed_cannot_be_deleted_and_its_stock_stays_out(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()
    request = sale_request(batch, SOLD)
    challan = shop.challan(request)
    shop.bill_from_challan(challan, request)

    challans = SaleChallan(shop.page)
    challans.screen.open_menu(challans.menu)
    challans.screen.delete_after_conversion(challan)

    views.expect_moved_by(before, -SOLD)
