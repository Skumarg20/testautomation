"""GST and bill-discount invoice amounts.

The original suite checked these through a calculation helper (`chemistCalculation`) that was never committed,
so the formulas are unknown here. They stay skipped until the expected amounts can be computed independently.
"""

import pytest

pytestmark = [
    pytest.mark.p0,
    pytest.mark.journey("gst-calculation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

GST_TYPES = ["Exclusive", "Inclusive"]
BILL_DISCOUNTS = ["discount 1", "discount 2", "discounts 1 and 2", "discount amount"]

FORMULA_QUESTION = (
    "GS-01: the chemist bill needs chemist items that QA does not hold for {case}. The discount order is now "
    "known (item discount, then bill discount slabs on what is left: dataCalculation.ts:1242-1320) and is "
    "scripted with independent figures on the garments bill in "
    "tests/journeys/sales/manual/test_manual_garments_amounts.py (rows 100-103, 174, 176)."
)


@pytest.mark.parametrize("gst_type", GST_TYPES)
def test_invoice_amount_with_item_discounts_matches_the_gst_formula(gst_type: str) -> None:
    pytest.skip(FORMULA_QUESTION.format(case=f"{gst_type} GST with item and volume discounts"))


@pytest.mark.parametrize("gst_type", GST_TYPES)
@pytest.mark.parametrize("discount", BILL_DISCOUNTS)
def test_invoice_amount_with_a_bill_discount_matches_the_gst_formula(gst_type: str, discount: str) -> None:
    pytest.skip(FORMULA_QUESTION.format(case=f"{gst_type} GST with bill {discount}"))
