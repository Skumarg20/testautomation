"""Stock row 34: the order in which the sale batch window offers batches.

The sheet expects the batch with the earliest expiry (FIFO stock) to be suggested first. The batch bought
first is also the one expiring first here, so a first-in-first-out and an earliest-expiry reading agree.
Only the order of the two test batches is asserted; the shared QA stock may hold older batches of the item.
"""

import pytest

from pages.stock.sale_impact.batch_list import BatchList
from pages.stock.sale_impact.documents import PRODUCT
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("inventory"),
    pytest.mark.xdist_group("chemist-tenant"),
]

SOON_DAYS = 100
LATER_DAYS = 400


def test_batch_that_expires_sooner_and_came_in_first_is_listed_before_the_later_one(shop: Shop) -> None:
    soon = shop.buy_batch_expiring_in(SOON_DAYS)
    later = shop.buy_batch_expiring_in(LATER_DAYS)

    listed = list(BatchList(shop.page).batches_with_stock(PRODUCT))

    assert listed.index(soon) < listed.index(later)
