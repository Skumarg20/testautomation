"""Manual cases 24, 25, 64, 65, 77, 104-107: editing, repeating and deleting rows of an unsaved bill.

Item 44646015 is sold on every row (the only item with a known batch), quantities 1, 2 and 3 tell the rows
apart. "Amount Calculation On Billing" is held at Rate*Qty so a row's amount is quantity x rate
(`dataCalculation.ts:750-757`, case '1'), and "Indicate if Item Repeated in Bill" at No so the same item may
be billed on several rows. Expected totals are the quantities times the rate of 100, never read from the
screen. Rules cited: a blank quantity warns "Quantity should be greater than 0!" when Enter leaves the
cell (`processout.transaction.component.ts:7345`, global.ts:18995); a save with no item warns "Please select
minimum one item!" (:10454, global.ts:19003). Nothing is saved.
"""

from decimal import Decimal

import pytest

from pages.sale.manual import messages
from pages.sale.manual.option_settings import AMOUNT_CALCULATION, ITEM_REPEATED, HeldOptions
from pages.sale.manual.pharma_bill import RATE, PharmaBill

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

RATE_TIMES_QUANTITY = "Rate*Qty"
NOT_INDICATED = "No"
ITEM_NOT_FOUND = "Please select minimum one item!"
QUANTITIES = [Decimal(1), Decimal(2), Decimal(3)]


def sale_of(quantities: list[Decimal]) -> Decimal:
    return sum(quantities, Decimal(0)) * RATE


@pytest.fixture
def plain_amounts(options: HeldOptions) -> None:
    """Amounts are rate x quantity and a repeated item is not questioned."""
    options.hold(AMOUNT_CALCULATION, RATE_TIMES_QUANTITY)
    options.hold(ITEM_REPEATED, NOT_INDICATED)


@pytest.fixture
def three_rows(plain_amounts: None, bill: PharmaBill) -> PharmaBill:
    """A bill with the same item on three rows: quantities 1, 2 and 3."""
    bill.start()
    for row, quantity in enumerate(QUANTITIES):
        bill.add_line(row, quantity)
    return bill


@pytest.mark.usefixtures("plain_amounts")
def test_same_item_twice_makes_two_separate_rows(bill: PharmaBill) -> None:
    """Rows 65 and 77 ("merge or add a separate row according to configuration"): the No configuration."""
    bill.start()
    bill.add_line(0, QUANTITIES[0])
    bill.add_line(1, QUANTITIES[1])

    bill.expect_quantities(QUANTITIES[:2])
    bill.expect_gross(sale_of(QUANTITIES[:2]))


@pytest.mark.usefixtures("plain_amounts")
def test_changing_the_quantity_changes_the_row_and_the_total(bill: PharmaBill) -> None:
    """Row 25: the amount follows the new quantity (4 x 100)."""
    new_quantity = Decimal(4)
    bill.start()
    bill.add_line(0, Decimal(1))

    bill.change_quantity(0, new_quantity)

    bill.expect_quantities([new_quantity])
    bill.expect_gross(sale_of([new_quantity]))


def test_blank_quantity_is_refused(bill: PharmaBill) -> None:
    """Row 64: clearing the quantity of a filled row warns that a quantity is needed."""
    bill.start()
    bill.pick_item(0, Decimal(1))

    bill.type_quantity(0, "")

    bill.messages.expect_warning(messages.QUANTITY_REQUIRED)


@pytest.mark.parametrize("position", [1, 2, 3], ids=["first", "middle", "last"])
def test_deleting_one_row_keeps_the_other_rows_and_the_total(three_rows: PharmaBill, position: int) -> None:
    """Rows 105, 106 and 107."""
    remaining = [quantity for number, quantity in enumerate(QUANTITIES, start=1) if number != position]

    three_rows.delete_row(position)

    three_rows.expect_quantities(remaining)
    three_rows.expect_gross(sale_of(remaining))


def test_deleting_every_row_empties_the_grid_and_the_bill_is_not_saved(three_rows: PharmaBill) -> None:
    """Row 104: "grid should become empty and bill should not save"."""
    for _ in QUANTITIES:
        three_rows.delete_row(1)

    three_rows.expect_quantities([])
    three_rows.try_save()
    three_rows.messages.expect_warning(ITEM_NOT_FOUND)
