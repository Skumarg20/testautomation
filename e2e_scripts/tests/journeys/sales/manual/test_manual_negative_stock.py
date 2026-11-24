"""Manual cases 45, 46, 169, 170, 171, 191, 192, 224, 225: selling more than the batch holds.

Rule, from `processout.transaction.component.ts` `applyStockNegativeSetting` (:12713), run when a quantity
is entered on the sale bill (:7608):
- "Stock Negative allowed" = Yes: any quantity is added; with "Indicate if going in negative stock" = Yes
  the bill warns "Stock going in negative!" (:12853-12857, global.ts:19322); with No it stays silent
  (:12834-12839).
- "Stock Negative allowed" = No: the quantity is cut to what the batch holds and the bill warns "Salable
  stock <n>." (:12809-12817, global.ts:19337); the item is not added with the quantity asked for.
Both are drop-downs of the sale bill's Setting window (`negativeAllowed`, `isGoingtoNegativeStock`).
The quantity asked for is far above any QA batch, so the cases do not read the batch stock; nothing is saved.
"""

from dataclasses import dataclass
from decimal import Decimal

import pytest

from pages.sale.manual import messages
from pages.sale.manual.option_settings import INDICATE_NEGATIVE, NEGATIVE_ALLOWED, HeldOptions
from pages.sale.manual.pharma_bill import PharmaBill

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("inventory"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ABOVE_ANY_BATCH = Decimal(99999)


@dataclass(frozen=True)
class StockRules:
    allowed: str
    indicate: str


def hold_rules(options: HeldOptions, rules: StockRules) -> None:
    options.hold(NEGATIVE_ALLOWED, rules.allowed)
    options.hold(INDICATE_NEGATIVE, rules.indicate)


def sell_above_stock(bill: PharmaBill) -> None:
    bill.start()
    bill.pick_item(0, ABOVE_ANY_BATCH)


def test_negative_stock_allowed_adds_the_item_and_indicates_it(
    options: HeldOptions, bill: PharmaBill
) -> None:
    """Rows 45, 191 (item adds to the grid), 169 and 170 (negative-stock warning on), 224 (toaster shows)."""
    hold_rules(options, StockRules(allowed="Yes", indicate="Yes"))

    sell_above_stock(bill)

    bill.messages.expect_warning(messages.STOCK_GOING_NEGATIVE)
    bill.expect_quantity_shown(0, ABOVE_ANY_BATCH)


def test_negative_stock_allowed_without_indication_adds_the_item_silently(
    options: HeldOptions, bill: PharmaBill
) -> None:
    """Rows 171 and 225: the warning is switched off, the item still adds."""
    hold_rules(options, StockRules(allowed="Yes", indicate="No"))

    sell_above_stock(bill)

    bill.expect_quantity_shown(0, ABOVE_ANY_BATCH)
    bill.messages.expect_no_warning(messages.STOCK_GOING_NEGATIVE)


def test_negative_stock_not_allowed_cuts_the_quantity_to_the_stock(
    options: HeldOptions, bill: PharmaBill
) -> None:
    """Rows 46 and 192: the item does not go into the grid with the quantity asked for."""
    hold_rules(options, StockRules(allowed="No", indicate="No"))

    sell_above_stock(bill)

    bill.messages.expect_warning(messages.SALABLE_STOCK)
    bill.expect_quantity_not_shown(0, ABOVE_ANY_BATCH)
