"""Sale promotion (scheme master) cases: Ajay rows 51, 131-134, 181, 182; Sale Checklist row 23.

Each test creates its own scheme (`run_id` in the name) through the API the Create Scheme screen uses, sells
item 44646015, and removes the scheme afterwards. The effect is read from the grid cell the app writes: `free`
for "Free Same Item" (Scheme.businesslogic.ts:1292-1325, setSameItemSchemeData :1492-1515), `discount1` for a
discount % (:1329-1350, setSameItemDiscPerSchemeData :1529-1561), `salePurchaseRate` for Rate Wise (:35-104).
Quantities are summed over the item's rows (CheckSchemeAppliedata :2158-2166) and compared by basis (">=" is
SchemeBasisEnum.GreaterThenEqualTo). The free quantity is the scheme's value, not proportional (:1503).
Schemes are tenant-wide and load when a bill opens, so the tests share the "chemist-tenant" worker group.
Request fixtures in this order: `schemes` first, so the bill closes before the Sales Promotion switch is
put back.
"""

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.components.bill_totals import BillTotals
from pages.masters.round2_c1.scheme_payload import (
    Basis,
    Criteria,
    OfferType,
    SchemeSpec,
    SchemeType,
    Slab,
)
from pages.sale.documents.document_requests import ProductLine
from pages.sale.documents.stock import StockLedger
from pages.sale.manual.pharma_bill import BATCH, ITEM, RATE
from pages.sale.round2_c1.cells import DISCOUNT_1, FREE, expect_invoice_close_to
from pages.sale.round2_c1.cells import RATE as RATE_COLUMN
from pages.sale.round2_c1.desk import Desk, SchemeKit
from pages.settings.bill_discount_configuration import BillDiscountConfiguration
from pages.settings.round2_c1.bill_discount_held import bill_discount_on

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

TOLERANCE = Decimal(1)
TEN = Decimal(10)
ONE = Decimal(1)
FIVE = Decimal(5)
FREE_ONE_FROM_TEN = Slab(Basis.AT_LEAST, 10, OfferType.FREE_SAME_ITEM, 1)


def _free_scheme(kit: SchemeKit) -> SchemeSpec:
    return kit.spec("Free", (SchemeType.ITEM_FREE_DISCOUNT, Criteria.ITEM), FREE_ONE_FROM_TEN)


def _sell(desk: Desk, quantity: Decimal) -> None:
    desk.bill.start()
    desk.bill.pick_item(0, quantity)


def test_scheme_gives_free_quantity(schemes: SchemeKit, desk: Desk) -> None:
    """Row 51 / checklist 23 (Item): buy 10, scheme ">= 10 gets 1 free" -> the free cell shows 1."""
    with schemes.created(_free_scheme(schemes)):
        _sell(desk, TEN)

        desk.cells.expect_value(0, FREE, ONE)


def test_scheme_of_another_item_does_not_apply(schemes: SchemeKit, desk: Desk) -> None:
    """Row 131: the scheme is made for a different item; 10 of 44646015 get no free quantity."""
    with schemes.created(_free_scheme(schemes), schemes.api.other_item(ITEM)):
        _sell(desk, TEN)

        desk.cells.expect_empty_or_zero(0, FREE)


@pytest.mark.parametrize("case", [(9, 0), (10, 1), (25, 1)], ids=["below", "at", "above"])
def test_quantity_slab_decides_the_scheme(schemes: SchemeKit, desk: Desk, case: tuple[int, int]) -> None:
    """Row 132: below the slab (9) nothing; at the slab (10) and above it (25) the scheme's 1 free."""
    quantity, free = case
    with schemes.created(_free_scheme(schemes)):
        _sell(desk, Decimal(quantity))

        if free:
            desk.cells.expect_value(0, FREE, Decimal(free))
        else:
            desk.cells.expect_empty_or_zero(0, FREE)


def test_changing_quantity_recalculates_the_scheme(schemes: SchemeKit, desk: Desk) -> None:
    """Row 133: 10 gets 1 free; changing the quantity to 5 takes the free quantity away."""
    with schemes.created(_free_scheme(schemes)):
        _sell(desk, TEN)
        desk.cells.expect_value(0, FREE, ONE)

        desk.bill.change_quantity(0, FIVE)

        desk.cells.expect_empty_or_zero(0, FREE)


