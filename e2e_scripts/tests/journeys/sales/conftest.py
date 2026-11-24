"""Fixtures for garments sale bill tests: a new, unsaved bill screen that is closed without saving."""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from config.settings import Account
from pages.company_switch_page import GARMENTS_COMPANY
from pages.components.bill_discount import BillDiscount
from pages.components.bill_totals import BillTotals
from pages.dashboard_page import DashboardPage
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from pages.settings.bill_discount_configuration import BillDiscountConfiguration, BillDiscountSwitches
from pages.settings.gst_configuration import GstConfiguration

GARMENTS: Account = "garments"


@pytest.fixture
def sale_page(company_page: Callable[[Account, str], Page]) -> Iterator[GarmentsSalePage]:
    page = company_page(GARMENTS, GARMENTS_COMPANY)
    DashboardPage(page).expect_menu_items(("Sale",))
    bill = GarmentsSalePage(page)
    bill.open_new_bill()
    yield bill
    BillTotals(page).leave_without_saving()


@pytest.fixture
def totals(sale_page: GarmentsSalePage) -> BillTotals:
    return BillTotals(sale_page.page)


@pytest.fixture
def original_gst_type(sale_page: GarmentsSalePage) -> Iterator[GstConfiguration]:
    """Lets a test change the calculation type; the tenant's original type is restored afterwards."""
    configuration = GstConfiguration(sale_page.page)
    original = configuration.current_gst_type()
    yield configuration
    configuration.select_gst_type(original)


@pytest.fixture
def bill_discount_fields(sale_page: GarmentsSalePage) -> Iterator[BillDiscount]:
    """Switches the bill-discount fields on; the tenant's original switches are restored afterwards."""
    configuration = BillDiscountConfiguration(sale_page.page)
    original = configuration.current_switches()
    configuration.apply(BillDiscountSwitches(discount1=True, discount2=True, in_amount=True))
    yield BillDiscount(sale_page.page)
    configuration.apply(original)
