"""Stock rows 13, 14, 27, 30, 33: a batch sold down to nothing, a return into it, an unknown batch name.

Rules cited: the batch window hides batches with no stock until "ShowAll Batch" (F7),
processinbatch.component.ts:575-597 and :991-993; a search that matches nothing shows "<text> Not Found!" and
lists no row (not.found.component.ts); the window only lets a listed row be picked (`onRowDoubleClick`), and
its F2 key creates nothing (processinbatch.component.ts:958-961), so a sale cannot make a new batch.
"""

from decimal import Decimal

import pytest

from pages.stock.sale_impact.batch_list import BatchList
from pages.stock.sale_impact.documents import PRODUCT, sale_request
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("inventory"),
    pytest.mark.xdist_group("chemist-tenant"),
]

RETURNED = Decimal(1)
NO_SUCH_BATCH = "NOSUCHBATCH"


def test_batch_sold_down_to_nothing_is_listed_with_zero_when_all_batches_are_shown(
    shop: Shop, batch: str
) -> None:
    shop.sell_everything(batch)

    assert BatchList(shop.page).all_batches(PRODUCT)[batch] == 0


def test_batch_with_no_stock_is_hidden_by_default_and_shown_by_show_all(shop: Shop, batch: str) -> None:
    shop.sell_everything(batch)
    batches = BatchList(shop.page)

    assert batch not in batches.batches_with_stock(PRODUCT)
    assert batch in batches.all_batches(PRODUCT)


def test_item_stock_falls_by_the_whole_batch_when_the_batch_is_sold_out(shop: Shop, batch: str) -> None:
    views = shop.views(batch)
    before = views.read()

    sold = shop.sell_everything(batch)

    views.expect_moved_by(before, -sold)


def test_return_into_a_batch_with_no_stock_is_accepted_and_adds_the_quantity(shop: Shop, batch: str) -> None:
    """Stock row 30: a return does not need stock in hand."""
    shop.sell_everything(batch)
    views = shop.views(batch)
    before = views.read()

    shop.return_to_empty_batch(sale_request(batch, RETURNED))

    views.expect_moved_by(before, RETURNED)


def test_a_batch_name_that_does_not_exist_cannot_be_picked(shop: Shop, batch: str) -> None:
    """Stock rows 13 and 33: the sale batch window lists existing batches only; a mistyped name finds none."""
    outcome = BatchList(shop.page).search_for(PRODUCT, NO_SUCH_BATCH)

    assert outcome.rows_listed == 0
    assert outcome.not_found_shown
