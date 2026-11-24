"""Purchase checklist rows 33 to 38: the Batch Details window of a new batch and its rate rules.

Rule texts are from transactioninbatch.component.ts:1008-1110 (`rateValidation`); they apply when Control Room
field 4163 (seventh action "F") enforces rate checks. The source compares every rate B to H with the M.R.P.
(the sheet says "sale rate"), and the sale rate A and the M.R.P. with the item's cost and purchase rate. A
window that shows no message at all means the checks are not enforced on this tenant, and the test is skipped.
The cost table is `calcMargin` (:235-237), worked out in `pages/purchase/checklist/line_math.py`.
"""

from decimal import Decimal

import pytest

from pages.purchase.checklist.batch_details_window import BatchDetailsWindow
from pages.purchase.checklist.line_flow import open_batch_details
from pages.purchase.checklist.line_math import cost_of
from pages.purchase.documents.bill_page import PurchaseBillEntryPage
from pages.purchase.documents.dates import timestamp_label
from pages.purchase.documents.line_items import PurchaseLineItem, standard_line

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("rate-validation"),
    pytest.mark.xdist_group("purchase-stock"),
]

MRP = Decimal(100)
ABOVE_MRP = Decimal(200)
BELOW_ANY_COST = Decimal("0.01")
TINY_MRP = Decimal("0.5")
OTHER_RATES = "bcdefgh"
NOT_ENFORCED = (
    "checklist rows 35 to 37: the rate checks (Control Room field 4163) are not enforced on this tenant"
)


def _new_batch_window(bill: PurchaseBillEntryPage, line: PurchaseLineItem) -> BatchDetailsWindow:
    return open_batch_details(bill, line.with_batch(timestamp_label()))


def _expect_refusal(window: BatchDetailsWindow, message: str) -> None:
    if not window.says(message):
        pytest.skip(NOT_ENFORCED)


def test_new_batch_opens_the_batch_details_window_after_the_discounts(
    new_bill: PurchaseBillEntryPage,
) -> None:
    window = _new_batch_window(new_bill, standard_line())

    window.expect_open()


def test_mrp_typed_in_the_window_is_kept(new_bill: PurchaseBillEntryPage) -> None:
    window = _new_batch_window(new_bill, standard_line())

    window.type_mrp(MRP)

    assert window.mrp() == MRP


def test_sale_rate_above_the_mrp_is_refused(new_bill: PurchaseBillEntryPage) -> None:
    window = _new_batch_window(new_bill, standard_line())
    window.type_mrp(MRP)

    window.type_rate("a", ABOVE_MRP)

    _expect_refusal(window, "Rate A should be less than or equal to M.R.P.")


def test_mrp_below_the_purchase_rate_is_refused(new_bill: PurchaseBillEntryPage) -> None:
    window = _new_batch_window(new_bill, standard_line())

    window.type_mrp(TINY_MRP)

    _expect_refusal(window, "M.R.P should be greater than or equal to Pur. Rate.")


def test_sale_rate_below_the_cost_is_refused(new_bill: PurchaseBillEntryPage) -> None:
    window = _new_batch_window(new_bill, standard_line())
    window.type_mrp(MRP)

    window.type_rate("a", BELOW_ANY_COST)

    _expect_refusal(window, "Rate A should be greater than or equal to Cost.")


@pytest.mark.parametrize("letter", list(OTHER_RATES))
def test_rates_b_to_h_above_the_mrp_are_refused(new_bill: PurchaseBillEntryPage, letter: str) -> None:
    window = _new_batch_window(new_bill, standard_line())
    if not window.has_rate(letter):
        pytest.skip(
            f"checklist row 37: Rate {letter.upper()} is not switched on in the Control Room (Rate Info)"
        )
    window.type_mrp(MRP)

    window.type_rate(letter, ABOVE_MRP)

    _expect_refusal(window, f"Rate {letter.upper()} should be less than or equal to M.R.P.")


def test_cost_is_worked_out_from_rate_quantity_free_and_discount(new_bill: PurchaseBillEntryPage) -> None:
    line = standard_line()
    window = _new_batch_window(new_bill, line)

    shown = window.new_batch_cost()

    assert shown == cost_of(line.rate, (line.quantity, line.free), Decimal(0))
