"""An item's rate A to H, set in the Item Master, must be the rate billed when that rate is the default."""

import pytest

from pages.sale.chemist.rate_validation_page import RateValidationPage
from pages.sale.chemist.sale_bill import SaleBill
from test_data.discounts import RATE_VALIDATION
from test_data.models import HeaderTag, ItemEntry

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("rate-validation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

QUANTITY = 2


@pytest.mark.parametrize("rate_letter", sorted(RATE_VALIDATION.rates))
def test_billed_rate_matches_the_rate_set_in_item_master(
    rates: RateValidationPage, sale_bill: SaleBill, rate_letter: str
) -> None:
    expected_rate = RATE_VALIDATION.rates[rate_letter]
    rates.change_item_rate(RATE_VALIDATION.item_description, rate_letter, expected_rate)
    sale_bill.start(HeaderTag.BASE)
    rates.set_default_billing_rate(rate_letter)

    sale_bill.add_item(0, ItemEntry(description=RATE_VALIDATION.item_description, quantity=QUANTITY))

    assert sale_bill.sale_rate_of(0) == expected_rate