def test_removing_the_item_removes_the_scheme(schemes: SchemeKit, desk: Desk) -> None:
    """Row 134: after the row is deleted, the same item at 5 pieces is billed with no free quantity."""
    with schemes.created(_free_scheme(schemes)):
        _sell(desk, TEN)
        desk.cells.expect_value(0, FREE, ONE)

        desk.bill.delete_row(1)
        desk.bill.pick_item(0, FIVE)

        desk.cells.expect_empty_or_zero(0, FREE)


def test_discount_scheme_sets_the_item_discount(schemes: SchemeKit, desk: Desk) -> None:
    """Checklist 23 (Item, discount): ">= 10 gets (Same) Discount 10 %" puts 10 in the Disc.1 cell."""
    slab = Slab(Basis.AT_LEAST, 10, OfferType.SAME_DISCOUNT_PERCENT, 10)
    with schemes.created(schemes.spec("Disc", (SchemeType.ITEM_FREE_DISCOUNT, Criteria.ITEM), slab)):
        _sell(desk, TEN)

        desk.cells.expect_value(0, DISCOUNT_1, TEN)


def test_rate_wise_scheme_sets_the_rate(schemes: SchemeKit, desk: Desk) -> None:
    """Checklist 23 (Rate wise): ">= 5 pieces get the rate 80" replaces the rate cell with 80."""
    slab = Slab(Basis.AT_LEAST, 5, OfferType.RATE, 80)
    with schemes.created(schemes.spec("Rate", (SchemeType.RATE_WISE, Criteria.ITEM), slab)):
        _sell(desk, FIVE)

        desk.cells.expect_value(0, RATE_COLUMN, Decimal(80))


def test_buy_x_get_y_by_company_discounts_the_row(schemes: SchemeKit, desk: Desk) -> None:
    """Checklist 23 (Buy X Get Y): any 3 pieces of the item's company get 10 % (Disc.1 = 10)."""
    slab = Slab(Basis.AT_LEAST, 3, OfferType.DIFF_DISCOUNT_PERCENT, 10)
    with schemes.created(schemes.spec("BxGy", (SchemeType.BUY_X_GET_Y, Criteria.COMPANY), slab)):
        _sell(desk, Decimal(3))

        desk.cells.expect_value(0, DISCOUNT_1, TEN)


def test_bill_value_scheme_is_offered_only_from_its_amount(schemes: SchemeKit, desk: Desk) -> None:
    """Checklist 23 (Bill Value): a ">= 500" scheme shows Load Scheme and its Apply icon at 600, neither
    at 100.

    revomeBillWiseScheme (:1168-1230) sets `applicable`; the button needs it
    (processout.transaction.component.html:1232) and so does the Apply icon (avaliableScheme.component.ts)."""
    slab = Slab(Basis.AT_LEAST, 0, OfferType.DIFF_DISCOUNT_PERCENT, 10, from_amount=500)
    with schemes.created(schemes.spec("Bill", (SchemeType.BILL_VALUE, Criteria.ITEM), slab)):
        desk.bill.start()
        desk.bill.add_line(0, ONE)
        load = desk.bill.page.locator("[id^=btnLoadScheme]")
        expect(load).to_have_count(0)

        desk.bill.change_quantity(0, Decimal(6))

        expect(load).to_be_visible()
        load.click()
        expect(desk.bill.page.locator("[id^=GridApplybtn]").first).to_be_visible()


def test_saved_scheme_bill_moves_stock_by_quantity_plus_free(schemes: SchemeKit, desk: Desk) -> None:
    """Row 181: selling 10 with 1 free reduces the item's stock by 11."""
    sold = (ProductLine(ITEM, BATCH, Decimal(11), RATE),)
    ledger = StockLedger(desk.bill.page)
    with schemes.created(_free_scheme(schemes)):
        before = ledger.snapshot(sold)
        desk.bill.start()
        desk.bill.add_line(0, TEN)
        desk.saved.save(desk.bill)

        ledger.expect_sold(before, sold)


