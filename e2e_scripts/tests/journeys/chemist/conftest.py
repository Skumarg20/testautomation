"""Fixtures for chemist-trade tests: a logged-in chemist page on the dashboard and the page objects."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import PHARMA_COMPANY, CompanySwitchPage
from pages.dashboard_page import DashboardPage
from pages.sale.chemist.ledger_master_discount_page import LedgerMasterDiscountPage
from pages.sale.chemist.ledger_special_discount_page import LedgerSpecialDiscountPage
from pages.sale.chemist.rate_validation_page import RateValidationPage
from pages.sale.chemist.restorable_rate_validation_page import RestorableRateValidationPage
from pages.sale.chemist.sale_bill import SaleBill
from pages.settings.control_room import BarcodeRequired, DateBilling, YesNo
from pages.settings.control_room_state import ControlRoomState
from pages.settings.database_repair import DatabaseRepair
from pages.settings.gst_configuration import GstConfiguration, GstType


@pytest.fixture
def chemist_page(page_as: Callable[[Account], Page]) -> Page:
    page = page_as("chemist")
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(PHARMA_COMPANY)
    return page


@pytest.fixture
def sale_bill(chemist_page: Page) -> SaleBill:
    return SaleBill(chemist_page)


@pytest.fixture
def control_room(chemist_page: Page) -> ControlRoomState:
    return ControlRoomState(chemist_page)


@pytest.fixture
def master_wise_barcodes(chemist_page: Page, control_room: ControlRoomState) -> Iterator[None]:
    """Barcode Required = Master wise, the mode the chemist tests scan master barcodes in.

    The Control Room is tenant-wide, so a test that depends on the mode asks for it instead of relying on
    what an earlier test left, and the tenant's original mode is put back after."""
    yield from _barcodes_required(chemist_page, control_room, "Master wise")


@pytest.fixture
def batch_wise_barcodes(chemist_page: Page, control_room: ControlRoomState) -> Iterator[None]:
    """Barcode Required = Batch wise; the tenant's original mode is put back after."""
    yield from _barcodes_required(chemist_page, control_room, "Batch wise")


@pytest.fixture
def sale_back_date_billing(chemist_page: Page, control_room: ControlRoomState) -> Iterator[None]:
    """Sale BackDate Billing = Yes; the tenant's original choice is put back after."""
    yield from _date_billing_held(chemist_page, control_room, ("Sale BackDate Billing", "Yes"))


@pytest.fixture
def sale_future_date_billing(chemist_page: Page, control_room: ControlRoomState) -> Iterator[None]:
    """Sale Future Date Billing = Yes; the tenant's original choice is put back after."""
    yield from _date_billing_held(chemist_page, control_room, ("Sale Future Date Billing", "Yes"))


@pytest.fixture
def sale_back_date_billing_off(chemist_page: Page, control_room: ControlRoomState) -> Iterator[None]:
    """Sale BackDate Billing = No; the tenant's original choice is put back after."""
    yield from _date_billing_held(chemist_page, control_room, ("Sale BackDate Billing", "No"))


@pytest.fixture
def sale_future_date_billing_off(chemist_page: Page, control_room: ControlRoomState) -> Iterator[None]:
    """Sale Future Date Billing = No; the tenant's original choice is put back after."""
    yield from _date_billing_held(chemist_page, control_room, ("Sale Future Date Billing", "No"))


def _barcodes_required(page: Page, control_room: ControlRoomState, mode: BarcodeRequired) -> Iterator[None]:
    original = control_room.current_barcode_required()
    control_room.set_barcode_required(mode)
    yield
    DashboardPage(page).open()  # a fresh start: the test leaves its bill open
    control_room.set_barcode_required(original)


def _date_billing_held(
    page: Page, control_room: ControlRoomState, wanted: tuple[DateBilling, YesNo]
) -> Iterator[None]:
    setting, value = wanted
    original = control_room.current_date_billing(setting)
    control_room.set_date_billing(setting, value)
    yield
    DashboardPage(page).open()  # a fresh start: the test leaves its bill open
    control_room.set_date_billing(setting, original)


@pytest.fixture
def use_gst_type(chemist_page: Page) -> Iterator[Callable[[GstType], None]]:
    """Sets the GST calculation type from the current screen; the tenant's original is put back after."""
    configuration = GstConfiguration(chemist_page)
    originals: list[GstType] = []

    def use(gst_type: GstType) -> None:
        if not originals:
            originals.append(configuration.current_gst_type())
        configuration.select_gst_type(gst_type)

    yield use
    if originals:
        configuration.select_gst_type(originals[0])


@pytest.fixture
def rates(chemist_page: Page) -> Iterator[RateValidationPage]:
    """Rate validation; the tenant's Default Billing Rate is put back after, from the screen the test left."""
    page = RestorableRateValidationPage(chemist_page)
    yield page
    page.restore_default_billing_rate()


@pytest.fixture
def ledger_master(chemist_page: Page) -> LedgerMasterDiscountPage:
    return LedgerMasterDiscountPage(chemist_page)


@pytest.fixture
def ledger_special(chemist_page: Page) -> LedgerSpecialDiscountPage:
    return LedgerSpecialDiscountPage(chemist_page)


@pytest.fixture
def database_repair(chemist_page: Page) -> DatabaseRepair:
    return DatabaseRepair(chemist_page)
