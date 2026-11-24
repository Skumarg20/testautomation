"""Item-master free deal ("Free + Scheme" with a Scheme Type) and Net Scheme: Ajay rows 135-137, 210, 211;
Sale Checklist rows 60, 74, 86, 87, 89.

Item 44646015 gets the deal 10 + 1 for the test and its own deal is written back afterwards (`deal_held`).
The bill computes the free quantity when the quantity is entered (applyFreeSchemeOnTransaction,
processout.transaction.component.ts:13414-13466) when "Free Quantity Required in Sale" is Yes and "Free Deal
From" is Master (:13430); formulas and lines are in pages/sale/round2_c1/deal_math.py. Net Scheme (Sale Bill
Setting) only changes the Whole and All schemes (Scheme.businesslogic.ts:757-778).
Decision needed (product owner): sheet row 136 says a net scheme must NOT apply below the threshold, but the
code gives a Whole scheme of 9 pieces the net share 0.09 x 9 = 0.81 (:768-778). The test asserts the code.
"""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from playwright.sync_api import Page

from pages.inventory.round2_c1.item_deal import Deal, ItemDealForm, deal_held
from pages.inventory.round2_c1.own_item import ItemSetup, own_stocked_item
from pages.sale.documents.item_grid import QUANTITY
from pages.sale.manual.option_settings import NET_SCHEME
from pages.sale.manual.pharma_bill import ITEM
from pages.sale.round2_c1.cells import FREE
from pages.sale.round2_c1.deal_math import (
    all_scheme_free,
    full_scheme_free,
    half_scheme_free,
    reverse_free,
    whole_scheme_net_free,
)
from pages.sale.round2_c1.desk import Desk
from pages.sale.round2_c1.own_item_sale import start_with_item
from pages.settings.round2_c1.fields import FREE_DEAL_FROM, FREE_QTY_ON_SALE
from pages.settings.round2_c1.netscheme_window import NetSchemeWindow, net_scheme_configured

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

DEAL = (10, 1)
FORMULA = "1"


def _deal(scheme_type: str) -> Deal:
    return Deal(str(DEAL[0]), str(DEAL[1]), scheme_type)


@pytest.fixture
def deal_form(pharma_page: Page) -> ItemDealForm:
    return ItemDealForm(pharma_page)


@pytest.fixture
def free_from_master(desk: Desk) -> Desk:
    desk.options.hold(FREE_QTY_ON_SALE, "Yes")
    desk.options.hold(FREE_DEAL_FROM, "Master")
    return desk


@pytest.fixture
def net_scheme_on(free_from_master: Desk) -> Iterator[Desk]:
    """Net Scheme Yes with formula 1 (free = 0.09 x quantity) and Reverse Calculation No."""
    desk = free_from_master
    desk.options.hold(NET_SCHEME, "Yes")
    desk.bill.document.open_new()
    with net_scheme_configured(NetSchemeWindow(desk.bill.page), FORMULA, "No"):
        desk.bill.leave_without_saving()
        yield desk
        desk.bill.document.open_new()


def _expect_free(desk: Desk, expected: Decimal) -> None:
    if expected:
        desk.cells.expect_value(0, FREE, expected)
    else:
        desk.cells.expect_empty_or_zero(0, FREE)


def _sell(desk: Desk, quantity: int) -> None:
    desk.bill.start()
    desk.bill.pick_item(0, Decimal(quantity))


@pytest.mark.parametrize(
    "case",
    [
        ("Full Scheme", 25, Decimal(full_scheme_free(25, DEAL))),
        ("Half Scheme", 4, half_scheme_free(4, DEAL)),
        ("Half Scheme", 10, half_scheme_free(10, DEAL)),
        ("All Scheme", 25, all_scheme_free(25, DEAL)),
        ("No Scheme", 25, Decimal(0)),
    ],
    ids=["full-25", "half-4", "half-10", "all-25", "none-25"],
)
def test_free_deal_from_master_follows_the_scheme_type(
    free_from_master: Desk, deal_form: ItemDealForm, case: tuple[str, int, Decimal]
) -> None:
    """Rows 74 (Master), 87 and 89 (decimal free of the All scheme): 10 + 1 sold at the case's quantity."""
    scheme_type, quantity, expected = case
    with deal_held(deal_form, ITEM, _deal(scheme_type)):
        _sell(free_from_master, quantity)

        _expect_free(free_from_master, expected)