def test_modifying_a_scheme_bill_recalculates_scheme_and_stock(schemes: SchemeKit, desk: Desk) -> None:
    """Row 182: the saved bill (10 + 1 free) is changed to 5; the free quantity goes, stock is down by 5."""
    sold = (ProductLine(ITEM, BATCH, FIVE, RATE),)
    ledger = StockLedger(desk.bill.page)
    with schemes.created(_free_scheme(schemes)):
        before = ledger.snapshot(sold)
        desk.bill.start()
        desk.bill.add_line(0, TEN)
        number = desk.saved.save(desk.bill)

        desk.bill.reopen(number)
        desk.bill.change_quantity(0, FIVE)
        desk.bill.save_changes()

        ledger.expect_sold(before, sold)


def test_bill_value_scheme_applies_its_discount(schemes: SchemeKit, desk: Desk) -> None:
    """Checklist 23 (Bill Value, applied): Load Scheme > Apply of a ">= 500 gets 10 %" scheme at 600 goods
    lowers the invoice value by 10 % (applySchemeDiscount, Scheme.businesslogic.ts:1066-1118, needs the bill
    discount switches). Compared within 1.00 because the invoice is rounded."""
    slab = Slab(Basis.AT_LEAST, 0, OfferType.DIFF_DISCOUNT_PERCENT, 10, from_amount=500)
    with schemes.created(schemes.spec("BillApply", (SchemeType.BILL_VALUE, Criteria.ITEM), slab)):
        desk.bill.start()
        with bill_discount_on(BillDiscountConfiguration(desk.bill.page)):
            desk.bill.add_line(0, Decimal(6))
            totals = BillTotals(desk.bill.page)
            before = totals.invoice_value()

            desk.bill.page.locator("[id^=btnLoadScheme]").click()
            desk.bill.page.locator("[id^=GridApplybtn]").first.click()

            expect_invoice_close_to(desk.bill.page, before * Decimal("0.9"), TOLERANCE)


def test_combo_scheme_is_offered_viewed_and_applied(schemes: SchemeKit, desk: Desk) -> None:
    """Checklist 23 (Combo Offer): a combo of two rows of the item (">= 2" each) with a 10 % offer.
    With 4 billed
    the Load Scheme window offers Apply and View (View shows "Combo Scheme Name - <name>"), and Apply puts
    10 in Disc.1: offer = 10 x (2 x floor(4 / 2)) / 4 (comboDiscoutapply :1015-1045, the quantity ratio
    :962). The combo turns applicable on the second evaluation (loadcomboScheme :2422-2437), so the quantity
    is entered twice."""
    slab = Slab(Basis.AT_LEAST, 2, OfferType.DIFF_DISCOUNT_PERCENT, 10)
    spec = schemes.spec("Combo", (SchemeType.COMBO_OFFER, Criteria.ITEM), slab)
    with schemes.created(spec):
        _sell(desk, Decimal(4))
        desk.bill.change_quantity(0, Decimal(4))
        page = desk.bill.page
        page.locator("[id^=btnLoadScheme]").click()

        page.get_by_title("View").first.click()
        expect(page.get_by_text(f"Combo Scheme Name - {spec.name}")).to_be_visible()
        page.keyboard.press("Escape")
        page.locator("[id^=GridApplybtn]").first.click()

        desk.cells.expect_value(0, DISCOUNT_1, TEN)


def test_no_scheme_item_is_left_out_of_other_schemes(schemes: SchemeKit, desk: Desk) -> None:
    """Checklist 23 (No Scheme): the item is listed in a No Scheme scheme, so a ">= 10 gets 1 free"
    scheme does
    not reach it (NoschemeDataRemove1 :2395-2420 drops the listed item ids from the rows and the quantity)."""
    no_scheme = schemes.spec(
        "None",
        (SchemeType.NO_SCHEME, Criteria.ITEM),
        Slab(Basis.AT_LEAST, 0, OfferType.SAME_DISCOUNT_PERCENT, 0),
    )
    with schemes.created(_free_scheme(schemes)), schemes.created(no_scheme):
        _sell(desk, TEN)

        desk.cells.expect_empty_or_zero(0, FREE)
