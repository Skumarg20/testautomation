"""J08 item master: required fields, duplicate names and editing an item.

Plan: specs/item-master-crud.md (IM-13, IM-13b, IM-14, IM-09).
"""

import re

import pytest

from pages.inventory.create_item_page import CreateItemPage, LookupField
from pages.inventory.item_list_page import SALE_RATE, ItemListPage
from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

pytestmark = [pytest.mark.p1, pytest.mark.journey("item-master-crud")]

# Case-blind for the same reason as the save message: CSS capitalises the DOM text.
DUPLICATE_NEEDS_PACKING = re.compile("Packing Is Required For Duplicate Product Names", re.IGNORECASE)


def test_save_with_an_empty_form_asks_for_the_product(create_item: CreateItemPage) -> None:
    create_item.open()
    create_item.save()

    create_item.expect_product_required()


@pytest.mark.parametrize("field", list(LookupField), ids=lambda field: field.name.lower())
def test_save_with_only_a_product_marks_each_empty_lookup(
    create_item: CreateItemPage, data: DataFactory, field: LookupField
) -> None:
    create_item.open()
    create_item.enter_product(data.item_master().product)
    create_item.save()

    create_item.expect_marked_invalid(field)


def test_save_with_only_a_product_saves_nothing(
    create_item: CreateItemPage, item_list: ItemListPage, new_item: ItemMasterSpec
) -> None:
    create_item.open()
    create_item.enter_product(new_item.product)
    create_item.save()

    item_list.open()
    item_list.expect_not_listed(new_item.product)


def test_second_item_with_the_same_name_and_no_packing_is_refused(
    saved_item: ItemMasterSpec, create_item: CreateItemPage, item_list: ItemListPage
) -> None:
    create_item.open()
    create_item.fill(saved_item)
    create_item.save()

    create_item.expect_refused_with(DUPLICATE_NEEDS_PACKING)
    item_list.open()
    item_list.expect_listed(saved_item.product)


def test_edited_hsn_and_sale_rate_are_kept(
    saved_item: ItemMasterSpec, create_item: CreateItemPage, item_list: ItemListPage
) -> None:
    edited = DataFactory.edited_item(saved_item)
    item_list.open()
    item_list.edit(saved_item.product)
    create_item.expect_editing(saved_item.product)
    create_item.change_hsn(edited.hsn)
    create_item.change_sale_rate(edited.sale_rate)
    create_item.save()

    create_item.expect_updated()
    item_list.open()
    item_list.select(saved_item.product)
    assert item_list.tax_info("HSN/SAC") == edited.hsn
    assert item_list.cell_amount(saved_item.product, SALE_RATE) == edited.sale_rate
