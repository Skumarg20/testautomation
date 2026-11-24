"""Fixtures for round-2 C1 sale cases: the pharma sale bill (item 44646015 / batch 1231231123), held settings,
saved bills deleted afterwards, and the Sales Promotion switch with a signed API session for schemes."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.dashboard_page import DashboardPage
from pages.inventory.round2_c1.own_item import OwnItem
from pages.inventory.round2_c1.two_unit_own_item import two_unit_own_item
from pages.masters.round2_c1.scheme_master import SchemeApi, open_scheme_api
from pages.masters.round2_c1.scheme_payload import SchemeItem
from pages.sale.documents.flows import open_sales_page
from pages.sale.manual.option_settings import HeldOptions, SaleBillSettings
from pages.sale.manual.pharma_bill import ITEM, PharmaBill
from pages.sale.manual.saved_bills import SavedBills
from pages.sale.round2_c1.cells import GridCells
from pages.sale.round2_c1.desk import Desk, SchemeKit
from pages.settings.control_room import YesNo
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held


@pytest.fixture
def pharma_page(page_as: Callable[[Account], Page]) -> Page:
    return open_sales_page(page_as)


@pytest.fixture
def saved_bills(pharma_page: Page) -> Iterator[SavedBills]:
    saved = SavedBills(pharma_page)
    yield saved
    saved.delete_all()


@pytest.fixture
def bill(pharma_page: Page, saved_bills: SavedBills) -> Iterator[PharmaBill]:
    new_bill = PharmaBill(pharma_page)
    yield new_bill
    if new_bill.is_open():
        new_bill.leave_without_saving()


@pytest.fixture
def options(pharma_page: Page, bill: PharmaBill) -> Iterator[HeldOptions]:
    held = HeldOptions(SaleBillSettings(pharma_page), bill.document.open_new, bill.leave_without_saving)
    yield held
    held.close()


@pytest.fixture
def cells(pharma_page: Page) -> GridCells:
    return GridCells(pharma_page)


@pytest.fixture
def promotions_on(pharma_page: Page) -> Iterator[None]:
    """Control Room "Sales Promotion" = Yes: schemes load only then (processout...component.ts:1352)."""
    dashboard = DashboardPage(pharma_page)
    dashboard.open()
    yes: YesNo = "Yes"
    with switch_held(ControlRoomState(pharma_page), SwitchValue("Sales Promotion", yes), dashboard.open):
        yield


@pytest.fixture
def scheme_api(pharma_page: Page, promotions_on: None) -> SchemeApi:
    return open_scheme_api(pharma_page)


@pytest.fixture
def scheme_item(scheme_api: SchemeApi) -> SchemeItem:
    return scheme_api.find_item(ITEM)


@pytest.fixture
def desk(bill: PharmaBill, options: HeldOptions, saved_bills: SavedBills) -> Desk:
    return Desk(bill, GridCells(bill.page), options, saved_bills)


@pytest.fixture
def schemes(scheme_api: SchemeApi, scheme_item: SchemeItem, run_id: str) -> SchemeKit:
    return SchemeKit(scheme_api, scheme_item, run_id)


@pytest.fixture
def two_unit_item(pharma_page: Page, run_id: str) -> Iterator[OwnItem]:
    with two_unit_own_item(pharma_page, run_id) as item:
        yield item
