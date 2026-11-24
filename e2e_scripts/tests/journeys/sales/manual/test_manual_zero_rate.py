"""Manual cases 62, 63, 172, 173, 223 (sheet "Sale Bill (Ajay)"): a zero or blank billing rate.

Rule, from `processout.transaction.component.ts` (the sale bill): with "Indicate if Billing Rate is Zero"
not "No", a rate of 0 or a blank one (a blank is first turned into 0.00, :12418-12421) asks "Are you sure
you want to go with 0 rate?" when the rate is entered (:12443-12445); "No" asks nothing. With "Indicate on
Item and Bill" the save asks again, "<n> items has rate value 0. Accept?" (:10357-10366). Saying No keeps
the user on the rate cell (:12446-12452). The option texts "Indicate on Item", "Indicate on Item and Bill"
and "No" are from the KB article "How to enable or disable indication if billing Rate is zero".
Nothing is saved: every test leaves the bill open and the fixture discards it.
"""

from dataclasses import dataclass
from decimal import Decimal

import pytest

from pages.sale.manual import messages
from pages.sale.manual.option_settings import ZERO_RATE, HeldOptions
from pages.sale.manual.pharma_bill import PharmaBill

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ON_ITEM = "Indicate on Item"
ON_ITEM_AND_BILL = "Indicate on Item and Bill"
NOT_INDICATED = "No"
ONE_UNIT = Decimal(1)


@dataclass(frozen=True)
class RateEntry:
    """The setting in force and what is typed into the rate cell ("" clears it)."""

    indication: str
    typed: str


INDICATED = [
    pytest.param(RateEntry(setting, typed), id=f"{label}-{name}")
    for setting, label in ((ON_ITEM, "on-item"), (ON_ITEM_AND_BILL, "on-item-and-bill"))
    for typed, name in (("0", "rate-0"), ("", "rate-blank"))
]
NOT_INDICATED_ENTRIES = [
    pytest.param(RateEntry(NOT_INDICATED, "0"), id="rate-0"),
    pytest.param(RateEntry(NOT_INDICATED, ""), id="rate-blank"),
]


@pytest.mark.parametrize("entry", INDICATED)
def test_zero_or_blank_rate_asks_for_confirmation_when_indicated(
    options: HeldOptions, bill: PharmaBill, entry: RateEntry
) -> None:
    """Rows 62 (blank rate), 63 and 172 (zero rate, "warning as per setting")."""
    options.hold(ZERO_RATE, entry.indication)
    bill.start()
    bill.pick_item(0, ONE_UNIT)

    bill.type_rate(0, entry.typed)

    bill.messages.expect_question(messages.ZERO_RATE_ASKED)
    bill.messages.answer_no()


@pytest.mark.parametrize("entry", NOT_INDICATED_ENTRIES)
def test_zero_or_blank_rate_asks_nothing_when_not_indicated(
    options: HeldOptions, bill: PharmaBill, entry: RateEntry
) -> None:
    """Row 173: "Disable indication, sell at zero: the warning should not appear"."""
    options.hold(ZERO_RATE, entry.indication)
    bill.start()
    bill.pick_item(0, ONE_UNIT)

    bill.type_rate(0, entry.typed)

    bill.messages.expect_no_question(messages.ZERO_RATE_ASKED)


def test_save_asks_again_about_zero_rate_lines_on_item_and_bill(
    options: HeldOptions, bill: PharmaBill
) -> None:
    """Row 223 ("toaster for invoice zero should appear") and the save half of row 62; nothing is saved."""
    options.hold(ZERO_RATE, ON_ITEM_AND_BILL)
    bill.start()
    bill.pick_item(0, ONE_UNIT)
    bill.type_rate(0, "0")
    bill.messages.expect_question(messages.ZERO_RATE_ASKED)
    bill.messages.answer_yes()

    bill.try_save()

    bill.messages.expect_question(f"1 {messages.ZERO_RATE_AT_SAVE}")
    bill.messages.answer_no()
