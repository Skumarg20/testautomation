"""Sale checklist rows 30 (selling at a loss) and 77 (minimum level crossed).

Row 30. "Net Loss and Margin Loss Indication" (Configure on the Setting window, lookup 1157) is Forcefully
(0), Indicate (1) or No (2). `applyNetLossSetting` (processout:12938-12950): No ends the check, the other
two open the Net Loss window when the rate does not clear the cost. The window
(netloss.component.html:54-64) has Yes and No buttons for Indicate and a single OK for Forcefully; OK closes
with status false when the loss is above 0 (netloss.component.ts:114), the rate cell is re-opened with "Net
Loss and Margin Loss Indication is Forcefully applied" (global.ts:19305, processout:13397-13400) and a save
is refused with "Item with Forced Loss:" (global.ts:19006, processout:10796). The item is bought at 100, so
a rate of 1 is a loss. The checklist words the row "(if warning disable)"; both readings are tried and the
open question is Q-C3-5.

Row 77. With "Indicate if Stock going Minimum/Maximum" Yes (Configure 'maxormin') and the item's Minimum
Quantity M > 0, a sale that leaves stock below M warns "Minimum Level Crossed!" (`itemminvalcross`,
processout:13811-13829, global.ts:19323): stock 100, M 90, selling 20 leaves 80; selling 5 leaves 95.
"""

from decimal import Decimal

import pytest

from pages.accounting.waiting import appears_within
from pages.sale.round2_c3.configure_settings import LOSS_INDICATION, MINIMUM_LEVEL_INDICATION
from pages.sale.round2_c3.owned_stock import BatchSpec, StockSpec
from pages.sale.round2_c3.sale_desk import SaleDesk
from pages.sale.round2_c3.stock_bill import StockLine

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

LOSS_RATE = Decimal(1)
FORCED_WARNING = "Net Loss and Margin Loss Indication is Forcefully applied"
FORCED_AT_SAVE = "Item with Forced Loss:"
MINIMUM_WARNING = "Minimum Level Crossed!"
LOSS_WINDOW_WAIT_MS = 5_000
SAVE_WINDOW_LOOKUP_MS = 3_000
SOLD_PIECES = Decimal(1)
STOCK = Decimal(100)
MINIMUM = 90
ONE_BATCH = StockSpec(batches=(BatchSpec(Decimal(180), Decimal(120)),))
WITH_MINIMUM = StockSpec(
    batches=(BatchSpec(Decimal(180), Decimal(120), quantity=STOCK),), minimum_quantity=MINIMUM
)


def sell_below_cost(desk: SaleDesk) -> None:
    item = desk.make_stock(ONE_BATCH)
    desk.sell(StockLine(item, item.batch_names[0], SOLD_PIECES))
    desk.bill.type_rate(0, LOSS_RATE)


def test_forced_loss_blocks_the_sale(desk: SaleDesk) -> None:
    """Row 30 (Forcefully): the loss window offers only OK; after it the forced-loss warning shows and the
    bill cannot be saved."""
    desk.options.hold(LOSS_INDICATION, "Forcefully")
    sell_below_cost(desk)
    page = desk.bill.bill.page
    assert appears_within(page.locator("#btnOk"), LOSS_WINDOW_WAIT_MS)
    assert page.locator("#btnYes").count() == 0

    page.locator("#btnOk").click()

    desk.bill.bill.messages.expect_warning(FORCED_WARNING)
    desk.bill.bill.save()
    desk.bill.bill.messages.expect_warning(FORCED_AT_SAVE)
    assert not appears_within(desk.bill.bill.document.save_window, SAVE_WINDOW_LOOKUP_MS)


def test_indicated_loss_asks_and_lets_the_sale_go_on_when_confirmed(desk: SaleDesk) -> None:
    """Row 30 (Indicate): the loss window asks Yes or No; Yes keeps the rate of 1 on the row."""
    desk.options.hold(LOSS_INDICATION, "Indicate")
    sell_below_cost(desk)
    page = desk.bill.bill.page
    assert appears_within(page.locator("#btnYes"), LOSS_WINDOW_WAIT_MS)

    page.locator("#btnYes").click()

    assert desk.bill.picked_rate(0) == LOSS_RATE


def test_no_loss_indication_lets_a_loss_sale_through_without_a_window(desk: SaleDesk) -> None:
    """Row 30 (warning disabled): nothing is asked and the rate of 1 stays on the row."""
    desk.options.hold(LOSS_INDICATION, "No")

    sell_below_cost(desk)

    page = desk.bill.bill.page
    assert not appears_within(page.locator("#btnYes").or_(page.locator("#btnOk")), LOSS_WINDOW_WAIT_MS)
    assert desk.bill.picked_rate(0) == LOSS_RATE


@pytest.mark.parametrize(
    ("quantity", "warns"), [(Decimal(20), True), (Decimal(5), False)], ids=["crossed", "kept"]
)
def test_minimum_level_warning_follows_the_stock_left(desk: SaleDesk, quantity: Decimal, warns: bool) -> None:
    """Row 77: stock 100 with minimum 90 warns when 20 are sold (80 left) and not when 5 are (95 left)."""
    item = desk.make_stock(WITH_MINIMUM)
    desk.options.hold(MINIMUM_LEVEL_INDICATION, "Yes")

    desk.sell(StockLine(item, item.batch_names[0], quantity))

    if warns:
        desk.bill.bill.messages.expect_warning(MINIMUM_WARNING)
    else:
        desk.bill.bill.messages.expect_no_warning(MINIMUM_WARNING)
