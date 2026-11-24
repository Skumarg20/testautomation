"""J37 the store's catalogue: the rate items go up at (OS-11), uploading (OS-31), unmapping and hiding (OS-32)
and Marg Mart's upload (OS-33).

Catalogue writes change the store for good, so they are answered by stubs on a page whose catalogue writes are
guarded; only `test_uploaded_item_is_counted_as_mapped` uploads for real and is marked `permanent`.
"""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import expect

from pages.components.stubbed_endpoint import StubbedEndpoint
from pages.online_store.marg_mart_items import MargMartItemList
from pages.online_store.order_dashboard import OrderDashboard
from pages.online_store.store_endpoints import (
    HIDE_STORE_ITEMS,
    INSERT_STORE_ITEMS,
    ITEMS_HIDDEN_REPLY,
    ITEMS_INSERTED_REPLY,
    MARG_MART_IMPORT_ONE_REPLY,
    MARG_MART_IMPORT_REFUSED_REPLY,
    MARG_MART_ITEM_RECORD,
    MARG_MART_ITEMS_RECORDED_REPLY,
    MARG_MART_PRODUCT_IMPORT,
)
from pages.online_store.store_items import StoreItemList
from pages.stock.messages import StockMessages
from test_data.models import ItemMasterSpec
from test_data.online_store import (
    HIDE_QUESTION,
    ITEM_HIDDEN,
    ITEMS_UNMAPPED,
    ITEMS_UPLOADED,
    MARG_MART_LIMIT_REACHED,
    MARG_MART_UPLOADED,
    MRP_RATE,
    RATE_B,
    UNMAP_QUESTION,
    UPLOAD_QUESTION,
)

pytestmark = [pytest.mark.p3, pytest.mark.journey("online-store")]

NO_MAPPED_ITEM = "OS-32: the own store has no mapped item to unmap or hide"
OpenItemList = Callable[[], StoreItemList]


def _expect_message(list_page: StoreItemList | MargMartItemList, text: str) -> None:
    StockMessages(list_page.page).expect_shown(re.compile(re.escape(text)))


@pytest.fixture
def mapped_item_list(guarded_item_list: StoreItemList) -> StoreItemList:
    guarded_item_list.show_mapped()
    if not guarded_item_list.has_rows():
        pytest.skip(NO_MAPPED_ITEM)
    return guarded_item_list


@pytest.fixture
def item_ticked(own_item: ItemMasterSpec, guarded_item_list: StoreItemList) -> StoreItemList:
    """Requested after `own_item` so the item exists before the list opens."""
    guarded_item_list.search(own_item.product)
    guarded_item_list.tick(own_item.product)
    return guarded_item_list


@pytest.fixture
def marg_mart_items(own_item: ItemMasterSpec, marg_mart_dashboard: OrderDashboard) -> MargMartItemList:
    """Marg Mart's Manage Item list with this test's item ticked (the item is created before it opens)."""
    marg_mart_dashboard.open_manage_items()
    items = MargMartItemList(marg_mart_dashboard.page)
    items.expect_open()
    items.tick(own_item.product)
    return items


@pytest.mark.xdist_group("chemist-tenant")
def test_item_price_is_captioned_with_the_chosen_rate(
    choose_store_rate: Callable[[str], None], open_item_list: OpenItemList, own_item: ItemMasterSpec
) -> None:
    """OS-11: with Rate B chosen, Edit Product's price is captioned "Rate B" (captions: verify live)."""
    choose_store_rate(RATE_B)
    window = open_item_list().edit(own_item.product)
    assert window.price_caption() == RATE_B


@pytest.mark.xdist_group("chemist-tenant")
def test_item_price_follows_the_chosen_rate(
    choose_store_rate: Callable[[str], None], open_item_list: OpenItemList, own_item: ItemMasterSpec
) -> None:
    """OS-11, KB vs live 11: with M.R.P chosen the upload price is the item's M.R.P, not Rate A."""
    choose_store_rate(MRP_RATE)
    window = open_item_list().edit(own_item.product)
    assert window.price() == own_item.mrp


def test_upload_asks_to_confirm_the_number_of_items(item_ticked: StoreItemList) -> None:
    """OS-31: "Do you really want to upload 1 item(s)?" (answered No: nothing is sent)."""
    question = item_ticked.ask_to_upload()
    question.expect_asking(UPLOAD_QUESTION.format(count=1))
    question.answer_no()


