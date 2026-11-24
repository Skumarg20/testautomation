"""J35 data-sync-offline: the "Internet Required for this option!" guards behind the offline overlay
(DS-09..DS-12).

The overlay covers every route while offline, so each test lifts it with the pack's test-only DOM tweak
(`pages/data_sync/offline_guards.py`) once it has been shown, and lets the app's own guard answer the click or
key. Every test arms a guard that aborts any send or third-party call (care portal, WhatsApp, e-mail, bill
upload, the paid GST lookup) and fails if one was tried; the browser is offline as well.
DRAFT: written from the Angular source (specs/data-sync-offline.md), not run against the app yet.
"""

from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page

from pages.company_switch_page import GARMENTS_COMPANY, PHARMA_COMPANY, CompanySwitchPage
from pages.data_sync.connection import Connectivity, NoInternetOverlay
from pages.data_sync.gst_verification import SAMPLE_GSTIN, GstVerificationWindow
from pages.data_sync.help_links import HelpLinks
from pages.data_sync.maintenance_page import ERROR_ROUTE
from pages.data_sync.offline_guards import expect_internet_required, lift_overlay
from pages.data_sync.sale_list_sends import SaleListSends
from pages.data_sync.saved_bill_print import SavedBillPrint

pytestmark = [pytest.mark.p3, pytest.mark.journey("data-sync-offline")]


def _go_offline_behind_lifted_overlay(page: Page) -> None:
    Connectivity(page).go_offline()
    NoInternetOverlay(page).expect_shown()
    lift_overlay(page)


@pytest.fixture
def own_pharma_page(own_login_page: Page, guard_outside_calls: Callable[[Page], None]) -> Page:
    """Its own form login on the pharma company, guarded. Email and WhatsApp may call the API before their
    guard; offline that ends on `/error` and a logout, which must not hit the worker's shared session."""
    guard_outside_calls(own_login_page)
    CompanySwitchPage(own_login_page).ensure_company(PHARMA_COMPANY)
    return own_login_page


@pytest.fixture
def offline_sale_list(own_pharma_page: Page) -> SaleListSends:
    """The sale bill list with one bill ticked, offline behind the lifted overlay."""
    sends = SaleListSends(own_pharma_page)
    sends.open()
    if not sends.has_a_bill():
        pytest.skip("DS-10: needs at least one sale bill on the pharma company's list")
    sends.tick_first_bill()
    _go_offline_behind_lifted_overlay(own_pharma_page)
    return sends


@pytest.fixture
def saved_bill_print(own_pharma_page: Page, sign_in_again: Callable[[], None]) -> Iterator[SavedBillPrint]:
    """A stored-case bill saved online, its print window open; the bill is deleted afterwards, after signing
    in again when the offline attempt ended in the app's logout."""
    print_window = SavedBillPrint(own_pharma_page)
    number = print_window.save_new_bill()
    yield print_window
    Connectivity(own_pharma_page).go_online()
    if not print_window.is_signed_in():
        sign_in_again()
    print_window.delete_bill(number)


def test_offline_care_portal_link_asks_for_internet(
    layout_page: Page, guard_outside_calls: Callable[[Page], None]
) -> None:
    guard_outside_calls(layout_page)
    help_links = HelpLinks(layout_page)
    help_links.open_help_window()
    _go_offline_behind_lifted_overlay(layout_page)
    pages_before = len(layout_page.context.pages)

    help_links.visit_portal.click()

    expect_internet_required(layout_page)
    assert len(layout_page.context.pages) == pages_before, "DS-09: the care portal opened while offline"


def test_offline_drug_helpline_asks_for_internet_and_stays(
    pharma_layout_page: Page, guard_outside_calls: Callable[[Page], None]
) -> None:
    guard_outside_calls(pharma_layout_page)
    help_links = HelpLinks(pharma_layout_page)
    if not help_links.drug_helpline.is_visible():
        pytest.skip("DS-09: the Drug Helpline link needs a pharma company with plan right C000123")
    _go_offline_behind_lifted_overlay(pharma_layout_page)

    help_links.drug_helpline.click()

    expect_internet_required(pharma_layout_page)
    help_links.expect_not_on_pharma_nxt()


def test_offline_upload_bills_asks_for_internet(offline_sale_list: SaleListSends) -> None:
    offline_sale_list.click_upload()

    expect_internet_required(offline_sale_list.page)


def test_offline_email_of_a_listed_bill_asks_for_internet(offline_sale_list: SaleListSends) -> None:
    offline_sale_list.press_email()

    expect_internet_required(offline_sale_list.page)


def test_offline_whatsapp_of_a_listed_bill_asks_for_internet(offline_sale_list: SaleListSends) -> None:
    offline_sale_list.press_whatsapp()

    expect_internet_required(offline_sale_list.page)


def test_offline_whatsapp_from_a_saved_bill_asks_for_internet(saved_bill_print: SavedBillPrint) -> None:
    _go_offline_behind_lifted_overlay(saved_bill_print.page)

    saved_bill_print.click_whatsapp()

    expect_internet_required(saved_bill_print.page)


def test_offline_gstin_fetch_leaves_the_ledger_form_for_manual_entry(
    own_login_page: Page, guard_outside_calls: Callable[[Page], None]
) -> None:
    guard_outside_calls(own_login_page)
    CompanySwitchPage(own_login_page).ensure_company(GARMENTS_COMPANY)
    gst_window = GstVerificationWindow(own_login_page)
    gst_window.open_from_new_ledger()
    Connectivity(own_login_page).go_offline()

    gst_window.verify_with_keyboard(SAMPLE_GSTIN)

    gst_window.expect_ledger_form_still_editable()
    assert not ERROR_ROUTE.search(own_login_page.url), (
        "DS-12: an offline GSTIN fetch left the ledger form for the maintenance page (D3)"
    )
