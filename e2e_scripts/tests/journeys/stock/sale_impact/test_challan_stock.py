"""Stock rows 2, 3, 11 and 24 of the "Stock (Sale Module)" sheet: what a sale challan and a return
challan do to the stock in Item List, Batch List and Item Register.

Each test buys a batch of its own, so the quantities are known; the expected figure is the quantity read
before, less or plus what the document moves. The three screens are described in `pages/stock/sale_impact/`
(Batch List: processinbatch.component.ts:140-142; Item Register: itemmaster.component.ts:2881-2916). A sale
challan takes stock out, the same rule as the ported challan case TC_SM_001 in
`tests/journeys/sales/test_challan.py`, which reads the Item List only.
"""

from decimal import Decimal

import pytest

from pages.sale.documents.challan import SaleChallan
from pages.stock.sale_impact.documents import sale_request
from pages.stock.sale_impact.modify import SavedDocument
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

SOLD = Decimal(2)
MORE_SOLD = Decimal(5)
RETURNED = Decimal(1)


def test_challan_takes_stock_out_of_item_list_batch_list_and_item_register(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()

    shop.challan(sale_request(batch, SOLD))

    views.expect_moved_by(before, -SOLD)


def test_deleted_challan_gives_the_stock_back_in_all_three_places(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()
    number = shop.challan(sale_request(batch, SOLD))

    shop.delete_challan(number)

    views.expect_moved_by(before, Decimal(0))


def test_raising_the_quantity_of_a_saved_challan_takes_the_difference_out_too(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()
    number = shop.challan(sale_request(batch, SOLD))

    saved = SavedDocument(SaleChallan(shop.page), number)
    saved.reopen()
    saved.change_quantity(MORE_SOLD)
    saved.save_again()

    views.expect_moved_by(before, -MORE_SOLD)


def test_return_challan_adds_the_returned_quantity_to_the_stock(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()

    shop.return_challan(sale_request(batch, RETURNED))

    views.expect_moved_by(before, RETURNED)
