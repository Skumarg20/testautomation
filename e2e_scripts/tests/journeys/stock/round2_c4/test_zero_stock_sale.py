"""Stock rows 15 and 35, and sale-bill rows 169, 224 and 225: selling from a batch that has no stock left.

Every test makes its own batch (purchase of 100 + 50 free) and sells all of it, so the batch really
holds 0 and
no QA item has to be found. The rules, from the web source:
- "Stock Negative allowed" = No: the sold-out batch is refused when picked, "Stock not available. Select
  another batch!" (processinbatch.component.ts:1069-1076, global.ts:19473);
- = Yes with "Indicate if going in negative stock" = Yes: the batch is taken and entering a quantity warns
  "Stock going in negative!" (processout.transaction.component.ts:12741-12775 and :12853-12857,
  global.ts:19322);
- = Yes with Indicate = No: the quantity is taken without a message (:12834-12839);
- a saved bill takes the whole quantity from the batch, so the batch goes below zero and the Item List
  falls by
  the same quantity (batch rows hold `openingQuantity`, ItemMasterDal.cs:1254).
"""

from decimal import Decimal

import pytest

from pages.sale.manual import messages
from pages.sale.manual.option_settings import INDICATE_NEGATIVE, NEGATIVE_ALLOWED, HeldOptions
from pages.sale.manual.pharma_bill import PharmaBill
from pages.stock.round2_c4.sold_out_batch import STOCK_NOT_AVAILABLE, SoldOutBatchLine
from pages.stock.sale_impact.batch_list import BatchList
from pages.stock.sale_impact.documents import PRODUCT, sale_request
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("inventory"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = Decimal(1)


@pytest.fixture
def sold_out_batch(shop: Shop, batch: str) -> str:
    """The batch bought for this test, with all of its stock sold."""
    shop.sell_everything(batch)
    return batch


def test_sold_out_batch_is_refused_when_negative_stock_is_not_allowed(
    options: HeldOptions, bill: PharmaBill, sold_out_batch: str
) -> None:
    """Stock row 15 and bill row 169 (warning when the setting blocks): the batch cannot be picked."""
    options.hold(NEGATIVE_ALLOWED, "No")
    bill.start()
    line = SoldOutBatchLine(bill)
    line.open_all_batches(0)

    line.try_take(sold_out_batch)

    bill.messages.expect_warning(STOCK_NOT_AVAILABLE)
    line.expect_window_still_open()
    line.close_window()


def test_sold_out_batch_is_taken_and_warns_when_the_negative_stock_indication_is_on(
    options: HeldOptions, bill: PharmaBill, sold_out_batch: str
) -> None:
    """Bill rows 169 and 224: negative stock allowed, indication Yes: the toaster for stock going negative."""
    options.hold(NEGATIVE_ALLOWED, "Yes")
    options.hold(INDICATE_NEGATIVE, "Yes")
    bill.start()
    line = SoldOutBatchLine(bill)
    line.open_all_batches(0)
    line.take(sold_out_batch)

    bill.document.grid.enter_quantity(0, ONE)

    bill.messages.expect_warning(messages.STOCK_GOING_NEGATIVE)
    bill.expect_quantity_shown(0, ONE)


def test_sold_out_batch_is_taken_silently_when_the_negative_stock_indication_is_off(
    options: HeldOptions, bill: PharmaBill, sold_out_batch: str
) -> None:
    """Bill row 225: negative stock allowed, indication No: no toaster, the quantity stays."""
    options.hold(NEGATIVE_ALLOWED, "Yes")
    options.hold(INDICATE_NEGATIVE, "No")
    bill.start()
    line = SoldOutBatchLine(bill)
    line.open_all_batches(0)
    line.take(sold_out_batch)

    bill.document.grid.enter_quantity(0, ONE)

    bill.expect_quantity_shown(0, ONE)
    bill.messages.expect_no_warning(messages.STOCK_GOING_NEGATIVE)


def test_selling_more_than_the_batch_holds_takes_the_batch_below_zero(
    options: HeldOptions, shop: Shop, batch: str
) -> None:
    """Stock row 35: with negative stock allowed, 1 piece more than the batch holds is sold; the batch shows
    -1
    and the Item List, Batch List and Item Register all fall by the whole quantity sold."""
    options.hold(NEGATIVE_ALLOWED, "Yes")
    options.hold(INDICATE_NEGATIVE, "No")
    in_stock = BatchList(shop.page).quantity_of(PRODUCT, batch)
    sold = in_stock + ONE
    views = shop.views(batch)
    before = views.read()

    shop.bill(sale_request(batch, sold))

    views.expect_moved_by(before, -sold)
    assert BatchList(shop.page).quantity_of(PRODUCT, batch) == -ONE
