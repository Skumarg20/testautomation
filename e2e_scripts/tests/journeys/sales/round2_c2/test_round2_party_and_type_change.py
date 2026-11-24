"""Ajay rows 73, 87 (customer change after items) and 74, 88 (sale type change after items).

Party: Sample Item 3 x 100 at 5% to the intra-state "Ajay" gives CGST 7.50 + SGST 7.50; changing the party
to the
other-state "Arun Sharma" must give IGST 15.00 and the same invoice value 315.00 (test_data.gst_calc; the app
resets the tax block and recalculates on a party change: processout.transaction.component.ts:3379-3386).
Sale type: with "Ask Sale Type at the time of Billing?" = Yes, choosing another type than the bill's clears
the
lines and the tax block (processout.transaction.component.ts:4867-4876). Decision needed: the sheet says
"recalculate"; the code resets and the user re-enters the lines.
"""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.components.bill_totals import BillTotals
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from pages.sale.manual.option_settings import ASK_SALE_TYPE, HeldOptions, SaleBillSettings
from pages.sale.round2_c2.party_and_type import SaleTypeBox, change_party
from test_data.gst_calc import line_tax

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ITEM = "Sample Item"
RATE = Decimal(100)
QUANTITY = Decimal(3)
SLAB = Decimal(5)
INTRA_STATE_PARTY = "Ajay"
INTER_STATE_PARTY = "Arun Sharma"


@pytest.fixture
def sale(guarded_page: Page) -> Iterator[GarmentsSalePage]:
    bill = GarmentsSalePage(guarded_page)
    bill.open_new_bill()
    yield bill
    BillTotals(guarded_page).leave_without_saving()


def test_changing_the_party_after_items_moves_the_tax_to_igst(sale: GarmentsSalePage) -> None:
    taxable = RATE * QUANTITY
    local = line_tax(taxable, SLAB, intra_state=True)
    sale.choose_party(INTRA_STATE_PARTY)
    sale.add_item(0, ITEM, QUANTITY)
    totals = BillTotals(sale.page)
    totals.expect_tax_amounts({"CGST Output": local.cgst, "SGST Output": local.sgst})

    change_party(sale.page, INTER_STATE_PARTY)

    other = line_tax(taxable, SLAB, intra_state=False)
    totals.expect_tax_amounts({"IGST Output": other.igst})
    totals.expect_invoice_value(taxable + other.total_tax)


def test_changing_the_sale_type_after_items_clears_the_lines(sale: GarmentsSalePage) -> None:
    held = HeldOptions(SaleBillSettings(sale.page), lambda: None, lambda: None)
    try:
        held.hold(ASK_SALE_TYPE, "Yes")
        box = SaleTypeBox(sale.page)
        sale.choose_party(INTRA_STATE_PARTY)
        sale.add_item(0, ITEM, QUANTITY)
        current = box.current()
        other = next(name for name in box.offered() if name.lower() != current.lower())

        box.choose(other)

        assert sale.line_amount(0) == 0
        assert not BillTotals(sale.page).tax_amounts()
    finally:
        held.close()
