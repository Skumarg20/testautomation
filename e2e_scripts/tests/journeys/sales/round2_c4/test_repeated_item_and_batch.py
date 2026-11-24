"""Sale bill rows 65, 66, 77, 78: the same item (and the same batch) twice on one bill.

Rule: `RepeatedItemBill` docstring (item window, `IndicateIfItemRepeatedInBill`). The rule looks at the item
only, so the same batch twice is governed by the same setting; with "No" both rows are kept and the batch is
reduced by the sum of the rows (stock arithmetic, not read from the screen under test).
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from pages.sale.documents.document_requests import ProductLine
from pages.sale.manual.option_settings import AMOUNT_CALCULATION, ITEM_REPEATED, HeldOptions
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.round2_c4.repeat_item import (
    FOLLOW_STRICTLY,
    INDICATE,
    ITEM_ALREADY_EXISTS,
    NOT_INDICATED,
    REPEATED_ITEM_REFUSED,
    RepeatedItemBill,
)
from pages.stock.sale_impact.documents import PRODUCT, SALE_PRICE, sale_request
from pages.stock.sale_impact.shop import Shop

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE = Decimal(1)
TWO = Decimal(2)


def test_indicate_warns_and_still_adds_the_repeated_item(options: HeldOptions, bill: PharmaBill) -> None:
    options.hold(ITEM_REPEATED, INDICATE)
    bill.start()
    bill.add_line(0, ONE)

    bill.add_line(1, TWO)

    bill.messages.expect_warning(ITEM_ALREADY_EXISTS)
    bill.expect_quantities([ONE, TWO])


def test_follow_strictly_adds_the_repeated_item_when_answered_yes(
    options: HeldOptions, bill: PharmaBill
) -> None:
    options.hold(ITEM_REPEATED, FOLLOW_STRICTLY)
    options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    bill.start()
    bill.add_line(0, ONE)
    repeat = RepeatedItemBill(bill)

    repeat.pick_item_again(1)
    repeat.expect_asked_about_row(1)
    repeat.answer_yes()
    repeat.complete_line(1, TWO)

    bill.expect_quantities([ONE, TWO])


def test_follow_strictly_refuses_the_repeated_item_when_answered_no(
    options: HeldOptions, bill: PharmaBill
) -> None:
    """Same item and same batch as row 1: the batch does not matter to the rule."""
    options.hold(ITEM_REPEATED, FOLLOW_STRICTLY)
    bill.start()
    bill.add_line(0, ONE)
    repeat = RepeatedItemBill(bill)

    repeat.pick_item_again(1)
    repeat.expect_asked_about_row(1)
    repeat.answer_no()

    bill.messages.expect_warning(REPEATED_ITEM_REFUSED)
    repeat.close_item_window()
    bill.expect_quantities([ONE])


def test_same_batch_on_two_rows_takes_both_quantities_from_the_batch(
    options: HeldOptions, shop: Shop, batch: str
) -> None:
    options.hold(ITEM_REPEATED, NOT_INDICATED)
    options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    request = sale_request(batch, Decimal(3))
    twice = replace(request, lines=(*request.lines, ProductLine(PRODUCT, batch, Decimal(4), SALE_PRICE)))
    views = shop.views(batch)
    before = views.read()

    shop.bill(twice)

    views.expect_moved_by(before, -Decimal(7))
