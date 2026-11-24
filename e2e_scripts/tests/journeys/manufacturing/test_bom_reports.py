"""J40 Bill of Materials reports: Pending & Register (MF-19), Costing (MF-27), Production Planning (MF-28).

The column names come from `sp_Bomreport`, which is not in the API repo (pages/manufacturing/bom_reports.py).
"""

from collections.abc import Callable
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.manufacturing.bom_reports import CostingReport, PendingRegister, ProductionPlanning
from test_data.manufacturing import (
    PLANNED_SETS,
    PLANNED_SETS_CHANGED,
    PRODUCTION_DEPARTMENT,
    SETS_ISSUED,
    SETS_RECEIVED_IN_PART,
    BomSpec,
)

pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("manufacturing-module"),
    pytest.mark.xdist_group("chemist-tenant"),
]

Receive = Callable[[Decimal], None]
NOT_A_MANUFACTURER = "Cash"
QUANTITY = "Qty"
COST = "Cost"
VALUE = "Value"
REQUIRED_QUANTITY = "Required Qty"


def test_pending_register_shows_the_sets_not_yet_received(
    receive: Receive, saved_bom: BomSpec, bom_page: Page
) -> None:
    """MF-19: 10 issued, 7 received: 3 sets pending with Production Department, RM-A 6 and RM-B 3
    (KB `onedrive_processed_data.csv#50cbfc45`)."""
    receive(SETS_RECEIVED_IN_PART)
    register = PendingRegister(bom_page)
    register.open_for(PRODUCTION_DEPARTMENT)
    sets_pending = SETS_ISSUED - SETS_RECEIVED_IN_PART
    for component in saved_bom.raw_materials:
        assert register.pending_figure(component.item.product) == component.for_sets(sets_pending)


def test_pending_register_refuses_a_ledger_that_is_not_a_manufacturer(bom_page: Page) -> None:
    """MF-27 (pack wording) / billofmaterial.report.ts:413: "Please Select Only 'Sundry Creditor
    (Manufacturer)' A/C Ledgers"."""
    register = PendingRegister(bom_page)
    register.open_for(NOT_A_MANUFACTURER)
    register.expect_only_manufacturer_ledgers_taken()


def test_costing_lists_each_component_with_its_bom_quantity(saved_bom: BomSpec, bom_page: Page) -> None:
    """MF-27: RM-A 2 and RM-B 1 per finished item."""
    costing = CostingReport(bom_page)
    costing.open_for(saved_bom.finished.product)
    for component in saved_bom.raw_materials:
        assert costing.figure(component.item.product, QUANTITY) == component.quantity_per_set


def test_costing_component_value_is_quantity_times_cost(saved_bom: BomSpec, bom_page: Page) -> None:
    """MF-27: each component's value is its quantity x its unit cost (KB-doc BOM_v1.0 "Costing")."""
    costing = CostingReport(bom_page)
    costing.open_for(saved_bom.finished.product)
    for component in saved_bom.raw_materials:
        product = component.item.product
        expected = costing.figure(product, QUANTITY) * costing.figure(product, COST)
        assert costing.figure(product, VALUE) == expected


def test_costing_total_is_the_sum_of_the_component_values(saved_bom: BomSpec, bom_page: Page) -> None:
    """MF-27: the cost per unit is the sum of the component values (whether addition cost is in: N6)."""
    costing = CostingReport(bom_page)
    costing.open_for(saved_bom.finished.product)
    values = (costing.figure(component.item.product, VALUE) for component in saved_bom.raw_materials)
    assert costing.total(VALUE) == sum(values, Decimal(0))


def test_production_planning_multiplies_the_bom_by_the_planned_quantity(
    saved_bom: BomSpec, bom_page: Page
) -> None:
    """MF-28: From Current Stock, FG 10: RM-A 20 and RM-B 10."""
    planning = ProductionPlanning(bom_page)
    planning.open_for(saved_bom.finished.product)
    planning.plan(PLANNED_SETS)
    for component in saved_bom.raw_materials:
        assert planning.figure(component.item.product, REQUIRED_QUANTITY) == component.for_sets(PLANNED_SETS)


def test_production_planning_recalculates_when_the_planned_quantity_changes(
    saved_bom: BomSpec, bom_page: Page
) -> None:
    """MF-28 / MBC-17129: 10 then 15: RM-A 30 and RM-B 15."""
    planning = ProductionPlanning(bom_page)
    planning.open_for(saved_bom.finished.product)
    planning.plan(PLANNED_SETS)
    planning.plan(PLANNED_SETS_CHANGED)
    for component in saved_bom.raw_materials:
        expected = component.for_sets(PLANNED_SETS_CHANGED)
        assert planning.figure(component.item.product, REQUIRED_QUANTITY) == expected
