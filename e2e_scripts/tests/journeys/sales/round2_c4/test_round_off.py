"""Sale bill row 97: the invoice value follows "Round Off Required in Sale ?" (No, Auto, Upper, Lower).

One bill (item 44646015, 1 piece at 100 with 3.33% item discount, so the invoice has paise) is totalled with
the option at No (the unrounded value U), then at Auto, Upper and Lower; the expected value is the rule
applied
to U (`invoice_after_round_off`). Labels of the choices: unverified live (a wrong one lists the offered ones).
"""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.components.bill_totals import BillTotals
from pages.dashboard_page import DashboardPage
from pages.sale.manual.pharma_bill import PharmaBill
from pages.sale.round2_c3.control_room_choice import ControlRoomChoices
from pages.sale.round2_c4.round_off import OPTION_NAME, RoundOff, invoice_after_round_off

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("gst-calculation"),
    pytest.mark.xdist_group("chemist-tenant"),
]


@pytest.fixture
def round_off_option(sales_page: Page) -> Iterator[ControlRoomChoices]:
    room = ControlRoomChoices(sales_page)
    original = room.current(OPTION_NAME)
    yield room
    DashboardPage(sales_page).open()
    room.choose(OPTION_NAME, original)


def invoice_with(room: ControlRoomChoices, bill: PharmaBill, mode: RoundOff) -> Decimal:
    DashboardPage(bill.page).open()
    room.choose(OPTION_NAME, mode.value)
    DashboardPage(bill.page).open()
    bill.start()
    bill.add_discounted_line(0, Decimal(1), Decimal("3.33"))
    value = BillTotals(bill.page).invoice_value()
    bill.leave_without_saving()
    return value


@pytest.mark.parametrize("mode", [RoundOff.AUTO, RoundOff.UPPER, RoundOff.LOWER], ids=lambda m: m.value)
def test_invoice_value_follows_the_round_off_choice(
    round_off_option: ControlRoomChoices, bill: PharmaBill, mode: RoundOff
) -> None:
    unrounded = invoice_with(round_off_option, bill, RoundOff.NO)
    assert unrounded != unrounded.to_integral_value()

    rounded = invoice_with(round_off_option, bill, mode)

    assert rounded == invoice_after_round_off(unrounded, mode)
