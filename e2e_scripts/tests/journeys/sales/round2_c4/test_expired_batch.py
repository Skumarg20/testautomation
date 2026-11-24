"""Sale bill rows 70 and 82: an expired batch in the sale batch window.

A batch expiring today is bought for the test (expiry equal to today passes the purchase check, which refuses
only earlier dates: dataCalculation.ts:2906). In the sale batch window a batch whose expiry is today or
earlier
is never taken: "<item> <batch> Expired!" (`expDateValidation`, processinbatch.component.ts:841 and
:1086). The
option "Allow Rate/ZERO Rate or Ban/Indicate for Expired Items" has no reader in the batch window (it is
only a
field of the settings model), so no setting choice makes an expired batch selectable.
DECISION NEEDED: what that option is meant to change. Near-expiry ban ("2") is a separate rule, not
tested here.
"""

import pytest

from pages.sale.manual.pharma_bill import PharmaBill
from pages.stock.round2_c4.batch_window import BatchWindowOfBill
from pages.stock.round2_c4.sold_out_batch import SoldOutBatchLine
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]


def test_batch_expiring_today_is_refused_as_expired(shop: Shop, bill: PharmaBill) -> None:
    expired = shop.buy_batch_expiring_in(0)
    bill.start()
    window = BatchWindowOfBill(bill)
    window.open(0)

    SoldOutBatchLine(bill).try_take(expired)

    bill.messages.expect_warning(f"{expired} Expired!")
    SoldOutBatchLine(bill).expect_window_still_open()
    window.close()
