"""Purchase return refusals: an unknown bill number, and a quantity above what the batch holds."""

from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.purchase.documents import messages
from pages.purchase.documents.dates import todays_serial
from pages.purchase.documents.drafts import PurchaseDraft
from pages.purchase.documents.feedback import ToastKind
from pages.purchase.documents.line_items import STANDARD_ITEM_CODE, PurchaseLineItem
from pages.purchase.documents.return_page import PurchaseReturnPage
from pages.purchase.documents.seed_documents import SEED_PARTY, seed_stock_for

pytestmark = [pytest.mark.p1, pytest.mark.journey("purchase-itc"), pytest.mark.xdist_group("purchase-stock")]

UNKNOWN_BILL_NUMBER = "ZZ99999999"
UNKNOWN_BILL_SKIP = (
    "PRD-01 bill-details step, unknown Bill No.: Enter in Bill No. calls GetBillDetailsByBillNo and fills "
    "the bill only when status is 1 and the party matches (billdetails.component.ts:121-164, onBillNoBlur); "
    "the KB snippet ends before the not-found branch and no doc or careportal article (careportal:309058 "
    "covers only a known bill) states the answer. Live, no 'Bill No. not exist' warning appeared. Question: "
    "what should the user see for an unknown bill number: a 'Bill No. not exist' warning, an error toast, "
    "or nothing?"
)
SEEDED_STOCK = Decimal(150)  # the standard line: 100 bought and 50 free


@pytest.mark.skip(reason=UNKNOWN_BILL_SKIP)
def test_return_of_an_unknown_bill_number_is_refused(pharma_page: Page) -> None:
    returns = PurchaseReturnPage(pharma_page)

    returns.look_up_bill_number(SEED_PARTY, UNKNOWN_BILL_NUMBER)

    returns.feedback.expect_toast_saying(ToastKind.WARNING, messages.BILL_NUMBER_NOT_FOUND)
    returns.discard()


def test_return_above_the_stock_of_the_batch_is_refused(pharma_page: Page) -> None:
    returns = PurchaseReturnPage(pharma_page)
    too_many = PurchaseLineItem(STANDARD_ITEM_CODE, SEEDED_STOCK + 1, rate=Decimal(100))
    draft = seed_stock_for(pharma_page, PurchaseDraft(SEED_PARTY, todays_serial(), (too_many,)))
    returns.begin(draft)
    returns.enter_entry_date(draft.entry_date)
    returns.grid.select_product(0, too_many.product)
    returns.grid.pick_batch(0, draft.lines[0].batch)

    returns.grid.type_quantity(0, too_many.quantity)

    returns.feedback.expect_toast_saying(ToastKind.WARNING, messages.STOCK_NOT_AVAILABLE)
    returns.discard()
