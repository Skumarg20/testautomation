"""Additional ledger / charges on the sale bill: Ajay rows 59, 126-130, 178.

The charge is an expense ledger the test creates (Indirect Expenses, name with the run id) and deletes
afterwards. One item row is billed first (the Additional Details grid refuses a charge before an item,
componentPlaceHolder.template.ts:157-160). Percentage charge = (goods - bill discount) x % / 100
(dataCalculation.ts:872-880, :959-971), an amount charge is the typed amount, the invoice value is goods +
charges (+ GST on a GST-applicable charge, :837-846, 1020-1130). Goods = quantity x rate with the Rate*Qty
calculation held, no bill discount. Expected figures come from pages/sale/round2_c1/deal_math.py.
"""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.components.bill_totals import BillTotals
from pages.masters.master_records import MasterRecords
from pages.masters.round2_c1.taxable_charge import make_gst_applicable
from pages.sale.manual.option_settings import AMOUNT_CALCULATION, HeldOptions
from pages.sale.manual.pharma_bill import RATE, PharmaBill
from pages.sale.round2_c1.additional_charges import AdditionalChargesGrid
from pages.sale.round2_c1.deal_math import charge_by_percentage, charge_tax
from pages.sale.round2_c1.desk import Desk
from test_data.masters import INDIRECT_EXPENSES, MasterDataFactory

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

QUANTITY = Decimal(10)
GOODS = QUANTITY * RATE
NO_DISCOUNT = Decimal(0)


@pytest.fixture
def charge_records(pharma_page: Page, run_id: str) -> Iterator[MasterRecords]:
    records = MasterRecords(pharma_page, MasterDataFactory(run_id))
    yield records
    records.delete_all()


@pytest.fixture
def charge(charge_records: MasterRecords) -> str:
    return charge_records.saved_general_ledger(INDIRECT_EXPENSES).name


@pytest.fixture
def second_charge(charge_records: MasterRecords) -> str:
    return charge_records.saved_general_ledger(INDIRECT_EXPENSES).name


@pytest.fixture
def goods_bill(options: HeldOptions, bill: PharmaBill) -> tuple[PharmaBill, AdditionalChargesGrid]:
    options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    bill.start()
    bill.add_line(0, QUANTITY)
    return bill, AdditionalChargesGrid(bill.page)


def _invoice(bill: PharmaBill) -> BillTotals:
    return BillTotals(bill.page)


def test_charge_in_percentage(charge: str, goods_bill: tuple[PharmaBill, AdditionalChargesGrid]) -> None:
    """Rows 59 and 126: 5 % of goods 1000 = 50.00 on the charge row."""
    bill, grid = goods_bill
    grid.add_charge(charge)

    grid.set_percentage(charge, Decimal(5))

    grid.expect_amount(charge, charge_by_percentage(GOODS, NO_DISCOUNT, Decimal(5)))


def test_charge_as_fixed_amount_is_added_to_the_invoice(
    charge: str, goods_bill: tuple[PharmaBill, AdditionalChargesGrid]
) -> None:
    """Row 127: a typed 75 stays 75 on the row and the invoice value rises by exactly 75."""
    bill, grid = goods_bill
    before = _invoice(bill).invoice_value()
    grid.add_charge(charge)

    grid.set_amount(charge, Decimal(75))

    grid.expect_amount(charge, Decimal(75))
    _invoice(bill).expect_invoice_value(before + Decimal(75))


def test_several_charges_are_all_added(
    charge: str, second_charge: str, goods_bill: tuple[PharmaBill, AdditionalChargesGrid]
) -> None:
    """Row 128: 5 % (50.00) and 30 fixed raise the invoice value by 80.00."""
    bill, grid = goods_bill
    before = _invoice(bill).invoice_value()
    grid.add_charge(charge)
    grid.set_percentage(charge, Decimal(5))
    grid.add_charge(second_charge)

    grid.set_amount(second_charge, Decimal(30))

    _invoice(bill).expect_invoice_value(before + charge_by_percentage(GOODS, NO_DISCOUNT, Decimal(5)) + 30)


def test_removing_a_charge_restores_the_invoice(
    charge: str, goods_bill: tuple[PharmaBill, AdditionalChargesGrid]
) -> None:
    """Row 130: after a 75 charge is deleted the invoice value is what it was before the charge."""
    bill, grid = goods_bill
    before = _invoice(bill).invoice_value()
    grid.add_charge(charge)
    grid.set_amount(charge, Decimal(75))

    grid.remove_charge(charge)

    grid.expect_absent(charge)
    _invoice(bill).expect_invoice_value(before)


def test_taxable_charge_carries_gst(charge: str, pharma_page: Page, desk: Desk) -> None:
    """Rows 129 and 178: a GST-applicable charge of 100 raises the invoice by 100 + 100 x rate / 100."""
    rate = make_gst_applicable(pharma_page, charge)
    desk.options.hold(AMOUNT_CALCULATION, "Rate*Qty")
    desk.bill.start()
    desk.bill.add_line(0, QUANTITY)
    grid = AdditionalChargesGrid(desk.bill.page)
    before = _invoice(desk.bill).invoice_value()
    grid.add_charge(charge)

    grid.set_amount(charge, Decimal(100))

    _invoice(desk.bill).expect_invoice_value(before + Decimal(100) + charge_tax(Decimal(100), rate))
