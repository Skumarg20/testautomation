"""Stock rows 18 and 25: a bill dated tomorrow, and undoing a sale (a bill turned back into its challan).

Row 18. The sheet expects "today's stock unaffected; impact seen on the future date". The web source has no
date in the stock figure: the Item List "Stock" is the sum of the item's batch balances
(`ItemMasterDal.cs:1254`, :1420, :1709: `sum(batchmaster.openingQuantity / totalBalanceQuantity)`), and a save
updates the batch whatever the bill date is. So the code lowers the Item List and the Batch List at once for
a bill dated tomorrow, and the Item Register lists the bill. The test asserts that. DECISION NEEDED: does the
product owner want future-dated bills kept out of the stock figure? If so this is an application change.

Row 25. "Re-Convert into Challan" deletes the bill without touching stock (`SaleChallanBill.cs:4631-4655`,
`SaleBillDelete(..., false)` for a sale bill) and puts the bill's pieces back as pending on the challan. The
challan keeps its own deduction (so the stock does not move), and the challan, which could not be deleted
while billed, can be deleted again; that deletion gives the stock back. A plain bill deleted gives its stock
back at once (undo of a sale).
"""

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest

from pages.dashboard_page import DashboardPage
from pages.sale.documents.bill import SaleBillDocument
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held
from pages.stock.sale_impact import documents
from pages.stock.sale_impact.cleanup import Cleanup
from pages.stock.sale_impact.documents import PRODUCT, dated, sale_request
from pages.stock.sale_impact.item_register import ItemRegister
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

SOLD = Decimal(2)
NOTHING = Decimal(0)
ONE_DAY = timedelta(days=1)


@pytest.fixture
def future_date_billing(shop: Shop) -> Iterator[None]:
    switch = SwitchValue("Sale Future Date Billing", "Yes")
    with switch_held(ControlRoomState(shop.page), switch, DashboardPage(shop.page).open):
        yield


@pytest.mark.usefixtures("future_date_billing")
def test_bill_dated_tomorrow_lowers_the_stock_figures_at_once_and_is_in_the_register(
    shop: Shop, batch: str
) -> None:
    views = shop.views(batch)
    before = views.read()

    number = shop.bill(dated(sale_request(batch, SOLD), date.today() + ONE_DAY))

    views.expect_moved_by(before, -SOLD)
    assert ItemRegister(shop.page).lists_document(PRODUCT, number)


def test_deleting_a_bill_gives_its_stock_back(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()
    number = documents.save_bill(shop.page, sale_request(batch, SOLD))
    try:
        views.expect_moved_by(before, -SOLD)
    finally:
        SaleBillDocument(shop.page).delete(number)

    views.expect_moved_by(before, NOTHING)


def test_challan_freed_by_re_converting_its_bill_can_be_deleted_and_returns_its_stock(
    shop: Shop, cleanup: Cleanup, batch: str
) -> None:
    views = shop.views(batch)
    before = views.read()
    request = sale_request(batch, SOLD)
    challan = shop.challan(request)
    bill = shop.bill_from_challan(challan, request)

    SaleBillDocument(shop.page).convert_back_to_challan(bill, challan)
    # The bill is gone; the shop's own undo step for it (named by document type and number) must not run.
    cleanup.discard(f"{SaleBillDocument.__name__}:{bill}")
    views.expect_moved_by(before, -SOLD)
    shop.delete_challan(challan)

    views.expect_moved_by(before, NOTHING)
