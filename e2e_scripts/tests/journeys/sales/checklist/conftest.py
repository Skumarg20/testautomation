"""Fixtures for the sale-checklist tests: the pharma company's sale bill, and tenant switches held for a
test."""

from collections.abc import Callable, Iterator
from contextlib import ExitStack

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.dashboard_page import DashboardPage
from pages.sale.checklist.bill_screen import ChecklistBill
from pages.sale.checklist.holds import HoldDateBilling
from pages.sale.documents.flows import open_sales_page
from pages.settings.control_room import DateBilling, YesNo
from pages.settings.control_room_state import ControlRoomState
from pages.settings.control_room_switch import SwitchValue, switch_held


@pytest.fixture
def pharma_page(page_as: Callable[[Account], Page]) -> Page:
    return open_sales_page(page_as)


@pytest.fixture
def screen(pharma_page: Page) -> Iterator[ChecklistBill]:
    """A sale bill screen not yet opened; whatever bill the test left open is closed without saving."""
    bill = ChecklistBill(pharma_page)
    yield bill
    if bill.is_open:
        bill.leave()


@pytest.fixture
def bill(screen: ChecklistBill) -> ChecklistBill:
    screen.open_new()
    return screen


@pytest.fixture
def hold_date_billing(pharma_page: Page) -> Iterator[HoldDateBilling]:
    """Sets a Control Room "Sale BackDate / Future Date Billing" switch from the dashboard.

    Ask for it before `screen` or `bill`, so the bill is closed first at teardown. Each switch is read first
    and put back afterwards (`switch_held`).
    """
    stack = ExitStack()
    state = ControlRoomState(pharma_page)

    def hold(setting: DateBilling, value: YesNo) -> None:
        DashboardPage(pharma_page).open()
        held = switch_held(state, SwitchValue(setting, value), DashboardPage(pharma_page).open)
        stack.enter_context(held)

    yield hold
    stack.close()
