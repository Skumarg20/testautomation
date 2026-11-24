"""J08 item master: create an item with the mandatory fields, find it in the Item List, delete it.

Plan: specs/item-master-crud.md (IM-01, IM-02, IM-03b, IM-04, IM-07, IM-11).
"""

from decimal import Decimal

import pytest

from pages.inventory.create_item_page import CreateItemPage
from pages.inventory.item_list_page import COMPANY, SALE_RATE, STOCK, UNIT, ItemListPage
from test_data.models import ItemMasterSpec

pytestmark = [pytest.mark.p1, pytest.mark.journey("item-master-crud")]


def test_item_with_mandatory_fields_is_saved_and_opening_stock_is_offered(
    create_item: CreateItemPage, new_item: ItemMasterSpec
) -> None:
    create_item.open()
    create_item.fill(new_item)
    create_item.save()

    create_item.expect_saved()
    create_item.expect_opening_stock_offered()
    create_item.decline_opening_stock()


def test_saved_item_is_listed_with_its_unit_company_and_sale_rate(
    saved_item: ItemMasterSpec, item_list: ItemListPage
) -> None:
    item_list.open()

    item_list.expect_listed(saved_item.product)
    assert item_list.cell_text(saved_item.product, UNIT) == saved_item.unit
    assert item_list.cell_text(saved_item.product, COMPANY) == saved_item.company
    assert item_list.cell_amount(saved_item.product, SALE_RATE) == saved_item.sale_rate


def test_item_saved_without_opening_stock_has_zero_stock(
    saved_item: ItemMasterSpec, item_list: ItemListPage
) -> None:
    item_list.open()
    item_list.expect_listed(saved_item.product)

    assert item_list.cell_amount(saved_item.product, STOCK) == Decimal(0)


def test_saved_item_shows_its_hsn_and_the_gst_split_of_its_tax_category(
    saved_item: ItemMasterSpec, item_list: ItemListPage
) -> None:
    item_list.open()
    item_list.select(saved_item.product)

    assert item_list.tax_info("HSN/SAC") == saved_item.hsn
    assert item_list.tax_rate("IGST %") == saved_item.gst_rate
    assert item_list.tax_rate("CGST %") == saved_item.half_gst_rate
    assert item_list.tax_rate("SGST %") == saved_item.half_gst_rate


def test_item_without_transactions_can_be_deleted(
    saved_item: ItemMasterSpec, item_list: ItemListPage
) -> None:
    item_list.open()
    item_list.delete(saved_item.product)

    item_list.expect_not_listed(saved_item.product)
