"""Stock rows 4, 8, 20, 22, 23, 29, 31 of the "Stock (Sale Module)" sheet: which batch a document moves.

Batches are bought for the test (purchase bill, 100 + 50 free each). Expected figures are the quantity read
before, less or plus the quantity of the document; nothing is taken from the screen being checked.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal

import pytest

from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.challan import SaleChallan
from pages.sale.documents.document import SaleDocument
from pages.sale.documents.document_requests import DocumentRequest
from pages.stock.sale_impact.documents import sale_request
from pages.stock.sale_impact.modify import SavedDocument
from pages.stock.sale_impact.shop import Shop
from pages.stock.sale_impact.stock_views import StockReading, expect_reading

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

SOLD = Decimal(2)
SOLD_ON_SECOND_LINE = Decimal(3)
RETURNED = Decimal(1)


@dataclass(frozen=True)
class SavedKind:
    """A document type that can be saved, reopened and changed."""

    document_type: type[SaleDocument]
    save: Callable[[Shop, DocumentRequest], str]


CHALLAN = SavedKind(SaleChallan, lambda shop, request: shop.challan(request))
BILL = SavedKind(SaleBillDocument, lambda shop, request: shop.bill(request))


@pytest.mark.parametrize("kind", [CHALLAN, BILL], ids=["challan-row-4", "bill-row-8"])
def test_changing_the_batch_of_a_saved_document_moves_the_deduction_to_the_new_batch(
    shop: Shop, kind: SavedKind
) -> None:
    first, second = shop.buy_batch(), shop.buy_batch()
    first_views, second_views = shop.views(first), shop.views(second)
    first_before, second_before = first_views.read(), second_views.batch_quantity()
    number = kind.save(shop, sale_request(first, SOLD))

    saved = SavedDocument(kind.document_type(shop.page), number)
    saved.reopen()
    saved.change_batch(second)
    saved.save_again()

    # The old batch is back, the new one is down, and the item as a whole is down by the same pieces.
    old_batch_restored = StockReading(
        item_list=first_before.item_list - SOLD,
        batch_list=first_before.batch_list,
        item_register=first_before.item_register - SOLD,
    )
    expect_reading(first_views.read(), old_batch_restored)
    assert second_views.batch_quantity() == second_before - SOLD


def test_one_challan_with_the_item_twice_takes_each_line_from_its_own_batch(shop: Shop) -> None:
    first, second = shop.buy_batch(), shop.buy_batch()
    first_views, second_views = shop.views(first), shop.views(second)
    first_before, second_before = first_views.batch_quantity(), second_views.batch_quantity()
    on_first, on_second = sale_request(first, SOLD), sale_request(second, SOLD_ON_SECOND_LINE)

    shop.challan(replace(on_first, lines=on_first.lines + on_second.lines))

    assert first_views.batch_quantity() == first_before - SOLD
    assert second_views.batch_quantity() == second_before - SOLD_ON_SECOND_LINE


def test_sale_from_a_batch_bought_twice_under_one_name_leaves_the_other_batch_alone(shop: Shop) -> None:
    """Stock row 29. Whether the app merges the two purchases into one batch row or lists two rows of the
    same name, the rows of that name together fall by the quantity sold and the other batch does not move."""
    shared = shop.buy_batch()
    shop.buy_again_under_the_name(shared)
    other = shop.buy_batch()
    shared_views, other_views = shop.views(shared), shop.views(other)
    shared_before, other_before = shared_views.batch_quantity(), other_views.batch_quantity()

    shop.challan(sale_request(shared, SOLD))

    assert shared_views.batch_quantity() == shared_before - SOLD
    assert other_views.batch_quantity() == other_before


def test_sale_then_return_on_a_batch_moves_its_stock_down_then_up(shop: Shop, batch: str) -> None:
    """Stock rows 22 and 31: the Batch List, Item List and Item Register follow a sale and a return."""
    views = shop.views(batch)
    before = views.read()
    shop.challan(sale_request(batch, SOLD))
    views.expect_moved_by(before, -SOLD)

    shop.manual_return(sale_request(batch, RETURNED))

    views.expect_moved_by(before, -SOLD + RETURNED)


def test_partial_sale_return_adds_back_only_the_returned_quantity(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()
    shop.bill(sale_request(batch, SOLD + RETURNED))

    shop.manual_return(sale_request(batch, RETURNED))

    views.expect_moved_by(before, -(SOLD + RETURNED) + RETURNED)
