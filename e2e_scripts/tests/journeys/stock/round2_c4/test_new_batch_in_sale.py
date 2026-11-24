"""Stock row 13: "Create new batch in bill manually; the new batch appears in the Batch List with
reduced stock".

The web sale bill has no way to create a batch: the batch window lists existing batches only and its F2
key just
calls `preventDefault` (processinbatch.component.ts:958-961); F3 edits a listed batch (:962-966); the message
"Batch Not Found in our Records Allow?" (global.ts:19549) is not raised by any sale screen. A new batch comes
from a purchase bill or an opening-stock entry. So the row is tested as far as the web goes: F2 makes nothing,
and a batch bought by a purchase is sold from and then listed with its reduced stock.
"""

from decimal import Decimal

import pytest

from pages.sale.manual.pharma_bill import PharmaBill
from pages.stock.round2_c4.batch_window import BatchWindowOfBill
from pages.stock.sale_impact.batch_list import BatchList
from pages.stock.sale_impact.documents import PRODUCT, sale_request
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("inventory"),
    pytest.mark.xdist_group("chemist-tenant"),
]

SOLD = Decimal(5)


def test_f2_in_the_sale_batch_window_creates_no_batch(bill: PharmaBill, batch: str) -> None:
    """The window shows the same batches and no new window after F2."""
    bill.start()
    window = BatchWindowOfBill(bill)
    window.open(0)
    batches_before, windows_before = window.listed_batches(), window.open_windows()

    window.press("F2")

    assert window.listed_batches() == batches_before
    assert window.open_windows() == windows_before
    window.close()


def test_batch_made_by_a_purchase_is_listed_with_its_stock_reduced_by_a_sale(shop: Shop, batch: str) -> None:
    """A bill of 5 from the bought batch leaves 5 fewer in the Batch List than the list showed before."""
    in_stock = BatchList(shop.page).quantity_of(PRODUCT, batch)
    assert in_stock >= SOLD

    shop.bill(sale_request(batch, SOLD))

    assert BatchList(shop.page).quantity_of(PRODUCT, batch) == in_stock - SOLD
