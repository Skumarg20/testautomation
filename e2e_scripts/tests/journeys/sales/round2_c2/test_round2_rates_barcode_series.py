"""Ajay rows 11, 29, 94 and Sale checklist row 82.

Row 11 (pharma item 44646015, batch 1231231123): with "Rates from master/batch" = Batch the grid takes the
batch's MRP (dataCalculation.ts:1664-1672), compared with the MRP the batch window shows; with Master the
grid rate is the item's own sale rate (dataCalculation.ts:1586-1588), compared with the Item List's sale-
rate column. Row 29: the app refuses a second item with a barcode already used (ItemMasterDal.cs:268-280
"Duplicate Barcode Found!", global.ts:19526), so a bill can never meet one barcode on two items; the
sheet's "multiple items window" cannot be reached (Decision needed). Row 94: with "Ask Sale Type" = Yes a
sale type that is not Item Wise gives every line the type's own rate (dataCalculation.ts:1853-1860). Row
82: one series per Criteria option is created in Control Room > Multi Series and each must be offered in
"Select Series".
"""

import re
from collections.abc import Callable, Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page, expect

from config.settings import Account
from pages.accounting.waiting import appears_within
from pages.components.bill_totals import BillTotals
from pages.dashboard_page import DashboardPage
from pages.inventory.item_list_page import SALE_RATE, ItemListPage
from pages.masters.round2_c2.owned_items import DUPLICATE_BARCODE, OwnedItems
from pages.sale.documents.flows import open_sales_page
from pages.sale.documents.item_grid import PRICE
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from pages.sale.manual.option_settings import (
    ASK_SALE_TYPE,
    HeldOptions,
    SaleBillSettings,
    SettingField,
    setting_held,
)
from pages.sale.manual.pharma_bill import BATCH, ITEM, PharmaBill
from pages.sale.round2_c2.party_and_type import SaleTypeBox
from pages.sale.round2_c2.series import MultiSeriesConfig, series_cell
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held
from test_data.gst_calc import line_tax
from test_data.money import parse_amount

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

RATE_SOURCE = SettingField("rateFromMasterBatchDate", "Rates from master/batch")
BATCH_COLUMN_MRP = '[col-id="mrp"]'
MRP_LOOKUP_MS = 10_000
SAMPLE = "Sample Item"
SAMPLE_RATE = Decimal(100)
QUANTITY = Decimal(3)


@pytest.fixture
def pharma_bill(page_as: Callable[[Account], Page]) -> Iterator[PharmaBill]:
    bill = PharmaBill(open_sales_page(page_as))
    yield bill
    if bill.is_open():
        bill.leave_without_saving()


def _batch_window_mrp(bill: PharmaBill) -> Decimal:
    """Opens the batch window of row 0 and reads the MRP of batch 1231231123; the window stays open."""
    page = bill.page
    bill.document.grid.select_product(0, ITEM)
    names = page.locator('[col-id="batchName"]')
    if not appears_within(names.first, 2_000):
        bill.document.grid.cell(0, "batchLinkID").press("Enter")
    row = page.locator(".ag-row").filter(has=names.get_by_text(BATCH, exact=True)).first
    return parse_amount(row.locator(BATCH_COLUMN_MRP).inner_text())


def test_batch_mode_takes_the_batch_mrp(pharma_bill: PharmaBill) -> None:
    """Row 11, batch half."""
    pharma_bill.start()
    held = HeldOptions(SaleBillSettings(pharma_bill.page), lambda: None, lambda: None)
    with setting_held(held._settings, RATE_SOURCE, "batch"):  # noqa: SLF001
        shown = _batch_window_mrp(pharma_bill)
        pharma_bill.document.selection.choose_cell_value(BATCH)

        grid_mrp = parse_amount(pharma_bill.document.grid.cell(0, "mrp").inner_text())

        assert grid_mrp == shown


def test_master_mode_takes_the_items_sale_rate(pharma_bill: PharmaBill) -> None:
    """Row 11, master half. Decision needed: the party's rate type (A to H) picks the master rate."""
    page = pharma_bill.page
    pharma_bill.start()
    held = HeldOptions(SaleBillSettings(page), lambda: None, lambda: None)
    with setting_held(held._settings, RATE_SOURCE, "master"):  # noqa: SLF001
        pharma_bill.pick_item(0, Decimal(1))
        rate = parse_amount(pharma_bill.document.grid.cell(0, PRICE).inner_text())
        pharma_bill.leave_without_saving()
        items = ItemListPage(page)
        DashboardPage(page).open()
        items.open()
        items.expect_listed(ITEM)

        assert rate == items.cell_amount(ITEM, SALE_RATE)


def test_second_item_with_a_used_barcode_is_refused(
    guarded_page: Page, items: OwnedItems, run_id: str
) -> None:
    barcode = f"9{int(run_id, 16) % 10**11:011d}"
    items.saved_with_barcode(items.spec(), barcode)

    form = items.refused_with_barcode(items.spec(), barcode)

    form.expect_refused_with(DUPLICATE_BARCODE)
    DashboardPage(guarded_page).open()


def test_sale_type_gives_every_line_its_own_gst_rate(guarded_page: Page) -> None:
    """Row 94: pick a sale type with a percentage in its name, add Sample Item 3 x 100, expect that rate."""
    sale = GarmentsSalePage(guarded_page)
    sale.open_new_bill()
    held = HeldOptions(SaleBillSettings(guarded_page), lambda: None, lambda: None)
    try:
        held.hold(ASK_SALE_TYPE, "Yes")
        box = SaleTypeBox(guarded_page)
        sale.choose_party("Ajay")
        priced = [name for name in box.offered() if re.search(r"\d+(\.\d+)?\s*%", name)]
        if not priced:
            pytest.skip("row 94: no sale type of the company carries its rate in its name")
        rate = Decimal(re.search(r"(\d+(?:\.\d+)?)\s*%", priced[0])[1])  # type: ignore[index]
        box.choose(priced[0])

        sale.add_item(0, SAMPLE, QUANTITY)

        tax = line_tax(SAMPLE_RATE * QUANTITY, rate, intra_state=True)
        totals = BillTotals(guarded_page)
        totals.expect_tax_amounts({"CGST Output": tax.cgst, "SGST Output": tax.sgst})
    finally:
        held.close()
        BillTotals(guarded_page).leave_without_saving()


def test_every_series_criteria_is_offered_in_a_new_bill(guarded_page: Page, run_id: str) -> None:
    """Row 82: a series for each Criteria option (group wise, agency wise, ...) appears in Select Series."""
    state = ControlRoomState(guarded_page)
    with switch_held(state, SwitchValue("Multi Series", "Yes")):
        config = MultiSeriesConfig(guarded_page)
        config.open()
        options = config.criteria_options()
        names = [f"QA{index}{run_id[:4]}" for index in range(len(options))]
        try:
            for index, name in enumerate(names):
                config.create(name, index)
            config.close()
            guarded_page.keyboard.press("Alt+N")
            for name in names:
                expect(series_cell(guarded_page, name)).to_be_visible()
            guarded_page.keyboard.press("Escape")
        finally:
            config.open()
            for name in names:
                config.delete(name)
            config.close()
