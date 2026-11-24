"""J40 Material Issue and Material Received: main-store stock of this run's own items after each step.

Figures are the pack's worked example: RM-A 100 and RM-B 50, BOM FG 1 = RM-A 2 + RM-B 1, issue for 10 sets.
"""

import re
from collections.abc import Callable
from decimal import Decimal

import pytest

from pages.manufacturing.bom_master import BomMasterList
from pages.manufacturing.stock_vouchers import MaterialIssue, RawMaterialsConsumedWindow
from pages.stock.item_stock_balance import ItemStockBalance
from test_data.manufacturing import (
    RM_A_OPENING,
    RM_B_OPENING,
    SETS_ISSUED,
    SETS_MORE_THAN_ISSUED,
    SETS_RECEIVED_IN_PART,
    BomSpec,
)

# The fixtures switch a tenant-wide Control Room option on and back (spec N1).
pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]

Receive = Callable[[Decimal], None]
StartReceive = Callable[[Decimal], RawMaterialsConsumedWindow]


def test_material_issue_takes_raw_materials_out_of_the_main_store(
    material_issue: MaterialIssue, saved_bom: BomSpec, stock: ItemStockBalance
) -> None:
    """MF-14: RM-A 100 -> 80 and RM-B 50 -> 40 for 10 sets issued."""
    raw_a, raw_b = saved_bom.raw_materials
    assert stock.main_store_stock(raw_a.item.product) == RM_A_OPENING - raw_a.for_sets(SETS_ISSUED)
    assert stock.main_store_stock(raw_b.item.product) == RM_B_OPENING - raw_b.for_sets(SETS_ISSUED)


def test_raw_materials_consumed_window_lists_bom_quantities_for_the_sets_received(
    start_receive: StartReceive, saved_bom: BomSpec
) -> None:
    """MF-18: receiving 10 FG lists RM-A 20 and RM-B 10 (BOM qty x 10)."""
    window = start_receive(SETS_ISSUED)
    for component in saved_bom.raw_materials:
        window.expect_quantity(component.item.product, component.for_sets(SETS_ISSUED))


def test_material_receive_adds_the_finished_items(
    receive: Receive, saved_bom: BomSpec, stock: ItemStockBalance
) -> None:
    """MF-18: FG 0 -> 10."""
    receive(SETS_ISSUED)
    assert stock.main_store_stock(saved_bom.finished.product) == SETS_ISSUED


def test_material_receive_does_not_take_raw_materials_out_again(
    receive: Receive, saved_bom: BomSpec, stock: ItemStockBalance
) -> None:
    """MF-18: RM-A stays 80 and RM-B 40 after the receive (SalePurchaseCommon.cs:431-446)."""
    receive(SETS_ISSUED)
    raw_a, raw_b = saved_bom.raw_materials
    assert stock.main_store_stock(raw_a.item.product) == RM_A_OPENING - raw_a.for_sets(SETS_ISSUED)
    assert stock.main_store_stock(raw_b.item.product) == RM_B_OPENING - raw_b.for_sets(SETS_ISSUED)


def test_partial_receive_adds_only_the_sets_received(
    receive: Receive, saved_bom: BomSpec, stock: ItemStockBalance
) -> None:
    """MF-19: 10 sets issued, 7 received: FG +7."""
    receive(SETS_RECEIVED_IN_PART)
    assert stock.main_store_stock(saved_bom.finished.product) == SETS_RECEIVED_IN_PART


def test_receive_of_more_sets_than_issued_is_refused(start_receive: StartReceive, saved_bom: BomSpec) -> None:
    """MF-20: 11 FG needs RM-A 22 > 20 pending: "<RM-A> Quantity Not Available", the window stays."""
    raw_a = saved_bom.raw_materials[0].item.product
    window = start_receive(SETS_MORE_THAN_ISSUED)
    window.expect_refused(re.compile(rf"{re.escape(raw_a)} Quantity Not Available"))


def test_bom_with_a_receive_cannot_be_deleted(
    receive: Receive, bom_list: BomMasterList, saved_bom: BomSpec
) -> None:
    """MF-24: "Bill of Material Already Used" and the row stays."""
    receive(SETS_ISSUED)
    bom_list.open()
    bom_list.delete(saved_bom.name)
    bom_list.expect_delete_refused_as_used()
    bom_list.expect_listed(saved_bom)