@pytest.mark.parametrize("quantity", [9, 10, 15])
def test_net_scheme_on_adds_the_net_share(
    net_scheme_on: Desk, deal_form: ItemDealForm, quantity: int
) -> None:
    """Rows 135 (exactly 10), 136 (9), 137 (15) and 210: Whole scheme 10 + 1, Net Scheme Yes, formula 1."""
    with deal_held(deal_form, ITEM, _deal("Whole Scheme")):
        _sell(net_scheme_on, quantity)

        _expect_free(net_scheme_on, whole_scheme_net_free(quantity, DEAL, int(FORMULA)))


@pytest.mark.parametrize("quantity", [9, 10, 15])
def test_net_scheme_off_gives_only_whole_deals(
    free_from_master: Desk, deal_form: ItemDealForm, quantity: int
) -> None:
    """Rows 211 and 60 (switched off): the same sale gives floor(quantity / 10) free and no net share."""
    free_from_master.options.hold(NET_SCHEME, "No")
    with deal_held(deal_form, ITEM, _deal("Whole Scheme")):
        _sell(free_from_master, quantity)

        _expect_free(free_from_master, Decimal(full_scheme_free(quantity, DEAL)))


def test_reverse_calculation_gives_the_proportional_free(
    free_from_master: Desk, deal_form: ItemDealForm
) -> None:
    """Row 86: Net Scheme and Reverse Calculation both Yes, Full 10 + 1, 25 pieces -> free 25 / 10 x 1 =
    2.5."""
    desk = free_from_master
    desk.options.hold(NET_SCHEME, "Yes")
    desk.bill.document.open_new()
    with net_scheme_configured(NetSchemeWindow(desk.bill.page), FORMULA, "Yes"):
        desk.bill.leave_without_saving()
        with deal_held(deal_form, ITEM, _deal("Full Scheme")):
            _sell(desk, 25)

            desk.cells.expect_value(0, FREE, reverse_free(25, DEAL))
            desk.cells.expect_value(0, QUANTITY, Decimal(25))
        desk.bill.leave_without_saving()
        desk.bill.document.open_new()


@pytest.mark.parametrize("source", ["Manual", "Lot", "Lot & Free"])
def test_other_free_deal_sources_do_not_fill_free_from_the_master(
    free_from_master: Desk, deal_form: ItemDealForm, source: str
) -> None:
    """Row 74 (Manual, Lot, Lot & Free): only "Master" and "Batch" read a deal; any other source leaves
    free empty
    (applyFreeSchemeOnTransaction :13430-13464, the final `else` sets free to 0). Batch needs a deal stored on
    the batch itself and is not scripted here."""
    free_from_master.options.hold(FREE_DEAL_FROM, source)
    with deal_held(deal_form, ITEM, _deal("Full Scheme")):
        _sell(free_from_master, 25)

        _expect_free(free_from_master, Decimal(0))


def test_free_deal_from_batch_uses_the_deal_stored_on_the_batch(
    pharma_page: Page, free_from_master: Desk, run_id: str
) -> None:
    """Row 74 (Batch): the test's own item (scheme type Full) is bought on a purchase bill whose
    new batch holds the
    deal 10 + 1; with Free Deal From = Batch a sale of 25 from that batch shows 2 free
    (applyFreeSchemeOnTransaction :13433-13445 reads batchData.scheme1/scheme2; the type comes from the item).
    The purchase bill and the item are deleted afterwards (own_stocked_item)."""
    desk = free_from_master
    desk.options.hold(FREE_DEAL_FROM, "Batch")
    with own_stocked_item(pharma_page, run_id, ItemSetup(DEAL, "Full Scheme")) as item:
        start_with_item(desk.bill, item, Decimal(25))

        _expect_free(desk, Decimal(full_scheme_free(25, DEAL)))
        desk.bill.leave_without_saving()
