"""Offline checks of the ported page objects against small HTML mocks. No MargBooks app required."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from playwright.sync_api import Page, expect

from pages.components.sale_bill_header import SaleBillHeader
from pages.grid.chemist_sale_grid import ChemistSaleGrid, MissingItemKeyError
from test_data.discounts import RATE_VALIDATION
from test_data.headers import HEADERS
from test_data.models import BillHeader, HeaderTag, ItemEntry
from test_data.sale_items import A_TO_Z_NS, CHEMIST_SALE_ITEMS

pytestmark = pytest.mark.framework

BILL_GRID_HTML = """
<div class="ag-body-container">
  <div class="ag-row">
    <div col-id="itemLinkID">A To Z Ns</div>
    <div col-id="tmp_barcode"><input id="barcode"></div>
    <div col-id="unitToEnteredValue"><input id="quantity" value="3"></div>
    <div col-id="salePurchaseRate"><input id="rate"></div>
    <div col-id="discount1"><input id="d1"></div>
    <div col-id="discount2"><input id="d2"></div>
    <div col-id="volumediscount"><input id="v1"></div>
    <div col-id="volumediscount2"><input id="v2"></div>
  </div>
</div>
"""

READ_ONLY_GRID_HTML = """
<div class="ag-body-container">
  <div class="ag-row">
    <div col-id="itemLinkID">  BioZentra  </div>
    <div col-id="unitToEnteredValue">12</div>
    <div col-id="salePurchaseRate">1,250.50</div>
    <div col-id="discount1">4.00</div>
  </div>
</div>
"""

HEADER_HTML = """
<input id="txtbillDate1">
<input formcontrolname="PatientName">
<input formcontrolname="DoctorName">
"""


def test_grid_reads_numbers_with_thousand_separators_as_decimals(page: Page) -> None:
    page.set_content(READ_ONLY_GRID_HTML)

    grid = ChemistSaleGrid(page)

    assert grid.sale_rate_of(0) == Decimal("1250.50")
    assert grid.quantity_of(0) == Decimal(12)
    assert grid.discount1_of(0) == Decimal(4)


def test_grid_reads_the_product_name_trimmed(page: Page) -> None:
    page.set_content(READ_ONLY_GRID_HTML)

    assert ChemistSaleGrid(page).product_of(0) == "BioZentra"


def test_changing_a_quantity_types_it_into_the_row_input(page: Page) -> None:
    page.set_content(BILL_GRID_HTML)

    ChemistSaleGrid(page).change_quantity(0, 7)

    expect(page.locator("#quantity")).to_have_value("7")


def test_discounts_are_entered_up_to_the_last_one_given(page: Page) -> None:
    page.set_content(BILL_GRID_HTML)

    ChemistSaleGrid(page).change_discounts(0, ItemEntry(discount1=2, volume_discount1=5))

    expect(page.locator("#d1")).to_have_value("2")
    expect(page.locator("#d2")).to_have_value("")
    expect(page.locator("#v1")).to_have_value("5")


def test_adding_an_item_without_barcode_itemcode_or_description_is_an_error(page: Page) -> None:
    page.set_content(BILL_GRID_HTML)

    with pytest.raises(MissingItemKeyError):
        ChemistSaleGrid(page).add_item(0, ItemEntry(quantity=1))


def test_header_types_the_date_relative_to_today(page: Page) -> None:
    page.set_content(HEADER_HTML)

    SaleBillHeader(page).fill(BillHeader(date_offset_days=2))

    expected = (date.today() + timedelta(days=2)).strftime("%d/%m/%Y")
    expect(page.locator("#txtbillDate1")).to_have_value(expected)


def test_header_fills_patient_and_doctor_and_skips_fields_not_on_the_page(page: Page) -> None:
    page.set_content(HEADER_HTML)

    SaleBillHeader(page).fill(BillHeader(patient_name="Asha", doctor="Dr Rao", address="Delhi"))

    expect(page.locator('[formcontrolname="PatientName"]')).to_have_value("Asha")
    expect(page.locator('[formcontrolname="DoctorName"]')).to_have_value("Dr Rao")


def test_every_header_tag_has_a_preset() -> None:
    assert set(HEADERS) == set(HeaderTag)


def test_item_entry_prefers_barcode_then_item_code_then_description() -> None:
    assert A_TO_Z_NS.entry().barcode == A_TO_Z_NS.barcode
    assert CHEMIST_SALE_ITEMS[1].entry().itemcode == CHEMIST_SALE_ITEMS[1].itemcode
    assert CHEMIST_SALE_ITEMS[2].entry().description == CHEMIST_SALE_ITEMS[2].description


def test_each_rate_a_to_h_has_its_own_value() -> None:
    assert len(set(RATE_VALIDATION.rates.values())) == len(RATE_VALIDATION.rates) == 8
