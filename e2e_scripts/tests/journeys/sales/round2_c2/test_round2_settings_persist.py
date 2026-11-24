"""Sale checklist row 49: sale bill settings remain after logging out and in again.

One fresh browser context (the plain `context` fixture, not `page_as`, which keeps one session per worker):
sign in, flip "Indicate if Item Repeated in Bill" on the garments bill, sign out, sign in again, and read it.
The original value is put back at the end, in a third sign-in if the check failed half-way.
"""

import pytest
from playwright.sync_api import BrowserContext, Page

from config.settings import settings
from pages.company_switch_page import GARMENTS_COMPANY, CompanySwitchPage
from pages.components.bill_totals import BillTotals
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.logout_page import LogoutPage
from pages.sale.garments.garments_sale_page import GarmentsSalePage
from pages.sale.manual.option_settings import ITEM_REPEATED, SaleBillSettings

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

OPPOSITE = {"yes": "No", "no": "Yes"}


def _sign_in(page: Page) -> None:
    credentials = settings.credentials("garments")
    if credentials is None:
        pytest.skip("checklist row 49: the garments account has no credentials")
    login = LoginPage(page)
    login.open()
    login.sign_in(*credentials)
    DashboardPage(page).open()
    CompanySwitchPage(page).ensure_company(GARMENTS_COMPANY)


def _read_or_set(page: Page, wanted: str | None) -> str:
    bill = GarmentsSalePage(page)
    bill.open_new_bill()
    options = SaleBillSettings(page)
    original = options.current(ITEM_REPEATED)
    if wanted is not None:
        options.choose(ITEM_REPEATED, wanted)
    BillTotals(page).leave_without_saving()
    return original


def test_a_changed_setting_survives_sign_out_and_sign_in(context: BrowserContext) -> None:
    page = context.new_page()
    _sign_in(page)
    original = _read_or_set(page, None)
    changed = OPPOSITE[original.strip().lower()]
    try:
        _read_or_set(page, changed)
        LogoutPage(page).log_out()
        LogoutPage(page).expect_signed_out()
        _sign_in(page)

        assert _read_or_set(page, None).strip().lower() == changed.lower()
    finally:
        _read_or_set(page, original)
