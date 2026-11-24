"""Stock rows 16, 17, 21 and 32: a Sale > Stock Issue entry, deleted again, and next to a sale.

A stock issue reduces item and batch stock like a challan does (sheet rows 16 and 17); its screen is
`SaleStockIssueFactory` (sale.stockissue.factory.ts), not the manufacturing Material Issue. The Item Register
lists a document by its number (the same lookup the J40 conversion tests use).
"""

from decimal import Decimal

import pytest

from pages.stock.sale_impact.documents import PRODUCT, sale_request
from pages.stock.sale_impact.item_register import ItemRegister
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("inventory"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ISSUED = Decimal(3)
SOLD = Decimal(2)


def test_stock_issue_reduces_item_batch_and_register_stock(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()

    shop.stock_issue(sale_request(batch, ISSUED))

    views.expect_moved_by(before, -ISSUED)


def test_deleted_stock_issue_adds_its_quantity_back(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()
    number = shop.stock_issue(sale_request(batch, ISSUED))

    shop.delete_stock_issue(number)

    views.expect_moved_by(before, Decimal(0))


def test_stock_issue_and_sale_of_the_same_item_show_their_combined_deduction(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()
    shop.stock_issue(sale_request(batch, ISSUED))
    shop.bill(sale_request(batch, SOLD))

    views.expect_moved_by(before, -(ISSUED + SOLD))


def test_item_register_lists_the_stock_issue_and_the_sale_by_their_numbers(shop: Shop, batch: str) -> None:
    issue = shop.stock_issue(sale_request(batch, ISSUED))
    bill = shop.bill(sale_request(batch, SOLD))
    register = ItemRegister(shop.page)

    assert register.lists_document(PRODUCT, issue)
    assert register.lists_document(PRODUCT, bill)
