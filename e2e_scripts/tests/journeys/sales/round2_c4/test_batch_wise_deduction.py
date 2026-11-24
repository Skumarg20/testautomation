"""Sale bill rows 69 and 81: a bill with a chosen batch takes stock from that batch only.

Two batches are bought; a bill sells from the first. The Batch List (read per batch, which the Item List
cannot do) shows the first down by the quantity and the second unchanged.
"""

from decimal import Decimal

import pytest

from pages.stock.sale_impact.documents import sale_request
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

SOLD = Decimal(3)


def test_bill_from_one_batch_leaves_the_other_batch_untouched(shop: Shop) -> None:
    first, second = shop.buy_batch(), shop.buy_batch()
    first_views, second_views = shop.views(first), shop.views(second)
    first_before, second_before = first_views.read(), second_views.batch_quantity()

    shop.bill(sale_request(first, SOLD))

    first_views.expect_moved_by(first_before, -SOLD)
    assert second_views.batch_quantity() == second_before
