"""Stock rows 26 and 34, on an item the test makes itself (part C3's `OwnedStock`, so no QA item is assumed).

Row 26: replacing item A by item B on a saved bill gives A's stock back and takes B's (steps of the old
skipped
stub). Row 34: the sale batch window lists batches in the order of the sale setting "Batch window index on"
(`openBatchWindowIndexOn`, salebill.setting.html:728-742), which the API turns into ORDER BY expiry date (1),
mfg date (2), entry date = first in first out (3, the default) or batch name (4)
(BatchAndStockOpeningBalance2.cs:312-345). "Earliest expiry" and "FIFO" of the sheet are the values 1 and 3.
Enter in the open window takes the highlighted first row (processinbatch.component.ts:979-981).
"""

from decimal import Decimal

import pytest

from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.stock import StockLedger
from pages.sale.manual.option_settings import HeldOptions, SettingField
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.round2_c3.owned_stock import BatchSpec, StockFactory, StockSpec
from pages.stock.round2_c4.batch_window import BatchWindowOfBill
from pages.stock.sale_impact.documents import sale_request
from pages.stock.sale_impact.modify import SavedDocument
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-modification"),
    pytest.mark.xdist_group("chemist-tenant"),
]

BATCH_WINDOW_INDEX = SettingField("openBatchWindowIndexOn", "Batch window index on", True)
SOLD = Decimal(3)
RATE = Decimal(150)
LATE_EXPIRY_DAYS = 400
EARLY_EXPIRY_DAYS = 100


def test_replacing_the_item_restores_the_old_items_stock_and_takes_the_new_ones(
    shop: Shop, batch: str, stock_factory: StockFactory
) -> None:
    other = stock_factory(StockSpec(batches=(BatchSpec(mrp=Decimal(200), rate_a=RATE),)))
    ledger = StockLedger(shop.page)
    a_views = shop.views(batch)
    a_before = a_views.read()
    b_before = ledger.stock_of(other.code)
    number = shop.bill(sale_request(batch, SOLD))

    saved = SavedDocument(SaleBillDocument(shop.page), number)
    saved.reopen()
    SaleBillDocument(shop.page).add_line(0, ProductLine(other.code, other.batch_names[0], SOLD, RATE))
    saved.save_again()

    a_views.expect_moved_by(a_before, Decimal(0))
    assert ledger.stock_of(other.code) == b_before - SOLD


@pytest.fixture
def two_batches(stock_factory: StockFactory) -> tuple[str, str, str]:
    """(item code, batch bought first but expiring later, batch bought second and expiring sooner)."""
    item = stock_factory(
        StockSpec(
            batches=(
                BatchSpec(mrp=Decimal(200), rate_a=RATE, expiry_in_days=LATE_EXPIRY_DAYS),
                BatchSpec(mrp=Decimal(200), rate_a=RATE, expiry_in_days=EARLY_EXPIRY_DAYS),
            )
        )
    )
    first, second = item.batch_names
    return item.code, first, second


def test_expiry_index_lists_the_sooner_expiring_batch_first(
    options: HeldOptions, bill: PharmaBill, two_batches: tuple[str, str, str]
) -> None:
    code, _, sooner = two_batches
    options.hold(BATCH_WINDOW_INDEX, "Expiry")
    bill.start()
    window = BatchWindowOfBill(bill)

    window.open(0, code)

    assert window.listed_names()[0] == sooner
    window.press("Enter")
    bill.expect_batch_in_row(0, sooner)


def test_entry_date_index_lists_the_batch_bought_first_first(
    options: HeldOptions, bill: PharmaBill, two_batches: tuple[str, str, str]
) -> None:
    code, first_in, _ = two_batches
    options.hold(BATCH_WINDOW_INDEX, "FIFO")
    bill.start()
    window = BatchWindowOfBill(bill)

    window.open(0, code)

    assert window.listed_names()[0] == first_in
    window.press("Enter")
    bill.expect_batch_in_row(0, first_in)