def test_confirmed_upload_sends_the_ticked_item(own_item_link_id: str, item_ticked: StoreItemList) -> None:
    """OS-31: the upload gets the ticked item's linkid; "Item(s) uploaded successfully" shows."""
    upload = StubbedEndpoint(item_ticked.page, INSERT_STORE_ITEMS)
    upload.answer_with(ITEMS_INSERTED_REPLY)
    question = item_ticked.ask_to_upload()
    sent = upload.capture_one(question.answer_yes)
    assert [str(link) for link in sent.json_body()["itemlinkids"]] == [own_item_link_id]
    _expect_message(item_ticked, ITEMS_UPLOADED)


@pytest.mark.permanent("this test's item uploaded (mapped) into the company's own Online Store")
def test_uploaded_item_is_counted_as_mapped(open_item_list: OpenItemList, own_item: ItemMasterSpec) -> None:
    """OS-31: after the upload "Mapped Item (n)" rises by one."""
    items = open_item_list()
    mapped_before = items.mapped_count()
    items.search(own_item.product)
    items.tick(own_item.product)
    items.ask_to_upload().answer_yes()
    _expect_message(items, ITEMS_UPLOADED)
    assert open_item_list().mapped_count() == mapped_before + 1


def test_unmap_needs_a_ticked_item(mapped_item_list: StoreItemList) -> None:
    """OS-32: with nothing ticked unmapping is refused; the source disables "Un-Map Item" (as K1)."""
    expect(mapped_item_list.unmap_button).to_be_disabled()


def test_confirmed_unmap_reports_success(mapped_item_list: StoreItemList) -> None:
    """OS-32: "Do you really want to unmap 1 item(s)?", then "Item(s) unmapped successfully" (stubbed)."""
    unmap = StubbedEndpoint(mapped_item_list.page, HIDE_STORE_ITEMS)
    unmap.answer_with(ITEMS_HIDDEN_REPLY)
    mapped_item_list.tick_first_row()
    question = mapped_item_list.ask_to_unmap()
    question.expect_asking(UNMAP_QUESTION.format(count=1))
    unmap.capture_one(question.answer_yes)
    _expect_message(mapped_item_list, ITEMS_UNMAPPED)


def test_confirmed_hide_reports_success(mapped_item_list: StoreItemList) -> None:
    """OS-32: "Do you really want to hide this item ?", then "Item Hide Successfully" (stubbed)."""
    hide = StubbedEndpoint(mapped_item_list.page, HIDE_STORE_ITEMS)
    hide.answer_with(ITEMS_HIDDEN_REPLY)
    question = mapped_item_list.ask_to_hide_first_row()
    question.expect_asking(HIDE_QUESTION)
    hide.capture_one(question.answer_yes)
    _expect_message(mapped_item_list, ITEM_HIDDEN)


def test_marg_mart_upload_reports_the_uploaded_count(marg_mart_items: MargMartItemList) -> None:
    """OS-33: Marg Mart accepts the item: "1 Products successfully uploaded" (margmart.com stubbed)."""
    page = marg_mart_items.page
    product_import = StubbedEndpoint(page, MARG_MART_PRODUCT_IMPORT)
    product_import.answer_with(MARG_MART_IMPORT_ONE_REPLY)
    StubbedEndpoint(page, MARG_MART_ITEM_RECORD).answer_with(MARG_MART_ITEMS_RECORDED_REPLY)
    product_import.capture_one(marg_mart_items.upload)
    _expect_message(marg_mart_items, MARG_MART_UPLOADED.format(count=1))


def test_marg_mart_upload_over_the_plan_limit_says_limit_reached(marg_mart_items: MargMartItemList) -> None:
    """OS-33: Marg Mart accepts nothing (plan limit): "Limit Reached" (margmart.com stubbed)."""
    product_import = StubbedEndpoint(marg_mart_items.page, MARG_MART_PRODUCT_IMPORT)
    product_import.answer_with(MARG_MART_IMPORT_REFUSED_REPLY)
    product_import.capture_one(marg_mart_items.upload)
    _expect_message(marg_mart_items, MARG_MART_LIMIT_REACHED)
